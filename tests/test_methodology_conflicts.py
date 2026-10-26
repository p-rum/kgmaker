"""T003-S09-W04: exact approval binding and offline cached evidence."""
import hashlib
import json
from pathlib import Path

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.confluence import ingest_export, persist_validation_index, validate_documents
from kgmaker.feature import prepare
from kgmaker.scanner import scan_repository


def export_fixture(root):
    export = root / 'export'
    export.mkdir()
    page = export / 'Methodology.html'
    page.write_text('<h1>Approved</h1><p>PaymentService calls LegacyGateway.</p>')
    item = dict(id='route', document_file=page.name,
                document_sha256=hashlib.sha256(page.read_bytes()).hexdigest(), section='Approved',
                subject='PaymentService', relation='CALLS', target='LegacyGateway',
                statement='PaymentService calls LegacyGateway', decision_id='ARCH-42',
                decision_revision=1, approval_status='APPROVED')
    sidecar = export / 'kgmaker-approved-requirements.json'
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    (root / 'payment.py').write_text('from fraud import FraudService\nclass PaymentService:\n def run(self): return FraudService()\n')
    (root / 'fraud.py').write_text('class FraudService: pass\n')
    (root / 'requirement.md').write_text('Change routing')
    return export, page, sidecar, item


@pytest.mark.parametrize('mutation', ['page', 'approval'])
def test_stale_cached_approval_is_not_carried_into_feature(tmp_path, mutation):
    export, page, sidecar, item = export_fixture(tmp_path)
    documents, _, _ = ingest_export(export, tmp_path)
    assertions = validate_documents(documents, scan_repository(tmp_path))
    persist_validation_index(tmp_path, assertions)
    original = (tmp_path / '.kgmaker/confluence-index.json').read_bytes()
    if mutation == 'page':
        page.write_text(page.read_text() + '<p>Second version</p>')
    else:
        item['approval_status'] = 'UNAPPROVED'
        sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    packet = prepare(tmp_path, 'requirement.md', 'stale-approval')
    assert not packet['coverage'].get('documentation_conflicts')
    assert any('stale' in text.lower() for text in packet['coverage']['limitations'])
    assert (tmp_path / '.kgmaker/confluence-index.json').read_bytes() == original


def test_duplicate_assertion_approvals_rejected_without_cache_mutation(tmp_path):
    export, page, sidecar, item = export_fixture(tmp_path)
    ingest_export(export, tmp_path)
    original = (tmp_path / '.kgmaker/confluence-index.json').read_bytes()
    duplicate = dict(item, id='other-decision', approval_status='UNAPPROVED')
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item, duplicate])))
    with pytest.raises(AnalysisError, match='Ambiguous'):
        ingest_export(export, tmp_path)
    assert (tmp_path / '.kgmaker/confluence-index.json').read_bytes() == original


def test_new_document_version_requires_new_explicit_approval(tmp_path):
    export, page, sidecar, item = export_fixture(tmp_path)
    ingest_export(export, tmp_path)
    original = (tmp_path / '.kgmaker/confluence-index.json').read_bytes()
    page.write_text(page.read_text() + '<!-- exported version 2 -->')
    with pytest.raises(AnalysisError, match='exact exported document'):
        ingest_export(export, tmp_path)
    assert (tmp_path / '.kgmaker/confluence-index.json').read_bytes() == original
    item['document_sha256'] = hashlib.sha256(page.read_bytes()).hexdigest()
    item['decision_revision'] = 2
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    documents, _, _ = ingest_export(export, tmp_path)
    conflict = validate_documents(documents, scan_repository(tmp_path))[0]
    assert conflict.authority == 'APPROVED_REQUIREMENT'
    assert conflict.decision_revision == 2
    assert conflict.approved_document_sha256 == item['document_sha256']


def test_legacy_index_is_readable_without_granting_approval():
    from kgmaker.confluence import current_documentation_assertions
    with pytest.raises(AnalysisError, match='stale'):
        current_documentation_assertions(dict(directory='/unused', pages={}, assertions=[]))


def test_unextractable_approval_does_not_publish_cache(tmp_path):
    export, page, sidecar, item = export_fixture(tmp_path)
    item['target'] = 'DifferentGateway'
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    with pytest.raises(AnalysisError, match='extracted assertion'):
        ingest_export(export, tmp_path)
    assert not (tmp_path / '.kgmaker/confluence-index.json').exists()


@pytest.mark.parametrize('mutation', ['changed', 'deleted'])
def test_attachment_freshness_is_checked_offline_without_mutating_index(tmp_path, mutation):
    from unittest.mock import patch
    from kgmaker.analysis_model import read_json
    from kgmaker.confluence import current_documentation_assertions

    export, page, sidecar, item = export_fixture(tmp_path)
    attachment = export / 'routing.svg'
    attachment.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    page.write_text(page.read_text() + '<img src="routing.svg">')
    item['document_sha256'] = hashlib.sha256(page.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    documents, _, _ = ingest_export(export, tmp_path)
    assertions = validate_documents(documents, scan_repository(tmp_path))
    persist_validation_index(tmp_path, assertions)
    index = tmp_path / '.kgmaker/confluence-index.json'
    original = index.read_bytes()
    cache = read_json(index)
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        assert any(a['authority'] == 'APPROVED_REQUIREMENT'
                   for a in current_documentation_assertions(cache))
        if mutation == 'changed':
            attachment.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>new</text></svg>')
        else:
            attachment.unlink()
        with pytest.raises(AnalysisError, match='attachment index is stale'):
            current_documentation_assertions(cache)
    packet = prepare(tmp_path, 'requirement.md', 'stale-attachment')
    assert not packet['coverage'].get('documentation_conflicts')
    assert any('attachment index is stale' in message for message in packet['coverage']['limitations'])
    assert index.read_bytes() == original


@pytest.mark.parametrize('mutation', ['page', 'approval', 'attachment'])
def test_prepared_packet_rejects_stale_external_documentation(tmp_path, mutation):
    from kgmaker.feature import freshness

    root = tmp_path / 'repo'
    root.mkdir()
    export, page, sidecar, item = export_fixture(root)
    attachment = export / 'routing.svg'
    attachment.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    page.write_text(page.read_text() + '<img src="routing.svg">')
    item['document_sha256'] = hashlib.sha256(page.read_bytes()).hexdigest()
    sidecar.write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    external = tmp_path / 'external-export'
    export.rename(external)
    documents, _, _ = ingest_export(external, root)
    persist_validation_index(root, validate_documents(documents, scan_repository(root)))
    packet = prepare(root, 'requirement.md', 'external-methodology')
    assert any(c['authority'] == 'APPROVED_REQUIREMENT'
               for c in packet['coverage']['documentation_conflicts'])
    assert not freshness(root, packet)
    index = root / '.kgmaker/confluence-index.json'
    packet_path = root / '.kgmaker/analyses/external-methodology/packet.json'
    original_index, original_packet = index.read_bytes(), packet_path.read_bytes()
    if mutation == 'page':
        page = external / page.name
        page.write_text(page.read_text() + '<p>Version two</p>')
    elif mutation == 'approval':
        item['approval_status'] = 'UNAPPROVED'
        (external / sidecar.name).write_text(json.dumps(dict(schema_version=1, requirements=[item])))
    else:
        (external / attachment.name).unlink()
    assert 'coverage.documentation_conflicts changed or became stale' in freshness(root, packet)
    assert index.read_bytes() == original_index
    assert packet_path.read_bytes() == original_packet

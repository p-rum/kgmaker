"""Real Java evidence, narrow read-only use, and unchanged legacy data proofs."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA, digest, inventory_candidate, write_json
from kgmaker.availability import evaluate_proof
from kgmaker.callgraph import adjacency
from kgmaker.cli import build_parser
from kgmaker.data_check import data_check
from kgmaker.dataflow import field_mapping_bindings, impact_paths
from kgmaker.feature_cli import run as run_feature
from kgmaker.runtime_evidence import import_manifest, produce_manifest
from kgmaker.runtime_value import FACT, PROOF
from kgmaker.store import GRAPH_FILE, MARKDOWN_FILE, MERMAID_FILE, load_graph
from tests.test_runtime_trace_producer import compile_runtime_fixture, inspect_runtime_fixture


ARTIFACT = Path('.kgmaker/runtime/presence.json')
VALUE = 'SYNTHETIC_FIXTURE_VALUE_49F95_NO_EXPORT'


@pytest.fixture(scope='module')
def application(tmp_path_factory):
    root, java, classes = compile_runtime_fixture(tmp_path_factory, 'runtime-value-presence', 'ValuePresenceApplication.java')
    (root / 'requirement.md').write_text('Use the current status for a scoped audit.\n')
    context = inspect_runtime_fixture(root, classes, 'w03-presence', digest({'fixture': 'presence'}))
    (root / ARTIFACT).parent.mkdir(exist_ok=True)
    argv = [str(java), '-cp', str(classes), 'fixture.ValuePresenceApplication']
    return root, argv, context


def produce(application, mode, *args):
    root, argv, context = application
    return produce_manifest(root, [*argv, mode, *args], context_id=context['id'], runtime_id='value-' + mode,
                            build_id=context['build_id'], config_fingerprint=context['config_fingerprint'],
                            service_id='presence-fixture', service_version='1', output=ARTIFACT)


def outputs(root):
    return {path: (root / path).read_bytes() for path in (ARTIFACT, GRAPH_FILE, MARKDOWN_FILE, MERMAID_FILE)}


def proof_input(requirement, input_id, target, evidence_id, metadata):
    return {'id': input_id, 'name': 'status', 'requirement_ids': [requirement['id']], **metadata,
            'candidate_entity_ids': [target], 'availability_proof': {
                'kind': PROOF, 'runtime_evidence_id': evidence_id, 'mapping_decision_id': 'approved-status',
            }}


def check_projected_hook_authority(root, packet, candidate, item):
    graph = feature.graph_for_packet(root, packet)
    original, = [row for row in graph.evidence if row['id'] == item['availability_proof']['runtime_evidence_id']]
    hook, = [site for site in graph.call_sites if site['id'] == original['hook_call_site']]
    other_hook, = [site['id'] for site in graph.call_sites if site.get('declared_target') == hook['declared_target']
                   and 'ValuePresenceApplication.reversed(' in site['caller'] and site.get('range')]
    missing = replace(graph, call_sites=[site for site in graph.call_sites if site['id'] != hook['id']])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_SITE'):
        evaluate_proof(root, packet, candidate, item, missing)
    wrong_ordinal = replace(graph, evidence=[{**row, 'parameter_index': 1} if row.get('call_site') == hook['id']
                                            and row.get('argument_index') == 0 else row for row in graph.evidence])
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_ARGUMENTS'):
        evaluate_proof(root, packet, candidate, item, wrong_ordinal)
    for field, value, error in (
        ('hook_call_site', other_hook, 'matching compiler hook proof'),
        ('runtime_id', 'invalid\n' + VALUE, 'identifier: runtime_id'),
        ('service_id', 'invalid\n' + VALUE, 'identifier: service_id'),
        ('service_version', 'invalid\n' + VALUE, 'identifier: service_version'),
    ):
        modified = {key: field_value for key, field_value in original.items() if key != 'id'}
        modified[field] = value
        modified['id'] = 'evidence:' + digest(modified)
        changed = replace(graph, evidence=[modified if row['id'] == original['id'] else row for row in graph.evidence],
                          edges=[replace(edge, evidence_ids=tuple(modified['id'] if ref == original['id'] else ref
                                                                 for ref in edge.evidence_ids)) for edge in graph.edges])
        changed_packet = {**packet, 'graph_evidence_ids': [*packet['graph_evidence_ids'], modified['id']]}
        input_item = {**item, 'availability_proof': {**item['availability_proof'], 'runtime_evidence_id': modified['id']}}
        with pytest.raises(AnalysisError, match=error) as exc:
            evaluate_proof(root, changed_packet, candidate, input_item, changed)
        assert VALUE not in str(exc.value)


def test_actual_java_value_presence_affects_only_matching_live_data_check(application, monkeypatch, capsys):
    root, argv, context = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    monkeypatch.delenv('KGMAKER_RUNTIME_TRACE', raising=False)
    assert subprocess.run([*argv, 'present'], cwd=root, capture_output=True, check=True).stdout == b''
    graph = load_graph(root)
    symbols = {item['name']: item for item in graph.symbols if item.get('kind') == 'method'
               and item.get('owner') == 'fixture.ValuePresenceApplication'}
    bindings = field_mapping_bindings(graph)
    mapping, = [row for row in bindings if row['relation'] == 'maps_to' and row['owner_method'] == symbols['copy']['id']]
    source, target = mapping['source'], mapping['target']
    call = produce(application, 'call', symbols['main']['id'], symbols['plain']['id'])
    assert call['schema_version'] == 2 and call['facts'][0]['kind'] == 'call'
    call['observations'] = [{'caller': symbols['main']['id'], 'target': symbols['plain']['id'], 'kind': 'call'}]
    with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
        assert import_manifest(root, call)['observations_imported'] == 1
    call_graph = load_graph(root)
    call_record, = [row for row in call_graph.evidence if row.get('runtime_id') == 'value-call']
    assertions = {}
    present = None
    for run, expected in [('present', 'PRESENT'), ('absent', 'ABSENT')]:
        manifest = produce(application, run)
        assert manifest['schema_version'] == 4 and manifest['observations'] == []
        fact, = manifest['facts']
        assert fact['presence'] == expected and fact['kind'] == FACT
        with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
            assertions[run], = import_manifest(root, manifest)['value_evidence_ids']
        if run == 'present':
            present = manifest
    before_replay = outputs(root)
    with pytest.raises(AnalysisError, match='RUNTIME_VALUE_AMBIGUOUS'):
        import_manifest(root, {**present, 'facts': manifest['facts']})
    assert outputs(root) == before_replay
    older = {**manifest, 'facts': [dict(manifest['facts'][0], presence='PRESENT')], 'runtime_id': 'expired',
             'run_started_at': (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()}
    assertions['expired'], = import_manifest(root, older)['value_evidence_ids']
    after = load_graph(root)
    assert field_mapping_bindings(after) == bindings
    assert impact_paths(after, source) == impact_paths(call_graph, source)
    assert adjacency(after) == adjacency(call_graph)
    packet = feature.prepare(root, 'requirement.md', 'w03', scope='production', context_id=context['id'])
    input_id, question_id = 'analysis:w03:input:status', 'analysis:w03:question:mapping'
    candidate = inventory_candidate(packet)
    requirement = {key: candidate['requirements'][0][key] for key in ('id', 'text', 'kind', 'source_quote')}
    candidate['questions'] = [{'id': question_id, 'text': 'Approve this exact status input?', 'owner_role': 'Analyst',
                              'status': 'OPEN', 'requirement_ids': [requirement['id']], 'blocking': True}]
    assert feature.apply(root, 'w03', candidate)['valid']
    metadata = dict.fromkeys(INPUT_METADATA)
    metadata.update(definition='Current status', data_type='string', freshness='PT1H', keys=['accountId'], quality=['nonempty'])
    answer = {'question_id': question_id, 'decision_id': 'approved-status', 'approval_status': 'APPROVED', 'revision': 1,
              'answer': json.dumps({'input_id': input_id, 'entity_id': target, 'metadata': metadata})}
    packet = feature.revise(root, 'w03', {'answers': [answer]})
    specification = {'schema_version': 1, 'analysis_id': 'w03', 'requirement_hash': packet['requirement_hash'],
                     'requirements': [requirement], 'inputs': [proof_input(requirement, input_id, target, assertions['present'], metadata)]}
    path = Path('.kgmaker/analyses/w03/live-inputs.json')
    write_json(root / path, specification)
    before = outputs(root)
    tracked = {file: file.read_bytes() for file in (root / '.kgmaker/analyses/w03').rglob('*.json')}
    real_popen = subprocess.Popen

    def read_only_git(command, *args, **kwargs):
        assert command == ['git', '-C', str(root), 'rev-parse', 'HEAD'], command
        return real_popen(command, *args, **kwargs)

    with patch('subprocess.Popen', side_effect=read_only_git):
        parsed = build_parser().parse_args(['feature', 'data-check', '--root', str(root), '--analysis', 'w03', '--inputs', str(path)])
        assert run_feature(parsed) == 0
        live = json.loads(capsys.readouterr().out)
        item, = live['candidate']['input_requirements']
        assert (item['availability'], item['usability']) == ('PARTIAL', 'UNASSESSED')
        assert 'value-present' in item['verification_scope'] and assertions['present'] in item['verification_scope']
        check_projected_hook_authority(root, packet, live['candidate'], item)
        assert not feature.apply(root, 'w03', live['candidate'])['valid']
        for evidence_id in (assertions['absent'], assertions['expired'], call_record['id'], 'evidence:arbitrary'):
            rejected = deepcopy(specification)
            rejected['inputs'][0]['availability_proof']['runtime_evidence_id'] = evidence_id
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
        for changes in ({'definition': 'Different business definition'}, {'candidate_entity_ids': [source]},
                        {'candidate_entity_ids': []}):
            rejected = deepcopy(specification)
            rejected['inputs'][0].update(changes)
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
        for updates in ({'raw_value': VALUE}, {'mapping_decision_id': VALUE}, {'runtime_evidence_id': VALUE}):
            rejected = deepcopy(specification)
            rejected['inputs'][0]['availability_proof'].update(updates)
            result = data_check(root, 'w03', rejected)
            assert result['valid'] and result['candidate']['input_requirements'][0]['availability'] == 'UNKNOWN'
            assert VALUE not in json.dumps(result)
    assert {file: file.read_bytes() for file in (root / '.kgmaker/analyses/w03').rglob('*.json')} == tracked
    assert outputs(root) == before
    forbidden = (VALUE.encode(), sha256(VALUE.encode()).hexdigest().encode())
    assert all(marker not in content for content in [*before.values(), json.dumps(live).encode()] for marker in forbidden)


def test_actual_java_value_capture_and_import_reject_unbound_evidence(application, monkeypatch):
    root, _, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    valid = produce(application, 'present')
    before = outputs(root)
    for mode in ('reversed', 'ambiguous'):
        with pytest.raises(AnalysisError, match='RUNTIME_VALUE_(ARGUMENTS|BINDING)'):
            produce(application, mode)
        assert outputs(root) == before
    with patch('subprocess.Popen', side_effect=AssertionError('Offline import spawned a process')):
        for updates, reason in [({'facts': [{**valid['facts'][0], 'raw_value': VALUE}]}, 'RUNTIME_VALUE_FACT'),
                                ({'facts': [{**valid['facts'][0], 'caller_name': 'plain'}]}, 'RUNTIME_VALUE_BINDING'),
                                ({'config_fingerprint': 'foreign'}, 'STALE_RUNTIME'),
                                ({'run_started_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}, 'RUNTIME_VALUE_CLOCK')]:
            with pytest.raises(AnalysisError, match=reason) as error:
                import_manifest(root, {**valid, **updates})
            assert VALUE not in str(error.value)
        java = root / 'src/main/java/ValuePresenceApplication.java'
        original = java.read_bytes()
        try:
            java.write_bytes(original + b'\n// changed\n')
            with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
                import_manifest(root, valid)
            with pytest.raises(AnalysisError, match='STALE_RUNTIME'):
                produce(application, 'present')
        finally:
            java.write_bytes(original)
    assert outputs(root) == before


def test_actual_java_value_capture_rechecks_late_source_change_before_replace(application, monkeypatch):
    from kgmaker import analysis_model

    root, _, _ = application
    monkeypatch.setenv('FIXTURE_ONLY_VALUE', VALUE)
    produce(application, 'present')
    before = outputs(root)
    source = root / 'src/main/java/ValuePresenceApplication.java'
    original = source.read_bytes()
    real_atomic = analysis_model.atomic_write

    def changed_input(path, text, *, before_replace=None):
        if path == root / ARTIFACT:
            assert before_replace is not None
            source.write_bytes(original + b'\n// changed during publication\n')
        return real_atomic(path, text, before_replace=before_replace)

    monkeypatch.setattr(analysis_model, 'atomic_write', changed_input)
    try:
        with pytest.raises(AnalysisError, match='STALE_RUNTIME: source changed'):
            produce(application, 'present')
    finally:
        source.write_bytes(original)
    assert outputs(root) == before

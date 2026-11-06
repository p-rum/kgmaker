"""T006/T008 public mixed workspace context-role boundaries; no worker/build."""
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

import pytest

from kgmaker.views import project_service_inventory, select_service_contexts, ContextSelectionError, ServiceInventoryError
from kgmaker.workspace import load_workspace, snapshot_workspace
from test_kafka_bindings import kafka_workspace


@pytest.fixture
def mixed_snapshot(kafka_workspace):
    root, manifest, declaration = kafka_workspace
    for repo in ('producer', 'consumer'):
        source = root / repo / 'src/main/java/App.java'
        source.parent.mkdir(parents=True)
        source.write_text('class App {}\n')
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    return load_workspace(manifest), graph, coverage


@pytest.mark.parametrize('catalog', ['inventory', 'http-providers', 'http-consumers', 'data-resources', 'triggers'])
def test_full_mixed_snapshot_reaches_original_source_inventory_without_mutation(mixed_snapshot, catalog):
    workspace, graph, coverage = mixed_snapshot
    from kgmaker.interfaces import project_http_providers, project_http_consumers
    from kgmaker.data_resources import project_data_resources
    from kgmaker.process_triggers import discover_process_triggers
    project = {'inventory': project_service_inventory, 'http-providers': project_http_providers,
               'http-consumers': project_http_consumers, 'data-resources': project_data_resources, 'triggers': discover_process_triggers}[catalog]
    before = deepcopy((workspace, graph.to_dict(), coverage))
    assert any(c.get('origin_trust') == 'WORKSPACE_DECLARATION' for c in graph.contexts)
    with patch('subprocess.Popen', side_effect=AssertionError('projection process')), patch('socket.create_connection', side_effect=AssertionError('projection network')):
        result = project(workspace, graph, source_coverage=coverage)
    assert {'producer-svc', 'consumer-svc'} <= set(result.context_selection['services'])
    if catalog != 'triggers':
        assert {'service:producer-svc', 'service:consumer-svc'} <= {n.id for n in result.nodes if n.kind == 'service'}
    assert (workspace, graph.to_dict(), coverage) == before
    if catalog == 'inventory':
        rows = [r for service in result.context_selection['services'].values() for r in service['contexts']]
        assert all(not str(row.get('context_id', '')).startswith('workspace:kafka-context:') for row in rows)
        assert all(row['status'] != 'CURRENT' for row in rows)  # actual SOURCE_ONLY capture
    assert all(n.kind not in {'http_endpoint', 'http_request', 'process_trigger'} for n in result.nodes)


@pytest.mark.parametrize('mutation', ['version', 'origin', 'input-hash', 'scope', 'repo', 'identity',
                                    'version-shape', 'freshness-shape', 'module', 'source-set', 'extra-path', 'foreign-selector', 'captured-hash'])
def test_malformed_derived_claim_is_diagnosed_without_ownership_fallback(mixed_snapshot, mutation):
    workspace, graph, coverage = mixed_snapshot
    candidate = next(c for c in graph.contexts if c.get('origin_trust') == 'WORKSPACE_DECLARATION')
    if mutation == 'version': candidate['kafka_binding_version'] = 'future-unknown'
    elif mutation == 'origin': candidate['origin_trust'] = 'UNRECOGNIZED_DERIVED_ROLE'
    elif mutation == 'input-hash': candidate['source_files'] = []
    elif mutation == 'captured-hash': candidate['source_files'][next(iter(candidate['source_files']))] = '0' * 64
    elif mutation == 'scope': candidate['scope'] = 'test'
    elif mutation == 'repo': candidate['repo_id'] = 'schemas'
    elif mutation == 'version-shape': candidate['kafka_binding_version'] = []
    elif mutation == 'freshness-shape': candidate['freshness'] = []
    elif mutation == 'module': candidate['module'] = 'foreign-module'
    elif mutation == 'source-set': candidate['source_set'] = 'test'
    elif mutation == 'extra-path': candidate['source_files']['@foreign/config.properties'] = 'f' * 64
    elif mutation == 'foreign-selector':
        from kgmaker.workspace import qualified
        candidate['selected_compiler_context'] = qualified('schemas', 'foreign')
    else:
        old = candidate['id']; candidate['id'] += '-forged'; new = candidate['id']
        # Keep the supplied Graph structurally valid so the identity guard,
        # rather than dangling-reference validation, is what rejects the claim.
        graph.edges = [replace(e, context_ids=tuple(new if c == old else c for c in e.context_ids)) for e in graph.edges]
        for proof in graph.evidence:
            if isinstance(proof.get('context_ids'), list):
                proof['context_ids'] = [new if c == old else c for c in proof['context_ids']]
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('projection process')):
        result = project_service_inventory(workspace, graph, source_coverage=coverage)
    assert any(d.get('code') == 'UNKNOWN_CONTEXT_ROLE' for d in result.diagnostics)
    assert (workspace, graph.to_dict(), coverage) == before


@pytest.mark.parametrize('mode', ['COMPILER', 'SOURCE_ONLY'])
def test_derived_claim_cannot_be_pinned_as_compiler_even_with_analyzer_marker(mixed_snapshot, mode):
    _, graph, coverage = mixed_snapshot
    candidate = next(c for c in graph.contexts if c.get('origin_trust') == 'WORKSPACE_DECLARATION')
    candidate['analyzer_version'] = 'spoofed-compiler-marker'
    request = {'service_id': 'producer-svc', 'repo_id': candidate['repo_id'], 'module': candidate['module'],
               'scope': candidate['scope'], 'mode': mode, 'context_id': candidate['id']}
    before = deepcopy(graph.to_dict())
    with pytest.raises(ContextSelectionError) as error:
        select_service_contexts(graph, [request], scope='production', source_coverage=coverage)
    assert error.value.diagnostic['code'] == 'INVALID_CONTEXT_ROLE'
    assert graph.to_dict() == before


def test_historical_derived_identity_does_not_require_current_private_replay(mixed_snapshot):
    workspace, original, _ = mixed_snapshot
    historical = deepcopy(next(c for c in original.contexts if c.get('origin_trust') == 'WORKSPACE_DECLARATION'))
    repo = next(r for r in workspace['repositories'] if r['id'] == historical['repo_id'])
    from pathlib import Path
    config = Path(repo['_root']) / 'src/main/resources/application.properties'
    config.write_text(config.read_text() + '\n# changed after captured declaration\n')
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    historical['freshness'] = 'STALE'
    historical['stale_reason'] = 'captured before current source'
    graph.contexts.append(historical)
    assert any(graph.files.get(path) != sha for path, sha in historical['source_files'].items())
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('projection process')), patch('kgmaker.workspace.validate_projected_context', side_effect=AssertionError('private replay')):
        inventory = project_service_inventory(workspace, graph, source_coverage=coverage)
    assert not any(d.get('code') == 'UNKNOWN_CONTEXT_ROLE' and d.get('context_id') == historical['id'] for d in inventory.diagnostics)
    assert (workspace, graph.to_dict(), coverage) == before


def test_prefix_and_mode_alone_do_not_exempt_genuine_foreign_source_paths(mixed_snapshot):
    workspace, graph, coverage = mixed_snapshot
    claim = next(c for c in graph.contexts if c.get('origin_trust') == 'WORKSPACE_DECLARATION')
    claim.pop('origin_trust'); claim.pop('kafka_binding_version')
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with pytest.raises(ServiceInventoryError) as error:
        project_service_inventory(workspace, graph, source_coverage=coverage)
    assert error.value.diagnostic['code'] == 'INVALID_OWNERSHIP'
    assert (workspace, graph.to_dict(), coverage) == before


def test_config_only_derived_declarations_never_become_compiler_or_code_proof(kafka_workspace):
    _, manifest, _ = kafka_workspace
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('projection process')):
        inventory = project_service_inventory(workspace, graph, source_coverage=coverage)
    assert not any(n.kind in {'kafka_code_listener', 'kafka_code_producer'} for n in graph.nodes)
    rows = [row for service in inventory.context_selection['services'].values() for row in service['contexts']]
    assert all(row['status'] != 'CURRENT' for row in rows)
    assert all(n.metadata['code_binding'] == 'UNPROVEN' for n in graph.nodes if n.kind == 'kafka_binding')
    assert (workspace, graph.to_dict(), coverage) == before

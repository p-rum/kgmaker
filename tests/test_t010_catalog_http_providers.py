"""T010 public projection over real workspace/source snapshots, without running apps."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.scanner import scan_repository
from kgmaker.workspace import load_workspace, snapshot_workspace


def projection(*args, **kwargs):
    try:
        function = importlib.import_module('kgmaker.interfaces').project_http_providers
    except (ImportError, AttributeError):
        pytest.fail('T010 project_http_providers public API is not implemented')
    return function(*args, **kwargs)


def workspace_inputs(tmp_path):
    for repo in ['alpha', 'beta']:
        root = tmp_path / repo
        (root / 'src/main/kotlin').mkdir(parents=True)
        (root / 'src/main/kotlin/Routes.kt').write_text('fun routes() { post("/orders") { } }\n')
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
    java = tmp_path / 'alpha/src/main/java'
    java.mkdir()
    (java / 'Orders.java').write_text('''
import org.springframework.web.bind.annotation.*;
@RequestMapping("/Api")
class Orders {
  @PostMapping("/Orders")
  public void upper() { }
  @PostMapping(path="/orders", params="v=1")
  public void first() { }
  @PostMapping(path="/orders", params="v=2")
  public void second() { }
}
''')
    (java / 'Dynamic.java').write_text('''
import org.springframework.web.bind.annotation.*;
@RequestMapping("${api.prefix}")
class Dynamic {
  @PostMapping("/pending")
  public void pending() { }
}
''')
    contract = tmp_path / 'alpha/src/main/resources'
    contract.mkdir()
    (contract / 'openapi.json').write_text(json.dumps({'openapi': '3.0.3', 'paths': {
        '/unimplemented': {'post': {'operationId': 'declaredOnly'}}}}))
    tests = tmp_path / 'alpha/src/test/kotlin'
    tests.mkdir(parents=True)
    (tests / 'RoutesTest.kt').write_text('fun testRoutes() { post("/test-only") { } }\n')
    manifest = tmp_path / 'workspace.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'workspace_id': 'http-fixture',
        'repositories': [{'id': name, 'role': 'backend', 'path': name} for name in ['alpha', 'beta']],
        'services': [{'id': name, 'backend_repo': name, 'frontend_repos': [], 'test_repos': [],
                      'contract': {'repo_id': name, 'path': 'src/main/resources/openapi.json'}}
                     for name in ['alpha', 'beta']],
        'service_ownership': {'schema_version': 1, 'services': [
            {'id': name, 'roots': [{'repo_id': name, 'path': 'src'}], 'modules': [], 'external_systems': []}
            for name in ['alpha', 'beta']]}}))
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    return load_workspace(manifest), graph, coverage


def interface_nodes(document):
    return [node for node in document.nodes if node.kind == 'http_interface']


def test_raw_registration_metadata_preserves_case_and_variants_before_projection(tmp_path):
    source = tmp_path / 'src/main/resources'
    source.mkdir(parents=True)
    (source / 'openapi.json').write_text(json.dumps({'openapi': '3.0.3', 'paths': {
        '/Orders': {'post': {}}, '/orders': {'post': {}}}}))
    graph = scan_repository(tmp_path)
    legacy = [node for node in graph.nodes if node.kind == 'api_endpoint']
    assert len(legacy) == 1  # Legacy identity is intentionally unchanged.
    registrations = (legacy[0].metadata or {}).get('http_registrations', [])
    assert {record['original_route'] for record in registrations} == {'/Orders', '/orders'}
    assert all(record['source_sha256'] == graph.files[record['source_path']] for record in registrations)


def test_ac01_same_post_route_in_two_real_services_stays_separate(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    document = projection(workspace, graph, source_coverage=coverage)
    nodes = [node for node in interface_nodes(document) if node.attributes['normalized_route'] == '/orders']
    assert {node.owner_id for node in nodes} == {'service:alpha', 'service:beta'}
    assert len({node.id for node in nodes}) == 2
    assert all(node.attributes['http_method'] == 'POST' for node in nodes)
    assert document.kind == 'interfaces' and document.coverage['status'] == 'PARTIAL'


def test_case_and_registration_variants_keep_original_identity(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    document = projection(workspace, graph, source_coverage=coverage)
    nodes = interface_nodes(document)
    upper = [node for node in nodes if node.attributes['normalized_route'] == '/Api/Orders']
    lower = [node for node in nodes if node.attributes['normalized_route'] == '/Api/orders']
    assert len(upper) == 1 and len(lower) == 2
    assert len({node.attributes['logical_id'] for node in lower}) == 1
    assert upper[0].attributes['logical_id'] != lower[0].attributes['logical_id']
    assert len({node.id for node in lower}) == 2
    assert all(node.original_ids and node.evidence_refs for node in upper + lower)


def test_ac02_openapi_contract_only_never_becomes_implemented(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    document = projection(workspace, graph, source_coverage=coverage)
    node = next(node for node in interface_nodes(document) if node.attributes['normalized_route'] == '/unimplemented')
    assert node.attributes['implementation_status'] == 'CONTRACT_ONLY'
    assert node.attributes['handler_ids'] == []
    assert node.attributes['deployment_status'] == 'UNKNOWN'
    assert 'RUNTIME_OBSERVED' not in node.evidence_kinds
    assert node.attributes['contract_fingerprint']


def test_ac03_dynamic_class_prefix_remains_unknown_without_fake_url(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    document = projection(workspace, graph, source_coverage=coverage)
    node = next(node for node in interface_nodes(document) if '${api.prefix}' in str(node.attributes.get('original_route')))
    assert node.attributes['normalized_route'] is None
    assert node.resolution_status == 'UNRESOLVED'
    assert 'DYNAMIC_ROUTE' in node.attributes['unresolved_reasons']
    assert any(item.get('code') == 'DYNAMIC_ROUTE' for item in document.diagnostics)


def test_ac04_05_pure_projection_preserves_inputs_and_excludes_test_routes(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    files_before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob('*')
                    if path.is_file() and '.git' not in path.parts}
    with patch('subprocess.Popen', side_effect=AssertionError('projection process')),\
         patch('socket.socket', side_effect=AssertionError('projection network')):
        document = projection(workspace, graph, source_coverage=coverage)
    assert before == (workspace, graph.to_dict(), coverage)
    assert files_before == {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob('*')
                            if path.is_file() and '.git' not in path.parts}
    assert all(node.attributes['normalized_route'] != '/test-only' for node in interface_nodes(document))
    assert all('FRAMEWORK_DERIVED' not in node.evidence_kinds and 'SYMBOL_RESOLVED' not in node.evidence_kinds
               for node in interface_nodes(document))


@pytest.mark.parametrize('field,value', [
    ('version', []), ('provider', []), ('http_method', []), ('source_path', []),
    ('source_sha256', '0' * 64), ('source_line', 0), ('variant_fingerprint', 'z' * 64),
    ('normalized_route', '/invented'),
])
def test_invalid_registration_is_structured_and_preserves_all_inputs(tmp_path, field, value):
    from dataclasses import replace
    from kgmaker.interfaces import InterfaceProjectionError
    workspace, graph, coverage = workspace_inputs(tmp_path)
    index = next(i for i, node in enumerate(graph.nodes) if node.kind == 'api_endpoint'
                 and any(record.get('provider') == 'ktor-source'
                         for record in (node.metadata or {}).get('http_registrations', [])))
    metadata = deepcopy(graph.nodes[index].metadata)
    metadata['http_registrations'][0][field] = value
    graph.nodes[index] = replace(graph.nodes[index], metadata=metadata)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with pytest.raises(InterfaceProjectionError):
        projection(workspace, graph, source_coverage=coverage)
    assert before == (workspace, graph.to_dict(), coverage)


def test_source_metadata_omits_uri_query_credentials_and_preserves_opaque_variants(tmp_path):
    source = tmp_path / 'src/main/resources'
    source.mkdir(parents=True)
    (source / 'openapi.json').write_text(json.dumps({'openapi': '3.0.3', 'paths': {
        '/orders?token=first-secret': {'post': {}}, '/orders?token=second-secret': {'post': {}},
        '/https://user:third-secret@example.test/orders': {'post': {}}}}))
    graph = scan_repository(tmp_path)
    records = [record for node in graph.nodes if node.kind == 'api_endpoint'
               for record in (node.metadata or {}).get('http_registrations', [])]
    serialized = json.dumps(records)
    assert 'first-secret' not in serialized and 'second-secret' not in serialized and 'third-secret' not in serialized
    assert len(records) == 3
    assert len({record['variant_fingerprint'] for record in records}) == 3
    assert all(record['normalized_route'] is None for record in records)


def test_unrelated_source_edit_preserves_logical_and_registration_identity(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    first = projection(workspace, graph, source_coverage=coverage)
    original = {node.attributes['source_path']: (node.id, node.attributes['logical_id'])
                for node in interface_nodes(first) if node.attributes['normalized_route'] is None}
    (tmp_path / 'alpha/src/main/kotlin/Unrelated.kt').write_text('class Unrelated\n')
    _, next_coverage, _, next_graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    second = projection(workspace, next_graph, source_coverage=next_coverage)
    current = {node.attributes['source_path']: (node.id, node.attributes['logical_id'])
               for node in interface_nodes(second) if node.attributes['normalized_route'] is None}
    assert original == current
    assert first.baseline_fingerprint != second.baseline_fingerprint


def test_two_services_in_same_repository_do_not_share_global_endpoint_identity(tmp_path):
    root = tmp_path / 'shared'
    for name in ['orders', 'billing']:
        source = root / 'src/main' / name
        source.mkdir(parents=True)
        (source / 'Routes.kt').write_text('fun routes() { post("/orders") { } }\n')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    manifest = tmp_path / 'workspace.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'workspace_id': 'one-repo',
        'repositories': [{'id': 'shared', 'role': 'backend', 'path': 'shared'}],
        'services': [{'id': name, 'backend_repo': 'shared', 'frontend_repos': [], 'test_repos': [],
                      'contract': {'repo_id': 'shared', 'path': 'api.json'}} for name in ['orders', 'billing']],
        'service_ownership': {'schema_version': 1, 'services': [
            {'id': name, 'roots': [{'repo_id': 'shared', 'path': 'src/main/' + name}],
             'modules': [], 'external_systems': []} for name in ['orders', 'billing']]}}))
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    assert len([node for node in graph.nodes if node.kind == 'api_endpoint']) == 1
    document = projection(load_workspace(manifest), graph, source_coverage=coverage)
    nodes = interface_nodes(document)
    assert len(nodes) == 2
    assert {node.owner_id for node in nodes} == {'service:orders', 'service:billing'}
    assert len({node.attributes['logical_id'] for node in nodes}) == 2


def test_contract_revisions_stay_separate_without_automatic_handler_binding(tmp_path):
    workspace, _, _ = workspace_inputs(tmp_path)
    second = tmp_path / 'alpha/src/main/resources/openapi-v2.json'
    second.write_text(json.dumps({'openapi': '3.0.3', 'paths': {'/unimplemented': {'post': {
        'operationId': 'secondContract', 'description': 'Second contract revision'}}}}))
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    nodes = [node for node in interface_nodes(projection(workspace, graph, source_coverage=coverage))
             if node.attributes['normalized_route'] == '/unimplemented']
    assert len(nodes) == 2 and len({node.id for node in nodes}) == 2
    assert len({node.attributes['logical_id'] for node in nodes}) == 1
    assert len({node.attributes['contract_fingerprint'] for node in nodes}) == 2
    assert all(node.attributes['implementation_status'] == 'CONTRACT_ONLY' and not node.attributes['handler_ids']
               for node in nodes)


def test_missing_explicit_ownership_never_infers_service_from_route_or_repository(tmp_path):
    workspace, _, _ = workspace_inputs(tmp_path)
    manifest = Path(workspace['_manifest_path'])
    data = json.loads(manifest.read_text()); data.pop('service_ownership')
    manifest.write_text(json.dumps(data))
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    document = projection(load_workspace(manifest), graph, source_coverage=coverage)
    assert interface_nodes(document)
    assert all(node.owner_id is None and node.resolution_status == 'UNRESOLVED' for node in interface_nodes(document))
    assert any(item.get('code') == 'HTTP_SERVICE_OWNERSHIP_UNKNOWN' for item in document.diagnostics)


def test_explicit_test_scope_does_not_import_production_interfaces(tmp_path):
    workspace, graph, coverage = workspace_inputs(tmp_path)
    document = projection(workspace, graph, source_coverage=coverage, scope='test')
    assert {node.attributes['normalized_route'] for node in interface_nodes(document)} == {'/test-only'}
    assert document.scope == 'test'
    assert all(node.attributes['scope'] == 'test' for node in interface_nodes(document))


def test_legacy_merged_node_without_registration_record_does_not_invent_route_case(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage = workspace_inputs(tmp_path)
    for index, node in enumerate(graph.nodes):
        if node.kind == 'api_endpoint' and node.path.startswith('@alpha/') and node.name == 'POST /orders':
            graph.nodes[index] = replace(node, metadata=None)
    document = projection(workspace, graph, source_coverage=coverage)
    assert any(item.get('code') == 'LEGACY_HTTP_REGISTRATION_UNKNOWN' for item in document.diagnostics)
    assert not any(node.owner_id == 'service:alpha' and node.attributes['normalized_route'] == '/orders'
                   for node in interface_nodes(document))


def test_http_consumer_edges_are_not_catalogued_as_providers(tmp_path):
    import shutil
    workspace, _, _ = workspace_inputs(tmp_path)
    for repo in ['alpha', 'beta']:
        shutil.rmtree(tmp_path / repo / 'src')
        root = tmp_path / repo / 'src/main'
        root.mkdir(parents=True)
        (root / 'client.ts').write_text("export function request() { return fetch('/consumed', {method: 'POST'}); }")
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    assert any(edge.kind == 'calls_endpoint' for edge in graph.edges)
    document = projection(workspace, graph, source_coverage=coverage)
    assert not interface_nodes(document)
    assert document.coverage['status'] == 'UNKNOWN'


def test_foreign_context_is_excluded_without_promoting_source_evidence(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage = workspace_inputs(tmp_path)
    graph.edges = [replace(edge, context_ids=('foreign-context',))
                   if edge.kind == 'declares_endpoint' else edge for edge in graph.edges]
    before = deepcopy(graph.to_dict())
    from kgmaker.views import ServiceInventoryError
    with pytest.raises(ServiceInventoryError) as error:
        projection(workspace, graph, source_coverage=coverage)
    assert error.value.diagnostic['code'] == 'INVALID_SNAPSHOT'
    assert graph.to_dict() == before


def test_runtime_named_metadata_and_unbound_edge_cannot_claim_observed_registration(tmp_path):
    # Deliberately invalid model data, NOT a real application execution/import proof.
    from dataclasses import replace
    from kgmaker.model import Edge
    workspace, graph, coverage = workspace_inputs(tmp_path)
    declaration = next(edge for edge in graph.edges if edge.kind == 'declares_endpoint')
    graph.nodes = [replace(node, metadata={**(node.metadata or {}), 'kind': 'RUNTIME_OBSERVED'})
                   if node.id == declaration.target else node for node in graph.nodes]
    graph.edges.append(Edge(declaration.source, declaration.target, 'runtime_framework_observation',
        evidence_kind='RUNTIME_OBSERVED', context_ids=declaration.context_ids, evidence_ids=('absent-runtime-record',)))
    graph.evidence.append({'id': 'absent-runtime-record', 'kind': 'RUNTIME_OBSERVED',
                           'source': declaration.source, 'target': declaration.target})
    before = deepcopy(graph.to_dict())
    document = projection(workspace, graph, source_coverage=coverage)
    assert all(node.attributes['runtime_status'] == 'UNKNOWN' for node in interface_nodes(document))
    assert all('RUNTIME_OBSERVED' not in node.evidence_kinds for node in interface_nodes(document))
    boundary = [item for item in document.diagnostics if item.get('code') == 'HTTP_RUNTIME_BINDING_UNKNOWN']
    assert boundary and boundary[0]['original_evidence_ids'] == ['absent-runtime-record']
    assert graph.to_dict() == before


@pytest.mark.parametrize('relative', ['src/main/kotlin/Routes.kt', 'src/main/java/Orders.java',
                                      'src/main/resources/openapi.json', 'src/main/resources/openapi.yaml'])
def test_raw_source_hash_capture_supports_crlf_without_projection_io(tmp_path, relative):
    import hashlib
    workspace, _, _ = workspace_inputs(tmp_path)
    path = tmp_path / 'alpha' / relative
    if path.suffix == '.yaml':
        path.write_text('openapi: 3.0.3\npaths:\n  /yaml-route:\n    post:\n      operationId: yamlRoute\n')
    text = path.read_text().rstrip('\n') + '\n'
    path.write_bytes(text.replace('\n', '\r\n').encode())
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    records = [record for node in graph.nodes if node.kind == 'api_endpoint' and node.id.startswith('repo:alpha:')
               for record in (node.metadata or {}).get('http_registrations', []) if record['source_path'] == relative]
    assert records and all(record['source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest() for record in records)
    before = deepcopy(graph.to_dict())
    with patch('subprocess.Popen', side_effect=AssertionError('CRLF projection process')),\
         patch('socket.socket', side_effect=AssertionError('CRLF projection network')):
        document = projection(workspace, graph, source_coverage=coverage)
    assert any(node.attributes['source_path'] == '@alpha/' + relative for node in interface_nodes(document))
    assert graph.to_dict() == before


def test_newline_only_scan_race_rejects_mixed_snapshot_and_preserves_saved_graph(tmp_path):
    from kgmaker.analysis_model import AnalysisError
    from kgmaker.scanner import _safe_source, _safe_text
    from kgmaker.store import save_graph
    path = tmp_path / 'src/main/kotlin/Routes.kt'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'fun routes() { post("/orders") { } }\n')
    save_graph(scan_repository(tmp_path), tmp_path)
    saved = (tmp_path / '.kgmaker/graph.json').read_bytes()
    old_text = _safe_text(path)
    changed = False
    def changing(source):
        nonlocal changed
        capture = _safe_source(source)
        if source == path and not changed:
            source.write_bytes(source.read_bytes().replace(b'\n', b'\r\n'))
            changed = True
        return capture
    with patch('kgmaker.scanner._safe_source', side_effect=changing):
        with pytest.raises(AnalysisError, match='snapshot changed'):
            scan_repository(tmp_path)
    assert changed and _safe_text(path) == old_text
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == saved


def test_http_capture_version_invalidates_existing_workspace_cache_without_changing_ids(tmp_path, monkeypatch):
    from kgmaker import domain, feature, workspace as workspace_module
    workspace, _, _ = workspace_inputs(tmp_path)
    manifest = Path(workspace['_manifest_path'])
    cache = tmp_path / 'coordinator'
    monkeypatch.setattr(workspace_module, '_REPO_CACHE', {})
    with patch.object(domain, 'HTTP_CAPTURE_VERSION', 'legacy-normalized-http-capture'):
        _, old_coverage, _, old_graph, _ = snapshot_workspace(manifest, cache_root=cache, persist_cache=True)
    assert list((cache / '.kgmaker/workspace-cache').glob('*.json'))
    monkeypatch.setattr(workspace_module, '_REPO_CACHE', {})
    with patch.object(feature, 'current_graph', wraps=feature.current_graph) as rebuild:
        _, coverage, _, graph, _ = snapshot_workspace(manifest, cache_root=cache)
    assert rebuild.call_count == 2  # both actual repository snapshots need the new capture contract
    old_ids = {node.id for node in interface_nodes(projection(workspace, old_graph, source_coverage=old_coverage))}
    current_ids = {node.id for node in interface_nodes(projection(workspace, graph, source_coverage=coverage))}
    assert current_ids == old_ids

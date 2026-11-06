"""Real contract declarations retain every colliding normalized route."""
from copy import deepcopy
import json

import pytest

from kgmaker.interfaces import project_http_providers
from kgmaker.workspace import load_workspace, snapshot_workspace
from test_t010_catalog_http_providers import workspace_inputs


def snapshot(tmp_path, *, yaml=False, two_services=False):
    workspace_inputs(tmp_path)
    document = {'openapi': '3.0.3', 'paths': {
        '/orders/{id}': {'post': {'operationId': 'byId'}, 'get': {'operationId': 'getOrder'}},
        '/orders/{name}': {'post': {'operationId': 'byName'}},
        '/health': {'get': {'operationId': 'health'}}}}
    name = 'openapi.yaml' if yaml else 'openapi.json'
    repos = ['alpha', 'beta'] if two_services else ['alpha']
    for repo in repos:
        root = tmp_path / repo / 'src/main/resources'
        root.mkdir(parents=True, exist_ok=True)
        if yaml:
            (root / 'openapi.json').unlink(missing_ok=True)
            text = 'openapi: 3.0.3\npaths:\n  /orders/{id}:\n    post:\n      operationId: byId\n  /orders/{name}:\n    post:\n      operationId: byName\n'
        else:
            text = json.dumps(document)
        (root / name).write_text(text)
    manifest = tmp_path / 'workspace.json'
    config = json.loads(manifest.read_text())
    for service in config['services']:
        if service['id'] in repos:
            service['contract']['path'] = 'src/main/resources/' + name
    manifest.write_text(json.dumps(config))
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    return load_workspace(manifest), graph, coverage


def colliding_nodes(view):
    return [n for n in view.nodes if n.kind == 'http_interface'
            and n.attributes['normalized_route'] == '/orders/{param}'
            and n.attributes['http_method'] == 'POST']


@pytest.mark.parametrize('two_services', [False, True])
def test_actual_json_collision_is_one_explicit_boundary_per_service(tmp_path, two_services):
    workspace, graph, coverage = snapshot(tmp_path, two_services=two_services)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    view = project_http_providers(workspace, graph, source_coverage=coverage)
    collisions = colliding_nodes(view)
    assert len(collisions) == (2 if two_services else 1)
    assert len({n.id for n in view.nodes}) == len(view.nodes)
    for node in collisions:
        assert node.resolution_status == 'AMBIGUOUS'
        assert node.attributes['original_route'] is None
        assert node.attributes['original_routes'] == ['/orders/{id}', '/orders/{name}']
        candidates = node.attributes['registration_candidates']
        assert {c['attributes']['original_route'] for c in candidates} == {'/orders/{id}', '/orders/{name}'}
        assert len(candidates) == 2 and len(node.evidence_refs) == 2
        assert node.attributes['implementation_status'] == 'CONTRACT_ONLY'
        assert node.attributes['runtime_status'] == node.attributes['deployment_status'] == 'UNKNOWN'
        assert any(d['code'] == 'HTTP_NORMALIZED_ROUTE_AMBIGUOUS' and d['interface_id'] == node.id
                   for d in view.diagnostics)
        edges = [e for e in view.edges if e.target == node.id and e.relation == 'declares_http_interface']
        assert len(edges) == 1 and set(edges[0].evidence_refs) == set(node.evidence_refs)
        assert edges[0].resolution_status == 'AMBIGUOUS'
    assert any(n.kind == 'http_interface' and n.attributes['normalized_route'] == '/health' for n in view.nodes)
    assert any(n.kind == 'http_interface' and n.attributes['http_method'] == 'GET'
               and n.attributes['normalized_route'] == '/orders/{param}' for n in view.nodes)
    assert (workspace, graph.to_dict(), coverage) == before


def test_order_and_identical_duplicate_records_do_not_change_boundary_or_siblings(tmp_path):
    workspace, graph, coverage = snapshot(tmp_path)
    first = project_http_providers(workspace, graph, source_coverage=coverage)
    for node in graph.nodes:
        records = (node.metadata or {}).get('http_registrations')
        if records:
            records.reverse()
            records.append(deepcopy(records[0]))
    graph.edges.reverse()
    second = project_http_providers(workspace, graph, source_coverage=coverage)
    assert {n.id: n.to_dict() for n in first.nodes} == {n.id: n.to_dict() for n in second.nodes}
    assert {e.id: e.to_dict() for e in first.edges} == {e.id: e.to_dict() for e in second.edges}


def test_yaml_distinct_source_locators_keep_their_existing_variants(tmp_path):
    workspace, graph, coverage = snapshot(tmp_path, yaml=True)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    view = project_http_providers(workspace, graph, source_coverage=coverage)
    variants = colliding_nodes(view)
    assert len(variants) == 2 and len({n.id for n in variants}) == 2
    assert {n.attributes['original_route'] for n in variants} == {'/orders/{id}', '/orders/{name}'}
    assert all(n.attributes['implementation_status'] == 'CONTRACT_ONLY' and n.resolution_status == 'UNRESOLVED'
               for n in variants)
    assert (workspace, graph.to_dict(), coverage) == before

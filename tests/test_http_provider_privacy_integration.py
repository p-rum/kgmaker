"""Actual public source capture and provider projection privacy composition."""
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from kgmaker.workspace import snapshot_workspace, split_id
from test_t010_catalog_http_providers import workspace_inputs, projection, interface_nodes


@pytest.mark.parametrize('route,private,unsupported', [
    ('/orders#fragment-private', 'fragment-private', False),
    ('https://fixture-user:credential-private@example.invalid/orders', 'credential-private', True),
    ('/orders?query-private=1', 'query-private', False),
])
def test_provider_legacy_identity_never_persists_sensitive_uri_components(tmp_path, route, private, unsupported):
    workspace, _, _ = workspace_inputs(tmp_path)
    source = tmp_path / 'alpha/src/main/java/Privacy.java'
    source.write_text('import org.springframework.web.bind.annotation.GetMapping;\n'
                      'class Privacy { @GetMapping("' + route + '") void endpoint() {} }\n')
    before = source.read_bytes()
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    captured = [node for node in graph.nodes if node.kind == 'api_endpoint'
                and node.path and node.path.endswith('/Privacy.java')]
    assert len(captured) == 1
    assert captured[0].name == 'GET UNKNOWN'
    assert ':unresolved:' in split_id(captured[0].id)[1]
    assert private not in json.dumps(asdict(graph))
    document = projection(workspace, graph, source_coverage=coverage)
    nodes = [node for node in interface_nodes(document)
             if node.attributes.get('source_path', '').endswith('/Privacy.java')]
    if unsupported:
        assert nodes == []
        assert any(item['code'] == 'HTTP_UNSUPPORTED_ROUTE'
                   and item.get('source_path', '').endswith('/Privacy.java')
                   for item in document.diagnostics)
    else:
        assert len(nodes) == 1
        assert nodes[0].attributes['normalized_route'] is None
        assert nodes[0].resolution_status == 'UNRESOLVED'
    assert private not in document.to_json()
    assert source.read_bytes() == before


def test_ordinary_provider_route_preserves_legacy_id_and_case(tmp_path):
    workspace, _, _ = workspace_inputs(tmp_path)
    source = tmp_path / 'alpha/src/main/java/Privacy.java'
    source.write_text('import org.springframework.web.bind.annotation.GetMapping;\n'
                      'class Privacy { @GetMapping("/Ordinary") void endpoint() {} }\n')
    _, coverage, _, graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    captured = [node for node in graph.nodes if node.kind == 'api_endpoint'
                and node.path and node.path.endswith('/Privacy.java')]
    assert len(captured) == 1
    assert split_id(captured[0].id)[1] == 'api_endpoint:GET:/ordinary'
    assert captured[0].name == 'GET /Ordinary'
    document = projection(workspace, graph, source_coverage=coverage)
    nodes = [node for node in interface_nodes(document)
             if node.attributes.get('source_path', '').endswith('/Privacy.java')]
    assert len(nodes) == 1
    assert nodes[0].attributes['normalized_route'] == '/Ordinary'

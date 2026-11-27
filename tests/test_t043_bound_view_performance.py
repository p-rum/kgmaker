"""Deterministic scope and gate checks. Measurements run separately."""

from hashlib import sha256
import json

import pytest

from benchmarks.t043_view_performance import (
    BINDINGS,
    CFG_BRANCHES,
    SERVICES,
    compare_samples,
    cyclic_cfg_fixture,
    cyclic_cfg_report,
    topology_fixture,
    topology_report,
)
from kgmaker import flow
from kgmaker.analysis_model import AnalysisError, digest
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.topology_filter import TopologyFilterError
from test_unified_flow_views import model_graph, nested_process_graph


def test_t043_scale_preserves_all_binding_ids_within_node_and_hop_limits():
    topology = topology_fixture()
    before = topology.content_fingerprint
    assert len(topology.nodes) == SERVICES
    expected_bindings = {f'binding:{index:05d}' for index in range(BINDINGS)}
    assert len(topology.edges) == BINDINGS
    assert {edge.original_ids[0] for edge in topology.edges} == expected_bindings

    filtered = topology_report(topology)
    view, boundaries = filtered['document'], filtered['filtering']
    retained = {node['id'] for node in view['nodes']}
    assert retained == {f'service:{index:03d}' for index in range(5)}
    retained_bindings = {identity for edge in view['edges'] for identity in edge['original_ids']}
    omitted_bindings = set(boundaries['omitted_original_ids'])
    assert len(view['edges']) == len(retained_bindings) == 24
    assert retained_bindings.isdisjoint(omitted_bindings)
    assert retained_bindings | omitted_bindings == expected_bindings
    assert all(edge['source'] in retained and edge['target'] in retained for edge in view['edges'])
    assert all(edge['resolution_status'] == 'AMBIGUOUS' and edge['evidence_kinds'] == ['SOURCE_ONLY']
               and edge['attributes']['context_ids'] == ['context:main'] for edge in view['edges'])
    assert view['scope'] == 'production' and view['coverage']['status'] == 'PARTIAL'
    assert boundaries['truncated'] and boundaries['omission_inventory_complete']
    assert len(boundaries['frontier']) == 952
    omitted_edges = set(boundaries['omitted_edge_ids'])
    assert all(row['anchor_id'] in retained and row['reason'] == 'NODE_LIMIT'
               and set(row['omitted_edge_ids']) <= omitted_edges
               for row in boundaries['frontier'])

    root_only = topology_report(topology, max_hops=0)
    assert [node['id'] for node in root_only['document']['nodes']] == ['service:000']
    assert root_only['document']['edges'] == []
    assert {row['reason'] for row in root_only['filtering']['frontier']} == {'HOP_LIMIT'}
    with pytest.raises(TopologyFilterError, match='FILTER_INVALID_NODE_BUDGET'):
        topology_report(topology, max_nodes=0)
    assert topology.content_fingerprint == before


def test_t043_large_cyclic_root_has_a_single_explicit_boundary():
    graph = cyclic_cfg_fixture()
    before = digest(graph.to_dict())
    cfg = graph.cfgs[0]
    assert len(cfg['blocks']) == CFG_BRANCHES + 3
    assert sum(bool(edge.get('loop_back')) for edge in cfg['edges']) == CFG_BRANCHES
    result = cyclic_cfg_report(graph)
    block, = result['cfg']['blocks']
    assert block['kind'] == 'unresolved_boundary'
    assert block['original_ids'] == ['entry', 'error', 'exit', 'method']
    assert result['cfg']['edges'] == []
    assert result['truncated'] and result['status'] == 'PARTIAL'
    assert {gap['code'] for gap in result['coverage']['gaps']} == {'NODE_LIMIT', 'UNRESOLVED_BOUNDARY'}
    assert result['provenance']['evidence_ids'] == ['cfg-proof']
    assert result['execution'] == 'NOT_OBSERVED' and result['availability'] == 'UNKNOWN'
    assert digest(graph.to_dict()) == before


def test_t043_process_depth_stops_at_the_exact_nested_call():
    graph = nested_process_graph()
    before = digest(graph.to_dict())
    report = flow.build_report(graph, 'method', view='process', max_depth=1)
    assert [edge['call_site'] for edge in report['cfg']['edges'] if edge['kind'] == 'call'] == ['site']
    assert {'call_site': 'nested-site', 'target': 'leaf', 'reason': 'depth limit'} in report['boundaries']
    assert report['truncated'] and report['status'] == 'PARTIAL'
    assert all(block['context_ids'] == ['ctx'] for block in report['cfg']['blocks'])
    assert report['execution'] == 'NOT_OBSERVED' and report['availability'] == 'UNKNOWN'
    with pytest.raises(AnalysisError, match='Invalid traversal limits'):
        flow.build_report(graph, 'method', view='process', max_depth=-1)
    assert digest(graph.to_dict()) == before


def test_t043_relative_gate_rejects_regressions_and_changed_fixtures():
    sample = {'case': 'topology', 'parameters': {'nodes': 100}, 'fixture_sha256': 'fixture',
              'output_sha256': 'output', 'output_bytes': 12, 'cold_ns': 100,
              'warm_ns': 200, 'peak_python_bytes': 1000}
    at_limit = {**sample, 'cold_ns': 125, 'warm_ns': 250, 'peak_python_bytes': 1250}
    assert not compare_samples([sample], [at_limit])['over_25_percent']
    over_limit = {**at_limit, 'cold_ns': 126, 'warm_ns': 251, 'peak_python_bytes': 1251}
    assert compare_samples([sample], [over_limit])['over_25_percent'] == [
        'cold_ns', 'warm_ns', 'peak_python_bytes',
    ]
    for field in ('fixture_sha256', 'output_sha256'):
        with pytest.raises(ValueError, match='mismatched fixture or output identities'):
            compare_samples([sample], [{**sample, field: 'different'}])


def source_diagnostics(count):
    return [{'code': 'SYNTHETIC_CFG_DIAGNOSTIC', 'reason': f'opaque source span {i:04d}'}
            for i in range(count)]


def test_t043_bounds_source_diagnostics_before_mirroring_coverage():
    graph = cyclic_cfg_fixture()
    diagnostics = source_diagnostics(1024)
    diagnostics[-1] = {'code': 'STALE_EVIDENCE', 'reason': 'source evidence no longer matches'}
    graph.cfgs[0]['diagnostics'] = diagnostics
    before = digest(graph.to_dict())

    report = cyclic_cfg_report(graph)
    assert report['diagnostics'] == report['cfg']['diagnostics'] == diagnostics[:256]
    gaps = report['coverage']['gaps']
    assert len(gaps) == 259
    summary, = [gap for gap in gaps if gap['code'] == 'FLOW_DIAGNOSTIC_LIMIT']
    assert summary['max_diagnostics'] == 256
    assert summary['omitted_diagnostics'] == summary['omitted_cfg_diagnostics'] == 768
    assert summary['omitted_unknown_codes'] == ['STALE_EVIDENCE']
    assert report['status'] == report['coverage']['status'] == 'UNKNOWN'
    assert report['scope'] == 'production' and report['provenance']['evidence_ids'] == ['cfg-proof']
    assert report['ordering']['display_order'] == [report['cfg']['blocks'][0]['id']]
    assert report['cfg']['blocks'][0]['original_ids'] == ['entry', 'error', 'exit', 'method']
    assert digest(graph.to_dict()) == before

    serialized = json.loads(flow.render(report, 'json'))
    assert serialized == report
    assert 'FLOW_DIAGNOSTIC_LIMIT' in flow.render(report, 'markdown')
    assert 'FLOW_DIAGNOSTIC_LIMIT' in flow.render(report, 'mermaid')


def test_t043_diagnostic_overflow_does_not_report_node_truncation():
    graph = model_graph()
    graph.cfgs[0]['diagnostics'] = source_diagnostics(256)
    graph.cfgs[0]['diagnostics'][0]['code'] = 123
    compatible = flow.build_report(graph, 'method')
    assert compatible['diagnostics'] == graph.cfgs[0]['diagnostics']
    assert all(gap['code'] != 'FLOW_DIAGNOSTIC_LIMIT' for gap in compatible['coverage']['gaps'])
    assert json.loads(flow.render(compatible, 'json')) == compatible

    graph.cfgs[0]['diagnostics'].append({'code': 'SYNTHETIC_CFG_DIAGNOSTIC', 'reason': 'overflow'})
    report = flow.build_report(graph, 'method')
    assert report['truncated'] is False
    assert 'FLOW_DIAGNOSTIC_LIMIT' in {gap['code'] for gap in report['coverage']['gaps']}
    assert 'NODE_LIMIT' not in {gap['code'] for gap in report['coverage']['gaps']}
    assert json.loads(flow.render(report, 'json')) == report


def test_t043_caps_process_diagnostics_without_changing_call_provenance():
    graph = nested_process_graph()
    expected = flow.build_report(graph, 'method', view='process', max_depth=1)
    diagnostics = source_diagnostics(257)
    root = next(cfg for cfg in graph.cfgs if cfg['method'] == 'method')
    root['diagnostics'] = diagnostics
    before = digest(graph.to_dict())

    report = flow.build_report(graph, 'method', view='process', max_depth=1)
    assert report['diagnostics'] == diagnostics[:256]
    assert 'diagnostics' not in report['cfg']
    summary, = [gap for gap in report['coverage']['gaps'] if gap['code'] == 'FLOW_DIAGNOSTIC_LIMIT']
    assert summary['omitted_diagnostics'] == 1 and summary['omitted_cfg_diagnostics'] == 0
    for key in ('cfg', 'ordering', 'boundaries', 'provenance', 'scope', 'status'):
        assert report[key] == expected[key]
    assert digest(graph.to_dict()) == before


def test_t043_render_caps_already_mirrored_legacy_source_diagnostics():
    legacy = flow.build_report(model_graph(), 'method')
    diagnostics = source_diagnostics(480)
    legacy['diagnostics'] = diagnostics
    legacy['cfg']['diagnostics'] = diagnostics
    original_gaps = list(legacy['coverage']['gaps'])
    legacy['coverage']['gaps'] += [{**item, 'diagnostic': item} for item in diagnostics]
    legacy_authority = {'code': 'EVIDENCE_FRESHNESS_UNKNOWN', 'reason': 'unavailable source'}
    legacy['coverage']['gaps'].append({**legacy_authority, 'diagnostic': legacy_authority})
    before = digest(legacy)
    report = json.loads(flow.render(legacy, 'json'))
    assert report['diagnostics'] == report['cfg']['diagnostics'] == diagnostics[:256]
    assert all(gap in report['coverage']['gaps'] for gap in original_gaps)
    assert len(report['coverage']['gaps']) == len(original_gaps) + 256 + 1
    assert report['status'] == 'UNKNOWN'
    summary, = [gap for gap in report['coverage']['gaps'] if gap['code'] == 'FLOW_DIAGNOSTIC_LIMIT']
    assert summary['omitted_unknown_codes'] == ['EVIDENCE_FRESHNESS_UNKNOWN']
    assert digest(legacy) == before


def test_t043_overflow_cannot_hide_malformed_diagnostics(tmp_path):
    report = flow.build_report(model_graph(), 'method')
    report['diagnostics'] = [*source_diagnostics(256), 'not a diagnostic']
    output = tmp_path / 'flow.json'
    output.write_bytes(b'previous report')
    before = digest(report)
    with pytest.raises(AnalysisError, match='Invalid flow source diagnostic'):
        flow.publish(report, 'json', output)
    assert output.read_bytes() == b'previous report'
    assert list(tmp_path.iterdir()) == [output]
    assert digest(report) == before


def test_t043_overflow_cannot_hide_nonfinite_legacy_coverage(tmp_path):
    report = flow.build_report(model_graph(), 'method')
    output = tmp_path / 'flow.json'
    previous = flow.publish(report, 'json', output).encode()
    report['diagnostics'] = source_diagnostics(257)
    report['coverage']['gaps'].append({
        'code': 'SOURCE_METRIC', 'reason': 'Invalid source metric',
        'diagnostic': {'sample': float('nan')},
    })
    before = json.dumps(report, sort_keys=True)

    with pytest.raises(ValueError, match='Out of range float values'):
        flow.publish(report, 'json', output)
    assert output.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [output]
    assert json.dumps(report, sort_keys=True) == before


_RELATION_256_SHA256 = {
    'integrations': (
        'e7d5476f5d6dfe3de0d73408b6d8455af4c4328c9082905d9c3d4d9d0e4663c4',
        'a45531791f45eb6225d7f50404adb6459754ac062aeb774ce3cfca64aa030cdf',
        '342f120addbaa5457f45ec36da7146b93755818db1a47dc39d78d3f51e1e569a',
    ),
    'data-flow': (
        'f3f689ff93a039e359791660d7afad3fc97242257367fddf442a6c33d0325c27',
        'fbca241648b208d464c46b095299cf6f54656aeaa295b380a277eb3c5924d1da',
        'efbb623c5c7abd5befe0d7ca99184139562ce92178a17f648bdb00db05c52546',
    ),
}


def relation_http_graph(count):
    source = 'src/main/java/Checkout.java'
    entry = Node('entry', 'method', 'checkout', source, scope='production')
    requests = [
        Node(f'http-{i:04d}', 'http_request_definition', f'request{i}', source, scope='production',
             metadata={'caller': 'entry', 'route_expression': f'/orders/{i}'})
        for i in range(count)
    ]
    foreign = Node('http-other-scope', 'http_request_definition', 'foreign', source, scope='test',
                   metadata={'caller': 'entry', 'route_expression': '/other'})
    return KnowledgeGraph(3, '.', 'schema-fixture', [entry, foreign, *reversed(requests)],
                          [Edge(entry.id, node.id, 'defines_http_request') for node in requests], {})


@pytest.mark.parametrize('view', ['integrations', 'data-flow'])
def test_t043_bounds_http_annex_in_all_relation_formats(view):
    formats = ('json', 'mermaid', 'markdown')
    at_limit = flow.build_report(relation_http_graph(256), 'entry', view=view, max_nodes=1)
    assert tuple(sha256(flow.render(at_limit, fmt).encode()).hexdigest() for fmt in formats) == _RELATION_256_SHA256[view]

    graph = relation_http_graph(258)
    original = digest(graph.to_dict())
    report = flow.build_report(graph, 'entry', view=view, max_nodes=1)
    assert report['nodes'] == ['entry'] and report['edges'] == [] and report['truncated']
    assert report['scope'] == 'production' and report['status'] == 'PARTIAL'
    assert report['execution'] == 'NOT_OBSERVED' and report['availability'] == 'UNKNOWN'
    assert report['http'] == at_limit['http']
    assert [row['id'] for row in report['http']['requests']] == [f'http-{i:04d}' for i in range(256)]
    gap, = [item for item in report['coverage']['gaps'] if item['code'] == 'FLOW_HTTP_ANNEX_LIMIT']
    assert gap['max_requests'] == 256 and gap['omitted_requests'] == 2
    assert gap['omitted_request_ids_sha256'] == sha256(b'["http-0256","http-0257"]').hexdigest()
    assert flow.finalize(report) == report
    for fmt in formats:
        text = flow.render(report, fmt)
        assert 'http-0256' not in text and 'http-other-scope' not in text
        if fmt == 'json':
            decoded = json.loads(text)
        else:
            metadata, = [line for line in text.splitlines() if line.startswith('  %% flow-meta ')]
            decoded = json.loads(metadata.removeprefix('  %% flow-meta '))
        assert decoded['http'] == at_limit['http'] and gap in decoded['coverage']['gaps']
    assert digest(graph.to_dict()) == original


def test_t043_http_annex_overflow_is_not_node_truncation():
    report = flow.build_report(relation_http_graph(257), 'entry', view='data-flow')
    assert len(report['nodes']) == 258 and report['truncated'] is False
    assert {gap['code'] for gap in report['coverage']['gaps']} == {'RELATIONSHIP_ONLY', 'FLOW_HTTP_ANNEX_LIMIT'}
    report['return_consumer_bindings'] = [{'id': f'binding:{i}'} for i in range(257)]
    assert flow.finalize(report)['return_consumer_bindings'] == report['return_consumer_bindings']


@pytest.mark.parametrize('format_name', ['json', 'mermaid', 'markdown'])
@pytest.mark.parametrize(('invalid_row', 'error', 'message'), [
    ('invalid HTTP request', AnalysisError, 'Invalid flow HTTP request'),
    ({'id': 'http-0256', 'route_expression': float('nan')}, ValueError, 'Out of range float values'),
])
def test_t043_http_annex_cannot_hide_invalid_omitted_rows(tmp_path, format_name, invalid_row, error, message):
    report = flow.build_report(relation_http_graph(256), 'entry', view='integrations', max_nodes=1)
    output = tmp_path / 'flow'
    previous = flow.publish(report, format_name, output).encode()
    report['http']['requests'].append(invalid_row)
    before = json.dumps(report, sort_keys=True)
    with pytest.raises(error, match=message):
        flow.publish(report, format_name, output)
    assert output.read_bytes() == previous and list(tmp_path.iterdir()) == [output]
    assert json.dumps(report, sort_keys=True) == before

"""Deterministic scope and gate checks. Measurements run separately."""

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

"""Deterministic scope and gate checks. Measurements run separately."""

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
from test_unified_flow_views import nested_process_graph


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

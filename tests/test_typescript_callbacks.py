"""Actual TypeScript higher-order/barrel/union proof; no emitted JS or runtime calls."""
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from kgmaker.inspection import inspect_frontend
from kgmaker.model import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


@pytest.fixture(scope='module')
def actual_graph(tmp_path_factory):
    if not shutil.which('node') or not (HOME / 'typescript/node_modules/typescript/lib/typescript.js').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Actual pinned TypeScript 5.7.3 worker required')
        pytest.skip('Actual pinned TypeScript worker unavailable')
    root = tmp_path_factory.mktemp('ts-callbacks')
    shutil.copytree(ROOT / 'fixtures/typescript-callbacks', root, dirs_exist_ok=True)
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = inspect_frontend(root, home=HOME, repo_id='callback-fixture', publish=False)
    assert before == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return root, result, KnowledgeGraph.from_dict(result['graph'])


def owned_sites(graph, owner):
    return [site for site in graph.call_sites if ':' + owner + ':' in site['caller']]


def test_generic_barrel_calls_keep_instantiated_signatures_and_exact_declarations(actual_graph):
    _, result, graph = actual_graph
    sites = owned_sites(graph, 'run')
    assert len(sites) == 1
    symbols = {s['id']: s for s in graph.symbols}
    target = symbols[sites[0]['declared_target']]
    assert target['name'] == 'mapValue' and target['path'] == 'src/api.ts'
    assert sites[0]['evidence_kind'] == 'SYMBOL_RESOLVED'
    assert 'number' in sites[0]['signature'] and 'string' in sites[0]['signature']
    overloads = owned_sites(graph, 'overloads')
    assert len(overloads) == 2 and len({s['declared_target'] for s in overloads}) == 2
    assert {s['signature'] for s in overloads} == {'(value: number): number', '(value: string): string'}
    direct = owned_sites(graph, 'direct')[0]
    assert symbols[direct['declared_target']]['name'] == 'asText'
    assert any(edge.kind == 'alias_of' for edge in graph.edges)


def test_generic_callback_parameter_uses_bindings_as_incomplete_candidates(actual_graph):
    _, _, graph = actual_graph
    site = owned_sites(graph, 'mapValue')[0]
    symbols = {s['id']: s for s in graph.symbols}
    assert site['declared_target'] is None
    assert {symbols[s]['name'] for s in site['dispatch_candidates']} == {'asText', '<anonymous>'}
    assert site['dispatch_complete'] is False
    assert site['evidence_kind'] != 'SYMBOL_RESOLVED'
    assert site['resolution_reason'] == 'CALLBACK_PARAMETER_OPEN_WORLD'
    # Argument/parameter proof includes direct inline arrows, not only identifiers.
    bindings = [edge for edge in graph.edges if edge.kind == 'argument_to_parameter'
                and symbols[edge.source]['name'] == '<anonymous>']
    assert len(bindings) == 1


def test_union_callback_does_not_choose_arbitrary_signature_declaration(actual_graph):
    _, _, graph = actual_graph
    site = owned_sites(graph, 'ambiguous')[0]
    symbols = {s['id']: s for s in graph.symbols}
    assert site['declared_target'] is None
    assert {symbols[s]['name'] for s in site['dispatch_candidates']} == {'asText', 'doubled'}
    assert site['dispatch_complete'] is False
    assert site['evidence_kind'] != 'SYMBOL_RESOLVED'
    assert site['resolution_reason'] == 'AMBIGUOUS_CALLBACK'
    dynamic = owned_sites(graph, 'dynamic')[0]
    assert dynamic['declared_target'] is None and dynamic['dispatch_candidates'] == []
    assert dynamic['resolution_reason'] == 'DYNAMIC_ANY'


def test_mutable_same_signature_callback_does_not_become_first_initializer(actual_graph):
    _, _, graph = actual_graph
    site = owned_sites(graph, 'mutable')[0]
    assert site['declared_target'] is None
    assert site['evidence_kind'] != 'SYMBOL_RESOLVED'
    assert site['dispatch_complete'] is False
    assert site['resolution_reason'] == 'MUTABLE_CALLBACK'


def test_candidates_roundtrip_and_offline_navigation_preserve_evidence(actual_graph):
    from kgmaker.callgraph import callees
    from kgmaker.feature import current_graph
    from kgmaker.store import save_graph
    root, _, graph = actual_graph
    graph = KnowledgeGraph.from_dict(graph.to_dict())
    site = owned_sites(graph, 'mapValue')[0]
    assert site['dispatch_candidates']
    candidate_edges = [edge for edge in graph.edges if edge.source == site['id']
                       and edge.kind == 'may_dispatch_to']
    assert {edge.target for edge in candidate_edges} == set(site['dispatch_candidates'])
    assert all(edge.evidence_kind == 'DISPATCH_CANDIDATE' for edge in candidate_edges)
    save_graph(graph, root, generate_docs=False)
    store = root / '.kgmaker/graph.json'
    before = store.read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('offline compiler process')):
        refreshed, _, _ = current_graph(root)
        definite = callees(refreshed, site['caller'], include_candidates=False)
        possible = callees(refreshed, site['caller'], include_candidates=True)
    assert not definite['results']
    assert {entry['target'] for entry in possible['results']} == set(site['dispatch_candidates'])
    assert all(entry['kind'] == 'DISPATCH_CANDIDATE' and not entry['dispatch_complete']
               for entry in possible['results'])
    assert store.read_bytes() == before


def test_overloaded_higher_order_api_binds_selected_signature_to_implementation_parameter(actual_graph):
    _, _, graph = actual_graph
    outer = owned_sites(graph, 'overloadedCallback')[0]
    assert outer['evidence_kind'] == 'SYMBOL_RESOLVED'
    assert outer['signature'] == '(value: number, callback: (value: number) => string): string'
    inner = owned_sites(graph, 'overloadedMap')[0]
    symbols = {s['id']: s for s in graph.symbols}
    assert inner['declared_target'] is None
    assert {symbols[target]['name'] for target in inner['dispatch_candidates']} == {'asText'}
    assert inner['dispatch_complete'] is False
    assert inner['resolution_reason'] == 'CALLBACK_PARAMETER_OPEN_WORLD'


def test_mutable_callback_property_does_not_promote_initializer(actual_graph):
    _, _, graph = actual_graph
    site = owned_sites(graph, 'mutableProperty')[0]
    assert site['declared_target'] is None
    assert site['evidence_kind'] != 'SYMBOL_RESOLVED'
    assert site['resolution_reason'] == 'MUTABLE_CALLBACK'


def test_ambient_callable_contract_remains_resolved_without_runtime_claim(actual_graph):
    _, _, graph = actual_graph
    site = owned_sites(graph, 'asText')[0]  # lib.es5 StringConstructor call signature
    symbols = {s['id']: s for s in graph.symbols}
    assert site['evidence_kind'] == 'SYMBOL_RESOLVED'
    assert symbols[site['declared_target']]['origin'] == 'dependency'
    assert site['dispatch_complete'] is False

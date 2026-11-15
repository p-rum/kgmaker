"""T003-S07-W08: evidence-bound priorities, never execution/availability proof."""
import copy
import io
import json
import shutil
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.views import rank


def snapshot():
    """Schema-v3 model fixture: exact identities; no compiler execution claimed."""
    nodes = [Node(i, kind, i, 'src/main/java/Orders.java', scope='production', role=role)
             for i, kind, role in [('entry', 'method', 'executable_code'),
                 ('decide', 'method', 'executable_code'), ('save', 'method', 'executable_code'),
                 ('Currency', 'enum', 'contract'), ('Order', 'class', 'contract'),
                 ('first', 'call_site', 'executable_code'), ('second', 'call_site', 'executable_code'),
                 ('unknown', 'call_site', 'executable_code'), ('table', 'table', 'contract')]]
    # Producer-shaped MODEL input; these IDs/claims are not native compiler results.
    # The separate actual Javac/CLI test establishes the positive native boundary.
    import hashlib
    source = Path(__file__).resolve().parents[1] / 'fixtures/evidence-ranking/src/main/java/Orders.java'
    files = {'src/main/java/Orders.java': hashlib.sha256(source.read_bytes()).hexdigest()}
    contexts = [{'id': 'ctx', 'scope': 'production', 'mode': 'BUILD_IMPORT',
                 'origin_trust': 'LOCAL_COMPILER_INPUTS', 'analyzer_version': 'model-inspection',
                 'worker': {'protocol_version': 1, 'worker': 'model-only-not-executed', 'compiler_version': 'model-only'},
                 'source_files': files.copy(),
                 'freshness': 'CONTENT_VERIFIED', 'coverage': 'COMPLETE_WITHIN_INDEXED_SCOPE'}]
    evidence = []
    edges = []
    def edge(a, b, kind, evidence_kind='SYMBOL_RESOLVED'):
        identity = f'ev:{a}:{b}:{kind}'
        evidence.append({'id': identity, 'kind': evidence_kind, 'source_file': 'src/main/java/Orders.java'})
        edges.append(Edge(a, b, kind, evidence_kind=evidence_kind, context_ids=('ctx',), evidence_ids=(identity,)))
        return identity
    sites = []
    for identity, caller, target in [('first', 'entry', 'decide'), ('second', 'decide', 'save'), ('unknown', 'save', None)]:
        kind = 'SYMBOL_RESOLVED' if target else 'UNRESOLVED'
        refs = [edge(caller, identity, 'declares_call', kind)]
        if target:
            refs.append(edge(identity, target, 'resolves_to'))
        sites.append({'id': identity, 'caller': caller, 'context_id': 'ctx', 'declared_target': target,
            'dispatch_candidates': [], 'dispatch_complete': bool(target), 'evidence_kind': kind,
            'evidence_ids': refs, 'resolution_reason': 'STATIC_TARGET' if target else 'MISSING_DEPENDENCY'})
    edge('save', 'table', 'query_writes', 'FRAMEWORK_DERIVED')
    edge('entry', 'Currency', 'references_type')
    edge('entry', 'Order', 'references_type')
    graph = KnowledgeGraph(3, '.', '', nodes, edges, files, contexts=contexts, evidence=evidence,
        symbols=[{'id': i, 'context_id': 'ctx'} for i in ('entry', 'decide', 'save', 'Currency', 'Order')], call_sites=sites)
    return KnowledgeGraph.from_dict(graph.to_dict())


def rows(result):
    return {row['id']: row for row in result['results']}


def test_every_score_has_traceable_contributions_and_local_penalty():
    graph = snapshot()
    result = rank(graph, 'entry')
    assert result['profile'] == 'execution-2'
    indexed = rows(result)
    for row in result['results']:
        assert row['score'] == sum(row['breakdown'].values())
        assert set(row['contributions']) == set(row['breakdown'])
        for term, value in row['breakdown'].items():
            if value:
                assert row['contributions'][term]
        assert row['coverage']['status'] in {'PARTIAL', 'UNKNOWN', 'COMPLETE_WITHIN_INDEXED_SCOPE'}
    assert indexed['decide']['score'] > indexed['Currency']['score'] == 0
    assert indexed['save']['breakdown']['incompleteness_penalty'] < 0
    assert any(gap['code'] == 'UNRESOLVED_CALL' and gap['call_site'] == 'unknown'
               for gap in indexed['save']['coverage']['gaps'])
    assert indexed['save']['path']['entity_ids'] == ['entry', 'first', 'decide', 'second', 'save']
    assert all(step['evidence_ids'] for step in indexed['save']['path']['steps'])
    assert any(edge['target'] == 'decide' for edge in indexed['decide']['evidence'])


def test_noise_and_order_do_not_inflate_execution_and_impact_is_separate():
    graph = snapshot()
    before = rank(graph, 'entry')
    noise = Node('test', 'method', 'test', 'src/test/java/Test.java', scope='test', role='executable_code')
    config = Node('config', 'method', 'fake', 'application.yml', scope='production', role='configuration')
    overlay = replace(graph, nodes=graph.nodes + [noise, config], edges=graph.edges + [
        Edge('test', 'decide', 'calls'), Edge('config', 'decide', 'calls'),
        *[Edge('entry', 'Currency', 'references_type') for _ in range(500)],
        Edge('Currency', 'decide', 'contains')])
    after = rank(overlay, 'entry')
    assert [(r['id'], r['score']) for r in before['results']] == [(r['id'], r['score']) for r in after['results']]
    impact = rows(rank(overlay, 'entry', 'impact'))
    assert impact['Currency']['breakdown']['type_reference_impact'] > 0
    assert impact['Currency']['breakdown']['execution_centrality'] == 0
    shuffled = replace(overlay, nodes=list(reversed(overlay.nodes)), edges=list(reversed(overlay.edges)),
        contexts=list(reversed(overlay.contexts)), call_sites=list(reversed(overlay.call_sites)), evidence=list(reversed(overlay.evidence)))
    assert after == rank(shuffled, 'entry')


@pytest.mark.parametrize('damage', ['unresolved', 'ambiguous', 'stale', 'runtime'])
def test_missing_proof_is_not_strengthened(damage):
    graph = snapshot()
    if damage == 'unresolved':
        graph.call_sites[0]['dispatch_complete'] = False
    elif damage == 'ambiguous':
        graph.call_sites[0]['dispatch_candidates'] = ['decide', 'save']
        graph.call_sites[0]['dispatch_complete'] = False
    elif damage == 'stale':
        graph.contexts[0]['freshness'] = 'STALE'
    else:
        graph.evidence.append({'id': 'runtime', 'kind': 'RUNTIME_OBSERVED'})
        graph.edges.append(Edge('entry', 'save', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                                context_ids=('ctx',), evidence_ids=('runtime',)))
        from kgmaker.callgraph import adjacency
        assert not next(e for e in adjacency(graph)['entry'] if e['kind'] == 'RUNTIME_OBSERVED')['dispatch_complete']
    result = rank(graph, 'entry')
    assert result['status'] in {'PARTIAL', 'UNKNOWN'}
    assert rows(result)['entry']['coverage']['gaps']
    assert 'availability' not in result
    if damage == 'stale':
        assert all(row['breakdown']['execution_centrality'] == 0 for row in result['results'])


@pytest.mark.parametrize('version', [1, 2, 3])
def test_old_schemas_roundtrip_without_invented_execution(version):
    raw = {'schema_version': version, 'nodes': [dict(id='a', kind='method', name='a', path='src/App.java',
            scope='production', role='executable_code')], 'edges': [], 'files': {}}
    graph = KnowledgeGraph.from_dict(raw)
    before = copy.deepcopy(graph.to_dict())
    result = rank(graph, scope='all')
    assert result['status'] == 'UNKNOWN'
    assert all(row['score'] == 0 for row in result['results'])
    assert before == graph.to_dict() == KnowledgeGraph.from_dict(graph.to_dict()).to_dict()


def test_invalid_and_interrupted_read_only_operations_never_mutate(tmp_path):
    graph = snapshot()
    before = copy.deepcopy(graph.to_dict())
    from kgmaker.store import save_graph
    save_graph(graph, tmp_path, generate_docs=False)
    stored = (tmp_path / '.kgmaker/graph.json').read_bytes()
    with patch('subprocess.run', side_effect=AssertionError('implicit process')):
        rank(graph)
        with pytest.raises(ValueError):
            rank(graph, 'missing')
        with pytest.raises(ValueError):
            rank(graph, profile='unknown')
        with patch('kgmaker.views.project', side_effect=TimeoutError('cancelled')):
            with pytest.raises(TimeoutError):
                rank(graph)
    assert graph.to_dict() == before
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == stored


def test_public_markdown_cli_and_renderer_are_explainable(tmp_path):
    from kgmaker.cli import main
    from kgmaker.analysis_report import render_ranking_report
    result = rank(snapshot(), 'entry')
    report = render_ranking_report(result)
    assert 'execution-2' in report and 'UNRESOLVED_CALL' in report and 'ev:' in report
    assert 'incompleteness_penalty' in report
    (tmp_path / 'app.py').write_text('def main(): pass\n')
    out = io.StringIO()
    with patch('sys.argv', ['kgmaker', 'graph', 'rank', '--root', str(tmp_path), '--format', 'markdown']), redirect_stdout(out):
        with pytest.raises(SystemExit) as exit_result:
            main()
        assert exit_result.value.code == 0
    assert '# Evidence ranking' in out.getvalue()


@pytest.mark.parametrize('damage', ['evidence', 'context', 'callsite', 'confidence'])
def test_invalid_references_are_rejected_before_scope_filtering_without_mutation(damage):
    graph = snapshot()
    if damage in {'evidence', 'context'}:
        graph.edges[0] = replace(graph.edges[0], **{damage + '_ids': ('missing',)})
    elif damage == 'callsite':
        graph.call_sites[0]['declared_target'] = 'absent'
    else:
        graph.edges[0] = replace(graph.edges[0], evidence_kind='RUNTIME_OBSERVED')
    before = copy.deepcopy(graph.to_dict())
    with pytest.raises(ValueError):
        rank(graph, scope='test')
    assert graph.to_dict() == before


def test_runtime_pair_does_not_remove_independent_static_completeness():
    graph = snapshot()
    graph.evidence.append({'id': 'runtime', 'kind': 'RUNTIME_OBSERVED'})
    graph.edges.append(Edge('entry', 'decide', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                           context_ids=('ctx',), evidence_ids=('runtime',)))
    from kgmaker.callgraph import adjacency
    pairs = adjacency(graph)['entry']
    assert next(e for e in pairs if e['kind'] == 'DECLARED_TARGET')['dispatch_complete']
    assert not next(e for e in pairs if e['kind'] == 'RUNTIME_OBSERVED')['dispatch_complete']
    assert not any(g['code'] == 'RUNTIME_SAMPLE_ONLY' for g in rows(rank(graph, 'entry'))['entry']['coverage']['gaps'])


def test_actual_javac_ranking_fixture_and_public_cli(tmp_path):
    import os
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    from kgmaker.cli import main
    fixture = Path(__file__).resolve().parents[1] / 'fixtures/evidence-ranking'
    shutil.copytree(fixture / 'src', tmp_path / 'src')
    try:
        result = inspect_jvm(tmp_path, classpath=[], publish=True)
    except WorkerError as error:
        if error.status == 'TOOLCHAIN_UNAVAILABLE' and os.environ.get('KGMAKER_REQUIRE_WORKERS') != '1':
            pytest.skip(str(error))
        raise
    assert result['exit_code'] == 0
    graph = KnowledgeGraph.from_dict(result['graph'])
    symbols = {n.name: n.id for n in graph.nodes if n.kind == 'method' and n.name in {'entry', 'decide', 'unresolved', 'dispatch'}}
    assert symbols.keys() == {'entry', 'decide', 'unresolved', 'dispatch'}
    ranked = rank(graph, symbols['entry'])
    indexed = rows(ranked)
    currency = next(n.id for n in graph.nodes if n.name == 'Currency' and n.kind == 'enum')
    assert indexed[symbols['decide']]['score'] > indexed[currency]['score'] == 0
    assert indexed[symbols['decide']]['path']['steps']
    assert any(g['code'] == 'UNRESOLVED_CALL' for g in indexed[symbols['unresolved']]['coverage']['gaps'])
    assert any(g['code'] == 'INCOMPLETE_DISPATCH' for g in indexed[symbols['dispatch']]['coverage']['gaps'])
    assert not any(n.id in indexed for n in graph.nodes if n.scope == 'test')
    stored = (tmp_path / '.kgmaker/graph.json').read_bytes()
    for format in ['json', 'markdown']:
        out = io.StringIO()
        with patch('subprocess.run', side_effect=AssertionError('implicit process')), patch('sys.argv', [
                'kgmaker', 'graph', 'rank', '--root', str(tmp_path), '--entry', symbols['entry'], '--format', format,
                '--context', result['context']['id']]), redirect_stdout(out):
            with pytest.raises(SystemExit) as exit_result:
                main()
        assert exit_result.value.code == 0, out.getvalue()
        if format == 'json':
            public = json.loads(out.getvalue())
            assert public['profile'] == ranked['profile']
            assert public['results'] == ranked['results']
        else:
            assert symbols['decide'] in out.getvalue() and 'UNRESOLVED_CALL' in out.getvalue()
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == stored
    # Public CLI must honor stale proof records even when compiler inputs/context
    # still validate as current. No worker is invoked to read the stored snapshot.
    from kgmaker.store import save_graph
    for proof in graph.evidence:
        proof['freshness'] = 'STALE'
    save_graph(graph, tmp_path, generate_docs=False)
    stored = (tmp_path / '.kgmaker/graph.json').read_bytes()
    out = io.StringIO()
    with patch('subprocess.run', side_effect=AssertionError('implicit process')), patch('sys.argv', [
            'kgmaker', 'graph', 'rank', '--root', str(tmp_path), '--entry', symbols['entry'],
            '--context', result['context']['id']]), redirect_stdout(out):
        with pytest.raises(SystemExit) as exit_result:
            main()
    assert exit_result.value.code == 0, out.getvalue()
    public = json.loads(out.getvalue())
    assert all(row['score'] == 0 and not row['path']['steps'] for row in public['results'])
    assert public['status'] == 'UNKNOWN'
    assert any(g['code'] == 'STALE_EVIDENCE' for row in public['results'] for g in row['coverage']['gaps'])
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == stored


def test_selected_variant_retains_only_required_source_contexts_and_valid_records():
    from kgmaker.views import project
    graph = snapshot()
    graph.contexts[0]['analyzer_version'] = 'fixture-1'
    other = snapshot().to_dict()
    # A disjoint complete compiler variant: symbol, call-site and CFG isolation.
    other = json.loads(json.dumps(other).replace('"ctx"', '"other"'))
    mapping = {n['id']: 'other:' + n['id'] for n in other['nodes']}
    for node in other['nodes']:
        node['id'] = mapping[node['id']]
    for edge in other['edges']:
        edge['source'], edge['target'] = mapping[edge['source']], mapping[edge['target']]
        edge['evidence_ids'] = ['other:' + i for i in edge['evidence_ids']]
    for item in other['evidence']:
        item['id'] = 'other:' + item['id']
    for item in other['symbols']:
        item['id'] = mapping[item['id']]
    for item in other['call_sites']:
        item['id'], item['caller'] = mapping[item['id']], mapping[item['caller']]
        if item['declared_target']:
            item['declared_target'] = mapping[item['declared_target']]
        item['evidence_ids'] = ['other:' + i for i in item['evidence_ids']]
    other['symbols'].append({'id': 'other:table', 'context_id': 'other'})
    other['contexts'][0]['analyzer_version'] = 'fixture-1'
    raw = graph.to_dict()
    for key in ['nodes', 'edges', 'evidence', 'contexts', 'symbols', 'call_sites']:
        raw[key] += other[key]
    for context_id, method in [('ctx', 'entry'), ('other', 'other:entry')]:
        raw['cfgs'].append({'context_id': context_id, 'method': method, 'entry': 'in', 'exit': 'out',
                           'blocks': [{'id': 'in'}, {'id': 'out'}], 'edges': []})
    raw['contexts'].append({'id': 'source', 'mode': 'SOURCE_ONLY', 'scope': 'production'})
    raw['edges'].append({'source': 'entry', 'target': 'Order', 'kind': 'contains', 'context_ids': ['source']})
    selected = project(KnowledgeGraph.from_dict(raw), context_id='ctx')
    assert {c['id'] for c in selected.contexts} == {'ctx', 'source'}
    assert all(not n.id.startswith('other:') for n in selected.nodes)
    assert {s['context_id'] for s in selected.call_sites + selected.symbols + selected.cfgs} == {'ctx'}
    assert all('other' not in e.context_ids for e in selected.edges)
    assert KnowledgeGraph.from_dict(selected.to_dict()).to_dict() == selected.to_dict()


def test_test_call_and_configuration_call_cannot_inflate_production_in_all_scope():
    graph = snapshot()
    baseline = rows(rank(graph, 'entry', scope='all'))
    for identity, scope, role in [('test', 'test', 'executable_code'), ('config', 'production', 'configuration')]:
        graph.nodes.append(Node(identity, 'method', identity, identity + '.java', scope=scope, role=role))
        graph.evidence.append({'id': identity, 'kind': 'SYMBOL_RESOLVED'})
        graph.edges.append(Edge(identity, 'decide', 'resolves_to', evidence_kind='SYMBOL_RESOLVED',
                               context_ids=('ctx',), evidence_ids=(identity,)))
    result = rows(rank(graph, 'entry', scope='all'))
    assert result['decide']['score'] == baseline['decide']['score']



def test_confidence_and_duplicate_records_do_not_add_weight():
    graph = snapshot()
    before = rows(rank(graph, 'entry'))
    graph.edges += [replace(edge, confidence_score=.01, evidence='another presentation') for edge in graph.edges]
    after = rows(rank(graph, 'entry'))
    assert {i: r['score'] for i, r in before.items()} == {i: r['score'] for i, r in after.items()}


@pytest.mark.parametrize('profile', ['execution', 'impact'])
def test_stale_proof_records_cannot_supply_current_weight_or_paths(profile, tmp_path):
    from kgmaker.analysis_report import render_ranking_report
    from kgmaker.store import save_graph
    graph = snapshot()
    for proof in graph.evidence:
        proof['freshness'] = 'STALE'
    graph = KnowledgeGraph.from_dict(graph.to_dict())
    save_graph(graph, tmp_path, generate_docs=False)
    before = copy.deepcopy(graph.to_dict())
    stored = (tmp_path / '.kgmaker/graph.json').read_bytes()
    with patch('subprocess.run', side_effect=AssertionError('implicit process')):
        result = rank(graph, 'entry', profile)
    assert result['status'] == 'UNKNOWN'
    for row in result['results']:
        assert row['score'] == 0
        assert row['coverage']['status'] == 'UNKNOWN'
        assert row['path'] == {'entity_ids': [], 'steps': []}
        assert not row['evidence']
        assert all(not value for term, value in row['contributions'].items() if term != 'incompleteness_penalty')
    entry = rows(result)['entry']
    assert any(g['code'] == 'STALE_EVIDENCE' and g['evidence_ids'] for g in entry['coverage']['gaps'])
    assert 'STALE_EVIDENCE' in render_ranking_report(result)
    assert graph.to_dict() == before and (tmp_path / '.kgmaker/graph.json').read_bytes() == stored


@pytest.mark.parametrize('kind', ['METHOD_REFERENCE', 'INVOKEDYNAMIC', 'UNSUPPORTED_REFERENCE'])
def test_non_execution_site_cannot_close_runtime_only_dispatch_gap(kind):
    from kgmaker.callgraph import adjacency
    graph = snapshot()
    graph.call_sites[0]['invocation_kind'] = kind
    assert graph.call_sites[0]['dispatch_complete'] is True
    graph.evidence.append({'id': 'runtime-only', 'kind': 'RUNTIME_OBSERVED', 'freshness': 'CURRENT'})
    graph.edges.append(Edge('entry', 'decide', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                           context_ids=('ctx',), evidence_ids=('runtime-only',)))
    result = rows(rank(KnowledgeGraph.from_dict(graph.to_dict()), 'entry'))
    entry = result['entry']
    assert any(g['code'] == 'RUNTIME_SAMPLE_ONLY' for g in entry['coverage']['gaps'])
    assert entry['coverage']['status'] == 'PARTIAL'
    assert all(e['kind'] == 'observed_dispatch_to' for e in entry['contributions']['execution_centrality'])
    assert result['decide']['path']['entity_ids'] == ['entry', 'decide']
    assert all(step['kind'] == 'observed_dispatch_to' for step in result['decide']['path']['steps'])
    assert all(e['kind'] == 'RUNTIME_OBSERVED' and not e['dispatch_complete'] for e in adjacency(graph)['entry'])


@pytest.mark.parametrize('damage', ['stale_proof', 'unknown_proof', 'stale_site_proof', 'missing_declares',
                                    'missing_resolves', 'unresolved_site', 'cross_scope', 'configuration_caller'])
def test_only_admitted_current_static_path_closes_observation_gap(damage):
    graph = snapshot()
    site = graph.call_sites[0]
    if damage in {'stale_proof', 'unknown_proof'}:
        proof = next(p for p in graph.evidence if p['id'] == site['evidence_ids'][-1])
        proof['freshness'] = 'STALE' if damage == 'stale_proof' else 'UNKNOWN'
    elif damage == 'stale_site_proof':
        graph.evidence.append({'id': 'stale-site', 'kind': 'SYMBOL_RESOLVED', 'freshness': 'STALE'})
        site['evidence_ids'].append('stale-site')
    elif damage == 'missing_declares':
        graph.edges = [e for e in graph.edges if not (e.source == 'entry' and e.target == 'first')]
    elif damage == 'missing_resolves':
        graph.edges = [e for e in graph.edges if not (e.source == 'first' and e.target == 'decide')]
    elif damage == 'unresolved_site':
        site['evidence_kind'] = 'UNRESOLVED'
    elif damage == 'cross_scope':
        graph.nodes = [replace(n, scope='test') if n.id == 'first' else n for n in graph.nodes]
    else:
        graph.nodes = [replace(n, role='configuration') if n.id == 'first' else n for n in graph.nodes]
    graph.evidence.append({'id': 'runtime-only', 'kind': 'RUNTIME_OBSERVED', 'freshness': 'CURRENT'})
    graph.edges.append(Edge('entry', 'decide', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                           context_ids=('ctx',), evidence_ids=('runtime-only',)))
    result = rows(rank(graph, 'entry', scope='all'))
    assert any(g['code'] == 'RUNTIME_SAMPLE_ONLY' for g in result['entry']['coverage']['gaps'])
    assert result['entry']['coverage']['status'] == 'PARTIAL'
    if damage in {'stale_proof', 'stale_site_proof', 'unresolved_site', 'cross_scope', 'configuration_caller'}:
        assert all(e['kind'] == 'observed_dispatch_to' for e in result['entry']['contributions']['execution_centrality'])
    if damage == 'unknown_proof':
        assert any(g['code'] == 'EVIDENCE_FRESHNESS_UNKNOWN' for g in result['entry']['coverage']['gaps'])



def test_runtime_only_and_unknown_proof_gaps_follow_the_selected_path():
    graph = snapshot()
    graph.call_sites[0]['invocation_kind'] = 'METHOD_REFERENCE'
    graph.evidence.append({'id': 'runtime-only', 'kind': 'RUNTIME_OBSERVED', 'freshness': 'UNKNOWN'})
    graph.edges.append(Edge('entry', 'decide', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                           context_ids=('ctx',), evidence_ids=('runtime-only',)))
    result = rows(rank(graph, 'entry'))['save']
    assert result['path']['entity_ids'] == ['entry', 'decide', 'second', 'save']
    for code in ['RUNTIME_SAMPLE_ONLY', 'EVIDENCE_FRESHNESS_UNKNOWN']:
        assert any(g['code'] == code and g['evidence_ids'] == ['runtime-only'] for g in result['coverage']['gaps'])
    assert result['coverage']['status'] == 'PARTIAL'



@pytest.mark.parametrize('kind', [None, 'CALL', 'STATIC', 'VIRTUAL', 'INTERFACE', 'SPECIAL',
                                  'CONSTRUCTOR', 'EXTENSION', 'OPERATOR', 'ACCESSOR'])
def test_supported_compiler_invocation_kinds_retain_static_evidence(kind):
    from kgmaker.callgraph import adjacency
    graph = snapshot()
    graph.call_sites[0]['invocation_kind'] = kind
    graph.evidence.append({'id': 'runtime-only', 'kind': 'RUNTIME_OBSERVED', 'freshness': 'CURRENT'})
    graph.edges.append(Edge('entry', 'decide', 'observed_dispatch_to', evidence_kind='RUNTIME_OBSERVED',
                           context_ids=('ctx',), evidence_ids=('runtime-only',)))
    entry = rows(rank(graph, 'entry'))['entry']
    assert any(e['kind'] == 'declares_call' for e in entry['contributions']['execution_centrality'])
    assert not any(g['code'] == 'RUNTIME_SAMPLE_ONLY' for g in entry['coverage']['gaps'])
    assert any(e['kind'] == 'DECLARED_TARGET' and e['dispatch_complete'] for e in adjacency(graph)['entry'])


@pytest.mark.parametrize('profile', ['execution', 'impact'])
@pytest.mark.parametrize('scope', ['production', 'all'])
@pytest.mark.parametrize('damage', ['source_only', 'unknown_mode', 'legacy_compiler_label', 'missing_mode',
                                    'bare_build', 'missing_analyzer', 'missing_worker', 'missing_sources',
                                    'mismatched_sources', 'unknown_freshness', 'source_only_proof', 'foreign_proof_context'])
def test_context_authority_is_required_before_execution_admission(profile, scope, damage):
    graph = snapshot()
    context = graph.contexts[0]
    if damage == 'source_only': context['mode'] = 'SOURCE_ONLY'
    elif damage == 'unknown_mode': context['mode'] = 'UNKNOWN'
    elif damage == 'legacy_compiler_label': context['mode'] = 'COMPILER'
    elif damage == 'missing_mode': context.pop('mode')
    elif damage == 'bare_build':
        graph.contexts[0] = {'id':'ctx', 'mode':'BUILD_IMPORT', 'scope':'production',
                             'freshness':'CONTENT_VERIFIED', 'coverage':'COMPLETE'}
    elif damage == 'missing_analyzer': context.pop('analyzer_version', None)
    elif damage == 'missing_worker': context.pop('worker', None)
    elif damage == 'missing_sources': context.pop('source_files', None)
    elif damage == 'mismatched_sources': graph.files = {}
    elif damage == 'unknown_freshness': context['freshness'] = 'UNKNOWN'
    elif damage == 'source_only_proof':
        for proof in graph.evidence: proof['mode'] = 'SOURCE_ONLY'
    else:
        graph.contexts.append({**context, 'id':'other'})
        for proof in graph.evidence: proof['context_ids'] = ['other']
    before = copy.deepcopy(graph.to_dict())
    result = rank(KnowledgeGraph.from_dict(graph.to_dict()), 'entry', profile, scope)
    for row in result['results']:
        assert all(row['breakdown'][term] == 0 for term in ('entry_relevance', 'execution_path', 'execution_centrality', 'side_effects'))
        assert not row['path']['entity_ids']
    entry = rows(result)['entry']
    assert entry['score'] == 0 and entry['coverage']['status'] == 'UNKNOWN'
    assert any('AUTHORITY' in g['code'] for g in entry['coverage']['gaps'])
    assert graph.to_dict() == before


@pytest.mark.parametrize('profile', ['execution', 'impact'])
@pytest.mark.parametrize('scope', ['production', 'all'])
def test_mixed_compiler_edge_is_omitted_without_importing_other_variant(profile, scope):
    from kgmaker.views import project
    graph = snapshot()
    graph.contexts.append({**graph.contexts[0], 'id': 'other'})
    graph.contexts.append({'id':'source', 'mode':'SOURCE_ONLY', 'scope':'production'})
    graph.edges[0] = replace(graph.edges[0], context_ids=('ctx', 'other'))
    graph.edges.append(Edge('entry', 'Order', 'contains', context_ids=('source',)))
    before = copy.deepcopy(graph.to_dict())
    selected = project(KnowledgeGraph.from_dict(graph.to_dict()), scope, context_id='ctx')
    assert {c['id'] for c in selected.contexts} == {'ctx', 'source'}
    assert all(set(e.context_ids) <= {'ctx', 'source'} for e in selected.edges)
    assert not any(e.source == 'entry' and e.target == 'first' for e in selected.edges)
    assert any(d['code'] == 'COMPILER_CONTEXT_BOUNDARY_UNKNOWN' for d in selected.diagnostics)
    assert selected.call_sites[0]['dispatch_complete'] is False
    assert selected.call_sites[0]['declared_target'] is None
    assert set(selected.call_sites[0]['evidence_ids']).isdisjoint(graph.edges[0].evidence_ids)
    assert KnowledgeGraph.from_dict(selected.to_dict()).to_dict() == selected.to_dict()
    entry = rows(rank(selected, 'entry', profile, scope))['entry']
    assert entry['breakdown']['execution_centrality'] == 0 and not entry['path']['entity_ids']
    assert graph.to_dict() == before


@pytest.mark.parametrize('origin,freshness', [('LOCAL_COMPILER_INPUTS', 'CONTENT_VERIFIED'),
    ('LOCAL_TRUSTED', 'EXECUTION_BOUND'), ('SUPPLIED_EXPORT_UNVERIFIED', 'EXECUTION_BOUND')])
@pytest.mark.parametrize('kind,relation', [('SYMBOL_RESOLVED','resolves_to'),
    ('DISPATCH_CANDIDATE','may_dispatch_to'), ('FRAMEWORK_DERIVED','query_writes'),
    ('RUNTIME_OBSERVED','observed_dispatch_to')])
def test_real_producer_context_shape_preserves_separate_evidence_families(origin, freshness, kind, relation):
    graph = snapshot()
    graph.contexts[0].update(origin_trust=origin, freshness=freshness)
    graph.edges = [Edge('entry','save',relation,evidence_kind=kind,context_ids=('ctx',),evidence_ids=('proof',))]
    graph.call_sites = []
    graph.evidence = [{'id':'proof','kind':kind, 'freshness':freshness, 'origin_trust':origin}]
    # These are modeled valid producer tuples. The separate actual JVM test
    # verifies that real inspection output satisfies this same admission rule.
    row = rows(rank(graph, 'entry'))['entry']
    assert row['score'] > 0
    assert row['breakdown']['side_effects' if kind == 'FRAMEWORK_DERIVED' else 'execution_centrality'] == 1
    assert not any('AUTHORITY' in g['code'] for g in row['coverage']['gaps'])
    if kind == 'RUNTIME_OBSERVED':
        assert any(g['code'] == 'RUNTIME_SAMPLE_ONLY' for g in row['coverage']['gaps'])


@pytest.mark.parametrize('version', [2, 3])
@pytest.mark.parametrize('profile', ['execution', 'impact'])
@pytest.mark.parametrize('scope', ['production', 'all'])
def test_legacy_source_only_label_never_becomes_execution(version, profile, scope):
    graph = snapshot()
    graph.schema_version = version
    graph.contexts = [{'id':'ctx', 'mode':'SOURCE_ONLY', 'freshness':'UNKNOWN',
                       'scope':'production', 'coverage':'PARTIAL'}]
    result = rank(KnowledgeGraph.from_dict(graph.to_dict()), 'entry', profile, scope)
    assert rows(result)['entry']['score'] == 0
    assert all(row['breakdown']['execution_centrality'] == 0 and not row['path']['steps'] for row in result['results'])


@pytest.mark.parametrize('foreign_place', ['edge', 'proof', 'site', 'cfg'])
def test_variant_boundary_cannot_expand_symbols_sites_cfg_or_evidence(foreign_place):
    from kgmaker.views import project
    graph = snapshot()
    graph.contexts.append({**graph.contexts[0], 'id':'other'})
    for identity, kind in [('other-method','method'), ('other-call','call_site')]:
        graph.nodes.append(Node(identity,kind,identity,'src/main/java/Orders.java',scope='production',role='executable_code'))
    graph.symbols.append({'id':'other-method','context_id':'other'})
    graph.evidence.append({'id':'foreign-proof','kind':'SYMBOL_RESOLVED','context_ids':['other']})
    graph.call_sites.append({'id':'other-call','caller':'other-method','declared_target':'other-method',
        'context_id':'other','evidence_kind':'SYMBOL_RESOLVED','evidence_ids':['foreign-proof'],
        'resolution_reason':'MODEL','dispatch_complete':True})
    graph.cfgs.append({'context_id':'other','method':'other-method','entry':'in','exit':'out',
                      'blocks':[{'id':'in'},{'id':'out'}],'edges':[],'evidence_ids':['foreign-proof']})
    if foreign_place == 'edge':
        graph.edges.append(Edge('entry','other-method','resolves_to',evidence_kind='SYMBOL_RESOLVED',
                               context_ids=('ctx','other'),evidence_ids=('foreign-proof',)))
    elif foreign_place == 'proof':
        graph.edges.append(Edge('entry','decide','resolves_to',evidence_kind='SYMBOL_RESOLVED',
                               context_ids=('ctx',),evidence_ids=('foreign-proof',)))
    elif foreign_place == 'site':
        graph.call_sites[0]['evidence_ids'].append('foreign-proof')
    else:
        graph.cfgs.append({'context_id':'ctx','method':'entry','entry':'in','exit':'out',
            'blocks':[{'id':'in','local_operation_version':1,'local_operation_evidence_ids':['foreign-proof']},
                      {'id':'out'}],'edges':[]})
    graph = KnowledgeGraph.from_dict(graph.to_dict())
    before = copy.deepcopy(graph.to_dict())
    selected = project(graph, context_id='ctx')
    assert {c['id'] for c in selected.contexts} == {'ctx'}
    assert all(not n.id.startswith('other-') for n in selected.nodes)
    assert all(s.get('context_id') == 'ctx' for s in selected.symbols + selected.call_sites + selected.cfgs)
    assert all(e['id'] != 'foreign-proof' for e in selected.evidence)
    assert all('other' not in e.context_ids and 'foreign-proof' not in e.evidence_ids for e in selected.edges)
    assert any(d['code'] == 'COMPILER_CONTEXT_BOUNDARY_UNKNOWN' for d in selected.diagnostics)
    assert KnowledgeGraph.from_dict(selected.to_dict()).to_dict() == selected.to_dict()
    assert graph.to_dict() == before



def test_selected_projection_retains_source_provenance_of_evidence_without_compiler_promotion():
    from kgmaker.views import project
    graph = snapshot()
    graph.contexts.append({'id':'source', 'mode':'SOURCE_ONLY', 'scope':'production', 'freshness':'CONTENT_VERIFIED'})
    for proof in graph.evidence:
        proof['context_ids'] = ['source']
    selected = project(graph, context_id='ctx')
    assert {c['id'] for c in selected.contexts} == {'ctx','source'}
    assert all(p['context_ids'] == ['source'] for p in selected.evidence)
    assert KnowledgeGraph.from_dict(selected.to_dict()).to_dict() == selected.to_dict()
    assert rows(rank(selected, 'entry'))['entry']['score'] == 0

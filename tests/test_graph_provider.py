"""Offline refresh regression tests; no compiler toolchain is required."""
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import pytest

from kgmaker.cli import scan, hook_context
from kgmaker.feature import current_graph
from kgmaker.inspection import context, graph_from_response
from kgmaker.graph_provider import merge_compiler_context
from kgmaker.scanner import scan_repository
from kgmaker.store import load_graph, save_graph
from kgmaker.worker_protocol import WorkerError


def indexed(root):
    path = root / 'src/main/java/Example.java'
    path.parent.mkdir(parents=True)
    path.write_text('class Example { void run() {} }')
    base = scan_repository(root)
    selected = context(root, base, 'jvm', {}, repo_id='fixture', module='core',
                       source_set='main', scope='production')
    symbol = {'id': 'compiler:run', 'name': 'run', 'kind': 'method',
              'context_id': selected['id'], 'path': path.relative_to(root).as_posix()}
    response = {'context_id': selected['id'], 'symbols': [symbol], 'worker': {},
                'call_sites': [], 'bodies': [], 'facts': [], 'diagnostics': [],
                'coverage': {}, 'status': 'PARTIAL'}
    graph = graph_from_response(root, base, response, selected)
    save_graph(graph, root)
    return graph, path


def module_graph(root, module, path, symbol_id, *, profile=None):
    model = {'source_sets': [{'module': module, 'id': 'main', 'scope': 'production',
                              'files': [path]}]}
    base = scan_repository(root, project_model=model)
    build_context = {'project_model': model, 'spring_profiles': [profile] if profile else []}
    selected = context(root, base, 'jvm', {}, repo_id='fixture', module=module,
                       source_set='main', scope='production', build_context=build_context)
    symbol = {'id': symbol_id, 'name': 'run', 'kind': 'method',
              'context_id': selected['id'], 'path': path}
    response = {'context_id': selected['id'], 'symbols': [symbol], 'worker': {},
                'call_sites': [], 'bodies': [], 'facts': [], 'diagnostics': [],
                'coverage': {}, 'status': 'PARTIAL'}
    return graph_from_response(root, base, response, selected), selected


def test_scan_hook_and_feature_retain_compiler_layer_without_processes(tmp_path):
    original, _ = indexed(tmp_path)
    with patch('subprocess.Popen', side_effect=AssertionError('offline path spawned process')):
        with redirect_stdout(StringIO()):
            assert scan(tmp_path, generate_docs=False) == 0
            assert hook_context(tmp_path) == 0
        graph, _, _ = current_graph(tmp_path)
    assert graph.symbols == original.symbols
    assert {e["id"] for e in original.evidence} <= {e["id"] for e in graph.evidence}
    assert load_graph(tmp_path).symbols == original.symbols


@pytest.mark.parametrize('change', ['modified', 'added', 'deleted'])
def test_stale_refresh_marks_context_and_does_not_publish_until_scan(tmp_path, change):
    original, source = indexed(tmp_path)
    before = (tmp_path / '.kgmaker/graph.json').read_bytes()
    if change == 'modified':
        source.write_text('class Example { void changed() {} }')
    elif change == 'added':
        source.with_name('Other.java').write_text('class Other {}')
    else:
        source.unlink()
    live, _, _ = current_graph(tmp_path)
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == before
    compiler = next(item for item in live.contexts if item.get('analyzer_version'))
    assert compiler['freshness'] == 'STALE'
    assert compiler['next_command'].startswith('kgmaker inspect code')
    assert not live.symbols
    assert original.symbols
    with patch('subprocess.Popen', side_effect=AssertionError('offline path spawned process')):
        with redirect_stdout(StringIO()):
            assert hook_context(tmp_path) == 0
    stored = load_graph(tmp_path)
    assert not stored.symbols
    assert any(item.get('freshness') == 'STALE' for item in stored.contexts)
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() != before


def test_second_module_and_profile_context_preserve_previous_contexts(tmp_path):
    for module in ('a', 'b'):
        source = tmp_path / module / f'{module.upper()}.java'
        source.parent.mkdir(parents=True)
        source.write_text(f'class {module.upper()} {{ void run() {{}} }}')
    graph_a, context_a = module_graph(tmp_path, 'a', 'a/A.java', 'compiler:a:default')
    save_graph(merge_compiler_context(tmp_path, graph_a, context_a), tmp_path)
    graph_b, context_b = module_graph(tmp_path, 'b', 'b/B.java', 'compiler:b:default')
    save_graph(merge_compiler_context(tmp_path, graph_b, context_b), tmp_path)
    graph_profile, context_profile = module_graph(
        tmp_path, 'a', 'a/A.java', 'compiler:a:special', profile='special')
    merged = merge_compiler_context(tmp_path, graph_profile, context_profile)
    save_graph(merged, tmp_path)
    compiler_contexts = [item for item in merged.contexts if item.get('analyzer_version')]
    assert {item['id'] for item in compiler_contexts} == {
        context_a['id'], context_b['id'], context_profile['id']}
    assert {item['id'] for item in merged.symbols} == {
        'compiler:a:default', 'compiler:b:default', 'compiler:a:special'}
    from kgmaker.views import project, select_context
    with pytest.raises(ValueError, match='Explicit --context required'):
        select_context(merged, 'production')
    selected = project(merged, 'all', context_id=context_b['id'])
    assert {item['id'] for item in selected.symbols} == {'compiler:b:default'}
    assert {item['context_id'] for item in selected.symbols} == {context_b['id']}


def test_stale_module_is_projected_out_while_other_context_remains_usable(tmp_path):
    for module in ('a', 'b'):
        source = tmp_path / module / f'{module.upper()}.java'
        source.parent.mkdir(parents=True)
        source.write_text(f'class {module.upper()} {{ void run() {{}} }}')
    graph_a, context_a = module_graph(tmp_path, 'a', 'a/A.java', 'compiler:a')
    save_graph(merge_compiler_context(tmp_path, graph_a, context_a), tmp_path)
    graph_b, context_b = module_graph(tmp_path, 'b', 'b/B.java', 'compiler:b')
    save_graph(merge_compiler_context(tmp_path, graph_b, context_b), tmp_path)

    (tmp_path / 'a/A.java').write_text('class A { void changed() {} }')
    with patch('subprocess.Popen', side_effect=AssertionError('offline path spawned process')):
        live, _, _ = current_graph(tmp_path)
    contexts = {item['id']: item for item in live.contexts if item.get('analyzer_version')}
    assert contexts[context_a['id']]['freshness'] == 'STALE'
    assert contexts[context_b['id']]['freshness'] == 'CONTENT_VERIFIED'
    assert {item['id'] for item in live.symbols} == {'compiler:b'}
    assert any(item.get('code') == 'STALE_COMPILER_CONTEXT' for item in live.diagnostics)


def test_feature_packet_binds_compiler_context_and_graph_evidence(tmp_path):
    original, source = indexed(tmp_path)
    requirement = tmp_path / 'requirement.md'
    requirement.write_text('Use the indexed compiler method.')
    from kgmaker.feature import prepare
    packet = prepare(tmp_path, 'requirement.md', 'compiler-context')
    compiler = next(item for item in packet['analysis_contexts']
                    if item.get('analyzer_version'))
    assert compiler['id'] == next(item['id'] for item in original.contexts
                                  if item.get('analyzer_version'))
    assert packet['baseline']['analysis_context_fingerprint'] == packet['analysis_context_fingerprint']
    assert packet['graph_evidence_ids']

    source.write_text('class Example { void changed() {} }')
    revised = prepare(tmp_path, 'requirement.md', 'compiler-context')
    stale = next(item for item in revised['analysis_contexts']
                 if item.get('analyzer_version'))
    assert stale['freshness'] == 'STALE'
    assert revised['analysis_context_fingerprint'] != packet['analysis_context_fingerprint']
    assert revised['revision'] == packet['revision'] + 1


def test_invalid_second_module_does_not_publish_over_first(tmp_path):
    for module in ('a', 'b'):
        source = tmp_path / module / f'{module.upper()}.java'
        source.parent.mkdir(parents=True)
        source.write_text(f'class {module.upper()} {{ void run() {{}} }}')
    graph_a, context_a = module_graph(tmp_path, 'a', 'a/A.java', 'compiler:a')
    save_graph(merge_compiler_context(tmp_path, graph_a, context_a), tmp_path)
    before = (tmp_path / '.kgmaker/graph.json').read_bytes()
    model = {'source_sets': [{'module': 'b', 'id': 'main', 'scope': 'production',
                              'files': ['b/B.java']}]}
    base = scan_repository(tmp_path, project_model=model)
    selected = context(tmp_path, base, 'jvm', {}, repo_id='fixture', module='b',
                       source_set='main', scope='production', build_context={'project_model': model})
    response = {'context_id': selected['id'], 'symbols': [], 'worker': {},
                'call_sites': [{'id': 'bad', 'caller': 'missing'}], 'bodies': [],
                'facts': [], 'diagnostics': [], 'coverage': {}, 'status': 'PARTIAL'}
    with pytest.raises(WorkerError, match='Dangling'):
        graph_from_response(tmp_path, base, response, selected)
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == before

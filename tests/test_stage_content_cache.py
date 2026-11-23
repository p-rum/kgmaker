"""W01 integration contracts; fake transport tests are separate from actual workers."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from kgmaker import extraction_cache, inspection, store
from kgmaker.analysis_model import file_hash
from kgmaker.extraction_cache import launch_inputs
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.worker_protocol import WorkerError


@pytest.fixture
def transport(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Example { void run() {} }\n')
    worker = tmp_path / 'worker.jar'
    worker.write_bytes(b'explicit fake transport fixture v1')
    metadata = {'protocol_version': 1, 'worker': 'test-worker-1',
                'compiler_version': 'test-compiler-1', 'capabilities': []}
    calls = {'analyze': 0, 'graph': 0, 'framework': 0}
    behavior = {'status': 'COMPLETE', 'error': None}
    monkeypatch.setattr(inspection, 'command', lambda *a, **kw: ['/bin/true'])
    monkeypatch.setattr(inspection, 'handshake', lambda *a, **kw: deepcopy(metadata))
    monkeypatch.setattr(inspection, 'distribution', lambda *a, **kw: [
        {'path': str(worker), 'sha256': file_hash(worker)}])
    def request(argv, payload, **kw):
        calls['analyze'] += 1
        if behavior['error']:
            raise WorkerError('deliberate transport error', behavior['error'])
        selected = payload['context']
        return {**metadata, 'context_id': selected['id'], 'symbols': [],
                'call_sites': [], 'bodies': [], 'facts': [], 'diagnostics': [],
                'coverage': {}, 'status': behavior['status']}
    monkeypatch.setattr(inspection, 'request_worker', request)
    graph = inspection.graph_from_response
    def graph_call(*a, **kw):
        calls['graph'] += 1
        return graph(*a, **kw)
    monkeypatch.setattr(inspection, 'graph_from_response', graph_call)
    import kgmaker.framework as framework
    augment = framework.augment_framework_graph
    def framework_call(*a, **kw):
        calls['framework'] += 1
        return augment(*a, **kw)
    monkeypatch.setattr(framework, 'augment_framework_graph', framework_call)
    return root, source, worker, metadata, calls, behavior


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


def facts(value):
    value = deepcopy(value)
    value.pop('generated_at', None)
    value.pop('extraction_cache', None)
    return value


@pytest.fixture
def java_launch(tmp_path, monkeypatch):
    for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS',
                 'NODE_OPTIONS', 'CLASSPATH'):
        monkeypatch.delenv(name, raising=False)
    jdk = tmp_path / 'jdk'
    java = jdk / 'bin/java'
    for path in (java, jdk / 'release', jdk / 'lib/modules', jdk / 'lib/ct.sym'):
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(path.name, encoding='utf-8')
    return [str(java)], jdk / 'lib/ct.sym'


@pytest.mark.skipif(os.name != 'posix', reason='POSIX Java locale capture')
@pytest.mark.parametrize('name', ['LANG', 'LC_ALL', 'LC_CTYPE'])
def test_java_launch_capture_binds_exact_locale(java_launch, monkeypatch, name):
    argv, _ = java_launch
    monkeypatch.delenv(name, raising=False)
    absent = launch_inputs(argv)
    monkeypatch.setenv(name, '')
    empty = launch_inputs(argv)
    monkeypatch.setenv(name, 'C')
    present = launch_inputs(argv)
    assert len({capture['environment_sha256'] for capture in (absent, empty, present)}) == 3
    monkeypatch.setenv('JDK_JAVA_OPTIONS', '-Duser.language=ja')
    assert launch_inputs(argv) is None


@pytest.mark.skipif(os.name != 'posix', reason='POSIX Java locale capture')
def test_java_launch_capture_binds_non_utf8_locale(java_launch, monkeypatch):
    argv, _ = java_launch
    monkeypatch.setitem(os.environb, b'LC_ALL', b'\xfe')
    before = launch_inputs(argv)
    monkeypatch.setitem(os.environb, b'LC_ALL', b'\xff')
    after = launch_inputs(argv)
    assert before['environment_sha256'] != after['environment_sha256']


def test_java_launch_capture_binds_ct_sym_contents(java_launch):
    argv, platform_symbols = java_launch
    original = launch_inputs(argv)
    assert original['files'][str(platform_symbols.resolve())] == file_hash(platform_symbols)
    platform_symbols.write_bytes(b'new platform symbols')
    changed = launch_inputs(argv)
    assert original != changed
    assert changed['files'][str(platform_symbols.resolve())] == file_hash(platform_symbols)
    platform_symbols.unlink()
    assert launch_inputs(argv) is None


@pytest.mark.skipif(os.name != 'posix', reason='POSIX Java launcher alias')
def test_requested_java_alias_keeps_platform_and_locale_capture(java_launch, monkeypatch):
    argv, platform_symbols = java_launch
    launcher = Path(argv[0])
    executable = launcher.with_name('java-real')
    launcher.rename(executable)
    launcher.symlink_to(executable.name)
    monkeypatch.setenv('LC_ALL', 'C')
    captured = launch_inputs(argv)
    assert captured['argv'] == argv
    assert captured['files'][str(executable)] == file_hash(executable)
    assert captured['files'][str(platform_symbols)] == file_hash(platform_symbols)
    monkeypatch.setenv('LC_ALL', 'POSIX')
    assert launch_inputs(argv)['environment_sha256'] != captured['environment_sha256']


def test_unreadable_java_launcher_allows_live_inspection_without_cache(transport, java_launch, monkeypatch):
    root, _, _, _, calls, _ = transport
    argv, _ = java_launch
    monkeypatch.setattr(inspection, 'command', lambda *args, **kwargs: argv)

    def hash_readable(path):
        if path == Path(argv[0]).resolve():
            raise PermissionError('launcher bytes unavailable')
        return file_hash(path)

    monkeypatch.setattr(extraction_cache, 'file_hash', hash_readable)
    result = inspection.inspect_jvm(root)
    assert result['exit_code'] == 0
    assert calls == {'analyze': 1, 'graph': 1, 'framework': 1}
    assert {(stage['status'], stage['reason']) for stage in result['cache']['stages']} == {
        ('BYPASS', 'INCOMPLETE_INPUT_CLOSURE'),
    }
    assert not store.load_graph(root).extraction_cache


def test_public_inspect_cold_warm_reexecutes_all_stages(transport):
    root, _, _, _, calls, _ = transport
    cold = inspection.inspect_jvm(root)
    warm = inspection.inspect_jvm(root)
    assert calls == {'analyze': 2, 'graph': 2, 'framework': 2}
    assert facts(cold['graph']) == facts(warm['graph'])
    assert {s['status'] for s in warm['cache']['stages']} == {'BYPASS'}
    saved = store.load_graph(root)
    assert {s['reason'] for s in warm['cache']['stages']} == {'UNVERIFIED_REPLAY'}
    assert len(saved.extraction_cache['entries']) == 3
    assert all('extraction_cache' not in e['payload'] for e in saved.extraction_cache['entries'])


@pytest.mark.parametrize('mutation', ['worker', 'rule', 'config', 'classpath', 'source', 'variant'])
def test_real_input_change_misses_in_public_inspect(transport, monkeypatch, mutation):
    root, source, worker, _, calls, _ = transport
    dependency = worker.with_name('dependency.jar')
    dependency.write_bytes(b'classpath-v1')
    options = {'classpath': [str(dependency)], 'build_context': {'spring_profiles': ['a']}}
    inspection.inspect_jvm(root, **options)
    if mutation == 'worker': worker.write_bytes(b'worker-v2')
    elif mutation == 'classpath': dependency.write_bytes(b'classpath-v2')
    elif mutation == 'source': source.write_text('class Example { void changed() {} }\n')
    elif mutation == 'variant': options['build_context']['spring_profiles'] = ['b']
    elif mutation == 'config': options['build_context']['spring_properties'] = {'mode': 'changed'}
    else:
        import kgmaker.framework as framework
        monkeypatch.setattr(framework, 'SPRING_RULE_VERSION', 'changed-rule')
        # Existing provider refuses to merge a different selector while an old
        # rule context is stale. Verify cache invalidation read-only, preserving
        # that existing publication contract rather than weakening it here.
        options['publish'] = False
    inspection.inspect_jvm(root, **options)
    assert calls['analyze'] == 2


@pytest.mark.parametrize('mode', ['dry', 'strict-partial', 'cancel', 'timeout'])
def test_failure_and_read_only_modes_do_not_publish_cache_or_graph(transport, mode):
    root, _, _, _, _, behavior = transport
    inspection.inspect_jvm(root)
    before = snapshot(root)
    options = {'build_context': {'spring_profiles': ['new']}}
    if mode == 'dry': inspection.inspect_jvm(root, publish=False, **options)
    elif mode == 'strict-partial':
        behavior['status'] = 'PARTIAL'
        assert inspection.inspect_jvm(root, strict=True, **options)['exit_code'] == 4
    else:
        behavior['error'] = 'CANCELLED' if mode == 'cancel' else 'TIMED_OUT'
        with pytest.raises(WorkerError): inspection.inspect_jvm(root, **options)
    assert snapshot(root) == before


def test_generated_render_failure_leaves_entire_store_unchanged(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text('x = 1\n')
    store.save_graph(scan_repository(tmp_path), tmp_path)
    (tmp_path / 'main.py').write_text('x = 2\n')
    before = snapshot(tmp_path)
    def fail(*args, **kwargs): raise ValueError('render rejected')
    monkeypatch.setattr(store, 'render_markdown', fail)
    with pytest.raises(ValueError): store.save_graph(scan_repository(tmp_path), tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('version', [1, 2, 3])
def test_legacy_and_unknown_cache_metadata_do_not_change_graph_facts(tmp_path, version):
    graph = scan_repository(tmp_path).to_dict()
    graph['schema_version'] = version
    expected = KnowledgeGraph.from_dict(graph).to_dict()
    for cache in ({'schema_version': 999}, {'schema_version': 1, 'entries': ['broken']}):
        decoded = KnowledgeGraph.from_dict({**graph, 'extraction_cache': cache})
        assert decoded.extraction_cache == {}
        assert decoded.to_dict() == expected


@pytest.mark.parametrize('phase', range(4))
def test_each_precommit_guard_failure_restores_owned_outputs(tmp_path, phase):
    (tmp_path / 'main.py').write_text('x = 1\n')
    store.save_graph(scan_repository(tmp_path), tmp_path)
    (tmp_path / 'main.py').write_text('x = 2\n')
    before = snapshot(tmp_path)
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == phase + 1: raise RuntimeError('late guard rejection')
    with pytest.raises(RuntimeError):
        store.save_graph(scan_repository(tmp_path), tmp_path, before_replace=guard)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('phase', range(3))
def test_each_output_replace_failure_preserves_old_generation(tmp_path, monkeypatch, phase):
    (tmp_path / 'main.py').write_text('x = 1\n')
    store.save_graph(scan_repository(tmp_path), tmp_path)
    (tmp_path / 'main.py').write_text('x = 2\n')
    before = snapshot(tmp_path)
    replace = store.os.replace
    target = ('GRAPH.mmd', 'GRAPH.md', 'graph.json')[phase]
    failed = False
    def once(source, destination):
        nonlocal failed
        if Path(destination).name == target and not failed:
            failed = True
            raise OSError('injected publication failure')
        return replace(source, destination)
    monkeypatch.setattr(store.os, 'replace', once)
    with pytest.raises(OSError): store.save_graph(scan_repository(tmp_path), tmp_path)
    assert snapshot(tmp_path) == before


def test_abort_removes_own_empty_directories_without_deleting_concurrent_content(tmp_path):
    (tmp_path / 'main.py').write_text('x = 1\n')
    graph = scan_repository(tmp_path)
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == 2: raise RuntimeError('aborted')
    with pytest.raises(RuntimeError): store.save_graph(graph, tmp_path, before_replace=guard)
    assert not (tmp_path / '.kgmaker').exists()
    calls = 0
    def concurrent():
        nonlocal calls
        calls += 1
        if calls == 2:
            (tmp_path / '.kgmaker/concurrent').write_text('other writer')
            raise RuntimeError('aborted')
    with pytest.raises(RuntimeError): store.save_graph(graph, tmp_path, before_replace=concurrent)
    assert snapshot(tmp_path) == {'main.py': b'x = 1\n', '.kgmaker/concurrent': b'other writer'}


def test_rollback_does_not_overwrite_concurrently_replaced_generated_file(tmp_path):
    (tmp_path / 'main.py').write_text('x = 1\n')
    store.save_graph(scan_repository(tmp_path), tmp_path)
    old_index = (tmp_path / '.kgmaker/graph.json').read_bytes()
    (tmp_path / 'main.py').write_text('x = 2\n')
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == 3:
            (tmp_path / '.kgmaker/GRAPH.mmd').write_text('concurrent data')
            raise RuntimeError('stop after concurrent write')
    with pytest.raises(RuntimeError):
        store.save_graph(scan_repository(tmp_path), tmp_path, before_replace=guard)
    assert (tmp_path / '.kgmaker/GRAPH.mmd').read_text() == 'concurrent data'
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == old_index


@pytest.mark.parametrize('mutation', ['foreign-context', 'foreign-worker', 'foreign-scope', 'bad-hash', 'recursive'])
def test_hash_rewritten_foreign_or_corrupt_cache_is_rebuilt(transport, mutation):
    from kgmaker.analysis_model import digest
    root, _, _, _, calls, _ = transport
    inspection.inspect_jvm(root)
    path = root / '.kgmaker/graph.json'
    raw = json.loads(path.read_text())
    entry = raw['extraction_cache']['entries'][0]
    if mutation == 'foreign-context': entry['payload']['context_id'] = 'foreign-context'
    elif mutation == 'foreign-worker': entry['payload']['worker'] = 'other-worker'
    elif mutation == 'foreign-scope':
        entry = raw['extraction_cache']['entries'][1]
        context = next(c for c in entry['payload']['contexts'] if c.get('analyzer_version'))
        context['scope'] = 'test'
    elif mutation == 'recursive': entry['payload']['extraction_cache'] = {'schema_version': 1, 'entries': []}
    if mutation != 'bad-hash': entry['payload_sha256'] = digest(entry['payload'])
    else: entry['payload_sha256'] = '0' * 64
    path.write_text(json.dumps(raw))
    expected = facts(store.load_graph(root).to_dict())
    result = inspection.inspect_jvm(root)
    assert facts(result['graph']) == expected
    assert calls['graph' if mutation == 'foreign-scope' else 'analyze'] == 2



def test_rehashed_worker_payload_cannot_alter_live_coverage(transport):
    from kgmaker.analysis_model import digest

    root, _, _, _, calls, _ = transport
    original = inspection.inspect_jvm(root)
    path = root / ".kgmaker/graph.json"
    document = json.loads(path.read_text())
    entry = next(e for e in document["extraction_cache"]["entries"]
                 if e["key"]["stage"] == "worker-analysis")
    entry["payload"]["coverage"] = {"calls_resolved": 100}
    entry["payload_sha256"] = digest(entry["payload"])
    path.write_text(json.dumps(document))
    before = snapshot(root)
    result = inspection.inspect_jvm(root, publish=False)
    assert result["coverage"] == original["coverage"]
    assert calls["analyze"] == 2
    assert snapshot(root) == before


@pytest.mark.parametrize("stage", ["compiler-graph", "framework-graph"])
def test_rehashed_cached_graph_cannot_create_resolved_call(transport, stage):
    from dataclasses import asdict

    from kgmaker.analysis_model import digest
    from kgmaker.model import Edge

    root, source, _, _, calls, _ = transport
    source.write_text("class Example {\n void run() {}\n void other() {}\n}\n")
    original = inspection.inspect_jvm(root)
    path = root / ".kgmaker/graph.json"
    document = json.loads(path.read_text())
    entry = next(e for e in document["extraction_cache"]["entries"] if e["key"]["stage"] == stage)
    payload = entry["payload"]
    node_ids = {node["name"]: node["id"] for node in payload["nodes"]}
    context = original["context"]["id"]
    proof = "cache-only-proof"
    payload["evidence"].append({"id": proof, "kind": "SYMBOL_RESOLVED", "context_id": context})
    payload["edges"].append(asdict(Edge(
        source=node_ids["run"], target=node_ids["other"], kind="calls", confidence="resolved",
        context_ids=(context,), evidence_ids=(proof,), evidence_kind="SYMBOL_RESOLVED")))
    entry["payload_sha256"] = digest(payload)
    path.write_text(json.dumps(document))
    before = snapshot(root)
    result = inspection.inspect_jvm(root, publish=False)
    assert not any(proof in edge.get("evidence_ids", []) for edge in result["graph"]["edges"])
    assert facts(result["graph"]) == facts(original["graph"])
    assert calls == {"analyze": 2, "graph": 2, "framework": 2}
    assert snapshot(root) == before


def test_scope_variant_retention_and_offline_refresh_do_not_launch_worker(transport, monkeypatch):
    from kgmaker.graph_provider import retain_compiler_layer
    root, _, _, _, calls, _ = transport
    inspection.inspect_jvm(root, build_context={'spring_profiles': ['a']})
    inspection.inspect_jvm(root, build_context={'spring_profiles': ['b']})
    warm = inspection.inspect_jvm(root, build_context={'spring_profiles': ['a']})
    assert calls['analyze'] == 3
    assert len(store.load_graph(root).extraction_cache['entries']) == 6
    assert len([c for c in warm['graph']['contexts'] if c.get('analyzer_version')]) == 2
    def forbidden(*a, **kw): raise AssertionError('implicit worker')
    monkeypatch.setattr(inspection, 'request_worker', forbidden)
    replay = retain_compiler_layer(root, scan_repository(root))
    assert len(replay.extraction_cache['entries']) == 6
    assert facts(replay.to_dict()) == facts(warm['graph'])


def test_oversized_cache_bypasses_without_rejecting_valid_inspect(transport, monkeypatch):
    from kgmaker import extraction_cache
    root, _, _, _, calls, _ = transport
    monkeypatch.setattr(extraction_cache, 'MAX_BYTES', 100)
    result = inspection.inspect_jvm(root)
    assert result['exit_code'] == 0
    assert {s['reason'] for s in result['cache']['stages']} == {'CACHE_SIZE_LIMIT'}
    assert store.load_graph(root).extraction_cache == {}
    inspection.inspect_jvm(root)
    assert calls['analyze'] == 2


@pytest.mark.parametrize('bad_context', ['corrupt', None, [], 5, {'id': 'foreign'}])
def test_malformed_cache_key_is_ignored_by_public_provider(transport, bad_context):
    from kgmaker.analysis_model import digest
    from kgmaker.graph_provider import retain_compiler_layer
    root, _, _, _, _, _ = transport
    result = inspection.inspect_jvm(root)
    path = root / '.kgmaker/graph.json'
    raw = json.loads(path.read_text())
    entry = raw['extraction_cache']['entries'][0]
    entry['key']['context'] = bad_context
    entry['key_sha256'] = digest(entry['key'])
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    replay = retain_compiler_layer(root, scan_repository(root))
    comparable_graph = facts(replay.to_dict())
    assert comparable_graph == facts(result['graph'])
    assert replay.extraction_cache == {} and path.read_bytes() == before


def test_public_graph_serialization_cannot_expose_unselected_cache_payload(transport):
    from kgmaker.views import project
    root, _, _, _, _, _ = transport
    inspection.inspect_jvm(root)
    graph = store.load_graph(root)
    assert graph.extraction_cache
    assert 'extraction_cache' not in graph.to_dict()
    assert 'extraction_cache' not in project(graph, 'test').to_dict()
    assert KnowledgeGraph.from_dict(graph.to_dict(include_cache=True)).extraction_cache == graph.extraction_cache


@pytest.mark.parametrize('field,value', [('project', {'foreign': 'closure'}),
    ('coverage', {'calls_resolved': 999}), ('status', 'PARTIAL'),
    ('diagnostics', [{'code': 'FOREIGN_DIAGNOSTIC'}])])
def test_cached_graph_context_is_bound_to_validated_upstream_response(transport, field, value):
    from kgmaker.analysis_model import digest
    root, _, _, _, calls, _ = transport
    original = inspection.inspect_jvm(root)
    path = root / '.kgmaker/graph.json'
    raw = json.loads(path.read_text())
    for entry in raw['extraction_cache']['entries'][1:]:
        selected = next(c for c in entry['payload']['contexts'] if c.get('analyzer_version'))
        selected[field] = value
        entry['payload_sha256'] = digest(entry['payload'])
    path.write_text(json.dumps(raw))
    result = inspection.inspect_jvm(root)
    assert calls == {'analyze': 2, 'graph': 2, 'framework': 2}
    assert facts(result['graph']) == facts(original['graph'])


@pytest.mark.parametrize('mode', ['cancel', 'timeout'])
def test_warm_inspection_honors_abort_before_publication(transport, mode):
    root, _, _, _, calls, _ = transport
    inspection.inspect_jvm(root)
    options = {'timeout': 0} if mode == 'timeout' else {'cancel_file': root / '.cancel'}
    if mode == 'cancel': options['cancel_file'].touch()
    before = snapshot(root)
    with pytest.raises(WorkerError) as error: inspection.inspect_jvm(root, **options)
    assert error.value.status == ('TIMED_OUT' if mode == 'timeout' else 'CANCELLED')
    assert calls['analyze'] == 1 and snapshot(root) == before


def test_entry_count_cap_preserves_other_context_facts(transport):
    from kgmaker.extraction_cache import MAX_ENTRIES
    root, _, _, _, calls, _ = transport
    for variant in range(MAX_ENTRIES // 3 + 1):
        inspection.inspect_jvm(root, build_context={'spring_profiles': [str(variant)]})
    graph = store.load_graph(root)
    assert len(graph.extraction_cache['entries']) == MAX_ENTRIES
    assert len([c for c in graph.contexts if c.get('analyzer_version')]) == MAX_ENTRIES // 3 + 1
    warm = inspection.inspect_jvm(root, build_context={'spring_profiles': [str(MAX_ENTRIES // 3)]})
    assert {s['status'] for s in warm['cache']['stages']} == {'BYPASS'}
    assert calls['analyze'] == MAX_ENTRIES // 3 + 2


def test_late_source_mutation_during_store_preparation_does_not_publish(transport, monkeypatch):
    root, source, _, _, _, _ = transport
    inspection.inspect_jvm(root)
    before = snapshot(root / '.kgmaker')
    real = store.render_markdown
    def mutate(graph):
        source.write_text('class Example { void lateChange() {} }\n')
        return real(graph)
    monkeypatch.setattr(store, 'render_markdown', mutate)
    with pytest.raises(WorkerError) as error: inspection.inspect_jvm(root)
    assert error.value.status == 'STALE'
    assert snapshot(root / '.kgmaker') == before


def test_late_worker_inventory_addition_does_not_publish(transport, monkeypatch):
    root, _, worker, _, _, _ = transport
    inspection.inspect_jvm(root)
    before = snapshot(root / '.kgmaker')
    extra = worker.with_name('new-dependency.jar')
    real = store.render_markdown
    def mutate(graph):
        extra.write_bytes(b'new worker dependency')
        return real(graph)
    monkeypatch.setattr(store, 'render_markdown', mutate)
    monkeypatch.setattr(inspection, 'distribution', lambda *a, **kw: [
        {'path': str(path), 'sha256': file_hash(path)} for path in (worker, extra) if path.exists()])
    with pytest.raises(WorkerError) as error: inspection.inspect_jvm(root)
    assert error.value.status == 'STALE'
    assert snapshot(root / '.kgmaker') == before


def test_authoritative_commit_needs_no_post_replace_read(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text('x = 1\n')
    graph = scan_repository(tmp_path)
    replace, state = store.os.replace, store._file_state
    committed = False
    def commit(source, destination):
        nonlocal committed
        result = replace(source, destination)
        if Path(destination).name == 'graph.json': committed = True
        return result
    def unreadable_after_commit(path):
        if committed and Path(path).name == 'graph.json':
            raise OSError('read failed after authoritative commit')
        return state(path)
    monkeypatch.setattr(store.os, 'replace', commit)
    monkeypatch.setattr(store, '_file_state', unreadable_after_commit)
    store.save_graph(graph, tmp_path)
    assert store.load_graph(tmp_path).to_dict() == graph.to_dict()

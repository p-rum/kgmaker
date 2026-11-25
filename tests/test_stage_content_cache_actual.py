"""Real explicit worker cold/warm gates; no test installs or builds a worker."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import shutil
import zipfile

import pytest

from kgmaker import inspection, store
from kgmaker.analysis_model import file_hash
from kgmaker.store import load_graph
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).parents[1]


def ready(language, backend='k1'):
    try:
        inspection.command(language, ROOT / 'workers', kotlin_backend=backend)
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1': pytest.fail(str(error))
        pytest.skip(str(error))


def comparable(value):
    value = deepcopy(value)
    value.pop('extraction_cache', None)
    value.pop('generated_at', None)
    return value


@pytest.mark.skipif(os.name != 'posix', reason='POSIX Java locale capture')
@pytest.mark.parametrize('when', ['after-analyze', 'after-first-replace'])
def test_actual_jvm_locale_drift_preserves_published_generation(tmp_path, monkeypatch, when):
    ready('jvm')
    for name in ('_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'NODE_OPTIONS', 'CLASSPATH'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('JAVA_TOOL_OPTIONS', '-XX:-UsePerfData')
    monkeypatch.setenv('LC_ALL', 'C')
    root = tmp_path / 'project'
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Example { int run() { return Math.abs(-1); } }\n', encoding='utf-8')
    options = {'home': ROOT / 'workers', 'java_release': 17}
    cold = inspection.inspect_jvm(root, **options)
    assert cold['exit_code'] == 0 and not cold['diagnostics']
    assert any(site['resolution_reason'] == 'JAVAC_ATTRIBUTED_SYMBOL'
               for site in cold['graph']['call_sites'])
    assert {stage['reason'] for stage in cold['cache']['stages']} == {'UNVERIFIED_REPLAY'}

    def outputs():
        return {path.relative_to(root): path.read_bytes()
                for path in (root / '.kgmaker').rglob('*') if path.is_file()}

    before = outputs()
    changes = []
    if when == 'after-analyze':
        request = inspection.request_worker

        def change_after_analyze(argv, payload, **kwargs):
            response = request(argv, payload, **kwargs)
            assert payload['operation'] == 'analyze'
            assert response['status'] == 'COMPLETE'
            changes.append(when)
            monkeypatch.setenv('LC_ALL', 'POSIX')
            return response

        monkeypatch.setattr(inspection, 'request_worker', change_after_analyze)
    else:
        replace = store.os.replace

        def change_after_first_replace(source, target):
            replace(source, target)
            if Path(target) == root / store.MERMAID_FILE and not changes:
                changes.append(when)
                monkeypatch.setenv('LC_ALL', 'POSIX')

        monkeypatch.setattr(store.os, 'replace', change_after_first_replace)

    with pytest.raises(WorkerError, match='launcher changed') as error:
        inspection.inspect_jvm(root, **options)
    assert error.value.status == 'STALE'
    assert changes == [when]
    assert outputs() == before
    jdk = Path(inspection.command('jvm', options['home'])[0]).resolve().parent.parent
    platform_symbols = jdk / 'lib/ct.sym'
    worker_stage = load_graph(root).extraction_cache['entries'][0]
    assert worker_stage['key']['stage'] == 'worker-analysis'
    assert worker_stage['key']['launch']['files'][str(platform_symbols)] == file_hash(platform_symbols)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX Java launcher symlink')
@pytest.mark.parametrize('when', ['after-analyze', 'after-first-replace'])
def test_actual_jvm_cyclic_launcher_is_stale_and_preserves_generation(tmp_path, monkeypatch, when):
    ready('jvm')
    home = ROOT / 'workers'
    java = Path(inspection.command('jvm', home)[0]).resolve()
    alias = tmp_path / 'selected'
    alias.symlink_to(java.parent.parent / 'lib', target_is_directory=True)
    selected_bin = alias / '..' / 'bin'
    monkeypatch.setenv('PATH', str(selected_bin) + os.pathsep + os.environ['PATH'])
    for name in ('_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'NODE_OPTIONS', 'CLASSPATH'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('JAVA_TOOL_OPTIONS', '-XX:-UsePerfData')
    root = tmp_path / 'project'
    java_sources = root / 'src/main/java'
    source = java_sources / 'demo/Sample.java'
    source.parent.mkdir(parents=True)
    source.write_text('package demo; public class Sample { int value() { return Math.abs(-3); } }\n',
                      encoding='utf-8')
    options = {'home': home, 'java_release': 17}
    cold = inspection.inspect_jvm(root, **options)
    assert cold['exit_code'] == 0
    assert any(site['resolution_reason'] == 'JAVAC_ATTRIBUTED_SYMBOL'
               for site in cold['graph']['call_sites'])

    def outputs():
        return {path.relative_to(root): path.read_bytes()
                for path in (root / '.kgmaker').rglob('*') if path.is_file()}

    before = outputs()
    extra = java_sources / 'other/Additional.java'
    extra.parent.mkdir()
    extra.write_text('package other;\nimport demo.Sample;\npublic class Additional extends Sample {}\n',
                     encoding='utf-8')
    events = []

    def make_cycle():
        alias.unlink()
        alias.symlink_to(alias.name)
        events.append(when)

    request = inspection.request_worker

    def after_analyze(argv, payload, **kwargs):
        assert Path(argv[0]) == selected_bin / 'java'
        response = request(argv, payload, **kwargs)
        assert payload['operation'] == 'analyze' and response['status'] == 'COMPLETE'
        events.append('analyze')
        if when == 'after-analyze':
            make_cycle()
        return response

    monkeypatch.setattr(inspection, 'request_worker', after_analyze)
    if when == 'after-first-replace':
        replace = store.os.replace

        def after_replace(source, target):
            replace(source, target)
            if Path(target) == root / store.MERMAID_FILE and when not in events:
                updated = Path(target).read_bytes()
                assert updated != before[store.MERMAID_FILE] and b'Additional.java' in updated
                make_cycle()

        monkeypatch.setattr(store.os, 'replace', after_replace)

    with pytest.raises(WorkerError, match='launcher changed') as error:
        inspection.inspect_jvm(root, **options)
    assert error.value.status == 'STALE'
    assert events == ['analyze', when]
    assert outputs() == before


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_jvm_cold_warm_context_isolation_and_classpath_change(tmp_path, monkeypatch, backend):
    ready('jvm', backend)
    root = tmp_path / 'app'
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Example { int run() { return dep.Library.value(); } }\n')
    kotlin = source.with_name('ExampleKt.kt')
    kotlin.write_text('package app\nclass Counter { fun plus(value: Int): Int = value + 1 }\n')
    library = tmp_path / 'library-src/dep/Library.java'
    library.parent.mkdir(parents=True)
    library.write_text('package dep; public class Library { public static int value() { return 1; } }\n')
    classes = tmp_path / 'library-classes'
    classes.mkdir()
    subprocess.run(['javac', '-d', str(classes), str(library)], check=True, capture_output=True)
    home = ROOT / 'workers'
    stdlib = home / 'jvm' / ('target-k2' if backend == 'k2' else 'target') / 'lib/kotlin-stdlib.jar'
    calls = []
    request = inspection.request_worker
    def counted(argv, payload, **kwargs):
        calls.append(payload['operation'])
        return request(argv, payload, **kwargs)
    monkeypatch.setattr(inspection, 'request_worker', counted)
    validations = []
    validate = inspection._stage_graph

    def count_graph_validation(payload, base, selected, response):
        validations.append(selected['id'])
        return validate(payload, base, selected, response)

    monkeypatch.setattr(inspection, '_stage_graph', count_graph_validation)
    options = {'home': home, 'kotlin_backend': backend,
               'classpath': [str(classes), str(stdlib)], 'repo_id': 'actual-cache',
               'module': 'core', 'source_set': 'main'}
    cold = inspection.inspect_jvm(root, **options)
    warm = inspection.inspect_jvm(root, **options)
    assert calls == ['analyze'] * 2
    assert {s['status'] for s in warm['cache']['stages']} == {'BYPASS'}
    assert comparable(cold['graph']) == comparable(warm['graph'])
    assert any(s['path'].endswith('ExampleKt.kt') for s in warm['graph']['symbols'])
    assert warm['graph']['call_sites'] and warm['graph']['cfgs']
    library.write_text('package dep; public class Library { public static int value() { return 2; } }\n')
    subprocess.run(['javac', '-d', str(classes), str(library)], check=True, capture_output=True)
    changed = inspection.inspect_jvm(root, **options)
    assert calls == ['analyze'] * 3
    assert validations == [cold['context']['id']] * 4 + [changed['context']['id']] * 2
    assert {s['status'] for s in changed['cache']['stages']} == {'BYPASS'}
    assert changed['context']['id'] != cold['context']['id']
    assert len([c for c in load_graph(root).contexts if c.get('analyzer_version')]) == 1


def test_actual_typescript_preflight_and_analysis_run_on_every_explicit_inspection(tmp_path, monkeypatch):
    ready('typescript')
    root = tmp_path / 'frontend'
    (root / 'src').mkdir(parents=True)
    (root / 'src/main.ts').write_text('export function twice(x: number): number { return x * 2; }\nexport const result = twice(2);\n')
    config = root / 'tsconfig.json'
    config.write_text(json.dumps({'compilerOptions': {'strict': True}, 'files': ['src/main.ts']}))
    calls = []
    request = inspection.request_worker
    def counted(argv, payload, **kwargs):
        calls.append(payload['operation'])
        return request(argv, payload, **kwargs)
    monkeypatch.setattr(inspection, 'request_worker', counted)
    validations = []
    validate = inspection._stage_graph

    def count_graph_validation(payload, base, selected, response):
        validations.append(selected['id'])
        return validate(payload, base, selected, response)

    monkeypatch.setattr(inspection, '_stage_graph', count_graph_validation)
    options = {'home': ROOT / 'workers', 'repo_id': 'frontend', 'module': 'ui'}
    cold = inspection.inspect_frontend(root, **options)
    warm = inspection.inspect_frontend(root, **options)
    assert calls == ['project', 'analyze'] * 2
    assert {s['status'] for s in warm['cache']['stages']} == {'BYPASS'}
    assert comparable(cold['graph']) == comparable(warm['graph'])
    assert warm['graph']['call_sites'] and warm['graph']['cfgs']
    config.write_text(json.dumps({'compilerOptions': {'strict': False}, 'files': ['src/main.ts']}))
    changed = inspection.inspect_frontend(root, **options)
    assert calls == ['project', 'analyze'] * 3
    assert validations == [cold['context']['id'], warm['context']['id'], changed['context']['id']]
    assert {s['status'] for s in changed['cache']['stages']} == {'BYPASS'}
    assert len([c for c in load_graph(root).contexts if c.get('analyzer_version')]) == 1


def test_actual_worker_bytes_and_analyzer_rule_change_force_reanalysis(tmp_path, monkeypatch):
    ready('jvm')
    shared = ROOT / 'workers/jvm/target'
    original_hash = file_hash(shared / 'kgmaker-jvm-worker.jar')
    target = tmp_path / 'worker-home/jvm/target'
    target.mkdir(parents=True)
    jar = target / 'kgmaker-jvm-worker.jar'
    shutil.copy2(shared / jar.name, jar)
    (target / 'lib').symlink_to((shared / 'lib').resolve(), target_is_directory=True)
    root = tmp_path / 'project'
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Example { int run() { return twice(2); } int twice(int x) { return x * 2; } }\n')
    request = inspection.request_worker
    calls = []
    def counted(argv, payload, **kwargs):
        calls.append(payload['operation'])
        return request(argv, payload, **kwargs)
    monkeypatch.setattr(inspection, 'request_worker', counted)
    home = tmp_path / 'worker-home'
    inspection.inspect_jvm(root, home=home)
    assert {s['status'] for s in inspection.inspect_jvm(root, home=home)['cache']['stages']} == {'BYPASS'}
    assert calls == ['analyze'] * 2
    # This is a valid local copy of the real executable JAR with different
    # content. Never modify the shared worker artifact or rebuild it implicitly.
    with zipfile.ZipFile(jar, 'a') as archive:
        archive.comment = b'W01 explicit content identity mutation'
    changed = inspection.inspect_jvm(root, home=home)
    assert {s['status'] for s in changed['cache']['stages']} == {'BYPASS'}
    monkeypatch.setattr(inspection, 'VERSION', 'inspection-rule-change-for-fixture')
    changed_rule = inspection.inspect_jvm(root, home=home)
    assert {s['status'] for s in changed_rule['cache']['stages']} == {'BYPASS'}
    assert calls == ['analyze'] * 4
    assert changed_rule['graph']['call_sites']
    assert file_hash(shared / jar.name) == original_hash


def test_overlapping_real_workers_do_not_overwrite_newer_publication(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from kgmaker import graph_provider

    ready('jvm', 'k1')
    root = tmp_path / 'app'
    source = root / 'src/main/java/Example.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Example { int run() { return 1; } }\n')
    captured, release = Event(), Event()
    merge = graph_provider.merge_compiler_context

    def interleave(root, graph, selected):
        candidate = merge(root, graph, selected)
        if selected['module'] == 'first':
            captured.set()
            assert release.wait(50)
        return candidate

    monkeypatch.setattr(graph_provider, 'merge_compiler_context', interleave)
    options = {'home': ROOT / 'workers', 'kotlin_backend': 'k1'}
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(inspection.inspect_jvm, root, module='first', **options)
        try:
            assert captured.wait(50)
            second = inspection.inspect_jvm(root, module='second', **options)
            assert second['exit_code'] == 0
            saved = (root / store.GRAPH_FILE).read_bytes()
        finally:
            release.set()
        with pytest.raises(store.GraphPublicationConflict, match='Graph generation changed'):
            first.result(timeout=10)
    assert (root / store.GRAPH_FILE).read_bytes() == saved
    assert [c['module'] for c in load_graph(root).contexts if c.get('analyzer_version')] == ['second']

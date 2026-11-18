"""Real explicit worker cold/warm gates; no test installs or builds a worker."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import shutil
import zipfile

import pytest

from kgmaker import inspection
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
    options = {'home': home, 'kotlin_backend': backend,
               'classpath': [str(classes), str(stdlib)], 'repo_id': 'actual-cache',
               'module': 'core', 'source_set': 'main'}
    cold = inspection.inspect_jvm(root, **options)
    warm = inspection.inspect_jvm(root, **options)
    assert calls == ['analyze']
    assert {s['status'] for s in warm['cache']['stages']} == {'HIT'}
    assert comparable(cold['graph']) == comparable(warm['graph'])
    assert any(s['path'].endswith('ExampleKt.kt') for s in warm['graph']['symbols'])
    assert warm['graph']['call_sites'] and warm['graph']['cfgs']
    library.write_text('package dep; public class Library { public static int value() { return 2; } }\n')
    subprocess.run(['javac', '-d', str(classes), str(library)], check=True, capture_output=True)
    changed = inspection.inspect_jvm(root, **options)
    assert calls == ['analyze', 'analyze']
    assert {s['status'] for s in changed['cache']['stages']} == {'MISS'}
    assert changed['context']['id'] != cold['context']['id']
    assert len([c for c in load_graph(root).contexts if c.get('analyzer_version')]) == 1


def test_actual_typescript_preflight_stays_explicit_but_analysis_and_graph_are_cached(tmp_path, monkeypatch):
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
    options = {'home': ROOT / 'workers', 'repo_id': 'frontend', 'module': 'ui'}
    cold = inspection.inspect_frontend(root, **options)
    warm = inspection.inspect_frontend(root, **options)
    assert calls == ['project', 'analyze', 'project']
    assert {s['status'] for s in warm['cache']['stages']} == {'HIT'}
    assert comparable(cold['graph']) == comparable(warm['graph'])
    assert warm['graph']['call_sites'] and warm['graph']['cfgs']
    config.write_text(json.dumps({'compilerOptions': {'strict': False}, 'files': ['src/main.ts']}))
    changed = inspection.inspect_frontend(root, **options)
    assert calls == ['project', 'analyze', 'project', 'project', 'analyze']
    assert {s['status'] for s in changed['cache']['stages']} == {'MISS'}
    assert len([c for c in load_graph(root).contexts if c.get('analyzer_version')]) == 1


def test_actual_worker_bytes_and_analyzer_rule_change_force_reanalysis(tmp_path, monkeypatch):
    from kgmaker.analysis_model import file_hash
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
    assert {s['status'] for s in inspection.inspect_jvm(root, home=home)['cache']['stages']} == {'HIT'}
    assert calls == ['analyze']
    # This is a valid local copy of the real executable JAR with different
    # content. Never modify the shared worker artifact or rebuild it implicitly.
    with zipfile.ZipFile(jar, 'a') as archive:
        archive.comment = b'W01 explicit content identity mutation'
    changed = inspection.inspect_jvm(root, home=home)
    assert {s['status'] for s in changed['cache']['stages']} == {'MISS'}
    monkeypatch.setattr(inspection, 'VERSION', 'inspection-rule-change-for-fixture')
    changed_rule = inspection.inspect_jvm(root, home=home)
    assert {s['status'] for s in changed_rule['cache']['stages']} == {'MISS'}
    assert calls == ['analyze', 'analyze', 'analyze']
    assert changed_rule['graph']['call_sites']
    assert file_hash(shared / jar.name) == original_hash

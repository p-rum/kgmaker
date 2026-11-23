"""Real Javac checks for byte-bound capture and offline replay."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker import inspection
from kgmaker.analysis_model import write_json
from kgmaker.compiler_sources import jvm_raw_capture_id
from kgmaker.feature import current_graph
from kgmaker.flow import process
from kgmaker.graph_provider import validate_context_snapshot
from kgmaker.store import GRAPH_FILE, load_graph
from kgmaker.views import execution_authority_gaps, select_service_contexts
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import qualified, snapshot_workspace


TARGET = 'src/main/java/Api.java'
CALLER = 'src/main/java/Caller.java'
CASES = [
    ('class Api { static int value(int x) { int marker = 1; return x + marker; } }',
     'class Caller { static int invoke() { return Api.value(1); } }', True),
    ('class Api { static void value(int x) { int marker = 1; } }',
     'class Caller { static void invoke() { Api.value(1); } }', True),
    ('interface Api { int value(int x); }',
     'class Caller { static int invoke(Api api) { return api.value(1); } }', False),
]


@pytest.fixture
def worker_home():
    home = Path(os.environ.get('KGMAKER_WORKERS_HOME', Path(__file__).resolve().parents[1] / 'workers'))
    try:
        inspection.command('jvm', home)
    except WorkerError as error:
        if error.status != 'TOOLCHAIN_UNAVAILABLE' or os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            raise
        pytest.skip(str(error))
    return home


def write_sources(root, target, caller, ending, caller_ending=b'\n'):
    (root / TARGET).parent.mkdir(parents=True, exist_ok=True)
    (root / TARGET).write_bytes(target.encode() + ending)
    (root / CALLER).write_bytes(caller.encode() + caller_ending)


def capture(root, home, explicit_model=True):
    model = {'source_sets': [{'module': 'app', 'id': 'main', 'scope': 'production',
                              'files': [TARGET, CALLER]}]} if explicit_model else None
    return inspection.inspect_jvm(root, home=home, module='app', sources=[TARGET, CALLER], project_model=model)


@pytest.mark.parametrize('target,caller,concrete', CASES, ids=['return', 'void', 'abstract'])
@pytest.mark.parametrize('ending', [b'\n', b'\r\n'], ids=['lf', 'crlf'])
def test_javac_capture_preserves_raw_and_normalized_authority(tmp_path, worker_home, target, caller, concrete, ending):
    write_sources(tmp_path, target, caller, ending)
    result = capture(tmp_path, worker_home, explicit_model=concrete)
    assert result['exit_code'] == 0
    context = result['context']
    graph = load_graph(tmp_path)
    raw = hashlib.sha256(target.encode() + ending).hexdigest()
    normalized = hashlib.sha256(target.encode() + b'\n').hexdigest()
    assert graph.files[TARGET] == normalized and context['source_files'][TARGET] == raw
    assert context['normalized_source_files'] == ({TARGET: normalized} if ending == b'\r\n' else {})
    symbol, = [s for s in graph.symbols if s.get('path') == TARGET and s['name'] == 'value']
    assert symbol['sha256'] == raw and symbol['context_id'] == context['id']
    site, = [s for s in graph.call_sites if s.get('path') == CALLER and s.get('declared_target') == symbol['id']]
    assert site['evidence_kind'] == 'SYMBOL_RESOLVED'
    operations = [p for p in graph.evidence if p.get('relation') == 'local_computation'
                  and p.get('source_file') == TARGET and p.get('operation') == 'LOCAL_LITERAL_ASSIGNMENT']
    assert bool(operations) == concrete
    assert all(p['sha256'] == raw and p['context_ids'] == [context['id']] for p in operations)
    assert {row['status'] for row in result['cache']['stages']} == {'BYPASS'}
    before = (tmp_path / GRAPH_FILE).read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('offline replay spawned a process')):
        validate_context_snapshot(tmp_path, context)
        live, _, _ = current_graph(tmp_path)
    assert any(s['id'] == symbol['id'] for s in live.symbols)
    assert (tmp_path / GRAPH_FILE).read_bytes() == before


def test_process_flow_preserves_javac_cfg_edges_across_line_endings(tmp_path, worker_home):
    target, caller, _ = CASES[0]
    structures = []
    for ending in (b'\n', b'\r\n'):
        root = tmp_path / ('lf' if ending == b'\n' else 'crlf')
        write_sources(root, target.replace('{ static', '{' + ending.decode() + ' static'),
                      caller.replace('{ static', '{' + ending.decode() + ' static'), ending, caller_ending=ending)
        result = capture(root, worker_home)
        graph = load_graph(root)
        owner, = [s for s in graph.symbols if s.get('name') == 'invoke' and s.get('path') == CALLER]
        callee, = [s for s in graph.symbols if s.get('name') == 'value' and s.get('path') == TARGET]
        assert owner['context_id'] == callee['context_id'] == result['context']['id']
        before = (root / GRAPH_FILE).read_bytes()
        with patch('subprocess.Popen', side_effect=AssertionError('process flow spawned a worker')):
            report = process(graph, owner['id'])
        assert not report['boundaries']
        assert any(block.get('method') == callee['id'] for block in report['cfg']['blocks'])
        structures.append(([b['kind'] for b in report['cfg']['blocks']],
                           sorted(e['kind'] for e in report['cfg']['edges'])))
        if ending == b'\r\n':
            damaged = deepcopy(graph)
            cfg, = [row for row in damaged.cfgs if row['method'] == callee['id']]
            proof, = [p for p in damaged.evidence if p['id'] in cfg['evidence_ids']]
            proof['sha256'] = damaged.files[TARGET]
            assert process(damaged, owner['id'])['boundaries'][0]['reason'] == (
                'callee CFG owner/source proof mismatch or unavailable')
        assert (root / GRAPH_FILE).read_bytes() == before
    assert sorted(structures[0][0]) == sorted(structures[1][0])
    assert structures[0][1] == structures[1][1]


def test_eol_edit_and_tampered_raw_capture_require_explicit_refresh(tmp_path, worker_home, monkeypatch):
    target, caller, _ = CASES[0]
    write_sources(tmp_path, target, caller, b'\n')
    original = capture(tmp_path, worker_home)['context']
    graph_file = tmp_path / GRAPH_FILE
    first = graph_file.read_bytes()
    first_digest = load_graph(tmp_path).files[TARGET]
    legacy = deepcopy(original)
    legacy.pop('normalized_source_files')
    legacy['source_snapshot_version'] = 'selected-source-set-2'
    downgraded = {**legacy}
    downgraded.pop('source_capture_base')
    legacy['id'] = legacy.pop('source_capture_base')
    with patch('subprocess.Popen', side_effect=AssertionError('offline replay spawned a process')):
        validate_context_snapshot(tmp_path, legacy)
        with pytest.raises(WorkerError, match='JVM compiler input capture identity changed'):
            validate_context_snapshot(tmp_path, downgraded)
        (tmp_path / TARGET).write_bytes(target.encode() + b'\r\n')
        with pytest.raises(WorkerError, match='STALE_INDEX'):
            validate_context_snapshot(tmp_path, original)
        stale, _, _ = current_graph(tmp_path)
    assert stale.files[TARGET] == first_digest and not stale.symbols
    assert graph_file.read_bytes() == first

    refreshed = capture(tmp_path, worker_home)['context']
    graph = load_graph(tmp_path)
    assert [c['id'] for c in graph.contexts if c.get('analyzer_version')] == [refreshed['id']]
    assert refreshed['selection_key'] == original['selection_key']
    assert refreshed['id'] != original['id']
    fresh = graph_file.read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('offline replay spawned a process')):
        for field in ('source_files', 'normalized_source_files'):
            damaged = deepcopy(refreshed)
            damaged[field][TARGET] = '0' * 64
            with pytest.raises(WorkerError, match='STALE_INDEX'):
                validate_context_snapshot(tmp_path, damaged)

    request = inspection.request_worker
    def normalized_worker_symbol(*args, **kwargs):
        response = request(*args, **kwargs)
        for symbol in response['symbols']:
            if symbol.get('path') == TARGET:
                symbol['sha256'] = first_digest
        return response

    monkeypatch.setattr(inspection, 'request_worker', normalized_worker_symbol)
    with pytest.raises(WorkerError, match='Return proof source snapshot') as error:
        capture(tmp_path, worker_home)
    assert error.value.status == 'INVALID_PROTOCOL'
    assert graph_file.read_bytes() == fresh


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_selected_kotlin_coordinate_guard_preserves_mixed_jvm_scope(tmp_path, worker_home, backend):
    try:
        inspection.command('jvm', worker_home, kotlin_backend=backend)
    except WorkerError as error:
        if error.status != 'TOOLCHAIN_UNAVAILABLE' or any(os.environ.get(name) == '1' for name in (
                'KGMAKER_REQUIRE_WORKERS', 'KGMAKER_REQUIRE_K2')):
            raise
        pytest.skip(str(error))
    target, caller, _ = CASES[0]
    write_sources(tmp_path, target, caller, b'\r\n')
    kotlin = 'src/main/kotlin/Calls.kt'
    other = 'src/main/kotlin/Unused.kt'
    text = (b'package fixture\nprivate fun target(x: Int) = x\n'
            b'fun run(): Int {\n    val local = 1\n    return target(local)\n}\n')
    (tmp_path / kotlin).parent.mkdir(parents=True)
    (tmp_path / kotlin).write_bytes(text)
    (tmp_path / other).write_bytes(b'package fixture\r\nfun unused() = 0\r\n')
    selected = [TARGET, CALLER, kotlin]
    model = {'source_sets': [{'module': 'app', 'id': 'main', 'scope': 'production',
                              'files': [*selected, other]}]}
    worker_dir = 'target-k2' if backend == 'k2' else 'target'
    stdlib = worker_home / 'jvm' / worker_dir / 'lib' / 'kotlin-stdlib.jar'
    kwargs = {'home': worker_home, 'module': 'app', 'sources': selected,
              'kotlin_backend': backend, 'project_model': model, 'classpath': [str(stdlib)]}
    result = inspection.inspect_jvm(tmp_path, **kwargs)
    assert result['exit_code'] == 0
    context = result['context']
    graph = load_graph(tmp_path)
    assert set(context['normalized_source_files']) == {TARGET, other}
    assert set(context['compiler_inputs']) == set(selected)
    symbol_ids = {s['id']: s for s in graph.symbols}
    site, = [s for s in graph.call_sites if s.get('path') == kotlin
             and symbol_ids.get(s.get('declared_target'), {}).get('name') == 'target']
    assert text[site['range']['start']:site['range']['end']] == b'target(local)'

    store = tmp_path / GRAPH_FILE
    before = store.read_bytes()
    raw = text.replace(b'\n', b'\r\n')
    (tmp_path / kotlin).write_bytes(raw)
    with patch.object(inspection, 'request_worker', side_effect=AssertionError('invalid Kotlin input reached analyze')):
        with pytest.raises(WorkerError, match='Selected Kotlin source uses unsupported raw byte coordinates'):
            inspection.inspect_jvm(tmp_path, **kwargs)
    damaged = deepcopy(context)
    damaged['source_files'][kotlin] = hashlib.sha256(raw).hexdigest()
    damaged['normalized_source_files'][kotlin] = hashlib.sha256(text).hexdigest()
    with patch('subprocess.Popen', side_effect=AssertionError('offline replay spawned a process')):
        with pytest.raises(WorkerError, match='JVM compiler input capture identity changed'):
            validate_context_snapshot(tmp_path, damaged)
        for forged in ([TARGET, CALLER], [], ['src/test/java/Absent.java'],
                       [*selected, kotlin], list(reversed(selected)), ['../Outside.java'], [other]):
            with pytest.raises(WorkerError, match='JVM compiler input capture identity changed'):
                validate_context_snapshot(tmp_path, {**damaged, 'compiler_inputs': forged})
        with pytest.raises(WorkerError, match='selected Kotlin source uses unsupported raw byte coordinates'):
            validate_context_snapshot(tmp_path, {**damaged, 'id': jvm_raw_capture_id(damaged)})
        forged_graph = graph.to_dict()
        forged_graph['contexts'] = [{**row, **damaged, 'compiler_inputs': [TARGET, CALLER]}
                                    if row['id'] == context['id'] else row for row in forged_graph['contexts']]
        write_json(store, forged_graph)
        forged_bytes = store.read_bytes()
        live, _, _ = current_graph(tmp_path)
        assert not any(s.get('path') == kotlin for s in live.call_sites)
        assert store.read_bytes() == forged_bytes
        store.write_bytes(before)
    assert store.read_bytes() == before


def test_workspace_qualified_jvm_snapshot_validates_both_hashes(tmp_path, worker_home):
    root = tmp_path / 'backend'
    target, caller, _ = CASES[0]
    write_sources(root, target, caller, b'\r\n')
    result = capture(root, worker_home)
    context_id = qualified('local', result['context']['id'])
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, {'schema_version': 1, 'workspace_id': 'byte-capture', 'repositories': [
        {'id': 'local', 'role': 'backend', 'path': 'backend'}]})
    before = (root / GRAPH_FILE).read_bytes()
    launch = subprocess.Popen

    def allow_git(argv, *args, **kwargs):
        assert argv[0] == 'git', 'offline workspace launched a compiler or build'
        return launch(argv, *args, **kwargs)

    with patch('subprocess.Popen', allow_git):
        _, _, _, graph, _ = snapshot_workspace(manifest)
        selected = select_service_contexts(graph, [{'service_id': 'app', 'repo_id': 'local', 'module': 'app'}],
                                           scope='production', repo_roots={'local': root})
    assert selected['context_selection']['app']['context_id'] == context_id
    assert selected['services'][0]['status'] == 'CURRENT'
    context, = [c for c in graph.contexts if c.get('id') == context_id]
    target_key = '@local/' + TARGET
    assert context['compiler_inputs'] == ['@local/' + path for path in result['context']['compiler_inputs']]
    assert graph.files[target_key] == context['source_files'][target_key]
    assert graph.files[target_key] != context['normalized_source_files'][target_key]
    symbol_ids = {s['id']: s for s in graph.symbols}
    site, = [s for s in graph.call_sites if s.get('path') == '@local/' + CALLER
             and symbol_ids.get(s.get('declared_target'), {}).get('name') == 'value']
    proofs = {p['id']: p for p in graph.evidence}
    assert not execution_authority_gaps({context_id: context}, graph.files, proofs,
                                        [context_id], site['evidence_ids'], site)
    assert (root / GRAPH_FILE).read_bytes() == before

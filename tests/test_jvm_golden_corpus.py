"""Hand-labelled inventory acceptance; no expected result is generated from workers."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/jvm-golden'


def test_corpus_declares_all_scenarios_and_backend_boundaries():
    corpus = json.loads((FIXTURE / 'expected.json').read_text(encoding='utf-8'))
    assert corpus['schema_version'] == 1
    assert set(corpus['requirements']) == {'T002-CG-01', 'T002-CG-02', 'T002-CG-03', 'T002-CG-04', 'T002-CG-05'}
    assert set(corpus['backends']) == {'k1', 'k2'}
    assert all(corpus['backends'][backend]['compiler'] == '2.1.10' for backend in corpus['backends'])
    assert {case['id'] for case in corpus['cases']} == {'mixed', 'java', 'kotlin', 'features', 'dispatch'}
    assert any(row['status'] == 'UNRESOLVED' for case in corpus['cases'] for row in case.get('sites', []))
    assert any(case['unsupported']['k2'] for case in corpus['cases'])

import copy
from collections import Counter
import hashlib
import os
import shutil
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.callgraph import adjacency
from kgmaker.flow import process as process_trace
from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.graph_provider import retain_compiler_layer
from kgmaker.store import save_graph
from kgmaker.scanner import scan_repository
from kgmaker.worker_protocol import WorkerError
from test_control_flow import reachable
from test_dependency_dispatch import real_dispatch

WORKERS = ROOT / 'workers'
CORPUS = json.loads((FIXTURE / 'expected.json').read_text(encoding='utf-8'))
PARAMS = [(case, backend) for case in CORPUS['cases'] for backend in CORPUS['backends']]
REALM = dict(repo_id='golden', module='core', source_set='main', scope='production')


def digest_files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def fixture_file(root, name, relative):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((FIXTURE / name).read_bytes())
    return target


def build_fixture(root, case):
    stdlib = WORKERS / 'jvm/target/lib/kotlin-stdlib.jar'
    classpath = [str(stdlib)]
    if case['id'] == 'mixed':
        source = ROOT / 'fixtures/build-inspection/maven'
        if not (source / 'target/classes/fixture/Worker.class').is_file():
            raise WorkerError('Actual prepared mixed Maven fixture required', 'TOOLCHAIN_UNAVAILABLE')
        shutil.copytree(source, root, ignore=shutil.ignore_patterns('.kgmaker'))
        classpath.insert(0, {'path': str(root / 'target/classes'), 'realm': REALM})
    elif case['id'] == 'dispatch':
        return real_dispatch.__wrapped__(root)[:2]
    else:
        root.mkdir()
        if case['id'] == 'java':
            fixture_file(root, 'GoldenCalls.java', 'src/main/java/golden/GoldenCalls.java')
            fixture_file(root, 'Broken.java', 'src/main/java/golden/Broken.java')
        elif case['id'] == 'kotlin':
            helper = fixture_file(root, 'Helper.java', 'src/main/java/fixture/Helper.java')
            fixture_file(root, 'Work.kt', 'src/main/kotlin/fixture/Work.kt')
            classes = root / 'classes'
            classes.mkdir()
            subprocess.run([shutil.which('javac'), '--release', '21', '-d', str(classes), str(helper)],
                           check=True, capture_output=True)
            classpath.insert(0, {'path': str(classes), 'realm': REALM})
        elif case['id'] == 'features':
            source = fixture_file(root, 'KotlinFeatures.kt', 'src/main/kotlin/golden/KotlinFeatures.kt')
            fixture_file(root, 'JavaCaller.java', 'src/main/java/golden/JavaCaller.java')
            classes = root / 'classes'
            classes.mkdir()
            subprocess.run([shutil.which('kotlinc'), str(source), '-jvm-target', '21', '-d', str(classes)],
                           check=True, capture_output=True)
            classpath.insert(0, {'path': str(classes), 'realm': REALM})
    return root, classpath


@pytest.fixture(scope='module', params=PARAMS, ids=[case['id'] + '-' + backend for case, backend in PARAMS])
def actual_case(request, tmp_path_factory):
    case, backend = request.param
    try:
        command('jvm', WORKERS, kotlin_backend=backend)
        if not shutil.which('javac') or not shutil.which('kotlinc'):
            raise WorkerError('Actual pinned JDK21/Kotlin2.1.10 tools required', 'TOOLCHAIN_UNAVAILABLE')
        parent = tmp_path_factory.mktemp('golden-' + case['id'] + '-' + backend)
        root, classpath = build_fixture(parent / 'project', case)
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or os.environ.get('KGMAKER_REQUIRE_K2') == '1':
            pytest.fail(str(error))
        pytest.skip(str(error))
    store = root / '.kgmaker/graph.json'
    store.parent.mkdir(exist_ok=True)
    with patch('subprocess.Popen', side_effect=AssertionError('Implicit source-only process')):
        baseline = scan_repository(root)
    store.write_text(json.dumps(baseline.to_dict()), encoding='utf-8')
    before = digest_files(root)
    result = inspect_jvm(root, home=WORKERS, kotlin_backend=backend, classpath=classpath,
                         publish=False, **REALM)
    assert digest_files(root) == before, 'Compiler corpus inspection mutated source/class/store bytes'
    graph = KnowledgeGraph.from_dict(result['graph'])
    save_graph(graph, root)  # Explicit fixture publication, never an implicit inspection write.
    published = store.read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('Implicit offline process')):
        retained = retain_compiler_layer(root, scan_repository(root))
    assert {site['id'] for site in retained.call_sites} == {site['id'] for site in graph.call_sites}
    assert store.read_bytes() == published
    return case, backend, root, graph, result


def signature(identity):
    return identity.split(':method:', 1)[1]


def caller_identity(site, symbols):
    caller = symbols[site['caller']]
    if caller.get('name') == '<lambda>':
        assert caller['identity_stability'] == 'SNAPSHOT'
        return '<lambda>@' + caller['path'] + ':' + str(caller['range']['start_line'])
    return signature(site['caller'])


def normalize_sites(root, graph):
    symbols = {item['id']: item for item in graph.symbols}
    result = []
    for site in graph.call_sites:
        assert not site['caller'].startswith('bytecode:'), 'Corpus selected SOURCE only'
        path, span = site.get('path'), site.get('range')
        assert path and span and span['start'] >= 0, 'No manufactured or absent source locator'
        text = (root / path).read_bytes().decode('utf-8')
        assert site['sha256'] == hashlib.sha256((root / path).read_bytes()).hexdigest()
        assert site['context_id'] in {item['id'] for item in graph.contexts if item.get('language') == 'jvm'}
        if site.get('declared_target'):
            assert site['evidence_kind'] == 'SYMBOL_RESOLVED'
        else:
            assert site['evidence_kind'] == 'UNRESOLVED' and not site.get('dispatch_candidates')
        result.append(dict(path=path, line=span['start_line'], text=text[span['start']:span['end']],
                           caller=caller_identity(site, symbols),
                           target=signature(site['declared_target']) if site.get('declared_target') else None,
                           status='RESOLVED' if site.get('declared_target') else 'UNRESOLVED',
                           invocation=site['invocation_kind'], reason=site['resolution_reason'], site=site, symbols=symbols))
    return result


def assert_inventory(case, backend, actual):
    counts = Counter(row['status'] for row in actual)
    assert {key: counts[key] for key in ['RESOLVED', 'UNRESOLVED']} == case['counts'][backend]
    if 'reference_inventory' in case:
        expected = [{**row, 'status': 'RESOLVED'} for row in
                    json.loads((ROOT / case['reference_inventory']).read_text(encoding='utf-8'))['jvm_calls']]
    else:
        expected = [{**row, **row.get(backend, {})} for row in case['sites']]
    keys = lambda row: (row['path'], row['line'], row['text'], row['caller'])
    assert Counter(map(keys, actual)) == Counter(map(keys, expected)), 'Extra, missing or relocated call-site identity'
    for row in expected:
        matches = [value for value in actual if keys(value) == keys(row)]
        assert len(matches) == 1, 'Ambiguous corpus annotation requires an explicit additional locator'
        value = matches[0]
        for field in ['target', 'status', 'invocation', 'reason', 'async_boundary']:
            if field in row:
                observed = value['site'].get(field) if field == 'async_boundary' else value[field]
                assert observed == row[field], (keys(row), field)
        if 'target_assertions' in row:
            target = value['site'].get('declared_target')
            assert target
            metadata = value['symbols'][target]
            for field, expected_value in row['target_assertions'].items():
                assert metadata.get(field) == expected_value
        if 'target_repo' in row:
            assert value['site']['declared_target'].startswith('jvm:' + row['target_repo'] + ':lib:main:')
        if 'candidates' in row:
            candidates = [candidate.split(':')[1] + ':' + signature(candidate) for candidate in value['site']['dispatch_candidates']]
            assert sorted(candidates) == sorted(row['candidates'])
            assert value['site']['dispatch_complete'] is False


def test_actual_inventory_and_unsupported_identity_match_hand_annotations(actual_case):
    case, backend, root, graph, result = actual_case
    actual = normalize_sites(root, graph)
    assert_inventory(case, backend, actual)
    expected_backend = CORPUS['backends'][backend]
    assert result['context']['worker']['kotlin_backend'] == expected_backend['frontend']
    assert result['context']['kotlin_version'] == expected_backend['compiler']
    unsupported = []
    for diagnostic in graph.diagnostics:
        if 'UNSUPPORTED' not in diagnostic.get('code', '') and diagnostic.get('code') != 'K2_SOURCE_MODEL_PARTIAL':
            continue
        row = dict(code=diagnostic['code'], path=diagnostic.get('path', diagnostic.get('source_file')),
                   line=(diagnostic.get('range') or diagnostic.get('source_range') or {}).get('start_line'))
        if diagnostic['code'] == 'DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED':
            detail = diagnostic.get('reason', diagnostic.get('message', ''))
            entries = [entry for entry in result['context']['classpath'] if detail.startswith(entry['path'] + ':')]
            assert len(entries) == 1, 'Unsupported archive diagnostic must bind its captured classpath identity'
            row['artifact_sha256'] = entries[0]['sha256']
        unsupported.append(row)
    assert Counter(tuple(sorted(row.items())) for row in unsupported) == Counter(
        tuple(sorted(row.items())) for row in case['unsupported'][backend])
    if 'kotlin_cfgs' in case:
        symbols = {item['id']: item for item in graph.symbols}
        kotlin_cfgs = [cfg for cfg in graph.cfgs if symbols[cfg['method']].get('path', '').endswith('.kt')]
        assert len(kotlin_cfgs) == case['kotlin_cfgs'][backend]
    assert KnowledgeGraph.from_dict(graph.to_dict()).call_sites == graph.call_sites
    references = [row['site'] for row in actual if row['invocation'] == 'METHOD_REFERENCE']
    executable = adjacency(graph, include_candidates=False)
    assert all(not any(edge['call_site'] == site['id'] for edges in executable.values() for edge in edges) for site in references)
    if case['id'] == 'java':
        assert result['status'] == 'PARTIAL'
        boundaries = [d for d in graph.diagnostics if d['code'] == 'DYNAMIC_REFLECTION_BOUNDARY']
        assert len(boundaries) == case['dynamic_boundaries']
        dynamic = [row for row in actual if '.dynamic(' in row['caller']]
        assert all(row['target'].startswith('java.') for row in dynamic), 'Reflection must not invent a runtime target'
        choose = next(cfg for cfg in graph.cfgs if '.choose(Z)' in cfg['method'])
        branches = [row['site']['id'] for row in actual if '.choose(Z)' in row['caller']]
        blocks = [block['id'] for block in choose['blocks'] if block['kind'] == 'call' and any(site in block['call_site_ids'] for site in branches)]
        assert len(blocks) == 2 and not reachable(choose, blocks[0], blocks[1]) and not reachable(choose, blocks[1], blocks[0])
        recursive = next(item['id'] for item in graph.symbols if item.get('owner') == 'golden.GoldenCalls' and item.get('name') == 'recurse')
        report = process_trace(graph, recursive, max_depth=3, max_nodes=200)
        assert any(boundary['reason'] == 'recursive call' for boundary in report['boundaries'])
    if case['id'] == 'features':
        symbols = {item['name']: item for item in graph.symbols if item.get('owner') == 'golden.KotlinFeaturesKt'}
        assert symbols['decorate']['default_arguments'] == [True]
        assert symbols['inlineTarget']['inline'] is True
        assert symbols['suspendCaller']['suspend'] is True


def test_inventory_rejects_missing_extra_retargeted_and_stronger_observations(actual_case):
    case, backend, root, graph, _ = actual_case
    actual = normalize_sites(root, graph)
    assert actual
    with pytest.raises(AssertionError):
        assert_inventory(case, backend, actual[1:])
    with pytest.raises(AssertionError):
        assert_inventory(case, backend, [*actual, copy.deepcopy(actual[0])])
    retargeted = copy.deepcopy(actual)
    next(row for row in retargeted if row['status'] == 'RESOLVED')['target'] = 'wrong.Owner.same()V'
    with pytest.raises(AssertionError):
        assert_inventory(case, backend, retargeted)
    if any(row['status'] == 'UNRESOLVED' for row in actual):
        stronger = copy.deepcopy(actual)
        row = next(row for row in stronger if row['status'] == 'UNRESOLVED')
        row.update(status='RESOLVED', target='wrong.Invented.target()V')
        with pytest.raises(AssertionError):
            assert_inventory(case, backend, stronger)

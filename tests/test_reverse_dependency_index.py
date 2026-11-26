from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from kgmaker import feature, inspection, store, workspace
from kgmaker.analysis_model import AnalysisError, digest, inventory_candidate, read_json, write_json
from kgmaker.callgraph import callees
from kgmaker.cli import main, scan
from kgmaker.graph_provider import dependency_impact, validate_context_snapshot
from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.store import GRAPH_FILE, save_graph
from kgmaker.worker_protocol import WorkerError


def _write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _store_bytes(root):
    return {path.relative_to(root): path.read_bytes()
            for path in (root / ".kgmaker").rglob("*") if path.is_file()}


def _require_javac_worker():
    try:
        command("jvm")
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            raise
        pytest.skip(str(error))


def _native_jvm_peer_fixture(root, backend, *, overlap=False, edit_peer=True, control_class=False):
    try:
        argv = command('jvm', kotlin_backend=backend)
        stdlib = Path(argv[-1]).parent / 'lib' / 'kotlin-stdlib.jar'
        if not stdlib.is_file():
            raise WorkerError('Matching Kotlin stdlib unavailable', 'TOOLCHAIN_UNAVAILABLE')
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (
                backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1'):
            raise
        pytest.skip(str(error))
    peers = {}
    for module in ('edited', 'selected', 'control'):
        peers[module] = _write(root, f'{module}/src/main/kotlin/Example.kt',
                                f'package {module}\nfun target(value: Int): Int = value\n'
                                'fun run(value: Int): Int = target(value)\n')
    java = _write(root, 'edited/src/main/java/Witness.java', 'package edited;\nclass Witness {}\n')
    extra = {'edited': [java.relative_to(root).as_posix()]}
    if overlap:
        extra['selected'] = extra['edited']
    if control_class:
        path = 'control/src/main/java/Independent.java'
        _write(root, path, 'package control;\nclass Independent {}\n')
        extra['control'] = [path]
    model = {'source_sets': [
        {'module': module, 'id': 'main', 'scope': 'production',
         'files': [file.relative_to(root).as_posix(), *extra.get(module, [])]}
        for module, file in peers.items()]}
    options = {'repo_id': 'peers', 'project_model': model, 'kotlin_backend': backend,
               'classpath': [str(stdlib)]}
    for module in peers:
        assert inspect_jvm(root, module=module, **options)['exit_code'] == 0
    initial = store.load_graph(root)
    if edit_peer:
        _write(root, peers['edited'], 'package edited\nfun target(value: Boolean): Int = if (value) 1 else 0\n'
               'fun run(value: Int): Int = target(value)\n')
    _write(root, peers['selected'], 'package selected\nfun replacement(value: Int): Int = value\n'
           'fun run(value: Int): Int = replacement(value)\n')
    return options, peers, java, initial


def _compiler_layer(graph, context_id):
    def in_scope(items):
        return [item for item in items if item.get('context_id') == context_id]

    return ([context for context in graph.contexts if context.get('id') == context_id],
            in_scope(graph.symbols), in_scope(graph.call_sites), in_scope(graph.cfgs),
            [edge for edge in graph.edges if context_id in edge.context_ids],
            [item for item in graph.evidence if context_id in item.get('context_ids', [])])


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_jvm_isolated_stale_peer_publication_and_guards(tmp_path, backend):
    options, peers, java, initial = _native_jvm_peer_fixture(tmp_path, backend)
    ids = {context['module']: context['id'] for context in initial.contexts
           if context.get('analyzer_version')}
    edited, selected, control = (ids[key] for key in ('edited', 'selected', 'control'))
    diagram = tmp_path / store.MERMAID_FILE
    diagram.write_bytes(diagram.read_bytes() + b'%% previous output rollback witness\n')
    previous = _store_bytes(tmp_path)
    request = inspection.request_worker

    def selected_drifts(*args, **kwargs):
        response = request(*args, **kwargs)
        assert response['coverage']['calls_resolved'] == 1
        peers['selected'].write_bytes(peers['selected'].read_bytes() + b'// changed after analyze\n')
        return response

    selected_bytes = peers['selected'].read_bytes()
    with patch.object(inspection, 'request_worker', selected_drifts), \
            pytest.raises(WorkerError, match='snapshot changed') as error:
        inspect_jvm(tmp_path, module='selected', **options)
    assert error.value.status == 'STALE' and _store_bytes(tmp_path) == previous
    peers['selected'].write_bytes(selected_bytes)

    changed_classpath = next(context for context in initial.contexts if context.get('id') == edited)
    dependency = changed_classpath['classpath'][0]
    unbound = tmp_path / 'unbound-library.jar'
    unbound.write_bytes(Path(dependency['path']).read_bytes())
    for key, value in [('sha256', '0' * 64), ('path', str(unbound))]:
        original = dependency[key]
        dependency[key] = value
        store.save_graph(initial, tmp_path)
        tampered = _store_bytes(tmp_path)
        with pytest.raises(WorkerError, match='source/config inputs changed') as error:
            inspect_jvm(tmp_path, module='selected', **options)
        assert error.value.status == 'STALE' and _store_bytes(tmp_path) == tampered
        dependency[key] = original

    old_site = next(site for site in initial.call_sites if site['context_id'] == edited)
    target = next(node.id for node in initial.nodes if node.kind == 'file' and node.path == old_site['path'])
    initial.analysis_annotations.append({'id': 'annotation:shared', 'origin': 'LLM_ANNOTATION',
                                         'target_ids': [target], 'evidence_ids': old_site['evidence_ids']})
    store.save_graph(initial, tmp_path)
    with_annotation = _store_bytes(tmp_path)
    with pytest.raises(WorkerError, match='source/config inputs changed') as error:
        inspect_jvm(tmp_path, module='selected', **options)
    assert error.value.status == 'STALE' and _store_bytes(tmp_path) == with_annotation
    initial.analysis_annotations.clear()
    for path, data in previous.items():
        (tmp_path / path).write_bytes(data)

    replace = store.os.replace
    java_bytes = java.read_bytes()
    replaced = []

    def peer_drifts_after_first_replace(source, destination):
        replace(source, destination)
        if destination == tmp_path / store.MERMAID_FILE and not replaced:
            replaced.append(destination)
            assert destination.read_bytes() != previous[store.MERMAID_FILE]
            java.write_bytes(java_bytes.replace(b'\n', b'\r\n'))

    with patch.object(store.os, 'replace', peer_drifts_after_first_replace), \
            pytest.raises(WorkerError, match='source-stage inputs changed before commit') as error:
        inspect_jvm(tmp_path, module='selected', **options)
    assert error.value.status == 'STALE' and len(replaced) == 1
    assert _store_bytes(tmp_path) == previous
    java.write_bytes(java_bytes)

    result = inspect_jvm(tmp_path, module='selected', **options)
    graph = store.load_graph(tmp_path)
    stale, symbols, calls, cfgs, edges, evidence = _compiler_layer(graph, edited)
    assert stale[0]['freshness'] == 'STALE' and 'source/config inputs changed' in stale[0]['stale_reason']
    assert not any((symbols, calls, cfgs, edges, evidence))
    assert not _compiler_layer(graph, selected)[0]
    assert _compiler_layer(graph, control) == _compiler_layer(initial, control)
    assert graph.to_dict() == result['graph']
    new_id = result['context']['id']
    new_site, = [site for site in graph.call_sites if site['context_id'] == new_id]
    new_target = next(symbol for symbol in graph.symbols if symbol['id'] == new_site['declared_target'])
    assert new_target['name'] == 'replacement' and new_target.get('logical_key')
    assert new_site['sha256'] == hashlib.sha256(selected_bytes).hexdigest()
    assert not any(entry['key']['context']['id'] == edited
                   for entry in graph.extraction_cache.get('entries', []))


def test_actual_jvm_overlapping_stale_peer_still_aborts(tmp_path):
    options, _, _, _ = _native_jvm_peer_fixture(tmp_path, 'k1', overlap=True)
    previous = _store_bytes(tmp_path)
    with pytest.raises(WorkerError, match='source/config inputs changed') as error:
        inspect_jvm(tmp_path, module='selected', **options)
    assert error.value.status == 'STALE' and _store_bytes(tmp_path) == previous


def test_actual_jvm_stale_peer_requires_unambiguous_runtime_proof_owner(tmp_path):
    options, _, _, initial = _native_jvm_peer_fixture(tmp_path, 'k1')
    ids = {context['module']: context['id'] for context in initial.contexts
           if context.get('analyzer_version')}
    peer, control = ids['edited'], ids['control']
    site = next(item for item in initial.call_sites if item['context_id'] == control)
    request = inspection.request_worker
    resolutions = []

    def resolved_selected(*args, **kwargs):
        response = request(*args, **kwargs)
        resolutions.append(response['coverage']['calls_resolved'])
        return response

    # Use the runtime importer's stored evidence shape over real compiler nodes.
    # The capture is intentionally unbound and has no runtime execution receipt.
    cases = [({'context_id': peer}, False, False),
             ({'context_id': control, 'context_ids': None}, False, False),
             ({'context_id': control, 'context_ids': [peer]}, False, False),
             ({'context_id': control}, True, False),
             ({'context_id': control}, False, True)]
    for fields, peer_endpoint, allowed in cases:
        nodes, target = initial.nodes, site['declared_target']
        if peer_endpoint:
            node = Node('runtime:stored-endpoint', 'method', 'stored endpoint', '<runtime>',
                        scope='production', metadata={'context_id': peer})
            nodes, target = [*nodes, node], node.id
        record = {'kind': 'RUNTIME_OBSERVED', 'source': site['caller'], 'target': target,
                  'relation': 'observed_dispatch_to', 'runtime_id': 'scope-fixture',
                  'build_id': 'synthetic-build', 'scenario': '', 'async': False,
                  'observation_source': None, **fields}
        proof = {'id': 'evidence:' + digest(record), **record}
        edge = Edge(record['source'], record['target'], record['relation'], evidence_kind='RUNTIME_OBSERVED',
                    context_ids=(control,), evidence_ids=(proof['id'],))
        stored = replace(initial, nodes=nodes, evidence=[*initial.evidence, proof], edges=[*initial.edges, edge])
        store.save_graph(stored, tmp_path, generate_docs=False)
        previous = _store_bytes(tmp_path)
        with patch.object(inspection, 'request_worker', resolved_selected):
            if allowed:
                assert inspect_jvm(tmp_path, module='selected', **options)['exit_code'] == 0
                after = store.load_graph(tmp_path)
                assert proof in after.evidence and edge in after.edges
                assert _compiler_layer(after, peer)[0][0]['freshness'] == 'STALE'
                assert any(row['kind'] == 'RUNTIME_OBSERVED' and row['evidence_ids'] == [proof['id']]
                           for row in callees(after, site['caller'])['results'])
            else:
                with pytest.raises(WorkerError, match='source/config inputs changed') as error:
                    inspect_jvm(tmp_path, module='selected', **options)
                assert error.value.status == 'STALE' and _store_bytes(tmp_path) == previous
    assert resolutions == [1] * len(cases)


def test_actual_jvm_stale_peer_checks_cfg_and_typed_proof_references(tmp_path):
    options, _, _, initial = _native_jvm_peer_fixture(tmp_path, 'k1', control_class=True)
    captures = {context['module']: context['id'] for context in initial.contexts
                if context.get('analyzer_version')}
    peer, control = captures['edited'], captures['control']
    peer_site = next(item for item in initial.call_sites if item['context_id'] == peer)
    control_site = next(item for item in initial.call_sites if item['context_id'] == control)
    classes = {symbol['context_id']: symbol for symbol in initial.symbols
               if symbol['kind'] == 'class' and str(symbol.get('path', '')).endswith('.java')}

    def compiler_source(context_id):
        symbol = classes[context_id]
        return {'symbol_id': symbol['id'], 'sha256': symbol['sha256'],
                'path': symbol['path'], 'context_id': context_id}

    framework = {'kind': 'FRAMEWORK_DERIVED', 'relation': 'produces_bean',
                 'context_ids': [control], 'source_file': control_site['path'], 'source_line': 3,
                 'detail': 'Stored compiler provenance fixture', 'framework_rules': {}}
    runtime = {'kind': 'RUNTIME_OBSERVED', 'relation': 'observed_dispatch_to', 'context_id': control,
               'runtime_id': 'scope-reference-fixture', 'build_id': 'synthetic-build',
               'scenario': '', 'async': False, 'observation_source': None}
    control_cfg = next(cfg for cfg in initial.cfgs if cfg['context_id'] == control)
    cases = {
        'cfg-null': None,
        'compiler-sources': {**framework, 'compiler_sources': [compiler_source(peer)]},
        'compiler-symbol': {**framework, 'compiler_symbol_id': classes[peer]['id']},
        'compiler-call-site': {**framework, 'compiler_symbol_id': peer_site['id']},
        'runtime-call-site': {**runtime, 'call_site': peer_site['id'], 'receiver_type': classes[control]['id']},
        'runtime-receiver': {**runtime, 'call_site': control_site['id'], 'receiver_type': classes[peer]['id']},
        'independent-compiler': {**framework, 'compiler_sources': [compiler_source(control)],
                                 'compiler_symbol_id': classes[control]['id']},
        'independent-compiler-site': {**framework, 'relation': 'may_traverse_proxy',
                                      'compiler_symbol_id': control_site['id']},
        'independent-runtime': {**runtime, 'call_site': control_site['id'], 'receiver_type': classes[control]['id']},
    }
    outcomes, resolutions = {}, []
    request = inspection.request_worker

    def resolved_selected(*args, **kwargs):
        response = request(*args, **kwargs)
        resolutions.append(response['coverage']['calls_resolved'])
        return response

    for case, record in cases.items():
        proof = None
        if record is None:
            stored = replace(initial, cfgs=[{**cfg, 'evidence_ids': None} if cfg == control_cfg else cfg
                                           for cfg in initial.cfgs])
        else:
            record = {**record, 'source': control_site['caller'], 'target': control_site['declared_target']}
            proof = {'id': 'evidence:' + digest(record), **record}
            edge = Edge(record['source'], record['target'], record['relation'], evidence_kind=record['kind'],
                        context_ids=(control,), evidence_ids=(proof['id'],))
            stored = replace(initial, evidence=[*initial.evidence, proof], edges=[*initial.edges, edge])
        store.save_graph(stored, tmp_path, generate_docs=False)
        before = _store_bytes(tmp_path)
        with patch.object(inspection, 'request_worker', resolved_selected):
            try:
                inspected = inspect_jvm(tmp_path, module='selected', **options)
            except WorkerError as error:
                outcomes[case] = (error.status, _store_bytes(tmp_path) == before)
            except TypeError:
                outcomes[case] = ('TypeError', _store_bytes(tmp_path) == before)
            else:
                assert inspected['exit_code'] == 0
                after = store.load_graph(tmp_path)
                assert _compiler_layer(after, peer)[0][0]['freshness'] == 'STALE'
                assert proof is not None and proof in after.evidence and edge in after.edges
                if record['kind'] == 'RUNTIME_OBSERVED':
                    assert any(row.get('call_site') == record['call_site']
                               and row.get('receiver_type') == record['receiver_type']
                               for row in callees(after, control_site['caller'])['results'])
                outcomes[case] = ('PUBLISHED', False)
    assert resolutions == [1] * len(cases)
    assert outcomes == {case: ('PUBLISHED', False) if case.startswith('independent-') else ('STALE', True)
                        for case in cases}


@pytest.mark.parametrize('retire_peer', [False, True], ids=['no-retirement', 'isolated-retirement'])
def test_actual_jvm_uncaptured_eol_drift_during_peer_publication(tmp_path, retire_peer):
    options, _, _, _ = _native_jvm_peer_fixture(tmp_path, 'k1', edit_peer=retire_peer)
    path = 'outside/src/main/java/Uncaptured.java'
    outside = _write(tmp_path, path, 'class Uncaptured { }\n')
    before = _store_bytes(tmp_path)
    replace = store.os.replace
    edited = []

    def outside_drifts_after_first_replace(source, destination):
        replace(source, destination)
        if destination == tmp_path / store.MERMAID_FILE and not edited:
            outside.write_bytes(b'class Uncaptured { }\r\n')
            edited.append(destination)

    with patch.object(store.os, 'replace', outside_drifts_after_first_replace):
        result = inspect_jvm(tmp_path, module='selected', **options)
    assert result['exit_code'] == 0 and len(edited) == 1
    assert _store_bytes(tmp_path)[GRAPH_FILE] != before[GRAPH_FILE]
    captures = [context for context in result['graph']['contexts'] if context.get('analyzer_version')]
    assert all(path not in context['source_files'] for context in captures)
    peer = next(context for context in captures if context['module'] == 'edited')
    assert peer['freshness'] == ('STALE' if retire_peer else 'CONTENT_VERIFIED')


def test_actual_javac_signature_change_reaches_transitive_callers_without_workers(tmp_path):
    _require_javac_worker()
    src = "app/src/main/java/"
    target = _write(tmp_path, src + "Api.java", "class Api { static int value(int x) { return x; } }")
    _write(tmp_path, src + "Middle.java", """class Middle {
        static int helper() { return Api.value(1); }
        static int pass() { return helper(); }
        static int separate() { return 1; }
    }""")
    _write(tmp_path, src + "Caller.java", "class Caller { static int call() { return Middle.pass(); } }")
    _write(tmp_path, src + "Reference.java",
           "class Reference { static java.util.function.IntUnaryOperator bind() { return Api::value; } }")
    _write(tmp_path, src + "Independent.java",
           "class Independent { static int value(int x) { return x + Middle.separate(); } }")
    outside = "service/src/main/java/Other.java"
    _write(tmp_path, outside,
           "class Api { static int value(int x) { return x; } } class Other { int run() { return Api.value(1); } }")
    inputs = [p.relative_to(tmp_path).as_posix() for p in (tmp_path / src).glob("*.java")]
    model = {"source_sets": [{"module": module, "id": "main", "scope": "production", "files": files}
                             for module, files in (("app", inputs), ("service", [outside]))]}
    inspection = inspect_jvm(tmp_path, module="app", sources=inputs, project_model=model)
    assert inspection["exit_code"] == 0
    independent = inspect_jvm(tmp_path, module="service", sources=[outside], project_model=model)
    assert independent["exit_code"] == 0 and independent["context"]["id"] != inspection["context"]["id"]
    expected_store = _store_bytes(tmp_path)
    target.write_text("class Api { static int value(String x) { return x.length(); } }", encoding="utf-8")

    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        report = dependency_impact(tmp_path, [src + "Api.java"])
    assert report["coverage"] == "PARTIAL"
    assert report["graph_sha256"] == hashlib.sha256(expected_store[GRAPH_FILE]).hexdigest()
    assert [row["path"] for row in report["changed_sources"]] == [src + "Api.java"]
    affected = report["affected"]
    assert sorted(item["path"] for item in affected) == [src + name for name in (
        "Caller.java", "Middle.java", "Middle.java", "Reference.java",
    )]
    def dependency(path, source):
        return next(item for item in affected if item["path"] == src + path
                    and item["reasons"][0]["dependency_path"] == src + source)

    caller = dependency("Caller.java", "Middle.java")
    helper = dependency("Middle.java", "Api.java")
    local_pass = dependency("Middle.java", "Middle.java")
    reference = dependency("Reference.java", "Api.java")
    assert caller["reasons"][0]["dependency_id"] == local_pass["id"]
    assert local_pass["reasons"][0]["dependency_id"] == helper["id"]
    assert reference["reasons"][0]["relation"] == "declares_reference"
    assert all(item["kind"] == "COMPILER_CALLER" and item["status"] == "RECHECK" for item in affected)
    assert all(len(reason["evidence_ids"]) == 2 and reason["call_site_id"]
               for item in affected for reason in item["reasons"])
    assert _store_bytes(tmp_path) == expected_store


@pytest.mark.parametrize(("target_ending", "caller_ending", "locator"), [
    pytest.param(b"\n", b"\n", "verified", id="lf-to-crlf-lf-caller"),
    pytest.param(b"\r\n", b"\n", "verified", id="crlf-to-lf-lf-caller"),
    pytest.param(b"\n", b"\r\n", "verified", id="lf-to-crlf-crlf-caller"),
    pytest.param(b"\r\n", b"\r\n", "verified", id="crlf-to-lf-crlf-caller"),
    pytest.param(b"\n", b"\n", "unknown", id="unknown-locator"),
    pytest.param(b"\n", b"\n", "mismatched", id="mismatched-locator"),
])
def test_actual_javac_line_ending_change_rechecks_proven_caller(tmp_path, target_ending, caller_ending, locator):
    _require_javac_worker()
    api = "src/main/java/Api.java"
    caller = "src/main/java/Caller.java"
    outer = "src/main/java/Outer.java"
    other_api = "src/main/java/Other.java"
    other_caller = "src/main/java/OtherCaller.java"
    api_lf = b"class Api {\n    static int value(int x) { return x; }\n}\n"
    caller_lf = b"class Caller {\n    static int read() { return Api.value(1); }\n}\n"
    original = api_lf.replace(b"\n", target_ending)
    caller_bytes = caller_lf.replace(b"\n", caller_ending)
    _write(tmp_path, other_api, "class Other { static int value(int x) { return -x; } }")
    _write(tmp_path, other_caller, "class OtherCaller { static int read() { return Other.value(1); } }")
    _write(tmp_path, outer, "class Outer { static int read() { return Caller.read(); } }")
    target = tmp_path / api
    target.write_bytes(original)
    (tmp_path / caller).write_bytes(caller_bytes)
    inputs = [api, caller, outer, other_api, other_caller]
    model = {"source_sets": [{"module": "app", "id": "main", "scope": "production", "files": inputs}]}
    inspection = inspect_jvm(tmp_path, module="app", sources=inputs, project_model=model)
    assert inspection["exit_code"] == 0
    graph = inspection["graph"]
    resolved = {site["path"]: site for site in graph["call_sites"] if site.get("declared_target")}
    assert set(resolved) == {caller, outer, other_caller}
    assert resolved[caller]["declared_target"] != resolved[other_caller]["declared_target"]
    assert resolved[outer]["declared_target"] == resolved[caller]["caller"]
    context = inspection["context"]
    target_raw_sha256 = hashlib.sha256(original).hexdigest()
    caller_raw_sha256 = hashlib.sha256(caller_bytes).hexdigest()
    lexical_sha256 = hashlib.sha256(api_lf).hexdigest()
    assert context["source_snapshot_version"] == "selected-source-set-raw-1"
    assert context["source_files"][api] == target_raw_sha256
    assert context["source_files"][caller] == caller_raw_sha256
    assert graph["files"][api] == lexical_sha256
    evidence = {item["id"]: item for item in graph["evidence"]}
    direct_proofs = [evidence[identity] for identity in resolved[caller]["evidence_ids"]]
    assert {(proof["relation"], proof["source_file"], proof["sha256"]) for proof in direct_proofs} == {
        ("declares_call", caller, caller_raw_sha256), ("resolves_to", caller, caller_raw_sha256),
    }
    stored_graph = read_json(tmp_path / GRAPH_FILE)
    target_symbol = next(item for item in stored_graph["symbols"]
                         if item["id"] == resolved[caller]["declared_target"])
    assert (target_symbol["path"], target_symbol["sha256"]) == (api, target_raw_sha256)
    if locator == "unknown":
        target_symbol.pop("sha256")
    elif locator == "mismatched":
        target_symbol["sha256"] = "f" * 64
    if locator != "verified":
        write_json(tmp_path / GRAPH_FILE, stored_graph)
    expected_store = _store_bytes(tmp_path)

    def impact():
        with patch("kgmaker.scanner.scan_repository", side_effect=AssertionError("implicit rescan")):
            result = dependency_impact(tmp_path, [api])
        assert _store_bytes(tmp_path) == expected_store
        assert result["graph_sha256"] == hashlib.sha256(expected_store[GRAPH_FILE]).hexdigest()
        return result

    next_ending = b"\n" if target_ending == b"\r\n" else b"\r\n"
    edit = api_lf.replace(b"return x;", b"return x + 1;")
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        validate_context_snapshot(tmp_path, context)
        unchanged = impact()
        target.write_bytes(api_lf.replace(b"\n", next_ending))
        with pytest.raises(WorkerError, match="STALE_INDEX: source/config") as stale:
            validate_context_snapshot(tmp_path, context)
        assert stale.value.status == "STALE"
        report = impact()
        target.write_bytes(edit.replace(b"\n", target_ending))
        normal_change = impact()

    assert report["coverage"] == "PARTIAL"
    assert unchanged["changed_sources"] == unchanged["affected"] == []
    assert report["changed_sources"] == []
    assert normal_change["changed_sources"] == [
        {"path": api, "before_sha256": lexical_sha256, "after_sha256": hashlib.sha256(edit).hexdigest()},
    ]
    assert [item["path"] for item in normal_change["affected"]] == [caller, outer]
    for affected, dependency_path in zip(normal_change["affected"], (api, caller)):
        site = resolved[affected["path"]]
        assert (affected["kind"], affected["status"], affected["id"]) == (
            "COMPILER_CALLER", "RECHECK", site["caller"],
        )
        reason, = affected["reasons"]
        assert reason["before_sha256"] == graph["files"][dependency_path]
        assert reason["dependency_path"] == dependency_path
        assert reason["dependency_id"] == site["declared_target"]
        assert reason["call_site_id"] == site["id"]
        assert reason["context_id"] == context["id"]
        assert reason["evidence_ids"] == sorted(site["evidence_ids"])
    assert report["affected"] == (normal_change["affected"] if locator == "verified" else [])


def test_actual_javac_tampered_capture_cannot_ground_reverse_impact(tmp_path):
    _require_javac_worker()
    api, caller = "src/main/java/Api.java", "src/main/java/Caller.java"
    source = _write(tmp_path, api, "class Api { static int value() { return 1; } }\n")
    _write(tmp_path, caller, "class Caller { static int read() { return Api.value(); } }\n")
    inputs = [api, caller]
    model = {"source_sets": [{"module": "app", "id": "main", "scope": "production", "files": inputs}]}
    inspection = inspect_jvm(tmp_path, module="app", sources=inputs, project_model=model)
    assert inspection["exit_code"] == 0
    graph = read_json(tmp_path / GRAPH_FILE)
    context = next(row for row in graph["contexts"] if row["id"] == inspection["context"]["id"])
    context["compiler_inputs"] = [caller]
    assert context["source_files"][api] == hashlib.sha256(source.read_bytes()).hexdigest()

    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")), \
            patch("kgmaker.scanner.scan_repository", side_effect=AssertionError("implicit rescan")):
        with pytest.raises(WorkerError, match="JVM compiler input capture identity changed"):
            validate_context_snapshot(tmp_path, context)
        source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
        assert [item["path"] for item in dependency_impact(tmp_path, [api])["affected"]] == [caller]
        write_json(tmp_path / GRAPH_FILE, graph)
        before = _store_bytes(tmp_path)
        rejected = dependency_impact(tmp_path, [api])
    assert rejected["changed_sources"] == rejected["affected"] == []
    assert rejected["graph_sha256"] == hashlib.sha256(before[GRAPH_FILE]).hexdigest()
    assert _store_bytes(tmp_path) == before


@pytest.mark.parametrize("digest_map", ["source_files", "normalized_source_files"])
def test_actual_javac_malformed_capture_digest_is_ignored_in_public_impact(tmp_path, monkeypatch, capsys, digest_map):
    _require_javac_worker()
    targets = {module: f"{module}/src/main/java/Api.java" for module in ("app", "service")}
    callers = {module: f"{module}/src/main/java/Caller.java" for module in targets}
    model = {"source_sets": [
        {"module": module, "id": "main", "scope": "production", "files": [target, callers[module]]}
        for module, target in targets.items()
    ]}
    original = b"class Api {\r\n    static int value() { return 1; }\r\n}\r\n"
    for module, target in targets.items():
        _write(tmp_path, callers[module], "class Caller { static int read() { return Api.value(); } }")
        (tmp_path / target).write_bytes(original)
    captures = {module: inspect_jvm(tmp_path, module=module, sources=[target, callers[module]], project_model=model)
                for module, target in targets.items()}
    assert all(result["exit_code"] == 0 for result in captures.values())
    for target in targets.values():
        (tmp_path / target).write_bytes(original.replace(b"return 1;", b"return 2;"))

    stored = tmp_path / GRAPH_FILE
    graph = read_json(stored)
    context = next(row for row in graph["contexts"] if row["id"] == captures["app"]["context"]["id"])
    assert context[digest_map][targets["app"]] == captures["app"]["context"][digest_map][targets["app"]]
    monkeypatch.setattr("sys.argv", ["kgmaker", "impact", "--root", str(tmp_path), "--evidence-only",
                                   "--format", "json", *targets.values()])
    capsys.readouterr()

    def impact():
        before = _store_bytes(tmp_path)
        with patch("subprocess.Popen", side_effect=AssertionError("implicit process")), \
                patch("kgmaker.scanner.scan_repository", side_effect=AssertionError("implicit rescan")), \
                pytest.raises(SystemExit) as outcome:
            main()
        assert outcome.value.code == 0
        output = capsys.readouterr()
        assert output.err == ""
        report = json.loads(output.out)
        assert report["coverage"] == "PARTIAL"
        assert report["graph_sha256"] == hashlib.sha256(before[GRAPH_FILE]).hexdigest()
        assert _store_bytes(tmp_path) == before
        return report

    control = impact()
    assert [item["path"] for item in control["affected"]] == list(callers.values())
    context[digest_map][targets["app"]] = "invalid test digest"
    stored.write_text(json.dumps(graph).replace('"invalid test digest"', "1e400"), encoding="utf-8")
    malformed = next(row for row in read_json(stored)["contexts"] if row["id"] == context["id"])
    assert malformed[digest_map][targets["app"]] == float("inf")

    report = impact()
    assert report["changed_sources"] == control["changed_sources"]
    assert report["affected"] == [control["affected"][1]]


def test_replayed_schema_and_openapi_citation_invalidate_only_proven_dependents(tmp_path, monkeypatch, capsys):
    migrations = "src/main/resources/db/migration/"
    base = _write(tmp_path, migrations + "V1__customers.sql", "CREATE TABLE customer (balance INTEGER);")
    _write(tmp_path, migrations + "V2__independent.sql", "CREATE TABLE other (balance INTEGER);")
    _write(tmp_path, migrations + "R__views.sql", "CREATE OR REPLACE VIEW balances AS SELECT balance FROM customer;")
    _write(tmp_path, "requirement.md", "Validate the published API contract.")
    api = tmp_path / "openapi.json"
    original_api = json.dumps({
        "openapi": "3.0.3", "paths": {"/balance": {"get": {"operationId": "getBalance"}}},
    }, indent=2).replace("\n", "\r\n").encode("utf-8")
    api.write_bytes(original_api)
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "requirement.md", "contracts")
    candidate = inventory_candidate(packet)
    evidence_id = "analysis:contracts:evidence:get"
    conclusion = "analysis:contracts:test:read"
    candidate["evidence"] = [{"id": evidence_id, "source_id": "openapi.json", "kind": "CONTRACT",
                              "path": "openapi.json", "sha256": packet["source_manifest"]["openapi.json"]["sha256"],
                              "location": {"type": "json_pointer", "pointer": "/paths/~1balance/get/operationId"},
                              "value": "getBalance", "supports": "Declared operation name.", "method": "EXTRACTED",
                              "confidence": 1, "validity": "VALID"}]
    candidate["test_plan"] = [{"id": conclusion, "text": "Check the declared operation.", "state": "TO_BE",
                               "requirement_ids": [candidate["requirements"][0]["id"]],
                               "entity_ids": [], "evidence_ids": [evidence_id]}]
    assert feature.apply(tmp_path, "contracts", candidate)["valid"]
    base.write_text("CREATE TABLE customer (balance BIGINT);", encoding="utf-8")
    api.write_bytes(original_api.replace(b"getBalance", b"fetchBalance"))
    # A newly prepared revision leaves the previously applied revision and its receipt readable.
    assert feature.prepare(tmp_path, "requirement.md", "contracts")["revision"] == 2
    expected_store = _store_bytes(tmp_path)

    capsys.readouterr()
    monkeypatch.setattr("sys.argv", ["kgmaker", "impact", "--root", str(tmp_path), "--evidence-only",
                                   "--format", "json", migrations + "V1__customers.sql", "openapi.json"])
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")), pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert [row["path"] for row in report["changed_sources"]] == [
        "openapi.json", migrations + "V1__customers.sql",
    ]
    assert {item["kind"] for item in report["affected"]} == {
        "CONTRACT_DECLARATION", "SCHEMA_DEPENDENT", "FEATURE_CONCLUSION",
    }
    schema = next(item for item in report["affected"] if item["kind"] == "SCHEMA_DEPENDENT")
    assert schema["path"] == migrations + "R__views.sql"
    assert schema["reasons"][0]["evidence_kind"] == "MIGRATION_DERIVED"
    stale = next(item for item in report["affected"] if item["kind"] == "FEATURE_CONCLUSION")
    assert stale["id"] == conclusion and stale["status"] == "STALE"
    assert stale["reasons"][0]["revision"] == 1
    assert stale["reasons"][0]["evidence_id"] == evidence_id
    assert stale["reasons"][0]["before_sha256"] == hashlib.sha256(original_api).hexdigest()
    assert _store_bytes(tmp_path) == expected_store
    assert dependency_impact(tmp_path, ["openapi.json", migrations + "V1__customers.sql"]) == report

    # The citation can no longer be trusted when the applied payload and receipt differ.
    applied = tmp_path / ".kgmaker/analyses/contracts/analysis.json"
    tampered = read_json(applied)
    tampered["test_plan"][0]["text"] = "Unrecorded conclusion"
    write_json(applied, tampered)
    expected_store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert [item["kind"] for item in report["affected"]] == ["CONTRACT_DECLARATION"]
    assert {"code": "FEATURE_REVISION_UNAVAILABLE", "analysis_id": "contracts"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == expected_store


def test_schema_dependency_follows_prior_migration_operations(tmp_path):
    migrations = "src/main/resources/db/migration/"
    created = _write(tmp_path, migrations + "V1__customers.sql", "CREATE TABLE customer (balance INTEGER);")
    altered = _write(tmp_path, migrations + "V2__default.sql", "ALTER TABLE customer ALTER COLUMN balance SET DEFAULT 0;")
    other = _write(tmp_path, migrations + "V3__other.sql", "CREATE TABLE other (balance INTEGER);")
    _write(tmp_path, migrations + "R__views.sql",
           "CREATE VIEW balances AS SELECT balance FROM customer;")
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    created.write_text("CREATE TABLE customer (balance BIGINT);", encoding="utf-8")
    altered.write_text("ALTER TABLE customer ALTER COLUMN balance SET DEFAULT 1;", encoding="utf-8")
    other.write_text("CREATE TABLE other (balance BIGINT);", encoding="utf-8")
    paths = [path.relative_to(tmp_path).as_posix() for path in (created, altered, other)]

    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        report = dependency_impact(tmp_path, paths)
    assert report["coverage"] == "PARTIAL"
    assert len(report["affected"]) == 1
    dependent = report["affected"][0]
    assert (dependent["kind"], dependent["status"], dependent["path"]) == (
        "SCHEMA_DEPENDENT", "RECHECK", migrations + "R__views.sql",
    )
    assert {reason["dependency_path"] for reason in dependent["reasons"]} == set(paths[:2])
    assert all(reason["operation_id"] and reason["operation_line"] == 1 for reason in dependent["reasons"])
    assert _store_bytes(tmp_path) == store

    # A malformed earlier operation cannot stand in for the saved replay trace.
    stored = read_json(tmp_path / GRAPH_FILE)
    target_id = dependent["reasons"][0]["dependency_id"]
    operation = next(edge for edge in stored["edges"] if edge["kind"] == "operation_targets"
                     and edge["target"] == target_id and edge["source_file"] == paths[0])
    operation["source_line"] += 1
    write_json(tmp_path / GRAPH_FILE, stored)
    store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, paths)
    assert [reason["dependency_path"] for item in report["affected"] for reason in item["reasons"]] == [paths[1]]
    assert _store_bytes(tmp_path) == store


def test_explicit_composite_fk_columns_join_historical_migration_operations(tmp_path):
    migrations = 'src/main/resources/db/migration/'
    _write(tmp_path, migrations + 'V1__tables.sql',
           'CREATE TABLE parent(a INTEGER, b INTEGER, other INTEGER, UNIQUE(b,a));\n'
           'CREATE TABLE sibling(b INTEGER);\n')
    fk_path = migrations + 'V2__reference.sql'
    _write(tmp_path, fk_path, 'CREATE TABLE child(x INTEGER, y INTEGER, '
           'CONSTRAINT child_parent FOREIGN KEY(x,y) REFERENCES parent(b,a));\n')
    changes = [(migrations + f'V{n}__{table}_{column}.sql', table, column)
               for n, (table, column) in enumerate(
                   [('parent', 'b'), ('parent', 'a'), ('parent', 'other'), ('sibling', 'b')], 3)]
    for path, table, column in changes:
        _write(tmp_path, path, f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 1;\n')

    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        assert scan(tmp_path, generate_docs=False) == 0
        graph = store.load_graph(tmp_path)
        foreign_key = next(node for node in graph.nodes if node.kind == 'db_constraint' and node.path == fk_path)
        target_ids = {node.name.rsplit('.', 1)[-1]: node.id for node in graph.nodes
                      if node.kind == 'db_column' and node.name in {'public.parent.a', 'public.parent.b'}}
        captured = _store_bytes(tmp_path)
        for path, table, column in changes:
            _write(tmp_path, path, f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 2;\n')
        with patch('kgmaker.schema_replay.reconstruct', side_effect=AssertionError('implicit replay')):
            report = dependency_impact(tmp_path, [path for path, _, _ in changes])
        assert _store_bytes(tmp_path) == captured
        assert scan(tmp_path, generate_docs=False) == 0
        replayed = store.load_graph(tmp_path)
        assert replayed.files != graph.files
        assert {node.id for node in replayed.nodes if node.name in {'public.sibling', 'public.sibling.b'}} == {
            node.id for node in graph.nodes if node.name in {'public.sibling', 'public.sibling.b'}
        }
        assert not dependency_impact(tmp_path, [path for path, _, _ in changes])['affected']

    assert {row['path'] for row in report['changed_sources']} == {path for path, _, _ in changes}
    assert [(row['kind'], row['id'], row['status']) for row in report['affected']] == [
        ('SCHEMA_DEPENDENT', foreign_key.id, 'RECHECK'),
    ]
    reasons = report['affected'][0]['reasons']
    assert {(row['dependency_path'], row['dependency_id']) for row in reasons} == {
        (path, target_ids[column]) for path, _, column in changes[:2]
    }
    assert all(row['relation'] == 'foreign_key_references_column' and row['operation_id']
               and row['operation_line'] == 1 for row in reasons)
    assert {edge.target for edge in graph.edges if edge.kind == 'foreign_key_references_column'
            and edge.source == foreign_key.id} == set(target_ids.values())
    parent = next(node for node in graph.nodes if node.kind == 'db_table' and node.name == 'public.parent')
    assert foreign_key.metadata['foreign_key_targets'] == {
        'table_id': parent.id, 'column_ids': [target_ids['b'], target_ids['a']],
    }
    assert {edge.target for edge in replayed.edges if edge.kind == 'foreign_key_references_column'
            and edge.source == foreign_key.id} == set(target_ids.values())


def test_explicit_fk_column_rejects_unbound_stored_scope_or_operation(tmp_path):
    from kgmaker.schema_replay import reconstruct, schema_snapshot_fingerprint

    migrations = 'src/main/resources/db/migration/'
    tables = migrations + 'V1__parent.sql'
    _write(tmp_path, tables, 'CREATE TABLE parent(id INTEGER UNIQUE, other INTEGER UNIQUE); '
           'CREATE TABLE sibling(id INTEGER);\n')
    _write(tmp_path, migrations + 'V2__fk.sql', 'CREATE TABLE child(p INTEGER, '
           'CONSTRAINT child_parent FOREIGN KEY(p) REFERENCES parent(id));\n'
           'CREATE TABLE independent(p INTEGER, '
           'CONSTRAINT independent_other FOREIGN KEY(p) REFERENCES parent(other));\n')
    altered = migrations + 'V3__alter.sql'
    _write(tmp_path, altered, 'ALTER TABLE parent ALTER COLUMN id SET DEFAULT 1;\n')
    independent = migrations + 'V4__independent.sql'
    _write(tmp_path, independent, 'ALTER TABLE parent ALTER COLUMN other SET DEFAULT 1;\n')
    related = 'foreign_key_references_column'
    graph_path = tmp_path / GRAPH_FILE
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        assert scan(tmp_path, generate_docs=False) == 0
        captured = read_json(graph_path)
        fk = next(row['id'] for row in captured['nodes'] if row['name'] == 'public.child.child_parent')
        edge, = [row for row in captured['edges'] if row['kind'] == related and row['source'] == fk]
        other, = [row for row in captured['edges'] if row['kind'] == related and row['source'] != fk]
        parent, = [row['target'] for row in captured['edges'] if row['kind'] == 'foreign_key_to'
                   and row['source'] == edge['source']]
        operation, = [row for row in captured['edges'] if row['kind'] == 'operation_targets'
                      and row['target'] == edge['target'] and row['source_file'] == altered]
        sibling = next(row['id'] for row in captured['nodes'] if row['name'] == 'public.sibling.id')
        _write(tmp_path, altered, 'ALTER TABLE parent ALTER COLUMN id SET DEFAULT 2;\n')
        _write(tmp_path, independent, 'ALTER TABLE parent ALTER COLUMN other SET DEFAULT 2;\n')
        other_snapshot = schema_snapshot_fingerprint(reconstruct(tmp_path))
        assert dependency_impact(tmp_path, [altered])['affected'][0]['id'] == edge['source']

        for identity in (edge['source'], edge['target'], parent, operation['source']):
            malformed = deepcopy(captured)
            node = next(row for row in malformed['nodes'] if row['id'] == identity)
            assert node['metadata']['schema_snapshot_fingerprint'] != other_snapshot
            node['metadata']['schema_snapshot_fingerprint'] = other_snapshot
            write_json(graph_path, malformed)
            before = _store_bytes(tmp_path)
            assert not dependency_impact(tmp_path, [altered])['affected']
            assert _store_bytes(tmp_path) == before

        wrong_parent = deepcopy(captured)
        next(row for row in wrong_parent['edges'] if row == edge)['target'] = sibling
        next(row for row in wrong_parent['edges'] if row == operation)['target'] = sibling
        write_json(graph_path, wrong_parent)
        before = _store_bytes(tmp_path)
        assert not dependency_impact(tmp_path, [altered])['affected']
        assert _store_bytes(tmp_path) == before

        wrong_column = deepcopy(captured)
        next(row for row in wrong_column['edges'] if row == edge)['target'] = other['target']
        write_json(graph_path, wrong_column)
        before = _store_bytes(tmp_path)
        assert [row['id'] for row in dependency_impact(tmp_path, [independent])['affected']] == [other['source']]
        assert _store_bytes(tmp_path) == before

        mismatched_path = deepcopy(captured)
        next(row for row in mismatched_path['edges'] if row == operation)['source_file'] = tables
        write_json(graph_path, mismatched_path)
        before = _store_bytes(tmp_path)
        assert not dependency_impact(tmp_path, [altered])['affected']
        assert _store_bytes(tmp_path) == before

        legacy = deepcopy(captured)
        legacy['edges'] = [row for row in legacy['edges'] if row['kind'] != related]
        for row in legacy['nodes']:
            if row['kind'] == 'migration_operation':
                row['metadata'].pop('schema_snapshot_fingerprint', None)
        write_json(graph_path, legacy)
        _write(tmp_path, tables, 'CREATE TABLE parent(id INTEGER UNIQUE, other INTEGER UNIQUE); '
               'CREATE TABLE sibling(id BIGINT);\n')
        before = _store_bytes(tmp_path)
        report = dependency_impact(tmp_path, [tables, altered])
        assert {(row['id'], row['status']) for row in report['affected']} == {
            (edge['source'], 'RECHECK'), (other['source'], 'RECHECK'),
        }
        assert all([reason['relation'] for reason in row['reasons']] == ['foreign_key_to'] for row in report['affected'])
        assert _store_bytes(tmp_path) == before


@pytest.mark.parametrize('authority', ['implicit', 'missing', 'partial', 'supplied-snapshot'])
def test_fk_column_projection_requires_all_named_columns_and_complete_local_replay(tmp_path, authority):
    from kgmaker.schema_replay import graph_entities, reconstruct

    migrations = 'src/main/resources/db/migration/'
    ddl = 'CREATE TABLE parent(a INTEGER, b INTEGER, UNIQUE(b,a));\n'
    refs = 'parent' if authority == 'implicit' else 'parent(b,a)'
    _write(tmp_path, migrations + 'V1__fk.sql', ddl + 'CREATE TABLE child(x INTEGER, y INTEGER, '
           f'CONSTRAINT child_parent FOREIGN KEY(x,y) REFERENCES {refs});\n')
    if authority == 'partial':
        _write(tmp_path, migrations + 'V2__blocked.sql', 'ALTER TABLE parent DROP COLUMN b;\n')
    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        schema = reconstruct(tmp_path)
        assert schema['status'] == ('PARTIAL' if authority == 'partial' else 'COMPLETE')
        if authority == 'missing':
            schema['objects'].pop('column:public.parent.a')
        if authority == 'supplied-snapshot':
            write_json(tmp_path / 'snapshot.json', {'schema_version': 1, 'objects': schema['objects']})
            schema = reconstruct(tmp_path, {'mode': 'snapshot', 'initial_snapshot': 'snapshot.json',
                                            'baseline_version': '1'})
            assert schema['status'] == 'COMPLETE' and schema.get('snapshot_provenance')
        _, edges = graph_entities(schema, include_named_fk_columns=True)
    assert any(edge.kind == 'foreign_key_to' for edge in edges)
    assert not any(edge.kind == 'foreign_key_references_column' for edge in edges)


def test_fk_column_projection_retains_renamed_identity_and_replaces_recreated_target(tmp_path):
    from kgmaker.schema_replay import graph_entities, reconstruct

    migrations = 'src/main/resources/db/migration/'
    _write(tmp_path, migrations + 'V1__fk.sql',
           'CREATE TABLE parent(a INTEGER, b INTEGER UNIQUE);\n'
           'CREATE TABLE child(x INTEGER, CONSTRAINT child_parent FOREIGN KEY(x) REFERENCES parent(b));\n')

    def references():
        schema = reconstruct(tmp_path)
        assert schema['status'] == 'COMPLETE'
        nodes, edges = graph_entities(schema, include_named_fk_columns=True)
        edge, = [edge for edge in edges if edge.kind == 'foreign_key_references_column']
        target = next(node for node in nodes if node.id == edge.target)
        return (edge.source, edge.target), target.name

    with patch('subprocess.Popen', side_effect=AssertionError('implicit process')):
        original, name = references()
        assert name == 'public.parent.b'
        _write(tmp_path, migrations + 'V2__rename.sql', 'ALTER TABLE parent RENAME COLUMN b TO renamed;\n')
        renamed, name = references()
        assert original == renamed and name == 'public.parent.renamed'
        _write(tmp_path, migrations + 'V3__replace.sql', 'ALTER TABLE child DROP CONSTRAINT child_parent;\n'
               'ALTER TABLE parent DROP COLUMN renamed; ALTER TABLE parent ADD COLUMN renamed INTEGER UNIQUE;\n'
               'ALTER TABLE child ADD CONSTRAINT child_parent FOREIGN KEY(x) REFERENCES parent(renamed);\n')
        recreated, name = references()
        assert set(recreated).isdisjoint(original) and name == 'public.parent.renamed'


@pytest.mark.parametrize("changed_path", ["req/requirement.md", "context.md"])
def test_applied_feature_dependency_requires_a_file_authority(tmp_path, changed_path):
    requirement_path = "req/requirement.md"
    _write(tmp_path, requirement_path, "Review the input definition.")
    _write(tmp_path, "context.md", "Context supplied alongside the decision.")
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "./req//requirement.md", "proof")
    candidate = inventory_candidate(packet)
    requirement_id = candidate["requirements"][0]["id"]
    question = {"id": "analysis:proof:question:definition", "text": "How should input be defined?",
                "status": "OPEN", "blocking": True, "owner_role": "Business",
                "requirement_ids": [requirement_id]}
    candidate["questions"] = [question]
    assert feature.apply(tmp_path, "proof", candidate)["valid"]
    answer = {"question_id": question["id"], "decision_id": "definition", "answer": "User-supplied definition",
              "revision": 1, "approval_status": "APPROVED"}
    packet = feature.revise(tmp_path, "proof", {"answers": [answer]})
    assert packet["requirement_path"] == "./req//requirement.md"
    candidate = inventory_candidate(packet)
    candidate["questions"] = [{**question, "status": "ANSWERED"}]
    requirement_evidence = "analysis:proof:evidence:requirement"
    decision_evidence = "analysis:proof:evidence:decision"
    shared = {"supports": "Review the supplied input.", "method": "EXTRACTED", "confidence": 1,
              "validity": "VALID"}
    candidate["evidence"] = [
        {**shared, "id": requirement_evidence, "source_id": requirement_id, "kind": "REQUIREMENT",
         "quote": packet["requirement"], "sha256": packet["requirement_file_hash"]},
        {**shared, **answer, "id": decision_evidence, "source_id": answer["decision_id"], "kind": "HUMAN_DECISION",
         "path": "context.md", "sha256": packet["source_manifest"]["context.md"]["sha256"]},
    ]
    candidate["test_plan"] = [
        {"id": "analysis:proof:test:" + name, "text": "Check the " + name, "state": "TO_BE",
         "requirement_ids": [requirement_id], "entity_ids": [], "evidence_ids": [evidence_id]}
        for name, evidence_id in (("requirement", requirement_evidence), ("decision", decision_evidence))
    ]
    assert feature.apply(tmp_path, "proof", candidate)["valid"]
    store = _store_bytes(tmp_path)
    (tmp_path / changed_path).write_text("Content changed.", encoding="utf-8")

    report = dependency_impact(tmp_path, [changed_path])
    if changed_path == requirement_path:
        assert [item["id"] for item in report["affected"]] == ["analysis:proof:test:requirement"]
        reason, = report["affected"][0]["reasons"]
        assert (reason["evidence_id"], reason["path"], reason["revision"]) == (requirement_evidence, requirement_path, 2)
    else:
        assert not report["affected"]
    assert _store_bytes(tmp_path) == store


@pytest.mark.parametrize("edit", ["none", "line_endings", "operation"])
def test_openapi_reverse_dependency_distinguishes_raw_and_normalized_hashes(tmp_path, edit):
    # Split a CRLF pair across the reader's chunk boundary.
    raw = b" " * 65535 + b'\r\n{"openapi":"3.0.3","paths":{"/item":{"get":{"operationId":"getItem"}}}}\r\n'
    api = tmp_path / "openapi.json"
    api.write_bytes(raw)
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    changed = {"none": raw, "line_endings": raw.replace(b"\r\n", b"\n"),
               "operation": raw.replace(b"getItem", b"fetchItem")}[edit]
    api.write_bytes(changed)

    report = dependency_impact(tmp_path, ["openapi.json"])
    normalized_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if edit == "operation":
        assert report["changed_sources"] == [{
            "path": "openapi.json", "before_sha256": normalized_hash,
            "after_sha256": hashlib.sha256(changed.replace(b"\r\n", b"\n")).hexdigest(),
        }]
    else:
        assert not report["changed_sources"]
    if edit == "none":
        assert not report["affected"]
    else:
        dependent, = report["affected"]
        assert (dependent["kind"], dependent["status"], dependent["path"]) == (
            "CONTRACT_DECLARATION", "RECHECK", "openapi.json",
        )
        assert dependent["reasons"][0]["before_sha256"] == hashlib.sha256(raw).hexdigest()
    assert _store_bytes(tmp_path) == store


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_and_unproven_name_matches_never_gain_positive_evidence(tmp_path, version):
    from kgmaker.analysis_model import file_hash

    target = _write(tmp_path, "target.py", "def target(): pass")
    _write(tmp_path, "caller.py", "def caller(): target()")
    graph = KnowledgeGraph(version, ".", "", [
        Node("caller", "file", "caller.py", "caller.py"),
        Node("target", "function", "target", "target.py"),
    ], [Edge("caller", "target", "calls", confidence="INFERRED")],
        {"target.py": file_hash(target), "caller.py": file_hash(tmp_path / "caller.py")})
    save_graph(graph, tmp_path, generate_docs=False)
    if version == 2:
        generated = read_json(tmp_path / GRAPH_FILE)
        generated.update(symbols=[{"id": ["not-a-v2-field"]}], call_sites=["not-a-v2-field"])
        write_json(tmp_path / GRAPH_FILE, generated)
    target.unlink()
    store = (tmp_path / GRAPH_FILE).read_bytes()
    report = dependency_impact(tmp_path, ["target.py", "new.py"])
    assert report["changed_sources"] == [{"path": "target.py", "before_sha256": graph.files["target.py"],
                                          "after_sha256": None}]
    assert not report["affected"]
    assert {"code": "DEPENDENCY_PATH_NOT_CAPTURED", "path": "new.py"} in report["diagnostics"]
    assert (tmp_path / GRAPH_FILE).read_bytes() == store


def test_invalid_graph_and_nonregular_changed_source_leave_store_untouched(tmp_path):
    _write(tmp_path, "openapi.json", '{"openapi":"3.0.3","paths":{"/items":{"get":{}}}}')
    assert scan(tmp_path, generate_docs=False) == 0
    target = tmp_path / "openapi.json"
    target.unlink()
    target.mkdir()
    store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert not report["affected"] and not report["changed_sources"]
    assert {"code": "DEPENDENCY_PATH_UNAVAILABLE", "path": "openapi.json"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store

    (tmp_path / GRAPH_FILE).write_text("[]", encoding="utf-8")
    store = _store_bytes(tmp_path)
    with pytest.raises(AnalysisError, match="No readable graph found"):
        dependency_impact(tmp_path, ["openapi.json"])
    assert _store_bytes(tmp_path) == store


def test_malformed_stored_compiler_graph_keys_fail_closed_in_public_cli(tmp_path):
    _require_javac_worker()
    dependency = "src/main/java/Api.java"
    target = _write(tmp_path, dependency, "class Api { static int value(int x) { return x; } }")
    _write(tmp_path, "src/main/java/Caller.java", "class Caller { int run() { return Api.value(1); } }")
    assert inspect_jvm(tmp_path)["exit_code"] == 0
    stored = tmp_path / GRAPH_FILE
    original = stored.read_bytes()
    target.write_text("class Api { static int value(String x) { return x.length(); } }", encoding="utf-8")

    for collection, field in (("edges", "source_file"), ("edges", "kind"),
                              ("nodes", "path"), ("nodes", "kind")):
        graph = json.loads(original)
        assert graph["schema_version"] == 3
        edge = next(item for item in graph["edges"] if item["kind"] == "declares_call"
                    and item["evidence_kind"] == "SYMBOL_RESOLVED")
        record = edge if collection == "edges" else next(node for node in graph["nodes"] if node["id"] == edge["source"])
        record[field] = [record[field]]
        stored.write_text(json.dumps(graph), encoding="utf-8")
        before = _store_bytes(tmp_path)
        result = subprocess.run([sys.executable, "-m", "kgmaker", "impact", "--root", str(tmp_path),
                                 "--evidence-only", "--format", "json", dependency],
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 1 and not result.stdout
        assert result.stderr.startswith("No readable graph found.") and "Traceback" not in result.stderr
        assert _store_bytes(tmp_path) == before


@pytest.mark.skipif(not all(hasattr(os, name) for name in ("mkfifo", "O_NONBLOCK")), reason="FIFO input requires POSIX")
def test_changed_source_swapped_to_fifo_is_unavailable(tmp_path, monkeypatch):
    target = _write(tmp_path, "openapi.json", '{"openapi":"3.0.3","paths":{"/items":{"get":{}}}}')
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    open_file = os.open

    def replace_before_open(path, flags, *args, **kwargs):
        if path == target:
            target.unlink()
            os.mkfifo(target)
            # Prove the race is covered without performing a blocking open on regression.
            assert flags & os.O_NONBLOCK
        return open_file(path, flags, *args, **kwargs)

    monkeypatch.setattr(workspace.os, "open", replace_before_open)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert report["coverage"] == "PARTIAL" and not report["changed_sources"] and not report["affected"]
    assert {"code": "DEPENDENCY_PATH_UNAVAILABLE", "path": "openapi.json"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO input requires POSIX")
@pytest.mark.parametrize("record", ["analysis.json", "receipts/1.json", "packet.json", "history/packet-1.json"])
def test_feature_record_fifos_do_not_block_or_publish(tmp_path, record):
    requirement = _write(tmp_path, "requirement.md", "Record current feature evidence.")
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "requirement.md", "record")
    assert feature.apply(tmp_path, "record", inventory_candidate(packet))["valid"]
    requirement.write_text("Change current feature evidence.", encoding="utf-8")
    if record.startswith("history/"):
        assert feature.prepare(tmp_path, "requirement.md", "record")["revision"] == 2
    target = tmp_path / ".kgmaker/analyses/record" / record
    target.unlink()
    os.mkfifo(target)
    store = _store_bytes(tmp_path)
    result = subprocess.run([sys.executable, "-m", "kgmaker", "impact", "--root", str(tmp_path),
                             "--evidence-only", "--format", "json", "requirement.md"],
                            capture_output=True, text=True, timeout=3, check=True)
    report = json.loads(result.stdout)
    assert report["coverage"] == "PARTIAL" and not report["affected"]
    assert [item["path"] for item in report["changed_sources"]] == ["requirement.md"]
    assert {"code": "FEATURE_REVISION_UNAVAILABLE", "analysis_id": "record"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store
    assert not target.is_file()

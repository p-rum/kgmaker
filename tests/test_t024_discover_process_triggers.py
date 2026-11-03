"""Public trigger inventory over explicit upstream facts and genuine worker capture."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest

from kgmaker.analysis_model import digest, file_hash, write_json
from kgmaker.architecture_model import ViewDocument
from kgmaker.inspection import source_snapshot
from kgmaker.model import Edge, Node
from kgmaker.process_model import ProcessDefinition, ProcessView
from kgmaker.process_triggers import TriggerInventoryError, discover_process_triggers
from kgmaker.scanner import scan_repository
from kgmaker.workspace import load_workspace, qualified, snapshot_workspace

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'
ANNOTATIONS = {'http': 'org.springframework.web.bind.annotation.GetMapping',
    'kafka': 'org.springframework.kafka.annotation.KafkaListener',
    'scheduler': 'org.springframework.scheduling.annotation.Scheduled'}


def inputs(tmp_path):
    root = tmp_path / 'backend'
    paths = {}
    for scope, part in [('production', 'main'), ('test', 'test')]:
        path = root / f'src/{part}/java/demo/Entries.java'
        path.parent.mkdir(parents=True); path.write_text('package demo; class Entries { void http() {} void kafka() {} void scheduler() {} }\n')
        paths[scope] = path.relative_to(root).as_posix()
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, {'schema_version': 1, 'workspace_id': 'retail',
        'repositories': [{'id': 'backend', 'role': 'backend', 'path': 'backend'}],
        'services': [{'id': 'orders', 'backend_repo': 'backend', 'frontend_repos': [],
            'test_repos': [], 'contract': {'repo_id': 'backend', 'path': 'api.json'}}],
        'service_ownership': {'schema_version': 1, 'services': [{'id': 'orders',
            'roots': [{'repo_id': 'backend', 'path': 'src'}],
            'modules': [{'repo_id': 'backend', 'id': 'app'}], 'external_systems': []}]}})
    workspace = load_workspace(manifest); _, coverage, _, graph, _ = snapshot_workspace(manifest)
    entries = {}
    for scope in ['production', 'test']:
        cid = qualified('backend', scope)
        ctx = {'id': cid, 'repo_id': 'backend', 'module': 'app', 'source_set': 'main' if scope == 'production' else 'test',
            'scope': scope, 'mode': 'SYMBOL_RESOLVED', 'analyzer_version': 'explicit-test-snapshot',
            'freshness': 'CURRENT', 'classpath': []}
        ctx['source_files'] = {'@backend/' + p: h for p, h in source_snapshot(root, scan_repository(root), ctx).items()}
        graph.contexts.append(ctx)
        for kind in ['http', 'kafka', 'scheduler']:
            path = '@backend/' + paths[scope]; method = qualified('backend', scope + ':' + kind)
            target = qualified('backend', scope + ':entry:' + kind); proof = 'proof:' + scope + ':' + kind
            relation = 'exposes_endpoint' if kind == 'http' else 'declares_entrypoint'
            graph.nodes.extend([Node(method, 'method', kind, path, 1, scope=scope),
                Node(target, 'spring_endpoint' if kind == 'http' else 'spring_entrypoint', kind, path, 1,
                     scope=scope, metadata={'entrypoint_kind': 'kafka_listener' if kind == 'kafka' else 'scheduled'})])
            graph.symbols.append({'id': method, 'name': kind, 'kind': 'method', 'path': path,
                'context_id': cid, 'scope': scope, 'range': {'start_line': 1}, 'sha256': graph.files[path],
                'annotations': [{'name': ANNOTATIONS[kind], 'values': {}}]})
            graph.nodes = [replace(n, metadata=deepcopy(graph.symbols[-1])) if n.id == method else n for n in graph.nodes]
            graph.evidence.append({'id': proof, 'kind': 'FRAMEWORK_DERIVED', 'source': method,
                'target': target, 'relation': relation, 'source_file': path, 'context_ids': [cid],
                'polarity': 'SUPPORTING'})  # Actual native framework records may omit per-fact SHA.
            graph.edges.append(Edge(method, target, relation, evidence_kind='FRAMEWORK_DERIVED',
                context_ids=(cid,), evidence_ids=(proof,), source_file=path, source_line=1))
            entries[(scope, kind)] = (method, target, proof)
    return workspace, graph, coverage, entries


def test_ac01_http_kafka_and_declared_scheduler_keep_distinct_type_origin_and_owner(tmp_path):
    workspace, graph, coverage, entries = inputs(tmp_path); before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('projection must not execute a worker')), \
         patch('socket.socket', side_effect=AssertionError('no network')):
        view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert view.kind == 'process' and {n.attributes['trigger_kind'] for n in view.nodes} == {'HTTP', 'KAFKA', 'SCHEDULER'}
    assert all(n.kind == 'trigger' and n.owner_id == 'service:orders' for n in view.nodes)
    assert not view.edges and all(n.attributes['registration_status'] == 'UNKNOWN' for n in view.nodes)
    for node in view.nodes:
        kind = node.attributes['trigger_kind'].lower(); method, target, proof = entries[('production', kind)]
        assert {method, target, proof} <= set(node.original_ids)
        assert node.attributes['entry_symbol_id'] == method
        assert node.attributes['context_ids'] == [qualified('backend', 'production')]
        assert node.evidence_kinds == ('FRAMEWORK_DERIVED',)
    assert all(p['hash_provenance'] == 'VALIDATED_CONTEXT_SOURCE' for p in view.provenance)
    assert all(p['content_hash'] == graph.files[p['source_file']] for p in view.provenance)
    assert (workspace, graph.to_dict(), coverage) == before
    assert ViewDocument.from_dict(json.loads(view.to_json())).content_fingerprint == view.content_fingerprint


def test_ac02_same_repo_test_controller_is_excluded_from_production(tmp_path):
    workspace, graph, coverage, entries = inputs(tmp_path)
    production = discover_process_triggers(workspace, graph, source_coverage=coverage)
    test = discover_process_triggers(workspace, graph, source_coverage=coverage, scope='test')
    assert len(production.nodes) == len(test.nodes) == 3
    assert not {x for n in production.nodes for x in n.original_ids} & {entries[('test', k)][0] for k in ANNOTATIONS}
    assert {n.attributes['entry_symbol_id'] for n in test.nodes} == {entries[('test', k)][0] for k in ANNOTATIONS}


def test_ac03_unsupported_scheduler_has_gap_and_no_fabricated_path(tmp_path):
    workspace, graph, coverage, entries = inputs(tmp_path); method, target, _ = entries[('production', 'scheduler')]
    graph.nodes = [replace(n, metadata={'entrypoint_kind': 'custom_scheduler'}) if n.id == target else n for n in graph.nodes]
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert {n.attributes['trigger_kind'] for n in view.nodes} == {'HTTP', 'KAFKA'}
    assert not view.edges and view.coverage['status'] == 'PARTIAL'
    assert any(d['code'] == 'TRIGGER_KIND_UNSUPPORTED' and d['source_id'] == method for d in view.diagnostics)


def test_unavailable_cfg_preserves_declared_candidate_and_explicit_body_gap(tmp_path):
    workspace, graph, coverage, _ = inputs(tmp_path)
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert len(view.nodes) == 3 and all(n.attributes['body_status'] == 'UNAVAILABLE' for n in view.nodes)
    assert sum(d['code'] == 'TRIGGER_BODY_UNAVAILABLE' for d in view.diagnostics) == 3
    assert not view.edges and view.coverage['status'] == 'PARTIAL'


@pytest.mark.parametrize('mutation', ['target_test', 'target_foreign_path', 'symbol_foreign_context',
    'target_context', 'target_metadata_scope', 'file_unknown', 'weak_edge', 'wrong_proof_source', 'wrong_proof_target',
    'wrong_proof_relation', 'wrong_proof_context', 'wrong_proof_file', 'wrong_fact_hash',
    'stale_proof', 'unknown_proof', 'fake_annotation'])
def test_scope_context_and_exact_fact_binding_never_borrow_other_trigger_proof(tmp_path, mutation):
    workspace, graph, coverage, entries = inputs(tmp_path); method, target, proof = entries[('production', 'http')]
    edge = next(e for e in graph.edges if e.source == method)
    record = next(p for p in graph.evidence if p['id'] == proof)
    if mutation == 'target_test': graph.nodes = [replace(n, scope='test') if n.id == target else n for n in graph.nodes]
    elif mutation == 'target_foreign_path': graph.nodes = [replace(n, path='@backend/src/test/java/demo/Entries.java') if n.id == target else n for n in graph.nodes]
    elif mutation == 'symbol_foreign_context': next(s for s in graph.symbols if s['id'] == method)['context_id'] = qualified('backend', 'test')
    elif mutation == 'target_context': graph.nodes = [replace(n, metadata={'context_id': 'foreign'}) if n.id == target else n for n in graph.nodes]
    elif mutation == 'target_metadata_scope': graph.nodes = [replace(n, metadata={'scope': 'test'}) if n.id == target else n for n in graph.nodes]
    elif mutation == 'file_unknown': graph.nodes = [replace(n, scope='unknown') if n.kind == 'file' and n.path == edge.source_file else n for n in graph.nodes]
    elif mutation == 'weak_edge':
        graph.edges = [replace(e, evidence_kind='SYNTAX_CANDIDATE') if e == edge else e for e in graph.edges]
        record['kind'] = 'SYNTAX_CANDIDATE'
    elif mutation.startswith('wrong_proof_'): record[mutation[len('wrong_proof_'):].replace('file', 'source_file')] = ('foreign' if mutation != 'wrong_proof_context' else [])
    elif mutation == 'wrong_fact_hash': record['sha256'] = '0' * 64
    elif mutation == 'stale_proof': record['freshness'] = 'STALE'
    elif mutation == 'unknown_proof': record['freshness'] = 'UNKNOWN'
    else: next(s for s in graph.symbols if s['id'] == method)['annotations'] = [{'name': 'fake.GetMapping'}]
    if mutation == 'wrong_proof_context': record['context_ids'] = []
    before = deepcopy(graph.to_dict())
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert not any(n.attributes['trigger_kind'] == 'HTTP' for n in view.nodes)
    assert graph.to_dict() == before and view.coverage['status'] in {'PARTIAL', 'UNKNOWN'}


def test_no_async_or_method_name_guess_creates_process_trigger(tmp_path):
    workspace, graph, coverage, entries = inputs(tmp_path); method, target, _ = entries[('production', 'scheduler')]
    next(s for s in graph.symbols if s['id'] == method)['annotations'] = [{'name': 'org.springframework.scheduling.annotation.Async'}]
    graph.nodes = [replace(n, name='handlePaymentScheduled', metadata={'entrypoint_kind': 'async_boundary'}) if n.id == target else n for n in graph.nodes]
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert len(view.nodes) == 2 and not any(n.attributes['entry_symbol_id'] == method for n in view.nodes)


def test_input_order_and_t023_trigger_node_compatibility(tmp_path):
    workspace, graph, coverage, _ = inputs(tmp_path)
    first = discover_process_triggers(workspace, graph, source_coverage=coverage)
    graph.nodes.reverse(); graph.edges.reverse(); graph.symbols.reverse(); graph.evidence.reverse(); graph.contexts.reverse()
    second = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert first.to_json() == second.to_json()
    technical = first.to_dict(); technical['view_id'] = 'process:caller-selected-draft'
    selected = {'schema_version': 1, 'process_id': technical['view_id'], 'revision': 1,
        'baseline_fingerprint': technical['baseline_fingerprint'], 'scope': 'production',
        'context_selection': technical['context_selection'], 'context_ids': [qualified('backend', 'production')],
        'trigger_ids': [n['id'] for n in technical['nodes']], 'semantic_review_status': 'PROPOSED'}
    definition = ProcessDefinition.from_dict(selected)
    process = ProcessView.from_dict({'schema_version': 1, 'process_id': selected['process_id'], 'revision': 1,
        'definition': definition.to_dict(), 'definition_fingerprint': definition.content_fingerprint,
        'technical_status': 'PARTIAL', 'technical_view': technical, 'entry_ids': selected['trigger_ids'],
        'exit_ids': [], 'outcome_ids': [], 'semantic_annotations': []})
    assert len(process.steps) == 3 and not process.transitions


def test_stale_source_and_invalid_graph_leave_last_valid_generation_unchanged(tmp_path):
    workspace, graph, coverage, _ = inputs(tmp_path); artifact = tmp_path / 'last-valid.json'; artifact.write_bytes(b'last valid')
    source = Path(workspace['repositories'][0]['_root']) / 'src/main/java/demo/Entries.java'
    source.write_text(source.read_text() + '// changed\n'); before = deepcopy((workspace, graph.to_dict(), coverage))
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert not view.nodes and any('STALE' in d['code'] for d in view.diagnostics)
    assert (workspace, graph.to_dict(), coverage) == before and artifact.read_bytes() == b'last valid'
    graph.edges.append(Edge('missing', 'missing', 'exposes_endpoint'))
    before = deepcopy(graph.to_dict())
    with pytest.raises(TriggerInventoryError): discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert graph.to_dict() == before and artifact.read_bytes() == b'last valid'


def api_jars():
    from kgmaker.worker_protocol import WorkerError
    repository = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', Path.home() / '.m2/repository'))
    lock = json.loads((ROOT / 'fixtures/process-triggers/dependencies.lock.json').read_text())
    jars = []
    for item in lock['artifacts']:
        for key, checksum in [('path', 'sha256'), ('artifact_pom', 'artifact_pom_sha256'), ('license_pom', 'license_pom_sha256')]:
            path = repository / item[key]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item[checksum]:
                raise WorkerError('Pinned trigger API/POM unavailable: ' + item['path'], 'TOOLCHAIN_UNAVAILABLE')
        name = ET.parse(repository / item['license_pom']).getroot().findtext('{http://maven.apache.org/POM/4.0.0}licenses/{http://maven.apache.org/POM/4.0.0}license/{http://maven.apache.org/POM/4.0.0}name')
        assert name == item['license_name']
        jars.append(str(repository / item['path']))
    return jars


def actual_prerequisites(backend):
    from kgmaker.inspection import command
    from kgmaker.worker_protocol import WorkerError
    try:
        jars = api_jars(); command('jvm', HOME, kotlin_backend=backend)
        stdlib = HOME / 'jvm' / ('target-k2' if backend == 'k2' else 'target') / 'lib/kotlin-stdlib.jar'
        if not stdlib.is_file():
            raise WorkerError('Matching worker Kotlin stdlib unavailable', 'TOOLCHAIN_UNAVAILABLE')
        jars.append(str(stdlib))
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1'):
            pytest.fail(str(error))
        pytest.skip(str(error))
    return jars


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_official_http_kafka_scheduler_and_test_scope_capture(tmp_path, backend):
    from kgmaker.inspection import inspect_jvm
    jars = actual_prerequisites(backend)
    root = tmp_path / 'backend'
    for part, name in [('main', 'Production'), ('test', 'TestOnly')]:
        source = root / f'src/{part}/kotlin/demo/{name}.kt'; source.parent.mkdir(parents=True)
        source.write_text(f'''package demo
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.scheduling.annotation.Scheduled
@RestController class {name} {{
 @GetMapping("/orders") fun http(): String = "static"
 @KafkaListener(topics=["orders"]) fun listen(value: String) {{ }}
 @Scheduled(fixedDelay=1000) fun tick() {{ }}
 fun ordinaryScheduledHandler() {{ }}
}}
''')
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, {'schema_version': 1, 'workspace_id': 'actual',
        'repositories': [{'id': 'backend', 'role': 'backend', 'path': 'backend'}],
        'services': [{'id': 'orders', 'backend_repo': 'backend', 'frontend_repos': [], 'test_repos': [],
            'contract': {'repo_id': 'backend', 'path': 'api.json'}}],
        'service_ownership': {'schema_version': 1, 'services': [{'id': 'orders',
            'roots': [{'repo_id': 'backend', 'path': 'src'}], 'modules': [{'repo_id': 'backend', 'id': 'app'}],
            'external_systems': []}]}})
    for scope, source_set in [('production', 'main'), ('test', 'test')]:
        result = inspect_jvm(root, home=HOME, repo_id='local', module='app', source_set=source_set, scope=scope,
            kotlin_backend=backend, classpath=jars, build_context={'spring_component_packages': ['demo']})
        assert not any('.err.' in d.get('code', '') or d.get('reason', '').startswith('ERROR:') for d in result['diagnostics'])
    workspace = load_workspace(manifest); _, coverage, _, graph, _ = snapshot_workspace(manifest)
    saved = {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('offline projection')):
        view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    if backend == 'k2':
        # This captured backend supplies no authoritative per-symbol annotations
        # or SOURCE CFG. The legacy framework fallback can attach preceding
        # annotations to an ordinary method; its edges alone are insufficient.
        # Reject those hints rather than infer annotation ownership from source.
        assert not view.nodes and view.coverage['status'] == 'UNKNOWN'
        assert any(d['code'] == 'TRIGGER_KIND_UNSUPPORTED' for d in view.diagnostics)
        assert not any(c.get('representation') == 'SOURCE' for c in graph.cfgs)
        ordinary = [s for s in graph.symbols if s.get('name') == 'ordinaryScheduledHandler']
        assert ordinary and all(not s.get('annotations') for s in ordinary)
        assert (workspace, graph.to_dict(), coverage) == before
        assert saved == {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
        return
    assert {n.attributes['trigger_kind'] for n in view.nodes} == {'HTTP', 'KAFKA', 'SCHEDULER'}
    assert len(view.nodes) == 3 and all('/src/main/' in p['source_file'] for p in view.provenance)
    # K1 expression bodies contain a synthetic return block without a captured
    # source locator. Candidate presence remains proved, body availability does
    # not get promoted by guessing ownership of that synthetic block.
    assert {n.attributes['trigger_kind']: n.attributes['body_status'] for n in view.nodes} == {
        'HTTP': 'UNAVAILABLE', 'KAFKA': 'AVAILABLE', 'SCHEDULER': 'AVAILABLE'}
    assert all(n.attributes['body_evidence_kinds'] == ([] if n.attributes['trigger_kind'] == 'HTTP'
        else ['SYNTAX_CANDIDATE']) for n in view.nodes)
    assert all(n.evidence_kinds == ('FRAMEWORK_DERIVED',) for n in view.nodes)
    assert not view.edges and view.coverage['status'] == 'PARTIAL'
    assert (workspace, graph.to_dict(), coverage) == before
    assert saved == {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
    # Independent-review regressions operate on the actual captured provider,
    # changing only one public field while retaining canonical source authority.
    http = next(n for n in view.nodes if n.attributes['trigger_kind'] == 'HTTP')
    handler = http.attributes['entry_symbol_id']; context_id = http.attributes['context_ids'][0]
    original_symbol = next(s for s in graph.symbols if s['id'] == handler)
    assert original_symbol.get('owner') and original_symbol.get('descriptor') and original_symbol.get('sha256')
    for mutation in ['symbol_hash', 'symbol_scope', 'symbol_name', 'symbol_descriptor', 'symbol_owner',
                     'symbol_range', 'edge_file', 'edge_line', 'edge_evidence_tuple', 'edge_duplicate_proof', 'proof_line']:
        altered = deepcopy(graph)
        symbol = next(s for s in altered.symbols if s['id'] == handler)
        edge = next(e for e in altered.edges if e.source == handler and e.kind == 'exposes_endpoint' and e.context_ids == (context_id,))
        if mutation == 'symbol_hash': symbol['sha256'] = '0' * 64
        elif mutation == 'symbol_scope': symbol['scope'] = 'test'
        elif mutation == 'symbol_name': symbol['name'] = 'forgedHandler'
        elif mutation == 'symbol_descriptor': symbol['descriptor'] = '()V'
        elif mutation == 'symbol_owner': symbol['owner'] = 'foreign.Handler'
        elif mutation == 'symbol_range': symbol['range']['start_line'] += 100
        elif mutation == 'proof_line': next(p for p in altered.evidence if p['id'] == edge.evidence_ids[0])['source_line'] = edge.source_line + 100
        else:
            if mutation == 'edge_file': changed = replace(edge, source_file='@backend/src/test/kotlin/demo/TestOnly.kt')
            elif mutation == 'edge_line': changed = replace(edge, source_line=edge.source_line + 100)
            elif mutation == 'edge_duplicate_proof': changed = replace(edge, evidence_ids=edge.evidence_ids * 2)
            else:
                other = next(e for e in altered.edges if e.kind == 'declares_entrypoint' and e.context_ids == (context_id,))
                changed = replace(edge, evidence_ids=other.evidence_ids)
            altered.edges = [changed if e == edge else e for e in altered.edges]
        altered_before = deepcopy(altered.to_dict())
        with patch('subprocess.Popen', side_effect=AssertionError('offline negative projection')):
            rejected = discover_process_triggers(workspace, altered, source_coverage=coverage)
        assert not any(n.attributes['trigger_kind'] == 'HTTP' for n in rejected.nodes), mutation
        assert {n.attributes['trigger_kind'] for n in rejected.nodes} == {'KAFKA', 'SCHEDULER'}, mutation
        assert altered.to_dict() == altered_before and saved == {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
    malformed = deepcopy(graph)
    next(c for c in malformed.cfgs if c['method'] == handler and c['context_id'] == context_id)['blocks'] = {}
    with pytest.raises(TriggerInventoryError): discover_process_triggers(workspace, malformed, source_coverage=coverage)


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_missing_pinned_apis_fail_mandatory_before_worker_probe(tmp_path, monkeypatch, backend):
    monkeypatch.setenv('KGMAKER_TEST_MAVEN_REPOSITORY', str(tmp_path)); monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', '1')
    with patch('kgmaker.inspection.command', side_effect=AssertionError('no worker probe before API preflight')):
        with pytest.raises(pytest.fail.Exception, match='Pinned trigger API/POM unavailable'):
            actual_prerequisites(backend)


@pytest.mark.parametrize('field,value', [('sha256', '0' * 64), ('scope', 'test'), ('name', 'foreign'),
    ('descriptor', []), ('owner', {}), ('kind', 'constructor')])
def test_canonical_source_symbol_contradictions_fail_closed_on_explicit_inputs(tmp_path, field, value):
    workspace, graph, coverage, entries = inputs(tmp_path)
    method = entries[('production', 'http')][0]
    next(s for s in graph.symbols if s['id'] == method)[field] = value
    before = deepcopy(graph.to_dict()); result = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert not any(n.attributes['trigger_kind'] == 'HTTP' for n in result.nodes)
    assert graph.to_dict() == before


@pytest.mark.parametrize('value', [None, {}, 3, [None]])
def test_malformed_cfg_blocks_produce_structured_error_without_store_mutation(tmp_path, value):
    workspace, graph, coverage, entries = inputs(tmp_path)
    method = entries[('production', 'http')][0]; cid = qualified('backend', 'production')
    graph.cfgs.append({'method': method, 'context_id': cid, 'representation': 'SOURCE',
        'version': 'source-cfg-1', 'entry': 'entry', 'exit': 'exit', 'blocks': value, 'edges': []})
    before = deepcopy(graph.to_dict()); artifact = tmp_path / 'last-valid.json'; artifact.write_bytes(b'unchanged')
    with pytest.raises(TriggerInventoryError): discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert graph.to_dict() == before and artifact.read_bytes() == b'unchanged'


@pytest.mark.parametrize('value', [[], '', False, 0])
def test_malformed_endpoint_metadata_is_not_treated_as_missing_legacy_metadata(tmp_path, value):
    workspace, graph, coverage, entries = inputs(tmp_path); target = entries[('production', 'http')][1]
    graph.nodes = [replace(n, metadata=value) if n.id == target else n for n in graph.nodes]
    before = deepcopy(graph.to_dict()); result = discover_process_triggers(workspace, graph, source_coverage=coverage)
    assert not any(n.attributes['trigger_kind'] == 'HTTP' for n in result.nodes) and graph.to_dict() == before

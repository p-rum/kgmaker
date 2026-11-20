"""Compiler facts for local operations, separate from syntax/control ordering."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.inspection import command
from kgmaker.worker_protocol import WorkerError, request_worker

ROOT = Path(__file__).resolve().parents[1]
HOME = Path(os.environ.get('KGMAKER_WORKERS_HOME', ROOT / 'workers'))
SOURCE = '''package sample;
class Demo {
 int field;
 public static void main(String[] args) {
   int first = 1;
   int second = 2;
   String text = "safe";
   first = 3;
 }
 void boundaries() {
   this.field = 1;
   Integer boxed = 2;
   int fromCall = other();
   int cast = (int) 2.5;
 }
 static int other() { return 1; }
}
'''


@pytest.fixture(scope='module', params=['k1', 'k2'])
def captured(request, tmp_path_factory):
    root = tmp_path_factory.mktemp('local-operation-' + request.param)
    path = root / 'src/main/java/sample/Demo.java'
    path.parent.mkdir(parents=True)
    path.write_text(SOURCE)
    relative = path.relative_to(root).as_posix()
    context = {'id': 'local-operations-' + request.param, 'repo_id': 'fixture',
               'module': 'app', 'source_set': 'main', 'scope': 'production',
               'local_operation_rule_version': 'java-local-operations-1',
               'source_files': {relative: hashlib.sha256(path.read_bytes()).hexdigest()}}
    try:
        response = request_worker(command('jvm', HOME, kotlin_backend=request.param),
            {'operation': 'analyze', 'root': str(root), 'context': context,
             'sources': [relative], 'classpath': [], 'kotlin_backend': request.param,
             'kotlin_version': '2.1.10'}, cwd=root)
    except WorkerError as error:
        if error.status != 'TOOLCHAIN_UNAVAILABLE':
            raise
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or os.environ.get('KGMAKER_REQUIRE_K2') == '1':
            pytest.fail(str(error))
        pytest.skip(str(error))
    assert not any('.err.' in d.get('code', '') for d in response['diagnostics']), response['diagnostics']
    assert not (root / '.kgmaker').exists()
    return response, context


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_actual_java_local_literal_witness_is_an_optional_typed_contract(captured):
    response, _ = captured
    body = next(b for b in response['bodies'] if '.main(' in b['method'])
    assert body.get('local_operation_version') == 1
    assert body.get('local_operation_status') == 'AVAILABLE'
    assignments = [n for n in walk(body['body']) if n.get('kind') == 'assign']
    assert len(assignments) == 4
    assert all(n.get('local_operation', {}).get('operation') == 'LOCAL_LITERAL_ASSIGNMENT' for n in assignments)
    assert {n['local_operation']['target_type'] for n in assignments} == {'I', 'Ljava/lang/String;'}
    assert all(n['binding']['kind'] == 'LOCAL_VARIABLE' for n in assignments)
    boundary = next(b for b in response['bodies'] if '.boundaries(' in b['method'])
    assert not any(n.get('local_operation') for n in walk(boundary['body']) if n.get('kind') == 'assign')


def test_legacy_ir_stays_readable_without_operation_proof(captured):
    from kgmaker.local_operations import validate_operations
    response, context = captured
    legacy = deepcopy(response)
    for body in legacy['bodies']:
        body.pop('local_operation_version', None)
        body.pop('local_operation_status', None)
        for node in walk(body.get('body', {})):
            node.pop('local_operation', None)
    before = deepcopy(legacy)
    assert validate_operations(legacy, context) == []
    assert legacy == before


def protocol_specimen():
    """Explicit protocol input, not a claim that a compiler was executed."""
    path, sha = 'src/Demo.java', '1' * 64
    def span(start, end):
        return {'start': start, 'end': end, 'start_line': 1, 'end_line': 1,
                'start_column': start + 1, 'end_column': end + 1}
    declaration = {'path': path, 'sha256': sha, 'range': span(20, 30)}
    binding = 'binding:ctx:src/Demo.java:' + sha + ':20:30'
    literal = {'kind': 'statement', 'path': path, 'sha256': sha, 'range': span(28, 29), 'calls': [],
        'literal': {'source': 'COMPILER_LITERAL', 'type': 'INT_LITERAL', 'value': 1},
        'local_operation': {'schema_version': 1, 'operation': 'LITERAL_EVALUATION',
            'target_type': 'I', 'target_binding': None, 'target_declaration': None}}
    assign = {'kind': 'assign', 'path': path, 'sha256': sha, 'range': span(20, 30), 'calls': [],
        'binding': {'id': binding, 'kind': 'LOCAL_VARIABLE', 'type': 'I', 'declaration': declaration},
        'local_operation': {'schema_version': 1, 'operation': 'LOCAL_LITERAL_ASSIGNMENT',
            'target_type': 'I', 'target_binding': binding, 'target_declaration': deepcopy(declaration)},
        'value': literal}
    method = 'jvm:fixture:app:main:ctx:method:Demo.run()V'
    response = {'symbols': [{'id': method, 'kind': 'method', 'name': 'run', 'owner': 'Demo', 'descriptor': '()V', 'context_id': 'ctx',
                    'path': path, 'sha256': sha, 'scope': 'production', 'range': span(0, 100)}],
        'bodies': [{'method': method, 'context_id': 'ctx', 'language': 'java',
            'local_operation_version': 1, 'local_operation_status': 'AVAILABLE',
            'body': {'kind': 'block', 'statements': [assign]}}]}
    context = {'id': 'ctx', 'repo_id': 'fixture', 'module': 'app', 'source_set': 'main', 'scope': 'production', 'source_files': {path: sha},
               'local_operation_rule_version': 'java-local-operations-1'}
    return response, context


@pytest.mark.parametrize('origin', [None, 'handwritten', 'generated'])
def test_explicit_protocol_preserves_two_distinct_operation_occurrences(origin):
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen()
    if origin is not None:
        node = response['bodies'][0]['body']['statements'][0]
        node['binding']['declaration']['origin'] = origin
        node['local_operation']['target_declaration']['origin'] = origin
    before = deepcopy((response, context))
    records = validate_operations(response, context)
    assert [r['operation'] for r in records] == ['LOCAL_LITERAL_ASSIGNMENT', 'LITERAL_EVALUATION']
    assert [r['ir_path'] for r in records] == [['statements', 0], ['statements', 0, 'value']]
    assert len({r['operation_ref'] for r in records}) == 2
    assert (response, context) == before


@pytest.mark.parametrize('refs', [None, 'proof', [None], ['proof', 1], ['proof', 'other-proof']])
def test_scope_projection_preserves_invalid_operation_shape_for_fail_closed_validation(refs):
    from kgmaker.model import KnowledgeGraph, Node
    from kgmaker.views import project
    graph = KnowledgeGraph(3, '/fixture', 'now',
        [Node('method', 'method', 'run', 'Demo.java', scope='production')], [], {},
        contexts=[{'id': 'ctx', 'scope': 'production'}],
        evidence=[{'id': 'proof', 'kind': 'SYMBOL_RESOLVED'}],
        cfgs=[{'method': 'method', 'context_id': 'ctx', 'blocks': [
            {'local_operation_version': 1, 'local_operation_evidence_ids': deepcopy(refs)}]}])
    before = deepcopy(graph.to_dict())
    selected = project(graph, 'production', context_id='ctx')
    assert selected.cfgs[0]['blocks'][0]['local_operation_evidence_ids'] == refs
    assert selected.evidence == []
    assert graph.to_dict() == before


@pytest.mark.parametrize('change', ['field', 'boxed', 'missing_hash', 'foreign_hash', 'literal_outside',
    'target_identity', 'literal_reference', 'body_version', 'reserved_ref', 'nonblock_body',
    'string_to_int', 'int_overflow', 'empty_literal', 'columns_reversed', 'long_to_int', 'char_overflow', 'calls_shape', 'foreign_origin'])
def test_malformed_or_unsupported_protocol_cannot_mint_operation_proof(change):
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen(); body = response['bodies'][0]
    node = body['body']['statements'][0]
    if change == 'foreign_origin':
        node['binding']['declaration']['origin'] = 'dependency'
        node['local_operation']['target_declaration']['origin'] = 'dependency'
    elif change == 'field': node['binding']['kind'] = 'FIELD'
    elif change == 'boxed': node['local_operation']['target_type'] = 'Ljava/lang/Integer;'
    elif change == 'missing_hash': context['source_files'].clear(); response['symbols'][0]['sha256'] = None
    elif change == 'foreign_hash': node['value']['sha256'] = '2' * 64
    elif change == 'literal_outside': node['value']['range']['end'] = 40
    elif change == 'target_identity': node['local_operation']['target_binding'] = 'binding:borrowed'
    elif change == 'literal_reference': node['value']['binding_ref'] = {'kind': 'FIELD'}
    elif change == 'body_version': body['local_operation_version'] = True
    elif change == 'reserved_ref': node['_verified_local_operation'] = 'borrowed'
    elif change == 'nonblock_body': body['body'] = node
    elif change == 'string_to_int':
        node['value']['literal'].update(type='STRING_LITERAL', value='text')
        node['value']['local_operation']['target_type'] = 'Ljava/lang/String;'
    elif change == 'int_overflow': node['value']['literal']['value'] = 2 ** 70
    elif change == 'empty_literal': node['value']['range']['end'] = node['value']['range']['start']
    elif change == 'columns_reversed': node['value']['range']['end_column'] = 1
    elif change == 'long_to_int':
        node['value']['literal']['type'] = 'LONG_LITERAL'
        node['value']['local_operation']['target_type'] = 'J'
    elif change == 'char_overflow':
        node['value']['literal'].update(type='CHAR_LITERAL', value=chr(0x10000))
        node['value']['local_operation']['target_type'] = 'C'
    elif change == 'calls_shape': node['calls'] = None
    before = deepcopy((response, context))
    with pytest.raises(ValueError): validate_operations(response, context)
    assert (response, context) == before


@pytest.mark.parametrize('target,value,allowed', [('B', 127, True), ('B', 128, False),
    ('S', -32768, True), ('S', -32769, False), ('C', 65535, True), ('C', -1, False),
    ('J', 2 ** 31 - 1, True), ('D', 1, True)])
def test_primitive_literal_assignment_conversion_boundaries(target, value, allowed):
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen(); node = response['bodies'][0]['body']['statements'][0]
    node['binding']['type'] = target
    node['local_operation']['target_type'] = target
    node['value']['literal']['value'] = value
    if allowed:
        assert len(validate_operations(response, context)) == 2
    else:
        with pytest.raises(ValueError): validate_operations(response, context)


def test_workspace_proof_hash_undoes_only_the_verified_repository_wrapper():
    from kgmaker.analysis_model import digest
    from kgmaker.local_operations import _original_proof
    from kgmaker.workspace import _qualified_evidence
    proof = {'kind': 'SYMBOL_RESOLVED', 'source': 'method:one', 'target': 'method:one',
        'method': 'method:one', 'compiler_symbol_id': 'method:one', 'cfg_block': 'cfg:one',
        'context_id': 'ctx', 'context_ids': ['ctx'], 'source_file': 'src/App.java',
        'local_operation_version': 1, 'target_binding': None, 'target_declaration': None}
    proof['id'] = 'evidence:local-operation:' + digest(proof)
    wrapped = _qualified_evidence('backend', proof)
    assert _original_proof(wrapped, {'repo_id': 'backend'}) == proof
    wrapped['repo_id'] = 'foreign'
    with pytest.raises(ValueError): _original_proof(wrapped, {'repo_id': 'backend'})


@pytest.mark.parametrize('value,allowed', [(3.4028235e38, True), (1.4e-45, True),
    (1e39, False), (1e-60, False), (float('inf'), False)])
def test_float_literal_json_rounding_preserves_java_bounds(value, allowed):
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen(); node = response['bodies'][0]['body']['statements'][0]
    node['binding']['type'] = 'F'; node['local_operation']['target_type'] = 'F'
    node['value']['literal'].update(type='FLOAT_LITERAL', value=value)
    node['value']['local_operation']['target_type'] = 'F'
    if allowed:
        assert len(validate_operations(response, context)) == 2
    else:
        with pytest.raises(ValueError): validate_operations(response, context)


@pytest.fixture(scope='module', params=['k1', 'k2'])
def pipeline(request, tmp_path_factory):
    import json
    from kgmaker.inspection import inspect_jvm
    from kgmaker.workspace import load_workspace, snapshot_workspace
    from kgmaker.process_triggers import discover_process_triggers
    from test_t024_discover_process_triggers import actual_prerequisites
    jars = actual_prerequisites(request.param)
    base = tmp_path_factory.mktemp('local-operation-pipeline-' + request.param)
    root = base / 'backend'; folder = root / 'src/main/java/sample'; folder.mkdir(parents=True)
    (folder / 'Controller.java').write_text('''package sample;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
@RestController public class Controller {
 int field;
 @GetMapping("/local") public int entry() {
   int first = 1;
   int second = 2;
   first = 3;
   return first + second;
 }
 @GetMapping("/unsafe") public void unsafe() {
   this.field = 1;
   Integer boxed = 2;
   int called = helper();
   int cast = (int) 2.5;
 }
 private static int helper() { return 1; }
 @GetMapping("/finally") public int cleanup(boolean flag) {
   try { if(flag) return 1; return 2; }
   finally { int clean = 3; }
 }
}
''')
    (root / 'api.json').write_text('{}')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    result = inspect_jvm(root, home=HOME, classpath=jars, kotlin_backend=request.param,
                         repo_id='backend', module='app', publish=True)
    assert not any('.err.' in d.get('code', '') for d in result['diagnostics']), result['diagnostics']
    manifest = base / 'workspace.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'workspace_id': 'local-operations',
        'repositories': [{'id': 'backend', 'role': 'backend', 'path': 'backend'}],
        'services': [{'id': 'app', 'backend_repo': 'backend', 'frontend_repos': [], 'test_repos': [],
                      'contract': {'repo_id': 'backend', 'path': 'api.json'}}],
        'service_ownership': {'schema_version': 1, 'services': [{'id': 'app',
            'roots': [{'repo_id': 'backend', 'path': 'src'}], 'modules': [], 'external_systems': []}]}}))
    workspace = load_workspace(manifest); _, coverage, _, graph, _ = snapshot_workspace(manifest)
    inventory = discover_process_triggers(workspace, graph, source_coverage=coverage)
    names = {s['id']: s['name'] for s in graph.symbols}
    triggers = {names[n.attributes['entry_symbol_id']]: n for n in inventory.nodes if n.kind == 'trigger'}
    assert set(triggers) == {'entry', 'unsafe', 'cleanup'}
    return graph, inventory, triggers, root


def test_actual_workspace_process_resolves_only_operations_not_control_order(pipeline):
    from kgmaker.process_paths import build_local_process
    from kgmaker.process_model import ProcessView
    graph, inventory, triggers, _ = pipeline; before = deepcopy(graph.to_dict())
    with patch('subprocess.Popen', side_effect=AssertionError('process projection must stay offline')):
        result = build_local_process(graph, inventory, triggers['entry'].id, process_id='process:locals')
    operations = [n for n in result.steps if n.attributes.get('local_operation')]
    assert len(operations) == 6  # three attributed assignments and their literal evaluations
    assert all(n.resolution_status == 'RESOLVED' and n.evidence_kinds == ('SYMBOL_RESOLVED',) for n in operations)
    assert all(n.attributes['cfg_evidence_refs'] for n in operations)
    control = [e for e in result.transitions if e.source in {n.id for n in operations} or e.target in {n.id for n in operations}]
    assert control and all(e.resolution_status == 'UNRESOLVED' and 'SYNTAX_CANDIDATE' in e.evidence_kinds for e in control)
    assert ProcessView.from_dict(result.to_dict()).to_dict() == result.to_dict()
    unsafe = build_local_process(graph, inventory, triggers['unsafe'].id, process_id='process:unsafe')
    unsafe_assignments = [n for n in unsafe.steps if n.label == 'assign']
    assert unsafe_assignments and all(n.resolution_status == 'UNRESOLVED' for n in unsafe_assignments)
    assert graph.to_dict() == before


def test_actual_finally_operations_keep_distinct_structural_block_proofs(pipeline):
    from kgmaker.process_paths import build_local_process
    graph, inventory, triggers, _ = pipeline
    result = build_local_process(graph, inventory, triggers['cleanup'].id, process_id='process:finally-operations')
    groups = {}
    for node in result.steps:
        certificate = node.attributes.get('local_operation')
        if certificate:
            groups.setdefault(certificate['operation_ref'], []).append(certificate)
    clones = [values for values in groups.values() if len(values) > 1]
    assert clones
    assert all(len({v['cfg_block'] for v in values}) == len(values) for values in clones)
    assert all(len({v['original_proof_id'] for v in values}) == len(values) for values in clones)


@pytest.mark.parametrize('change', ['proof_hash', 'missing_ref', 'foreign_block', 'missing_sha', 'wrong_rule', 'borrow_origin'])
def test_actual_selected_operation_tampering_never_upgrades_a_process(pipeline, change):
    from kgmaker.process_paths import build_local_process, ProcessPathError
    graph, inventory, triggers, root = pipeline; graph = deepcopy(graph)
    method = triggers['entry'].attributes['entry_symbol_id']
    cfg = next(c for c in graph.cfgs if c['method'] == method and c['representation'] == 'SOURCE')
    block = next(b for b in cfg['blocks'] if b.get('local_operation_evidence_ids'))
    proof = next(p for p in graph.evidence if p['id'] == block['local_operation_evidence_ids'][0])
    if change == 'proof_hash': proof['target_type'] = 'J'
    elif change == 'missing_ref': block['local_operation_evidence_ids'] = []
    elif change == 'foreign_block': proof['cfg_block'] = 'foreign:cfg-block'
    elif change == 'missing_sha': proof['sha256'] = None
    elif change == 'wrong_rule': proof['rules_version'] = 'unproved-future-version'
    elif change == 'borrow_origin':
        other = next(b for b in cfg['blocks'] if b['id'] != block['id'] and b.get('local_operation_evidence_ids'))
        block['local_operation_evidence_ids'] = other['local_operation_evidence_ids'][:]
    before = deepcopy(graph.to_dict()); saved = (root / '.kgmaker/graph.json').read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('invalid process projection must stay offline')):
        with pytest.raises(ProcessPathError):
            build_local_process(graph, inventory, triggers['entry'].id, process_id='process:tampered')
    assert graph.to_dict() == before
    assert (root / '.kgmaker/graph.json').read_bytes() == saved

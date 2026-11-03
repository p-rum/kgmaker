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


def test_explicit_protocol_preserves_two_distinct_operation_occurrences():
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen(); before = deepcopy((response, context))
    records = validate_operations(response, context)
    assert [r['operation'] for r in records] == ['LOCAL_LITERAL_ASSIGNMENT', 'LITERAL_EVALUATION']
    assert [r['ir_path'] for r in records] == [['statements', 0], ['statements', 0, 'value']]
    assert len({r['operation_ref'] for r in records}) == 2
    assert (response, context) == before


@pytest.mark.parametrize('change', ['field', 'boxed', 'missing_hash', 'foreign_hash', 'literal_outside',
    'target_identity', 'literal_reference', 'body_version', 'reserved_ref', 'nonblock_body'])
def test_malformed_or_unsupported_protocol_cannot_mint_operation_proof(change):
    from kgmaker.local_operations import validate_operations
    response, context = protocol_specimen(); body = response['bodies'][0]
    node = body['body']['statements'][0]
    if change == 'field': node['binding']['kind'] = 'FIELD'
    elif change == 'boxed': node['local_operation']['target_type'] = 'Ljava/lang/Integer;'
    elif change == 'missing_hash': context['source_files'].clear(); response['symbols'][0]['sha256'] = None
    elif change == 'foreign_hash': node['value']['sha256'] = '2' * 64
    elif change == 'literal_outside': node['value']['range']['end'] = 40
    elif change == 'target_identity': node['local_operation']['target_binding'] = 'binding:borrowed'
    elif change == 'literal_reference': node['value']['binding_ref'] = {'kind': 'FIELD'}
    elif change == 'body_version': body['local_operation_version'] = True
    elif change == 'reserved_ref': node['_verified_local_operation'] = 'borrowed'
    elif change == 'nonblock_body': body['body'] = node
    before = deepcopy((response, context))
    with pytest.raises(ValueError): validate_operations(response, context)
    assert (response, context) == before


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

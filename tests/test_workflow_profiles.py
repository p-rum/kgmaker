"""Profile handoffs reuse task persistence; commands are never executed here."""
from copy import deepcopy
import json

import pytest

from kgmaker.analysis_model import digest
from kgmaker.cli import main
from kgmaker.context import ContextError, prepare_packet
from kgmaker.workflow import (WorkflowError, add_task, advance_task, create_task,
                              load_task, record_artifact, save_task, stop_task, task_id, task_path, validate_task)
from kgmaker.workflow_profiles import CONFIG_PATH, catalog, select_profile


def configure(root, **overrides):
    config = {'schema_version': 1, 'default': 'team', 'profiles': {
        'team': {'extends': 'existing-feature', 'validations': [
            {'label': 'unit', 'command': 'python -m unittest discover'}], **overrides}}}
    path = root / CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config), encoding='utf-8')
    return path


def artifact(root, task, phase, **changes):
    role = {'analyze': 'architect', 'plan': 'architect', 'implement': 'implementation',
            'test': 'test_expert', 'review': 'review'}[phase]
    value = {'summary': f'Completed {phase}', 'status': 'completed', 'cited_paths': [],
             'cited_node_ids': [], 'packet_id': None, 'disposition': None}
    if phase == 'plan':
        value.update(steps=[{'id': 'one', 'intent': 'Small change', 'paths': ['app.py'],
                             'tests': ['tests/test_app.py']}], out_of_scope=[])
    if phase == 'implement':
        value.update(changed_paths=['app.py'], notes='Updated local source')
    if phase == 'test':
        value['validations'] = [{'label': 'unit', 'command': 'python -m unittest discover', 'status': 'passed'}]
    if phase == 'review':
        value.update(overall='approve', findings=[])
    value.update(changes)
    return record_artifact(root, task['id'], role, value)


def reach(root, phase='test', workflow='existing-feature'):
    task = add_task(root, 'Connect workflow', workflow=workflow)
    for current in ('analyze', 'plan', 'implement', 'test', 'review'):
        task = advance_task(root, task['id'], current)
        if phase == current:
            return task
        task = artifact(root, task, current)
    raise AssertionError(phase)


def test_legacy_identity_and_profile_snapshot_survive_config_change(tmp_path):
    old = create_task(tmp_path, 'request')
    assert old['schema_version'] == 1
    assert old['id'] == task_id(old['title'], old['request'], 3, None)
    path = configure(tmp_path, max_iterations=2, token_budget=5000)
    task = add_task(tmp_path, 'request')
    assert task['schema_version'] == 3 and task['max_iterations'] == 2
    assert add_task(tmp_path, 'request') == task
    packet = prepare_packet(tmp_path, task, 'implementation', persist=False)
    assert packet['token_budget'] == 5000
    path.unlink()
    assert load_task(tmp_path, task['id']) == task
    assert prepare_packet(tmp_path, task, 'implementation', persist=False)['workflow'] == packet['workflow']
    assert create_task(tmp_path, 'request', workflow='bugfix')['id'] != task['id']


@pytest.mark.parametrize('bad', [
    '{"schema_version":1,"schema_version":1,"default":null,"profiles":{}}',
    '{"schema_version":true,"default":null,"profiles":{}}',
    '{"schema_version":9,"default":null,"profiles":{}}',
    '{"schema_version":1,"default":"missing","profiles":{}}',
    '{"schema_version":1,"default":null,"profiles":{"bad":{"extends":"bugfix","execute":"echo x"}}}',
    '{"schema_version":1,"default":null,"profiles":{"bad":{"extends":"bugfix","max_iterations":true}}}',
    '{"schema_version":1,"default":null,"profiles":{"bad":{"extends":[]}}}',
    '{"schema_version":1,"default":null,"profiles":{"bad":{"extends":"bugfix","instructions":{"admin":[]}}}}',
])
def test_invalid_configuration_has_no_mutation(tmp_path, bad):
    path = tmp_path / CONFIG_PATH
    path.parent.mkdir()
    path.write_text(bad)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):
        add_task(tmp_path, 'request')
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before


def test_symlink_configuration_rejected_and_commands_are_data(tmp_path):
    outside = tmp_path / 'outside.json'
    outside.write_text('{}')
    path = tmp_path / CONFIG_PATH
    path.parent.mkdir()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match='Symlink'):
        catalog(tmp_path)
    path.unlink()
    configure(tmp_path, validations=[{'label': 'never', 'command': 'touch MUST_NOT_EXIST'}])
    catalog(tmp_path)
    task = add_task(tmp_path, 'request')
    prepare_packet(tmp_path, task, 'test_expert')
    assert not (tmp_path / 'MUST_NOT_EXIST').exists()


def test_direct_save_cannot_skip_handoff_or_rewrite_snapshot(tmp_path):
    task = add_task(tmp_path, 'request', workflow='bugfix')
    task = advance_task(tmp_path, task['id'], 'analyze')
    before = task_path(tmp_path, task['id']).read_bytes()
    invalid = {**task, 'status': 'plan'}
    with pytest.raises(WorkflowError, match='architect/analyze'):
        save_task(tmp_path, invalid, expected_revision=digest(task))
    assert task_path(tmp_path, task['id']).read_bytes() == before
    invalid = deepcopy(task)
    invalid['workflow']['profile']['instructions']['architect'] = ['changed']
    invalid['workflow']['sha256'] = digest({k:v for k,v in invalid['workflow'].items() if k != 'sha256'})
    with pytest.raises(WorkflowError):
        save_task(tmp_path, invalid, expected_revision=digest(task))
    assert task_path(tmp_path, task['id']).read_bytes() == before
    assert stop_task(tmp_path, task['id'], 'User cancelled')['status'] == 'failed'


@pytest.mark.parametrize('status', ['failed', 'skipped', 'unknown'])
def test_required_validation_needs_pass_and_retry_is_available(tmp_path, status):
    configure(tmp_path)
    task = reach(tmp_path, workflow='team')
    task = artifact(tmp_path, task, 'test', validations=[
        {'label': 'unit', 'command': 'python -m unittest discover', 'status': status}])
    before = task_path(tmp_path, task['id']).read_bytes()
    with pytest.raises(WorkflowError):
        advance_task(tmp_path, task['id'], 'review')
    assert task_path(tmp_path, task['id']).read_bytes() == before
    assert advance_task(tmp_path, task['id'], 'implement')['iteration'] == 1


def test_command_mismatch_and_unrelated_pass_do_not_satisfy_required_check(tmp_path):
    configure(tmp_path)
    task = reach(tmp_path, workflow='team')
    task = artifact(tmp_path, task, 'test', validations=[{'label': 'unit', 'command': 'echo pass', 'status': 'passed'}])
    with pytest.raises(WorkflowError, match='required validation'):
        advance_task(tmp_path, task['id'], 'review')


@pytest.mark.parametrize('phase', ['test', 'review'])
def test_changed_sources_invalidate_test_and_review(tmp_path, phase):
    source = tmp_path / 'app.py'
    source.write_text('def value(): return 1\n')
    task = reach(tmp_path, phase=phase)
    task = artifact(tmp_path, task, phase)
    source.write_text('def value(): return 2\n')
    with pytest.raises(WorkflowError, match='stale'):
        advance_task(tmp_path, task['id'], 'review' if phase == 'test' else 'done')


@pytest.mark.parametrize('profile', ['greenfield', 'existing-feature', 'bugfix'])
def test_complete_profiled_cycle_without_graph_and_schema_preservation(tmp_path, profile):
    task = reach(tmp_path, phase='review', workflow=profile)
    assert task['schema_version'] == 3
    task = artifact(tmp_path, task, 'review')
    task = advance_task(tmp_path, task['id'], 'done')
    assert task['status'] == 'done'
    assert task['schema_version'] == 3
    bound = {a['phase'] for a in task['artifacts'] if a['id'] in task['delivery']['bindings']}
    assert bound == {'implement', 'test', 'review'}


def test_open_major_review_blocks_completion(tmp_path):
    task = reach(tmp_path, phase='review')
    task = artifact(tmp_path, task, 'review', findings=[
        {'severity': 'major', 'path': 'app.py', 'summary': 'Mismatch', 'disposition': 'open'}])
    with pytest.raises(WorkflowError, match='review approval'):
        advance_task(tmp_path, task['id'], 'done')


def test_role_packet_preserves_workflow_and_rejects_insufficient_budget(tmp_path):
    task = add_task(tmp_path, 'request', workflow='bugfix')
    with pytest.raises(ContextError, match='budget'):
        prepare_packet(tmp_path, task, 'architect', token_budget=128)
    assert not (tmp_path / '.kgmaker/workflow/packets').exists()
    packet = prepare_packet(tmp_path, task, 'architect')
    assert packet['token_estimate'] <= packet['token_budget']
    assert packet['workflow']['instructions'] == task['workflow']['profile']['instructions']['architect']
    markdown = next((tmp_path / '.kgmaker/workflow/packets').glob('*.md')).read_text()
    assert task['workflow']['sha256'] in markdown


def test_cli_profile_commands_and_task_default(tmp_path, capsys, monkeypatch):
    def invoke(args):
        monkeypatch.setattr('sys.argv', ['kgmaker', *args])
        main()
    configure(tmp_path)
    for command in [('workflow', 'list'), ('workflow', 'check'), ('workflow', 'show', 'team')]:
        with pytest.raises(SystemExit) as exit_info:
            invoke([*command, '--root', str(tmp_path)])
        assert exit_info.value.code == 0
        assert json.loads(capsys.readouterr().out)
    with pytest.raises(SystemExit) as exit_info:
        invoke(['task', 'add', 'CLI request', '--workflow', 'greenfield', '--root', str(tmp_path)])
    assert exit_info.value.code == 0
    identifier = capsys.readouterr().out.splitlines()[0]
    assert load_task(tmp_path, identifier)['workflow']['name'] == 'greenfield'
    with pytest.raises(SystemExit) as exit_info:
        invoke(['workflow', 'show', 'unknown', '--root', str(tmp_path)])
    assert exit_info.value.code == 2


@pytest.mark.parametrize('version', [[], {}, True, None, '3'])
def test_invalid_task_version_uses_contract_error(tmp_path, version):
    task = create_task(tmp_path, 'request')
    task['schema_version'] = version
    with pytest.raises(WorkflowError, match='schema_version'):
        validate_task(task)


def test_example_configuration_and_init_instruction_parity(tmp_path):
    from pathlib import Path
    from kgmaker.cli import init
    from kgmaker.delivery_instructions import DELIVERY_INSTRUCTIONS
    root = Path(__file__).resolve().parents[1]
    (tmp_path / '.kgmaker').mkdir()
    (tmp_path / CONFIG_PATH).write_bytes((root / 'examples/workflows/python-project.json').read_bytes())
    assert select_profile(tmp_path)['name'] == 'team-feature'
    init(tmp_path)
    paths = [Path(f'.github/agents/kgmaker-{name}.agent.md') for name in
             ('orchestrator', 'implementation', 'test-expert', 'review', 'analyst')]
    paths += [Path('.junie/commands/kgmaker-analyze-feature.md'), Path('.github/copilot-instructions.md')]
    for path in paths:
        assert DELIVERY_INSTRUCTIONS.strip() in (tmp_path / path).read_text()
        assert DELIVERY_INSTRUCTIONS.strip() in (root / path).read_text()
    custom = tmp_path / '.github/copilot-instructions.md'
    custom.write_text('My instructions')
    init(tmp_path)
    assert custom.read_text() == 'My instructions'
    assert (tmp_path / CONFIG_PATH).read_bytes() == (root / 'examples/workflows/python-project.json').read_bytes()


def test_cli_file_artifact_handoffs_complete_without_self_invalidating(tmp_path, monkeypatch, capsys):
    def invoke(*args):
        monkeypatch.setattr('sys.argv', ['kgmaker', *args, '--root', str(tmp_path)])
        with pytest.raises(SystemExit) as result:
            main()
        output = capsys.readouterr()
        assert result.value.code == 0, output.err
        return output.out
    identifier = invoke('task', 'add', 'CLI handoff', '--workflow', 'greenfield').splitlines()[0]
    inputs = tmp_path / '.kgmaker/workflow/inputs'
    inputs.mkdir()
    for phase, role, extra in [
        ('analyze', 'architect', {}),
        ('plan', 'architect', {'steps': [{'id':'one','intent':'Create module','paths':['app.py'],'tests':[]}], 'out_of_scope':[]}),
        ('implement', 'implementation', {'changed_paths':[], 'notes':'No external execution'}),
        ('test', 'test_expert', {'validations':[{'label':'unit','command':'fixture check','status':'passed'}]}),
        ('review', 'review', {'overall':'approve','findings':[]}),
    ]:
        invoke('task', 'advance', identifier, phase)
        packet = json.loads(invoke('task', 'context', identifier, '--role', role))
        payload = {'summary': phase, 'status':'completed', 'cited_paths':[], 'cited_node_ids':[],
                   'packet_id':packet['packet_id'], 'disposition':None, **extra}
        path = inputs / (phase + '.json')
        path.write_text(json.dumps(payload))
        invoke('task','record',identifier,'--role',role,'--artifact',str(path))
    invoke('task', 'advance', identifier, 'done')
    assert load_task(tmp_path, identifier)['status'] == 'done'

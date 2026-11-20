"""Completion handoff exercises the real profiled task store and packet API."""
from argparse import ArgumentParser

import pytest

from kgmaker import completion_handoff as coordinator
from kgmaker.analysis_model import read_json, write_json
from kgmaker.context import ContextError
from kgmaker.workflow import (WorkflowError, add_task, advance_task, load_task,
                              packet_path, record_artifact)
from kgmaker.workflow_profiles import CONFIG_PATH


def _files(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def _record(root, task, **fields):
    phase = task['status']
    artifact = {'summary': f'{phase} result', 'status': 'completed', 'cited_paths': [],
                'cited_node_ids': [], 'packet_id': None, 'disposition': None}
    if phase == 'plan':
        artifact.update(steps=[{'id': 'change', 'intent': 'Fix the error', 'paths': ['app.py'],
                                'tests': ['test_app.py']}], out_of_scope=[])
    if phase == 'implement':
        artifact.update(changed_paths=['app.py'], notes='Fix applied')
    if phase == 'test':
        artifact['validations'] = [{'label': 'unit', 'command': 'python -m unittest', 'status': 'passed'}]
    if phase == 'review':
        artifact.update(overall='approve', findings=[])
    artifact.update(fields)
    return record_artifact(root, task['id'], coordinator.ROLE[phase], artifact)


def _reach(root, phase, *, limit=3):
    task = add_task(root, 'Fix the test error', workflow='bugfix', max_iterations=limit)
    for next_phase in ('analyze', 'plan', 'implement', 'test', 'review'):
        task = advance_task(root, task['id'], next_phase)
        if next_phase == phase:
            return task
        task = _record(root, task)
    raise AssertionError(phase)


def _fail(root, task):
    if task['status'] == 'test':
        return _record(root, task, status='failed', validations=[
            {'label': 'unit', 'command': 'python -m unittest', 'status': 'failed'}])
    return _record(root, task, overall='request_changes', findings=[
        {'severity': 'major', 'path': 'app.py', 'summary': 'Return value lost', 'disposition': 'open'}])


def test_preview_apply_and_reissue_after_interruption(tmp_path):
    task = add_task(tmp_path, 'Fix fixture state', workflow='bugfix')
    identifier = task['id']
    before = _files(tmp_path)
    draft = coordinator.handoff(tmp_path, identifier)
    assert (draft['from_phase'], draft['phase'], draft['role'], draft['action']) == (
        'intake', 'analyze', 'architect', 'advance')
    assert not draft['applied'] and _files(tmp_path) == before
    applied = coordinator.handoff(tmp_path, identifier, apply=True)
    assert applied['applied'] and applied['packet'] == draft['packet']
    current = load_task(tmp_path, identifier)
    assert current['status'] == 'analyze' and current['iteration'] == 0
    stored = packet_path(tmp_path, current, 'architect', 0)
    assert read_json(stored) == applied['packet']
    stored.unlink()  # The phase change survived an interrupted packet write.
    resumed = coordinator.handoff(tmp_path, identifier, apply=True)
    assert resumed['action'] == 'dispatch' and read_json(stored) == resumed['packet']
    assert resumed['packet']['packet_id'] == applied['packet']['packet_id']
    _record(tmp_path, current, packet_id=resumed['packet']['packet_id'])
    prepared = coordinator.handoff(tmp_path, identifier, apply=True)
    assert prepared['phase'] == 'plan' and prepared['packet']['workflow']['phase'] == 'plan'


@pytest.mark.parametrize('phase, feedback_key', [('test', 'validations'), ('review', 'findings')])
def test_retry_carries_exact_persisted_feedback_to_implementation(tmp_path, phase, feedback_key):
    task = _fail(tmp_path, _reach(tmp_path, phase))
    before = _files(tmp_path)
    prior = task['artifacts'][-1]
    draft = coordinator.handoff(tmp_path, task['id'])
    assert draft['action'] == 'retry' and draft['iteration'] == 1
    assert draft['feedback']['id'] == prior['id']
    assert draft['feedback'][feedback_key] == prior[feedback_key]
    assert _files(tmp_path) == before
    applied = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert applied['action'] == 'retry' and applied['role'] == 'implementation'
    stored = load_task(tmp_path, task['id'])
    assert (stored['iteration'], stored['status']) == (1, 'implement')
    resumed = coordinator.handoff(tmp_path, task['id'])
    assert resumed['action'] == 'dispatch' and resumed['feedback'] == applied['feedback']


def test_retry_limit_reports_feedback_without_mutation(tmp_path):
    task = _fail(tmp_path, _reach(tmp_path, 'test', limit=1))
    before = _files(tmp_path)
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['action'] == 'hold' and response['role'] is None
    assert response['feedback']['id'] == task['artifacts'][-1]['id']
    assert 'retry limit' in response['diagnostic']
    assert not response['applied'] and _files(tmp_path) == before


@pytest.mark.parametrize('phase', ['test', 'review'])
def test_stale_failure_requests_current_checks_without_retry(tmp_path, phase):
    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _fail(tmp_path, _reach(tmp_path, phase))
    source.write_text('value = 2\n')
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['phase'] == phase and 'stale' in response['diagnostic']
    if phase == 'test':
        assert response['action'] == 'dispatch' and response['feedback'] is None
    else:
        assert response['action'] == 'hold' and response['role'] is None
        assert response['feedback']['phase'] == 'test'
    assert load_task(tmp_path, task['id'])['iteration'] == 0


def test_approved_review_requires_explicit_decision(tmp_path):
    task = _record(tmp_path, _reach(tmp_path, 'review'))
    before = _files(tmp_path)
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['action'] == 'hold' and response['role'] is None
    assert not response['applied'] and _files(tmp_path) == before
    assert load_task(tmp_path, task['id'])['status'] == 'review'


def test_skipped_test_cannot_advance(tmp_path):
    task = _record(tmp_path, _reach(tmp_path, 'test'), validations=[
        {'label': 'unit', 'command': 'python -m unittest', 'status': 'skipped'}])
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='requires at least one passed'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert _files(tmp_path) == before


def test_packet_budget_failure_leaves_phase_intact(tmp_path):
    write_json(tmp_path / CONFIG_PATH, {'schema_version': 1, 'default': 'low-budget',
               'profiles': {'low-budget': {'extends': 'bugfix', 'token_budget': 128}}})
    task = add_task(tmp_path, 'Repair fixture', workflow='low-budget')
    before = _files(tmp_path)
    with pytest.raises(ContextError, match='token budget'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert _files(tmp_path) == before


def test_competing_test_artifact_prevents_retry_on_superseded_failure(tmp_path, monkeypatch):
    task = _fail(tmp_path, _reach(tmp_path, 'test'))
    def competing_write(root, identifier, target, **kwargs):
        _record(root, load_task(root, identifier))
        return advance_task(root, identifier, target, **kwargs)
    monkeypatch.setattr(coordinator, 'advance_task', competing_write)
    with pytest.raises(WorkflowError, match='stale workflow task'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    latest = load_task(tmp_path, task['id'])
    assert latest['status'] == 'test' and latest['iteration'] == 0
    assert latest['artifacts'][-1]['validations'][0]['status'] == 'passed'
    assert not packet_path(tmp_path, latest, 'implementation', 1).exists()


def test_cli_registration_and_legacy_guard(tmp_path):
    task = add_task(tmp_path, 'Legacy task')
    parser = ArgumentParser()
    coordinator.register(parser.add_subparsers(required=True))
    args = parser.parse_args(['handoff', task['id'], '--root', str(tmp_path)])
    before = _files(tmp_path)
    assert not args.apply
    with pytest.raises(WorkflowError, match='profiled task'):
        args.handler(args)
    assert _files(tmp_path) == before



def test_completed_success_on_old_source_requests_current_tests(tmp_path):
    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _record(tmp_path, _reach(tmp_path, 'test'))
    source.write_text('value = 2\n')
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['action'] == 'dispatch' and response['role'] == 'test_expert'
    assert 'stale' in response['diagnostic']
    assert load_task(tmp_path, task['id'])['iteration'] == 0


def test_binding_change_between_preview_and_retry_stops_advance(tmp_path, monkeypatch):
    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _fail(tmp_path, _reach(tmp_path, 'test'))
    def competing_edit(root, identifier, target, **kwargs):
        source.write_text('value = 2\n')
        return advance_task(root, identifier, target, **kwargs)
    monkeypatch.setattr(coordinator, 'advance_task', competing_edit)
    with pytest.raises(WorkflowError, match='stale workflow source evidence'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert load_task(tmp_path, task['id']) == task


def test_role_blocker_does_not_consume_retry(tmp_path):
    task = _record(tmp_path, _reach(tmp_path, 'test'), status='blocked', validations=[
        {'label': 'unit', 'command': 'python -m unittest', 'status': 'failed'}])
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['action'] == 'hold' and response['diagnostic'] == 'Role reported a blocker'
    assert load_task(tmp_path, task['id']) == task



def test_resume_implementation_respects_an_explicit_revocation(tmp_path):
    from kgmaker import provenance
    from kgmaker.analysis_model import AnalysisError

    task = _reach(tmp_path, 'implement')
    with provenance.transaction(tmp_path) as journal:
        provenance.sync_task(journal, task)
        journal['policy']['before_implement'] = True
        human = {'id': 'reviewer', 'kind': 'human'}
        for ref in provenance.task_references(task):
            if ref['kind'] in {'requirement', 'plan'}:
                provenance.event(journal, ref['key'], 'approved', 'Fixture approval', actor=human)
    result = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert result['role'] == 'implementation'
    with provenance.transaction(tmp_path) as journal:
        plan = next(ref for ref in provenance.task_references(task) if ref['kind'] == 'plan')
        provenance.event(journal, plan['key'], 'revoked', 'Fixture revocation', actor=human)
    before = _files(tmp_path)
    with pytest.raises(AnalysisError, match='lacks local approval'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert _files(tmp_path) == before


def test_source_change_forces_a_new_test_packet_and_rejects_old_submission(tmp_path):
    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _reach(tmp_path, 'test')
    old = coordinator.handoff(tmp_path, task['id'], apply=True)['packet']['packet_id']
    source.write_text('value = 2\n')
    with pytest.raises(WorkflowError, match='artifact packet is stale'):
        _record(tmp_path, task, packet_id=old)
    new = coordinator.handoff(tmp_path, task['id'], apply=True)['packet']['packet_id']
    assert old != new
    assert _record(tmp_path, task, packet_id=new)['artifacts'][-1]['packet_id'] == new



def test_packet_binding_stays_fixed_until_the_locked_artifact_write(tmp_path, monkeypatch):
    from kgmaker import workflow

    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _reach(tmp_path, 'test')
    packet = coordinator.handoff(tmp_path, task['id'], apply=True)['packet']
    real_binding = workflow.source_binding
    first = True

    def change_after_verification(root):
        nonlocal first
        binding = real_binding(root)
        if first:
            first = False
            source.write_text('value = 2\n')
        return binding

    monkeypatch.setattr(workflow, 'source_binding', change_after_verification)
    with pytest.raises(WorkflowError, match='stale workflow source evidence'):
        _record(tmp_path, task, packet_id=packet['packet_id'])
    assert load_task(tmp_path, task['id']) == task

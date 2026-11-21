"""Completion handoff exercises the real profiled task store and packet API."""
from argparse import ArgumentParser

import pytest

from kgmaker import completion_handoff as coordinator
from kgmaker.completion_review import attribute
from kgmaker.analysis_model import read_json, write_json
from kgmaker.context import ContextError, prepare_task_packet
from kgmaker.workflow import (WorkflowError, add_task, advance_task, load_task,
                              packet_id, packet_path, record_artifact)
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
    _attributed_change(root, task)
    task = _record(root, task, overall='request_changes', disposition='correctness',
                   packet_id=_review_packet(root, task), findings=[
        {'severity': 'major', 'path': 'app.py', 'summary': 'Return value lost', 'disposition': 'open'}])
    attribute(root, task['id'], task['artifacts'][-1]['id'], 'reviewer')
    return task


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


def test_unattributed_generic_approval_does_not_complete_review(tmp_path):
    task = _record(tmp_path, _reach(tmp_path, 'review'))
    before = _files(tmp_path)
    response = coordinator.handoff(tmp_path, task['id'])
    assert response['action'] == 'dispatch' and response['role'] == 'review'
    assert response['reviews']['pending'] == ['correctness', 'steelman']
    assert not response['applied'] and _files(tmp_path) == before
    assert load_task(tmp_path, task['id'])['status'] == 'review'


def _review_packet(root, task):
    return coordinator.handoff(root, task['id'], apply=True)['packet']['packet_id']


def _attributed_change(root, task):
    change = next(item for item in task['artifacts'] if item['role'] == 'implementation')
    attribute(root, task['id'], change['id'], 'implementer')


def test_two_current_independent_approvals_are_ready_for_t045(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = _review_packet(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=packet)
    correctness = task['artifacts'][-1]['id']
    task = _record(tmp_path, task, disposition='steelman', packet_id=packet)
    steelman = task['artifacts'][-1]['id']
    receipt = attribute(tmp_path, task['id'], correctness, 'correctness-agent')
    assert receipt['identity_trust'] == 'LOCAL_DECLARED'
    before = _files(tmp_path)
    assert attribute(tmp_path, task['id'], correctness, 'correctness-agent') == receipt
    assert _files(tmp_path) == before
    partial = coordinator.handoff(tmp_path, task['id'])
    assert partial['action'] == 'dispatch' and partial['reviews']['pending'] == ['steelman']
    attribute(tmp_path, task['id'], steelman, 'steelman-agent')
    before = _files(tmp_path)
    ready = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert ready['action'] == 'awaiting_pr_review'
    assert ready['reviews']['approved']['correctness']['artifact_id'] == correctness
    assert ready['reviews']['approved']['steelman']['artifact_id'] == steelman
    assert not ready['applied'] and _files(tmp_path) == before
    assert load_task(tmp_path, task['id'])['status'] == 'review'
    for overall in ('request_changes', 'block'):
        task = _record(tmp_path, task, overall=overall, disposition='legacy-vote')
        response = coordinator.handoff(tmp_path, task['id'])
        assert response['action'] == 'awaiting_pr_review'


def test_resumed_parallel_review_reuses_the_first_source_bound_packet(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    original = coordinator.handoff(tmp_path, task['id'], apply=True)['packet']
    task = _record(tmp_path, task, disposition='correctness', packet_id=original['packet_id'])
    attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'correctness-agent')
    before = _files(tmp_path)
    for apply in (False, True):
        pending = coordinator.handoff(tmp_path, task['id'], apply=apply, token_budget=8000)
        assert pending['reviews']['pending'] == ['steelman']
        assert pending['packet'] == original and _files(tmp_path) == before
    task = _record(tmp_path, task, disposition='steelman', packet_id=original['packet_id'])
    attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'steelman-agent')
    assert coordinator.handoff(tmp_path, task['id'])['action'] == 'awaiting_pr_review'


def test_corrupt_review_packet_does_not_advance_or_replace_files(tmp_path):
    task = _record(tmp_path, _reach(tmp_path, 'test'))
    path = packet_path(tmp_path, task, 'review', task['iteration'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{}')
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='Persisted review packet'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert _files(tmp_path) == before


def test_missing_review_packet_cannot_split_existing_review_tracks(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    original = _review_packet(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=original)
    attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'correctness-agent')
    path = packet_path(tmp_path, task, 'review', task['iteration'])
    path.unlink()
    before = _files(tmp_path)
    for apply in (False, True):
        with pytest.raises(WorkflowError, match='Original review packet unavailable'):
            coordinator.handoff(tmp_path, task['id'], apply=apply)
        assert _files(tmp_path) == before
    replacement = prepare_task_packet(tmp_path, task['id'], 'review')['packet_id']
    assert replacement != original
    task = _record(tmp_path, task, disposition='steelman', packet_id=replacement)
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='same source-bound packet'):
        attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'steelman-agent')
    assert _files(tmp_path) == before


def test_reject_self_review_duplicate_actor_and_duplicate_track(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = _review_packet(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=packet)
    first = task['artifacts'][-1]['id']
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='their own review'):
        attribute(tmp_path, task['id'], first, 'implementer')
    assert _files(tmp_path) == before
    attribute(tmp_path, task['id'], first, 'reviewer')
    task = _record(tmp_path, task, disposition='correctness', summary='Different result', packet_id=packet)
    duplicate = task['artifacts'][-1]['id']
    task = _record(tmp_path, task, disposition='steelman', packet_id=packet)
    second = task['artifacts'][-1]['id']
    before = _files(tmp_path)
    for candidate, actor, diagnostic in (
        (first, 'someone-else', 'different actor'),
        (duplicate, 'someone-else', 'already has an attributed artifact'),
        (second, 'reviewer', 'distinct actors'),
    ):
        with pytest.raises(WorkflowError, match=diagnostic):
            attribute(tmp_path, task['id'], candidate, actor)
        assert _files(tmp_path) == before


def test_stale_attribution_cannot_authorize_review(tmp_path):
    source = tmp_path / 'app.py'
    source.write_text('value = 1\n')
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=_review_packet(tmp_path, task))
    receipt = task['artifacts'][-1]['id']
    source.write_text('value = 2\n')
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='current iteration and source'):
        attribute(tmp_path, task['id'], receipt, 'reviewer')
    response = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert response['action'] == 'hold' and 'Test evidence is stale' in response['diagnostic']
    assert _files(tmp_path) == before


def test_legacy_unbound_packet_cannot_be_attributed(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = coordinator.handoff(tmp_path, task['id'], apply=True)['packet']
    del packet['workflow']['source_binding']
    packet['packet_id'] = packet_id(packet)
    write_json(packet_path(tmp_path, task, 'review', task['iteration']), packet)
    task = _record(tmp_path, task, disposition='correctness', packet_id=packet['packet_id'])
    before = _files(tmp_path)
    with pytest.raises(WorkflowError, match='original current source-bound packet'):
        attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'reviewer')
    assert _files(tmp_path) == before
    assert coordinator.handoff(tmp_path, task['id'])['reviews']['pending'] == ['correctness', 'steelman']


@pytest.mark.parametrize(('overall', 'severity', 'expected'), [
    ('request_changes', 'minor', 'retry'),
    ('approve', 'major', 'retry'),
    ('block', 'note', 'hold'),
])
def test_later_approval_cannot_hide_current_review_findings(tmp_path, overall, severity, expected):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = _review_packet(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=packet,
                   overall=overall, findings=[{'severity': severity, 'path': 'app.py',
                   'summary': 'A real finding', 'disposition': 'open'}])
    negative = task['artifacts'][-1]['id']
    task = _record(tmp_path, task, disposition='steelman', packet_id=packet)
    attribute(tmp_path, task['id'], negative, 'correctness-agent')
    attribute(tmp_path, task['id'], task['artifacts'][-1]['id'], 'steelman-agent')
    result = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert result['action'] == expected and result['feedback']['id'] == negative
    assert result['feedback']['findings'][0]['summary'] == 'A real finding'
    if expected == 'retry':
        resumed = coordinator.handoff(tmp_path, task['id'])
        assert resumed['phase'] == 'implement' and resumed['feedback']['id'] == negative


def test_retry_and_resume_return_findings_from_both_tracks(tmp_path):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = _review_packet(tmp_path, task)
    negatives = []
    for track in ('correctness', 'steelman'):
        task = _record(tmp_path, task, disposition=track, packet_id=packet, overall='request_changes',
                       findings=[{'severity': 'major', 'path': 'app.py',
                                  'summary': f'{track} finding', 'disposition': 'open'}])
        negatives.append(task['artifacts'][-1]['id'])
        attribute(tmp_path, task['id'], negatives[-1], f'{track}-agent')
    retry = coordinator.handoff(tmp_path, task['id'], apply=True)
    assert retry['action'] == 'retry'
    resumed = coordinator.handoff(tmp_path, task['id'])
    for response in (retry, resumed):
        assert response['feedback']['id'] == negatives[0]
        assert [item['id'] for item in response['reviews']['feedback']] == negatives
        assert [item['findings'][0]['summary'] for item in response['reviews']['feedback']] == [
            'correctness finding', 'steelman finding']


def test_late_attributed_block_prevents_stale_review_retry(tmp_path, monkeypatch):
    task = _reach(tmp_path, 'review')
    _attributed_change(tmp_path, task)
    packet = _review_packet(tmp_path, task)
    task = _record(tmp_path, task, disposition='correctness', packet_id=packet, overall='request_changes')
    change = task['artifacts'][-1]['id']
    task = _record(tmp_path, task, disposition='steelman', packet_id=packet, overall='block')
    blocker = task['artifacts'][-1]['id']
    attribute(tmp_path, task['id'], change, 'correctness-agent')

    def competing_attribution(root, identifier, target, **kwargs):
        attribute(root, identifier, blocker, 'steelman-agent')
        return advance_task(root, identifier, target, **kwargs)

    monkeypatch.setattr(coordinator, 'advance_task', competing_attribution)
    with pytest.raises(WorkflowError, match='Stale journal revision'):
        coordinator.handoff(tmp_path, task['id'], apply=True)
    assert load_task(tmp_path, task['id']) == task
    assert not packet_path(tmp_path, task, 'implementation', 1).exists()
    blocked = coordinator.handoff(tmp_path, task['id'])
    assert blocked['action'] == 'hold' and blocked['feedback']['id'] == blocker


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

    parser = ArgumentParser()
    coordinator.register(parser.add_subparsers(required=True))
    args = parser.parse_args(['handoff', task['id'], '--root', str(tmp_path),
                              '--token-budget', '8000'])
    draft = args.handler(args)
    assert draft['packet']['token_budget'] == 8000 and _files(tmp_path) == before

    args.apply = True
    applied = args.handler(args)
    assert applied['packet'] == draft['packet']
    current = load_task(tmp_path, task['id'])
    assert current['status'] == 'analyze' and current['workflow'] == task['workflow']
    assert read_json(packet_path(tmp_path, current, 'architect', 0)) == applied['packet']


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

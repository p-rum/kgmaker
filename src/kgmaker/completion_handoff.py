"""Advance one profiled workflow handoff and prepare its standard role packet."""
from pathlib import Path

from .analysis_model import digest
from .completion_review import TRACKS, eligible_reviews, review_packet
from .context import prepare_packet, prepare_task_packet
from .provenance import enforce_gate, load as load_journal, transaction
from .workflow import (TERMINAL_STATUSES, WorkflowError, advance_task,
                       legal_transitions, load_task, source_binding)
from .workflow_profiles import enforce_handoff

ROLE = {
    'analyze': 'architect',
    'plan': 'architect',
    'implement': 'implementation',
    'test': 'test_expert',
    'review': 'review',
}
FORWARD = {'analyze': 'plan', 'plan': 'implement', 'implement': 'test', 'test': 'review'}


def _artifact(task, phase, iteration):
    return next((item for item in reversed(task['artifacts'])
                 if item['phase'] == phase and item['role'] == ROLE[phase]
                 and item['iteration'] == iteration), None)


def _feedback(item):
    if item is None:
        return None
    return {key: item[key] for key in ('id', 'phase', 'status', 'summary', 'overall',
                                       'findings', 'validations', 'disposition') if key in item}


def _fresh(root, task, item):
    saved = task['delivery']['bindings'].get(item['id'])
    return saved == source_binding(root)


def _blocked_review(item):
    return item['status'] == 'blocked' or item['overall'] == 'block'


def _changes_review(item):
    return item['status'] == 'failed' or item['overall'] == 'request_changes' or any(
        finding['disposition'] == 'open' and finding['severity'] in {'major', 'blocker'}
        for finding in item['findings'])


def _review_findings(reviews):
    blockers, changes = [], []
    for item, _ in reviews.values():
        if _blocked_review(item):
            blockers.append(item)
        elif _changes_review(item):
            changes.append(item)
    return blockers, changes


def _prior_failure(journal, task, iteration):
    test = _artifact(task, 'test', iteration)
    if test is None:
        return None, []
    binding = task['delivery']['bindings'].get(test['id'])
    reviews, _ = eligible_reviews(journal, task, binding, iteration=iteration)
    blockers, changes = _review_findings(reviews)
    return (changes[0] if changes else test), blockers + changes


def _next(root, task, review_state, journal):
    phase, iteration = task['status'], task['iteration']
    if phase in TERMINAL_STATUSES:
        return None, 'hold', None, task['stop_reason'] or 'Workflow is already complete'
    if phase == 'intake':
        return 'analyze', 'advance', None, None
    item = _artifact(task, phase, iteration)
    if phase == 'review':
        test = _artifact(task, 'test', iteration)
        binding = source_binding(root)
        if test is None or task['delivery']['bindings'].get(test['id']) != binding:
            return (None, 'hold', _feedback(test),
                    'Test evidence is stale or missing; retry through implementation and test')
        reviews, attribution_error = eligible_reviews(journal, task, binding, iteration=iteration)
        blockers, changes = _review_findings(reviews)
        review_state['feedback'] = [_feedback(item) for item in blockers + changes]
        if blockers:
            return None, 'hold', _feedback(blockers[0]), 'Role reported a blocker'
        if changes:
            if 'implement' not in legal_transitions(task):
                return None, 'hold', _feedback(changes[0]), 'Workflow retry limit reached'
            return 'implement', 'retry', _feedback(changes[0]), None
        approved = {track: {'artifact_id': item['id'], 'actor': actor, 'packet_id': item['packet_id']}
                    for track, (item, actor) in reviews.items()
                    if item['overall'] == 'approve' and item['status'] == 'completed'}
        pending = [track for track in TRACKS if track not in approved]
        review_state.update(approved=approved, pending=pending)
        if pending:
            return phase, 'dispatch', None, attribution_error or 'Awaiting independent review tracks'
        return None, 'awaiting_pr_review', None, 'Independent local review recorded; proceed through T045'
    prior = None
    if phase == 'implement' and iteration:
        prior, findings = _prior_failure(journal, task, iteration - 1)
        review_state['feedback'] = [_feedback(item) for item in findings]
    if item is None:
        return phase, 'dispatch', _feedback(prior), None
    if item['status'] == 'blocked':
        return None, 'hold', _feedback(item), 'Role reported a blocker'
    failed_test = phase == 'test' and (item['status'] == 'failed' or any(
        entry['status'] == 'failed' for entry in item['validations']))
    if failed_test:
        if not _fresh(root, task, item):
            return phase, 'dispatch', None, 'Failure evidence is stale; verify the current revision'
        if 'implement' not in legal_transitions(task):
            return None, 'hold', _feedback(item), 'Workflow retry limit reached'
        return 'implement', 'retry', _feedback(item), None
    if phase == 'test' and item['status'] == 'completed' and not _fresh(root, task, item):
        return phase, 'dispatch', None, 'Test evidence is stale; test the current revision'
    if item['status'] != 'completed':
        return phase, 'dispatch', _feedback(prior), None
    return FORWARD[phase], 'advance', None, None


def _review_packet(root, task, reviews):
    packet = review_packet(root, task, source_binding(root))
    prior = next(iter(reviews['approved'].values()), None)
    if prior is not None and (packet is None or packet['packet_id'] != prior['packet_id']):
        raise WorkflowError('Original review packet unavailable; restore it or start a new review iteration')
    return packet


def handoff(root: Path, task_id: str, *, apply: bool = False) -> dict:
    """Preview or persist one handoff. Specialist execution stays with the host."""
    task = load_task(root, task_id)
    if task['schema_version'] != 3:
        raise WorkflowError('Completion handoff requires a profiled task')
    phase = task['status']
    journal = load_journal(root) if phase == 'review' or (phase == 'implement' and task['iteration']) else None
    journal_revision = journal['revision'] if phase == 'review' else None
    reviews = {'approved': {}, 'pending': list(TRACKS), 'feedback': []}
    target, action, feedback, diagnostic = _next(root, task, reviews, journal)
    role = ROLE.get(target)
    iteration = task['iteration'] + (action == 'retry')
    packet = None
    if role is not None:
        projected = {**task, 'status': target, 'iteration': iteration}
        if target != phase:
            enforce_handoff(root, task, projected)
        if target == 'implement':
            enforce_gate(root, projected, target)
        if target == 'review':
            packet = _review_packet(root, projected, reviews)
        if not apply:
            if packet is None:
                packet = prepare_packet(root, projected, role, persist=False)
        else:
            current = task
            if target != phase:
                # Validate that the next packet can be prepared before advancing.
                if packet is None:
                    prepare_packet(root, projected, role, persist=False)
                binding = task['delivery']['bindings'][feedback['id']] if action == 'retry' else None
                current = advance_task(root, task['id'], target, expected_revision=digest(task),
                                       expected_binding=binding, expected_journal_revision=journal_revision)
            revision = journal_revision if target == phase == 'review' else None
            with transaction(root, expected_revision=revision):
                if load_task(root, task['id']) != current:
                    raise WorkflowError('Task changed concurrently; reload before preparing a packet')
                if target == 'implement':
                    enforce_gate(root, current, target)
                if target == 'review':
                    packet = _review_packet(root, current, reviews)
                if packet is None:
                    packet = prepare_task_packet(root, task['id'], role)
    return {'task_id': task['id'], 'from_phase': phase, 'phase': target or phase,
            'iteration': iteration, 'role': role, 'action': action, 'feedback': feedback,
            'diagnostic': diagnostic, 'packet': packet, 'applied': bool(apply and role),
            'reviews': reviews}


def _run(args):
    return handoff(args.root, args.task_id, apply=args.apply)


def register(commands) -> None:
    parser = commands.add_parser('handoff', help='preview or prepare the next profiled task role')
    parser.add_argument('task_id')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--apply', action='store_true', help='persist one phase and its role packet')
    parser.set_defaults(handler=_run)

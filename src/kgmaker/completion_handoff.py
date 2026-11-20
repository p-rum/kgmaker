"""Advance one profiled workflow handoff and prepare its standard role packet."""
from pathlib import Path

from .analysis_model import digest
from .context import prepare_packet, prepare_task_packet
from .provenance import enforce_gate, transaction
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
                                       'findings', 'validations') if key in item}


def _fresh(root, task, item):
    saved = task['delivery']['bindings'].get(item['id'])
    return saved == source_binding(root)


def _next(root, task):
    phase, iteration = task['status'], task['iteration']
    if phase in TERMINAL_STATUSES:
        return None, 'hold', None, task['stop_reason'] or 'Workflow is already complete'
    if phase == 'intake':
        return 'analyze', 'advance', None, None
    item = _artifact(task, phase, iteration)
    if phase == 'review':
        test = _artifact(task, 'test', iteration)
        if test is None or not _fresh(root, task, test):
            return (None, 'hold', _feedback(test),
                    'Test evidence is stale or missing; retry through implementation and test')
    prior = None
    if phase == 'implement' and iteration:
        prior = _artifact(task, 'review', iteration - 1) or _artifact(task, 'test', iteration - 1)
    if item is None:
        return phase, 'dispatch', _feedback(prior), None
    if item['status'] == 'blocked' or (phase == 'review' and item['overall'] == 'block'):
        return None, 'hold', _feedback(item), 'Role reported a blocker'
    failed_test = phase == 'test' and (item['status'] == 'failed' or any(
        entry['status'] == 'failed' for entry in item['validations']))
    review_changes = phase == 'review' and item['overall'] == 'request_changes'
    if failed_test or review_changes:
        if not _fresh(root, task, item):
            return phase, 'dispatch', None, 'Failure evidence is stale; verify the current revision'
        if 'implement' not in legal_transitions(task):
            return None, 'hold', _feedback(item), 'Workflow retry limit reached'
        return 'implement', 'retry', _feedback(item), None
    if phase == 'test' and item['status'] == 'completed' and not _fresh(root, task, item):
        return phase, 'dispatch', None, 'Test evidence is stale; test the current revision'
    if phase == 'review' and item['status'] == 'completed':
        if not _fresh(root, task, item):
            return phase, 'dispatch', None, 'Review evidence is stale; review the current revision'
        return None, 'hold', _feedback(item), 'Review recorded; completion requires an explicit decision'
    if item['status'] != 'completed':
        return phase, 'dispatch', _feedback(prior), None
    return FORWARD[phase], 'advance', None, None


def handoff(root: Path, task_id: str, *, apply: bool = False) -> dict:
    """Preview or persist one handoff. Specialist execution stays with the host."""
    task = load_task(root, task_id)
    if task['schema_version'] != 3:
        raise WorkflowError('Completion handoff requires a profiled task')
    target, action, feedback, diagnostic = _next(root, task)
    role = ROLE.get(target)
    phase = task['status']
    iteration = task['iteration'] + (action == 'retry')
    packet = None
    if role is not None:
        projected = {**task, 'status': target, 'iteration': iteration}
        if target != phase:
            enforce_handoff(root, task, projected)
        if target == 'implement':
            enforce_gate(root, projected, target)
        if not apply:
            packet = prepare_packet(root, projected, role, persist=False)
        else:
            current = task
            if target != phase:
                # Validate that the next packet can be prepared before advancing.
                prepare_packet(root, projected, role, persist=False)
                binding = task['delivery']['bindings'][feedback['id']] if action == 'retry' else None
                current = advance_task(root, task['id'], target, expected_revision=digest(task),
                                       expected_binding=binding)
            with transaction(root):
                if load_task(root, task['id']) != current:
                    raise WorkflowError('Task changed concurrently; reload before preparing a packet')
                if target == 'implement':
                    enforce_gate(root, current, target)
                packet = prepare_task_packet(root, task['id'], role)
    return {'task_id': task['id'], 'from_phase': phase, 'phase': target or phase,
            'iteration': iteration, 'role': role, 'action': action, 'feedback': feedback,
            'diagnostic': diagnostic, 'packet': packet, 'applied': bool(apply and role)}


def _run(args):
    return handoff(args.root, args.task_id, apply=args.apply)


def register(commands) -> None:
    parser = commands.add_parser('handoff', help='preview or prepare the next profiled task role')
    parser.add_argument('task_id')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--apply', action='store_true', help='persist one phase and its role packet')
    parser.set_defaults(handler=_run)

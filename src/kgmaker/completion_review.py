"""Attribute completion artifacts in the existing local provenance journal."""
import re
from pathlib import Path

from . import provenance
from .analysis_model import AnalysisError, read_json
from .workflow import WorkflowError, load_task, packet_id, packet_path, source_binding

TRACKS = ('correctness', 'steelman')
ATTRIBUTION = 'T052 artifact attribution'


def current_artifacts(task, phase, binding, *, iteration=None):
    role = {'review': 'review', 'implement': 'implementation'}[phase]
    iteration = task['iteration'] if iteration is None else iteration
    return [item for item in task['artifacts']
            if item['phase'] == phase and item['role'] == role and item['iteration'] == iteration
            and task['delivery']['bindings'].get(item['id']) == binding]


def _actors(journal, task):
    references = {ref['key']: ref['id'] for ref in provenance.task_references(task)
                  if ref['kind'] in {'change', 'review'}}
    actors = {}
    for event in journal['events']:
        artifact_id = references.get(event['subject'])
        if (artifact_id and event['action'] == 'submitted' and event['reason'] == ATTRIBUTION
                and event['actor']['kind'] == 'agent' and event['identity_trust'] == 'LOCAL_DECLARED'):
            actors.setdefault(artifact_id, set()).add(event['actor']['id'])
    return actors


def _implementers(task, actors, iteration):
    return {actor for item in task['artifacts'] if item['role'] == 'implementation'
            and item['iteration'] <= iteration
            for actor in actors.get(item['id'], ())}


def eligible_reviews(journal, task, binding, *, iteration):
    """Return review votes with one distinct, attributed actor per track."""
    actors = _actors(journal, task)
    changes = current_artifacts(task, 'implement', binding, iteration=iteration)
    if not changes or any(len(actors.get(item['id'], ())) != 1 for item in changes):
        return {}, 'Current implementation artifacts require attribution'
    implementers = _implementers(task, actors, iteration)
    reviews = current_artifacts(task, 'review', binding, iteration=iteration)
    eligible = {}
    for track in TRACKS:
        votes = [item for item in reviews if item['disposition'] == track and item['id'] in actors]
        if len(votes) != 1:
            continue
        item = votes[0]
        ids = actors[item['id']]
        if len(ids) == 1 and not ids & implementers and item['packet_id'] is not None:
            eligible[track] = (item, next(iter(ids)))
    if len({actor for item, actor in eligible.values()}) != len(eligible):
        return {}, 'Review tracks require distinct actors'
    if len({item['packet_id'] for item, _ in eligible.values()}) > 1:
        return {}, 'Review tracks require the same source-bound packet'
    return eligible, None


def review_packet(root, task, binding):
    """Keep a valid common review packet stable while either agent is pending."""
    path = packet_path(root, task, 'review', task['iteration'])
    if not path.exists():
        return None
    try:
        packet = read_json(path)
    except AnalysisError as exc:
        raise WorkflowError('Review attribution requires a readable source-bound packet') from exc
    workflow = packet.get('workflow') if isinstance(packet, dict) else None
    profile = task['workflow']
    if (not isinstance(workflow, dict) or packet_id(packet) != packet.get('packet_id')
            or packet.get('task_id') != task['id'] or packet.get('role') != 'review'
            or packet.get('iteration') != task['iteration'] or workflow.get('phase') != 'review'
            or workflow.get('sha256') != profile['sha256'] or workflow.get('name') != profile['name']):
        raise WorkflowError('Persisted review packet does not match the task or its pinned profile')
    return packet if workflow.get('source_binding') == binding else None


def attribute(root: Path, task_id: str, artifact_id: str, actor: str) -> dict:
    """Record a host attestation of an existing artifact."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}', actor):
        raise WorkflowError('Expected a bounded host actor ID')
    observed = load_task(root, task_id)
    if observed['schema_version'] != 3 or observed['status'] not in {'implement', 'test', 'review'}:
        raise WorkflowError('Attribution requires an active profiled implementation or review')
    with provenance.transaction(root) as journal:
        task = load_task(root, task_id)
        if task != observed:
            raise WorkflowError('Task changed concurrently; reload before attributing the artifact')
        binding = source_binding(root)
        changes = current_artifacts(task, 'implement', binding)
        reviews = current_artifacts(task, 'review', binding)
        item = next((entry for entry in (*changes, *reviews) if entry['id'] == artifact_id), None)
        if item is None:
            raise WorkflowError('Artifact does not belong to the current iteration and source')
        if item['phase'] == 'review' and (item['disposition'] not in TRACKS or item['packet_id'] is None):
            raise WorkflowError('Review attribution requires a packet and a correctness or steelman disposition')
        actors = _actors(journal, task)
        existing = actors.get(artifact_id)
        if existing and existing != {actor}:
            raise WorkflowError('Artifact already has a different actor')
        attributed_reviews = [entry for entry in reviews if entry['id'] in actors]
        if item['phase'] == 'review':
            if actor in _implementers(task, actors, task['iteration']):
                raise WorkflowError('Implementers cannot attribute their own review')
            for vote in attributed_reviews:
                if vote['id'] == artifact_id:
                    continue
                if vote['packet_id'] != item['packet_id']:
                    raise WorkflowError('Review tracks require the same source-bound packet')
                if vote['disposition'] == item['disposition']:
                    raise WorkflowError('Review track already has an attributed artifact')
                if actor in actors[vote['id']]:
                    raise WorkflowError('Review tracks require distinct actors')
        elif any(actor in actors[vote['id']] for vote in attributed_reviews):
            raise WorkflowError('An attributed reviewer cannot be the implementer')
        if not existing:
            if item['phase'] == 'review':
                packet = review_packet(root, task, binding)
                if packet is None or packet['packet_id'] != item['packet_id']:
                    raise WorkflowError('Review attribution requires the original current source-bound packet')
            refs = provenance.sync_task(journal, task)
            ref = next(ref for ref in refs if ref['id'] == artifact_id)
            if source_binding(root) != binding:
                raise WorkflowError('Source changed during artifact attribution')
            provenance.event(journal, ref['key'], 'submitted', ATTRIBUTION,
                             actor={'id': actor, 'kind': 'agent'})
    return {'artifact_id': artifact_id, 'actor': actor, 'binding': binding,
            'identity_trust': 'LOCAL_DECLARED'}


def _run(args):
    return attribute(args.root, args.task_id, args.artifact_id, args.actor)


def register(commands):
    command = commands.add_parser('attribute', help='attribute a current implementation or review artifact')
    command.add_argument('task_id')
    command.add_argument('artifact_id')
    command.add_argument('--actor', required=True, help='host agent session ID')
    command.add_argument('--root', type=Path, default=Path.cwd())
    command.set_defaults(handler=_run)

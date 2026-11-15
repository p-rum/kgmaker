"""Versioned, data-only workflow profiles and content-bound handoff checks."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re

from .analysis_model import digest, read_json, safe_path
from .workflow import ROLES, WorkflowError

CONFIG_PATH = '.kgmaker/workflows.json'
PHASES = ('analyze', 'plan', 'implement', 'test', 'review')
_FIELDS = {'description', 'instructions', 'validations', 'max_iterations', 'token_budget'}
_NAME = re.compile(r'[a-z][a-z0-9-]{0,63}')

_COMMON = {
    'architect': ['Verify current sources, graph freshness and memory. Separate requirements, assumptions and evidence.',
                  'Record analysis, then a plan with acceptance, affected paths, tests, compatibility and unresolved questions.'],
    'implementation': ['Implement the recorded plan in small changes; preserve unrelated edits. Update affected documentation.'],
    'test_expert': ['Use testgen for existing targets when useful. Execute only authorized project checks; record real results.',
                    'Code characterization is not business truth. Missing tools and unrun checks are skipped/unknown, never passed.'],
    'review': ['Inspect the current diff, acceptance, documentation and test evidence. Record findings with disposition.'],
    'orchestrator': ['Use task context and record role artifacts before advancing. Reuse feature/data-check, testgen and trace.',
                     'Keep requirement → analysis → task → change → test links explicit. Stop on unresolved requirements.'],
}


def _builtin(description, analysis):
    instructions = deepcopy(_COMMON)
    instructions['architect'].append(analysis)
    return {'description': description, 'instructions': instructions, 'validations': [],
            'max_iterations': 3, 'token_budget': 4000}


BUILTINS = {
    'greenfield': _builtin('New project: establish contracts and the smallest testable vertical slice.',
                          'A missing graph or empty repository is expected. Define requirements, architecture, stack choices and acceptance before creating code. Never invent existing targets for testgen.'),
    'existing-feature': _builtin('Existing project: source-backed impact and compatible implementation.',
                                'Inspect existing extension points and callers. Use feature packets for uncertain feasibility and data-check for data prerequisites; retain UNKNOWN gaps.'),
    'bugfix': _builtin('Bug fix: reproduction, bounded correction and regression evidence.',
                      'Record a reproducible failure and expected behavior from a requirement/contract. Bound root cause and regression scope; avoid unrelated refactoring.'),
}


def _text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise WorkflowError(f'{field} must be non-empty text of at most {limit} characters')


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != _FIELDS:
        raise WorkflowError('workflow profile must contain exactly ' + ', '.join(sorted(_FIELDS)))
    _text(profile['description'], 'description', 500)
    for field, low, high in [('max_iterations', 1, 10), ('token_budget', 128, 32000)]:
        if type(profile[field]) is not int or not low <= profile[field] <= high:
            raise WorkflowError(f'{field} must be an integer from {low} to {high}')
    instructions = profile['instructions']
    if not isinstance(instructions, dict) or set(instructions) != set(ROLES):
        raise WorkflowError('instructions must define all workflow roles')
    for role, items in instructions.items():
        if not isinstance(items, list) or len(items) > 20:
            raise WorkflowError(f'instructions.{role} must be an array of at most 20 strings')
        for item in items:
            _text(item, f'instructions.{role}', 1000)
    validations = profile['validations']
    if not isinstance(validations, list) or len(validations) > 30:
        raise WorkflowError('validations must be an array of at most 30 checks')
    labels = set()
    for check in validations:
        if not isinstance(check, dict) or set(check) != {'label', 'command'}:
            raise WorkflowError('each validation must contain label and command')
        _text(check['label'], 'validation.label', 80)
        _text(check['command'], 'validation.command', 200)
        if check['label'] in labels:
            raise WorkflowError('validation labels must be unique')
        labels.add(check['label'])
    return profile


def catalog(root):
    """Resolve local overlays without executing commands or writing any state."""
    profiles = deepcopy(BUILTINS)
    path = safe_path(root, CONFIG_PATH)
    default = None
    if path.exists():
        if path.stat().st_size > 256_000:
            raise WorkflowError('workflow configuration exceeds 256000 bytes')
        config = read_json(path)
        if (not isinstance(config, dict) or set(config) != {'schema_version', 'default', 'profiles'}
                or type(config['schema_version']) is not int or config['schema_version'] != 1):
            raise WorkflowError('workflow configuration requires schema_version 1, default and profiles')
        entries = config['profiles']
        if not isinstance(entries, dict) or len(entries) > 50:
            raise WorkflowError('profiles must be an object with at most 50 entries')
        for name, overlay in entries.items():
            if not _NAME.fullmatch(name) or name in BUILTINS:
                raise WorkflowError('custom profile names must be unique lower-case slugs, not builtin names')
            if (not isinstance(overlay, dict) or not {'extends'} <= set(overlay)
                    or set(overlay) - (_FIELDS | {'extends'})):
                raise WorkflowError(f'profile {name} requires extends and supported fields only')
            parent = overlay['extends']
            if not isinstance(parent, str) or parent not in BUILTINS:
                raise WorkflowError('extends must name a builtin profile')
            value = deepcopy(BUILTINS[parent])
            for key, item in overlay.items():
                if key == 'instructions':
                    if not isinstance(item, dict) or set(item) - set(ROLES):
                        raise WorkflowError('instructions contains an unsupported role')
                    value[key].update(item)
                elif key != 'extends':
                    value[key] = item
            profiles[name] = validate_profile(value)
        default = config['default']
        if default is not None and (not isinstance(default, str) or default not in profiles):
            raise WorkflowError('default must name a known profile or be null')
    return {'default': default, 'profiles': profiles}


def select_profile(root, name=None):
    data = catalog(root)
    selected = name if name is not None else data['default']
    if selected is None:
        return None
    if selected not in data['profiles']:
        raise WorkflowError(f'unknown workflow profile: {selected}')
    payload = {'schema_version': 1, 'name': selected, 'profile': data['profiles'][selected]}
    return {**payload, 'sha256': digest(payload)}


def validate_snapshot(snapshot):
    if (not isinstance(snapshot, dict)
            or set(snapshot) != {'schema_version', 'name', 'profile', 'sha256'}
            or type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1
            or not isinstance(snapshot['name'], str) or not _NAME.fullmatch(snapshot['name'])):
        raise WorkflowError('invalid workflow snapshot')
    validate_profile(snapshot['profile'])
    if snapshot['sha256'] != digest({k: v for k, v in snapshot.items() if k != 'sha256'}):
        raise WorkflowError('workflow snapshot hash mismatch')
    return snapshot


def _latest(task, phase):
    role = {'analyze': 'architect', 'plan': 'architect', 'implement': 'implementation',
            'test': 'test_expert', 'review': 'review'}[phase]
    found = [a for a in task['artifacts'] if a['phase'] == phase and a['role'] == role
             and (phase in {'analyze', 'plan'} or a['iteration'] == task['iteration'])]
    if not found or found[-1]['status'] != 'completed':
        raise WorkflowError(f'workflow requires a completed {role}/{phase} artifact')
    return found[-1]


def enforce_handoff(root, previous, task):
    """Enforce v3 forward handoffs in the shared persistence path, not only CLI."""
    source, target = previous['status'], task['status']
    forward = dict(zip(PHASES, (*PHASES[1:], 'done')))
    if forward.get(source) != target:
        return
    artifact = _latest(task, source)
    if source in {'test', 'review'}:
        test = _latest(task, 'test')
        results = {v['label']: v for v in test['validations']}
        if any(v['status'] == 'failed' for v in results.values()):
            raise WorkflowError('workflow test validations contain failed results')
        if not any(v['status'] == 'passed' for v in results.values()):
            raise WorkflowError('workflow requires at least one passed validation')
        for required in task['workflow']['profile']['validations']:
            actual = results.get(required['label'])
            if not actual or actual['command'] != required['command'] or actual['status'] != 'passed':
                raise WorkflowError(f"required validation has not passed: {required['label']}")
        from .feature import source_inventory
        from .workflow import _git_head
        current = {'head_commit': _git_head(root), 'source_fingerprint': digest(source_inventory(root)[0])}
        checked = [test, artifact] if source == 'review' else [test]
        for item in checked:
            if task['delivery']['bindings'].get(item['id']) != current:
                raise WorkflowError('workflow evidence is stale; record current test/review results')
    if source == 'review' and (artifact['overall'] != 'approve' or any(
            f['severity'] in {'major', 'blocker'} and f['disposition'] == 'open'
            for f in artifact['findings'])):
        raise WorkflowError('workflow requires review approval without open major/blocker findings')


def register(sub):
    parser = sub.add_parser('workflow', help='inspect data-only project workflow profiles')
    commands = parser.add_subparsers(dest='workflow_command', required=True)
    for name in ('list', 'show', 'check'):
        command = commands.add_parser(name)
        command.add_argument('--root', type=Path, default=Path.cwd())
        if name == 'show':
            command.add_argument('name')


def run(args):
    import json
    import sys
    try:
        data = select_profile(args.root, args.name) if args.workflow_command == 'show' else catalog(args.root)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(f'Invalid workflow configuration: {error}', file=sys.stderr)
        return 2

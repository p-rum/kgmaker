"""Read-only public rendering of current local technical processes."""
import json
from pathlib import Path
import re
import sys

from .analysis_model import AnalysisError, canonical
from .architecture_cli import (
    ArchitectureCLIError, SafeParser, _MAX_OUTPUT_CHARS, _fail, _preflight,
    _read, _readonly_git, _safe_output, _selectors,
)
from .process_model import ProcessView
from .process_paths import ProcessPathError, build_local_process
from .process_triggers import discover_process_triggers
from .remote_mapping import SCOPES, _bounded
from .workspace import snapshot_workspace


def _configure(parser):
    actions = parser.add_subparsers(dest='process_command', required=True, parser_class=SafeParser)
    render = actions.add_parser('render', help='render one current local ProcessView as JSON', allow_abbrev=False)
    render.add_argument('--root', type=Path, default=Path.cwd(), help='coordinator and relative input path root')
    render.add_argument('--workspace', type=Path, required=True, help='explicit local workspace manifest')
    render.add_argument('--scope', choices=sorted(SCOPES), default='production')
    render.add_argument('--context-selection', type=Path, help='versioned capture pins shared with architecture')
    selection = render.add_mutually_exclusive_group(required=True)
    selection.add_argument('--entry', help='exact T024 trigger ID for a new local view')
    selection.add_argument('--process', help='exact process ID in an explicitly supplied view')
    render.add_argument('--process-view', type=Path, help='canonical ProcessView JSON for --process')
    render.add_argument('--format', choices=('json',), default='json')
    render.add_argument('--expected-fingerprint', help='exact canonical ProcessView SHA-256')
    render.add_argument('--strict', action='store_true', help='emit incomplete JSON with exit status 4')
    return parser


def register(subparsers):
    _configure(subparsers.add_parser('process', help='read-only local technical process rendering'))


def _render(args):
    stored = None
    if args.process is None:
        if args.process_view is not None:
            _fail('PROCESS_VIEW_UNEXPECTED')
        trigger_id = args.entry
        process_id = 'process:' + trigger_id.removeprefix('trigger:')
        revision = 1
    else:
        if args.process_view is None:
            _fail('PROCESS_VIEW_REQUIRED')
        stored = ProcessView.from_dict(_read(args, args.process_view))
        definition = stored.definition
        process_id, revision = definition.process_id, definition.revision
        if process_id != args.process:
            _fail('PROCESS_ID_MISMATCH')
        if definition.scope != args.scope:
            _fail('PROCESS_SCOPE_MISMATCH')
        if len(definition.trigger_ids) != 1:
            _fail('PROCESS_SINGLE_TRIGGER_REQUIRED')
        trigger_id, = definition.trigger_ids
    if re.fullmatch(r'trigger:[0-9a-f]{64}', trigger_id) is None:
        _fail('INVALID_TRIGGER_ID')

    selected = _selectors(args)
    with _readonly_git():
        workspace, manifest = _preflight(args)
        baseline, coverage, _, graph, _ = snapshot_workspace(manifest, persist_cache=False)
        if baseline['manifest_hash'] != workspace['_manifest_hash']:
            _fail('CURRENT_CAPTURE_CONFLICT', 3)
        triggers = discover_process_triggers(workspace, graph, source_coverage=coverage,
            scope=args.scope, selected_contexts=selected)

    if selected:
        # Check every explicit pin before T025 narrows the inventory to one trigger context.
        current_pins = {
            (service_id, row['repo_id'], row['module'], row['context_id'])
            for service_id, service in triggers.context_selection['services'].items()
            for row in service['contexts'] if row['status'] == 'CURRENT'
        }
        if any((*key, context_id) not in current_pins for key, context_id in selected.items()):
            _fail('INVALID_SELECTOR')

    try:
        view = build_local_process(graph, triggers, trigger_id, process_id=process_id, revision=revision)
    except ProcessPathError as error:
        code = error.diagnostic['code']
        if stored is not None and code == 'TRIGGER_UNAVAILABLE':
            _fail('PROCESS_VIEW_STALE', 3)
        _fail(code)

    result = view.to_dict(include_generation_metadata=False)
    _bounded(result)
    _safe_output(result)
    payload = canonical(result) + '\n'
    if len(payload) > _MAX_OUTPUT_CHARS:
        _fail('OUTPUT_LIMIT')
    if stored is not None and stored.to_json(include_generation_metadata=False) + '\n' != payload:
        _fail('PROCESS_VIEW_STALE', 3)
    if args.expected_fingerprint is not None and args.expected_fingerprint != view.content_fingerprint:
        _fail('EXPECTED_FINGERPRINT_MISMATCH', 3)

    sys.stdout.write(payload)
    sys.stdout.flush()
    return 4 if args.strict and view.technical_status != 'COMPLETE_WITHIN_SELECTED_SCOPE' else 0


def run(argv):
    try:
        args = _configure(SafeParser(prog='kgmaker process')).parse_args(argv)
        args.root = args.root.resolve()
        if not args.root.is_dir():
            _fail('INVALID_ROOT')
        if args.expected_fingerprint is not None and re.fullmatch(r'[0-9a-f]{64}', args.expected_fingerprint) is None:
            _fail('INVALID_EXPECTED_FINGERPRINT')
        return _render(args)
    except ArchitectureCLIError as error:
        code, exit_code = error.code, error.exit_code
    except KeyboardInterrupt:
        code, exit_code = 'CANCELLED', 130
    except BrokenPipeError:
        return 141
    except (ValueError, TypeError, KeyError, AttributeError, OSError, RecursionError, OverflowError) as error:
        if isinstance(error, AnalysisError) and error.code == 3:
            code, exit_code = 'CURRENT_CAPTURE_CONFLICT', 3
        else:
            code, exit_code = 'INVALID_INPUT', 2
    except Exception:
        code, exit_code = 'INTERNAL_ERROR', 1
    sys.stderr.write(json.dumps({'code': code, 'exit_code': exit_code}) + '\n')
    return exit_code

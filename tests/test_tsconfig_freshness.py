"""Actual TypeScript effective-config freshness (T003-S08-W02)."""
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from kgmaker.inspection import inspect_frontend
from kgmaker.graph_provider import validate_context_snapshot
from kgmaker.worker_protocol import WorkerError

HOME = Path(__file__).resolve().parents[1] / 'workers'


def actual_typescript():
    if not shutil.which('node') or not (HOME / 'typescript/node_modules/typescript/lib/typescript.js').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Actual prepared TypeScript worker required')
        pytest.skip('Actual prepared TypeScript worker required')


def project(root, home=HOME):
    actual_typescript()
    (root / 'src/lib').mkdir(parents=True)
    (root / 'src/main.ts').write_text("import { target } from '@lib/used'; export function caller() { return target(); }\n")
    (root / 'src/lib/used.ts').write_text('export function target(): number { return 1; }\n')
    (root / 'src/unused.ts').write_text('export const unused = 1;\n')
    (root / 'tsconfig.base.json').write_text(json.dumps({'compilerOptions': {
        'target': 'ES2022', 'module': 'commonjs', 'baseUrl': '.', 'paths': {'@lib/*': ['src/lib/*']},
        'strict': True}, 'include': ['src/main.ts'], 'exclude': ['src/lib/used.ts', 'src/unused.ts']}))
    (root / 'tsconfig.a.json').write_text(json.dumps({'extends': './tsconfig.base.json'}))
    (root / 'tsconfig.b.json').write_text(json.dumps({'files': ['src/unused.ts']}))
    return inspect_frontend(root, tsconfig='tsconfig.a.json', home=home)


@pytest.mark.parametrize('change', ['sibling-config', 'excluded-source'])
def test_irrelevant_content_keeps_selected_config_fresh_offline(tmp_path, change):
    result = project(tmp_path)
    targets = {s['id']: s['path'] for s in result['graph']['symbols']}
    assert any(targets[c['declared_target']] == 'src/lib/used.ts'
               for c in result['graph']['call_sites'] if c.get('declared_target'))
    # Exclude limits root discovery; it must not remove imported dependencies.
    selected = result['context']
    saved = (tmp_path / '.kgmaker/graph.json').read_bytes()
    if change == 'sibling-config':
        (tmp_path / 'tsconfig.b.json').write_text(json.dumps({'compilerOptions': {'strict': False}, 'files': ['src/unused.ts']}))
    else:
        (tmp_path / 'src/unused.ts').write_text('export const unused = 2;\n')
    with patch('subprocess.Popen', side_effect=AssertionError('offline freshness launched a process')):
        validate_context_snapshot(tmp_path, selected)
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == saved


def test_new_negative_lookup_dependency_invalidates_without_store_mutation(tmp_path):
    actual_typescript()
    root = tmp_path / 'repo'
    (root / 'src').mkdir(parents=True)
    dependency = tmp_path / 'dep'
    dependency.mkdir()
    (root / 'src/main.ts').write_text("import { target } from '@dep'; export const result = target();\n")
    (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'target': 'ES2022',
        'module': 'commonjs', 'baseUrl': '.', 'paths': {'@dep': ['../dep/new']}}, 'files': ['src/main.ts']}))
    result = inspect_frontend(root, home=HOME)
    assert result['status'] == 'PARTIAL'
    saved = (root / '.kgmaker/graph.json').read_bytes()
    (dependency / 'new.ts').write_text('export function target(): number { return 1; }\n')
    with patch('subprocess.Popen', side_effect=AssertionError('offline freshness launched a process')):
        with pytest.raises(WorkerError) as caught:
            validate_context_snapshot(root, result['context'])
    assert caught.value.status == 'STALE'
    assert (root / '.kgmaker/graph.json').read_bytes() == saved


def test_two_config_contexts_refresh_independently_without_compiler(tmp_path):
    from kgmaker.feature import current_graph
    first = project(tmp_path)
    inspect_frontend(tmp_path, tsconfig='tsconfig.b.json', home=HOME)
    stored = tmp_path / '.kgmaker/graph.json'
    before = stored.read_bytes()
    (tmp_path / 'tsconfig.b.json').write_text(json.dumps({'compilerOptions': {'strict': False}, 'files': ['src/unused.ts']}))
    with patch('subprocess.Popen', side_effect=AssertionError('offline refresh launched compiler')):
        graph, _, _ = current_graph(tmp_path)
    contexts = {c.get('tsconfig'): c for c in graph.contexts if c.get('analyzer_version')}
    assert contexts['tsconfig.a.json']['freshness'] != 'STALE'
    assert contexts['tsconfig.b.json']['freshness'] == 'STALE'
    assert any(c['context_id'] == first['context']['id'] for c in graph.call_sites)
    assert stored.read_bytes() == before


@pytest.mark.parametrize('change', ['imported-excluded', 'extends-option', 'new-include-member', 'new-directory'])
def test_relevant_content_and_discovery_invalidate_selected_config(tmp_path, change):
    result = project(tmp_path)
    if change in {'new-include-member', 'new-directory'}:
        base = tmp_path / 'tsconfig.base.json'
        settings = json.loads(base.read_text())
        settings['include'] = ['src/**/*.ts']
        settings['exclude'] = ['src/unused.ts']
        base.write_text(json.dumps(settings))
        result = inspect_frontend(tmp_path, tsconfig='tsconfig.a.json', home=HOME)
    saved = (tmp_path / '.kgmaker/graph.json').read_bytes()
    if change == 'imported-excluded':
        (tmp_path / 'src/lib/used.ts').write_text('export function target(): number { return 2; }\n')
    elif change == 'extends-option':
        settings = json.loads((tmp_path / 'tsconfig.base.json').read_text())
        settings['compilerOptions']['strict'] = False
        (tmp_path / 'tsconfig.base.json').write_text(json.dumps(settings))
    else:
        target = tmp_path / ('src/new.ts' if change == 'new-include-member' else 'src/nested/new.ts')
        target.parent.mkdir(exist_ok=True)
        target.write_text('export const added = 1;\n')
    with patch('subprocess.Popen', side_effect=AssertionError('offline refresh launched compiler')):
        with pytest.raises(WorkerError) as caught:
            validate_context_snapshot(tmp_path, result['context'])
    assert caught.value.status == 'STALE'
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == saved


def test_alias_reinspection_uses_effective_extends_and_replaces_same_selector(tmp_path):
    initial = project(tmp_path)
    (tmp_path / 'src/lib/other.ts').write_text('export function target(): number { return 3; }\n')
    base = tmp_path / 'tsconfig.base.json'
    settings = json.loads(base.read_text())
    settings['compilerOptions']['paths'] = {'@lib/*': ['src/lib/other.ts']}
    base.write_text(json.dumps(settings))
    result = inspect_frontend(tmp_path, tsconfig='tsconfig.a.json', home=HOME)
    symbols = {s['id']: s['path'] for s in result['graph']['symbols']}
    assert any(symbols[c['declared_target']] == 'src/lib/other.ts'
               for c in result['graph']['call_sites'] if c.get('declared_target'))
    assert initial['context']['selection_key'] == result['context']['selection_key']
    assert len([c for c in result['graph']['contexts'] if c.get('analyzer_version')]) == 1


LOCKFILES = ['package-lock.json', 'npm-shrinkwrap.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lock', 'bun.lockb']


def test_lockfile_absence_content_and_removal_are_captured(tmp_path):
    initial = project(tmp_path)
    saved = (tmp_path / '.kgmaker/graph.json').read_bytes()
    for name in LOCKFILES:
        target = tmp_path / name
        assert any(o['op'] == 'file' and o['path'] == target.as_posix() and o['value'] is False
                   for o in initial['context']['project']['input_discovery']['observations'])
        target.write_bytes(b'lock content')
        with patch('subprocess.Popen', side_effect=AssertionError('offline compiler')):
            with pytest.raises(WorkerError):
                validate_context_snapshot(tmp_path, initial['context'])
        target.unlink()
    for name in LOCKFILES:
        (tmp_path / name).write_bytes(b'lock content')
    captured = inspect_frontend(tmp_path, tsconfig='tsconfig.a.json', home=HOME)
    for name in LOCKFILES:
        target = tmp_path / name
        target.write_bytes(b'changed lock content')
        with pytest.raises(WorkerError):
            validate_context_snapshot(tmp_path, captured['context'])
        target.write_bytes(b'lock content')
        target.unlink()
        with pytest.raises(WorkerError):
            validate_context_snapshot(tmp_path, captured['context'])
        target.write_bytes(b'lock content')
    # Only explicit reinspection may replace the store.
    assert saved != (tmp_path / '.kgmaker/graph.json').read_bytes()


def test_changed_discovery_between_worker_requests_preserves_store(tmp_path, monkeypatch):
    import kgmaker.inspection as inspection
    project(tmp_path)
    old = (tmp_path / '.kgmaker/graph.json').read_bytes()
    original = inspection.request_worker
    def intervene(argv, request, **options):
        response = original(argv, request, **options)
        if request.get('operation') == 'project':
            (tmp_path / 'yarn.lock').write_text('new lock between phases')
        return response
    monkeypatch.setattr(inspection, 'request_worker', intervene)
    with pytest.raises(WorkerError) as caught:
        inspect_frontend(tmp_path, tsconfig='tsconfig.a.json', home=HOME)
    assert caught.value.status == 'STALE'
    assert (tmp_path / '.kgmaker/graph.json').read_bytes() == old


@pytest.mark.parametrize('variant', ['version', 'boolean-version', 'relative', 'duplicate', 'operation', 'entry', 'file', 'limit', 'future-context', 'operation-container', 'entry-container', 'empty-proof', 'missing-observation', 'language'])
def test_malformed_snapshot_is_rejected_before_io(tmp_path, variant):
    snapshot = {'version': 1, 'case_sensitive': True, 'observations': [{'op': 'file', 'path': str(tmp_path / 'source.ts'), 'value': True}], 'directories': []}
    project_data = {'input_files': [{'path': str(tmp_path / 'source.ts'), 'sha256': '0' * 64}], 'input_discovery': snapshot}
    context = {'source_snapshot_version': 'typescript-input-discovery-1', 'language': 'typescript',
               'project': project_data, 'source_files': {}, 'analyzer_version': 'test'}
    if variant == 'version': snapshot['version'] = 99
    elif variant == 'boolean-version': snapshot['version'] = True
    elif variant == 'relative': snapshot['observations'] = [{'op': 'file', 'path': 'relative.ts', 'value': False}]
    elif variant == 'duplicate': snapshot['observations'] = [{'op': 'file', 'path': str(tmp_path / 'x'), 'value': False}] * 2
    elif variant == 'operation': snapshot['observations'] = [{'op': 'execute', 'path': str(tmp_path / 'x'), 'value': False}]
    elif variant == 'entry': snapshot['directories'] = [{'path': str(tmp_path), 'entries': [['../escape', 'file', None]]}]
    elif variant == 'file': project_data['input_files'] = [{'path': str(tmp_path / 'x')}]
    elif variant == 'limit': snapshot['observations'] = [None] * 20001
    elif variant == 'operation-container': snapshot['observations'][0]['op'] = []
    elif variant == 'entry-container': snapshot['directories'] = [{'path': str(tmp_path), 'entries': [['source.ts', [], None]]}]
    elif variant == 'empty-proof': project_data['input_files'] = []
    elif variant == 'missing-observation': snapshot['observations'] = []
    elif variant == 'language': context['language'] = 'jvm'
    else: context['source_snapshot_version'] = 'typescript-input-discovery-99'
    with patch('pathlib.Path.is_file', side_effect=AssertionError('malformed snapshot performed IO')), \
            patch('subprocess.Popen', side_effect=AssertionError('malformed snapshot launched process')):
        with pytest.raises(WorkerError) as caught:
            validate_context_snapshot(tmp_path, context)
    assert caught.value.status == 'STALE'


def test_unrelated_config_change_between_requests_does_not_abort_selected_inspection(tmp_path, monkeypatch):
    import kgmaker.inspection as inspection
    from kgmaker.analysis_model import file_hash
    project(tmp_path)
    original = inspection.request_worker
    def intervene(argv, request, **options):
        response = original(argv, request, **options)
        if request.get('operation') == 'project':
            (tmp_path / 'tsconfig.b.json').write_text(json.dumps({'compilerOptions': {'strict': False}, 'files': ['src/unused.ts']}))
        return response
    monkeypatch.setattr(inspection, 'request_worker', intervene)
    result = inspect_frontend(tmp_path, tsconfig='tsconfig.a.json', home=HOME)
    assert result['status'] == 'COMPLETE_WITHIN_SUPPORTED_MATRIX'
    assert result['graph']['files']['tsconfig.b.json'] == file_hash(tmp_path / 'tsconfig.b.json')
    validate_context_snapshot(tmp_path, result['context'])


def test_discovery_only_membership_change_between_requests_preserves_store(tmp_path, monkeypatch):
    import kgmaker.inspection as inspection
    actual_typescript()
    root = tmp_path / 'repo'
    (root / 'src').mkdir(parents=True)
    (tmp_path / 'dep').mkdir()
    (root / 'src/main.ts').write_text("import { target } from '@dep'; export const value = target();\n")
    (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'baseUrl': '.', 'paths': {'@dep': ['../dep/new']}}, 'files': ['src/main.ts']}))
    inspect_frontend(root, home=HOME)
    saved = (root / '.kgmaker/graph.json').read_bytes()
    original = inspection.request_worker
    def intervene(argv, request, **options):
        response = original(argv, request, **options)
        if request.get('operation') == 'project':
            (tmp_path / 'dep/new').mkdir()
        return response
    monkeypatch.setattr(inspection, 'request_worker', intervene)
    with pytest.raises(WorkerError, match='discovery changed') as caught:
        inspect_frontend(root, home=HOME)
    assert caught.value.status == 'STALE'
    assert saved == (root / '.kgmaker/graph.json').read_bytes()


def test_legacy_snapshot_retains_conservative_fallback(tmp_path):
    from copy import deepcopy
    from kgmaker.inspection import source_snapshot
    from kgmaker.scanner import scan_repository
    current = project(tmp_path)['context']
    legacy = deepcopy(current)
    legacy.pop('source_snapshot_version')
    legacy['project'].pop('input_discovery')
    legacy['source_files'] = source_snapshot(tmp_path, scan_repository(tmp_path), legacy)
    validate_context_snapshot(tmp_path, legacy)
    (tmp_path / 'src/unused.ts').write_text('export const unused = 10;\n')
    with patch('subprocess.Popen', side_effect=AssertionError('legacy validation ran compiler')):
        with pytest.raises(WorkerError):
            validate_context_snapshot(tmp_path, legacy)
        validate_context_snapshot(tmp_path, current)


@pytest.mark.parametrize('version', [1, 2, 3])
def test_new_snapshot_survives_supported_graph_loader_versions(tmp_path, version):
    from kgmaker.model import KnowledgeGraph
    context = project(tmp_path)['context']
    graph = KnowledgeGraph.from_dict({'schema_version': version, 'root': str(tmp_path),
        'generated_at': '', 'files': {}, 'nodes': [], 'edges': [], 'contexts': [context]})
    assert graph.contexts[0]['project']['input_discovery'] == context['project']['input_discovery']
    validate_context_snapshot(tmp_path, graph.contexts[0])


@pytest.mark.parametrize('helper_name', ['input_snapshot.cjs', 'ui_events.cjs'])
def test_snapshot_helper_is_hash_bound_to_distribution(tmp_path, helper_name):
    custom = tmp_path / 'custom-workers/typescript'
    custom.mkdir(parents=True)
    for name in ('worker.cjs', 'input_snapshot.cjs', 'ui_events.cjs', 'package.json'):
        shutil.copy2(HOME / 'typescript' / name, custom / name)
    try:
        (custom / 'node_modules').symlink_to(HOME / 'typescript/node_modules', target_is_directory=True)
    except OSError:
        pytest.skip('toolchain symlink permission unavailable')
    root = tmp_path / 'repo'
    result = project(root, home=custom.parent)
    helper = custom / helper_name
    assert any(Path(item['path']) == helper for item in result['context']['worker']['distribution'])
    helper.write_text(helper.read_text() + '\n// changed distribution\n')
    with patch('subprocess.Popen', side_effect=AssertionError('distribution validation ran compiler')):
        with pytest.raises(WorkerError, match='distribution changed'):
            validate_context_snapshot(root, result['context'])


def test_incomplete_snapshot_distribution_fails_before_process(tmp_path):
    from kgmaker.inspection import command
    root = tmp_path / 'workers'
    worker = root / 'typescript'
    (worker / 'node_modules/typescript/lib').mkdir(parents=True)
    (worker / 'node_modules/typescript/lib/typescript.js').write_text('not executed')
    (worker / 'worker.cjs').write_text('not executed')
    (worker / 'package.json').write_text(json.dumps({'kgmaker_input_snapshot': 1}))
    with patch('kgmaker.inspection.shutil.which', return_value='node'), \
            patch('subprocess.Popen', side_effect=AssertionError('incomplete distribution launched a process')):
        with pytest.raises(WorkerError, match='snapshot helper unavailable') as caught:
            command('typescript', root)
    assert caught.value.status == 'TOOLCHAIN_UNAVAILABLE'

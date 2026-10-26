"""T003-S08-W01: actual TypeScript project graphs, without emitting/building."""
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from kgmaker.feature import current_graph
from kgmaker.inspection import inspect_frontend
from kgmaker.model import KnowledgeGraph
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / 'workers'


@pytest.fixture(autouse=True)
def actual_typescript():
    if not shutil.which('node') or not (WORKERS / 'typescript/node_modules/typescript/lib/typescript.js').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('blocked: actual TypeScript 5.7.3 worker required')
        pytest.skip('blocked: actual TypeScript 5.7.3 worker required')


def config(root, project, references=()):
    directory = root / project
    (directory / 'src').mkdir(parents=True)
    (directory / 'tsconfig.json').write_text(json.dumps({
        'compilerOptions': {'composite': True, 'declaration': True, 'strict': True,
                            'target': 'ES2022', 'module': 'commonjs', 'rootDir': 'src', 'outDir': 'dist'},
        'include': ['src/*.ts'], 'references': [{'path': '../' + ref} for ref in references],
    }))
    return directory / 'src/index.ts'


def solution(root):
    config(root, 'left').write_text('export function choose(x: number): number { return x + 1; }')
    config(root, 'right').write_text('export function choose(x: number): number { return x + 2; }')
    config(root, 'app', ('left', 'right')).write_text('''
import {choose as left} from '../../left/src/index';
import {choose as right} from '../../right/src/index';
export function run() { const a = left(1); const b = right(2); return a + b; }
''')
    (root / 'tsconfig.json').write_text(json.dumps({'files': [], 'references': [{'path': './app'}]}))


def inspect(root, **options):
    return inspect_frontend(root, home=WORKERS, repo_id='composite-fixture', **options)


def test_solution_programs_resolve_exact_source_project_identities_without_outputs(tmp_path):
    solution(tmp_path)
    before = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = inspect(tmp_path, publish=False)
    assert result['status'] == 'COMPLETE_WITHIN_SUPPORTED_MATRIX', result['diagnostics']
    graph = KnowledgeGraph.from_dict(result['graph'])
    calls = [site for site in graph.call_sites if site['path'] == 'app/src/index.ts']
    assert len(calls) == 2
    targets = {symbol['id']: symbol for symbol in graph.symbols}
    assert {targets[site['declared_target']]['path'] for site in calls} == {'left/src/index.ts', 'right/src/index.ts'}
    assert all(site['evidence_kind'] == 'SYMBOL_RESOLVED' for site in calls)
    assert len({site['declared_target'] for site in calls}) == 2
    projects = result['context']['project']['project_graph']['projects']
    assert {project['config'] for project in projects} == {'tsconfig.json', 'app/tsconfig.json', 'left/tsconfig.json', 'right/tsconfig.json'}
    assert all(project['id'].startswith('ts-project:composite-fixture:') for project in projects)
    assert all(targets[site['declared_target']]['project_id'].endswith(('left/tsconfig.json', 'right/tsconfig.json')) for site in calls)
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before
    assert not list(tmp_path.rglob('dist')) and not list(tmp_path.rglob('*.tsbuildinfo'))


def test_source_redirect_does_not_resolve_against_stale_emitted_declaration(tmp_path):
    solution(tmp_path)
    output = tmp_path / 'left/dist/index.d.ts'
    output.parent.mkdir()
    output.write_text('export declare function choose(x: string): boolean;')
    result = inspect(tmp_path, publish=False)
    calls = [site for site in result['graph']['call_sites'] if site['path'] == 'app/src/index.ts']
    targets = {symbol['id']: symbol for symbol in result['graph']['symbols']}
    left = next(site for site in calls if targets[site['declared_target']]['path'] == 'left/src/index.ts')
    assert left['signature'] == '(x: number): number'
    assert not any(symbol['path'] == 'left/dist/index.d.ts' for symbol in targets.values())
    assert output.read_text() == 'export declare function choose(x: string): boolean;'


def test_incremental_project_fingerprints_propagate_only_through_reference_edges(tmp_path):
    solution(tmp_path)
    before = inspect(tmp_path, publish=False)['context']['project']['project_graph']['projects']
    source = tmp_path / 'left/src/index.ts'
    source.write_text(source.read_text() + '\n// new source snapshot\n')
    after = inspect(tmp_path, publish=False)['context']['project']['project_graph']['projects']
    old = {project['config']: project for project in before}
    new = {project['config']: project for project in after}
    assert {key: value['id'] for key, value in old.items()} == {key: value['id'] for key, value in new.items()}
    assert {key for key in old if old[key]['fingerprint'] != new[key]['fingerprint']} == {
        'left/tsconfig.json', 'app/tsconfig.json', 'tsconfig.json'}
    assert old['right/tsconfig.json']['fingerprint'] == new['right/tsconfig.json']['fingerprint']


@pytest.mark.parametrize('invalid', ['missing', 'cycle', 'outside'])
def test_invalid_reference_graph_is_localized_and_does_not_replace_store(tmp_path, invalid):
    solution(tmp_path)
    inspect(tmp_path)
    store = tmp_path / '.kgmaker/graph.json'
    before = store.read_bytes()
    selected = tmp_path / 'app/tsconfig.json'
    payload = json.loads(selected.read_text())
    if invalid == 'missing':
        payload['references'].append({'path': '../absent'})
        selected.write_text(json.dumps(payload))
        code = 'TS_PROJECT_REFERENCE_MISSING'
    elif invalid == 'cycle':
        selected = tmp_path / 'left/tsconfig.json'
        payload = json.loads(selected.read_text())
        payload['references'] = [{'path': '../app'}]
        selected.write_text(json.dumps(payload))
        code = 'TS_PROJECT_REFERENCE_CYCLE'
    else:
        payload['references'].append({'path': '../../outside'})
        selected.write_text(json.dumps(payload))
        code = 'TS_PROJECT_REFERENCE_OUTSIDE_ROOT'
    with pytest.raises(WorkerError) as error:
        inspect(tmp_path)
    assert code in str(error.value)
    assert selected.relative_to(tmp_path).as_posix() in str(error.value)
    assert store.read_bytes() == before


@pytest.mark.parametrize('changed', ['source', 'config'])
def test_transitive_project_edit_invalidates_stored_compiler_layer_offline(tmp_path, changed):
    solution(tmp_path)
    inspect(tmp_path)
    store = tmp_path / '.kgmaker/graph.json'
    before = store.read_bytes()
    if changed == 'source':
        (tmp_path / 'left/src/index.ts').write_text('export function choose(x: string): string { return x; }')
    else:
        path = tmp_path / 'left/tsconfig.json'
        config = json.loads(path.read_text())
        config['compilerOptions']['strict'] = False
        path.write_text(json.dumps(config))
    with patch('subprocess.Popen', side_effect=AssertionError('offline refresh ran a process')):
        graph, _, _ = current_graph(tmp_path)
    contexts = [c for c in graph.contexts if c.get('analyzer_version')]
    assert len(contexts) == 1 and contexts[0]['freshness'] == 'STALE'
    assert not graph.call_sites
    assert store.read_bytes() == before


def test_overlapping_projects_do_not_arbitrarily_choose_symbol_owner(tmp_path):
    solution(tmp_path)
    path = tmp_path / 'right/tsconfig.json'
    payload = json.loads(path.read_text())
    payload['include'].append('../left/src/*.ts')
    path.write_text(json.dumps(payload))
    with pytest.raises(WorkerError, match='TS_PROJECT_SOURCE_AMBIGUOUS:right/tsconfig.json: left/src/index.ts'):
        inspect(tmp_path)
    assert not (tmp_path / '.kgmaker').exists()


def test_graph_loader_legacy_versions_remain_accepted(tmp_path):
    for version in (1, 2, 3):
        graph = KnowledgeGraph.from_dict({'schema_version': version, 'root': str(tmp_path),
            'generated_at': '', 'nodes': [], 'edges': [], 'files': {}})
        assert graph.schema_version == version

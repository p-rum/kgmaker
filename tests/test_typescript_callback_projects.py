"""Canonical callback binding identities across real referenced Programs/checkers."""
import json
import os
from pathlib import Path
import shutil

import pytest

from kgmaker.inspection import inspect_frontend
from kgmaker.model import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


@pytest.mark.parametrize('consumer_strict', [True, False])
def test_callback_parameter_and_candidates_use_owner_program_ids(tmp_path, consumer_strict):
    if not shutil.which('node') or not (HOME / 'typescript/node_modules/typescript/lib/typescript.js').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Actual pinned TypeScript required')
        pytest.skip('Actual TypeScript unavailable')
    for name, strict in [('lib', True), ('app', consumer_strict)]:
        directory = tmp_path / name
        (directory / 'src').mkdir(parents=True)
        config = {'compilerOptions': {'composite': True, 'strict': strict, 'target': 'ES2022',
                                     'module': 'commonjs', 'rootDir': 'src', 'outDir': 'dist'},
                  'include': ['src/**/*.ts']}
        if name == 'app':
            config['references'] = [{'path': '../lib'}]
        (directory / 'tsconfig.json').write_text(json.dumps(config))
    (tmp_path / 'tsconfig.json').write_text(json.dumps({'files': [], 'references': [{'path': './app'}]}))
    (tmp_path / 'lib/src/api.ts').write_text('''
export function apply(value: number | null, callback: (value: number | null) => string): string {
  return callback(value);
}
''')
    argument_type = 'number | null' if consumer_strict else 'number'
    (tmp_path / 'app/src/main.ts').write_text('''
import { apply } from '../../lib/src/api';
function handler(value: TYPE): string { return String(value); }
const first = handler;
const alias = first;
export function run(): string { return apply(1, alias); }
'''.replace('TYPE', argument_type))
    all_ids = []
    for repo in ['callback-owner-a', 'callback-owner-b']:
        result = inspect_frontend(tmp_path, home=HOME, repo_id=repo, publish=False)
        graph = KnowledgeGraph.from_dict(result['graph'])
        symbols = {s['id']: s for s in graph.symbols}
        inner = next(site for site in graph.call_sites if site['path'] == 'lib/src/api.ts')
        assert inner['declared_target'] is None
        assert inner['resolution_reason'] == 'CALLBACK_PARAMETER_OPEN_WORLD'
        assert {symbols[target]['name'] for target in inner['dispatch_candidates']} == {'handler'}
        assert all(symbols[target]['project_id'].endswith(':app/tsconfig.json') for target in inner['dispatch_candidates'])
        parameters = [s for s in graph.symbols if s['name'] == 'callback' and s['kind'] == 'parameter']
        assert len(parameters) == 1 and parameters[0]['project_id'].endswith(':lib/tsconfig.json')
        assert parameters[0]['method'] == inner['caller']
        assert parameters[0]['id'] == inner['caller'] + ':parameter:1'
        occurrences = [edge for edge in graph.edges if edge.kind == 'argument_to_parameter'
                       and edge.target == parameters[0]['id'] and symbols[edge.source]['kind'] == 'value']
        assert len(occurrences) == 1 and occurrences[0].evidence_kind == 'SYMBOL_RESOLVED'
        occurrence = symbols[occurrences[0].source]
        outer = next(call for call in graph.call_sites if call['id'] == occurrence['call_site'])
        assert occurrence['owner_method'] == outer['caller']
        assert outer['declared_target'] == inner['caller']
        assert any(edge.kind == 'argument_to_parameter' and edge.target == parameters[0]['id']
                   and edge.source in inner['dispatch_candidates'] for edge in graph.edges)
        assert any(cfg['method'] == inner['caller'] for cfg in graph.cfgs)
        all_ids.append(set(symbols))
    assert all_ids[0].isdisjoint(all_ids[1])
    assert not list(tmp_path.rglob('dist')) and not list(tmp_path.rglob('*.tsbuildinfo'))

"""Bounded callback candidates retain useful partial evidence and atomic publication."""
import json
import os
from pathlib import Path
import shutil

import pytest

from kgmaker.inspection import inspect_frontend
from kgmaker.model import KnowledgeGraph
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


@pytest.fixture(autouse=True)
def actual_typescript():
    if not shutil.which('node') or not (HOME / 'typescript/node_modules/typescript/lib/typescript.js').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Actual pinned TypeScript worker required')
        pytest.skip('Actual TypeScript unavailable')


def project(root, source):
    (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {
        'strict': True, 'target': 'ES2022', 'module': 'commonjs'}, 'include': ['*.ts']}))
    (root / 'app.ts').write_text(source)


def test_dependency_callback_bindings_do_not_consume_local_dispatch_limit(tmp_path):
    source = 'const values = [1, 2];\n' + '\n'.join(
        f'const output{i} = values.map(value => value + {i});' for i in range(65))
    project(tmp_path, source)
    result = inspect_frontend(tmp_path, home=HOME, publish=False)
    assert result['status'] == 'COMPLETE_WITHIN_SUPPORTED_MATRIX'
    assert result['coverage']['calls_resolved'] == 65
    assert not any(d.get('code') == 'CALLBACK_TARGET_LIMIT' for d in result['diagnostics'])


def test_local_callback_limit_reports_partial_candidates_instead_of_losing_graph(tmp_path):
    source = 'function apply(callback: (value: number) => number) { return callback(1); }\n' + '\n'.join(
        f'const output{i} = apply(value => value + {i});' for i in range(65))
    project(tmp_path, source)
    result = inspect_frontend(tmp_path, home=HOME, publish=False)
    graph = KnowledgeGraph.from_dict(result['graph'])
    site = next(site for site in graph.call_sites if ':apply:' in site['caller'])
    assert result['status'] == 'PARTIAL'
    assert len(site['dispatch_candidates']) == 64
    assert site['declared_target'] is None and site['dispatch_complete'] is False
    assert site['resolution_reason'] == 'CALLBACK_TARGET_LIMIT'
    assert any(d.get('code') == 'CALLBACK_TARGET_LIMIT' and d.get('call_site') == site['id']
               for d in result['diagnostics'])
    assert (tmp_path / 'app.ts').read_text() == source


def test_invalid_callback_candidate_preserves_last_valid_store(tmp_path, monkeypatch):
    import kgmaker.inspection as inspection
    project(tmp_path, 'function apply(callback: (value: number) => number) { return callback(1); }\n'
                      'const output = apply(value => value + 1);')
    inspect_frontend(tmp_path, home=HOME)
    store = tmp_path / '.kgmaker/graph.json'
    before = store.read_bytes()
    request = inspection.request_worker
    def corrupt(*args, **kwargs):
        response = request(*args, **kwargs)
        if args[1].get('operation') == 'analyze':
            site = next(site for site in response['call_sites'] if ':apply:' in site['caller'])
            site['dispatch_candidates'].append('ts:invented-callback')
        return response
    monkeypatch.setattr(inspection, 'request_worker', corrupt)
    with pytest.raises(WorkerError) as caught:
        inspect_frontend(tmp_path, home=HOME)
    assert caught.value.status == 'INVALID_PROTOCOL'
    assert store.read_bytes() == before


def test_union_callback_argument_keeps_each_binding_as_candidate(tmp_path):
    project(tmp_path, '''
function apply<T, U>(value: T, callback: (value: T) => U): U { return callback(value); }
function asNumber(value: number): number { return value; }
function asString(value: number): string { return String(value); }
export function run(flag: boolean) {
  return apply<number, number | string>(1, flag ? asNumber : asString);
}
''')
    result = inspect_frontend(tmp_path, home=HOME, publish=False)
    graph = KnowledgeGraph.from_dict(result['graph'])
    symbols = {s['id']: s for s in graph.symbols}
    site = next(site for site in graph.call_sites if ':apply:' in site['caller'])
    assert {symbols[target]['name'] for target in site['dispatch_candidates']} == {'asNumber', 'asString'}
    bindings = [edge for edge in graph.edges if edge.kind == 'argument_to_parameter'
                and symbols[edge.target]['name'] == 'callback']
    assert len(bindings) == 2
    assert all(edge.evidence_kind == 'DISPATCH_CANDIDATE' for edge in bindings)
    assert site['declared_target'] is None and site['dispatch_complete'] is False
    assert result['status'] == 'PARTIAL'


def test_single_callback_expression_limit_is_reported_at_parameter_invocation(tmp_path):
    names = [f'f{i}' for i in range(65)]
    def choice(items):
        if len(items) == 1:
            return items[0]
        middle = len(items) // 2
        return f'(flag ? {choice(items[:middle])} : {choice(items[middle:])})'
    source = 'function apply(callback: (value: number) => number) { return callback(1); }\n'
    source += '\n'.join(f'function {name}(value: number) {{ return value + {i}; }}' for i, name in enumerate(names))
    source += f'\nexport function run(flag: boolean) {{ return apply({choice(names)}); }}'
    project(tmp_path, source)
    result = inspect_frontend(tmp_path, home=HOME, publish=False)
    graph = KnowledgeGraph.from_dict(result['graph'])
    site = next(site for site in graph.call_sites if ':apply:' in site['caller'])
    assert result['status'] == 'PARTIAL'
    assert site['resolution_reason'] == 'CALLBACK_TARGET_LIMIT'
    assert len(site['dispatch_candidates']) == 64 and not site['dispatch_complete']

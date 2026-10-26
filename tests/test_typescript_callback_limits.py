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

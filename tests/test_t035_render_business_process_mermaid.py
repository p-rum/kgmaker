"""Public process diagram tests over independently checked ProcessView inputs."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.process_model import ProcessDefinition, ProcessView
from test_t029_project_process_failures import actual_pipeline  # pytest fixture for the real Javac case


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/process-model/checkout.json'


def render(view):
    from kgmaker.process_render import render_process_mermaid
    return render_process_mermaid(view)


def records(diagram, name):
    prefix = f'  %% process-{name} '
    return [json.loads(line[len(prefix):]) for line in diagram.splitlines() if line.startswith(prefix)]


def check_records(view, diagram):
    document = view.to_dict(include_generation_metadata=False)
    technical = document['technical_view']
    meta, = records(diagram, 'meta')
    assert {k: v for k, v in technical.items() if k not in {'nodes', 'edges'}} == meta['technical_view']
    assert meta['technical_status'] == document['technical_status']
    assert meta['context_ids'] == document['definition']['context_ids']
    assert [record['node'] for record in records(diagram, 'node')] == sorted(technical['nodes'], key=lambda row: row['id'])
    assert [record['edge'] for record in records(diagram, 'edge')] == sorted(technical['edges'], key=lambda row: row['id'])


def parse_and_render(diagram, tmp_path):
    harness = ROOT / 'tests/rendering/validate_t035_process.mjs'
    node = shutil.which('node')
    if node is None or not (harness.parent / 'node_modules/mermaid/package.json').is_file():
        pytest.skip('Pinned Mermaid 11.4.1/jsdom 26.0.0 test runtime unavailable')
    path = tmp_path / 'process.mmd'
    path.write_text(diagram, encoding='utf-8')
    run = subprocess.run([node, str(harness), str(path)], check=False, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr[-4000:]
    return json.loads(run.stdout)


def test_t023_checked_in_branch_cycle_and_origins_are_deterministic():
    source = FIXTURE.read_bytes()
    view = ProcessView.from_dict(json.loads(source))
    snapshot = view.to_json()
    with patch('pathlib.Path.open', side_effect=AssertionError('renderer read a file')), \
            patch('subprocess.Popen', side_effect=AssertionError('renderer started a process')), \
            patch('socket.socket', side_effect=AssertionError('renderer opened a socket')):
        diagram = render(view)
        assert render(view) == diagram
    check_records(view, diagram)
    assert len(records(diagram, 'node')) == 7 and len(records(diagram, 'edge')) == 8
    assert {'true', 'false', 'retry', 'async', 'exception'} <= {record['edge']['relation'] for record in records(diagram, 'edge')}
    assert records(diagram, 'lane') == []
    raw = json.loads(source)
    for name in ('nodes', 'edges', 'provenance'):
        raw['technical_view'][name].reverse()
    assert render(ProcessView.from_dict(raw)) == diagram
    assert view.to_json() == snapshot and FIXTURE.read_bytes() == source


def test_t023_golden_parses_and_renders_branch_cycle(tmp_path):
    view = ProcessView.from_dict(json.loads(FIXTURE.read_bytes()))
    diagram = render(view)
    assert sha256(diagram.encode('utf-8')).hexdigest() == '55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa'
    assert 'payment == CARD' in diagram and 'retry budget remains' in diagram
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 8, 'lanes': 0}


def test_t028_projection_places_service_lanes_without_ordering_fanout(tmp_path):
    from test_t028_cross_async_process_boundary import api, consumers, imported, local, project_remote, reaches, specimen

    def owned(view, owner):
        document = view.to_dict()
        for node in document['technical_view']['nodes']:
            node['owner_id'] = owner
        return ProcessView.from_dict(document)

    view = api(owned(local(), 'service:checkout'), project_remote(specimen(fanout=True)),
               target_processes=[owned(consumer, 'service:orders') for consumer in consumers()])
    original = view.to_json()
    left = {node.id for node in imported(view, 'consumer-a')}
    right = {node.id for node in imported(view, 'consumer-b')}
    assert left and right and left.isdisjoint(right)
    assert not any(reaches(view, a, b) or reaches(view, b, a) for a in left for b in right)
    diagram = render(view)
    check_records(view, diagram)
    assert {r['owner_id'] for r in records(diagram, 'lane')} == {'service:checkout', 'service:orders'}
    assert any(r['edge']['relation'] == 'async' for r in records(diagram, 'edge'))
    assert parse_and_render(diagram, tmp_path) == {'vertices': len(view.steps), 'edges': len(view.transitions), 'lanes': 2}
    assert view.to_json() == original


@pytest.mark.parametrize('actual_pipeline', ['java'], indirect=True)
def test_real_t029_javac_retry_dlt_keeps_static_boundary_and_exception_path(actual_pipeline, tmp_path):
    from kgmaker.business_process import collapse_business_steps, project_process_failures
    from test_t025_build_local_process_path import paths

    graph, source, root, language = actual_pipeline
    assert language == 'java'
    view = project_process_failures(collapse_business_steps(source), graph)
    original = view.to_json()
    files = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
    retry, = [node for node in view.steps if node.attributes.get('failure_role') == 'retry']
    dlt, = [node for node in view.steps if node.attributes.get('failure_role') == 'dlt']
    assert retry.attributes['attempts'] == 3 and paths(view.transitions, retry.id, dlt.id)
    exceptional, = [node for node in source.steps if node.kind == 'exceptional_exit'
                    and node.attributes.get('method') == retry.attributes['origin_method']]
    assert paths(view.transitions, exceptional.id, retry.id)
    assert dlt.attributes['delivery'] == 'NOT_OBSERVED'
    diagram = render(view)
    check_records(view, diagram)
    assert 'STATIC_POLICY_ONLY' in diagram and 'NOT_OBSERVED' in diagram
    assert parse_and_render(diagram, tmp_path) == {'vertices': len(view.steps), 'edges': len(view.transitions), 'lanes': 1}
    assert view.to_json() == original
    assert {path: path.read_bytes() for path in root.rglob('*') if path.is_file()} == files


def test_truncated_parallel_edges_escaped_text_and_no_unverified_business_label(tmp_path):
    document = json.loads(FIXTURE.read_bytes())
    technical = document['technical_view']
    scope = 'typed scope "<script>"\n---'
    technical['scope'] = document['definition']['scope'] = scope
    document['definition_fingerprint'] = ProcessDefinition.from_dict(document['definition']).content_fingerprint
    for item in [*technical['nodes'], *technical['edges']]:
        item['attributes']['scope'] = scope
    for proof in technical['provenance']:
        proof['scope'] = scope
    technical['coverage'] = {'status': 'PARTIAL', 'truncated': True, 'omitted_nodes': 2}
    document['technical_status'] = 'PARTIAL'
    choose = next(n for n in technical['nodes'] if n['id'] == 'choose')
    choose.update(label='Check "A|B"\u2028\n%%{text} <b> & <script>alert(1)</script>', owner_id='team:unverified')
    choose['attributes']['service_id'] = 'invented-from-attribute'
    parallel = deepcopy(next(e for e in technical['edges'] if e['id'] == 'pay-card'))
    parallel.update(id='pay-card-alternative', original_ids=['second-card-branch'])
    parallel['attributes']['condition'] = 'value < 3 || value > 8'
    technical['edges'].append(parallel)
    document['semantic_annotations'] = [{'id': 'submitted', 'target_id': 'choose', 'label': 'Unverified semantic label',
        'source_refs': ['choose'], 'semantic_review_status': 'APPROVED'}]
    view = ProcessView.from_dict(document)
    diagram = render(view)
    check_records(view, diagram)
    assert records(diagram, 'lane') == []
    assert 'TRUNCATED' in diagram.splitlines()[1] and 'Unverified semantic label' not in diagram
    assert 'value #lt; 3 || value #gt; 8' in diagram
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 9, 'lanes': 0}


@pytest.mark.parametrize(('mutation', 'code'), [
    ('scope', 'INVALID_PROCESS_MERMAID'), ('context', 'INVALID_PROCESS_MERMAID'),
    ('type', 'INVALID_PROCESS_MERMAID'), ('size', 'PROCESS_MERMAID_LIMIT'),
    ('unsafe', 'UNSAFE_PROCESS_MERMAID'),
])
def test_invalid_input_and_limits_leave_supplied_and_last_valid_artifact_unchanged(tmp_path, mutation, code):
    from kgmaker.process_render import ProcessMermaidError

    document = json.loads(FIXTURE.read_bytes())
    artifact = tmp_path / 'kept.mmd'
    artifact.write_bytes(b'last valid\n')
    view = ProcessView.from_dict(document)
    data = view._document
    node = data['technical_view']['nodes'][0]
    if mutation == 'scope':
        node['attributes']['scope'] = 'test'
    elif mutation == 'context':
        node['attributes']['context_ids'] = ['foreign-context']
    elif mutation == 'size':
        node['label'] = 'x' * 16385
    elif mutation == 'unsafe':
        node['label'] = 'Bearer synthetic-private-value'
    before = deepcopy(data)
    with pytest.raises(ProcessMermaidError, match=code):
        render(data if mutation == 'type' else view)
    assert before == data and artifact.read_bytes() == b'last valid\n'


def test_output_bound_refuses_the_whole_diagram(monkeypatch):
    from kgmaker.process_render import ProcessMermaidError

    view = ProcessView.from_dict(json.loads(FIXTURE.read_bytes()))
    original = view.to_json()
    monkeypatch.setattr('kgmaker.process_render._MAX_OUTPUT_BYTES', 100)
    with pytest.raises(ProcessMermaidError, match='PROCESS_MERMAID_LIMIT'):
        render(view)
    assert view.to_json() == original

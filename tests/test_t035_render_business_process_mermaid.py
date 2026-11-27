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
from test_t030_prepare_process_label_packet import document as captured_document


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


def parse_and_render(diagram, tmp_path, *, expected_labels=None):
    harness = ROOT / 'tests/rendering/validate_t035_process.mjs'
    node = shutil.which('node')
    if node is None or not (harness.parent / 'node_modules/mermaid/package.json').is_file():
        pytest.skip('Pinned Mermaid 11.4.1/jsdom 26.0.0 test runtime unavailable')
    path = tmp_path / 'process.mmd'
    path.write_text(diagram, encoding='utf-8')
    command = [node, str(harness), str(path)]
    if expected_labels is not None:
        labels = tmp_path / 'approved-labels.json'
        labels.write_text(json.dumps(expected_labels), encoding='utf-8')
        command.append(str(labels))
    run = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
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


@pytest.mark.parametrize('exceeded', ['edges', 'text'])
def test_default_mermaid_host_limits_refuse_the_whole_diagram(tmp_path, exceeded):
    from kgmaker.process_render import ProcessMermaidError

    source = FIXTURE.read_bytes()
    document = json.loads(source)
    technical = document['technical_view']
    if exceeded == 'edges':
        original_edge = technical['edges'][0]
        for index in range(501 - len(technical['edges'])):
            identifier = f'parallel-{index}'
            technical['edges'].append({**original_edge, 'id': identifier, 'original_ids': [identifier]})
    else:
        for node in technical['nodes'][:4]:
            node['label'] = '\U0001f535' * 6500
    view = ProcessView.from_dict(document)
    snapshot = view.to_json()
    artifact = tmp_path / 'kept.mmd'
    artifact.write_bytes(b'last valid\n')

    with pytest.raises(ProcessMermaidError, match='PROCESS_MERMAID_LIMIT'):
        render(view)

    assert view.to_json() == snapshot and FIXTURE.read_bytes() == source
    assert artifact.read_bytes() == b'last valid\n'


def test_mermaid_host_text_budget_excludes_evidence_comments(tmp_path):
    document = json.loads(FIXTURE.read_bytes())
    for node in document['technical_view']['nodes'][:4]:
        node['label'] = '\U0001f535' * 5700
    view = ProcessView.from_dict(document)
    snapshot = view.to_json()
    diagram = render(view)
    assert len(diagram) > 50_000
    check_records(view, diagram)
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 8, 'lanes': 0}
    assert view.to_json() == snapshot


def render_reviewed(root, view, **captures):
    from kgmaker.process_render import render_reviewed_process_mermaid
    return render_reviewed_process_mermaid(root, view, **captures)


def record_review(root, view, labels, *, documents=(), action='APPROVE', head=None):
    from kgmaker.process_semantics import prepare_process_label_packet
    from kgmaker.process_store import prepare_process_review, persist_process_review

    packet = prepare_process_label_packet(view, documents=documents)['packet']
    candidate = {'schema_version': 1, 'packet_hash': packet['packet_hash'], 'annotations': [
        {'id': f'candidate:{index}', 'target_id': target, 'label': label,
         'source_refs': ['doc:guide'] if documents else [target], 'semantic_review_status': 'PROPOSED'}
        for index, (target, label) in enumerate(labels)
    ]}
    prepared = prepare_process_review(view, packet, candidate, documents=documents)
    receipt = persist_process_review(root, view, packet, candidate, documents=documents, action=action,
                                     reviewer='local:reviewer', operation_id=f'diagram:{action}:{head or "first"}',
                                     expected_head=head, expected_payload_hash=prepared['payload_hash'],
                                     expected_baseline_hash=prepared['baseline_hash'])
    assert receipt['status'] == 'COMMITTED'
    return receipt['head']


def file_snapshot(root):
    return {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob('*') if path.is_file()}


def test_effective_reviewed_labels_bind_to_exact_title_node_and_parallel_edge(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    source = json.loads(FIXTURE.read_bytes())
    technical = source['technical_view']
    parallel = deepcopy(next(edge for edge in technical['edges'] if edge['id'] == 'pay-card'))
    parallel.update(id='pay-card-alternative', original_ids=['alternative-card-branch'])
    technical['edges'].append(parallel)
    for node in technical['nodes'][:2]:
        node['owner_id'] = 'service:orders'
    view = ProcessView.from_dict(source)
    snapshot = view.to_json()
    original = render(view)
    documents = [captured_document(text='Captured source for reviewed labels.')]
    labels = {'title': 'Reviewed checkout', 'node': {'card': 'Reviewed card'},
              'edge': {'pay-card-alternative': 'Reviewed alternative'}}
    card = ('card', 'Reviewed card "quoted" <script>sample</script> & detail')
    approved = record_review(root, view, [('process:checkout', labels['title']), card, card,
                                         *labels['edge'].items()], documents=documents)
    record_review(root, view, [('card', 'Rejected proposal')], documents=documents, action='REJECT', head=approved)
    (root / 'kept.mmd').write_text(original, encoding='utf-8')
    before = file_snapshot(root)

    with patch('subprocess.Popen', side_effect=AssertionError('renderer started a process')), \
            patch('socket.socket', side_effect=AssertionError('renderer opened a socket')):
        diagram = render_reviewed(root, view, documents=documents)
        assert diagram == render_reviewed(root, view, documents=documents)
    assert render(view) == original
    assert [line for line in diagram.splitlines() if line.startswith('  %% process-')] == [
        line for line in original.splitlines() if line.startswith('  %% process-')]
    original_title = json.loads(original.splitlines()[1].removeprefix('title: '))
    assert json.loads(diagram.splitlines()[1].removeprefix('title: ')).startswith(original_title)
    assert 'Rejected proposal' not in diagram and 'Reviewed card #quot;quoted#quot;' in diagram
    check_records(view, diagram)
    assert parse_and_render(diagram, tmp_path, expected_labels=labels) == {'vertices': 7, 'edges': 9, 'lanes': 1}
    assert view.to_json() == snapshot and file_snapshot(root) == before


def test_reviewed_diagram_requires_current_local_approval_and_original_captures(tmp_path):
    from kgmaker.process_render import ProcessMermaidError

    source = json.loads(FIXTURE.read_bytes())
    source['semantic_annotations'] = [{'id': 'unverified', 'target_id': 'card', 'label': 'Unverified label',
        'source_refs': ['card'], 'semantic_review_status': 'APPROVED'}]
    view = ProcessView.from_dict(source)
    snapshot = view.to_json()
    documents = [captured_document(text='Original captured note.')]
    labels = [('card', 'Approved local label')]
    with pytest.raises(ProcessMermaidError, match='^PROCESS_MERMAID_REVIEW_EMPTY$'):
        render_reviewed(tmp_path, view, documents=documents)
    assert not list(tmp_path.iterdir())
    rejected = record_review(tmp_path, view, labels, documents=documents, action='REJECT')
    before = file_snapshot(tmp_path)
    with pytest.raises(ProcessMermaidError, match='^PROCESS_MERMAID_REVIEW_REJECTED$'):
        render_reviewed(tmp_path, view, documents=documents)
    assert file_snapshot(tmp_path) == before
    approved = record_review(tmp_path, view, labels, documents=documents, head=rejected)
    (tmp_path / 'kept.mmd').write_text(render(view), encoding='utf-8')
    before = file_snapshot(tmp_path)
    changed = deepcopy(source)
    changed['technical_view']['nodes'][0]['label'] = 'Changed current technical label'
    new_view = ProcessView.from_dict(changed)
    conflict = {'document_ref': 'doc:guide', 'target_id': 'card', 'status': 'CONFLICT', 'source_refs': ['origin:card']}
    for current, captures in [
        (view, {}),
        (view, {'documents': [captured_document(text='Changed captured note.')]}),
        (view, {'documents': documents, 'conflicts': [conflict]}),
        (new_view, {'documents': documents}),
    ]:
        with pytest.raises(ProcessMermaidError, match='^PROCESS_MERMAID_REVIEW_NEEDS_REVALIDATION$'):
            render_reviewed(tmp_path, current, **captures)
    assert 'Unverified label' not in render_reviewed(tmp_path, view, documents=documents)
    assert file_snapshot(tmp_path) == before

    record_review(tmp_path, new_view, labels, documents=documents, head=approved)
    before = file_snapshot(tmp_path)
    with pytest.raises(ProcessMermaidError, match='^PROCESS_MERMAID_REVIEW_NEEDS_REVALIDATION$'):
        render_reviewed(tmp_path, view, documents=documents)
    assert 'Approved local label' in render_reviewed(tmp_path, new_view, documents=documents)
    assert view.to_json() == snapshot and file_snapshot(tmp_path) == before


@pytest.mark.parametrize(('failure', 'code'), [('unsafe', 'UNSAFE_PROCESS_MERMAID'),
                                               ('text', 'PROCESS_MERMAID_LIMIT')])
def test_approved_label_obeys_diagram_safety_and_host_budget(tmp_path, failure, code):
    from kgmaker.process_render import ProcessMermaidError

    source = json.loads(FIXTURE.read_bytes())
    if failure == 'text':
        for node in source['technical_view']['nodes'][:4]:
            node['label'] = '\U0001f535' * 5950
    view = ProcessView.from_dict(source)
    snapshot = view.to_json()
    original = render(view)
    (tmp_path / 'kept.mmd').write_text(original, encoding='utf-8')
    label = 'repo:unqualified' if failure == 'unsafe' else '\U0001f535' * 200
    record_review(tmp_path, view, [('card', label)])
    before = file_snapshot(tmp_path)
    with pytest.raises(ProcessMermaidError, match=f'^{code}$'):
        render_reviewed(tmp_path, view)
    assert render(view) == original and view.to_json() == snapshot
    assert file_snapshot(tmp_path) == before

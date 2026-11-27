"""Technical report evidence from one supplied ProcessView."""
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
import json
from unittest.mock import patch

import pytest

from kgmaker.process_model import ProcessView
from kgmaker.workspace import qualified
from test_t035_render_business_process_mermaid import FIXTURE, file_snapshot, parse_and_render, records, render


def report(view):
    from kgmaker.process_render import render_process_markdown
    return render_process_markdown(view)


def inspect_report(markdown):
    from test_t020_render_interface_markdown import parsed

    assert version('markdown-it-py') == '3.0.0'
    tokens = parsed(markdown)
    tables = {}
    for token in tokens:
        if token.type == 'table_open':
            table_rows = []
        elif token.type == 'tr_open':
            row = []
        elif token.type == 'inline' and token.level == 4:
            assert all(child.type == 'text' for child in token.children or [])
            row.append(''.join(child.content for child in token.children or []))
        elif token.type == 'tr_close':
            table_rows.append(row)
        elif token.type == 'table_close':
            headers, *values = table_rows
            assert len(set(headers)) == len(headers)
            tables[headers[0]] = [dict(zip(headers, row, strict=True)) for row in values]
    diagrams = [token.content for token in tokens if token.type == 'fence' and token.info == 'mermaid']
    diagram, = diagrams
    assert sum(token.type == 'fence' for token in tokens) == 1
    forbidden = {'link_open', 'image', 'html_block', 'html_inline'}
    assert not any(item.type in forbidden for token in tokens for item in (token, *(token.children or ())))
    return tables, diagram


def assert_no_io(view):
    with patch('pathlib.Path.open', side_effect=AssertionError('report read or wrote a file')), \
            patch('subprocess.Popen', side_effect=AssertionError('report started a process')), \
            patch('socket.socket', side_effect=AssertionError('report opened a socket')), \
            patch('kgmaker.process_render.read_process_reviews', side_effect=AssertionError('report used the store')):
        return report(view)


def test_checkout_report_uses_one_snapshot_and_fixed_mermaid(tmp_path):
    source = FIXTURE.read_bytes()
    view = ProcessView.from_dict(json.loads(source))
    before = view.to_json()
    original_to_dict = ProcessView.to_dict
    conversions = []

    def checked_to_dict(self, *, include_generation_metadata=True):
        conversions.append(include_generation_metadata)
        return original_to_dict(self, include_generation_metadata=include_generation_metadata)

    with patch.object(ProcessView, 'to_dict', checked_to_dict):
        markdown = assert_no_io(view)
    assert conversions == [False]
    candidate = json.loads(source)
    for items in ('nodes', 'edges', 'provenance'):
        candidate['technical_view'][items].reverse()
    candidate['technical_view']['generation_metadata'] = {'generated_at': '2070-01-01'}
    assert report(ProcessView.from_dict(candidate)) == markdown

    tables, diagram = inspect_report(markdown)
    assert {row['Snapshot']: row['Captured value'] for row in tables['Snapshot']} == {
        'Process ID': '"process:checkout"', 'Revision': '3',
        'Content fingerprint': 'fcb448c2df7341791973b0e260d92f4907303dfde1ba06cc1af3ee8a88523387',
        'Baseline fingerprint': '"snapshot:checkout-v3"', 'Scope': '"production"',
        'Selected context IDs': '["ctx-prod"]', 'Context selection': '{"orders":["ctx-prod"]}',
        'Technical coverage': 'COMPLETE_WITHIN_SELECTED_SCOPE', 'Purpose': 'UNKNOWN',
        'Source observation': 'NOT_CHECKED', 'Runtime execution': 'NOT_CHECKED', 'Data availability': 'UNKNOWN',
    }
    assert {row['Role']: row['IDs'] for row in tables['Role']} == {
        'Triggers': '["request"]', 'Entries': '["request"]', 'Exits': '["done"]', 'Outcomes': '["done"]',
    }
    assert sha256(diagram.encode()).hexdigest() == '55881e998d92ad88d42a03e3f28f259256827b9429ed1ce1c8be4f3833de57fa'
    assert diagram == render(view)
    meta, = records(diagram, 'meta')
    assert meta['process_id'] == 'process:checkout' and meta['revision'] == 3 and meta['context_ids'] == ['ctx-prod']
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 8, 'lanes': 0}
    assert view.to_json() == before and FIXTURE.read_bytes() == source


def partial_view():
    source = json.loads(FIXTURE.read_bytes())
    source['technical_status'] = 'PARTIAL'
    technical = source['technical_view']
    technical['coverage'] = {'status': 'PARTIAL', 'truncated': True, 'omitted_edges': 1}
    technical['diagnostics'] = [{'code': 'MANUAL_HANDOFF', 'message': 'Selected source cannot prove handoff.'}]
    send = next(row for row in technical['nodes'] if row['id'] == 'send')
    dispatch = next(row for row in technical['edges'] if row['id'] == 'dispatch')
    for row, reason in ((send, 'Manual completion has no supplied evidence'),
                        (dispatch, 'The manual handoff is outside supplied process evidence')):
        row.update(evidence_refs=[], evidence_kinds=[], supporting_refs=[], resolution_status='UNRESOLVED',
                   freshness='UNKNOWN')
        row['attributes']['boundary_reason'] = reason
    send.update(kind='unresolved_boundary', label='External manual review')
    dispatch['relation'] = 'unknown'
    technical['provenance'] = [row for row in technical['provenance'] if row['id'] not in {'ev:send', 'ev:dispatch'}]
    payment = deepcopy(next(row for row in technical['edges'] if row['id'] == 'pay-card'))
    payment.update(id='pay-card-alternative', original_ids=['origin:pay-card-alternative'])
    technical['edges'].append(payment)
    card = next(row for row in technical['provenance'] if row['id'] == 'ev:card')
    card.update(source_id=qualified('orders', 'origin:card'), source_file='@orders/src/Checkout.java',
                source_range={'start_line': 12, 'end_line': 14}, freshness='STALE')
    technical_card = next(row for row in technical['nodes'] if row['id'] == 'card')
    technical_card['freshness'] = 'STALE'
    source['semantic_annotations'] = [{'id': 'unverified-label', 'target_id': 'card', 'label': 'Review flag only',
        'source_refs': ['card'], 'semantic_review_status': 'APPROVED'}]
    return ProcessView.from_dict(source)


def test_partial_report_preserves_every_occurrence_and_manual_handoff(tmp_path):
    view = partial_view()
    before = view.to_json()
    artifact = tmp_path / 'kept.md'
    artifact.write_bytes(b'last valid\n')
    saved = file_snapshot(tmp_path)
    markdown = assert_no_io(view)
    tables, diagram = inspect_report(markdown)
    steps = {json.loads(row['Step ID']): row for row in tables['Step ID']}
    transitions = {json.loads(row['Transition ID']): row for row in tables['Transition ID']}
    assert set(steps) == {'card', 'cash', 'choose', 'done', 'request', 'retry', 'send'}
    assert [(*map(json.loads, (row['Transition ID'], row['Source'], row['Target'])), row['Relation'])
            for row in tables['Transition ID']] == [
        ('card-retry', 'card', 'retry', 'exception'), ('card-send', 'card', 'send', 'normal'),
        ('cash-send', 'cash', 'send', 'normal'), ('dispatch', 'send', 'done', 'unknown'),
        ('pay-card', 'choose', 'card', 'true'), ('pay-card-alternative', 'choose', 'card', 'true'),
        ('pay-cash', 'choose', 'cash', 'false'), ('start', 'request', 'choose', 'normal'),
        ('try-again', 'retry', 'choose', 'retry'),
    ]
    assert steps['send']['Technical label'] == 'External manual review'
    assert steps['send']['Kind'] == 'unresolved_boundary'
    for row, reason, origin in ((steps['send'], 'Manual completion has no supplied evidence', 'origin:send'),
                                (transitions['dispatch'], 'The manual handoff is outside supplied process evidence',
                                 'origin:dispatch')):
        assert row['Boundary reason'] == reason
        assert (row['Resolution'], row['Freshness'], row['Evidence refs']) == ('UNRESOLVED', 'UNKNOWN', '[]')
        assert row['Original IDs'] == json.dumps([origin]) and row['Contexts'] == '["ctx-prod"]'
    assert transitions['pay-card']['Condition'] == 'payment == CARD'
    assert transitions['pay-card-alternative']['Original IDs'] == '["origin:pay-card-alternative"]'
    assert {row['Coverage field']: row['Value'] for row in tables['Coverage field']} == {
        'omitted_edges': '1', 'status': 'PARTIAL', 'truncated': 'true',
    }
    assert json.loads(tables['Diagnostic'][0]['Diagnostic'])['code'] == 'MANUAL_HANDOFF'
    assert tables['Captured limitation'] == [{'Captured limitation': 'Static structure; scheduling unknown.'}]
    proof = {json.loads(row['Evidence ID']): row for row in tables['Evidence ID']}
    assert proof['ev:card']['Kind'] == 'SYMBOL_RESOLVED' and proof['ev:card']['Polarity'] == 'SUPPORTING'
    assert proof['ev:card']['Freshness'] == 'STALE' and steps['card']['Freshness'] == 'STALE'
    assert proof['ev:card']['Contexts'] == '["ctx-prod"]' and steps['card']['Evidence refs'] == '["ev:card"]'
    assert json.loads(proof['ev:card']['Captured locator']) == {'path': '@orders/src/Checkout.java',
        'range': {'start_line': 12, 'end_line': 14}, 'content_hash': 'a' * 64}
    assert proof['ev:cash']['Captured locator'] == 'SOURCE_LOCATOR_UNAVAILABLE'
    assert 'ev:send' not in proof and 'ev:dispatch' not in proof and 'Review flag only' not in markdown
    assert diagram == render(view) and 'TRUNCATED' in diagram.splitlines()[1]
    assert file_snapshot(tmp_path) == saved and view.to_json() == before
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 9, 'lanes': 0}


def test_report_escapes_cells_and_delimits_the_exact_mermaid(tmp_path):
    data = json.loads(FIXTURE.read_bytes())
    item = next(row for row in data['technical_view']['nodes'] if row['id'] == 'card')
    item['label'] = 'Literal | ```markdown [ref](https://example.invalid) <script>sample</script>'
    view = ProcessView.from_dict(data)
    tables, diagram = inspect_report(assert_no_io(view))
    card = next(row for row in tables['Step ID'] if json.loads(row['Step ID']) == 'card')
    assert card['Technical label'] == item['label']
    assert diagram == render(view)
    assert parse_and_render(diagram, tmp_path) == {'vertices': 7, 'edges': 8, 'lanes': 0}


def test_report_keeps_whitespace_and_literal_escape_occurrence_ids_distinct():
    data = json.loads(FIXTURE.read_bytes())
    technical = data['technical_view']
    step = next(row for row in technical['nodes'] if row['id'] == 'cash')
    transition = next(row for row in technical['edges'] if row['id'] == 'pay-cash')
    pairs = [(' cash ', ' pay-cash '), (r'\u0020cash\u0020', r'\u0020pay-cash\u0020'),
             ('cash\nmanual', 'pay-cash\tmanual'), ('cash ⏎ manual', 'pay-cash ⇥ manual'),
             ('\u00a0cash\u00a0', '\u2028pay-cash\u2028')]
    for index, (step_id, transition_id) in enumerate(pairs):
        technical['nodes'].append({**step, 'id': step_id, 'original_ids': [f'origin:step-{index}']})
        technical['edges'].append({**transition, 'id': transition_id, 'target': step_id,
                                   'original_ids': [f'origin:transition-{index}']})
    view = ProcessView.from_dict(data)
    tables, diagram = inspect_report(assert_no_io(view))
    step_cells = [row['Step ID'] for row in tables['Step ID']]
    transition_cells = [(row['Transition ID'], row['Source'], row['Target']) for row in tables['Transition ID']]
    assert len(step_cells) == len(set(step_cells))
    assert len(transition_cells) == len({row[0] for row in transition_cells})
    assert {json.loads(value) for value in step_cells} == {row['id'] for row in technical['nodes']}
    assert {tuple(map(json.loads, cells)) for cells in transition_cells} == {
        (row['id'], row['source'], row['target']) for row in technical['edges']}
    assert r'"\u0020cash\u0020"' in step_cells and r'"\\u0020cash\\u0020"' in step_cells
    assert all(not any(char.isspace() for char in value) for value in step_cells)
    assert diagram == render(view)
    assert {row['node']['id'] for row in records(diagram, 'node')} == {row['id'] for row in technical['nodes']}


def test_report_exposes_captured_occurrence_truncation_independently_of_coverage():
    data = json.loads(FIXTURE.read_bytes())
    data['technical_status'] = 'PARTIAL'
    technical = data['technical_view']
    technical['coverage'] = {'status': 'PARTIAL', 'truncated': False}
    for collection, identity in (('nodes', 'card'), ('edges', 'pay-card')):
        next(row for row in technical[collection] if row['id'] == identity)['attributes']['truncated'] = True
    next(row for row in technical['nodes'] if row['id'] == 'cash')['attributes']['truncated'] = 'true'
    view = ProcessView.from_dict(data)
    tables, diagram = inspect_report(assert_no_io(view))

    assert {row['Coverage field']: row['Value'] for row in tables['Coverage field']} == {
        'status': 'PARTIAL', 'truncated': 'false',
    }
    rows = [row for table in ('Step ID', 'Transition ID') for row in tables[table]]
    assert 'Truncated' in rows[0]
    assert {json.loads(row.get('Step ID') or row['Transition ID'])
            for row in rows if row['Truncated'] == 'true'} == {'card', 'pay-card'}
    assert next(row for row in tables['Step ID'] if json.loads(row['Step ID']) == 'cash')['Truncated'] == 'UNKNOWN'
    assert diagram == render(view)


@pytest.mark.parametrize(('failure', 'code'), [
    ('type', 'INVALID_PROCESS_MARKDOWN'), ('scope', 'INVALID_PROCESS_MARKDOWN'),
    ('dangling', 'INVALID_PROCESS_MARKDOWN'), ('proof-context', 'INVALID_PROCESS_MARKDOWN'),
    ('unsafe', 'UNSAFE_PROCESS_MARKDOWN'), ('mermaid-limit', 'PROCESS_MARKDOWN_LIMIT'),
    ('report-limit', 'PROCESS_MARKDOWN_LIMIT'),
])
def test_invalid_or_over_budget_report_preserves_last_valid_artifact(tmp_path, monkeypatch, failure, code):
    from kgmaker.process_render import ProcessMarkdownError

    view = ProcessView.from_dict(json.loads(FIXTURE.read_bytes()))
    technical = view._document['technical_view']
    first = technical['nodes'][0]
    if failure == 'scope':
        first['attributes']['scope'] = 'test'
    elif failure == 'dangling':
        first['evidence_refs'] = first['supporting_refs'] = ['ev:missing']
    elif failure == 'proof-context':
        technical['provenance'][0]['context_ids'] = ['other-context']
    elif failure == 'unsafe':
        first['label'] = 'Bearer synthetic-private-value'
    elif failure == 'mermaid-limit':
        edge = technical['edges'][0]
        for index in range(501 - len(technical['edges'])):
            identity = f'parallel-{index}'
            technical['edges'].append({**edge, 'id': identity, 'original_ids': [identity]})
        ProcessView.from_dict(view._document)
    elif failure == 'report-limit':
        diagram_bytes = len(render(view).encode())
        monkeypatch.setattr('kgmaker.process_render._MAX_OUTPUT_BYTES', diagram_bytes + 10)
        assert len(render(view).encode()) == diagram_bytes
    artifact = tmp_path / 'kept.md'
    artifact.write_bytes(b'last valid report\n')
    saved = file_snapshot(tmp_path)
    supplied = deepcopy(view._document)

    with pytest.raises(ProcessMarkdownError, match=f'^{code}$'):
        assert_no_io(view._document if failure == 'type' else view)

    assert view._document == supplied and file_snapshot(tmp_path) == saved

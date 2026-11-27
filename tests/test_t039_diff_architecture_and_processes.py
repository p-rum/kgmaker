"""Compare explicit ProcessView snapshots and their recorded evidence offline."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.architecture_model import ViewValidationError
from kgmaker.process_model import ProcessDefinition, ProcessView
from test_t036_render_business_process_report import partial_view


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/process-model/checkout.json'


def checkout():
    return json.loads(FIXTURE.read_bytes())


def snapshot(data):
    data['definition_fingerprint'] = ProcessDefinition.from_dict(data['definition']).content_fingerprint
    return ProcessView.from_dict(data)


def compare(before, after):
    from kgmaker.view_diff import diff_process_views

    with patch('builtins.open', side_effect=AssertionError('diff opened a file')), \
            patch('pathlib.Path.open', side_effect=AssertionError('diff opened a path')), \
            patch('subprocess.Popen', side_effect=AssertionError('diff started a process')), \
            patch('socket.socket', side_effect=AssertionError('diff opened a socket')):
        return diff_process_views(before, after)


def find(rows, identity):
    return next(row for row in rows if row['id'] == identity)


def test_reorder_and_generation_metadata_have_no_deltas():
    raw = FIXTURE.read_bytes()
    before = partial_view()
    data = before.to_dict()
    for key in ('nodes', 'edges', 'provenance'):
        data['technical_view'][key].reverse()
    data['technical_view']['generation_metadata'] = {'generated_at': '2070-01-01'}
    after = snapshot(data)

    result = compare(before, after)

    assert result['status'] == 'COMPARABLE' and result['changes'] == {}
    assert result['before'] == result['after']
    assert result['before']['coverage']['truncated'] is True
    assert result['before']['unresolved_edge_ids'] == ['dispatch']
    assert sha256(FIXTURE.read_bytes()).hexdigest() == sha256(raw).hexdigest()


def test_label_and_supplied_review_are_independent_of_parallel_edge_removal():
    baseline = checkout()
    technical = baseline['technical_view']
    edge = deepcopy(find(technical['edges'], 'pay-card'))
    edge.update(id='pay-card-alternative', original_ids=['origin:pay-card-alternative'])
    technical['edges'].append(edge)
    before = snapshot(baseline)

    renamed = before.to_dict()
    find(renamed['technical_view']['nodes'], 'card')['label'] = 'Review the card'
    renamed['semantic_annotations'] = [{'id': 'review-flag', 'target_id': 'card', 'label': 'Collect card',
        'source_refs': ['card'], 'semantic_review_status': 'APPROVED'}]
    result = compare(before, snapshot(renamed))
    assert set(result['changes']) == {'nodes', 'supplied_annotations'}
    card, = result['changes']['nodes']['changed']
    assert card['id'] == 'card' and card['fields'] == {'presentation': ['label']}
    annotation, = result['changes']['supplied_annotations']['added']
    assert annotation['id'] == 'review-flag' and annotation['semantic_review_status'] == 'APPROVED'
    assert 'effective_review_status' not in result

    removed = before.to_dict()
    removed['technical_view']['edges'] = [row for row in removed['technical_view']['edges']
                                          if row['id'] != 'pay-card-alternative']
    result = compare(before, snapshot(removed))
    assert set(result['changes']) == {'edges'}
    occurrence, = result['changes']['edges']['removed']
    assert occurrence['id'] == 'pay-card-alternative'
    assert (occurrence['source'], occurrence['target']) == (edge['source'], edge['target'])
    assert occurrence['original_ids'] == ['origin:pay-card-alternative']
    assert occurrence['evidence_refs'] == edge['evidence_refs']


def test_same_edge_id_technical_relation_change_keeps_directed_identity():
    before = snapshot(checkout())
    candidate = before.to_dict()
    find(candidate['technical_view']['edges'], 'start')['relation'] = 'call'

    result = compare(before, snapshot(candidate))

    assert set(result['changes']) == {'edges'}
    changed, = result['changes']['edges']['changed']
    assert changed['id'] == 'start' and changed['fields'] == {'topology': ['relation']}
    assert [changed[side]['source'] for side in ('before', 'after')] == ['request', 'request']
    assert [changed[side]['target'] for side in ('before', 'after')] == ['choose', 'choose']
    assert [changed[side]['relation'] for side in ('before', 'after')] == ['normal', 'call']


def test_unresolved_and_stale_are_separate_and_retain_proof_and_limits():
    before = snapshot(checkout())
    result = compare(before, partial_view())
    dispatch = find(result['changes']['edges']['changed'], 'dispatch')
    assert dispatch['fields']['resolution'] == ['attributes.boundary_reason', 'resolution_status']
    assert dispatch['fields']['freshness'] == ['freshness']
    assert dispatch['before']['resolution_status'] == 'RESOLVED'
    assert dispatch['after']['resolution_status'] == 'UNRESOLVED'
    assert dispatch['before']['evidence_refs'] == ['ev:dispatch']
    assert dispatch['after']['evidence_refs'] == []
    assert result['after']['coverage']['omitted_edges'] == 1
    assert result['after']['diagnostics'][0]['code'] == 'MANUAL_HANDOFF'

    candidate = before.to_dict()
    technical = candidate['technical_view']
    find(technical['edges'], 'dispatch')['freshness'] = 'STALE'
    find(technical['provenance'], 'ev:dispatch')['freshness'] = 'STALE'
    technical['coverage']['status'] = candidate['technical_status'] = 'PARTIAL'
    result = compare(before, snapshot(candidate))
    dispatch, = result['changes']['edges']['changed']
    assert dispatch['fields'] == {'freshness': ['freshness']}
    assert dispatch['after']['resolution_status'] == 'RESOLVED'
    proof, = result['changes']['provenance']['changed']
    assert proof['id'] == 'ev:dispatch' and proof['fields'] == {'freshness': ['freshness']}
    assert proof['before']['freshness'] == 'CURRENT' and proof['after']['freshness'] == 'STALE'
    assert proof['after']['evidence_kind'] == 'SYMBOL_RESOLVED'
    assert proof['after']['source_id'] == 'origin:dispatch'


def test_partial_projection_absence_does_not_claim_removed_edges():
    before = partial_view()
    data = before.to_dict()
    data['technical_view']['edges'] = [row for row in data['technical_view']['edges']
                                       if row['id'] != 'pay-card-alternative']

    result = compare(before, snapshot(data))

    assert set(result['changes']['edges']) == {'not_observed_after'}
    missing, = result['changes']['edges']['not_observed_after']
    assert missing['id'] == 'pay-card-alternative'
    assert result['before']['coverage']['status'] == 'PARTIAL'


@pytest.mark.parametrize('complete', [False, True], ids=['partial', 'complete'])
def test_projection_gap_is_symmetric_and_complete_addition_remains_genuine(complete):
    data = checkout()
    full = snapshot(deepcopy(data))
    technical = data['technical_view']
    technical['edges'] = [row for row in technical['edges'] if row['id'] != 'pay-card']
    if not complete:
        technical['coverage'].update(status='PARTIAL', truncated=True)
        data['technical_status'] = 'PARTIAL'
    missing = snapshot(data)
    original = (missing.to_json(), full.to_json())

    forward, reverse = compare(missing, full), compare(full, missing)

    assert forward['status'] == reverse['status'] == 'COMPARABLE'
    incoming = 'added' if complete else 'not_observed_before'
    outgoing = 'removed' if complete else 'not_observed_after'
    for result, category in ((forward, incoming), (reverse, outgoing)):
        changes = result['changes']['edges']
        assert set(changes) == {category}
        assert [row['id'] for row in changes[category]] == ['pay-card']
    assert (missing.to_json(), full.to_json()) == original


@pytest.mark.parametrize(('collection', 'identity', 'summary'), [
    ('nodes', 'card', 'truncated_node_ids'),
    ('edges', 'start', 'truncated_edge_ids'),
])
def test_local_truncation_qualifies_absence_and_preserves_coverage(collection, identity, summary):
    data = checkout()
    full = snapshot(deepcopy(data))
    technical = data['technical_view']
    find(technical[collection], identity)['attributes']['truncated'] = True
    technical['edges'] = [row for row in technical['edges'] if row['id'] != 'pay-card']
    limited = snapshot(data)
    original = (limited.to_json(), full.to_json())

    forward, reverse = compare(limited, full), compare(full, limited)

    assert forward['status'] == reverse['status'] == 'COMPARABLE'
    assert set(forward['changes']) == set(reverse['changes']) == {'edges', 'coverage'}
    for result, category, truncated in (
        (forward, 'not_observed_before', 'before'), (reverse, 'not_observed_after', 'after'),
    ):
        edge_changes = result['changes']['edges']
        assert set(edge_changes) == {category}
        assert [row['id'] for row in edge_changes[category]] == ['pay-card']
        assert result[truncated][summary] == [identity]
        assert result['changes']['coverage'][truncated][summary] == [identity]
        assert result['before']['coverage'] == result['after']['coverage'] == {
            'status': 'COMPLETE_WITHIN_SELECTED_SCOPE',
        }
    unchanged = compare(limited, limited)
    assert unchanged['changes'] == {}
    assert unchanged['before'][summary] == unchanged['after'][summary] == [identity]
    assert (limited.to_json(), full.to_json()) == original


def test_changed_projection_limits_make_new_absence_uncertain():
    before = snapshot(checkout())
    data = before.to_dict()
    technical = data['technical_view']
    technical['edges'] = [row for row in technical['edges'] if row['id'] != 'pay-card']
    technical['limits'] = ['A different projection filter reports payment alternatives only.']

    result = compare(before, snapshot(data))

    assert result['before']['coverage'] == result['after']['coverage']
    assert set(result['changes']['edges']) == {'not_observed_after'}
    missing, = result['changes']['edges']['not_observed_after']
    assert missing['id'] == 'pay-card'
    assert result['changes']['coverage']['after']['limits'] == technical['limits']


def retag(value, replacements):
    if isinstance(value, dict):
        return {key: retag(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [retag(item, replacements) for item in value]
    return replacements.get(value, value)


@pytest.mark.parametrize(('replacements', 'reason'), [
    ({'production': 'test', 'ctx-prod': 'ctx-test'}, 'SCOPE_MISMATCH'),
    ({'process:checkout': 'process:replacement'}, 'PROCESS_MISMATCH'),
    ({'test-contract-1': 'test-contract-2'}, 'RULES_MISMATCH'),
])
def test_incompatible_pair_never_invents_changed_records(replacements, reason):
    before = snapshot(checkout())
    after = snapshot(retag(checkout(), replacements))

    result = compare(before, after)

    assert result['status'] == 'INCOMPARABLE' and result['changes'] == {}
    assert reason in result['reasons']
    assert result['before']['content_fingerprint'] == before.content_fingerprint
    assert result['after']['content_fingerprint'] == after.content_fingerprint


def structured_capture(data):
    # T025's captured local shape contains an unbound source-only row and one
    # current build context with distinct context and variant identifiers.
    active = {'repo_id': 'orders', 'module': 'app', 'context_id': 'ctx-prod', 'scope': 'production',
              'context_selection_key': 'stable-app-variant', 'context_fingerprint': 'initial-raw-capture',
              'candidate_context_ids': ['ctx-prod'], 'status': 'CURRENT'}
    unbound = {'repo_id': 'orders', 'module': None, 'context_id': None, 'scope': 'production',
               'candidate_context_ids': ['source-only'], 'status': 'PARTIAL'}
    selection = {'services': {'orders': {'scope': 'production', 'status': 'PARTIAL',
                                         'contexts': [active, unbound]}}}
    data['definition']['context_selection'] = selection
    data['technical_view']['context_selection'] = selection
    return data


def test_t025_selection_row_order_is_irrelevant_and_recapture_requires_exact_proof():
    original = structured_capture(checkout())
    before = snapshot(original)
    reordered = deepcopy(before.to_dict())
    for document in (reordered['definition'], reordered['technical_view']):
        document['context_selection']['services']['orders']['contexts'].reverse()
    result = compare(before, snapshot(reordered))
    assert result['status'] == 'COMPARABLE' and result['changes'] == {}

    recaptured = retag(original, {'ctx-prod': 'ctx-recapped', 'initial-raw-capture': 'second-raw-capture'})
    result = compare(before, snapshot(recaptured))
    assert result['status'] == 'INCOMPARABLE' and result['changes'] == {}
    assert 'CONTEXT_MISMATCH' in result['reasons']
    assert result['before']['context_ids'] == ['ctx-prod'] and result['after']['context_ids'] == ['ctx-recapped']


def test_selected_context_diagnostic_order_and_duplicate_evidence():
    original = structured_capture(checkout())
    active_rows = original['definition']['context_selection']['services']['orders']['contexts']
    active_rows[0]['diagnostics'] = [
        {'code': 'MISSING_TYPE', 'reason': 'First type'},
        {'code': 'MISSING_TYPE', 'reason': 'First type'},
        {'code': 'UNSUPPORTED_LOOKUP', 'reason': 'Other type'},
    ]
    before = snapshot(original)
    reordered = deepcopy(before.to_dict())
    for document in (reordered['definition'], reordered['technical_view']):
        document['context_selection']['services']['orders']['contexts'][0]['diagnostics'].reverse()
    after = snapshot(reordered)
    original = (before.to_json(), after.to_json())

    result = compare(before, after)

    assert result['status'] == 'COMPARABLE' and result['changes'] == {}
    preserved = [result[side]['context_selection']['services']['orders']['contexts'][0]['diagnostics']
                 for side in ('before', 'after')]
    assert preserved == [active_rows[0]['diagnostics'], list(reversed(active_rows[0]['diagnostics']))]
    assert (before.to_json(), after.to_json()) == original

    for document in (reordered['definition'], reordered['technical_view']):
        document['context_selection']['services']['orders']['contexts'][0]['diagnostics'].pop()
    changed = compare(before, snapshot(reordered))
    assert changed['status'] == 'INCOMPARABLE' and changed['changes'] == {}
    assert changed['reasons'] == ['CONTEXT_SELECTION_MISMATCH']


def test_capture_fingerprint_and_result_binding_stay_detached():
    before = snapshot(structured_capture(checkout()))
    changed = retag(deepcopy(before.to_dict()), {'initial-raw-capture': 'second-raw-capture'})
    after = snapshot(changed)
    before_input, after_input = before.to_json(), after.to_json()

    result = compare(before, after)

    assert result['status'] == 'INCOMPARABLE' and result['changes'] == {}
    assert result['reasons'] == ['CONTEXT_SELECTION_MISMATCH']
    result['before']['context_selection']['services']['orders']['contexts'][0]['context_id'] = 'foreign'
    result['after']['context_selection']['services']['orders']['contexts'].clear()
    assert (before.to_json(), after.to_json()) == (before_input, after_input)


def test_opaque_selection_cannot_prove_comparability_even_when_equal():
    data = checkout()
    for document in (data['definition'], data['technical_view']):
        document['context_selection'] = {'opaque': {'fingerprint': 'same-text'}}
    supplied = snapshot(data)

    result = compare(supplied, supplied)

    assert result['status'] == 'INCOMPARABLE' and result['changes'] == {}
    assert result['reasons'] == ['UNPROVEN_CONTEXT_SELECTION']


def test_baseline_and_revision_are_binding_metadata():
    before = snapshot(checkout())
    candidate = before.to_dict()
    candidate['revision'] = candidate['definition']['revision'] = 4
    for document in (candidate['definition'], candidate['technical_view']):
        document['baseline_fingerprint'] = 'snapshot:checkout-v4'

    result = compare(before, snapshot(candidate))

    assert result['status'] == 'COMPARABLE' and result['changes'] == {}
    assert result['before']['baseline_fingerprint'] == 'snapshot:checkout-v3'
    assert result['after']['baseline_fingerprint'] == 'snapshot:checkout-v4'
    assert (result['before']['revision'], result['after']['revision']) == (3, 4)


def test_invalid_and_over_limit_inputs_cannot_mutate_any_supplied_data(tmp_path):
    valid = snapshot(checkout())
    large = valid.to_dict()
    find(large['technical_view']['nodes'], 'card')['label'] = 'x' * 16_385
    over_limit = snapshot(large)
    published = tmp_path / 'manifest.json'
    published.write_bytes(b'previous valid generation\n')
    before = (valid.to_json(), over_limit.to_json(), published.read_bytes(), published.stat().st_mtime_ns)
    invalid = {'technical_view': {}}

    with pytest.raises(ViewValidationError) as invalid_error:
        compare(valid, invalid)
    assert invalid_error.value.errors == ({'code': 'INVALID_PROCESS_VIEW', 'path': 'after'},)
    with pytest.raises(ViewValidationError) as limit_error:
        compare(valid, over_limit)
    assert limit_error.value.errors == ({'code': 'PROCESS_DIFF_LIMIT', 'path': 'after'},)
    after = (valid.to_json(), over_limit.to_json(), published.read_bytes(), published.stat().st_mtime_ns)
    assert before == after and invalid == {'technical_view': {}}

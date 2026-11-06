"""Explicit process documents: branch/loop topology is independent of list order."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.architecture_model import ViewValidationError
from kgmaker.process_model import ProcessDefinition, ProcessView


def definition():
    return {'schema_version': 1, 'process_id': 'process:checkout', 'revision': 3,
        'baseline_fingerprint': 'snapshot:checkout-v3', 'scope': 'production',
        'context_selection': {'orders': ['ctx-prod']}, 'context_ids': ['ctx-prod'],
        'trigger_ids': ['request'], 'semantic_review_status': 'PROPOSED'}


def sample_process():
    selected = definition()
    def proof(identity):
        return {'id': 'ev:' + identity, 'evidence_kind': 'SYMBOL_RESOLVED',
            'freshness': 'CURRENT', 'polarity': 'SUPPORTING', 'scope': 'production',
            'context_ids': ['ctx-prod'], 'source_id': 'origin:' + identity,
            'content_hash': 'a' * 64}
    def common(identity):
        return {'id': identity, 'original_ids': ['origin:' + identity],
            'evidence_refs': ['ev:' + identity], 'evidence_kinds': ['SYMBOL_RESOLVED'],
            'resolution_status': 'RESOLVED', 'freshness': 'CURRENT',
            'supporting_refs': ['ev:' + identity], 'contradicting_refs': [], 'unknown_refs': [],
            'attributes': {'scope': 'production', 'context_ids': ['ctx-prod']}}
    kinds = [('request', 'trigger'), ('choose', 'decision'), ('card', 'action'),
             ('cash', 'action'), ('retry', 'action'), ('send', 'async_boundary'), ('done', 'outcome')]
    nodes = [{**common(identity), 'kind': kind, 'label': identity, 'owner_id': None} for identity, kind in kinds]
    edges = []
    for identity, source, target, relation, condition in [
        ('start', 'request', 'choose', 'normal', None),
        ('pay-card', 'choose', 'card', 'true', 'payment == CARD'),
        ('pay-cash', 'choose', 'cash', 'false', 'payment != CARD'),
        ('card-retry', 'card', 'retry', 'exception', 'payment failed'),
        ('try-again', 'retry', 'choose', 'retry', 'retry budget remains'),
        ('card-send', 'card', 'send', 'normal', None),
        ('cash-send', 'cash', 'send', 'normal', None),
        ('dispatch', 'send', 'done', 'async', None),
    ]:
        edge = {**common(identity), 'source': source, 'target': target, 'relation': relation}
        if condition is not None: edge['attributes']['condition'] = condition
        edges.append(edge)
    view = {'schema_version': 1, 'view_id': selected['process_id'], 'kind': 'process',
        'baseline_fingerprint': selected['baseline_fingerprint'], 'rules_version': 'test-contract-1',
        'scope': selected['scope'], 'context_selection': deepcopy(selected['context_selection']),
        'nodes': nodes, 'edges': edges, 'diagnostics': [],
        'coverage': {'status': 'COMPLETE_WITHIN_SELECTED_SCOPE'}, 'limits': ['Static structure; scheduling unknown.'],
        'provenance': [proof(item['id']) for item in nodes + edges]}
    return {'schema_version': 1, 'process_id': selected['process_id'], 'revision': selected['revision'],
        'definition': selected, 'definition_fingerprint': hashlib.sha256(json.dumps(selected,
            sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
        'technical_status': view['coverage']['status'], 'technical_view': view,
        'entry_ids': ['request'], 'exit_ids': ['done'], 'outcome_ids': ['done'], 'semantic_annotations': []}


def test_ac01_diamond_loop_exception_and_async_roundtrip_preserve_exact_ids():
    source = sample_process()
    model = ProcessView.from_dict(source)
    actual = json.loads(model.to_json())
    assert {step.id for step in model.steps} == {'request', 'choose', 'card', 'cash', 'retry', 'send', 'done'}
    transitions = {(e.source, e.target, e.relation) for e in model.transitions}
    assert ('choose', 'card', 'true') in transitions
    assert ('choose', 'cash', 'false') in transitions
    assert ('card', 'cash', 'normal') not in transitions
    assert ('retry', 'choose', 'retry') in transitions
    assert ('card', 'retry', 'exception') in transitions
    assert ('send', 'done', 'async') in transitions
    assert model.outcome_ids == ('done',) and model.definition.revision == 3
    assert all(step.original_ids == ('origin:' + step.id,) for step in model.steps)
    assert ProcessView.from_dict(actual).to_json() == model.to_json()


def test_input_order_is_not_execution_order_or_identity():
    source = sample_process(); other = deepcopy(source)
    for key in ['nodes', 'edges', 'provenance']: other['technical_view'][key].reverse()
    first, second = ProcessView.from_dict(source), ProcessView.from_dict(other)
    assert first.to_json() == second.to_json()
    assert first.content_fingerprint == second.content_fingerprint


def test_ac02_approved_czech_label_never_changes_technical_truth():
    source = sample_process(); before = ProcessView.from_dict(source)
    source['semantic_annotations'] = [{'id': 'label:card', 'target_id': 'card',
        'label': 'Zaplatit kartou', 'description': 'Obchodní význam navržený uživatelem.',
        'source_refs': ['origin:card'], 'semantic_review_status': 'APPROVED',
        'grouping_proposal': ['card', 'cash']}]
    labelled = ProcessView.from_dict(source)
    assert labelled.technical_view.to_json() == before.technical_view.to_json()
    assert labelled.technical_fingerprint == before.technical_fingerprint
    assert labelled.technical_status == before.technical_status
    assert labelled.content_fingerprint != before.content_fingerprint
    assert labelled.to_dict()['semantic_annotations'][0]['label'] == 'Zaplatit kartou'
    assert labelled.definition.semantic_review_status == 'PROPOSED'


@pytest.mark.parametrize('key,value', [('technical_status', 'COMPLETE_WITHIN_SELECTED_SCOPE'),
    ('evidence_kind', 'RUNTIME_OBSERVED'), ('edges', []), ('conditions', 'true'),
    ('availability', 'AVAILABLE'), ('attributes', {'technical_status': 'RESOLVED'})])
def test_ac03_annotation_technical_injection_is_rejected(key, value):
    source = sample_process()
    source['semantic_annotations'] = [{'id': 'evil', 'target_id': 'card', 'label': 'Paid',
        'source_refs': [], 'semantic_review_status': 'APPROVED', key: value}]
    before = deepcopy(source)
    with pytest.raises(ViewValidationError, match='UNKNOWN_FIELD'):
        ProcessView.from_dict(source)
    assert source == before


@pytest.mark.parametrize('path,value,code', [
    (('technical_view', 'edges', 0, 'target'), 'missing', 'DANGLING_EDGE_ENDPOINT'),
    (('entry_ids',), ['missing'], 'INVALID_STEP_REFERENCE'),
    (('exit_ids',), ['missing'], 'INVALID_STEP_REFERENCE'),
    (('outcome_ids',), ['card'], 'INVALID_OUTCOME'),
    (('definition', 'trigger_ids'), ['missing'], 'DEFINITION_FINGERPRINT_MISMATCH'),
    (('revision',), 4, 'REVISION_MISMATCH'),
    (('definition', 'revision'), True, 'INVALID_REVISION'),
    (('definition', 'revision'), 0, 'INVALID_REVISION'),
    (('definition_fingerprint',), '0' * 64, 'DEFINITION_FINGERPRINT_MISMATCH'),
    (('technical_view', 'baseline_fingerprint'), 'other', 'BASELINE_MISMATCH'),
    (('technical_view', 'scope'), 'test', 'SCOPE_MISMATCH'),
    (('technical_view', 'context_selection'), {'orders': ['ctx-test']}, 'CONTEXT_SELECTION_MISMATCH'),
    (('technical_view', 'nodes', 0, 'original_ids'), [], 'ORIGINAL_IDS_REQUIRED'),
    (('technical_view', 'nodes', 0, 'evidence_refs'), [], 'EVIDENCE_REQUIRED'),
    (('technical_view', 'nodes', 0, 'attributes', 'context_ids'), ['foreign'], 'CONTEXT_MISMATCH'),
    (('technical_view', 'nodes', 0, 'attributes', 'scope'), 'test', 'SCOPE_MISMATCH'),
    (('technical_view', 'provenance', 0, 'context_ids'), ['foreign'], 'CONTEXT_MISMATCH'),
    (('technical_view', 'provenance', 0, 'scope'), 'test', 'SCOPE_MISMATCH'),
    (('technical_view', 'edges', 1, 'attributes', 'condition'), '', 'BRANCH_CONDITION_REQUIRED'),
    (('technical_status',), 'UNKNOWN', 'TECHNICAL_STATUS_MISMATCH'),
    (('schema_version',), 99, 'UNSUPPORTED_PROCESS_SCHEMA'),
    (('semantic_annotations',), [{'id': 'x', 'target_id': 'missing', 'label': 'Label',
        'source_refs': [], 'semantic_review_status': 'PROPOSED'}], 'INVALID_ANNOTATION_TARGET'),
])
def test_invalid_references_revision_scope_and_evidence_fail_without_mutation(tmp_path, path, value, code):
    source = sample_process(); target = source
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    if path == ('technical_view', 'nodes', 0, 'evidence_refs') and value == []:
        for key in ('supporting_refs', 'contradicting_refs', 'unknown_refs', 'evidence_kinds'):
            source['technical_view']['nodes'][0][key] = []
    before = deepcopy(source)
    last = tmp_path / 'last-valid.json'; last.write_text('last valid artifact')
    with patch('subprocess.Popen', side_effect=AssertionError('pure model')):
        with pytest.raises(ViewValidationError) as caught: ProcessView.from_dict(source)
    assert code in {error['code'] for error in caught.value.errors}
    assert source == before and last.read_text() == 'last valid artifact'


def test_missing_technical_proof_is_explicit_unknown_boundary_not_current_or_complete():
    source = sample_process(); view = source['technical_view']; view['coverage']['status'] = 'PARTIAL'
    source['technical_status'] = 'PARTIAL'
    boundary = view['nodes'][0]
    boundary.update(kind='unresolved_boundary', evidence_refs=[], evidence_kinds=[],
        supporting_refs=[], contradicting_refs=[], unknown_refs=[], resolution_status='UNRESOLVED', freshness='UNKNOWN')
    boundary['attributes']['boundary_reason'] = 'Compiler body unavailable'
    source['definition']['trigger_ids'] = []
    source['definition_fingerprint'] = ProcessDefinition.from_dict(source['definition']).content_fingerprint
    result = ProcessView.from_dict(source)
    assert result.technical_status == 'PARTIAL'
    roundtrip = result.to_dict()
    assert next(n for n in roundtrip['technical_view']['nodes'] if n['id'] == 'request')['freshness'] == 'UNKNOWN'
    bad = deepcopy(source); bad['technical_view']['coverage']['status'] = 'COMPLETE_WITHIN_SELECTED_SCOPE'
    bad['technical_status'] = 'COMPLETE_WITHIN_SELECTED_SCOPE'
    with pytest.raises(ViewValidationError, match='INCOMPLETE_TECHNICAL_COVERAGE'): ProcessView.from_dict(bad)


def test_mixed_evidence_stale_unknown_and_contradiction_are_never_strengthened():
    source = sample_process(); view = source['technical_view']; node = view['nodes'][0]; proof = view['provenance'][0]
    node.update(evidence_kinds=['SYNTAX_CANDIDATE'], freshness='STALE', resolution_status='UNRESOLVED',
                supporting_refs=[], unknown_refs=['ev:request'])
    proof.update(evidence_kind='SYNTAX_CANDIDATE', freshness='STALE', polarity='UNKNOWN')
    view['coverage']['status'] = source['technical_status'] = 'PARTIAL'
    result = ProcessView.from_dict(source).to_dict()
    actual = next(n for n in result['technical_view']['nodes'] if n['id'] == 'request')
    assert actual['evidence_kinds'] == ['SYNTAX_CANDIDATE']
    assert actual['freshness'] == 'STALE' and actual['unknown_refs'] == ['ev:request']
    assert result['technical_status'] == 'PARTIAL'


def test_model_copies_input_and_output_instead_of_aliasing_nested_payloads():
    source = sample_process(); model = ProcessView.from_dict(source); fingerprint = model.content_fingerprint
    source['technical_view']['nodes'][0]['label'] = 'modified input'
    output = model.to_dict(); output['technical_view']['nodes'][0]['label'] = 'modified output'
    assert model.content_fingerprint == fingerprint


def test_generation_timestamp_changes_no_process_or_technical_content_fingerprint():
    source = sample_process(); first = ProcessView.from_dict(source)
    source['technical_view']['generation_metadata'] = {'generated_at': '2026-10-27T00:00:00Z'}
    other = ProcessView.from_dict(source)
    assert first.content_fingerprint == other.content_fingerprint
    assert first.technical_fingerprint == other.technical_fingerprint


def test_definition_is_versioned_and_stable_identity_survives_revision():
    original = definition(); newer = deepcopy(original); newer['revision'] = 4
    first, second = ProcessDefinition.from_dict(original), ProcessDefinition.from_dict(newer)
    assert first.process_id == second.process_id and first.revision != second.revision
    assert first.content_fingerprint != second.content_fingerprint
    assert ProcessDefinition.from_dict(json.loads(first.to_json())).to_dict() == original


def test_public_json_schema_reuses_shared_view_schema_offline():
    import jsonschema
    from referencing import Registry, Resource
    root = Path(__file__).parents[1] / 'docs/schemas'
    process = json.loads((root / 'process-v1.schema.json').read_text())
    view = json.loads((root / 'view-v1.schema.json').read_text())
    registry = Registry().with_resource(view['$id'], Resource.from_contents(view))
    validator = jsonschema.Draft202012Validator(process, registry=registry)
    document = ProcessView.from_dict(sample_process()).to_dict()
    validator.validate(document)
    bad = deepcopy(document); bad['semantic_annotations'] = [{'id': 'injected', 'target_id': 'card',
        'source_refs': [], 'semantic_review_status': 'PROPOSED', 'technical_status': 'CURRENT'}]
    assert list(validator.iter_errors(bad))


@pytest.mark.parametrize('path,value,code', [
    (('technical_view', 'nodes', 0, 'evidence_kinds'), [], 'EVIDENCE_KIND_NOT_PRESERVED'),
    (('technical_view', 'provenance', 0, 'context_ids'), [], 'CONTEXT_REQUIRED'),
    (('technical_view', 'diagnostics'), [{'code': 'TRUNCATED_SOURCE'}], 'INCOMPLETE_TECHNICAL_COVERAGE'),
    (('technical_view', 'nodes', 0, 'kind'), 'invented', 'INVALID_STEP_KIND'),
    (('technical_view', 'edges', 0, 'relation'), 'invented', 'INVALID_TRANSITION_KIND'),
    (('definition', 'semantic_review_status'), 'AUTO_APPROVED', 'INVALID_SEMANTIC_REVIEW_STATUS'),
    (('semantic_annotations',), [{'id': 'x', 'target_id': 'card', 'label': 'Paid',
        'source_refs': ['invented-document-proof'], 'semantic_review_status': 'APPROVED'}], 'INVALID_ANNOTATION_SOURCE'),
    (('semantic_annotations',), [{'id': 'x', 'target_id': 'card', 'label': 'Paid',
        'source_refs': [], 'semantic_review_status': 'PROPOSED', 'grouping_proposal': ['invented-step']}], 'INVALID_GROUPING_REFERENCE'),
])
def test_additional_boundaries_reject_hidden_uncertainty_and_forged_citations(path, value, code):
    source = sample_process(); target = source
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with pytest.raises(ViewValidationError) as caught: ProcessView.from_dict(source)
    assert code in {error['code'] for error in caught.value.errors}


@pytest.mark.parametrize('value', [None, [], 7, {'schema_version': []}, {'definition': []}])
def test_malformed_top_level_is_a_structured_validation_error(value):
    with pytest.raises(ViewValidationError): ProcessView.from_dict(value)


@pytest.mark.parametrize('field', ['context_ids', 'trigger_ids'])
def test_duplicate_definition_references_are_rejected(field):
    value = definition(); value[field] *= 2
    with pytest.raises(ViewValidationError, match='DUPLICATE_REFERENCE'): ProcessDefinition.from_dict(value)


def test_non_json_nan_and_recursive_documents_are_structured_errors():
    value = sample_process(); value['technical_view']['nodes'][0]['attributes']['value'] = float('nan')
    with pytest.raises(ViewValidationError, match='NON_JSON_VALUE'): ProcessView.from_dict(value)
    value = {}; value['technical_view'] = value
    with pytest.raises(ViewValidationError, match='NON_JSON_VALUE'): ProcessView.from_dict(value)


def test_candidate_status_cannot_be_resolved_even_when_coverage_is_partial():
    source = sample_process(); view = source['technical_view']
    source['technical_status'] = view['coverage']['status'] = 'PARTIAL'
    view['nodes'][0]['evidence_kinds'] = ['SYNTAX_CANDIDATE']
    view['provenance'][0]['evidence_kind'] = 'SYNTAX_CANDIDATE'
    with pytest.raises(ViewValidationError, match='EVIDENCE_STATUS_UPGRADE'): ProcessView.from_dict(source)


@pytest.mark.parametrize('path,value', [
    (('technical_view', 'nodes', 0, 'original_ids'), 7),
    (('technical_view', 'nodes', 0, 'attributes'), []),
    (('technical_view', 'provenance'), [None]),
    (('definition', 'context_ids'), {}),
    (('entry_ids',), [{}]),
    (('semantic_annotations',), [None]),
])
def test_malformed_nested_json_is_a_structured_error_without_mutation(path, value):
    source = sample_process(); target = source
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value; before = deepcopy(source)
    with pytest.raises(ViewValidationError): ProcessView.from_dict(source)
    assert source == before


def test_pure_parse_and_serialization_perform_no_file_network_or_process_io():
    source = sample_process(); before = deepcopy(source)
    with patch('builtins.open', side_effect=AssertionError('no artifact/source reads or writes')), \
         patch('socket.socket', side_effect=AssertionError('no network')), \
         patch('subprocess.Popen', side_effect=AssertionError('no child processes')):
        model = ProcessView.from_dict(source)
        assert json.loads(model.to_json())['process_id'] == 'process:checkout'
        assert model.technical_fingerprint
    assert source == before


def test_unused_foreign_proof_cannot_be_smuggled_into_process_provenance():
    source = sample_process()
    source['technical_view']['provenance'].append({'id': 'foreign', 'scope': 'test',
        'context_ids': ['ctx-foreign'], 'evidence_kind': 'RUNTIME_OBSERVED',
        'freshness': 'CURRENT', 'polarity': 'SUPPORTING'})
    with pytest.raises(ViewValidationError) as caught: ProcessView.from_dict(source)
    assert {'SCOPE_MISMATCH', 'CONTEXT_MISMATCH'} <= {e['code'] for e in caught.value.errors}


def test_documented_fixture_loads_on_public_api_with_loop_and_no_guessed_branch_join():
    path = Path(__file__).parents[1] / 'fixtures/process-model/checkout.json'
    source = json.loads(path.read_text())
    model = ProcessView.from_dict(source)
    edges = {(e.source, e.target, e.relation) for e in model.transitions}
    assert ('retry', 'choose', 'retry') in edges
    assert ('send', 'done', 'async') in edges
    assert not any(source == 'card' and target == 'cash' for source, target, _ in edges)
    assert model.definition.process_id == 'process:checkout' and model.definition.revision == 3


@pytest.mark.parametrize('path,value', [
    (('technical_view', 'edges', 0, 'relation'), []),
    (('technical_view', 'edges', 0, 'relation'), {}),
    (('technical_view', 'provenance', 0, 'evidence_kind'), []),
    (('technical_view', 'provenance', 0, 'evidence_kind'), {}),
])
def test_independent_review_malformed_enum_shapes_remain_structured_and_read_only(tmp_path, path, value):
    source = sample_process(); target = source
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value; before = deepcopy(source)
    artifact = tmp_path / 'last-valid.json'; artifact.write_bytes(b'valid unchanged generation')
    with pytest.raises(ViewValidationError): ProcessView.from_dict(source)
    assert source == before and artifact.read_bytes() == b'valid unchanged generation'


@pytest.mark.parametrize('collision', ['node_edge', 'process_node'])
def test_semantic_target_identity_is_unambiguous_across_process_steps_and_transitions(collision):
    source = sample_process()
    if collision == 'node_edge': source['technical_view']['edges'][0]['id'] = 'request'
    else:
        source['process_id'] = source['definition']['process_id'] = source['technical_view']['view_id'] = 'request'
        source['definition_fingerprint'] = ProcessDefinition.from_dict(source['definition']).content_fingerprint
    with pytest.raises(ViewValidationError, match='DUPLICATE_PROCESS_TARGET'): ProcessView.from_dict(source)

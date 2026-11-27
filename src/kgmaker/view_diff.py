"""Pure comparison of two explicit, captured ProcessView projections."""

from copy import deepcopy

from .analysis_model import canonical, digest
from .architecture_model import ViewValidationError
from .architecture_render_common import InterfaceMarkdownError, _bounded
from .process_model import ProcessView, validate_process_view


_EVIDENCE_FIELDS = frozenset({'original_ids', 'evidence_refs', 'evidence_kinds',
                              'supporting_refs', 'contradicting_refs', 'unknown_refs'})
_BOUNDARY_FIELDS = ('entry_ids', 'exit_ids', 'outcome_ids', 'trigger_ids')
_CAPTURE_ID_FIELDS = ('repo_id', 'module', 'context_fingerprint', 'context_selection_key')
_COVERAGE_FIELDS = ('coverage', 'diagnostics', 'limits', 'truncated_node_ids', 'truncated_edge_ids')


def _document(view, side):
    if type(view) is not ProcessView:
        raise ViewValidationError([{'code': 'INVALID_PROCESS_VIEW', 'path': side}])
    try:
        _bounded(vars(view))
    except InterfaceMarkdownError as error:
        code = 'PROCESS_DIFF_LIMIT' if error.code == 'INTERFACE_MARKDOWN_LIMIT' else 'INVALID_PROCESS_VIEW'
        raise ViewValidationError([{'code': code, 'path': side}]) from None
    # Some nested fields returned by ViewDocument retain the input's objects.
    document = deepcopy(view.to_dict(include_generation_metadata=False))
    validate_process_view(document)
    return document


def _strings(values):
    return isinstance(values, (list, tuple)) and all(isinstance(item, str) and item for item in values)


def _structured_selection(services, scope, selected):
    normalized = {}
    for service_id, service in services.items():
        if (not service_id or not isinstance(service, dict) or service.get('scope') != scope
                or not isinstance(service.get('contexts'), (list, tuple)) or not service['contexts']):
            return None
        rows = []
        for row in service['contexts']:
            if (not isinstance(row, dict) or row.get('scope') != scope or 'context_id' not in row
                    or row.get('service_id', service_id) != service_id):
                return None
            candidates = row.get('candidate_context_ids', ())
            if not _strings(candidates):
                return None
            context = row['context_id']
            if context is not None:
                if (not isinstance(context, str) or not context or row.get('status') != 'CURRENT'
                        or not all(isinstance(row.get(key), str) and row[key] for key in _CAPTURE_ID_FIELDS)):
                    return None
                selected.append(context)
            normalized_row = dict(row)
            if 'candidate_context_ids' in row:
                normalized_row['candidate_context_ids'] = sorted(candidates)
            owners = row.get('candidate_owner_ids')
            if _strings(owners):
                normalized_row['candidate_owner_ids'] = sorted(owners)
            diagnostics = row.get('diagnostics')
            if (context is not None and isinstance(diagnostics, (list, tuple))
                    and all(isinstance(item, dict) for item in diagnostics)):
                normalized_row['diagnostics'] = sorted(diagnostics, key=canonical)
            rows.append(normalized_row)
        normalized[service_id] = {**service, 'contexts': sorted(rows, key=canonical)}
    return {'services': normalized}


def _selection(definition):
    selection = definition['context_selection']
    selected = []
    if set(selection) == {'services'} and isinstance(selection['services'], dict):
        normalized = _structured_selection(selection['services'], definition['scope'], selected)
    else:
        normalized = {}
        for service_id, contexts in selection.items():
            if not service_id or not _strings(contexts) or not contexts:
                return None
            selected.extend(contexts)
            normalized[service_id] = sorted(contexts)
    if selected and sorted(selected) == definition['context_ids']:
        return normalized
    return None


def _binding(document):
    definition = document['definition']
    technical = document['technical_view']
    return {
        'content_fingerprint': digest(document),
        'baseline_fingerprint': definition['baseline_fingerprint'],
        'process_id': definition['process_id'], 'revision': definition['revision'],
        'scope': definition['scope'], 'rules_version': technical['rules_version'],
        'context_ids': definition['context_ids'], 'context_selection': definition['context_selection'],
        'coverage': technical['coverage'], 'diagnostics': technical['diagnostics'], 'limits': technical['limits'],
        'unresolved_node_ids': [row['id'] for row in technical['nodes'] if row['resolution_status'] != 'RESOLVED'],
        'unresolved_edge_ids': [row['id'] for row in technical['edges'] if row['resolution_status'] != 'RESOLVED'],
        'truncated_node_ids': [row['id'] for row in technical['nodes'] if row['attributes'].get('truncated') is True],
        'truncated_edge_ids': [row['id'] for row in technical['edges'] if row['attributes'].get('truncated') is True],
    }


def _incompatibilities(before, after):
    left, right = before['definition'], after['definition']
    reasons = [reason for field, reason in (
        ('process_id', 'PROCESS_MISMATCH'), ('scope', 'SCOPE_MISMATCH'), ('context_ids', 'CONTEXT_MISMATCH'),
    ) if left[field] != right[field]]
    if before['technical_view']['rules_version'] != after['technical_view']['rules_version']:
        reasons.append('RULES_MISMATCH')
    if reasons:
        return reasons
    left_selection, right_selection = _selection(left), _selection(right)
    if left_selection is None or right_selection is None:
        return ['UNPROVEN_CONTEXT_SELECTION']
    if canonical(left_selection) != canonical(right_selection):
        return ['CONTEXT_SELECTION_MISMATCH']
    return []


def _complete_projection(binding):
    coverage = binding['coverage']
    counts = coverage.get('counts', {})
    return (coverage['status'] == 'COMPLETE_WITHIN_SELECTED_SCOPE'
            and coverage.get('truncated', False) is False
            and not (binding['truncated_node_ids'] or binding['truncated_edge_ids'])
            and not counts.get('excluded') and not counts.get('unresolved')
            and not any(value for key, value in coverage.items() if key.startswith(('omitted_', 'excluded_'))))


def _projection_limits(binding):
    coverage = {key: value for key, value in binding['coverage'].items() if key not in {'counts', 'truncated'}}
    return coverage, binding['limits']


def _changes(before, after):
    return sorted(key for key in before.keys() | after.keys()
                  if key not in before or key not in after or canonical(before[key]) != canonical(after[key]))


def _record_fields(collection, row):
    fields = {key: value for key, value in row.items() if key != 'id'}
    if 'context_ids' in fields:
        fields['context_ids'] = sorted(fields['context_ids'])
    if collection in {'nodes', 'edges'}:
        attributes = dict(fields['attributes'])
        if 'context_ids' in attributes:
            attributes['context_ids'] = sorted(attributes['context_ids'])
        if 'boundary_reason' in attributes:
            fields['attributes.boundary_reason'] = attributes.pop('boundary_reason')
        if type(attributes.get('truncated')) is bool:
            attributes.pop('truncated')
        fields['attributes'] = attributes
    return fields


def _category(collection, field):
    if collection == 'supplied_annotations':
        return 'supplied_annotation'
    if field == 'label' and collection == 'nodes':
        return 'presentation'
    if field == 'freshness':
        return 'freshness'
    if field in {'resolution_status', 'attributes.boundary_reason'}:
        return 'resolution'
    if field in _EVIDENCE_FIELDS or collection == 'provenance':
        return 'evidence'
    return 'topology'


def _record_delta(collection, before, after, complete):
    left = {row['id']: row for row in before}
    right = {row['id']: row for row in after}
    changed = []
    for identity in sorted(left.keys() & right.keys()):
        old, new = left[identity], right[identity]
        fields = {}
        for field in _changes(_record_fields(collection, old), _record_fields(collection, new)):
            fields.setdefault(_category(collection, field), []).append(field)
        if fields:
            changed.append({'id': identity, 'fields': fields, 'before': old, 'after': new})
    return {key: records for key, records in (
        ('added' if complete else 'not_observed_before',
         [right[identity] for identity in sorted(right.keys() - left.keys())]),
        ('removed' if complete else 'not_observed_after',
         [left[identity] for identity in sorted(left.keys() - right.keys())]),
        ('changed', changed),
    ) if records}


def _boundaries(document):
    return {key: document['definition'][key] if key == 'trigger_ids' else document[key]
            for key in _BOUNDARY_FIELDS}


def diff_process_views(before: ProcessView, after: ProcessView) -> dict:
    """Report recorded deltas with the scope, coverage and witnesses of each input.

    Additions and removals refer to records in matching complete projections.
    Supplied semantic annotations retain their original metadata.
    """
    left = _document(before, 'before')
    right = _document(after, 'after')
    old, new = _binding(left), _binding(right)
    reasons = _incompatibilities(left, right)
    changes = {}
    result = {'status': 'INCOMPARABLE' if reasons else 'COMPARABLE', 'reasons': reasons,
              'before': old, 'after': new, 'changes': changes}
    if reasons:
        return result

    complete = (_complete_projection(old) and _complete_projection(new)
                and canonical(_projection_limits(old)) == canonical(_projection_limits(new)))
    for collection in ('nodes', 'edges', 'provenance', 'supplied_annotations'):
        if collection == 'supplied_annotations':
            a, b = left['semantic_annotations'], right['semantic_annotations']
        else:
            a, b = left['technical_view'][collection], right['technical_view'][collection]
        delta = _record_delta(collection, a, b, complete)
        if delta:
            changes[collection] = delta

    comparisons = {
        'boundaries': (_boundaries(left), _boundaries(right)),
        'coverage': ({key: old[key] for key in _COVERAGE_FIELDS},
                     {key: new[key] for key in _COVERAGE_FIELDS}),
        'supplied_review_status': (left['definition']['semantic_review_status'],
                                   right['definition']['semantic_review_status']),
    }
    for key, (previous, current) in comparisons.items():
        if canonical(previous) != canonical(current):
            changes[key] = {'before': previous, 'after': current}
    return result

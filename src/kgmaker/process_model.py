"""Pure, versioned business-process documents built on the shared view contract.

These models validate explicit documents. They do not discover triggers, derive
execution order, approve annotations, load a graph, or publish an artifact.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from .architecture_model import ViewDocument, ViewValidationError, validate_view_document

PROCESS_SCHEMA_VERSION = 1
SEMANTIC_REVIEW_STATUSES = frozenset({'PROPOSED', 'APPROVED', 'REJECTED', 'NEEDS_REVALIDATION'})
STEP_KINDS = frozenset({'trigger', 'action', 'decision', 'outcome', 'entry', 'exit',
    'basic_block', 'call', 'condition', 'loop_header', 'return', 'throw', 'break', 'continue',
    'exception_dispatch', 'exceptional_exit', 'async_boundary', 'unresolved_boundary',
    'service_boundary', 'transaction_boundary', 'retry'})
TRANSITION_KINDS = frozenset({'normal', 'branch', 'true', 'false', 'case', 'exception',
    'finally', 'loop', 'retry', 'async', 'suspend', 'resume', 'call', 'returns_to',
    'return', 'throw', 'break', 'continue', 'unknown'})
DEFINITION_FIELDS = frozenset({'schema_version', 'process_id', 'revision', 'baseline_fingerprint',
    'scope', 'context_selection', 'context_ids', 'trigger_ids', 'semantic_review_status'})
PROCESS_FIELDS = frozenset({'schema_version', 'process_id', 'revision', 'definition',
    'definition_fingerprint', 'technical_status', 'technical_view', 'entry_ids', 'exit_ids',
    'outcome_ids', 'semantic_annotations'})
ANNOTATION_FIELDS = frozenset({'id', 'target_id', 'label', 'description', 'source_refs',
    'semantic_review_status', 'grouping_proposal'})


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _fingerprint(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


class _Validation:
    def __init__(self):
        self.errors = []

    def error(self, code, path):
        item = {'code': code, 'path': path}
        if item not in self.errors:
            self.errors.append(item)

    def object(self, value, allowed, required, path):
        if not isinstance(value, Mapping):
            self.error('INVALID_OBJECT', path)
            return False
        for key in set(value) - allowed:
            self.error('UNKNOWN_FIELD', path + '.' + str(key))
        for key in required - set(value):
            self.error('REQUIRED_FIELD', path + '.' + key)
        return True

    def strings(self, value, path, *, nonempty=False):
        if (not isinstance(value, (list, tuple)) or any(not isinstance(x, str) or not x for x in value)):
            self.error('INVALID_STRING_ARRAY', path)
            return []
        if len(set(value)) != len(value):
            self.error('DUPLICATE_REFERENCE', path)
        if nonempty and not value:
            self.error('ORIGINAL_IDS_REQUIRED', path)
        return list(value)

    def json(self, value):
        try:
            _canonical(value)
        except (ValueError, TypeError, OverflowError, RecursionError):
            self.error('NON_JSON_VALUE', '$')

    def finish(self):
        if self.errors:
            raise ViewValidationError(self.errors)


def _definition(data, check, prefix='definition'):
    if not check.object(data, DEFINITION_FIELDS, DEFINITION_FIELDS, prefix):
        return
    if type(data.get('schema_version')) is not int or data['schema_version'] != PROCESS_SCHEMA_VERSION:
        check.error('UNSUPPORTED_PROCESS_SCHEMA', prefix + '.schema_version')
    for name in ('process_id', 'baseline_fingerprint', 'scope'):
        if not isinstance(data.get(name), str) or not data[name]:
            check.error('REQUIRED_STRING', prefix + '.' + name)
    if type(data.get('revision')) is not int or data['revision'] < 1:
        check.error('INVALID_REVISION', prefix + '.revision')
    if not isinstance(data.get('context_selection'), Mapping):
        check.error('INVALID_CONTEXT_SELECTION', prefix + '.context_selection')
    check.strings(data.get('context_ids'), prefix + '.context_ids')
    check.strings(data.get('trigger_ids'), prefix + '.trigger_ids')
    status = data.get('semantic_review_status')
    if not isinstance(status, str) or status not in SEMANTIC_REVIEW_STATUSES:
        check.error('INVALID_SEMANTIC_REVIEW_STATUS', prefix + '.semantic_review_status')


def validate_process_definition(data):
    """Validate a declared identity/revision; trigger targets bind in ProcessView."""
    check = _Validation()
    check.json(data)
    check.finish()
    _definition(data, check, '$')
    check.finish()


def _canonical_definition(data):
    result = deepcopy(dict(data))
    for key in ('context_ids', 'trigger_ids'):
        result[key] = sorted(result[key])
    return result


def validate_process_view(data):
    """Validate topology, revision binding, evidence and the semantic-only overlay.

    Source freshness is carried from explicit input proofs. This function does
    not validate a checkout or turn a declaration into an execution observation.
    """
    check = _Validation()
    check.json(data)
    check.finish()
    if not check.object(data, PROCESS_FIELDS, PROCESS_FIELDS, '$'):
        check.finish()
    if type(data.get('schema_version')) is not int or data['schema_version'] != PROCESS_SCHEMA_VERSION:
        check.error('UNSUPPORTED_PROCESS_SCHEMA', 'schema_version')
    definition = data.get('definition')
    _definition(definition, check)
    if not isinstance(definition, Mapping):
        check.finish()
    for field, code in [('process_id', 'PROCESS_ID_MISMATCH'), ('revision', 'REVISION_MISMATCH')]:
        if (type(data.get(field)) is not type(definition.get(field))
                or data.get(field) != definition.get(field)):
            check.error(code, field)
    try:
        fingerprint = _fingerprint(_canonical_definition(definition))
    except (TypeError, ValueError, KeyError, RecursionError):
        fingerprint = None
    if not isinstance(data.get('definition_fingerprint'), str) or data['definition_fingerprint'] != fingerprint:
        check.error('DEFINITION_FINGERPRINT_MISMATCH', 'definition_fingerprint')
    view = data.get('technical_view')
    try:
        validate_view_document(view)
    except ViewValidationError as error:
        for item in error.errors:
            check.error(item['code'], 'technical_view.' + item['path'])
        # Own cross-reference checks require the shared primitive shapes. Do not
        # inspect malformed enum/list values after their error was established.
        check.finish()
    if not isinstance(view, Mapping):
        check.finish()
    for field, expected, code in [('kind', 'process', 'INVALID_KIND'),
        ('view_id', definition.get('process_id'), 'PROCESS_ID_MISMATCH'),
        ('scope', definition.get('scope'), 'SCOPE_MISMATCH'),
        ('context_selection', definition.get('context_selection'), 'CONTEXT_SELECTION_MISMATCH'),
        ('baseline_fingerprint', definition.get('baseline_fingerprint'), 'BASELINE_MISMATCH')]:
        if view.get(field) != expected:
            check.error(code, 'technical_view.' + field)
    coverage = view.get('coverage')
    coverage_status = coverage.get('status') if isinstance(coverage, Mapping) else None
    if data.get('technical_status') != coverage_status:
        check.error('TECHNICAL_STATUS_MISMATCH', 'technical_status')
    selected = check.strings(definition.get('context_ids'), 'definition.context_ids')
    nodes = view.get('nodes') if isinstance(view.get('nodes'), list) else []
    edges = view.get('edges') if isinstance(view.get('edges'), list) else []
    provenance = view.get('provenance') if isinstance(view.get('provenance'), list) else []
    node_index = {n['id']: n for n in nodes if isinstance(n, Mapping) and isinstance(n.get('id'), str)}
    evidence = {p['id']: p for p in provenance if isinstance(p, Mapping) and isinstance(p.get('id'), str)}
    incomplete = not nodes or bool(view.get('diagnostics'))

    def scope_context(item, path):
        if item.get('scope') != definition.get('scope'):
            check.error('SCOPE_MISMATCH', path + '.scope')
        contexts = check.strings(item.get('context_ids'), path + '.context_ids')
        if not set(contexts) <= set(selected):
            check.error('CONTEXT_MISMATCH', path + '.context_ids')
        return set(contexts)

    for index, record in enumerate(provenance):
        if isinstance(record, Mapping):
            scope_context(record, 'technical_view.provenance[' + str(index) + ']')

    for collection_name, collection in [('nodes', nodes), ('edges', edges)]:
        for index, item in enumerate(collection):
            path = 'technical_view.' + collection_name + '[' + str(index) + ']'
            if not isinstance(item, Mapping):
                continue
            check.strings(item.get('original_ids'), path + '.original_ids', nonempty=True)
            attrs = item.get('attributes')
            if not isinstance(attrs, Mapping):
                continue
            contexts = scope_context(attrs, path + '.attributes')
            refs = check.strings(item.get('evidence_refs'), path + '.evidence_refs')
            kinds = check.strings(item.get('evidence_kinds', []), path + '.evidence_kinds')
            status, freshness = item.get('resolution_status'), item.get('freshness')
            reason = attrs.get('boundary_reason')
            explicit_unknown = (status == 'UNRESOLVED' and freshness == 'UNKNOWN'
                and isinstance(reason, str) and bool(reason)
                and set(kinds) <= {'UNKNOWN', 'UNRESOLVED'})
            if not refs and not explicit_unknown:
                check.error('EVIDENCE_REQUIRED', path + '.evidence_refs')
            if not contexts and not explicit_unknown:
                check.error('CONTEXT_REQUIRED', path + '.attributes.context_ids')
            referenced_kinds = {evidence[ref].get('evidence_kind', 'UNKNOWN') for ref in refs
                if ref in evidence and isinstance(evidence[ref].get('evidence_kind', 'UNKNOWN'), str)}
            if refs and set(kinds) != referenced_kinds:
                check.error('EVIDENCE_KIND_NOT_PRESERVED', path + '.evidence_kinds')
            if status == 'RESOLVED' and referenced_kinds & {'UNKNOWN', 'UNRESOLVED', 'SYNTAX_CANDIDATE', 'DISPATCH_CANDIDATE'}:
                check.error('EVIDENCE_STATUS_UPGRADE', path + '.resolution_status')
            if collection_name == 'nodes':
                if not isinstance(item.get('kind'), str) or item['kind'] not in STEP_KINDS:
                    check.error('INVALID_STEP_KIND', path + '.kind')
            else:
                relation = item.get('relation')
                if not isinstance(relation, str) or relation not in TRANSITION_KINDS:
                    check.error('INVALID_TRANSITION_KIND', path + '.relation')
                if relation in {'branch', 'true', 'false', 'case'} and (
                        not isinstance(attrs.get('condition'), str) or not attrs['condition']):
                    check.error('BRANCH_CONDITION_REQUIRED', path + '.attributes.condition')
            if status != 'RESOLVED' or freshness != 'CURRENT' or not refs:
                incomplete = True
            for ref in refs:
                record = evidence.get(ref)
                if record is None:
                    continue  # Shared validator reports the dangling reference.
                proof_contexts = scope_context(record, 'technical_view.provenance.' + ref)
                if not proof_contexts and not explicit_unknown:
                    check.error('CONTEXT_REQUIRED', path + '.evidence_refs')
                if not proof_contexts <= contexts:
                    check.error('CONTEXT_MISMATCH', path + '.evidence_refs')
                if (record.get('polarity', 'UNKNOWN') != 'SUPPORTING'
                        or record.get('freshness', 'UNKNOWN') != 'CURRENT'
                        or record.get('evidence_kind', 'UNKNOWN') in
                            {'UNKNOWN', 'UNRESOLVED', 'SYNTAX_CANDIDATE', 'DISPATCH_CANDIDATE'}):
                    incomplete = True

    for name in ('entry_ids', 'exit_ids', 'outcome_ids'):
        refs = check.strings(data.get(name), name)
        for ref in refs:
            if ref not in node_index:
                check.error('INVALID_STEP_REFERENCE', name)
            elif name == 'outcome_ids' and (node_index[ref].get('kind') != 'outcome'
                    or ref not in (data.get('exit_ids') if isinstance(data.get('exit_ids'), list) else [])):
                check.error('INVALID_OUTCOME', name)
    triggers = check.strings(definition.get('trigger_ids'), 'definition.trigger_ids')
    entries = data.get('entry_ids') if isinstance(data.get('entry_ids'), list) else []
    for ref in triggers:
        if ref not in node_index or node_index[ref].get('kind') != 'trigger' or ref not in entries:
            check.error('INVALID_TRIGGER', 'definition.trigger_ids')
    if not entries or not data.get('exit_ids'):
        incomplete = True
    if incomplete and coverage_status == 'COMPLETE_WITHIN_SELECTED_SCOPE':
        check.error('INCOMPLETE_TECHNICAL_COVERAGE', 'technical_status')

    annotations = data.get('semantic_annotations')
    if not isinstance(annotations, list):
        check.error('INVALID_ANNOTATIONS', 'semantic_annotations')
        annotations = []
    known_targets = {definition.get('process_id')} if isinstance(definition.get('process_id'), str) else set()
    for item in nodes + edges:
        if isinstance(item, Mapping) and isinstance(item.get('id'), str):
            if item['id'] in known_targets:
                check.error('DUPLICATE_PROCESS_TARGET', 'technical_view.' + item['id'])
            known_targets.add(item['id'])
    known_sources = set(evidence) | known_targets
    for item in nodes + edges:
        if isinstance(item, Mapping) and isinstance(item.get('original_ids'), (list, tuple)):
            known_sources.update(x for x in item['original_ids'] if isinstance(x, str))
    known_sources.update(p['source_id'] for p in evidence.values() if isinstance(p.get('source_id'), str))
    annotation_ids = set()
    for index, item in enumerate(annotations):
        path = 'semantic_annotations[' + str(index) + ']'
        if not check.object(item, ANNOTATION_FIELDS,
                {'id', 'target_id', 'source_refs', 'semantic_review_status'}, path):
            continue
        identity = item.get('id')
        if not isinstance(identity, str) or not identity:
            check.error('REQUIRED_STRING', path + '.id')
        elif identity in annotation_ids:
            check.error('DUPLICATE_ANNOTATION_ID', path + '.id')
        else:
            annotation_ids.add(identity)
        if not isinstance(item.get('target_id'), str) or item['target_id'] not in known_targets:
            check.error('INVALID_ANNOTATION_TARGET', path + '.target_id')
        review = item.get('semantic_review_status')
        if not isinstance(review, str) or review not in SEMANTIC_REVIEW_STATUSES:
            check.error('INVALID_SEMANTIC_REVIEW_STATUS', path + '.semantic_review_status')
        for field in ('label', 'description'):
            if field in item and (not isinstance(item[field], str) or not item[field]):
                check.error('REQUIRED_STRING', path + '.' + field)
        source_refs = check.strings(item.get('source_refs'), path + '.source_refs')
        if not set(source_refs) <= known_sources:
            check.error('INVALID_ANNOTATION_SOURCE', path + '.source_refs')
        if not any(field in item for field in ('label', 'description', 'grouping_proposal')):
            check.error('EMPTY_ANNOTATION', path)
        if 'grouping_proposal' in item:
            grouping = check.strings(item['grouping_proposal'], path + '.grouping_proposal')
            if not grouping or any(ref not in node_index for ref in grouping):
                check.error('INVALID_GROUPING_REFERENCE', path + '.grouping_proposal')
    check.finish()


@dataclass(frozen=True)
class ProcessDefinition:
    """Declared process identity and revision; approval here is supplied metadata."""
    _document: Mapping

    def __post_init__(self):
        validate_process_definition(self._document)
        object.__setattr__(self, '_document', _canonical_definition(self._document))

    @classmethod
    def from_dict(cls, data):
        return cls(data)

    def to_dict(self):
        return deepcopy(self._document)

    def to_json(self):
        return _canonical(self.to_dict())

    @property
    def content_fingerprint(self):
        return _fingerprint(self.to_dict())

    @property
    def process_id(self): return self._document['process_id']
    @property
    def revision(self): return self._document['revision']
    @property
    def scope(self): return self._document['scope']
    @property
    def semantic_review_status(self): return self._document['semantic_review_status']
    @property
    def trigger_ids(self): return tuple(self._document['trigger_ids'])


@dataclass(frozen=True)
class ProcessView:
    """Technical view plus a strictly separate, non-executable semantic overlay."""
    _document: Mapping

    def __post_init__(self):
        validate_process_view(self._document)
        object.__setattr__(self, '_document', deepcopy(dict(self._document)))

    @classmethod
    def from_dict(cls, data):
        return cls(data)

    def to_dict(self, *, include_generation_metadata=True):
        result = deepcopy(self._document)
        result['definition'] = self.definition.to_dict()
        result['technical_view'] = self.technical_view.to_dict(include_generation_metadata=include_generation_metadata)
        for name in ('entry_ids', 'exit_ids', 'outcome_ids'):
            result[name] = sorted(result[name])
        for item in result['semantic_annotations']:
            for name in ('source_refs', 'grouping_proposal'):
                if name in item: item[name] = sorted(item[name])
        result['semantic_annotations'].sort(key=lambda item: item['id'])
        return result

    def to_json(self, *, include_generation_metadata=True):
        return _canonical(self.to_dict(include_generation_metadata=include_generation_metadata))

    @property
    def content_fingerprint(self):
        return _fingerprint(self.to_dict(include_generation_metadata=False))

    @property
    def technical_fingerprint(self): return self.technical_view.content_fingerprint
    @property
    def definition(self): return ProcessDefinition.from_dict(self._document['definition'])
    @property
    def technical_view(self): return ViewDocument.from_dict(self._document['technical_view'])
    @property
    def steps(self): return self.technical_view.nodes
    @property
    def transitions(self): return self.technical_view.edges
    @property
    def outcome_ids(self): return tuple(sorted(self._document['outcome_ids']))
    @property
    def technical_status(self): return self._document['technical_status']

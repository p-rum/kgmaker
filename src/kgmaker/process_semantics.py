"""Pure, bounded T030 packets; supplied facts are not semantic approval.

No checkout, provider, feature.prepare, model call, filesystem or apply operation
belongs here. Raw presentation/configuration/proof text is never exported.
"""
from copy import deepcopy
import hashlib
import math
import re
import unicodedata

from .analysis_model import canonical, digest
from .architecture_model import EVIDENCE_KINDS, EVIDENCE_POLARITIES, FRESHNESS_STATUSES
from .process_model import ANNOTATION_FIELDS, ProcessView

VERSION = 'process-label-packet-1'
HARD_PACKET_CHAR_LIMIT = 2_000_000
_INPUT_CHAR_LIMIT = 4_000_000
_INPUT_ITEM_LIMIT = 100_000
_INPUT_DEPTH_LIMIT = 40
_CREDENTIAL = re.compile(r'(?i)(authorization\s*:\s*|bearer\s+\S+|(?:password|passwd|secret|credential|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*[=:]\s*\S+|-----BEGIN|://|\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b)')
# Same recognized auth token syntax as inspection.sanitize; reject immutable
# identifiers instead of redacting or returning the material in an exception.
_AUTH_TOKEN = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*", re.I)
_URI_USERINFO = re.compile(r"//[^/\s]*@")
_FORMATS = frozenset({'HTML', 'MARKDOWN', 'TEXT', 'STRUCTURED'})
_BOUNDARIES = frozenset({'unresolved_boundary', 'service_boundary', 'transaction_boundary',
    'async_boundary', 'retry', 'exception_dispatch', 'exceptional_exit'})


class ProcessLabelPacketError(ValueError):
    """Errors contain fixed codes only, never input values or validation paths."""
    def __init__(self, code):
        self.diagnostic = {'code': code}
        super().__init__(code)


def _fail(code):
    raise ProcessLabelPacketError(code) from None


def _bounded(value):
    # Per occurrence (including shared aliases), before model copy or JSON.
    stack = [(iter((value,)), 0, None)]; active = set(); count = chars = 0
    while stack:
        iterator, depth, owner = stack[-1]
        try:
            item = next(iterator)
        except StopIteration:
            stack.pop()
            if owner is not None: active.remove(owner)
            continue
        count += 1
        if count > _INPUT_ITEM_LIMIT or depth > _INPUT_DEPTH_LIMIT:
            _fail('INPUT_STRUCTURE_LIMIT')
        if type(item) is str:
            chars += len(item)
        elif type(item) is int:
            if item.bit_length() > 128: _fail('INPUT_NUMBER_LIMIT')
        elif type(item) is float:
            if not math.isfinite(item): _fail('INVALID_JSON_INPUT')
        elif item is not None and type(item) not in (bool, dict, list, tuple):
            _fail('INVALID_JSON_INPUT')
        if type(item) in (dict, list, tuple):
            if id(item) in active: _fail('CYCLIC_INPUT')
            if len(item) > 30_000: _fail('INPUT_COLLECTION_LIMIT')
            if type(item) is dict:
                for key in item:
                    if type(key) is not str: _fail('INVALID_JSON_INPUT')
                    chars += len(key)
                children = iter(item.values())
            else: children = iter(item)
            active.add(id(item)); stack.append((children, depth + 1, id(item)))
        if chars > _INPUT_CHAR_LIMIT: _fail('INPUT_TEXT_LIMIT')


def _identifier(value):
    if (type(value) is not str or not value or len(value) > 4096
            or any(unicodedata.category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'} for char in value)
            or _CREDENTIAL.search(value) is not None or _AUTH_TOKEN.search(value) is not None
            or _URI_USERINFO.search(value) is not None):
        _fail('UNSAFE_REQUIRED_IDENTIFIER')
    return value


def _identifiers(values):
    if type(values) not in (list, tuple): _fail('INVALID_REFERENCE_LIST')
    return sorted({_identifier(value) for value in values})


def _context_selection(value, scope, contexts, *, replay=False):
    """Normalize declared selections or validate replay of their exact hash bindings."""
    if type(value) is not dict: _fail('INVALID_SELECTION')
    allowed_ids = {'service_id', 'repo_id', 'module', 'context_id',
                   'context_fingerprint', 'context_selection_key'}
    lists = {'candidate_context_ids', 'candidate_owner_ids', 'profile'}
    enums = {'mode', 'status', 'freshness', 'evidence_kind', 'module_coverage'}
    capture_fields = {'coverage_binding', 'diagnostics_binding'} if replay else {'coverage', 'diagnostics'}
    enum_values = EVIDENCE_KINDS | FRESHNESS_STATUSES | {
        'BUILD_IMPORT', 'BUILD_EXECUTE', 'COMPILER', 'CONTENT_VERIFIED', 'EXECUTION_BOUND',
        'PARTIAL', 'AMBIGUOUS', 'COMPLETE', 'COMPLETE_WITHIN_SELECTED_SCOPE',
        'COMPLETE_WITHIN_SUPPORTED_SYNTAX', 'COMPLETE_WITHIN_SUPPORTED_MATRIX'}
    def row(item):
        if type(item) is not dict or set(item) - allowed_ids - lists - enums - {'scope'} - capture_fields:
            _fail('UNSUPPORTED_SELECTION_SHAPE')
        result = {}
        for key, child in item.items():
            if key in allowed_ids:
                result[key] = None if child is None else _identifier(child)
                if key == 'context_id' and child is not None and child not in contexts:
                    _fail('SELECTION_CONTEXT_MISMATCH')
            elif key in lists:
                if child is None: result[key] = None
                elif type(child) in (list, tuple): result[key] = [_identifier(c) for c in child]
                elif key == 'profile': result[key] = _identifier(child)
                else: _fail('INVALID_SELECTION')
            elif key in enums:
                if type(child) is not str or child not in enum_values: _fail('UNSUPPORTED_SELECTION_STATUS')
                result[key] = child
            elif key == 'scope':
                if child != scope: _fail('SELECTION_SCOPE_MISMATCH')
                result[key] = scope
            elif key in capture_fields:
                if replay:
                    if (type(child) is not dict or set(child) != {'content_hash'}
                            or type(child['content_hash']) is not str
                            or re.fullmatch('[0-9a-f]{64}', child['content_hash']) is None):
                        _fail('INVALID_SELECTION_BINDING')
                    result[key] = {'content_hash': child['content_hash']}
                else:
                    # Preserve the capture binding without copying its prose.
                    result[key + '_binding'] = {'content_hash': digest(child)}
        return result
    def service(item):
        if type(item) in (list, tuple):
            selected = [_identifier(c) for c in item]
            if not set(selected) <= set(contexts): _fail('SELECTION_CONTEXT_MISMATCH')
            return selected
        if type(item) is not dict: _fail('UNSUPPORTED_SELECTION_SHAPE')
        if 'contexts' not in item: return row(item)
        if set(item) - {'scope', 'status', 'contexts'}: _fail('UNSUPPORTED_SELECTION_SHAPE')
        if type(item['contexts']) not in (list, tuple): _fail('INVALID_SELECTION')
        head = row({k:v for k,v in item.items() if k != 'contexts'})
        head['contexts'] = [row(child) for child in item['contexts']]
        return head
    if 'services' in value:
        if set(value) != {'services'} or type(value['services']) is not dict: _fail('UNSUPPORTED_SELECTION_SHAPE')
        return {'services': {_identifier(k):service(v) for k,v in value['services'].items()}}
    return {_identifier(k):service(v) for k,v in value.items()}


def _document_provenance(value, ref, known_sources, contexts):
    if (type(value) is not dict or not {'capture_id', 'source_ref'} <= set(value)
            or set(value) - {'capture_id', 'source_ref', 'context_ids'}):
        _fail('INVALID_DOCUMENT_PROVENANCE')
    capture = _identifier(value['capture_id']); source = _identifier(value['source_ref'])
    if source not in known_sources | {ref}: _fail('UNKNOWN_DOCUMENT_SOURCE_REFERENCE')
    result = {'capture_id': capture, 'source_ref': source}
    if 'context_ids' in value:
        selected = _identifiers(value['context_ids'])
        if selected != contexts: _fail('DOCUMENT_SELECTION_MISMATCH')
        result['context_ids'] = selected
    return result

def _cost(result):
    text = canonical(result); size = len(text.encode('utf-8'))
    return {'characters': len(text), 'utf8_bytes': size, 'tokens': (size + 3) // 4}



def _budget_status(budget, overflow):
    # Fixed serialized width prevents false/true and null/reason from making
    # their own boundary predicate oscillate. Padding is public and accounted.
    budget['over_budget'] = overflow
    budget['reason'] = 'MANDATORY_IDENTITY_AND_COVERAGE' if overflow else None
    width = len(canonical({'over_budget': True, 'reason': 'MANDATORY_IDENTITY_AND_COVERAGE'}))
    used = len(canonical({'over_budget': overflow, 'reason': budget['reason']}))
    budget['status_padding'] = ' ' * (width - used)


def _settle(result, mandatory=None, *, enforce_hard=True):
    # Costs account for themselves, omission metadata and the complete template.
    # Hash placeholders have the same fixed width as the final canonical hash.
    budget = result['packet']['budget']
    _budget_status(budget, False)
    for _ in range(32):
        before = canonical(budget)
        cost = _cost(result)
        budget['actual_cost'] = cost
        budget['mandatory_cost'] = cost if mandatory is None else mandatory
        overflow = cost['tokens'] > budget['token_budget'] or cost['characters'] > budget['char_budget']
        _budget_status(budget, overflow)
        if canonical(budget) == before:
            if enforce_hard and cost['characters'] > HARD_PACKET_CHAR_LIMIT: _fail('PACKET_HARD_LIMIT')
            return cost
    _fail('PACKET_ACCOUNTING_LIMIT')


def _omission(category, identity, field, value):
    return {'category': category, 'id': identity, 'field': field,
            'reason': 'UNTRUSTED_TEXT', 'content_hash': digest(value)}


def _documents(documents, scope, context_ids, known_sources):
    if type(documents) not in (list, tuple) or len(documents) > 256:
        _fail('INVALID_DOCUMENTS')
    bindings = []; summaries = []; omissions = []; inputs = []; refs = set()
    required = {'ref', 'format', 'content_hash', 'scope', 'context_ids', 'selection_provenance'}
    for document in documents:
        if (type(document) is not dict or not required <= set(document)
                or set(document) - required - {'content'}): _fail('INVALID_DOCUMENT')
        ref = _identifier(document['ref'])
        if ref in refs: _fail('DUPLICATE_DOCUMENT')
        refs.add(ref)
        contexts = _identifiers(document['context_ids'])
        if document['scope'] != scope or not set(contexts) <= set(context_ids):
            _fail('DOCUMENT_SELECTION_MISMATCH')
        if type(document['format']) is not str or document['format'] not in _FORMATS:
            _fail('UNSUPPORTED_DOCUMENT_FORMAT')
        h = document['content_hash']
        if type(h) is not str or re.fullmatch('[0-9a-f]{64}', h) is None: _fail('INVALID_DOCUMENT_HASH')
        if 'content' in document:
            content = document['content']
            if type(content) is not str or hashlib.sha256(content.encode('utf-8')).hexdigest() != h:
                _fail('DOCUMENT_CONTENT_MISMATCH')
        provenance = _document_provenance(document['selection_provenance'], ref, known_sources, contexts)
        bindings.append({'ref': ref, 'content_hash': h, 'scope': scope, 'context_ids': contexts,
            'hash_status': 'CONTENT_VERIFIED' if 'content' in document else 'SUPPLIED_NOT_REVERIFIED',
            'capture_hash': digest({**document, 'context_ids': contexts})})
        summaries.append({'ref': ref, 'format': document['format'], 'selection_provenance': provenance,
                          'text_included': False})
        omissions.append({'category': 'document_text', 'id': ref, 'field': 'content',
                          'reason': 'UNTRUSTED_TEXT', 'content_hash': h})
        omissions.append({'category': 'document_summary', 'id': ref, 'reason': 'BUDGET', 'content_hash': h})
        inputs.append({'ref': ref, 'hash': digest({**document, 'context_ids': contexts})})
    return (sorted(bindings, key=lambda d: d['ref']), sorted(summaries, key=lambda d: d['ref']),
            omissions, sorted(inputs, key=lambda d: d['ref']))


def prepare_process_label_packet(process, *, documents=(), conflicts=(), token_budget=8000, char_budget=32000):
    """Return deterministic {packet, candidate_template} from explicit input only.

    Budget overflow never truncates validation IDs. Mandatory overflow is explicit;
    hard bounds fail without returning an artifact. Raw text is hash-bound/omitted.
    The template is a proposal contract, not an applied or approved ProcessView.
    """
    if (type(token_budget) is not int or not 1 <= token_budget <= 500_000
            or type(char_budget) is not int or not 1 <= char_budget <= 2_000_000):
        _fail('INVALID_PACKET_BUDGET')
    raw = process._document if type(process) is ProcessView else process
    _bounded([raw, documents, conflicts])
    try:
        model = ProcessView.from_dict(raw)
        value = model.to_dict(include_generation_metadata=False)
        content_hash = model.content_fingerprint
        technical_hash = model.technical_fingerprint
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        # Shared validators may include raw object keys in their exception paths.
        # Never copy their messages, diagnostic payloads or exception chain.
        _fail('INVALID_PROCESS_DOCUMENT')
    definition = value['definition']; view = value['technical_view']
    process_id = _identifier(value['process_id']); scope = _identifier(definition['scope'])
    contexts = _identifiers(definition['context_ids'])
    identity = {'process_id': process_id, 'revision': value['revision'], 'scope': scope,
        'context_ids': contexts, 'context_selection': _context_selection(definition['context_selection'], scope, contexts),
        'context_selection_hash': digest(definition['context_selection']),
        'baseline_fingerprint': _identifier(definition['baseline_fingerprint']),
        'definition_fingerprint': value['definition_fingerprint'],
        'technical_fingerprint': technical_hash, 'process_content_hash': content_hash}
    inventory = []; source_refs = {process_id}; targets = {process_id}; omissions = []
    uncertain = set(); truncated = view['coverage'].get('truncated') is True
    for collection, category in [('nodes', 'step'), ('edges', 'transition')]:
        for item in view[collection]:
            ref = _identifier(item['id']); targets.add(ref)
            originals = _identifiers(item['original_ids']); proofs = _identifiers(item['evidence_refs'])
            source_refs.update([ref, *originals, *proofs])
            attrs = item['attributes']
            row = {'id': ref, 'category': category, 'original_ids': originals, 'evidence_refs': proofs,
                'scope': scope, 'context_ids': _identifiers(attrs['context_ids']),
                'evidence_kinds': sorted(item['evidence_kinds']),
                'resolution_status': item['resolution_status'], 'freshness': item['freshness'],
                'supporting_refs': _identifiers(item['supporting_refs']),
                'contradicting_refs': _identifiers(item['contradicting_refs']),
                'unknown_refs': _identifiers(item['unknown_refs'])}
            if category == 'step':
                row['kind'] = item['kind']
                row['owner_id'] = _identifier(item['owner_id']) if item.get('owner_id') is not None else None
            else:
                row.update(source=_identifier(item['source']), target=_identifier(item['target']), relation=item['relation'])
            inventory.append(row)
            if (item['resolution_status'] != 'RESOLVED' or item['freshness'] != 'CURRENT'
                    or item.get('kind') in _BOUNDARIES or 'boundary_reason' in attrs): uncertain.add(ref)
            truncated = truncated or attrs.get('truncated') is True
            omissions.append(_omission('technical_text', ref, 'attributes', attrs))
            if 'label' in item: omissions.append(_omission('technical_text', ref, 'label', item['label']))
    evidence = []; original_refs = set()
    for proof in view['provenance']:
        ref = _identifier(proof['id']); source_refs.add(ref)
        row = {'id': ref, 'scope': scope, 'context_ids': _identifiers(proof['context_ids']),
            'evidence_kind': proof['evidence_kind'] if proof['evidence_kind'] in EVIDENCE_KINDS else 'UNKNOWN',
            'polarity': proof['polarity'] if proof['polarity'] in EVIDENCE_POLARITIES else 'UNKNOWN',
            'freshness': proof['freshness'] if proof['freshness'] in FRESHNESS_STATUSES else 'UNKNOWN'}
        if proof.get('source_id') is not None:
            row['source_ref'] = _identifier(proof['source_id']); source_refs.add(row['source_ref'])
        if proof.get('original_id') is not None:
            row['original_id'] = _identifier(proof['original_id']); original_refs.add(row['original_id'])
        for field in ('original_ids', 'original_evidence_ids', 'compiler_evidence_ids'):
            if field in proof:
                row[field] = _identifiers(proof[field]); original_refs.update(row[field])
        if type(proof.get('confidence_score')) in (int, float) and 0 <= proof['confidence_score'] <= 1:
            row['confidence_score'] = proof['confidence_score']
        evidence.append(row); omissions.append(_omission('evidence_payload', ref, 'payload', proof))
    source_refs.update(targets)
    bindings, summaries, doc_omissions, doc_inputs = _documents(documents, scope, contexts, source_refs)
    doc_refs = {d['ref'] for d in bindings}
    if doc_refs & source_refs: _fail('DOCUMENT_REFERENCE_COLLISION')
    if type(conflicts) not in (list, tuple) or len(conflicts) > 1024: _fail('INVALID_DOCUMENT_CONFLICTS')
    captured_conflicts = []
    for conflict in conflicts:
        if type(conflict) is not dict or set(conflict) != {'document_ref', 'target_id', 'source_refs', 'status'}:
            _fail('INVALID_DOCUMENT_CONFLICT')
        _identifier(conflict['document_ref']); _identifier(conflict['target_id'])
        if (type(conflict['status']) is not str or conflict['status'] not in {'CONFLICT', 'UNKNOWN'}
                or conflict['document_ref'] not in doc_refs or conflict['target_id'] not in targets):
            _fail('INVALID_DOCUMENT_CONFLICT')
        refs = _identifiers(conflict['source_refs'])
        if not refs or not set(refs) <= source_refs: _fail('INVALID_DOCUMENT_CONFLICT')
        captured_conflicts.append({**conflict, 'source_refs': refs})
    omissions += doc_omissions
    omissions.append(_omission('selection_payload', process_id, 'context_selection', definition['context_selection']))
    for field in ['diagnostics', 'limits', 'coverage']:
        omissions.append(_omission('coverage_text', process_id, field, view[field]))
    omissions.append(_omission('semantic_text', process_id, 'semantic_annotations', value['semantic_annotations']))
    zero = {'characters': 0, 'utf8_bytes': 0, 'tokens': 0}
    packet = {'schema_version': 1, 'rules_version': VERSION, 'identity': identity,
        'allowed_target_ids': sorted(targets), 'allowed_source_refs': sorted(source_refs | doc_refs),
        'original_reference_ids': sorted(original_refs),
        'entry_ids': _identifiers(value['entry_ids']), 'exit_ids': _identifiers(value['exit_ids']),
        'outcome_ids': _identifiers(value['outcome_ids']), 'technical_status': value['technical_status'],
        'technical_inventory': sorted(inventory, key=lambda row: row['id']),
        'evidence_summaries': sorted(evidence, key=lambda row: row['id']),
        'uncertainty': {'target_ids': sorted(uncertain), 'truncated': truncated,
                        'diagnostic_count': len(view['diagnostics']), 'coverage_hash': digest(view['coverage'])},
        'document_bindings': bindings, 'document_summaries': [],
        'documentation_comparison': 'NOT_EVALUATED',
        'captured_conflicts': sorted(captured_conflicts, key=canonical),
        'input_binding_hash': digest({'process': content_hash, 'documents': doc_inputs,
                                     'conflicts': sorted(captured_conflicts, key=canonical)}),
        'annotation_schema': {'allowed_fields': sorted(ANNOTATION_FIELDS),
            'mutable_fields': ['description', 'grouping_proposal', 'label', 'source_refs'],
            'required_fields': ['id', 'target_id', 'source_refs', 'semantic_review_status'],
            'fixed_semantic_review_status': 'PROPOSED',
            'grouping_target_ids': sorted(item['id'] for item in view['nodes'])},
        'omitted': sorted(omissions, key=canonical),
        'budget': {'token_budget': token_budget, 'char_budget': char_budget,
            'estimator': 'ceil(canonical_UTF8_bytes/4)', 'mandatory_cost': zero.copy(),
            'actual_cost': zero.copy(), 'over_budget': False, 'reason': None},
        'packet_hash': '0' * 64}
    result = {'packet': packet, 'candidate_template': {'schema_version': 1, 'packet_hash': '0' * 64, 'annotations': []}}
    mandatory = _settle(result)
    if not packet['budget']['over_budget']:
        for summary in summaries:
            trial = deepcopy(result)
            trial_packet = trial['packet']; trial_packet['document_summaries'].append(summary)
            trial_packet['omitted'] = [row for row in trial_packet['omitted']
                if not (row['category'] == 'document_summary' and row['id'] == summary['ref'])]
            trial_cost = _settle(trial, mandatory, enforce_hard=False)
            if not trial_packet['budget']['over_budget'] and trial_cost['characters'] <= HARD_PACKET_CHAR_LIMIT:
                result = trial
    _settle(result, mandatory)
    packet = result['packet']; packet['packet_hash'] = digest({k: v for k, v in packet.items() if k != 'packet_hash'})
    result['candidate_template']['packet_hash'] = packet['packet_hash']
    return result


ANNOTATION_VALIDATION_VERSION = 'process-annotation-validation-1'


def _proposal_text(value, limit, *, description=False):
    if type(value) is not str or not value.strip() or len(value) > limit:
        _fail('INVALID_ANNOTATION_TEXT')
    if (any(unicodedata.category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'}
            and not (description and char in '\n\t') for char in value)
            or _CREDENTIAL.search(value) is not None or _AUTH_TOKEN.search(value) is not None
            or _URI_USERINFO.search(value) is not None):
        _fail('UNSAFE_ANNOTATION_TEXT')
    return value


def _proposal_refs(value, allowed, *, grouping=False):
    if type(value) is not list: _fail('INVALID_ANNOTATION_REFERENCES')
    refs = [_identifier(ref) for ref in value]
    if len(set(refs)) != len(refs): _fail('DUPLICATE_ANNOTATION_REFERENCE')
    if grouping and not refs: _fail('EMPTY_GROUPING_PROPOSAL')
    if not set(refs) <= allowed:
        _fail('INVALID_GROUPING_REFERENCE' if grouping else 'INVALID_ANNOTATION_SOURCE')
    return sorted(refs)


def _proposed_annotations(packet, candidate):
    if type(candidate) is not dict or set(candidate) != {'schema_version', 'packet_hash', 'annotations'}:
        _fail('INVALID_CANDIDATE_SCHEMA')
    if type(candidate['schema_version']) is not int or candidate['schema_version'] != 1:
        _fail('UNSUPPORTED_CANDIDATE_VERSION')
    if (type(candidate['packet_hash']) is not str
            or re.fullmatch('[0-9a-f]{64}', candidate['packet_hash']) is None
            or candidate['packet_hash'] != packet['packet_hash']):
        _fail('CANDIDATE_PACKET_MISMATCH')
    annotations = candidate['annotations']
    if type(annotations) is not list or len(annotations) > 256: _fail('INVALID_ANNOTATION_COLLECTION')
    schema = packet['annotation_schema']; targets = set(packet['allowed_target_ids'])
    sources = set(packet['allowed_source_refs']); groups = set(schema['grouping_target_ids'])
    seen = set(); result = []
    for annotation in annotations:
        if (type(annotation) is not dict or set(annotation) - set(schema['allowed_fields'])
                or not set(schema['required_fields']) <= set(annotation)):
            _fail('INVALID_ANNOTATION_SCHEMA')
        identity = _identifier(annotation['id']); target = _identifier(annotation['target_id'])
        if identity in seen or identity in targets: _fail('ANNOTATION_ID_COLLISION')
        if target not in targets: _fail('INVALID_ANNOTATION_TARGET')
        seen.add(identity)
        if annotation['semantic_review_status'] != 'PROPOSED': _fail('INVALID_PROPOSAL_STATUS')
        if not {'label', 'description', 'grouping_proposal'} & set(annotation): _fail('EMPTY_ANNOTATION')
        item = {'id': identity, 'target_id': target,
                'semantic_review_status': 'PROPOSED',
                'source_refs': _proposal_refs(annotation['source_refs'], sources)}
        if 'label' in annotation: item['label'] = _proposal_text(annotation['label'], 512)
        if 'description' in annotation:
            item['description'] = _proposal_text(annotation['description'], 4096, description=True)
        if 'grouping_proposal' in annotation:
            item['grouping_proposal'] = _proposal_refs(annotation['grouping_proposal'], groups, grouping=True)
        result.append(item)
    return sorted(result, key=lambda item: item['id'])


def _annotation_validation_report(packet=None, annotations=(), code=None):
    # Only a completely rederived packet and fully validated proposals reach here.
    # Invalid input never returns partially normalized annotations or raw errors.
    items = []
    if packet is not None:
        for conflict in packet['captured_conflicts']:
            items.append({'kind': 'CAPTURED_DOCUMENT_CONFLICT' if conflict['status'] == 'CONFLICT'
                          else 'CAPTURED_DOCUMENT_UNKNOWN', **deepcopy(conflict)})
    if code is None:
        by_target = {}
        for annotation in annotations:
            by_target.setdefault(annotation['target_id'], []).append(annotation)
            base = {'annotation_ids': [annotation['id']], 'target_id': annotation['target_id'],
                    'source_refs': list(annotation['source_refs'])}
            items.append({'kind': 'PROPOSAL_REQUIRES_REVIEW', **base})
            if not annotation['source_refs']: items.append({'kind': 'PROPOSAL_HAS_NO_CITATIONS', **base})
            if 'grouping_proposal' in annotation: items.append({'kind': 'GROUPING_REQUIRES_REVIEW', **base})
        for target, proposals in by_target.items():
            fields = [field for field in ('description', 'grouping_proposal', 'label')
                      if len({canonical(a[field]) for a in proposals if field in a}) > 1]
            if fields:
                items.append({'kind': 'CONFLICTING_TARGET_PROPOSALS', 'target_id': target,
                    'annotation_ids': sorted(a['id'] for a in proposals), 'fields': fields})
    conflict = any(item['kind'] in {'CAPTURED_DOCUMENT_CONFLICT', 'CONFLICTING_TARGET_PROPOSALS'} for item in items)
    return {'schema_version': 1, 'rules_version': ANNOTATION_VALIDATION_VERSION,
        'valid': code is None, 'validation_status': 'VALID' if code is None else 'REJECTED',
        'review_status': 'CONFLICT' if conflict else 'PENDING', 'requires_review': True,
        'packet_hash': packet['packet_hash'] if packet is not None else None,
        'technical_binding': deepcopy(packet['identity']) if packet is not None else None,
        'technical_status': packet['technical_status'] if packet is not None else None,
        'uncertainty': deepcopy(packet['uncertainty']) if packet is not None else None,
        'documentation_comparison': 'NOT_EVALUATED',
        'annotations': deepcopy(list(annotations)) if code is None else [],
        'diagnostics': [] if code is None else [{'code': code}],
        'review_items': sorted(items, key=canonical)}


def validate_process_annotations(process, packet, candidate, *, documents=(), conflicts=()):
    """Pure T031 validation; valid never means approved, applied or observed.

    Expected malformed/stale/unsafe inputs return a fixed-code REJECTED report.
    No input values or shared-validator errors are reflected in diagnostics.
    Programmer/infrastructure exceptions outside this validation are not masked.
    """
    trusted = None
    try:
        raw = process._document if type(process) is ProcessView else process
        _bounded([raw, packet, candidate, documents, conflicts])
        if type(packet) is not dict: _fail('INVALID_PACKET_SCHEMA')
        if (type(packet.get('schema_version')) is not int or packet['schema_version'] != 1
                or packet.get('rules_version') != VERSION): _fail('UNSUPPORTED_PACKET_VERSION')
        if type(packet.get('budget')) is not dict: _fail('INVALID_PACKET_BUDGET')
        expected = prepare_process_label_packet(process, documents=documents, conflicts=conflicts,
            token_budget=packet['budget'].get('token_budget'), char_budget=packet['budget'].get('char_budget'))['packet']
        if canonical(packet) != canonical(expected): _fail('PACKET_REDERIVATION_MISMATCH')
        trusted = expected
        return _annotation_validation_report(trusted, _proposed_annotations(trusted, candidate))
    except ProcessLabelPacketError as error:
        return _annotation_validation_report(trusted, code=error.diagnostic['code'])
    except UnicodeError:
        # Invalid UTF-8 content is malformed data; do not expose codec details.
        return _annotation_validation_report(trusted, code='INVALID_UNICODE_INPUT')

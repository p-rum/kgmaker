"""Lossless static business-step projection of existing certified process inputs.

No compiler, graph loader, resolver, filesystem or runtime observation is invoked.
CURRENT is supplied input evidence, not a claim about a physical checkout.
"""
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy

from .analysis_model import digest
from .local_operations import VERSION as OPERATION_VERSION, _BASE, _original_proof, _range, _TYPES
from .process_model import ProcessView
from .views import _summarize_view_evidence

VERSION = 'business-steps-1'
_GROUP = 'business_group'


class BusinessProcessError(ValueError):
    def __init__(self, code, message):
        self.diagnostic = {'code': code, 'message': message}
        super().__init__(code + ': ' + message)


def _fail(message):
    raise BusinessProcessError('INVALID_BUSINESS_PROCESS', message)


def _bounded(value):
    # Account repeated/shared objects per occurrence, detect cycles before copy
    # or JSON validation. Bounds apply equally to nested expansion metadata.
    stack = [(value, 0, False)]; active = set(); count = size = 0
    while stack:
        item, depth, leaving = stack.pop()
        container = isinstance(item, (Mapping, list, tuple))
        if leaving:
            active.remove(id(item)); continue
        count += 1
        if count > 500_000 or depth > 80:
            _fail('Input structure budget exceeded')
        if isinstance(item, str):
            size += len(item)
            if size > 32_000_000:
                _fail('Input text budget exceeded')
        if container:
            if id(item) in active:
                _fail('Cyclic input metadata')
            if len(item) > 50_000:
                _fail('Input collection budget exceeded')
            active.add(id(item)); stack.append((item, depth, True))
            children = item.items() if isinstance(item, Mapping) else enumerate(item)
            for key, child in children:
                if isinstance(item, Mapping) and not isinstance(key, str):
                    _fail('Object keys must be strings')
                if isinstance(item, Mapping):
                    size += len(key)
                    if size > 32_000_000: _fail('Input text budget exceeded')
                stack.append((child, depth + 1, False))


def _document(value):
    raw = value._document if isinstance(value, ProcessView) else value
    _bounded(raw)
    result = ProcessView.from_dict(raw).to_dict()
    if len(result['technical_view']['nodes']) > 10_000 or len(result['technical_view']['edges']) > 30_000:
        _fail('Process topology budget exceeded')
    return result


def _cyclic(nodes, edges):
    """Iterative SCC walk over the supplied topology, including non-normal edges."""
    forward = defaultdict(list); reverse = defaultdict(list)
    for e in edges:
        forward[e['source']].append(e['target']); reverse[e['target']].append(e['source'])
    visited = set(); order = []
    for root in nodes:
        if root in visited: continue
        stack = [(root, False)]
        while stack:
            node, done = stack.pop()
            if done:
                order.append(node); continue
            if node in visited: continue
            visited.add(node); stack.append((node, True))
            stack.extend((n, False) for n in forward[node] if n not in visited)
    visited.clear(); cyclic = set()
    for root in reversed(order):
        if root in visited: continue
        component = []; pending = [root]; visited.add(root)
        while pending:
            node = pending.pop(); component.append(node)
            for n in reverse[node]:
                if n not in visited: visited.add(n); pending.append(n)
        if len(component) > 1 or root in forward[root]: cyclic.update(component)
    return cyclic


def _operation(node, provenance):
    attrs = node['attributes']; certificate = attrs.get('local_operation')
    if certificate is None: return False
    # A present but malformed certificate is an error, not silent fallback.
    if not isinstance(certificate, dict) or set(certificate) != {
            'schema_version', 'operation', 'target_type', 'original_proof_id', 'cfg_block', 'operation_ref'}:
        _fail('Malformed local operation reference')
    refs = node['evidence_refs']
    if len(refs) != 1: _fail('Operation must reference its exact certificate')
    record = provenance[refs[0]]; proof = record.get('local_operation_proof')
    if not isinstance(proof, dict): _fail('Missing embedded operation certificate')
    try:
        original = _original_proof(proof, {'repo_id': proof.get('repo_id')})
        identity = original.pop('id')
        base = {key: original[key] for key in _BASE}
        valid = (identity == 'evidence:local-operation:' + digest(original)
            and original['operation_ref'] == 'local-operation:' + digest(base)
            and type(proof['local_operation_version']) is int and proof['local_operation_version'] == 1
            and type(certificate['schema_version']) is int and certificate['schema_version'] == 1
            and proof['rules_version'] == OPERATION_VERSION and proof['compiler_backend'] == 'javac'
            and proof['operation'] in ('LOCAL_LITERAL_ASSIGNMENT', 'LITERAL_EVALUATION')
            and isinstance(proof['target_type'], str) and proof['target_type'] in _TYPES
            and _range(proof['source_range'])
            and proof['kind'] == 'SYMBOL_RESOLVED' and proof['relation'] == 'local_computation'
            and proof['runtime_execution'] == 'NOT_OBSERVED' and proof['runtime_availability'] == 'UNKNOWN'
            and proof['source'] == proof['target'] == proof['method'] == proof['compiler_symbol_id'] == attrs['method']
            and proof['context_ids'] == [proof['context_id']] == attrs['context_ids'] == record['context_ids']
            and proof['scope'] == attrs['scope'] == record['scope']
            and proof['polarity'] == record['polarity'] == 'SUPPORTING'
            and record['evidence_kind'] == 'SYMBOL_RESOLVED'
            and record['original_relation'] == 'local_computation'
            and record['source_id'] == proof['method']
            and record['source_file'] == proof['source_file'] and record['source_range'] == proof['source_range']
            and record['content_hash'] == proof['sha256']
            and certificate['original_proof_id'] == record['original_id'] == proof['id']
            and certificate['cfg_block'] == proof['cfg_block'] and proof['cfg_block'] in node['original_ids']
            and certificate['operation_ref'] == proof['operation_ref']
            and certificate['operation'] == proof['operation'] and certificate['target_type'] == proof['target_type'])
    except (KeyError, TypeError, ValueError, AttributeError):
        _fail('Malformed or altered operation certificate')
    if not valid: _fail('Operation certificate tuple mismatch')
    pointer = proof.get('ir_path')
    if (not isinstance(pointer, list) or not pointer or len(pointer) > 150
            or any(not (isinstance(k, str) and k) and not (type(k) is int and k >= 0) for k in pointer)):
        _fail('Malformed operation IR occurrence')
    # Finally continuations remain distinct even if they share an IR proof.
    return (node['kind'] == 'basic_block' and node['resolution_status'] == 'RESOLVED'
        and node['freshness'] == record['freshness'] == 'CURRENT'
        and node['evidence_kinds'] == ['SYMBOL_RESOLVED']
        and not node['contradicting_refs'] and not node['unknown_refs']
        and not set(attrs) - {'scope', 'context_ids', 'method', 'call_site_ids', 'cfg_evidence_refs', 'local_operation'}
        and not attrs.get('call_site_ids') and not attrs.get('boundary_reason')
        and 'finally' not in pointer)


def _collapse(doc):
    view = doc['technical_view']; nodes = {n['id']: n for n in view['nodes']}
    provenance = {p['id']: p for p in view['provenance']}
    protected = set(doc['entry_ids'] + doc['exit_ids'] + doc['outcome_ids'])
    for annotation in doc['semantic_annotations']:
        protected.add(annotation['target_id']); protected.update(annotation.get('grouping_proposal', []))
    cyclic = _cyclic(nodes, view['edges'])
    eligible = {n['id'] for n in nodes.values() if _operation(n, provenance)} - protected - cyclic
    incoming = defaultdict(list); outgoing = defaultdict(list)
    for edge in view['edges']:
        incoming[edge['target']].append(edge); outgoing[edge['source']].append(edge)
    # Any exceptional/boundary edge touching an operation blocks grouping it.
    def normal(edge):
        return (edge['relation'] == 'normal' and edge['freshness'] == 'CURRENT'
            and not set(edge['attributes']) - {'scope', 'context_ids', 'loop_back'}
            and edge['attributes'].get('loop_back', False) is False)
    eligible = {n for n in eligible if len(incoming[n]) == len(outgoing[n]) == 1
        and all(normal(e) for e in incoming[n] + outgoing[n])}
    following = {}; previous = {}
    for node in sorted(eligible):
        if len(outgoing[node]) != 1: continue
        edge = outgoing[node][0]; target = edge['target']
        if target not in eligible or len(incoming[target]) != 1: continue
        first, second = nodes[node], nodes[target]
        if (first['owner_id'] != second['owner_id'] or any(
                first['attributes'].get(k) != second['attributes'].get(k) for k in ('method', 'scope', 'context_ids'))):
            continue
        following[node] = target; previous[target] = node
    groups = []
    for start in sorted(eligible - set(previous)):
        chain = [start]
        while chain[-1] in following: chain.append(following[chain[-1]])
        if len(chain) >= 2: groups.append(chain)
    replacements = {}; removed_edges = set(); actions = []
    for chain in groups:
        members = set(chain)
        internals = [outgoing[n][0] for n in chain[:-1]]
        incident = {e['id']: e for n in chain for e in incoming[n] + outgoing[n]}
        external = [e for _, e in sorted(incident.items()) if (e['source'] in members) != (e['target'] in members)]
        origins = [nodes[n] for n in chain]
        payload = {'version': VERSION, 'nodes': deepcopy(origins), 'edges': deepcopy(internals),
                   'external_edges': deepcopy(external)}
        identity = 'business-step:' + digest(payload)
        if identity in nodes: _fail('Generated business identity collision')
        refs = sorted({ref for n in origins + internals for ref in n['evidence_refs']})
        summary = _summarize_view_evidence(refs, provenance)
        action = deepcopy(origins[0]); action.update(id=identity, kind='action', label='Local computations',
            original_ids=sorted({i for n in origins + internals for i in n['original_ids']}),
            evidence_refs=refs, **summary)
        # Even resolved local computation is joined only by static CFG adjacency.
        action['resolution_status'] = 'UNRESOLVED'
        action['attributes'] = {k: deepcopy(origins[0]['attributes'][k]) for k in ('method', 'scope', 'context_ids')}
        action['attributes'][_GROUP] = payload
        actions.append(action); replacements.update({n: identity for n in chain})
        removed_edges.update(e['id'] for e in internals)
    view['nodes'] = [n for n in view['nodes'] if n['id'] not in replacements] + actions
    view['edges'] = [dict(e, source=replacements.get(e['source'], e['source']),
        target=replacements.get(e['target'], e['target'])) for e in view['edges'] if e['id'] not in removed_edges]
    return ProcessView.from_dict(doc)


def _expand_impl(doc, expected_document):
    view = doc['technical_view']; groups = [n for n in view['nodes'] if _GROUP in n['attributes']]
    if not groups: return ProcessView.from_dict(doc)
    group_ids = {n['id'] for n in groups}; origin_nodes = {}; internal_edges = {}; external_edges = {}
    member_group = {}
    for group in groups:
        payload = group['attributes'][_GROUP]
        if (not isinstance(payload, dict) or set(payload) != {'version', 'nodes', 'edges', 'external_edges'}
                or payload['version'] != VERSION or any(not isinstance(payload[k], list) for k in ('nodes', 'edges', 'external_edges'))
                or len(payload['nodes']) < 2 or len(payload['edges']) != len(payload['nodes']) - 1
                or group['id'] != 'business-step:' + digest(payload)):
            _fail('Unsupported or altered business group')
        for node in payload['nodes']:
            if not isinstance(node, dict) or not isinstance(node.get('id'), str) or node['id'] in origin_nodes:
                _fail('Duplicate or malformed origin node')
            if _GROUP in node.get('attributes', {}): _fail('Nested business group')
            origin_nodes[node['id']] = node; member_group[node['id']] = group['id']
        for key, collection in [('edges', internal_edges), ('external_edges', external_edges)]:
            for edge in payload[key]:
                if not isinstance(edge, dict) or not isinstance(edge.get('id'), str): _fail('Malformed origin edge')
                prior = collection.get(edge['id'])
                if prior is not None and (key == 'edges' or prior != edge): _fail('Conflicting origin edge')
                collection[edge['id']] = edge
    remaining = [n for n in view['nodes'] if n['id'] not in group_ids]
    if set(origin_nodes) & {n['id'] for n in remaining}: _fail('Origin node identity collision')
    restored = []
    for edge in view['edges']:
        original = external_edges.pop(edge['id'], None)
        if original is not None:
            expected = dict(original, source=member_group.get(original['source'], original['source']),
                            target=member_group.get(original['target'], original['target']))
            if edge != expected: _fail('Altered external transition')
            restored.append(original)
        elif edge['source'] in group_ids or edge['target'] in group_ids:
            _fail('Unrecorded external transition')
        else: restored.append(edge)
    if external_edges or set(internal_edges) & {e['id'] for e in restored}: _fail('Lost or duplicate transition')
    view['nodes'] = remaining + list(origin_nodes.values()); view['edges'] = restored + list(internal_edges.values())
    expanded = ProcessView.from_dict(doc)
    # Revalidate membership/order/proofs/summary, rather than trusting a digest
    # supplied together with arbitrary grouping metadata.
    if _collapse(expanded.to_dict()).to_dict() != ProcessView.from_dict(expected_document).to_dict():
        _fail('Business group does not match deterministic supported projection')
    return expanded


def _public(value, expand):
    try:
        doc = _document(value)
        if expand:
            result = _expand_checked(doc)
            _bounded(result._document)
            return result
        if any(_GROUP in n['attributes'] for n in doc['technical_view']['nodes']):
            _expand_checked(deepcopy(doc))
            return ProcessView.from_dict(doc)
        result = _collapse(doc)
        _bounded(result._document)
        return result
    except BusinessProcessError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as error:
        raise BusinessProcessError('INVALID_BUSINESS_PROCESS', 'Invalid process projection input') from error


def _expand_checked(doc):
    # Pass the immutable expected projection explicitly through the comparison.
    expected = deepcopy(doc)
    return _expand_impl(doc, expected)


def collapse_business_steps(process):
    """Group maximal certified acyclic chains; no input mutation or I/O."""
    return _public(process, False)


def expand_business_steps(process):
    """Restore the canonical technical document exactly, validating group records."""
    return _public(process, True)

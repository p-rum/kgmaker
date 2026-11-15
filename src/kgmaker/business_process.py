"""Lossless static business-step projection of existing certified process inputs.

No compiler, graph loader, resolver, filesystem or runtime observation is invoked.
CURRENT is supplied input evidence, not a claim about a physical checkout.
"""
from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy

from .analysis_model import digest
from .architecture_model import ViewDocument, ViewEdge, ViewNode
from .local_operations import VERSION as OPERATION_VERSION, _BASE, _original_proof, _range, _TYPES
from .process_model import ProcessView
from .remote_interfaces import VERSION as REMOTE_VIEW_VERSION
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


def project_http_process_boundary(local_process, remote_interfaces, *, target_processes=()):
    """Join a local ProcessView to only its explicitly bound HTTP target.

    The remote T014 view is the authority for the source callsite, release,
    target service/context and candidate status. Target ProcessViews are
    caller-supplied snapshots. Missing or ambiguous target CFG stays an
    external service boundary; original local transitions are retained.
    """
    try:
        if not isinstance(target_processes, (list, tuple)):
            _fail('HTTP_BOUNDARY_INVALID_TARGETS')
        local = ProcessView.from_dict(_document(local_process))
        remote = ViewDocument.from_dict(remote_interfaces.to_dict() if isinstance(remote_interfaces, ViewDocument)
                                       else deepcopy(remote_interfaces))
        targets = [ProcessView.from_dict(_document(value)) for value in target_processes]
        if remote.rules_version != REMOTE_VIEW_VERSION:
            _fail('HTTP_BOUNDARY_UNSUPPORTED_REMOTE_VERSION')
        if remote.kind != 'topology' or remote.scope != local.definition.scope:
            _fail('HTTP_BOUNDARY_SCOPE_OR_KIND_MISMATCH')
        local_doc = local.to_dict()
        technical = deepcopy(local_doc['technical_view'])
        existing_nodes = {row['id']: row for row in technical['nodes']}
        existing_edges = {row['id']: row for row in technical['edges']}
        provenance = {row['id']: row for row in technical['provenance']}
        remote_nodes = {node.id: node for node in remote.nodes}
        local_contexts = set(local.to_dict()['definition']['context_ids'])
        local_definition = local.to_dict()['definition']
        service_selections = deepcopy(local_definition['context_selection'].get('services', {}))
        all_contexts = set(local_contexts)
        matched_call_sites = set()
        diagnostics = list(technical['diagnostics']) + deepcopy(list(remote.diagnostics))
        limits = list(technical['limits']) + list(remote.limits)
        truncated = technical['coverage'].get('truncated') is True or remote.coverage.get('truncated') is True
        upstream_coverage = [{'kind': 'remote_interfaces', 'view_id': remote.view_id,
            'fingerprint': remote.content_fingerprint, 'coverage': deepcopy(remote.coverage)}]

        def selection_matches(selection, service, context, *, required=False):
            if selection.get('scope', local.definition.scope) != local.definition.scope:
                return False
            row = selection.get('services', {}).get(service)
            if row is None:
                return not required
            return (row.get('scope') == local.definition.scope
                and any(item.get('context_id') == context
                    and item.get('scope', local.definition.scope) == local.definition.scope
                    and item.get('freshness') != 'STALE' and item.get('status') != 'STALE'
                    for item in row.get('contexts', [])))

        def add_proof(proof):
            prior = provenance.get(proof['id'])
            if prior is not None and prior != proof:
                _fail('HTTP_BOUNDARY_PROOF_COLLISION')
            provenance[proof['id']] = deepcopy(proof)

        for remote_edge in remote.edges:
            if remote_edge.relation != 'remote_http_request_response':
                continue
            source = remote_nodes.get(remote_edge.source)
            target_interface = remote_nodes.get(remote_edge.target)
            if source is None or target_interface is None:
                _fail('HTTP_BOUNDARY_ENDPOINT_MISSING')
            site = source.attributes.get('origin_call_site')
            if (source.kind != 'http_interface' or source.attributes.get('direction') != 'CONSUMER'
                    or not isinstance(site, str) or source.resolution_status != 'RESOLVED'
                    or source.attributes.get('scope') != local.definition.scope
                    or source.attributes.get('context_id') not in local_contexts):
                continue
            call_nodes = [node for node in technical['nodes']
                if site in node['attributes'].get('call_site_ids', [])
                or node['attributes'].get('call_site') == site or site in node.get('original_ids', [])]
            call_edges = [edge for edge in technical['edges']
                if edge['attributes'].get('call_site') == site or site in edge.get('original_ids', [])]
            if len(call_nodes) != 1 or not call_edges or site in matched_call_sites:
                continue
            matched_call_sites.add(site)
            attrs = remote_edge.attributes
            candidate = attrs if (attrs.get('target_interface_id') == target_interface.id
                and attrs.get('target_service_id') == target_interface.attributes.get('service_id')
                and target_interface.attributes.get('context_id') in attrs.get('context_ids', [])) else None
            site_edges = [edge for edge in remote.edges if edge.relation == 'remote_http_request_response'
                and edge.source == source.id]
            if remote_edge.resolution_status == 'AMBIGUOUS' or len(site_edges) > 1:
                matched_call_sites.add(site)
                source_context = source.attributes['context_id']
                target_contexts = sorted({ctx for edge in site_edges
                    for ctx in edge.attributes.get('context_ids', []) if ctx != source_context})
                contexts = sorted({source_context, *target_contexts})
                refs = tuple(sorted({ref for edge in site_edges for ref in edge.evidence_refs}))
                remote_proofs = {proof['id']: proof for proof in remote.provenance}
                for ref in refs:
                    if ref in remote_proofs: add_proof(remote_proofs[ref])
                candidates = []
                for edge in site_edges:
                    target_node = remote_nodes.get(edge.target)
                    if target_node:
                        candidates.append({'interface_id': target_node.id,
                            'service_id': edge.attributes.get('target_service_id'),
                            'release_id': edge.attributes.get('target_release_id'),
                            'context_ids': list(edge.attributes.get('context_ids', [])),
                            'mapping_id': edge.attributes.get('mapping_id')})
                boundary_id = 'http-boundary:' + digest([local.definition.process_id, source.id, site,
                    sorted(edge.id for edge in site_edges)])
                boundary = ViewNode(boundary_id, 'service_boundary', 'Ambiguous HTTP remote boundary',
                    original_ids=tuple(sorted({site, source.id, *(edge.id for edge in site_edges)})),
                    evidence_refs=refs, attributes={'scope': local.definition.scope, 'context_ids': contexts,
                        'binding_id': attrs.get('binding_id'), 'source_call_site': site,
                        'target_candidates': candidates, 'boundary_reason': 'AMBIGUOUS_REMOTE_BINDING',
                        'request_response': 'HTTP_REQUEST_RESPONSE', 'error_semantics': 'TRANSPORT_BOUNDARY_ONLY',
                        'runtime_execution': 'NOT_OBSERVED', 'runtime_availability': 'UNKNOWN'},
                    evidence_kinds=tuple(sorted({kind for edge in site_edges for kind in edge.evidence_kinds})),
                    resolution_status='UNRESOLVED', freshness='UNKNOWN', unknown_refs=refs)
                existing_nodes[boundary_id] = boundary.to_dict()
                local_call = call_nodes[0]['id']
                identity='http-transition:'+digest([boundary_id,local_call,'ambiguous'])
                transition=ViewEdge(identity,local_call,boundary_id,'call',
                    original_ids=tuple(sorted({local_call,site,*(edge.id for edge in site_edges)})),
                    evidence_refs=refs,attributes={'scope':local.definition.scope,'context_ids':contexts,
                        'http_transition':'REQUEST','boundary_reason':'AMBIGUOUS_REMOTE_BINDING'},
                    evidence_kinds=boundary.evidence_kinds,resolution_status='UNRESOLVED',
                    freshness='UNKNOWN',unknown_refs=refs)
                existing_edges[identity]=transition.to_dict()
                all_contexts.update(contexts)
                for item in candidates:
                    service_id=item['service_id']
                    if service_id and service_id not in service_selections:
                        service_selections[service_id]={'scope':local.definition.scope,
                            'status':'EXPLICIT_REMOTE_BINDING','contexts':[{'context_id':ctx,
                                'status':'EXPLICIT_REMOTE_BINDING'} for ctx in item['context_ids'] if ctx != source_context]}
                diagnostics.append({'code':'AMBIGUOUS_REMOTE_BINDING','boundary_id':boundary_id,
                                    'candidate_count':len(candidates)})
                continue
            binding_valid = (remote_edge.resolution_status == 'RESOLVED' and candidate is not None
                    and candidate.get('scope') == local.definition.scope
                    and candidate.get('capture_freshness') == 'CAPTURE_TIME_ONLY'
                    and remote_edge.freshness != 'STALE' and source.freshness != 'STALE'
                    and target_interface.freshness != 'STALE'
                    and target_interface.kind == 'http_interface'
                    and target_interface.attributes.get('direction') in {'PROVIDED', 'PROVIDER'}
                    and target_interface.attributes.get('scope') == local.definition.scope
                    and target_interface.resolution_status == 'RESOLVED'
                    and set(candidate.get('context_ids', [])) == {
                        source.attributes['context_id'], target_interface.attributes.get('context_id')}
                    and selection_matches(remote.context_selection, source.attributes.get('service_id'),
                        source.attributes['context_id'])
                    and selection_matches(remote.context_selection, candidate.get('target_service_id'),
                        target_interface.attributes.get('context_id')))
            source_context = source.attributes['context_id']
            context_values = (candidate or attrs).get('context_ids', [])
            target_contexts = [ctx for ctx in context_values if ctx != source_context]
            if len(target_contexts) != 1:
                continue
            target_context = target_contexts[0]
            target_service = (candidate or attrs).get('target_service_id')
            if not isinstance(target_service, str):
                continue
            matching_processes = []
            handlers = set(target_interface.attributes.get('handler_ids', [])) if binding_valid else set()
            for target_process in (targets if binding_valid else ()):
                target_definition = target_process.to_dict()['definition']
                selection = target_definition['context_selection'].get('services', {})
                service = selection.get(target_service)
                if (target_process.definition.scope != local.definition.scope
                        or target_context not in target_process.to_dict()['definition']['context_ids'] or service is None
                        or not selection_matches(target_definition['context_selection'], target_service,
                            target_context, required=True)):
                    continue
                selected = {row.get('context_id') for row in service.get('contexts', [])}
                if target_context not in selected:
                    continue
                triggers = [node for node in target_process.steps if node.kind == 'trigger'
                    and node.attributes.get('entry_symbol_id') in handlers]
                if len(triggers) == 1:
                    matching_processes.append((target_process, triggers[0]))
            selected_process = matching_processes[0] if len(matching_processes) == 1 else None
            process_has_cfg = False
            if selected_process is not None:
                tp, trigger = selected_process
                process_has_cfg = any(node.id != trigger.id and node.kind not in
                    {'trigger', 'unresolved_boundary', 'entry', 'exit', 'exceptional_exit'} for node in tp.steps)
            boundary_reason = None if process_has_cfg else ('TARGET_PROCESS_UNAVAILABLE' if binding_valid else 'REMOTE_BINDING_UNRESOLVED')
            remote_services = remote.context_selection.get('services', {})
            remote_selection = remote_services.get(target_service)
            if remote_selection is not None and selection_matches(remote.context_selection, target_service, target_context):
                service_selections[target_service] = deepcopy(remote_selection)
            elif target_service not in service_selections:
                service_selections[target_service] = {'scope': local.definition.scope,
                    'status': 'EXPLICIT_REMOTE_BINDING', 'contexts': [{'context_id': target_context,
                        'status': 'EXPLICIT_REMOTE_BINDING'}]}
            all_contexts.update((source_context, target_context))
            remote_proofs = {proof['id']: proof for proof in remote.provenance}
            refs = tuple(remote_edge.evidence_refs)
            for ref in refs:
                if ref in remote_proofs:
                    add_proof(remote_proofs[ref])
            boundary_id = 'http-boundary:' + digest([local.definition.process_id, remote_edge.id, site])
            boundary = ViewNode(boundary_id, 'service_boundary', 'HTTP request/response boundary',
                original_ids=tuple(sorted(set((site, remote_edge.id, *remote_edge.original_ids)))),
                evidence_refs=refs, attributes={'scope': local.definition.scope,
                    'context_ids': sorted(set((source_context, target_context))),
                    'binding_id': attrs.get('binding_id'), 'mapping_ids': list(attrs.get('mapping_ids', [])),
                    'source_call_site': site, 'target_interface_id': target_interface.id,
                    'target_service_id': target_service, 'target_context_id': target_context,
                    'target_release_id': (candidate or attrs).get('target_release_id'),
                    'boundary_reason': boundary_reason,
                    'request_response': 'HTTP_REQUEST_RESPONSE',
                    'error_semantics': 'TRANSPORT_BOUNDARY_ONLY',
                    'runtime_execution': 'NOT_OBSERVED', 'runtime_availability': 'UNKNOWN'},
                evidence_kinds=tuple(remote_edge.evidence_kinds), resolution_status='UNRESOLVED',
                freshness='UNKNOWN', unknown_refs=refs)
            if boundary.id in existing_nodes:
                _fail('HTTP_BOUNDARY_NODE_COLLISION')
            existing_nodes[boundary.id] = boundary.to_dict()
            local_call = call_nodes[0]['id']
            # T025 annotates call, returns_to AND exception edges with the
            # same lexical site. Only the matching call node initiates HTTP;
            # callee exits must never start another request.
            identity = 'http-transition:' + digest([boundary_id, local_call, 'request'])
            edge = ViewEdge(identity, local_call, boundary_id, 'call',
                original_ids=tuple(sorted(set((local_call, site, remote_edge.id)))),
                evidence_refs=refs, attributes={'scope': local.definition.scope,
                    'context_ids': sorted(set((source_context, target_context))),
                    'http_transition': 'REQUEST', 'binding_id': attrs.get('binding_id')},
                evidence_kinds=tuple(remote_edge.evidence_kinds), resolution_status='UNRESOLVED',
                freshness='UNKNOWN', unknown_refs=refs)
            existing_edges[identity] = edge.to_dict()
            if boundary_reason:
                diagnostics.append({'code': boundary_reason, 'boundary_id': boundary_id,
                                    'target_service_id': target_service, 'target_context_id': target_context})
                continue

            tp, trigger = selected_process
            tp_doc = tp.to_dict(); tp_view = tp_doc['technical_view']
            diagnostics.extend({**deepcopy(item), 'http_source_process_id': tp.definition.process_id,
                'http_source_revision': tp.definition.revision} for item in tp_view['diagnostics'])
            limits.extend(tp_view['limits'])
            truncated = truncated or tp_view['coverage'].get('truncated') is True
            upstream_coverage.append({'kind': 'target_process', 'process_id': tp.definition.process_id,
                'revision': tp.definition.revision, 'fingerprint': tp.content_fingerprint,
                'coverage': deepcopy(tp_view['coverage'])})
            prefix = 'http-target:' + digest([boundary_id, tp.definition.process_id, tp.definition.revision]) + ':'
            id_map = {row['id']: prefix + row['id'] for row in tp_view['nodes']}
            for proof in tp_view['provenance']:
                add_proof(proof)
            for row in tp_view['nodes']:
                clone = deepcopy(row); clone['id'] = id_map[row['id']]
                clone['attributes']['source_process_id'] = tp.definition.process_id
                clone['attributes']['source_process_revision'] = tp.definition.revision
                clone['attributes']['context_ids'] = sorted(set(clone['attributes'].get('context_ids', [])))
                if clone['id'] in existing_nodes:
                    _fail('HTTP_BOUNDARY_NODE_COLLISION')
                existing_nodes[clone['id']] = clone
            for row in tp_view['edges']:
                clone = deepcopy(row); clone['id'] = prefix + row['id']
                clone['source'] = id_map[row['source']]; clone['target'] = id_map[row['target']]
                clone['attributes']['source_process_id'] = tp.definition.process_id
                existing_edges[clone['id']] = clone
            entry = id_map.get(trigger.id)
            connect = ViewEdge('http-transition:' + digest([boundary_id, entry, 'enter']),
                boundary_id, entry, 'call', original_ids=(remote_edge.id, trigger.id),
                evidence_refs=refs, attributes={'scope': local.definition.scope,
                    'context_ids': sorted(set((source_context, target_context))),
                    'http_transition': 'TARGET_ENTRY', 'binding_id': attrs.get('binding_id')},
                evidence_kinds=tuple(remote_edge.evidence_kinds), resolution_status='UNRESOLVED',
                freshness='UNKNOWN', unknown_refs=refs)
            existing_edges[connect.id] = connect.to_dict()
            # A target exception does not prove an HTTP/client exception mapping.
            # Only a normal target exit may rejoin the original normal caller
            # continuation. Preserve local exception paths without joining them.
            normal_exits = [identity for identity in tp_doc['exit_ids']
                if next(row for row in tp_view['nodes'] if row['id'] == identity)['kind'] == 'exit']
            exceptional_exits = [identity for identity in tp_doc['exit_ids'] if identity not in normal_exits]
            if exceptional_exits:
                diagnostics.append({'code': 'HTTP_TARGET_ERROR_BOUNDARY', 'boundary_id': boundary_id,
                    'http_source_process_id': tp.definition.process_id,
                    'original_exit_ids': exceptional_exits, 'error_semantics': 'TRANSPORT_BOUNDARY_ONLY'})
            local_origins = {local_call, *call_nodes[0]['original_ids']}
            for call_edge in call_edges:
                if not (call_edge['relation'] == 'normal' and call_edge['source'] == local_call
                        or call_edge['relation'] == 'returns_to'
                        and call_edge['attributes'].get('caller_block') in local_origins):
                    continue
                continuation = call_edge['target']
                if existing_nodes[continuation]['kind'] == 'exceptional_exit':
                    continue
                for target_exit in normal_exits:
                    identity = 'http-transition:' + digest([boundary_id, target_exit, continuation, call_edge['id'], 'return'])
                    exit_edge = ViewEdge(identity, id_map[target_exit], continuation, 'returns_to',
                        original_ids=tuple(sorted((remote_edge.id, site, call_edge['id']))), evidence_refs=refs,
                        attributes={'scope': local.definition.scope,
                            'context_ids': sorted(set((source_context, target_context))),
                            'http_transition': 'RESPONSE', 'binding_id': attrs.get('binding_id'),
                            'original_continuation_id': call_edge['id'],
                            'caller_transition': deepcopy(call_edge['attributes'])},
                        evidence_kinds=tuple(remote_edge.evidence_kinds), resolution_status='UNRESOLVED',
                        freshness='UNKNOWN', unknown_refs=refs)
                    existing_edges[identity] = exit_edge.to_dict()
            all_contexts.update((source_context, target_context))
            tp_selection = tp.to_dict()['definition']['context_selection'].get('services', {})
            if target_service in tp_selection:
                service_selections[target_service] = deepcopy(tp_selection[target_service])

        # T014 represents an incompatible or wholly unresolved declaration as a
        # binding plus selector records, with no candidate edge. Keep that source
        # callsite visible as an external boundary instead of silently dropping it.
        for binding in remote.nodes:
            if binding.kind != 'remote_binding' or binding.resolution_status == 'RESOLVED':
                continue
            source = remote_nodes.get(binding.attributes.get('source_interface_id'))
            selectors = binding.attributes.get('unresolved_selectors', [])
            if source is None or not selectors or source.kind != 'http_interface':
                continue
            site = source.attributes.get('origin_call_site')
            if (not isinstance(site, str) or source.attributes.get('context_id') not in local_contexts
                    or site in matched_call_sites):
                continue
            call_nodes = [node for node in technical['nodes'] if site in node['attributes'].get('call_site_ids', [])
                or node['attributes'].get('call_site') == site or site in node.get('original_ids', [])]
            call_edges = [edge for edge in technical['edges'] if edge['attributes'].get('call_site') == site
                or site in edge.get('original_ids', [])]
            if len(call_nodes) != 1 or not call_edges:
                continue
            selector = selectors[0]
            target_context = selector.get('context_id')
            target_service = selector.get('service_id')
            if not isinstance(target_context, str) or not isinstance(target_service, str):
                continue
            matched_call_sites.add(site)
            source_context = source.attributes['context_id']
            refs = tuple(binding.evidence_refs)
            for proof in remote.provenance:
                if proof['id'] in refs:
                    add_proof(proof)
            boundary_id = 'http-boundary:' + digest([local.definition.process_id, binding.id, site])
            boundary = ViewNode(boundary_id, 'service_boundary', 'Unresolved HTTP remote boundary',
                original_ids=tuple(sorted(set((site, binding.id, *binding.original_ids)))), evidence_refs=refs,
                attributes={'scope': local.definition.scope, 'context_ids': sorted({source_context, target_context}),
                    'binding_id': binding.id, 'mapping_ids': list(binding.attributes.get('mapping_ids', [])),
                    'source_call_site': site, 'target_interface_id': selector.get('interface_id'),
                    'target_service_id': target_service, 'target_context_id': target_context,
                    'target_release_id': selector.get('id'), 'boundary_reason': 'REMOTE_BINDING_UNRESOLVED',
                    'request_response': 'HTTP_REQUEST_RESPONSE', 'error_semantics': 'TRANSPORT_BOUNDARY_ONLY',
                    'runtime_execution': 'NOT_OBSERVED', 'runtime_availability': 'UNKNOWN'},
                evidence_kinds=tuple(binding.evidence_kinds), resolution_status='UNRESOLVED',
                freshness='UNKNOWN', unknown_refs=refs)
            if boundary_id in existing_nodes:
                _fail('HTTP_BOUNDARY_NODE_COLLISION')
            existing_nodes[boundary_id] = boundary.to_dict()
            local_call = call_nodes[0]['id']
            identity = 'http-transition:' + digest([boundary_id, local_call, 'unresolved'])
            edge = ViewEdge(identity, local_call, boundary_id, 'call',
                original_ids=tuple(sorted(set((local_call, site, binding.id)))), evidence_refs=refs,
                attributes={'scope': local.definition.scope, 'context_ids': sorted({source_context, target_context}),
                    'http_transition': 'REQUEST', 'binding_id': binding.id},
                evidence_kinds=tuple(binding.evidence_kinds), resolution_status='UNRESOLVED',
                freshness='UNKNOWN', unknown_refs=refs)
            existing_edges[identity] = edge.to_dict()
            remote_services = remote.context_selection.get('services', {})
            remote_selection = remote_services.get(target_service)
            if remote_selection is not None and selection_matches(remote.context_selection, target_service, target_context):
                service_selections[target_service] = deepcopy(remote_selection)
            elif target_service not in service_selections:
                service_selections[target_service] = {'scope': local.definition.scope,
                    'status': 'EXPLICIT_REMOTE_BINDING', 'contexts': [{'context_id': target_context,
                        'status': 'EXPLICIT_REMOTE_BINDING'}]}
            all_contexts.update((source_context, target_context))
            diagnostics.append({'code': 'REMOTE_BINDING_UNRESOLVED', 'boundary_id': boundary_id,
                                'target_service_id': target_service, 'target_context_id': target_context})

        if not matched_call_sites:
            return local
        selection = deepcopy(local_definition['context_selection'])
        selection['services'] = service_selections
        definition = local.definition.to_dict()
        definition['context_selection'] = selection
        definition['context_ids'] = sorted(all_contexts)
        definition['baseline_fingerprint'] = digest({'local': local_definition['baseline_fingerprint'],
            'remote': remote.content_fingerprint, 'targets': sorted(tp.content_fingerprint for tp in targets),
            'rule': 'http-process-boundary-1'})
        from .process_model import ProcessDefinition
        canonical_definition = ProcessDefinition.from_dict(definition)
        technical.update(view_id=local.definition.process_id, baseline_fingerprint=canonical_definition.to_dict()['baseline_fingerprint'],
            context_selection=selection, nodes=list(existing_nodes.values()), edges=list(existing_edges.values()),
            provenance=list(provenance.values()), diagnostics=diagnostics,
            limits=list(dict.fromkeys(limits)),
            coverage={**technical['coverage'], 'status': 'PARTIAL', 'truncated': truncated,
                'http_boundary_count': len(matched_call_sites), 'http_upstream_coverage': upstream_coverage})
        technical_view = ViewDocument.from_dict(technical)
        result = local_doc
        result['definition'] = canonical_definition.to_dict()
        result['definition_fingerprint'] = canonical_definition.content_fingerprint
        result['technical_view'] = technical_view.to_dict()
        result['technical_status'] = 'PARTIAL'
        _bounded(result)
        return ProcessView.from_dict(result)
    except BusinessProcessError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as error:
        raise BusinessProcessError('INVALID_HTTP_PROCESS_BOUNDARY', 'Invalid or incompatible HTTP process boundary input') from error


ASYNC_VERSION = 'async-process-boundary-1'


def project_async_process_boundary(local_process, remote_interfaces, *, target_processes=(),
                                   max_depth=4, max_expansions=32):
    """Project potential Kafka paths from supplied T014/T025 documents, without I/O.

    Exact original call-site/listener IDs join the snapshots. A declared remote
    membership is static evidence only: neither delivery nor instance correlation.
    Fan-out branches never rejoin the publisher or each other. Recursion is bounded
    and leaves its subscription boundary visible when a target cannot be expanded.
    """
    try:
        if (type(max_depth) is not int or not 0 <= max_depth <= 32
                or type(max_expansions) is not int or not 0 <= max_expansions <= 128
                or not isinstance(target_processes, (list, tuple)) or len(target_processes) > 128):
            _fail('ASYNC_INVALID_LIMITS_OR_TARGETS')
        _bounded([value._document if isinstance(value, ProcessView) else value for value in target_processes])
        local = _document(local_process)
        remote_raw = remote_interfaces.to_dict() if isinstance(remote_interfaces, ViewDocument) else remote_interfaces
        _bounded(remote_raw)
        remote = ViewDocument.from_dict(remote_raw)
        targets = [_document(value) for value in target_processes]
        if remote.rules_version != REMOTE_VIEW_VERSION:
            _fail('ASYNC_UNSUPPORTED_REMOTE_VERSION')
        scope = local['definition']['scope']
        if remote.kind != 'topology' or remote.scope != scope:
            _fail('ASYNC_SCOPE_OR_KIND_MISMATCH')
        view = deepcopy(local['technical_view'])
        nodes = {n['id']: n for n in view['nodes']}
        edges = {e['id']: e for e in view['edges']}
        proofs = {p['id']: p for p in view['provenance']}
        rnodes = {n.id: n for n in remote.nodes}
        rproofs = {p['id']: p for p in remote.provenance}
        selection = deepcopy(local['definition']['context_selection'])
        contexts = set(local['definition']['context_ids'])
        diagnostics = list(view['diagnostics']) + deepcopy(list(remote.diagnostics))
        limits = list(view['limits']) + list(remote.limits) + [
            'Potential static Kafka membership paths; no consumer order or return to publisher.',
            'Delivery, processing completion and exactly-once are not observed.',
            'Supported inputs contain no instance-correlation mapping contract; topic equality is not correlation.']
        truncated = view['coverage'].get('truncated') is True or remote.coverage.get('truncated') is True
        truncated = truncated or any(d.get('truncated') is True for d in remote.diagnostics)
        upstream = [{'kind':'remote_interfaces', 'view_id':remote.view_id,
            'fingerprint':remote.content_fingerprint, 'coverage':deepcopy(remote.coverage)}]
        expansions = 0
        boundary_count = 0

        def service(node):
            return node.attributes.get('service_id') or (node.owner_id or '').removeprefix('service:')

        # Release IDs are selectors, not additional consumer identities. Compare
        # the canonical endpoint/service/context/group across the entire capture,
        # including separate source-release bindings. Distinct content-bound
        # endpoint IDs, groups or contexts remain independent potential members.
        memberships = defaultdict(list)
        for edge in remote.edges:
            if edge.relation != 'remote_kafka_publish_subscribe': continue
            source, target = rnodes.get(edge.source), rnodes.get(edge.target)
            if source is None or target is None: continue
            key = digest([source.id, service(source), target.id, service(target),
                edge.attributes.get('scope'), sorted(edge.attributes.get('context_ids', [])),
                source.attributes.get('broker_realm'), sorted(source.attributes.get('topics', [])),
                target.attributes.get('consumer_group')])
            memberships[key].append(edge)
        selector_conflicts = {}
        for group in memberships.values():
            if len(group) < 2: continue
            selectors = []
            for edge in sorted(group, key=lambda value: value.id):
                binding = rnodes.get(edge.attributes.get('binding_id'))
                selectors.append({'edge_id':edge.id, 'binding_id':binding.id if binding else None,
                    'source_release_id':binding.attributes.get('source_release_id') if binding else None,
                    'target_release_id':edge.attributes.get('target_release_id'),
                    'mapping_id':edge.attributes.get('mapping_id')})
            for edge in group: selector_conflicts[edge.id] = selectors

        def selected(doc, owner, context):
            definition = doc['definition']
            choice = definition['context_selection']
            row = choice.get('services', {}).get(owner, {})
            return (definition['scope'] == scope and context in definition['context_ids']
                and choice.get('scope', scope) == scope and row.get('scope') == scope
                and row.get('status') != 'STALE'
                and any(c.get('context_id') == context and c.get('scope', scope) == scope
                    and c.get('freshness') != 'STALE' and c.get('status') not in {'STALE','AMBIGUOUS','UNRESOLVED','UNKNOWN'}
                    for c in row.get('contexts', [])))

        def put_proof(proof):
            if proof.get('scope') != scope:
                _fail('ASYNC_PROOF_SCOPE_MISMATCH')
            if proof['id'] in proofs and proofs[proof['id']] != proof:
                _fail('ASYNC_PROOF_COLLISION')
            proofs[proof['id']] = deepcopy(proof)
            contexts.update(proof.get('context_ids', []))

        def put(collection, item):
            if item['id'] in collection:
                _fail('ASYNC_ID_COLLISION')
            collection[item['id']] = item

        def derived(identity, role, originals, refs, context_ids, attrs):
            nonlocal boundary_count
            refs = tuple(sorted(set(refs)))
            for ref in refs:
                if ref not in proofs:
                    if ref not in rproofs: _fail('ASYNC_PROOF_MISSING')
                    put_proof(rproofs[ref])
            context_ids = set(context_ids)
            for ref in refs: context_ids.update(proofs[ref].get('context_ids', []))
            contexts.update(context_ids)
            common = {'scope':scope, 'context_ids':sorted(context_ids), 'async_role':role,
                'runtime_execution':'NOT_OBSERVED', 'delivery':'NOT_OBSERVED',
                'processing_completion':'UNKNOWN', 'exactly_once':'UNKNOWN',
                'instance_correlation':'UNKNOWN', 'correlation_evidence_refs':[],
                'boundary_reason':'ASYNC_STATIC_POTENTIAL', **attrs}
            kinds = tuple(sorted({proofs[ref].get('evidence_kind', 'UNKNOWN') for ref in refs}))
            buckets = {name:tuple(ref for ref in refs if proofs[ref].get('polarity', 'UNKNOWN') == polarity)
                for name, polarity in [('supporting_refs','SUPPORTING'),
                    ('contradicting_refs','CONTRADICTING'), ('unknown_refs','UNKNOWN')]}
            node = ViewNode(identity, 'async_boundary', role, original_ids=tuple(sorted(set(originals))),
                evidence_refs=refs, evidence_kinds=kinds, resolution_status='UNRESOLVED',
                freshness='STALE' if any(proofs[ref].get('freshness') == 'STALE' for ref in refs) else 'UNKNOWN',
                **buckets, attributes=common)
            put(nodes, node.to_dict())
            boundary_count += 1
            return node

        def transition(source, target, witness, role):
            identity = 'async-edge:' + digest([source, target, witness.id, role])
            edge = ViewEdge(identity, source, target, 'async', original_ids=witness.original_ids,
                evidence_refs=witness.evidence_refs, evidence_kinds=witness.evidence_kinds,
                resolution_status='UNRESOLVED', freshness=witness.freshness,
                supporting_refs=witness.supporting_refs, contradicting_refs=witness.contradicting_refs,
                unknown_refs=witness.unknown_refs,
                attributes={**deepcopy(witness.attributes), 'async_transition':role})
            put(edges, edge.to_dict())

        def retained_remote_refs(refs, projection_contexts):
            """Keep raw upstream authority; an envelope supplies only process scope.

            T012 framework proofs can have no scope and virtual Kafka contexts.
            Rebinding those fields in-place would invent authority. Preserve the
            exact record inside a distinct envelope when ProcessView cannot admit
            its original scope/context. The envelope is UNKNOWN reference authority;
            original kind, freshness and polarity survive only in the raw record.
            """
            result = []
            projection_contexts = sorted(set(projection_contexts))
            for ref in sorted(set(refs)):
                proof = rproofs[ref]
                if (proof.get('scope') == scope
                        and set(proof.get('context_ids', [])) <= set(projection_contexts)):
                    retained = proof
                else:
                    retained = {'id':'ev:async-remote:' + digest([proof, scope, projection_contexts]),
                        'original_id':ref, 'scope':scope, 'context_ids':projection_contexts,
                        'evidence_kind':'UNKNOWN',
                        'freshness':'STALE' if proof.get('freshness') == 'STALE' else 'UNKNOWN',
                        'polarity':'UNKNOWN', 'authority':'PROVENANCE_REFERENCE_ONLY',
                        'projection_role':'REMOTE_PROOF_ENVELOPE', 'original_provenance':deepcopy(proof)}
                    if retained['id'] not in proofs:
                        diagnostics.append({'code':'ASYNC_REMOTE_PROOF_REFERENCE_ONLY',
                            'proof_id':retained['id'], 'original_proof_id':ref,
                            'original_scope':proof.get('scope'),
                            'original_context_ids':deepcopy(proof.get('context_ids', [])),
                            'original_freshness':proof.get('freshness', 'UNKNOWN')})
                put_proof(retained)
                result.append(retained['id'])
            return result

        def endpoint_proofs_valid(node):
            # UNKNOWN is canonical for T012's mixed framework evidence. It is
            # retained, not promoted. STALE/contradicting/foreign proofs cannot
            # authorize an expansion regardless of the endpoint summary flag.
            return all(rproofs[ref].get('freshness') != 'STALE'
                and rproofs[ref].get('polarity') != 'CONTRADICTING'
                and rproofs[ref].get('scope') in {None, scope}
                and rproofs[ref].get('evidence_kind') not in
                    {'UNKNOWN', 'UNRESOLVED', 'SYNTAX_CANDIDATE', 'DISPATCH_CANDIDATE'}
                for ref in node.evidence_refs)

        def declaration_proofs_valid(node, expected_contexts, mapping_ids):
            return bool(node.evidence_refs) and all(
                rproofs[ref].get('evidence_kind') == 'SOURCE_ONLY'
                and rproofs[ref].get('freshness') == 'UNKNOWN'
                and rproofs[ref].get('polarity') == 'UNKNOWN'
                and rproofs[ref].get('scope') == scope
                and set(rproofs[ref].get('context_ids', [])) == set(expected_contexts)
                and set(rproofs[ref].get('mapping_ids', [])) == set(mapping_ids)
                and isinstance(rproofs[ref].get('capture_id'), str)
                and bool(rproofs[ref]['capture_id']) for ref in node.evidence_refs)

        def current_interface(node, direction):
            attrs = node.attributes
            return (node.kind == 'kafka_interface' and attrs.get('direction') == direction
                and attrs.get('scope') == scope and node.freshness != 'STALE'
                and node.resolution_status == 'RESOLVED' and not node.contradicting_refs
                and endpoint_proofs_valid(node)
                and attrs.get('code_binding') == 'VERIFIED_STATIC'
                and all(attrs[key] in node.original_ids for key in ('origin_id', 'subscription_id', 'code_fact_id')
                    if attrs.get(key) is not None))

        def membership(source, edge, binding, source_context):
            """Validate one exact T014 candidate; aggregate ambiguity is not authority."""
            target = rnodes.get(edge.target)
            if target is None or binding is None or edge.id in selector_conflicts:
                return None
            attrs, ba = edge.attributes, binding.attributes
            candidates = ba.get('candidates', [])
            matches = [c for c in candidates if c.get('mapping_id') == attrs.get('mapping_id')]
            if len(matches) != 1: return None
            candidate = matches[0]
            if sum((c.get('target_interface_id'), c.get('target_release_id')) ==
                    (candidate.get('target_interface_id'), candidate.get('target_release_id')) for c in candidates) != 1:
                return None
            pairs = {(c.get('target_interface_id'), c.get('target_release_id')) for c in candidates}
            expected = 'AMBIGUOUS' if len(pairs) > 1 else 'UNRESOLVED' if ba.get('unresolved_mapping_ids') else 'RESOLVED'
            if (binding.kind != 'remote_binding' or binding.freshness == 'STALE' or binding.contradicting_refs
                    or binding.resolution_status != expected or edge.resolution_status != expected
                    or edge.freshness == 'STALE' or edge.contradicting_refs
                    or ba.get('transport') != 'KAFKA' or ba.get('scope') != scope
                    or ba.get('source_interface_id') != source.id
                    or ba.get('context_ids') != [source_context]
                    or ba.get('capture_freshness') != 'CAPTURE_TIME_ONLY'
                    or attrs.get('capture_freshness') != 'CAPTURE_TIME_ONLY'
                    or not all(attrs.get(k) == v for k, v in candidate.items())
                    or candidate.get('mapping_id') not in ba.get('mapping_ids', [])
                    or candidate.get('mapping_id') in ba.get('unresolved_mapping_ids', [])
                    or attrs.get('target_interface_id') != target.id or attrs.get('scope') != scope
                    or attrs.get('target_service_id') != service(target)
                    or attrs.get('transition_kind') != 'ASYNC_PUBLISH_SUBSCRIBE'
                    or attrs.get('compatibility') not in {'EXACT_DECLARATION', 'EXPLICIT_PAIRED_DECLARATION'}
                    or not current_interface(source, 'PRODUCER') or not current_interface(target, 'CONSUMER')
                    or set(candidate.get('evidence_refs', [])) != set(source.evidence_refs) | set(target.evidence_refs)
                    or set(attrs.get('original_evidence_refs', [])) != set(candidate.get('evidence_refs', []))
                    or not declaration_proofs_valid(binding, [source_context], ba.get('mapping_ids', []))
                    or not declaration_proofs_valid(edge, candidate.get('context_ids', []), [candidate['mapping_id']])
                    or len({rproofs[ref]['capture_id'] for ref in (*binding.evidence_refs, *edge.evidence_refs)}) != 1
                    or source.attributes.get('broker_realm') is None
                    or source.attributes.get('broker_realm') != target.attributes.get('broker_realm')
                    or not source.attributes.get('topics') or source.attributes.get('topics') != target.attributes.get('topics')
                    or source.attributes.get('topic_pattern') or target.attributes.get('topic_pattern')):
                return None
            # Multiple release selectors for the same endpoint remain ambiguous.
            if len({c.get('target_release_id') for c in candidates if c.get('target_interface_id') == target.id}) != 1:
                return None
            target_contexts = set(attrs.get('context_ids', [])) - {source_context}
            if not target_contexts and attrs.get('context_ids') == [source_context]:
                target_contexts = {source_context}
            if len(target_contexts) != 1: return None
            target_context = next(iter(target_contexts))
            if (set(attrs['context_ids']) != {source_context, target_context}
                    or source.attributes.get('context_id', source_context) != source_context
                    or target.attributes.get('context_id', target_context) != target_context):
                return None
            return target, target_context

        def expand(doc, id_map, depth, ancestry):
            nonlocal expansions, truncated
            for source in sorted(remote.nodes, key=lambda n: n.id):
                if source.kind != 'kafka_interface' or source.attributes.get('direction') != 'PRODUCER':
                    continue
                # Only concrete call-site-bearing CFG nodes initiate publication;
                # returns_to/exception edge sources are never origin candidates.
                origins = []
                for node in doc['technical_view']['nodes']:
                    if node['kind'] not in {'call','unresolved_boundary','basic_block','action'}: continue
                    sites = set(node['attributes'].get('call_site_ids', []))
                    if isinstance(node['attributes'].get('call_site'), str): sites.add(node['attributes']['call_site'])
                    matched = sites & set(source.original_ids)
                    if source.attributes.get('origin_id') is not None:
                        matched &= {source.attributes['origin_id']}
                    if len(matched) == 1:
                        cids = set(node['attributes'].get('context_ids', [])) & set(doc['definition']['context_ids'])
                        if len(cids) == 1 and selected(doc, service(source), next(iter(cids))):
                            origins.append((node, next(iter(matched)), next(iter(cids))))
                for origin, site, source_context in origins:
                    prefix = 'async:' + digest([id_map[origin['id']], source.id, site])
                    origin_refs = origin['evidence_refs']
                    publish_refs = [*origin_refs, *retained_remote_refs(source.evidence_refs, [source_context])]
                    publish = derived(prefix + ':publish', 'publish', [source.id, site], publish_refs,
                        [source_context], {'source_interface_id':source.id, 'source_call_site':site})
                    transition(id_map[origin['id']], publish.id, publish, 'PUBLISH_INTENT')
                    channel = derived(prefix + ':channel', 'channel', [source.id, site], publish_refs,
                        [source_context], {'source_interface_id':source.id,
                            'broker_realm':source.attributes.get('broker_realm'), 'topics':deepcopy(source.attributes.get('topics', []))})
                    transition(publish.id, channel.id, channel, 'CHANNEL_INTENT')
                    diagnostics.append({'code':'ASYNC_INSTANCE_CORRELATION_UNKNOWN', 'boundary_id':publish.id})
                    branches = [(e, rnodes.get(e.attributes.get('binding_id')), None) for e in remote.edges
                        if e.source == source.id and e.relation == 'remote_kafka_publish_subscribe']
                    for binding in remote.nodes:
                        if binding.kind == 'remote_binding' and binding.attributes.get('source_interface_id') == source.id:
                            for selector in binding.attributes.get('unresolved_selectors', []):
                                branches.append((None, binding, selector))
                    if not branches: branches = [(None, None, None)]
                    branches.sort(key=lambda branch: digest([branch[0].id if branch[0] else None,
                        branch[1].id if branch[1] else None, branch[2]]))
                    for edge, binding, selector in branches:
                        target = rnodes.get(edge.target) if edge else None
                        checked = membership(source, edge, binding, source_context) if edge else None
                        if origin['freshness'] == 'STALE' or any(proofs[r].get('freshness') == 'STALE' for r in origin_refs):
                            checked = None
                        target_context = checked[1] if checked else None
                        remote_refs = set(source.evidence_refs)
                        for witness in (edge, binding, target):
                            if witness is not None: remote_refs.update(witness.evidence_refs)
                        refs = retained_remote_refs(remote_refs, [source_context,
                            *([target_context] if target_context else [])]) or origin_refs
                        reasons = ('ASYNC_MEMBERSHIP_SELECTOR_CONFLICT' if edge and edge.id in selector_conflicts
                            else 'ASYNC_REMOTE_MEMBERSHIP_UNPROVEN' if edge else 'ASYNC_REMOTE_TARGET_UNRESOLVED')
                        matching = []
                        if checked:
                            for tp in targets:
                                if not selected(tp, service(target), target_context): continue
                                triggers = [n for n in tp['technical_view']['nodes']
                                    if n['kind'] == 'trigger' and n['id'] in tp['entry_ids']
                                    and n['attributes'].get('trigger_kind') == 'KAFKA'
                                    and n['attributes'].get('entry_symbol_id') in target.original_ids
                                    and n['freshness'] != 'STALE'
                                    and n['attributes'].get('context_ids') == [target_context]
                                    and all(p.get('freshness') != 'STALE' for p in tp['technical_view']['provenance']
                                        if p['id'] in n['evidence_refs'])]
                                if len(triggers) == 1: matching.append((tp, triggers[0]))
                            reasons = 'ASYNC_TARGET_PROCESS_UNAVAILABLE' if not matching else 'ASYNC_TARGET_PROCESS_AMBIGUOUS'
                        selected_target = matching[0] if len(matching) == 1 else None
                        key = None
                        if selected_target:
                            tp, trigger = selected_target
                            tv = tp['technical_view']
                            diagnostics.extend({**deepcopy(d), 'async_source_process_id':tp['process_id'],
                                'async_source_revision':tp['revision']} for d in tv['diagnostics'])
                            limits.extend(tv['limits'])
                            truncated = truncated or tv['coverage'].get('truncated') is True
                            upstream.append({'kind':'target_process', 'process_id':tp['process_id'], 'revision':tp['revision'],
                                'fingerprint':ProcessView.from_dict(tp).content_fingerprint, 'coverage':deepcopy(tv['coverage'])})
                            key = (tp['process_id'], target_context)
                            has_body = any(n['kind'] not in {'trigger', 'entry', 'exit', 'exceptional_exit', 'unresolved_boundary'}
                                for n in tp['technical_view']['nodes'])
                            reasons = ('ASYNC_LOOP' if key in ancestry else 'ASYNC_DEPTH_LIMIT' if depth >= max_depth
                                else 'ASYNC_EXPANSION_LIMIT' if expansions >= max_expansions
                                else 'ASYNC_TARGET_CFG_UNAVAILABLE' if not has_body else None)
                        identity = prefix + ':subscription:' + digest([edge.id if edge else None,
                            binding.id if binding else None, selector])
                        attrs = {'boundary_reason':reasons or 'ASYNC_STATIC_POTENTIAL',
                            'source_interface_id':source.id, 'target_interface_id':target.id if target else (selector or {}).get('interface_id'),
                            'binding_id':binding.id if binding else None, 'target_selector':deepcopy(selector),
                            'consumer_group':target.attributes.get('consumer_group') if target else None,
                            'subscription_id':target.attributes.get('subscription_id') if target else None,
                            'subscription_logical_id':target.attributes.get('subscription_logical_id') if target else None,
                            'membership_evidence_refs':list(edge.evidence_refs) if edge else [],
                            'remote_evidence_refs':sorted(remote_refs),
                            'conflicting_selectors':deepcopy(selector_conflicts.get(edge.id, [])) if edge else [],
                            'membership_status':edge.resolution_status if edge else 'UNRESOLVED',
                            'branch_semantics':'POTENTIAL_MEMBERSHIP', 'consumer_order':'UNSPECIFIED'}
                        original = [source.id, edge.id] + list(edge.original_ids) if edge else [source.id, binding.id] if binding else [source.id]
                        if target: original += [target.id, *target.original_ids]
                        subscription = derived(identity, 'subscription', original, refs,
                            [source_context, *([target_context] if target_context else [])], attrs)
                        transition(channel.id, subscription.id, subscription, 'SUBSCRIPTION_POTENTIAL')
                        if reasons:
                            diagnostics.append({'code':reasons, 'boundary_id':identity})
                            if reasons in {'ASYNC_DEPTH_LIMIT', 'ASYNC_EXPANSION_LIMIT', 'ASYNC_LOOP'}: truncated = True
                            continue
                        tp, trigger = selected_target
                        expansions += 1
                        tv = tp['technical_view']
                        for proof in tv['provenance']: put_proof(proof)
                        contexts.update(tp['definition']['context_ids'])
                        for owner, choice in tp['definition']['context_selection'].get('services', {}).items():
                            if owner not in selection.setdefault('services', {}): selection['services'][owner] = deepcopy(choice)
                        mapping = {n['id']:identity + ':target:' + n['id'] for n in tv['nodes']}
                        for n in tv['nodes']:
                            clone = deepcopy(n); clone['id'] = mapping[n['id']]
                            clone['attributes'].update(source_process_id=tp['process_id'], source_process_revision=tp['revision'])
                            put(nodes, clone)
                        for e in tv['edges']:
                            clone = deepcopy(e); clone['id'] = identity + ':target:' + e['id']
                            clone['source'] = mapping[e['source']]; clone['target'] = mapping[e['target']]
                            clone['attributes']['source_process_id'] = tp['process_id']
                            put(edges, clone)
                        transition(subscription.id, mapping[trigger['id']], subscription, 'CONSUMER_POTENTIAL')
                        if len(nodes) > 10000 or len(edges) > 30000: _fail('ASYNC_OUTPUT_TOPOLOGY_BUDGET')
                        expand(tp, mapping, depth + 1, ancestry | {key})

        expand(local, {n['id']:n['id'] for n in view['nodes']}, 0,
            {(local['process_id'], cid) for cid in local['definition']['context_ids']})
        if len(nodes) > 10000 or len(edges) > 30000: _fail('ASYNC_OUTPUT_TOPOLOGY_BUDGET')
        from .process_model import ProcessDefinition
        definition = deepcopy(local['definition'])
        definition.update(context_ids=sorted(contexts), context_selection=selection,
            baseline_fingerprint=digest([ASYNC_VERSION, local['definition']['baseline_fingerprint'],
                remote.content_fingerprint, sorted(ProcessView.from_dict(tp).content_fingerprint for tp in targets),
                max_depth, max_expansions]))
        definition = ProcessDefinition.from_dict(definition)
        view.update(baseline_fingerprint=definition.to_dict()['baseline_fingerprint'], context_selection=selection,
            rules_version=ASYNC_VERSION, nodes=list(nodes.values()), edges=list(edges.values()),
            provenance=list(proofs.values()), diagnostics=diagnostics, limits=list(dict.fromkeys(limits)),
            coverage={**view['coverage'], 'status':'PARTIAL', 'truncated':truncated,
                'async_boundary_count':boundary_count, 'async_expansion_count':expansions,
                'async_upstream_coverage':upstream})
        local.update(definition=definition.to_dict(), definition_fingerprint=definition.content_fingerprint,
            technical_view=ViewDocument.from_dict(view).to_dict(), technical_status='PARTIAL')
        _bounded(local)
        return ProcessView.from_dict(local)
    except BusinessProcessError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as error:
        raise BusinessProcessError('INVALID_ASYNC_PROCESS_BOUNDARY', 'Invalid or incompatible async process input') from error


FAILURE_VERSION = 'process-failures-2'


def project_process_failures(process, graph=None, *, compensation_proposals=(), max_policies=128):
    """Preserve source CFG and project bounded static failure-policy declarations.

    graph is an explicit KnowledgeGraph snapshot, never a path or a loader.
    Retry/DLT associations do not execute handlers or roll back remote effects.
    Compensation is accepted only in the existing PROPOSED semantic overlay.
    """
    try:
        from .model import KnowledgeGraph
        from .process_model import ProcessDefinition
        from .process_paths import _cfg_proofs, _selected_trigger, ProcessPathError, TRIGGER_VERSION
        from .kafka_retry import policy_boundaries
        if type(max_policies) is not int or not 0 <= max_policies <= 512:
            _fail('Invalid failure policy budget')
        if not isinstance(compensation_proposals, (list, tuple)) or len(compensation_proposals) > 128:
            _fail('Invalid compensation proposal collection')
        _bounded(compensation_proposals)
        doc = _document(process)
        if doc['technical_view']['rules_version'] in {FAILURE_VERSION, 'process-failures-1'}:
            _fail('Failure projection requires its original input, not a previous projection')
        # Only validated stored T026 membership can recover the technical CFG.
        if any(_GROUP in n['attributes'] for n in doc['technical_view']['nodes']):
            doc = _expand_checked(doc).to_dict()
        view = doc['technical_view']; scope = doc['definition']['scope']
        contexts = set(doc['definition']['context_ids'])
        nodes = view['nodes']; edges = view['edges']; provenance = {p['id']:p for p in view['provenance']}
        diagnostics = view['diagnostics']; truncated = view['coverage'].get('truncated') is True
        methods = {n['attributes']['method'] for n in nodes if isinstance(n['attributes'].get('method'), str)}
        methods.update(n['attributes']['entry_symbol_id'] for n in nodes
            if n['kind'] == 'trigger' and isinstance(n['attributes'].get('entry_symbol_id'), str))
        for node in nodes:
            if node['kind'] == 'transaction_boundary':
                node['attributes']['failure_semantics'] = {'transaction_scope':'LOCAL_DECLARATION_ONLY',
                    'rollback':'UNKNOWN', 'remote_effects':'NOT_INCLUDED', 'execution':'NOT_OBSERVED'}
                diagnostics.append({'code':'LOCAL_TRANSACTION_ROLLBACK_UNOBSERVED','node_id':node['id']})
            elif node['kind'] in {'service_boundary','async_boundary'}:
                node['attributes']['failure_semantics'] = {'local_transaction_rollback':'NOT_PROVEN'}
        for proposal in compensation_proposals:
            if not isinstance(proposal, Mapping) or proposal.get('semantic_review_status') != 'PROPOSED':
                _fail('Compensation must be a separate PROPOSED semantic annotation')
            doc['semantic_annotations'].append(deepcopy(dict(proposal)))
            diagnostics.append({'code':'COMPENSATION_PROPOSAL_ONLY','annotation_id':proposal.get('id'),
                'technical_relationship':'NOT_ESTABLISHED','rollback':'UNKNOWN'})
        # Validate proposals against the existing exact target/provenance refs.
        view['coverage']['status'] = doc['technical_status'] = 'PARTIAL'
        ProcessView.from_dict(doc)
        snapshot = None; rows = []; graph_proofs = {}; graph_nodes = {}; cfgs = {}; expected_proofs = {}
        if graph is None:
            diagnostics.append({'code':'FAILURE_POLICY_INPUT_UNAVAILABLE','policy_status':'UNKNOWN'})
        else:
            raw = graph.to_dict() if isinstance(graph, KnowledgeGraph) else graph
            _bounded(raw)
            snapshot = KnowledgeGraph.from_dict(deepcopy(raw))
            graph_proofs = {p['id']:p for p in snapshot.evidence}; graph_nodes = {n.id:n for n in snapshot.nodes}
            symbols = {s['id']:s for s in snapshot.symbols}
            for context in snapshot.contexts:
                if context['id'] in contexts and context.get('scope') == scope:
                    accepted, proofs = _cfg_proofs(snapshot, context, graph_nodes, symbols)
                    cfgs.update(accepted); expected_proofs.update(proofs)
            rows = policy_boundaries(snapshot, methods)
            relevant = [d for d in snapshot.diagnostics if d.get('scope',scope)==scope and (
                d.get('context_id') in contexts or d.get('source_id') in methods
                or bool(set(d.get('context_ids',[])) & contexts)
                or not any(d.get(k) for k in ('context_id','context_ids','source_id')))]
            diagnostics.extend({'failure_upstream':True, **deepcopy(d)} for d in relevant)
            truncated = truncated or any(d.get('truncated') is True for d in relevant)
            if not rows:
                diagnostics.append({'code':'FAILURE_POLICY_NOT_PROVEN','policy_status':'UNKNOWN'})
        groups = defaultdict(list)
        for row in rows: groups[row['policy_id']].append(row)
        if len(groups) > max_policies:
            truncated = True
            diagnostics.append({'code':'FAILURE_POLICY_LIMIT','limit':max_policies,
                'omitted_policy_ids':sorted(groups)[max_policies:]})
        def retained(records, cids):
            refs = []
            for raw in sorted(records, key=lambda p:p['id']):
                identity = 'ev:failure-reference:' + digest([raw, scope, cids])
                item = {'id':identity,'original_id':raw['id'],'scope':scope,'context_ids':cids,
                    'evidence_kind':'UNKNOWN','freshness':'STALE' if raw.get('freshness')=='STALE' else 'UNKNOWN',
                    'polarity':'UNKNOWN','authority':'PROVENANCE_REFERENCE_ONLY',
                    'original_provenance':deepcopy(raw)}
                if identity in provenance and provenance[identity] != item: _fail('Failure provenance collision')
                provenance[identity] = item; refs.append(identity)
            return refs
        def boundary(identity, role, originals, cids, refs, attrs, owner=None):
            if any(n['id']==identity for n in nodes): _fail('Failure boundary identity collision')
            summary = _summarize_view_evidence(refs, provenance)
            if not refs: summary['evidence_kinds'] = []
            node = ViewNode(identity,'retry' if role=='retry' else 'async_boundary',
                'Static '+role+' policy', original_ids=tuple(sorted(set(originals))),owner_id=owner,
                evidence_refs=tuple(refs),attributes={'scope':scope,'context_ids':cids,
                    'failure_role':role,'boundary_reason':'STATIC_POLICY_ONLY',
                    'execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED','activation':'UNKNOWN',
                    'runtime_availability':'UNKNOWN','processing_completion':'UNKNOWN',**attrs},
                resolution_status='UNRESOLVED',**summary).to_dict()
            if len(nodes)>=10000: _fail('Failure output topology budget exceeded')
            nodes.append(node); return node
        def transition(source, target, role, node):
            identity = 'failure-transition:' + digest([source,target,role])
            if any(e['id']==identity for e in edges): _fail('Failure transition identity collision')
            summary = _summarize_view_evidence(node['evidence_refs'],provenance)
            edges.append(ViewEdge(identity,source,target,'retry' if role=='RETRY_POTENTIAL' else 'async',
                original_ids=tuple(node['original_ids']),evidence_refs=tuple(node['evidence_refs']),
                attributes={'scope':scope,'context_ids':node['attributes']['context_ids'],
                    'failure_transition':role,'boundary_reason':'STATIC_POLICY_ONLY',
                    'execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED','condition':'failure policy may apply; feasibility UNKNOWN'},
                resolution_status='UNRESOLVED',**summary).to_dict())
        def selected_anchor(node, cids):
            choice=doc['definition']['context_selection']
            row=choice.get('services',{}).get((node.get('owner_id') or '').removeprefix('service:'),{})
            return (choice.get('scope',scope)==scope and row.get('scope')==scope
                and row.get('status')!='STALE' and len(cids)==1
                and any(c.get('context_id')==cids[0] and c.get('scope',scope)==scope
                    and c.get('status')=='CURRENT' and c.get('freshness')!='STALE'
                    for c in row.get('contexts',[])))
        original_nodes = {n['id']:n for n in nodes}
        def kafka_occurrence(exit_node, origin, cfg, cids, expected):
            # T025's root CFG path is (entry method,). Ordinary local calls use
            # an additional call-site/block path, even for the same declaration.
            body_entry = 'process:' + digest({'path':(origin,), 'id':cfg['entry']})[:24]
            body_exit = 'process:' + digest({'path':(origin,), 'id':cfg['exceptional_exit']})[:24]
            matches = []
            for trigger in original_nodes.values():
                attrs = trigger['attributes']
                if (trigger['kind']!='trigger' or attrs.get('trigger_kind')!='KAFKA'
                        or attrs.get('entry_symbol_id')!=origin or attrs.get('context_ids')!=cids
                        or trigger['freshness']!='CURRENT' or trigger['contradicting_refs']):
                    continue
                canonical = 'trigger:' + digest({'context':cids[0], 'symbol':origin,
                    'entrypoint':attrs.get('entrypoint_id'), 'kind':'KAFKA'})
                if not trigger['id'].endswith(canonical): continue
                prefix = trigger['id'][:-len(canonical)]
                if exit_node['id']!=prefix+body_exit: continue
                entry = original_nodes.get(prefix+body_entry)
                if (entry is None or entry['kind']!='entry' or entry['freshness']!='CURRENT'
                        or entry['contradicting_refs'] or entry['owner_id']!=exit_node['owner_id']
                        or trigger['owner_id']!=exit_node['owner_id']
                        or cfg['entry'] not in entry['original_ids']
                        or entry['attributes'].get('method')!=origin
                        or entry['attributes'].get('context_ids')!=cids
                        or any(p['id'] not in entry['evidence_refs'] or provenance.get(p['id'])!=p for p in expected)):
                    continue
                declaration = [e for e in edges if e['source']==trigger['id'] and e['target']==entry['id']
                    and e['id']==prefix+'process-entry:'+digest([canonical,body_entry])
                    and e['relation']=='unknown' and {canonical,origin}<=set(e['original_ids'])
                    and e['attributes'].get('boundary_reason')=='declaration-to-body static association'
                    and e['attributes'].get('scope')==scope and e['attributes'].get('context_ids')==cids]
                if (len(declaration)!=1 or sum(e['target']==entry['id'] for e in edges)!=1
                        or declaration[0]['freshness']=='STALE' or declaration[0]['contradicting_refs']): continue
                occurrence_refs = list(trigger['evidence_refs'])
                if not prefix:
                    if trigger['id'] not in doc['entry_ids'] or trigger['id'] not in doc['definition']['trigger_ids']: continue
                else:
                    # T028 supplies one distinct subscription -> consumer entry
                    # association per imported occurrence, not a Java call edge.
                    incoming = [e for e in edges if e['target']==trigger['id'] and e['relation']=='async'
                        and e['attributes'].get('async_transition')=='CONSUMER_POTENTIAL']
                    if len(incoming)!=1: continue
                    link = incoming[0]; subscription = original_nodes.get(link['source'])
                    if (subscription is None or subscription['kind']!='async_boundary'
                            or prefix!=subscription['id']+':target:'
                            or subscription['attributes'].get('async_role')!='subscription'
                            or subscription['attributes'].get('boundary_reason')!='ASYNC_STATIC_POTENTIAL'
                            or origin not in subscription['original_ids']
                            or not subscription['attributes'].get('membership_evidence_refs')
                            or link['evidence_refs']!=subscription['evidence_refs']
                            or link['original_ids']!=subscription['original_ids']
                            or any(n['freshness']=='STALE' or n['contradicting_refs'] for n in (subscription,link))
                            or not isinstance(attrs.get('source_process_id'),str)
                            or type(attrs.get('source_process_revision')) is not int
                            or any(n['attributes'].get(k)!=attrs[k] for n in (entry,exit_node)
                                for k in ('source_process_id','source_process_revision'))):
                        continue
                    occurrence_refs += link['evidence_refs'] + subscription['evidence_refs']
                    raw = [provenance[ref].get('original_provenance',provenance[ref]) for ref in occurrence_refs]
                    if any(p.get('freshness')=='STALE' or p.get('polarity')=='CONTRADICTING'
                           or p.get('scope') not in (None,scope) for p in raw): continue
                if prefix and not set(subscription['attributes']['membership_evidence_refs']) <= {p['id'] for p in raw}: continue
                # Replay the existing T025 trigger guard over its exact original
                # declaration/proofs. Renaming a trigger or adding metadata cannot
                # turn a scheduler/call occurrence into a Kafka entry.
                canonical_node = {**deepcopy(trigger), 'id':canonical}
                inventory = ViewDocument.from_dict({**view, 'rules_version':TRIGGER_VERSION,
                    'nodes':[canonical_node], 'edges':[],
                    'provenance':[provenance[ref] for ref in trigger['evidence_refs']]})
                try:
                    _selected_trigger(snapshot,inventory,canonical)
                except ProcessPathError:
                    continue
                matches.append({'trigger_id':trigger['id'],'entry_id':entry['id'],
                    'exceptional_exit_id':exit_node['id'],'evidence_refs':sorted(set(occurrence_refs))})
            return matches[0] if len(matches)==1 else None
        for policy_id in sorted(groups)[:max_policies]:
            group = groups[policy_id]; policy = graph_nodes.get(policy_id)
            md = policy.metadata if policy and isinstance(policy.metadata,dict) else {}
            origin = md.get('origin_id')
            if not isinstance(origin,str): origin = next((r['source'] for r in group if r['source'] in methods),None)
            process_contexts = {cid for n in nodes if n['attributes'].get('method')==origin
                or n['attributes'].get('entry_symbol_id')==origin for cid in n['attributes']['context_ids']}
            cids = sorted(process_contexts or contexts)
            context_valid = len(cids)==1 and md.get('context_id')==cids[0]
            related = [e for e in snapshot.edges if e.kind in {'declares_retry_boundary','declares_dlt_boundary'}
                and policy_id in (e.source,e.target)]
            raw_refs = {r for e in related for r in e.evidence_ids}
            pending = list(raw_refs)
            while pending:
                for ref in graph_proofs.get(pending.pop(),{}).get('compiler_evidence_ids',[]):
                    if ref not in raw_refs: raw_refs.add(ref); pending.append(ref)
            records = [graph_proofs[r] for r in sorted(raw_refs) if r in graph_proofs]
            proof_valid = bool(records) and len(records)==len(raw_refs) and all(
                p.get('freshness') not in {'STALE'} and p.get('polarity') != 'CONTRADICTING'
                and p.get('scope',scope)==scope and p.get('context_ids')==cids for p in records)
            candidates = [n for n in nodes if n['kind']=='exceptional_exit'
                and n['attributes'].get('method')==origin and n['attributes'].get('context_ids')==cids]
            cfg = cfgs.get(origin,{}); expected = expected_proofs.get(origin,[])
            anchors = [n for n in candidates if cfg.get('exceptional_exit') in n['original_ids']
                and n['freshness']=='CURRENT' and not n['contradicting_refs']
                and selected_anchor(n,cids) and expected and all(p['polarity']!='CONTRADICTING' and p['id'] in n['evidence_refs']
                    and provenance.get(p['id'])==p for p in expected)]
            policy_valid = (context_valid and proof_valid and md.get('status')=='DECLARED'
                and all(r['status']=='DECLARED' for r in group)
                and {r['kind'] for r in group}=={'declares_retry_boundary','declares_dlt_boundary'})
            refs = retained(records,cids)
            attrs = {'policy_id':policy_id,'policy_logical_id':md.get('logical_id'),
                'origin_method':origin,
                'attempts_semantics':'DECLARED_TOTAL_LIMIT_NOT_OBSERVED',
                'destinations':'UNKNOWN','scheduling':'UNKNOWN','unrolled_attempts':0,
                'upstream_policy_rows':deepcopy(group),'original_evidence_refs':sorted(raw_refs)}
            for anchor in candidates or [None]:
                occurrence = kafka_occurrence(anchor,origin,cfg,cids,expected) if anchor in anchors else None
                declared = policy_valid and occurrence is not None
                # An async membership spans producer and consumer contexts. Keep
                # its original proof intact; the target policy's reference-only
                # envelope does not rebind that upstream authority in place.
                occurrence_refs = sorted(set(refs + (retained(
                    [provenance[ref] for ref in occurrence['evidence_refs']],cids) if occurrence else [])))
                occurrence_attrs = {**attrs,'policy_status':'DECLARED' if declared else 'UNKNOWN',
                    'attempts':md.get('attempts') if declared else None,
                    'retry_suffix':md.get('retry_suffix') if declared else None,
                    'dlt_suffix':md.get('dlt_suffix') if declared else None,
                    'kafka_entry_occurrence':deepcopy(occurrence) if declared else None,
                    'source_exceptional_exit':anchor['id'] if anchor else None}
                identity = 'failure-policy:' + digest([policy_id,origin,anchor['id'] if anchor else None])
                retry = boundary(identity,'retry',[policy_id,*([origin] if origin else [])],cids,occurrence_refs,occurrence_attrs,
                    anchor.get('owner_id') if anchor else None)
                if not declared:
                    diagnostics.append({'code':'FAILURE_POLICY_UNPROVEN','policy_id':policy_id,
                        'boundary_id':identity,'reasons':sorted({r for row in group for r in row['reasons']}
                            | ({'KAFKA_ENTRY_OCCURRENCE_UNPROVEN'} if occurrence is None else {'PROCESS_CFG_OR_POLICY_AUTHORITY_UNPROVEN'}))})
                    continue
                transition(anchor['id'],retry['id'],'RETRY_POTENTIAL',retry)
                dlt = boundary(identity+':dlt','dlt',[policy_id,md['handler_id']],cids,occurrence_refs,
                    {**occurrence_attrs,'handler_id':md['handler_id'],'handler_execution':'NOT_OBSERVED',
                        'condition':'declared attempt limit may be exhausted'},anchor.get('owner_id'))
                transition(retry['id'],dlt['id'],'DLT_POTENTIAL',dlt)
        if len(nodes)>10000 or len(edges)>30000: _fail('Failure output topology budget exceeded')
        baseline = digest([FAILURE_VERSION,ProcessView.from_dict(_document(process)).content_fingerprint,
            snapshot.to_dict() if snapshot else None,compensation_proposals,max_policies])
        definition = ProcessDefinition.from_dict({**doc['definition'],'baseline_fingerprint':baseline})
        view.update(rules_version=FAILURE_VERSION,baseline_fingerprint=baseline,provenance=list(provenance.values()),
            coverage={**view['coverage'],'status':'PARTIAL','truncated':truncated},
            limits=list(dict.fromkeys(view['limits']+[
                'Failure policies are static declarations; retry scheduling, delivery and successful processing are not observed.',
                'Local transaction declarations do not establish rollback of HTTP/Kafka effects.',
                'Compensation proposals are semantic annotations, not technical rollback relationships.'])))
        doc.update(definition=definition.to_dict(),definition_fingerprint=definition.content_fingerprint,
            technical_view=ViewDocument.from_dict(view).to_dict(),technical_status='PARTIAL')
        _bounded(doc)
        return ProcessView.from_dict(doc)
    except BusinessProcessError:
        raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError) as error:
        raise BusinessProcessError('INVALID_PROCESS_FAILURES','Invalid failure projection input') from error

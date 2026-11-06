"""Deterministic pure filtering of an already captured T016 topology."""
from collections import deque
from copy import deepcopy
from dataclasses import replace

from .architecture_model import ViewDocument
from .remote_mapping import _bounded, digest
from .remote_interfaces import _ref, _refs
from .service_topology import VERSION as TOPOLOGY_VERSION
from .analysis_model import canonical

VERSION = 'topology-filter-1'
_MAX_OBJECTS = 20000
_MAX_OUTPUT_CHARS = 4 * 1024 * 1024


class TopologyFilterError(ValueError):
    def __init__(self, code):
        self.diagnostic = {'code': code}
        super().__init__(code)


def _fail(code):
    raise TopologyFilterError(code) from None


def _contexts(item):
    return _refs(item.attributes.get('context_ids', []))


def _inventory(items):
    result = {k: set() for k in ('original_interface_ids', 'mapping_ids', 'release_ids', 'original_ids')}
    for item in items:
        result['original_ids'].update(_refs(item.original_ids))
        for target, field in (('original_interface_ids', 'origin_interface_ids'),
                              ('mapping_ids', 'origin_mapping_ids'), ('release_ids', 'origin_release_ids')):
            result[target].update(_refs(item.attributes.get(field, [])))
        candidates = item.attributes.get('origin_candidates', [])
        if not isinstance(candidates, (list, tuple)):
            _fail('FILTER_INVALID_EXPANSION')
        for candidate in candidates:
            if not isinstance(candidate, dict):
                _fail('FILTER_INVALID_EXPANSION')
            for target, fields in (('original_interface_ids', ('source_interface_id', 'target_interface_id')),
                                   ('mapping_ids', ('mapping_id',)),
                                   ('release_ids', ('source_release_id', 'target_release_id'))):
                for field in fields:
                    if field in candidate:
                        result[target].add(_ref(candidate[field]))
    return {k: sorted(v) for k, v in result.items()}


def filter_topology(topology, *, focus_service=None, direction='both', max_hops=None,
                    max_nodes=200, relations=None, scope=None, context_ids=None):
    """Filter a trusted snapshot; no capture, I/O, reselection or freshness claim."""
    try:
        return _filter(topology, focus_service, direction, max_hops, max_nodes,
                       relations, scope, context_ids)
    except TopologyFilterError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        _fail('FILTER_INVALID_INPUT')


def _filter(topology, focus, direction, hops, budget, relations, scope, contexts):
    _bounded((topology, focus, direction, hops, budget, relations, scope, contexts))
    if direction not in ('incoming', 'outgoing', 'both'):
        _fail('FILTER_INVALID_DIRECTION')
    if type(budget) is not int or not 1 <= budget <= _MAX_OBJECTS:
        _fail('FILTER_INVALID_NODE_BUDGET')
    if hops is not None and (type(hops) is not int or not 0 <= hops <= _MAX_OBJECTS):
        _fail('FILTER_INVALID_HOPS')
    if focus is not None:
        focus = _ref(focus)
    allowed_relations = None if relations is None else set(_refs(relations))
    allowed_contexts = None if contexts is None else set(_refs(contexts))
    raw = topology.to_dict(include_generation_metadata=False) if isinstance(topology, ViewDocument) else topology
    view = ViewDocument.from_dict(raw)
    if view.kind != 'topology' or view.rules_version != TOPOLOGY_VERSION:
        _fail('FILTER_UNSUPPORTED_TOPOLOGY')
    if scope is not None and _ref(scope) != view.scope:
        _fail('FILTER_SCOPE_NOT_CAPTURED')
    scope = _ref(view.scope)
    if len(view.nodes) + len(view.edges) + len(view.provenance) > _MAX_OBJECTS:
        _fail('FILTER_OBJECT_LIMIT')
    nodes = {n.id: n for n in view.nodes}
    edges = {e.id: e for e in view.edges}
    # Validate expansions on retained claims too; a display cutoff must never be
    # what decides whether a required original identity is safe to export.
    _inventory((*view.nodes, *view.edges))
    known_contexts = set()
    for item in (*view.nodes, *view.edges):
        _ref(item.id)
        _ref(item.relation if hasattr(item, 'relation') else item.kind)
        if getattr(item, 'owner_id', None) is not None:
            _ref(item.owner_id)
        _refs(item.original_ids)
        _refs(item.evidence_refs)
        if item.attributes.get('scope', scope) not in (scope, 'unknown'):
            _fail('FILTER_FOREIGN_SCOPE')
        known_contexts.update(_contexts(item))
    for proof in view.provenance:
        _ref(proof['id'])
        for field in ('source_id', 'original_id', 'scope'):
            if proof.get(field) is not None:
                _ref(proof[field])
        for field in ('source_refs', 'original_ids', 'original_evidence_ids', 'compiler_evidence_ids'):
            if field in proof:
                _refs(proof[field])
        known_contexts.update(_refs(proof.get('context_ids', [])))
    if allowed_contexts is not None and not allowed_contexts <= known_contexts:
        _fail('FILTER_CONTEXT_NOT_CAPTURED')
    if focus in nodes and nodes[focus].kind != 'service':
        _fail('FILTER_FOCUS_NOT_SERVICE')
    unknown_focus = focus is not None and focus not in nodes

    def context_matches(item):
        if allowed_contexts is None:
            return True
        required = set(_contexts(item))
        return bool(required and required <= allowed_contexts) or (
            not required and item.attributes.get('context_independent') is True)

    eligible_nodes = {n.id for n in view.nodes if context_matches(n)}
    edge_reasons = {}
    adjacency = {i: set() for i in eligible_nodes}
    for edge in view.edges:
        if allowed_relations is not None and edge.relation not in allowed_relations:
            edge_reasons[edge.id] = 'RELATION_FILTER'
        elif not context_matches(edge) or edge.source not in eligible_nodes or edge.target not in eligible_nodes:
            edge_reasons[edge.id] = 'CONTEXT_FILTER'
        else:
            if direction in ('outgoing', 'both'):
                adjacency[edge.source].add(edge.target)
            if direction in ('incoming', 'both'):
                adjacency[edge.target].add(edge.source)
    distances = {}
    if focus is None:
        distances = dict.fromkeys(eligible_nodes, 0)
    elif focus in eligible_nodes:
        distances[focus] = 0
        queue = deque([focus])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency[current]):
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
    ordered = sorted((i for i in distances if hops is None or distances[i] <= hops),
                     key=lambda i: (distances[i], i))
    kept = set(ordered[:budget])
    node_reasons = {}
    for identity in nodes.keys() - kept:
        node_reasons[identity] = ('UNKNOWN_FOCUS' if unknown_focus else
            'CONTEXT_FILTER' if identity not in eligible_nodes else
            'DISCONNECTED' if identity not in distances else
            'HOP_LIMIT' if hops is not None and distances[identity] > hops else 'NODE_LIMIT')
    kept_edges = []
    for edge in view.edges:
        if edge.id not in edge_reasons and {edge.source, edge.target} <= kept:
            kept_edges.append(edge)
        elif edge.id not in edge_reasons:
            reasons = {node_reasons[i] for i in (edge.source, edge.target) if i in node_reasons}
            edge_reasons[edge.id] = next((r for r in ('UNKNOWN_FOCUS', 'CONTEXT_FILTER', 'HOP_LIMIT', 'NODE_LIMIT')
                                          if r in reasons), 'DISCONNECTED')
    omitted_nodes = sorted(node_reasons)
    omitted_edges = sorted(edge_reasons)
    inventory = _inventory([nodes[i] for i in omitted_nodes] + [edges[i] for i in omitted_edges])
    source_fingerprint = view.content_fingerprint
    frontier = []
    for identity in omitted_edges:
        edge = edges[identity]
        for anchor, other, way in ((edge.source, edge.target, 'outgoing'),
                                    (edge.target, edge.source, 'incoming')):
            if anchor not in kept:
                continue
            entry = {'anchor_id': anchor, 'direction': way, 'reason': edge_reasons[identity],
                'relation': _ref(edge.relation), 'scope': edge.attributes.get('scope', scope),
                'context_ids': list(_contexts(edge)), 'omitted_node_ids': [other] if other not in kept else [],
                'omitted_edge_ids': [identity], 'evidence_refs': list(_refs(edge.evidence_refs)),
                **_inventory([edge])}
            for field in ('transport', 'broker_realm', 'topic', 'consumer_group'):
                if edge.attributes.get(field) is not None:
                    entry[field] = _ref(edge.attributes[field])
            entry['id'] = 'topology-frontier:' + digest([VERSION, source_fingerprint, entry])
            frontier.append(entry)
    upstream = view.coverage.get('truncated') is True or view.coverage.get('upstream_truncated') is True
    if upstream:
        frontier.append({'id': 'topology-frontier:' + digest([VERSION, source_fingerprint, 'upstream']),
            'anchor_id': None, 'direction': 'global', 'reason': 'UPSTREAM_TRUNCATION',
            'omission_inventory_complete': False, 'upstream_coverage_hash': digest(view.coverage)})
    truncated = upstream or any(r in ('HOP_LIMIT', 'NODE_LIMIT') for r in (*node_reasons.values(), *edge_reasons.values()))
    criteria = {'focus_service': focus, 'direction': direction, 'max_hops': hops, 'max_nodes': budget,
        'relations': sorted(allowed_relations) if allowed_relations is not None else None, 'scope': scope,
        'context_ids': sorted(allowed_contexts) if allowed_contexts is not None else None}
    filtering = {'source_fingerprint': source_fingerprint, 'criteria': criteria,
        'status': 'UNKNOWN_FOCUS' if unknown_focus else 'FILTERED' if omitted_nodes or omitted_edges else 'UNRESTRICTED',
        'truncated': truncated, 'upstream_truncated': upstream, 'omission_inventory_complete': not upstream,
        'omitted_node_ids': omitted_nodes, 'omitted_edge_ids': omitted_edges,
        'omitted_original_interface_ids': inventory['original_interface_ids'],
        'omitted_mapping_ids': inventory['mapping_ids'], 'omitted_release_ids': inventory['release_ids'],
        'omitted_original_ids': inventory['original_ids'],
        'omitted_nodes': [{'id': i, 'reason': node_reasons[i]} for i in omitted_nodes],
        'frontier': sorted(frontier, key=lambda f: f['id']),
        'counts': {'retained_nodes': len(kept), 'retained_edges': len(kept_edges),
            'omitted_nodes': len(omitted_nodes), 'omitted_edges': len(omitted_edges),
            **{k: len(v) for k, v in inventory.items()}}}
    filtering['fingerprint'] = digest(filtering)
    coverage = deepcopy(dict(view.coverage))
    if unknown_focus:
        coverage['status'] = 'UNKNOWN'
    elif (omitted_nodes or omitted_edges or upstream) and coverage['status'] != 'UNKNOWN':
        coverage['status'] = 'PARTIAL'
    coverage.update(truncated=truncated, filtering_fingerprint=filtering['fingerprint'],
                    omission_inventory_complete=not upstream)
    filtered = replace(view, view_id='view:topology-filter:' + digest([VERSION, source_fingerprint, criteria]),
        rules_version=VERSION, nodes=tuple(nodes[i] for i in sorted(kept)),
        edges=tuple(sorted(kept_edges, key=lambda e: e.id)), coverage=coverage, generated_at=None)
    document = ViewDocument.from_dict(filtered.to_dict()).to_dict(include_generation_metadata=False)
    result = {'schema_version': 1, 'rules_version': VERSION, 'document': document, 'filtering': filtering}
    _bounded(result)
    if len(canonical(result)) > _MAX_OUTPUT_CHARS:
        _fail('FILTER_METADATA_LIMIT')
    return result

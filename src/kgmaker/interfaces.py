"""Pure HTTP provider projection over explicit workspace/provider snapshots."""
from __future__ import annotations

from copy import deepcopy
from itertools import islice, product
from pathlib import PurePosixPath
import re
from typing import Mapping

from .analysis_model import AnalysisError, digest
from .domain import normalize_api_path
from .framework import HTTP_ANNOTATIONS
from .model import KnowledgeGraph
from .architecture_model import ViewDocument, ViewNode, ViewEdge, aggregate_view_edges
from .views import project_service_inventory
from .workspace import resolve_service_ownership, split_id, source_key

RULES_VERSION = 'http-providers-1'
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}
SOURCE_PROVIDERS = {'spring-source', 'ktor-source', 'openapi-json', 'openapi-yaml'}
# Shape validation only: no class lookup, ID parsing or signature rewriting.
_FIELD_DESCRIPTOR = r'\[*(?:[BCDFIJSZ]|L[^.;\[()]+;)'
_METHOD_DESCRIPTOR = re.compile(r'\((?:' + _FIELD_DESCRIPTOR + r')*\)(?:V|' + _FIELD_DESCRIPTOR + r')\Z')


class InterfaceProjectionError(ValueError):
    def __init__(self, code, message):
        self.diagnostic = {'code': code, 'message': message}
        super().__init__(code + ': ' + message)


def _fail(code, message):
    raise InterfaceProjectionError(code, message)


def _registration(record, graph, path):
    if not isinstance(record, Mapping) or type(record.get('version')) is not int or record['version'] != 1:
        _fail('INVALID_HTTP_REGISTRATION', 'Unsupported registration metadata version')
    required = {'version', 'provider', 'http_method', 'original_route', 'normalized_route', 'method_route',
                'class_prefix', 'source_path', 'source_sha256', 'source_line', 'variant_fingerprint', 'unresolved_reasons'}
    if not required.issubset(record):
        _fail('INVALID_HTTP_REGISTRATION', 'Missing required registration fields')
    if (not isinstance(record.get('provider'), str) or record['provider'] not in SOURCE_PROVIDERS
            or not isinstance(record.get('http_method'), str) or record['http_method'] not in METHODS):
        _fail('INVALID_HTTP_REGISTRATION', 'Unsupported provider or method')
    original = record.get('source_path')
    if (not isinstance(original, str) or not original or PurePosixPath(original).is_absolute()
            or '..' in PurePosixPath(original).parts or PurePosixPath(original).as_posix() != original):
        _fail('INVALID_HTTP_REGISTRATION', 'Registration source path must be canonical and relative')
    checksum = record.get('source_sha256')
    if (not isinstance(checksum, str) or len(checksum) != 64
            or any(c not in '0123456789abcdef' for c in checksum) or graph.files.get(path) != checksum):
        _fail('HTTP_SOURCE_HASH_MISMATCH', 'Registration is not bound to its selected source snapshot')
    for key in ['original_route', 'normalized_route', 'method_route', 'class_prefix']:
        value = record.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 8192
                                  or any(c in value for c in ['\0', '\n', '\r', '?', '#'])
                                  or value.startswith('//') or '://' in value):
            _fail('INVALID_HTTP_REGISTRATION', 'Unsafe or malformed route component')
    if record.get('normalized_route') is not None and not record['normalized_route'].startswith('/'):
        _fail('INVALID_HTTP_REGISTRATION', 'Normalized route must be an absolute path component')
    reasons = record.get('unresolved_reasons')
    if not isinstance(reasons, list) or any(not isinstance(value, str) for value in reasons):
        _fail('INVALID_HTTP_REGISTRATION', 'Registration reasons must be a string array')
    if record.get('source_line') is not None and (type(record['source_line']) is not int or record['source_line'] < 1):
        _fail('INVALID_HTTP_REGISTRATION', 'Source line must be positive')
    fingerprint = record.get('variant_fingerprint')
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
        _fail('INVALID_HTTP_REGISTRATION', 'Missing registration variant fingerprint')
    if record['normalized_route'] is not None and (record['original_route'] is None
            or normalize_api_path(record['original_route']) != record['normalized_route']
            or reasons or '${' in record['original_route'] or '{{' in record['original_route']):
        _fail('INVALID_HTTP_REGISTRATION', 'Normalized route disagrees with captured literal route')



def _mirror_mapping(symbol, *, class_level=False):
    annotations = symbol.get('annotations')
    if not isinstance(annotations, list):
        return None, ['COMPILER_ANNOTATION_METADATA_UNKNOWN']
    matches = []
    for annotation in annotations:
        if not isinstance(annotation, Mapping) or not isinstance(annotation.get('name'), str):
            return None, ['COMPILER_ANNOTATION_METADATA_UNKNOWN']
        name = annotation['name']
        simple = name.rsplit('.', 1)[-1]
        if name.startswith('org.springframework.web.bind.annotation.') and simple in HTTP_ANNOTATIONS:
            if not class_level or simple == 'RequestMapping':
                matches.append(annotation)
    if len(matches) > 1:
        return None, ['AMBIGUOUS_SPRING_MAPPING']
    if not matches:
        supertypes = symbol.get('supertypes')
        hierarchy = symbol.get('type_hierarchy')
        complete_root = (isinstance(hierarchy, Mapping) and type(hierarchy.get('schema_version')) is int
                         and hierarchy['schema_version'] == 1 and hierarchy.get('complete') is True
                         and isinstance(hierarchy.get('types'), list)
                         and (supertypes == hierarchy['types'] == ['java.lang.Object']
                              or symbol.get('kind') == 'interface' and supertypes == hierarchy['types'] == []))
        if class_level and complete_root and isinstance(supertypes, list) and not any(
                not isinstance(name, str) or name != 'java.lang.Object' for name in supertypes):
            # Unknown composed annotations can carry another mapping prefix.
            allowed = {'org.springframework.web.bind.annotation.RestController',
                       'org.springframework.stereotype.Controller', 'java.lang.Deprecated'}
            if all(item['name'] in allowed for item in annotations):
                return {'name': 'RequestMapping', 'values': {}, 'paths': ['']}, []
        return None, ['SPRING_CLASS_PREFIX_UNKNOWN' if class_level else 'SPRING_METHOD_MAPPING_UNKNOWN']
    annotation = matches[0]
    values = annotation.get('values')
    if not isinstance(values, Mapping):
        return None, ['COMPILER_ANNOTATION_METADATA_UNKNOWN']
    def strings(key):
        value = values.get(key, [])
        if isinstance(value, str):
            return [value]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return None
        return value
    paths, aliases = strings('path'), strings('value')
    if paths is None or aliases is None:
        return None, ['COMPILER_ANNOTATION_METADATA_UNKNOWN']
    if paths and aliases and set(paths) != set(aliases):
        return None, ['CONFLICTING_ROUTE_ALIASES']
    return {'name': annotation['name'].rsplit('.', 1)[-1], 'values': dict(values),
            'paths': sorted(set(paths or aliases or ['']))}, []


def _canonical_owner(value):
    return isinstance(value, str) and bool(value) and not any(char.isspace() for char in value)


def _compiler_source_binding(symbol, node, context, graph):
    """Exact existing compiler declaration tuple; never infer absent metadata."""
    if not isinstance(symbol, Mapping) or node is None:
        return False
    repo, path = context.get('repo_id'), node.path
    if not isinstance(repo, str) or not isinstance(path, str) or not path.startswith(source_key(repo, '')):
        return False
    relative = path[len(source_key(repo, '')):]
    if (not relative or PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts
            or PurePosixPath(relative).as_posix() != relative):
        return False
    checksum = graph.files.get(path)
    captured = context.get('source_files')
    if (not isinstance(checksum, str) or len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum)
            or not isinstance(captured, Mapping) or captured.get(path) != checksum):
        return False
    position = symbol.get('range')
    if (not isinstance(position, Mapping) or type(node.line) is not int or node.line < 1
            or type(position.get('start_line')) is not int or position['start_line'] != node.line):
        return False
    try:
        if split_id(symbol.get('id', ''))[0] != repo or split_id(context.get('id', ''))[0] != repo:
            return False
    except (AnalysisError, AttributeError, ValueError):
        return False
    return (symbol.get('id') == node.id and symbol.get('kind') == node.kind
            and isinstance(symbol.get('name'), str) and bool(symbol['name']) and symbol['name'] == node.name
            and node.signature == (symbol.get('descriptor') or symbol.get('type'))
            and symbol.get('path') == path and symbol.get('sha256') == checksum
            and symbol.get('scope') == node.scope == context.get('scope')
            and symbol.get('context_id') == context.get('id')
            and (symbol.get('repo_id') is None or symbol['repo_id'] == repo)
            and (symbol.get('module') is None or symbol['module'] == context.get('module')))


def _framework_edge_binding(edge, handler, endpoint, context, evidence, checksum):
    if (endpoint.path != handler.path or endpoint.scope != handler.scope
            or type(endpoint.line) is not int or endpoint.line != handler.line or edge.source_file != handler.path
            or type(edge.source_line) is not int or edge.source_line != handler.line or tuple(edge.context_ids) != (context['id'],)):
        return False
    if not edge.evidence_ids:
        return False
    for identity in edge.evidence_ids:
        proof = evidence.get(identity, {})
        if (proof.get('kind') != 'FRAMEWORK_DERIVED' or proof.get('source') != handler.id
                or proof.get('target') != endpoint.id or proof.get('relation') != 'exposes_endpoint'
                or proof.get('context_ids') != [context['id']] or proof.get('source_file') != handler.path
                or type(proof.get('source_line')) is not int or proof['source_line'] != handler.line
                or ('sha256' in proof and proof['sha256'] != checksum)
                or proof.get('framework_rules') != context.get('framework_rule_versions', {})):
            return False
    return True


def _compiler_registrations(handler, endpoint, symbols, graph, context, by_id):
    symbol = symbols.get(handler.id)
    if not isinstance(symbol, Mapping):
        _fail('INVALID_HTTP_COMPILER_METADATA', 'Handler metadata must be an object')
    context_id = symbol.get('context_id')
    owner = symbol.get('owner')
    classes = [item for item in symbols.values() if isinstance(item.get('kind'), str)
               and item['kind'] in {'class', 'interface', 'record'}
               and _canonical_owner(owner) and _canonical_owner(item.get('owner')) and item['owner'] == owner
               and _compiler_source_binding(item, by_id.get(item.get('id')), context, graph)
               and item.get('path') == handler.path and item.get('context_id') == context_id]
    class_symbol = classes[0] if len(classes) == 1 else None
    class_mapping, class_reasons = (_mirror_mapping(class_symbol, class_level=True)
                                    if class_symbol else (None, ['SPRING_CLASS_PREFIX_UNKNOWN']))
    method_mapping, method_reasons = _mirror_mapping(symbol)
    endpoint_meta = endpoint.metadata or {}
    if not isinstance(endpoint_meta, Mapping):
        _fail('INVALID_HTTP_COMPILER_METADATA', 'Endpoint metadata must be an object')
    class_paths = class_mapping['paths'] if class_mapping else [None]
    method_paths = method_mapping['paths'] if method_mapping else [endpoint_meta.get('endpoint_path')]
    method_reasons = list(method_reasons)
    if method_mapping:
        method_name = method_mapping['name']
        verb = HTTP_ANNOTATIONS.get(method_name)
        if verb:
            verbs = [verb]
        else:
            selected = method_mapping['values'].get('method', [])
            if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
                selected = []
                method_reasons.append('HTTP_METHOD_UNKNOWN')
            verbs = sorted({item.rsplit('.', 1)[-1] for item in selected
                            if item.rsplit('.', 1)[-1] in METHODS}) or [None]
    else:
        fallback = endpoint_meta.get('http_method')
        verbs = [fallback if isinstance(fallback, str) and fallback in METHODS else None]
    known_method = endpoint_meta.get('http_method')
    known_path = endpoint_meta.get('endpoint_path')
    if ((known_method is not None and (not isinstance(known_method, str) or known_method not in verbs))
            or (known_path is not None and (not isinstance(known_path, str)
                or known_path not in {path or '/' for path in method_paths if isinstance(path, str)}))):
        method_reasons.append('HTTP_FRAMEWORK_ENDPOINT_MISMATCH')
    count = len(class_paths) * len(method_paths) * len(verbs)
    position = symbol.get('range') or {}
    if not isinstance(position, Mapping):
        _fail('INVALID_HTTP_COMPILER_METADATA', 'Handler range must be an object')
    line = position.get('start_line')
    if line is not None and (type(line) is not int or line < 1):
        _fail('INVALID_HTTP_COMPILER_METADATA', 'Handler line must be positive')
    for prefix, method_path, verb in islice(product(class_paths, method_paths, verbs), 64):
        reasons = [*class_reasons, *method_reasons]
        if count > 64:
            reasons.append('HTTP_ROUTE_VARIANTS_TRUNCATED')
        def component(value):
            if value is None:
                return None
            if (not isinstance(value, str) or len(value) > 8192 or any(c in value for c in '\r\n\0')
                    or '://' in value or value.startswith('//')):
                reasons.append('UNSUPPORTED_ROUTE')
                return None
            if '?' in value or '#' in value:
                reasons.append('ROUTE_QUERY_OMITTED')
            return value.split('?', 1)[0].split('#', 1)[0]
        prefix, method_path = component(prefix), component(method_path)
        original = prefix.rstrip('/') + '/' + method_path.lstrip('/') if prefix is not None and method_path is not None else None
        if original is None or any('${' in value or '{{' in value for value in [prefix, method_path] if value is not None):
            reasons.append('DYNAMIC_ROUTE')
        if verb not in METHODS:
            reasons.append('HTTP_METHOD_UNKNOWN')
        normalized = normalize_api_path(original) if original is not None and not reasons else None
        # Mirrors are explicit compiler inputs, never source-text reparsing.
        declaration = [owner if _canonical_owner(owner) else None, symbol['name'], symbol['descriptor']]
        variant = digest([declaration, class_mapping, method_mapping, prefix, method_path, verb])
        yield {'provider': 'spring-compiler', 'http_method': verb, 'original_route': original,
               'normalized_route': normalized, 'class_prefix': prefix, 'method_route': method_path,
               'source_path': handler.path, 'source_sha256': graph.files.get(handler.path),
               'source_line': line,
               'variant_fingerprint': variant, 'declaration_identity': digest(declaration) if _canonical_owner(owner) else None,
               'unresolved_reasons': sorted(set(reasons))}, class_symbol


def project_http_providers(workspace, graph, *, scope='production', selected_contexts=None, source_coverage=None):
    """Project provider registrations; contracts never imply implementation/runtime.

    No source parsing, process, network or persistent store exists in this layer.
    Source metadata is accepted only through the exact qualified declaration edge.
    """
    if not isinstance(workspace, Mapping) or not isinstance(graph, KnowledgeGraph):
        _fail('INVALID_HTTP_SNAPSHOT', 'Expected a loaded workspace and provider graph')
    before = deepcopy((workspace, graph.to_dict(), source_coverage))
    inventory = project_service_inventory(workspace, graph, scope=scope,
                                          selected_contexts=selected_contexts, source_coverage=source_coverage)
    nodes = [node for node in inventory.nodes if node.kind == 'service']
    node_ids = {node.id for node in nodes}
    by_id = {node.id: node for node in graph.nodes}
    contexts = {context['id']: context for context in graph.contexts if isinstance(context.get('id'), str)}
    provenance = {record['id']: deepcopy(record) for record in inventory.provenance}
    diagnostics = [dict(item) for item in inventory.diagnostics]
    edges = []
    found, excluded = 0, 0
    seen = set()
    selected_by_service = inventory.context_selection.get('services', {})
    selected_framework_contexts = {
        row['context_id'] for service in selected_by_service.values() for row in service.get('contexts', [])
        if isinstance(row.get('context_id'), str)}
    # A requested but stale/bad source capture still receives fail-closed tuple
    # validation. Sibling captures are historical facts, never current inputs.
    requested_framework_contexts = set((selected_contexts or {}).values())
    declaration_keys = set()
    for item in graph.edges:
        origin = by_id.get(item.source)
        if item.kind == 'declares_endpoint' and origin is not None and origin.scope == scope:
            if (not isinstance(origin.path, str) or item.source_line is not None
                    and (type(item.source_line) is not int or item.source_line < 1)):
                _fail('INVALID_HTTP_DECLARATION', 'Declaration path/line must be well formed')
            declaration_keys.add((item.target, origin.path, item.source_line))

    def emit(record, source, endpoint, edge, context_id, repo, *, evidence_kind='SYNTAX_CANDIDATE', handler_ids=(), class_id=None):
        nonlocal found
        path = source.path
        context = contexts[context_id]
        owner = resolve_service_ownership({'id': source.id, 'path': source.path, 'repo_id': repo,
            'module': context.get('module'), 'context_id': context_id}, workspace.get('service_ownership'),
            context_id=context_id)
        service = owner.get('owner_id') if owner.get('status') == 'RESOLVED' else None
        reasons = list(record['unresolved_reasons'])
        if service is None or 'service:' + service not in node_ids:
            service = None
            reasons.append('HTTP_SERVICE_OWNERSHIP_UNKNOWN')
        if service is None and evidence_kind != 'SYNTAX_CANDIDATE':
            diagnostics.append({'code': 'HTTP_SERVICE_OWNERSHIP_UNKNOWN', 'source_path': path, 'context_id': context_id})
            return
        if service is not None:
            rows = selected_by_service.get(service, {}).get('contexts', [])
            eligible = {row.get('context_id') for row in rows} | {
                item for row in rows for item in row.get('candidate_context_ids', [])}
            if evidence_kind != 'SYNTAX_CANDIDATE':
                eligible = {row.get('context_id') for row in rows}
            if context_id not in eligible:
                diagnostics.append({'code': 'HTTP_CONTEXT_NOT_SELECTED', 'source_path': path,
                                    'context_id': context_id})
                return
        key = digest([service, repo, path, context_id, record, evidence_kind, handler_ids])
        if key in seen:
            return
        seen.add(key)
        contract = record['provider'].startswith('openapi-')
        normalized = record['normalized_route']
        realm = service or 'unknown:' + repo + ':' + path
        selector = context.get('selection_key') or digest([repo, context.get('module'), context.get('source_set'), scope, context.get('mode')])
        # A canonical compiler declaration survives source relocation/line edits.
        # Weak source expressions retain a locator and an explicit UNKNOWN boundary.
        location = None if handler_ids and record.get('declaration_identity') else [path, record['source_line']]
        unknown_anchor = digest([repo, location, record['provider'], record['variant_fingerprint'], selector])
        logical_id = 'interface:http:' + digest([realm, record['http_method'], normalized or 'unknown:' + unknown_anchor])[:32]
        variant = graph.files[path] if contract else record['variant_fingerprint']
        identity = logical_id + ':variant:' + digest([location, variant, selector, evidence_kind])[:24]
        evidence_id = 'ev:http-registration:' + key
        current = evidence_kind != 'SYNTAX_CANDIDATE' and any(row.get('context_id') == context_id and row.get('status') == 'CURRENT' for row in rows)
        freshness = 'CURRENT' if current else 'UNKNOWN'
        provenance[evidence_id] = {'id': evidence_id, 'evidence_kind': evidence_kind,
            'freshness': freshness, 'polarity': 'UNKNOWN', 'source_id': source.id,
            'source_file': path, 'source_line': record['source_line'], 'content_hash': graph.files[path],
            'context_ids': [context_id], 'original_evidence_ids': list(edge.evidence_ids)}
        if contract:
            reasons.append('CONTRACT_DECLARATION_ONLY')
        elif not handler_ids:
            reasons.append('SOURCE_HANDLER_UNKNOWN')
        attrs = {'scope': scope, 'context_ids': [context_id], 'service_id': service,
            'logical_id': logical_id, 'direction': 'PROVIDED', 'protocol': 'HTTP',
            'http_method': record['http_method'], 'original_route': record['original_route'],
            'normalized_route': normalized, 'method_route': record['method_route'],
            'class_prefix': record['class_prefix'], 'handler_ids': list(handler_ids),
            'registration_variant': record['variant_fingerprint'],
            'contract_fingerprint': graph.files[path] if contract else None,
            'registration_kind': 'CONTRACT_DECLARATION' if contract else 'FRAMEWORK_DECLARATION' if handler_ids else 'SOURCE_CANDIDATE',
            'implementation_status': 'CONTRACT_ONLY' if contract else 'HANDLER_DECLARATION' if handler_ids else 'UNKNOWN',
            'deployment_status': 'UNKNOWN', 'runtime_status': 'UNKNOWN',
            'unresolved_reasons': sorted(set(reasons)), 'source_path': path}
        status = 'RESOLVED' if handler_ids and normalized is not None and service and not reasons else 'UNRESOLVED'
        originals = tuple(sorted({edge.source, edge.target, *handler_ids, *([class_id] if class_id else [])}))
        nodes.append(ViewNode(identity, 'http_interface', (record['http_method'] or 'HTTP') + ' ' + (normalized or 'UNKNOWN'),
            original_ids=originals, owner_id='service:' + service if service else None,
            evidence_refs=(evidence_id,), attributes=attrs, evidence_kinds=(evidence_kind,),
            resolution_status=status, freshness=freshness, unknown_refs=(evidence_id,)))
        found += 1
        for reason in sorted(set(reasons)):
            diagnostics.append({'code': reason, 'interface_id': identity, 'source_path': path})
        if service:
            edges.append(ViewEdge('edge:http-provider:' + key, 'service:' + service, identity,
                'declares_http_interface', evidence_refs=(evidence_id,),
                attributes={'scope': scope, 'context_ids': [context_id]},
                evidence_kinds=(evidence_kind,), freshness=freshness, resolution_status=status, unknown_refs=(evidence_id,)))

    for edge in graph.edges:
        if edge.kind != 'declares_endpoint':
            continue  # HTTP consumers and frontend/client calls are outside this projection.
        source, endpoint = by_id.get(edge.source), by_id.get(edge.target)
        if source is None or endpoint is None or endpoint.kind != 'api_endpoint':
            continue
        if source.scope != scope:
            excluded += 1
            continue
        try:
            repo, _ = split_id(source.id)
            endpoint_repo, _ = split_id(endpoint.id)
        except (ValueError, AnalysisError):
            _fail('UNQUALIFIED_HTTP_DECLARATION', 'Provider declarations require a repository realm')
        if repo != endpoint_repo:
            _fail('HTTP_REALM_MISMATCH', 'Provider endpoint belongs to a different repository')
        if endpoint.metadata is not None and not isinstance(endpoint.metadata, Mapping):
            _fail('INVALID_HTTP_REGISTRATION', 'Endpoint metadata must be an object')
        records = (endpoint.metadata or {}).get('http_registrations')
        if records is None:
            diagnostics.append({'code': 'LEGACY_HTTP_REGISTRATION_UNKNOWN', 'source_path': source.path,
                                'message': 'Legacy merged endpoint identity cannot prove each original route'})
            continue
        if not isinstance(records, list) or len(records) > 10000:
            _fail('INVALID_HTTP_REGISTRATION', 'Expected a bounded registration list')
        applicable_contexts = [identity for identity in edge.context_ids
                               if identity in contexts and contexts[identity].get('scope') == scope
                               and contexts[identity].get('repo_id') == repo]
        if not applicable_contexts:
            diagnostics.append({'code': 'HTTP_CONTEXT_UNKNOWN', 'source_path': source.path})
            continue
        for record in records:
            if not isinstance(record, Mapping):
                _fail('INVALID_HTTP_REGISTRATION', 'Registration must be an object')
            if not isinstance(record.get('source_path'), str):
                _fail('INVALID_HTTP_REGISTRATION', 'Registration source path must be a string')
            path = source_key(repo, record['source_path'])
            _registration(record, graph, path)
            if 'UNSUPPORTED_ROUTE' in record['unresolved_reasons']:
                diagnostics.append({'code': 'HTTP_UNSUPPORTED_ROUTE', 'source_path': path,
                                    'source_line': record['source_line']})
                continue
            declaration = (endpoint.id, path, record['source_line']) in declaration_keys
            if not declaration:
                _fail('HTTP_DECLARATION_MISMATCH', 'Registration has no exact source declaration edge')
            if record['normalized_route'] is not None and not split_id(endpoint.id)[1].endswith(
                    'api_endpoint:' + record['http_method'] + ':' + record['normalized_route'].lower()):
                _fail('HTTP_DECLARATION_MISMATCH', 'Registration disagrees with the original endpoint identity')
            if path != source.path or record['source_line'] != edge.source_line:
                continue
            for context_id in applicable_contexts:
                context = contexts[context_id]
                emit(record, source, endpoint, edge, context_id, repo)
    symbols = {item['id']: item for item in graph.symbols if isinstance(item.get('id'), str)}
    evidence = {item['id']: item for item in graph.evidence}
    for edge in graph.edges:
        if edge.kind != 'exposes_endpoint':
            continue
        handler, endpoint = by_id.get(edge.source), by_id.get(edge.target)
        if handler is None or endpoint is None or endpoint.kind != 'spring_endpoint':
            continue
        if handler.scope != scope:
            excluded += 1
            continue
        if edge.evidence_kind != 'FRAMEWORK_DERIVED':
            diagnostics.append({'code': 'HTTP_FRAMEWORK_EVIDENCE_UNKNOWN', 'source_path': handler.path})
            continue
        active_contexts = []
        for context_id in edge.context_ids:
            if context_id in selected_framework_contexts or context_id in requested_framework_contexts:
                active_contexts.append(context_id)
            else:
                diagnostics.append({'code': 'HTTP_CONTEXT_NOT_SELECTED', 'source_id': edge.source,
                    'target_id': edge.target, 'context_id': context_id,
                    'original_evidence_ids': list(edge.evidence_ids),
                    'freshness': 'STALE' if contexts.get(context_id, {}).get('freshness') == 'STALE' else 'UNKNOWN'})
        if not active_contexts:
            continue
        try:
            repo = split_id(handler.id)[0]
            if split_id(endpoint.id)[0] != repo:
                _fail('HTTP_REALM_MISMATCH', 'Framework endpoint belongs to another repository')
        except (ValueError, AnalysisError):
            _fail('UNQUALIFIED_HTTP_DECLARATION', 'Framework handlers require a repository realm')
        if not isinstance(handler.path, str) or handler.path not in graph.files:
            _fail('HTTP_SOURCE_HASH_MISMATCH', 'Framework handler has no source snapshot')
        for context_id in active_contexts:
            context = contexts.get(context_id, {})
            if context.get('scope') != scope or context.get('repo_id') != repo:
                diagnostics.append({'code': 'HTTP_CONTEXT_UNKNOWN', 'source_path': handler.path})
                continue
            symbol_context = symbols.get(handler.id)
            if not isinstance(symbol_context, Mapping) or symbol_context.get('context_id') != context_id:
                _fail('HTTP_CONTEXT_MISMATCH', 'Handler declaration belongs to another compiler context')
            descriptor = symbol_context.get('descriptor')
            if (not isinstance(descriptor, str) or len(descriptor) > 8192
                    or _METHOD_DESCRIPTOR.fullmatch(descriptor) is None):
                diagnostics.append({'code': 'HTTP_HANDLER_SIGNATURE_UNKNOWN', 'source_id': handler.id,
                    'context_id': context_id, 'original_evidence_ids': list(edge.evidence_ids)})
                continue
            captured = context.get('source_files', {})
            if not isinstance(captured, Mapping) or captured.get(handler.path) != graph.files[handler.path]:
                _fail('HTTP_SOURCE_HASH_MISMATCH', 'Compiler handler is outside its selected source snapshot')
            if not _compiler_source_binding(symbol_context, handler, context, graph):
                _fail('HTTP_COMPILER_BINDING_MISMATCH', 'Handler metadata disagrees with its exact source/context declaration')
            if not _framework_edge_binding(edge, handler, endpoint, context, evidence, graph.files[handler.path]):
                diagnostics.append({'code': 'HTTP_FRAMEWORK_BINDING_UNKNOWN', 'source_id': handler.id,
                    'target_id': endpoint.id, 'context_ids': [context_id], 'original_evidence_ids': list(edge.evidence_ids)})
                continue
            for record, class_symbol in _compiler_registrations(handler, endpoint, symbols, graph, context, by_id):
                if 'UNSUPPORTED_ROUTE' in record['unresolved_reasons']:
                    diagnostics.append({'code': 'HTTP_UNSUPPORTED_ROUTE', 'source_path': handler.path})
                    continue
                emit(record, handler, endpoint, edge, context_id, repo,
                     evidence_kind='FRAMEWORK_DERIVED', handler_ids=(handler.id,),
                     class_id=class_symbol['id'] if class_symbol else None)
    # Existing runtime imports are a separate lifecycle contract. A graph edge or
    # metadata label alone cannot bind an observed registration to this selected
    # HTTP variant. Keep the boundary and original refs visible without inventing
    # a runtime import format or an inferred route join.
    for edge in graph.edges:
        if edge.kind != 'runtime_framework_observation':
            continue
        source = by_id.get(edge.source)
        if source is None or source.scope != scope:
            continue
        diagnostics.append({'code': 'HTTP_RUNTIME_BINDING_UNKNOWN',
            'source_id': edge.source, 'target_id': edge.target,
            'context_ids': list(edge.context_ids), 'original_evidence_ids': list(edge.evidence_ids),
            'message': 'Runtime-to-interface lifecycle/variant binding is not supported; imported edge is not an availability claim.'})
    result = aggregate_view_edges(edges, tuple(provenance.values()), scope=scope, diagnostics=diagnostics)
    document = ViewDocument('view:http-providers:' + workspace['workspace_id'] + ':' + scope,
        'interfaces', digest([inventory.baseline_fingerprint, graph.files, RULES_VERSION]), RULES_VERSION,
        scope, inventory.context_selection, nodes=tuple(nodes), edges=result['edges'],
        diagnostics=result['diagnostics'], coverage={'status': 'PARTIAL' if found else 'UNKNOWN',
            'counts': {'found': found,
                       'resolved': sum(node.kind == 'http_interface' and node.resolution_status == 'RESOLVED' for node in nodes),
                       'unresolved': sum(node.kind == 'http_interface' and node.resolution_status != 'RESOLVED' for node in nodes),
                       'excluded': excluded},
            'reasons': ['Found counts emitted HTTP variants; excluded counts declaration edges outside the selected scope.']},
        provenance=result['provenance'], limits=('Static registrations and contracts do not prove deployment or data availability.',))
    ViewDocument.from_dict(document.to_dict())
    if before != (workspace, graph.to_dict(), source_coverage):
        _fail('HTTP_INPUT_MUTATED', 'Provider projection changed a caller snapshot')
    return document


CONSUMER_RULES_VERSION = 'http-consumers-1'
_CLIENT_STATES = {'UNKNOWN', 'DEFINITION_ONLY', 'UNSUBSCRIBED_WITHIN_SCOPE',
                  'STATIC_TRIGGER', 'CONDITIONAL_STATIC_TRIGGER', 'DECLARATION_ONLY',
                  'FEIGN_INVOCATION_INTENT'}


def project_http_consumers(workspace, graph, *, scope='production', selected_contexts=None, source_coverage=None):
    """Project existing typed client facts; no client or resolver is executed.

    A terminal proves static invocation intent, never observed network traffic.
    Feign declarations and individual consuming call sites retain separate IDs.
    """
    from .http_execution import VERSION, redact_uri_text
    from .workspace import qualified
    from .views import ServiceInventoryError, ContextSelectionError, _summarize_view_evidence, _canonical_polarity

    if not isinstance(workspace, Mapping) or not isinstance(graph, KnowledgeGraph):
        _fail('INVALID_HTTP_SNAPSHOT', 'Expected a loaded workspace and provider graph')
    before = deepcopy((workspace, graph.to_dict(), source_coverage))
    try:
        inventory = project_service_inventory(workspace, graph, scope=scope,
            selected_contexts=selected_contexts, source_coverage=source_coverage)
    except (ServiceInventoryError, ContextSelectionError) as error:
        _fail('INVALID_HTTP_SNAPSHOT', str(error))
    nodes = [node for node in inventory.nodes if node.kind == 'service']
    services = {node.id for node in nodes}
    contexts = {c['id']: c for c in graph.contexts if isinstance(c.get('id'), str)}
    by_id = {n.id: n for n in graph.nodes}
    symbols = {s['id']: s for s in graph.symbols if isinstance(s.get('id'), str)}
    sites = {s['id']: s for s in graph.call_sites if isinstance(s.get('id'), str)}
    proofs = {e['id']: e for e in graph.evidence if isinstance(e.get('id'), str)}
    selected = inventory.context_selection.get('services', {})
    eligible = {row.get('context_id') for service in selected.values()
                for row in service.get('contexts', []) if row.get('status') == 'CURRENT'}
    requested = set((selected_contexts or {}).values())
    provenance = {p['id']: deepcopy(p) for p in inventory.provenance}
    diagnostics = [dict(d) for d in inventory.diagnostics]
    edges, found = [], 0
    request_edges = {}
    for edge in graph.edges:
        if edge.kind in {'defines_http_request','may_execute_http_request'}:
            request_edges.setdefault((edge.target,edge.kind,edge.source),[]).append(edge)

    def fail(message):
        _fail('INVALID_HTTP_CONSUMER_BINDING', message)

    def local(identity, repo):
        try:
            owner, raw = split_id(identity)
        except (AnalysisError, AttributeError, TypeError, ValueError):
            fail('Identity must be canonical and repository-qualified')
        if owner != repo:
            fail('Identity belongs to a different repository')
        return raw

    def text(value):
        return isinstance(value, str) and bool(value) and len(value) <= 8192

    def strings(value):
        return (isinstance(value, list) and len(value) <= 1000
                and all(text(item) for item in value) and len(set(value)) == len(value))

    def position(value):
        return (isinstance(value, Mapping)
                and set(value).issubset({'start','end','start_line','end_line','start_column','end_column'})
                and all(type(value.get(k)) is int for k in ('start','end','start_line','end_line'))
                and 0 <= value['start'] <= value['end']
                and 1 <= value['start_line'] <= value['end_line']
                and all(k not in value or type(value[k]) is int and value[k] >= 1 for k in ('start_column','end_column')))

    def declaration(identity, context):
        node = by_id.get(identity)
        if not _compiler_source_binding(symbols.get(identity), node, context, graph) or node.scope != scope:
            fail('Caller declaration does not match the selected canonical source tuple')
        return node

    def site(identity, context, expected_caller=None):
        value = sites.get(identity)
        if not isinstance(value, Mapping) or not text(value.get('caller')):
            fail('Missing original compiler call site')
        caller = declaration(value['caller'], context)
        sha = graph.files.get(caller.path)
        span, parent = value.get('range'), symbols[caller.id].get('range')
        if (value.get('context_id') != context['id'] or value.get('path') != caller.path
                or value.get('sha256') != sha or not position(span) or not position(parent)
                or not parent['start'] <= span['start'] <= span['end'] <= parent['end']
                or not parent['start_line'] <= span['start_line'] <= span['end_line'] <= parent['end_line']
                or value.get('scope', scope) != scope
                or expected_caller is not None and caller.id != expected_caller):
            fail('Call site source, range, caller or selected context is inconsistent')
        local_caller = local(caller.id, context['repo_id'])
        expected = qualified(context['repo_id'], 'call:' + local_caller + ':' + sha
                             + ':' + str(span['start']) + ':' + str(span['end']))
        if value.get('id') != expected:
            fail('Call site identity is not its canonical source occurrence')
        return value, caller

    def binding(request, source, locator, call_id, relation, context):
        matches = request_edges.get((request.id,relation,source),[])
        if len(matches) != 1:
            fail('Missing or ambiguous original request evidence edge')
        edge = matches[0]
        path, span, sha = locator['path'], locator['range'], locator['sha256']
        if (edge.evidence_kind != 'FRAMEWORK_DERIVED' or tuple(edge.context_ids) != (context['id'],)
                or edge.source_file != path or type(edge.source_line) is not int
                or edge.source_line != span['start_line'] or not edge.evidence_ids):
            fail('Request edge does not match its canonical source tuple')
        for identity in edge.evidence_ids:
            proof = proofs.get(identity)
            if (not isinstance(proof, Mapping) or proof.get('kind') != 'FRAMEWORK_DERIVED'
                    or proof.get('source') != source or proof.get('target') != request.id
                    or proof.get('relation') != relation or proof.get('call_site') != call_id
                    or proof.get('context_ids') != [context['id']] or proof.get('rule') != VERSION
                    or proof.get('source_file') != path or proof.get('source_range') != span
                    or proof.get('sha256') != sha or proof.get('runtime_execution') != 'NOT_OBSERVED'
                    or proof.get('runtime_availability') != 'UNKNOWN'):
                fail('Original request proof tuple is inconsistent')
        return edge

    for request in graph.nodes:
        if request.kind != 'http_request_definition' or request.scope != scope:
            continue
        md = request.metadata
        if not isinstance(md, Mapping):
            fail('Typed request metadata must be an object')
        cid = md.get('context_id')
        if not isinstance(cid, str):
            fail('Typed request needs a primitive context identity')
        if cid not in eligible and cid not in requested:
            diagnostics.append({'code':'HTTP_CONSUMER_CONTEXT_NOT_SELECTED','source_id':request.id,'context_id':cid})
            continue
        context = contexts.get(cid)
        if not context or context.get('scope') != scope or context.get('language') != 'jvm':
            fail('Request context is not the selected JVM scope')
        rules = context.get('framework_rule_versions')
        if not isinstance(rules, Mapping):
            fail('Malformed framework rule snapshot')
        if md.get('rule_version') != VERSION or rules.get('http') != VERSION:
            diagnostics.append({'code':'HTTP_CONSUMER_RULE_UNKNOWN','source_id':request.id})
            continue
        family, state = md.get('family'), md.get('execution_status')
        if (not isinstance(family, str) or family not in {'WEBCLIENT','RESTCLIENT','FEIGN'}
                or not isinstance(state, str) or state not in _CLIENT_STATES
                or type(md.get('publisher')) is not bool or type(md.get('conditional')) is not bool
                or not strings(md.get('chain_call_site_ids')) or not strings(md.get('terminal_call_site_ids'))
                or not strings(md.get('unknown_reasons'))
                or not all(re.fullmatch(r'[A-Z0-9_]{1,128}', x) for x in md['unknown_reasons'])
                or md.get('runtime_execution') != 'NOT_OBSERVED' or md.get('runtime_availability') != 'UNKNOWN'
                or md.get('method') is not None and (not isinstance(md['method'], str) or md['method'] not in METHODS)
                or not text(md.get('uri_status')) or not text(md.get('caller'))
                or md.get('repo_id') != context.get('repo_id') or md.get('module') != context.get('module')
                or md.get('source_set') != context.get('source_set')):
            fail('Malformed typed request fields')
        repo = context['repo_id']
        caller = declaration(md['caller'], context)
        local(request.id, repo)
        if (request.path != caller.path or request.scope != caller.scope
                or type(request.line) is not int):
            fail('Request node does not match the canonical declaring source')
        origin = md.get('origin_call_site')
        if family == 'FEIGN':
            if origin is not None or md.get('declaration') != caller.id or not text(md.get('client_type')):
                fail('Feign declaration metadata is inconsistent')
            declaration(md['client_type'], context)
            expected_id = qualified(repo, 'http-request:' + digest({'context':local(cid,repo),
                'client':local(md['client_type'],repo), 'method':local(caller.id,repo)}))
            locator = symbols[caller.id]
        else:
            if not text(origin) or origin not in md['chain_call_site_ids']:
                fail('Request origin must belong to its compiler call chain')
            locator, _ = site(origin, context, caller.id)
            expected_id = qualified(repo, 'http-request:' + digest({'context':local(cid,repo), ('publisher' if md['publisher'] else 'origin'):local(origin,repo)}))
        if request.id != expected_id or request.line != locator['range']['start_line']:
            fail('Request identity or source line does not bind its original declaration')
        defining = binding(request, caller.id, locator, origin, 'defines_http_request', context)
        for identity in md['chain_call_site_ids']:
            site(identity, context, caller.id)
        terminals = []
        for identity in md['terminal_call_site_ids']:
            terminal, consumer = site(identity, context, None if family == 'FEIGN' else caller.id)
            if family == 'FEIGN' and terminal.get('declared_target') != caller.id:
                fail('Feign terminal does not invoke the declared method')
            terminals.append((identity, consumer, binding(request, identity, terminal, identity,
                'may_execute_http_request', context)))
        if bool(terminals) != (state in {'STATIC_TRIGGER','CONDITIONAL_STATIC_TRIGGER','FEIGN_INVOCATION_INTENT'}):
            fail('Execution state contradicts original terminal facts')
        if family == 'FEIGN' and (state not in {'DECLARATION_ONLY','FEIGN_INVOCATION_INTENT'} or md['chain_call_site_ids']):
            fail('Feign declaration cannot be a WebClient request chain')
        if family != 'FEIGN' and state in {'DECLARATION_ONLY','FEIGN_INVOCATION_INTENT'}:
            fail('Non-Feign request cannot claim Feign invocation')
        route = md.get('path')
        if route is not None and (not text(route) or not route.startswith('/') or redact_uri_text(route) != route
                                  or any(x in route for x in ['?', '#', '\0', '\r', '\n']) or route.startswith('//')):
            fail('Route must be a safe captured path or unknown')
        if request.name != str(md.get('method') or 'UNKNOWN') + ' ' + (route or '(URI unknown)'):
            fail('Request label disagrees with its captured method and route')
        uri_provenance = md.get('uri_provenance')
        if not isinstance(uri_provenance, list) or len(uri_provenance) > 1000:
            fail('URI provenance must be bounded captured records')
        for item in uri_provenance:
            if (not isinstance(item, Mapping) or not text(item.get('source_file'))
                    or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in item['sha256'])
                    or context.get('source_files', {}).get(item['source_file']) != item['sha256']
                    or graph.files.get(item['source_file']) != item['sha256']):
                fail('URI provenance is outside its captured source inputs')
            literal = (set(item) == {'source_file','sha256','source_range','kind'}
                       and isinstance(item['kind'], str) and item['kind'] in {'COMPILER_LITERAL','COMPILER_CONSTANT'} and position(item['source_range']))
            configured = (set(item) == {'source_file','sha256','status','profiles','key'}
                          and item['status'] == 'MATCHED' and isinstance(item['key'], str)
                          and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',item['key'])
                          and isinstance(item['profiles'], list) and len(item['profiles']) <= 128
                          and all(isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',v) for v in item['profiles']))
            if not literal and not configured:
                fail('Unsupported or private URI provenance payload')
            if configured:
                config = context.get('http_config_provenance')
                records = config.get(item['key']) if isinstance(config, Mapping) else None
                if (not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], Mapping)
                        or not isinstance(records[0].get('source_file'), str)):
                    fail('Configured URI provenance has no unique canonical context record')
                canonical = {**records[0], 'source_file': source_key(repo, records[0]['source_file'])}
                if dict(item) != canonical:
                    fail('Configured URI provenance does not match its captured context tuple')
        for terminal_id, consumer, terminal_edge in terminals or [(None,caller,None)]:
            owner = resolve_service_ownership({'id':consumer.id,'path':consumer.path,'repo_id':repo,
                'module':context.get('module'),'context_id':cid},workspace.get('service_ownership'),context_id=cid)
            service = owner.get('owner_id') if owner.get('status') == 'RESOLVED' else None
            rows = selected.get(service, {}).get('contexts', [])
            if (service is None or 'service:'+service not in services
                    or not any(row.get('context_id') == cid and row.get('status') == 'CURRENT' for row in rows)):
                diagnostics.append({'code':'HTTP_CONSUMER_OWNERSHIP_UNKNOWN','source_id':request.id,'caller':consumer.id})
                continue
            identity = 'interface:http-consumer:' + digest([service, request.id, terminal_id])
            refs = tuple(sorted(set(defining.evidence_ids) | set(terminal_edge.evidence_ids if terminal_edge else ())))
            for ref in refs:
                proof = proofs[ref]
                provenance[ref] = {'id':ref,'evidence_kind':'FRAMEWORK_DERIVED','freshness':'CURRENT',
                    'polarity':_canonical_polarity(proof.get('polarity')),'source_refs':[ref],
                    'attributes':{'context_ids':[cid],'source_path':proof['source_file'],
                                  'source_sha256':proof['sha256'],'original_evidence_id':ref}}
            summary = _summarize_view_evidence(refs, provenance)
            reasons = list(md['unknown_reasons'])
            if route is None or md['uri_status'] != 'DECLARED_LITERAL': reasons.append('HTTP_CONSUMER_URI_UNKNOWN')
            resolution = 'RESOLVED' if not reasons and route is not None and md.get('method') else 'UNRESOLVED'
            attrs = {'direction':'CONSUMER','family':family,'execution_status':state,
                'caller':consumer.id,'origin_call_site':origin,'terminal_call_site':terminal_id,
                'request_definition_id':request.id,'declaration_id':md.get('declaration') if family == 'FEIGN' else None,
                'http_method':md.get('method'),'route_expression':route,'uri_status':md['uri_status'],
                'uri_provenance':deepcopy(uri_provenance),'service_binding':None,
                'request_contract_ref':None,'response_contract_ref':None,
                'runtime_execution':'NOT_OBSERVED','runtime_availability':'UNKNOWN',
                'deployment_status':'UNKNOWN','unresolved_reasons':sorted(set(reasons)),'context_id':cid,
                'source_path':consumer.path}
            nodes.append(ViewNode(identity,'http_interface',(md.get('method') or 'HTTP')+' '+(route or 'UNKNOWN'),
                original_ids=tuple(sorted({request.id,consumer.id,caller.id,*md['chain_call_site_ids'],
                    *([terminal_id] if terminal_id else [])})),owner_id='service:'+service,
                evidence_refs=refs,attributes=attrs,resolution_status=resolution,**summary))
            edges.append(ViewEdge('edge:'+identity,'service:'+service,identity,'uses_http_interface',
                evidence_refs=refs,attributes={'scope':scope,'context_ids':[cid]},resolution_status=resolution,**summary))
            found += 1
    if not found:
        diagnostics.append({'code':'HTTP_CONSUMER_FACTS_UNAVAILABLE','message':'No selected typed client occurrences; legacy names are not execution proof.'})
    result = aggregate_view_edges(edges,tuple(provenance.values()),scope=scope,diagnostics=diagnostics)
    document = ViewDocument('view:http-consumers:'+workspace['workspace_id']+':'+scope,'interfaces',
        digest([inventory.baseline_fingerprint,graph.files,CONSUMER_RULES_VERSION]),CONSUMER_RULES_VERSION,
        scope,inventory.context_selection,nodes=tuple(nodes),edges=result['edges'],provenance=result['provenance'],
        diagnostics=result['diagnostics'],coverage={'status':'PARTIAL' if found else 'UNKNOWN','counts':{'found':found,
            'resolved':sum(n.kind=='http_interface' and n.resolution_status=='RESOLVED' for n in nodes),
            'unresolved':sum(n.kind=='http_interface' and n.resolution_status!='RESOLVED' for n in nodes),'excluded':0}},
        limits=('Static definitions and invocation intent do not prove network execution or runtime/data availability.',))
    ViewDocument.from_dict(document.to_dict())
    if before != (workspace,graph.to_dict(),source_coverage):
        _fail('HTTP_INPUT_MUTATED','Consumer projection changed a caller snapshot')
    return document

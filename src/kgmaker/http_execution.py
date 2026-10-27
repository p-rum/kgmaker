"""Typed, bounded HTTP request definitions and static terminal intent.

No request is sent and no object is instantiated. URI/privacy helpers are also
used before legacy source-reference identities and explicit context persistence.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from .analysis_model import digest, file_hash, safe_path
from .model import Edge, KnowledgeGraph, Node

VERSION = 'http-client-execution-2'
WEB = 'org.springframework.web.reactive.function.client.WebClient'
REST = 'org.springframework.web.client.RestClient'
MONO = 'reactor.core.publisher.Mono'
FLUX = 'reactor.core.publisher.Flux'
FEIGN = 'org.springframework.cloud.openfeign.FeignClient'
VERBS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}


def uri_parts(value):
    if not isinstance(value, str) or not value or '${' in value or '#{' in value or '<redacted' in value:
        return {'status': 'UNKNOWN_URI'}
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.scheme not in {'http', 'https'}:
            return {'status': 'UNSUPPORTED_URI_SCHEME'}
        if parsed.netloc and not parsed.scheme:
            return {'status': 'UNKNOWN_URI_SCHEME'}
        if parsed.scheme:
            if not parsed.hostname:
                return {'status': 'INVALID_URI'}
            authority = parsed.hostname
            if ':' in authority:
                authority = '[' + authority + ']'
            if parsed.port is not None:
                authority += ':' + str(parsed.port)
            base = parsed.scheme + '://' + authority
        elif not parsed.path.startswith('/'):
            return {'status': 'UNKNOWN_RELATIVE_URI'}
        else:
            base = None
        if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
            return {'status': 'REDACTED_URI'}
        return {'status': 'LITERAL', 'base': base, 'path': parsed.path or '/',
                'public_uri': urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))}
    except ValueError:
        return {'status': 'INVALID_URI'}


def redact_uri_text(value: str, *, relative=True) -> str:
    """Do not retain URI userinfo, query values or fragments in graph payloads."""
    def clean_uri(uri):
        # Privacy applies even when this scheme is unsupported by HTTP analysis.
        try:
            parsed = urlsplit(uri)
            if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
                return '<redacted-uri>'
            parsed.port  # malformed authorities must not retain opaque payloads
            return uri
        except ValueError:
            return '<redacted-uri>'
    result = re.sub(r'[A-Za-z][A-Za-z0-9+.-]*://[^\s\"\'<>]+',
                    lambda match: clean_uri(match[0]), value)
    # Quoted relative URI defaults may also occur in source-only signatures.
    result = re.sub(r"""(["'`])(/[^"'`\r\n]*)\1""",
                    lambda match: match[1] + clean_uri(match[2]) + match[1], result)
    result = re.sub(r'(?<![A-Za-z0-9:/])//[^\s\"\'<>]+',
                    lambda match: clean_uri(match[0]), result)
    if relative and ('?' in result or '#' in result) and not any(c.isspace() for c in result) and not result.startswith('#{'):
        return '<redacted-uri>'
    return result


def _redact_tree(value, *, relative=False):
    if isinstance(value, dict):
        return {redact_uri_text(k, relative=False) if isinstance(k, str) else k:
                _redact_tree(v, relative=relative or k == 'spring_properties') for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_tree(v, relative=relative) for v in value]
    return redact_uri_text(value, relative=relative) if isinstance(value, str) else value


def prepare_context(root: Path, context: dict) -> dict:
    """Bind redacted input fingerprints before IDs; config values stay explicit."""
    result = _redact_tree(context)
    original = context.get('spring_properties')
    if isinstance(original, dict):
        redactions = {}
        for key, value in original.items():
            safe_key = redact_uri_text(key) if isinstance(key, str) else key
            if safe_key != key:
                result['spring_properties'].pop(key, None)
                result['spring_properties'].pop(safe_key, None)
                result['spring_properties'][safe_key] = None
                redactions[digest(key)] = digest(value)
            elif isinstance(value, str) and redact_uri_text(value) != value:
                result['spring_properties'][key] = None
                redactions[key] = digest(value)
        if redactions:
            result['http_redacted_property_hashes'] = redactions
    if result != context:
        result['http_redacted_input_hash'] = digest(context)
    records = {}
    properties = result.get('spring_properties')
    profiles = result.get('spring_profiles')
    if isinstance(properties, dict) and isinstance(profiles, list) and all(isinstance(p, str) for p in profiles):
        for name, checksum in context.get('source_files', {}).items():
            path = Path(name)
            if path.name != 'application.properties' and path.name not in {'application-' + p + '.properties' for p in profiles}:
                continue
            def invalidate(status):
                for key in properties:
                    records.setdefault(key, []).append({'status': status, 'source_file': name, 'sha256': checksum})
            try:
                source = safe_path(root, name)
                if file_hash(source) != checksum:
                    raise ValueError('HTTP configuration snapshot changed')
                if source.stat().st_size > 1024 * 1024:
                    invalidate('PROPERTY_FILE_LIMIT')
                    continue
                text = source.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                invalidate('PROPERTY_FILE_UNREADABLE')
                continue
            parsed, complete = [], True
            for line in text.splitlines():
                if not line.strip() or line.lstrip().startswith(('#', '!')):
                    continue
                match = re.fullmatch(r'\s*([A-Za-z0-9_.-]+)\s*[=:]\s*(.*?)\s*', line)
                if '\\' in line or not match:
                    invalidate('UNSUPPORTED_PROPERTY_SYNTAX')
                    complete = False
                    break
                parsed.append(match.groups())
            if not complete:
                continue
            seen = set()
            for key, value in parsed:
                if key in seen:
                    records.setdefault(key, []).append({'status': 'DUPLICATE_PROPERTY'})
                seen.add(key)
                if key in properties and isinstance(properties[key], str) and properties[key] == value and '${' not in value and '#{' not in value:
                    records.setdefault(key, []).append({'status': 'MATCHED', 'source_file': name, 'sha256': checksum,
                                                        'profiles': profiles, 'key': key})
    result['http_config_provenance'] = records
    result['http_inputs_hash'] = digest({'sources': records, 'redacted': result.get('http_redacted_input_hash')})
    result['framework_rule_versions'] = {**result.get('framework_rule_versions', {}), 'http': VERSION}
    return result


@dataclass(frozen=True)
class _Value:
    kind: str = 'unknown'
    origins: frozenset = frozenset()
    family: str | None = None
    base: str | None = None
    literal: object = None
    provenance: tuple = ()
    opaque: bool = False


def _merge(left, right):
    if left == right:
        return left
    return _Value(origins=left.origins | right.origins, opaque=True)


class _Projection:
    def __init__(self, graph, context):
        self.graph, self.context = graph, context
        self.symbols = {s['id']: s for s in graph.symbols}
        self.sites = {s['id']: s for s in graph.call_sites if s.get('context_id') == context['id']}
        self.requests, self.handled, self.diagnostics = {}, set(), []
        self.steps = 0
        self.eval_depth = 0
        self.unsupported_control_depth = 0
        self.shadowed_types = {s.get('owner') for s in graph.symbols if s.get('path') and s.get('kind') in {'class', 'interface', 'type', 'annotation_type'}}
        self.feign_targets = {}

    def issue(self, code, site=None):
        record = {'code': code, 'reason': code, 'context_id': self.context['id']}
        if site:
            record.update(call_site=site['id'], path=site.get('path'), range=site.get('range'))
        if record not in self.diagnostics:
            self.diagnostics.append(record)

    def target(self, site):
        return self.symbols.get(site.get('declared_target'), {})

    def external(self, site, family):
        symbol = self.target(site)
        owner = str(symbol.get('owner', '')).replace('$', '.')
        return (not symbol.get('path') and symbol.get('origin') == 'dependency'
                and (owner == family or owner.startswith(family + '.')))

    def escape(self, origins, reason):
        for identity in origins:
            if identity in self.requests:
                self.requests[identity]['unknown_reasons'].add(reason)

    def property_value(self, text):
        match = re.fullmatch(r'\$\{([A-Za-z0-9_.-]+)\}', text) if isinstance(text, str) else None
        if not match:
            return _Value('literal', literal=text)
        key = match[1]
        props = self.context.get('spring_properties', {})
        records = self.context.get('http_config_provenance', {}).get(key, [])
        if (isinstance(props, dict) and isinstance(props.get(key), str)
                and len(records) == 1 and records[0].get('status') == 'MATCHED'):
            return _Value('literal', literal=props[key], provenance=(records[0],))
        self.issue('HTTP_CONFIGURATION_VALUE_OR_PROVENANCE_UNKNOWN')
        return _Value(opaque=True)

    def reference(self, record, aliases):
        if not isinstance(record, dict):
            return _Value()
        if record.get('id') in aliases:
            return aliases[record['id']]
        symbol = self.symbols.get(record.get('symbol'), {})
        for annotation in symbol.get('annotations', []):
            if annotation.get('name') == 'org.springframework.beans.factory.annotation.Value' and annotation['name'] not in self.shadowed_types:
                value = annotation.get('values', {}).get('value')
                if isinstance(value, str):
                    return self.property_value(value)
        return _Value()

    def new(self, site, family, method, receiver, caller, conditional):
        identity = 'http-request:' + digest({'context': self.context['id'], 'origin': site['id']})
        if identity not in self.requests and len(self.requests) >= 1000:
            self.escape(self.requests, 'HTTP_REQUEST_LIMIT');self.issue('HTTP_REQUEST_LIMIT');return _Value(opaque=True)
        if identity not in self.requests:
            self.requests[identity] = {'id': identity, 'family': family, 'method': method,
                'base_url': receiver.base, 'path': None, 'uri_status': 'UNKNOWN_URI',
                'uri_provenance': list(receiver.provenance), 'origin_call_site': site['id'],
                'caller': caller, 'chain_call_site_ids': {site['id']}, 'terminals': [],
                'publisher': False, 'conditional': conditional, 'unknown_reasons': set(), 'uri_values': set(), 'children': set()}
        return _Value('request', frozenset({identity}), family, receiver.base)

    def publisher(self, receiver, site):
        parent_id = next(iter(receiver.origins))
        parent = self.requests[parent_id]
        identity = 'http-request:' + digest({'context': self.context['id'], 'publisher': site['id']})
        if identity not in self.requests:
            if len(self.requests) >= 1000:
                self.escape(self.requests, 'HTTP_REQUEST_LIMIT');self.issue('HTTP_REQUEST_LIMIT');return _Value(opaque=True)
            value = copy.deepcopy(parent)
            value.update(id=identity, origin_call_site=site['id'], root_call_site=parent['origin_call_site'],
                         publisher=True, children=set(), terminals=[])
            self.requests[identity] = value
            parent['children'].add(identity)
        return replace(receiver, kind='publisher', origins=frozenset({identity}))

    def update_uri(self, origins, value, node):
        info = uri_parts(value.literal) if value.kind == 'literal' else {'status': 'UNKNOWN_URI'}
        for identity in origins:
            request = self.requests.get(identity)
            if not request:
                continue
            if info['status'] == 'LITERAL':
                request['uri_values'].add((info.get('base'), info['path']))
                if len(request['uri_values']) == 1:
                    request['path'] = info['path']
                    if info.get('base'):
                        request['base_url'] = info['base']
                    request['uri_status'] = 'DECLARED_LITERAL'
                    request['uri_provenance'].extend(value.provenance or ({'source_file': node.get('path'), 'sha256': node.get('sha256'), 'source_range': node.get('range'), 'kind': 'COMPILER_LITERAL'},))
                else:
                    request['path'], request['base_url'], request['uri_status'] = None, None, 'AMBIGUOUS_URI_CONFIGURATION'
                if len(request['uri_values']) > 1:
                    for child in request.get('children', set()):
                        self.requests[child]['path'] = None
                        self.requests[child]['base_url'] = None
                        self.requests[child]['uri_status'] = 'AMBIGUOUS_URI_CONFIGURATION'
            else:
                request['uri_values'].add((None, None))
                request['path'], request['base_url'] = None, None
                request['uri_status'] = info['status']
                for child in request.get('children', set()):
                    self.requests[child]['path'] = None
                    self.requests[child]['base_url'] = None
                    self.requests[child]['uri_status'] = info['status']
                self.issue('HTTP_URI_VALUE_UNKNOWN')

    def call(self, node, aliases, caller, conditional):
        receiver = self.eval(node.get('receiver', {}), aliases, caller, conditional)
        arguments = [self.eval(arg, aliases, caller, conditional) for arg in node.get('arguments', [])]
        site = self.sites.get(node.get('call_site'))
        captured = frozenset().union(*(self.reference(r, aliases).origins for r in node.get('captured_bindings', [])))
        self.escape(captured, 'HTTP_PUBLISHER_CAPTURED_BY_REFERENCE')
        if node.get('binding_references_complete') is False:
            self.escape(self.requests, 'HTTP_CAPTURE_BINDING_LIMIT')
        origins = receiver.origins | captured | frozenset().union(*(v.origins for v in arguments))
        if not site or site.get('caller') != caller or site.get('invocation_kind') == 'METHOD_REFERENCE':
            self.escape(origins, 'HTTP_CALLER_OR_BINDING_UNKNOWN')
            return _Value(origins=origins, opaque=True)
        self.handled.add(site['id'])
        symbol = self.target(site); name = symbol.get('name')
        family = 'WEBCLIENT' if self.external(site, WEB) else 'RESTCLIENT' if self.external(site, REST) else None
        if family:
            for identity in receiver.origins:
                if identity in self.requests:
                    self.requests[identity]['chain_call_site_ids'].add(site['id'])
            if name in {'create', 'builder'}:
                base = None; provenance = ()
                if arguments and arguments[0].kind == 'literal':
                    info = uri_parts(arguments[0].literal)
                    if info['status'] == 'LITERAL' and info.get('base'):
                        base = info['public_uri']; provenance = arguments[0].provenance
                return _Value('client', family=family, base=base, provenance=provenance)
            if name == 'baseUrl' and receiver.kind == 'client':
                info = uri_parts(arguments[0].literal) if arguments and arguments[0].kind == 'literal' else {}
                return replace(receiver, base=info.get('public_uri'), provenance=arguments[0].provenance if arguments else ())
            if name == 'build' and receiver.kind == 'client':
                return receiver
            if name in VERBS:
                return self.new(site, family, name.upper(), receiver, caller, conditional)
            if name == 'method':
                enum = node.get('arguments', [{}])[0].get('enum_constant', {})
                enum_symbol = self.symbols.get(enum.get('symbol'), {})
                method = enum.get('name') if enum.get('owner') == 'org.springframework.http.HttpMethod' and not enum_symbol.get('path') and enum_symbol.get('origin') == 'dependency' else None
                return self.new(site, family, method, receiver, caller, conditional)
            if receiver.origins and (receiver.opaque or len(receiver.origins) != 1):
                self.escape(receiver.origins, 'HTTP_REQUEST_ORIGIN_UNPROVEN')
                return _Value(origins=receiver.origins, opaque=True)
            if name == 'uri' and receiver.origins:
                # URI callbacks/extra arguments can replace path or authority.
                # The literal first argument alone is not the effective route.
                if len(arguments) != 1:
                    self.escape(receiver.origins, 'HTTP_URI_OVERLOAD_UNSUPPORTED')
                    self.issue('HTTP_URI_OVERLOAD_UNSUPPORTED', site)
                self.update_uri(receiver.origins, arguments[0] if len(arguments) == 1 else _Value(), node)
                return receiver
            if name == 'retrieve' and receiver.origins:
                return replace(receiver, kind='response')
            if family == 'WEBCLIENT' and name in {'bodyToMono', 'bodyToFlux', 'exchangeToMono', 'exchangeToFlux', 'exchange'} and receiver.origins:
                publisher_type = FLUX if name in {'bodyToFlux', 'exchangeToFlux'} else MONO
                if publisher_type in self.shadowed_types:
                    self.escape(receiver.origins, 'HTTP_REACTOR_TYPE_SHADOWED')
                    return _Value(origins=receiver.origins, opaque=True)
                return self.publisher(receiver, site)
            if family == 'RESTCLIENT' and name in {'body', 'toEntity', 'toBodilessEntity', 'exchange'} and receiver.origins:
                self.trigger(receiver, site, conditional)
                return _Value('result')
        owner = str(symbol.get('owner', '')).replace('$', '.')
        if ((owner == MONO and self.external(site, MONO) and name in {'block', 'blockOptional', 'subscribe', 'toFuture'})
                or (owner == FLUX and self.external(site, FLUX) and name in {'blockFirst', 'blockLast', 'subscribe'})):
            if receiver.origins:
                self.trigger(receiver, site, conditional)
            return _Value('result')
        if owner in {'org.springframework.core.env.Environment', 'org.springframework.core.env.PropertyResolver'} and not symbol.get('path') and name == 'getProperty' and len(arguments) == 1 and isinstance(arguments[0].literal, str):
            return self.property_value('${' + arguments[0].literal + '}')
        self.escape(origins, 'HTTP_PUBLISHER_OR_SPEC_ESCAPED_TO_UNKNOWN_CALL')
        return _Value(origins=origins, opaque=bool(origins))

    def trigger(self, receiver, site, conditional):
        if self.unsupported_control_depth:
            self.escape(receiver.origins, 'HTTP_UNSUPPORTED_CONTROL_FLOW')
            self.issue('HTTP_UNSUPPORTED_CONTROL_FLOW', site)
            return
        if receiver.opaque or len(receiver.origins) != 1:
            self.escape(receiver.origins, 'HTTP_TERMINAL_ORIGIN_AMBIGUOUS')
            self.issue('HTTP_TERMINAL_ORIGIN_AMBIGUOUS', site)
            return
        request = self.requests.get(next(iter(receiver.origins)))
        if request:
            request['terminals'].append((site['id'], conditional))

    def eval(self, node, aliases, caller, conditional=False):
        if self.eval_depth >= 128:
            self.escape(self.requests, 'HTTP_EXPRESSION_DEPTH_LIMIT');self.issue('HTTP_EXPRESSION_DEPTH_LIMIT');return _Value(opaque=True)
        self.eval_depth += 1
        try:
            return self._eval(node, aliases, caller, conditional)
        finally:
            self.eval_depth -= 1

    def _eval(self, node, aliases, caller, conditional=False):
        self.steps += 1
        if self.steps > 20000:
            self.escape(self.requests, 'HTTP_ANALYSIS_TRUNCATED');self.issue('HTTP_ANALYSIS_TRUNCATED');return _Value(opaque=True)
        if not isinstance(node, dict):
            return _Value()
        kind = node.get('kind')
        if kind == 'call':
            return self.call(node, aliases, caller, conditional)
        if kind == 'reference':
            value = self.eval(node.get('reference_receiver', {}), aliases, caller, conditional)
            origins = value.origins | frozenset().union(*(self.reference(r, aliases).origins for r in node.get('captured_bindings', [])))
            self.escape(origins, 'HTTP_PUBLISHER_CAPTURED_BY_REFERENCE')
            if node.get('binding_references_complete') is False:
                self.escape(self.requests, 'HTTP_CAPTURE_BINDING_LIMIT')
            return _Value('reference', origins, opaque=bool(origins))
        literal = node.get('literal')
        if isinstance(literal, dict) and literal.get('type') in {'STRING_LITERAL', 'java.lang.String'} and isinstance(literal.get('value'), str):
            value = _Value('literal', literal=literal['value'])
            return replace(value, provenance=value.provenance or ({'source_file': node.get('path'), 'sha256': node.get('sha256'), 'source_range': node.get('range'), 'kind': literal.get('source')},))
        if isinstance(node.get('binding_ref'), dict):
            return self.reference(node['binding_ref'], aliases)
        if kind == 'assign':
            value = self.eval(node.get('value', {}), aliases, caller, conditional)
            binding = node.get('binding') or {}
            if binding.get('id') and binding.get('kind') in {'LOCAL_VARIABLE', 'PARAMETER', 'RESOURCE_VARIABLE'}:
                if binding['id'] not in aliases and len(aliases) >= 2000:
                    self.escape(self.requests, 'HTTP_LOCAL_BINDING_LIMIT');self.issue('HTTP_LOCAL_BINDING_LIMIT')
                else:
                    aliases[binding['id']] = value
            else:
                self.escape(value.origins, 'HTTP_PUBLISHER_STORED_OR_UNBOUND')
            return value
        if kind == 'if':
            self.eval(node.get('condition', {}), aliases, caller, conditional)
            left, right = dict(aliases), dict(aliases)
            yes = self.eval(node.get('then', {}), left, caller, True)
            no = self.eval(node.get('else', {}), right, caller, True)
            for key in left.keys() | right.keys():
                aliases[key] = _merge(left.get(key, _Value()), right.get(key, _Value()))
            return _merge(yes, no)
        refs = node.get('referenced_bindings', [])
        origins = frozenset().union(*(self.reference(r, aliases).origins for r in refs))
        self.escape(origins, 'HTTP_UNSUPPORTED_EXPRESSION_ESCAPE')
        if node.get('binding_references_complete') is False:
            self.escape(self.requests, 'HTTP_BINDING_REFERENCE_LIMIT')
        return _Value(origins=origins, opaque=bool(origins))

    def execute(self, node, aliases, caller, conditional=False, depth=0):
        if depth > 32:
            self.escape(self.requests, 'HTTP_CONTROL_FLOW_DEPTH_LIMIT');return
        kind = node.get('kind') if isinstance(node, dict) else None
        if kind == 'block':
            for child in node.get('statements', []):
                self.execute(child, aliases, caller, conditional, depth+1)
        elif kind in {'return', 'throw'}:
            value = self.eval(node.get('value', {}), aliases, caller, conditional)
            self.escape(value.origins, 'HTTP_PUBLISHER_RETURNED' if kind == 'return' else 'HTTP_PUBLISHER_THROWN')
        elif kind == 'if':
            self.eval(node.get('condition', {}), aliases, caller, conditional)
            left, right = dict(aliases), dict(aliases)
            self.execute(node.get('then', {}), left, caller, True, depth+1)
            self.execute(node.get('else', {}), right, caller, True, depth+1)
            for key in left.keys() | right.keys():
                aliases[key] = _merge(left.get(key, _Value()), right.get(key, _Value()))
        elif kind in {'while', 'do', 'for', 'foreach', 'try'}:
            # Visit every operand, but do not invent loop/catch/abrupt order.
            # Updates may be unreachable (break/throw); resource construction
            # and catches also require control-flow proof beyond this projection.
            before, after = dict(aliases), dict(aliases)
            prior_requests = set(self.requests)
            self.unsupported_control_depth += 1
            try:
                for item in node.get('resources', []):
                    self.execute(item, after, caller, True, depth+1)
                for key in ('initial', 'condition', 'iterable', 'body', 'update', 'finally'):
                    if isinstance(node.get(key), dict):
                        self.execute(node[key], after, caller, True, depth+1)
                for item in node.get('catches', []):
                    self.execute(item.get('body', {}), after, caller, True, depth+1)
            finally:
                self.unsupported_control_depth -= 1
            origins = frozenset().union(*(value.origins for value in [*before.values(), *after.values()]))
            self.escape(origins | (set(self.requests) - prior_requests), 'HTTP_UNSUPPORTED_CONTROL_FLOW')
            for key in before.keys() | after.keys():
                value = _merge(before.get(key, _Value()), after.get(key, _Value()))
                aliases[key] = _Value(origins=value.origins, opaque=True)
            diagnostic = {'code': 'HTTP_UNSUPPORTED_CONTROL_FLOW', 'reason': 'HTTP_UNSUPPORTED_CONTROL_FLOW',
                          'context_id': self.context['id'], 'path': node.get('path'), 'range': node.get('range')}
            if diagnostic not in self.diagnostics:
                self.diagnostics.append(diagnostic)
        else:
            self.eval(node, aliases, caller, conditional)

    def feign(self):
        types = {s.get('owner'): s for s in self.symbols.values() if s.get('kind') in {'interface', 'class', 'type'}}
        def parents(owner, seen):
            if owner in seen or len(seen) >= 128:
                return set()
            seen.add(owner)
            value = types.get(owner, {})
            result = {owner}
            for parent in value.get('jvm_interfaces', []):
                result |= parents(parent.replace('/', '.'), seen)
            return result
        mappings = {'GetMapping': 'GET', 'PostMapping': 'POST', 'PutMapping': 'PUT',
                    'PatchMapping': 'PATCH', 'DeleteMapping': 'DELETE'}
        for owner, client in types.items():
            annotation = next((a for a in client.get('annotations', []) if a.get('name') == FEIGN), None)
            if not annotation or FEIGN in self.shadowed_types or client.get('kind') != 'interface':
                continue
            values = annotation.get('values', {})
            name = values.get('name') or values.get('value') or None
            service = self.property_value(name) if isinstance(name, str) else _Value()
            base = self.property_value(values.get('url')) if isinstance(values.get('url'), str) else _Value()
            info = uri_parts(base.literal)
            prefix_declared = values.get('path') is not None and values.get('path') != ''
            prefix = self.property_value(values.get('path')) if isinstance(values.get('path'), str) else _Value()
            prefix_info = uri_parts(prefix.literal)
            inherited = parents(owner, set())
            for method in self.symbols.values():
                if len(self.requests) >= 1000:
                    self.issue('HTTP_REQUEST_LIMIT');break
                if method.get('kind') != 'method' or method.get('owner') not in inherited:
                    continue
                if not isinstance(method.get('modifiers'), list) or type(method.get('jvm_static')) is not bool:
                    self.issue('HTTP_FEIGN_ABSTRACTNESS_UNKNOWN');continue
                if method['jvm_static'] or 'abstract' not in method['modifiers']:
                    continue
                selected = []
                for mapping in method.get('annotations', []):
                    qualified = mapping.get('name', '')
                    if qualified in self.shadowed_types or not qualified.startswith('org.springframework.web.bind.annotation.'):
                        continue
                    short = qualified.rsplit('.', 1)[-1]
                    members = mapping.get('values', {})
                    verb = mappings.get(short)
                    if short == 'RequestMapping':
                        modes = members.get('method', [])
                        if isinstance(modes, list) and len(modes) == 1 and isinstance(modes[0], str) and modes[0].startswith('org.springframework.web.bind.annotation.RequestMethod.'):
                            verb = modes[0].rsplit('.', 1)[-1]
                    if verb:
                        paths = members.get('path') or members.get('value') or ['/']
                        route = paths[0] if isinstance(paths, list) and len(paths) == 1 and isinstance(paths[0], str) else None
                        selected.append((verb, route))
                if len(selected) != 1:
                    self.issue('HTTP_FEIGN_MAPPING_UNAVAILABLE')
                    continue
                verb, route = selected[0]
                path_info = uri_parts(route)
                identity = 'http-request:' + digest({'context': self.context['id'], 'client': client['id'], 'method': method['id']})
                self.requests[identity] = {'id': identity, 'family': 'FEIGN', 'method': verb,
                    'base_url': info.get('public_uri'), 'path': None if prefix_declared else path_info.get('path'),
                    'method_path': path_info.get('path'),
                    'client_path': prefix_info.get('path') if prefix_info.get('base') is None else None,
                    'uri_status': 'COMPOSED_ROUTE_UNKNOWN' if prefix_declared else 'DECLARED_LITERAL' if path_info['status'] == 'LITERAL' else 'UNKNOWN_URI',
                    'uri_provenance': list(base.provenance + service.provenance + prefix.provenance), 'origin_call_site': None,
                    'caller': method['id'], 'declaration': method['id'], 'client_type': client['id'],
                    'declared_service_name': service.literal if isinstance(service.literal, str) and '<redacted' not in service.literal else None,
                    'proxy_registration': 'UNKNOWN', 'chain_call_site_ids': set(), 'terminals': [],
                    'publisher': False, 'conditional': False, 'unknown_reasons': {'HTTP_FEIGN_PATH_PREFIX_UNRESOLVED'} if prefix_declared else set(), 'uri_values': set(), 'children': set()}
                self.feign_targets.setdefault(method['id'], []).append((owner, identity))
        for site in self.sites.values():
            if site.get('invocation_kind') == 'METHOD_REFERENCE':
                continue
            candidates = self.feign_targets.get(site.get('declared_target'), [])
            receiver = str(site.get('dispatch_receiver') or site.get('receiver_type') or '').replace('/', '.')
            matched = [(owner, identity) for owner, identity in candidates if receiver == owner]
            if len(matched) == 1:
                self.requests[matched[0][1]]['terminals'].append((site['id'], True))
            elif candidates:
                self.issue('HTTP_FEIGN_RECEIVER_UNAVAILABLE', site)

    def finish(self, bodies):
        self.feign()
        for body in bodies:
            caller = body.get('method')
            if (caller in self.symbols and body.get('context_id') == self.context['id']
                    and str(self.symbols[caller].get('path', '')).endswith('.java')):
                self.execute(body.get('body', {}), {}, caller)
                if self.symbols[caller].get('kind') == 'lambda':
                    self.escape((key for key, value in self.requests.items() if value['caller'] == caller), 'HTTP_LAMBDA_ESCAPE_UNKNOWN')
        for site in self.sites.values():
            symbol = self.target(site)
            family = 'WEBCLIENT' if self.external(site, WEB) else 'RESTCLIENT' if self.external(site, REST) else None
            if family and symbol.get('name') in VERBS and site['id'] not in self.handled and site.get('invocation_kind') != 'METHOD_REFERENCE':
                value = self.new(site, family, symbol['name'].upper(), _Value(), site['caller'], True)
                self.escape(value.origins, 'HTTP_TYPED_IR_UNAVAILABLE')
                self.issue('HTTP_TYPED_IR_UNAVAILABLE', site)
        nodes, edges, evidence = list(self.graph.nodes), list(self.graph.edges), list(self.graph.evidence)
        indexed = {n.id: n for n in nodes}
        for item in self.requests.values():
            if item.get('children') and not item['terminals']:
                continue
            site = self.sites.get(item['origin_call_site']) or self.symbols.get(item.get('declaration'), {})
            caller = indexed.get(item['caller'])
            if not caller:
                continue
            terminals = sorted(set(item['terminals']))
            status = ('CONDITIONAL_STATIC_TRIGGER' if any(c for _, c in terminals) else 'STATIC_TRIGGER') if terminals else (
                'UNKNOWN' if item['unknown_reasons'] else 'UNSUBSCRIBED_WITHIN_SCOPE' if item['publisher'] else 'DEFINITION_ONLY')
            if item['family'] == 'FEIGN':
                status = 'FEIGN_INVOCATION_INTENT' if terminals else 'DECLARATION_ONLY'
            metadata = {k: v for k, v in item.items() if k not in {'id', 'terminals', 'uri_values', 'unknown_reasons', 'chain_call_site_ids', 'children'}}
            metadata.update(context_id=self.context['id'], repo_id=self.context.get('repo_id'), module=self.context.get('module'),
                source_set=self.context.get('source_set'), execution_status=status, runtime_availability='UNKNOWN',
                runtime_execution='NOT_OBSERVED', terminal_call_site_ids=[s for s, _ in terminals],
                chain_call_site_ids=sorted(item['chain_call_site_ids']), unknown_reasons=sorted(item['unknown_reasons']), rule_version=VERSION)
            nodes.append(Node(item['id'], 'http_request_definition', str(item['method'] or 'UNKNOWN') + ' ' + (item['path'] or '(URI unknown)'),
                site.get('path') or caller.path, line=(site.get('range') or {}).get('start_line'), scope=caller.scope,
                role='contract', origin=caller.origin, metadata=metadata))
            for source, relation, original in [(item['caller'], 'defines_http_request', item['origin_call_site'])] + [(s, 'may_execute_http_request', s) for s, _ in terminals]:
                call = self.sites.get(original) or site
                proof = {'kind': 'FRAMEWORK_DERIVED', 'source': source, 'target': item['id'], 'relation': relation,
                         'call_site': original, 'context_ids': [self.context['id']], 'rule': VERSION,
                         'source_file': call.get('path'), 'source_range': call.get('range'), 'sha256': call.get('sha256'),
                         'runtime_execution': 'NOT_OBSERVED', 'runtime_availability': 'UNKNOWN'}
                identity = 'evidence:' + digest(proof)
                evidence.append({'id': identity, **proof})
                edges.append(Edge(source, item['id'], relation, evidence_kind='FRAMEWORK_DERIVED', context_ids=(self.context['id'],),
                    evidence_ids=(identity,), source_file=call.get('path'), source_line=(call.get('range') or {}).get('start_line')))
        return replace(self.graph, nodes=nodes, edges=edges, evidence=evidence, diagnostics=self.graph.diagnostics+self.diagnostics)


def augment_http_graph(graph: KnowledgeGraph, bodies: list[dict], context: dict) -> KnowledgeGraph:
    return _Projection(graph, context).finish(bodies)

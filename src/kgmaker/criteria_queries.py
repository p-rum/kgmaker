"""Bounded programmatic query intent from validated Javac IR.

No query text, runtime dispatch, object alias, database access or provider execution
is inferred. Candidates retain original source/call identities for later ORM replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from copy import deepcopy
import hashlib
import re

from .analysis_model import digest
from .return_flow import _children, _range

VERSION = 'programmatic-query-2'
SPEC = 'org.springframework.data.jpa.domain.Specification'
QBASE = 'com.querydsl.core.types.dsl.EntityPathBase'
JPA = ('jakarta.persistence.', 'javax.persistence.')


def _walk(node):
    yield node
    for child in _children(node):
        yield from _walk(child)
    if isinstance(node.get('field_receiver'), dict):
        yield from _walk(node['field_receiver'])


def _generic(value, outer):
    match = re.fullmatch(re.escape(outer) + r'<([\w.$]+)>', value or '')
    return match[1] if match else None


def _dependency(symbol, context):
    return (symbol.get('origin') == 'dependency' and symbol.get('path') is None
            and symbol.get('context_id') == context['id']
            and str(symbol.get('id', '')).startswith('jvm:')
            and bool(context.get('classpath')))


def _source(value, context):
    return (isinstance(value, dict) and _range(value.get('range'))
            and isinstance(value.get('sha256'), str)
            and context.get('source_files', {}).get(value.get('path')) == value['sha256'])


def _spec_override(symbol, symbols, context):
    if not isinstance(symbol.get('query_override'), str):
        return False
    contract = symbols.get(symbol.get('query_override'), {})
    return (symbol.get('kind') == 'method' and _source(symbol, context)
            and _dependency(contract, context) and contract.get('owner') == SPEC
            and contract.get('name') == symbol.get('name') == 'toPredicate'
            and contract.get('descriptor') == symbol.get('descriptor')
            and 'public' in symbol.get('modifiers', []) and not symbol.get('jvm_static'))


def validate_query_ir(response, context):
    """Optional v1 fields are strict whenever any part of the extension is present."""
    symbols = {s['id']: s for s in response['symbols']}
    sites = {s['id']: s for s in response['call_sites']}
    extension = {'query_type', 'class_literal', 'query_lambda', 'field_receiver'}
    for body in response['bodies']:
        nodes = list(_walk(body.get('body', {})))
        present = ('query_ir_version' in body or 'query_parameters' in body or 'query_ir_status' in body
                   or 'query_override' in symbols[body['method']]
                   or any(extension.intersection(node) for node in nodes))
        if not present:
            continue
        if (type(body.get('query_ir_version')) is not int or body['query_ir_version'] != 1
                or body.get('language') != 'java' or not isinstance(body.get('query_parameters'), list)
                or len(body['query_parameters']) > 256 or not isinstance(body.get('query_ir_status'), str)
                or body['query_ir_status'] not in {'AVAILABLE', 'UNAVAILABLE'}):
            raise ValueError('Invalid programmatic query IR version/parameters')
        owner = symbols[body['method']]
        for parameter in body['query_parameters']:
            binding = parameter.get('binding') if isinstance(parameter, dict) else None
            if (not isinstance(binding, dict) or binding.get('kind') != 'PARAMETER'
                    or not isinstance(binding.get('id'), str) or not _source(binding.get('declaration'), context)
                    or not isinstance(parameter.get('type'), str)
                    or binding['id'] != 'binding:' + context['id'] + ':' + binding['declaration']['path'] + ':'
                        + binding['declaration']['sha256'] + ':' + str(binding['declaration']['range']['start'])
                        + ':' + str(binding['declaration']['range']['end'])):
                raise ValueError('Invalid query parameter identity')
        for node in nodes:
            if not extension.intersection(node):
                continue
            if (not _source(node, context) or node['path'] != owner.get('path')
                    or not _range(owner.get('range'))
                    or not owner['range']['start'] <= node['range']['start'] < node['range']['end'] <= owner['range']['end']):
                raise ValueError('Invalid query IR source/context')
            for key in ('binding_ref', 'binding'):
                binding = node.get(key)
                if binding is None or binding.get('id') is None:
                    continue  # Dependency fields have no source-local binding authority.
                declaration = binding.get('declaration')
                if not _source(declaration, context):
                    raise ValueError('Invalid query source binding declaration')
                expected = ('binding:' + context['id'] + ':' + declaration['path'] + ':'
                            + declaration['sha256'] + ':' + str(declaration['range']['start'])
                            + ':' + str(declaration['range']['end']))
                if binding['id'] != expected:
                    raise ValueError('Invalid query source binding identity')
                if binding.get('kind') in {'FIELD', 'ENUM_CONSTANT'}:
                    member = symbols.get(binding.get('symbol'), {})
                    if (member.get('context_id') != context['id']
                            or any(member.get(k) != declaration.get(k) for k in ('path', 'sha256', 'range'))):
                        raise ValueError('Invalid query field binding identity')
            if 'query_type' in node and (not isinstance(node['query_type'], str) or len(node['query_type']) > 4096):
                raise ValueError('Invalid query expression type')
            if 'class_literal' in node:
                literal = node['class_literal']
                if (not isinstance(literal, dict) or literal.get('version') != 1
                        or not isinstance(literal.get('owner'), str)
                        or not re.fullmatch(r'[\w.$]+', literal['owner'])
                        or _generic(node.get('query_type'), 'java.lang.Class') != literal['owner']):
                    raise ValueError('Invalid query class literal')
            if 'field_receiver' in node and not isinstance(node['field_receiver'], dict):
                raise ValueError('Invalid query field receiver')
            if 'query_lambda' in node and (not isinstance(node['query_lambda'], str) or node['query_lambda'] not in symbols
                    or symbols[node['query_lambda']].get('kind') != 'function'):
                raise ValueError('Invalid query lambda identity')
            if node.get('kind') == 'call':
                site = sites.get(node.get('call_site'), {})
                if site.get('caller') != body['method'] or site.get('range') != node.get('range'):
                    raise ValueError('Invalid query call identity')
    for symbol in response['symbols']:
        if 'query_override' in symbol and (not isinstance(symbol['query_override'], str)
                or not _spec_override(symbol, symbols, context)):
            raise ValueError('Invalid Specification override identity')
        if 'querydsl_path' in symbol:
            path = symbol['querydsl_path']
            if (not isinstance(path, dict) or type(path.get('version')) is not int or path['version'] != 1
                    or not _source(symbol, context) or symbol.get('kind') != 'field'
                    or not isinstance(path.get('entity_type'), str) or not isinstance(path.get('attribute'), str)
                    or not path['attribute'] or not isinstance(path.get('factory'), str) or path.get('factory') not in symbols
                    or not _dependency(symbols[path['factory']], context)
                    or symbols[path['factory']].get('owner') != 'com.querydsl.core.types.dsl.BeanPath'):
                raise ValueError('Invalid QueryDSL member initialization proof')
        if 'query_type_contracts' in symbol:
            contracts = symbol['query_type_contracts']
            if (not isinstance(contracts, list) or not _source(symbol, context)
                    or any(not isinstance(c, dict) or not isinstance(c.get('type'), str)
                           or not isinstance(c.get('symbol'), str) or c.get('symbol') not in symbols for c in contracts)):
                raise ValueError('Invalid query type contracts')
        if 'query_callable_type' in symbol or 'query_callable_symbol' in symbol:
            if (not isinstance(symbol.get('query_callable_type'), str)
                    or not isinstance(symbol.get('query_callable_symbol'), str)
                    or symbol.get('query_callable_symbol') not in symbols or not _source(symbol, context)):
                raise ValueError('Invalid query callable identity')


@dataclass
class _Value:
    kind: str = 'UNKNOWN'
    entity: str | None = None
    root: str | None = None
    attributes: list = field(default_factory=list)
    operations: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    witnesses: list = field(default_factory=list)
    literal: object = None
    filters: list = field(default_factory=list)


class _Capture:
    def __init__(self, graph, bodies, context):
        self.graph, self.context = graph, context
        self.symbols = {s['id']: s for s in graph.symbols}
        self.sites = {s['id']: s for s in graph.call_sites}
        self.bodies = bodies
        self.types = {s.get('owner'): s for s in graph.symbols if s.get('kind') in {'class', 'interface'}}
        self.records = {}

    def witness(self, node, site=None):
        return {'path': node.get('path'), 'sha256': node.get('sha256'), 'range': node.get('range'),
                'call_site': site.get('id') if site else None,
                'compiler_target': site.get('declared_target') if site else None}

    def type_entity(self, name, outer):
        declaration = self.types.get(name, {})
        matches = [(_generic(c.get('type'), outer), c.get('symbol')) for c in declaration.get('query_type_contracts', [])
                   if _dependency(self.symbols.get(c.get('symbol'), {}), self.context)
                   and self.symbols.get(c.get('symbol'), {}).get('owner') == outer]
        return matches[0][0] if len(matches) == 1 else None

    def combine(self, kind, values, witness):
        return _Value(kind, attributes=[a for v in values for a in v.attributes],
                      operations=[o for v in values for o in v.operations],
                      gaps=[g for v in values for g in v.gaps],
                      witnesses=[*[w for v in values for w in v.witnesses], witness])

    def evaluate(self, node):
        if not isinstance(node, dict):
            return _Value()
        kind = node.get('kind')
        for reference in [*node.get('captured_bindings', []), *node.get('referenced_bindings', [])]:
            value = self.env.get(reference.get('id'))
            if value is not None and value.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'}:
                self.global_gaps.append('QUERY_STATE_ESCAPES_LOCAL')
        if kind == 'block':
            result = _Value()
            for child in node.get('statements', []):
                result = self.evaluate(child)
            return result
        if kind == 'return':
            value = self.evaluate(node.get('value'))
            self.returns.append(value)
            return value
        if kind == 'assign':
            value = self.evaluate(node.get('value'))
            binding = node.get('binding') or {}
            if binding.get('kind') == 'LOCAL_VARIABLE' and binding.get('id'):
                if binding['id'] in self.env:
                    self.global_gaps.append('REASSIGNMENT_UNSUPPORTED')
                self.env[binding['id']] = value
            elif value.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'}:
                self.global_gaps.append('QUERY_STATE_ESCAPES_LOCAL')
            return value
        if kind in {'if', 'while', 'do', 'for', 'foreach', 'try', 'unsupported', 'and', 'or'}:
            # No path-sensitive claims from conditionally mutated builder objects.
            self.global_gaps.append('DYNAMIC_CONTROL_FLOW')
            for child in _children(node):
                self.evaluate(child)
            return _Value(gaps=['DYNAMIC_CONTROL_FLOW'])
        if kind == 'call':
            return self.call(node)
        if node.get('class_literal'):
            return _Value('CLASS', entity=node['class_literal']['owner'], witnesses=[self.witness(node)])
        literal = node.get('literal')
        if isinstance(literal, dict):
            return _Value('SCALAR', literal=literal.get('value'))
        binding = node.get('binding_ref') or {}
        if binding.get('id') in self.env:
            return self.env[binding['id']]
        member = self.symbols.get(binding.get('symbol'), {})
        path = member.get('querydsl_path')
        if path:
            if 'final' not in member.get('modifiers', []):
                return _Value(gaps=['QUERYDSL_MUTABLE_PATH_UNSUPPORTED'])
            receiver = self.evaluate(node.get('field_receiver'))
            if receiver.kind == 'ROOT' and receiver.entity == path['entity_type']:
                return _Value('PATH', receiver.entity, receiver.root,
                              attributes=[{'entity': receiver.entity, 'name': path['attribute'],
                                           'root': receiver.root, 'symbol': member['id']}],
                              witnesses=[*receiver.witnesses, self.witness(node), self.witness(member)])
            return _Value(gaps=['QUERYDSL_RECEIVER_UNRESOLVED'])
        qentity = self.type_entity(node.get('query_type'), QBASE)
        if qentity and binding.get('kind') in {'FIELD', 'PARAMETER', 'LOCAL_VARIABLE'}:
            return _Value('ROOT', qentity, binding.get('symbol') or binding.get('id'), witnesses=[self.witness(node)])
        if binding.get('kind') in {'PARAMETER', 'LOCAL_VARIABLE', 'FIELD'}:
            typename = node.get('query_type', '')
            if typename in {'jakarta.persistence.criteria.CriteriaBuilder', 'javax.persistence.criteria.CriteriaBuilder'}:
                return _Value('BUILDER')
            if typename.endswith('Predicate') or 'Specification' in typename:
                return _Value(gaps=['DYNAMIC_PREDICATE'])
            return _Value('SCALAR')
        return _Value()

    def call(self, node):
        site = self.sites.get(node.get('call_site'), {})
        target = self.symbols.get(site.get('declared_target'), {})
        receiver = self.evaluate(node.get('receiver'))
        args = [self.evaluate(arg) for arg in node.get('arguments', [])]
        witness = self.witness(node, site)
        owner, name = target.get('owner', ''), target.get('name')
        if (site.get('caller') != self.method or site.get('evidence_kind') != 'SYMBOL_RESOLVED'
                or not _dependency(target, self.context)):
            if receiver.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'} or any(a.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'} for a in args):
                self.global_gaps.append('CUSTOM_QUERY_HELPER_UNSUPPORTED')
            return _Value(gaps=['UNSUPPORTED_CALL'])
        api = owner.removeprefix('jakarta.persistence.').removeprefix('javax.persistence.') if owner.startswith(JPA) else ''
        if api == 'EntityManager' and name == 'getCriteriaBuilder':
            return _Value('BUILDER', witnesses=[witness])
        if api == 'criteria.CriteriaBuilder' and name == 'createQuery':
            value = _Value('QUERY', root=site['id'], witnesses=[witness], operations=['SELECT'])
            self.queries.append(('CRITERIA', value, node))
            return value
        if api in {'criteria.AbstractQuery', 'criteria.CriteriaQuery'} and name == 'from' and receiver.kind == 'QUERY':
            if len(args) == 1 and args[0].kind == 'CLASS':
                if receiver.entity is not None:
                    receiver.gaps.append('MULTIPLE_ROOTS_UNSUPPORTED')
                receiver.entity = args[0].entity
                receiver.witnesses.extend([witness, *args[0].witnesses])
                return _Value('ROOT', receiver.entity, receiver.root, witnesses=[witness, *args[0].witnesses])
            receiver.gaps.append('DYNAMIC_ROOT')
            return _Value(gaps=['DYNAMIC_ROOT'])
        if api in {'criteria.Path', 'criteria.Root'} and name == 'get':
            if receiver.kind == 'ROOT' and len(args) == 1 and isinstance(args[0].literal, str):
                return _Value('PATH', receiver.entity, receiver.root,
                              attributes=[{'entity': receiver.entity, 'name': args[0].literal, 'root': receiver.root}],
                              witnesses=[*receiver.witnesses, witness])
            return _Value(gaps=['DYNAMIC_ATTRIBUTE'], witnesses=[witness])
        if api == 'criteria.CriteriaBuilder' and name == 'equal':
            value = self.combine('PREDICATE', args, witness)
            value.operations.append(name)
            if not args or args[0].kind != 'PATH':
                value.gaps.append('PREDICATE_PATH_UNRESOLVED')
            return value
        if api == 'criteria.CriteriaQuery' and name in {'select', 'where'} and receiver.kind == 'QUERY':
            return self.query_clause(receiver, args, name, witness, replace_filters=True)
        if api == 'EntityManager' and name == 'createQuery' and len(args) == 1 and args[0].kind == 'QUERY':
            value = self.snapshot('CRITERIA', args[0], node)
            value.witnesses.append(witness)
            return value
        if api in {'TypedQuery', 'Query'} and name == 'getResultList' and receiver.kind == 'QUERY':
            receiver.operations.append(name)
            receiver.witnesses.append(witness)
            return receiver
        if owner == 'com.querydsl.jpa.impl.JPAQueryFactory' and name == 'selectFrom':
            value = _Value('QUERY', root=args[0].root if len(args) == 1 else None,
                           entity=args[0].entity if len(args) == 1 and args[0].kind == 'ROOT' else None,
                           operations=['SELECT'], witnesses=[witness, *[w for a in args for w in a.witnesses]])
            if value.entity is None:
                value.gaps.append('DYNAMIC_ROOT')
            self.queries.append(('QUERYDSL', value, node))
            return value
        if owner == 'com.querydsl.core.types.dsl.SimpleExpression' and name == 'eq':
            value = self.combine('PREDICATE', [receiver, *args], witness)
            value.operations.append(name)
            if receiver.kind not in {'PATH', 'PREDICATE'}:
                value.gaps.append('PREDICATE_PATH_UNRESOLVED')
            return value
        if owner == 'com.querydsl.core.support.QueryBase' and name == 'where' and receiver.kind == 'QUERY':
            return self.query_clause(receiver, args, name, witness)
        if owner == 'com.querydsl.jpa.impl.AbstractJPAQuery' and name == 'fetch' and receiver.kind == 'QUERY':
            value = self.snapshot('QUERYDSL', receiver, node)
            value.operations.append(name)
            value.witnesses.append(witness)
            return value
        # An attributed dependency call is not automatically a trusted builder API.
        # It may retain/mutate a query value just like a source-defined helper.
        if receiver.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'} or any(
                a.kind in {'QUERY', 'ROOT', 'PATH', 'PREDICATE'} for a in args):
            self.global_gaps.append('CUSTOM_QUERY_HELPER_UNSUPPORTED')
        if owner.startswith('com.querydsl.') or api.startswith('criteria.'):
            if receiver.kind == 'QUERY':
                receiver.gaps.append('UNSUPPORTED_QUERY_OPERATION:' + name)
            return _Value(gaps=['UNSUPPORTED_QUERY_OPERATION:' + str(name)], witnesses=[witness])
        return _Value('SCALAR')

    def snapshot(self, family, query, node):
        # Criteria createQuery copies the definition; later builder edits must not
        # rewrite executable intent. QueryDSL fetch captures its current definition.
        value = deepcopy(query)
        self.queries = [(f, q, n) for f, q, n in self.queries if q is not query]
        self.queries.append((family, value, node))
        return value

    def query_clause(self, query, args, name, witness, *, replace_filters=False):
        query.witnesses.append(witness)
        if name == 'select':
            if len(args) != 1 or args[0].kind != 'ROOT' or args[0].root != query.root:
                query.gaps.append('PROJECTION_UNSUPPORTED')
        else:
            # JPA where replaces (zero predicates clears); QueryDSL appends.
            if replace_filters:
                query.filters = []
            for value in args:
                clause = self.combine('PREDICATE', [value], witness)
                if value.kind != 'PREDICATE':
                    clause.gaps.append('DYNAMIC_PREDICATE')
                clause.attributes = []
                for attribute in value.attributes:
                    if attribute['root'] != query.root:
                        clause.gaps.append('FOREIGN_QUERY_ROOT')
                    else:
                        clause.attributes.append(attribute)
                query.filters.append(clause)
        return query

    def finish(self):
        for body in self.bodies:
            self.method = body['method']
            symbol = self.symbols[self.method]
            if body.get('query_ir_version') != 1 or body.get('language') != 'java' or not _source(symbol, self.context):
                continue
            self.env, self.queries, self.returns, self.global_gaps = {}, [], [], []
            if body.get('query_ir_status') != 'AVAILABLE':
                self.global_gaps.append('COMPILER_BODY_UNAVAILABLE')
            spec_entity = None
            callable_symbol = self.symbols.get(symbol.get('query_callable_symbol'), {})
            if _dependency(callable_symbol, self.context) and callable_symbol.get('owner') == SPEC:
                spec_entity = _generic(symbol.get('query_callable_type'), SPEC)
            elif _spec_override(symbol, self.symbols, self.context):
                spec_entity = self.type_entity(symbol.get('owner'), SPEC)
            spec_value = _Value('QUERY', spec_entity, self.method, operations=['PREDICATE'], witnesses=[self.witness(symbol)]) if spec_entity else None
            if spec_value and symbol.get('query_override'):
                spec_value.witnesses[0]['compiler_contract'] = symbol['query_override']
            for parameter in body.get('query_parameters', []):
                binding = parameter['binding']
                root_entity = next((_generic(parameter['type'], prefix + 'criteria.Root') for prefix in JPA
                                    if _generic(parameter['type'], prefix + 'criteria.Root')), None)
                if spec_entity and root_entity == spec_entity:
                    self.env[binding['id']] = _Value('ROOT', spec_entity, self.method, witnesses=[self.witness(binding['declaration'])])
            result = self.evaluate(body['body'])
            if spec_value:
                returns = self.returns or [result]
                if len(returns) != 1 or returns[0].kind != 'PREDICATE':
                    spec_value.gaps.append('DYNAMIC_PREDICATE')
                for value in returns:
                    self.query_clause(spec_value, [value], 'where', self.witness(symbol))
                self.queries.append(('SPECIFICATION', spec_value, body['body']))
            for family, query, node in self.queries:
                query.attributes = [a for clause in query.filters for a in clause.attributes]
                query.operations.extend(o for clause in query.filters for o in clause.operations)
                query.witnesses.extend(w for clause in query.filters for w in clause.witnesses)
                gaps = sorted(set(query.gaps + self.global_gaps + [g for clause in query.filters for g in clause.gaps]))
                if len(self.queries) > 1:
                    gaps.append('MULTIPLE_QUERIES_UNSUPPORTED')
                witnesses = {digest(w): w for w in query.witnesses if _source(w, self.context)}
                record = {'version': 2, 'family': family, 'method': self.method,
                          'entity': query.entity, 'root': query.root, 'attributes': query.attributes,
                          'operations': sorted(set(query.operations)), 'gaps': gaps,
                          'witnesses': list(witnesses.values()), 'context_id': self.context['id'],
                          'path': symbol['path'], 'sha256': symbol['sha256'], 'range': node.get('range')}
                record['id'] = digest(record)
                self.records.setdefault(self.method, []).append(record)
        symbols = [{**s, 'programmatic_queries': self.records[s['id']]} if s['id'] in self.records else s
                   for s in self.graph.symbols]
        return replace(self.graph, symbols=symbols)


def capture_query_facts(graph, bodies, context):
    return _Capture(graph, bodies, context).finish()


def project_queries(root, graph, context, nodes, symbols, edges, entity_nodes,
                    entity_attributes, repository_models, add_node, add_edge, diagnostics):
    """Resolve saved intent only against the final, context-local effective ORM model."""
    types = {s.get('owner'): s for s in symbols.values() if s.get('kind') in {'class', 'interface'}}
    sites = {s['id']: s for s in graph.call_sites if s.get('context_id') == context['id']}
    hashes = {}

    def current(proof):
        if not isinstance(proof, dict):
            return False
        path = proof.get('path')
        if not _source(proof, context) or graph.files.get(path) != proof.get('sha256'):
            return False
        if path not in hashes:
            try:
                candidate = (root / path).resolve()
                candidate.relative_to(root.resolve())
                hashes[path] = hashlib.sha256(candidate.read_bytes()).hexdigest()
            except (ValueError, OSError):
                hashes[path] = None
        return hashes[path] == proof['sha256']

    def valid(record, symbol):
        if (not isinstance(record, dict) or type(record.get('version')) is not int or record['version'] != 2
                or record.get('context_id') != context['id'] or record.get('method') != symbol['id']
                or record.get('id') != digest({k: v for k, v in record.items() if k != 'id'})
                or record.get('family') not in {'CRITERIA', 'SPECIFICATION', 'QUERYDSL'}
                or not isinstance(record.get('entity'), (str, type(None)))
                or not isinstance(record.get('gaps'), list) or not all(isinstance(g, str) for g in record['gaps'])
                or not isinstance(record.get('operations'), list) or not all(isinstance(o, str) for o in record['operations'])
                or not isinstance(record.get('attributes'), list)
                or any(not isinstance(a, dict) or not isinstance(a.get('entity'), str) or not isinstance(a.get('name'), str) for a in record['attributes'])
                or not _range(record.get('range'))
                or not isinstance(record.get('witnesses'), list) or not record['witnesses']
                or not current(symbol) or context.get('freshness') != 'CONTENT_VERIFIED'):
            return False
        for witness in record['witnesses']:
            if not current(witness):
                return False
            if 'compiler_contract' in witness and (witness['compiler_contract'] != symbol.get('query_override')
                    or not _spec_override(symbol, symbols, context)):
                return False
            if witness.get('call_site'):
                site = sites.get(witness['call_site'], {})
                target = symbols.get(witness.get('compiler_target'), {})
                if (site.get('caller') != symbol['id'] or site.get('declared_target') != target.get('id')
                        or site.get('range') != witness.get('range') or not current(site)
                        or site.get('evidence_kind') != 'SYMBOL_RESOLVED' or not _dependency(target, context)):
                    return False
        if record['family'] == 'SPECIFICATION' and symbol.get('kind') == 'method':
            if (not _spec_override(symbol, symbols, context)
                    or not any(w.get('compiler_contract') == symbol['query_override'] for w in record['witnesses'])):
                return False
        if record['family'] == 'QUERYDSL':
            for attribute in record['attributes']:
                member = symbols.get(attribute.get('symbol'), {})
                path = member.get('querydsl_path') or {}
                if (not current(member) or 'final' not in member.get('modifiers', [])
                        or path.get('entity_type') != attribute['entity'] or path.get('attribute') != attribute['name']
                        or not _dependency(symbols.get(path.get('factory'), {}), context)):
                    return False
        return True

    def fragment(symbol, entity):
        owner = types.get(symbol.get('owner'), {})
        inherited = {str(t).split('<', 1)[0] for t in owner.get('supertypes', [])}
        candidates = []
        for repository, model in repository_models.items():
            if model != entity:
                continue
            repo = types.get(repository, {})
            if not any(_dependency(symbols.get(c.get('symbol'), {}), context)
                       and symbols.get(c.get('symbol'), {}).get('owner') in {
                           'org.springframework.data.jpa.repository.JpaRepository',
                           'org.springframework.data.repository.CrudRepository',
                           'org.springframework.data.repository.PagingAndSortingRepository',
                           'org.springframework.data.repository.Repository'}
                       for c in repo.get('query_type_contracts', [])):
                continue
            for contract in inherited.intersection(str(t).split('<', 1)[0] for t in repo.get('supertypes', [])):
                declaration = types.get(contract, {})
                methods = [s for s in symbols.values() if s.get('owner') == contract
                           and s.get('name') == symbol.get('name') and s.get('descriptor') == symbol.get('descriptor')
                           and s.get('kind') == 'method']
                if declaration.get('kind') == 'interface' and len(methods) == 1:
                    implementations = [s for s in types.values() if s.get('kind') == 'class'
                                       and contract in {str(t).split('<', 1)[0] for t in s.get('supertypes', [])}
                                       and 'abstract' not in s.get('modifiers', [])]
                    candidates.append({'repository': repo['id'], 'contract': declaration['id'],
                                       'method': methods[0]['id'], 'implementation': owner.get('id'),
                                       'implementations': sorted(s['id'] for s in implementations)})
        if not candidates:
            return None
        return {'status': 'UNIQUE_DECLARATION' if len(candidates) == 1 and len(candidates[0]['implementations']) == 1
                else 'UNKNOWN', 'candidates': candidates, 'execution': 'NOT_OBSERVED'}

    for symbol in list(symbols.values()):
        records = symbol.get('programmatic_queries', [])
        if not isinstance(records, list):
            diagnostics.append({'code': 'ORM_PROGRAMMATIC_PROVENANCE_INVALID', 'method': symbol['id']})
            continue
        for record in records:
            if not valid(record, symbol):
                diagnostics.append({'code': 'ORM_PROGRAMMATIC_PROVENANCE_INVALID', 'method': symbol['id'],
                                    'path': symbol.get('path'), 'reason': 'Programmatic intent is stale, malformed or foreign; no query projection.'})
                continue
            entity = record.get('entity')
            entity_id = entity_nodes.get(entity)
            active_entity = entity_id in nodes and any(e.source == entity_id and e.kind == 'maps_to_table'
                                                       and e.context_ids == (context['id'],) for e in edges.values())
            gaps = list(record['gaps'])
            if not active_entity:
                gaps.append('ENTITY_UNRESOLVED_IN_SELECTED_PERSISTENCE_UNIT')
            resolved = []
            for attribute in record['attributes']:
                identity = entity_attributes.get(entity, {}).get(attribute['name'].casefold())
                node = nodes.get(identity)
                if (not active_entity or attribute.get('entity') != entity or node is None
                        or (node.metadata or {}).get('context_id') != context['id']
                        or (node.metadata or {}).get('attribute') != attribute['name']
                        or (node.metadata or {}).get('mapping_status') == 'UNKNOWN'):
                    gaps.append('ATTRIBUTE_UNRESOLVED:' + attribute['name'])
                else:
                    resolved.append(identity)
            frag = fragment(symbol, entity)
            if frag and frag['status'] == 'UNKNOWN':
                gaps.append('REPOSITORY_FRAGMENT_AMBIGUOUS')
            gaps = sorted(set(gaps))
            # Conditional builders and multiple roots do not establish one complete query intent.
            unsafe = any(g in gaps for g in ('DYNAMIC_CONTROL_FLOW', 'REASSIGNMENT_UNSUPPORTED',
                         'MULTIPLE_ROOTS_UNSUPPORTED', 'MULTIPLE_QUERIES_UNSUPPORTED', 'FOREIGN_QUERY_ROOT',
                         'COMPILER_BODY_UNAVAILABLE', 'CUSTOM_QUERY_HELPER_UNSUPPORTED', 'QUERY_STATE_ESCAPES_LOCAL'))
            if unsafe:
                resolved = []
                active_entity = False
            status = 'COMPLETE' if not gaps else 'PARTIAL' if active_entity else 'UNKNOWN'
            path, line = symbol['path'], record['range'].get('start_line')
            query = add_node('orm_query', symbol['name'] + ':' + record['family'], path, line, nodes[symbol['id']],
                             declaration_identity=record['id'], query_language=record['family'], query=None,
                             method=symbol['id'], entity=entity, operations=record['operations'],
                             dynamic=bool(gaps), validated=not gaps, analysis_status=status, gaps=gaps,
                             query_intent_version=VERSION, execution='NOT_OBSERVED', availability='UNKNOWN',
                             repository_fragment=frag, compiler_witnesses=record['witnesses'])
            proof_symbol = {**symbol, 'programmatic_query_provenance': {
                'version': VERSION, 'candidate_id': record['id'], 'witnesses': record['witnesses']}}
            add_edge(symbol['id'], query, 'declares_query', path, line,
                     'Compiler-backed bounded programmatic query intent; no generated query text', compiler_fact=proof_symbol)
            if active_entity:
                add_edge(query, entity_id, 'query_reads', path, line,
                         'Potential query root in the selected effective persistence model; not execution', compiler_fact=proof_symbol)
            for identity in sorted(set(resolved)):
                add_edge(query, identity, 'filters_by', path, line,
                         'Compiler API receiver and static attribute in final effective ORM model', compiler_fact=proof_symbol)
            if frag and frag['status'] == 'UNIQUE_DECLARATION':
                candidate = frag['candidates'][0]
                add_edge(candidate['repository'], query, 'repository_uses_fragment', path, line,
                         'One source-declared repository fragment implementation; runtime selection not observed',
                         compiler_fact=proof_symbol, supporting_facts=[symbols[candidate[k]] for k in ('repository', 'contract', 'method', 'implementation')])
            for gap in gaps:
                diagnostics.append({'code': 'ORM_PROGRAMMATIC_QUERY_PARTIAL', 'path': path, 'source_line': line,
                                    'method': symbol['id'], 'query': query, 'reason': gap, 'status': status})

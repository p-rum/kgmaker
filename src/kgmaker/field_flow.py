"""Bounded compiler-owned field transfers, not object alias or business proofs.

Consume the existing validated return IR. Only Java direct bindings and closed,
straight-line source helpers participate in cross-method transfers. No mapper
annotation, matching property name, or generated filename is a mapping proof.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .analysis_model import digest
from .model import Edge, KnowledgeGraph, Node
from .return_flow import _children

VERSION = 'field-mapping-1'


@dataclass
class _Value:
    source: str
    provenance: list[dict]


class _Fields:
    def __init__(self, graph, bodies, context):
        self.graph, self.context = graph, context
        self.nodes = {n.id: n for n in graph.nodes}
        self.symbols = {s['id']: s for s in graph.symbols}
        self.sites = {s['id']: s for s in graph.call_sites}
        self.bodies = {b['method']: b for b in bodies if b.get('context_id') == context['id']}
        self.edges, self.proofs, self.diagnostics = [], {}, []
        self.summaries = {}
        self.parameters = {}
        for symbol in graph.symbols:
            if symbol.get('kind') == 'parameter':
                self.parameters.setdefault(symbol.get('method'), []).append(symbol)
        for method, parameters in self.parameters.items():
            self.parameters[method] = [s['id'] for s in sorted(parameters, key=lambda s: s.get('parameter_index', 0))]
        self.argument_bindings = {}
        for proof in graph.evidence:
            if (proof.get('argument_mapping_version') == 1 and proof.get('relation') == 'argument_to_parameter'
                    and proof.get('kind') == 'SYMBOL_RESOLVED' and proof.get('transformation') == 'DIRECT'):
                self.argument_bindings.setdefault(proof.get('call_site'), {})[proof['target']] = proof['argument_index']
        self.steps = 0

    def locator(self, node, method, call_site=None):
        return {'method': method, 'path': node.get('path'), 'range': node.get('range'),
                'sha256': node.get('sha256'), 'call_site': call_site}

    def issue(self, reason, node, method):
        record = {'code': reason, 'reason': reason, 'status': 'UNKNOWN',
                  'context_id': self.context['id'], 'method': method,
                  'path': node.get('path'), 'range': node.get('range')}
        if record not in self.diagnostics:
            self.diagnostics.append(record)

    def supported(self, method):
        body = self.bodies.get(method, {})
        symbol = self.symbols.get(method, {})
        return (body.get('language') == 'java' and body.get('return_flow_version') == 1
                and body.get('return_body_kind') == 'DECLARED'
                and symbol.get('context_id') == self.context['id']
                and (self.context.get('scope') == 'all' or symbol.get('scope') == self.context.get('scope')))

    def direct(self, site):
        target = self.symbols.get(site.get('declared_target'), {})
        modifiers = target.get('modifiers') or []
        return (site.get('evidence_kind') == 'SYMBOL_RESOLVED'
                and site.get('argument_mapping_status') == 'PROVEN'
                and site.get('invocation_kind') != 'METHOD_REFERENCE'
                and set(site.get('dispatch_candidates', [])) <= {site.get('declared_target')}
                and (target.get('jvm_static') is True or any(m in modifiers for m in ('static', 'final', 'private'))
                     or site.get('invocation_kind') in {'STATIC', 'SPECIAL'}))

    def proof(self, source, target, relation, loc, method, provenance, guards=(), **extra):
        if source not in self.nodes or target not in self.nodes:
            return
        record = {'kind': 'SYMBOL_RESOLVED', 'source': source, 'target': target, 'relation': relation,
                  'field_mapping_version': 1, 'extractor': VERSION, 'owner_method': method,
                  'context_ids': [self.context['id']], 'source_file': loc.get('path'),
                  'source_range': loc.get('range'), 'sha256': loc.get('sha256'),
                  'provenance': provenance, 'branch_guards': list(guards),
                  'availability': 'UNKNOWN', 'runtime_execution': 'NOT_OBSERVED',
                  'business_equivalence': 'UNKNOWN', **extra}
        identity = 'evidence:' + digest(record)
        if identity in self.proofs:
            return
        self.proofs[identity] = {'id': identity, **record}
        self.edges.append(Edge(source, target, relation, evidence_kind='SYMBOL_RESOLVED',
                               context_ids=(self.context['id'],), evidence_ids=(identity,),
                               source_file=loc.get('path'), source_line=(loc.get('range') or {}).get('start_line')))

    def access(self, field, kind, loc, method, guards=(), provenance=None):
        if field not in self.nodes or not isinstance(loc.get('range'), dict):
            return
        identity = method + ':' + kind + ':' + digest({'field': field, 'path': loc.get('path'),
                                                       'range': loc['range'], 'sha256': loc.get('sha256')})
        owner = self.nodes[method]
        metadata = {'field_mapping_version': 1, 'owner_method': method, 'context_id': self.context['id'],
                    'id': identity, 'path': loc['path'], 'sha256': loc['sha256'], 'range': loc['range'],
                    'value_role': kind.upper(), 'availability': 'UNKNOWN', 'runtime_execution': 'NOT_OBSERVED'}
        self.nodes[identity] = Node(identity, 'value', kind.replace('_', ' '), loc['path'],
                                    line=loc['range'].get('start_line'), scope=owner.scope,
                                    role='contract', origin=owner.origin, metadata=metadata)
        self.proof(identity, field, 'reads_value' if kind == 'field_read' else 'writes_value', loc, method,
                   provenance or [self.locator(loc, method)], guards)

    def transfer(self, target, value, loc, method, guards, provenance):
        self.access(target, 'field_write', loc, method, guards, provenance)
        if value is not None and len(value.provenance) + len(provenance) > 256:
            self.issue('FIELD_MAPPING_LIMIT', loc, method)
            return
        if value is not None and self.symbols.get(value.source, {}).get('kind') == 'field':
            self.proof(value.source, target, 'maps_to', loc, method, value.provenance + provenance, guards,
                       transformation='DIRECT_ASSIGNMENT', identity_scope='FIELD_DECLARATION')
        else:
            self.issue('FIELD_MAPPING_VALUE_UNKNOWN', loc, method)

    def substitute(self, value, arguments, parameters, bindings):
        if value is None:
            return None
        if value.source in parameters:
            index = bindings.get(value.source)
            source = arguments[index] if type(index) is int and 0 <= index < len(arguments) else None
            return _Value(source.source, source.provenance + value.provenance) if source is not None else None
        return value

    def expression(self, node, env, method, stack=(), *, emit=False, guards=()):
        self.steps += 1
        if self.steps > 50000 or len(stack) > 16:
            if emit: self.issue('FIELD_MAPPING_LIMIT', node, method)
            return None, [], False
        kind = node.get('kind')
        binding = node.get('value_binding')
        if isinstance(binding, dict) and kind != 'assign':
            if binding['kind'] == 'FIELD':
                if emit: self.access(binding['symbol'], 'field_read', node, method, guards)
                return _Value(binding['symbol'], [self.locator(node, method)]), [], True
            if binding['kind'] == 'PARAMETER' and binding.get('method') == method:
                return env.get(binding['id'], _Value(binding['id'], [self.locator(node, method)])), [], True
            if binding['kind'] == 'LOCAL_VARIABLE' and binding.get('method') == method:
                return env.get(binding['id']), [], True
            return None, [], False
        if kind == 'call':
            args = [self.expression(arg, env, method, stack, emit=emit, guards=guards)[0]
                    for arg in node.get('arguments', [])]
            self.expression(node.get('receiver', {}), env, method, stack, emit=emit, guards=guards)
            site = self.sites.get(node.get('call_site'), {})
            target = site.get('declared_target')
            summary = self.summary(target, stack) if self.direct(site) else None
            if summary is None:
                if emit and self.symbols.get(target, {}).get('name') != '<init>':
                    self.issue('FIELD_MAPPING_CALL_BODY_UNKNOWN', node, method)
                return None, [], False
            value, writes, parameters = summary
            call = self.locator(node, method, site['id'])
            bindings = self.argument_bindings.get(site['id'], {})
            result = self.substitute(value, args, parameters, bindings)
            if result is not None:
                if len(result.provenance) >= 256:
                    if emit: self.issue('FIELD_MAPPING_LIMIT', node, method)
                    return None, [], False
                result = _Value(result.source, result.provenance + [call])
            effects = []
            for field, source, provenance in writes:
                mapped = self.substitute(source, args, parameters, bindings)
                trail = provenance + [call]
                effects.append((field, mapped, trail))
                if emit: self.transfer(field, mapped, node, method, guards, trail)
            # A returned value after writes is not a pure value helper.
            return (None if writes else result), effects, True
        if node.get('literal') is not None or kind in {'empty', 'reference'}:
            return None, [], True
        if emit:
            self.issue('FIELD_MAPPING_EXPRESSION_UNKNOWN', node, method)
        return None, [], False

    def summary(self, method, stack):
        if method in stack or len(stack) >= 16 or not self.supported(method):
            return None
        if method in self.summaries:
            return self.summaries[method]
        # Restrict summaries to straight-line source: no branch, loop, exception,
        # array, arithmetic, reflection or delegated object/receiver mutation.
        body = self.bodies[method]['body']
        statements = body.get('statements', []) if body.get('kind') == 'block' else []
        env, writes, returned = {}, [], None
        parameter_ids = self.parameters.get(method, [])
        for i, node in enumerate(statements):
            kind = node.get('kind')
            expr = node.get('value', {}) if kind in {'assign', 'return'} else node
            value, effects, valid = self.expression(expr, env, method, stack + (method,))
            if not valid:
                return None
            writes.extend(effects)
            if kind == 'assign':
                binding = node.get('value_binding') or {}
                if binding.get('kind') == 'FIELD':
                    writes.append((binding['symbol'], value, [self.locator(node, method)]))
                elif binding.get('kind') == 'LOCAL_VARIABLE': env[binding['id']] = value
                else: return None
            elif kind == 'return':
                if i != len(statements) - 1: return None
                returned = value
            elif kind not in {'call', 'empty'}:
                return None
        result = (returned, writes, parameter_ids)
        # Recursion failures are never cached as a successful summary.
        self.summaries[method] = result
        return result

    def walk(self, node, env, method, guards=(), depth=0):
        if depth > 64 or self.steps > 50000:
            self.issue('FIELD_MAPPING_LIMIT', node, method)
            env.clear()
            return False
        kind = node.get('kind')
        if kind == 'block':
            for child in node.get('statements', []):
                if self.walk(child, env, method, guards, depth + 1): return True
        elif kind == 'if':
            self.expression(node.get('condition', {}), env, method, emit=True, guards=guards)
            left, right = dict(env), dict(env)
            yes = guards + ({'range': node.get('range'), 'branch': 'TRUE'},)
            no = guards + ({'range': node.get('range'), 'branch': 'FALSE'},)
            left_end = self.walk(node.get('then', {}), left, method, yes, depth + 1)
            right_end = self.walk(node.get('else', {}), right, method, no, depth + 1)
            env.clear()
            if left_end and right_end: return True
            if left_end: env.update(right)
            elif right_end: env.update(left)
            else: env.update({key: left[key] if left[key] == right.get(key) else None for key in left})
        elif kind == 'assign':
            value, _, _ = self.expression(node.get('value', {}), env, method, emit=True, guards=guards)
            binding = node.get('value_binding') or {}
            if binding.get('kind') == 'FIELD':
                self.transfer(binding['symbol'], value, node, method, guards, [self.locator(node, method)])
            elif binding.get('kind') in {'LOCAL_VARIABLE', 'PARAMETER'}:
                env[binding['id']] = value
            else:
                env.clear()
                self.issue('FIELD_MAPPING_TARGET_UNKNOWN', node, method)
        elif kind == 'return':
            self.expression(node.get('value', {}), env, method, emit=True, guards=guards)
            return True
        elif kind in {'call', 'statement', 'reference', 'empty'}:
            _, _, valid = self.expression(node, env, method, emit=True, guards=guards)
            if not valid and kind != 'call': env.clear()
        else:
            env.clear()
            self.issue('FIELD_MAPPING_CONTROL_FLOW_UNKNOWN', node, method)
        return False

    def relevant_methods(self):
        # Bound diagnostics to source bodies with field accesses, and their
        # callers. An unrelated Java function is not a failed mapper analysis.
        relevant = set()
        for method, body in self.bodies.items():
            pending = [body.get('body', {})]
            while pending:
                node = pending.pop()
                bindings = [node.get('value_binding') or {}] + node.get('referenced_bindings', [])
                if any(b.get('kind') == 'FIELD' for b in bindings):
                    relevant.add(method)
                    break
                pending.extend(_children(node))
        callers = {}
        for site in self.sites.values():
            callers.setdefault(site.get('declared_target'), set()).add(site.get('caller'))
        pending = list(relevant)
        while pending:
            for method in callers.get(pending.pop(), set()) - relevant:
                relevant.add(method)
                pending.append(method)
        return relevant

    def finish(self):
        relevant = self.relevant_methods()
        for method, body in sorted(self.bodies.items()):
            if method in relevant and self.supported(method):
                self.walk(body['body'], {}, method)
        return replace(self.graph, nodes=sorted(self.nodes.values(), key=lambda n: n.id),
                       edges=self.graph.edges + self.edges, evidence=self.graph.evidence + list(self.proofs.values()),
                       diagnostics=self.graph.diagnostics + self.diagnostics)


def augment_field_flow(graph: KnowledgeGraph, bodies: list[dict], context: dict) -> KnowledgeGraph:
    """Call only after return IR validation and before atomic store publication."""
    return _Fields(graph, bodies, context).finish()


def field_mapping_bindings(graph: KnowledgeGraph) -> list[dict]:
    proofs = {p['id']: p for p in graph.evidence if p.get('field_mapping_version') == 1}
    result = []
    for edge in graph.edges:
        if edge.kind not in {'maps_to', 'reads_value', 'writes_value'} or edge.evidence_kind != 'SYMBOL_RESOLVED':
            continue
        for identity in edge.evidence_ids:
            proof = proofs.get(identity)
            if proof and (proof['source'], proof['target'], proof['relation']) == (edge.source, edge.target, edge.kind):
                result.append(proof)
    return sorted(result, key=lambda p: p['id'])

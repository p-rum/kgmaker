"""Conservative field inventory, local Kotlin expressions and directed impact.

No name-only cross-file call resolution is treated as a data path. Unsupported
expressions produce diagnostics; all paths are static dependencies, not proof of
runtime availability or business equivalence.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path

from .model import Edge, KnowledgeGraph, Node

PARSER_VERSION = 'dataflow-1'
CAPABILITIES = {
    'version': PARSER_VERSION,
    'fields': ['Kotlin primary constructor val/var', 'Java records and simple fields',
               'TypeScript interface/type properties', 'JSON Schema/OpenAPI JSON properties'],
    'value_flow': ['Kotlin expression functions with explicit parameter/return types',
                   'local numeric/property expressions', 'unambiguous Kotlin constructor mapping'],
    'unsupported': ['SOURCE_ONLY overloaded/interprocedural calls', 'control-flow-dependent mappings', 'dynamic SQL',
                    'OpenAPI YAML fields', 'Kafka payload resolution', 'frontend binding', 'template binding'],
}
# Direction of propagation of a changed value, not direction of its stored edge.
FORWARD = {'maps_to', 'serialized_as', 'displayed_in', 'rendered_in', 'sent_to',
           'tested_by', 'documented_by', 'writes_value', 'argument_to_parameter'}
REVERSE = {'reads_value', 'derived_from', 'persisted_in', 'asserts_field', 'targets_ui',
           'tests_endpoint', 'uses_fixture', 'depends_on_contract'}


def masked(text: str) -> str:
    """Blank comments/string contents while preserving offsets and line numbers."""
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|`(?:\\.|[^`\\])*`'
    return re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)


def closing(text: str, start: int, opening='(', ending=')') -> int | None:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == ending:
            depth -= 1
            if depth == 0:
                return index
    return None


def parts(text: str) -> list[str]:
    return [x.strip() for x in text.split(',') if x.strip()]


@dataclass
class Extraction:
    nodes: list[Node]
    edges: list[Edge]
    diagnostics: list[dict]


def extract_dataflow(sources: dict[str, str]) -> Extraction:
    nodes, edges, diagnostics = {}, set(), []
    types = defaultdict(list)
    fields = {}
    texts = {path: masked(text) for path, text in sources.items()}

    def node(path, kind, qualified, offset, signature=None, summary=None):
        identity = f'{kind}:{path}:{qualified}'
        result = Node(identity, kind, qualified, path,
                      sources[path].count('\n', 0, offset) + 1 if offset is not None else None,
                      signature, summary)
        if identity in nodes:
            diagnostics.append({'path': path, 'line': result.line, 'reason': 'duplicate declaration identity: ' + qualified})
        nodes[identity] = result
        return result

    def issue(path, offset, reason):
        diagnostics.append({'path': path, 'line': sources[path].count('\n', 0, offset) + 1, 'reason': reason})

    def relation(source, target, kind, path, offset, evidence):
        edges.add(Edge(source.id, target.id, kind, evidence, source_file=path,
                       source_line=sources[path].count('\n', 0, offset) + 1))

    # Collect owners before resolving any mapping; duplicate names stay ambiguous.
    for path, text in sorted(texts.items()):
        suffix = Path(path).suffix.lower()
        if suffix in {'.kt', '.kts'}:
            declarations = list(re.finditer(r'\b(?:data\s+)?class\s+(\w+)\s*\(', text))
            for match in declarations:
                start = text.index('(', match.start())
                end = closing(text, start)
                if end is None:
                    issue(path, start, 'unclosed primary constructor')
                    continue
                owner = match[1]
                properties = []
                for prop in re.finditer(r'\b(?:val|var)\s+(\w+)\s*:\s*([\w.]+\??)', text[start + 1:end]):
                    offset = start + 1 + prop.start()
                    result = node(path, 'data_field', owner + '.' + prop[1], offset, prop[2])
                    properties.append((prop[1], result))
                types[owner].append((path, properties))
                fields[path, owner] = dict(properties)
        elif suffix == '.java':
            for match in re.finditer(r'\brecord\s+(\w+)\s*\(([^()]*)\)', text):
                properties = []
                for prop in re.finditer(r'([\w.]+)\s+(\w+)\s*(?:,|$)', match[2]):
                    result = node(path, 'data_field', match[1] + '.' + prop[2], match.start(2) + prop.start(), prop[1])
                    properties.append((prop[2], result))
                types[match[1]].append((path, properties))
                fields[path, match[1]] = dict(properties)
            for match in re.finditer(r'\bclass\s+(\w+)[^{]*\{', text):
                start = text.index('{', match.start())
                end = closing(text, start, '{', '}')
                if end is None:
                    continue
                body = text[start + 1:end]
                # Keep only statements at class brace depth zero (not method locals).
                depth = 0
                filtered = []
                for c in body:
                    if c == '{': depth += 1
                    filtered.append(c if depth == 0 else '\n' if c == '\n' else ' ')
                    if c == '}': depth -= 1
                properties = []
                for prop in re.finditer(r'(?m)(?:^|(?<=;))\s*(?:(?:public|private|protected|static|final|volatile|transient)\s+)*([\w.]+)\s+(\w+)\s*(?:=[^;]*)?;', ''.join(filtered)):
                    result = node(path, 'data_field', match[1] + '.' + prop[2], start + 1 + prop.start(), prop[1])
                    properties.append((prop[2], result))
                types[match[1]].append((path, properties))
                fields[path, match[1]] = dict(properties)
        elif suffix in {'.ts', '.tsx'}:
            for match in re.finditer(r'\b(?:interface\s+(\w+)|type\s+(\w+)\s*=)\s*\{([^{}]*)\}', text):
                owner = match[1] or match[2]
                properties = []
                for prop in re.finditer(r'(?:^|[;,\n])\s*(?:readonly\s+)?(\w+)(\?)?\s*:\s*([\w.]+(?:\[\])?)\s*(?=[;,\n]|$)', match[3]):
                    result = node(path, 'data_field', owner + '.' + prop[1], match.start(3) + prop.start(), prop[3] + ('?' if prop[2] else ''))
                    properties.append((prop[1], result))
                types[owner].append((path, properties))
                fields[path, owner] = dict(properties)
        elif suffix == '.json':
            try:
                document = json.loads(sources[path])
            except (ValueError, RecursionError):
                continue
            def walk(value, pointer=''):
                if isinstance(value, dict):
                    if isinstance(value.get('properties'), dict):
                        for key, specification in value['properties'].items():
                            location = pointer + '/properties/' + key.replace('~', '~0').replace('/', '~1')
                            node(path, 'contract_field', location, None,
                                 specification.get('type') if isinstance(specification, dict) and isinstance(specification.get('type'), str) else None,
                                 'JSON pointer ' + location)
                    for key, child in value.items():
                        walk(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
                elif isinstance(value, list):
                    for index, child in enumerate(value):
                        walk(child, pointer + '/' + str(index))
            try:
                walk(document)
            except RecursionError:
                issue(path, 0, 'JSON schema nesting exceeds supported depth')

    # Only explicit, simple Kotlin function scopes; never resolve calls by name.
    for path, text in sorted(texts.items()):
        if Path(path).suffix.lower() not in {'.kt', '.kts'}:
            continue
        owner_scopes = []
        for owner in re.finditer(r'\b(?:class|object)\s+(\w+)(?:\s*\([^{}]*?\))?(?:\s*:\s*[^{}\n]+)?\s*\{', text):
            start = text.index('{', owner.start())
            end = closing(text, start, '{', '}')
            if end is not None:
                owner_scopes.append((start, end, owner[1]))
        for match in re.finditer(r'\bfun\s+(\w+)\s*\(([^()]*)\)\s*:\s*([\w.]+\??)\s*(=|\{)', text):
            owners = [name for start, end, name in owner_scopes if start < match.start() < end]
            method = '.'.join(owners + [match[1]]) + '(' + ','.join(p.strip() for p in parts(match[2])) + ')'
            offset = match.end()
            if match[4] == '{':
                end = closing(text, offset - 1, '{', '}')
                if end is None:
                    issue(path, offset, 'unclosed function body')
                    continue
                body = text[offset:end]
            else:
                end = text.find('\n', offset)
                end = len(text) if end == -1 else end
                body = 'return ' + text[offset:end]
            if re.search(r'\b(if|when|for|while|try|catch|throw)\b|[{}]', body):
                issue(path, offset, 'control flow is unsupported for value mapping')
                continue
            statements = [line.strip() for line in body.splitlines() if line.strip()]
            if any(not re.fullmatch(r'(?:val\s+\w+(?:\s*:\s*[\w.]+\??)?\s*=\s*.+|return\s+.+)', line) for line in statements):
                issue(path, offset, 'unsupported statement prevents reliable function mapping')
                continue
            if sum(line.startswith('return ') for line in statements) != 1 or not statements[-1].startswith('return '):
                issue(path, offset, 'simple function requires one final return')
                continue
            values, variable_types = {}, {}
            for param in parts(match[2]):
                parsed = re.fullmatch(r'(\w+)\s*:\s*([\w.]+\??)', param)
                if not parsed:
                    issue(path, match.start(), 'unsupported function parameter')
                    continue
                values[parsed[1]] = node(path, 'parameter', method + ':' + parsed[1], match.start(), parsed[2])
                variable_types[parsed[1]] = parsed[2].rstrip('?').split('.')[-1]
            result = node(path, 'return_value', method, match.start(), match[3])

            def resolve(token):
                if '.' not in token:
                    return values.get(token)
                variable, property_name = token.split('.', 1)
                typename = variable_types.get(variable)
                candidates = types.get(typename, [])
                # Even same-file preference is unsafe without import/package resolution.
                if len(candidates) != 1:
                    return None
                return dict(candidates[0][1]).get(property_name)

            def expression(value, destination, statement_offset):
                value = value.strip().rstrip(';').strip()
                constructor = re.fullmatch(r'(\w+)\s*\(([^()]*)\)', value)
                if constructor:
                    choices = types.get(constructor[1], [])
                    if len(choices) != 1:
                        issue(path, statement_offset, 'unresolved/ambiguous constructor: ' + constructor[1])
                        return
                    declared = choices[0][1]
                    arguments = parts(constructor[2])
                    if len(arguments) != len(declared):
                        issue(path, statement_offset, 'constructor defaults/arity are unsupported')
                        return
                    mapped = []
                    for index, argument in enumerate(arguments):
                        if '=' in argument:
                            name, argument = argument.split('=', 1)
                            target = dict(declared).get(name.strip())
                        else:
                            target = declared[index][1]
                        source = resolve(argument.strip())
                        if source is None or target is None:
                            issue(path, statement_offset, 'constructor arguments must resolve to direct values')
                            return
                        mapped.append((source, target))
                    if len({target.id for _, target in mapped}) != len(mapped):
                        issue(path, statement_offset, 'duplicate constructor target')
                        return
                    for source, target in mapped:
                        relation(source, target, 'maps_to', path, statement_offset, value)
                        relation(destination, target, 'reads_value', path, statement_offset, value)
                    return
                # Restrict to literals, parameters, single property reads and arithmetic.
                if not re.fullmatch(r'[\w.\s+*/%()\-]+', value) or re.search(r'[A-Za-z_]\w*\s*\(', value):
                    issue(path, statement_offset, 'unsupported expression: ' + value[:120])
                    return
                tokens = re.findall(r'\b[A-Za-z_]\w*(?:\.\w+)?', value)
                references = [resolve(token) for token in tokens]
                if any(reference is None for reference in references):
                    issue(path, statement_offset, 'unresolved expression input: ' + value[:120])
                    return
                for source in references:
                    relation(destination, source, 'derived_from', path, statement_offset, value)

            for line in body.splitlines():
                statement = line.strip()
                if not statement:
                    offset += len(line) + 1
                    continue
                local = re.fullmatch(r'val\s+(\w+)(?:\s*:\s*([\w.]+\??))?\s*=\s*(.+?);?', statement)
                if local:
                    destination = node(path, 'local_value', method + ':' + local[1], min(offset, len(text)), local[2], 'Declared expression: ' + local[3])
                    expression(local[3], destination, min(offset, len(text)))
                    values[local[1]] = destination
                    if local[2]:
                        variable_types[local[1]] = local[2].rstrip('?').split('.')[-1]
                elif statement.startswith('return '):
                    expression(statement[7:], result, min(offset, len(text)))
                else:
                    issue(path, min(offset, len(text)), 'unsupported statement in simple function')
                offset += len(line) + 1
    return Extraction(sorted(nodes.values(), key=lambda n: n.id),
                      sorted(edges, key=lambda e: (e.source, e.kind, e.target, e.source_line or 0)),
                      sorted(diagnostics, key=lambda d: (d['path'], d['line'], d['reason'])))


def impact_paths(graph: KnowledgeGraph, entity: str, max_depth: int = 20) -> dict:
    """Breadth-first shortest paths with relationship-specific direction."""
    nodes = {n.id: n for n in graph.nodes}
    if entity not in nodes:
        raise ValueError('Entity is not in the current graph: ' + entity)
    adjacency = defaultdict(list)
    binding_evidence = {value['id']: value for value in graph.evidence
                        if value.get('argument_mapping_version') == 1}
    for edge in graph.edges:
        if edge.kind == 'argument_to_parameter' and (edge.evidence_kind != 'SYMBOL_RESOLVED'
                or not any(identity in binding_evidence for identity in edge.evidence_ids)):
            continue
        if edge.kind in FORWARD:
            adjacency[edge.source].append((edge.target, edge))
        elif edge.kind in REVERSE:
            adjacency[edge.target].append((edge.source, edge))
    queue = deque([(entity, [], [entity])])
    seen, paths = {entity}, []
    truncated = False
    rank = {'EXTRACTED': 0, 'INFERRED': 1, 'AMBIGUOUS': 2}
    while queue:
        current, steps, chain = queue.popleft()
        if len(steps) >= max_depth:
            truncated = truncated or bool(adjacency[current])
            continue
        for target, edge in sorted(adjacency[current], key=lambda x: (x[0], x[1].kind)):
            if target in seen or target not in nodes:
                continue
            seen.add(target)
            # Keep the feature v1 path proof contract stable. Typed inspection
            # evidence is a separate contract, never inferred from this path.
            next_steps = steps + [{key: value for key, value in asdict(edge).items()
                                   if key not in {"evidence_kind", "context_ids", "evidence_ids"}}]
            weakest = max((step['confidence'] for step in next_steps), key=lambda x: rank.get(x, 3))
            boundary = 'external system; internals not inspected' if nodes[target].kind in {'external_service', 'external_system'} else (
                'no further supported dependency' if not adjacency[target] else None)
            paths.append({'entity_ids': chain + [target], 'edges': next_steps,
                          'weakest_confidence': weakest, 'unresolved_boundary': boundary})
            if boundary != 'external system; internals not inspected':
                queue.append((target, next_steps, chain + [target]))
    used = {value for path in paths for value in path['entity_ids']}
    binding_sites = sorted({value['call_site'] for value in binding_evidence.values()
                            if value.get('source') in used or value.get('target') in used})
    bindings = [item for site in binding_sites for item in argument_parameter_bindings(graph, site)]
    return {'seed': entity, 'paths': paths, 'truncated': truncated,
            'argument_parameter_bindings': bindings,
            'limitations': CAPABILITIES['unsupported'],
            'interpretation': 'static value dependency, not runtime availability or business equivalence'}


def validate_argument_bindings(response: dict) -> None:
    """Validate additive compiler bindings before publishing any graph generation.

    Legacy unversioned compiler facts remain readable. Version1 means declared
    formal binding only; it never claims a runtime implementation or evaluation.
    """
    symbols = {value['id']: value for value in response['symbols']}
    sites = {value['id']: value for value in response['call_sites']}
    seen = set()
    for site in response['call_sites']:
        if 'argument_mapping_version' in site and (type(site['argument_mapping_version']) is not int
                or site['argument_mapping_version'] != 1
                or not isinstance(site.get('argument_mapping_status'), str)
                or site.get('argument_mapping_status') not in {'PROVEN', 'UNKNOWN', 'NOT_EXECUTION'}
                or not isinstance(site.get('argument_mapping_reason'), str)):
            raise ValueError('Invalid call-site argument mapping status')
        if 'argument_omissions' not in site:
            continue
        omissions = site['argument_omissions']
        if not isinstance(omissions, list) or len(omissions) > 10000:
            raise ValueError('Invalid omitted argument mapping')
        omitted_indices = set()
        for omission in omissions:
            if (not isinstance(omission, dict) or type(omission.get('parameter_index')) is not int
                    or omission['parameter_index'] < 0 or omission['parameter_index'] in omitted_indices
                    or not isinstance(omission.get('parameter_name'), str)
                    or omission.get('reason') != 'DEFAULT_VALUE_NOT_EVALUATED'):
                raise ValueError('Invalid omitted argument mapping')
            omitted_indices.add(omission['parameter_index'])
    for fact in response['facts']:
        if fact.get('kind') != 'argument_to_parameter' or 'argument_mapping_version' not in fact:
            continue
        if type(fact['argument_mapping_version']) is not int or fact['argument_mapping_version'] != 1:
            raise ValueError('Unsupported argument mapping version')
        if not isinstance(fact.get('call_site'), str):
            raise ValueError('Invalid compiler argument binding call site')
        site = sites.get(fact.get('call_site'))
        parameter, argument = symbols.get(fact.get('target'), {}), symbols.get(fact.get('source'), {})
        indices = (fact.get('argument_index'), fact.get('parameter_index'))
        if (site is None or not site.get('declared_target') or site.get('invocation_kind') == 'METHOD_REFERENCE'
                or site.get('argument_mapping_version') != 1 or site.get('argument_mapping_status') == 'NOT_EXECUTION'
                or fact.get('context_id') != response['context_id']
                or site.get('context_id') != response['context_id']
                or parameter.get('context_id') != response['context_id']
                or argument.get('context_id') != response['context_id']
                or not isinstance(fact.get('parameter_name'), str) or not fact['parameter_name']
                or any(type(index) is not int or index < 0 for index in indices)
                or fact.get('binding_kind') != 'DECLARED_PARAMETER'
                or fact.get('evidence_kind') != 'SYMBOL_RESOLVED'
                or parameter.get('kind') != 'parameter' or parameter.get('method') != site['declared_target']
                or type(parameter.get('parameter_index')) is not int or parameter['parameter_index'] != indices[1]
                or argument.get('kind') != 'value' or argument.get('call_site') != site['id']
                or argument.get('owner_method') != site['caller']
                or argument.get('id') != site['id'] + ':argument:' + str(indices[0])
                or ('argument_index' in argument and (type(argument['argument_index']) is not int
                                                      or argument['argument_index'] != indices[0]))
                or not isinstance(fact.get('transformation'), str)
                or fact.get('transformation') not in {'DIRECT', 'VARARG_ELEMENT', 'VARARG_ARRAY', 'VARARG_SPREAD'}):
            raise ValueError('Invalid compiler argument binding proof')
        identity = (site['id'], indices[0])
        if identity in seen:
            raise ValueError('Ambiguous compiler argument binding')
        seen.add(identity)


def argument_parameter_bindings(graph: KnowledgeGraph, call_site: str) -> list[dict]:
    """Read preserved static declared-parameter proofs for one original call site."""
    proofs = {value['id']: value for value in graph.evidence}
    result = []
    for edge in graph.edges:
        if edge.kind != 'argument_to_parameter':
            continue
        for identity in edge.evidence_ids:
            proof = proofs.get(identity, {})
            if proof.get('argument_mapping_version') != 1 or proof.get('call_site') != call_site:
                continue
            result.append({'argument': edge.source, 'parameter': edge.target,
                           'call_site': call_site, 'context_ids': list(edge.context_ids),
                           'argument_index': proof['argument_index'], 'parameter_index': proof['parameter_index'],
                           'transformation': proof['transformation'], 'binding_kind': proof['binding_kind'],
                           'evidence_kind': edge.evidence_kind, 'evidence_ids': [identity],
                           'availability': 'UNKNOWN', 'execution': 'NOT_OBSERVED'})
    return sorted(result, key=lambda value: (value['argument_index'], value['parameter_index'], value['parameter']))

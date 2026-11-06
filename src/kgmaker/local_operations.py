"""Bounded compiler operation witnesses; never resolve control-flow feasibility."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import re
import struct

from .analysis_model import digest

VERSION = 'java-local-operations-1'
_INTERNAL_REF = '_verified_local_operation'
_TYPES = frozenset('ZBCSIJFD') | {'Ljava/lang/String;'}
_LITERALS = {'BOOLEAN_LITERAL': 'Z', 'CHAR_LITERAL': 'C', 'INT_LITERAL': 'I',
             'LONG_LITERAL': 'J', 'FLOAT_LITERAL': 'F', 'DOUBLE_LITERAL': 'D',
             'STRING_LITERAL': 'Ljava/lang/String;'}
_BASE = ('method', 'context_id', 'source_file', 'sha256', 'source_range', 'ir_path',
         'ir_digest', 'body_digest', 'operation', 'target_type', 'target_binding',
         'target_declaration')


def _fail(message):
    raise ValueError('Invalid local operation proof: ' + message)


def _range(value):
    return (isinstance(value, dict)
        and set(value) == {'start', 'end', 'start_line', 'end_line', 'start_column', 'end_column'}
        and all(type(v) is int for v in value.values())
        and 0 <= value['start'] < value['end']
        and 1 <= value['start_line'] <= value['end_line']
        and value['start_column'] >= 1 and value['end_column'] >= 1
        and (value['start_line'] != value['end_line'] or value['start_column'] < value['end_column']))


def _walk(root):
    pending = [(root, [])]; count = 0
    while pending:
        value, path = pending.pop(); count += 1
        if count > 200_000 or len(path) > 150:
            _fail('IR limit exceeded')
        if isinstance(value, dict):
            yield value, path
            pending.extend((v, path + [k]) for k, v in reversed(list(value.items()))
                           if isinstance(v, (dict, list)))
        elif isinstance(value, list):
            pending.extend((v, path + [i]) for i, v in reversed(list(enumerate(value)))
                           if isinstance(v, (dict, list)))


def _checksum(context, path):
    if not isinstance(path, str):
        return None
    captured = context.get('source_files')
    value = captured.get(path) if isinstance(captured, dict) else None
    return value if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) else None


def _ir_digest(value):
    # Java literals can contain individual UTF-16 code units. Canonical escaped
    # JSON hashes them without storing their values in graph evidence.
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def _literal(value):
    if not isinstance(value, dict) or value.get('source') != 'COMPILER_LITERAL':
        return False
    kind, item = value.get('type'), value.get('value')
    if kind in ('INT_LITERAL', 'LONG_LITERAL'):
        bits = 32 if kind == 'INT_LITERAL' else 64
        return type(item) is int and -(2 ** (bits - 1)) <= item < 2 ** (bits - 1)
    if kind == 'BOOLEAN_LITERAL':
        return type(item) is bool
    if kind in ('FLOAT_LITERAL', 'DOUBLE_LITERAL'):
        if type(item) not in (int, float):
            return False
        try:
            number = float(item)
        except OverflowError:
            return False
        if not math.isfinite(number):
            return False
        if kind == 'FLOAT_LITERAL':
            try:
                rounded = struct.unpack('!f', struct.pack('!f', number))[0]
            except (OverflowError, struct.error):
                return False
            return math.isfinite(rounded) and (number == 0 or rounded != 0)
        return True
    return isinstance(item, str) and (kind == 'STRING_LITERAL'
        or kind == 'CHAR_LITERAL' and len(item) == 1 and ord(item) <= 65535)


def _assignable(literal, target):
    """Only JLS primitive/string literal assignment conversions, no resolver."""
    source = _LITERALS[literal['type']]
    if target in {'Z', 'Ljava/lang/String;'}:
        return source == target
    if source in {'Z', 'Ljava/lang/String;'}:
        return False
    value = ord(literal['value']) if source == 'C' else literal['value']
    if target in {'B', 'S', 'C'}:
        low, high = {'B': (-128, 127), 'S': (-32768, 32767), 'C': (0, 65535)}[target]
        return source in {'I', 'C'} and low <= value <= high
    return source in {'I': {'I', 'C'}, 'J': {'I', 'J', 'C'},
                      'F': {'I', 'J', 'C', 'F'}, 'D': {'I', 'J', 'C', 'F', 'D'}}.get(target, set())


def _validate_operations(response, context):
    """Validate optional named-Javac-body contracts without mutating raw IR."""
    admitted = []; seen = set()
    if context.get('local_operation_rule_version') != VERSION:
        return admitted
    symbols = {s['id']: s for s in response['symbols'] if isinstance(s.get('id'), str)}
    for body in response['bodies']:
        tree = body.get('body', {})
        if any(_INTERNAL_REF in node for node, _ in _walk(tree)):
            _fail('reserved materializer field supplied by worker')
        if 'local_operation_version' not in body:
            continue
        if type(body['local_operation_version']) is not int or body['local_operation_version'] != 1:
            _fail('unsupported body version')
        if not isinstance(body.get('local_operation_status'), str) or body['local_operation_status'] not in {'AVAILABLE', 'UNAVAILABLE'}:
            _fail('invalid body status')
        if body['local_operation_status'] != 'AVAILABLE':
            continue
        method = symbols.get(body.get('method'), {})
        path = method.get('path'); sha = _checksum(context, path)
        if (body.get('method') in seen or body.get('language') != 'java'
                or method.get('kind') != 'method' or method.get('context_id') != context.get('id')
                or body.get('context_id') != context.get('id') or sha is None
                or method.get('sha256') != sha or method.get('scope') != context.get('scope')
                or not _range(method.get('range'))):
            _fail('uncaptured or ambiguous named Java body')
        if not isinstance(tree, dict) or tree.get('kind') != 'block':
            _fail('named Java method requires its captured block body')
        if (not all(isinstance(context.get(key), str) and context[key] for key in ('repo_id', 'module', 'source_set', 'id'))
                or not all(isinstance(method.get(key), str) and method[key] for key in ('owner', 'name', 'descriptor'))):
            _fail('missing canonical Java method identity')
        expected_method = 'jvm:' + ':'.join(context[key] for key in ('repo_id', 'module', 'source_set', 'id')) + ':method:' + method['owner'] + '.' + method['name'] + method['descriptor']
        if method['id'] != expected_method:
            _fail('Java method identity does not match its selected source realm')
        seen.add(body['method']); body_hash = _ir_digest(tree)
        for node, pointer in _walk(tree):
            witness = node.get('local_operation')
            if witness is None:
                continue
            if (not isinstance(witness, dict) or set(witness) != {'schema_version', 'operation',
                    'target_type', 'target_binding', 'target_declaration'}
                    or type(witness['schema_version']) is not int or witness['schema_version'] != 1
                    or not isinstance(witness['target_type'], str) or witness['target_type'] not in _TYPES
                    or node.get('path') != path or node.get('sha256') != sha
                    or not _range(node.get('range')) or not isinstance(node.get('calls'), list)
                    or node['calls'] or node.get('call_site')):
                _fail('malformed operation/source witness')
            span = node['range']; parent = method['range']
            if not parent['start'] <= span['start'] <= span['end'] <= parent['end']:
                _fail('operation outside canonical method range')
            operation = witness['operation']
            if operation == 'LITERAL_EVALUATION':
                literal = node.get('literal', {})
                if (node.get('kind') != 'statement' or node.get('binding_ref') or node.get('binding')
                        or not _literal(literal)
                        or _LITERALS.get(literal.get('type')) != witness['target_type']
                        or witness['target_binding'] is not None or witness['target_declaration'] is not None):
                    _fail('literal identity/type contradiction')
            elif operation == 'LOCAL_LITERAL_ASSIGNMENT':
                value = node.get('value', {}); literal = value.get('literal', {})
                binding = node.get('binding', {}); declaration = witness['target_declaration']
                if (node.get('kind') != 'assign' or binding.get('kind') != 'LOCAL_VARIABLE'
                        or binding.get('type') != witness['target_type']
                        or binding.get('id') != witness['target_binding']
                        or binding.get('declaration') != declaration
                        or not isinstance(declaration, dict)
                        or not {'path', 'sha256', 'range'} <= set(declaration) <= {'path', 'sha256', 'range', 'origin'}
                        or ('origin' in declaration and declaration['origin'] not in {'handwritten', 'generated'})
                        or declaration['path'] != path or declaration['sha256'] != sha
                        or not _range(declaration['range']) or not _literal(literal)
                        or not _assignable(literal, witness['target_type'])
                        or literal.get('type') not in _LITERALS or not isinstance(value.get('calls'), list)
                        or value['calls'] or value.get('call_site')
                        or value.get('path') != path or value.get('sha256') != sha or not _range(value.get('range'))
                        or not span['start'] <= value['range']['start'] <= value['range']['end'] <= span['end']
                        or value.get('local_operation', {}).get('operation') != 'LITERAL_EVALUATION'):
                    _fail('assignment is not a typed local literal operation')
                declared = declaration['range']
                expected = 'binding:' + context['id'] + ':' + path + ':' + sha + ':' + str(declared['start']) + ':' + str(declared['end'])
                if (witness['target_binding'] != expected
                        or not parent['start'] <= declared['start'] <= declared['end'] <= parent['end']):
                    _fail('local declaration identity/range contradiction')
            else:
                _fail('unsupported operation')
            record = {'method': body['method'], 'context_id': context['id'], 'source_file': path,
                'sha256': sha, 'source_range': deepcopy(span), 'ir_path': pointer,
                'ir_digest': _ir_digest(node), 'body_digest': body_hash,
                **{key: deepcopy(witness[key]) for key in ('operation', 'target_type', 'target_binding', 'target_declaration')}}
            record['operation_ref'] = 'local-operation:' + digest(record)
            admitted.append(record)
    return admitted


def validate_operations(response, context):
    try:
        return _validate_operations(response, context)
    except (TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ValueError('Invalid local operation proof structure') from error


def annotated_bodies(response, context):
    records = validate_operations(response, context)
    bodies = deepcopy(response['bodies'])
    methods = {b['method']: b for b in bodies}
    for record in records:
        node = methods[record['method']]['body']
        for key in record['ir_path']:
            node = node[key]
        node[_INTERNAL_REF] = record['operation_ref']
    return bodies, records


def materialize_operations(graph, records, context):
    """Bind an admitted IR occurrence separately to each actual CFG clone."""
    from .process_triggers import _canonical_symbol
    nodes = {n.id: n for n in graph.nodes}; symbols = {s['id']: s for s in graph.symbols}
    evidence = {p['id']: p for p in graph.evidence}; by_ref = {r['operation_ref']: r for r in records}
    cfgs = deepcopy(graph.cfgs)
    for cfg in cfgs:
        if cfg.get('representation') != 'SOURCE' or cfg.get('context_id') != context['id']:
            continue
        for block in cfg['blocks']:
            reference = block.pop(_INTERNAL_REF, None)
            if reference is None:
                continue
            record = by_ref.get(reference); method = nodes.get(cfg['method']); symbol = symbols.get(cfg['method'])
            if (record is None or method is None or symbol is None or record['method'] != cfg['method']
                    or context.get('mode') not in {'BUILD_IMPORT', 'SYMBOL_RESOLVED'}
                    or not isinstance(context.get('analyzer_version'), str)
                    or not _canonical_symbol(symbol, method, context) or method.scope != context['scope']
                    or graph.files.get(method.path) != record['sha256'] or block['kind'] != 'basic_block'
                    or block.get('call_site_ids') or block.get('source_file') != method.path
                    or block.get('sha256') != record['sha256'] or block.get('source_range') != record['source_range']):
                _fail('operation does not match its canonical CFG block')
            contains = [e for e in graph.edges if e.target == method.id and e.kind == 'contains'
                        and e.evidence_kind == 'SYMBOL_RESOLVED' and e.context_ids == (context['id'],)
                        and e.source_file == method.path and e.evidence_ids
                        and nodes.get(e.source) is not None and nodes[e.source].kind == 'file'
                        and nodes[e.source].path == method.path and nodes[e.source].scope == context['scope']
                        and all(evidence.get(ref, {}).get('kind') == 'SYMBOL_RESOLVED'
                            and evidence[ref].get('source') == e.source and evidence[ref].get('target') == method.id
                            and evidence[ref].get('relation') == 'contains'
                            and evidence[ref].get('context_ids') == [context['id']]
                            and evidence[ref].get('source_file') == method.path
                            and evidence[ref].get('sha256') == record['sha256'] for ref in e.evidence_ids)]
            if not contains:
                _fail('compiler declaration containment proof unavailable')
            proof = {**deepcopy(record), 'kind': 'SYMBOL_RESOLVED', 'source': method.id, 'target': method.id,
                'relation': 'local_computation', 'context_ids': [context['id']], 'scope': context['scope'],
                'compiler_symbol_id': method.id, 'compiler_backend': 'javac',
                'cfg_block': block['id'], 'cfg_version': cfg['version'],
                'local_operation_version': 1, 'rules_version': VERSION,
                'polarity': 'SUPPORTING', 'runtime_execution': 'NOT_OBSERVED', 'runtime_availability': 'UNKNOWN'}
            identity = 'evidence:local-operation:' + digest(proof)
            evidence[identity] = {'id': identity, **proof}
            block['local_operation_version'] = 1
            block['local_operation_ref'] = reference
            block['local_operation_evidence_ids'] = [identity]
    return replace(graph, cfgs=cfgs, evidence=sorted(evidence.values(), key=lambda p: p['id']))


def _original_proof(proof, context):
    """Undo only the existing workspace wrappers before checking an origin hash."""
    from .workspace import split_id
    result = deepcopy(proof)
    if not proof['id'].startswith('repo:'):
        return result
    repo = context['repo_id']
    if result.pop('repo_id', None) != repo:
        _fail('workspace proof wrapper belongs to another repository')
    def original(value):
        owner, raw = split_id(value)
        if owner != repo:
            _fail('foreign workspace reference')
        return raw
    for key in ('id', 'source', 'target', 'method', 'compiler_symbol_id', 'cfg_block', 'target_binding'):
        if isinstance(result.get(key), str):
            result[key] = original(result[key])
    result['context_id'] = original(result['context_id'])
    result['context_ids'] = [original(value) for value in result['context_ids']]
    prefix = '@' + repo + '/'
    if not result['source_file'].startswith(prefix):
        _fail('foreign workspace source')
    result['source_file'] = result['source_file'][len(prefix):]
    if isinstance(result.get('target_declaration'), dict):
        path = result['target_declaration']['path']
        if not path.startswith(prefix):
            _fail('foreign local declaration source')
        result['target_declaration']['path'] = path[len(prefix):]
    return result


def validated_cfg_operations(graph, context):
    """Read only selected, current, hash-bound operation evidence for T025."""
    from .process_paths import _source_checksum
    from .process_triggers import _canonical_symbol
    nodes = {n.id: n for n in graph.nodes}; symbols = {s['id']: s for s in graph.symbols}
    evidence = {p['id']: p for p in graph.evidence}; admitted = {}
    for cfg in graph.cfgs:
        if cfg.get('context_id') != context['id'] or cfg.get('representation') != 'SOURCE':
            continue
        method = nodes.get(cfg.get('method')); symbol = symbols.get(cfg.get('method'))
        for block in cfg['blocks']:
            if 'local_operation_version' not in block:
                continue
            refs = block.get('local_operation_evidence_ids')
            if (type(block['local_operation_version']) is not int or block['local_operation_version'] != 1
                    or not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], str)
                    or method is None or symbol is None or not _canonical_symbol(symbol, method, context)
                    or context.get('local_operation_rule_version') != VERSION):
                _fail('missing or unsupported selected operation evidence')
            p = evidence.get(refs[0], {}); sha = _source_checksum(graph, context, method.path)
            if (not p or sha is None or symbol.get('sha256') != sha or p.get('sha256') != sha
                    or type(p.get('local_operation_version')) is not int or p['local_operation_version'] != 1
                    or p.get('compiler_backend') != 'javac' or p.get('polarity') != 'SUPPORTING'
                    or not isinstance(p.get('operation'), str) or p['operation'] not in {'LITERAL_EVALUATION', 'LOCAL_LITERAL_ASSIGNMENT'}
                    or not isinstance(p.get('target_type'), str) or p['target_type'] not in _TYPES
                    or not _range(p.get('source_range'))
                    or not all(isinstance(p.get(key), str) and re.fullmatch('[0-9a-f]{64}', p[key]) for key in ('ir_digest', 'body_digest'))
                    or context.get('mode') not in {'BUILD_IMPORT', 'SYMBOL_RESOLVED'}
                    or context.get('freshness') not in {'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND'}
                    or p.get('kind') != 'SYMBOL_RESOLVED' or p.get('source') != method.id or p.get('target') != method.id
                    or p.get('method') != method.id or p.get('compiler_symbol_id') != method.id
                    or p.get('context_id') != context['id'] or p.get('context_ids') != [context['id']]
                    or p.get('scope') != method.scope or method.scope != context['scope']
                    or p.get('source_file') != method.path or block.get('source_file') != method.path
                    or p.get('source_range') != block.get('source_range') or block.get('sha256') != sha
                    or p.get('cfg_block') != block['id'] or p.get('cfg_version') != cfg.get('version')
                    or p.get('relation') != 'local_computation' or p.get('rules_version') != VERSION
                    or p.get('operation_ref') != block.get('local_operation_ref')
                    or p.get('runtime_execution') != 'NOT_OBSERVED' or p.get('runtime_availability') != 'UNKNOWN'
                    or block.get('kind') != 'basic_block' or block.get('call_site_ids')):
                _fail('selected operation source/CFG/proof tuple mismatch')
            original = _original_proof(p, context); identity = original.pop('id')
            if identity != 'evidence:local-operation:' + digest(original):
                _fail('operation proof content hash mismatch')
            base = {key: original[key] for key in _BASE}
            if original['operation_ref'] != 'local-operation:' + digest(base):
                _fail('IR occurrence identity mismatch')
            pointer = original['ir_path']
            if (not isinstance(pointer, list) or not 1 <= len(pointer) <= 150
                    or any(not (isinstance(key, str) and 0 < len(key) <= 64)
                           and not (type(key) is int and key >= 0) for key in pointer)):
                _fail('invalid original IR path')
            declaration = original['target_declaration']
            if original['operation'] == 'LITERAL_EVALUATION':
                if original['target_binding'] is not None or declaration is not None:
                    _fail('literal operation has a target binding')
            else:
                if (not isinstance(declaration, dict)
                        or not {'path', 'sha256', 'range'} <= set(declaration) <= {'path', 'sha256', 'range', 'origin'}
                        or ('origin' in declaration and declaration['origin'] not in {'handwritten', 'generated'})
                        or not _range(declaration['range']) or declaration['path'] != original['source_file']
                        or declaration['sha256'] != sha):
                    _fail('invalid original local declaration')
                declared = declaration['range']
                expected = 'binding:' + original['context_id'] + ':' + original['source_file'] + ':' + sha + ':' + str(declared['start']) + ':' + str(declared['end'])
                if original['target_binding'] != expected:
                    _fail('original local binding identity mismatch')
            admitted[block['id']] = p
    return admitted

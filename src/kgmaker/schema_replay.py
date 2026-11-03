"""Conservative PostgreSQL DDL replay, lifecycle and prefix checkpoints.

This is a declaration model, not a database, SQL executor or deployment proof.
Unknown operations taint the stream even when subsequent known DDL is useful.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path
from urllib.parse import quote

from .analysis_model import AnalysisError, digest, file_hash, read_json, safe_path
from .flyway import migration_plan
from .model import Edge, Node

PARSER_VERSION = 'postgres-ddl-4-creation-identity'
_CHECKPOINTS: dict[str, dict] = {}


def persistence_pair(database_id, stream_id):
    """A structured explicit identity; never recover it by splitting node IDs."""
    if any(not isinstance(v, str) or not v or len(v) > 128 or v != v.strip() or any(ord(c) < 32 for c in v) for v in (database_id, stream_id)):
        return None
    return database_id, stream_id


def persistence_selection(context):
    result = {key: context.get(key) for key in
              ('database_id', 'schema_stream_id', 'persistence_unit', 'persistence_schema', 'flyway_target')}
    for key, value in result.items():
        if value is not None and (not isinstance(value, str) or not value or len(value) > 128
                                  or value != value.strip() or any(ord(c) < 32 for c in value)):
            raise AnalysisError('Invalid persistence selector: ' + key)
    return result


def realm_prefix(config):
    pair = persistence_pair(config.get('database_id'), config.get('stream_id'))
    if pair is None:
        raise AnalysisError('Invalid persistence database/stream identity')
    return ':'.join(quote(v, safe='') for v in pair)


def schema_realm(schema, *, schema_name=None):
    config = schema['config']
    keys = sorted({key for p in config.get('provenance', [])
                   if p.get('kind') == 'EXPLICIT_CONFIGURATION' for key in p.get('keys', [])})
    result = {'database_id': config['database_id'], 'stream_id': config['stream_id'],
            'schema': schema_name, 'schemas': list(config['schemas']), 'target': config['target'],
            'config_fingerprint': digest(config), 'explicit_keys': keys,
            'derivation': 'MIGRATION_DERIVED'}
    result['proof_hash'] = digest(result)
    return result


def schema_node_realm(node):
    """Validate the replay object's typed identity against its structured proof."""
    metadata = node.metadata
    if not isinstance(metadata, dict):
        return None
    realm, name = metadata.get('persistence_realm'), metadata.get('schema_object')
    if not isinstance(realm, dict) or not isinstance(name, list) or not name or any(
            not isinstance(n, str) or not n for n in name):
        return None
    expected_fields = {'database_id', 'stream_id', 'schema', 'schemas', 'target', 'config_fingerprint',
                       'explicit_keys', 'derivation', 'proof_hash'}
    if set(realm) != expected_fields:
        return None
    try:
        valid_hash = realm['proof_hash'] == digest({k: v for k, v in realm.items() if k != 'proof_hash'})
    except (TypeError, ValueError, RecursionError):
        return None
    if not valid_hash or node.name != '.'.join(name) or node.kind not in {'db_table', 'db_column'}:
        return None
    if len(name) != (2 if node.kind == 'db_table' else 3):
        return None
    pair = persistence_pair(realm.get('database_id'), realm.get('stream_id'))
    keys, schemas = realm.get('explicit_keys'), realm.get('schemas')
    if (pair is None or not isinstance(keys, list) or any(not isinstance(k, str) for k in keys)
            or not {'database_id', 'stream_id'} <= set(keys)
            or not isinstance(schemas, list) or any(not isinstance(s, str) or not s for s in schemas)
            or realm.get('schema') != name[0] or name[0] not in schemas
            or not isinstance(realm.get('target'), str) or not realm['target']
            or realm.get('derivation') != 'MIGRATION_DERIVED'
            or not isinstance(realm.get('config_fingerprint'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', realm['config_fingerprint'])
            or not node.kind.startswith('db_')):
        return None
    creation = metadata.get('schema_identity')
    fields = {'schema_version','database_id','stream_id','kind','name','incarnation','origin','proof_hash'}
    if (not isinstance(creation,dict) or set(creation) != fields or type(creation.get('schema_version')) is not int
            or creation['schema_version'] != 1 or persistence_pair(creation.get('database_id'),creation.get('stream_id')) != pair
            or creation.get('kind') != node.kind[3:] or not isinstance(creation.get('name'),list)
            or len(creation['name']) != len(name) or any(not isinstance(n,str) or not n for n in creation['name'])
            or not isinstance(creation.get('origin'),dict)
            or creation.get('proof_hash') != digest({key:value for key,value in creation.items() if key != 'proof_hash'})):
        return None
    origin = creation['origin']
    if (not isinstance(origin.get('path'),str) or not origin['path'] or not isinstance(origin.get('sha256'),str)
            or not re.fullmatch(r'[0-9a-f]{64}',origin['sha256']) or type(origin.get('statement')) is not int
            or origin['statement'] < 1 or type(origin.get('line')) is not int or origin['line'] < 1):
        return None
    expected = 'schema:' + realm_prefix({'database_id': pair[0], 'stream_id': pair[1]}) + ':' + Replay.key(creation['kind'],tuple(creation['name']))
    incarnation = creation['incarnation']
    if incarnation is not None:
        if not isinstance(incarnation,str) or incarnation != digest(origin)[:12]:
            return None
        expected += ':incarnation:' + incarnation
    if node.id != expected:
        return None
    return realm


def statements(text: str) -> list[tuple[list[str], int]]:
    """Tokenize before splitting; comments/literals never become DDL tokens."""
    result, tokens, start, pos, line = [], [], None, 0, 1
    while pos < len(text):
        rest = text[pos:]
        if rest[0].isspace():
            line += rest[0] == '\n'
            pos += 1
            continue
        if rest.startswith('--'):
            end = text.find('\n', pos)
            pos = len(text) if end < 0 else end
            continue
        if rest.startswith('/*'):
            end, depth = pos + 2, 1
            while end < len(text) and depth:
                if text.startswith('/*', end):
                    depth += 1; end += 2
                elif text.startswith('*/', end):
                    depth -= 1; end += 2
                else:
                    end += 1
            if depth:
                raise AnalysisError('Unclosed SQL comment')
            line += text[pos:end].count('\n'); pos = end
            continue
        start = line if start is None else start
        if rest[0] == ';':
            if tokens:
                result.append((tokens, start))
            tokens, start, pos = [], None, pos + 1
            continue
        dollar = re.match(r'\$(?:[A-Za-z_][\w]*)?\$', rest)
        if dollar:
            delimiter = dollar[0]
            end = text.find(delimiter, pos + len(delimiter))
            if end < 0:
                raise AnalysisError('Unclosed SQL dollar-quoted body')
            end += len(delimiter)
        elif rest[0] in "\"'":
            quote, end = rest[0], pos + 1
            while end < len(text):
                if text[end] == quote:
                    if end + 1 < len(text) and text[end + 1] == quote:
                        end += 2; continue
                    end += 1; break
                # E-string backslash escaping is accepted conservatively.
                if text[end] == '\\' and quote == "'":
                    end += 2
                else:
                    end += 1
            else:
                raise AnalysisError('Unclosed SQL quoted value')
        else:
            match = re.match(r'[A-Za-z_][\w$]*|\d+(?:\.\d+)?|::|<=|>=|<>|!=|.', rest)
            end = pos + len(match[0])
        token = text[pos:end]
        tokens.append(token)
        line += token.count('\n'); pos = end
    if tokens:
        result.append((tokens, start))
    return result


def identifier(token: str) -> str:
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1].replace('""', '"')
    if not re.fullmatch(r'[A-Za-z_][\w$]*', token):
        raise AnalysisError('Expected SQL identifier, found ' + token)
    return token.lower()


def groups(tokens: list[str]) -> list[list[str]]:
    result, current, depth = [], [], 0
    for token in tokens:
        if token == ',' and depth == 0:
            result.append(current); current = []; continue
        current.append(token)
        depth += (token == '(') - (token == ')')
    if current:
        result.append(current)
    return result


class Replay:
    def __init__(self, config: dict):
        self.config = config
        self.search_path = [config['default_schema']]
        self.objects, self.history, self.operations, self.diagnostics = {}, [], [], []
        self.evidence = None

    def name(self, tokens, offset=0):
        first = identifier(tokens[offset]); offset += 1
        if offset < len(tokens) and tokens[offset] == '.':
            return (first, identifier(tokens[offset + 1])), offset + 2
        if len(self.search_path) != 1:
            raise AnalysisError('Ambiguous unqualified name under search_path')
        return (self.search_path[0], first), offset

    @staticmethod
    def key(kind, name):
        return kind + ':' + '.'.join(quote(component, safe='').replace('.', '%2E') for component in name)

    def create(self, kind, name, **attributes):
        key = self.key(kind, name)
        if key in self.objects:
            raise AnalysisError('Object already exists: ' + key)
        identity = 'schema:' + realm_prefix(self.config) + ':' + key
        incarnation = None
        if any(old['id'] == identity for old in self.history):
            incarnation = digest(self.evidence)[:12]
            identity += ':incarnation:' + incarnation
        creation = {'schema_version':1,'database_id':self.config['database_id'],
                    'stream_id':self.config['stream_id'],'kind':kind,'name':list(name),
                    'incarnation':incarnation,'origin':copy.deepcopy(self.evidence)}
        creation['proof_hash'] = digest(creation)
        item = {'id': identity, 'kind': kind, 'name': list(name), 'lifecycle': 'ACTIVE',
                'origin': copy.deepcopy(self.evidence), 'last_change': copy.deepcopy(self.evidence),
                'previous_names': [], 'creation_identity':creation, **attributes}
        self.objects[key] = item
        return item

    def get(self, kind, name):
        key = self.key(kind, name)
        if key not in self.objects:
            raise AnalysisError('Unknown object: ' + key)
        return self.objects[key]

    def change(self, item):
        self.history.append(copy.deepcopy(item))
        item['last_change'] = copy.deepcopy(self.evidence)

    def drop(self, kind, name, optional=False):
        key = self.key(kind, name)
        if key not in self.objects:
            if optional:
                return
            raise AnalysisError('DROP references unknown object: ' + key)
        if kind in {'table','column'}:
            for constraint in self.objects.values():
                if constraint.get('constraint_type') != 'FOREIGN':
                    continue
                referenced = constraint.get('references')
                if ((kind == 'table' and referenced == list(name) and constraint.get('table') != list(name))
                        or (kind == 'column' and referenced == list(name[:-1])
                            and name[-1] in (constraint.get('referenced_columns') or []))):
                    raise AnalysisError('DROP references a foreign-key target; supported cascade is unavailable')
        item = self.objects.pop(key)
        item['lifecycle'] = 'DROPPED'; item['last_change'] = copy.deepcopy(self.evidence)
        self.history.append(item)

    def rename(self, kind, name, target):
        old, new = self.key(kind, name), self.key(kind, target)
        if new in self.objects:
            raise AnalysisError('Rename target already exists: ' + new)
        item = self.get(kind, name); self.change(item)
        item['previous_names'].append(item['name']); item['name'] = list(target)
        self.objects.pop(old); self.objects[new] = item
        for constraint in list(self.objects.values()):
            if constraint.get('constraint_type') != 'FOREIGN':
                continue
            if kind == 'table' and constraint.get('references') == list(name):
                self.change(constraint); constraint['references'] = list(target)
            if kind == 'column' and constraint.get('references') == list(name[:-1]) and name[-1] in (constraint.get('referenced_columns') or []):
                self.change(constraint)
                constraint['referenced_columns'] = [target[-1] if column == name[-1] else column for column in constraint['referenced_columns']]
        if kind == 'table':
            children = [x for x in self.objects.values() if x.get('table') == list(name)]
            for child in children:
                if child['kind'] in {'column', 'constraint'}:
                    child_name = tuple(child['name']); child_target = tuple(target) + (child_name[-1],)
                    self.rename(child['kind'], child_name, child_target)
                else:
                    self.change(child)
                child['table'] = list(target)
        if kind == 'schema':
            children = [x for x in self.objects.values() if x['name'][0] == name[0]]
            for child in children:
                if child['name'][0] != name[0]:
                    continue  # a renamed table already moved its column/constraint children
                child_name = tuple(child['name']); child_target = target + child_name[1:]
                self.rename(child['kind'], child_name, child_target)
                if child.get('table'):
                    child['table'] = [target[0]] + child['table'][1:]

    def constraint(self, table, tokens, fallback):
        upper = [x.upper() for x in tokens]
        if upper[0] == 'CONSTRAINT':
            name, tokens, upper = identifier(tokens[1]), tokens[2:], upper[2:]
        else:
            name = fallback
        if not upper or upper[0] not in {'PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK'}:
            raise AnalysisError('Unsupported constraint')
        columns = []
        if '(' in tokens and upper[0] != 'CHECK':
            begin = tokens.index('('); end = tokens.index(')', begin)
            columns = [identifier(t) for t in tokens[begin + 1:end] if t != ',']
            for column in columns:
                self.get('column', table + (column,))
        referenced = None
        referenced_columns = None
        if 'REFERENCES' in upper:
            index = upper.index('REFERENCES') + 1
            target, index = self.name(tokens, index)
            self.get('table', target)
            referenced = list(target)
            if index < len(tokens) and tokens[index] == '(':
                try:
                    end = tokens.index(')', index + 1)
                except ValueError as exc:
                    raise AnalysisError('Unclosed referenced column list') from exc
                parts = groups(tokens[index + 1:end])
                if any(len(part) != 1 for part in parts):
                    raise AnalysisError('Only explicit referenced column identifiers supported')
                referenced_columns = [identifier(part[0]) for part in parts]
                if not referenced_columns or len(set(referenced_columns)) != len(referenced_columns) or len(referenced_columns) != len(columns):
                    raise AnalysisError('Foreign key column arity or duplicate mismatch')
                for column in referenced_columns:
                    self.get('column', target + (column,))
        self.create('constraint', table + (name,), table=list(table),
                    constraint_type=upper[0], columns=columns, references=referenced, referenced_columns=referenced_columns, expression=' '.join(tokens))
        if upper[0] == 'PRIMARY':
            for column in columns:
                self.get('column', table + (column,))['nullable'] = False

    def column(self, table, tokens):
        name = identifier(tokens[0]); upper = [x.upper() for x in tokens]
        stop = next((i for i, v in enumerate(upper[1:], 1) if v in {'NOT', 'NULL', 'DEFAULT', 'PRIMARY', 'UNIQUE', 'REFERENCES', 'CHECK', 'CONSTRAINT'}), len(tokens))
        if stop <= 1:
            raise AnalysisError('Missing column type')
        type_text = ' '.join(tokens[1:stop])
        if any(x.upper() in {'GENERATED', 'IDENTITY'} for x in tokens[1:stop]):
            raise AnalysisError('Generated/identity columns are not supported')
        default = None
        if 'DEFAULT' in upper:
            begin = upper.index('DEFAULT') + 1
            end = next((i for i in range(begin, len(tokens)) if upper[i] in {'NOT', 'NULL', 'PRIMARY', 'UNIQUE', 'REFERENCES', 'CHECK', 'CONSTRAINT'}), len(tokens))
            default = ' '.join(tokens[begin:end])
        nullable, level = True, 0
        for index, token in enumerate(tokens):
            if token == '(':
                level += 1
            elif token == ')':
                level -= 1
            elif level == 0 and (upper[index:index + 2] == ['NOT','NULL'] or upper[index] == 'PRIMARY'):
                nullable = False
        item = self.create('column', table + (name,), table=list(table), data_type=type_text,
                           nullable=nullable, default=default)
        for tag in ('PRIMARY', 'UNIQUE', 'REFERENCES', 'CHECK'):
            if tag in upper:
                if tag == 'REFERENCES':
                    self.constraint(table, ['FOREIGN', 'KEY', '(', tokens[0], ')'] + tokens[upper.index(tag):], name + '_fkey')
                elif tag == 'CHECK':
                    self.constraint(table, tokens[upper.index(tag):], name + '_check')
                else:
                    self.constraint(table, ([tag, 'KEY'] if tag == 'PRIMARY' else [tag]) + ['(', tokens[0], ')'], name + '_' + tag.lower())
        return item

    def apply(self, tokens):
        upper = [t.upper() for t in tokens]
        if upper[:2] == ['SET', 'SEARCH_PATH']:
            start = 3 if upper[2] in {'TO', '='} else 2
            self.search_path = [identifier(t) for t in tokens[start:] if t != ',']
            if not self.search_path:
                raise AnalysisError('Empty search_path')
            return
        if upper[0] in {'INSERT', 'UPDATE', 'DELETE', 'MERGE'}:
            return  # operation remains inventoried; never a populated-data proof
        if upper[0] in {'BEGIN', 'COMMIT'} and len(tokens) == 1:
            return
        if upper[0] == 'CREATE':
            offset = 1
            replace = upper[1:3] == ['OR', 'REPLACE']
            if replace:
                offset = 3
            unique = upper[offset] == 'UNIQUE'
            if unique:
                offset += 1
            kind = upper[offset].lower(); offset += 1
            if kind not in {'schema', 'table', 'index', 'view', 'sequence'}:
                raise AnalysisError('Unsupported CREATE ' + kind)
            optional = upper[offset:offset + 3] == ['IF', 'NOT', 'EXISTS']
            if optional:
                offset += 3
            if kind == 'schema':
                name, offset = (identifier(tokens[offset]),), offset + 1
            else:
                name, offset = self.name(tokens, offset)
            if self.key(kind, name) in self.objects:
                if optional:
                    return
                if replace and kind == 'view':
                    self.drop(kind, name)
                else:
                    raise AnalysisError('Duplicate CREATE: ' + '.'.join(name))
            if kind == 'table':
                if tokens[offset:offset + 1] != ['('] or tokens[-1] != ')':
                    raise AnalysisError('Only explicit CREATE TABLE column definitions supported')
                self.create(kind, name)
                definitions = groups(tokens[offset + 1:-1])
                deferred = []
                for definition in definitions:
                    if definition[0].upper() in {'CONSTRAINT', 'PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK'}:
                        deferred.append(definition)
                    else:
                        self.column(name, definition)
                for i, definition in enumerate(deferred):
                    self.constraint(name, definition, 'constraint_' + str(i))
            elif kind == 'index':
                if upper[offset] != 'ON':
                    raise AnalysisError('Unsupported index target')
                table, offset = self.name(tokens, offset + 1); self.get('table', table)
                self.create(kind, name, table=list(table), unique=unique, expression=' '.join(tokens[offset:]))
            elif kind == 'view':
                if upper[offset:offset + 2] != ['AS', 'SELECT'] or 'FROM' not in upper:
                    raise AnalysisError('Only simple SELECT views supported')
                begin = offset + 2; end = upper.index('FROM', begin)
                table, after = self.name(tokens, end + 1); self.get('table', table)
                if after != len(tokens):
                    raise AnalysisError('Complex view query is unresolved')
                columns = []
                for projection in groups(tokens[begin:end]):
                    if len(projection) == 1:
                        source, alias = identifier(projection[0]), identifier(projection[0])
                    elif len(projection) == 3 and projection[1].upper() == 'AS':
                        source, alias = identifier(projection[0]), identifier(projection[2])
                    else:
                        raise AnalysisError('Unsupported view projection')
                    field = self.get('column', table + (source,))
                    columns.append({'name': alias, 'source_id': field['id'], 'data_type': field['data_type']})
                self.create(kind, name, columns=columns, query=' '.join(tokens[begin:]))
            else:
                if offset != len(tokens):
                    raise AnalysisError('Unsupported ' + kind + ' options')
                self.create(kind, name)
            return
        if upper[0] == 'DROP':
            kind, offset = upper[1].lower(), 2
            if kind not in {'schema', 'table', 'index', 'view', 'sequence'}:
                raise AnalysisError('Unsupported DROP ' + kind)
            optional = upper[offset:offset + 2] == ['IF', 'EXISTS']
            if optional:
                offset += 2
            name, offset = ((identifier(tokens[offset]),), offset + 1) if kind == 'schema' else self.name(tokens, offset)
            if offset < len(tokens) and upper[offset] not in {'CASCADE', 'RESTRICT'}:
                raise AnalysisError('Unsupported multi-object DROP')
            children = [x for x in self.objects.values() if x.get('table') == list(name) or kind == 'schema' and x['name'][0] == name[0]]
            dependent_views = [x for x in self.objects.values() if x['kind'] == 'view' and any(
                f['source_id'] in {c['id'] for c in children} for f in x.get('columns', []))]
            if dependent_views:
                if 'CASCADE' not in upper:
                    raise AnalysisError('DROP has dependent views and requires CASCADE')
                for view in dependent_views:
                    self.drop('view', tuple(view['name']))
            for item in children:
                self.drop(item['kind'], tuple(item['name']))
            self.drop(kind, name, optional); return
        if upper[0] == 'ALTER':
            kind, offset = upper[1].lower(), 2
            name, offset = ((identifier(tokens[offset]),), offset + 1) if kind == 'schema' else self.name(tokens, offset)
            self.get(kind, name)
            if upper[offset:offset + 2] == ['RENAME', 'TO'] and len(tokens) == offset + 3:
                target = name[:-1] + (identifier(tokens[offset + 2]),)
                self.rename(kind, name, target); return
            if kind != 'table':
                raise AnalysisError('Unsupported ALTER ' + kind)
            for action in groups(tokens[offset:]):
                u = [t.upper() for t in action]
                if u[0] == 'ADD':
                    body = action[2:] if u[1] == 'COLUMN' else action[1:]
                    if body[0].upper() in {'CONSTRAINT', 'PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK'}:
                        self.constraint(name, body, 'constraint_' + str(len(self.operations)))
                    else:
                        optional = [t.upper() for t in body[:3]] == ['IF', 'NOT', 'EXISTS']
                        if optional:
                            body = body[3:]
                        if not optional or self.key('column', name + (identifier(body[0]),)) not in self.objects:
                            self.column(name, body)
                elif u[0] == 'DROP':
                    kind2, i = ('constraint', 2) if u[1] == 'CONSTRAINT' else ('column', 2 if u[1] == 'COLUMN' else 1)
                    optional = u[i:i + 2] == ['IF', 'EXISTS']
                    if optional:
                        i += 2
                    target = name + (identifier(action[i]),)
                    if kind2 == 'column':
                        column = self.objects.get(self.key(kind2, target))
                        if column:
                            dependencies = [x for x in self.objects.values() if x['kind'] == 'constraint' and
                                            x.get('table') == list(name) and target[-1] in x.get('columns', [])]
                            views = [x for x in self.objects.values() if x['kind'] == 'view' and any(f['source_id'] == column['id'] for f in x.get('columns', []))]
                            if views and 'CASCADE' not in u:
                                raise AnalysisError('DROP COLUMN has dependent view and needs CASCADE')
                            for dependent in dependencies + views:
                                self.drop(dependent['kind'], tuple(dependent['name']))
                    self.drop(kind2, target, optional)
                elif u[:2] == ['RENAME', 'COLUMN'] and u[3] == 'TO':
                    self.rename('column', name + (identifier(action[2]),), name + (identifier(action[4]),))
                    for constraint in self.objects.values():
                        if constraint['kind'] == 'constraint' and constraint.get('table') == list(name):
                            updated = [identifier(action[4]) if c == identifier(action[2]) else c for c in constraint.get('columns', [])]
                            if updated != constraint.get('columns',[]):
                                self.change(constraint); constraint['columns'] = updated
                elif u[0] == 'ALTER':
                    i = 2 if u[1] == 'COLUMN' else 1
                    column = self.get('column', name + (identifier(action[i]),)); self.change(column)
                    tail, raw = u[i + 1:], action[i + 1:]
                    if tail[:1] == ['TYPE'] and 'USING' not in tail:
                        column['data_type'] = ' '.join(raw[1:])
                    elif tail[:3] == ['SET', 'NOT', 'NULL']:
                        column['nullable'] = False
                    elif tail[:3] == ['DROP', 'NOT', 'NULL']:
                        column['nullable'] = True
                    elif tail[:2] == ['SET', 'DEFAULT']:
                        column['default'] = ' '.join(raw[2:])
                    elif tail[:2] == ['DROP', 'DEFAULT']:
                        column['default'] = None
                    else:
                        raise AnalysisError('Unsupported ALTER COLUMN')
                else:
                    raise AnalysisError('Unsupported ALTER TABLE action')
            return
        raise AnalysisError('Unresolved SQL effects: ' + upper[0])


def reconstruct(root: Path, config: dict | None = None, *, use_cache: bool = True) -> dict:
    plan = migration_plan(root, config)
    replay = Replay(plan['config'])
    replay.diagnostics.extend(plan['diagnostics'])
    if not plan['valid']:
        return {**plan, 'status': 'INVALID', 'objects': {}, 'history': [], 'operations': [], 'checkpoints': [],
                'schema_parser_version': PARSER_VERSION, 'data_availability': 'UNKNOWN', 'deployment_verified': False}
    snapshot = plan['config'].get('initial_snapshot')
    if plan['config']['mode'] == 'snapshot' and snapshot:
        source = safe_path(root, snapshot)
        supplied = read_json(source)
        if not isinstance(supplied, dict) or supplied.get('schema_version') != 1 or not isinstance(supplied.get('objects'), dict):
            raise AnalysisError('Invalid initial schema snapshot')
        replay.objects = copy.deepcopy(supplied['objects'])
        plan['snapshot_provenance'] = {'path': snapshot, 'sha256': file_hash(source)}
    config_key = digest({'root': str(root.resolve()), 'config': plan['config'], 'parser': PARSER_VERSION,
                         'snapshot': plan.get('snapshot_provenance')})
    prefix, checkpoints = [], []
    for migration in plan['migrations']:
        prefix.append(migration)
        key = digest({'config': config_key, 'prefix': prefix})
        if use_cache and key in _CHECKPOINTS:
            saved = copy.deepcopy(_CHECKPOINTS[key])
            replay.objects, replay.history, replay.operations = saved['objects'], saved['history'], saved['operations']
            replay.search_path = saved['search_path']
            replay.diagnostics = sorted(set(plan['diagnostics'] + saved['replay_diagnostics']))
            checkpoints.append({'fingerprint': key, 'migration': migration['path'], 'reused': True})
            continue
        path = safe_path(root, migration['path'])
        text = path.read_text(encoding='utf-8')
        unknown = re.findall(r'\$\{([^}]+)\}', text)
        for placeholder in unknown:
            if placeholder not in plan['config']['placeholders']:
                replay.diagnostics.append('Unresolved placeholder ' + placeholder + ' in ' + migration['path'])
            else:
                text = text.replace('${' + placeholder + '}', plan['config']['placeholders'][placeholder])
        try:
            parsed = statements(text)
        except AnalysisError as exc:
            replay.diagnostics.append(str(exc) + ': ' + migration['path']); parsed = []
        for ordinal, (tokens, line) in enumerate(parsed):
            replay.evidence = {'path': migration['path'], 'sha256': migration['sha256'], 'line': line,
                               'statement': ordinal + 1, 'version': migration['version']}
            before = copy.deepcopy(replay.objects)
            history_before = copy.deepcopy(replay.history)
            error = None
            try:
                replay.apply(tokens)
            except (AnalysisError, IndexError, ValueError) as exc:
                replay.objects, replay.history = before, history_before
                error = str(exc)
                replay.diagnostics.append(migration['path'] + ':' + str(line) + ': ' + error)
            changed = [obj['id'] for name, obj in replay.objects.items() if before.get(name) != obj]
            changed += [obj['id'] for name, obj in before.items() if name not in replay.objects]
            replay.operations.append({'id': 'migration-operation:' + realm_prefix(plan['config']) + ':' + migration['path'] + ':' + str(ordinal + 1),
                                      'kind': tokens[0].upper(), 'evidence': copy.deepcopy(replay.evidence),
                                      'targets': sorted(set(changed)), 'unresolved': error,
                                      'data_effect_only': tokens[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'MERGE'}})
        _CHECKPOINTS[key] = copy.deepcopy({'objects': replay.objects, 'history': replay.history,
                                         'operations': replay.operations, 'search_path': replay.search_path,
                                         'replay_diagnostics': [d for d in replay.diagnostics if d not in plan['diagnostics']]})
        checkpoints.append({'fingerprint': key, 'migration': migration['path'], 'reused': False})
    return {**plan, 'status': 'PARTIAL' if replay.diagnostics else 'COMPLETE',
            'objects': dict(sorted(replay.objects.items())), 'history': replay.history,
            'operations': replay.operations, 'diagnostics': sorted(set(replay.diagnostics)),
            'checkpoints': checkpoints, 'schema_parser_version': PARSER_VERSION,
            'data_availability': 'UNASSESSED', 'deployment_verified': False}


def schema_diff(root: Path, config: dict, start: str, end: str) -> dict:
    left, right = reconstruct(root, {**config, 'target': start}), reconstruct(root, {**config, 'target': end})
    keys = set(left['objects']) | set(right['objects'])
    return {'from': start, 'to': end, 'exact': left['status'] == right['status'] == 'COMPLETE',
            'provenance': 'MIGRATION_DERIVED', 'diagnostics': sorted(set(left['diagnostics'] + right['diagnostics'])),
            'changes': [{'object': key, 'before': left['objects'].get(key), 'after': right['objects'].get(key)}
                        for key in sorted(keys) if left['objects'].get(key) != right['objects'].get(key)]}


def graph_entities(schema: dict) -> tuple[list[Node], list[Edge]]:
    nodes, edges = [], []
    if schema['inventory']:
        first = schema['inventory'][0]
        database_id = 'database:' + realm_prefix(schema['config'])
        nodes.append(Node(database_id, 'database', schema['config']['database_id'], first['path'], 1,
                          summary='Independent stream; no automatic stream merge or deployment confirmation',
                          metadata={'persistence_realm': schema_realm(schema)}))
    for item in schema['objects'].values():
        evidence = item['last_change']; path = evidence['path']
        kind = 'db_' + item['kind']
        nodes.append(Node(item['id'], kind, '.'.join(item['name']), path, evidence['line'],
                          item.get('data_type'), 'MIGRATION_DERIVED; ' + schema['status'],
                          metadata={'persistence_realm': schema_realm(schema, schema_name=item['name'][0]),
                                    'schema_object': list(item['name']),
                                    'schema_identity': copy.deepcopy(item.get('creation_identity')),
                                    'schema_snapshot_fingerprint': schema_snapshot_fingerprint(schema)}))
        if item.get('table'):
            table = schema['objects'].get(Replay.key('table', tuple(item['table'])))
            if table:
                edges.append(Edge(table['id'], item['id'], 'contains_' + item['kind'], source_file=path, source_line=evidence['line']))
        if item['kind'] == 'constraint' and item.get('references'):
            table = schema['objects'].get(Replay.key('table', tuple(item['references'])))
            if table:
                edges.append(Edge(item['id'], table['id'], 'foreign_key_to', source_file=path, source_line=evidence['line']))
        if item['kind'] == 'view':
            for field in item['columns']:
                identity = item['id'] + ':field:' + field['name']
                nodes.append(Node(identity, 'db_view_field', field['name'], path, evidence['line'], field['data_type'],
                                  metadata={'persistence_realm': schema_realm(schema, schema_name=item['name'][0])}))
                edges.append(Edge(identity, field['source_id'], 'derived_from', 'Explicit view projection',
                                  source_file=path, source_line=evidence['line']))
    for op in schema['operations']:
        ev = op['evidence']; migration_id = 'migration:' + realm_prefix(schema['config']) + ':' + ev['path']
        if not any(n.id == migration_id for n in nodes):
            nodes.append(Node(migration_id, 'migration', ev['path'], ev['path'], 1, metadata={'persistence_realm': schema_realm(schema)}))
        nodes.append(Node(op['id'], 'migration_operation', op['kind'], ev['path'], ev['line'], summary=op['unresolved'], metadata={'persistence_realm': schema_realm(schema)}))
        edges.append(Edge(migration_id, op['id'], 'migration_changes', source_file=ev['path'], source_line=ev['line']))
        for target in op['targets']:
            if any(n.id == target for n in nodes):
                edges.append(Edge(op['id'], target, 'operation_targets', source_file=ev['path'], source_line=ev['line']))
    return nodes, edges


def schema_mappings(root: Path, schema: dict, graph) -> tuple[list[Edge], list[dict]]:
    """Explicit @Table/@Column binding of supported declared fields, with mismatches."""
    edges, diagnostics = [], []
    objects = schema['objects']
    for node in graph.nodes:
        if node.kind != 'data_field' or Path(node.path).suffix not in {'.kt', '.java'}:
            continue
        text = safe_path(root, node.path).read_text(encoding='utf-8')
        if not isinstance(node.name, str) or '.' not in node.name:
            continue
        owner, field = node.name.rsplit('.', 1)
        declaration = re.search(r'\b(?:class|record)\s+' + re.escape(owner) + r'\b', text)
        if not declaration or not re.search(r'@Table\s*\(', text[max(0, declaration.start() - 500):declaration.start()]):
            continue
        if not re.search(r'@Column\s*\([^)]*\)\s*(?:val|var)\s+' + re.escape(field) + r'\b', text[declaration.end():]):
            continue
        diagnostics.append({'code': 'PERSISTENCE_REALM_UNPROVEN', 'path': node.path, 'line': node.line,
                            'reason': 'Source-only field has no compiler-owned explicit persistence realm; no physical schema binding.'})
    return edges, diagnostics


COMPATIBILITY_VERSION = 'orm-schema-2-creation-identity'


def schema_snapshot_fingerprint(schema):
    """Bind the explicit replay projection, not a claim of deployment/freshness."""
    return digest({key: schema.get(key) for key in
                   ('config', 'objects', 'inventory', 'status', 'schema_parser_version', 'diagnostics', 'snapshot_provenance')})


def _verified_mapping_annotations(symbol, canonical):
    """Bind only consumed typed members to captured Node annotation authority."""
    members = {
        'Column': ('name','nullable','precision','scale','unique','table','columnDefinition'),
        'JoinColumn': ('name','referencedColumnName','nullable','unique','table'),
        'ManyToOne': ('targetEntity','optional'),
        'OneToOne': ('targetEntity','mappedBy','optional'),
    }
    accepted_sites = {'','FIELD','BACKING_FIELD'} if symbol.get('kind') == 'field' else {'','PROPERTY_GETTER','GETTER','GET'}
    def selected(annotations):
        result = {}
        for annotation in annotations if isinstance(annotations,list) else []:
            if not isinstance(annotation,dict) or not isinstance(annotation.get('name'),str):
                continue
            package, _, name = annotation['name'].rpartition('.')
            site = str(annotation.get('use_site_target') or '').upper()
            if package not in {'jakarta.persistence','javax.persistence'} or site not in accepted_sites:
                continue
            key = (annotation['name'],site)
            if key in result:
                return None
            result[key] = annotation
        return result
    actual = selected(symbol.get('annotations'))
    captured = selected((canonical.metadata or {}).get('annotations'))
    if actual is None or captured is None or set(actual) != set(captured):
        return None
    for key, annotation in actual.items():
        original = captured[key]
        names = members.get(key[0].rsplit('.',1)[-1],())
        if names:
            if (annotation.get('values_resolved') is False or original.get('values_resolved') is False
                    or not isinstance(annotation.get('values'),dict) or not isinstance(original.get('values'),dict)):
                return None
            for name in names:
                value, expected = annotation['values'].get(name), original['values'].get(name)
                if type(value) is not type(expected) or value != expected or type(value) not in {str,int,bool,type(None)}:
                    return None
    return list(actual.values())


def schema_compatibility(schema, graph, *, context_id=None):
    """Pure compatibility of a supplied content-bound replay and compiler graph.

    The provider supplies the current snapshots. This projection does not read a
    checkout, run a worker/migration or authenticate database state. Legacy or
    unsupported contracts remain UNKNOWN, never positive data availability.
    """
    import json
    from dataclasses import replace
    from .model import KnowledgeGraph
    from .framework import JPA_RULE_VERSION, _sql_identifier
    from .process_triggers import _canonical_symbol
    from .workspace import split_id, qualified
    json.dumps(schema, allow_nan=False)
    graph = KnowledgeGraph.from_dict(graph.to_dict())
    if not isinstance(schema, dict) or not isinstance(schema.get('objects'), dict):
        raise AnalysisError('Invalid replay compatibility snapshot')
    config = schema.get('config', {})
    if (not isinstance(config, dict) or schema.get('status') not in {'COMPLETE','PARTIAL','INVALID'}
            or not isinstance(schema.get('inventory'), list)
            or any(not isinstance(key,str) or not isinstance(value,dict) for key,value in schema['objects'].items())):
        raise AnalysisError('Malformed replay compatibility snapshot')
    if persistence_pair(config.get('database_id'), config.get('stream_id')) is None:
        raise AnalysisError('Invalid replay compatibility realm')
    snapshot = schema_snapshot_fingerprint(schema)
    # A later rename's last_change does not replace older type/key source inputs.
    def replay_sources_current(repo=None):
        supplied = list(schema.get('inventory',[]))
        if schema.get('snapshot_provenance'):
            supplied.append(schema['snapshot_provenance'])
        for entry in supplied:
            path, checksum = entry.get('path'),entry.get('sha256')
            if not isinstance(path,str) or not isinstance(checksum,str) or not re.fullmatch(r'[0-9a-f]{64}',checksum):
                return False
            path = '@' + repo + '/' + path if repo else path
            if path not in graph.files or graph.files[path] != checksum:
                return False
        return True
    nodes = {n.id: n for n in graph.nodes}
    symbols = {s['id']: s for s in graph.symbols}
    proofs = {p['id']: p for p in graph.evidence}
    contexts = {c['id']: c for c in graph.contexts}
    edge_index = {}
    class_index = {}
    for edge in graph.edges:
        edge_index.setdefault((edge.source,edge.kind),[]).append(edge)
    for symbol in graph.symbols:
        if symbol.get('kind') == 'class':
            class_index.setdefault((symbol.get('context_id'),symbol.get('owner')),[]).append(symbol['id'])
    dimensions = ('presence', 'type', 'nullability', 'precision', 'scale', 'primary_key', 'unique', 'foreign_key')

    def result(status, reason):
        return {'status': status, 'reason': reason}

    def local_id(identity):
        return split_id(identity)[1] if identity.startswith('repo:') else identity

    def local_path(path):
        return path.split('/', 1)[1] if path.startswith('@') and '/' in path else path

    def proof_id(identity, proof):
        # Workspace preserves original compiler_symbol_id in the proof record.
        if identity.startswith('repo:'):
            repo, _ = split_id(identity)
            return qualified(repo, proof)
        return proof

    def current_source(path, context, checksum=None):
        captured = context.get('source_files', {}).get(path)
        return (isinstance(captured, str) and re.fullmatch(r'[0-9a-f]{64}', captured)
                and graph.files.get(path) == captured and (checksum is None or checksum == captured))

    def proven(edge, context, physical=False):
        if edge.evidence_kind != 'FRAMEWORK_DERIVED' or list(edge.context_ids) != [context['id']] or not edge.evidence_ids:
            return False
        for ref in edge.evidence_ids:
            p = proofs.get(ref, {})
            record = copy.deepcopy(p); record.pop('id', None)
            if ref.startswith('repo:'):
                repo, _ = split_id(ref)
                if record.pop('repo_id', None) != repo:
                    return False
                for key in ('source','target'):
                    if not isinstance(record.get(key), str) or split_id(record[key])[0] != repo:
                        return False
                    record[key] = split_id(record[key])[1]
                if any(split_id(cid)[0] != repo for cid in record.get('context_ids', [])):
                    return False
                record['context_ids'] = [split_id(cid)[1] for cid in record.get('context_ids', [])]
                if not str(record.get('source_file','')).startswith('@' + repo + '/'):
                    return False
                record['source_file'] = local_path(record['source_file'])
            if local_id(ref) != 'evidence:' + digest(record):
                return False
            if (p.get('kind') != 'FRAMEWORK_DERIVED' or p.get('source') != edge.source
                    or p.get('target') != edge.target or p.get('relation') != edge.kind
                    or p.get('context_ids') != [context['id']]
                    or not isinstance(p.get('framework_rules'),dict) or p['framework_rules'].get('jpa') != JPA_RULE_VERSION
                    or p.get('source_file') != edge.source_file or p.get('source_line') != edge.source_line
                    or not current_source(edge.source_file, context, p.get('sha256'))):
                return False
            if physical:
                target = nodes[edge.target]
                realm = (target.metadata or {}).get('persistence_realm')
                if (p.get('persistence_realm') != realm or p.get('persistence_selection') != persistence_selection(context)):
                    return False
        return True

    def physical_object(node, kind):
        metadata = node.metadata or {}
        original = replace(node, id=local_id(node.id))
        realm = schema_node_realm(original)
        names = metadata.get('schema_object')
        if (node.kind != 'db_' + kind or realm is None or metadata.get('schema_snapshot_fingerprint') != snapshot
                or realm != schema_realm(schema, schema_name=names[0])):
            return None
        obj = schema['objects'].get(Replay.key(kind, tuple(names)))
        if (obj is None or obj.get('id') != local_id(node.id) or obj.get('lifecycle') != 'ACTIVE'
                or metadata.get('schema_identity') != obj.get('creation_identity')):
            return None
        if kind == 'column' and node.signature != obj.get('data_type'):
            return None
        ev = obj.get('last_change', {})
        if (not isinstance(ev.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',ev['sha256'])
                or local_path(node.path) != ev.get('path') or node.path not in graph.files
                or graph.files[node.path] != ev['sha256']):
            return None
        return obj

    def edges_from(identity, kind, context):
        return [e for e in edge_index.get((identity,kind),[]) if proven(e, context)]

    def mapping_namespace(owner,context,scope):
        namespaces = []
        relevant = {'Entity','MappedSuperclass','Table','Access','Inheritance','IdClass',
                    'AttributeOverride','AttributeOverrides','SecondaryTable','SecondaryTables'}
        for identity in class_index.get((context['id'],owner),[]):
            node, symbol = nodes.get(identity),symbols[identity]
            if (node is None or node.scope != scope or not _canonical_symbol(symbol,node,context)
                    or not isinstance(symbol.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',symbol['sha256'])
                    or not current_source(node.path,context,symbol['sha256'])):
                continue
            annotations = symbol.get('annotations',[])
            kinds = {a['name'].rsplit('.',1)[0] for a in annotations if isinstance(a,dict)
                     and a.get('name') in {'jakarta.persistence.Entity','javax.persistence.Entity',
                                          'jakarta.persistence.MappedSuperclass','javax.persistence.MappedSuperclass'}}
            if len(kinds) != 1:
                continue
            namespace = next(iter(kinds))
            if any(a.get('name','').rsplit('.',1)[-1] in relevant
                   and a.get('name','').rsplit('.',1)[0] in {'jakarta.persistence','javax.persistence'}
                   and a['name'].rsplit('.',1)[0] != namespace for a in annotations if isinstance(a,dict)):
                continue
            namespaces.append(namespace)
        return namespaces[0] if len(namespaces) == 1 else None

    def association_fk(item, attr, fact, context, witness, official, declared):
        def unknown(reason):
            item['dimensions']['foreign_key'] = result('UNKNOWN',reason)
        meta = attr.metadata or {}
        if meta.get('access') != 'FIELD' or meta.get('inherited') or len(declared) != 1:
            return unknown('OWNING_FIELD_ASSOCIATION_UNPROVEN')
        relations = [a for a in official if a['name'].rsplit('.',1)[-1] == 'ManyToOne']
        joins = [a for a in official if a['name'].rsplit('.',1)[-1] == 'JoinColumn']
        if len(relations) != 1 or len(joins) != 1:
            return unknown('SINGLE_EXPLICIT_MANY_TO_ONE_JOIN_REQUIRED')
        values = joins[0].get('values',{})
        local_name, referenced_name = _sql_identifier(values.get('name')), _sql_identifier(values.get('referencedColumnName'))
        if local_name is None or referenced_name is None or values.get('table') not in (None,''):
            return unknown('EXPLICIT_PRIMARY_TABLE_JOIN_COLUMNS_REQUIRED')
        association = nodes[declared[0].target]
        if (association.kind != 'orm_association' or association.scope != attr.scope
                or (association.metadata or {}).get('association_role') != 'OWNING'):
            return unknown('OWNING_ASSOCIATION_UNPROVEN')
        bindings = [e for e in edges_from(fact['id'],'projects_persistent_association',context)
                    if e.target == association.id]
        if len(bindings) != 1 or any(proof_id(fact['id'],proofs[ref].get('compiler_symbol_id','')) != fact['id']
                or proofs[ref].get('sha256') != fact['sha256'] for ref in bindings[0].evidence_ids):
            return unknown('COMPILER_ASSOCIATION_WITNESS_UNPROVEN')
        def class_symbol(node):
            symbol = symbols.get(node.id,{})
            if (node.kind != 'class' or symbol.get('kind') != 'class' or symbol.get('context_id') != context['id']
                    or node.scope != attr.scope or not _canonical_symbol(symbol,node,context)
                    or not isinstance(symbol.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',symbol['sha256'])
                    or not current_source(node.path,context,symbol['sha256'])
                    or (node.metadata or {}).get('owner') != symbol.get('owner')
                    or (node.metadata or {}).get('sha256') != symbol['sha256']
                    or not local_id(node.id).endswith(':type:' + str(symbol.get('owner')))
                    or not any(a.get('name') in {'jakarta.persistence.Entity','javax.persistence.Entity'}
                               for a in symbol.get('annotations',[]) if isinstance(a,dict))):
                return None
            return symbol
        owners = [nodes[identity] for identity in class_index.get((context['id'],fact.get('owner')),[])
                  if identity in nodes and class_symbol(nodes[identity])]
        targets = edges_from(association.id,'targets_entity',context)
        if len(owners) != 1 or len(targets) != 1:
            return unknown('CANONICAL_ASSOCIATION_ENTITIES_UNPROVEN')
        target = nodes[targets[0].target]; target_symbol = class_symbol(target)
        if target_symbol is not None and mapping_namespace(target_symbol.get('owner'),context,attr.scope) != mapping_namespace(fact.get('owner'),context,attr.scope):
            return unknown('ASSOCIATION_MAPPING_NAMESPACE_MISMATCH')
        descriptor = fact.get('descriptor','')
        expected_owner = descriptor[1:-1].replace('/','.') if re.fullmatch(r'L[^;]+;',descriptor) else None
        target_entity = relations[0].get('values',{}).get('targetEntity')
        if (target_symbol is None or expected_owner is None or target_symbol.get('owner') != expected_owner
                or target_entity not in (None,'void','java.lang.Void',expected_owner)):
            return unknown('COMPILER_ASSOCIATION_TARGET_MISMATCH')
        def table_for(class_node):
            mapped = edges_from(class_node.id,'maps_to_table',context)
            if len(mapped) != 1:
                return None
            orm = nodes[mapped[0].target]; metadata = orm.metadata or {}
            links = [e for e in edges_from(orm.id,'resolves_to_schema_table',context) if proven(e,context,physical=True)]
            if (orm.kind != 'orm_table' or metadata.get('mapping_status') == 'UNKNOWN' or metadata.get('inferred') is not False
                    or metadata.get('naming_strategy') not in (None,'') or len(links) != 1):
                return None
            physical = nodes[links[0].target]; obj = physical_object(physical,'table')
            return (orm,physical,obj,mapped+links) if obj is not None else None
        owner_table, target_table = table_for(owners[0]),table_for(target)
        declared_tables = edges_from(attr.id,'declared_on_table',context)
        join_edges = edges_from(association.id,'maps_to_join_column',context)
        if (owner_table is None or target_table is None or len(declared_tables) != 1
                or declared_tables[0].target != owner_table[0].id or len(join_edges) != 1
                or _sql_identifier((nodes[join_edges[0].target].metadata or {}).get('logical_name')) != local_name):
            return unknown('EXPLICIT_ASSOCIATION_PHYSICAL_TABLES_UNPROVEN')
        def qualified_object(identity):
            return qualified(split_id(attr.id)[0],identity) if attr.id.startswith('repo:') else identity
        def column(table,name):
            obj = schema['objects'].get(Replay.key('column',tuple(table['name'])+(name,)))
            node = nodes.get(qualified_object(obj['id'])) if obj is not None else None
            return (obj,node) if node is not None and physical_object(node,'column') == obj else None
        local_column, target_column = column(owner_table[2],local_name),column(target_table[2],referenced_name)
        item['compiler_symbol_id'] = fact['id']; item['table_id'] = owner_table[1].id
        used = [witness,*declared,*bindings,*targets,*declared_tables,*join_edges,*owner_table[3],*target_table[3]]
        item['evidence_refs'] = sorted({ref for e in used for ref in e.evidence_ids})
        if any('xml_mapping_file' in proofs[ref] for e in used for ref in e.evidence_ids):
            return unknown('EFFECTIVE_XML_ASSOCIATION_CONTRACT_UNSUPPORTED')
        if local_column is None or target_column is None:
            return unknown('ASSOCIATION_PHYSICAL_COLUMNS_UNPROVEN')
        item['column_id'] = local_column[1].id
        item['dimensions']['presence'] = result('COMPATIBLE','EXPLICIT_ASSOCIATION_COLUMNS_PRESENT')
        item['schema_evidence'] = [copy.deepcopy(obj['last_change']) for obj in (owner_table[2],target_table[2],local_column[0],target_column[0])]
        def source_proved(obj):
            ev = obj.get('last_change',{}); path = ev.get('path')
            if not isinstance(path,str) or not isinstance(ev.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',ev['sha256']):
                return False
            path = '@' + split_id(attr.id)[0] + '/' + path if attr.id.startswith('repo:') else path
            return path in graph.files and graph.files[path] == ev['sha256']
        def key_proof(table,column_name):
            return [obj for obj in schema['objects'].values() if obj.get('kind') == 'constraint'
                    and obj.get('table') == table['name'] and obj.get('constraint_type') in {'PRIMARY','UNIQUE'}
                    and obj.get('columns') == [column_name] and source_proved(obj)]
        expected_keys = key_proof(target_table[2],referenced_name)
        fks = [obj for obj in schema['objects'].values() if obj.get('kind') == 'constraint'
               and obj.get('table') == owner_table[2]['name'] and obj.get('constraint_type') == 'FOREIGN'
               and obj.get('columns') == [local_name] and source_proved(obj)]
        if not expected_keys:
            return unknown('EXPLICIT_REFERENCED_SINGLE_COLUMN_KEY_UNPROVEN')
        if not fks:
            return unknown('NO_PHYSICAL_FK_DECLARED_WITHOUT_EXPLICIT_CONSTRAINT_POLICY')
        if len(fks) != 1 or not isinstance(fks[0].get('referenced_columns'),list) or len(fks[0]['referenced_columns']) != 1:
            return unknown('SINGLE_STRUCTURED_FK_TUPLE_UNPROVEN')
        fk = fks[0]
        actual_table = schema['objects'].get(Replay.key('table',tuple(fk.get('references') or [])))
        actual_node = nodes.get(qualified_object(actual_table['id'])) if actual_table else None
        actual_column = column(actual_table,fk['referenced_columns'][0]) if actual_table else None
        if (actual_node is None or physical_object(actual_node,'table') != actual_table or actual_column is None
                or not key_proof(actual_table,fk['referenced_columns'][0])):
            return unknown('ACTUAL_FK_REFERENCED_KEY_UNPROVEN')
        shape = lambda obj: re.sub(r'\s+','',obj.get('data_type','')).lower()
        supported_shape = re.fullmatch(r'(?:bigint|int8|integer|int|int4|smallint|int2|text|varchar(?:\(\d+\))?|charactervarying(?:\(\d+\))?|(?:numeric|decimal)\(\d+,\d+\))',shape(local_column[0]))
        if not supported_shape or shape(local_column[0]) != shape(actual_column[0]):
            return unknown('FK_COLUMN_TYPE_COMPATIBILITY_UNSUPPORTED')
        exact = fk['references'] == target_table[2]['name'] and fk['referenced_columns'] == [referenced_name]
        item['schema_evidence'].extend(copy.deepcopy(obj['last_change']) for obj in [fk,*expected_keys])
        item['dimensions']['foreign_key'] = result('COMPATIBLE' if exact else 'CONFLICT',
            'EXACT_COMPILER_ASSOCIATION_FK_KEY_TUPLE' if exact else 'PROVEN_FK_TARGET_COLUMN_TUPLE_CONFLICT')

    items = []
    for attr in sorted(graph.nodes, key=lambda n: n.id):
        if attr.kind != 'orm_attribute':
            continue
        meta = attr.metadata or {}; cid = meta.get('context_id')
        if attr.id.startswith('repo:'):
            repo, _ = split_id(attr.id)
            if isinstance(cid, str) and not cid.startswith('repo:'):
                cid = qualified(repo, cid)
            elif isinstance(cid, str) and split_id(cid)[0] != repo:
                cid = None
        if not isinstance(cid,str):
            cid = None
        if context_id is not None and cid != context_id:
            continue
        context = contexts.get(cid, {})
        item = {'attribute_id': attr.id, 'attribute_name': meta.get('attribute'),
                'context_id': cid, 'scope': attr.scope, 'column_id': None, 'table_id':None,
                'compiler_symbol_id':None,'schema_evidence':[],'evidence_refs': [],
                'dimensions': {name: result('UNKNOWN', 'MAPPING_UNPROVEN') for name in dimensions}}
        items.append(item); dims = item['dimensions']
        if (not context or context.get('language') != 'jvm' or context.get('mode') != 'BUILD_IMPORT'
                or context.get('status') not in {'COMPLETE','PARTIAL'} or meta.get('mapping_status') == 'UNKNOWN' or meta.get('access') not in {'FIELD','PROPERTY'}
                or context.get('freshness') not in {'CURRENT','CONTENT_VERIFIED','EXECUTION_BOUND'} or attr.scope != context.get('scope')
                or context.get('database_id') != config['database_id']
                or context.get('schema_stream_id') != config['stream_id']
                or context.get('flyway_target') != config.get('target')
                or not isinstance(context.get('framework_rule_versions'),dict)
                or context['framework_rule_versions'].get('jpa') != JPA_RULE_VERSION
                or not current_source(attr.path, context)
                or schema.get('status') != 'COMPLETE' or schema.get('diagnostics')
                or not replay_sources_current(split_id(attr.id)[0] if attr.id.startswith('repo:') else None)):
            continue
        witnesses = [e for e in graph.edges if e.target == attr.id and e.kind == 'projects_persistent_attribute'
                     and proven(e, context)]
        if len(witnesses) != 1:
            continue
        witness = witnesses[0]; fact = symbols.get(witness.source, {}); canonical = nodes.get(witness.source)
        descriptor = fact.get('descriptor', '')
        name = meta.get('attribute') if meta.get('access') == 'FIELD' else meta.get('getter')
        kind = 'field' if meta.get('access') == 'FIELD' else 'method'
        if (canonical is None or canonical.kind != kind or fact.get('kind') != kind
                or fact.get('name') != name or canonical.name != name
                or meta.get('declaring_owner') != fact.get('owner') or canonical.path != attr.path
                or canonical.signature != descriptor or canonical.scope != attr.scope or fact.get('path') != attr.path
                or fact.get('context_id') != cid or not isinstance(fact.get('sha256'),str)
                or not re.fullmatch(r'[0-9a-f]{64}',fact['sha256'])
                or not current_source(attr.path, context, fact.get('sha256'))
                or not local_id(fact.get('id', '')).endswith(':' + kind + ':' + str(fact.get('owner')) + '.' + str(name) + (':' if kind == 'field' else '') + descriptor)
                or any(proof_id(witness.source, proofs[ref].get('compiler_symbol_id', '')) != fact.get('id')
                       or proofs[ref].get('sha256') != fact.get('sha256') for ref in witness.evidence_ids)):
            continue
        # The compiler record and canonical node independently retain the owner.
        canonical_meta = canonical.metadata or {}
        if any(canonical_meta.get(key) != fact.get(key) for key in ('owner', 'name', 'descriptor', 'kind', 'sha256')):
            continue
        if kind == 'method':
            if not descriptor.startswith('()'):
                continue
            descriptor = descriptor[2:]
        if not isinstance(context.get('repo_id'),str) or not _canonical_symbol(fact,canonical,context):
            continue
        official = _verified_mapping_annotations(fact,canonical)
        namespace = mapping_namespace(fact.get('owner'),context,attr.scope)
        effective_owner = meta.get('effective_owner')
        if (official is None or namespace is None or any(a['name'].rsplit('.',1)[0] != namespace for a in official)
                or effective_owner is not None and mapping_namespace(effective_owner,context,attr.scope) != namespace):
            continue
        associations = {'ManyToOne','OneToOne','OneToMany','ManyToMany','JoinColumn','JoinColumns','JoinTable'}
        if any(a['name'].rsplit('.',1)[-1] in associations for a in official):
            declared = edges_from(attr.id, 'declares_association', context)
            item['association_ids'] = [e.target for e in declared]
            item['evidence_refs'] = sorted({ref for e in [witness,*declared] for ref in e.evidence_ids})
            for dimension in dimensions:
                dims[dimension] = result('UNKNOWN','ASSOCIATION_EFFECTIVE_FK_CONTRACT_UNSUPPORTED')
            association_fk(item,attr,fact,context,witness,official,declared)
            continue
        columns = [a for a in official if a['name'].rsplit('.',1)[-1] == 'Column' and a.get('values_resolved') is not False]
        if (len(columns) != 1 or not isinstance(columns[0].get('values'), dict)
                or any(a['name'].rsplit('.',1)[-1] in {'Convert','Converts','Enumerated','Temporal','Lob','Embedded','EmbeddedId'} for a in official)):
            continue
        values = columns[0]['values']
        if values.get('table') not in (None,'') or values.get('columnDefinition') not in (None,''):
            continue
        mapped = edges_from(attr.id, 'maps_to_column', context)
        tables = edges_from(attr.id, 'declared_on_table', context)
        if len(mapped) != 1 or len(tables) != 1:
            continue
        orm_column = nodes[mapped[0].target]; orm_table = nodes[tables[0].target]
        cm = orm_column.metadata or {}; tm = orm_table.metadata or {}
        xml_mapping = (str(meta.get('mapping_source', '')).startswith('ORM_XML')
                       or any('xml_mapping_file' in proofs[ref] for e in mapped + tables for ref in e.evidence_ids))
        if (xml_mapping or cm.get('mapping_status') == 'UNKNOWN' or tm.get('mapping_status') == 'UNKNOWN'
                or cm.get('inferred') is not False or tm.get('inferred') is not False
                or tm.get('naming_strategy') not in (None, '') or cm.get('logical_name') != values.get('name')):
            continue
        table_links = [e for e in edges_from(orm_table.id, 'resolves_to_schema_table', context)
                       if proven(e, context, physical=True)]
        if len(table_links) != 1:
            continue
        table = physical_object(nodes[table_links[0].target], 'table')
        if table is None:
            continue
        item['table_id'] = table_links[0].target
        item['compiler_symbol_id'] = fact['id']
        item['schema_evidence'] = [copy.deepcopy(table['last_change'])]
        expected_name = tuple(table['name']) + (identifier(values['name']),)
        obj = schema['objects'].get(Replay.key('column', expected_name))
        links = [e for e in edges_from(orm_column.id, 'resolves_to_schema_column', context)
                 if proven(e, context, physical=True)]
        item['evidence_refs'] = sorted({ref for e in [witness, *mapped, *tables, *table_links, *links] for ref in e.evidence_ids})
        if obj is None:
            dims['presence'] = result('CONFLICT', 'EXPLICIT_COLUMN_ABSENT_FROM_COMPLETE_SELECTED_TABLE')
            continue
        if len(links) != 1 or physical_object(nodes[links[0].target], 'column') != obj:
            continue
        item['column_id'] = links[0].target
        item['schema_evidence'].append(copy.deepcopy(obj['last_change']))
        dims['presence'] = result('COMPATIBLE', 'EXPLICIT_COLUMN_PRESENT')
        sql = re.sub(r'\s+', '', obj.get('data_type','')).lower()
        decimal = re.fullmatch(r'(?:numeric|decimal)\((\d+),(\d+)\)',sql)
        type_groups = {'J': {'bigint','int8'}, 'Ljava/lang/Long;': {'bigint','int8'},
            'I': {'integer','int','int4'}, 'Ljava/lang/Integer;': {'integer','int','int4'},
            'Ljava/lang/String;': {'text','varchar','charactervarying'},
            'Ljava/math/BigDecimal;': {'numeric','decimal'}}
        expected = type_groups.get(descriptor)
        if expected is None:
            dims['type'] = result('UNKNOWN','UNSUPPORTED_CANONICAL_COMPILER_DESCRIPTOR')
        if expected is not None:
            family = 'numeric' if decimal else sql
            if descriptor == 'Ljava/lang/String;' and re.fullmatch(r'(?:varchar|charactervarying)\(\d+\)', sql):
                family = 'varchar'
            known_sql = {'bigint','int8','integer','int','int4','smallint','int2','text','varchar',
                         'charactervarying','boolean','bool','numeric','decimal','real','float4','doubleprecision','float8'}
            if family in known_sql:
                dims['type'] = result('COMPATIBLE' if family in expected else 'CONFLICT', 'CANONICAL_COMPILER_DESCRIPTOR_VS_SQL_TYPE')
            else:
                dims['type'] = result('UNKNOWN','UNSUPPORTED_SQL_TYPE')
        nullable = False if any(a['name'].rsplit('.',1)[-1] == 'Id' for a in official) else values.get('nullable')
        if type(nullable) is bool and type(obj.get('nullable')) is bool:
            dims['nullability'] = result('CONFLICT' if nullable and not obj['nullable'] else 'COMPATIBLE', 'EXPLICIT_ORM_NULLABILITY_PERSISTENCE_DIRECTION')
        for dimension, index in (('precision',1),('scale',2)):
            number = values.get(dimension)
            if descriptor != 'Ljava/math/BigDecimal;':
                dims[dimension] = result('COMPATIBLE','NOT_REQUIRED_FOR_SUPPORTED_NON_DECIMAL') if expected else result('UNKNOWN','UNSUPPORTED_COMPILER_TYPE')
            elif type(number) is int and values.get('precision',0) > 0:
                dims[dimension] = (result('COMPATIBLE' if int(decimal[index]) == number else 'CONFLICT', 'EXPLICIT_DECIMAL_DIMENSION')
                                   if decimal else result('UNKNOWN','SQL_DECIMAL_DIMENSIONS_UNPROVEN'))
        constraints = [x for x in schema['objects'].values() if x.get('kind') == 'constraint' and x.get('table') == table['name']]
        item['schema_evidence'].extend(copy.deepcopy(x['last_change']) for x in constraints)
        if any(x.get('constraint_type') == 'CHECK' for x in constraints):
            dims['nullability'] = result('UNKNOWN','CHECK_CONSTRAINT_SEMANTICS_UNSUPPORTED')
        required_pk = any(a['name'].rsplit('.',1)[-1] == 'Id' for a in official)
        for dimension, required, sqlkind in (('primary_key',required_pk,'PRIMARY'),('unique',values.get('unique'),'UNIQUE')):
            if required is False:
                dims[dimension] = result('COMPATIBLE','NOT_REQUIRED')
            elif required is True:
                match = any(x.get('constraint_type') == sqlkind and x.get('columns') == [expected_name[-1]] for x in constraints)
                if (not match and dimension == 'primary_key' and any(x.get('constraint_type') == 'PRIMARY'
                        and expected_name[-1] in x.get('columns',[]) and len(x.get('columns',[])) > 1 for x in constraints)):
                    dims[dimension] = result('UNKNOWN','COMPOSITE_IDENTIFIER_CONTRACT_UNSUPPORTED')
                elif (not match and dimension == 'unique' and any(x.get('kind') == 'index' and x.get('unique') is True
                        and x.get('table') == table['name'] for x in schema['objects'].values())):
                    dims[dimension] = result('UNKNOWN','UNIQUE_INDEX_COLUMNS_UNSUPPORTED')
                else:
                    dims[dimension] = result('COMPATIBLE' if match else 'CONFLICT','EXPLICIT_SINGLE_COLUMN_KEY')
        dims['foreign_key'] = result('COMPATIBLE','NOT_REQUIRED')
    for item in items:
        statuses = {d['status'] for d in item['dimensions'].values()}
        item['status'] = 'CONFLICT' if 'CONFLICT' in statuses else 'UNKNOWN' if 'UNKNOWN' in statuses else 'COMPATIBLE'
    statuses = {i['status'] for i in items}
    return {'schema_version':1, 'rules_version':COMPATIBILITY_VERSION,
            'status':'CONFLICT' if 'CONFLICT' in statuses else 'COMPATIBLE' if statuses == {'COMPATIBLE'} else 'UNKNOWN',
            'realm':{'database_id':config['database_id'],'stream_id':config['stream_id'],'target':config.get('target')},
            'schema_snapshot_fingerprint':snapshot, 'items':items, 'replay_status':schema['status'],
            'diagnostics':list(schema.get('diagnostics',[])) + ([] if items else ['NO_COMPILER_OWNED_ATTRIBUTES_IN_SELECTED_CONTEXT']),
            'data_availability':'UNASSESSED','deployment_verified':False,
            'limitations':['Static selected-snapshot compatibility; no deployment, populated data or runtime observation.']}

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

PARSER_VERSION = 'postgres-ddl-2-realms'
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
    return {'database_id': config['database_id'], 'stream_id': config['stream_id'],
            'schema': schema_name, 'schemas': list(config['schemas']), 'target': config['target'],
            'config_fingerprint': digest(config), 'explicit_keys': keys,
            'derivation': 'MIGRATION_DERIVED'}


def schema_node_realm(node):
    """Validate the replay object's typed identity against its structured proof."""
    metadata = node.metadata
    if not isinstance(metadata, dict):
        return None
    realm, name = metadata.get('persistence_realm'), metadata.get('schema_object')
    if not isinstance(realm, dict) or not isinstance(name, list) or not name or any(
            not isinstance(n, str) or not n for n in name):
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
    expected = 'schema:' + realm_prefix({'database_id': pair[0], 'stream_id': pair[1]}) + ':' + Replay.key(node.kind[3:], name)
    if node.id != expected and not re.fullmatch(re.escape(expected) + r':incarnation:[0-9a-f]{12}', node.id):
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
        if any(old['id'] == identity for old in self.history):
            identity += ':incarnation:' + digest(self.evidence)[:12]
        item = {'id': identity, 'kind': kind, 'name': list(name), 'lifecycle': 'ACTIVE',
                'origin': copy.deepcopy(self.evidence), 'last_change': copy.deepcopy(self.evidence),
                'previous_names': [], **attributes}
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
        if 'REFERENCES' in upper:
            index = upper.index('REFERENCES') + 1
            target, index = self.name(tokens, index)
            self.get('table', target)
            referenced = list(target)
        self.create('constraint', table + (name,), table=list(table),
                    constraint_type=upper[0], columns=columns, references=referenced, expression=' '.join(tokens))
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
        item = self.create('column', table + (name,), table=list(table), data_type=type_text,
                           nullable=not ('NOT' in upper or 'PRIMARY' in upper), default=default)
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
                            constraint['columns'] = [identifier(action[4]) if c == identifier(action[2]) else c for c in constraint.get('columns', [])]
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
                                    'schema_object': list(item['name'])}))
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

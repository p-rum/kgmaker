"""Narrow, evidenced HTTP/UI/test linkage. No test execution or PASS claims."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .analysis_model import safe_path
from .model import Edge, Node
from .dataflow import masked
from .contract_inputs import capture_file, generation_origin


def normalized_path(path: str) -> str:
    # Only documented whole-segment path parameters are normalized.
    return re.sub(r'\{[A-Za-z_]\w*\}', '{}', path.rstrip('/') or '/')


def _ref(document, value):
    visited = set()
    while isinstance(value, dict) and '$ref' in value:
        pointer = value['$ref']
        if not isinstance(pointer, str) or not pointer.startswith('#/') or pointer in visited:
            return None
        visited.add(pointer)
        value = document
        try:
            for key in pointer[2:].split('/'):
                value = value[key.replace('~1', '/').replace('~0', '~')]
        except (KeyError, TypeError):
            return None
    return value


def federated_links(workspace, graphs, sources):
    from .workspace import qualified, source_key
    nodes, edges, diagnostics = {}, set(), []
    repo_map = {r['id']: r for r in workspace['repositories']}
    calls, fields, ui_elements = {}, {}, {}

    def file_identity(repo, path):
        matches = [n.id for n in graphs[repo].nodes if n.kind == 'file' and n.path == path]
        return qualified(repo, matches[0]) if len(matches) == 1 else None

    def node(identity, kind, name, repo, path, line, signature=None):
        result = Node(identity, kind, name, source_key(repo, path), line, signature)
        nodes[identity] = result
        return result

    def edge(source, target, kind, repo, path, line, evidence, confidence='EXTRACTED'):
        edges.add(Edge(source, target, kind, evidence, confidence, 1 if confidence == 'EXTRACTED' else .65,
                       source_key(repo, path), line))

    for service in workspace.get('services', []):
        if service.get('transport') == 'kafka':
            continue
        declared = service['contract']; repo, path = declared['repo_id'], declared['path']
        if repo not in graphs:
            diagnostics.append('Contract checkout missing: ' + service['id']); continue
        key = source_key(repo, path)
        if key not in sources:
            diagnostics.append('Contract not inventoried: ' + service['id']); continue
        try:
            document = capture_file(Path(repo_map[repo]['_root']), path, json_document=True)['document']
        except (ValueError, OSError):
            diagnostics.append('Unsupported contract: ' + key); continue
        if not isinstance(document, dict) or not isinstance(document.get('paths'), dict):
            diagnostics.append('Service contract is not OpenAPI JSON: ' + key); continue
        contract_id = 'workspace:contract:' + service['id'] + ':' + sources[key]['sha256']
        node(contract_id, 'api_contract', service['id'], repo, path, 1)
        generated = []
        for declaration in service.get('generated_clients', []):
            if not isinstance(declaration, dict) or set(declaration) != {'repo_id', 'path', 'metadata_path', 'consumers'}:
                diagnostics.append('Unsupported generated-client declaration: ' + service['id']); continue
            consumer = declaration['repo_id']
            if consumer not in graphs:
                diagnostics.append('Generated-client checkout missing: ' + str(consumer)); continue
            metadata_key = source_key(consumer, declaration['metadata_path'])
            if metadata_key not in sources:
                diagnostics.append('Generation metadata not inventoried: ' + metadata_key); continue
            try:
                metadata = capture_file(Path(repo_map[consumer]['_root']), declaration['metadata_path'], json_document=True)['document']
                expected_origin = {'repo_id': repo, 'path': path, 'sha256': sources[key]['sha256']}
                if generation_origin(metadata, expected_origin, declaration['path'])[0] != 'VALID':
                    diagnostics.append('Generated-client contract version mismatch: ' + consumer + '/' + declaration['path']); continue
                safe_path(Path(repo_map[consumer]['_root']), declaration['path'])
            except (ValueError, OSError, TypeError):
                diagnostics.append('Invalid generation provenance: ' + metadata_key); continue
            artifact = node(qualified(consumer, 'generated_client:' + declaration['path']), 'generated_client', declaration['path'], consumer, declaration['metadata_path'], 1)
            edge(artifact.id, contract_id, 'depends_on_contract', consumer, declaration['metadata_path'], 1,
                 'Generation metadata cites the original contract version; not independent confirmation')
            generated.append(artifact.id)
            for consumer_path in declaration['consumers']:
                if source_key(consumer, consumer_path) not in sources:
                    diagnostics.append('Generated-client consumer not covered: ' + consumer + '/' + consumer_path); continue
                target = file_identity(consumer, consumer_path)
                if target:
                    edge(artifact.id, target, 'sent_to', consumer,
                         declaration['metadata_path'], 1, 'Declared generation consumer; candidate until source use is checked', 'INFERRED')
        for route, methods in document['paths'].items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}:
                    continue
                if not isinstance(operation, dict):
                    continue
                identity = 'workspace:service:' + service['id'] + ':endpoint:' + method.upper() + ':' + route
                endpoint = node(identity, 'api_endpoint', method.upper() + ' ' + route, repo, path, 1)
                providers = [n for n in graphs.get(service['backend_repo'], graphs[repo]).nodes
                             if n.kind == 'api_endpoint' and n.name.upper().split(' ', 1)[0] == method.upper()
                             and Path(n.path).suffix in {'.kt', '.java', '.py', '.ts', '.js'}
                             and normalized_path(n.name.split(' ', 1)[-1]) == normalized_path(route)]
                if len(providers) == 1:
                    provider = providers[0]
                    edge(qualified(service['backend_repo'], provider.id), endpoint.id, 'maps_to',
                         service['backend_repo'], provider.path, provider.line or 1, 'Explicit service identity, method and path')
                elif len(providers) > 1:
                    diagnostics.append('Ambiguous provider endpoint: ' + service['id'] + ':' + route)
                properties = {}
                for status, response in operation.get('responses', {}).items():
                    if not str(status).startswith('2'):
                        continue
                    response = _ref(document, response)
                    schema = response.get('content', {}).get('application/json', {}).get('schema', {}) if isinstance(response, dict) else {}
                    schema = _ref(document, schema)
                    if isinstance(schema, dict) and schema.get('type') == 'array':
                        schema = _ref(document, schema.get('items'))
                    if isinstance(schema, dict):
                        for field, spec in schema.get('properties', {}).items():
                            if field in properties and properties[field] != spec:
                                diagnostics.append('Ambiguous response field: ' + service['id'] + ':' + field)
                            properties[field] = spec
                field_nodes = {}
                for field, spec in sorted(properties.items()):
                    field_node = node(identity + ':field:' + field, 'contract_field', field, repo, path, 1,
                                      spec.get('type') if isinstance(spec, dict) else None)
                    field_nodes[field] = field_node.id
                    edge(field_node.id, contract_id, 'maps_to', repo, path, 1, 'Field belongs to this contract version')
                    for artifact in generated:
                        edge(field_node.id, artifact, 'serialized_as', repo, path, 1,
                             'Generated client derives from original contract; no independent proof')
                    # Optional explicit origin ID in contract; a linkage, not an availability proof.
                    origin = spec.get('x-kgmaker-source') if isinstance(spec, dict) else None
                    if isinstance(origin, str) and any(n.id == origin for n in graphs.get(service['backend_repo'], graphs[repo]).nodes):
                        edge(qualified(service['backend_repo'], origin), field_node.id, 'serialized_as',
                             repo, path, 1, 'Explicit contract source annotation; business equivalence unassessed', 'INFERRED')
                consumers = service.get('frontend_repos', []) + service.get('test_repos', [])
                for consumer in consumers:
                    if consumer not in graphs:
                        continue
                    for source, meta in sources.items():
                        if meta['repo_id'] != consumer or Path(meta['path']).suffix not in {'.ts', '.tsx', '.js', '.jsx', '.java', '.kt'}:
                            continue
                        file_path = meta['path']
                        text = safe_path(Path(repo_map[consumer]['_root']), file_path).read_text(encoding='utf-8')
                        code = masked(text)
                        matches = []
                        for call in re.finditer(r'\b(fetch|axios\.(get|post|put|patch|delete)|request\.(get|post|put|patch|delete)|\.(get|post|put|patch|delete))\s*\(\s*[\"\']([^\"\']+)[\"\']', text):
                            if not code[call.start():call.start() + len(call[1])].strip():
                                continue
                            call_method = next((v for v in call.groups()[1:4] if v), 'get').upper()
                            if call[1] == 'fetch' and not re.match(r'\s*\)', text[call.end():]):
                                diagnostics.append('Fetch options/method require supported explicit parsing: ' + consumer + '/' + file_path)
                                continue
                            request_path = call[5]
                            prefix = service.get('consumer_path_prefix', '')
                            if prefix and request_path != prefix and not request_path.startswith(prefix.rstrip('/') + '/'):
                                continue
                            request_path = service.get('provider_path_prefix', '') + request_path[len(prefix):]
                            if call_method == method.upper() and normalized_path(request_path) == normalized_path(route):
                                matches.append(call)
                        if not matches:
                            continue
                        # Two services may declare the same consumer. Never silently disambiguate.
                        contenders = [s for s in workspace.get('services', []) if consumer in s.get('frontend_repos', []) + s.get('test_repos', [])
                                      and s.get('consumer_path_prefix', '') == service.get('consumer_path_prefix', '')]
                        if len(contenders) > 1:
                            diagnostics.append('Ambiguous service identity for consumer: ' + consumer + '/' + file_path); continue
                        file_id = file_identity(consumer, file_path)
                        if file_id is None:
                            diagnostics.append('Consumer source has no structural file identity: ' + consumer + '/' + file_path); continue
                        calls.setdefault((consumer, file_path), []).append((endpoint.id, field_nodes))
                        for match in matches:
                            line = text.count('\n', 0, match.start()) + 1
                            edge(endpoint.id, file_id, 'sent_to', consumer, file_path, line, 'Explicit HTTP call under manifest service/prefix mapping')
                            if consumer in service.get('test_repos', []):
                                edge(file_id, endpoint.id, 'tests_endpoint', consumer, file_path, line, 'Request exists; does not prove assertion coverage')
                        fields[consumer, file_path] = field_nodes

    for repo, graph in sorted(graphs.items(), key=lambda item: repo_map[item[0]]['role'] == 'automated-tests'):
        root = Path(repo_map[repo]['_root'])
        role = repo_map[repo]['role']
        for source, metadata in sources.items():
            if metadata['repo_id'] != repo:
                continue
            path = metadata['path']; suffix = Path(path).suffix
            if suffix not in {'.ts', '.tsx', '.js', '.jsx', '.java', '.kt'}:
                continue
            text = safe_path(root, path).read_text(encoding='utf-8')
            code = masked(text)
            file_id = file_identity(repo, path)
            if file_id is None:
                continue
            if role == 'frontend' and (repo, path) in fields:
                for match in re.finditer(r'<([A-Za-z]\w*)[^>]*\bdata-testid=[\"\']([^\"\']+)[\"\'][^>]*>\s*\{\s*\w+\.(\w+)\s*\}', text):
                    if not code[match.start():match.start() + 1].strip():
                        continue
                    if match[3] not in fields[repo, path]:
                        diagnostics.append('UI field absent from selected contract: ' + repo + '/' + path + ':' + match[3]); continue
                    if len(calls.get((repo, path), [])) != 1:
                        diagnostics.append('Multiple endpoint responses prevent UI field resolution: ' + repo + '/' + path); continue
                    line = text.count('\n', 0, match.start()) + 1
                    ui = node(qualified(repo, 'ui_element:' + path + ':' + match[2]), 'ui_element', match[2], repo, path, line)
                    ui_elements.setdefault(match[2], []).append(ui.id)
                    edge(fields[repo, path][match[3]], ui.id, 'displayed_in', repo, path, line,
                         'Explicit field use in a single-response component; runtime mapping unverified', 'INFERRED')
            if role == 'automated-tests':
                suite = node(qualified(repo, 'test_suite:' + path), 'test_suite', path, repo, path, 1)
                test_matches = [m for m in re.finditer(r'\b(?:test|it)\s*\(\s*[\"\']([^\"\']+)[\"\']|@Test\s+(?:public\s+)?(?:void|fun)\s+(\w+)', text)
                                if code[m.start():m.start() + 2].strip()]
                cases = []
                for index, match in enumerate(test_matches):
                    line = text.count('\n', 0, match.start()) + 1
                    case = node(qualified(repo, 'test_case:' + path + ':' + str(line)), 'test_case', match[1] or match[2], repo, path, line)
                    end = test_matches[index + 1].start() if index + 1 < len(test_matches) else len(text)
                    cases.append((case, text[match.start():end], match.start()))
                    edge(file_id, case.id, 'tested_by', repo, path, line, 'Test declaration belongs to this source')
                    edge(suite.id, case.id, 'tested_by', repo, path, line, 'Test suite contains case')
                for case, body, offset in cases:
                    for match in re.finditer(r'\bexpect\s*\(\s*\w+\.(\w+)\s*\)\s*\.to(?:Be|Equal|BeTruthy|BeDefined)|\.body\s*\(\s*[\"\'](\w+)[\"\']', body):
                        if not code[offset + match.start():offset + match.start() + 2].strip():
                            continue
                        field = match[1] or match[2]
                        line = text.count('\n', 0, offset + match.start()) + 1
                        assertion = node(qualified(repo, 'test_assertion:' + path + ':' + str(line)), 'test_assertion', field, repo, path, line)
                        edge(case.id, assertion.id, 'tested_by', repo, path, line, 'Explicit assertion in test case')
                        if field in fields.get((repo, path), {}) and len(calls.get((repo, path), [])) == 1:
                            target = fields[repo, path][field]
                            edge(assertion.id, target, 'asserts_field', repo, path, line, 'Single-call field assertion; not a runtime PASS claim', 'INFERRED')
                    for match in re.finditer(r'getByTestId\s*\(\s*[\"\']([^\"\']+)[\"\']', body):
                        if not code[offset + match.start():offset + match.start() + 2].strip():
                            continue
                        line = text.count('\n', 0, offset + match.start()) + 1
                        targets = ui_elements.get(match[1], [])
                        if len(targets) == 1:
                            edge(case.id, targets[0], 'targets_ui', repo, path, line, 'Unique explicit data-testid locator')
                        else:
                            diagnostics.append('Unresolved UI selector: ' + repo + '/' + path + ':' + match[1])
                if not test_matches:
                    kind = 'test_fixture' if re.search(r'fixture|test.?data|builder', path, re.I) else 'test_helper'
                    helper = node(qualified(repo, kind + ':' + path), kind, path, repo, path, 1)
                    edge(helper.id, file_id, 'maps_to', repo, path, 1, 'Fixture/helper source identity; invocation remains unverified')
                for local_edge in graph.edges:
                    if local_edge.kind == 'imports' and qualified(repo, local_edge.source) == file_id:
                        edge(qualified(repo, local_edge.source), qualified(repo, local_edge.target), 'uses_fixture',
                             repo, path, local_edge.source_line or 1, 'Explicit imported helper/fixture; invocation coverage unverified', 'INFERRED')
    return sorted(nodes.values(), key=lambda n: n.id), sorted(edges, key=lambda e: (e.source, e.kind, e.target)), sorted(set(diagnostics))


def test_data_diagnostics(workspace, sources, schemas):
    from .schema_replay import statements, Replay, identifier
    diagnostics = []
    repo_map = {r['id']: r for r in workspace['repositories']}
    for key, source in sources.items():
        repo, path = source['repo_id'], source['path']
        if repo_map[repo]['role'] != 'automated-tests' or Path(path).suffix != '.sql':
            continue
        services = [s for s in workspace.get('services', []) if repo in s.get('test_repos', [])]
        if len(services) != 1 or len(schemas.get(services[0]['backend_repo'], [])) != 1:
            diagnostics.append('Test SQL schema identity is ambiguous: ' + key); continue
        schema = schemas[services[0]['backend_repo']][0]
        replay = Replay(schema['config'])
        text = safe_path(Path(repo_map[repo]['_root']), path).read_text()
        try:
            for tokens, line in statements(text):
                if [t.upper() for t in tokens[:2]] != ['INSERT', 'INTO']:
                    continue
                table, offset = replay.name(tokens, 2)
                if tokens[offset:offset + 1] != ['('] or ')' not in tokens[offset:]:
                    diagnostics.append(f'Test SQL columns are unresolved: {key}:{line}'); continue
                end = tokens.index(')', offset)
                for token in tokens[offset + 1:end]:
                    if token == ',':
                        continue
                    column = Replay.key('column', table + (identifier(token),))
                    if column not in schema['objects']:
                        diagnostics.append(f'Test data/schema mismatch: {key}:{line} references absent {column}; target {schema["config"]["target"]}; migration scope {services[0]["backend_repo"]}/{schema["config"]["stream_id"]}')
        except (ValueError, IndexError):
            diagnostics.append('Unsupported test SQL: ' + key)
    return diagnostics

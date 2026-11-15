"""Compiler occurrence federation through explicitly captured contract provenance."""
from .analysis_model import digest
from .worker_protocol import WorkerError

VERSION = 'frontend-values-1'
ROLES = {'HTTP_RESPONSE', 'JSON_RESULT', 'ASSIGNMENT', 'FIELD_READ', 'DESTRUCTURE',
         'OBJECT_MAPPING', 'STATE_WRITE', 'JSX_CONSUMER', 'ARGUMENT'}


def validate_frontend_values(response, context):
    """Optional additive protocol; old workers have no frontend value claims."""
    from .local_operations import _range
    symbols = {s['id']: s for s in response['symbols']}
    sites = {s['id']: s for s in response['call_sites']}
    def fail():
        raise WorkerError('Invalid frontend value occurrence/source/context', 'INVALID_PROTOCOL')
    for item in [*response['symbols'], *response['facts']]:
        if 'value_flow_version' not in item:
            continue
        path = item.get('path'); span = item.get('range')
        if (type(item['value_flow_version']) is not int or item['value_flow_version'] != 1
                or not isinstance(path, str) or context.get('source_files', {}).get(path) != item.get('sha256')
                or not _range(span) or item.get('runtime_execution') != 'NOT_OBSERVED'
                or item.get('availability') != 'UNKNOWN'):
            fail()
        if 'source' in item:
            if item.get('kind') not in {'maps_to', 'writes_value', 'passes_value', 'displayed_in'}:
                fail()
            for key in ('source', 'target'):
                target = symbols.get(item[key], {})
                if target.get('value_flow_version') != 1 or target.get('context_id') != context['id']:
                    fail()
            source, target = symbols[item['source']], symbols[item['target']]
            if (source.get('request') != target.get('request')
                    or any(source.get(k) != target.get(k) or item.get(k) != target.get(k) for k in ('path', 'sha256'))
                    or item.get('range') != target.get('range')
                    or source.get('field') is not None and source.get('field') != target.get('field')):
                fail()
            target_roles = {'writes_value': 'STATE_WRITE', 'passes_value': 'ARGUMENT', 'displayed_in': 'JSX_CONSUMER'}
            if item['kind'] in target_roles and target.get('value_role') != target_roles[item['kind']]:
                fail()
            if item['kind'] == 'maps_to' and target.get('value_role') not in {'ASSIGNMENT', 'JSON_RESULT', 'FIELD_READ', 'DESTRUCTURE', 'OBJECT_MAPPING'}:
                fail()
        else:
            expected = f"value:{context['id']}:{path}:{item['sha256']}:{span['start']}:{span['end']}:{item.get('value_role')}"
            if 'projection_key' in item:
                from urllib.parse import quote
                projection = item['projection_key']
                if projection is not None and not isinstance(projection, str):
                    fail()
                expected += ':projection:' + quote('null' if projection is None else projection, safe="-_.!~*'()")
            if (item['id'] != expected or item.get('kind') != 'value_occurrence'
                    or item.get('value_role') not in ROLES or item.get('context_id') != context['id']
                    or item.get('scope') != context.get('scope')):
                fail()
            parents = [s for s in response['symbols'] if s.get('value_flow_version') is None
                       and s.get('path') == path and s.get('sha256') == item['sha256']
                       and s.get('context_id') == context['id'] and _range(s.get('range'))
                       and s['range']['start'] <= span['start'] < span['end'] <= s['range']['end']]
            if not parents:
                fail()
            request = item.get('request')
            if (not isinstance(request, dict) or set(request) != {'call_site', 'method', 'path'}
                    or request.get('call_site') not in sites or request.get('method') != 'GET'
                    or not isinstance(request.get('path'), str) or not request['path'].startswith('/')):
                fail()
            site = sites[request['call_site']]
            if site.get('path') != path or site.get('sha256') != item['sha256'] or site.get('context_id') != context['id']:
                fail()
            declaration = item.get('field_declaration')
            if declaration is not None:
                selected = symbols.get(declaration.get('symbol'), {}) if isinstance(declaration, dict) else {}
                if (not selected or any(selected.get(k) != declaration.get(k) for k in ('path', 'sha256', 'range'))
                        or context.get('source_files', {}).get(selected.get('path')) != selected.get('sha256')
                        or not _range(selected.get('range'))):
                    fail()
            if item.get('value_role') == 'HTTP_RESPONSE' and item['range'] != site.get('range'):
                fail()
            if item.get('value_role') == 'STATE_WRITE':
                adapter = item.get('ui_adapter', {})
                if (context.get('ui_framework') != 'react' or adapter.get('status') != 'SUPPORTED'
                        or adapter.get('react_version') != '18.3.1' or adapter.get('types_version') != '18.3.18'
                        or adapter.get('declaration_sha256') != 'b89c2ddec6bd955e8721d41e24ca667de06882338d88b183c2cdc1f41f4c5a34'):
                    fail()


def workspace_value_links(workspace, graphs, sources):
    """Read captured inputs only. Declaration provenance is not payload equivalence."""
    from pathlib import Path
    from .contract_inputs import capture_file, generation_origin
    from .model import Edge
    from .workspace import qualified, source_key
    from .test_analysis import _ref
    repos = {r['id']: r for r in workspace['repositories']}
    edges, evidence, diagnostics = [], [], []
    from .graph_provider import validate_context_snapshot
    current_contexts = {}
    needed = {repo for repo, local in graphs.items() if any(s.get('value_flow_version') == 1 for s in local.symbols)}
    needed |= {service['backend_repo'] for service in workspace.get('services', [])
               if needed.intersection(service.get('frontend_repos', []) + service.get('test_repos', []))}
    validated_contexts = []
    for identity, local in graphs.items():
        current_contexts[identity] = {}
        for context in local.contexts if identity in needed else []:
            if context.get('freshness') != 'CONTENT_VERIFIED':
                continue
            try:
                validate_context_snapshot(Path(repos[identity]['_root']), context)
            except (WorkerError, ValueError, OSError):
                continue
            current_contexts[identity][context['id']] = context
            validated_contexts.append((Path(repos[identity]['_root']), context))
    def gap(code, repo, path):
        diagnostics.append(code + ': ' + repo + '/' + path)
    def link(source, target, kind, repo, path, sha, contexts, details):
        proof = {'source': source, 'target': target, 'relation': kind,
                 'kind': 'FRAMEWORK_DERIVED', 'source_file': source_key(repo, path), 'sha256': sha,
                 'context_ids': contexts, 'extractor': VERSION, 'runtime_execution': 'NOT_OBSERVED',
                 'availability': 'UNKNOWN', 'payload_compatibility': 'UNKNOWN', **details}
        identity = 'evidence:' + digest(proof)
        evidence.append({'id': identity, **proof})
        edges.append(Edge(source, target, kind, evidence_kind='FRAMEWORK_DERIVED',
                          context_ids=tuple(contexts), evidence_ids=(identity,), source_file=source_key(repo, path)))
    for repo, graph in graphs.items():
        if repos[repo]['role'] not in {'frontend', 'automated-tests'}:
            continue
        contexts = current_contexts[repo]
        values = [s for s in graph.symbols if s.get('value_flow_version') == 1 and s.get('context_id') in contexts]
        if not values:
            gap('VALUE_FLOW_COMPILER_EVIDENCE_UNAVAILABLE', repo, '*')
        adjacency = {}
        roles = {s['id']: s.get('value_role') for s in values}
        for edge in graph.edges:
            if edge.source in roles and edge.target in roles and edge.kind in {'maps_to', 'writes_value', 'displayed_in', 'passes_value'}:
                adjacency.setdefault(edge.source, []).append(edge.target)
        for request_value in (s for s in values if s.get('value_role') == 'HTTP_RESPONSE'):
            pending = [request_value['id']]; seen = set()
            while pending:
                at = pending.pop()
                if at in seen:
                    continue
                seen.add(at); pending.extend(adjacency.get(at, []))
            if not any(roles.get(at) in {'JSX_CONSUMER', 'ARGUMENT'} for at in seen):
                gap('VALUE_FLOW_CONSUMER_UNPROVEN', repo, request_value['path'])
        # Link only first actual field projections. Every subsequent consumer is
        # reached through compiler occurrence edges, never same-name lookup.
        for value in values:
            if value.get('value_role') not in {'DESTRUCTURE', 'FIELD_READ'} or not value.get('field') or value.get('json_projection') is not True:
                continue
            request = value['request']; path = value['path']; field = value['field']
            if value.get('sha256') != sources.get(source_key(repo, path), {}).get('sha256'):
                continue
            candidates = []
            for service in workspace.get('services', []):
                if service.get('transport') == 'kafka' or repo not in service.get('frontend_repos', []) + service.get('test_repos', []):
                    continue
                prefix = service.get('consumer_path_prefix', '')
                route = request['path']
                if prefix and not route.startswith(prefix.rstrip('/') + '/'):
                    continue
                route = service.get('provider_path_prefix', '') + route[len(prefix):]
                declared = service['contract']; owner, contract_path = declared['repo_id'], declared['path']
                if owner not in graphs:
                    continue
                try:
                    captured = capture_file(Path(repos[owner]['_root']), contract_path, json_document=True)
                except (OSError, ValueError):
                    gap('VALUE_FLOW_CONTRACT_UNAVAILABLE', repo, path); continue
                document = captured['document']
                paths = document.get('paths')
                methods = paths.get(route) if isinstance(paths, dict) else None
                operation = methods.get(request['method'].lower()) if isinstance(methods, dict) else None
                if isinstance(operation, dict):
                    candidates.append((service, owner, contract_path, captured, operation, route))
            if len(candidates) != 1:
                gap('VALUE_FLOW_AMBIGUOUS_SERVICE', repo, path); continue
            service, owner, contract_path, captured, operation, route = candidates[0]
            specs = []
            responses = operation.get('responses')
            if not isinstance(responses, dict):
                gap('VALUE_FLOW_CONTRACT_FIELD_UNKNOWN', repo, path); continue
            for status, response in responses.items():
                if not str(status).startswith('2'):
                    continue
                response = _ref(captured['document'], response)
                schema = _ref(captured['document'], response.get('content', {}).get('application/json', {}).get('schema', {})) if isinstance(response, dict) else None
                if isinstance(schema, dict) and isinstance(schema.get('properties'), dict) and field in schema['properties']:
                    specs.append(schema['properties'][field])
            if not specs or any(spec != specs[0] for spec in specs) or not isinstance(specs[0], dict):
                gap('VALUE_FLOW_CONTRACT_FIELD_UNKNOWN', repo, path); continue
            spec = specs[0]; backend = service['backend_repo']; backend_graph = graphs.get(backend)
            origins = [s for s in (backend_graph.symbols if backend_graph else []) if s['id'] == spec.get('x-kgmaker-source')
                       and s.get('kind') in {'field', 'property'} and s.get('sha256') == spec.get('x-kgmaker-source-sha256')]
            current = current_contexts.get(backend, {})
            if len(origins) != 1 or origins[0].get('context_id') not in current:
                gap('VALUE_FLOW_BACKEND_FIELD_UNKNOWN', repo, path); continue
            valid = []
            for declaration in service.get('generated_clients', []):
                if declaration.get('repo_id') != repo or path not in declaration.get('consumers', []):
                    continue
                metadata_path = declaration['metadata_path']; generated_path = declaration['path']
                try:
                    metadata_capture = capture_file(Path(repos[repo]['_root']), metadata_path, json_document=True)
                    metadata = metadata_capture['document']
                    expected = {'repo_id': owner, 'path': contract_path, 'sha256': captured['raw_sha256']}
                    generated = capture_file(Path(repos[repo]['_root']), generated_path)
                    info = captured['document'].get('info')
                    release = info.get('version') if isinstance(info, dict) else None
                    if (generation_origin(metadata, expected, generated_path)[0] == 'VALID'
                            and isinstance(metadata.get('generated_sha256'), dict)
                            and metadata['generated_sha256'].get(generated_path) == generated['raw_sha256']
                            and isinstance(value.get('field_declaration'), dict)
                            and value['field_declaration'].get('path') == generated_path
                            and value['field_declaration'].get('sha256') == generated['source_sha256']
                            and isinstance(release, str) and metadata.get('release') == release):
                        valid.append({'metadata_path': source_key(repo, metadata_path), 'metadata_sha256': metadata_capture['raw_sha256'],
                                      'generated_path': source_key(repo, generated_path), 'generated_sha256': generated['raw_sha256'],
                                      'contract_sha256': captured['raw_sha256'], 'release': release,
                                      'trust': 'LOCAL_DECLARED'})
                except (OSError, ValueError, TypeError):
                    pass
            if len(valid) != 1:
                gap('VALUE_FLOW_GENERATION_OR_RELEASE_UNKNOWN', repo, path); continue
            origin = origins[0]
            context_ids = [qualified(backend, origin['context_id']), qualified(repo, value['context_id'])]
            field_id = 'workspace:service:' + service['id'] + ':endpoint:' + request['method'] + ':' + route + ':field:' + field
            details = {'generation': valid[0], 'request_call_site': qualified(repo, request['call_site']),
                       'consumer_occurrence': qualified(repo, value['id']), 'source_range': value['range']}
            link(qualified(backend, origin['id']), field_id, 'serialized_as', owner, contract_path, captured['raw_sha256'], context_ids, details)
            link(field_id, qualified(repo, value['id']), 'maps_to', owner, contract_path, captured['raw_sha256'], context_ids, details)
    return edges, evidence, sorted(set(diagnostics)), validated_contexts

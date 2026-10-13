"""Explicit local checkout federation with qualified IDs and coherent baselines."""
from __future__ import annotations

import copy
import subprocess
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote, unquote

from .analysis_model import AnalysisError, ID_PATTERN, digest, file_hash, read_json, safe_path
from .model import KnowledgeGraph

_REPO_CACHE = {}


def qualified(repo: str, identity: str) -> str:
    return 'repo:' + quote(repo, safe='') + ':' + quote(identity, safe='')


def split_id(identity: str) -> tuple[str, str]:
    parts = identity.split(':', 2)
    if len(parts) != 3 or parts[0] != 'repo':
        raise AnalysisError('Not a repo-qualified graph identity')
    result = unquote(parts[1]), unquote(parts[2])
    if qualified(*result) != identity:
        raise AnalysisError('Noncanonical repo-qualified identity')
    return result


def source_key(repo: str, path: str) -> str:
    return '@' + repo + '/' + path


def load_workspace(path: Path) -> dict:
    path = path.resolve()
    data = read_json(path)
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1 or not ID_PATTERN.fullmatch(str(data.get('workspace_id', '')))
            or not isinstance(data.get('repositories'), list)):
        raise AnalysisError('Invalid workspace manifest version/identity/repositories')
    if set(data) - {'schema_version', 'workspace_id', 'repositories', 'services', 'release_mapping'}:
        raise AnalysisError('Unknown workspace fields')
    roots, ids = [], set()
    for repo in data['repositories']:
        if not isinstance(repo, dict) or set(repo) - {'id', 'role', 'path', 'flyway', 'expected_remote', 'revision'}:
            raise AnalysisError('Invalid repository declaration')
        identity = repo.get('id')
        if not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity) or identity in ids:
            raise AnalysisError('Duplicate/invalid repo ID')
        if repo.get('role') not in {'backend', 'frontend', 'automated-tests', 'shared'} or not isinstance(repo.get('path'), str):
            raise AnalysisError('Repository requires a role and explicit local path')
        location = Path(repo['path'])
        if location.is_absolute() or ':' in repo['path']:
            raise AnalysisError('Repository paths must be local and relative to manifest')
        lexical = path.parent / location
        if any(p.is_symlink() for p in [lexical, *lexical.parents]):
            raise AnalysisError('Symlink repository roots are not supported')
        root = lexical.resolve()
        if any(root.is_relative_to(old) or old.is_relative_to(root) for old in roots):
            raise AnalysisError('Repository roots overlap')
        roots.append(root); ids.add(identity)
        repo['_root'] = str(root)
    services = data.get('services', [])
    if not isinstance(services, list):
        raise AnalysisError('services must be an array')
    service_ids = set()
    for service in services:
        if not isinstance(service, dict) or not ID_PATTERN.fullmatch(str(service.get('id', ''))) or service['id'] in service_ids:
            raise AnalysisError('Duplicate/invalid service ID')
        service_ids.add(service['id'])
        if set(service) - {'id', 'backend_repo', 'frontend_repos', 'test_repos', 'contract',
                           'consumer_path_prefix', 'provider_path_prefix', 'generated_clients'}:
            raise AnalysisError('Unknown service configuration')
        if service.get('backend_repo') not in ids:
            raise AnalysisError('Service backend_repo is not declared')
        for key in ('frontend_repos', 'test_repos'):
            values = service.get(key, [])
            if not isinstance(values, list) or any(v not in ids for v in values):
                raise AnalysisError('Service consumers must refer to declared repository IDs')
        contract = service.get('contract')
        if not isinstance(contract, dict) or set(contract) != {'repo_id', 'path'} or contract['repo_id'] not in ids:
            raise AnalysisError('Service requires an explicit repo/path contract')
        safe_path(Path(next(r['_root'] for r in data['repositories'] if r['id'] == contract['repo_id'])), contract['path'])
        for key in ('consumer_path_prefix', 'provider_path_prefix'):
            prefix = service.get(key, '')
            if not isinstance(prefix, str) or prefix and not prefix.startswith('/'):
                raise AnalysisError('HTTP prefix must be empty or start with /')
    data['_manifest_path'] = str(path)
    data['_manifest_hash'] = file_hash(path)
    return data


def source_path(packet: dict, key: str) -> Path:
    item = packet['source_manifest'].get(key)
    if not item or 'repo_id' not in item:
        raise AnalysisError('Unknown qualified evidence source')
    roots = packet['workspace']['roots']
    if item['repo_id'] not in roots:
        raise AnalysisError('Evidence repo is outside workspace roots')
    return safe_path(Path(roots[item['repo_id']]), item['path'])


def snapshot_workspace(manifest: Path, *, cache_root: Path | None = None, persist_cache: bool = False) -> tuple[dict, dict, dict, KnowledgeGraph, dict]:
    from . import feature
    from .schema_replay import reconstruct
    from .test_analysis import federated_links
    workspace = load_workspace(manifest)
    baseline_repos, sources, exclusions, nodes, edges, graphs, schemas = {}, {}, [], [], [], {}, {}
    diagnostics, pending, before = [], [], {}
    parsed = []
    pending_cache = {}
    for repo in workspace['repositories']:
        identity, root = repo['id'], Path(repo['_root'])
        if not root.is_dir():
            diagnostics.append('Missing checkout: ' + identity); pending.append('Missing checkout: ' + identity)
            baseline_repos[identity] = {'status': 'MISSING'}; continue
        inventory, excluded = feature.source_inventory(root)
        before[identity] = inventory
        semantic = root / '.kgmaker/semantic.json'
        from .classification import Classifier
        classification = Classifier(root).fingerprint
        key = digest({'root': str(root), 'sources': inventory, 'classification': classification, 'flyway': repo.get('flyway'),
                      'parser_versions': ['workspace-1', feature.PARSER_VERSION, 'flyway-offline-1', 'postgres-ddl-1', 'dataflow-1'],
                      'semantic': file_hash(semantic) if semantic.is_file() else None})
        try:
            commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        if repo.get('revision') and commit != repo['revision']:
            pending.append('Declared revision mismatch: ' + identity)
        if repo.get('expected_remote'):
            actual = subprocess.run(['git', '-C', str(root), 'config', '--get', 'remote.origin.url'], capture_output=True, text=True).stdout.strip()
            if actual != repo['expected_remote']:
                raise AnalysisError('Checkout remote identity mismatch: ' + identity)
        disk = safe_path(cache_root, f'.kgmaker/workspace-cache/{key}.json') if cache_root is not None else None
        if key not in _REPO_CACHE and disk is not None and disk.is_file():
            try:
                cached = read_json(disk)
                if cached['schema_version'] == 1 and cached['cache_key'] == key and digest(cached['payload']) == cached['payload_hash']:
                    _REPO_CACHE[key] = (KnowledgeGraph.from_dict(cached['payload']['graph']), cached['payload']['schemas'])
            except (AnalysisError, KeyError, TypeError, ValueError, OSError):
                pass  # corrupted cache is a cache miss, not evidence
        if key in _REPO_CACHE:
            local, local_schema = copy.deepcopy(_REPO_CACHE[key])
        else:
            local, _, error = feature.current_graph(root)
            local_schema = None
            if repo.get('flyway'):
                configs = repo['flyway'] if isinstance(repo['flyway'], list) else [repo['flyway']]
                local_schema = [reconstruct(root, cfg) for cfg in configs]
                if len({s['config']['stream_id'] for s in local_schema}) != len(local_schema):
                    raise AnalysisError('Duplicate migration-stream ID: ' + identity)
                for schema in local_schema:
                    local = feature.attach_schema(local, schema, root)
                    from .schema_replay import schema_mappings
                    _, schema['mapping_diagnostics'] = schema_mappings(root, schema, local)
                    schema.pop('checkpoints', None)  # execution/cache statistics are not baseline identity
            if error:
                diagnostics.append(identity + ': ' + error)
            pending_cache[key] = copy.deepcopy((local, local_schema)); parsed.append(identity)
        graphs[identity] = local
        if local_schema is not None:
            schemas[identity] = local_schema
            for schema in local_schema:
                pending += [identity + ': ' + d for d in schema['diagnostics']]
                pending += [identity + ': ' + d['reason'] for d in schema.get('mapping_diagnostics', [])]
        baseline_repos[identity] = {'status': 'PRESENT', 'git_commit': commit,
                                    'working_tree_fingerprint': digest(inventory), 'cache_key': key}
        for path, item in inventory.items():
            sources[source_key(identity, path)] = {**item, 'repo_id': identity, 'path': path}
        exclusions += [{'repo_id': identity, **item} for item in excluded]
        nodes += [replace(n, id=qualified(identity, n.id), path=source_key(identity, n.path)) for n in local.nodes]
        edges += [replace(e, source=qualified(identity, e.source), target=qualified(identity, e.target),
                          context_ids=tuple(qualified(identity, c) for c in e.context_ids),
                          evidence_ids=tuple(qualified(identity, c) for c in e.evidence_ids),
                          source_file=source_key(identity, e.source_file) if e.source_file else None) for e in local.edges]
    link_nodes, link_edges, link_diagnostics = federated_links(workspace, graphs, sources)
    nodes += link_nodes; edges += link_edges; diagnostics += link_diagnostics
    from .test_analysis import test_data_diagnostics
    diagnostics += test_data_diagnostics(workspace, sources, schemas)
    for repo in workspace['repositories']:
        identity, root = repo['id'], Path(repo['_root'])
        if identity in before:
            after, _ = feature.source_inventory(root)
            if after != before[identity]:
                raise AnalysisError('Sources changed during workspace snapshot: ' + identity, 3)
        elif root.is_dir():
            raise AnalysisError('Checkout appeared during workspace snapshot: ' + identity, 3)
    if file_hash(manifest) != workspace['_manifest_hash']:
        raise AnalysisError('Manifest changed during workspace snapshot', 3)
    _REPO_CACHE.update(pending_cache)
    if persist_cache and cache_root is not None:
        from .analysis_model import write_json
        for key, (local, local_schema) in pending_cache.items():
            payload = {'graph': local.to_dict(), 'schemas': local_schema}
            write_json(safe_path(cache_root, f'.kgmaker/workspace-cache/{key}.json'),
                       {'schema_version': 1, 'cache_key': key, 'payload': payload, 'payload_hash': digest(payload)})
    graph = KnowledgeGraph(2, '.', '', sorted(nodes, key=lambda n: n.id),
                           sorted(set(edges), key=lambda e: (e.source, e.kind, e.target)),
                           {k: v['sha256'] for k, v in sources.items()},
                           [{**context, 'repo_id': repo, 'id': qualified(repo, context['id'])}
                            for repo, local in graphs.items() for context in local.contexts if 'id' in context],
                           [{'repo_id': repo, **d} for repo, local in graphs.items() for d in local.diagnostics],
                           [{**e, 'repo_id': repo, 'id': qualified(repo, e['id']),
                             'source': qualified(repo, e['source']), 'target': qualified(repo, e['target']),
                             'source_file': source_key(repo, e['source_file']) if e.get('source_file') else None,
                             'context_ids': [qualified(repo, c) for c in e.get('context_ids', [])]}
                            for repo, local in graphs.items() for e in local.evidence])
    graph.files['@workspace/manifest.json'] = workspace['_manifest_hash']
    baseline = {'git_commit': None, 'graph_fingerprint': digest(graph.to_dict()),
                'working_tree_fingerprint': digest(sources), 'parser_version': 'workspace-1',
                'semantic_hash': None, 'manifest_hash': workspace['_manifest_hash'], 'repositories': baseline_repos}
    coverage = {'roots': [r['id'] for r in workspace['repositories']], 'artifacts': sorted(sources),
                'exclusions': exclusions, 'excluded_directories': [], 'dataflow_diagnostics': [],
                'unsupported_sources': sorted(k for k, v in sources.items() if not v['supported']),
                'parser_capabilities': {'workspace': 1, 'schema_replay': 1, 'local_checkout_only': True},
                'limitations': ['No deployment compatibility is established without an explicit release mapping.',
                                'Static test assertions do not establish runtime PASS/FAIL.'] + diagnostics,
                'pending': pending + diagnostics, 'repositories': copy.deepcopy(baseline_repos), 'schemas': schemas}
    metadata = {'manifest_path': str(manifest.resolve()), 'manifest_hash': workspace['_manifest_hash'],
                'workspace_id': workspace['workspace_id'], 'roots': {r['id']: r['_root'] for r in workspace['repositories']},
                'release_mapping': workspace.get('release_mapping')}
    return baseline, coverage, sources, graph, metadata

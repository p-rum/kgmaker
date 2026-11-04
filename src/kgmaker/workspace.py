"""Explicit local checkout federation with qualified IDs and coherent baselines."""
from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
import subprocess
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote, unquote

from .analysis_model import AnalysisError, ID_PATTERN, digest, file_hash, read_json, safe_path
from .model import Edge, KnowledgeGraph, Node

_REPO_CACHE = {}
_CONTENT_HASH = re.compile(r'[0-9a-f]{64}\Z')


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


def _qualified_http_metadata(repo: str, value: dict) -> dict:
    """Qualify identities and locators, preserving URI paths as URI paths."""
    result = copy.deepcopy(value)
    for key in ('context_id', 'caller', 'origin_call_site', 'root_call_site', 'declaration', 'client_type'):
        if isinstance(result.get(key), str):
            result[key] = qualified(repo, result[key])
    for key in ('terminal_call_site_ids', 'chain_call_site_ids'):
        if key in result:
            result[key] = [qualified(repo, item) for item in result[key]]
    for record in result.get('uri_provenance', []):
        if record.get('source_file'):
            record['source_file'] = source_key(repo, record['source_file'])
    result['repo_id'] = repo
    return result


def _qualified_kafka_metadata(repo: str, value: dict) -> dict:
    """Qualify code identities; preserve the exact original capture IDs explicitly."""
    result = copy.deepcopy(value)
    for key in ('origin_id', 'logical_id', 'context_id', 'call_site', 'caller', 'declared_target', 'argument_id', 'parameter_id'):
        if isinstance(value.get(key), str):
            result['original_' + key] = value[key]
            result[key] = qualified(repo, value[key])
    if isinstance(value.get('source_file'), str):
        result['original_source_file'] = value['source_file']
        result['source_file'] = source_key(repo, value['source_file'])
    result['repo_id'] = repo
    return result


def _qualified_context(repo: str, value: dict, *, redact_kafka_properties=False) -> dict:
    if redact_kafka_properties:
        from .kafka_bindings import project_captured_context
        result = project_captured_context(value)
    else:
        result = copy.deepcopy(value)
    result['id'] = qualified(repo, value['id'])
    if isinstance(result.get('source_files'), dict):
        result['source_files'] = {source_key(repo, path): checksum
                                  for path, checksum in result['source_files'].items()}
    return result


def validate_projected_context(root: Path, repo: str, public_context: dict) -> None:
    """Validate a public redacted view against its private saved authority."""
    from .store import load_graph
    from .graph_provider import _selection_key, validate_context_snapshot
    from .worker_protocol import WorkerError

    def stale():
        return WorkerError("STALE_INDEX: redacted context requires its matching valid original; inspect again", "STALE")

    projection = public_context.get('spring_properties_projection')
    if (not isinstance(projection, dict)
            or set(projection) != {'redacted', 'sha256', 'original_context_id'}
            or projection['redacted'] is not True
            or not isinstance(projection['sha256'], str) or not _CONTENT_HASH.fullmatch(projection['sha256'])
            or not isinstance(projection['original_context_id'], str)):
        raise stale()
    stored = load_graph(root)
    matches = [context for context in stored.contexts if context.get('id') == projection['original_context_id']] if stored else []
    if len(matches) != 1 or not matches[0].get('analyzer_version'):
        raise stale()
    original = matches[0]
    expected = {**_qualified_context(repo, original, redact_kafka_properties=True), 'repo_id': repo}
    # Compare the complete projection, not just caller-supplied marker hashes.
    if expected != public_context:
        raise stale()
    recorded = original.get('selection_key')
    recomputed = _selection_key({key: value for key, value in original.items() if key != 'selection_key'})
    if not isinstance(recorded, str) or _selection_key(original) != recomputed:
        raise stale()
    try:
        validate_context_snapshot(root, original)
    except (ValueError, OSError):
        raise stale() from None


def _qualified_symbol(repo: str, value: dict) -> dict:
    result = copy.deepcopy(value)
    result['id'] = qualified(repo, value['id'])
    for key in ('method', 'owner_method', 'call_site', 'declared_target', 'binding_id'):
        if isinstance(value.get(key), str):
            result[key] = qualified(repo, value[key])
    result['context_id'] = qualified(repo, value['context_id'])
    if isinstance(value.get('path'), str):
        result['path'] = source_key(repo, value['path'])
    if isinstance(result.get('projection'), dict) and isinstance(result['projection'].get('component_target'), str):
        result['projection']['component_target'] = qualified(repo, result['projection']['component_target'])
    return result


def _qualified_evidence(repo: str, value: dict) -> dict:
    result = copy.deepcopy(value)
    result.update(repo_id=repo, id=qualified(repo, value['id']),
                  source=qualified(repo, value['source']), target=qualified(repo, value['target']),
                  source_file=source_key(repo, value['source_file']) if value.get('source_file') else None,
                  context_ids=[qualified(repo, item) for item in value.get('context_ids', [])])
    for key in ('call_site', 'producer_call_site', 'consumer_call_site', 'declared_target'):
        if isinstance(value.get(key), str):
            result[key] = qualified(repo, value[key])
    if isinstance(result.get('projection'), dict) and isinstance(result['projection'].get('component_target'), str):
        result['projection']['component_target'] = qualified(repo, result['projection']['component_target'])
    if str(value.get('extractor', '')).startswith('kafka-code-'):
        if isinstance(value.get('origin_id'), str):
            result['original_origin_id'] = value['origin_id']
            result['origin_id'] = qualified(repo, value['origin_id'])
        result['compiler_evidence_ids'] = [qualified(repo, item) for item in value.get('compiler_evidence_ids', [])]
    if type(value.get('local_operation_version')) is int and value['local_operation_version'] == 1:
        for key in ('method', 'compiler_symbol_id', 'cfg_block', 'target_binding', 'context_id'):
            if isinstance(value.get(key), str):
                result[key] = qualified(repo, value[key])
        if isinstance(result.get('target_declaration'), dict):
            result['target_declaration']['path'] = source_key(repo, result['target_declaration']['path'])
    return result


def _qualified_call_site(repo: str, value: dict) -> dict:
    result = copy.deepcopy(value)
    for key in ('id', 'caller', 'declared_target', 'omitted_declared_target'):
        if isinstance(value.get(key), str):
            result[key] = qualified(repo, value[key])
    result['context_id'] = qualified(repo, value['context_id'])
    result['dispatch_candidates'] = [qualified(repo, item)
                                     for item in value.get('dispatch_candidates', [])]
    result['evidence_ids'] = [qualified(repo, item) for item in value.get('evidence_ids', [])]
    if isinstance(value.get('path'), str):
        result['path'] = source_key(repo, value['path'])
    return result


def _qualified_cfg(repo: str, value: dict) -> dict:
    result = copy.deepcopy(value)
    result['method'] = qualified(repo, value['method'])
    result['context_id'] = qualified(repo, value['context_id'])
    result['evidence_ids'] = [qualified(repo, item) for item in value.get('evidence_ids', [])]
    block_ids = {block['id']: qualified(repo, block['id']) for block in value.get('blocks', [])}
    for key in ('entry', 'exit', 'exceptional_exit'):
        if isinstance(value.get(key), str):
            result[key] = block_ids[value[key]]
    result['blocks'] = []
    for block in value.get('blocks', []):
        item = copy.deepcopy(block)
        item['id'] = block_ids[block['id']]
        item['call_site_ids'] = [qualified(repo, identity)
                                 for identity in block.get('call_site_ids', [])]
        item['original_ids'] = [qualified(repo, identity)
                                for identity in block.get('original_ids', [])]
        if type(block.get('local_operation_version')) is int and block['local_operation_version'] == 1:
            item['local_operation_evidence_ids'] = [qualified(repo, identity)
                for identity in block.get('local_operation_evidence_ids', [])]
        if isinstance(block.get('source_file'), str):
            item['source_file'] = source_key(repo, block['source_file'])
        result['blocks'].append(item)
    result['edges'] = [{**copy.deepcopy(edge),
                        'source': block_ids[edge['source']],
                        'target': block_ids[edge['target']]}
                       for edge in value.get('edges', [])]
    result['diagnostics'] = [
        {**copy.deepcopy(item),
         **({'source_file': source_key(repo, item['source_file'])}
            if isinstance(item.get('source_file'), str) else {})}
        for item in value.get('diagnostics', [])]
    return result


def _qualified_annotation(repo: str, value: dict) -> dict:
    result = copy.deepcopy(value)
    result['id'] = qualified(repo, value['id'])
    result['target_ids'] = [qualified(repo, item) for item in value.get('target_ids', [])]
    result['evidence_ids'] = [qualified(repo, item) for item in value.get('evidence_ids', [])]
    return result


def _validate_release_mapping(data: dict, repo_ids: set[str]) -> None:
    release = data.get('release_mapping')
    if release is None:
        return
    if (not isinstance(release, dict) or set(release) != {'schema_version', 'mappings'}
            or type(release.get('schema_version')) is not int or release['schema_version'] != 1
            or not isinstance(release.get('mappings'), list) or not release['mappings']):
        raise AnalysisError('Invalid release mapping contract; expected schema_version 1 and mappings')
    mapping_ids = set()
    roots = {repo['id']: Path(repo['_root']) for repo in data['repositories']}
    for mapping in release['mappings']:
        if (not isinstance(mapping, dict)
                or set(mapping) != {'id', 'producer', 'consumer', 'output_sha256'}):
            raise AnalysisError('Invalid release mapping entry')
        identity = mapping.get('id')
        if (not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity)
                or identity in mapping_ids):
            raise AnalysisError('Duplicate/invalid release mapping ID')
        mapping_ids.add(identity)
        producer, consumer = mapping.get('producer'), mapping.get('consumer')
        if (not isinstance(producer, dict)
                or set(producer) != {'repo_id', 'manifest_path', 'context_id'}
                or not isinstance(consumer, dict)
                or set(consumer) != {'repo_id', 'context_id'}):
            raise AnalysisError('Invalid release mapping producer/consumer selector')
        if (producer.get('repo_id') not in repo_ids or consumer.get('repo_id') not in repo_ids
                or producer['repo_id'] == consumer['repo_id']):
            raise AnalysisError('Cross-repo release mapping requires distinct declared repositories')
        if (not isinstance(producer.get('context_id'), str) or not producer['context_id']
                or not isinstance(consumer.get('context_id'), str) or not consumer['context_id']):
            raise AnalysisError('Invalid release mapping context selector')
        safe_path(roots[producer['repo_id']], producer.get('manifest_path'))
        if not isinstance(mapping.get('output_sha256'), str) or not _CONTENT_HASH.fullmatch(mapping['output_sha256']):
            raise AnalysisError('Invalid release mapping output_sha256')


def load_workspace(path: Path) -> dict:
    path = path.resolve()
    data = read_json(path)
    if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
            or data['schema_version'] != 1 or not ID_PATTERN.fullmatch(str(data.get('workspace_id', '')))
            or not isinstance(data.get('repositories'), list)):
        raise AnalysisError('Invalid workspace manifest version/identity/repositories')
    if set(data) - {'schema_version', 'workspace_id', 'repositories', 'services', 'release_mapping',
                    'service_ownership', 'kafka_bindings'}:
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
                           'consumer_path_prefix', 'provider_path_prefix', 'generated_clients', 'transport'}:
            raise AnalysisError('Unknown service configuration')
        transport = service.get('transport')
        if transport is not None and (not isinstance(transport, str) or transport not in {'http', 'kafka'}):
            raise AnalysisError('Unsupported service transport declaration')
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
    _validate_service_ownership(data.get('service_ownership'), data['repositories'], service_ids)
    _validate_release_mapping(data, ids)
    from .kafka_bindings import validate as validate_kafka_bindings
    validate_kafka_bindings(data)
    data['_manifest_path'] = str(path)
    data['_manifest_hash'] = file_hash(path)
    return data


def _validate_service_ownership(declaration: dict | None, repositories: list[dict],
                                legacy_service_ids: set[str]) -> None:
    """Validate explicit ownership without changing the legacy service mapping contract."""
    if declaration is None:
        return
    from .analysis_model import ID_PATTERN
    if (not isinstance(declaration, dict) or set(declaration) != {'schema_version', 'services'}
            or type(declaration.get('schema_version')) is not int
            or declaration['schema_version'] != 1 or not isinstance(declaration.get('services'), list)):
        raise AnalysisError('Invalid service_ownership; expected schema_version 1 and services')
    repo_roots = {repo['id']: Path(repo['_root']) for repo in repositories}
    ids = set()
    for service in declaration['services']:
        if (not isinstance(service, dict)
                or set(service) != {'id', 'roots', 'modules', 'external_systems'}
                or not isinstance(service.get('id'), str)
                or not ID_PATTERN.fullmatch(service['id'])
                or service['id'] in ids or service['id'] not in legacy_service_ids):
            raise AnalysisError('Invalid, duplicate, or undeclared service ownership ID')
        ids.add(service['id'])
        roots, modules, systems = service['roots'], service['modules'], service['external_systems']
        if not isinstance(roots, list) or not isinstance(modules, list) or not isinstance(systems, list):
            raise AnalysisError('Service ownership roots/modules/external_systems must be arrays')
        if not roots and not modules:
            raise AnalysisError('Service ownership requires at least one explicit root or module')
        seen_roots, seen_modules, seen_systems = set(), set(), set()
        for root in roots:
            if (not isinstance(root, dict) or set(root) != {'repo_id', 'path'}
                    or root.get('repo_id') not in repo_roots):
                raise AnalysisError('Invalid service ownership root')
            safe_path(repo_roots[root['repo_id']], root.get('path'))
            key = (root['repo_id'], Path(root['path']).as_posix().rstrip('/'))
            if key in seen_roots:
                raise AnalysisError('Duplicate service ownership root')
            seen_roots.add(key)
        for module in modules:
            if (not isinstance(module, dict) or set(module) != {'repo_id', 'id'}
                    or module.get('repo_id') not in repo_roots
                    or not isinstance(module.get('id'), str) or not module['id'].strip()):
                raise AnalysisError('Invalid service ownership module; expected repo_id and id')
            key = (module['repo_id'], module['id'])
            if key in seen_modules:
                raise AnalysisError('Duplicate service ownership module')
            seen_modules.add(key)
        for system in systems:
            if (not isinstance(system, dict) or set(system) != {'id'}
                    or not isinstance(system.get('id'), str) or not ID_PATTERN.fullmatch(system['id'])
                    or system['id'] in seen_systems):
                raise AnalysisError('Invalid or duplicate external system identity')
            seen_systems.add(system['id'])


def resolve_service_ownership(symbol: dict, declaration: dict | None, *, context_id: str) -> dict:
    """Resolve only explicit root/module declarations for one supplied symbol context.

    A declaration can match by repo-qualified path root or exact module name. Multiple
    declarations remain AMBIGUOUS and no match remains UNASSIGNED.
    """
    if not isinstance(context_id, str) or not context_id:
        raise AnalysisError('Ownership resolution requires an explicit context_id')
    if (not isinstance(symbol, dict) or not isinstance(symbol.get('repo_id'), str)
            or symbol.get('context_id') != context_id):
        raise AnalysisError('Ownership symbol requires matching repo_id and context_id')
    context_repo = split_id(context_id)[0] if context_id.startswith('repo:') else None
    if context_repo is not None and context_repo != symbol['repo_id']:
        raise AnalysisError('Ownership context belongs to a different repository')
    if declaration is not None and (
            not isinstance(declaration, dict)
            or type(declaration.get('schema_version')) is not int
            or declaration.get('schema_version') != 1
            or set(declaration) != {'schema_version', 'services'}
            or not isinstance(declaration.get('services'), list)):
        raise AnalysisError('Unsupported or invalid service ownership declaration')
    path, module = symbol.get('path'), symbol.get('module')
    if isinstance(path, str) and path.startswith('@'):
        prefix, separator, path = path[1:].partition('/')
        if not separator or prefix != symbol['repo_id'] or not path:
            raise AnalysisError('Qualified ownership path must match symbol repo_id')
        if source_key(prefix, path) != symbol['path']:
            raise AnalysisError('Qualified ownership path is not canonical')
    if path is not None and (not isinstance(path, str) or not path or Path(path).is_absolute()
                             or '\\' in path or ':' in path or '..' in Path(path).parts):
        raise AnalysisError('Ownership symbol path must be repository-relative')
    owners = []
    for service in (declaration or {}).get('services', []):
        path_match = False
        if isinstance(path, str):
            for root in service['roots']:
                if root['repo_id'] == symbol['repo_id']:
                    base = Path(root['path']).as_posix().rstrip('/')
                    if base == '.':
                        base = ''
                    candidate = Path(path).as_posix()
                    if not base or candidate == base or candidate.startswith(base + '/'):
                        path_match = True
                        break
        module_match = (isinstance(module, str) and any(
            item['repo_id'] == symbol['repo_id'] and item['id'] == module
            for item in service['modules']))
        if path_match or module_match:
            owners.append(service)
    owners.sort(key=lambda item: item['id'])
    status = 'UNASSIGNED' if not owners else 'RESOLVED' if len(owners) == 1 else 'AMBIGUOUS'
    return {'status': status, 'owner_id': owners[0]['id'] if len(owners) == 1 else None,
            'candidate_owner_ids': [item['id'] for item in owners], 'context_id': context_id,
            'external_system_ids': ([system['id'] for system in owners[0]['external_systems']]
                                    if len(owners) == 1 else [])}


def _release_artifact_links(workspace: dict, graphs: dict[str, KnowledgeGraph]):
    """Resolve declared cross-repo build outputs without executing any project."""
    release = workspace.get('release_mapping')
    if release is None:
        return [], [], [], [], None
    from .build_model import resolve_content_bound_output
    from .graph_provider import resolve_context_classpath_artifact
    from .worker_protocol import WorkerError

    roots = {repo['id']: Path(repo['_root']) for repo in workspace['repositories']}
    nodes, edges, evidence, diagnostics, results = [], [], [], [], []
    for mapping in release['mappings']:
        producer, consumer = mapping['producer'], mapping['consumer']
        result = {'id': mapping['id'], 'producer_repo': producer['repo_id'],
                  'consumer_repo': consumer['repo_id'], 'sha256': mapping['output_sha256']}
        try:
            manifest_path = safe_path(roots[producer['repo_id']], producer['manifest_path'])
            if not manifest_path.is_file():
                raise AnalysisError('RELEASE_MANIFEST_UNAVAILABLE: ' + producer['manifest_path'], 3)
            manifest_hash = file_hash(manifest_path)
            manifest_data = read_json(manifest_path)
            if file_hash(manifest_path) != manifest_hash:
                raise AnalysisError('RELEASE_MANIFEST_CHANGED_DURING_SNAPSHOT: '
                                    + producer['manifest_path'], 3)
            output = resolve_content_bound_output(
                roots[producer['repo_id']], manifest_data,
                context_id=producer['context_id'], sha256=mapping['output_sha256'],
            )
            contexts = [item for item in graphs[consumer['repo_id']].contexts
                        if item.get('id') == consumer['context_id']]
            if not contexts:
                raise AnalysisError('RELEASE_CONSUMER_CONTEXT_UNAVAILABLE: '
                                    + consumer['context_id'], 3)
            if len(contexts) != 1:
                raise AnalysisError('RELEASE_CONSUMER_CONTEXT_AMBIGUOUS: '
                                    + consumer['context_id'], 3)
            classpath = resolve_context_classpath_artifact(
                roots[consumer['repo_id']], contexts[0], mapping['output_sha256'])
        except (AnalysisError, WorkerError, OSError, ValueError) as error:
            message = str(error)
            code = ('RELEASE_CONSUMER_CONTEXT_STALE' if isinstance(error, WorkerError)
                    else message.split(':', 1)[0])
            if not code.startswith('RELEASE_'):
                code = 'RELEASE_MAPPING_INVALID'
            diagnostic = {'code': code, 'mapping_id': mapping['id'], 'reason': message,
                          'status': 'PARTIAL'}
            diagnostics.append(diagnostic)
            results.append({**result, 'status': 'PARTIAL', 'diagnostic': code})
            continue

        output_id = 'workspace:release-output:' + mapping['id']
        classpath_id = 'workspace:classpath-artifact:' + mapping['id']
        evidence_id = 'workspace:evidence:release-output:' + mapping['id']
        producer_source = source_key(producer['repo_id'], producer['manifest_path'])
        classpath_path = Path(classpath['path'])
        try:
            consumer_path = source_key(
                consumer['repo_id'],
                classpath_path.resolve().relative_to(roots[consumer['repo_id']]).as_posix(),
            )
        except ValueError:
            consumer_path = '@workspace/manifest.json'
        nodes.extend([
            Node(output_id, 'workspace_release_output', mapping['id'], producer_source,
                 scope='production', role='resource', origin='generated',
                 metadata={'repo_id': producer['repo_id'], 'build_context_id': producer['context_id'],
                           'sha256': output['sha256']}),
            Node(classpath_id, 'workspace_classpath_artifact', mapping['id'], consumer_path,
                 scope='production', role='resource', origin='dependency',
                 metadata={'repo_id': consumer['repo_id'], 'compiler_context_id': consumer['context_id'],
                           'sha256': classpath['sha256']}),
        ])
        evidence.append({
            'id': evidence_id, 'kind': 'SYMBOL_RESOLVED',
            'method': 'CONTENT_HASH_MATCH_V1', 'sha256': mapping['output_sha256'],
            'source': output_id, 'target': classpath_id,
            'source_file': producer_source,
            'context_ids': [qualified(consumer['repo_id'], consumer['context_id'])],
        })
        edges.append(Edge(
            output_id, classpath_id, 'supplies_classpath',
            evidence='BuildManifest output and compiler classpath contain identical bytes.',
            confidence='CONTENT_VERIFIED', confidence_score=1.0,
            source_file='@workspace/manifest.json', evidence_kind='SYMBOL_RESOLVED',
            context_ids=(qualified(consumer['repo_id'], consumer['context_id']),),
            evidence_ids=(evidence_id,),
        ))
        results.append({**result, 'status': 'CONTENT_VERIFIED',
                        'manifest_sha256': manifest_hash,
                        'producer_output_path': output['path'],
                        'consumer_classpath_path': classpath['path']})
    report = {'schema_version': 1,
              'status': 'COMPLETE' if not diagnostics else 'PARTIAL',
              'mappings': results, 'diagnostics': diagnostics}
    return nodes, edges, evidence, diagnostics, report


def _regular_file_hash(path: Path) -> str | None:
    """Hash one unchanged regular file without following a swapped symlink."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        return None
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            return None
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(65536), b''):
            checksum.update(chunk)
        read = os.fstat(stream.fileno())
    after = path.lstat()
    snapshots = (before, opened, read, after)
    if any(not stat.S_ISREG(item.st_mode) for item in snapshots):
        return None
    identity = {(item.st_dev, item.st_ino) for item in snapshots}
    content_state = {(item.st_size, item.st_mtime_ns) for item in snapshots}
    if len(identity) != 1 or len(content_state) != 1:
        return None
    return checksum.hexdigest()


def _validate_release_artifact_snapshot(workspace: dict, report: dict | None) -> None:
    """Recheck every mapped byte source before publishing/cache mutation."""
    if report is None:
        return
    roots = {repo['id']: Path(repo['_root']) for repo in workspace['repositories']}
    declarations = {item['id']: item for item in workspace['release_mapping']['mappings']}
    for result in report['mappings']:
        if result['status'] != 'CONTENT_VERIFIED':
            continue
        declaration = declarations[result['id']]
        producer = declaration['producer']
        manifest = safe_path(roots[producer['repo_id']], producer['manifest_path'])
        output = Path(result['producer_output_path'])
        if not output.is_absolute():
            output = safe_path(roots[producer['repo_id']], result['producer_output_path'])
        classpath = Path(result['consumer_classpath_path'])
        if not classpath.is_absolute():
            classpath = safe_path(
                roots[declaration['consumer']['repo_id']], result['consumer_classpath_path'])
        try:
            current = (_regular_file_hash(manifest) == result['manifest_sha256']
                       and _regular_file_hash(output) == result['sha256']
                       and _regular_file_hash(classpath) == result['sha256'])
        except (AnalysisError, OSError, ValueError):
            current = False
        if not current:
            raise AnalysisError('RELEASE_ARTIFACT_CHANGED_DURING_SNAPSHOT: ' + result['id'], 3)


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
    from .schema_replay import reconstruct, PARSER_VERSION as SCHEMA_PARSER_VERSION
    from .domain import HTTP_CAPTURE_VERSION
    from .test_analysis import federated_links
    from .kafka_bindings import VERSION as kafka_binding_version
    workspace = load_workspace(manifest)
    baseline_repos, sources, exclusions, nodes, edges, graphs, schemas = {}, {}, [], [], [], {}, {}
    symbols, call_sites, cfgs, annotations = [], [], [], []
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
                      'parser_versions': ['workspace-1', feature.PARSER_VERSION, feature.WORKBOOK_VERSION,
                                          'flyway-offline-1', SCHEMA_PARSER_VERSION, 'dataflow-1', HTTP_CAPTURE_VERSION, kafka_binding_version],
                      'compiler_index': file_hash(root / '.kgmaker/graph.json') if (root / '.kgmaker/graph.json').is_file() else None,
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
                    pending_cache[key] = (KnowledgeGraph.from_dict(cached['payload']['graph']), cached['payload']['schemas'])
            except (AnalysisError, KeyError, TypeError, ValueError, OSError):
                pass  # corrupted cache is a cache miss, not evidence
        if key in _REPO_CACHE:
            local, local_schema = copy.deepcopy(_REPO_CACHE[key])
        elif key in pending_cache:
            local, local_schema = copy.deepcopy(pending_cache[key])
        else:
            local, _, error = feature.current_graph(root)
            local_schema = None
            if repo.get('flyway'):
                configs = repo['flyway'] if isinstance(repo['flyway'], list) else [repo['flyway']]
                from .flyway import configuration
                from .schema_replay import persistence_pair
                pairs = [persistence_pair(c['database_id'], c['stream_id']) for c in
                         (configuration(root, cfg) for cfg in configs)]
                if None in pairs or len(set(pairs)) != len(pairs):
                    raise AnalysisError('Duplicate migration-stream ID or invalid persistence realm: ' + identity)
                local_schema = [reconstruct(root, cfg) for cfg in configs]
                for schema in local_schema:
                    local = feature.attach_schema(local, schema, root)
                    from .schema_replay import schema_mappings
                    _, schema['mapping_diagnostics'] = schema_mappings(root, schema, local)
                    schema.pop('checkpoints', None)  # execution/cache statistics are not baseline identity
                # Explicit offline replay can join existing fresh compiler facts;
                # this does not inspect, build, install or execute a repository.
                from .framework import augment_framework_graph
                for selected in list(local.contexts):
                    if selected.get('language') == 'jvm' and selected.get('freshness') != 'STALE':
                        local = augment_framework_graph(root, local, selected)
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
        nodes += [replace(n, id=qualified(identity, n.id), path=source_key(identity, n.path),
                          metadata=_qualified_http_metadata(identity, n.metadata or {}) if n.kind == "http_request_definition"
                          else _qualified_symbol(identity, n.metadata) if (n.metadata or {}).get("return_mapping_version") == 1
                          else _qualified_kafka_metadata(identity, n.metadata or {}) if n.kind in {"kafka_code_listener", "kafka_code_producer"}
                          else n.metadata) for n in local.nodes]
        edges += [replace(e, source=qualified(identity, e.source), target=qualified(identity, e.target),
                          context_ids=tuple(qualified(identity, c) for c in e.context_ids),
                          evidence_ids=tuple(qualified(identity, c) for c in e.evidence_ids),
                          source_file=source_key(identity, e.source_file) if e.source_file else None) for e in local.edges]
        symbols += [_qualified_symbol(identity, item) for item in local.symbols]
        call_sites += [_qualified_call_site(identity, item) for item in local.call_sites]
        cfgs += [_qualified_cfg(identity, item) for item in local.cfgs]
        annotations += [_qualified_annotation(identity, item) for item in local.analysis_annotations]
    link_nodes, link_edges, link_diagnostics = federated_links(workspace, graphs, sources)
    nodes += link_nodes; edges += link_edges; diagnostics += link_diagnostics
    release_nodes, release_edges, release_evidence, release_diagnostics, release_report = (
        _release_artifact_links(workspace, graphs)
    )
    nodes += release_nodes; edges += release_edges
    from .kafka_bindings import build_links as kafka_links, validate_snapshot as validate_kafka_snapshot
    kafka_nodes, kafka_edges, kafka_evidence, kafka_contexts, kafka_diagnostics, kafka_report = kafka_links(workspace, graphs)
    nodes += kafka_nodes; edges += kafka_edges
    diagnostics += ['KAFKA_BINDING_UNKNOWN: ' + item['binding_id'] for item in kafka_diagnostics]
    release_messages = [item['code'] + ': ' + item['mapping_id'] + ': ' + item['reason']
                        for item in release_diagnostics]
    diagnostics += release_messages
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
    _validate_release_artifact_snapshot(workspace, release_report)
    validate_kafka_snapshot(workspace, kafka_report)
    _REPO_CACHE.update(pending_cache)
    if persist_cache and cache_root is not None:
        from .analysis_model import write_json
        for key, (local, local_schema) in pending_cache.items():
            payload = {'graph': local.to_dict(), 'schemas': local_schema}
            write_json(safe_path(cache_root, f'.kgmaker/workspace-cache/{key}.json'),
                       {'schema_version': 1, 'cache_key': key, 'payload': payload, 'payload_hash': digest(payload)})
    graph = KnowledgeGraph(3, '.', '', sorted(nodes, key=lambda n: n.id),
                           sorted(set(edges), key=lambda e: (e.source, e.kind, e.target)),
                           {k: v['sha256'] for k, v in sources.items()},
                           [{**_qualified_context(repo, context, redact_kafka_properties=workspace.get('kafka_bindings') is not None), 'repo_id': repo}
                            for repo, local in graphs.items() for context in local.contexts if 'id' in context] + kafka_contexts,
                           ([{'repo_id': repo, **d}
                             for repo, local in graphs.items() for d in local.diagnostics]
                            + release_diagnostics + kafka_diagnostics),
                           ([_qualified_evidence(repo, e)
                             for repo, local in graphs.items() for e in local.evidence]
                            + release_evidence + kafka_evidence),
                           symbols=sorted(symbols, key=lambda item: item['id']),
                           call_sites=sorted(call_sites, key=lambda item: item['id']),
                           cfgs=sorted(cfgs, key=lambda item: (item['method'], item.get('representation', ''))),
                           analysis_annotations=sorted(annotations, key=lambda item: item['id']))
    graph.files['@workspace/manifest.json'] = workspace['_manifest_hash']
    KnowledgeGraph.from_dict(graph.to_dict())
    baseline = {'git_commit': None, 'graph_fingerprint': digest(graph.to_dict()),
                'working_tree_fingerprint': digest(sources), 'parser_version': 'workspace-1',
                'semantic_hash': None, 'manifest_hash': workspace['_manifest_hash'], 'repositories': baseline_repos}
    coverage = {'roots': [r['id'] for r in workspace['repositories']], 'artifacts': sorted(sources),
                'exclusions': exclusions, 'excluded_directories': [], 'dataflow_diagnostics': [],
                'artifact_diagnostics': [dict(item) for item in graph.diagnostics
                                         if item.get('code') in {'BINARY_XLS_UNSUPPORTED', 'XLSX_PARSE_FAILED'}],
                'unsupported_sources': sorted(k for k, v in sources.items() if not v['supported']),
                'parser_capabilities': {'workspace': 1, 'schema_replay': 1,
                                        'release_artifact_mapping': 1,
                                        'local_checkout_only': True},
                'limitations': [(
                    'Runtime deployment remains unknown; release mapping proves only the declared '
                    'BuildManifest output to compiler-classpath byte identity.'
                    if release_report is not None else
                    'No deployment compatibility is established without an explicit release mapping.'
                ),
                                'Static test assertions do not establish runtime PASS/FAIL.'] + diagnostics,
                'pending': pending + diagnostics, 'repositories': copy.deepcopy(baseline_repos), 'schemas': schemas}
    if release_report is not None:
        coverage['release_mapping'] = release_report
    if kafka_report is not None:
        coverage['kafka_bindings'] = kafka_report
        coverage['parser_capabilities']['kafka_binding_identity'] = 1
    metadata = {'manifest_path': str(manifest.resolve()), 'manifest_hash': workspace['_manifest_hash'],
                'workspace_id': workspace['workspace_id'], 'roots': {r['id']: r['_root'] for r in workspace['repositories']},
                'release_mapping': workspace.get('release_mapping')}
    return baseline, coverage, sources, graph, metadata

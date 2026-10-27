"""Pure projection of explicit datasource realms and existing persistence facts.

Migration derivation is an attribute, not a new evidence kind or a statement
about a deployed database. This module never parses queries or connects to a DB.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re

from .analysis_model import digest, file_hash, safe_path
from .architecture_model import ViewDocument, ViewNode, ViewEdge, aggregate_view_edges
from .model import KnowledgeGraph
from .views import project_service_inventory, _summarize_view_evidence, ServiceInventoryError
from .workspace import load_workspace, qualified, resolve_service_ownership

VERSION = 't015-data-resources-1'
ACCESS = {'query_reads': 'reads', 'query_writes': 'writes', 'query_deletes': 'deletes'}
RELATIONS = {**ACCESS, 'maps_to_table': 'depends_on'}
IDENTIFIER = re.compile(r'[A-Za-z0-9_.-]{1,128}')


class DataResourceError(ValueError):
    """Invalid or no longer content-bound resource projection inputs."""


def project_data_resources(workspace: Mapping, graph: KnowledgeGraph, *, source_coverage: Mapping,
                           scope='production', selected_contexts=None) -> ViewDocument:
    """Project T008-owned services, explicit DB/stream resources and bounded access.

    ``source_coverage`` is the coverage returned by ``snapshot_workspace``. Its
    schema inventories must still agree with the supplied graph and local files.
    Unsupported/missing datasource mappings stay separate unresolved boundaries.
    Only selected, current context-bound upstream query facts can establish access.
    """
    if not isinstance(source_coverage, Mapping) or not isinstance(source_coverage.get('schemas', {}), Mapping):
        raise DataResourceError('Invalid schema snapshot coverage')
    try:
        inventory = project_service_inventory(workspace, graph, scope=scope,
            selected_contexts=selected_contexts, source_coverage=source_coverage)
    except ServiceInventoryError as error:
        raise DataResourceError(str(error)) from error
    verified = load_workspace(Path(workspace['_manifest_path']))
    repos = {r['id']: r for r in verified['repositories']}
    nodes = {n.id: n for n in graph.nodes}
    files = {n.path: n for n in graph.nodes if n.kind == 'file'}
    contexts = {c['id']: c for c in graph.contexts}
    diagnostics = [dict(d) for d in inventory.diagnostics]
    evidence = {p['id']: dict(p) for p in inventory.provenance}
    records, table_resources, claims = {}, {}, []
    excluded = 0
    selected = {}
    services = {n.id for n in inventory.nodes if n.kind == 'service'}
    for service, value in inventory.context_selection['services'].items():
        for row in value['contexts']:
            if row.get('context_id') and row.get('status') == 'CURRENT':
                selected.setdefault(row['context_id'], set()).add('service:' + service)

    def issue(code, **fields):
        item = {'code': code, **fields}
        if item not in diagnostics:
            diagnostics.append(item)

    def local_path(path):
        if not isinstance(path, str) or not path.startswith('@') or '/' not in path:
            raise DataResourceError('Resource source snapshot requires a qualified local path')
        repo, relative = path[1:].split('/', 1)
        if repo not in repos:
            raise DataResourceError('Foreign resource source snapshot')
        try:
            return repo, safe_path(Path(repos[repo]['_root']), relative)
        except (ValueError, OSError) as error:
            raise DataResourceError('Invalid resource source snapshot path') from error

    def current(path, checksum):
        _, source = local_path(path)
        try:
            valid = (isinstance(checksum, str) and graph.files.get(path) == checksum
                     and source.is_file() and file_hash(source) == checksum)
        except OSError:
            valid = False
        if not valid:
            raise DataResourceError('Resource source snapshot changed or is missing')

    def owners(repo, path, context=None):
        file = files.get(path)
        if file is None or file.scope != scope:
            return set()
        choices = [context] if context else [c for c in graph.contexts if c.get('repo_id') == repo
            and c.get('scope') == scope and c.get('freshness') != 'STALE'
            and (path in c.get('source_files', {}) or c.get('mode') == 'SOURCE_ONLY')]
        ids = set()
        for selected_context in choices:
            result = resolve_service_ownership({'repo_id': repo, 'path': path,
                'module': selected_context.get('module'), 'context_id': selected_context['id']},
                verified.get('service_ownership'), context_id=selected_context['id'])
            ids.update('service:' + s for s in result['candidate_owner_ids'])
        ids &= services
        if len(ids) != 1:
            if ids:
                issue('DATA_RESOURCE_OWNERSHIP_AMBIGUOUS', source_id=path)
            return set()
        return ids

    def realm(database, stream):
        return (database, stream) if all(isinstance(x, str) and IDENTIFIER.fullmatch(x) for x in (database, stream)) else None

    def resource(repo, selected_realm, boundary):
        identity = 'data-resource:' + digest({'workspace': verified['workspace_id'], 'repo': repo,
            'realm': selected_realm, 'unmapped': boundary if selected_realm is None else None})
        if identity not in records:
            records[identity] = {'repo_id': repo, 'realm': selected_realm, 'tables': set(),
                'refs': set(), 'owners': set(), 'derivation': set(), 'contexts': set(),
                'scope_proven': False, 'realm_verified': False, 'ambiguous': False}
        if selected_realm is None:
            issue('DATASOURCE_MAPPING_UNKNOWN', resource_id=identity, repo_id=repo)
        return identity

    def source_proof(source_id, *, kind='SOURCE_ONLY', checksum=None, derivation=None):
        proof = {'source_id': source_id, 'evidence_kind': kind, 'freshness': 'CURRENT', 'polarity': 'UNKNOWN'}
        if checksum is not None:
            proof['content_hash'] = checksum
        if derivation is not None:
            proof['derivation'] = derivation
        ref = 'ev:data-resource:' + digest(proof)
        evidence[ref] = {'id': ref, **proof}
        return ref

    # Verify existing replay inventories, not a parallel schema reconstruction.
    for repo, schemas in sorted(source_coverage.get('schemas', {}).items()):
        if repo not in repos or not isinstance(schemas, list):
            raise DataResourceError('Invalid or foreign schema snapshot repository')
        seen = set()
        for schema in schemas:
            if (not isinstance(schema, Mapping) or not isinstance(schema.get('config'), Mapping)
                    or not isinstance(schema.get('inventory'), list) or not isinstance(schema.get('objects'), Mapping)
                    or schema.get('provenance') != 'MIGRATION_DERIVED'):
                raise DataResourceError('Invalid migration schema snapshot')
            config = schema['config']
            if (not isinstance(config.get('provenance', []), list)
                    or any(not isinstance(p, Mapping) or ('keys' in p and
                        (not isinstance(p['keys'], list) or any(not isinstance(k, str) for k in p['keys'])))
                           for p in config.get('provenance', []))
                    or any(not isinstance(i, Mapping) for i in schema['inventory'])
                    or realm(config.get('database_id'), config.get('stream_id')) is None):
                raise DataResourceError('Invalid migration realm/configuration snapshot')
            override = repos[repo].get('flyway')
            if override:
                declarations = override if isinstance(override, list) else [override]
                if not any(all(config.get(k) == v for k, v in declaration.items()) for declaration in declarations):
                    raise DataResourceError('Migration configuration snapshot disagrees with workspace declaration')
            if schema.get('fingerprint') != digest({'config': config, 'inventory': schema['inventory']}):
                raise DataResourceError('Migration schema snapshot fingerprint mismatch')
            proof_paths = []
            for item in [*schema['inventory'], *[p for p in config.get('provenance', []) if 'path' in p]]:
                if not isinstance(item, Mapping) or not isinstance(item.get('path'), str):
                    raise DataResourceError('Invalid migration source snapshot')
                path = '@' + repo + '/' + item['path']
                current(path, item.get('sha256'))
                proof_paths.append((path, item['sha256']))
            inventory_paths = {'@' + repo + '/' + i['path'] for i in schema['inventory']}
            known_scopes = {files[p].scope for p in inventory_paths if p in files}
            if known_scopes and scope not in known_scopes and 'unknown' not in known_scopes:
                excluded += 1
                continue
            explicit = any(p.get('kind') == 'EXPLICIT_CONFIGURATION' and 'database_id' in p.get('keys', [])
                           for p in config.get('provenance', []))
            selected_realm = realm(config.get('database_id'), config.get('stream_id')) if explicit else None
            identity = resource(repo, selected_realm, 'migration:' + str(config.get('stream_id')))
            record = records[identity]
            if identity in seen:
                record['ambiguous'] = True
                issue('DATA_RESOURCE_REALM_CONFLICT', resource_id=identity)
            seen.add(identity)
            record['realm_verified'] |= selected_realm is not None
            record['derivation'].add('MIGRATION_DERIVED')
            record['scope_proven'] |= scope in known_scopes
            for path, checksum in proof_paths:
                record['refs'].add(source_proof(path, checksum=checksum, derivation='MIGRATION_DERIVED'))
                record['owners'].update(owners(repo, path))
            expected_tables = {qualified(repo, item['id']) for item in schema['objects'].values()
                if isinstance(item, Mapping) and item.get('kind') == 'table' and isinstance(item.get('id'), str)}
            prefix = qualified(repo, 'schema:' + config['database_id'] + ':' + config['stream_id'] + ':table:')
            graph_tables = {n.id for n in graph.nodes if n.kind == 'db_table' and n.id.startswith(prefix) and n.path in inventory_paths}
            if expected_tables != graph_tables:
                raise DataResourceError('Migration table inventory snapshot does not match graph')
            for item in schema['objects'].values():
                if not isinstance(item, Mapping) or not isinstance(item.get('id'), str):
                    raise DataResourceError('Invalid migration object snapshot')
                if item.get('kind') != 'table':
                    continue
                prefix = 'schema:' + config['database_id'] + ':' + config['stream_id'] + ':table:'
                if not item['id'].startswith(prefix):
                    raise DataResourceError('Migration table realm snapshot mismatch')
                original = qualified(repo, item['id'])
                target = nodes.get(original)
                if target is None or target.kind != 'db_table':
                    raise DataResourceError('Migration table snapshot does not match graph')
                change = item.get('last_change', {})
                if not isinstance(change, Mapping):
                    raise DataResourceError('Invalid migration table source snapshot')
                if target.path != '@' + repo + '/' + str(change.get('path')):
                    raise DataResourceError('Migration table source snapshot mismatch')
                if files.get(target.path) is None or files[target.path].scope != scope:
                    issue('DATA_RESOURCE_TABLE_SCOPE_UNKNOWN_OR_EXCLUDED', source_id=original)
                    continue
                record['tables'].add(original)
                table_resources[original] = identity
            if schema.get('status') != 'COMPLETE' or schema.get('diagnostics') or schema.get('mapping_diagnostics'):
                issue('DATA_RESOURCE_SCHEMA_PARTIAL', resource_id=identity)

    # Existing ORM table nodes are declarations, not query execution or access.
    for node in graph.nodes:
        if node.kind != 'orm_table' or node.scope != scope:
            continue
        repo, _ = local_path(node.path)
        if node.path not in files or files[node.path].scope != scope:
            excluded += 1
            issue('DATA_RESOURCE_ORM_SCOPE_UNKNOWN_OR_EXCLUDED', source_id=node.id)
            continue
        metadata = node.metadata or {}
        if not isinstance(metadata, Mapping):
            raise DataResourceError('Invalid ORM realm metadata')
        member_contexts = {cid for edge in graph.edges if edge.target == node.id
            and edge.context_ids and set(edge.context_ids) <= set(selected) for cid in edge.context_ids
            if contexts[cid].get('repo_id') == repo
            and contexts[cid].get('source_files', {}).get(node.path) == graph.files.get(node.path)}
        if metadata.get('context_id') is not None:
            declared = metadata['context_id']
            member_contexts = {cid for cid in member_contexts if isinstance(declared, str)
                and (declared == cid or qualified(repo, declared) == cid)}
        if not member_contexts:
            issue('DATA_RESOURCE_ORM_CONTEXT_UNKNOWN', source_id=node.id)
            continue
        selected_realm = realm(metadata.get('database_id'), metadata.get('schema_stream_id'))
        identity = resource(repo, selected_realm, 'orm:' + node.id)
        record = records[identity]
        record['tables'].add(node.id)
        record['scope_proven'] |= node.path in files and files[node.path].scope == scope
        table_resources[node.id] = identity
        current(node.path, graph.files.get(node.path))
        record['refs'].add(source_proof(node.id, kind='UNKNOWN', checksum=graph.files[node.path]))

    def endpoint_matches(node, context):
        captured = context.get('source_files', {})
        metadata = node.metadata or {}
        if not isinstance(captured, Mapping) or not isinstance(metadata, Mapping):
            return False
        declared_context = metadata.get('context_id')
        # Workspace qualifies public IDs and symbol records, while older generic
        # Node metadata may still carry the original local context ID.
        context_ok = (declared_context is None or declared_context == context['id']
            or isinstance(declared_context, str)
            and qualified(context['repo_id'], declared_context) == context['id'])
        scope_ok = node.scope == scope or node.kind == 'db_table' and node.scope == 'unknown'
        return (scope_ok and node.path in files and files[node.path].scope == scope
            and node.path in captured and captured[node.path] == graph.files.get(node.path)
            and context_ok and (metadata.get('sha256') is None or metadata['sha256'] == captured[node.path]))

    def edge_reference(edge):
        # Graph Edge has no standalone ID: retain its exact public composite
        # identity and original evidence IDs rather than inventing a graph node.
        return {'source': edge.source, 'target': edge.target, 'relation': edge.kind,
                'context_ids': list(edge.context_ids), 'evidence_refs': list(edge.evidence_ids)}

    def proofs_for(edge, context):
        source, target = nodes[edge.source], nodes[edge.target]
        if (edge.evidence_kind not in {'FRAMEWORK_DERIVED', 'SYMBOL_RESOLVED'}
                or edge.context_ids != (context['id'],) or not edge.evidence_ids
                or not endpoint_matches(source, context) or not endpoint_matches(target, context)):
            return None
        captured = context['source_files']
        current(source.path, captured[source.path])
        current(target.path, captured[target.path])
        proofs = []
        for ref in edge.evidence_ids:
            original = next((p for p in graph.evidence if p['id'] == ref), None)
            if (original is None or original.get('source') != edge.source or original.get('target') != edge.target
                    or original.get('relation') != edge.kind or original.get('kind') != edge.evidence_kind
                    or original.get('context_ids') != list(edge.context_ids)
                    or original.get('source_file') != source.path):
                return None
            if original.get('freshness') not in (None, 'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND'):
                issue('DATA_RESOURCE_EVIDENCE_FRESHNESS_UNKNOWN', source_id=edge.source)
                return None
            checksum = original.get('sha256')
            hash_provenance = 'ORIGINAL_FACT_SHA'
            if checksum is None:
                # Existing framework.evidence_for has no per-fact SHA unless a
                # compiler_fact was supplied. Its exact context/source binding
                # still provides a current captured hash; do not pretend the
                # original fact carried that field.
                checksum = captured[source.path]
                hash_provenance = 'VALIDATED_CONTEXT_SOURCE'
            if not isinstance(checksum, str) or checksum != captured[source.path]:
                issue('DATA_RESOURCE_FACT_HASH_UNKNOWN_OR_STALE', source_id=edge.source)
                return None
            polarity = original.get('polarity', 'UNKNOWN')
            if not isinstance(polarity, str) or polarity not in {'SUPPORTING', 'CONTRADICTING', 'UNKNOWN'}:
                polarity = 'UNKNOWN'
                issue('DATA_RESOURCE_EVIDENCE_POLARITY_UNKNOWN', source_id=edge.source)
            proof = {'original_id': ref, 'evidence_kind': edge.evidence_kind, 'freshness': 'CURRENT',
                'polarity': polarity, 'source_id': source.id, 'source_file': source.path,
                'content_hash': checksum, 'hash_provenance': hash_provenance,
                'target_source_file': target.path, 'target_content_hash': captured[target.path],
                'context_ids': list(edge.context_ids), 'original_edge': edge_reference(edge)}
            proof['id'] = 'ev:data-access:' + digest(proof)
            proofs.append(proof)
        return proofs

    for edge in graph.edges:
        if edge.kind not in RELATIONS:
            continue
        path = [edge]
        if edge.target not in table_resources and edge.kind in ACCESS:
            mappings = [m for m in graph.edges if m.source == edge.target and m.kind == 'maps_to_table']
            if len(mappings) != 1:
                issue('DATA_RESOURCE_ENTITY_MAPPING_AMBIGUOUS_OR_MISSING', source_id=edge.source,
                      target_id=edge.target, candidate_count=len(mappings))
                continue
            path.append(mappings[0])
        target = nodes.get(path[-1].target)
        source = nodes.get(edge.source)
        identity = table_resources.get(path[-1].target)
        if source is None or target is None or identity is None or source.scope != scope:
            issue('DATA_RESOURCE_ACCESS_SCOPE_OR_TARGET_UNKNOWN', source_id=edge.source)
            continue
        record = records[identity]
        context = contexts.get(edge.context_ids[0], {}) if len(edge.context_ids) == 1 else {}
        valid = (record['realm'] is not None and not record['ambiguous']
                 and context.get('id') in selected
                 and realm(context.get('database_id'), context.get('schema_stream_id')) == record['realm'])
        repo, _ = local_path(source.path)
        owner_ids = owners(repo, source.path, context) & selected.get(context.get('id'), set())
        if repo != record['repo_id'] or not owner_ids or context.get('repo_id') != repo:
            valid = False
        pending_proofs = []
        if valid:
            for member in path:
                if member.source not in nodes or member.target not in nodes:
                    valid = False; break
                proofs = proofs_for(member, context)
                if proofs is None:
                    valid = False; break
                pending_proofs.extend(proofs)
        if not valid:
            issue('DATA_RESOURCE_ACCESS_UNPROVEN', source_id=edge.source, target_id=path[-1].target)
            continue
        evidence.update((p['id'], p) for p in pending_proofs)
        refs = sorted({p['id'] for p in pending_proofs})
        record['realm_verified'] = True
        record['scope_proven'] = True
        record['contexts'].add(context['id'])
        record['owners'].update(owner_ids)
        record['refs'].update(refs)
        for owner in owner_ids:
            summary = _summarize_view_evidence(refs, evidence)
            claims.append(ViewEdge('data-access:' + digest({'owner': owner, 'target': identity,
                'relation': edge.kind, 'contexts': edge.context_ids, 'evidence': refs}), owner, identity,
                RELATIONS[edge.kind], original_ids=tuple(sorted({i for m in path for i in (m.source, m.target, *m.evidence_ids)})),
                evidence_refs=tuple(refs),
                resolution_status=('AMBIGUOUS' if summary['supporting_refs'] and summary['contradicting_refs'] else
                    'UNRESOLVED' if summary['contradicting_refs'] else 'RESOLVED'),
                attributes={'scope': scope, 'context_ids': list(edge.context_ids),
                            'original_edges': [edge_reference(m) for m in path]},
                evidence_kinds=tuple(summary['evidence_kinds']), freshness=summary['freshness'],
                supporting_refs=tuple(summary['supporting_refs']), contradicting_refs=tuple(summary['contradicting_refs']),
                unknown_refs=tuple(summary['unknown_refs'])))

    resource_nodes = []
    for identity, record in sorted(records.items()):
        refs = sorted(record['refs'])
        summary = _summarize_view_evidence(refs, evidence)
        resolved = record['realm_verified'] and not record['ambiguous'] and record['scope_proven']
        if record['realm'] is not None and not record['realm_verified']:
            issue('DATASOURCE_CONTEXT_PROOF_UNKNOWN', resource_id=identity)
        if not record['scope_proven']:
            issue('DATA_RESOURCE_SCOPE_UNKNOWN', resource_id=identity)
        database, stream = record['realm'] or (None, None)
        resource_nodes.append(ViewNode(identity, 'database_resource' if resolved else 'unresolved_data_resource',
            database or 'Unmapped data resource', original_ids=tuple(sorted(record['tables'])), evidence_refs=tuple(refs),
            resolution_status='RESOLVED' if resolved else 'AMBIGUOUS' if record['ambiguous'] else 'UNRESOLVED',
            attributes={'database_id': database, 'schema_stream_id': stream, 'repo_id': record['repo_id'],
                'scope': scope if record['scope_proven'] else 'unknown', 'table_ids': sorted(record['tables']), 'derivation': sorted(record['derivation']),
                'deployment_status': 'UNKNOWN', 'data_availability': 'UNKNOWN',
                'context_ids': sorted(record['contexts'])},
            evidence_kinds=tuple(summary['evidence_kinds']), freshness=summary['freshness'],
            supporting_refs=tuple(summary['supporting_refs']), contradicting_refs=tuple(summary['contradicting_refs']),
            unknown_refs=tuple(summary['unknown_refs'])))
        for owner in sorted(record['owners']):
            claims.append(ViewEdge('data-dependency:' + digest((owner, identity)), owner, identity, 'depends_on',
                evidence_refs=tuple(refs), resolution_status='RESOLVED' if resolved else 'UNRESOLVED',
                attributes={'scope': scope, 'context_ids': sorted(record['contexts']),
                            'deployment_status': 'UNKNOWN', 'data_availability': 'UNKNOWN'},
                evidence_kinds=tuple(summary['evidence_kinds']), freshness=summary['freshness'],
                supporting_refs=tuple(summary['supporting_refs']), contradicting_refs=tuple(summary['contradicting_refs']),
                unknown_refs=tuple(summary['unknown_refs'])))
    aggregation = aggregate_view_edges([*inventory.edges, *claims], tuple(evidence.values()), scope=scope, diagnostics=diagnostics)
    resolved_count = sum(n.resolution_status == 'RESOLVED' for n in resource_nodes)
    result = ViewDocument(view_id='data-resources:' + verified['workspace_id'] + ':' + scope, kind='topology',
        baseline_fingerprint=digest({'inventory': inventory.baseline_fingerprint, 'schemas': {repo: sorted(digest(s) for s in schemas)
            for repo, schemas in source_coverage.get('schemas', {}).items()}}),
        rules_version=VERSION, scope=scope, context_selection=inventory.context_selection,
        nodes=inventory.nodes + tuple(resource_nodes), edges=aggregation['edges'],
        provenance=aggregation['provenance'], diagnostics=aggregation['diagnostics'] + ({'code': 'PERSISTENCE_COVERAGE_PARTIAL',
            'message': 'Only existing bounded upstream persistence facts are projected; complete S06/datasource compatibility is not established.'},),
        coverage={'status': 'PARTIAL' if resource_nodes else 'UNKNOWN', 'counts': {'found': len(resource_nodes),
            'resolved': resolved_count, 'unresolved': len(resource_nodes) - resolved_count, 'excluded': excluded}},
        limits=inventory.limits + ('Migration derivation is not deployed/populated-data proof.',
            'No query parsing, datasource discovery or cross-realm access inference is performed.'))
    return ViewDocument.from_dict(result.to_dict())

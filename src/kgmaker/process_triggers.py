"""Read-only inventory of existing context-bound Spring trigger declarations.

No application/worker is executed. A trigger candidate is not a registered,
executing or identified business process, and no CFG path is expanded here.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

from .analysis_model import digest, file_hash, safe_path
from .architecture_model import ViewDocument, ViewNode
from .control_flow import VERSION as SOURCE_CFG_VERSION
from .views import project_service_inventory, ServiceInventoryError, _summarize_view_evidence
from .workspace import load_workspace, qualified, resolve_service_ownership

VERSION = 't024-proved-trigger-inventory-1'
HTTP_ANNOTATIONS = frozenset('org.springframework.web.bind.annotation.' + name for name in
    ('GetMapping', 'PostMapping', 'PutMapping', 'DeleteMapping', 'PatchMapping', 'RequestMapping'))
KAFKA_ANNOTATION = 'org.springframework.kafka.annotation.KafkaListener'
SCHEDULER_ANNOTATION = 'org.springframework.scheduling.annotation.Scheduled'
FACT_RELATIONS = frozenset({'exposes_endpoint', 'declares_entrypoint'})


class TriggerInventoryError(ValueError):
    """Invalid or no longer content-bound inputs; publication is the caller's job."""
    def __init__(self, code, message):
        self.diagnostic = {'code': code, 'message': message}
        super().__init__(code + ': ' + message)


def _annotations(symbol):
    values = symbol.get('annotations')
    return {v['name'] for v in values if isinstance(v, Mapping) and isinstance(v.get('name'), str)} if isinstance(values, list) else set()


def _same_line(value, canonical):
    return value is None or type(value) is int and type(canonical) is int and value == canonical


def _canonical_symbol(symbol, node, context):
    """Check only identity fields against the captured source-node authority.

    Workspace wraps IDs/paths/context IDs but leaves the source node's captured
    metadata local. Annotation arguments and unrelated nested metadata are not
    compared or interpreted as identity.
    """
    canonical = node.metadata if isinstance(node.metadata, Mapping) else {}
    repo = context['repo_id']
    if symbol.get('name') != node.name or symbol.get('kind') != node.kind:
        return False
    if any(symbol.get(field) is not None and not isinstance(symbol[field], str)
           for field in ('owner', 'descriptor', 'type')):
        return False
    for field in ('name', 'kind', 'owner', 'descriptor', 'sha256', 'scope'):
        expected = canonical.get(field)
        if expected is not None and (not isinstance(expected, str) or symbol.get(field) != expected):
            return False
    if 'scope' in symbol and symbol['scope'] != node.scope:
        return False
    signature = symbol.get('descriptor') or symbol.get('type')
    if signature != node.signature:
        return False
    for field, expected in [('id', node.id), ('context_id', context['id'])]:
        value = canonical.get(field)
        if value is not None and (not isinstance(value, str) or value != expected and qualified(repo, value) != expected):
            return False
    path = canonical.get('path')
    if path is not None and (not isinstance(path, str) or path != node.path and '@' + repo + '/' + path != node.path):
        return False
    if not _same_line(symbol.get('range', {}).get('start_line') if isinstance(symbol.get('range'), Mapping) else None, node.line):
        return False
    captured_range = canonical.get('range')
    if isinstance(captured_range, Mapping) and captured_range.get('start_line') is not None:
        if not isinstance(symbol.get('range'), Mapping) or symbol['range'].get('start_line') != captured_range['start_line']:
            return False
    if isinstance(canonical.get('annotations'), list) and _annotations(symbol) != _annotations(canonical):
        return False
    return True


def discover_process_triggers(workspace, graph, *, source_coverage, scope='production', selected_contexts=None):
    """Project only proved HTTP/Kafka/scheduler declarations into trigger nodes.

    Inputs use the existing loaded-workspace/provider contract. Service/context
    selection and source freshness reuse T008/T006; all output evidence remains
    distinguishable from body existence, runtime registration or execution.
    """
    try:
        inventory = project_service_inventory(workspace, graph, scope=scope,
            selected_contexts=selected_contexts, source_coverage=source_coverage)
        snapshot = graph.to_dict()
        json.dumps(snapshot, allow_nan=False)
        verified = load_workspace(Path(workspace['_manifest_path']))
    except ServiceInventoryError as error:
        raise TriggerInventoryError(error.diagnostic['code'], error.diagnostic['message']) from error
    except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
        raise TriggerInventoryError('INVALID_TRIGGER_SNAPSHOT', 'Invalid workspace/provider document') from error
    repos = {repo['id']: Path(repo['_root']) for repo in verified['repositories']}
    nodes = {node.id: node for node in graph.nodes}
    symbols = {symbol['id']: symbol for symbol in graph.symbols}
    evidence = {proof['id']: proof for proof in graph.evidence}
    contexts = {}
    for context in graph.contexts:
        cid = context.get('id')
        if isinstance(cid, str):
            if cid in contexts:
                raise TriggerInventoryError('DUPLICATE_TRIGGER_CONTEXT', 'Context IDs must be unique')
            contexts[cid] = context
    file_scopes = {}
    for node in graph.nodes:
        if node.kind == 'file':
            if not isinstance(node.path, str):
                raise TriggerInventoryError('INVALID_TRIGGER_SOURCE', 'File nodes require canonical source paths')
            file_scopes.setdefault(node.path, []).append(node.scope)
    selected = {}
    for service, value in inventory.context_selection['services'].items():
        for row in value['contexts']:
            if row.get('status') == 'CURRENT' and row.get('context_id'):
                selected.setdefault(row['context_id'], set()).add('service:' + service)
    diagnostics = [dict(d) for d in inventory.diagnostics]
    output_proofs, candidates, accepted_sources = {}, {}, {}
    excluded = 0
    consumed = set()

    def issue(code, source_id=None, **fields):
        item = {'code': code, **({'source_id': source_id} if source_id else {}), **fields}
        if item not in diagnostics:
            diagnostics.append(item)

    def local_path(path, repo):
        if not isinstance(path, str) or not path.startswith('@' + repo + '/') or repo not in repos:
            raise TriggerInventoryError('INVALID_TRIGGER_SOURCE', 'Trigger requires a repository-qualified source path')
        try:
            return safe_path(repos[repo], path[len(repo) + 2:])
        except (ValueError, OSError) as error:
            raise TriggerInventoryError('INVALID_TRIGGER_SOURCE', 'Trigger source leaves the selected repository') from error

    def current(path, checksum, repo):
        source = local_path(path, repo)
        try:
            valid = (isinstance(checksum, str) and graph.files.get(path) == checksum
                and source.is_file() and file_hash(source) == checksum)
        except OSError:
            valid = False
        if not valid:
            raise TriggerInventoryError('TRIGGER_SOURCE_CHANGED', 'Trigger source snapshot changed or disappeared')
        accepted_sources[path] = (checksum, repo)

    def endpoint_valid(node, context):
        metadata = {} if node.metadata is None else node.metadata
        captured = context.get('source_files')
        if not isinstance(metadata, Mapping) or not isinstance(captured, Mapping):
            return False
        declared = metadata.get('context_id')
        return (node.scope == scope and file_scopes.get(node.path) == [scope]
            and (node.line is None or type(node.line) is int and node.line > 0)
            and node.path in captured and captured[node.path] == graph.files.get(node.path)
            and (metadata.get('scope') is None or metadata['scope'] == node.scope)
            and (declared is None or declared == context['id'] or isinstance(declared, str)
                 and qualified(context['repo_id'], declared) == context['id'])
            and (metadata.get('sha256') is None or metadata['sha256'] == captured[node.path]))

    def body_status(method, context):
        cfgs = [c for c in graph.cfgs if c.get('method') == method.id
                and c.get('context_id') == context['id'] and c.get('representation') == 'SOURCE']
        if len(cfgs) != 1:
            return ('AMBIGUOUS' if cfgs else 'UNAVAILABLE'), [], []
        cfg = cfgs[0]
        if not isinstance(cfg.get('version'), str) or cfg['version'] not in {'source-cfg-1', SOURCE_CFG_VERSION}:
            return 'UNAVAILABLE', [], []
        refs = cfg.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            return 'UNAVAILABLE', [], []
        kinds = set()
        for ref in refs:
            proof = evidence.get(ref, {})
            kind = proof.get('kind')
            if (not isinstance(kind, str) or kind not in {'SYNTAX_CANDIDATE', 'SYMBOL_RESOLVED'}
                    or proof.get('source') != method.id or proof.get('target') != method.id
                    or proof.get('relation') != 'control_flow' or proof.get('context_ids') != [context['id']]
                    or proof.get('representation') != 'SOURCE' or proof.get('source_file') != method.path
                    or proof.get('sha256') != context['source_files'][method.path]
                    or proof.get('freshness') not in (None, 'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND')):
                return 'UNAVAILABLE', [], []
            kinds.add(kind)
        blocks = cfg.get('blocks')
        if not isinstance(blocks, list) or any(not isinstance(block, Mapping) for block in blocks):
            return 'UNAVAILABLE', [], []
        for block in blocks:
            path = block.get('source_file')
            if path is None:
                if not isinstance(block.get('kind'), str) or block['kind'] not in {'entry', 'exit', 'exceptional_exit'}:
                    return 'UNAVAILABLE', [], []
            elif (path != method.path or block.get('sha256') != context['source_files'][method.path]):
                return 'UNAVAILABLE', [], []
        complete = cfg.get('status') == 'COMPLETE_WITHIN_SUPPORTED_SYNTAX' and not cfg.get('diagnostics')
        return ('AVAILABLE' if complete else 'PARTIAL'), sorted(set(refs)), sorted(kinds)

    for edge in graph.edges:
        if not isinstance(edge.kind, str) or edge.kind not in FACT_RELATIONS:
            continue
        source, target = nodes[edge.source], nodes[edge.target]
        cid = edge.context_ids[0] if len(edge.context_ids) == 1 else None
        context = contexts.get(cid, {})
        mode, freshness = context.get('mode'), context.get('freshness')
        if (cid not in selected or not isinstance(mode, str) or mode not in {'SYMBOL_RESOLVED', 'BUILD_IMPORT'}
                or not isinstance(context.get('analyzer_version'), str) or not context['analyzer_version']
                or context.get('scope') != scope or context.get('repo_id') not in repos
                or not isinstance(freshness, str) or freshness not in {'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND'}):
            excluded += 1
            issue('TRIGGER_CONTEXT_NOT_SELECTED', edge.source)
            continue
        symbol = symbols.get(source.id, {})
        if (symbol.get('context_id') != cid or symbol.get('path') != source.path
                or not isinstance(symbol.get('kind'), str) or symbol['kind'] not in {'method', 'function'}
                or not isinstance(source.kind, str) or source.kind not in {'method', 'function'}
                or not isinstance(source.path, str) or Path(source.path).suffix.lower() not in {'.java', '.kt', '.kts'}
                or source.path != target.path or not endpoint_valid(source, context) or not endpoint_valid(target, context)):
            excluded += 1
            issue('TRIGGER_ENDPOINT_SCOPE_OR_CONTEXT_UNPROVED', edge.source)
            continue
        if not _canonical_symbol(symbol, source, context):
            excluded += 1
            issue('TRIGGER_CANONICAL_SYMBOL_MISMATCH', source.id)
            continue
        annotations = _annotations(symbol)
        metadata = target.metadata if isinstance(target.metadata, Mapping) else {}
        kind = None
        if edge.kind == 'exposes_endpoint' and target.kind == 'spring_endpoint' and annotations & HTTP_ANNOTATIONS:
            kind = 'HTTP'
        elif edge.kind == 'declares_entrypoint' and target.kind == 'spring_entrypoint':
            declared_kind = metadata.get('entrypoint_kind')
            if declared_kind == 'kafka_listener' and KAFKA_ANNOTATION in annotations:
                kind = 'KAFKA'
            elif declared_kind == 'scheduled' and SCHEDULER_ANNOTATION in annotations:
                kind = 'SCHEDULER'
        if kind is None:
            excluded += 1
            issue('TRIGGER_KIND_UNSUPPORTED', source.id)
            continue
        consumed.add((source.id, cid))
        if (edge.evidence_kind not in {'FRAMEWORK_DERIVED', 'SYMBOL_RESOLVED'} or not edge.evidence_ids
                or len(set(edge.evidence_ids)) != len(edge.evidence_ids) or edge.source_file != source.path
                or not _same_line(edge.source_line, source.line)):
            excluded += 1
            issue('TRIGGER_PROOF_UNAVAILABLE', source.id)
            continue
        repo = context['repo_id']; checksum = context['source_files'][source.path]
        if symbol.get('sha256') is not None and symbol['sha256'] != checksum:
            excluded += 1
            issue('TRIGGER_SYMBOL_HASH_MISMATCH', source.id)
            continue
        current(source.path, checksum, repo)
        original_edge = {'source': edge.source, 'target': edge.target, 'relation': edge.kind,
            'context_ids': list(edge.context_ids), 'evidence_refs': sorted(edge.evidence_ids),
            'source_file': edge.source_file, 'source_line': edge.source_line}
        pending = []
        for ref in edge.evidence_ids:
            proof = evidence[ref]
            if (proof.get('source') != edge.source or proof.get('target') != edge.target
                    or proof.get('relation') != edge.kind or proof.get('kind') != edge.evidence_kind
                    or proof.get('context_ids') != list(edge.context_ids) or proof.get('source_file') != source.path
                    or not _same_line(proof.get('source_line'), source.line)
                    or proof.get('freshness') not in (None, 'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND')
                    or proof.get('sha256') is not None and proof['sha256'] != checksum):
                issue('TRIGGER_FACT_BINDING_UNPROVED', source.id)
                pending = []; break
            polarity = proof.get('polarity', 'UNKNOWN')
            if not isinstance(polarity, str) or polarity not in {'SUPPORTING', 'CONTRADICTING', 'UNKNOWN'}:
                polarity = 'UNKNOWN'; issue('TRIGGER_POLARITY_UNKNOWN', source.id)
            value = {'original_id': ref, 'source_id': source.id, 'source_file': source.path, 'source_line': source.line,
                'content_hash': checksum, 'hash_provenance': 'ORIGINAL_FACT_SHA' if proof.get('sha256') is not None else 'VALIDATED_CONTEXT_SOURCE',
                'evidence_kind': edge.evidence_kind, 'freshness': 'CURRENT', 'polarity': polarity,
                'scope': scope, 'context_ids': [cid], 'original_edge': original_edge}
            value['id'] = 'ev:trigger:' + digest(value); pending.append(value)
        if not pending:
            excluded += 1
            continue
        owner = resolve_service_ownership({'repo_id': repo, 'path': source.path, 'module': context.get('module'),
            'context_id': cid}, verified.get('service_ownership'), context_id=cid)
        owner_id = 'service:' + owner['owner_id'] if owner['owner_id'] else None
        if owner_id not in selected[cid]:
            owner_id = None
            issue('TRIGGER_OWNER_UNAVAILABLE', source.id)
        body, body_refs, body_kinds = body_status(source, context)
        if body != 'AVAILABLE':
            issue('TRIGGER_BODY_UNAVAILABLE' if body == 'UNAVAILABLE' else 'TRIGGER_BODY_PARTIAL_OR_AMBIGUOUS', source.id)
        identity = 'trigger:' + digest({'context': cid, 'symbol': source.id, 'entrypoint': target.id, 'kind': kind})
        value = candidates.setdefault(identity, {'refs': set(), 'originals': {source.id, target.id},
            'owner_id': owner_id, 'attrs': {'scope': scope, 'context_ids': [cid], 'trigger_kind': kind,
                'entry_symbol_id': source.id, 'entrypoint_id': target.id, 'repo_id': repo,
                'body_status': body, 'body_evidence_refs': body_refs, 'body_evidence_kinds': body_kinds,
                'owner_status': owner['status'], 'candidate_owner_ids': owner['candidate_owner_ids'],
                'registration_status': 'UNKNOWN', 'execution_status': 'UNKNOWN', 'data_availability': 'UNKNOWN'}})
        value['originals'].update(edge.evidence_ids); value['originals'].update(body_refs)
        for proof in pending:
            output_proofs[proof['id']] = proof; value['refs'].add(proof['id'])

    # Annotation-only hints explain absent upstream support, never mint a trigger.
    for symbol in graph.symbols:
        cid = symbol.get('context_id')
        if cid in selected and (symbol.get('id'), cid) not in consumed:
            names = _annotations(symbol)
            if names & (HTTP_ANNOTATIONS | {KAFKA_ANNOTATION, SCHEDULER_ANNOTATION}):
                issue('TRIGGER_UPSTREAM_FACT_UNAVAILABLE', symbol['id'])
    output_nodes = []
    for identity, value in sorted(candidates.items()):
        refs = sorted(value['refs']); summary = _summarize_view_evidence(refs, output_proofs)
        status = ('AMBIGUOUS' if summary['contradicting_refs'] and summary['supporting_refs'] else
                  'UNRESOLVED' if value['owner_id'] is None or summary['contradicting_refs'] else 'RESOLVED')
        output_nodes.append(ViewNode(identity, 'trigger', value['attrs']['trigger_kind'] + ' trigger',
            original_ids=tuple(sorted(value['originals'])), owner_id=value['owner_id'], evidence_refs=tuple(refs),
            attributes=value['attrs'], evidence_kinds=tuple(summary['evidence_kinds']), resolution_status=status,
            freshness=summary['freshness'], supporting_refs=tuple(summary['supporting_refs']),
            contradicting_refs=tuple(summary['contradicting_refs']), unknown_refs=tuple(summary['unknown_refs'])))
    # Detect concurrent source edits after earlier proof checks, before returning.
    for path, (checksum, repo) in list(accepted_sources.items()):
        current(path, checksum, repo)
    issue('TRIGGER_DISCOVERY_PARTIAL', message='Only supplied Spring HTTP/Kafka/scheduler declarations are inventoried; unsupported trigger types and scheduler variants remain unknown.')
    sections = {name: sorted(digest(item) for item in snapshot.get(name, []))
        for name in ('nodes', 'edges', 'contexts', 'symbols', 'cfgs', 'evidence', 'diagnostics', 'analysis_annotations')}
    result = ViewDocument(view_id='trigger-inventory:' + verified['workspace_id'] + ':' + scope, kind='process',
        baseline_fingerprint=digest({'inventory': inventory.baseline_fingerprint, 'files': graph.files, 'sections': sections}),
        rules_version=VERSION, scope=scope, context_selection=inventory.context_selection,
        nodes=tuple(output_nodes), edges=(), provenance=tuple(output_proofs.values()), diagnostics=tuple(diagnostics),
        coverage={'status': 'PARTIAL' if output_nodes else 'UNKNOWN', 'counts': {'found': len(output_nodes),
            'resolved': sum(n.resolution_status == 'RESOLVED' for n in output_nodes),
            'unresolved': sum(n.resolution_status != 'RESOLVED' for n in output_nodes), 'excluded': excluded}},
        limits=('Trigger declarations are candidates, not observed registration or execution.',
            'CFG presence is syntax evidence only; no process path, async scheduling or business meaning is inferred.',
            'No source parsing, worker execution, Spring context, broker, network or store mutation.'))
    return ViewDocument.from_dict(result.to_dict())

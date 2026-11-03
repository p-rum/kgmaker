"""Pure adaptation of a selected, content-bound trigger and existing source CFG.

The caller supplies validated provider snapshots. No physical checkout freshness,
application execution, business equivalence or runtime availability is inferred.
"""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
import json

from .analysis_model import digest
from .architecture_model import ViewDocument, ViewNode, ViewEdge
from .control_flow import VERSION as CFG_VERSION
from .flow import process
from .model import KnowledgeGraph
from .process_model import ProcessDefinition, ProcessView, STEP_KINDS, TRANSITION_KINDS
from .process_triggers import (_canonical_symbol, _annotations, VERSION as TRIGGER_VERSION,
    HTTP_ANNOTATIONS, KAFKA_ANNOTATION, SCHEDULER_ANNOTATION)
from .workspace import qualified
from .views import project, _summarize_view_evidence

VERSION = 'local-process-path-1'


class ProcessPathError(ValueError):
    def __init__(self, code, message):
        self.diagnostic = {'code': code, 'message': message}
        super().__init__(code + ': ' + message)


def _fail(code, message):
    raise ProcessPathError(code, message)


def _source_checksum(graph, context, path):
    captured=context.get('source_files')
    if not isinstance(captured,Mapping) or path not in captured or path not in graph.files:
        return None
    checksum=graph.files[path]
    return checksum if (isinstance(checksum,str) and len(checksum)==64
        and all(c in '0123456789abcdef' for c in checksum) and captured[path]==checksum) else None


def _selected_trigger(graph, inventory, trigger_id):
    if inventory.kind != 'process' or inventory.rules_version != TRIGGER_VERSION:
        _fail('INVALID_TRIGGER_INVENTORY', 'Expected a process-kind trigger inventory')
    matches = [n for n in inventory.nodes if n.id == trigger_id and n.kind == 'trigger']
    if len(matches) != 1:
        _fail('TRIGGER_UNAVAILABLE', 'Select exactly one existing trigger candidate')
    trigger = matches[0]; attrs = trigger.attributes
    cids = attrs.get('context_ids')
    if not isinstance(cids, list) or len(cids) != 1 or not isinstance(cids[0], str):
        _fail('TRIGGER_CONTEXT_MISMATCH', 'Trigger requires one selected context')
    cid = cids[0]; contexts = [c for c in graph.contexts if c.get('id') == cid]
    if len(contexts) != 1:
        _fail('TRIGGER_CONTEXT_MISMATCH', 'Trigger context is missing or ambiguous')
    context = contexts[0]; scope = inventory.scope
    selected = any(row.get('context_id') == cid and row.get('status') == 'CURRENT'
        for service in inventory.context_selection.get('services', {}).values()
        for row in service.get('contexts', []))
    if (attrs.get('scope') != scope or context.get('scope') != scope
            or context.get('mode') not in ('BUILD_IMPORT', 'SYMBOL_RESOLVED')
            or context.get('freshness') not in ('CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND') or not selected):
        _fail('TRIGGER_CONTEXT_MISMATCH', 'Trigger requires current selected compiler input')
    nodes = {n.id: n for n in graph.nodes}; symbols = {s['id']: s for s in graph.symbols}
    entry = attrs.get('entry_symbol_id'); endpoint = attrs.get('entrypoint_id')
    method = nodes.get(entry); symbol = symbols.get(entry)
    if (method is None or symbol is None or method.scope != scope or symbol.get('context_id') != cid
            or symbol.get('path') != method.path or method.kind not in ('method', 'function')
            or not _canonical_symbol(symbol, method, context)):
        _fail('TRIGGER_DECLARATION_MISMATCH', 'Entry does not match its canonical compiler declaration')
    checksum = _source_checksum(graph,context,method.path)
    if (checksum is None
            or [n.scope for n in graph.nodes if n.kind == 'file' and n.path == method.path] != [scope]
            or symbol.get('sha256') != checksum):
        _fail('TRIGGER_SOURCE_MISMATCH', 'Entry is not bound to the supplied source snapshot')
    if trigger.id != 'trigger:' + digest({'context': cid, 'symbol': entry,
            'entrypoint': endpoint, 'kind': attrs.get('trigger_kind')}):
        _fail('TRIGGER_IDENTITY_MISMATCH', 'Trigger identity disagrees with its selected declaration')
    target = nodes.get(endpoint)
    if target is None or target.path != method.path or target.scope != scope:
        _fail('TRIGGER_DECLARATION_MISMATCH', 'Trigger endpoint is outside its declaration source')
    kind = attrs.get('trigger_kind'); annotation_names = _annotations(symbol)
    target_meta = target.metadata if isinstance(target.metadata, Mapping) else {}
    if (target.line != method.line or not {entry,endpoint} <= set(trigger.original_ids)
            or target_meta.get('scope',scope) != scope or target_meta.get('sha256',checksum) != checksum
            or target_meta.get('context_id') is not None and target_meta['context_id'] != cid
                and qualified(context['repo_id'],target_meta['context_id']) != cid):
        _fail('TRIGGER_DECLARATION_MISMATCH', 'Endpoint provenance contradicts its compiler source')
    relation = ('exposes_endpoint' if kind == 'HTTP' and target.kind == 'spring_endpoint'
        and annotation_names & HTTP_ANNOTATIONS else 'declares_entrypoint'
        if target.kind == 'spring_entrypoint' and (kind == 'KAFKA'
            and target_meta.get('entrypoint_kind') == 'kafka_listener' and KAFKA_ANNOTATION in annotation_names
            or kind == 'SCHEDULER' and target_meta.get('entrypoint_kind') == 'scheduled'
            and SCHEDULER_ANNOTATION in annotation_names) else None)
    if relation is None:
        _fail('TRIGGER_KIND_MISMATCH', 'Trigger kind disagrees with the canonical declaration')
    proofs = {p['id']: p for p in inventory.provenance}; originals = {p['id']: p for p in graph.evidence}
    if not trigger.evidence_refs:
        _fail('TRIGGER_PROOF_UNAVAILABLE', 'Trigger has no declaration evidence')
    for ref in trigger.evidence_refs:
        p = proofs.get(ref, {}); original = originals.get(p.get('original_id'), {})
        binding = p.get('original_edge')
        if (not isinstance(binding, Mapping) or binding.get('source') != entry or binding.get('target') != endpoint
                or binding.get('relation') != relation
                or binding.get('context_ids') != [cid] or binding.get('source_file') != method.path
                or p.get('source_id') != entry or p.get('source_file') != method.path
                or p.get('content_hash') != checksum or p.get('scope') != scope or p.get('context_ids') != [cid]
                or p.get('freshness') != 'CURRENT' or p.get('evidence_kind') not in ('FRAMEWORK_DERIVED', 'SYMBOL_RESOLVED')
                or original.get('kind') != p.get('evidence_kind') or original.get('source') != entry
                or original.get('target') != endpoint or original.get('relation') != binding.get('relation')
                or original.get('context_ids') != [cid] or original.get('source_file') != method.path
                or original.get('freshness') not in (None, 'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND')
                or original.get('sha256', checksum) != checksum
                or original.get('polarity', 'UNKNOWN') != p.get('polarity', 'UNKNOWN')
                or not any(e.source == entry and e.target == endpoint and e.kind == binding.get('relation')
                    and e.evidence_kind == original.get('kind') and list(e.context_ids) == [cid]
                    and sorted(e.evidence_ids) == binding.get('evidence_refs') and p['original_id'] in e.evidence_ids
                    and e.source_file == method.path and e.source_line == binding.get('source_line')
                    for e in graph.edges)):
            _fail('TRIGGER_PROOF_MISMATCH', 'Trigger declaration evidence no longer matches the supplied graph')
    return trigger, context, method, {ref: deepcopy(proofs[ref]) for ref in trigger.evidence_refs}


def _cfg_proofs(graph, context, nodes, symbols):
    """Select existing CFGs with exact canonical method/context/source witnesses."""
    originals = {p['id']: p for p in graph.evidence}; accepted = {}; proofs = {}
    for cfg in graph.cfgs:
        method = nodes.get(cfg.get('method')); symbol = symbols.get(cfg.get('method'))
        if (method is None or method.kind not in ('method','function','constructor') or symbol is None or cfg.get('context_id') != context['id']
                or method.scope != context['scope'] or symbol.get('context_id') != context['id']
                or symbol.get('path') != method.path or not _canonical_symbol(symbol, method, context)
                or cfg.get('representation') != 'SOURCE' or cfg.get('version') != CFG_VERSION
                or cfg.get('exceptional_exit') not in {b['id'] for b in cfg['blocks']}):
            continue
        checksum = _source_checksum(graph,context,method.path)
        if (checksum is None or symbol.get('sha256') != checksum
                or [n.scope for n in graph.nodes if n.kind == 'file' and n.path == method.path] != [context['scope']]):
            continue
        refs = cfg.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
            continue
        if any(not isinstance(b.get('kind'), str)
                or not isinstance(b.get('original_ids', []), list)
                or any(not isinstance(x, str) for x in b.get('original_ids', []))
                or not isinstance(b.get('call_site_ids', []), list)
                or any(not isinstance(x, str) for x in b.get('call_site_ids', []))
                or b.get('source_file') is not None and (b['source_file'] != method.path or b.get('sha256') != checksum)
                for b in cfg['blocks']):
            continue
        if any(not isinstance(e.get('kind'), str) or e.get('condition') is not None
                and not isinstance(e['condition'], str) for e in cfg['edges']):
            continue
        local = []
        for ref in refs:
            p = originals.get(ref, {})
            if (p.get('source') != method.id or p.get('target') != method.id or p.get('relation') != 'control_flow'
                    or p.get('context_ids') != [context['id']] or p.get('representation') != 'SOURCE'
                    or p.get('source_file') != method.path or p.get('sha256') != checksum
                    or p.get('kind') not in ('SYNTAX_CANDIDATE', 'SYMBOL_RESOLVED')
                    or p.get('freshness') not in (None, 'CURRENT', 'CONTENT_VERIFIED', 'EXECUTION_BOUND')):
                break
            local.append({'id': 'ev:process-cfg:' + ref, 'source_id': method.id, 'original_id': ref,
                'source_file': method.path, 'content_hash': checksum, 'context_ids': [context['id']],
                'scope': context['scope'], 'evidence_kind': p['kind'], 'freshness': 'CURRENT',
                'polarity': p.get('polarity', 'UNKNOWN')})
        else:
            if method.id in accepted:
                _fail('AMBIGUOUS_PROCESS_CFG', 'Multiple source CFGs for one selected method')
            accepted[method.id] = cfg
            proofs[method.id] = local
    return accepted, proofs


def _proved_sites(graph, context, nodes, symbols):
    evidence = {p['id']: p for p in graph.evidence}; accepted = []; admitted_proofs={}
    def canonical(value, expected):
        return value == expected or isinstance(value, str) and qualified(context['repo_id'], value) == expected
    for site in graph.call_sites:
        node = nodes.get(site['id']); caller = nodes.get(site.get('caller')); symbol = symbols.get(site.get('caller'))
        if (node is None or node.kind != 'call_site' or caller is None or symbol is None or site.get('context_id') != context['id']
                or node.scope != context['scope'] or node.path != caller.path or site.get('path') != caller.path
                or _source_checksum(graph,context,caller.path) is None
                or site.get('sha256') != _source_checksum(graph,context,caller.path)
                or node.name != site.get('invocation_kind')
                or not isinstance(site.get('range'), Mapping) or site['range'].get('start_line') != node.line
                or not _canonical_symbol(symbol,caller,context)):
            continue
        meta = node.metadata if isinstance(node.metadata,Mapping) else {}
        if any(key in meta and not canonical(meta[key],site.get(key)) for key in ('id','caller','declared_target','context_id')):
            continue
        if 'path' in meta and meta['path'] not in (site.get('path'), site.get('path', '').removeprefix('@'+context['repo_id']+'/')):
            continue
        if any(key in meta and meta[key] != site.get(key) for key in ('sha256','range','invocation_kind','dispatch_complete','receiver_type','dispatch_receiver')):
            continue
        if 'dispatch_candidates' in meta:
            candidates=site.get('dispatch_candidates',[])
            if (not isinstance(meta['dispatch_candidates'],list)
                    or any(not isinstance(x,str) for x in meta['dispatch_candidates'])
                    or sorted(x if x in candidates else qualified(context['repo_id'],x) for x in meta['dispatch_candidates'])
                    != sorted(candidates)):
                continue
        refs = [evidence.get(ref,{}) for ref in site.get('evidence_ids',[])]
        def proof(p, source, target, relation):
            return (p.get('kind') == 'SYMBOL_RESOLVED' and p.get('source') == source and p.get('target') == target
                and p.get('relation') == relation and p.get('context_ids') == [context['id']]
                and p.get('source_file') == caller.path and p.get('sha256') == site['sha256']
                and p.get('source_range') == site['range']
                and p.get('freshness') in (None,'CURRENT','CONTENT_VERIFIED','EXECUTION_BOUND')
                and any(e.source == source and e.target == target and e.kind == relation
                    and e.evidence_kind == 'SYMBOL_RESOLVED' and e.context_ids == (context['id'],)
                    and p.get('id') in e.evidence_ids and e.source_file == caller.path and e.source_line == node.line
                    for e in graph.edges))
        if not any(proof(p,caller.id,site['id'],'declares_call') for p in refs):continue
        if site.get('declared_target') and not any(proof(p,site['id'],site['declared_target'],'resolves_to') for p in refs):continue
        # Current capture stores invocation kind in the canonical node label,
        # but has no separate receiver/complete-dispatch witness in that node.
        # Such virtual sites retain their original identity as boundaries even
        # if a mutable site-table flag claims complete dispatch.
        if site.get('invocation_kind') in ('VIRTUAL','INTERFACE','INVOKEVIRTUAL','INVOKEINTERFACE') or (
                site.get('invocation_kind') == 'CALL' and site.get('receiver_type')):
            if not meta or not all(key in meta for key in ('dispatch_complete','receiver_type','dispatch_candidates')):
                site={**site,'dispatch_complete':False}
        accepted.append(site)
        admitted_proofs[site['id']]=[deepcopy(p) for p in refs if
            proof(p,caller.id,site['id'],'declares_call')
            or proof(p,site['id'],site.get('declared_target'),'resolves_to')]
    return accepted,admitted_proofs


def _build_local_process(graph, trigger_inventory, trigger_id, *, process_id, revision=1,
                        max_depth=3, max_nodes=500):
    """Adapt explicit supplied snapshots, without refreshing a physical checkout."""
    if (not isinstance(process_id, str) or not process_id or type(revision) is not int or revision < 1
            or type(max_depth) is not int or max_depth < 0 or type(max_nodes) is not int or max_nodes < 1):
        _fail('INVALID_PROCESS_REQUEST', 'Process identity, revision and traversal limits must be explicit')
    try:
        json.dumps(graph.to_dict(),allow_nan=False)
        graph = KnowledgeGraph.from_dict(deepcopy(graph.to_dict()))
        inventory = ViewDocument.from_dict(deepcopy(trigger_inventory.to_dict() if isinstance(trigger_inventory, ViewDocument) else trigger_inventory))
        trigger, context, entry, provenance = _selected_trigger(graph, inventory, trigger_id)
        selected = project(graph, inventory.scope, context_id=context['id'])
        nodes = {n.id:n for n in selected.nodes}; symbols = {s['id']:s for s in selected.symbols}
        cfgs, cfg_proofs = _cfg_proofs(selected, context, nodes, symbols)
        proved_sites,site_proofs=_proved_sites(selected,context,nodes,symbols)
        selected = replace(selected, call_sites=proved_sites)
    except ProcessPathError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ProcessPathError('INVALID_PROCESS_INPUT', 'Malformed graph or trigger inventory') from error
    diagnostics = []; technical_nodes = []; technical_edges = []
    attrs = deepcopy(dict(trigger.attributes));attrs.update(scope=inventory.scope,context_ids=[context['id']])
    if max_nodes == 1:
        attrs['boundary_reason'] = 'node limit'
    technical_nodes.append(replace(trigger,attributes=attrs))
    def boundary(reason):
        identity = 'process-boundary:' + digest([trigger.id,entry.id,reason])
        technical_nodes.append(ViewNode(identity,'unresolved_boundary',reason,original_ids=(entry.id,),
            owner_id=trigger.owner_id,attributes={'scope':inventory.scope,'context_ids':[context['id']],
                'boundary_reason':reason},resolution_status='UNRESOLVED',freshness='UNKNOWN'))
        diagnostics.append({'code':'PROCESS_ENTRY_UNAVAILABLE','method':entry.id,'reason':reason})
        return identity
    report = None
    if max_nodes == 1:
        diagnostics.append({'code':'PROCESS_NODE_LIMIT','method':entry.id});exits=[]
    elif entry.id not in cfgs or attrs.get('body_status') not in ('AVAILABLE','PARTIAL'):
        boundary('source body unavailable');exits=[]
    else:
        selected = replace(selected,cfgs=list(cfgs.values()))
        report = process(selected,entry.id,scope=inventory.scope,max_depth=max_depth,max_nodes=max_nodes-1)
        diagnostics.extend(deepcopy(report['diagnostics']))
        diagnostics.extend({'code':'PROCESS_BOUNDARY',**deepcopy(row)} for row in report['boundaries'])
        for block in report['cfg']['blocks']:
            method = block.get('method');proofs = cfg_proofs.get(method,[])
            for p in proofs:provenance[p['id']]=p
            refs=tuple(p['id'] for p in proofs);summary=_summarize_view_evidence(refs,provenance)
            reason=block.get('boundary_reason')
            kind='unresolved_boundary' if reason else block['kind'] if block['kind'] in STEP_KINDS else 'unresolved_boundary'
            attributes={'scope':inventory.scope,'context_ids':[context['id']], 'method':method,
                'call_site_ids':list(block.get('call_site_ids',[]))}
            if reason or kind=='unresolved_boundary':attributes['boundary_reason']=reason or 'unsupported CFG block'
            technical_nodes.append(ViewNode(block['id'],kind,block.get('label',kind),
                original_ids=tuple(sorted(set(block.get('original_ids',[])+[method]))),owner_id=trigger.owner_id,
                evidence_refs=refs,attributes=attributes,evidence_kinds=tuple(summary['evidence_kinds']),
                resolution_status='UNRESOLVED',freshness=summary['freshness'],
                supporting_refs=tuple(summary['supporting_refs']),contradicting_refs=tuple(summary['contradicting_refs']),
                unknown_refs=tuple(summary['unknown_refs'])))
        by_id={n.id:n for n in technical_nodes}
        for e in report['cfg']['edges']:
            source,target=by_id[e['source']],by_id[e['target']]
            call_site=e.get('call_site');call_refs=[]
            for original in site_proofs.get(call_site,[]):
                identity='ev:process-call:'+original['id'];call_refs.append(identity)
                provenance[identity]={'id':identity,'original_id':original['id'],
                    'source_id':original['source'],'source_file':original['source_file'],
                    'source_range':deepcopy(original['source_range']),'content_hash':original['sha256'],
                    'context_ids':[context['id']],'scope':inventory.scope,'evidence_kind':original['kind'],
                    'freshness':'CURRENT','polarity':original.get('polarity','UNKNOWN'),
                    'original_relation':original['relation'],'original_target':original['target']}
            refs=tuple(sorted(set(source.evidence_refs)|set(target.evidence_refs)|set(call_refs)))
            summary=_summarize_view_evidence(refs,provenance);kind=e['kind'] if e['kind'] in TRANSITION_KINDS else 'unknown'
            attributes={'scope':inventory.scope,'context_ids':[context['id']], 'loop_back':e.get('loop_back',False)}
            if call_site is not None:attributes['call_site']=call_site
            if e.get('caller_block') is not None:attributes['caller_block']=e['caller_block']
            if kind in ('branch','true','false','case'):attributes['condition']=str(e.get('condition') or kind)
            technical_edges.append(ViewEdge('process-edge:'+digest(e),e['source'],e['target'],kind,
                original_ids=tuple(sorted(set(e.get('original_ids') or [digest(e)])|({call_site} if call_site else set()))),evidence_refs=refs,attributes=attributes,
                evidence_kinds=tuple(summary['evidence_kinds']),resolution_status='UNRESOLVED',freshness=summary['freshness'],
                supporting_refs=tuple(summary['supporting_refs']),contradicting_refs=tuple(summary['contradicting_refs']),
                unknown_refs=tuple(summary['unknown_refs'])))
        exits=sorted({report['cfg']['exit'],report['cfg']['exceptional_exit']})
    # The inventory trigger is a declaration entry, not evidence that its body executes.
    first = report['cfg']['entry'] if report else technical_nodes[-1].id if len(technical_nodes)>1 else None
    if first is not None:
        technical_edges.append(ViewEdge('process-entry:'+digest([trigger.id,first]),trigger.id,first,'unknown',
            original_ids=(entry.id,trigger.id),attributes={'scope':inventory.scope,'context_ids':[context['id']],
                'boundary_reason':'declaration-to-body static association'},resolution_status='UNRESOLVED',freshness='UNKNOWN'))
    snapshot=selected.to_dict()
    bound_snapshot={key: sorted(digest(item) for item in snapshot.get(key,[]))
        for key in ('nodes','edges','contexts','symbols','call_sites','cfgs','evidence')}
    bound_snapshot['files']=snapshot['files']
    baseline=digest({'inventory':inventory.content_fingerprint,'graph':bound_snapshot,
        'trigger':trigger.id,'limits':[max_depth,max_nodes]})
    view=ViewDocument(process_id,'process',baseline,VERSION,inventory.scope,deepcopy(inventory.context_selection),
        nodes=tuple(technical_nodes),edges=tuple(technical_edges),diagnostics=tuple(diagnostics),
        coverage={'status':'PARTIAL','truncated':bool(max_nodes==1 or report and report['truncated'])},
        provenance=tuple(provenance.values()),limits=('Static source topology; no observed execution or business equivalence.',
            'Input provider freshness is supplied; physical checkout is not read or refreshed.'))
    definition=ProcessDefinition.from_dict({'schema_version':1,'process_id':process_id,'revision':revision,
        'baseline_fingerprint':baseline,'scope':inventory.scope,'context_selection':deepcopy(inventory.context_selection),
        'context_ids':[context['id']],'trigger_ids':[trigger.id],'semantic_review_status':'PROPOSED'})
    return ProcessView.from_dict({'schema_version':1,'process_id':process_id,'revision':revision,
        'definition':definition.to_dict(),'definition_fingerprint':definition.content_fingerprint,
        'technical_status':'PARTIAL','technical_view':view.to_dict(),'entry_ids':[trigger.id],
        'exit_ids':exits,'outcome_ids':[],'semantic_annotations':[]})


def build_local_process(graph, trigger_inventory, trigger_id, *, process_id, revision=1,
                        max_depth=3, max_nodes=500):
    """Return an immutable typed process; malformed inputs fail without writes."""
    try:
        return _build_local_process(graph,trigger_inventory,trigger_id,process_id=process_id,
            revision=revision,max_depth=max_depth,max_nodes=max_nodes)
    except ProcessPathError:
        raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError) as error:
        raise ProcessPathError('INVALID_PROCESS_INPUT','Malformed graph or process document') from error

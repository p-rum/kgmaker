"""Read-only catalog of explicit technical snapshots and local review history.

No discovery, archive reconstruction, fuzzy identity or semantic store write.
An inventory's partial absence is not proof of universal trigger deletion.
"""
from pathlib import Path

from .analysis_model import canonical, digest
from .architecture_model import ViewDocument, ViewNode, ViewValidationError
from .process_model import ProcessView
from .process_semantics import _bounded, _identifier, _BOUNDARIES, ProcessLabelPacketError
from .process_store import read_process_reviews, ProcessReviewError
from .process_triggers import VERSION as TRIGGER_VERSION

VERSION='process-catalog-1'
MAX_SNAPSHOTS=256
MAX_TRIGGER_NODES=4096
MAX_OUTPUT_BYTES=2*1024*1024


class ProcessCatalogError(ValueError):
    """Fixed diagnostic codes; no raw model paths, prose or store errors."""
    def __init__(self,code):
        self.diagnostic={'code':code}
        super().__init__(code)


def _fail(code):
    raise ProcessCatalogError(code) from None


def _id(value):
    try:return _identifier(value)
    except ProcessLabelPacketError:_fail('UNSAFE_IDENTIFIER')


def _ids(values):
    if type(values) not in (list,tuple):_fail('INVALID_REFERENCE_LIST')
    return sorted({_id(value) for value in values})


def _snapshot(value):
    try:
        raw=value._document if type(value) is ProcessView else value
        _bounded(raw)
        model=ProcessView.from_dict(raw)
        # T030's bounded packet validates immutable IDs and safely binds omitted
        # presentation/context data; direct T032 reads rederive it again.
        from .process_semantics import prepare_process_label_packet
        packet=prepare_process_label_packet(model)['packet']
        return model,packet['identity']
    except (ViewValidationError,ProcessLabelPacketError,UnicodeError,TypeError,RecursionError):
        _fail('INVALID_PROCESS_SNAPSHOT')


def _inventory(value):
    try:
        raw=value.to_dict() if type(value) is ViewDocument else value
        _bounded(raw)
        model=ViewDocument.from_dict(raw)
        if (model.kind!='process' or model.rules_version!=TRIGGER_VERSION or model.edges
                or len(model.nodes)>MAX_TRIGGER_NODES or any(n.kind!='trigger' for n in model.nodes)):
            _fail('INVALID_TRIGGER_INVENTORY')
        _id(model.scope);_id(model.view_id)
        return model
    except (ViewValidationError,ProcessLabelPacketError,UnicodeError,TypeError,RecursionError):
        _fail('INVALID_TRIGGER_INVENTORY')


def _trigger(node,identity):
    attrs=node.attributes
    if attrs.get('scope')!=identity['scope']:_fail('TRIGGER_SCOPE_MISMATCH')
    contexts=_ids(attrs.get('context_ids'))
    selected=bool(contexts) and set(contexts)<=set(identity['context_ids'])
    eligible=selected and node.freshness=='CURRENT'
    result={'id':_id(node.id),'presence':'PRESENT' if selected else 'CONTEXT_NOT_SELECTED','in_current_selection':eligible,
        'context_ids':contexts,'owner_id':_id(node.owner_id) if node.owner_id is not None else None,
        'candidate_owner_ids':_ids(attrs.get('candidate_owner_ids',[])),
        'original_ids':_ids(node.original_ids),'evidence_refs':_ids(node.evidence_refs),
        'evidence_kinds':list(node.evidence_kinds),'resolution_status':node.resolution_status,
        'freshness':node.freshness,'supporting_refs':_ids(node.supporting_refs),
        'contradicting_refs':_ids(node.contradicting_refs),'unknown_refs':_ids(node.unknown_refs)}
    enums={'trigger_kind':{'HTTP','KAFKA','SCHEDULER'},'owner_status':{'RESOLVED','AMBIGUOUS','UNASSIGNED'},
        'body_status':{'AVAILABLE','PARTIAL','UNAVAILABLE'},
        'registration_status':{'UNKNOWN'},'execution_status':{'UNKNOWN'},'data_availability':{'UNKNOWN'}}
    for field,allowed in enums.items():
        value=attrs.get(field)
        if type(value) is not str or value not in allowed:_fail('INVALID_TRIGGER_FACT')
        result[field]=value
    for field in ('entry_symbol_id','entrypoint_id','repo_id'):
        result[field]=_id(attrs.get(field))
    result['body_evidence_refs']=_ids(attrs.get('body_evidence_refs',[]))
    kinds=attrs.get('body_evidence_kinds',[])
    if type(kinds) not in (list,tuple) or any(k not in ('SYNTAX_CANDIDATE','SYMBOL_RESOLVED') for k in kinds):
        _fail('INVALID_TRIGGER_FACT')
    result['body_evidence_kinds']=sorted(set(kinds))
    return result


def _captures(rows,identities):
    if type(rows) not in (list,tuple) or len(rows)>MAX_SNAPSHOTS:_fail('INVALID_REVIEW_INPUTS')
    result={}
    for row in rows:
        if type(row) is not dict or set(row)!={'process_id','documents','conflicts'}:_fail('INVALID_REVIEW_INPUTS')
        identity=_id(row['process_id'])
        if identity not in identities or identity in result:_fail('INVALID_REVIEW_INPUTS')
        result[identity]={'documents':row['documents'],'conflicts':row['conflicts']}
    return result


def _aliases(rows,snapshots):
    if type(rows) not in (list,tuple) or len(rows)>MAX_SNAPSHOTS:_fail('INVALID_ALIAS')
    result={}
    for row in rows:
        if type(row) is not dict or set(row)!={'alias_process_id','canonical_process_id'}:_fail('INVALID_ALIAS')
        alias=_id(row['alias_process_id']);target=_id(row['canonical_process_id'])
        if alias==target or alias not in snapshots or target not in snapshots:_fail('INVALID_ALIAS')
        if alias in result and result[alias]!=target:_fail('INVALID_ALIAS')
        result[alias]=target
    if set(result)&set(result.values()):_fail('INVALID_ALIAS')
    for alias,target in result.items():
        selections={canonical({'scope':identity['scope'],'context_ids':identity['context_ids'],
            'context_selection':identity['context_selection']})
            for name in (alias,target) for _,identity in snapshots[name].values()}
        if len(selections)!=1:_fail('ALIAS_CONTEXT_MISMATCH')
    return result


def _review(root,model,captures,historical):
    try:review=read_process_reviews(root,model,**captures)
    except (ProcessReviewError,ProcessLabelPacketError,UnicodeError):_fail('INVALID_REVIEW_STORE_OR_INPUT')
    if historical:review['active_annotations']=[]
    return review


def _record(root,model,identity,triggers,captures,designation):
    value=model.to_dict();selected=[]
    for trigger_id in sorted(value['definition']['trigger_ids']):
        node=triggers.get(trigger_id)
        selected.append(_trigger(node,identity) if node is not None else {
            'id':_id(trigger_id),'presence':'NOT_IN_CURRENT_INVENTORY','in_current_selection':False,
            'execution_status':'UNKNOWN','data_availability':'UNKNOWN'})
    present=bool(selected) and all(t['in_current_selection'] for t in selected)
    historical=designation=='HISTORICAL' or not present
    review=_review(root,model,captures,historical)
    status=review['effective_status']
    lifecycle=('HISTORICAL' if historical else 'NEEDS_REVALIDATION' if status=='NEEDS_REVALIDATION'
        else 'REVIEWED' if status=='APPROVED' else 'CANDIDATE')
    view=value['technical_view']
    # Prose/config/proof metadata is not catalog authority. Keep coverage structure
    # content-bound rather than copying arbitrary nested user text.
    coverage={'status':view['coverage']['status'],'content_hash':digest(view['coverage']),
        'truncated':view['coverage'].get('truncated') is True}
    return {'designation':designation,'lifecycle':lifecycle,'revision':identity['revision'],
        'definition_fingerprint':identity['definition_fingerprint'],
        'technical_fingerprint':identity['technical_fingerprint'],
        'process_content_hash':identity['process_content_hash'],
        'baseline_fingerprint':identity['baseline_fingerprint'],
        'context_ids':identity['context_ids'],'context_selection_hash':identity['context_selection_hash'],
        'in_current_selection':designation=='CURRENT' and present,'triggers':selected,
        'technical_status':value['technical_status'],'technical_coverage':coverage,
        'technical_limits_hash':digest(view['limits']),
        'omissions':[{'field':'technical_limits','reason':'RAW_TECHNICAL_PROSE_OMITTED','content_hash':digest(view['limits'])}],
        'uncertainty':{'target_ids':sorted({_id(n.id) for n in model.technical_view.nodes
            if n.kind in _BOUNDARIES or n.resolution_status!='RESOLVED' or n.freshness!='CURRENT'}
            | {_id(e.id) for e in model.technical_view.edges if e.resolution_status!='RESOLVED' or e.freshness!='CURRENT'}),
            'truncated':view['coverage'].get('truncated') is True,
            'diagnostic_count':len(view['diagnostics']),'diagnostics_hash':digest(view['diagnostics'])},
        'entry_ids':_ids(value['entry_ids']),
        'exit_ids':_ids(value['exit_ids']),'outcome_ids':_ids(value['outcome_ids']),
        'outcomes':[{'id':_id(node.id),'original_ids':_ids(node.original_ids),
            'evidence_refs':_ids(node.evidence_refs),'evidence_kinds':list(node.evidence_kinds),
            'resolution_status':node.resolution_status,'freshness':node.freshness}
            for node in sorted(model.technical_view.nodes,key=lambda n:n.id) if node.id in set(value['outcome_ids'])],
        'technical_owner_ids':_ids([node.owner_id for node in model.technical_view.nodes if node.owner_id is not None]),
        'review':review,'registration_status':'UNKNOWN','execution_status':'UNKNOWN',
        'data_availability':'UNKNOWN'}


def catalog_business_processes(root,trigger_inventory,*,current_processes=(),historical_processes=(),
        review_inputs=(),aliases=()):
    """Catalog only explicit snapshots; reads supplied T032 root, never writes."""
    try:
        if type(trigger_inventory) is ViewDocument:
            if len(trigger_inventory.nodes)>MAX_TRIGGER_NODES or trigger_inventory.edges:
                _fail('INVALID_TRIGGER_INVENTORY')
            if any(type(node) is not ViewNode for node in trigger_inventory.nodes):
                _fail('INVALID_TRIGGER_INVENTORY')
            # Shallow structural view before any model serializer/deepcopy.
            raw_inventory={**vars(trigger_inventory),'nodes':[vars(n) for n in trigger_inventory.nodes],
                'edges':[]}
        else:raw_inventory=trigger_inventory
        for values in (current_processes,historical_processes):
            if type(values) not in (list,tuple):_fail('INVALID_SNAPSHOT_COLLECTION')
        if len(current_processes)+len(historical_processes)>MAX_SNAPSHOTS:_fail('SNAPSHOT_LIMIT')
        raw_processes=[p._document if type(p) is ProcessView else p for p in (*current_processes,*historical_processes)]
        _bounded([raw_inventory,raw_processes,review_inputs,aliases])
        approved_root=Path(root)
        if approved_root.is_symlink() or not approved_root.is_dir():_fail('INVALID_STORE_ROOT')
        inventory=_inventory(trigger_inventory);triggers={node.id:node for node in inventory.nodes}
        snapshots={};current={};history={}
        for designation,values in [('CURRENT',current_processes),('HISTORICAL',historical_processes)]:
            for supplied in values:
                model,identity=_snapshot(supplied);name=identity['process_id'];revision=identity['revision']
                if identity['scope']!=inventory.scope:_fail('PROCESS_SCOPE_MISMATCH')
                versions=snapshots.setdefault(name,{})
                if revision in versions and versions[revision][0].content_fingerprint!=model.content_fingerprint:
                    _fail('CONFLICTING_PROCESS_SNAPSHOT')
                versions[revision]=(model,identity)
                if designation=='CURRENT':
                    if name in current and current[name][0].content_fingerprint!=model.content_fingerprint:
                        _fail('CONFLICTING_PROCESS_SNAPSHOT')
                    current[name]=(model,identity)
                else:history.setdefault(name,set()).add(revision)
        captures=_captures(review_inputs,snapshots);alias_map=_aliases(aliases,snapshots)
        grouped={}
        for name,versions in sorted(snapshots.items()):
            selected=current.get(name)
            now=_record(approved_root,*selected,triggers,captures.get(name,{}),'CURRENT') if selected else None
            old=[]
            for revision in sorted(history.get(name,())):
                # Exact current duplicates are represented once, as current.
                if selected and revision==selected[1]['revision']:continue
                old.append(_record(approved_root,*versions[revision],triggers,captures.get(name,{}),'HISTORICAL'))
            member={'process_id':name,'scope':inventory.scope,'current':now,'historical':old}
            grouped.setdefault(alias_map.get(name,name),[]).append(member)
            # Check aggregate before further copies/read bundles; accumulation
            # cannot grow to snapshots*maximum store size.
            _bounded(grouped)
        rows=[{'process_id':canonical_id,'scope':inventory.scope,
            'selection_id':'process-selection:'+digest({'process_id':canonical_id,'scope':inventory.scope}),
            'member_ids':sorted(m['process_id'] for m in members),'members':members}
            for canonical_id,members in sorted(grouped.items())]
        result={'schema_version':1,'rules_version':VERSION,'scope':inventory.scope,
            'inventory_id':_id(inventory.view_id),'inventory_fingerprint':inventory.content_fingerprint,
            'inventory_coverage':{'status':inventory.coverage['status'],'content_hash':digest(inventory.coverage)},
            'inventory_context_selection_hash':digest(inventory.context_selection),'rows':rows,
            'counts':{'groups':len(rows),'members':len(snapshots),'current':len(current),
                'historical_snapshots':sum(len(m['historical']) for ms in grouped.values() for m in ms)},
            'identity_assurance':'LOCAL_DECLARATION_NOT_AUTHENTICATED',
            'absence_semantics':'NOT_IN_CURRENT_INVENTORY_IS_NOT_UNIVERSAL_DELETION',
            'registration_status':'UNKNOWN','execution_status':'UNKNOWN','data_availability':'UNKNOWN'}
        _bounded(result)
        if len(canonical(result).encode('utf-8'))>MAX_OUTPUT_BYTES:_fail('CATALOG_SIZE_LIMIT')
        return result
    except (ProcessLabelPacketError,ViewValidationError,UnicodeError,TypeError,RecursionError,OSError):
        _fail('INVALID_CATALOG_INPUT')

"""Pure T014 projection of the existing trusted W07 capture handoff."""
from copy import deepcopy
import unicodedata

from .analysis_model import canonical
from .architecture_model import ViewDocument, ViewNode, ViewEdge
from .remote_mapping import resolve_remote_mappings, _bounded, _text, digest, RemoteMappingError

VERSION = 'remote-interface-view-1'
_MAX_OBJECTS = 20000


def _fail(code):
    raise RemoteMappingError(code) from None


def _ref(value):
    if not _text(value) or any(unicodedata.category(c) in {'Cc','Cf','Cs','Zl','Zp'} for c in value):
        _fail('REMOTE_VIEW_UNSAFE_REFERENCE')
    return value


def _refs(values):
    if not isinstance(values,(list,tuple)):_fail('REMOTE_VIEW_INVALID_REFERENCES')
    return tuple(sorted({_ref(v) for v in values}))


def _node(value, scope):
    """Preserve identity/status/buckets, omit raw labels and payload attributes."""
    attrs=value['attributes']
    if attrs.get('scope',scope)!=scope:_fail('REMOTE_VIEW_SCOPE_MISMATCH')
    for key in ('origin_id', 'subscription_id'):
        if (value['kind'] == 'kafka_interface' and attrs.get(key) is not None
                and attrs[key] not in value['original_ids']):
            _fail('REMOTE_VIEW_KAFKA_ORIGINAL_ID_MISMATCH')
    safe={}
    for key in ('service_id','direction','context_id','code_binding','subscription_kind',
                'execution_status','payload_compatibility','caller','origin_call_site',
                'terminal_call_site','request_definition_id','declaration_id','code_fact_id',
                'broker_realm','consumer_group','topic_pattern','origin_id','subscription_id',
                'subscription_logical_id','http_method',
                'route_expression','normalized_route'):
        if key in {'origin_id','subscription_id','subscription_logical_id'} and value['kind'] != 'kafka_interface':
            continue
        if attrs.get(key) is not None:safe[key]=_ref(attrs[key])
    for key in ('context_ids','topics','handler_ids'):
        if key in attrs:safe[key]=list(_refs(attrs[key]))
    safe.update(scope=_ref(scope), original_attributes_hash=digest(attrs))
    return ViewNode(_ref(value['id']),_ref(value['kind']),'Captured interface',
        original_ids=_refs(value['original_ids']),owner_id=_ref(value['owner_id']) if value['owner_id'] else None,
        evidence_refs=_refs(value['evidence_refs']),attributes=safe,
        evidence_kinds=tuple(value['evidence_kinds']),resolution_status=value['resolution_status'],
        freshness=value['freshness'],supporting_refs=_refs(value['supporting_refs']),
        contradicting_refs=_refs(value['contradicting_refs']),unknown_refs=_refs(value['unknown_refs']))


def _proof(value):
    # Shared model validates enums before this allowlist is consumed.
    result={'id':_ref(value['id'])}
    for key in ('evidence_kind','freshness','polarity'):
        result[key]=value.get(key,'UNKNOWN')
    for key in ('source_id','original_id','scope'):
        if value.get(key) is not None:result[key]=_ref(value[key])
    for key in ('context_ids','source_refs','original_ids','original_evidence_ids','compiler_evidence_ids'):
        if key in value:result[key]=list(_refs(value[key]))
    result['original_payload_hash']=digest(value)
    return result


def project_remote_interfaces(workspace, graph, interfaces, *, captured,
                              scope='production', selected_contexts=None):
    """Return static remote topology; never capture, discover, execute or apply.

    Capture consistency is supplied authority, not physical source freshness or
    authentication of arbitrary replacement JSON. Every derived claim is UNKNOWN
    freshness and has only a SOURCE_ONLY declaration proof with UNKNOWN polarity.
    """
    _bounded((workspace,graph,interfaces,captured,selected_contexts))
    report=resolve_remote_mappings(workspace,graph,interfaces,captured=captured,
                                   scope=scope,selected_contexts=selected_contexts)
    documents=captured['canonical_interfaces']
    _ref(workspace['workspace_id']);_ref(scope)
    nodes={};proofs={};originals={};diagnostics=[]
    for document in documents:
        for value in document['nodes']:
            identity=_ref(value['id'])
            if identity in originals and originals[identity]!=value:_fail('REMOTE_VIEW_NODE_COLLISION')
            originals[identity]=value
            nodes[identity]=_node(value,scope)
        for value in document['provenance']:
            proof=_proof(value)
            if proof['id'] in proofs and proofs[proof['id']]!=proof:_fail('REMOTE_VIEW_PROOF_COLLISION')
            proofs[proof['id']]=proof
        diagnostics.append({'code':'REMOTE_UPSTREAM_COVERAGE','view_id':_ref(document['view_id']),
            'coverage_hash':digest(document['coverage']),'diagnostics_hash':digest(document['diagnostics']),
            'diagnostic_count':len(document['diagnostics']),
            'coverage_status':document['coverage']['status'],
            'truncated':document['coverage'].get('truncated') is True})
    edges=[];mapped=set();releases={r['id']:r for r in captured['remote_declarations']['releases']}
    def add_node(node):
        if node.id in nodes:_fail('REMOTE_VIEW_NODE_COLLISION')
        nodes[node.id]=node
    def declaration(identity, contexts, mapping_ids):
        identity='remote-declaration:'+digest([VERSION,captured['capture_id'],identity])
        record={'id':identity,'evidence_kind':'SOURCE_ONLY','freshness':'UNKNOWN','polarity':'UNKNOWN',
            'scope':scope,'context_ids':list(_refs(contexts)),'capture_id':captured['capture_id'],
            'mapping_ids':list(_refs(mapping_ids))}
        if identity in proofs and proofs[identity]!=record:_fail('REMOTE_VIEW_PROOF_COLLISION')
        proofs[identity]=record
        return identity
    for row in report['bindings']:
        source=_ref(row['source_interface_id']);release=_ref(row['source_release_id']);mapped.add(source)
        selected=releases[release];contexts=[_ref(selected['context_id'])]
        binding='remote-binding:'+digest([VERSION,workspace['workspace_id'],release,source])
        proof=declaration(binding,contexts,row['mapping_ids'])
        common={k:deepcopy(row[k]) for k in ('transport','resolution_status','mapping_ids',
            'unresolved_mapping_ids','reasons','runtime_execution','delivery','runtime_availability',
            'deployment','payload_compatibility')}
        for key in ('mapping_ids','unresolved_mapping_ids','reasons'):_refs(common[key])
        if 'execution_intent' in row:common['execution_intent']=_ref(row['execution_intent'])
        mapping_index={m['id']:m for m in captured['remote_declarations']['mappings']}
        common['unresolved_selectors']=[]
        for mapping_id in row['unresolved_mapping_ids']:
            target_release=releases[mapping_index[mapping_id]['target_release_id']]
            selector={k:_ref(target_release[k]) for k in ('id','service_id','interface_id','context_id','release')}
            common['unresolved_selectors'].append({'mapping_id':mapping_id,**selector})
            boundary='remote-boundary:'+digest([VERSION,binding,mapping_id,target_release['id']])
            add_node(ViewNode(boundary,'unresolved_remote_target','Unresolved declared target',
                original_ids=_refs([mapping_id,target_release['id'],target_release['interface_id']]),
                attributes={'scope':scope,'context_ids':contexts,'source_interface_id':source,
                    'target_selector':selector,'mapping_id':mapping_id,'binding_id':binding,
                    'capture_freshness':'CAPTURE_TIME_ONLY','runtime_availability':'UNKNOWN'}))
        common.update(scope=scope,context_ids=contexts,capture_freshness='CAPTURE_TIME_ONLY',
            source_interface_id=source,source_release_id=release,candidates=deepcopy(row['candidates']))
        # Contract/path/release IDs are validated by W07. Check every exported
        # candidate identity against the same privacy policy, including context refs.
        for candidate in common['candidates']:
            for key in ('target_interface_id','target_service_id','target_release_id','mapping_id'):_ref(candidate[key])
            _refs(candidate['context_ids']);_refs(candidate['evidence_refs'])
            if candidate['consumer_group'] is not None:_ref(candidate['consumer_group'])
            for contract in (candidate['source_contract'],candidate['target_contract']):
                for value in contract.values():
                    if value:_ref(value)
        add_node(ViewNode(binding,'remote_binding','Static remote declaration',
            original_ids=_refs([source,release,*row['mapping_ids']]),evidence_refs=(proof,),
            attributes=common,evidence_kinds=('SOURCE_ONLY',),resolution_status=row['resolution_status'],
            freshness='UNKNOWN',unknown_refs=(proof,)))
        if source not in nodes:
            boundary='remote-boundary:'+digest([VERSION,binding,source])
            add_node(ViewNode(boundary,'unresolved_remote_target','Unresolved remote selector',
                original_ids=(source,),attributes={'scope':scope,'context_ids':contexts,
                'source_release_id':release,'reason':'REMOTE_SOURCE_INTERFACE_UNAVAILABLE'}))
        for candidate in row['candidates']:
            target=candidate['target_interface_id']
            if source not in nodes or target not in nodes:_fail('REMOTE_VIEW_CANDIDATE_ENDPOINT_MISSING')
            claim='remote-edge:'+digest([VERSION,binding,candidate])
            ev=declaration(claim,candidate['context_ids'],[candidate['mapping_id']])
            attrs={**deepcopy(candidate),'scope':scope,'capture_freshness':'CAPTURE_TIME_ONLY',
                'original_evidence_refs':list(candidate['evidence_refs']),
                'runtime_execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED','runtime_availability':'UNKNOWN',
                'deployment':'UNKNOWN','payload_compatibility':'UNKNOWN',
                'source_contract_authority':'MANIFEST_EXPECTATION' if row['transport']=='HTTP' else 'BOUND_DECLARATION',
                'target_contract_authority':'BOUND_DECLARATION','binding_id':binding,
                'execution_intent':common.get('execution_intent','UNKNOWN')}
            edges.append(ViewEdge(claim,source,target,
                'remote_http_request_response' if row['transport']=='HTTP' else 'remote_kafka_publish_subscribe',
                original_ids=_refs([candidate['mapping_id'],release,candidate['target_release_id']]),
                evidence_refs=(ev,),resolution_status=row['resolution_status'],attributes=attrs,
                evidence_kinds=('SOURCE_ONLY',),freshness='UNKNOWN',unknown_refs=(ev,)))
    for identity,value in originals.items():
        if identity in mapped:continue
        attrs=value['attributes'];direction=attrs.get('direction')
        if value['kind'] not in {'http_interface','kafka_interface'}:continue
        if (value['kind']=='http_interface' and direction!='CONSUMER'
                or value['kind']=='kafka_interface' and direction!='PRODUCER'):continue
        boundary='remote-boundary:'+digest([VERSION,workspace['workspace_id'],identity])
        add_node(ViewNode(boundary,'unresolved_remote_target','No explicit remote mapping',
            original_ids=(identity,),attributes={'scope':scope,'context_ids':list(_refs(attrs.get('context_ids',[]))),
                'source_interface_id':identity,'reason':'NO_EXPLICIT_REMOTE_MAPPING',
                'runtime_availability':'UNKNOWN','capture_freshness':'CAPTURE_TIME_ONLY'}))
    if len(nodes)+len(edges)+len(proofs)>_MAX_OBJECTS:_fail('REMOTE_VIEW_OBJECT_LIMIT')
    view=ViewDocument('view:remote-interfaces:'+workspace['workspace_id']+':'+scope,'topology',
        digest([VERSION,captured['capture_id']]),VERSION,scope,deepcopy(captured['selection']),
        nodes=tuple(nodes[k] for k in sorted(nodes)),edges=tuple(sorted(edges,key=lambda e:e.id)),
        diagnostics=tuple(diagnostics),coverage={'status':'PARTIAL' if nodes else 'UNKNOWN',
            'truncated':False,'omitted_mapping_ids':[], 'binding_count':len(report['bindings']),
            'capture_freshness':'CAPTURE_TIME_ONLY'},
        limits=('Static declarations only; no JVM calls, process continuation or observed execution.',
                'Trusted supplied capture consistency; physical checkout freshness is not evaluated.',
                'Payload, delivery, deployment and runtime availability remain UNKNOWN/NOT_OBSERVED.'),
        provenance=tuple(proofs[k] for k in sorted(proofs)))
    try:return ViewDocument.from_dict(view.to_dict())
    except (ValueError,TypeError,KeyError):_fail('REMOTE_VIEW_INVALID_DOCUMENT')

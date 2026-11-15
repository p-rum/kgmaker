"""T016 explicit common capture and pure topology, without live service claims."""
from copy import deepcopy
from pathlib import Path
import re

from .architecture_model import ViewDocument, ViewNode, ViewEdge, aggregate_view_edges
from .remote_mapping import _bounded, _workspace, _graph, _selection, digest
from .remote_interfaces import _ref, _refs, _node, _proof

CAPTURE_VERSION = 'service-topology-capture-1'
VERSION = 'service-topology-view-1'
_MAX_OBJECTS = 20000
_FIELDS = {'schema_version','rules_version','authority','workspace_id','manifest_sha256',
    'input_binding','shared_input_hash','actual_selection','remote_selection','remote_capture_id',
    'data_document','remote_document','data_baseline','remote_baseline','data_fingerprint',
    'remote_fingerprint','release_bindings','capture_id'}


class ServiceTopologyError(ValueError):
    def __init__(self, code):
        self.diagnostic={'code':code}
        super().__init__(code)


def _fail(code):
    raise ServiceTopologyError(code) from None


def _closure(workspace, graph, coverage, scope, selected):
    requested=_selection(scope,selected)
    return {'workspace_fingerprint':digest(_workspace(workspace)),
        'graph_fingerprint':digest(_graph(graph)),'coverage_fingerprint':digest(coverage),
        'scope':scope,'requested_selection':requested['selected_contexts']}


def capture_topology_inputs(manifest, *, scope='production', selected_contexts=None):
    """Explicit local I/O boundary; no compiler/build/application/store invocation."""
    from .workspace import load_workspace, snapshot_workspace
    from .data_resources import project_data_resources
    from .remote_mapping import capture_remote_mapping_inputs
    from .remote_interfaces import project_remote_interfaces
    try:
        _bounded(selected_contexts);_selection(scope,selected_contexts)
        manifest=Path(manifest)
        workspace=load_workspace(manifest);expected=workspace['_manifest_hash']
        _,coverage,_,graph,_=snapshot_workspace(manifest,persist_cache=False)
        if load_workspace(manifest)['_manifest_hash']!=expected:_fail('TOPOLOGY_CAPTURE_CHANGED')
        binding=_closure(workspace,graph,coverage,scope,selected_contexts)
        data=project_data_resources(workspace,graph,source_coverage=coverage,
                                   scope=scope,selected_contexts=selected_contexts)
        remote_capture=capture_remote_mapping_inputs(workspace,graph,scope=scope,
            selected_contexts=selected_contexts,source_coverage=coverage)
        if remote_capture['selection']['source_coverage_fingerprint']!=binding['coverage_fingerprint']:
            _fail('TOPOLOGY_COVERAGE_MISMATCH')
        remote=project_remote_interfaces(workspace,graph,remote_capture['canonical_interfaces'],
            captured=remote_capture,scope=scope,selected_contexts=selected_contexts)
        selections=[d['context_selection'] for d in remote_capture['canonical_interfaces']]
        if (remote.context_selection!=remote_capture['selection']
                or not selections or any(s!=selections[0] for s in selections)
                or data.context_selection!=selections[0]):_fail('TOPOLOGY_CAPTURE_SELECTION_MISMATCH')
        after=load_workspace(manifest)
        _,after_coverage,_,after_graph,_=snapshot_workspace(manifest,persist_cache=False)
        if (after['_manifest_hash']!=expected or load_workspace(manifest)['_manifest_hash']!=expected
                or _closure(after,after_graph,after_coverage,scope,selected_contexts)!=binding):
            _fail('TOPOLOGY_CAPTURE_CHANGED')
        result={'schema_version':1,'rules_version':CAPTURE_VERSION,'authority':'LOCAL_COMMON_CAPTURE',
            'workspace_id':workspace['workspace_id'],'manifest_sha256':expected,
            'input_binding':binding,'shared_input_hash':digest(binding),'actual_selection':deepcopy(selections[0]),
            'remote_selection':deepcopy(remote_capture['selection']),'remote_capture_id':remote_capture['capture_id'],
            'data_document':data.to_dict(include_generation_metadata=False),
            'remote_document':remote.to_dict(include_generation_metadata=False),
            'data_baseline':data.baseline_fingerprint,'remote_baseline':remote.baseline_fingerprint,
            'data_fingerprint':data.content_fingerprint,'remote_fingerprint':remote.content_fingerprint,
            'release_bindings':deepcopy(remote_capture['remote_declarations']['releases'])}
        _bounded(result)
        result['capture_id']=digest(result)
        # Run the exact pure consumer before returning a publishable handoff.
        aggregate_service_topology(result)
        return result
    except ServiceTopologyError:raise
    except (ValueError,TypeError,KeyError,OSError,AttributeError,RecursionError,OverflowError):
        _fail('TOPOLOGY_CAPTURE_UNAVAILABLE')


def _validated(captured):
    _bounded(captured)
    if not isinstance(captured,dict) or set(captured)!=_FIELDS:_fail('TOPOLOGY_INVALID_CAPTURE')
    if (type(captured['schema_version']) is not int or captured['schema_version']!=1
            or captured['rules_version']!=CAPTURE_VERSION or captured['authority']!='LOCAL_COMMON_CAPTURE'):
        _fail('TOPOLOGY_UNSUPPORTED_CAPTURE')
    if captured['capture_id']!=digest({k:v for k,v in captured.items() if k!='capture_id'}):
        _fail('TOPOLOGY_CAPTURE_MISMATCH')
    binding=captured['input_binding']
    if (not isinstance(binding,dict) or set(binding)!={'workspace_fingerprint','graph_fingerprint',
            'coverage_fingerprint','scope','requested_selection'}
            or captured['shared_input_hash']!=digest(binding)):_fail('TOPOLOGY_INPUT_MISMATCH')
    _ref(captured['workspace_id'])
    for key in ('manifest_sha256','remote_capture_id','shared_input_hash','capture_id'):
        if type(captured[key]) is not str or re.fullmatch('[0-9a-f]{64}',captured[key]) is None:_fail('TOPOLOGY_INVALID_HASH')
    for key in ('workspace_fingerprint','graph_fingerprint','coverage_fingerprint'):
        if type(binding[key]) is not str or re.fullmatch('[0-9a-f]{64}',binding[key]) is None:_fail('TOPOLOGY_INVALID_HASH')
    if not isinstance(captured['remote_selection'],dict):_fail('TOPOLOGY_SELECTION_MISMATCH')
    selection=captured['remote_selection']
    if (set(selection)!={'scope','selected_contexts','source_coverage_fingerprint'}
            or selection['scope']!=binding['scope'] or selection['selected_contexts']!=binding['requested_selection']):
        _fail('TOPOLOGY_SELECTION_MISMATCH')
    requested={}
    if not isinstance(selection['selected_contexts'],list):_fail('TOPOLOGY_SELECTION_MISMATCH')
    for row in selection['selected_contexts']:
        if not isinstance(row,dict) or set(row)!={'key','context_id'} or not isinstance(row['key'],list) or len(row['key'])!=3:_fail('TOPOLOGY_SELECTION_MISMATCH')
        key=tuple(_ref(value) for value in row['key'])
        if key in requested:_fail('TOPOLOGY_SELECTION_MISMATCH')
        requested[key]=_ref(row['context_id'])
    if _selection(binding['scope'],requested)['selected_contexts']!=selection['selected_contexts']:_fail('TOPOLOGY_SELECTION_MISMATCH')
    if type(selection['source_coverage_fingerprint']) is not str or re.fullmatch('[0-9a-f]{64}',selection['source_coverage_fingerprint']) is None:_fail('TOPOLOGY_INVALID_HASH')
    if selection['source_coverage_fingerprint']!=binding['coverage_fingerprint']:_fail('TOPOLOGY_COVERAGE_MISMATCH')
    documents=[]
    for name in ('data','remote'):
        document=ViewDocument.from_dict(captured[name+'_document'])
        if (document.kind!='topology' or document.scope!=binding['scope']
                or document.baseline_fingerprint!=captured[name+'_baseline']
                or document.content_fingerprint!=captured[name+'_fingerprint']):_fail('TOPOLOGY_DOCUMENT_MISMATCH')
        documents.append(document)
    if (documents[0].context_selection!=captured['actual_selection']
            or documents[1].context_selection!=selection):_fail('TOPOLOGY_SELECTION_MISMATCH')
    releases=captured['release_bindings']
    if not isinstance(releases,list) or len(releases)>2000:_fail('TOPOLOGY_RELEASE_LIMIT')
    indexed={}
    for release in releases:
        if (not isinstance(release,dict) or set(release)!={'id','service_id','interface_id','context_id','scope','release','contract'}
                or not isinstance(release['contract'],dict) or set(release['contract'])!={'repo_id','path','sha256','pointer'}):
            _fail('TOPOLOGY_INVALID_RELEASE')
        for key,value in release.items():
            if key!='contract':_ref(value)
        for value in release['contract'].values():
            if value:_ref(value)
        if release['id'] in indexed:_fail('TOPOLOGY_RELEASE_COLLISION')
        indexed[release['id']]=release
    return documents[0],documents[1],indexed


def aggregate_service_topology(captured):
    """Pure trusted-handoff aggregate, not physical freshness or authentication."""
    try:return _aggregate(captured)
    except ServiceTopologyError:raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):
        _fail('TOPOLOGY_INVALID_INPUT')


def prepare_service_topology_cache(captured, cache_path, *, annotations=()):
    """Prepare a cache candidate without publishing it.

    The complete, already-validated T016 handoff is the dependency snapshot.
    Callers that combine reviewed process annotations with this view may pass
    their current T032 review snapshot as ``annotations``; any review transition
    invalidates the cache, but review state is never copied into the topology.
    """
    from .view_cache import prepare_snapshot_view
    try:
        _validated(captured)
        selection={'requested_selection':deepcopy(captured['remote_selection']),
            'actual_selection_fingerprint':digest(captured['actual_selection'])}
        expected_baseline=digest([VERSION,captured['capture_id']])
        return prepare_snapshot_view(cache_path,snapshot=captured,
            rules={'capture':CAPTURE_VERSION,'view':VERSION},
            scope=captured['input_binding']['scope'],context_selection=selection,
            annotations=annotations,expected_baseline_fingerprint=expected_baseline,
            builder=lambda:_aggregate(captured))
    except ServiceTopologyError:raise
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):
        _fail('TOPOLOGY_CACHE_UNAVAILABLE')


def aggregate_service_topology_cached(captured, cache_path, *, annotations=()):
    """Explicitly prepare and atomically publish an aggregate cache."""
    return prepare_service_topology_cache(captured, cache_path,
        annotations=annotations).publish()


def _aggregate(captured):
    data,remote,releases=_validated(captured)
    scope=data.scope;workspace=_ref(captured['workspace_id'])
    upstream_truncated=any(d.coverage.get('truncated') is True for d in (data,remote))
    data_rows=data.to_dict();remote_rows=remote.to_dict()
    nodes={};proofs={};endpoints={n.id:n for n in remote.nodes};edge_by_id={e.id:e for e in remote.edges}
    for document in (data_rows,remote_rows):
        for proof in document['provenance']:
            safe=_proof(proof)
            if 'original_payload_hash' in proof:
                safe['original_payload_hash']=_ref(proof['original_payload_hash'])
            if safe['id'] in proofs and proofs[safe['id']]!=safe:_fail('TOPOLOGY_PROOF_COLLISION')
            proofs[safe['id']]=safe
    # Existing catalog services/resources, not graph degree or DTO centrality.
    for row in data_rows['nodes']:
        if row['kind'] not in {'service','database_resource','unresolved_data_resource','external_system'}:continue
        safe=_node(row,scope if row['attributes'].get('scope')!='unknown' else 'unknown')
        attrs=dict(safe.attributes)
        for key in ('database_id','schema_stream_id','repo_id'):
            if row['attributes'].get(key) is not None:attrs[key]=_ref(row['attributes'][key])
        for key in ('table_ids','derivation'):
            if key in row['attributes']:attrs[key]=list(_refs(row['attributes'][key]))
        nodes[safe.id]=ViewNode(safe.id,safe.kind,'Service' if safe.kind=='service' else 'Captured resource',
            original_ids=safe.original_ids,owner_id=safe.owner_id,evidence_refs=safe.evidence_refs,
            attributes=attrs,evidence_kinds=safe.evidence_kinds,resolution_status=safe.resolution_status,
            freshness=safe.freshness,supporting_refs=safe.supporting_refs,
            contradicting_refs=safe.contradicting_refs,unknown_refs=safe.unknown_refs)
    groups={};boundaries=[]
    def add_boundary(identity,originals,attrs):
        identity='topology-boundary:'+digest([VERSION,workspace,identity])
        if identity in nodes:_fail('TOPOLOGY_NODE_COLLISION')
        nodes[identity]=ViewNode(identity,'unresolved_topology_boundary','Unresolved topology boundary',
            original_ids=_refs(originals),attributes={'scope':scope,**attrs,'runtime_availability':'UNKNOWN'})
    def append(key,source,target,relation,edge,attrs):
        groups.setdefault(key,[]).append((source,target,relation,edge,attrs))
    for row in remote_rows['nodes']:
        if row['kind'] in {'unresolved_remote_target','remote_binding'}:
            if row['kind']=='remote_binding' and row['resolution_status']=='RESOLVED':continue
            add_boundary(row['id'],[row['id'],*row['original_ids']],
                {'origin_binding_ids':[row['id']],'context_ids':list(_refs(row['attributes'].get('context_ids',[]))),
                 'source_resolution_status':row['resolution_status'],'original_boundary_hash':digest(row)})
    for edge in remote.edges:
        if edge.attributes.get('scope')!=scope:_fail('TOPOLOGY_REMOTE_SCOPE_MISMATCH')
        if edge.relation not in {'remote_http_request_response','remote_kafka_publish_subscribe'}:
            _fail('TOPOLOGY_UNSUPPORTED_REMOTE_RELATION')
        source=endpoints.get(edge.source);target=endpoints.get(edge.target)
        contexts=list(_refs(edge.attributes.get('context_ids',[])))
        mapping=_ref(edge.attributes['mapping_id']);binding_id=_ref(edge.attributes['binding_id'])
        binding=endpoints.get(binding_id)
        if binding is None:_fail('TOPOLOGY_REMOTE_BINDING_MISSING')
        left=releases[binding.attributes['source_release_id']];right=releases[edge.attributes['target_release_id']]
        def catalog_owner(endpoint, release):
            # T012 uses plain service IDs; HTTP uses catalog IDs. The selected
            # explicit release is authority, never parsing an endpoint label/ID.
            service=release['service_id'];catalog='service:'+service
            if (endpoint is None or endpoint.id!=release['interface_id']
                    or endpoint.owner_id not in {service,catalog} or catalog not in nodes
                    or nodes[catalog].kind!='service' or nodes[catalog].resolution_status!='RESOLVED'):
                return None
            return catalog
        source_owner=catalog_owner(source,left);target_owner=catalog_owner(target,right)
        if source_owner is None or target_owner is None:
            add_boundary(edge.id,[edge.id,edge.source,edge.target],{'reason':'TOPOLOGY_SERVICE_OWNER_UNPROVEN'})
            continue
        common={'scope':scope,'context_ids':contexts,'capture_freshness':'CAPTURE_TIME_ONLY',
            'runtime_execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED','deployment':'UNKNOWN',
            'runtime_availability':'UNKNOWN','payload_compatibility':'UNKNOWN',
            'origin_interface_ids':list(_refs([edge.source,edge.target])), 'origin_mapping_ids':[mapping],
            'origin_release_ids':list(_refs([left['id'],right['id']])), 'origin_edge_ids':[edge.id],
            'origin_binding_ids':[binding_id],'origin_candidates':[{'source_interface_id':edge.source,
                'target_interface_id':edge.target,'mapping_id':mapping,'source_release_id':left['id'],
                'target_release_id':right['id'],'edge_id':edge.id}]}
        if edge.relation=='remote_http_request_response':
            # Operation pointers remain reversible inventory; grouping boundary is
            # contract content + explicit release selector, not endpoint spelling.
            contracts=[edge.attributes['source_contract'],edge.attributes['target_contract']]
            for contract in contracts:
                if not isinstance(contract,dict) or set(contract)!={'repo_id','path','sha256','pointer'}:_fail('TOPOLOGY_INVALID_CONTRACT')
                for value in contract.values():
                    if value:_ref(value)
            boundary=[{k:v for k,v in c.items() if k!='pointer'} for c in contracts]
            common.update(contract_boundary=boundary,release_selectors=[left['release'],right['release']],
                origin_operations=[{'edge_id':edge.id,'source_pointer':edge.attributes['source_contract']['pointer'],
                    'target_pointer':edge.attributes['target_contract']['pointer']}])
            key=digest([source_owner,target_owner,edge.relation,scope,contexts,boundary,left['release'],right['release']])
            append(key,source_owner,target_owner,edge.relation,edge,common)
        else:
            a,b=source.attributes,target.attributes
            realm=a.get('broker_realm');topics=a.get('topics');group=b.get('consumer_group')
            if (not isinstance(topics,list) or not topics or realm!=b.get('broker_realm')
                    or sorted(topics)!=sorted(b.get('topics',[])) or not realm or a.get('topic_pattern') or b.get('topic_pattern')):
                add_boundary(edge.id,[edge.id,edge.source,edge.target],{'reason':'TOPOLOGY_CHANNEL_REALM_UNPROVEN'})
                continue
            for topic in _refs(topics):
                realm=_ref(realm);group=_ref(group) if group is not None else None
                channel='kafka-channel:'+digest([workspace,realm,topic])
                channel_node=ViewNode(channel,'kafka_channel','Kafka channel',
                    attributes={'scope':scope,'broker_realm':realm,'topic':topic,'runtime_availability':'UNKNOWN'},
                    resolution_status='UNRESOLVED',freshness='UNKNOWN')
                if channel in nodes and nodes[channel]!=channel_node:_fail('TOPOLOGY_CHANNEL_COLLISION')
                nodes[channel]=channel_node
                for source_id,target_id,relation in [(source_owner,channel,'publishes_to_channel'),(channel,target_owner,'consumes_from_channel')]:
                    attrs={**common,'broker_realm':realm,'topic':topic,'consumer_group':group if relation=='consumes_from_channel' else None}
                    key=digest([source_id,target_id,relation,scope,contexts,realm,topic,attrs['consumer_group'],left['release'],right['release']])
                    append(key,source_id,target_id,relation,edge,attrs)
    # Preserve actual T015 relations and original buckets separately from remote declarations.
    edges=[]
    for edge in data.edges:
        if edge.source not in nodes or edge.target not in nodes:continue
        edge_scope=edge.attributes.get('scope',scope)
        if edge_scope not in {scope,'unknown'}:_fail('TOPOLOGY_RESOURCE_SCOPE_MISMATCH')
        attrs={'scope':edge_scope,'context_ids':list(_refs(edge.attributes.get('context_ids',[]))),
            'origin_edge_ids':[edge.id],'original_attributes_hash':digest(edge.attributes),
            'runtime_availability':'UNKNOWN','deployment':'UNKNOWN'}
        edges.append(ViewEdge(_ref(edge.id),edge.source,edge.target,_ref(edge.relation),
            original_ids=_refs(edge.original_ids),evidence_refs=edge.evidence_refs,attributes=attrs,
            evidence_kinds=edge.evidence_kinds,
            resolution_status='UNRESOLVED' if edge_scope=='unknown' else edge.resolution_status,freshness=edge.freshness,
            supporting_refs=edge.supporting_refs,contradicting_refs=edge.contradicting_refs,unknown_refs=edge.unknown_refs))
    for key,claims in sorted(groups.items()):
        source,target,relation,first,attrs=claims[0];attrs=deepcopy(attrs)
        for field in ('origin_interface_ids','origin_mapping_ids','origin_release_ids','origin_edge_ids','origin_binding_ids'):
            attrs[field]=sorted({ref for claim in claims for ref in claim[4][field]})
        for field in ('origin_candidates','origin_operations'):
            if field in attrs:
                values={digest(v):v for claim in claims for v in claim[4].get(field,[])}
                attrs[field]=[values[k] for k in sorted(values)]
        projected=[]
        for claim in claims:
            original=claim[3]
            projected.append(ViewEdge('topology-claim:'+digest([key,original.id]),source,target,relation,
                original_ids=(original.id,),evidence_refs=original.evidence_refs,
                attributes={'scope':scope,'context_ids':list(_refs(claim[4]['context_ids']))},
                evidence_kinds=original.evidence_kinds,
                resolution_status='UNRESOLVED' if upstream_truncated else original.resolution_status,
                freshness='UNKNOWN',unknown_refs=original.evidence_refs))
        refs={ref for claim in claims for ref in claim[3].evidence_refs}
        aggregation=aggregate_view_edges(projected,tuple(proofs[ref] for ref in sorted(refs)),scope=scope)
        if len(aggregation['edges'])!=1:_fail('TOPOLOGY_GROUP_CONTEXT_MISMATCH')
        merged=aggregation['edges'][0]
        attrs['source_claims']=merged.attributes['source_claims']
        if upstream_truncated:attrs['incomplete_reason']='TOPOLOGY_UPSTREAM_TRUNCATED'
        edges.append(ViewEdge('topology-edge:'+key,source,target,relation,
            original_ids=tuple(attrs['origin_edge_ids']),evidence_refs=merged.evidence_refs,attributes=attrs,
            evidence_kinds=merged.evidence_kinds,resolution_status=merged.resolution_status,
            freshness='UNKNOWN',supporting_refs=merged.supporting_refs,
            contradicting_refs=merged.contradicting_refs,unknown_refs=merged.unknown_refs))
    if len(nodes)+len(edges)+len(proofs)>_MAX_OBJECTS:_fail('TOPOLOGY_OBJECT_LIMIT')
    view=ViewDocument('view:service-topology:'+workspace+':'+scope,'topology',
        digest([VERSION,captured['capture_id']]),VERSION,scope,
        {'requested_selection':deepcopy(captured['remote_selection']),
         'actual_selection_fingerprint':digest(captured['actual_selection'])},
        nodes=tuple(nodes[k] for k in sorted(nodes)),edges=tuple(sorted(edges,key=lambda e:e.id)),
        provenance=tuple(proofs[k] for k in sorted(proofs)),coverage={'status':'PARTIAL' if nodes and all(d.coverage['status']!='UNKNOWN' for d in (data,remote)) else 'UNKNOWN',
            'truncated':upstream_truncated,'upstream_statuses':[data.coverage['status'],remote.coverage['status']],
            'upstream_truncated':any(d.coverage.get('truncated') is True for d in (data,remote)),
            'capture_freshness':'CAPTURE_TIME_ONLY'},diagnostics=tuple({'code':'TOPOLOGY_UPSTREAM_BOUNDARY',
                'view_id':d.view_id,'coverage_hash':digest(d.coverage),'diagnostics_hash':digest(d.diagnostics),
                'diagnostic_count':len(d.diagnostics)} for d in (data,remote)),
        limits=('Trusted explicit common capture; no live checkout authentication or service execution.',
                'Remote mappings remain capture-time UNKNOWN; no JVM calls or process continuation.',
                'All original alternatives and origin inventories retained; payload/runtime availability UNKNOWN.'))
    return ViewDocument.from_dict(view.to_dict())

"""T016 public common-handoff contracts, hand-labelled examples not native proof."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from kgmaker.analysis_model import digest
from kgmaker.architecture_model import ViewDocument, ViewNode
from test_cross_service_contract_mapping import trusted_protocol_specimen
from kgmaker.remote_interfaces import project_remote_interfaces


def api():
    assert importlib.util.find_spec('kgmaker.service_topology'), 'T016 common capture/pure aggregation API is absent'
    module=importlib.import_module('kgmaker.service_topology')
    assert callable(module.capture_topology_inputs) and callable(module.aggregate_service_topology)
    return module


def labelled_handoff(transport='HTTP'):
    workspace,graph,docs,capture=trusted_protocol_specimen(transport)
    remote=project_remote_interfaces(workspace,graph,docs,captured=capture,scope='production')
    selection=docs[0]['context_selection']
    data=ViewDocument('resources','topology','DIFFERENT-DATA-BASELINE','resource-example-1','production',selection,
        nodes=tuple(ViewNode('service:'+s,'service',s,resolution_status='RESOLVED',
            attributes={'scope':'production','context_ids':['client-context' if s=='checkout' else 'server-context']})
            for s in ['checkout','orders']),coverage={'status':'PARTIAL'})
    binding={'workspace_fingerprint':capture['workspace_fingerprint'],
        'graph_fingerprint':capture['graph_fingerprint'],'coverage_fingerprint':capture['selection']['source_coverage_fingerprint'],
        'scope':'production','requested_selection':capture['selection']['selected_contexts']}
    value={'schema_version':1,'rules_version':'service-topology-capture-1','authority':'LOCAL_COMMON_CAPTURE',
        'workspace_id':workspace['workspace_id'],'manifest_sha256':workspace['_manifest_hash'],
        'input_binding':binding,'shared_input_hash':digest(binding),'actual_selection':selection,
        'remote_selection':capture['selection'],'remote_capture_id':capture['capture_id'],
        'data_document':data.to_dict(),'remote_document':remote.to_dict(),
        'data_baseline':data.baseline_fingerprint,'remote_baseline':remote.baseline_fingerprint,
        'data_fingerprint':data.content_fingerprint,'remote_fingerprint':remote.content_fingerprint,
        'release_bindings':capture['remote_declarations']['releases']}
    value['capture_id']=digest(value)
    return value


def test_public_http_summary_retains_exact_origin_expansion_and_independent_baselines():
    captured=labelled_handoff();before=deepcopy(captured)
    view=api().aggregate_service_topology(captured)
    assert view.kind=='topology'
    edges=[e for e in view.edges if e.relation=='remote_http_request_response']
    assert len(edges)==1 and edges[0].source=='service:checkout' and edges[0].target=='service:orders'
    assert edges[0].attributes['origin_interface_ids']==['client','provider']
    assert edges[0].attributes['origin_mapping_ids']==['one']
    assert edges[0].attributes['origin_edge_ids']==[captured['remote_document']['edges'][0]['id']]
    assert edges[0].freshness=='UNKNOWN' and edges[0].attributes['runtime_execution']=='NOT_OBSERVED'
    assert captured['data_baseline']!=captured['remote_baseline'] and captured==before


def test_public_kafka_uses_channel_and_distinct_publish_consume_group_edges():
    captured=labelled_handoff('KAFKA');view=api().aggregate_service_topology(captured)
    channel=next(n for n in view.nodes if n.kind=='kafka_channel')
    assert channel.attributes['broker_realm']=='alpha' and channel.attributes['topic']=='orders'
    assert {(e.source,e.target,e.relation) for e in view.edges}=={
        ('service:checkout',channel.id,'publishes_to_channel'),(channel.id,'service:orders','consumes_from_channel')}
    consume=next(e for e in view.edges if e.relation=='consumes_from_channel')
    assert consume.attributes['consumer_group']=='group-one'
    assert not any(e.source=='service:checkout' and e.target=='service:orders' for e in view.edges)


def rehash(value):
    value['capture_id']=digest({k:v for k,v in value.items() if k!='capture_id'})


@pytest.mark.parametrize('case',['workspace','selection','remote_selection','data_baseline','remote_document','version','origin'])
def test_inconsistent_handoff_is_rejected_without_mutation(case):
    captured=labelled_handoff()
    if case=='workspace':captured['workspace_id']='foreign' # original envelope hash remains
    elif case=='selection':captured['actual_selection']={'foreign':[]};rehash(captured)
    elif case=='remote_selection':captured['remote_selection']['scope']='test';rehash(captured)
    elif case=='data_baseline':captured['data_baseline']='copied-baseline';rehash(captured)
    elif case=='remote_document':captured['remote_document']['nodes'][0]['owner_id']='foreign';rehash(captured)
    elif case=='version':captured['schema_version']=True;rehash(captured)
    else:captured['authority']='UNTRUSTED_SUPPLIED_DOCS';rehash(captured)
    before=deepcopy(captured)
    with pytest.raises(ValueError):api().aggregate_service_topology(captured)
    assert captured==before


@pytest.mark.parametrize('case',['cycle','deep','shared','unsafe_id','limit'])
def test_bounded_privacy_errors_leave_input_unpublished(case,monkeypatch):
    captured=labelled_handoff()
    if case=='cycle':captured['extra']=captured
    elif case=='deep':
        child={};captured['extra']=child
        for _ in range(90):child['next']={};child=child['next']
    elif case=='shared':captured['extra']=['x'*1000]*33000
    elif case=='unsafe_id':captured['workspace_id']='//user:PRIVATE_SENTINEL@host';rehash(captured)
    else:monkeypatch.setattr(api(),'_MAX_OBJECTS',1)
    with pytest.raises(ValueError) as error:api().aggregate_service_topology(captured)
    assert 'PRIVATE_SENTINEL' not in str(error.value)


def test_pure_aggregate_never_loads_snapshots_projects_or_executes(monkeypatch):
    from pathlib import Path
    import socket,subprocess
    import kgmaker.workspace,kgmaker.data_resources,kgmaker.remote_mapping,kgmaker.remote_interfaces
    captured=labelled_handoff()
    def forbidden(*args,**kwargs):raise AssertionError('pure aggregate performed IO')
    for name in ['read_text','read_bytes','open','write_text']:monkeypatch.setattr(Path,name,forbidden)
    monkeypatch.setattr(socket,'socket',forbidden);monkeypatch.setattr(subprocess,'Popen',forbidden)
    for module,names in [(kgmaker.workspace,['load_workspace','snapshot_workspace']),
        (kgmaker.data_resources,['project_data_resources']),
        (kgmaker.remote_mapping,['capture_remote_mapping_inputs','resolve_remote_mappings']),
        (kgmaker.remote_interfaces,['project_remote_interfaces'])]:
        for name in names:monkeypatch.setattr(module,name,forbidden)
    assert api().aggregate_service_topology(captured).kind=='topology'


def test_enum_noise_changes_binding_hash_but_not_topology_or_origin_expansion():
    captured=labelled_handoff();first=api().aggregate_service_topology(captured)
    captured['input_binding']['graph_fingerprint']=digest({'enum':'widely-used'})
    captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    second=api().aggregate_service_topology(captured)
    assert first.baseline_fingerprint!=second.baseline_fingerprint
    assert [n.to_dict() for n in first.nodes]==[n.to_dict() for n in second.nodes]
    assert [e.to_dict() for e in first.edges]==[e.to_dict() for e in second.edges]


def test_missing_service_owner_stays_boundary_and_never_name_matches():
    captured=labelled_handoff();data=captured['data_document'];data['nodes']=[n for n in data['nodes'] if n['id']!='service:orders']
    captured['data_fingerprint']=ViewDocument.from_dict(data).content_fingerprint;rehash(captured)
    view=api().aggregate_service_topology(captured)
    assert not view.edges and any(n.kind=='unresolved_topology_boundary' for n in view.nodes)


def test_explicit_common_capture_uses_one_snapshot_objects_then_rechecks_same_closure(monkeypatch):
    import kgmaker.workspace,kgmaker.data_resources,kgmaker.remote_mapping,kgmaker.remote_interfaces
    workspace,graph,docs,remote_capture=trusted_protocol_specimen();coverage={'schemas':{}}
    remote_capture['selection']['source_coverage_fingerprint']=digest(coverage)
    remote_capture['capture_id']=digest({k:v for k,v in remote_capture.items() if k!='capture_id'})
    labelled=labelled_handoff();data=ViewDocument.from_dict(labelled['data_document'])
    calls=[]
    monkeypatch.setattr(kgmaker.workspace,'load_workspace',lambda p:workspace)
    def snapshot(path,**kwargs):
        assert kwargs=={'persist_cache':False};calls.append('snapshot')
        return {},coverage,{},graph,{}
    monkeypatch.setattr(kgmaker.workspace,'snapshot_workspace',snapshot)
    def resources(ws,g,**kwargs):
        assert ws is workspace and g is graph and kwargs['source_coverage'] is coverage
        calls.append('data');return data
    monkeypatch.setattr(kgmaker.data_resources,'project_data_resources',resources)
    def remote_inputs(ws,g,**kwargs):
        assert ws is workspace and g is graph and kwargs['source_coverage'] is coverage
        calls.append('remote');return remote_capture
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',remote_inputs)
    original=kgmaker.remote_interfaces.project_remote_interfaces
    def remote_view(ws,g,interfaces,**kwargs):
        assert ws is workspace and g is graph and interfaces is remote_capture['canonical_interfaces']
        assert kwargs['captured'] is remote_capture;return original(ws,g,interfaces,**kwargs)
    monkeypatch.setattr(kgmaker.remote_interfaces,'project_remote_interfaces',remote_view)
    result=api().capture_topology_inputs('unused-explicit-manifest')
    assert calls==['snapshot','data','remote','snapshot']
    assert result['data_baseline']!=result['remote_baseline']
    assert api().aggregate_service_topology(result).kind=='topology'


@pytest.mark.parametrize('mutation',['manifest','source','coverage','selection'])
def test_common_capture_rejects_mutation_between_phases(monkeypatch,mutation):
    import kgmaker.workspace,kgmaker.data_resources,kgmaker.remote_mapping
    workspace,graph,docs,remote_capture=trusted_protocol_specimen();coverage={'schemas':{}}
    remote_capture['selection']['source_coverage_fingerprint']=digest(coverage)
    remote_capture['capture_id']=digest({k:v for k,v in remote_capture.items() if k!='capture_id'})
    data=ViewDocument.from_dict(labelled_handoff()['data_document'])
    snapshots=[]
    monkeypatch.setattr(kgmaker.workspace,'load_workspace',lambda p:workspace)
    def snapshot(path,**kwargs):
        snapshots.append(1)
        return {},coverage,{},graph,{}
    monkeypatch.setattr(kgmaker.workspace,'snapshot_workspace',snapshot)
    monkeypatch.setattr(kgmaker.data_resources,'project_data_resources',lambda *a,**k:data)
    def changed(*args,**kwargs):
        if mutation=='manifest':workspace['_manifest_hash']='e'*64
        elif mutation=='source':graph.files['new-source']='a'*64
        elif mutation=='coverage':coverage['schemas']['changed']=[]
        else:remote_capture['canonical_interfaces'][0]['context_selection']={'foreign':[]}
        return remote_capture
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',changed)
    with pytest.raises(ValueError):api().capture_topology_inputs('unused-explicit-manifest')


from test_t013_attach_interface_contracts import fixture as explicit_contract_fixture


def test_real_public_common_capture_preserves_distinct_baselines_and_offline_replay(explicit_contract_fixture):
    from pathlib import Path
    import json
    manifest,contract,generated,metadata=explicit_contract_fixture
    before={str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}
    captured=api().capture_topology_inputs(manifest)
    assert captured['data_baseline']!=captured['remote_baseline']
    assert captured['data_document']['context_selection']==captured['actual_selection']
    assert captured['remote_document']['context_selection']==captured['remote_selection']
    view=api().aggregate_service_topology(captured)
    assert view.kind=='topology' and view.coverage['status'] in {'PARTIAL','UNKNOWN'}
    assert {str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}==before
    assert not any(p.name=='cache' for p in manifest.parent.rglob('*'))


def refresh_documents(captured):
    for name in ['data','remote']:
        captured[name+'_fingerprint']=ViewDocument.from_dict(captured[name+'_document']).content_fingerprint
    rehash(captured)


def extra_remote_occurrence(captured, *, realm=None, group='group-two'):
    remote=captured['remote_document'];old_edge=remote['edges'][0]
    source=deepcopy(next(n for n in remote['nodes'] if n['id']==old_edge['source']))
    target=deepcopy(next(n for n in remote['nodes'] if n['id']==old_edge['target']))
    source['id']='client-two';target['id']='provider-two'
    if realm:
        source['attributes']['broker_realm']=target['attributes']['broker_realm']=realm
    target['attributes']['consumer_group']=group
    binding=deepcopy(next(n for n in remote['nodes'] if n['id']==old_edge['attributes']['binding_id']))
    binding['id']='binding-two';binding['attributes']['source_release_id']='left-two'
    remote['nodes'] += [source,target,binding]
    for original,identity,interface in [(captured['release_bindings'][0],'left-two','client-two'),
                                      (captured['release_bindings'][1],'right-two','provider-two')]:
        release=deepcopy(original);release.update(id=identity,interface_id=interface)
        captured['release_bindings'].append(release)
    edge=deepcopy(old_edge);edge.update(id='remote-edge-two',source='client-two',target='provider-two')
    edge['attributes'].update(binding_id='binding-two',mapping_id='two',target_release_id='right-two',consumer_group=group)
    for key in ['source_contract','target_contract']:edge['attributes'][key]['pointer']='#/paths/~1second/post'
    remote['edges'].append(edge);refresh_documents(captured)


def test_http_endpoints_group_with_exact_reversible_interface_mapping_release_inventory():
    captured=labelled_handoff();extra_remote_occurrence(captured)
    view=api().aggregate_service_topology(captured)
    assert len(view.edges)==1
    edge=view.edges[0]
    assert edge.attributes['origin_interface_ids']==['client','client-two','provider','provider-two']
    assert edge.attributes['origin_mapping_ids']==['one','two']
    assert len(edge.attributes['origin_edge_ids'])==2 and len(edge.attributes['origin_candidates'])==2
    assert len(edge.attributes['origin_release_ids'])==4 and len(edge.attributes['origin_operations'])==2


@pytest.mark.parametrize('realm',['alpha','beta'])
def test_kafka_groups_and_realms_remain_distinct_channel_consumer_alternatives(realm):
    captured=labelled_handoff('KAFKA');extra_remote_occurrence(captured,realm=realm)
    view=api().aggregate_service_topology(captured)
    channels=[n for n in view.nodes if n.kind=='kafka_channel']
    assert len(channels)==(1 if realm=='alpha' else 2)
    consume=[e for e in view.edges if e.relation=='consumes_from_channel']
    assert len(consume)==2 and {e.attributes['consumer_group'] for e in consume}=={'group-one','group-two'}
    assert all(e.attributes['runtime_execution']=='NOT_OBSERVED' for e in view.edges)


@pytest.mark.parametrize('changed',['manifest','source','schema'])
def test_real_capture_detects_files_changed_after_remote_phase(explicit_contract_fixture,monkeypatch,changed):
    import json
    import kgmaker.remote_mapping
    manifest,contract,generated,metadata=explicit_contract_fixture
    original=kgmaker.remote_mapping.capture_remote_mapping_inputs
    def mutate(*args,**kwargs):
        value=original(*args,**kwargs)
        if changed=='manifest':
            document=json.loads(manifest.read_text());document['workspace_id']='changed';manifest.write_text(json.dumps(document))
        elif changed=='source':generated.write_text(generated.read_text()+'\nexport enum Noise { One }\n')
        else:
            document=json.loads(contract.read_text());document['info']['description']='changed';contract.write_text(json.dumps(document))
        return value
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',mutate)
    with pytest.raises(ValueError) as error:api().capture_topology_inputs(manifest)
    assert getattr(error.value,'diagnostic',{}).get('code') in {'TOPOLOGY_CAPTURE_CHANGED','TOPOLOGY_CAPTURE_UNAVAILABLE'}


@pytest.mark.parametrize('case',['selector','contract-extra','contract-pointer','original-resource-ref'])
def test_recognizable_secret_in_exported_reference_or_untyped_contract_is_rejected(case):
    from kgmaker.architecture_model import ViewEdge
    captured=labelled_handoff();secret='//user:PRIVATE_SENTINEL@host/path'
    if case=='selector':
        selected=[{'key':['service',secret,'module'],'context_id':'ctx'}]
        captured['input_binding']['requested_selection']=selected
        captured['remote_selection']['selected_contexts']=selected
        captured['remote_document']['context_selection']=deepcopy(captured['remote_selection'])
        captured['shared_input_hash']=digest(captured['input_binding'])
    elif case.startswith('contract'):
        contract=captured['remote_document']['edges'][0]['attributes']['source_contract']
        contract['raw_sql' if case=='contract-extra' else 'pointer']=secret
    else:
        doc=captured['data_document']
        doc['edges']=[ViewEdge('resource-edge','service:checkout','service:orders','reads',original_ids=(secret,)).to_dict()]
    refresh_documents(captured)
    with pytest.raises(ValueError) as error:api().aggregate_service_topology(captured)
    assert 'PRIVATE_SENTINEL' not in str(error.value)


def test_unknown_and_truncated_upstream_coverage_never_becomes_complete_unique_topology():
    captured=labelled_handoff();captured['data_document']['coverage'].update(status='UNKNOWN',truncated=True)
    refresh_documents(captured);view=api().aggregate_service_topology(captured)
    assert view.coverage['status']=='UNKNOWN' and view.coverage['truncated'] is True
    assert all(e.resolution_status=='UNRESOLVED' for e in view.edges)
    assert view.edges[0].attributes['incomplete_reason']=='TOPOLOGY_UPSTREAM_TRUNCATED'


def test_resource_contradicting_refs_and_original_status_survive_separately_from_remote_proof():
    from kgmaker.architecture_model import ViewEdge
    captured=labelled_handoff();data=captured['data_document']
    data['provenance']=[{'id':'support','evidence_kind':'FRAMEWORK_DERIVED','freshness':'CURRENT','polarity':'SUPPORTING'},
                        {'id':'contradiction','evidence_kind':'SOURCE_ONLY','freshness':'STALE','polarity':'CONTRADICTING'}]
    data['edges']=[ViewEdge('resource-claim','service:checkout','service:orders','depends_on',
        evidence_refs=('support','contradiction'),evidence_kinds=('FRAMEWORK_DERIVED','SOURCE_ONLY'),
        supporting_refs=('support',),contradicting_refs=('contradiction',),resolution_status='AMBIGUOUS',
        freshness='STALE',attributes={'scope':'production','context_ids':['client-context']}).to_dict()]
    refresh_documents(captured);view=api().aggregate_service_topology(captured)
    edge=next(e for e in view.edges if e.id=='resource-claim')
    assert edge.resolution_status=='AMBIGUOUS' and edge.freshness=='STALE'
    assert edge.supporting_refs==('support',) and edge.contradicting_refs==('contradiction',)
    remote=next(e for e in view.edges if e.relation=='remote_http_request_response')
    assert remote.supporting_refs==() and remote.evidence_kinds==('SOURCE_ONLY',)


@pytest.mark.parametrize('kind',['remote','data'])
def test_foreign_scope_claim_cannot_be_rewritten_into_selected_scope(kind):
    from kgmaker.architecture_model import ViewEdge
    captured=labelled_handoff()
    if kind=='remote':captured['remote_document']['edges'][0]['attributes']['scope']='test'
    else:captured['data_document']['edges']=[ViewEdge('foreign','service:checkout','service:orders','reads',attributes={'scope':'test'}).to_dict()]
    refresh_documents(captured)
    with pytest.raises(ValueError):api().aggregate_service_topology(captured)


def test_shared_and_remote_coverage_fingerprints_must_match_even_with_recomputed_handoff_hash():
    captured=labelled_handoff()
    captured['input_binding']['coverage_fingerprint']=digest({'different':'coverage'})
    captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    before=deepcopy(captured)
    with pytest.raises(ValueError) as error:api().aggregate_service_topology(captured)
    assert str(error.value)=='TOPOLOGY_COVERAGE_MISMATCH' and captured==before


def test_exact_same_coverage_fingerprint_is_valid_without_equating_upstream_baselines():
    captured=labelled_handoff()
    assert captured['input_binding']['coverage_fingerprint']==captured['remote_selection']['source_coverage_fingerprint']==digest(None)
    assert captured['data_baseline']!=captured['remote_baseline']
    assert len(api().aggregate_service_topology(captured).edges)==1


def test_capture_rejects_remote_coverage_mismatch_before_projecting(explicit_contract_fixture,monkeypatch):
    import kgmaker.remote_mapping,kgmaker.remote_interfaces
    manifest,*_=explicit_contract_fixture
    original=kgmaker.remote_mapping.capture_remote_mapping_inputs
    def inconsistent(*args,**kwargs):
        captured=original(*args,**kwargs)
        captured['selection']['source_coverage_fingerprint']=digest({'different':'coverage'})
        captured['capture_id']=digest({k:v for k,v in captured.items() if k!='capture_id'})
        return captured
    def forbidden(*args,**kwargs):raise AssertionError('mismatched coverage reached projection')
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',inconsistent)
    monkeypatch.setattr(kgmaker.remote_interfaces,'project_remote_interfaces',forbidden)
    with pytest.raises(ValueError) as error:api().capture_topology_inputs(manifest)
    assert str(error.value)=='TOPOLOGY_COVERAGE_MISMATCH'


def test_canonical_kafka_plain_service_owners_map_via_exact_explicit_release_service():
    captured=labelled_handoff('KAFKA')
    for node in captured['remote_document']['nodes']:
        if node['id']=='client':node['owner_id']='checkout'
        elif node['id']=='provider':node['owner_id']='orders'
    refresh_documents(captured);view=api().aggregate_service_topology(captured)
    assert len([n for n in view.nodes if n.kind=='kafka_channel'])==1
    assert {e.relation for e in view.edges}=={'publishes_to_channel','consumes_from_channel'}
    assert not any(n.attributes.get('reason')=='TOPOLOGY_SERVICE_OWNER_UNPROVEN' for n in view.nodes)


@pytest.mark.parametrize('owner',['foreign','service:foreign','prefix:orders','checkout'])
def test_kafka_owner_must_match_exact_selected_release_service_without_parsing(owner):
    captured=labelled_handoff('KAFKA')
    node=next(n for n in captured['remote_document']['nodes'] if n['id']=='provider');node['owner_id']=owner
    refresh_documents(captured);view=api().aggregate_service_topology(captured)
    assert not any(n.kind=='kafka_channel' for n in view.nodes)
    assert not view.edges
    assert any(n.attributes.get('reason')=='TOPOLOGY_SERVICE_OWNER_UNPROVEN' for n in view.nodes)


def test_qualified_http_owner_control_still_maps_to_exact_catalog_service():
    view=api().aggregate_service_topology(labelled_handoff('HTTP'))
    assert len(view.edges)==1 and view.edges[0].source=='service:checkout' and view.edges[0].target=='service:orders'

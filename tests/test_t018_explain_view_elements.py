"""T018 explicit snapshot explanation; protocol fixtures are not native proof."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from kgmaker.service_topology import aggregate_service_topology
from test_t016_aggregate_service_topology import labelled_handoff


def api():
    assert importlib.util.find_spec('kgmaker.view_explanation'), 'T018 pure explanation/source-status API is absent'
    module=importlib.import_module('kgmaker.view_explanation')
    assert callable(module.explain_view_element) and callable(module.capture_explanation_source_status)
    return module


def test_public_summary_expands_exact_origins_and_missing_graph_is_explicit_unavailable():
    captured=labelled_handoff();view=aggregate_service_topology(captured);edge=view.edges[0]
    before=deepcopy(captured),view.to_dict()
    report=api().explain_view_element(view,edge.id,captured=captured)
    assert report['status']=='EXPLAINED' and report['element_id']==edge.id
    assert report['view_fingerprint']==view.content_fingerprint
    assert report['baseline_fingerprint']==view.baseline_fingerprint
    assert report['origin_interface_ids']==['client','provider'] and report['mapping_ids']==['one']
    assert report['graph_status']=='NOT_SUPPLIED'
    assert report['current_source_status']=='NOT_CHECKED'
    assert report['unavailable_references']
    assert (captured,view.to_dict())==before


def test_public_unknown_element_does_not_search_or_invent_graph_identity():
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,'unknown-element',captured=captured)
    assert report['status']=='UNKNOWN_ELEMENT' and report['element_id']=='unknown-element'
    assert report['source_locators']==[] and report['current_source_status']=='NOT_CHECKED'


from pathlib import Path
import hashlib
import json
from kgmaker.analysis_model import digest
from kgmaker.model import KnowledgeGraph,Node
from kgmaker.remote_mapping import _graph,_workspace
from kgmaker.workspace import qualified,load_workspace
from test_t016_aggregate_service_topology import refresh_documents,rehash


def bound_source(tmp_path, *, span=True):
    backend=tmp_path/'backend';source=backend/'src/main/java/demo/Code.java';source.parent.mkdir(parents=True)
    source.write_text('package demo;\nclass Code { void entry(){} }\n')
    manifest=tmp_path/'workspace.json';manifest.write_text(json.dumps({'schema_version':1,'workspace_id':'manual-protocol',
        'repositories':[{'id':'backend','role':'backend','path':'backend'}],
        'services':[{'id':'checkout','backend_repo':'backend','contract':{'repo_id':'backend','path':'openapi.json'}}]}))
    workspace=load_workspace(manifest);captured=labelled_handoff()
    checksum=hashlib.sha256(source.read_bytes()).hexdigest();path='@backend/src/main/java/demo/Code.java'
    context_id=qualified('backend','context:one');identity=qualified('backend','symbol:method:demo.Code.entry()V')
    record={'id':identity,'kind':'method','name':'entry','owner':'demo.Code','descriptor':'()V','sha256':checksum,
        'path':path,'context_id':context_id,'scope':'production'}
    if span:record['range']={'start':0,'end':len(source.read_bytes()),'start_line':1,'end_line':2}
    node=Node(identity,'method','entry',path,1,'()V',scope='production',metadata=deepcopy(record))
    graph=KnowledgeGraph(3,'.','captured',[node],[],{path:checksum},symbols=[deepcopy(record)],
        contexts=[{'id':context_id,'repo_id':'backend','language':'jvm','mode':'BUILD_IMPORT','scope':'production',
            'freshness':'CURRENT','source_files':{path:checksum}}])
    captured['manifest_sha256']=workspace['_manifest_hash']
    captured['input_binding']['workspace_fingerprint']=digest(_workspace(workspace))
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding'])
    captured['actual_selection']={'services':{'checkout':{'scope':'production','status':'CURRENT','contexts':[{'context_id':context_id}]}}}
    captured['data_document']['context_selection']=deepcopy(captured['actual_selection'])
    endpoint=next(n for n in captured['remote_document']['nodes'] if n['id']=='client');endpoint['original_ids'].append(identity)
    refresh_documents(captured)
    return workspace,graph,captured,source,identity


@pytest.mark.parametrize('change',['same','edit','delete'])
def test_explicit_real_file_status_keeps_original_fingerprint_and_only_current_hash_separate(tmp_path,change):
    workspace,graph,captured,source,ref=bound_source(tmp_path);view=aggregate_service_topology(captured)
    fingerprint=view.content_fingerprint;oldhash=graph.files[next(iter(graph.files))]
    if change=='edit':source.write_text('changed source\n')
    elif change=='delete':source.unlink()
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph,source_status=status)
    expected={'same':'CONTENT_MATCH','edit':'SOURCE_STALE','delete':'SOURCE_MISSING'}[change]
    assert report['current_source_status']==expected and report['view_fingerprint']==fingerprint
    assert report['baseline_fingerprint']==view.baseline_fingerprint and report['freshness']=='UNKNOWN'
    locator=report['source_locators'][0]
    assert locator['reference_id']==ref and locator['source_sha256']==oldhash and locator['status']==expected
    assert str(tmp_path) not in json.dumps(report) and 'changed source' not in json.dumps(status)
    assert locator['path']=='src/main/java/demo/Code.java'


def test_missing_range_stays_null_without_fabricated_node_line_or_current_read(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path,span=False);view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
    locator=report['source_locators'][0]
    assert locator['range'] is None and locator['range_status']=='RANGE_UNAVAILABLE'
    assert locator['status']=='NOT_CHECKED' and locator['current_sha256'] is None
    assert report['current_source_status']=='NOT_CHECKED'


@pytest.mark.parametrize('damage',['wrong_graph','wrong_context','wrong_hash','wrong_node','wrong_scope'])
def test_foreign_or_unselected_graph_records_never_borrow_source_locations(tmp_path,damage):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    if damage=='wrong_graph':graph.files['@backend/foreign']='a'*64
    elif damage=='wrong_context':
        context=deepcopy(graph.contexts[0]);context['id']=qualified('backend','unselected');graph.contexts.append(context)
        graph.symbols[0]['context_id']=context['id']
    elif damage=='wrong_hash':graph.contexts[0]['source_files'][graph.symbols[0]['path']]='b'*64
    elif damage=='wrong_node':graph.nodes[0].metadata['owner']='foreign.Owner'
    else:graph.nodes[0]=Node(**{**vars(graph.nodes[0]),'scope':'test'})
    if damage!='wrong_graph':
        captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    view=aggregate_service_topology(captured)
    if damage=='wrong_graph':
        with pytest.raises(ValueError,match='EXPLAIN_GRAPH_MISMATCH'):api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
    else:
        report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
        assert not report['source_locators']
        assert ref in {r['reference_id'] for r in report['unavailable_references']}
        with pytest.raises(ValueError):api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])


def test_pure_explain_denies_all_io_projectors_and_reselection(tmp_path,monkeypatch):
    import socket,subprocess
    import kgmaker.workspace,kgmaker.graph_provider,kgmaker.remote_mapping,kgmaker.data_resources
    workspace,graph,captured,source,ref=bound_source(tmp_path);view=aggregate_service_topology(captured);module=api()
    def forbidden(*args,**kwargs):raise AssertionError('pure explain did I/O')
    for name in ['open','read_text','read_bytes','write_text']:monkeypatch.setattr(Path,name,forbidden)
    monkeypatch.setattr(socket,'socket',forbidden);monkeypatch.setattr(subprocess,'Popen',forbidden)
    for name in ['load_workspace','snapshot_workspace']:monkeypatch.setattr(kgmaker.workspace,name,forbidden)
    monkeypatch.setattr(kgmaker.data_resources,'project_data_resources',forbidden)
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',forbidden)
    report=module.explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
    assert report['source_locators'][0]['status']=='NOT_CHECKED'


@pytest.mark.parametrize('damage',['symlink','traversal','foreign_repo','absolute','unselected_ref'])
def test_source_status_refuses_unsafe_or_foreign_requested_locators_before_reads(tmp_path,damage):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    if damage=='symlink':
        outside=tmp_path/'outside';outside.write_text('PRIVATE_SENTINEL');source.unlink();source.symlink_to(outside)
    elif damage=='unselected_ref':ref=qualified('other','missing')
    else:
        path={'traversal':'@backend/../outside','foreign_repo':'@foreign/file','absolute':'/outside'}[damage]
        graph.symbols[0]['path']=graph.nodes[0].metadata['path']=path
        graph.nodes[0]=Node(**{**vars(graph.nodes[0]),'path':path})
        checksum=graph.symbols[0]['sha256'];graph.files={path:checksum};graph.contexts[0]['source_files']={path:checksum}
        captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    with pytest.raises(ValueError) as error:api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    assert 'PRIVATE_SENTINEL' not in str(error.value) and str(tmp_path) not in str(error.value)


def test_filtered_view_rederivation_preserves_original_fingerprint_and_omitted_alternatives():
    from kgmaker.topology_filter import filter_topology
    captured=labelled_handoff();original=aggregate_service_topology(captured)
    filtered=filter_topology(original,focus_service='service:checkout',max_nodes=1)
    report=api().explain_view_element(filtered['document'],'service:checkout',captured=captured,filtering=filtered)
    assert report['truncated'] and report['filtering_rule']=='topology-filter-1'
    assert report['baseline_fingerprint']==original.baseline_fingerprint
    poisoned=deepcopy(filtered);poisoned['filtering']['omitted_edge_ids']=[]
    with pytest.raises(ValueError):api().explain_view_element(filtered['document'],'service:checkout',captured=captured,filtering=poisoned)


@pytest.mark.parametrize('damage',['status_path','status_hash','status_context','status_label','unknown_version'])
def test_tampered_source_status_cannot_rebind_reference_with_recomputed_status_hash(tmp_path,damage):
    workspace,graph,captured,source,ref=bound_source(tmp_path);view=aggregate_service_topology(captured)
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    if damage=='status_path':status['locators'][0]['path']='other.java'
    elif damage=='status_hash':status['locators'][0]['source_sha256']='c'*64
    elif damage=='status_context':status['locators'][0]['context_id']='foreign'
    elif damage=='status_label':status['locators'][0]['status']='CURRENT'
    else:status['rules_version']='future'
    status['status_id']=digest({k:v for k,v in status.items() if k!='status_id'})
    before=deepcopy(status)
    with pytest.raises(ValueError):api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph,source_status=status)
    assert status==before


def test_record_range_cannot_override_canonical_node_range(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    graph.symbols[0]['range']['end_line']=999
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
    assert not report['source_locators']
    assert {'reference_id':ref,'reason':'CANONICAL_SOURCE_RANGE_MISMATCH'} in report['unavailable_references']


@pytest.mark.parametrize('unknown',[False,True])
def test_report_hard_limit_also_applies_to_unknown_element(unknown,monkeypatch):
    module=api();monkeypatch.setattr(module,'_MAX_REPORT_CHARS',100)
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    with pytest.raises(ValueError,match='EXPLAIN_REPORT_LIMIT'):
        module.explain_view_element(view,'missing' if unknown else view.edges[0].id,captured=captured)


@pytest.mark.parametrize('damage',['cycle','deep','shared','unsafe_id','version'])
def test_bounded_and_privacy_errors_leave_inputs_unchanged(damage):
    captured=labelled_handoff();view=aggregate_service_topology(captured);identity=view.edges[0].id
    if damage=='cycle':captured['extra']=captured
    elif damage=='deep':
        child={};captured['extra']=child
        for _ in range(90):child['next']={};child=child['next']
    elif damage=='shared':captured['extra']=['x'*1000]*33000
    elif damage=='unsafe_id':identity='prefix //u:PRIVATE_SENTINEL@host/x'
    else:captured['schema_version']=True;rehash(captured)
    with pytest.raises(ValueError) as error:api().explain_view_element(view,identity,captured=captured)
    assert 'PRIVATE_SENTINEL' not in str(error.value)


def test_filtered_single_candidate_explains_all_original_compatible_alternatives():
    from kgmaker.remote_interfaces import project_remote_interfaces
    from kgmaker.topology_filter import filter_topology
    from test_cross_service_contract_mapping import trusted_protocol_specimen,refresh_handoff
    from kgmaker.architecture_model import ViewNode
    workspace,graph,documents,handoff=specimen=trusted_protocol_specimen()
    workspace['services'].append({**deepcopy(workspace['services'][1]),'id':'other'})
    doc=next(d for d in documents if any(n['id']=='provider' for n in d['nodes']))
    other=deepcopy(next(n for n in doc['nodes'] if n['id']=='provider'))
    other['id']='other-provider';other['owner_id']='service:other';other['attributes']['service_id']='other';doc['nodes'].append(other)
    release=deepcopy(workspace['remote_mapping']['releases'][1]);release.update(id='other-release',service_id='other',interface_id='other-provider')
    workspace['remote_mapping']['releases'].append(release)
    workspace['remote_mapping']['mappings'].append({'id':'other-mapping','transport':'HTTP','source_release_id':'client-v1','target_release_id':'other-release','compatibility_id':None})
    refresh_handoff(*specimen)
    captured=labelled_handoff();remote=project_remote_interfaces(workspace,graph,documents,captured=handoff,scope='production')
    captured['remote_document']=remote.to_dict();captured['remote_baseline']=remote.baseline_fingerprint
    captured['remote_capture_id']=handoff['capture_id'];captured['release_bindings']=deepcopy(handoff['remote_declarations']['releases'])
    captured['data_document']['nodes'].append(ViewNode('service:other','service','Other',resolution_status='RESOLVED',attributes={'scope':'production'}).to_dict())
    refresh_documents(captured);original=aggregate_service_topology(captured)
    filtered=filter_topology(original,focus_service='service:checkout',max_nodes=2)
    assert len(filtered['document']['edges'])==1
    edge=filtered['document']['edges'][0]
    report=api().explain_view_element(filtered['document'],edge['id'],captured=captured,filtering=filtered)
    assert report['resolution_status']=='AMBIGUOUS'
    assert report['origin_interface_ids']==['client','other-provider','provider']
    assert report['mapping_ids']==['one','other-mapping']
    assert report['filtering']['omitted_edge_ids']


def test_current_file_match_does_not_upgrade_stale_captured_compiler_context(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path);graph.contexts[0]['freshness']='STALE'
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    view=aggregate_service_topology(captured)
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph,source_status=status)
    assert report['source_locators'][0]['captured_context_freshness']=='STALE'
    assert report['source_locators'][0]['status']=='CONTENT_MATCH' and report['freshness']=='UNKNOWN'


def test_original_proof_buckets_and_secret_payload_omissions_are_not_promoted(tmp_path):
    from kgmaker.architecture_model import ViewEdge
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    data=captured['data_document']
    data['provenance']=[{'id':'support','evidence_kind':'FRAMEWORK_DERIVED','polarity':'SUPPORTING','freshness':'CURRENT','source_id':ref,'raw_secret':'PRIVATE_SENTINEL'},
        {'id':'contra','evidence_kind':'SOURCE_ONLY','polarity':'CONTRADICTING','freshness':'STALE','raw_secret':'PRIVATE_SENTINEL'},
        {'id':'unknown','evidence_kind':'UNKNOWN','polarity':'UNKNOWN','freshness':'UNKNOWN'}]
    data['edges']=[ViewEdge('resource-claim','service:checkout','service:orders','depends_on',
        evidence_refs=('support','contra','unknown'),evidence_kinds=('FRAMEWORK_DERIVED','SOURCE_ONLY','UNKNOWN'),
        supporting_refs=('support',),contradicting_refs=('contra',),unknown_refs=('unknown',),
        resolution_status='AMBIGUOUS',freshness='STALE',attributes={'scope':'production'}).to_dict()]
    refresh_documents(captured);view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,'resource-claim',captured=captured,graph=graph)
    bucket=next(e for e in report['evidence'] if e['owner_id']=='resource-claim')
    assert bucket['supporting_refs']==['support'] and bucket['contradicting_refs']==['contra'] and bucket['unknown_refs']==['unknown']
    assert report['freshness']=='STALE' and report['resolution_status']=='AMBIGUOUS'
    assert {p['polarity'] for p in report['provenance']}=={'SUPPORTING','CONTRADICTING','UNKNOWN'}
    assert 'PRIVATE_SENTINEL' not in json.dumps(report)


def test_every_requested_locator_is_validated_before_any_file_read(tmp_path,monkeypatch):
    workspace,graph,captured,source,ref=bound_source(tmp_path);module=api()
    original=module._read_hash
    def forbidden(root,relative,budget):
        if relative==Path(workspace['_manifest_path']).name:return original(root,relative,budget)
        raise AssertionError('source read happened before all references validated')
    monkeypatch.setattr(module,'_read_hash',forbidden)
    with pytest.raises(ValueError,match='EXPLAIN_SOURCE_REFERENCE_UNAVAILABLE'):
        module.capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref,qualified('zzz','missing')])


def test_source_byte_limit_is_unavailable_not_false_content_match(tmp_path,monkeypatch):
    workspace,graph,captured,source,ref=bound_source(tmp_path);module=api();monkeypatch.setattr(module,'_MAX_TOTAL_BYTES',1)
    status=module.capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    assert status['locators'][0]['status']=='SOURCE_UNAVAILABLE' and status['locators'][0]['current_sha256'] is None


def test_source_capture_uses_loaded_manifest_roots_not_forged_private_root(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    outside=tmp_path/'outside';outside.mkdir();workspace['repositories'][0]['_root']=str(outside)
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    assert status['locators'][0]['status']=='CONTENT_MATCH'
    assert str(tmp_path) not in json.dumps(status)


def test_bound_fact_origin_chain_reaches_existing_code_without_parsing_fact_id(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    fact=qualified('backend','opaque-captured-kafka-fact')
    graph.nodes.append(Node(fact,'kafka_code_producer','Captured',graph.nodes[0].path,1,scope='production',metadata={'origin_id':ref}))
    endpoint=next(n for n in captured['remote_document']['nodes'] if n['id']=='client')
    endpoint['original_ids']=[fact]
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);refresh_documents(captured)
    view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph)
    assert fact in report['expanded_reference_ids'] and ref in report['expanded_reference_ids']
    assert report['source_locators'][0]['reference_id']==ref


def test_same_relative_file_in_two_repos_preserves_each_exact_context_and_hash(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    other=tmp_path/'other/src/main/java/demo/Code.java';other.parent.mkdir(parents=True);other.write_text('class Other {}\n')
    manifest=Path(workspace['_manifest_path']);document=json.loads(manifest.read_text())
    document['repositories'].append({'id':'other','role':'backend','path':'other'})
    document['services'].append({'id':'orders','backend_repo':'other','contract':{'repo_id':'other','path':'openapi.json'}})
    manifest.write_text(json.dumps(document));workspace=load_workspace(manifest)
    checksum=hashlib.sha256(other.read_bytes()).hexdigest();path='@other/src/main/java/demo/Code.java'
    cid=qualified('other','context:two');second=qualified('other','symbol:method:demo.Other.entry()V')
    record={**deepcopy(graph.symbols[0]),'id':second,'owner':'demo.Other','context_id':cid,'path':path,'sha256':checksum}
    record['range']={'start':0,'end':len(other.read_bytes()),'start_line':1,'end_line':1}
    graph.symbols.append(record);graph.nodes.append(Node(second,'method','entry',path,1,'()V',scope='production',metadata=deepcopy(record)))
    graph.files[path]=checksum;graph.contexts.append({'id':cid,'repo_id':'other','language':'jvm','mode':'BUILD_IMPORT','scope':'production','freshness':'CURRENT','source_files':{path:checksum}})
    captured['actual_selection']['services']['orders']={'contexts':[{'context_id':cid}]}
    captured['data_document']['context_selection']=deepcopy(captured['actual_selection'])
    next(n for n in captured['remote_document']['nodes'] if n['id']=='provider')['original_ids'].append(second)
    captured['manifest_sha256']=workspace['_manifest_hash'];captured['input_binding']['workspace_fingerprint']=digest(_workspace(workspace))
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);refresh_documents(captured)
    view=aggregate_service_topology(captured);other.unlink()
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref,second])
    report=api().explain_view_element(view,view.edges[0].id,captured=captured,graph=graph,source_status=status)
    locators=report['source_locators'];assert {r['repo_id'] for r in locators}=={'backend','other'}
    assert {r['path'] for r in locators}=={'src/main/java/demo/Code.java'}
    assert len({r['source_sha256'] for r in locators})==2
    assert {r['status'] for r in locators}=={'CONTENT_MATCH','SOURCE_MISSING'}
    assert report['current_source_status']=='MIXED_SOURCE_STATUS'


def test_status_capture_rejects_symlinked_manifest_even_with_identical_bytes(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    manifest=Path(workspace['_manifest_path']);copy=tmp_path/'copied-manifest.json';copy.write_bytes(manifest.read_bytes())
    manifest.unlink();manifest.symlink_to(copy)
    with pytest.raises(ValueError):api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])


def test_kafka_explanation_preserves_channel_realm_group_and_capture_time_unknown():
    captured=labelled_handoff('KAFKA');view=aggregate_service_topology(captured)
    consume=next(e for e in view.edges if e.relation=='consumes_from_channel')
    report=api().explain_view_element(view,consume.id,captured=captured)
    assert report['broker_realm']=='alpha' and report['topic']=='orders' and report['consumer_group']=='group-one'
    assert report['capture_freshness']=='CAPTURE_TIME_ONLY' and report['freshness']=='UNKNOWN'
    assert report['runtime_availability']=='UNKNOWN' and report['runtime_execution']=='NOT_OBSERVED'
    assert report['source_status_authority']=='NOT_SUPPLIED' and report['current_source_status']=='NOT_CHECKED'


def test_canonical_repo_namespace_does_not_hide_recognizable_userinfo_credentials():
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    identity=qualified('backend','opaque //user:PRIVATE_SENTINEL@host/path')
    with pytest.raises(ValueError) as error:api().explain_view_element(view,identity,captured=captured)
    assert 'PRIVATE_SENTINEL' not in str(error.value) and identity not in repr(error.value)


def test_unicode_source_path_with_spaces_remains_exact_during_confined_read(tmp_path):
    workspace,graph,captured,source,ref=bound_source(tmp_path)
    moved=source.with_name('Částka Handler.java');source.rename(moved)
    old=graph.nodes[0].path;path='@backend/src/main/java/demo/'+moved.name
    record=graph.symbols[0];record['path']=path;graph.nodes[0].metadata['path']=path
    graph.nodes[0]=Node(**{**vars(graph.nodes[0]),'path':path})
    checksum=graph.files.pop(old);graph.files[path]=checksum;graph.contexts[0]['source_files']={path:checksum}
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);rehash(captured)
    status=api().capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    assert status['locators'][0]['path']=='src/main/java/demo/Částka Handler.java'
    assert status['locators'][0]['status']=='CONTENT_MATCH'


def test_qualified_code_field_name_is_not_mistaken_for_credential_value():
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    identity=qualified('backend','symbol:field:demo.Config.password:Ljava/lang/String;')
    report=api().explain_view_element(view,identity,captured=captured)
    assert report['status']=='UNKNOWN_ELEMENT' and report['element_id']==identity


def test_exact_framework_local_compiler_alias_keeps_existing_qualified_field_reference(tmp_path):
    from kgmaker.architecture_model import ViewEdge
    workspace,graph,captured,source,old=bound_source(tmp_path)
    local='symbol:field:demo.Config.password:Ljava/lang/String;';identity=qualified('backend',local)
    record=graph.symbols[0];record.update(id=identity,kind='field',name='password',owner='demo.Config',descriptor='Ljava/lang/String;')
    graph.nodes=[Node(identity,'field','password',record['path'],1,'Ljava/lang/String;',scope='production',metadata=deepcopy(record))]
    proof={'id':'field-proof','kind':'FRAMEWORK_DERIVED','repo_id':'backend','source':identity,
        'context_ids':[record['context_id']],'compiler_symbol_id':local,'sha256':record['sha256']}
    graph.evidence=[proof]
    captured['data_document']['provenance']=[{'id':'field-proof','evidence_kind':'FRAMEWORK_DERIVED',
        'freshness':'CURRENT','polarity':'SUPPORTING','source_id':identity}]
    captured['data_document']['edges']=[ViewEdge('field-use','service:checkout','service:orders','depends_on',
        evidence_refs=('field-proof',),evidence_kinds=('FRAMEWORK_DERIVED',),supporting_refs=('field-proof',),
        resolution_status='RESOLVED',freshness='CURRENT',attributes={'scope':'production'}).to_dict()]
    captured['input_binding']['graph_fingerprint']=digest(_graph(graph));captured['shared_input_hash']=digest(captured['input_binding']);refresh_documents(captured)
    view=aggregate_service_topology(captured)
    report=api().explain_view_element(view,'field-use',captured=captured,graph=graph)
    assert identity in report['expanded_reference_ids'] and report['source_locators'][0]['reference_id']==identity


@pytest.mark.parametrize('local',['password=PRIVATE_SENTINEL','secret:PRIVATE_SENTINEL'])
def test_namespace_decoding_rejects_credential_assignments_without_rewriting_ids(local):
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    identity=qualified('backend',local)
    with pytest.raises(ValueError) as error:api().explain_view_element(view,identity,captured=captured)
    assert 'PRIVATE_SENTINEL' not in str(error.value) and identity not in repr(error.value)


def test_typed_field_privacy_exception_does_not_bypass_identifier_length_limit():
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    identity='symbol:field:demo.Config.password:L'+'A'*5000+';'
    with pytest.raises(ValueError):api().explain_view_element(view,identity,captured=captured)

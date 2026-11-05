"""W07 public acceptance RED; no producer implementation or implicit discovery."""
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

from test_t013_attach_interface_contracts import fixture as explicit_contract_fixture
from test_t013_attach_interface_contracts import inputs, capture as contract_capture, attach
from test_t012_catalog_kafka_interfaces import capture as kafka_capture
from test_t011_catalog_http_consumers import captured as http_capture


def api():
    name='kgmaker.remote_mapping'
    assert importlib.util.find_spec(name) is not None, 'W07 pure remote mapping/capture API is not implemented'
    module=importlib.import_module(name)
    assert callable(getattr(module,'capture_remote_mapping_inputs',None))
    assert callable(getattr(module,'resolve_remote_mappings',None))
    return module


def test_public_canonical_capture_and_offline_empty_mapping(explicit_contract_fixture):
    workspace,graph,catalog=inputs(explicit_contract_fixture)
    catalog=attach(workspace,graph,catalog,contract_capture(workspace,graph))
    module=api()
    captured=module.capture_remote_mapping_inputs(workspace,graph,scope='production')
    assert set(captured)=={'schema_version','rule_version','workspace_id',
        'workspace_manifest_sha256','workspace_fingerprint','graph_fingerprint','selection',
        'remote_declarations','contract_capture','canonical_interfaces','diagnostics','capture_id'}
    assert captured['canonical_interfaces']
    before=copy.deepcopy(workspace),graph.to_dict(),catalog.to_dict(),copy.deepcopy(captured)
    def forbidden(*args,**kwargs):raise AssertionError('Pure W07 resolver invoked I/O/upstream projector')
    with patch('pathlib.Path.open',forbidden),patch('pathlib.Path.read_bytes',forbidden),patch('pathlib.Path.read_text',forbidden),\
            patch('subprocess.Popen',forbidden),patch('socket.socket',forbidden),\
            patch('kgmaker.interfaces.project_http_providers',forbidden),\
            patch('kgmaker.interfaces.project_http_consumers',forbidden),\
            patch('kgmaker.interfaces.project_kafka_interfaces',forbidden),\
            patch('kgmaker.interfaces.capture_interface_contracts',forbidden),\
            patch('kgmaker.interfaces.attach_interface_contracts',forbidden):
        result=module.resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],
            captured=captured,scope='production')
    assert result['bindings']==[]  # no explicit mapping: no name/URL auto-binding
    assert (workspace,graph.to_dict(),catalog.to_dict(),captured)==before


def persist(kind,workspace,graph,coverage):
    directory=os.environ.get('KGMAKER_REMOTE_CAPTURE_RED_DIR')
    if directory:
        target=Path(directory);target.mkdir(parents=True,exist_ok=True)
        (target/(kind+'.json')).write_text(json.dumps({'workspace_id':workspace['workspace_id'],
            'graph':graph.to_dict(),'coverage':coverage},indent=2))


def test_actual_kafka_canonical_capture_contract_before_resolution(kafka_capture):
    workspace,graph,coverage=kafka_capture
    assert any(n.kind=='kafka_code_listener' for n in graph.nodes)
    assert any(n.kind=='kafka_code_producer' for n in graph.nodes)
    persist('kafka',workspace,graph,coverage)  # completed native fixture before feature RED
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    assert any(n['kind']=='kafka_interface' for doc in captured['canonical_interfaces'] for n in doc['nodes'])
    assert captured['selection']['scope']=='production'


def test_actual_http_canonical_capture_contract_before_resolution(http_capture):
    workspace,graph,coverage=http_capture
    assert any(n.kind=='http_request_definition' for n in graph.nodes)
    persist('http',workspace,graph,coverage)
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    assert any(n['kind']=='http_interface' for doc in captured['canonical_interfaces'] for n in doc['nodes'])
    assert captured['selection']['scope']=='production'


def trusted_protocol_specimen(transport='HTTP'):
    """Hand-labelled local capture HANDOFF, not authentication/native evidence.

    This exercises pure compatibility policy. Actual capture tests independently
    require canonical upstream producers; no fabricated native positive is claimed.
    """
    from kgmaker.analysis_model import digest
    from kgmaker.architecture_model import ViewDocument,ViewNode
    from kgmaker.model import KnowledgeGraph
    from kgmaker.remote_mapping import VERSION,_views,_workspace,_graph
    sha='a'*64;pointer='#/paths/~1orders/post' if transport=='HTTP' else ''
    workspace={'schema_version':1,'workspace_id':'manual-protocol',
        'repositories':[{'id':'contract','role':'shared','path':'contract','_root':'/explicit/contract'}],
        'services':[{'id':s,'contract':{'repo_id':'contract','path':'orders.json'}} for s in ['checkout','orders']],
        '_manifest_hash':'f'*64}
    contract={'repo_id':'contract','path':'orders.json','sha256':sha,'pointer':pointer}
    source={'id':'client-v1','service_id':'checkout','interface_id':'client','context_id':'client-context',
        'scope':'production','release':'v1','contract':copy.deepcopy(contract)}
    target={'id':'provider-v1','service_id':'orders','interface_id':'provider','context_id':'server-context',
        'scope':'production','release':'v1','contract':copy.deepcopy(contract)}
    workspace['remote_mapping']={'schema_version':1,'releases':[source,target],'compatibilities':[],
        'mappings':[{'id':'one','transport':transport,'source_release_id':'client-v1',
                     'target_release_id':'provider-v1','compatibility_id':None}]}
    contexts=[{'id':cid,'scope':'production','freshness':'CONTENT_VERIFIED'} for cid in ['client-context','server-context']]
    graph=KnowledgeGraph(3,'.','now',[],[],{},contexts=contexts)
    def node(identity,service,cid,direction):
        attrs={'direction':direction,'service_id':service,'context_id':cid,'scope':'production',
            'contract_bindings':[{'status':'BOUND_DECLARATION','contract':{'repo_id':'contract','path':'orders.json'},
                'raw_sha256':sha,'operation_pointer':pointer if transport=='HTTP' else None}],
            'execution_status':'UNSUBSCRIBED_WITHIN_SCOPE','payload_compatibility':'UNKNOWN',
            'http_method':'POST','route_expression':'/orders','normalized_route':'/orders'}
        if transport=='KAFKA':attrs.update(code_binding='VERIFIED_STATIC',broker_realm='alpha',topics=['orders'],topic_pattern=None,
            subscription_kind='TOPICS',consumer_group='group-one' if identity=='provider' else None,
            message_contract_ref={'release':'v1','sha256':sha,'source_file':'@contract/orders.json'})
        return ViewNode(identity,'http_interface' if transport=='HTTP' else 'kafka_interface',identity,
            owner_id='service:'+service,attributes=attrs,resolution_status='RESOLVED',freshness='CURRENT')
    first=node('client','checkout','client-context','CONSUMER' if transport=='HTTP' else 'PRODUCER')
    second=node('provider','orders','server-context','PROVIDED' if transport=='HTTP' else 'CONSUMER')
    docs=[ViewDocument('p','interfaces','b','http-providers-1','production',{},nodes=(second,) if transport=='HTTP' else ()),
          ViewDocument('c','interfaces','b','http-consumers-1','production',{},nodes=(first,) if transport=='HTTP' else ()),
          ViewDocument('k','interfaces','b','kafka-interfaces-1','production',{},nodes=(first,second) if transport=='KAFKA' else ())]
    documents=_views(docs)
    capture={'schema_version':1,'rule_version':VERSION,'workspace_id':workspace['workspace_id'],
        'workspace_manifest_sha256':workspace['_manifest_hash'],'workspace_fingerprint':digest(_workspace(workspace)),
        'graph_fingerprint':digest(_graph(graph)),'selection':{'scope':'production','selected_contexts':[],
            'source_coverage_fingerprint':digest(None)},'remote_declarations':copy.deepcopy(workspace['remote_mapping']),
        'canonical_interfaces':copy.deepcopy(documents),'contract_capture':{'files':{'@contract/orders.json':{
            'status':'CAPTURED','indexed':True,'raw_sha256':sha,'pointers':['#',pointer],'pointers_truncated':False}}},'diagnostics':[]}
    refresh_handoff(workspace,graph,documents,capture)
    return workspace,graph,documents,capture


def refresh_handoff(workspace,graph,documents,captured):
    """Only fixture constructor mutates hand-labelled trusted input authority."""
    from kgmaker.analysis_model import digest
    from kgmaker.remote_mapping import _views,_workspace,_graph,validate_remote_declarations
    captured.update(workspace_fingerprint=digest(_workspace(workspace)),graph_fingerprint=digest(_graph(graph)),
        canonical_interfaces=_views(documents),remote_declarations=validate_remote_declarations(workspace))
    captured['capture_id']=digest({k:v for k,v in captured.items() if k!='capture_id'})


def solve(specimen):
    workspace,graph,documents,captured=specimen
    return api().resolve_remote_mappings(workspace,graph,documents,captured=captured,scope='production')


def test_public_protocol_exact_binding_preserves_transport_and_no_runtime_claim():
    for transport,kind in [('HTTP','HTTP_REQUEST_RESPONSE'),('KAFKA','ASYNC_PUBLISH_SUBSCRIBE')]:
        specimen=trusted_protocol_specimen(transport);before=copy.deepcopy((specimen[0],specimen[1].to_dict(),specimen[2:]))
        row=solve(specimen)['bindings'][0]
        assert row['resolution_status']=='RESOLVED' and row['candidates'][0]['transition_kind']==kind
        assert row['runtime_execution']=='NOT_OBSERVED' and row['payload_compatibility']=='UNKNOWN'
        assert row['candidates'][0]['context_ids']==['client-context','server-context']
        if transport=='HTTP':assert row['execution_intent']=='UNSUBSCRIBED_WITHIN_SCOPE'
        assert (specimen[0],specimen[1].to_dict(),specimen[2:])==before


import pytest


@pytest.mark.parametrize('field',['release','sha256','pointer'])
def test_default_mismatch_has_no_confirmed_remote_transition(field):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    release=workspace['remote_mapping']['releases'][1]
    if field=='release':release['release']='v2'
    else:release['contract'][field]='b'*64 if field=='sha256' else '#/paths/~1other/post'
    refresh_handoff(*specimen)
    row=solve(specimen)['bindings'][0]
    assert row['resolution_status']=='UNRESOLVED' and row['candidates']==[]
    assert 'REMOTE_CONTRACT_OR_RELEASE_INCOMPATIBLE' in row['reasons']


def test_explicit_paired_compatibility_is_directional_and_never_payload_equivalence():
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    workspace['remote_mapping']['releases'][1]['release']='service-release-42'
    workspace['remote_mapping']['compatibilities']=[{'id':'pair','source_release_id':'client-v1',
        'target_release_id':'provider-v1','assertion':'DECLARED_OPERATION_COMPATIBILITY'}]
    workspace['remote_mapping']['mappings'][0]['compatibility_id']='pair'
    refresh_handoff(*specimen)
    row=solve(specimen)['bindings'][0]
    assert row['resolution_status']=='RESOLVED'
    assert row['candidates'][0]['compatibility']=='EXPLICIT_PAIRED_DECLARATION'
    assert row['payload_compatibility']=='UNKNOWN'
    workspace['remote_mapping']['compatibilities'][0]['source_release_id']='provider-v1'
    with pytest.raises(ValueError,match='REMOTE_COMPATIBILITY_PAIR_MISMATCH'):refresh_handoff(*specimen)


@pytest.mark.parametrize('tamper',['graph','interface','selection','workspace','declaration','capture','rules'])
def test_original_captured_authority_rejects_changed_supplied_inputs_without_io(tamper):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen();original=copy.deepcopy(captured)
    if tamper=='graph':graph.files['foreign']='b'*64
    elif tamper=='interface':docs[0]['nodes'][0]['attributes']['context_id']='foreign'
    elif tamper=='selection':captured['selection']['scope']='test'
    elif tamper=='workspace':workspace['services'][0]['id']='foreign'
    elif tamper=='declaration':captured['remote_declarations']['releases'][0]['release']='foreign'
    elif tamper=='capture':captured['contract_capture']['files']['@contract/orders.json']['indexed']=False
    else:captured['rule_version']='unknown'
    before=copy.deepcopy((workspace,graph.to_dict(),docs,captured))
    with patch('pathlib.Path.open',side_effect=AssertionError('unexpected IO')),pytest.raises(ValueError):solve(specimen)
    assert (workspace,graph.to_dict(),docs,captured)==before


@pytest.mark.parametrize('field,value',[('context_id','foreign'),('service_id','orders'),('scope','test')])
def test_explicit_realm_selector_never_binds_other_context(field,value):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    workspace['remote_mapping']['releases'][0][field]=value
    if field in {'service_id','scope'}:
        with pytest.raises(ValueError):refresh_handoff(*specimen)
    else:
        refresh_handoff(*specimen);assert solve(specimen)['bindings'][0]['candidates']==[]


@pytest.mark.parametrize('mutation',['regex','realm','topic','config_only'])
def test_kafka_declared_intent_does_not_bridge_unknown_realms_or_patterns(mutation):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen('KAFKA')
    node=next(n for doc in docs for n in doc['nodes'] if n['id']=='provider')
    if mutation=='regex':node['attributes']['topic_pattern']='orders.*'
    elif mutation=='realm':node['attributes']['broker_realm']='other'
    elif mutation=='topic':node['attributes']['topics']=['other']
    else:node['attributes']['code_binding']='UNPROVEN'
    refresh_handoff(*specimen)
    assert solve(specimen)['bindings'][0]['candidates']==[]


def test_two_authorized_targets_remain_ambiguous_independent_of_mapping_order():
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    provider_doc=next(d for d in docs if any(n['id']=='provider' for n in d['nodes']))
    second=copy.deepcopy(next(n for n in provider_doc['nodes'] if n['id']=='provider'));second['id']='provider-two'
    provider_doc['nodes'].append(second)
    release=copy.deepcopy(workspace['remote_mapping']['releases'][1]);release.update(id='provider-v1-two',interface_id='provider-two')
    workspace['remote_mapping']['releases'].append(release)
    mapping=copy.deepcopy(workspace['remote_mapping']['mappings'][0]);mapping.update(id='two',target_release_id=release['id'])
    workspace['remote_mapping']['mappings'].append(mapping)
    refresh_handoff(*specimen);first=solve(specimen)
    assert first['bindings'][0]['resolution_status']=='AMBIGUOUS'
    assert {c['target_interface_id'] for c in first['bindings'][0]['candidates']}=={'provider','provider-two'}
    workspace['remote_mapping']['mappings'].reverse();refresh_handoff(*specimen)
    assert solve(specimen)['bindings']==first['bindings']


@pytest.mark.parametrize('bad',[True,2,[],{},'1'])
def test_manifest_unknown_version_is_a_controlled_error(bad):
    workspace,*_=trusted_protocol_specimen();workspace['remote_mapping']['schema_version']=bad
    from kgmaker.remote_mapping import validate_remote_declarations
    with pytest.raises(ValueError):validate_remote_declarations(workspace)


def test_cycle_and_shared_input_budget_are_bounded_before_copy_or_digest():
    from kgmaker.remote_mapping import validate_remote_declarations
    workspace,*_=trusted_protocol_specimen();value=workspace['remote_mapping'];value['extra']=value
    with pytest.raises(ValueError,match='REMOTE_CYCLIC_INPUT'):validate_remote_declarations(workspace)


def _declare_real_pair(workspace,graph,coverage,transport,*,allow_unresolved_source=False):
    """Reuse successful native capture; declare exact user mapping in its manifest."""
    from kgmaker.workspace import load_workspace,snapshot_workspace
    workspace=load_workspace(Path(workspace['_manifest_path']))
    _,coverage,_,graph,_=snapshot_workspace(Path(workspace['_manifest_path']))
    first=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    nodes=[n for doc in first['canonical_interfaces'] for n in doc['nodes']
        if n['kind']==('http_interface' if transport=='HTTP' else 'kafka_interface')
        and (n['resolution_status']=='RESOLVED' or allow_unresolved_source and n['attributes'].get('direction')=='CONSUMER')]
    if transport=='KAFKA':
        source=next(n for n in nodes if n['attributes'].get('direction')=='PRODUCER'
            and n['attributes'].get('code_binding')=='VERIFIED_STATIC' and n['attributes'].get('contract_bindings'))
        target=next(n for n in nodes if n['attributes'].get('direction')=='CONSUMER'
            and n['attributes'].get('broker_realm')==source['attributes']['broker_realm']
            and n['attributes'].get('topics')==source['attributes']['topics'] and n['attributes'].get('contract_bindings'))
    else:
        source=next(n for n in nodes if n['attributes'].get('direction')=='CONSUMER'
            and n['attributes'].get('service_id')=='checkout'
            and (n['attributes'].get('route_expression')=='/orders' or allow_unresolved_source))
        target=next(n for n in nodes if n['attributes'].get('direction')=='PROVIDED'
            and n['attributes'].get('service_id')=='orders'
            and n['attributes'].get('normalized_route')=='/orders')
    binding=next(b for b in target['attributes']['contract_bindings'] if b['status']=='BOUND_DECLARATION')
    by_id={n.id:n for n in graph.nodes}
    releases=[]
    for label,node in [('source-release',source),('target-release',target)]:
        attrs=node['attributes']
        context=attrs.get('context_id') or (attrs.get('context_ids') or [None])[0]
        if context is None:context=by_id[attrs['code_fact_id']].metadata['context_id']
        release=attrs.get('message_contract_ref',{}).get('release') or 'declared-v1'
        releases.append({'id':label,'service_id':attrs.get('service_id') or node['owner_id'].removeprefix('service:'),
            'interface_id':node['id'],'context_id':context,'scope':'production','release':release,
            'contract':{**binding['contract'],'sha256':binding['raw_sha256'],
                        'pointer':binding['operation_pointer'] or ''}})
    manifest=Path(workspace['_manifest_path']);value=json.loads(manifest.read_text())
    value['remote_mapping']={'schema_version':1,'releases':releases,'compatibilities':[],
        'mappings':[{'id':'explicit-pair','transport':transport,'source_release_id':'source-release',
                     'target_release_id':'target-release','compatibility_id':None}]}
    manifest.write_text(json.dumps(value))
    workspace=load_workspace(manifest);_,coverage,_,graph,_=snapshot_workspace(manifest)
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    return workspace,graph,captured


def test_actual_explicit_kafka_mapping_retains_broker_group_and_no_delivery(kafka_capture):
    workspace,graph,captured=_declare_real_pair(*kafka_capture,'KAFKA')
    before=copy.deepcopy(workspace),graph.to_dict(),copy.deepcopy(captured)
    result=api().resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],captured=captured,scope='production')
    row=result['bindings'][0]
    assert row['resolution_status']=='RESOLVED',result
    assert row['candidates'][0]['consumer_group']=='group-one'
    assert row['candidates'][0]['transition_kind']=='ASYNC_PUBLISH_SUBSCRIBE'
    assert row['delivery']=='NOT_OBSERVED' and row['payload_compatibility']=='UNKNOWN'
    assert (workspace,graph.to_dict(),captured)==before


def _http_toolchain_error(error):
    if error.status!='TOOLCHAIN_UNAVAILABLE':raise error
    if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1':pytest.fail('Required HTTP fixture toolchain unavailable')
    pytest.skip('Optional pinned HTTP fixture toolchain unavailable')


def _http_prerequisites():
    from kgmaker.inspection import command
    from kgmaker.worker_protocol import WorkerError
    from test_http_client_execution import api_jars
    home=Path(__file__).resolve().parents[1]/'workers'
    try:
        command('jvm',home,kotlin_backend='k1')
        jars=api_jars();stdlib=home/'jvm/target/lib/kotlin-stdlib.jar'
        if not stdlib.is_file():raise WorkerError('Kotlin fixture API unavailable','TOOLCHAIN_UNAVAILABLE')
        return jars+[str(stdlib)]
    except WorkerError as error:_http_toolchain_error(error)


def _inspect_http_repo(repo,jars):
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    try:
        return inspect_jvm(repo,home=Path(__file__).resolve().parents[1]/'workers',classpath=jars,
            kotlin_backend='k1',repo_id='local',module=repo.name)
    except WorkerError as error:_http_toolchain_error(error)


@pytest.fixture(scope='module',params=['java','kotlin'])
def real_http_pair(tmp_path_factory,request):
    from kgmaker.inspection import inspect_jvm
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from test_http_client_execution import api_jars
    root=tmp_path_factory.mktemp('remote-http-'+request.param)
    client=root/'client';server=root/'server';other=root/'other';contracts=root/'contracts'
    contracts.mkdir()
    (contracts/'orders-v1.json').write_text(json.dumps({'openapi':'3.0.3','info':{'version':'v1'},
        'paths':{'/orders':{'post':{'responses':{'200':{'description':'OK'}}}}}}))
    (contracts/'orders-v2.json').write_text((contracts/'orders-v1.json').read_text().replace('v1','v2'))
    if request.param=='java':
        source=client/'src/main/java/demo/Client.java';text='''package demo;
import org.springframework.web.reactive.function.client.WebClient;
public class Client { public void lazy(){WebClient.create("https://same.example.invalid").post().uri("/orders").retrieve().bodyToMono(String.class);} }
'''
    else:
        source=client/'src/main/kotlin/demo/Client.kt';text='''package demo
import org.springframework.web.reactive.function.client.WebClient
class Client { fun lazy(){WebClient.create("https://same.example.invalid").post().uri("/orders").retrieve().bodyToMono(String::class.java)} }
'''
    source.parent.mkdir(parents=True);source.write_text(text)
    source=server/'src/main/java/demo/Server.java';source.parent.mkdir(parents=True)
    source.write_text('''package demo;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PostMapping;
@RestController public class Server { @PostMapping("/orders") public String submit(){return "ok";} }
''')
    replica=other/'src/main/java/demo/Server.java';replica.parent.mkdir(parents=True);replica.write_bytes(source.read_bytes())
    jars=_http_prerequisites()
    for repo in [client,server,other]:
        result=_inspect_http_repo(repo,jars)
        assert not any('.err.' in d.get('code','') for d in result['diagnostics']),result['diagnostics']
    manifest=root/'workspace.json'
    manifest.write_text(json.dumps({'schema_version':1,'workspace_id':'explicit-http-pair',
        'repositories':[{'id':name,'path':name,'role':'shared' if name=='contracts' else 'backend'} for name in ['client','server','other','contracts']],
        'services':[{'id':name,'backend_repo':repo,'contract':{'repo_id':'contracts','path':'orders-v2.json' if name=='unrelated' else 'orders-v1.json'}} for name,repo in [('checkout','client'),('orders','server'),('unrelated','other')]],
        'service_ownership':{'schema_version':1,'services':[{'id':name,'roots':[{'repo_id':repo,'path':'src'}],
            'modules':[],'external_systems':[]} for name,repo in [('checkout','client'),('orders','server'),('unrelated','other')]]}}))
    workspace=load_workspace(manifest);_,coverage,_,graph,_=snapshot_workspace(manifest)
    return workspace,graph,coverage,request.param


def test_actual_explicit_http_request_mapping_preserves_unsubscribed_boundary(real_http_pair):
    workspace,graph,coverage,language=real_http_pair
    workspace,graph,captured=_declare_real_pair(workspace,graph,coverage,'HTTP',allow_unresolved_source=language=='kotlin')
    result=api().resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],captured=captured,scope='production')
    row=result['bindings'][0]
    if language=='kotlin':
        assert row['resolution_status']=='UNRESOLVED' and row['candidates']==[]
        assert 'REMOTE_INTERFACE_UNRESOLVED' in row['reasons']
        return  # upstream W06 explicitly has no Kotlin typed request body proof
    assert row['resolution_status']=='RESOLVED',result
    assert row['execution_intent']=='UNSUBSCRIBED_WITHIN_SCOPE'
    assert row['candidates'][0]['transition_kind']=='HTTP_REQUEST_RESPONSE'
    assert row['runtime_execution']=='NOT_OBSERVED' and row['runtime_availability']=='UNKNOWN'
    assert row['payload_compatibility']=='UNKNOWN'


@pytest.mark.parametrize('field,value',[('http_method','GET'),('route_expression','/other')])
def test_explicit_release_does_not_override_known_http_request_operation(field,value):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    source=next(n for d in docs for n in d['nodes'] if n['id']=='client')
    source['attributes'][field]=value;refresh_handoff(*specimen)
    row=solve(specimen)['bindings'][0]
    assert row['resolution_status']=='UNRESOLVED' and row['candidates']==[]
    assert 'REMOTE_OPERATION_MISMATCH' in row['reasons']


def test_different_contract_hashes_need_exact_explicit_pair_not_version_labels():
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    remote=workspace['remote_mapping'];target=remote['releases'][1]
    target['contract'].update(path='orders-v2.json',sha256='b'*64);target['release']='v2'
    workspace['services'][1]['contract']['path']='orders-v2.json'
    node=next(n for d in docs for n in d['nodes'] if n['id']=='provider')
    node['attributes']['contract_bindings'][0].update(contract={'repo_id':'contract','path':'orders-v2.json'},raw_sha256='b'*64)
    captured['contract_capture']['files']['@contract/orders-v2.json']={'status':'CAPTURED','indexed':True,
        'raw_sha256':'b'*64,'pointers':['#','#/paths/~1orders/post'],'pointers_truncated':False}
    refresh_handoff(*specimen)
    assert solve(specimen)['bindings'][0]['candidates']==[]
    remote['compatibilities']=[{'id':'versions','source_release_id':'client-v1','target_release_id':'provider-v1',
        'assertion':'DECLARED_OPERATION_COMPATIBILITY'}]
    remote['mappings'][0]['compatibility_id']='versions';refresh_handoff(*specimen)
    result=solve(specimen)['bindings'][0]
    assert result['resolution_status']=='RESOLVED'
    assert result['candidates'][0]['source_contract']['sha256']!=result['candidates'][0]['target_contract']['sha256']
    assert result['payload_compatibility']=='UNKNOWN'


@pytest.mark.parametrize('damage',['sha','stale','unknown','contract_only','context_scope','context_freshness'])
def test_original_upstream_uncertainty_cannot_be_overridden_by_explicit_mapping(damage):
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    target=next(n for d in docs for n in d['nodes'] if n['id']=='provider')
    if damage=='sha':captured['contract_capture']['files']['@contract/orders.json']['raw_sha256']='b'*64
    elif damage=='stale':target['freshness']='STALE'
    elif damage=='unknown':target['resolution_status']='UNRESOLVED'
    elif damage=='contract_only':target['attributes']['contract_bindings']=[]
    elif damage=='context_scope':graph.contexts[1]['scope']='test'
    else:graph.contexts[1]['freshness']='STALE'
    refresh_handoff(*specimen)
    assert solve(specimen)['bindings'][0]['candidates']==[]


def test_manifest_loader_preserves_existing_artifact_contract_and_validates_new_field(explicit_contract_fixture):
    from kgmaker.workspace import load_workspace
    manifest=explicit_contract_fixture[0];value=json.loads(manifest.read_text())
    value['remote_mapping']={'schema_version':1,'releases':[],'compatibilities':[],'mappings':[]}
    manifest.write_text(json.dumps(value));before=manifest.read_bytes()
    result=load_workspace(manifest)
    assert result['remote_mapping']==value['remote_mapping'] and 'release_mapping' not in result
    assert manifest.read_bytes()==before
    value['remote_mapping']['schema_version']=True;manifest.write_text(json.dumps(value));bad=manifest.read_bytes()
    with pytest.raises(ValueError):load_workspace(manifest)
    assert manifest.read_bytes()==bad


def test_raw_contract_examples_are_not_exported_in_capture_or_report(explicit_contract_fixture):
    manifest,contract,_,_=explicit_contract_fixture
    value=json.loads(contract.read_text());value['example']={'password':'RAW_PRIVATE_SENTINEL_357','Authorization':'Bearer RAW_PRIVATE_SENTINEL_357'}
    contract.write_text(json.dumps(value))
    workspace,graph,_=inputs(explicit_contract_fixture)
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production')
    assert 'RAW_PRIVATE_SENTINEL_357' not in json.dumps(captured)
    assert all('document' not in r for r in captured['contract_capture']['files'].values())


@pytest.mark.parametrize('field,value',[('releases',{}),('mappings',None),('compatibilities','bad')])
def test_bad_manifest_collections_fail_without_mutation(field,value):
    from kgmaker.remote_mapping import validate_remote_declarations
    workspace,*_=trusted_protocol_specimen();workspace['remote_mapping'][field]=value;before=copy.deepcopy(workspace)
    with pytest.raises(ValueError):validate_remote_declarations(workspace)
    assert workspace==before


def test_declared_fanout_over_hard_bound_is_rejected_not_silently_unique():
    from kgmaker.remote_mapping import validate_remote_declarations
    workspace,*_=trusted_protocol_specimen()
    workspace['remote_mapping']['mappings']=[{**workspace['remote_mapping']['mappings'][0],'id':str(i)} for i in range(2001)]
    with pytest.raises(ValueError,match='REMOTE_DECLARATION_LIMIT'):validate_remote_declarations(workspace)


@pytest.mark.parametrize('field',['release_id','release_selector','mapping_id'])
@pytest.mark.parametrize('value',['//alice:PRIVATE_SENTINEL@host/path',
                                'prefix //alice:PRIVATE_SENTINEL@host/path suffix'])
def test_scheme_relative_userinfo_rejected_without_echo_or_immutable_rewrite(field,value,explicit_contract_fixture):
    from kgmaker.remote_mapping import validate_remote_declarations
    from kgmaker.workspace import load_workspace
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    declaration=workspace['remote_mapping']
    if field=='release_id':declaration['releases'][0]['id']=value
    elif field=='release_selector':declaration['releases'][0]['release']=value
    else:declaration['mappings'][0]['id']=value
    before=copy.deepcopy(workspace),graph.to_dict(),copy.deepcopy(docs),copy.deepcopy(captured)
    for action in (lambda:validate_remote_declarations(workspace),
                   lambda:api().capture_remote_mapping_inputs(workspace,graph,scope='production'),
                   lambda:solve(specimen)):
        with pytest.raises(ValueError) as error:action()
        assert 'PRIVATE_SENTINEL' not in str(error.value)
        assert 'alice' not in str(error.value)
        assert getattr(error.value,'diagnostic',{})=={'code':str(error.value)}
    assert (workspace,graph.to_dict(),docs,captured)==before
    manifest,contract,_,_=explicit_contract_fixture
    document=json.loads(manifest.read_text())
    document['services'].append({**copy.deepcopy(document['services'][0]),'id':'checkout',
                                 'frontend_repos':[],'generated_clients':[]})
    remote=trusted_protocol_specimen()[0]['remote_mapping']
    for release in remote['releases']:
        release['contract'].update(repo_id='backend',path='src/main/resources/openapi.json',
                                   sha256=hashlib.sha256(contract.read_bytes()).hexdigest())
    document['remote_mapping']=remote;manifest.write_text(json.dumps(document))
    assert load_workspace(manifest)['remote_mapping']==remote  # otherwise valid manifest
    if field=='release_id':
        remote['releases'][0]['id']=value;remote['mappings'][0]['source_release_id']=value
    elif field=='release_selector':remote['releases'][0]['release']=value
    else:remote['mappings'][0]['id']=value
    manifest.write_text(json.dumps(document));raw=manifest.read_bytes()
    with pytest.raises(ValueError) as error:load_workspace(manifest)
    assert 'PRIVATE_SENTINEL' not in str(error.value) and manifest.read_bytes()==raw



def test_unicode_and_space_contract_references_are_preserved_not_blanket_rejected():
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    path='návrhy objednávek.json'
    for service in workspace['services']:service['contract']['path']=path
    for release in workspace['remote_mapping']['releases']:
        release['contract']['path']=path;release['release']='vydání jedna'
    workspace['remote_mapping']['mappings'][0]['id']='mapování objednávek'
    for document in docs:
        for node in document['nodes']:node['attributes']['contract_bindings'][0]['contract']['path']=path
    files=captured['contract_capture']['files'];files['@contract/'+path]=files.pop('@contract/orders.json')
    refresh_handoff(*specimen)
    result=solve(specimen)['bindings'][0]
    assert result['resolution_status']=='RESOLVED'
    assert result['mapping_ids']==['mapování objednávek']
    assert result['candidates'][0]['source_contract']['path']==path


def test_capture_accepts_explicit_unicode_contract_path_with_spaces(explicit_contract_fixture):
    manifest,contract,_,metadata=explicit_contract_fixture
    moved=contract.with_name('objednávky nové.json');contract.rename(moved)
    relative='src/main/resources/'+moved.name
    document=json.loads(manifest.read_text());document['services'][0]['contract']['path']=relative
    manifest.write_text(json.dumps(document))
    origin=json.loads(metadata.read_text());origin['source_contract']['path']=relative
    metadata.write_text(json.dumps(origin))
    workspace,graph,_=inputs(explicit_contract_fixture)
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production')
    assert '@backend/'+relative in captured['contract_capture']['files']


@pytest.mark.parametrize('entry',['prerequisites','inspection'])
@pytest.mark.parametrize('required',[False,True])
@pytest.mark.parametrize('status',['TOOLCHAIN_UNAVAILABLE','INVALID_PROTOCOL'])
def test_http_fixture_optional_prerequisites_never_mask_protocol_errors(monkeypatch,entry,required,status,tmp_path):
    from kgmaker.worker_protocol import WorkerError
    import kgmaker.inspection
    import test_http_client_execution
    error=WorkerError('fixture diagnostic',status)
    def fail(*args,**kwargs):raise error
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS','1' if required else '0')
    if entry=='prerequisites':
        monkeypatch.setattr(kgmaker.inspection,'command',lambda *a,**k:['not-executed'])
        monkeypatch.setattr(test_http_client_execution,'api_jars',fail)
        call=_http_prerequisites
    else:
        monkeypatch.setattr(kgmaker.inspection,'inspect_jvm',fail)
        call=lambda:_inspect_http_repo(tmp_path,[])
    if status!='TOOLCHAIN_UNAVAILABLE':
        with pytest.raises(WorkerError) as raised:call()
        assert raised.value is error
    elif required:
        with pytest.raises(pytest.fail.Exception):call()
    else:
        with pytest.raises(pytest.skip.Exception):call()


def test_actual_same_url_versions_require_explicit_pair_and_keep_candidate_set(real_http_pair):
    from kgmaker.workspace import load_workspace,snapshot_workspace
    workspace,graph,coverage,language=real_http_pair
    workspace,graph,captured=_declare_real_pair(workspace,graph,coverage,'HTTP',allow_unresolved_source=language=='kotlin')
    baseline=api().resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],captured=captured,scope='production')
    if language=='java':
        assert baseline['bindings'][0]['resolution_status']=='RESOLVED'
        assert {c['target_service_id'] for c in baseline['bindings'][0]['candidates']}=={'orders'}
    unrelated=next(n for d in captured['canonical_interfaces'] for n in d['nodes']
        if n['kind']=='http_interface' and n['attributes'].get('service_id')=='unrelated'
        and n['attributes'].get('direction')=='PROVIDED' and n['resolution_status']=='RESOLVED')
    attrs=unrelated['attributes'];binding=next(b for b in attrs['contract_bindings'] if b['status']=='BOUND_DECLARATION')
    manifest=Path(workspace['_manifest_path']);document=json.loads(manifest.read_text());remote=document['remote_mapping']
    remote['releases'].append({'id':'other-version','service_id':'unrelated','interface_id':unrelated['id'],
        'context_id':attrs['context_ids'][0],'scope':'production','release':'v2',
        'contract':{**binding['contract'],'sha256':binding['raw_sha256'],'pointer':binding['operation_pointer']}})
    remote['mappings'].append({'id':'other-pair','transport':'HTTP','source_release_id':'source-release',
        'target_release_id':'other-version','compatibility_id':None})
    def recapture():
        manifest.write_text(json.dumps(document));ws=load_workspace(manifest)
        _,coverage,_,g,_=snapshot_workspace(manifest)
        capture=api().capture_remote_mapping_inputs(ws,g,scope='production',source_coverage=coverage)
        return api().resolve_remote_mappings(ws,g,capture['canonical_interfaces'],captured=capture,scope='production')
    incompatible=recapture()['bindings'][0]
    assert incompatible['resolution_status']=='UNRESOLVED'
    assert 'REMOTE_CONTRACT_OR_RELEASE_INCOMPATIBLE' in incompatible['reasons']
    remote['compatibilities'].append({'id':'explicit-versions','source_release_id':'source-release',
        'target_release_id':'other-version','assertion':'DECLARED_OPERATION_COMPATIBILITY'})
    remote['mappings'][-1]['compatibility_id']='explicit-versions'
    declared=recapture()['bindings'][0]
    if language=='java':
        assert declared['resolution_status']=='AMBIGUOUS'
        assert {c['target_service_id'] for c in declared['candidates']}=={'orders','unrelated'}
        assert len({c['target_contract']['sha256'] for c in declared['candidates']})==2
    else:assert declared['resolution_status']=='UNRESOLVED' and declared['candidates']==[]
    assert declared['payload_compatibility']=='UNKNOWN' and declared['runtime_execution']=='NOT_OBSERVED'


def test_non_json_capture_keys_have_fixed_error_not_raw_digest_exception():
    specimen=trusted_protocol_specimen();specimen[3]['contract_capture']['files'][('malformed','PRIVATE_KEY_SENTINEL')]={}
    with pytest.raises(ValueError) as raised:solve(specimen)
    assert 'PRIVATE_KEY_SENTINEL' not in str(raised.value)

"""Public static failure paths, never a simulated successful retry or rollback."""
from copy import deepcopy
from dataclasses import replace
import importlib
from unittest.mock import patch

import pytest
from kgmaker.business_process import collapse_business_steps, expand_business_steps, BusinessProcessError
from kgmaker.process_model import ProcessView
from test_t025_build_local_process_path import setup, helper, ir, call, add_cfg, inventory, build_local_process, paths, assert_finally_clone_topology
from test_t028_cross_async_process_boundary import local


def api(*args, **kwargs):
    module=importlib.import_module('kgmaker.business_process')
    assert hasattr(module,'project_process_failures'), 'T029 public failure projection is absent'
    return module.project_process_failures(*args,**kwargs)


def test_finally_keeps_distinct_return_throw_paths_through_collapse(tmp_path):
    w,g,c,m,s=setup(tmp_path); child=helper(g,s,'cleanup')
    add_cfg(g,child['id'],child,ir(child,'statement',label='cleanup-body'))
    cleanup=call(g,s,child,'cleanup')
    body=ir(s,'try',body=ir(s,'if',condition=ir(s,'statement',label='flag'),
        then=ir(s,'return',value=ir(s,'statement',label='returned')),
        **{'else':ir(s,'throw',value=ir(s,'statement',label='thrown'))}),catches=[],**{'finally':cleanup})
    cfg=add_cfg(g,m,s,body);inv,t=inventory(w,g,c,m)
    source=build_local_process(g,inv,t,process_id='process:failures')
    before=source.to_dict(); result=api(collapse_business_steps(source),g)
    grouped=collapse_business_steps(result)
    assert_finally_clone_topology(grouped,cfg,g.call_sites[-1]['id'])
    assert {e.id for e in source.transitions} <= {e.id for e in grouped.transitions}
    assert expand_business_steps(grouped).to_dict()==result.to_dict()
    assert source.to_dict()==before


def test_local_transaction_never_rolls_back_http_or_kafka():
    value=local().to_dict();nodes=value['technical_view']['nodes']
    next(n for n in nodes if n['id']=='local-call')['kind']='transaction_boundary'
    for transport in ['HTTP','KAFKA']:
        remote=deepcopy(nodes[-1]);remote.update(id='remote:'+transport,kind='service_boundary' if transport=='HTTP' else 'async_boundary')
        remote['attributes'].update(transport=transport);nodes.append(remote)
    before=deepcopy(value);result=api(value)
    assert [e.to_dict() for e in result.transitions]==[e.to_dict() for e in ProcessView.from_dict(value).transitions]
    tx=next(n for n in result.steps if n.id=='local-call')
    assert tx.attributes['failure_semantics']['transaction_scope']=='LOCAL_DECLARATION_ONLY'
    assert tx.attributes['failure_semantics']['rollback']=='UNKNOWN'
    for n in result.steps:
        if n.id.startswith('remote:'):assert n.attributes['failure_semantics']['local_transaction_rollback']=='NOT_PROVEN'
    assert any(d['code']=='FAILURE_POLICY_INPUT_UNAVAILABLE' for d in result.technical_view.diagnostics)
    assert value==before


def test_compensation_is_only_an_explicit_proposed_annotation():
    source=local();proposal={'id':'proposal:compensation','target_id':'local-call',
        'label':'Proposed compensation','description':'Candidate business interpretation',
        'source_refs':['local-call'],'semantic_review_status':'PROPOSED'}
    result=api(source,compensation_proposals=[proposal])
    assert result.to_dict()['semantic_annotations']==[proposal]
    assert result.transitions==source.transitions
    assert {n.id for n in result.steps}=={n.id for n in source.steps}
    assert any(d['code']=='COMPENSATION_PROPOSAL_ONLY' for d in result.technical_view.diagnostics)


@pytest.mark.parametrize('mutation',['approved','foreign','technical','budget','cycle'])
def test_invalid_inputs_preserve_input_and_last_artifact(tmp_path,mutation):
    value=local().to_dict();saved=tmp_path/'valid.json';saved.write_text('last valid')
    proposal={'id':'proposal','target_id':'local-call','label':'undo','source_refs':['local-call'],'semantic_review_status':'PROPOSED'}
    kwargs={'compensation_proposals':[proposal]}
    if mutation=='approved':proposal['semantic_review_status']='APPROVED'
    elif mutation=='foreign':proposal['source_refs']=['other-scope-proof']
    elif mutation=='technical':proposal['technical_edges']=[]
    elif mutation=='budget':kwargs['max_policies']=True
    else:proposal['description']=proposal
    before=deepcopy(value)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        with pytest.raises(BusinessProcessError):api(value,**kwargs)
    assert value==before and saved.read_text()=='last valid'


@pytest.fixture(scope='module',params=['java','k1','k2'])
def actual_pipeline(tmp_path_factory,request):
    from pathlib import Path
    from kgmaker.analysis_model import write_json
    from kgmaker.inspection import inspect_jvm
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from kgmaker.process_triggers import discover_process_triggers
    from test_t024_discover_process_triggers import actual_prerequisites
    from test_kafka_code_bindings import extra_api_jars
    from test_kafka_retry_dlt import JAVA,KOTLIN
    base=tmp_path_factory.mktemp('t029-'+request.param);root=base/'backend'
    language='java' if request.param=='java' else 'kotlin';backend='k2' if request.param=='k2' else 'k1'
    folder=root/('src/main/java/demo' if language=='java' else 'src/main/kotlin/demo');folder.mkdir(parents=True)
    jars=actual_prerequisites(backend)+extra_api_jars()
    text=JAVA if language=='java' else KOTLIN
    if language=='java':
        text=text.replace('public void consume(String value) {}','public void consume(String value) { try { if(value.isEmpty()) throw new IllegalStateException(); } catch(IllegalStateException error) { throw error; } finally { cleanup(); } }')
        text=text.replace('@DltHandler','static void cleanup() {}\n @DltHandler')
    else:
        text=text.replace('fun consume(value: String) {}','fun consume(value: String) { try { if(value.isEmpty()) throw IllegalStateException() } catch(error: IllegalStateException) { throw error } finally { cleanup() } }')
        text+='\nprivate fun cleanup() {}\n'
    if language=='java':
        text+='\n'+JAVA[JAVA.index('public class'):].replace('public class RetryEntries','class OtherRetryEntries').replace('group-one','group-two')
    else:
        text+='\n'+KOTLIN[KOTLIN.index('class RetryEntries'):].replace('class RetryEntries','class OtherRetryEntries').replace('group-one','group-two')
    (folder/('RetryEntries.java' if language=='java' else 'RetryEntries.kt')).write_text(text)
    manifest=base/'workspace.json'
    write_json(manifest,{'schema_version':1,'workspace_id':'failures','repositories':[{'id':'backend','role':'backend','path':'backend'}],
        'services':[{'id':'orders','backend_repo':'backend','frontend_repos':[],'test_repos':[],'contract':{'repo_id':'backend','path':'api.json'}}],
        'service_ownership':{'schema_version':1,'services':[{'id':'orders','roots':[{'repo_id':'backend','path':'src'}],
            'modules':[{'repo_id':'backend','id':'app'}],'external_systems':[]}]}})
    captured=inspect_jvm(root,home=Path(__file__).resolve().parents[1]/'workers',repo_id='backend',module='app',source_set='main',scope='production',kotlin_backend=backend,classpath=jars)
    assert not any('.err.' in d.get('code','') or str(d.get('reason','')).startswith('ERROR:') for d in captured['diagnostics'])
    workspace=load_workspace(manifest);_,coverage,_,graph,_=snapshot_workspace(manifest)
    inv=discover_process_triggers(workspace,graph,source_coverage=coverage)
    if backend=='k2':
        assert not any(n.attributes.get('trigger_kind')=='KAFKA' for n in inv.nodes)
        return graph,local(),root,request.param
    trigger=next(n for n in inv.nodes if n.attributes.get('trigger_kind')=='KAFKA' and 'OtherRetryEntries' not in n.attributes['entry_symbol_id'])
    source=build_local_process(graph,inv,trigger.id,process_id='process:retry-actual')
    return graph,source,root,request.param


def test_actual_retry_dlt_static_path_and_finally(actual_pipeline):
    graph,source,root,backend=actual_pipeline
    before=deepcopy((graph.to_dict(),source.to_dict()));files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('no implicit worker')),patch('socket.socket',side_effect=AssertionError('no network')):
        result=api(collapse_business_steps(source),graph)
    rows=[n for n in result.steps if n.attributes.get('failure_role')=='retry']
    if backend=='k2':
        assert not any(n.attributes.get('policy_status')=='DECLARED' for n in rows)
        assert result.technical_status=='PARTIAL'
    else:
        assert len(rows)==1
        retry=rows[0];dlt=next(n for n in result.steps if n.attributes.get('failure_role')=='dlt')
        assert retry.attributes['attempts']==3 and retry.attributes['policy_status']=='DECLARED'
        assert paths(result.transitions,retry.id,dlt.id)
        assert not paths(result.transitions,dlt.id,retry.id)
        origins=[n for n in source.steps if n.kind=='exceptional_exit' and n.attributes.get('method')==retry.attributes['origin_method']]
        assert len(origins)==1 and paths(result.transitions,origins[0].id,retry.id)
        normal=[n for n in source.steps if n.kind=='exit' and n.attributes.get('method')==retry.attributes['origin_method']]
        assert all(not paths(result.transitions,n.id,retry.id) for n in normal)
        assert retry.attributes['execution']=='NOT_OBSERVED' and dlt.attributes['delivery']=='NOT_OBSERVED'
        assert not any(n.attributes.get('method')==dlt.attributes['handler_id'] for n in result.steps)
    assert {e.id for e in source.transitions}<={e.id for e in result.transitions}
    assert (graph.to_dict(),source.to_dict())==before
    assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==files


@pytest.mark.parametrize('mutation',['stale_policy_proof','contradicting_policy_proof','foreign_policy_proof',
    'stale_context','source_only_context','unsupported_version','wrong_hash','stale_process_proof','foreign_policy_context','stale_selection','test_selection','unknown_selection'])
def test_policy_authority_never_borrows_stale_foreign_or_unsupported_proofs(actual_pipeline,mutation):
    from kgmaker.model import KnowledgeGraph
    graph,process,_,backend=actual_pipeline
    raw=deepcopy(graph.to_dict());doc=process.to_dict()
    policies=[n for n in raw['nodes'] if n['kind']=='kafka_retry_policy']
    if backend=='k2':
        assert not policies
        assert not any(n.attributes.get('policy_status')=='DECLARED' for n in api(doc,graph).steps)
        return
    policy=next(n for n in policies if 'OtherRetryEntries' not in n['metadata']['origin_id']);md=policy['metadata'];context=next(c for c in raw['contexts'] if c['id']==md['context_id'])
    edge=next(e for e in raw['edges'] if e['kind']=='declares_retry_boundary' and e['target']==policy['id'])
    proof=next(p for p in raw['evidence'] if p['id']==edge['evidence_ids'][0])
    if mutation=='stale_policy_proof':proof['freshness']='STALE'
    elif mutation=='contradicting_policy_proof':proof['polarity']='CONTRADICTING'
    elif mutation=='foreign_policy_proof':proof['scope']='test'
    elif mutation=='stale_context':context['freshness']='STALE'
    elif mutation=='source_only_context':context['mode']='SOURCE_ONLY'
    elif mutation=='unsupported_version':md['version']='future'
    elif mutation=='wrong_hash':md['source_sha256']='0'*64
    elif mutation=='foreign_policy_context':md['context_id']='foreign'
    elif mutation in {'stale_selection','test_selection','unknown_selection'}:
        from kgmaker.process_model import ProcessDefinition
        selection=doc['definition']['context_selection']
        for service in selection['services'].values():
            if mutation=='test_selection':service['scope']='test'
            elif mutation=='stale_selection':service['status']='STALE'
            else:
                for c in service['contexts']:c['status']='UNKNOWN'
        definition=ProcessDefinition.from_dict(doc['definition'])
        doc['definition_fingerprint']=definition.content_fingerprint
        doc['technical_view']['context_selection']=deepcopy(selection)
    else:
        for p in doc['technical_view']['provenance']:
            if p.get('source_id')==md['origin_id']:p['freshness']='STALE'
        from kgmaker.views import _summarize_view_evidence
        records={p['id']:p for p in doc['technical_view']['provenance']}
        for item in doc['technical_view']['nodes']+doc['technical_view']['edges']:
            if item['evidence_refs']:item.update(_summarize_view_evidence(item['evidence_refs'],records))
    altered=KnowledgeGraph.from_dict(raw);before=deepcopy((raw,doc))
    result=api(doc,altered)
    assert any(n.attributes.get('failure_role')=='retry' and n.attributes['policy_status']=='UNKNOWN' for n in result.steps)
    assert not any(e.attributes.get('failure_transition') for e in result.transitions)
    assert any(d['code']=='FAILURE_POLICY_UNPROVEN' for d in result.technical_view.diagnostics)
    originals=[p.get('original_provenance') for p in result.technical_view.provenance if p.get('authority')=='PROVENANCE_REFERENCE_ONLY']
    assert proof in originals
    assert all(p['evidence_kind']=='UNKNOWN' for p in result.technical_view.provenance if p.get('authority')=='PROVENANCE_REFERENCE_ONLY')
    assert (raw,doc)==before


def test_policy_budget_and_upstream_truncation_are_explicit(actual_pipeline):
    graph,source,_,backend=actual_pipeline
    doc=source.to_dict();doc['technical_view']['coverage']['truncated']=True
    doc['technical_view']['diagnostics'].append({'code':'UPSTREAM_BOUNDED'})
    doc['technical_view']['limits'].append('upstream exact limit')
    result=api(doc,graph,max_policies=0)
    assert result.technical_view.coverage['truncated'] is True
    assert {'code':'UPSTREAM_BOUNDED'} in result.technical_view.diagnostics
    assert 'upstream exact limit' in result.technical_view.limits
    assert not any(e.attributes.get('failure_transition') for e in result.transitions)
    if backend!='k2':
        diagnostic=next(d for d in result.technical_view.diagnostics if d['code']=='FAILURE_POLICY_LIMIT')
        assert set(diagnostic['omitted_policy_ids'])=={n.id for n in graph.nodes if n.kind=='kafka_retry_policy' and 'OtherRetryEntries' not in n.metadata['origin_id']}


@pytest.mark.parametrize('schema',[1,2,3])
def test_legacy_graph_or_policy_names_cannot_invent_retry(schema):
    from kgmaker.model import KnowledgeGraph
    doc=local().to_dict()
    for n in doc['technical_view']['nodes']:
        n['label']='retry compensate rollback'
        n['attributes']['attempts']=3
    result=api(doc,KnowledgeGraph(schema_version=schema,root=".",generated_at="",nodes=[],edges=[],files={}))
    assert not any(n.attributes.get('failure_role') for n in result.steps)
    assert result.transitions==ProcessView.from_dict(doc).transitions
    assert any(d['code']=='FAILURE_POLICY_NOT_PROVEN' for d in result.technical_view.diagnostics)


# Genuine Javac operation certificates exercise stored T026 grouping/finally guards.
from test_local_operation_proofs import pipeline

def test_actual_certified_group_and_finally_clones_survive_projection(pipeline):
    graph,inventory,triggers,_=pipeline
    for name in ('entry','cleanup'):
        source=build_local_process(graph,inventory,triggers[name].id,process_id='process:'+name)
        grouped=collapse_business_steps(source)
        if name=='entry':assert any(n.attributes.get('business_group') for n in grouped.steps)
        result=api(grouped,graph)
        assert {n.id for n in source.steps}=={n.id for n in result.steps}
        assert source.transitions==result.transitions
        simplified=collapse_business_steps(result)
        assert expand_business_steps(simplified).to_dict()==result.to_dict()
        if name=='cleanup':
            clones=[n.id for n in source.steps if n.attributes.get('local_operation')]
            assert len(clones)>=2 and set(clones)<={n.id for n in simplified.steps}


def test_unproved_policy_without_proofs_remains_a_boundary():
    from kgmaker.model import KnowledgeGraph,Node
    doc=local().to_dict()
    next(n for n in doc['technical_view']['nodes'] if n['id']=='local-call')['attributes']['method']='method:unproved'
    graph=KnowledgeGraph(schema_version=3,root='.',generated_at='',nodes=[Node('policy:unproved',
        'kafka_retry_policy','retry','source.java',scope='production',metadata={'origin_id':'method:unproved'})],edges=[],files={})
    result=api(doc,graph)
    boundary=next(n for n in result.steps if n.attributes.get('failure_role')=='retry')
    assert boundary.attributes['policy_status']=='UNKNOWN' and not boundary.evidence_refs
    assert not any(e.attributes.get('failure_transition') for e in result.transitions)


@pytest.mark.parametrize('malformed',[{'schema_version':999}, {'nodes':None}, 'path-is-not-a-snapshot'])
def test_invalid_graph_snapshot_never_mutates_inputs_or_artifact(tmp_path,malformed):
    source=local().to_dict();before=deepcopy((source,malformed))
    artifact=tmp_path/'last-valid.json';artifact.write_text('last valid')
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        with pytest.raises(BusinessProcessError):api(source,malformed)
    assert (source,malformed)==before and artifact.read_text()=='last valid'

def test_unscoped_upstream_truncation_and_selected_diagnostics_survive():
    from kgmaker.model import KnowledgeGraph
    diagnostics=[{'code':'GLOBAL_LIMIT','truncated':True},
        {'code':'SELECTED_LIMIT','context_ids':['client-context']},
        {'code':'FOREIGN_LIMIT','context_id':'other'}, {'code':'TEST_LIMIT','scope':'test'}]
    graph=KnowledgeGraph(schema_version=3,root='.',generated_at='',nodes=[],edges=[],files={},diagnostics=diagnostics)
    result=api(local(),graph)
    codes={d['code'] for d in result.technical_view.diagnostics}
    assert {'GLOBAL_LIMIT','SELECTED_LIMIT'}<=codes
    assert not {'FOREIGN_LIMIT','TEST_LIMIT'}&codes
    assert result.technical_view.coverage['truncated'] is True
    assert graph.diagnostics==diagnostics


@pytest.mark.parametrize('actual_pipeline',['java'],indirect=True)
@pytest.mark.parametrize('entry_kind',['scheduler','other_listener'])
def test_actual_ordinary_listener_callee_has_no_container_policy(actual_pipeline,tmp_path,entry_kind):
    from pathlib import Path
    import shutil
    from kgmaker.inspection import inspect_jvm
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from kgmaker.process_triggers import discover_process_triggers
    from test_t024_discover_process_triggers import actual_prerequisites
    from test_kafka_code_bindings import extra_api_jars
    _,_,original,_=actual_pipeline
    # Each recapture owns its source/cache; the module fixture stays immutable.
    shutil.copytree(original.parent,tmp_path/'fixture');root=tmp_path/'fixture/backend'
    path=root/'src/main/java/demo/RetryEntries.java';text=path.read_text()
    if entry_kind=='scheduler':
        text=text.replace('public void consume(String value) { try','private void consume(String value) { try')
        text=text.replace('static void cleanup()', '@org.springframework.scheduling.annotation.Scheduled(fixedRate=1000) public void scheduled() { consume("payload"); }\n static void cleanup()')
    else:
        text=text.replace('public void consume(String value) { try','public static void consume(String value) { try')
        text=text.replace('public void consume(String value) {}','public void consume(String value) { RetryEntries.consume(value); }')
    path.write_text(text)
    response=inspect_jvm(root,home=Path(__file__).resolve().parents[1]/'workers',repo_id='backend',
        module='app',source_set='main',scope='production',kotlin_backend='k1',
        classpath=actual_prerequisites('k1')+extra_api_jars())
    assert not any('.err.' in d.get('code','') for d in response['diagnostics'])
    manifest=root.parent/'workspace.json';workspace=load_workspace(manifest)
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    inv=discover_process_triggers(workspace,graph,source_coverage=coverage)
    trigger=next(n for n in inv.nodes if n.attributes.get('trigger_kind')=='SCHEDULER') if entry_kind=='scheduler' else next(
        n for n in inv.nodes if n.attributes.get('trigger_kind')=='KAFKA' and 'OtherRetryEntries' in n.attributes['entry_symbol_id'])
    source=build_local_process(graph,inv,trigger.id,process_id='process:'+entry_kind)
    callee=next(n for n in source.steps if n.kind=='exceptional_exit'
        and 'method%3Ademo.RetryEntries.consume' in n.attributes.get('method',''))
    before=deepcopy((source.to_dict(),graph.to_dict()))
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        result=api(source,graph)
    boundary=next(n for n in result.steps if n.attributes.get('source_exceptional_exit')==callee.id)
    assert boundary.attributes['policy_status']=='UNKNOWN' and boundary.evidence_refs
    assert boundary.attributes['kafka_entry_occurrence'] is None
    assert not any(e.attributes.get('failure_transition') and e.source==callee.id for e in result.transitions)
    declared=[n for n in result.steps if n.attributes.get('policy_status')=='DECLARED']
    if entry_kind=='scheduler':
        assert not any(n.kind=='trigger' and n.attributes.get('trigger_kind')=='KAFKA' for n in source.steps)
        assert not declared and not any(e.attributes.get('failure_transition') for e in result.transitions)
    else:
        assert len(declared)==2
        assert all(n.attributes['origin_method']==trigger.attributes['entry_symbol_id'] for n in declared)
    assert {e.id for e in source.transitions}<={e.id for e in result.transitions}
    assert (source.to_dict(),graph.to_dict())==before


@pytest.fixture(scope='module')
def actual_imported_retry(tmp_path_factory):
    """Real T012 -> T014 -> T025 -> T028 plus an ordinary call of the same method."""
    from pathlib import Path
    import json
    from kgmaker.inspection import inspect_jvm
    from kgmaker.model import KnowledgeGraph
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from kgmaker.process_triggers import discover_process_triggers
    from kgmaker.remote_interfaces import project_remote_interfaces
    from kgmaker.business_process import project_async_process_boundary
    from test_kafka_bindings import kafka_workspace
    from test_t024_discover_process_triggers import actual_prerequisites
    from test_kafka_code_bindings import extra_api_jars
    from test_cross_service_contract_mapping import _declare_real_pair
    root,manifest,document=kafka_workspace.__wrapped__(tmp_path_factory.mktemp('t029-import'))
    jars=actual_prerequisites('k1')+extra_api_jars()
    bodies={
        'producer':'''package demo;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
public class Code { private KafkaTemplate<String,String> template;
 @Scheduled(fixedRate=1000) public void publish() { template.send("orders-blue", "payload"); } }
''',
        'consumer':'''package demo;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.annotation.RetryableTopic;
import org.springframework.kafka.annotation.DltHandler;
import org.springframework.scheduling.annotation.Scheduled;
public class Code {
 @RetryableTopic(attempts="3", retryTopicSuffix="-retry", dltTopicSuffix="-dlt")
 @KafkaListener(id="one", topics={"orders-blue"}, groupId="group-one")
 private void one(String value) { try { if(value.isEmpty()) throw new IllegalStateException(); } finally { cleanup(); } }
 @Scheduled(fixedRate=1000) public void scheduled() { one("local"); }
 private void cleanup() {}
 @DltHandler public void dead(String value) {}
}
'''}
    config=root/'consumer/src/main/resources/application.properties'
    config.write_text(config.read_text()+'spring.cloud.stream.bindings.orders-in-0.group=group-one\n')
    facts={}
    for repo,body in bodies.items():
        path=root/repo/'src/main/java/demo/Code.java';path.parent.mkdir(parents=True);path.write_text(body)
        response=inspect_jvm(root/repo,home=Path(__file__).resolve().parents[1]/'workers',kotlin_backend='k1',
            repo_id=repo,classpath=jars,build_context={'spring_profiles':['blue']})
        assert not any('.err.' in str(d.get('code','')) for d in response['diagnostics'])
        graph=KnowledgeGraph.from_dict(response['graph'])
        facts[repo]=(response['context']['id'],next(n for n in graph.nodes if n.kind in {'kafka_code_listener','kafka_code_producer'}))
    document['kafka_bindings']['schema_version']=2
    for binding in document['kafka_bindings']['bindings']:
        cid,fact=facts[binding['repo_id']];binding['context_id']=cid
        binding['code_ref']={'kind':'send' if binding['repo_id']=='producer' else 'listener',
            'id':fact.metadata['origin_id'],'context_id':cid,'source_file':fact.metadata['source_file'],
            'sha256':fact.metadata['source_sha256']}
    manifest.write_text(json.dumps(document));workspace=load_workspace(manifest)
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    workspace,graph,captured=_declare_real_pair(workspace,graph,coverage,'KAFKA')
    remote=project_remote_interfaces(workspace,graph,captured['canonical_interfaces'],captured=captured)
    inv=discover_process_triggers(workspace,graph,source_coverage=coverage)
    processes={next(n.name for n in graph.nodes if n.id==t.attributes['entry_symbol_id']):
        build_local_process(graph,inv,t.id,process_id='actual:'+t.attributes['entry_symbol_id']) for t in inv.nodes}
    assert {'publish','one','scheduled'}<=set(processes)
    imported=project_async_process_boundary(processes['publish'],remote,target_processes=[processes['one']])
    assert any(n.attributes.get('source_process_id')==processes['one'].definition.process_id for n in imported.steps)
    for node in imported.steps:
        if node.attributes.get('async_role')!='subscription':continue
        witness=node.attributes['membership_witness']
        assert witness['capture_id']==captured['capture_id'] and witness['rules_version']==remote.rules_version
        for key in ('source','target','binding'):
            assert witness[key]==next(n.to_dict() for n in remote.nodes if n.id==witness[key]['id'])
        assert witness['edge']==next(e.to_dict() for e in remote.edges if e.id==witness['edge']['id'])
    return graph,imported,processes['scheduled']


def test_actual_imported_entry_and_ordinary_same_method_are_distinct(actual_imported_retry):
    from kgmaker.process_model import ProcessDefinition
    from kgmaker.analysis_model import digest
    graph,imported,ordinary=actual_imported_retry
    doc=deepcopy(imported.to_dict());other=ordinary.to_dict();view=doc['technical_view']
    # Explicit disjoint union of two already captured paths, no inferred order.
    for key in ('nodes','edges','provenance'):
        merged={item['id']:item for item in view[key]}
        for item in other['technical_view'][key]:
            assert item['id'] not in merged or merged[item['id']]==item
            merged[item['id']]=item
        view[key]=list(merged.values())
    for key in ('entry_ids','exit_ids','outcome_ids'):doc[key]=sorted(set(doc[key]+other[key]))
    definition=ProcessDefinition.from_dict({**doc['definition'],'trigger_ids':doc['entry_ids'],
        'baseline_fingerprint':digest([imported.content_fingerprint,ordinary.content_fingerprint])})
    doc.update(definition=definition.to_dict(),definition_fingerprint=definition.content_fingerprint)
    view['baseline_fingerprint']=definition.to_dict()['baseline_fingerprint']
    source=ProcessView.from_dict(doc);before=deepcopy((source.to_dict(),graph.to_dict()))
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        result=api(source,graph)
    retries=[n for n in result.steps if n.attributes.get('failure_role')=='retry']
    assert len(retries)==2
    declared=next(n for n in retries if n.attributes['policy_status']=='DECLARED')
    unknown=next(n for n in retries if n.attributes['policy_status']=='UNKNOWN')
    assert declared.attributes['origin_method']==unknown.attributes['origin_method']
    imported_exit=declared.attributes['source_exceptional_exit'];ordinary_exit=unknown.attributes['source_exceptional_exit']
    assert imported_exit!=ordinary_exit and ':target:' in imported_exit and ':target:' not in ordinary_exit
    assert paths(result.transitions,imported.to_dict()['entry_ids'][0],declared.id)
    assert not paths(result.transitions,ordinary.to_dict()['entry_ids'][0],declared.id)
    assert not any(e.attributes.get('failure_transition') and e.source==ordinary_exit for e in result.transitions)
    assert len([n for n in result.steps if n.attributes.get('failure_role')=='dlt'])==1
    assert declared.attributes['kafka_entry_occurrence']['exceptional_exit_id']==imported_exit
    assert unknown.evidence_refs and result.technical_status=='PARTIAL'
    assert (source.to_dict(),graph.to_dict())==before


@pytest.mark.parametrize('mutation',['missing_subscription','stale_subscription','wrong_import_revision',
    'wrong_trigger_kind','stale_trigger_proof','contradicting_trigger_proof','foreign_trigger_proof',
    'foreign_trigger_original','missing_body_association','foreign_membership_reference'])
def test_imported_retry_requires_current_exact_entry_authority(actual_imported_retry,mutation):
    from kgmaker.views import _summarize_view_evidence
    graph,imported,_=actual_imported_retry;doc=deepcopy(imported.to_dict());view=doc['technical_view']
    trigger=next(n for n in view['nodes'] if n['kind']=='trigger' and n['attributes'].get('trigger_kind')=='KAFKA')
    link=next(e for e in view['edges'] if e['attributes'].get('async_transition')=='CONSUMER_POTENTIAL')
    association=next(e for e in view['edges'] if e['source']==trigger['id']
        and e['attributes'].get('boundary_reason')=='declaration-to-body static association')
    entry=next(n for n in view['nodes'] if n['id']==association['target'])
    proof=next(p for p in view['provenance'] if p['id']==trigger['evidence_refs'][0])
    if mutation=='missing_subscription':view['edges'].remove(link)
    elif mutation=='stale_subscription':link['freshness']='STALE'
    elif mutation=='wrong_import_revision':entry['attributes']['source_process_revision']+=1
    elif mutation=='wrong_trigger_kind':trigger['attributes']['trigger_kind']='SCHEDULER'
    elif mutation=='foreign_membership_reference':
        next(n for n in view['nodes'] if n['id']==link['source'])['attributes']['membership_evidence_refs']=['foreign:membership']
    elif mutation=='missing_body_association':
        view['edges'].remove(association)
    else:
        if mutation=='stale_trigger_proof':proof['freshness']='STALE'
        elif mutation=='contradicting_trigger_proof':proof['polarity']='CONTRADICTING'
        elif mutation=='foreign_trigger_proof':proof['content_hash']='0'*64
        else:proof['original_id']='foreign:unrelated-proof'
        records={p['id']:p for p in view['provenance']}
        for item in view['nodes']+view['edges']:
            if item['evidence_refs']:item.update(_summarize_view_evidence(item['evidence_refs'],records))
    ProcessView.from_dict(doc);before=deepcopy((doc,graph.to_dict()))
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        result=api(doc,graph)
    retries=[n for n in result.steps if n.attributes.get('failure_role')=='retry']
    assert len(retries)==1 and retries[0].attributes['policy_status']=='UNKNOWN'
    assert retries[0].evidence_refs and not any(e.attributes.get('failure_transition') for e in result.transitions)
    assert all(p in result.technical_view.provenance for p in view['provenance'])
    assert any('KAFKA_ENTRY_OCCURRENCE_UNPROVEN' in d.get('reasons',[]) for d in result.technical_view.diagnostics)
    assert result.technical_status=='PARTIAL' and (doc,graph.to_dict())==before


def test_endpoint_proof_cannot_replace_removed_mapping_declarations(actual_imported_retry):
    from kgmaker.views import _summarize_view_evidence
    graph,imported,_=actual_imported_retry;doc=deepcopy(imported.to_dict());view=doc['technical_view']
    byproof={p['id']:p for p in view['provenance']}
    link=next(e for e in view['edges'] if e['attributes'].get('async_transition')=='CONSUMER_POTENTIAL')
    subscription=next(n for n in view['nodes'] if n['id']==link['source'])
    raw=[byproof[ref].get('original_provenance',byproof[ref]) for ref in subscription['evidence_refs']]
    endpoint=next(p for p in raw if not p.get('mapping_ids'))
    assert endpoint['evidence_kind']=='FRAMEWORK_DERIVED'
    removed={ref for ref,p in byproof.items() if p.get('original_provenance',p).get('mapping_ids')}
    assert removed
    for item in view['nodes']+view['edges']:
        if set(item['evidence_refs']) & removed:
            item['evidence_refs']=[ref for ref in item['evidence_refs'] if ref not in removed]
            item.update(_summarize_view_evidence(item['evidence_refs'],byproof))
    view['provenance']=[p for p in view['provenance'] if p['id'] not in removed]
    # Alter both copies, so merely comparing the new witness fields cannot pass this test.
    for item in (subscription,link):
        item['attributes']['membership_evidence_refs']=[endpoint['id']]
        item['attributes']['remote_evidence_refs']=[p['id'] for p in raw if not p.get('mapping_ids')]
    ProcessView.from_dict(doc);before=deepcopy((doc,graph.to_dict()))
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        result=api(doc,graph)
    assert not any(n.attributes.get('policy_status')=='DECLARED' for n in result.steps)
    assert not any(e.attributes.get('failure_transition') for e in result.transitions)
    assert any(n.attributes.get('policy_status')=='UNKNOWN' for n in result.steps)
    assert all(p in result.technical_view.provenance for p in view['provenance'])
    assert (doc,graph.to_dict())==before


@pytest.mark.parametrize('mutation',['legacy','rules','schema_bool','capture','binding','source_endpoint','target_endpoint',
    'scope','context','proof_capture','proof_mapping','proof_kind','binding_proof_as_membership'])
def test_import_requires_exact_t014_tuple_and_declaration_type(actual_imported_retry,mutation):
    from kgmaker.views import _summarize_view_evidence
    graph,imported,_=actual_imported_retry;doc=deepcopy(imported.to_dict());view=doc['technical_view']
    link=next(e for e in view['edges'] if e['attributes'].get('async_transition')=='CONSUMER_POTENTIAL')
    subscription=next(n for n in view['nodes'] if n['id']==link['source'])
    witness=subscription['attributes']['membership_witness'];assert witness
    proofs={p.get('original_provenance',p)['id']:p.get('original_provenance',p) for p in view['provenance']}
    declaration=proofs[witness['edge']['evidence_refs'][0]]
    assert declaration['evidence_kind']=='SOURCE_ONLY' and declaration['mapping_ids']
    if mutation=='legacy':subscription['attributes'].pop('membership_witness')
    elif mutation=='rules':witness['rules_version']='foreign-version'
    elif mutation=='schema_bool':witness['schema_version']=True
    elif mutation=='capture':witness['capture_id']='foreign-capture'
    elif mutation=='binding':witness['binding']['id']='foreign-binding'
    elif mutation=='source_endpoint':witness['source']['id']='foreign-source'
    elif mutation=='target_endpoint':witness['target']['id']='foreign-target'
    elif mutation=='scope':witness['edge']['attributes']['scope']='test'
    elif mutation=='context':witness['edge']['attributes']['context_ids']=['foreign-context']
    elif mutation=='proof_capture':declaration['capture_id']='foreign-capture'
    elif mutation=='proof_mapping':declaration['mapping_ids']=['foreign-mapping']
    elif mutation=='proof_kind':declaration['evidence_kind']='FRAMEWORK_DERIVED'
    else:
        refs=witness['binding']['evidence_refs']
        witness['edge'].update(evidence_refs=deepcopy(refs),unknown_refs=deepcopy(refs))
        subscription['attributes']['membership_evidence_refs']=deepcopy(refs)
    link['attributes']=deepcopy({**subscription['attributes'],'async_transition':'CONSUMER_POTENTIAL'})
    records={p['id']:p for p in view['provenance']}
    for item in view['nodes']+view['edges']:
        if item['evidence_refs']:item.update(_summarize_view_evidence(item['evidence_refs'],records))
    ProcessView.from_dict(doc);before=deepcopy((doc,graph.to_dict()))
    result=api(doc,graph)
    assert not any(n.attributes.get('policy_status')=='DECLARED' for n in result.steps)
    assert not any(e.attributes.get('failure_transition') for e in result.transitions)
    assert any(n.attributes.get('policy_status')=='UNKNOWN' for n in result.steps)
    assert all(p in result.technical_view.provenance for p in view['provenance'])
    assert (doc,graph.to_dict())==before


from test_t028_cross_async_process_boundary import actual_pipeline as actual_other_memberships


@pytest.mark.parametrize('actual_other_memberships',['k1'],indirect=True)
def test_copied_actual_other_endpoint_witness_cannot_authorize_retry(actual_imported_retry,actual_other_memberships):
    from kgmaker.business_process import project_async_process_boundary
    graph,imported,_=actual_imported_retry
    processes,remote,_=actual_other_memberships
    donor=project_async_process_boundary(processes['publish'],remote,target_processes=[processes['one'],processes['two']])
    witnesses=[n.attributes['membership_witness'] for n in donor.steps if n.attributes.get('async_role')=='subscription']
    assert len(witnesses)==2 and all(witnesses)
    for witness in witnesses:
        doc=deepcopy(imported.to_dict());view=doc['technical_view']
        link=next(e for e in view['edges'] if e['attributes'].get('async_transition')=='CONSUMER_POTENTIAL')
        subscription=next(n for n in view['nodes'] if n['id']==link['source'])
        assert witness['target']['id']!=subscription['attributes']['target_interface_id']
        assert witness['capture_id']!=subscription['attributes']['membership_witness']['capture_id']
        for item in (subscription,link):item['attributes']['membership_witness']=deepcopy(witness)
        ProcessView.from_dict(doc);before=deepcopy(doc);result=api(doc,graph)
        assert not any(n.attributes.get('policy_status')=='DECLARED' for n in result.steps)
        assert not any(e.attributes.get('failure_transition') for e in result.transitions)
        assert doc==before


@pytest.mark.parametrize('mutation',['cycle','oversize'])
def test_invalid_witness_respects_existing_bounds_without_mutation(actual_imported_retry,tmp_path,mutation):
    graph,imported,_=actual_imported_retry;doc=deepcopy(imported.to_dict())
    witness=next(n['attributes']['membership_witness'] for n in doc['technical_view']['nodes']
        if n['attributes'].get('async_role')=='subscription')
    if mutation=='cycle':witness['invalid']=witness
    else:witness['invalid']=[None]*50_001
    graph_before=graph.to_dict();saved=tmp_path/'last-valid.json';saved.write_text('last valid')
    nodes_before=len(doc['technical_view']['nodes']);refs_before=deepcopy(doc['technical_view']['provenance'])
    with patch('subprocess.Popen',side_effect=AssertionError('offline')),patch('socket.socket',side_effect=AssertionError('offline')):
        with pytest.raises(BusinessProcessError):api(doc,graph)
    assert saved.read_text()=='last valid' and graph.to_dict()==graph_before
    assert len(doc['technical_view']['nodes'])==nodes_before and doc['technical_view']['provenance']==refs_before
    if mutation=='cycle':assert witness['invalid'] is witness
    else:assert witness['invalid']==[None]*50_001

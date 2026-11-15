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

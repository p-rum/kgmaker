"""Compiler-bound return occurrences/consumers, never observed values."""
import json
import os
from pathlib import Path

import pytest

from kgmaker.inspection import command,inspect_jvm,inspect_frontend
from kgmaker.worker_protocol import WorkerError

HOME=Path(__file__).resolve().parents[1]/'workers'
FIXTURE=Path(__file__).resolve().parents[1]/'fixtures/return-consumer'


def fixture_sources(language):
    root=FIXTURE/language
    return {p.relative_to(root).as_posix():p.read_text() for p in root.rglob('*') if p.is_file()}



def analyze(root,sources,*,language='jvm',backend='k1',compiler_options=None):
    store=root/'.kgmaker'
    before={p.relative_to(store):p.read_bytes() for p in store.rglob('*') if p.is_file()} if store.exists() else None
    try:
        command(language,HOME,kotlin_backend=backend)
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS')=='1' or (backend=='k2' and os.environ.get('KGMAKER_REQUIRE_K2')=='1'):
            pytest.fail(str(error))
        pytest.skip(str(error))
    for name,text in sources.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    if language=='typescript':
        (root/'tsconfig.json').write_text(json.dumps({'compilerOptions':{'strict':True,'target':'ES2020',**(compiler_options or {})},'include':['src/**/*.ts']}))
        result=inspect_frontend(root,home=HOME,publish=False)
    else:
        result=inspect_jvm(root,home=HOME,publish=False,kotlin_backend=backend,
            classpath=[str(HOME/'jvm/target/lib/kotlin-stdlib.jar')])
    assert not any('.err.' in d.get('code','') for d in result['diagnostics']),result['diagnostics']
    if before is None:assert not store.exists()
    else:assert before=={p.relative_to(store):p.read_bytes() for p in store.rglob('*') if p.is_file()}
    return result['graph']


def return_facts(graph):
    values=[e for e in graph['evidence'] if e.get('return_mapping_version')==1 and e.get('relation')=='returns_to']
    assert values,'compiler-proven return-to-consumer facts missing'
    assert all(e['kind']=='SYMBOL_RESOLVED' and e['runtime_execution']=='NOT_OBSERVED' and e['availability']=='UNKNOWN' for e in values)
    return values


@pytest.mark.parametrize('backend',['k1','k2'])
def test_java_branch_returns_assignment_and_chained_receiver(tmp_path,backend):
    graph=analyze(tmp_path,fixture_sources('java'),backend=backend)
    facts=return_facts(graph)
    nodes={n['id']:n for n in graph['nodes']}
    occurrences=[n for n in nodes.values() if (n.get('metadata') or {}).get('value_role')=='RETURN_EXPRESSION']
    assert len(occurrences)==2
    assert len({(n['metadata']['range']['start'],n['metadata']['range']['end']) for n in occurrences})==2
    assert any(f.get('consumer_kind')=='ASSIGNMENT' for f in facts)
    assert any(f.get('consumer_kind')=='RECEIVER' for f in facts)
    results=[n for n in nodes.values() if (n.get('metadata') or {}).get('value_role')=='CALL_RESULT']
    assert results and all(n['id']==n['metadata']['call_site']+':result' for n in results)


def test_k1_nullable_safe_chain_and_generated_destructure(tmp_path):
    graph=analyze(tmp_path,fixture_sources('kotlin'))
    facts=return_facts(graph)
    assert any(f.get('consumer_kind')=='ASSIGNMENT' for f in facts)
    assert len([f for f in facts if f.get('consumer_kind')=='DESTRUCTURE'])==2
    assert any(f.get('condition')=='NON_NULL_RECEIVER' for f in facts)


def test_typescript_branch_nullable_chain_and_destructure(tmp_path):
    graph=analyze(tmp_path,fixture_sources('typescript'),language='typescript')
    facts=return_facts(graph)
    assert any(f.get('consumer_kind')=='ASSIGNMENT' for f in facts)
    assert len([f for f in facts if f.get('consumer_kind')=='DESTRUCTURE'])==4
    assert any(f.get('condition')=='NON_NULL_RECEIVER' for f in facts)


def test_void_references_any_async_and_generator_do_not_invent_values(tmp_path):
    graph=analyze(tmp_path,{'src/negative.ts':'''function source(){return "value";}
function voided():void{}
async function asyncValue(){return "value";}
function* generated(){yield "value";}
export function use(dynamic:any){const ref=source;voided();const missing=dynamic();const pending=asyncValue();const iterator=generated();}
'''},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    results=[n for n in graph['nodes'] if (n.get('metadata') or {}).get('value_role')=='CALL_RESULT']
    assert not results
    sites=graph['call_sites']
    assert all(s.get('return_mapping_status') in {'UNKNOWN','NOT_VALUE','NOT_EXECUTION'} for s in sites)
    assert not any(p.get('return_mapping_version')==1 and p.get('consumer_kind')=='CALL_RESULT' for p in graph['evidence'])


def test_open_dispatch_and_recursion_have_no_declared_body_origin(tmp_path):
    graph=analyze(tmp_path,{'src/main/java/Boundaries.java':'''interface Api {String source();}
class Impl implements Api {public String source(){return "value";}}
class Boundaries {
 static String recursive(int n){return recursive(n+1);}
 static void use(Api api){String a=api.source();String b=recursive(0);}
}'''})
    sites={s['id']:s for s in graph['call_sites']}
    for node in graph['nodes']:
        if (node.get('metadata') or {}).get('value_role')=='CALL_RESULT':
            site=sites[node['metadata']['call_site']]
            assert site['return_body_status']=='UNKNOWN'
    assert not any(p.get('return_mapping_version')==1 and p.get('consumer_kind')=='CALL_RESULT' for p in graph['evidence'])


def test_custom_component_is_unknown_and_generated_component_can_feed_argument(tmp_path):
    graph=analyze(tmp_path,{'src/main/kotlin/Components.kt':'''data class Data(val name:String)
class Custom {operator fun component1():String="unrelated"}
fun data()=Data("value")
fun custom()=Custom()
fun consume(value:String){}
fun use(){val(name)=data();consume(name);val(other)=custom();consume(other)}
'''})
    proofs=[p for p in graph['evidence'] if p.get('return_mapping_version')==1]
    destructures=[p for p in proofs if p.get('consumer_kind')=='DESTRUCTURE']
    assert len(destructures)==1 and destructures[0]['projection']['kind']=='DATA_COMPONENT'
    assert any(p.get('consumer_kind')=='ARGUMENT' and p['source']==destructures[0]['target'] for p in proofs)
    assert any(d.get('code')=='RETURN_DESTRUCTURING_PROJECTION_UNKNOWN' for d in graph['diagnostics'])


def test_assignment_shadowing_and_overwrite_keep_occurrences_distinct(tmp_path):
    graph=analyze(tmp_path,{'src/main/java/Shadow.java':'''class Shadow {
 static String first(){return "first";}static String second(){return "second";}static void consume(String x){}
 static void use(){String same=first();{String other=second();consume(other);}same=second();consume(same);}
}'''})
    facts=return_facts(graph);symbols={s['id']:s for s in graph['symbols']}
    writes=[s for s in symbols.values() if s.get('value_role')=='ASSIGNMENT']
    same=[s for s in writes if s.get('binding_name')=='same']
    assert len(same)==2 and same[0]['id']!=same[1]['id'] and same[0]['binding_id']==same[1]['binding_id']
    used={p['source'] for p in facts if p.get('consumer_kind')=='ARGUMENT'}
    assert sum(s['id'] in used for s in same)==1


def test_k2_kotlin_missing_ir_stays_unknown(tmp_path):
    graph=analyze(tmp_path,{'src/main/kotlin/Unknown.kt':'fun source():String="value"\nfun use(){val assigned=source()}\n'},backend='k2')
    assert not any((n.get('metadata') or {}).get('value_role')=='CALL_RESULT' for n in graph['nodes'])
    assert all(s.get('return_mapping_status')=='UNKNOWN' for s in graph['call_sites'])
    assert any(d.get('code')=='K2_SOURCE_CFG_UNSUPPORTED' for d in graph['diagnostics'])


@pytest.mark.parametrize('version',[1,2,3])
def test_legacy_store_is_readable_without_return_proof(tmp_path,monkeypatch,version):
    from kgmaker.model import KnowledgeGraph,Node,Edge
    from kgmaker.store import save_graph,load_graph
    from kgmaker.return_flow import return_consumer_bindings
    graph=KnowledgeGraph(version,str(tmp_path),'',[Node('a','method','A','A.java'),Node('b','method','B','B.java')],[Edge('a','b','returns_to')],{})
    save_graph(graph,tmp_path,generate_docs=False)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit process'))
    assert return_consumer_bindings(load_graph(tmp_path))==[]


@pytest.mark.parametrize('bad',[
 {'return_flow_version':True},
 {'return_body_kind':'invented'},
 {'return_type':{'version':1,'status':'OBSERVED','type_ref':'string','nullability':'UNKNOWN'}},
])
def test_malformed_return_body_rejected_without_store_mutation(tmp_path,monkeypatch,bad):
    from kgmaker.model import KnowledgeGraph,Node
    from kgmaker.store import save_graph
    from kgmaker.inspection import graph_from_response
    graph=KnowledgeGraph(2,str(tmp_path),'',[Node('valid','class','Valid','Valid.java')],[],{})
    save_graph(graph,tmp_path,generate_docs=False)
    before={p:p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    body={'method':'method','context_id':'ctx','return_flow_version':1,'return_body_kind':'DECLARED',
          'return_type':{'version':1,'status':'VALUE','type_ref':'string','nullability':'UNKNOWN'},'body':{'kind':'block','statements':[]},**bad}
    response={'context_id':'ctx','symbols':[{'id':'method'}],'call_sites':[],'bodies':[body],'facts':[],'diagnostics':[]}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit process'))
    with pytest.raises(WorkerError,match='return|Return') as error:graph_from_response(tmp_path,graph,response,{'id':'ctx'})
    assert error.value.status=='INVALID_PROTOCOL'
    assert before=={p:p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}


def test_return_proof_references_are_repo_qualified():
    from kgmaker.workspace import _qualified_symbol,_qualified_evidence,qualified
    symbol={'id':'value','context_id':'ctx','owner_method':'method','call_site':'site','declared_target':'callee','binding_id':'binding','path':'src/A.java',
            'projection':{'component_target':'component'}}
    value=_qualified_symbol('repo',symbol)
    for key in ('id','context_id','owner_method','call_site','declared_target','binding_id'):assert value[key]==qualified('repo',symbol[key])
    assert value['projection']['component_target']==qualified('repo','component')
    proof={'id':'proof','source':'producer','target':'consumer','context_ids':['ctx'],'source_file':'src/A.java',
           'call_site':'inner','producer_call_site':'inner','consumer_call_site':'outer','declared_target':'callee','projection':{'component_target':'component'}}
    result=_qualified_evidence('repo',proof)
    assert result['producer_call_site']==qualified('repo','inner') and result['consumer_call_site']==qualified('repo','outer')
    assert result['source_file']=='@repo/src/A.java'


def test_branch_alternatives_are_not_sequential_and_nullable_type_is_declared(tmp_path):
    graph=analyze(tmp_path,{'src/main/kotlin/Branches.kt':'fun source(flag:Boolean):String? {if(flag)return "left";return null}\nfun use(){val assigned=source(true)}\n'})
    values=[n for n in graph['nodes'] if (n.get('metadata') or {}).get('value_role')=='RETURN_EXPRESSION']
    assert len(values)==2
    ids={n['id'] for n in values}
    assert not any(e['source'] in ids and e['target'] in ids for e in graph['edges'])
    assert {n['metadata']['branch_guards'][-1]['branch'] for n in values}=={'TRUE','FALSE'}
    results=[n for n in graph['nodes'] if (n.get('metadata') or {}).get('value_role')=='CALL_RESULT']
    assert results and all(n['metadata']['value_type']['nullability']=='MAY_BE_NULL' for n in results)


def test_open_method_literal_body_cannot_prove_destructure_projection(tmp_path):
    graph=analyze(tmp_path,{'src/open.ts':'''class Base {source(){return {name:"base"};}}
class Derived extends Base {source(){return {get name(){return "other";}};}}
export function use(input:Base){const{name}=input.source();}
'''},language='typescript')
    assert not any(p.get('return_mapping_version')==1 and p.get('consumer_kind')=='DESTRUCTURE' for p in graph['evidence'])
    assert any(d.get('code')=='RETURN_DESTRUCTURING_PROJECTION_UNKNOWN' for d in graph['diagnostics'])


@pytest.mark.parametrize('bad',[
 {'value_info':{'version':True,'status':'VALUE','type_ref':'string','nullability':'UNKNOWN'}},
 {'value_targets':None},
 {'value_shape':{'kind':'TUPLE_ELEMENT','size':-1}},
 {'kind':'call','call_site':'foreign'},
 {'kind':'call','call_site':'site','value_info':{'version':1,'status':'VALUE','type_ref':'string','nullability':'UNKNOWN'},'path':'A.java','sha256':'a'*64,'range':{'start':3,'end':7}},
])
def test_malformed_optional_return_expression_proof_is_rejected(bad):
    from kgmaker.return_flow import validate_return_ir
    response={'context_id':'ctx','symbols':[{'id':'method'},{'id':'other'}],
              'call_sites':[{'id':'site','caller':'method','path':'A.java','sha256':'a'*64,'range':{'start':2,'end':7}}, {'id':'foreign','caller':'other'}],
              'bodies':[{'method':'method','context_id':'ctx','return_flow_version':1,'return_body_kind':'DECLARED',
                         'return_type':{'version':1,'status':'VALUE','type_ref':'string','nullability':'UNKNOWN'},'body':bad}]}
    with pytest.raises(ValueError):validate_return_ir(response)


def test_process_and_impact_report_static_return_consumer_provenance(tmp_path):
    from kgmaker.model import KnowledgeGraph
    from kgmaker.flow import process,markdown
    from kgmaker.dataflow import impact_paths
    graph=KnowledgeGraph.from_dict(analyze(tmp_path,fixture_sources('java')))
    entry=next(s['id'] for s in graph.symbols if s.get('name')=='use' and s.get('kind')=='method')
    report=process(graph,entry)
    bindings=[p for block in report['cfg']['blocks'] for p in block.get('return_consumer_bindings',[])]
    assert bindings and all(p['availability']=='UNKNOWN' and p['runtime_execution']=='NOT_OBSERVED' for p in bindings)
    assert 'Static return/consumer bindings' in markdown(report)
    source=next(n.id for n in graph.nodes if (n.metadata or {}).get('value_role')=='RETURN_EXPRESSION')
    impact=impact_paths(graph,source)
    assert impact['return_consumer_bindings']
    assert any(graph_node.kind=='value' and graph_node.id in {node for path in impact['paths'] for node in path['entity_ids']} for graph_node in graph.nodes)


def test_stale_return_rule_is_rejected_without_implicit_refresh(tmp_path,monkeypatch):
    from kgmaker.graph_provider import validate_context_snapshot
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit process'))
    with pytest.raises(WorkerError,match='return/consumer rules changed') as error:
        validate_context_snapshot(tmp_path,{'return_flow_rule_version':'unknown'})
    assert error.value.status=='STALE'


@pytest.mark.parametrize('source,callee',[
    ('class B { static make():number{return 1;} static run():number{return B.make();} } B.make=()=>2; export const result=B.run();','make'),
    ('class B { private make():number{return 1;} run():number{return this.make();} } export const result=new B().run();','make'),
    ('function make():number{return 1;} make=()=>2; export function use(){return make();}','make'),
    ('namespace N {export function make():number{return 1;}} const alias:any=N;alias.make=()=>2;export function use(){return N.make();}','make'),
    ('function make(){return 1;} function use(){return make();} for(make of [()=>2]){} export const result=use();','make'),
    ('function make(){return 1;} function use(){return make();} for([make] of [[()=>2]]){} export const result=use();','make'),
    ('function make(){return 1;} function use(){return make();} for(make in {}){} export const result=use();','make'),
    ('function make(){return 1;} const alias:any=globalThis;alias.make=()=>2;function use(){return make();} use();','make'),
    ('function make(){return 1;} function use(){return make();} ({make}={make:()=>2});export const result=use();','make'),
    ('function make(){return 1;} function use(){return make();} for({make} of [{make:()=>2}]){} export const result=use();','make'),
    ('function make(){return 1;} function use(){return make();} ({slot:make}={slot:()=>2});export const result=use();','make'),
    ('function make(){return 1;} function use(){return make();} ({make=()=>2}={});export const result=use();','make'),
])
def test_mutable_typescript_bodies_do_not_claim_original_return(tmp_path,source,callee):
    graph=analyze(tmp_path,{'src/mutable.ts':source},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')==callee]
    assert sites
    assert all(s.get('return_body_status')=='UNKNOWN' for s in sites)
    assert all(s.get('return_mapping_status')=='PROVEN' for s in sites)
    assert all(s.get('return_body_reason')=='TS_MUTABLE_BODY_BINDING' for s in sites)
    assert not any(e.get('transformation')=='DECLARED_BODY_RETURN' and e.get('call_site') in {s['id'] for s in sites} for e in graph['evidence'])


def test_unassigned_lexical_and_hard_private_typescript_bodies_keep_proof(tmp_path):
    graph=analyze(tmp_path,{'src/closed.ts':'''function lexical():number{return 1;}
class B { #make():number{return 2;} run():number{return this.#make();} }
export function use(){const result=lexical();return result;} export const b=new B().run();'''},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name') in {'lexical','#make'}]
    assert len(sites)==2
    assert all(s.get('return_body_status')=='DECLARED_SOURCE_BODY' for s in sites)


def test_compiler_bound_direct_eval_makes_lexical_body_unknown(tmp_path):
    graph=analyze(tmp_path,{'src/eval.ts':'''function make(){return 1;}
function use(){eval("make=()=>2");return make();} export const result=use();'''},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')=='make']
    assert sites and all(s.get('return_body_status')=='UNKNOWN' for s in sites)
    assert all(s.get('return_body_reason')=='TS_DIRECT_BUILTIN_EVAL' for s in sites)
    assert all(s.get('return_mapping_status')=='PROVEN' for s in sites)
    assert not any(e.get('transformation')=='DECLARED_BODY_RETURN' and e.get('call_site') in {s['id'] for s in sites} for e in graph['evidence'])


def test_const_local_eval_function_is_not_builtin_eval(tmp_path):
    graph=analyze(tmp_path,{'src/shadow.ts':'''function container(){
const eval=(source:string)=>0; function lexical(){return 1;}
function use(){eval("ignored");return lexical();} return use();} container();'''},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')=='lexical']
    assert sites and all(s.get('return_body_status')=='DECLARED_SOURCE_BODY' for s in sites)


def test_ambiguous_local_eval_alias_does_not_claim_lexical_body(tmp_path):
    graph=analyze(tmp_path,{'src/alias-eval.ts':'''function container(){
const eval=globalThis.eval;function lexical(){return 1;}
function use(){eval("lexical=()=>2");return lexical();} return use();} container();'''},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')=='lexical']
    assert sites and all(s.get('return_body_status')=='UNKNOWN' for s in sites)
    assert all(s.get('return_body_reason')=='TS_DIRECT_EVAL_IDENTITY_UNKNOWN' for s in sites)


@pytest.fixture(scope='module')
def captured_return_response(tmp_path_factory):
    """One real compiler response, replayed offline for protocol tampering tests."""
    import copy
    import kgmaker.inspection as inspection
    root=tmp_path_factory.mktemp('captured-return')
    captured={};original=inspection.request_worker
    def capture(argv,payload,**kwargs):
        response=original(argv,payload,**kwargs)
        if payload['operation']=='analyze':
            captured.update(response=copy.deepcopy(response),selected=copy.deepcopy(payload['context']))
        return response
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(inspection,'request_worker',capture)
        graph=analyze(root,{'src/main.ts':'''export function make(){return 1;}
export function other(){const value=make();return value;}
function tuple():[number,string]{return [1,"x"];}
export function unpack(){const[a,b]=tuple();}
function sink(value:number):void{}
export function consume(){sink(make());}
''','src/foreign.ts':'export function foreign(){return 3;}'},language='typescript')
    return root,captured,graph


@pytest.mark.parametrize('mutation',[
    'foreign_literal','missing_literal_path','literal_hash','captured_foreign_literal','literal_range','body_owner','body_context',
    'binding_path','binding_hash','binding_owner','binding_range','node_kind_list','body_kind_dict','body_root_list','body_method_list','status_list','nullability_dict','shape_kind_list','projection_status_dict','projection_kind_list','call_site_list','binding_method_dict','binding_symbol_list','language_list','dispatch_dict','boundary_list','reference_kind_list','range_line_list','range_column_dict','modifiers_scalar','static_flag_list','invocation_kind_list','site_target_dict','site_caller_list','fact_source_list','candidate_dict','symbol_id_list','void_call_range',
])
def test_actual_return_ir_tampering_rejected_without_store_mutation(captured_return_response,monkeypatch,mutation):
    import copy
    from kgmaker.inspection import graph_from_response
    from kgmaker.model import KnowledgeGraph
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    root,captured,graph=captured_return_response
    response=copy.deepcopy(captured['response']);selected=copy.deepcopy(captured['selected'])
    symbols={s['id']:s for s in response['symbols']}
    body=next(b for b in response['bodies'] if symbols[b['method']]['name']=='make')
    other=next(b for b in response['bodies'] if symbols[b['method']]['name']=='other')
    def walk(value):
        if isinstance(value,dict):
            yield value
            for child in value.values():yield from walk(child)
        elif isinstance(value,list):
            for child in value:yield from walk(child)
    literal=next(n['value'] for n in walk(body['body']) if n.get('kind')=='return')
    binding=next(n['value_binding'] for n in walk(other['body']) if isinstance(n.get('value_binding'),dict))
    if mutation=='foreign_literal':literal.update(path='src/not-captured.ts',sha256='0'*64)
    elif mutation=='missing_literal_path':literal.pop('path')
    elif mutation=='literal_hash':literal['sha256']='0'*64
    elif mutation=='modifiers_scalar':symbols[body['method']]['modifiers']=42
    elif mutation=='static_flag_list':symbols[body['method']]['jvm_static']=[]
    elif mutation=='invocation_kind_list':response['call_sites'][0]['invocation_kind']=[]
    elif mutation=='site_target_dict':response['call_sites'][0]['declared_target']={}
    elif mutation=='site_caller_list':response['call_sites'][0]['caller']=[]
    elif mutation=='fact_source_list':response['facts'][0]['source']=[]
    elif mutation=='candidate_dict':response['call_sites'][0]['dispatch_candidates']=[{}]
    elif mutation=='symbol_id_list':symbols[body['method']]['id']=[]
    elif mutation=='void_call_range':
        consumer=next(b for b in response['bodies'] if symbols[b['method']]['name']=='consume')
        call=next(n for n in walk(consumer['body']) if n.get('kind')=='call' and n.get('value_info',{}).get('status')=='VOID')
        call['range']={**call['range'],'start':call['range']['start']+1}
    elif mutation=='captured_foreign_literal':literal.update(path='src/foreign.ts',sha256=selected['source_files']['src/foreign.ts'])
    elif mutation=='literal_range':literal['range']={**literal['range'],'start':0,'end':1}
    elif mutation=='range_line_list':literal['range']['start_line']=[]
    elif mutation=='range_column_dict':literal['range']['end_column']={}
    elif mutation=='body_owner':body['method']=other['method']
    elif mutation=='body_context':body['context_id']='foreign'
    elif mutation=='call_site_list':next(n for n in walk(other['body']) if n.get('kind')=='call')['call_site']=[]
    elif mutation=='binding_method_dict':binding['method']={}
    elif mutation=='binding_symbol_list':binding['symbol']=[]
    elif mutation=='language_list':body['language']=[]
    elif mutation=='dispatch_dict':body['return_dispatch']={}
    elif mutation=='boundary_list':body['return_binding_boundary']=[]
    elif mutation=='reference_kind_list':response['call_sites'][0]['return_reference_kind']=[]
    elif mutation=='binding_path':binding['path']='src/not-captured.ts'
    elif mutation=='binding_hash':binding['sha256']='0'*64
    elif mutation=='binding_owner':binding['method']=body['method']
    elif mutation=='binding_range':binding['range']={**binding['range'],'start':0,'end':1}
    elif mutation=='node_kind_list':literal['kind']=[]
    elif mutation=='body_kind_dict':body['return_body_kind']={}
    elif mutation=='body_root_list':body['body']=[]
    elif mutation=='body_method_list':body['method']=[]
    elif mutation=='status_list':literal['value_info']['status']=[]
    elif mutation=='nullability_dict':literal['value_info']['nullability']={}
    elif mutation=='shape_kind_list':next(n['value_shape'] for n in walk(response['bodies']) if isinstance(n.get('value_shape'),dict))['kind']=[]
    elif mutation=='projection_kind_list':next(n['projection'] for n in walk(response['bodies']) if isinstance(n.get('projection'),dict))['kind']=[]
    elif mutation=='projection_status_dict':next(n['projection'] for n in walk(response['bodies']) if isinstance(n.get('projection'),dict))['status']={}
    save_graph(KnowledgeGraph.from_dict(graph),root,generate_docs=False)
    before={p.relative_to(root):p.read_bytes() for p in (root/'.kgmaker').rglob('*') if p.is_file()}
    base=scan_repository(root)
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('Offline response validation must not launch'))
    with pytest.raises(WorkerError) as error:graph_from_response(root,base,response,selected)
    assert error.value.status=='INVALID_PROTOCOL'
    assert before=={p.relative_to(root):p.read_bytes() for p in (root/'.kgmaker').rglob('*') if p.is_file()}


def test_future_string_ir_kind_is_unknown_not_declared_body(captured_return_response,monkeypatch):
    import copy
    from kgmaker.inspection import graph_from_response
    from kgmaker.scanner import scan_repository
    root,captured,_=captured_return_response
    response=copy.deepcopy(captured['response'])
    symbols={s['id']:s for s in response['symbols']}
    body=next(b for b in response['bodies'] if symbols[b['method']]['name']=='make')
    body['body']['statements'][0]['value']['kind']='future_control_expression'
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('Offline IR replay must not launch'))
    result=graph_from_response(root,scan_repository(root),response,captured['selected'])
    sites=[s for s in result.call_sites if symbols.get(s.get('declared_target'),{}).get('name')=='make']
    assert sites and all(s.get('return_body_status')=='UNKNOWN' for s in sites)
    assert any(d.get('code')=='RETURN_CONTROL_FLOW_UNSUPPORTED' for d in result.diagnostics)


def test_compiler_capture_does_not_upgrade_excluded_source_scope(tmp_path):
    (tmp_path/'.kgmaker').mkdir()
    (tmp_path/'.kgmaker/classification.json').write_text(json.dumps({'schema_version':1,'overrides':[{'path':'src/test','scope':'test','reason':'Explicit test source despite a broad compiler root'}]}))
    graph=analyze(tmp_path,{'src/main.ts':'import {ignored} from "./test/Excluded"; export function make(){return 1;} export function use(){const result=ignored();return make();}',
        'src/test/Excluded.ts':'export function ignored(){return 2;}'},language='typescript')
    symbols={s['id']:s for s in graph['symbols']}
    excluded=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')=='ignored']
    assert excluded and all(s.get('return_body_status')=='UNKNOWN' and s.get('return_body_reason')=='RETURN_SOURCE_SCOPE_NOT_SELECTED' for s in excluded)
    targets={s['declared_target'] for s in excluded}
    assert all(n['scope']=='test' for n in graph['nodes'] if n['id'] in targets)
    assert not any(p.get('return_mapping_version')==1 and p.get('source_file')=='src/test/Excluded.ts' for p in graph['evidence'])
    assert any(p.get('return_mapping_version')==1 and p.get('source_file')=='src/main.ts' for p in graph['evidence'])


def test_commonjs_import_alias_is_not_closed_lexical_body(tmp_path):
    graph=analyze(tmp_path,{'src/dep.ts':'export function make(){return 1;}',
        'src/main.ts':'''import {make} from "./dep";import * as dep from "./dep";
(dep as any).make=()=>2;export function use(){return make();}'''},language='typescript',
        compiler_options={'module':'CommonJS','esModuleInterop':False})
    symbols={s['id']:s for s in graph['symbols']}
    sites=[s for s in graph['call_sites'] if symbols.get(s.get('declared_target'),{}).get('name')=='make']
    assert sites and all(s.get('return_mapping_status')=='PROVEN' for s in sites)
    assert all(s.get('return_body_status')=='UNKNOWN' for s in sites)
    assert not any(e.get('transformation')=='DECLARED_BODY_RETURN' and e.get('call_site') in {s['id'] for s in sites} for e in graph['evidence'])

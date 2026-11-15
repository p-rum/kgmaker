"""W05 actual Javac21/TypeScript5.7.3/React18 captured value path acceptance."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import file_hash, write_json
from kgmaker.inspection import inspect_frontend, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.workspace import qualified, snapshot_workspace

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'
PAGE = '''import React, {useState} from 'react';
import {Exposure} from '../generated/client';
export function ExposurePage() {
  const [view, assign] = useState<Exposure | null>(null);
  async function load() {
    const response = await fetch('/api/exposure');
    const data: Exposure = await response.json();
    const {decline: amount} = data;
    assign({decline: amount});
  }
  return <span data-testid="decline">{view?.decline}</span>;
}
'''
TEST = '''import {Exposure} from '../generated/client';
function check(actual:number) { if(actual !== 2) throw new Error('unexpected'); }
export async function responseTest() {
 const response = await fetch('/api/exposure');
 const data: Exposure = await response.json();
 const {decline: observed} = data;
 check(observed);
}
'''


def require_workers():
    from kgmaker.inspection import command
    from kgmaker.worker_protocol import WorkerError
    try:
        command('jvm', HOME); command('typescript', HOME)
        assert (ROOT/'fixtures/build-inspection/frontend/node_modules/@types/react/index.d.ts').is_file()
    except (WorkerError, AssertionError) as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail(str(error) or 'Pinned React fixture missing')
        pytest.skip(str(error) or 'Pinned React fixture missing')


def prepare_ts(root, source, filename='src/page.tsx'):
    shutil.copytree(ROOT/'fixtures/build-inspection/frontend/node_modules', root/'node_modules')
    (root/'src').mkdir()
    (root/'generated').mkdir()
    (root/'generated/client.ts').write_text('export interface Exposure { decline: number; }\n')
    (root/filename).write_text(source)
    write_json(root/'tsconfig.json', {'compilerOptions': {'strict': True, 'target': 'ES2020',
        'module': 'ESNext', 'moduleResolution': 'node', 'jsx': 'react', 'esModuleInterop': True},
        'include': ['src/**/*', 'generated/**/*']})


def capture_workspace(root):
    require_workers()
    for name in ('backend','frontend','tests'):
        (root/name).mkdir();subprocess.run(['git','init','-q',str(root/name)],check=True)
    java=root/'backend/src/main/java/demo/Exposure.java';java.parent.mkdir(parents=True)
    java.write_text('package demo; public class Exposure { public double decline; }\n')
    result=inspect_jvm(root/'backend',home=HOME,repo_id='backend',publish=True)
    assert not any('.err.' in d.get('code','') for d in result['diagnostics'])
    origin=next(s for s in result['graph']['symbols'] if s.get('kind')=='field' and s.get('name')=='decline')
    contract={'openapi':'3.0.3','info':{'title':'Exposure','version':'v1'},'paths':{'/exposure':{'get':{
        'responses':{'200':{'description':'ok','content':{'application/json':{'schema':{'type':'object','properties':{
            'decline':{'type':'number','x-kgmaker-source':origin['id'],'x-kgmaker-source-sha256':origin['sha256']}}}}}}}}}}}
    (root/'backend/contracts').mkdir();write_json(root/'backend/contracts/exposure.json',contract)
    prepare_ts(root/'frontend',PAGE)
    prepare_ts(root/'tests',TEST,'src/response.ts')
    declarations=[]
    for name,filename in [('frontend','src/page.tsx'),('tests','src/response.ts')]:
        write_json(root/name/'generation.json',{'source_contract':{'repo_id':'backend','path':'contracts/exposure.json',
            'sha256':file_hash(root/'backend/contracts/exposure.json')},'generated_files':['generated/client.ts'],
            'generated_sha256':{'generated/client.ts':file_hash(root/name/'generated/client.ts')},'release':'v1'})
        declarations.append({'repo_id':name,'path':'generated/client.ts','metadata_path':'generation.json','consumers':[filename]})
        result=inspect_frontend(root/name,home=HOME,repo_id=name,ui_framework='react',publish=True)
        assert not any(d.get('code')=='TS_DIAGNOSTIC' and d.get('category')=='Error' for d in result['diagnostics'])
    write_json(root/'workspace.json',{'schema_version':1,'workspace_id':'befe','repositories':[
        {'id':name,'role':role,'path':name} for name,role in [('backend','backend'),('frontend','frontend'),('tests','automated-tests')]],
        'services':[{'id':'exposure-api','backend_repo':'backend','frontend_repos':['frontend'],'test_repos':['tests'],
        'contract':{'repo_id':'backend','path':'contracts/exposure.json'},'consumer_path_prefix':'/api','generated_clients':declarations}]})
    return root,origin


@pytest.fixture(scope='module')
def captured(tmp_path_factory):
    return capture_workspace(tmp_path_factory.mktemp('befe'))


def snapshot(root):
    # Git baseline reads are permitted; no worker, application, package manager or network.
    run=subprocess.Popen
    def git_only(argv,*args,**kwargs):
        assert isinstance(argv,list) and argv[0]=='git', argv
        return run(argv,*args,**kwargs)
    before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    with patch('subprocess.Popen',git_only),patch('socket.socket',side_effect=AssertionError('network')):
        result=snapshot_workspace(root/'workspace.json')
    assert before=={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    return result


def path_between(graph,start,end):
    todo=[(start,[])];seen=set()
    while todo:
        at,route=todo.pop(0)
        if at==end:return route
        if at in seen:continue
        seen.add(at)
        todo.extend((e.target,route+[e]) for e in graph.edges if e.source==at and e.kind in {'maps_to','serialized_as','writes_value','passes_value','displayed_in'})
    return []


def consumers(graph,repo,role):
    return [s for s in graph.symbols if s.get('value_flow_version')==1 and s.get('value_role')==role and s['id'].startswith('repo:'+repo+':')]


def test_ac01_actual_backend_field_has_exact_ui_and_test_paths(captured):
    root,origin=captured;_,coverage,_,graph,_=snapshot(root)
    start=qualified('backend',origin['id']);evidence={p['id']:p for p in graph.evidence}
    for repo,role,roles in [('frontend','JSX_CONSUMER',['DESTRUCTURE','OBJECT_MAPPING','STATE_WRITE','FIELD_READ','JSX_CONSUMER']),
                            ('tests','ARGUMENT',['DESTRUCTURE','ARGUMENT'])]:
        targets=consumers(graph,repo,role);assert len(targets)==1
        route=path_between(graph,start,targets[0]['id']);assert route
        nodes={n.id:n for n in graph.nodes}
        assert [nodes[e.target].metadata['value_role'] for e in route if nodes[e.target].kind=='value_occurrence']==roles
        assert route[0].kind=='serialized_as' and nodes[route[0].target].kind=='contract_field'
        projection=nodes[route[1].target]
        request=next(s for s in graph.symbols if s.get('value_role')=='HTTP_RESPONSE' and s['id'].startswith('repo:'+repo+':'))
        # The exact request/json ancestry joins the exact contract projection.
        ancestry=path_between(graph,request['id'],projection.id)
        assert [nodes[e.target].metadata['value_role'] for e in ancestry]==['ASSIGNMENT','JSON_RESULT','ASSIGNMENT','DESTRUCTURE']
        for edge in route+ancestry:
            assert edge.evidence_ids and all(p in evidence for p in edge.evidence_ids)
            assert edge.evidence_kind in {'SYMBOL_RESOLVED','FRAMEWORK_DERIVED'}
        assert all(evidence[p].get('availability')=='UNKNOWN' for e in route for p in e.evidence_ids)
    from kgmaker.dataflow import impact_paths
    report = impact_paths(graph, start)
    assert report['frontend_value_bindings']
    assert all(t['id'] in {p['entity_ids'][-1] for p in report['paths']} for t in consumers(graph, 'tests', 'ARGUMENT'))
    assert not any('VALUE_FLOW_' in d for d in coverage['limitations']),coverage['limitations']


@pytest.mark.parametrize('change,diagnostic',[('contract','GENERATION_OR_RELEASE'),('release','GENERATION_OR_RELEASE'),('generated','COMPILER_EVIDENCE_UNAVAILABLE'),('backend','BACKEND_FIELD'),('field','CONTRACT_FIELD'),('missing','Missing checkout'),('ambiguous','AMBIGUOUS_SERVICE')])
def test_ac03_stale_and_ambiguous_inputs_do_not_join(captured,change,diagnostic):
    root,origin=captured;manifest=root/'workspace.json'
    path={'field':root/'backend/contracts/exposure.json','contract':root/'backend/contracts/exposure.json','release':root/'frontend/generation.json',
          'generated':root/'frontend/generated/client.ts','backend':root/'backend/src/main/java/demo/Exposure.java'}.get(change,manifest)
    original=path.read_bytes()
    try:
        if change in {'contract','generated','backend'}:path.write_bytes(original+b'\n')
        else:
            data=json.loads(original)
            if change=='field':
                props=data['paths']['/exposure']['get']['responses']['200']['content']['application/json']['schema']['properties']
                props['renamed']=props.pop('decline')
            elif change=='release':data['release']='v2'
            elif change=='missing':data['repositories'][1]['path']='absent'
            else:
                other=copy.deepcopy(data['services'][0]);other['id']='other';data['services'].append(other)
            write_json(path,data)
        _,coverage,_,graph,_=snapshot(root)
        start=qualified('backend',origin['id'])
        assert not any(path_between(graph,start,t['id']) for t in consumers(graph,'frontend','JSX_CONSUMER'))
        assert any(diagnostic in d for d in coverage['limitations']),coverage['limitations']
    finally:path.write_bytes(original)


@pytest.mark.parametrize('change', ['unrelated-json','unrelated-promise','shadowed-state','fake-use-state','multiple-setters','no-await','shadowed-fetch','unrelated-assertion','dynamic-eval'])
def test_ac03_compiler_symbols_reject_name_only_flow(tmp_path,change):
    require_workers()
    source=PAGE
    if change=='unrelated-json':source=source.replace('const data: Exposure = await response.json();', "const unrelated = new Response('{\"decline\":7}'); const data: Exposure = await unrelated.json();")
    elif change=='unrelated-promise':source=source.replace('assign({decline: amount});', "Promise.resolve({decline:7}).then(({decline})=>assign({decline}));")
    elif change=='shadowed-state':source=source.replace('return <span', 'const holder = {decline: 7}; return <span').replace('{view?.decline}', '{holder.decline}')
    elif change=='fake-use-state':source=source.replace("import React, {useState} from 'react';", "import React from 'react'; function useState<T>(initial:T):[T,(value:T)=>void] {return [initial,()=>{}];}")
    elif change=='multiple-setters':source=source.replace('assign({decline: amount});','assign({decline: amount}); assign({decline:7});')
    elif change=='no-await':source=source.replace('await response.json()', 'response.json() as any')
    elif change=='shadowed-fetch':source=source.replace('async function load() {', "async function load() { const fetch = async (url:string)=>new Response('{\"decline\":7}');")
    elif change=='dynamic-eval':source=source.replace('const {decline: amount} = data;', "eval('data.decline = 7'); const {decline: amount} = data;")
    else:source=TEST.replace('check(observed);','{const observed = 7; check(observed);}')
    prepare_ts(tmp_path,source)
    result=inspect_frontend(tmp_path,home=HOME,ui_framework='react',publish=False)
    values=[s for s in result['graph']['symbols'] if s.get('value_flow_version')==1]
    assert not any(s.get('value_role') in {'JSX_CONSUMER','ARGUMENT'} for s in values)


def test_ac02_source_only_and_legacy_versions_never_gain_compiler_flow(captured):
    root,_=captured;files=[root/repo/'.kgmaker/graph.json' for repo in ['frontend','tests']]
    originals=[p.read_bytes() for p in files]
    try:
        for path in files:path.unlink()
        _,coverage,_,graph,_=snapshot(root)
        assert not any(s.get('value_flow_version') for s in graph.symbols)
        assert any('COMPILER_EVIDENCE_UNAVAILABLE' in d for d in coverage['limitations'])
        for version in (1,2,3):
            data={'schema_version':version,'root':'.','generated_at':'','nodes':[],'edges':[],'files':{}}
            assert KnowledgeGraph.from_dict(data).nodes==[]
    finally:
        for p,data in zip(files,originals):p.write_bytes(data)


@pytest.mark.parametrize('corruption', ['hash', 'range', 'context', 'version', 'cross-request', 'fact-range', 'fact-file', 'evidence-kind', 'adapter',
    'unmarked-cross-request', 'unmarked-fact', 'unknown-fact-version', 'mixed-endpoint',
    'unmarked-symbol', 'unknown-symbol-version', 'all-unmarked', 'role-stripped'])
def test_ac03_invalid_worker_value_does_not_replace_store(tmp_path, corruption):
    require_workers()
    prepare_ts(tmp_path, PAGE.replace('assign({decline: amount});', "assign({decline: amount}); const otherResponse = await fetch('/api/other'); const otherData: Exposure = await otherResponse.json(); const other = otherData.decline;"))
    from kgmaker import inspection
    from kgmaker.worker_protocol import WorkerError
    inspection.inspect_frontend(tmp_path, home=HOME, ui_framework='react', publish=True)
    before={str(p):p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    original=inspection.request_worker
    def corrupt(*args,**kwargs):
        result=original(*args,**kwargs)
        candidates=[s for s in result.get('symbols',[]) if s.get('value_flow_version')==1]
        if candidates and corruption in {'cross-request','fact-range','fact-file','evidence-kind','adapter',
                'unmarked-cross-request','unmarked-fact','unknown-fact-version','mixed-endpoint'}:
            symbols={s['id']:s for s in result['symbols']}
            fact=next(f for f in result['facts'] if f.get('value_flow_version')==1 and symbols[f['target']].get('value_role')=='JSON_RESULT' and symbols[f['target']]['request']['path']=='/api/other')
            if corruption in {'cross-request','unmarked-cross-request'}:
                fact['source']=next(s['id'] for s in candidates if s.get('value_role')=='ASSIGNMENT' and s['request']['path']=='/api/exposure')
                if corruption=='unmarked-cross-request':del fact['value_flow_version']
            elif corruption=='unmarked-fact':del fact['value_flow_version']
            elif corruption=='unknown-fact-version':fact['value_flow_version']=2
            elif corruption=='mixed-endpoint':
                fact['source']=next(s['id'] for s in result['symbols'] if 'value_flow_version' not in s and s['path']==fact['path'])
            elif corruption=='fact-range':
                fact['range']={**fact['range'],'start':fact['range']['start']+1,'start_column':fact['range']['start_column']+1}
            elif corruption=='evidence-kind':fact['evidence_kind']='RUNTIME_OBSERVED'
            elif corruption=='adapter':
                fact=next(f for f in result['facts'] if f.get('value_flow_version')==1 and f['kind']=='writes_value')
                fact['ui_adapter']={**fact['ui_adapter'],'react_version':'99.0.0'}
            else:
                other=next(s for s in result['symbols'] if s.get('path')=='generated/client.ts')
                fact.update(path=other['path'],sha256=other['sha256'],range=other['range'])
        elif candidates:
            item=candidates[0]
            if corruption=='hash':item['sha256']='0'*64
            elif corruption=='range':item['range']['end']=10**9
            elif corruption=='context':item['context_id']='another-context'
            elif corruption=='unmarked-symbol':del item['value_flow_version']
            elif corruption=='unknown-symbol-version':item['value_flow_version']=2
            elif corruption=='role-stripped':del item['value_role']
            elif corruption=='all-unmarked':
                for value in [*result['symbols'],*result['facts']]:value.pop('value_flow_version',None)
            else:item['value_flow_version']=True
        return result
    with patch.object(inspection,'request_worker',side_effect=corrupt):
        with pytest.raises(WorkerError,match='Invalid frontend value'):
            inspection.inspect_frontend(tmp_path,home=HOME,ui_framework='react',publish=True)
    assert before=={str(p):p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}


def test_ac01_two_state_properties_keep_separate_occurrences(tmp_path):
    require_workers()
    source=PAGE.replace('const {decline: amount} = data;', 'const {decline: amount, other} = data as Exposure & {other:number};')
    source=source.replace('assign({decline: amount});', 'assign({decline: amount, other} as Exposure);')
    prepare_ts(tmp_path,source)
    result=inspect_frontend(tmp_path,home=HOME,ui_framework='react',publish=False)
    graph=KnowledgeGraph.from_dict(result['graph'])
    writes=[s for s in graph.symbols if s.get('value_role')=='STATE_WRITE']
    assert {s['field'] for s in writes}=={'decline','other'}
    assert len({s['id'] for s in writes})==2
    ui=next(s for s in graph.symbols if s.get('value_role')=='JSX_CONSUMER')
    assert all(bool(path_between(graph,s['id'],ui['id']))==(s['field']=='decline') for s in writes)


def test_ac03_local_same_name_type_is_not_generated_contract(captured):
    root,origin=captured
    page=root/'frontend/src/page.tsx';store=root/'frontend/.kgmaker/graph.json'
    before_page,before_store=page.read_bytes(),store.read_bytes()
    try:
        page.write_text(PAGE.replace("import {Exposure} from '../generated/client';", 'interface Exposure { decline:number; }'))
        inspect_frontend(root/'frontend',home=HOME,repo_id='frontend',ui_framework='react',publish=True)
        _,coverage,_,graph,_=snapshot(root)
        assert not any(path_between(graph,qualified('backend',origin['id']),t['id']) for t in consumers(graph,'frontend','JSX_CONSUMER'))
        assert any('GENERATION_OR_RELEASE_UNKNOWN' in d for d in coverage['limitations'])
    finally:
        page.write_bytes(before_page);store.write_bytes(before_store)


def test_ac03_cached_context_revalidates_external_package_inputs(captured):
    root,origin=captured
    baseline=snapshot(root)[3]  # prime cache before changing an excluded dependency
    original_targets=consumers(baseline,'frontend','JSX_CONSUMER')
    assert len(original_targets)==1
    start=qualified('backend',origin['id']);target=original_targets[0]['id']
    original_route=path_between(baseline,start,target);assert original_route
    stored=root/'frontend/.kgmaker/graph.json';stored_bytes=stored.read_bytes()
    package=root/'frontend/node_modules/react/package.json';before=package.read_bytes()
    try:
        data=json.loads(before);data['version']='99.0.0';write_json(package,data)
        _,coverage,_,graph,_=snapshot(root)
        assert not any(path_between(graph,qualified('backend',origin['id']),t['id']) for t in consumers(graph,'frontend','JSX_CONSUMER'))
        assert any('COMPILER_EVIDENCE_UNAVAILABLE' in d for d in coverage['limitations'])
        assert any(c.get('freshness')=='STALE' and c.get('repo_id')=='frontend' for c in graph.contexts)
        assert not consumers(graph,'frontend','JSX_CONSUMER')
        # A repeated read while the dependency is still invalid cannot promote it.
        repeated=snapshot(root)[3]
        assert not consumers(repeated,'frontend','JSX_CONSUMER')
        assert any(c.get('freshness')=='STALE' and c.get('repo_id')=='frontend' for c in repeated.contexts)
    finally:package.write_bytes(before)
    # Exact original bytes recover the original captured proof without inspection.
    restored=snapshot(root)[3]
    assert path_between(restored,start,target)==original_route
    assert stored.read_bytes()==stored_bytes


ALIAS_HAZARDS = {
    'alias-write': 'const alias = data; alias.decline = 7;',
    'alias-escape': 'const alias = data; overwrite(alias);',
    'chain-write': 'const first = data; const second = first; second.decline = 7;',
    'chain-escape': 'const first = data; const second = first; overwrite((second as Exposure));',
    'chain-compound': 'const first = data; const second = first; second.decline += 7;',
    'chain-increment': 'const first = data; const second = first; second.decline++;',
    'cast-delete': 'const alias = data; delete (alias as Partial<Exposure>).decline;',
    'cast-scalar': 'const first = data as unknown as number; const second = first; (second as any).decline = 7;',
    'cast-scalar-escape': 'const first = data as unknown as number; const second = first; overwrite(second as unknown as Exposure);',
    'object-container': 'const holder = {data}; holder.data.decline = 7;',
    'array-container': 'const holder = [data]; holder[0].decline = 7;',
    'static-mutator': 'const alias = data; Object.assign(alias, {decline:7});',
    'receiver-mutator': 'const alias = data as Exposure & {overwrite():void}; alias.overwrite();',
    'readonly-escape': 'const alias: Readonly<Exposure> = data; overwrite(alias);',
    'readonly-callee': 'const alias = data; ((value:Readonly<Exposure>)=>overwrite(value))(alias);',
    'conditional-assignment': 'let alias:Exposure = {decline:0}; alias = true ? data : {decline:7}; alias.decline = 7;',
    'class-container': 'class Holder { payload = data; } const holder = new Holder(); holder.payload.decline = 7;',
    'tagged-receiver': 'const alias = data as Exposure & {overwrite(parts:TemplateStringsArray):void}; alias.overwrite``;',
    'conditional-alias': 'const alias = true ? data : {decline:7}; alias.decline = 7;',
    'arrow-return': 'const get = () => data; const alias = get(); alias.decline = 7;',
    'await-alias': 'const alias = await data; alias.decline = 7;',
    'reassigned-alias': 'let alias:Exposure; alias = data; alias.decline = 7;',
}


def hazard_source(source, addition, variable='observed'):
    return ('function overwrite(x: {decline:number}) { x.decline = 7; }\n' +
            source.replace(f'const {{decline: {variable}}} = data;', addition + f' const {{decline: {variable}}} = data;'))


@pytest.mark.parametrize('hazard', ALIAS_HAZARDS)
def test_ac03_actual_alias_mutation_and_escape_invalidate_origin(tmp_path, hazard):
    require_workers()
    prepare_ts(tmp_path,hazard_source(TEST,ALIAS_HAZARDS[hazard]))
    result=inspect_frontend(tmp_path,home=HOME,publish=True)
    assert not [d for d in result['diagnostics'] if d.get('category')=='Error']
    graph=KnowledgeGraph.from_dict(result['graph'])
    requests=[s for s in graph.symbols if s.get('value_role')=='HTTP_RESPONSE']
    assert len(requests)==1  # The explicit request remains evidenced.
    assert not [s for s in graph.symbols if s.get('value_role') in {'ARGUMENT','JSX_CONSUMER'}]
    assert (tmp_path/'.kgmaker/graph.json').is_file()


@pytest.mark.parametrize('variant', ['readonly-alias-chain','primitive-copy','primitive-property-copy','unrelated-object'])
def test_ac01_safe_aliases_and_independent_scalars_keep_exact_path(tmp_path, variant):
    require_workers()
    source=TEST
    if variant=='readonly-alias-chain':source=source.replace('const {decline: observed} = data;', 'const first = data; const second = first; const {decline: observed} = second;')
    elif variant=='primitive-copy':source=source.replace('check(observed);', 'let copy = observed; copy = 7; check(observed);')
    elif variant=='primitive-property-copy':source=source.replace('check(observed);', 'const alias = data; const scalar = alias.decline; let copy = scalar; copy = 7; check(observed);')
    else:source=source.replace('check(observed);', 'const independent = {decline:7}; const alias = independent; overwrite(alias); check(observed);')
    prepare_ts(tmp_path,'function overwrite(x:{decline:number}) {x.decline=8;}\n'+source)
    result=inspect_frontend(tmp_path,home=HOME,publish=False)
    assert not [d for d in result['diagnostics'] if d.get('category')=='Error']
    graph=KnowledgeGraph.from_dict(result['graph'])
    request=next(s for s in graph.symbols if s.get('value_role')=='HTTP_RESPONSE')
    consumer=next(s for s in graph.symbols if s.get('value_role')=='ARGUMENT')
    route=path_between(graph,request['id'],consumer['id'])
    assert route and all(e.evidence_ids for e in route)
    assert route[-1].kind=='passes_value'


@pytest.mark.parametrize('repo,hazard', [('tests','alias-write'),('frontend','chain-escape')])
def test_ac03_workspace_never_bridges_aliased_mutable_payload(tmp_path,repo,hazard):
    # Own explicit captures: the stale-dependency test intentionally leaves a
    # conservative STALE cache entry in the shared module fixture.
    root,origin=capture_workspace(tmp_path)
    filename='src/response.ts' if repo=='tests' else 'src/page.tsx'
    page=root/repo/filename;store=root/repo/'.kgmaker/graph.json'
    original_page,original_store=page.read_bytes(),store.read_bytes()
    try:
        page.write_text(hazard_source(TEST if repo=='tests' else PAGE,ALIAS_HAZARDS[hazard], 'observed' if repo=='tests' else 'amount'))
        result=inspect_frontend(root/repo,home=HOME,repo_id=repo,ui_framework='react',publish=True)
        assert not [d for d in result['diagnostics'] if d.get('category')=='Error']
        _,coverage,_,graph,_=snapshot(root)
        assert not consumers(graph,repo,'ARGUMENT' if repo=='tests' else 'JSX_CONSUMER')
        assert any('VALUE_FLOW_CONSUMER_UNPROVEN: '+repo+'/' in d for d in coverage['limitations'])
        # Independent other repository still has its fully evidenced BE path.
        other='frontend' if repo=='tests' else 'tests'
        target=consumers(graph,other,'JSX_CONSUMER' if other=='frontend' else 'ARGUMENT')[0]
        assert path_between(graph,qualified('backend',origin['id']),target['id'])
    finally:page.write_bytes(original_page);store.write_bytes(original_store)


def test_ac02_genuine_legacy_worker_facts_still_publish(tmp_path):
    require_workers();prepare_ts(tmp_path,TEST)
    from kgmaker import inspection
    original=inspection.request_worker
    def legacy(*args,**kwargs):
        result=original(*args,**kwargs)
        if 'symbols' in result:
            result['symbols']=[s for s in result['symbols'] if 'value_flow_version' not in s]
            result['facts']=[f for f in result['facts'] if 'value_flow_version' not in f]
            assert result['symbols'] and result['facts']
        return result
    with patch.object(inspection,'request_worker',side_effect=legacy):
        result=inspection.inspect_frontend(tmp_path,home=HOME,publish=True)
    assert result['graph']['symbols'] and (tmp_path/'.kgmaker/graph.json').is_file()
    assert not any(s.get('value_flow_version') for s in result['graph']['symbols'])

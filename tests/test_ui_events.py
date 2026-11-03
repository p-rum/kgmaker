"""Actual pinned React TSX adapter evidence; no UI or application execution."""
import json
import os
from pathlib import Path
import shutil

import pytest

from kgmaker.inspection import inspect_frontend
from kgmaker.model import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'

@pytest.fixture
def ui_project(tmp_path):
    dependencies = ROOT / 'fixtures/build-inspection/frontend/node_modules'
    if not shutil.which('node') or not (HOME / 'typescript/node_modules/typescript/lib/typescript.js').is_file() or not (dependencies / '@types/react/index.d.ts').is_file():
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            pytest.fail('Prepared TypeScript and pinned React packages required')
        pytest.skip('Prepared TypeScript/React fixture missing')
    shutil.copytree(dependencies, tmp_path / 'node_modules')
    (tmp_path / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'jsx': 'react', 'strict': True, 'esModuleInterop': True, 'target': 'ES2020', 'moduleResolution': 'node', 'skipLibCheck': True}, 'include': ['src/**/*.tsx']}))
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/App.tsx').write_text('''import React from 'react';
export function direct() {}
export function forwarded() {}
export function swallowed() {}
export function unrelated() {}
export function Wrapper(props: React.ButtonHTMLAttributes<HTMLButtonElement>) { return <button onClick={props.onClick}/>; }
export function Swallow(props: React.ButtonHTMLAttributes<HTMLButtonElement>) { return <button/>; }
export function Other(props: {onClick: () => void}) { return <span/>; }
export function App() { return <><button onClick={direct}/><Wrapper onClick={forwarded}/><Swallow onClick={swallowed}/><Other onClick={unrelated}/></>; }
''')
    return tmp_path


def inspect(root):
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = inspect_frontend(root, home=HOME, repo_id='ui-fixture', ui_framework='react', publish=False)
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return result, KnowledgeGraph.from_dict(result['graph'])


def handler_names(graph):
    symbols = {s['id']: s for s in graph.symbols}
    return {symbols[e.target]['name'] for e in graph.edges if e.kind == 'handles_event'}


def test_intrinsic_and_verified_wrapper_have_library_bound_event_evidence(ui_project):
    result, graph = inspect(ui_project)
    assert handler_names(graph) == {'direct', 'forwarded'}
    evidence = [p for p in graph.evidence if p['relation'] == 'handles_event']
    assert len(evidence) == 2
    for proof in evidence:
        assert proof['kind'] == 'FRAMEWORK_DERIVED'
        adapter = proof['ui_adapter']
        assert adapter['rule'] == 'react-jsx-events-4'
        assert adapter['react_version'] == '18.3.1' and adapter['types_version'] == '18.3.18'
        assert adapter['declaration_sha256'] == 'b89c2ddec6bd955e8721d41e24ca667de06882338d88b183c2cdc1f41f4c5a34'
        assert proof['execution'] == 'NOT_OBSERVED'
    assert result['context']['framework_rule_versions']['react'] == 'react-jsx-events-4'
    assert result['context']['project']['ui_adapters']


@pytest.mark.parametrize('change', ['runtime-version', 'types-version', 'declaration'])
def test_changed_or_unsupported_library_never_reuses_version_rule(ui_project, change):
    _, original = inspect(ui_project)
    if change == 'declaration':
        file = ui_project / 'node_modules/@types/react/index.d.ts'
        file.write_text(file.read_text() + '\n// changed declaration\n')
    else:
        file = ui_project / ('node_modules/react/package.json' if change == 'runtime-version' else 'node_modules/@types/react/package.json')
        data = json.loads(file.read_text()); data['version'] = '99.0.0'; file.write_text(json.dumps(data))
    _, changed = inspect(ui_project)
    assert not handler_names(changed)
    assert changed.contexts[-1]['id'] != original.contexts[-1]['id']
    assert any(d['code'] == 'UNSUPPORTED_UI_ADAPTER' for d in changed.diagnostics)


@pytest.mark.parametrize('case', ['mutable', 'conditional', 'spread', 'fake-module', 'missing-runtime'])
def test_unknown_bindings_never_create_framework_event(ui_project, case):
    file = ui_project / 'src/App.tsx'
    if case == 'mutable':
        file.write_text("import React from 'react'; function first(){} function second(){} let handler=first; handler=second; export function App(){return <button onClick={handler}/>;}\n")
    elif case == 'conditional':
        file.write_text("import React from 'react'; function first(){} function second(){} declare const flag:boolean; export function App(){return <button onClick={flag?first:second}/>;}\n")
    elif case == 'spread':
        file.write_text("import React from 'react'; function first(){} const extra={onClick:()=>{}}; export function App(){return <button onClick={first} {...extra}/>;}\n")
    elif case == 'fake-module':
        (ui_project / 'src/fake.tsx').write_text("export const value=1;\n")
        config = json.loads((ui_project / 'tsconfig.json').read_text());config['compilerOptions'].update(baseUrl='.', paths={'react':['src/fake.tsx']});(ui_project / 'tsconfig.json').write_text(json.dumps(config))
    else:
        shutil.rmtree(ui_project / 'node_modules/react')
    _, graph = inspect(ui_project)
    assert not handler_names(graph)
    assert any(d['code'] in {'UNSUPPORTED_UI_ADAPTER','MUTABLE_UI_HANDLER','MUTABLE_CALLBACK','UNRESOLVED_UI_HANDLER','UI_ATTRIBUTE_SPREAD_UNSUPPORTED','UI_WRAPPER_UNPROVEN','UI_RENDERER_UNPROVEN'} for d in graph.diagnostics)


def test_published_context_detects_package_change_offline(ui_project):
    from unittest.mock import patch
    from kgmaker.graph_provider import retain_compiler_layer
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    _, graph = inspect(ui_project)
    save_graph(graph, ui_project)
    store = ui_project / '.kgmaker/graph.json'; previous = store.read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('offline UI context must not launch process')):
        retained = retain_compiler_layer(ui_project, scan_repository(ui_project))
    assert handler_names(retained) == {'direct','forwarded'}
    package = ui_project / 'node_modules/react/package.json'
    package.write_text(package.read_text().replace('18.3.1','18.3.0'))
    with patch('subprocess.Popen', side_effect=AssertionError('offline UI context must not launch process')):
        stale = retain_compiler_layer(ui_project, scan_repository(ui_project))
    assert any(c.get('freshness') == 'STALE' for c in stale.contexts if c.get('ui_framework'))
    assert store.read_bytes() == previous


@pytest.mark.parametrize('tag', ['Fancy', 'fancy'])
def test_local_intrinsic_augmentation_cannot_bypass_wrapper_proof(ui_project, tag):
    (ui_project / 'src/App.tsx').write_text('''import React from 'react';
declare global { namespace JSX { interface IntrinsicElements { TAG: React.ButtonHTMLAttributes<HTMLButtonElement> } } }
function Fancy(props: React.ButtonHTMLAttributes<HTMLButtonElement>) { return <button/>; }
function swallowed() {}
export function App() { return <TAG onClick={swallowed}/>; }
'''.replace('TAG', tag))
    _, graph = inspect(ui_project)
    assert not handler_names(graph)


@pytest.mark.parametrize('case', ['factory', 'lexical-shadow', 'typed-shadow', 'pragma', 'import-source', 'namespace', 'fragment-factory', 'empty-factory', 'empty-import-source', 'preserve', 'react-native', 'legacy-react-namespace', 'canonical-fragment', 'explicit-react-import-source', 'runtime-pragma', 'fragment-pragma', 'import-source-pragma'])
def test_custom_renderer_never_gets_react_event_claim(ui_project, case):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    prefix = "import React from 'react';\n"
    if case == 'factory':
        config['compilerOptions']['jsxFactory'] = 'h'
        prefix += 'function h(tag:any,props:any,...children:any[]):any{return null;}\n'
    elif case == 'namespace':
        config['compilerOptions']['reactNamespace']='Fake'
        prefix += 'const Fake={createElement(tag:any,props:any,...children:any[]):any{return null;}};\n'
    elif case == 'fragment-factory':
        config['compilerOptions']['jsxFragmentFactory']='h'
        prefix += 'function h(...children:any[]):any{return null;}\n'
    elif case == 'empty-factory':
        config['compilerOptions']['jsxFactory']=''
    elif case == 'empty-import-source':
        config['compilerOptions']['jsx']='react-jsx'
        config['compilerOptions']['jsxImportSource']=''
    elif case in {'preserve','react-native'}:
        config['compilerOptions']['jsx']=case
    elif case == 'legacy-react-namespace':
        config['compilerOptions']['reactNamespace']='React'
    elif case == 'canonical-fragment':
        config['compilerOptions']['jsxFragmentFactory']='React.Fragment'
    elif case == 'explicit-react-import-source':
        config['compilerOptions']['jsx']='react-jsx'
        config['compilerOptions']['jsxImportSource']='react'
    elif case in {'runtime-pragma','fragment-pragma','import-source-pragma'}:
        pragma={'runtime-pragma':'@jsxRuntime automatic','fragment-pragma':'@jsxFrag React.Fragment','import-source-pragma':'@jsxImportSource react'}[case]
        prefix='/** '+pragma+' */\n'+prefix
    elif case == 'lexical-shadow':
        prefix = "import R from 'react'; const React={createElement(tag:any,props:any,...children:any[]):any{return null;}};\n"
    elif case == 'typed-shadow':
        prefix = "import R from 'react'; const React={createElement(tag:any,props:any,...children:any[]):any{return null;}} as unknown as typeof R;\n"
    elif case == 'pragma':
        prefix = '/** @jsx h */\n' + prefix + 'function h(tag:any,props:any,...children:any[]):any{return null;}\n'
    else:
        config['compilerOptions']['jsx'] = 'react-jsx'
        config['compilerOptions']['jsxImportSource'] = 'other-renderer'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/App.tsx').write_text(prefix+'export function swallowed(){} export function App(){return <button onClick={swallowed}/>;}\n')
    _, graph = inspect(ui_project)
    assert not handler_names(graph)


@pytest.mark.parametrize('mode', ['alias', 'classic-explicit', 'function-alias', 'automatic', 'automatic-dev'])
def test_compiler_bound_official_factory_modes_remain_supported(ui_project, mode):
    config=json.loads((ui_project / 'tsconfig.json').read_text())
    if mode=='alias':
        config['compilerOptions']['jsxFactory']='R.createElement'
        text="import R from 'react';"
    elif mode in {'classic-explicit','function-alias'}:
        config['compilerOptions']['jsxFactory']='React.createElement' if mode=='classic-explicit' else 'h'
        text="import React from 'react';" if mode=='classic-explicit' else "import {createElement as h} from 'react';"
    else:
        config['compilerOptions']['jsx']='react-jsxdev' if mode=='automatic-dev' else 'react-jsx'
        text="import React from 'react';"
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/App.tsx').write_text(text+' export function handler(){} export function App(){return <button onClick={handler}/>;}')
    _, graph=inspect(ui_project)
    assert handler_names(graph)=={'handler'}



def test_missing_versioned_worker_contract_preserves_last_valid_store(ui_project, monkeypatch):
    from kgmaker import inspection
    from kgmaker.worker_protocol import WorkerError
    store=ui_project / '.kgmaker/graph.json';store.parent.mkdir();store.write_bytes(b'last valid index')
    original=inspection.request_worker
    def legacy_peer(argv, request, **kwargs):
        response=original(argv,request,**kwargs)
        if request.get('operation')=='project':
            response['project'].pop('ui_adapters',None)
        return response
    monkeypatch.setattr(inspection,'request_worker',legacy_peer)
    before={str(p.relative_to(ui_project)):p.read_bytes() for p in ui_project.rglob('*') if p.is_file()}
    with pytest.raises(WorkerError,match='lacks versioned UI adapter'):
        inspect_frontend(ui_project,home=HOME,ui_framework='react')
    assert before=={str(p.relative_to(ui_project)):p.read_bytes() for p in ui_project.rglob('*') if p.is_file()}


def test_incomplete_marked_distribution_fails_before_process(tmp_path, monkeypatch):
    from kgmaker.inspection import command
    from kgmaker.worker_protocol import WorkerError
    from unittest.mock import patch
    # This is a pure pre-process metadata guard, not a toolchain PASS.
    monkeypatch.setattr('kgmaker.inspection.shutil.which', lambda name: '/preflight-only-node')
    worker=tmp_path / 'typescript';(worker / 'node_modules/typescript/lib').mkdir(parents=True)
    (worker / 'worker.cjs').write_text('')
    (worker / 'node_modules/typescript/lib/typescript.js').write_text('')
    (worker / 'package.json').write_text(json.dumps({'kgmaker_ui_adapter':1}))
    with patch('subprocess.Popen',side_effect=AssertionError('incomplete worker must not launch')):
        with pytest.raises(WorkerError,match='UI adapter helper unavailable'):
            command('typescript',tmp_path)


@pytest.mark.parametrize('tag,interface,element,event', [
    ('input','InputHTMLAttributes','HTMLInputElement','onChange'),
    ('select','SelectHTMLAttributes','HTMLSelectElement','onChange'),
    ('textarea','TextareaHTMLAttributes','HTMLTextAreaElement','onChange'),
    ('form','FormHTMLAttributes','HTMLFormElement','onSubmit'),
])
def test_standard_form_controls_and_verified_wrappers_keep_official_events(ui_project, tag, interface, element, event):
    (ui_project / 'src/App.tsx').write_text(f'''import React from 'react';
export function direct() {{}}
export function forwarded() {{}}
function Wrapper(props:React.{interface}<{element}>) {{return <{tag} {event}={{props.{event}}}/>;}}
export function App() {{return <><{tag} {event}={{direct}}/><Wrapper {event}={{forwarded}}/></>;}}
''')
    _,graph=inspect(ui_project)
    assert handler_names(graph)=={'direct','forwarded'}


def test_checkout_interface_with_official_event_type_name_is_not_official_property(ui_project):
    (ui_project / 'src/App.tsx').write_text('''import React from 'react';
interface InputHTMLAttributes {onChange:()=>void}
function Wrapper(props:InputHTMLAttributes){return <input onChange={props.onChange}/>;}
function unrelated(){}
export function App(){return <Wrapper onChange={unrelated}/>;}
''')
    _,graph=inspect(ui_project)
    assert not handler_names(graph)

@pytest.mark.parametrize('mutation', [
    '(Wrapper as any)=Swallow;',
    '({Wrapper}={Wrapper:Swallow});',
    'for ({Wrapper} of [{Wrapper:Swallow}]) {}',
    '[Wrapper]=[Swallow];',
    '({value:Wrapper}={value:Swallow});',
    '({Wrapper=Swallow}={});',
    'for (Wrapper in {}) {}',
    '(Wrapper as any)+=Swallow;',
    '++(Wrapper as any);',
    '(Wrapper as any)--;',
    'var Wrapper=Swallow;',
    '(eval satisfies Function)("Wrapper=Swallow");',
    'eval("Wrapper=Swallow");',
])
def test_mutable_wrapper_never_borrows_original_forwarder(ui_project, mutation):
    source = ui_project / 'src/App.tsx'
    source.write_text('''import React from 'react';
function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}
function Swallow(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button/>;}
function swallowed(){}
''' + mutation + '\nexport function App(){return <Wrapper onClick={swallowed}/>;}')
    _, graph = inspect(ui_project)
    assert handler_names(graph) == set()


@pytest.mark.parametrize('binding', [
    'function original(){} function other(){} original=other;',
    'function original(){} function other(){} ({original}={original:other});',
    'class Handlers {static original(){} static other(){}} Handlers.original=Handlers.other; const original=Handlers.original;',
    'class Handlers {static original(){}} const original=Handlers.original;',
    'function original(){} eval("original=()=>{}");',
])
def test_mutable_handler_does_not_claim_original_function(ui_project, binding):
    (ui_project / 'src/App.tsx').write_text("import React from 'react';\n" + binding + '\nexport function App(){return <button onClick={original}/>;}')
    _, graph = inspect(ui_project)
    assert handler_names(graph) == set()


def test_definite_local_eval_named_callable_does_not_block_ui(ui_project):
    (ui_project / 'src/App.tsx').write_text("import React from 'react';\nconst eval=()=>0; eval(); function original(){} export function App(){return <button onClick={original}/>;}")
    _, graph = inspect(ui_project)
    assert handler_names(graph) == {'original'}


def test_direct_mutable_method_handler_is_not_a_closed_binding(ui_project):
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; class Handlers {static original(){} static other(){}} Handlers.original=Handlers.other; export function App(){return <button onClick={Handlers.original}/>;}")
    _, graph = inspect(ui_project)
    assert handler_names(graph) == set()


def test_imported_wrapper_uses_write_catalog_from_declaration_source(ui_project):
    (ui_project / 'src/Wrapper.tsx').write_text("import React from 'react'; export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;} function Swallow(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button/>;} Wrapper=Swallow;")
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; import {Wrapper} from './Wrapper'; function swallowed(){} export function App(){return <Wrapper onClick={swallowed}/>;}")
    _, graph = inspect(ui_project)
    assert handler_names(graph) == set()


def test_immutable_arrow_and_const_alias_handlers_remain_supported(ui_project):
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; const original=()=>{}; const alias=original; export function App(){return <button onClick={alias}/>;}")
    _, graph = inspect(ui_project)
    assert len([edge for edge in graph.edges if edge.kind == 'handles_event']) == 1


@pytest.mark.parametrize('old_rule', ['react-jsx-events-1', 'react-jsx-events-2', 'react-jsx-events-3'])
def test_previous_rule_generation_is_stale_offline_without_store_mutation(ui_project, old_rule):
    from unittest.mock import patch
    from kgmaker.graph_provider import retain_compiler_layer
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    _, graph = inspect(ui_project)
    for context in graph.contexts:
        if context.get('ui_framework') == 'react':
            context['framework_rule_versions']['react'] = old_rule
    save_graph(graph, ui_project)
    store = ui_project / '.kgmaker/graph.json'
    previous = store.read_bytes()
    with patch('subprocess.Popen', side_effect=AssertionError('freshness must stay offline')):
        retained = retain_compiler_layer(ui_project, scan_repository(ui_project))
    assert any(c.get('freshness') == 'STALE' for c in retained.contexts if c.get('ui_framework') == 'react')
    assert store.read_bytes() == previous


def test_explicit_factory_write_cannot_borrow_official_renderer(ui_project):
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; function localFactory(...args:any[]):any{return null;} (React.createElement as any)=localFactory; function swallowed(){} export function App(){return <button onClick={swallowed}/>;}")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()
    assert any(d.get('code') == 'UI_RENDERER_UNPROVEN' for d in graph.diagnostics)


@pytest.mark.parametrize('shape', ['any', 'as', 'element'])
def test_commonjs_imported_handler_and_wrapper_are_not_closed_bindings(ui_project, shape):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['module'] = 'commonjs'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/handlers.tsx').write_text("import React from 'react'; export function original(){} export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}")
    aliases = {
        'any': 'const alias:any=dep; alias.original=()=>{}; alias.Wrapper=()=>null;',
        'as': 'const alias=dep as any; alias.original=()=>{}; alias.Wrapper=()=>null;',
        'element': "const alias:any=dep; alias['original']=()=>{}; alias['Wrapper']=()=>null;",
    }
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; import {original,Wrapper} from './handlers'; import * as dep from './handlers'; " + aliases[shape] + ' function swallowed(){} export function App(){return <><button onClick={original}/><Wrapper onClick={swallowed}/></>;}')
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()


@pytest.mark.parametrize('escape', [
    'const alias:any=React; alias.createElement=(...args:any[])=>null;',
    'const alias=React as any; alias.createElement=(...args:any[])=>null;',
    "const alias:any=React; alias['createElement']=(...args:any[])=>null;",
    'const alias:any={React}; alias.React.createElement=(...args:any[])=>null;',
    'const alias:any=[React]; alias[0].createElement=(...args:any[])=>null;',
    'let alias:any; alias=React; alias.createElement=(...args:any[])=>null;',
])
def test_opaque_renderer_namespace_escape_is_unknown(ui_project, escape):
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; " + escape + ' function swallowed(){} export function App(){return <button onClick={swallowed}/>;}')
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()


def test_explicit_esm_imports_keep_immutable_handler_and_wrapper_proof(ui_project):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['module'] = 'esnext'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/handlers.tsx').write_text("import React from 'react'; export function original(){} export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}")
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; import {original,Wrapper} from './handlers'; function forwarded(){} export function App(){return <><button onClick={original}/><Wrapper onClick={forwarded}/></>;} ")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == {'original', 'forwarded'}


def test_esm_reexport_chain_is_not_a_direct_import_binding(ui_project):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['module'] = 'esnext'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/handlers.tsx').write_text("import React from 'react'; export function original(){} export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}")
    (ui_project / 'src/bridge.tsx').write_text("export {original,Wrapper} from './handlers';")
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; import {original,Wrapper} from './bridge'; function forwarded(){} export function App(){return <><button onClick={original}/><Wrapper onClick={forwarded}/></>;} ")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()


@pytest.mark.parametrize('owner_module,expected', [('commonjs', set()), ('esnext', {'original', 'forwarded'})])
def test_import_binding_uses_declaration_owner_project_module(ui_project, owner_module, expected):
    shutil.rmtree(ui_project / 'src')
    for name, module in [('lib', owner_module), ('app', 'esnext')]:
        directory = ui_project / name
        (directory / 'src').mkdir(parents=True)
        config = {'compilerOptions': {'jsx': 'react', 'strict': True, 'esModuleInterop': True,
                  'target': 'ES2020', 'moduleResolution': 'node', 'skipLibCheck': True,
                  'composite': True, 'declaration': True, 'module': module, 'rootDir': 'src', 'outDir': 'dist'},
                  'include': ['src/**/*.tsx']}
        if name == 'app':
            config['references'] = [{'path': '../lib'}]
        (directory / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'tsconfig.json').write_text(json.dumps({'files': [], 'references': [{'path': './app'}]}))
    (ui_project / 'lib/src/handlers.tsx').write_text("import React from 'react'; export function original(){} export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}")
    (ui_project / 'app/src/App.tsx').write_text("import React from 'react'; import {original,Wrapper} from '../../lib/src/handlers'; function forwarded(){} export function App(){return <><button onClick={original}/><Wrapper onClick={forwarded}/></>;} ")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == expected
    assert all(not (ui_project / project / 'dist').exists() for project in ('lib', 'app'))
    assert not list(ui_project.rglob('*.tsbuildinfo'))


def test_renderer_namespace_escape_also_invalidates_official_factory_alias(ui_project):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['jsxFactory'] = 'h'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/App.tsx').write_text("import React,{createElement as h} from 'react'; const alias:any=React; alias['createElement']=(...args:any[])=>null; function swallowed(){} export function App(){return <button onClick={swallowed}/>;}")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()


def test_automatic_runtime_namespace_escape_is_unknown(ui_project):
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['jsx'] = 'react-jsx'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    (ui_project / 'src/App.tsx').write_text("import * as runtime from 'react/jsx-runtime'; const alias:any=runtime; alias.jsx=(...args:any[])=>null; alias.jsxs=(...args:any[])=>null; function swallowed(){} export function App(){return <button onClick={swallowed}/>;}")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert handler_names(graph) == set()


def test_ui_binding_cannot_compose_excluded_test_handler_or_wrapper(ui_project):
    (ui_project / '.kgmaker').mkdir()
    (ui_project / '.kgmaker/classification.json').write_text(json.dumps({'schema_version': 1, 'overrides': [{'path': 'src/tests', 'scope': 'test', 'reason': 'Explicit excluded harness'}]}))
    config = json.loads((ui_project / 'tsconfig.json').read_text())
    config['compilerOptions']['module'] = 'esnext'
    (ui_project / 'tsconfig.json').write_text(json.dumps(config))
    directory = ui_project / 'src/tests'
    directory.mkdir()
    (directory / 'handlers.tsx').write_text("import React from 'react'; export function original(){} export function Wrapper(props:React.ButtonHTMLAttributes<HTMLButtonElement>){return <button onClick={props.onClick}/>;}")
    (ui_project / 'src/App.tsx').write_text("import React from 'react'; import {original,Wrapper} from './tests/handlers'; function forwarded(){} export function App(){return <><button onClick={original}/><Wrapper onClick={forwarded}/></>;} ")
    _, graph = inspect(ui_project)
    assert not [d for d in graph.diagnostics if str(d.get('code', '')).startswith('TS')]
    assert any(node.name == 'original' and node.path == 'src/tests/handlers.tsx' and node.scope == 'test' for node in graph.nodes)
    assert handler_names(graph) == set()

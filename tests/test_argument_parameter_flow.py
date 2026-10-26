"""Actual compiler binding proofs, independent from runtime execution."""
import os
import sys
from pathlib import Path

import pytest

from kgmaker.inspection import command
from kgmaker.worker_protocol import WorkerError, request_worker

HOME = Path(os.environ.get('KGMAKER_WORKERS_HOME', Path(__file__).resolve().parents[1] / 'workers'))


def analyze(root, sources, *, language='jvm', backend='k1'):
    for name, text in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    context = {'id': 'argument-proof-' + language + '-' + backend, 'repo_id': 'fixture',
               'module': 'argument-flow', 'source_set': 'main', 'scope': 'production'}
    payload = {'operation': 'analyze', 'root': str(root), 'context': context,
               'sources': list(sources), 'classpath': [], 'kotlin_backend': backend,
               'kotlin_version': '2.1.10'}
    if language == 'typescript':
        (root / 'tsconfig.json').write_text('{"compilerOptions":{"strict":true,"target":"ES2020"},"include":["src/**/*.ts"]}')
    if language == 'jvm':
        payload['classpath'] = [str(HOME / 'jvm/target/lib/kotlin-stdlib.jar')]
    try:
        result = request_worker(command(language, HOME, kotlin_backend=backend), payload, cwd=root)
    except WorkerError as error:
        if error.status != 'TOOLCHAIN_UNAVAILABLE':
            raise
        required = os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (
            language == 'jvm' and backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1')
        if required:
            pytest.fail(str(error))
        pytest.skip(str(error))
    assert not (root / '.kgmaker').exists()
    return result


def proofs(response, callee):
    sites = {s['id']: s for s in response['call_sites']}
    symbols = {s['id']: s for s in response['symbols']}
    facts = [f for f in response['facts'] if f['kind'] == 'argument_to_parameter'
             and callee in symbols[f['target']].get('method', '')]
    assert facts, 'compiler-proven argument binding facts missing: ' + callee
    for fact in facts:
        site = sites[fact['call_site']]
        assert site.get('argument_mapping_status') == 'PROVEN'
        parameter = symbols[fact['target']]
        argument = symbols[fact['source']]
        assert parameter['kind'] == 'parameter'
        assert parameter['method'] == site['declared_target']
        assert argument['kind'] == 'value' and argument['call_site'] == site['id']
        assert fact['context_id'] == site['context_id']
        assert fact['binding_kind'] == 'DECLARED_PARAMETER'
        assert isinstance(fact['argument_index'], int) and isinstance(fact['parameter_index'], int)
        assert fact['evidence_kind'] == 'SYMBOL_RESOLVED'
        assert fact['transformation'] in {'DIRECT', 'VARARG_ELEMENT', 'VARARG_SPREAD', 'VARARG_ARRAY'}
    return facts


def test_actual_javac_overload_and_vararg_binding(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''public class Calls {
 static int over(int n){return n;} static int over(String n){return n.length();}
 static int many(String label,int... values){return values.length;}
 static void entry(int n,int[] values){over(n);over("x");many("v",n,2);many("v",values);}
}'''})
    overloads = proofs(response, '.over(')
    assert len({f['target'] for f in overloads}) == 2
    varargs = proofs(response, '.many(')
    assert any(f['parameter_index'] == 1 and f['transformation'] == 'VARARG_ELEMENT' for f in varargs)
    assert any(f['parameter_index'] == 1 and f['transformation'] == 'VARARG_ARRAY' for f in varargs)


def test_actual_k1_named_default_vararg_mapping(tmp_path):
    response = analyze(tmp_path, {'src/main/kotlin/Calls.kt': '''package fixture
fun pair(first:Int,second:String="default")=first
fun many(vararg values:Int)=values.size
fun entry(n:Int,values:IntArray){pair(second="named",first=n);pair(first=n);many(n,2);many(*values)}
'''})
    pair = proofs(response, '.pair(')
    assert any(f['argument_index'] == 0 and f['parameter_index'] == 1 for f in pair)
    assert any(f['argument_index'] == 1 and f['parameter_index'] == 0 for f in pair)
    omissions = [o for s in response['call_sites'] for o in s.get('argument_omissions', [])]
    assert any(o['parameter_index'] == 1 and o['reason'] == 'DEFAULT_VALUE_NOT_EVALUATED' for o in omissions)
    varargs = proofs(response, '.many(')
    assert {'VARARG_ELEMENT', 'VARARG_SPREAD'} <= {f['transformation'] for f in varargs}


def test_actual_k2_argument_binding_is_an_explicit_unknown(tmp_path):
    response = analyze(tmp_path, {'src/main/kotlin/Calls.kt': 'fun take(n:Int)=n\nfun entry(){take(1)}'}, backend='k2')
    assert any(d['code'] == 'K2_ARGUMENT_BINDINGS_UNAVAILABLE' for d in response['diagnostics'])
    assert not any(f['kind'] == 'argument_to_parameter' for f in response['facts'])
    assert response['status'] == 'PARTIAL'
    assert all(s.get('argument_mapping_status') == 'UNKNOWN' for s in response['call_sites'])


def test_actual_typescript_signature_rest_and_default_binding(tmp_path):
    response = analyze(tmp_path, {'src/calls.ts': '''function over(n:number):number;
function over(n:string):string;
function over(n:number|string){return n;}
function many(...values:number[]){return values.length;}
function defaulted(n:number=1){return n;}
function forward(n:number){return over(n);}
function entry(values:number[]){over(1);over("x");many(1,2);many(...values);defaulted();forward(2);}
'''}, language='typescript')
    overloads = proofs(response, ':over:')
    assert len({f['target'] for f in overloads}) == 2
    assert proofs(response, ':forward:')
    varargs = proofs(response, ':many:')
    assert {'VARARG_ELEMENT', 'VARARG_SPREAD'} <= {f['transformation'] for f in varargs}
    assert any(o['reason'] == 'DEFAULT_VALUE_NOT_EVALUATED' for site in response['call_sites']
               for o in site.get('argument_omissions', []))


def test_unresolved_and_reference_creation_do_not_gain_argument_flows(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''import java.util.function.IntUnaryOperator;
class Calls {static int take(int n){return n;} static void entry(int n){
 IntUnaryOperator reference=Calls::take; missing(n);
}}'''})
    boundaries = [s for s in response['call_sites'] if s.get('declared_target') is None
                  or s['invocation_kind'] == 'METHOD_REFERENCE']
    assert boundaries
    assert not any(f['kind'] == 'argument_to_parameter' and f.get('call_site') in {s['id'] for s in boundaries}
                   for f in response['facts'])


def test_declared_virtual_contract_binding_never_becomes_implementation_execution(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''interface Api {int take(int n);}
class Implementation implements Api {public int take(int n){return n;}}
class Calls {static int entry(Api api,int n){return api.take(n);}}'''})
    facts = proofs(response, 'Api.take(')
    assert facts
    assert all('Implementation' not in f['target'] for f in facts)
    assert all(f['binding_kind'] == 'DECLARED_PARAMETER' for f in facts)
    site = next(s for s in response['call_sites'] if 'Api.take(' in (s.get('declared_target') or ''))
    assert site['dispatch_complete'] is False


def test_graph_evidence_roundtrip_and_process_preserve_call_binding(tmp_path):
    from kgmaker.dataflow import argument_parameter_bindings, impact_paths
    from kgmaker.flow import process
    from kgmaker.inspection import graph_from_response
    from kgmaker.model import KnowledgeGraph
    from kgmaker.scanner import scan_repository
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''class Calls {
 static int take(int n){return n;} static int entry(int n){return take(n+1);}}
'''})
    selected = {'id': response['context_id'], 'scope': 'production', 'freshness': 'CURRENT',
                'origin_trust': 'LOCAL_SOURCE', 'mode': 'BUILD_AWARE', 'worker': {}}
    graph = graph_from_response(tmp_path, scan_repository(tmp_path), response, selected)
    restored = KnowledgeGraph.from_dict(graph.to_dict())
    site = next(s for s in restored.call_sites if '.take(' in (s.get('declared_target') or ''))
    bindings = argument_parameter_bindings(restored, site['id'])
    assert len(bindings) == 1 and bindings[0]['transformation'] == 'DIRECT'
    assert bindings[0]['availability'] == 'UNKNOWN' and bindings[0]['execution'] == 'NOT_OBSERVED'
    assert any(path['entity_ids'][-1] == bindings[0]['parameter']
               for path in impact_paths(restored, bindings[0]['argument'])['paths'])
    entry = next(s['id'] for s in response['symbols'] if s.get('name') == 'entry')
    report = process(restored, entry)
    assert any(b.get('argument_parameter_bindings') == bindings for b in report['cfg']['blocks'])


def binding_response():
    return {'context_id': 'context', 'symbols': [
        {'id': 'caller', 'kind': 'method'}, {'id': 'callee', 'kind': 'method'},
        {'id': 'argument', 'kind': 'value', 'call_site': 'call', 'context_id': 'context'},
        {'id': 'parameter', 'kind': 'parameter', 'name': 'n', 'method': 'callee', 'parameter_index': 0, 'context_id': 'context'}],
        'call_sites': [{'id': 'call', 'caller': 'caller', 'declared_target': 'callee',
                        'invocation_kind': 'STATIC', 'context_id': 'context', 'argument_mapping_version': 1,
                        'argument_mapping_status': 'PROVEN', 'argument_mapping_reason': 'COMPILER_ARGUMENT_MAPPING'}], 'bodies': [], 'diagnostics': [],
        'facts': [{'kind': 'argument_to_parameter', 'source': 'argument', 'target': 'parameter',
                   'call_site': 'call', 'context_id': 'context', 'argument_index': 0, 'parameter_index': 0,
                   'argument_mapping_version': 1, 'binding_kind': 'DECLARED_PARAMETER',
                   'transformation': 'DIRECT', 'parameter_name': 'n', 'evidence_kind': 'SYMBOL_RESOLVED'}]}


@pytest.mark.parametrize('change', [
    {'call_site': 'other'}, {'argument_index': True}, {'parameter_index': -1},
    {'context_id': 'other'}, {'evidence_kind': 'DISPATCH_CANDIDATE'},
    {'binding_kind': 'RUNTIME_IMPLEMENTATION'}, {'transformation': 'GUESSED'},
    {'argument_mapping_version': True}, {'target': 'caller'},
])
def test_malformed_binding_fails_before_any_publication(tmp_path, monkeypatch, change):
    from kgmaker.inspection import graph_from_response
    from kgmaker.model import KnowledgeGraph
    response = binding_response()
    response['facts'][0].update(change)
    original = tmp_path / 'last-valid-generation'
    original.write_bytes(b'unchanged')
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('implicit process'))
    base = KnowledgeGraph(3, str(tmp_path), '', [], [], {})
    with pytest.raises(WorkerError, match='binding|mapping'):
        graph_from_response(tmp_path, base, response, {'id': 'context'})
    assert original.read_bytes() == b'unchanged'
    assert not (tmp_path / '.kgmaker').exists()


def test_legacy_unversioned_binding_fact_remains_readable():
    from kgmaker.inspection import validate_response
    response = binding_response()
    response['facts'] = [{'kind': 'argument_to_parameter', 'source': 'argument', 'target': 'parameter',
                          'evidence_kind': 'SYMBOL_RESOLVED'}]
    validate_response(response, {'id': 'context'})


def test_duplicate_binding_is_ambiguous_without_arbitrary_choice():
    from kgmaker.inspection import validate_response
    response = binding_response()
    response['facts'].append(dict(response['facts'][0]))
    with pytest.raises(WorkerError, match='Ambiguous compiler argument binding'):
        validate_response(response, {'id': 'context'})


def test_workspace_qualifies_argument_context_without_changing_transform():
    from kgmaker.workspace import _qualified_evidence, _qualified_symbol, qualified
    original = {'id': 'proof', 'source': 'argument', 'target': 'parameter', 'context_ids': ['context'],
                'call_site': 'call', 'source_file': 'src/main/java/Calls.java', 'transformation': 'VARARG_ELEMENT'}
    left, right = (_qualified_evidence(repo, original) for repo in ['left', 'right'])
    assert left['call_site'] == qualified('left', 'call')
    assert right['call_site'] == qualified('right', 'call')
    assert left['source'] != right['source'] and left['target'] != right['target']
    assert left['transformation'] == right['transformation'] == 'VARARG_ELEMENT'
    symbol = _qualified_symbol('left', {'id': 'parameter', 'context_id': 'context', 'method': 'callee'})
    assert symbol['method'] == qualified('left', 'callee')
    assert original['call_site'] == 'call'


def test_actual_ambiguous_javac_overload_does_not_guess_a_parameter(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''class Calls {
 static void take(Integer n){} static void take(String n){}
 static void entry(){take(null);}}'''})
    assert any(s.get('declared_target') is None for s in response['call_sites'])
    assert not any(f['kind'] == 'argument_to_parameter' for f in response['facts'])


def test_actual_erroneous_ts_signature_does_not_prove_argument_mapping(tmp_path):
    response = analyze(tmp_path, {'src/calls.ts': '''function take(n:number):void;
function take(n:string):void;
function take(n:number|string){}
function entry(){take({});}'''}, language='typescript')
    assert not any(f['kind'] == 'argument_to_parameter' for f in response['facts'])
    assert any(d['code'] == 'TS_ARGUMENT_MAPPING_UNAVAILABLE' for d in response['diagnostics'])


def test_invalid_binding_preserves_actual_last_valid_store_generation(tmp_path, monkeypatch):
    import copy
    from kgmaker.inspection import inspect_jvm
    from kgmaker.model import KnowledgeGraph, Node
    from kgmaker.store import save_graph
    source = tmp_path / 'src/main/java/Calls.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Calls {}')
    baseline = KnowledgeGraph(3, str(tmp_path), '', [Node('sentinel', 'value', 'last valid', source.as_posix())], [], {})
    save_graph(baseline, tmp_path)
    before = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in (tmp_path / '.kgmaker').rglob('*') if p.is_file()}
    def malformed(argv, request, **kwargs):
        result = copy.deepcopy(binding_response())
        result['context_id'] = request['context']['id']
        for value in result['symbols'] + result['call_sites'] + result['facts']:
            value['context_id'] = result['context_id']
        result['facts'][0]['call_site'] = 'unproven-call'
        return result
    monkeypatch.setattr('kgmaker.inspection.command', lambda *a, **k: ['explicit-worker'])
    monkeypatch.setattr('kgmaker.inspection.handshake', lambda *a, **k: {'worker': 'test-worker', 'compiler_version': '2.1.10', 'capabilities': []})
    monkeypatch.setattr('kgmaker.inspection.distribution', lambda *a, **k: [])
    monkeypatch.setattr('kgmaker.inspection.request_worker', malformed)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('implicit application process'))
    with pytest.raises(WorkerError, match='binding'):
        inspect_jvm(tmp_path, home=HOME, publish=True)
    after = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in (tmp_path / '.kgmaker').rglob('*') if p.is_file()}
    assert before == after


def test_legacy_and_candidate_edges_do_not_gain_new_strong_impact_paths():
    from kgmaker.dataflow import impact_paths
    from kgmaker.model import Edge, KnowledgeGraph, Node
    graph = KnowledgeGraph(3, '.', '', [Node('argument', 'value', 'argument', 'a'),
                                       Node('parameter', 'parameter', 'parameter', 'a')],
                           [Edge('argument', 'parameter', 'argument_to_parameter', evidence_kind='SYMBOL_RESOLVED')], {})
    assert impact_paths(graph, 'argument')['paths'] == []
    graph.edges = [Edge('argument', 'parameter', 'argument_to_parameter', evidence_kind='DISPATCH_CANDIDATE',
                        evidence_ids=('candidate',))]
    graph.evidence = [{'id': 'candidate', 'argument_mapping_version': 1, 'call_site': 'call',
                       'source': 'argument', 'target': 'parameter'}]
    assert impact_paths(graph, 'argument')['paths'] == []


def test_actual_javac_generic_vararg_uses_instantiated_method_formal(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''class Calls {
 static <T> int many(T... values){return values.length;}
 static void entry(String[] values){many(values);many("a","b");}}
'''})
    bindings = proofs(response, '.many(')
    assert {'VARARG_ARRAY', 'VARARG_ELEMENT'} <= {f['transformation'] for f in bindings}


def test_generic_constructor_vararg_packing_without_instantiated_formal_is_unknown(tmp_path):
    response = analyze(tmp_path, {'src/main/java/Calls.java': '''class Calls {
 <T> Calls(T... values){} static void entry(String[] values){new Calls(values);}}
'''})
    site = next(s for s in response['call_sites'] if s['invocation_kind'] == 'CONSTRUCTOR' and 'Calls.<init>' in (s.get('declared_target') or ''))
    assert site['argument_mapping_status'] == 'UNKNOWN'
    assert any(d['code'] == 'JAVA_VARARG_TRANSFORMATION_UNAVAILABLE' for d in response['diagnostics'])
    assert not any(f['kind'] == 'argument_to_parameter' and f.get('call_site') == site['id'] for f in response['facts'])


@pytest.mark.parametrize('workers_required,k2_required,backend', [('1', '0', 'k1'), ('0', '1', 'k2'), ('0', '0', 'k2')])
def test_missing_required_binding_worker_cannot_be_a_green_skip(tmp_path, monkeypatch, workers_required, k2_required, backend):
    monkeypatch.setattr(sys.modules[__name__], 'HOME', tmp_path / 'missing-distribution')
    monkeypatch.setenv('KGMAKER_REQUIRE_WORKERS', workers_required)
    monkeypatch.setenv('KGMAKER_REQUIRE_K2', k2_required)
    monkeypatch.setattr('subprocess.Popen', lambda *a, **k: pytest.fail('tool discovery executed a process'))
    expected = pytest.fail.Exception if workers_required == '1' or k2_required == '1' else pytest.skip.Exception
    with pytest.raises(expected):
        analyze(tmp_path, {'src/main/kotlin/Calls.kt': 'fun entry(){}'}, backend=backend)


def test_mixed_java_kotlin_formal_binding_uses_identity_not_display_name(tmp_path):
    from kgmaker.inspection import validate_response
    response = analyze(tmp_path, {
        'src/main/java/JavaCalls.java': 'class JavaCalls {static int parse(String x){return Integer.parseInt(x);}}',
        'src/main/kotlin/KotlinCalls.kt': 'fun parseOther(x:String):Int = java.lang.Integer.parseInt(x)',
    })
    validate_response(response, {'id': response['context_id']})
    bindings = proofs(response, 'java.lang.Integer.parseInt(')
    assert len(bindings) == 2 and len({f['target'] for f in bindings}) == 1


def test_actual_inspection_pipeline_accepts_formals_without_fabricated_ranges(tmp_path):
    from kgmaker.inspection import inspect_jvm
    sources = {'src/main/java/Calls.java': '''class Calls {
 static int take(int n){return n;} static int entry(int n){return take(n);}}
'''}
    analyze(tmp_path, sources)
    result = inspect_jvm(tmp_path, home=HOME, publish=False)
    assert any(e['kind'] == 'argument_to_parameter' for e in result['graph']['edges'])
    formals = [s for s in result['graph']['symbols'] if s.get('kind') == 'parameter']
    assert formals and all(s['range'] is None for s in formals)
    assert not (tmp_path / '.kgmaker').exists()

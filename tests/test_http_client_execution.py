"""Typed request definitions/terminal intent, never actual HTTP execution."""
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from kgmaker.inspection import command, inspect_jvm
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'


def api_jars():
    repository = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', Path.home() / '.m2/repository'))
    lock = json.loads((ROOT / 'fixtures/http-client-execution/dependencies.lock.json').read_text())
    jars = []
    for entry in lock['artifacts']:
        jar, pom = repository / entry['path'], repository / entry['license_pom']
        if not jar.is_file() or not pom.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest() != entry['sha256'] or hashlib.sha256(pom.read_bytes()).hexdigest() != entry['license_pom_sha256']:
            raise WorkerError('Pinned HTTP API/license unavailable or changed: ' + entry['coordinate'], 'TOOLCHAIN_UNAVAILABLE')
        name = ET.parse(pom).getroot().findtext('{http://maven.apache.org/POM/4.0.0}licenses/{http://maven.apache.org/POM/4.0.0}license/{http://maven.apache.org/POM/4.0.0}name')
        assert name == entry['license_name']
        jars.append(str(jar))
    return jars


def analyze(root, source, *, backend='k1', config=None):
    try:
        command('jvm', HOME, kotlin_backend=backend)
        jars = api_jars()
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1'):
            pytest.fail(str(error))
        pytest.skip(str(error))
    path = root / 'src/main/java/demo/Clients.java'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    result = inspect_jvm(root, home=HOME, classpath=jars, kotlin_backend=backend, build_context=config, publish=False)
    assert not any('.err.' in d.get('code', '') for d in result['diagnostics']), result['diagnostics']
    assert not (root / '.kgmaker').exists()
    return result


def definitions(result):
    return [n for n in result['graph']['nodes'] if n['kind'] == 'http_request_definition']


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_cold_request_and_same_origin_block_are_separate(tmp_path, backend):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
class Clients {
 void cold(){Mono<String> unused=WebClient.create("https://orders.example.invalid").get().uri("/cold").retrieve().bodyToMono(String.class);}
 String triggered(){Mono<String> request=WebClient.create("https://orders.example.invalid").get().uri("/triggered").retrieve().bodyToMono(String.class);return request.block();}
}''', backend=backend)
    items = {n['metadata']['path']: n for n in definitions(result)}
    assert set(items) == {'/cold', '/triggered'}
    assert items['/cold']['metadata']['execution_status'] == 'UNSUBSCRIBED_WITHIN_SCOPE'
    assert items['/triggered']['metadata']['execution_status'] == 'STATIC_TRIGGER'
    assert all(n['metadata']['runtime_availability'] == 'UNKNOWN' for n in items.values())
    edges = [e for e in result['graph']['edges'] if e['kind'] == 'may_execute_http_request']
    assert len(edges) == 1 and edges[0]['target'] == items['/triggered']['id']
    assert edges[0]['evidence_kind'] == 'FRAMEWORK_DERIVED'


def test_same_request_spec_does_not_mix_distinct_publishers(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
class Clients {void check(){
 var spec=WebClient.create("https://orders.example.invalid").get().uri("/shared");
 Mono<String> unused=spec.retrieve().bodyToMono(String.class);
 Mono<String> subscribed=spec.retrieve().bodyToMono(String.class);
 subscribed.block();
}}''')
    values = definitions(result)
    assert len(values) == 2
    assert sorted(v['metadata']['execution_status'] for v in values) == ['STATIC_TRIGGER', 'UNSUBSCRIBED_WITHIN_SCOPE']
    assert len({v['metadata']['origin_call_site'] for v in values}) == 2


def test_imperative_retrieve_is_not_a_terminal(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.client.RestClient;
class Clients {void check(){
 RestClient.create("https://orders.example.invalid").get().uri("/prepared").retrieve();
 RestClient.create("https://orders.example.invalid").get().uri("/body").retrieve().body(String.class);
 RestClient.create("https://orders.example.invalid").get().uri("/exchange").exchange((request,response)->null);
}}''')
    values = {n['metadata']['path']: n['metadata'] for n in definitions(result)}
    assert values['/prepared']['execution_status'] == 'DEFINITION_ONLY'
    assert values['/body']['execution_status'] == values['/exchange']['execution_status'] == 'STATIC_TRIGGER'


def test_unused_unrelated_and_escaped_publishers_are_not_activated(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
class Clients {
 static void consume(Object value){}
 Mono<String> returned(){return WebClient.create("https://orders.example.invalid").get().uri("/returned").retrieve().bodyToMono(String.class);}
 void unrelated(){Mono<String> request=WebClient.create("https://orders.example.invalid").get().uri("/unrelated").retrieve().bodyToMono(String.class);Mono.just("other").block();}
 void passed(){Mono<String> request=WebClient.create("https://orders.example.invalid").get().uri("/passed").retrieve().bodyToMono(String.class);consume(request);}
 void operator(){Mono<String> request=WebClient.create("https://orders.example.invalid").get().uri("/operator").retrieve().bodyToMono(String.class);request.map(x->x).block();}
}''')
    values = {n['metadata']['path']: n['metadata'] for n in definitions(result)}
    assert values['/unrelated']['execution_status'] == 'UNSUBSCRIBED_WITHIN_SCOPE'
    assert all(values[p]['execution_status'] == 'UNKNOWN' for p in ['/returned','/passed','/operator'])
    assert not any(e['kind'] == 'may_execute_http_request' for e in result['graph']['edges'])


def test_feign_declaration_only_and_abstract_invocation_intent(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
@FeignClient(name="orders",url="https://orders.example.invalid") interface Orders {
 @GetMapping("/called") String get();
 @GetMapping("/unused") String unused();
 @GetMapping("/default") default String custom(){return "local";}
 @GetMapping("/static") static String local(){return "local";}
}
class Clients {String go(Orders orders){orders.custom();Orders.local();return orders.get();}}
''')
    values = {n['metadata']['path']: n['metadata'] for n in definitions(result)}
    assert set(values) == {'/called','/unused'}
    assert values['/called']['execution_status'] == 'FEIGN_INVOCATION_INTENT'
    assert values['/unused']['execution_status'] == 'DECLARATION_ONLY'
    assert all(v['proxy_registration'] == 'UNKNOWN' for v in values.values())
    assert len([e for e in result['graph']['edges'] if e['kind'] == 'may_execute_http_request']) == 1
    from kgmaker.model import KnowledgeGraph
    from kgmaker.flow import process
    graph = KnowledgeGraph.from_dict(result['graph'])
    entry = next(s['id'] for s in graph.symbols if s.get('owner') == 'demo.Clients' and s.get('name') == 'go')
    report = process(graph, entry)
    assert [item['path'] for item in report['http']['requests']] == ['/called']


def test_credentials_never_persist_in_graph_or_context(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class Clients {void go(){WebClient.create("https://secretUser:secretPass@example.invalid").get().uri("/route?privateToken=secretQuery#secretFragment").retrieve().bodyToMono(String.class).block();}}
''', config={'spring_properties': {'service.url':'https://privateUser:privatePass@example.invalid?a=privateQuery'}, 'spring_profiles': []})
    serialized = json.dumps(result)
    for secret in ['secretUser','secretPass','secretQuery','secretFragment','privateUser','privatePass','privateQuery']:
        assert secret not in serialized
    value = definitions(result)[0]['metadata']
    assert value['path'] is None and value['base_url'] is None
    assert value['runtime_availability'] == 'UNKNOWN'


def test_bound_property_source_provenance_and_plain_literal_placeholder(tmp_path):
    path = tmp_path / 'src/main/resources/application-test.properties'
    path.parent.mkdir(parents=True)
    path.write_text('orders.base=https://orders.example.invalid\n')
    source = '''package demo;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.reactive.function.client.WebClient;
class Clients {
 @Value("${orders.base}") String base;
 void configured(){WebClient.create(base).get().uri("/configured").retrieve().bodyToMono(String.class);}
 void plain(){WebClient.create("${orders.base}").get().uri("/plain").retrieve().bodyToMono(String.class);}
}'''
    result = analyze(tmp_path, source, config={'spring_properties': {'orders.base':'https://orders.example.invalid'}, 'spring_profiles':['test']})
    values = {n['metadata']['path']:n['metadata'] for n in definitions(result)}
    assert values['/configured']['base_url'] == 'https://orders.example.invalid'
    record = values['/configured']['uri_provenance'][0]
    assert record['source_file'] == 'src/main/resources/application-test.properties'
    assert record['key'] == 'orders.base' and record['profiles'] == ['test']
    assert record['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert values['/plain']['base_url'] is None


def test_capture_field_and_branch_boundaries(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
class Clients {Mono<String> stored;
 void captured(){var request=WebClient.create().get().uri("/captured").retrieve().bodyToMono(String.class);Runnable later=()->request.block();}
 void field(){stored=WebClient.create().get().uri("/field").retrieve().bodyToMono(String.class);}
 void branch(boolean active){var request=WebClient.create().get().uri("/branch").retrieve().bodyToMono(String.class);if(active)request.block();}
}''')
    values = {n['metadata']['path']:n['metadata'] for n in definitions(result)}
    assert values['/captured']['execution_status'] == 'UNKNOWN'
    assert values['/field']['execution_status'] == 'UNKNOWN'
    assert values['/branch']['execution_status'] == 'CONDITIONAL_STATIC_TRIGGER'
    assert len([e for e in result['graph']['edges'] if e['kind']=='may_execute_http_request']) == 1


def test_source_lookalike_and_method_reference_are_not_execution(tmp_path):
    result = analyze(tmp_path, '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class Fake {Fake get(){return this;} Fake uri(String x){return this;} Fake retrieve(){return this;} Fake bodyToMono(Class<?> c){return this;} String block(){return "fake";}}
class Clients {void go(){new Fake().get().uri("/fake").retrieve().bodyToMono(String.class).block();var request=WebClient.create().get().uri("/reference").retrieve().bodyToMono(String.class);java.util.function.Supplier<String> ref=request::block;}}
''')
    values=definitions(result)
    assert len(values)==1 and values[0]['metadata']['path']=='/reference'
    assert values[0]['metadata']['execution_status']=='UNKNOWN'
    assert not any(e['kind']=='may_execute_http_request' for e in result['graph']['edges'])


def test_inventory_legacy_and_qualified_uri_path():
    from kgmaker.model import KnowledgeGraph, Node
    from kgmaker.dataflow import http_request_inventory
    from kgmaker.workspace import _qualified_http_metadata, qualified
    graph=KnowledgeGraph(1,'.','',[],[],{})
    assert http_request_inventory(graph)['coverage']=='UNKNOWN_LEGACY_OR_SOURCE_ONLY'
    metadata={'context_id':'ctx','caller':'caller','origin_call_site':'site','path':'/orders',
              'terminal_call_site_ids':['terminal'],'uri_provenance':[{'source_file':'application.properties'}]}
    result=_qualified_http_metadata('orders',metadata)
    assert result['path']=='/orders'
    assert result['caller']==qualified('orders','caller')
    assert result['terminal_call_site_ids']==[qualified('orders','terminal')]
    assert result['uri_provenance'][0]['source_file']=='@orders/application.properties'
    assert metadata['caller']=='caller'


@pytest.mark.parametrize('version',[1,2,3])
def test_old_graph_store_versions_remain_readable(tmp_path,version):
    from kgmaker.model import KnowledgeGraph,Node
    from kgmaker.store import save_graph,load_graph
    from kgmaker.dataflow import http_request_inventory
    graph=KnowledgeGraph(version,str(tmp_path),'',[Node('source','class','Source','Source.java')],[],{})
    save_graph(graph,tmp_path,generate_docs=False)
    restored=load_graph(tmp_path)
    assert restored.nodes[0].id=='source'
    assert http_request_inventory(restored)['coverage']=='UNKNOWN_LEGACY_OR_SOURCE_ONLY'


def test_configuration_snapshot_failure_precedes_worker_and_preserves_store(tmp_path,monkeypatch):
    from kgmaker.http_execution import prepare_context
    from kgmaker.model import KnowledgeGraph,Node
    from kgmaker.store import save_graph
    graph=KnowledgeGraph(2,str(tmp_path),'',[Node('valid','class','Valid','Valid.java')],[],{})
    save_graph(graph,tmp_path,generate_docs=False)
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    config=tmp_path/'application.properties';config.write_text('service.url=https://orders.example.invalid\n')
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit process allowed'))
    with pytest.raises(ValueError,match='snapshot changed'):
        prepare_context(tmp_path,{'source_files':{'application.properties':'0'*64},'spring_properties':{'service.url':'https://orders.example.invalid'},'spring_profiles':[]})
    after={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    assert before==after


def test_duplicate_and_unbound_configuration_stays_unknown(tmp_path):
    from kgmaker.http_execution import prepare_context,_Projection
    from kgmaker.model import KnowledgeGraph
    config=tmp_path/'application.properties';config.write_text('orders.base=https://orders.example.invalid\norders.base=https://orders.example.invalid\n')
    context=prepare_context(tmp_path,{'id':'context','source_files':{'application.properties':hashlib.sha256(config.read_bytes()).hexdigest()},'spring_properties':{'orders.base':'https://orders.example.invalid'},'spring_profiles':[]})
    projection=_Projection(KnowledgeGraph(3,'.','',[],[],{}),context)
    assert projection.property_value('${orders.base}').kind=='unknown'
    assert projection.property_value('${missing}').kind=='unknown'
    assert projection.property_value('${orders.base:guessed}').literal=='${orders.base:guessed}'
    assert any(d['code']=='HTTP_CONFIGURATION_VALUE_OR_PROVENANCE_UNKNOWN' for d in projection.diagnostics)


@pytest.mark.parametrize('backend',['k1','k2'])
def test_kotlin_unavailable_bindings_are_explicit_unknown(tmp_path,backend):
    path=tmp_path/'src/main/kotlin/demo/Clients.kt';path.parent.mkdir(parents=True)
    path.write_text('''package demo
import org.springframework.web.reactive.function.client.WebClient
fun cold(){WebClient.create().get().uri("/kotlin").retrieve().bodyToMono(String::class.java)}
''')
    result=analyze(tmp_path,'package demo; class JavaInput {}',backend=backend)
    values=definitions(result)
    assert values and all(v['metadata']['execution_status']=='UNKNOWN' for v in values)
    assert any(d['code']=='HTTP_TYPED_IR_UNAVAILABLE' for d in result['graph']['diagnostics'])
    assert not any(e['kind']=='may_execute_http_request' for e in result['graph']['edges'])


@pytest.mark.parametrize('bad',[
 {'binding':{'id':3,'kind':'LOCAL_VARIABLE'}},
 {'binding_ref':{'id':'local','kind':'LOCAL_VARIABLE','symbol':'missing'}},
 {'literal':{'type':'STRING_LITERAL','value':{},'source':'COMPILER_LITERAL'}},
 {'captured_bindings':'not-a-list'},
 {'binding_references_complete':'true'},
])
def test_malformed_optional_ir_is_rejected_before_graph_publication(tmp_path,bad):
    from kgmaker.inspection import graph_from_response
    from kgmaker.model import KnowledgeGraph
    response={'context_id':'ctx','symbols':[{'id':'method'}],'call_sites':[],
              'bodies':[{'method':'method','context_id':'ctx','body':bad}], 'facts':[],'diagnostics':[]}
    with pytest.raises(WorkerError,match='typed'):
        graph_from_response(tmp_path,KnowledgeGraph(2,'.','',[],[],{}),response,{'id':'ctx'})
    assert not (tmp_path/'.kgmaker').exists()


def test_unknown_reconfiguration_does_not_keep_old_route(tmp_path):
    result=analyze(tmp_path,'''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class Clients {void go(String dynamic){var spec=WebClient.create("https://orders.example.invalid").get();spec.uri("/old");spec.uri(dynamic);spec.retrieve().bodyToMono(String.class);}}
''')
    values=definitions(result)
    assert len(values)==1
    assert values[0]['metadata']['path'] is None and values[0]['metadata']['base_url'] is None


def test_feign_inherited_contract_and_ambiguous_receiver(tmp_path):
    result=analyze(tmp_path,'''package demo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
interface Base { @GetMapping("/inherited") String get(); }
@FeignClient(name="orders",url="https://orders.example.invalid") interface Orders extends Base {}
@FeignClient(name="other",url="https://other.example.invalid") interface Other extends Base {}
class Clients {String explicit(Orders orders){return orders.get();}String unknown(Base base){return base.get();}}
''')
    values=definitions(result)
    assert len(values)==2
    assert sorted(v['metadata']['execution_status'] for v in values)==['DECLARATION_ONLY','FEIGN_INVOCATION_INTENT']
    assert any(d['code']=='HTTP_FEIGN_RECEIVER_UNAVAILABLE' for d in result['graph']['diagnostics'])


def test_anonymous_capture_and_unsupported_switch_remain_unknown(tmp_path):
    result=analyze(tmp_path,'''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class Clients {
 void captured(){var request=WebClient.create().get().uri("/anonymous").retrieve().bodyToMono(String.class);Runnable later=new Runnable(){public void run(){request.block();}};}
 void switched(int x){var request=WebClient.create().get().uri("/switch").retrieve().bodyToMono(String.class);switch(x){case 1:request.block();break;default:break;}}
}''')
    values={n['metadata']['path']:n['metadata'] for n in definitions(result)}
    assert values['/anonymous']['execution_status']=='UNKNOWN'
    assert values['/switch']['execution_status']=='UNKNOWN'
    assert not any(e['kind']=='may_execute_http_request' for e in result['graph']['edges'])


def test_source_only_defaults_and_documentation_cannot_persist_uri_credentials(tmp_path,monkeypatch):
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph,load_graph
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('SOURCE_ONLY must not start a process'))
    path=tmp_path/'src/main/kotlin/demo/Defaults.kt';path.parent.mkdir(parents=True)
    path.write_text('''package demo
fun absolute(url: String = "https://sourceUser:sourcePass@example.invalid/?token=sourceQuery") {}
fun relative(url: String = "/route?token=relativeQuery#relativeFragment") {}
fun documented() {
 // https://docUser:docPass@example.invalid/path#docFragment
}
''')
    (tmp_path/'README.md').write_text('# https://headingUser:headingPass@example.invalid/path?token=headingQuery\n')
    (tmp_path/'app.py').write_text('def documented():\n    # see //embeddedUser:embeddedPass@example.invalid/path\n    pass\n')
    graph=scan_repository(tmp_path)
    save_graph(graph,tmp_path,generate_docs=True)
    serialized=json.dumps(load_graph(tmp_path).to_dict())
    persisted='\n'.join(p.read_text() for p in (tmp_path/'.kgmaker').glob('*') if p.is_file())
    for secret in ['sourceUser','sourcePass','sourceQuery','relativeQuery','relativeFragment','docUser','docPass','docFragment','headingUser','headingPass','headingQuery','embeddedUser','embeddedPass']:
        assert secret not in serialized and secret not in persisted
    assert 'absolute' in serialized and 'relative' in serialized


@pytest.mark.parametrize('uri',[
 'ftp://unsupportedUser:unsupportedPass@example.invalid/file',
 'postgresql://unsupportedUser:unsupportedPass@example.invalid/db',
 'jdbc:postgresql://unsupportedUser:unsupportedPass@example.invalid/db?token=unsupportedQuery',
 '//unsupportedUser:unsupportedPass@example.invalid/path',
 'gopher://example.invalid/path?token=unsupportedQuery#unsupportedFragment',
])
def test_unsupported_uri_credentials_are_private_without_http_mapping(tmp_path,monkeypatch,uri):
    from kgmaker.http_execution import prepare_context,uri_parts
    from kgmaker.scanner import _public_source_text
    from kgmaker.inspection import sanitize
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit process'))
    context=prepare_context(tmp_path,{'spring_properties':{'service.url':uri},'spring_profiles':[]})
    assert context['spring_properties']['service.url'] is None
    assert context['http_redacted_input_hash']
    visible=json.dumps(context)+_public_source_text('fun call(url: String = '+json.dumps(uri)+')')+str(sanitize({'literal':{'value':uri}}))
    assert 'unsupportedUser' not in visible and 'unsupportedPass' not in visible
    assert 'unsupportedQuery' not in visible and 'unsupportedFragment' not in visible
    assert uri_parts(uri)['status'] != 'LITERAL'


@pytest.mark.parametrize('backend',['k1','k2'])
def test_abrupt_conditional_loop_and_resource_operands_do_not_claim_unused(tmp_path,backend):
    result=analyze(tmp_path,'''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class E extends RuntimeException {E(Object value){}}
class Resource implements AutoCloseable {Resource(Object value){} public void close(){}}
class Clients {
 static boolean consume(Object value){return true;}
 void thrown(){var p=WebClient.create().get().uri("/throw").retrieve().bodyToMono(String.class);throw new E(p);}
 void condition(){var p=WebClient.create().get().uri("/ternary").retrieve().bodyToMono(String.class);Object x=consume(p)?"yes":"no";}
 void updated(boolean active){var p=WebClient.create().get().uri("/update").retrieve().bodyToMono(String.class);for(;active;p.block()){}}
 void resource(){var p=WebClient.create().get().uri("/resource").retrieve().bodyToMono(String.class);try(var resource=new Resource(p)){}}
 void unreachableUpdate(){var p=WebClient.create().get().uri("/break").retrieve().bodyToMono(String.class);for(;;p.block()){break;}}
}''',backend=backend)
    values={n['metadata']['path']:n['metadata'] for n in definitions(result)}
    assert set(values)=={'/throw','/ternary','/update','/resource','/break'}
    assert all(v['execution_status']=='UNKNOWN' and v['unknown_reasons'] for v in values.values())
    assert not any(e['kind']=='may_execute_http_request' for e in result['graph']['edges'])


@pytest.mark.parametrize('backend',['k1','k2'])
def test_uri_callback_cannot_keep_original_literal_route(tmp_path,backend):
    result=analyze(tmp_path,'''package demo;
import org.springframework.web.reactive.function.client.WebClient;
class Clients {void callback(){WebClient.create("https://orders.example.invalid").get().uri("/old",builder->builder.replacePath("/new").build()).retrieve().bodyToMono(String.class).block();}}
''',backend=backend)
    values=definitions(result)
    assert len(values)==1
    metadata=values[0]['metadata']
    assert metadata['path'] is None and metadata['base_url'] is None
    assert 'HTTP_URI_OVERLOAD_UNSUPPORTED' in metadata['unknown_reasons']
    assert metadata['runtime_availability']=='UNKNOWN'


def test_feign_client_prefix_is_not_an_exact_unprefixed_route(tmp_path):
    result=analyze(tmp_path,'''package demo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
@FeignClient(name="orders",url="https://orders.example.invalid",path="/api") interface Orders {@GetMapping("/orders") String get();}
class Clients {String call(Orders orders){return orders.get();}}
''')
    metadata=definitions(result)[0]['metadata']
    assert metadata['path'] is None
    assert metadata['method_path']=='/orders' and metadata['client_path']=='/api'
    assert metadata['uri_status']=='COMPOSED_ROUTE_UNKNOWN'
    assert metadata['execution_status']=='FEIGN_INVOCATION_INTENT'


@pytest.mark.parametrize('override',[
 'orders.base=https\\://overrides.example.invalid',
 'orders.base https://overrides.example.invalid',
])
def test_unsupported_properties_override_cannot_prove_first_literal(tmp_path,override):
    from kgmaker.http_execution import prepare_context,_Projection
    from kgmaker.model import KnowledgeGraph
    path=tmp_path/'application.properties';path.write_text('orders.base=https://orders.example.invalid\n'+override+'\n')
    context=prepare_context(tmp_path,{'id':'ctx','source_files':{'application.properties':hashlib.sha256(path.read_bytes()).hexdigest()},'spring_properties':{'orders.base':'https://orders.example.invalid'},'spring_profiles':[]})
    projection=_Projection(KnowledgeGraph(3,'.','',[],[],{}),context)
    assert projection.property_value('${orders.base}').kind=='unknown'
    assert any(item['status']=='UNSUPPORTED_PROPERTY_SYNTAX' for item in context['http_config_provenance']['orders.base'])


def test_prior_http_proof_is_stale_without_process_or_store_mutation(tmp_path,monkeypatch):
    from kgmaker.http_execution import VERSION,prepare_context
    from kgmaker.graph_provider import validate_context_snapshot
    from kgmaker.model import KnowledgeGraph,Node
    from kgmaker.store import save_graph
    from kgmaker.analysis_model import digest
    save_graph(KnowledgeGraph(2,str(tmp_path),'',[Node('valid','class','Valid','Valid.java')],[],{}),tmp_path,generate_docs=False)
    before={p:p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**kw:pytest.fail('No implicit refresh'))
    old={'language':'jvm','framework_rule_versions':{'http':'http-client-execution-1'},'http_inputs_hash':digest({'sources':{},'redacted':None})}
    with pytest.raises(WorkerError,match='HTTP rule/configuration proof changed') as error:
        validate_context_snapshot(tmp_path,old)
    assert error.value.status=='STALE'
    assert VERSION=='http-client-execution-2'
    current=prepare_context(tmp_path,{'language':'jvm','source_files':{}})
    validate_context_snapshot(tmp_path,current)
    assert before=={p:p.read_bytes() for p in (tmp_path/'.kgmaker').rglob('*') if p.is_file()}

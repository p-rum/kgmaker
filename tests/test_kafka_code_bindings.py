"""Actual pinned Kafka code declarations; never starts Spring, Kafka or app code."""
from pathlib import Path

import pytest

from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph
from test_t024_discover_process_triggers import actual_prerequisites

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'workers'
LISTENER = 'org.springframework.kafka.annotation.KafkaListener'


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_canonical_listener_groups_and_regex_keep_original_method_ids(tmp_path, backend):
    jars = actual_prerequisites(backend)
    source = tmp_path / 'src/main/java/demo/KafkaEntries.java'
    source.parent.mkdir(parents=True)
    source.write_text('''package demo;
import org.springframework.kafka.annotation.KafkaListener;
public class KafkaEntries {
  @KafkaListener(id="first-listener", topics={"orders"}, groupId="first-group")
  public void first(String payload) {}
  @KafkaListener(id="second-listener", topics={"orders"}, groupId="second-group")
  public void second(String payload) {}
  @KafkaListener(id="pattern-listener", topicPattern="orders[.].*", groupId="pattern-group")
  public void pattern(String payload) {}
}
''')
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend=backend, repo_id='kafka-fixture',
                         classpath=jars, build_context={'spring_component_packages': ['demo']}, publish=False)
    assert not any('.err.' in str(d.get('code', '')) or str(d.get('reason', '')).startswith('ERROR:')
                   for d in result['diagnostics'])
    graph = KnowledgeGraph.from_dict(result['graph'])
    methods = {item['name']: item for item in graph.symbols
               if item.get('owner') == 'demo.KafkaEntries' and item.get('name') in {'first', 'second', 'pattern'}}
    assert set(methods) == {'first', 'second', 'pattern'}
    # The pre-existing compiler genuinely captured the pinned canonical annotation.
    assert all(any(a.get('name') == LISTENER for a in m.get('annotations', [])) for m in methods.values())
    raw_groups = {a['values']['groupId'] for m in methods.values()
                  for a in m['annotations'] if a.get('name') == LISTENER}
    assert raw_groups == {'first-group', 'second-group', 'pattern-group'}
    facts = [node for node in graph.nodes if node.kind == 'kafka_code_listener']
    assert len(facts) == 3
    by_origin = {node.metadata['origin_id']: node for node in facts}
    assert set(by_origin) == {item['id'] for item in methods.values()}
    assert {by_origin[methods[name]['id']].metadata['group_id'] for name in ['first', 'second']} == {'first-group', 'second-group'}
    assert by_origin[methods['first']['id']].id != by_origin[methods['second']['id']].id
    pattern = by_origin[methods['pattern']['id']]
    assert pattern.metadata['subscription_kind'] == 'REGEX'
    assert pattern.metadata['topic_pattern'] == 'orders[.].*'
    assert pattern.metadata['topics'] == []
    assert all(node.metadata['execution'] == 'NOT_OBSERVED' for node in facts)
    # Replay canonical proofs against independently corrupted captures; matching
    # symbol/Node mirrors alone must never authorize a changed annotation or realm.
    import copy
    from kgmaker.kafka_code import validate_code_fact
    original = graph.to_dict()
    context = next(c for c in graph.contexts if c['id'] == result['context']['id'])
    fact = by_origin[methods['first']['id']]
    assert validate_code_fact(tmp_path, graph, context, fact)
    for corruption in ['annotation', 'realm', 'source-range', 'weak-proof', 'missing-proof']:
        payload = copy.deepcopy(original)
        selected = next(c for c in payload['contexts'] if c['id'] == context['id'])
        method = next(m for m in payload['symbols'] if m['id'] == methods['first']['id'])
        node = next(n for n in payload['nodes'] if n['id'] == method['id'])
        proofs = [e for e in payload['evidence'] if e.get('relation') == 'contains'
                  and e.get('target') == method['id']]
        assert proofs
        if corruption == 'annotation':
            for target in [method, node['metadata']]:
                next(a for a in target['annotations'] if a['name'] == LISTENER)['values']['groupId'] = 'forged-group'
        elif corruption == 'realm':
            selected['module'] = 'foreign-module'
        elif corruption == 'source-range':
            method['range']['start'] = True
            node['metadata']['range']['start'] = True
        elif corruption == 'weak-proof':
            for proof in proofs:
                proof['compiler_realm'] = {}
        else:
            for proof in proofs:
                proof.pop('compiler_annotation_fingerprint', None)
        damaged = KnowledgeGraph.from_dict(payload)
        before = damaged.to_dict()
        assert not validate_code_fact(tmp_path, damaged, selected, fact), corruption
        assert damaged.to_dict() == before
    assert graph.to_dict() == original


@pytest.mark.parametrize('mode', ['SOURCE_ONLY', 'BUILD_IMPORT'])
def test_source_graph_and_mirrored_annotation_metadata_are_not_compiler_proof(tmp_path, mode):
    from dataclasses import replace
    import hashlib
    from kgmaker.kafka_code import augment_kafka_graph
    from kgmaker.model import Node
    from kgmaker.scanner import scan_repository
    path = 'src/main/java/Demo.java'
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    source.write_text('class Demo { void listen(String p) {} }\n')
    base = scan_repository(tmp_path)
    ctx = {'id': 'forged-context', 'language': 'jvm', 'scope': 'production', 'repo_id': 'demo',
           'module': 'root', 'source_set': 'main', 'source_files': base.files, 'mode': mode,
           'analyzer_version': 'inspection-1', 'origin_trust': 'LOCAL_COMPILER_INPUTS',
           'freshness': 'CONTENT_VERIFIED'}
    where = {'start': 0, 'end': len(source.read_text()), 'start_line': 1, 'end_line': 1,
             'start_column': 1, 'end_column': 40}
    raw = {'id': 'forged:method', 'kind': 'method', 'owner': 'Demo', 'name': 'listen',
           'descriptor': '(Ljava/lang/String;)V', 'path': path, 'range': where, 'scope': 'production',
           'context_id': ctx['id'], 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'annotations': [{'name': LISTENER, 'values': {'topics': ['orders'], 'groupId': 'group'}}]}
    graph = replace(base, contexts=base.contexts + [ctx], symbols=[raw], nodes=base.nodes + [
        Node(raw['id'], 'method', 'listen', path, line=1, signature=raw['descriptor'],
             scope='production', metadata=dict(raw))])
    before = graph.to_dict()
    result = augment_kafka_graph(tmp_path, graph, [], ctx)
    assert not any(n.kind == 'kafka_code_listener' for n in result.nodes)
    assert graph.to_dict() == before


def extra_api_jars():
    import hashlib
    import json
    import os
    import xml.etree.ElementTree as ET
    repository = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', str(Path.home() / '.m2/repository')))
    lock = json.loads((ROOT / 'fixtures/kafka-code-bindings/dependencies.lock.json').read_text())
    jars = []
    for item in lock['artifacts']:
        for key, checksum in [('path', 'sha256'), ('artifact_pom', 'artifact_pom_sha256'), ('license_pom', 'license_pom_sha256')]:
            artifact = repository / item[key]
            if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != item[checksum]:
                message = 'Explicit pinned Kafka code API preparation missing/mismatched: ' + item[key]
                if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or os.environ.get('KGMAKER_REQUIRE_K2') == '1':
                    pytest.fail(message)
                pytest.skip(message)
        name = ET.parse(repository / item['license_pom']).getroot().findtext('{http://maven.apache.org/POM/4.0.0}licenses/{http://maven.apache.org/POM/4.0.0}license/{http://maven.apache.org/POM/4.0.0}name')
        assert name == item['license_name']
        jars.append(str(repository / item['path']))
    return jars


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_java_send_requires_canonical_api_and_typed_literal_in_both_backends(tmp_path, backend):
    jars = actual_prerequisites(backend) + extra_api_jars()
    source = tmp_path / 'src/main/java/demo/Producer.java'
    source.parent.mkdir(parents=True)
    source.write_text('''package demo;
import org.springframework.kafka.core.KafkaTemplate;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.ProducerRecord;
import java.util.function.BiFunction;
interface Wrapper { Object send(String topic, String payload); }
public class Producer {
  public void publish(KafkaTemplate<String,String> template, Wrapper wrapper, String dynamic) {
    template.send("orders", "payload");
    template.send(dynamic, "payload");
    final String constant = "orders";
    template.send(constant, "payload");
    template.send("ord\\u0065rs", "payload");
    template.send(new ProducerRecord<String,String>("orders", "payload"));
    wrapper.send("orders", "payload");
    new NewTopic("orders", 1, (short)1);
    new ProducerRecord<String,String>("orders", "payload");
    BiFunction<String,String,Object> reference = template::send;
  }
}
''')
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend=backend, repo_id='producer-fixture',
                         classpath=jars, publish=False)
    assert not any('.err.' in str(d.get('code', '')) for d in result['diagnostics'])
    graph = KnowledgeGraph.from_dict(result['graph'])
    facts = [n for n in graph.nodes if n.kind == 'kafka_code_producer']
    assert len(facts) == 1
    fact = facts[0]
    assert fact.metadata['topic'] == 'orders'
    assert fact.metadata['execution'] == 'NOT_OBSERVED' and fact.metadata['activation'] == 'UNKNOWN'
    sites = {s['id']: s for s in graph.call_sites}
    symbols = {s['id']: s for s in graph.symbols}
    site = sites[fact.metadata['origin_id']]
    assert symbols[site['declared_target']]['owner'] == 'org.springframework.kafka.core.KafkaTemplate'
    assert fact.metadata['call_site'] == site['id'] and fact.metadata['caller'] == site['caller']
    assert fact.metadata['api_descriptor'] == '(Ljava/lang/String;Ljava/lang/Object;)Ljava/util/concurrent/CompletableFuture;'
    assert fact.metadata['code_origin'] == 'JAVAC_API_CONTRACT'
    assert not any(n.metadata.get('code_origin') == 'KOTLIN' for n in facts)


from test_kafka_bindings import kafka_workspace


def test_actual_schema2_joins_source_code_and_group_without_exposing_private_capture(kafka_workspace):
    import json
    from kgmaker.workspace import snapshot_workspace, qualified
    from kgmaker.views import select_service_contexts
    from kgmaker.kafka_code import validate_code_fact
    root, manifest, document = kafka_workspace
    jars = actual_prerequisites('k1') + extra_api_jars()
    captures = {}
    for repo in ['producer', 'consumer']:
        path = root / repo / 'src/main/java/demo/Code.java'
        path.parent.mkdir(parents=True)
        body = ('''package demo; import org.springframework.kafka.core.KafkaTemplate;
public class Code { public void publish(KafkaTemplate<String,String> t) { t.send("orders-blue", "payload"); } }
''' if repo == 'producer' else '''package demo; import org.springframework.kafka.annotation.KafkaListener;
public class Code { @KafkaListener(id="orders",topics={"orders-blue"},groupId="${listener.group}")
public void consume(String value) {} }
''')
        path.write_text(body)
        result = inspect_jvm(root / repo, home=HOME, repo_id='local', classpath=jars,
            build_context={'spring_profiles': ['blue'], 'spring_properties': {
                'listener.group': 'blue-group', 'spring.kafka.password': 'SYNTHETIC_DO_NOT_EXPORT_CODE_GROUP'}})
        graph = KnowledgeGraph.from_dict(result['graph'])
        fact = next(n for n in graph.nodes if n.kind == ('kafka_code_producer' if repo == 'producer' else 'kafka_code_listener'))
        context = next(c for c in graph.contexts if c['id'] == result['context']['id'])
        assert validate_code_fact(root / repo, graph, context, fact)
        captures[repo] = (result, fact, (root / repo / '.kgmaker/graph.json').read_bytes())
    config = root / 'consumer/src/main/resources/application.properties'
    config.write_text(config.read_text() + 'spring.cloud.stream.bindings.orders-in-0.group=${listener.group}\n')
    # Config is itself a captured source input: refresh after adding its explicit group.
    result = inspect_jvm(root / 'consumer', home=HOME, repo_id='local', classpath=jars,
        build_context={'spring_profiles': ['blue'], 'spring_properties': {
            'listener.group': 'blue-group', 'spring.kafka.password': 'SYNTHETIC_DO_NOT_EXPORT_CODE_GROUP'}})
    graph = KnowledgeGraph.from_dict(result['graph'])
    fact = next(n for n in graph.nodes if n.kind == 'kafka_code_listener')
    captures['consumer'] = (result, fact, (root / 'consumer/.kgmaker/graph.json').read_bytes())
    document['kafka_bindings']['schema_version'] = 2
    for binding in document['kafka_bindings']['bindings']:
        result, fact, _ = captures[binding['repo_id']]
        binding['context_id'] = result['context']['id']
        binding['code_ref'] = {'kind': 'listener' if binding['direction'] == 'consumer' else 'send',
            'id': fact.metadata['origin_id'], 'context_id': result['context']['id'],
            'source_file': fact.metadata['source_file'], 'sha256': fact.metadata['source_sha256']}
    manifest.write_text(json.dumps(document))
    _, _, _, graph, _ = snapshot_workspace(manifest)
    bindings = [n for n in graph.nodes if n.kind == 'kafka_binding']
    assert len(bindings) == 2 and all(n.metadata['code_binding'] == 'VERIFIED_STATIC' for n in bindings)
    consumer = next(n for n in bindings if n.metadata['direction'] == 'consumer')
    group = consumer.metadata['consumer_group']
    assert group['value'] == 'blue-group' and group['status'] == 'RESOLVED'
    assert group['key'] == 'spring.cloud.stream.bindings.orders-in-0.group'
    assert group['origin'] == 'CAPTURED_PROPERTY_OVERRIDE' and group['active_profiles'] == ['blue']
    assert len([n for n in graph.nodes if n.kind == 'kafka_subscription']) == 1
    assert any(e.kind == 'uses_kafka_listener' for e in graph.edges)
    evidence = {e['id']: e for e in graph.evidence}
    for item in evidence.values():
        if item.get('extractor') == 'kafka-code-1':
            assert all(identity in evidence for identity in item['compiler_evidence_ids'])
    for repo, (result, fact, before) in captures.items():
        assert (root / repo / '.kgmaker/graph.json').read_bytes() == before
        projected = next(n for n in graph.nodes if n.id == qualified(repo, fact.id))
        assert projected.metadata['origin_id'] == qualified(repo, fact.metadata['origin_id'])
        assert projected.metadata['original_origin_id'] == fact.metadata['origin_id']
        assert projected.metadata['source_file'] == projected.path
    selected = select_service_contexts(graph, [{'service_id': 'consumer-svc', 'repo_id': 'consumer', 'module': 'root'}],
        scope='production', repo_roots={'consumer': root / 'consumer'})
    assert selected['services'][0]['status'] == 'CURRENT'
    assert 'SYNTHETIC_DO_NOT_EXPORT_CODE_GROUP' not in json.dumps(graph.to_dict())
    import copy
    # Explicit selectors must agree with the actual current code fact. A valid
    # config/topic is insufficient when any code-side identity is wrong.
    original_document = copy.deepcopy(document)
    for field, value in [('id', 'foreign-method'), ('sha256', '0' * 64),
                         ('context_id', 'foreign-context')]:
        damaged = copy.deepcopy(original_document)
        consumer_binding = next(b for b in damaged['kafka_bindings']['bindings'] if b['direction'] == 'consumer')
        consumer_binding['code_ref'][field] = value
        if field == 'context_id':
            consumer_binding['context_id'] = value
        manifest.write_text(json.dumps(damaged))
        if field == 'context_id':
            from kgmaker.analysis_model import AnalysisError
            with pytest.raises(AnalysisError, match='Unknown or incompatible Kafka compiler context'):
                snapshot_workspace(manifest)
            for repo, (_, _, before) in captures.items():
                assert (root / repo / '.kgmaker/graph.json').read_bytes() == before
            continue
        _, _, _, rejected, _ = snapshot_workspace(manifest)
        consumer = next(n for n in rejected.nodes if n.kind == 'kafka_binding' and n.metadata['direction'] == 'consumer')
        assert consumer.metadata['code_binding'] == 'UNPROVEN', field
        assert not any(n.kind == 'kafka_subscription' for n in rejected.nodes), field
        for repo, (_, _, before) in captures.items():
            assert (root / repo / '.kgmaker/graph.json').read_bytes() == before
    manifest.write_text(json.dumps(original_document))


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_kotlin_listener_requires_explicit_group_and_keeps_regex_candidate(tmp_path, backend):
    jars = actual_prerequisites(backend)
    source = tmp_path / 'src/main/kotlin/demo/Listeners.kt'
    source.parent.mkdir(parents=True)
    source.write_text('''package demo
import org.springframework.kafka.annotation.KafkaListener
class Listeners {
    @KafkaListener(topics = ["orders"], groupId = "explicit")
    fun consume(value: String) {}
    @KafkaListener(id = "not-a-group", topics = ["orders"])
    fun missing(value: String) {}
    @KafkaListener(topicPattern = "orders.*", groupId = "pattern")
    fun regex(value: String) {}
}
''')
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend=backend, repo_id='kafka-fixture',
                         classpath=jars, publish=False)
    assert not any('.err.' in str(d.get('code', '')) or str(d.get('reason', '')).startswith('ERROR:')
                   for d in result['diagnostics'])
    graph = KnowledgeGraph.from_dict(result['graph'])
    facts = {n.metadata['method_name']: n for n in graph.nodes if n.kind == 'kafka_code_listener'}
    if backend == 'k2':
        # This pinned backend explicitly omits method annotations. No fallback
        # source parser or method-name inference may manufacture a listener.
        methods = [m for m in graph.symbols if m.get('name') in {'consume', 'missing', 'regex'}]
        assert len(methods) == 3 and all('annotations' not in m for m in methods)
        assert any(d.get('code') == 'K2_SOURCE_MODEL_PARTIAL' for d in result['diagnostics'])
        assert facts == {}
        assert not any(c.get('kafka_code_analysis') for c in graph.contexts)
        return
    assert set(facts) == {'consume', 'missing', 'regex'}
    assert facts['consume'].metadata['status'] == 'DECLARED'
    assert facts['consume'].metadata['group_id'] == 'explicit'
    assert facts['missing'].metadata['status'] == 'UNKNOWN'
    assert facts['missing'].metadata['group_id'] is None
    assert facts['regex'].metadata['status'] == 'REGEX_CANDIDATE'
    assert facts['regex'].metadata['topics'] == []

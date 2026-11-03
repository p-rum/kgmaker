"""Captured public Kafka catalogue fixtures; compiler runs only in explicit setup."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.workspace import load_workspace, snapshot_workspace
from test_kafka_bindings import kafka_workspace
from test_kafka_code_bindings import extra_api_jars
from test_t024_discover_process_triggers import actual_prerequisites

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', params=['k1', 'k2'])
def capture(tmp_path_factory, request):
    backend = request.param
    root = tmp_path_factory.mktemp('t012-' + backend)
    root, manifest, document = kafka_workspace.__wrapped__(root)
    jars = actual_prerequisites(backend) + extra_api_jars()
    bodies = {
        'producer': '''package demo; import org.springframework.kafka.core.KafkaTemplate;
import org.apache.kafka.clients.admin.NewTopic;
public class Code { public void publish(KafkaTemplate<String,String> t) { t.send("orders-blue", "payload"); }
 public NewTopic declaration() { return new NewTopic("infrastructure-only", 1, (short)1); } }
''',
        'consumer': '''package demo; import org.springframework.kafka.annotation.KafkaListener;
public class Code {
 @KafkaListener(id="one",topics={"orders-blue"},groupId="group-one") public void one(String value) {}
 @KafkaListener(id="two",topics={"orders-blue"},groupId="group-two") public void two(String value) {}
 @KafkaListener(topicPattern="orders[.].*",groupId="pattern-group") public void pattern(String value) {}
}
'''}
    config = root / 'consumer/src/main/resources/application.properties'
    config.write_text(config.read_text() + 'spring.cloud.stream.bindings.orders-in-0.group=group-one\n'
        'spring.cloud.stream.bindings.second-in-0.destination=orders-blue\n'
        'spring.cloud.stream.bindings.second-in-0.binder=beta\n'
        'spring.cloud.stream.bindings.second-in-0.group=group-two\n')
    facts = {}
    for repo, body in bodies.items():
        source = root / repo / 'src/main/java/demo/Code.java'
        source.parent.mkdir(parents=True); source.write_text(body)
        if repo=='consumer':
            kotlin=root/repo/'src/main/kotlin/demo/Listener.kt';kotlin.parent.mkdir(parents=True)
            kotlin.write_text('''package demo
import org.springframework.kafka.annotation.KafkaListener
class KotlinListener { @KafkaListener(topics=["kotlin-orders"],groupId="kotlin-group")
fun kotlinConsume(value: String) {} }
''')
        result = inspect_jvm(root / repo, home=ROOT / 'workers', kotlin_backend=backend,
            repo_id='local', classpath=jars, build_context={'spring_profiles': ['blue']})
        assert not any('.err.' in str(d.get('code', '')) for d in result['diagnostics'])
        graph = KnowledgeGraph.from_dict(result['graph'])
        facts[repo] = (result['context']['id'], {n.metadata['method_name']: n for n in graph.nodes
            if n.kind in {'kafka_code_listener','kafka_code_producer'}})
    second = copy.deepcopy(document['kafka_bindings']['bindings'][1])
    second.update(id='second-group', binding='second-in-0')
    document['kafka_bindings']['bindings'].append(second)
    document['kafka_bindings']['schema_version'] = 2
    for binding in document['kafka_bindings']['bindings']:
        repo = binding['repo_id']; context, by_method = facts[repo]
        fact = by_method['publish' if repo == 'producer' else 'two' if binding['id']=='second-group' else 'one']
        binding['context_id'] = context
        binding['code_ref'] = {'kind':'send' if repo=='producer' else 'listener',
            'id':fact.metadata['origin_id'], 'context_id':context,
            'source_file':fact.metadata['source_file'], 'sha256':fact.metadata['source_sha256']}
    manifest.write_text(json.dumps(document))
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    assert len([n for n in graph.nodes if n.kind=='kafka_subscription']) == 2
    return workspace, graph, coverage


def project(capture):
    from kgmaker.interfaces import project_kafka_interfaces
    workspace, graph, coverage = capture
    return project_kafka_interfaces(workspace, graph, source_coverage=coverage)


def test_actual_ac01_ac02_realms_groups_original_ids_and_regex(capture):
    view = project(capture).to_dict()
    nodes = [n for n in view['nodes'] if n['kind']=='kafka_interface']
    subscriptions = [n for n in nodes if n['attributes'].get('subscription_id')]
    assert len(subscriptions)==2
    assert {n['attributes']['consumer_group'] for n in subscriptions}=={'group-one','group-two'}
    assert {n['attributes']['broker_realm'] for n in subscriptions}=={'cluster-a','cluster-b'}
    assert len({n['id'] for n in subscriptions})==2
    assert all(n['attributes']['origin_id'] in n['original_ids'] for n in subscriptions)
    regex = [n for n in nodes if n['attributes'].get('subscription_kind')=='REGEX']
    assert len(regex)==1 and regex[0]['attributes']['topic_pattern']=='orders[.].*'
    assert regex[0]['attributes']['topics']==[]
    assert regex[0]['attributes']['broker_realm'] is None


def test_actual_ac03_ac04_no_infrastructure_publisher_offline_immutable(capture):
    workspace, graph, coverage = capture
    before = copy.deepcopy(workspace), graph.to_dict()
    with patch('subprocess.Popen',side_effect=AssertionError('implicit process')), patch('socket.socket',side_effect=AssertionError('network')):
        view = project(capture).to_dict()
    assert workspace==before[0] and graph.to_dict()==before[1]
    publishers=[n for n in view['nodes'] if n['kind']=='kafka_interface' and n['attributes']['direction']=='PRODUCER']
    assert len(publishers)==1 and publishers[0]['attributes']['topics']==['orders-blue']
    assert 'infrastructure-only' not in json.dumps(view)
    assert all(n['attributes']['delivery']=='NOT_OBSERVED' for n in publishers)


@pytest.mark.parametrize('corruption', ['group','realm','origin','source','context','scope','logical',
    'code-proof','missing-code-edge','binding-proof','subscription-group','contract',
    'virtual-kind','virtual-path','virtual-context-mode','virtual-context-path','virtual-context-id'])
def test_actual_ac05_malformed_relevant_snapshot_fails_closed_without_mutation(capture, corruption):
    from kgmaker.interfaces import InterfaceProjectionError, project_kafka_interfaces
    workspace, graph, coverage = capture
    payload = copy.deepcopy(graph.to_dict())
    listener = next(n for n in payload['nodes'] if n['kind']=='kafka_code_listener' and n['metadata']['method_name']=='one')
    md=listener['metadata']
    if corruption=='group': md['group_id']='forged'
    elif corruption=='realm': md['source_realm']['module']='foreign'
    elif corruption=='origin': md['origin_id']='repo:consumer:forged'
    elif corruption=='source': md['source_sha256']='0'*64
    elif corruption=='context': md['context_id']='repo:consumer:foreign-context'
    elif corruption=='scope': listener['scope']='test'
    elif corruption=='logical': md['logical_id']='forged'
    elif corruption=='code-proof':
        next(e for e in payload['evidence'] if e.get('target')==listener['id'] and e.get('extractor')=='kafka-code-1')['sha256']='0'*64
    elif corruption=='missing-code-edge':
        payload['edges']=[e for e in payload['edges'] if not (e['kind']=='declares_kafka_listener' and e['target']==listener['id'])]
    elif corruption=='binding-proof':
        next(e for e in payload['evidence'] if e.get('relation')=='binds_kafka_code')['manifest_sha256']='0'*64
    elif corruption=='subscription-group':
        next(n for n in payload['nodes'] if n['kind']=='kafka_subscription')['metadata']['group_id']='forged'
    elif corruption=='contract':
        next(n for n in payload['nodes'] if n['kind']=='kafka_binding')['metadata']['contract_sha256']='0'*64
    elif corruption in {'virtual-kind','virtual-path'}:
        virtual=next(n for n in payload['nodes'] if n['kind']=='kafka_binding')
        virtual['kind' if corruption=='virtual-kind' else 'path']='forged'
    else:
        virtual=next(c for c in payload['contexts'] if c.get('kafka_binding_version'))
        if corruption=='virtual-context-mode':virtual['mode']='BUILD_IMPORT'
        elif corruption=='virtual-context-path':virtual['source_files']['@foreign/secret']='0'*64
        else:virtual['id']='workspace:kafka-context:forged'
    from dataclasses import replace
    damaged=(replace(graph,contexts=payload['contexts']) if corruption=='virtual-context-id'
             else KnowledgeGraph.from_dict(payload))
    before=damaged.to_dict(),copy.deepcopy(workspace)
    with pytest.raises(InterfaceProjectionError):
        project_kafka_interfaces(workspace,damaged,source_coverage=coverage)
    assert damaged.to_dict()==before[0] and workspace==before[1]


def test_ac03_configuration_only_and_unknown_realm_remain_declared(kafka_workspace):
    from kgmaker.interfaces import project_kafka_interfaces
    root,manifest,document=kafka_workspace
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    view=project_kafka_interfaces(load_workspace(manifest),graph,source_coverage=coverage).to_dict()
    nodes=[n for n in view['nodes'] if n['kind']=='kafka_interface']
    assert len(nodes)==2
    assert all(n['attributes']['code_binding']=='UNPROVEN' and n['resolution_status']=='UNRESOLVED' for n in nodes)
    assert all(n['attributes']['origin_id'] is None and n['attributes']['delivery']=='NOT_OBSERVED' for n in nodes)
    config=root/'consumer/src/main/resources/application.properties'
    config.write_text(config.read_text().replace('.binder=alpha','.binder=unmapped'))
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    view=project_kafka_interfaces(load_workspace(manifest),graph,source_coverage=coverage).to_dict()
    assert any(n['attributes'].get('broker_realm') is None for n in view['nodes'] if n['kind']=='kafka_interface')


def test_actual_kotlin_k1_listener_and_k2_annotation_boundary(capture):
    workspace,graph,coverage=capture
    view=project(capture).to_dict()
    kotlin=[n for n in view['nodes'] if n['kind']=='kafka_interface' and n['attributes'].get('consumer_group')=='kotlin-group']
    contexts=[c for c in graph.contexts if c.get('repo_id')=='consumer' and c.get('kotlin_backend')]
    assert len(contexts)==1
    if contexts[0]['kotlin_backend']=='k1':
        assert len(kotlin)==1 and kotlin[0]['attributes']['topics']==['kotlin-orders']
    else:
        assert kotlin==[]
        assert any(d.get('code')=='K2_SOURCE_MODEL_PARTIAL' for d in graph.diagnostics)


def test_actual_selected_context_ignores_stale_neighbor_capture(capture):
    from dataclasses import replace
    from kgmaker.interfaces import project_kafka_interfaces
    workspace,graph,coverage=capture
    compiler=[c for c in graph.contexts if c.get('mode') in {'BUILD_IMPORT','BUILD_EXECUTE'}]
    selected={('consumer-svc' if c['repo_id']=='consumer' else 'producer-svc',c['repo_id'],c['module']):c['id']
              for c in compiler if c['repo_id'] in {'producer','consumer'}}
    stale=copy.deepcopy(next(c for c in compiler if c['repo_id']=='consumer'))
    stale.update(id=stale['id']+':historical',freshness='STALE')
    stale['source_files']={'@consumer/src/main/java/demo/old.java':'0'*64}
    damaged=replace(graph,contexts=[*graph.contexts,stale]);before=damaged.to_dict()
    view=project_kafka_interfaces(workspace,damaged,source_coverage=coverage,selected_contexts=selected).to_dict()
    assert len([n for n in view['nodes'] if n['kind']=='kafka_interface' and n['attributes'].get('subscription_id')])==2
    assert damaged.to_dict()==before


@pytest.mark.parametrize('role', ['producer-origin','producer-caller','producer-target','listener-origin'])
@pytest.mark.parametrize('field', ['kind','name','scope','path','line','metadata'])
def test_actual_public_compiler_nodes_require_canonical_authority(capture, role, field):
    from kgmaker.interfaces import InterfaceProjectionError, project_kafka_interfaces
    workspace,graph,coverage=capture
    payload=copy.deepcopy(graph.to_dict())
    producer=next(n for n in payload['nodes'] if n['kind']=='kafka_code_producer')
    listener=next(n for n in payload['nodes'] if n['kind']=='kafka_code_listener' and n['metadata']['method_name']=='one')
    site=next(s for s in payload['call_sites'] if s['id']==producer['metadata']['origin_id'])
    identity={'producer-origin':producer['metadata']['origin_id'],'producer-caller':site['caller'],
              'producer-target':site['declared_target'],'listener-origin':listener['metadata']['origin_id']}[role]
    node=next(n for n in payload['nodes'] if n['id']==identity)
    node[field]=({'forged':True} if field=='metadata' else (node.get('line') or 0)+1 if field=='line'
                 else 'test' if field=='scope' else 'CORRUPTED')
    damaged=KnowledgeGraph.from_dict(payload);before=damaged.to_dict(),copy.deepcopy(workspace)
    with pytest.raises(InterfaceProjectionError):
        project_kafka_interfaces(workspace,damaged,source_coverage=coverage)
    assert damaged.to_dict()==before[0] and workspace==before[1]

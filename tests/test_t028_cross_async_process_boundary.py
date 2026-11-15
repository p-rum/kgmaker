"""T028 public pure projection; hand-labelled protocol versus actual compiler evidence."""
from copy import deepcopy
import importlib

import pytest

from kgmaker.process_model import ProcessView
from test_t027_cross_http_process_boundary import process
from test_cross_service_contract_mapping import trusted_protocol_specimen, refresh_handoff
from test_t014_bind_remote_interfaces import project as project_remote


def api(*args, **kwargs):
    module = importlib.import_module('kgmaker.business_process')
    assert hasattr(module, 'project_async_process_boundary'), 'T028 public API is absent'
    return module.project_async_process_boundary(*args, **kwargs)


def local(identity='publisher', context='client-context', service='checkout', *, site='site:publish', handler='handler'):
    value = process(identity, context, service, handler_id=handler).to_dict()
    for node in value['technical_view']['nodes']:
        if node['kind'] == 'trigger': node['attributes']['trigger_kind'] = 'KAFKA'
        if node['id'] == 'local-call': node['attributes']['call_site_ids'] = [site]
    for edge in value['technical_view']['edges']:
        if edge['id'] == 'e2':
            edge['attributes']['call_site'] = site
            edge['original_ids'] = ['e2', site]
    return ProcessView.from_dict(value)


def specimen(*, fanout=False, unknown=False):
    result = trusted_protocol_specimen('KAFKA')
    workspace, graph, docs, captured = result
    doc = next(d for d in docs if d['nodes'])
    source, target = doc['nodes']
    source['original_ids'] = ['site:publish', 'fact:publish']
    source['attributes'].update(origin_id='site:publish', code_fact_id='fact:publish')
    target['original_ids'] = ['handler', 'subscription:one', 'fact:listener']
    target['attributes'].update(origin_id='handler', code_fact_id='fact:listener',
        subscription_id='subscription:one', subscription_logical_id='logical:one')
    if fanout:
        second = deepcopy(target)
        second['id'] = 'consumer-two'
        second['original_ids'] = ['handler-two', 'subscription:two', 'fact:two']
        second['attributes'].update(origin_id='handler-two', code_fact_id='fact:two',
            subscription_id='subscription:two', subscription_logical_id='logical:two', consumer_group='group-two')
        doc['nodes'].append(second)
        release = deepcopy(workspace['remote_mapping']['releases'][1])
        release.update(id='consumer-two-release', interface_id='consumer-two')
        workspace['remote_mapping']['releases'].append(release)
        workspace['remote_mapping']['mappings'].append({'id':'two','transport':'KAFKA',
            'source_release_id':'client-v1','target_release_id':release['id'],'compatibility_id':None})
    if unknown:
        release = deepcopy(workspace['remote_mapping']['releases'][1])
        release.update(id='missing-release', interface_id='missing-consumer')
        workspace['remote_mapping']['releases'].append(release)
        workspace['remote_mapping']['mappings'].append({'id':'missing','transport':'KAFKA',
            'source_release_id':'client-v1','target_release_id':release['id'],'compatibility_id':None})
    refresh_handoff(*result)
    return result


def consumers():
    return [local('consumer-a', 'server-context', 'orders', site='site:a', handler='handler'),
            local('consumer-b', 'server-context', 'orders', site='site:b', handler='handler-two')]


def reaches(view, start, end):
    edges = view.technical_view.edges
    seen = {start}; pending = [start]
    while pending:
        source = pending.pop()
        for edge in edges:
            if edge.source == source and edge.target not in seen:
                seen.add(edge.target); pending.append(edge.target)
    return end in seen


def role(view, name):
    return [n for n in view.steps if n.attributes.get('async_role') == name]


def imported(view, process_id):
    return [n for n in view.steps if n.attributes.get('source_process_id') == process_id]


def test_ac01_fanout_groups_have_real_paths_without_consumer_order():
    result = api(local(), project_remote(specimen(fanout=True)), target_processes=consumers())
    left, right = imported(result, 'consumer-a'), imported(result, 'consumer-b')
    assert left and right
    assert all(reaches(result, 'local-call', node.id) for node in left + right)
    assert not any(reaches(result, a.id, b.id) or reaches(result, b.id, a.id) for a in left for b in right)
    assert {n.attributes['consumer_group'] for n in role(result, 'subscription')} == {'group-one', 'group-two'}
    assert not any(reaches(result, n.id, 'exit') for n in left + right)


def test_ac02_publish_is_not_completed_processing_or_instance_correlation():
    result = api(local(), project_remote(specimen()), target_processes=consumers())
    assert len(role(result, 'publish')) == len(role(result, 'channel')) == len(role(result, 'subscription')) == 1
    assert reaches(result, 'local-call', 'exit')  # unchanged independent local completion
    for node in role(result, 'publish') + role(result, 'subscription'):
        assert node.attributes['delivery'] == 'NOT_OBSERVED'
        assert node.attributes['processing_completion'] == 'UNKNOWN'
        assert node.attributes['instance_correlation'] == 'UNKNOWN'
        assert node.attributes['correlation_evidence_refs'] == []
    assert any(d['code'] == 'ASYNC_INSTANCE_CORRELATION_UNKNOWN' for d in result.technical_view.diagnostics)


def test_ac03_missing_consumer_keeps_every_declared_boundary_and_valid_branch():
    result = api(local(), project_remote(specimen(unknown=True)), target_processes=consumers())
    subscriptions = role(result, 'subscription')
    assert len(subscriptions) == 2
    assert all(reaches(result, 'local-call', n.id) for n in subscriptions)
    assert imported(result, 'consumer-a')
    assert any(n.attributes.get('boundary_reason') == 'ASYNC_REMOTE_TARGET_UNRESOLVED' for n in subscriptions)


def test_ac04_invalid_input_does_not_mutate_or_write(tmp_path, monkeypatch):
    source = local().to_dict(); remote = project_remote(specimen()).to_dict()
    artifact = tmp_path / 'last-valid.json'; artifact.write_text('last-valid')
    before = deepcopy((source, remote)); remote['rules_version'] = 'foreign'
    damaged = deepcopy((source, remote))
    with pytest.raises(ValueError): api(source, remote)
    assert (source, remote) == damaged and artifact.read_text() == 'last-valid'
    remote = before[1]
    import subprocess, socket, builtins
    def forbidden(*args, **kwargs): raise AssertionError('pure projection invoked I/O')
    with monkeypatch.context() as patcher:
        patcher.setattr(builtins, 'open', forbidden)
        patcher.setattr(subprocess, 'Popen', forbidden)
        patcher.setattr(socket, 'socket', forbidden)
        api(source, remote, target_processes=consumers())
    assert (source, remote) == before


@pytest.mark.parametrize('damage', ['stale-edge','stale-source','stale-target','direction','origin','target-context',
    'binding-candidate','binding-transport','target-scope','binding-status','target-version-ambiguity'])
def test_ac05_invalid_membership_retains_boundary_without_import(damage):
    remote = project_remote(specimen()).to_dict()
    edge = remote['edges'][0]
    source = next(n for n in remote['nodes'] if n['id'] == 'client')
    target = next(n for n in remote['nodes'] if n['id'] == 'provider')
    binding = next(n for n in remote['nodes'] if n['kind'] == 'remote_binding')
    if damage == 'stale-edge': edge['freshness'] = 'STALE'
    elif damage == 'stale-source': source['freshness'] = 'STALE'
    elif damage == 'stale-target': target['freshness'] = 'STALE'
    elif damage == 'direction': target['attributes']['direction'] = 'PRODUCER'
    elif damage == 'origin': target['attributes']['origin_id'] = 'unrelated'
    elif damage == 'target-context': target['attributes']['context_id'] = 'foreign'
    elif damage == 'binding-candidate': binding['attributes']['candidates'][0]['target_release_id'] = 'foreign'
    elif damage == 'binding-transport': binding['attributes']['transport'] = 'HTTP'
    elif damage == 'target-scope': target['attributes']['scope'] = 'test'
    elif damage == 'binding-status': binding['resolution_status'] = edge['resolution_status'] = 'AMBIGUOUS'
    elif damage == 'target-version-ambiguity':
        candidate = deepcopy(binding['attributes']['candidates'][0]); candidate['target_release_id'] = 'v2'
        binding['attributes']['candidates'].append(candidate)
    before = deepcopy(remote)
    result = api(local(), remote, target_processes=consumers())
    assert len(role(result, 'subscription')) == 1
    assert not imported(result, 'consumer-a')
    assert reaches(result, 'local-call', role(result, 'subscription')[0].id)
    assert remote == before


@pytest.mark.parametrize('damage', ['scope','service-context','trigger-context','stale-trigger','wrong-entry','duplicate'])
def test_target_process_identity_is_required(damage):
    target = consumers()[0].to_dict()
    if damage == 'scope': target['definition']['context_selection']['services']['orders']['scope'] = 'test'
    elif damage == 'service-context': target['definition']['context_selection']['services']['orders']['contexts'][0]['context_id'] = 'foreign'
    elif damage == 'trigger-context':
        next(n for n in target['technical_view']['nodes'] if n['kind'] == 'trigger')['attributes']['context_ids'] = ['foreign']
        with pytest.raises(ValueError): api(local(), project_remote(specimen()), target_processes=[target])
        return
    elif damage == 'stale-trigger': next(n for n in target['technical_view']['nodes'] if n['kind']=='trigger')['freshness'] = 'STALE'
    elif damage == 'wrong-entry': next(n for n in target['technical_view']['nodes'] if n['kind']=='trigger')['attributes']['entry_symbol_id'] = 'foreign'
    from kgmaker.process_model import ProcessDefinition
    target['technical_view']['context_selection'] = deepcopy(target['definition']['context_selection'])
    target['definition_fingerprint'] = ProcessDefinition.from_dict(target['definition']).content_fingerprint
    targets = [target, target] if damage == 'duplicate' else [target]
    result = api(local(), project_remote(specimen()), target_processes=targets)
    assert not imported(result, 'consumer-a')
    assert len(role(result, 'subscription')) == 1


def test_all_upstream_limits_diagnostics_and_truncation_survive():
    target = consumers()[0].to_dict()
    target['technical_view']['coverage'].update(truncated=True, omitted_ids=['hidden'])
    target['technical_view']['diagnostics'] = [{'code':'TARGET_CFG_LIMIT'}]
    target['technical_view']['limits'] = ['target budget']
    result = api(local(), project_remote(specimen()), target_processes=[target])
    assert result.technical_view.coverage['truncated'] is True
    assert 'target budget' in result.technical_view.limits
    assert any(d['code']=='TARGET_CFG_LIMIT' for d in result.technical_view.diagnostics)
    assert any(row['coverage'].get('omitted_ids') == ['hidden'] for row in result.technical_view.coverage['async_upstream_coverage'])
    assert result.to_dict()['exit_ids'] == ['exit']


@pytest.mark.parametrize('limit', ['max_depth','max_expansions'])
def test_expansion_limit_keeps_reachable_subscription(limit):
    result = api(local(), project_remote(specimen()), target_processes=consumers(), **{limit:0})
    assert not imported(result, 'consumer-a')
    assert reaches(result, 'local-call', role(result, 'subscription')[0].id)
    assert result.technical_view.coverage['truncated'] is True


def test_actual_expanded_callee_exception_cannot_initiate_publish():
    source = local().to_dict(); view = source['technical_view']
    for identity, kind in [('callee-entry','entry'),('callee-exit','exit'),('callee-error','exceptional_exit'),('failure','exceptional_exit')]:
        clone = deepcopy(view['nodes'][0]); clone.update(id=identity,kind=kind)
        clone['attributes'] = {'scope':'production','context_ids':['client-context']}
        view['nodes'].append(clone)
    witness = next(e for e in view['edges'] if e['id']=='e2'); view['edges'].remove(witness)
    for identity, start, end, relation in [('call','local-call','callee-entry','call'),
        ('body','callee-entry','callee-exit','normal'),('throw','callee-entry','callee-error','exception'),
        ('return','callee-exit','exit','returns_to'),('error','callee-error','failure','exception')]:
        e = deepcopy(witness); e.update(id=identity,source=start,target=end,relation=relation)
        e['attributes']['caller_block']='local-call'; view['edges'].append(e)
    source['exit_ids'].append('failure')
    result = api(source, project_remote(specimen()), target_processes=consumers())
    assert not reaches(result, 'callee-error', 'exit')
    assert not any(reaches(result, 'callee-error', n.id) for n in role(result, 'publish'))
    assert reaches(result, 'callee-error', 'failure')


def test_topic_match_without_remote_declaration_never_expands_consumer():
    inputs = specimen(); inputs[0]['remote_mapping']['mappings'] = []
    refresh_handoff(*inputs)
    result = api(local(), project_remote(inputs), target_processes=consumers())
    assert len(role(result, 'subscription')) == 1 and not imported(result, 'consumer-a')
    assert role(result, 'subscription')[0].attributes['boundary_reason']=='ASYNC_REMOTE_TARGET_UNRESOLVED'


def loop_specimen():
    result = specimen(); workspace, graph, docs, captured = result
    doc = next(d for d in docs if d['nodes'])
    producer = deepcopy(doc['nodes'][0]); producer.update(id='loop-producer', owner_id='service:orders')
    producer['original_ids'] = ['site:a', 'fact:loop']
    producer['attributes'].update(service_id='orders',context_id='server-context',origin_id='site:a',code_fact_id='fact:loop')
    consumer = deepcopy(doc['nodes'][1]); consumer.update(id='root-consumer', owner_id='service:checkout')
    consumer['original_ids'] = ['handler', 'subscription:root', 'fact:root']
    consumer['attributes'].update(service_id='checkout',context_id='client-context',origin_id='handler',
        code_fact_id='fact:root',subscription_id='subscription:root',subscription_logical_id='logical:root')
    doc['nodes'].extend([producer,consumer])
    source = deepcopy(workspace['remote_mapping']['releases'][1]); source.update(id='loop-source',interface_id=producer['id'])
    target = deepcopy(workspace['remote_mapping']['releases'][0]); target.update(id='loop-target',interface_id=consumer['id'])
    workspace['remote_mapping']['releases'].extend([source,target])
    workspace['remote_mapping']['mappings'].append({'id':'loop','transport':'KAFKA',
        'source_release_id':'loop-source','target_release_id':'loop-target','compatibility_id':None})
    refresh_handoff(*result)
    return result


def test_async_loop_preserves_cycle_boundary_without_unbounded_copies():
    source = local(); result = api(source, project_remote(loop_specimen()), target_processes=[source,*consumers()])
    loops = [n for n in role(result, 'subscription') if n.attributes['boundary_reason']=='ASYNC_LOOP']
    assert len(loops) == 1 and reaches(result, 'local-call', loops[0].id)
    assert len(role(result, 'publish')) == 2
    assert result.technical_view.coverage['truncated'] is True
    assert not any(reaches(result, n.id, 'exit') for n in imported(result, 'consumer-a'))


@pytest.fixture(scope='module', params=['k1','k2'])
def actual_pipeline(tmp_path_factory, request):
    """Explicit actual JDK/Spring Kafka capture; no compiler-shaped hand-labelled CFG."""
    import json
    from pathlib import Path
    from kgmaker.inspection import inspect_jvm
    from kgmaker.model import KnowledgeGraph
    from kgmaker.workspace import load_workspace, snapshot_workspace
    from kgmaker.remote_mapping import capture_remote_mapping_inputs
    from kgmaker.process_triggers import discover_process_triggers
    from kgmaker.process_paths import build_local_process
    from test_kafka_bindings import kafka_workspace
    from test_kafka_code_bindings import extra_api_jars
    from test_t024_discover_process_triggers import actual_prerequisites
    from test_cross_service_contract_mapping import _declare_real_pair
    backend = request.param
    root, manifest, document = kafka_workspace.__wrapped__(tmp_path_factory.mktemp('t028-'+backend))
    jars = actual_prerequisites(backend) + extra_api_jars()
    bodies = {
        'producer': '''package demo;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
public class Code { private KafkaTemplate<String,String> template;
 @Scheduled(fixedRate=1000) public void publish() { template.send("orders-blue", "payload"); } }
''',
        'consumer': '''package demo;
import org.springframework.kafka.annotation.KafkaListener;
public class Code {
 @KafkaListener(id="one",topics={"orders-blue"},groupId="group-one") public void one(String value) { consume(value); }
 @KafkaListener(id="two",topics={"orders-blue"},groupId="group-two") public void two(String value) { consume(value); }
 private void consume(String value) { if (value == null) throw new IllegalArgumentException(); }
}
'''}
    config = root/'consumer/src/main/resources/application.properties'
    config.write_text(config.read_text()+'spring.cloud.stream.bindings.orders-in-0.group=group-one\n'
        'spring.cloud.stream.bindings.second-in-0.destination=orders-blue\n'
        'spring.cloud.stream.bindings.second-in-0.binder=alpha\n'
        'spring.cloud.stream.bindings.second-in-0.group=group-two\n')
    facts = {}
    for repo, body in bodies.items():
        path = root/repo/'src/main/java/demo/Code.java'; path.parent.mkdir(parents=True); path.write_text(body)
        response = inspect_jvm(root/repo, home=Path(__file__).resolve().parents[1]/'workers',
            kotlin_backend=backend, repo_id='local', classpath=jars, build_context={'spring_profiles':['blue']})
        assert not any('.err.' in str(d.get('code','')) for d in response['diagnostics'])
        graph = KnowledgeGraph.from_dict(response['graph'])
        facts[repo] = (response['context']['id'], {n.metadata['method_name']:n for n in graph.nodes
            if n.kind in {'kafka_code_listener','kafka_code_producer'}})
    second = deepcopy(document['kafka_bindings']['bindings'][1]); second.update(id='second-group',binding='second-in-0')
    document['kafka_bindings']['bindings'].append(second); document['kafka_bindings']['schema_version']=2
    for binding in document['kafka_bindings']['bindings']:
        context, by_method = facts[binding['repo_id']]
        fact = by_method['publish' if binding['repo_id']=='producer' else 'two' if binding['id']=='second-group' else 'one']
        binding['context_id']=context
        binding['code_ref']={'kind':'send' if binding['repo_id']=='producer' else 'listener',
            'id':fact.metadata['origin_id'],'context_id':context,'source_file':fact.metadata['source_file'],
            'sha256':fact.metadata['source_sha256']}
    manifest.write_text(json.dumps(document))
    workspace=load_workspace(manifest); _,coverage,_,graph,_=snapshot_workspace(manifest)
    workspace,graph,captured=_declare_real_pair(workspace,graph,coverage,'KAFKA')
    first_target_id = workspace['remote_mapping']['releases'][1]['interface_id']
    target = next(n for d in captured['canonical_interfaces'] for n in d['nodes']
        if n['kind']=='kafka_interface' and n['attributes'].get('consumer_group') in {'group-one','group-two'}
        and n['id'] != first_target_id)
    document=json.loads(manifest.read_text()); release=deepcopy(document['remote_mapping']['releases'][1])
    release.update(id='second-release',interface_id=target['id'])
    document['remote_mapping']['releases'].append(release)
    document['remote_mapping']['mappings'].append({'id':'second-map','transport':'KAFKA',
        'source_release_id':'source-release','target_release_id':'second-release','compatibility_id':None})
    manifest.write_text(json.dumps(document)); workspace=load_workspace(manifest)
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    captured=capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    from kgmaker.remote_interfaces import project_remote_interfaces
    remote=project_remote_interfaces(workspace,graph,captured['canonical_interfaces'],captured=captured)
    inventory=discover_process_triggers(workspace,graph,source_coverage=coverage)
    processes={}
    for trigger in inventory.nodes:
        name = next(n.name for n in graph.nodes if n.id == trigger.attributes['entry_symbol_id'])
        processes[name]=build_local_process(graph,inventory,trigger.id,process_id='actual:'+name)
    assert {'publish','one','two'} <= set(processes), inventory.to_dict()
    return processes, remote, captured


def test_actual_t012_t014_t025_t028_fanout_paths_and_exact_identity(actual_pipeline):
    processes, remote, captured = actual_pipeline
    before = deepcopy((remote.to_dict(),{k:p.to_dict() for k,p in processes.items()}))
    result = api(processes['publish'],remote,target_processes=[processes['one'],processes['two']])
    left, right = imported(result,'actual:one'), imported(result,'actual:two')
    assert left and right
    start = result.to_dict()['entry_ids'][0]
    for pid in ['actual:one','actual:two']:
        trigger = next(n for n in imported(result,pid) if n.kind=='trigger')
        assert reaches(result,start,trigger.id)
        exits = [n for n in imported(result,pid) if n.kind=='exit']
        assert exits and any(reaches(result,trigger.id,n.id) for n in exits)
    assert not any(reaches(result,a.id,b.id) or reaches(result,b.id,a.id) for a in left for b in right)
    assert {n.attributes['consumer_group'] for n in role(result,'subscription')} == {'group-one','group-two'}
    for node in role(result,'subscription'):
        assert node.attributes['subscription_id'] in node.original_ids
        assert node.attributes['instance_correlation']=='UNKNOWN'
    assert (remote.to_dict(),{k:p.to_dict() for k,p in processes.items()}) == before


def test_identity_metadata_transport_preserves_originals_and_rejects_forged_ids():
    inputs = specimen(); remote = project_remote(inputs)
    for old in next(d for d in inputs[2] if d['nodes'])['nodes']:
        new = next(n for n in remote.nodes if n.id==old['id'])
        assert set(new.original_ids)==set(old['original_ids']) and list(new.evidence_refs)==old['evidence_refs']
        for key in ['origin_id','subscription_id','subscription_logical_id']:
            if key in old['attributes']: assert new.attributes[key]==old['attributes'][key]
    target = next(d for d in inputs[2] if d['nodes'])['nodes'][1]
    target['attributes']['subscription_id']='forged'
    refresh_handoff(*inputs)
    before=deepcopy((inputs[0],inputs[1].to_dict(),inputs[2:]))
    with pytest.raises(ValueError,match='REMOTE_VIEW_KAFKA_ORIGINAL_ID_MISMATCH'): project_remote(inputs)
    assert (inputs[0],inputs[1].to_dict(),inputs[2:])==before


def test_provenance_and_original_local_paths_are_preserved_without_uplift():
    source=local(); target=consumers()[0]; remote=project_remote(specimen())
    result=api(source,remote,target_processes=[target])
    document=result.to_dict()['technical_view']
    assert all(n in document['nodes'] for n in source.to_dict()['technical_view']['nodes'])
    assert all(e in document['edges'] for e in source.to_dict()['technical_view']['edges'])
    assert all(p in document['provenance'] for p in target.to_dict()['technical_view']['provenance'])
    assert all(n.freshness=='UNKNOWN' and n.resolution_status=='UNRESOLVED' for n in role(result,'subscription'))
    assert result.technical_status=='PARTIAL'


def test_permutations_preserve_fingerprint_including_expansion_budget():
    remote=project_remote(specimen(fanout=True)).to_dict(); targets=consumers()
    first=api(local(),remote,target_processes=targets,max_expansions=1)
    remote['nodes'].reverse();remote['edges'].reverse();remote['provenance'].reverse()
    second=api(local(),remote,target_processes=list(reversed(targets)),max_expansions=1)
    assert first.to_json()==second.to_json()
    assert len(role(first,'subscription'))==2 and first.technical_view.coverage['truncated']


def test_blocked_target_and_remote_upstream_truncation_are_not_dropped():
    target=consumers()[0].to_dict();target['technical_view']['diagnostics']=[{'code':'BODY_TRUNCATED'}]
    target['technical_view']['limits']=['opaque body budget'];target['technical_view']['coverage']['truncated']=True
    remote=project_remote(specimen()).to_dict();remote['diagnostics'].append({'code':'REMOTE_UPSTREAM_COVERAGE','truncated':True})
    result=api(local(),remote,target_processes=[target],max_depth=0)
    assert result.technical_view.coverage['truncated']
    assert any(d['code']=='BODY_TRUNCATED' for d in result.technical_view.diagnostics)
    assert 'opaque body budget' in result.technical_view.limits
    assert not imported(result,'consumer-a')


@pytest.mark.parametrize('kwargs',[{'max_depth':-1},{'max_depth':True},{'max_expansions':129},{'target_processes':{}}])
def test_invalid_budgets_are_rejected_without_mutation(kwargs):
    source=local().to_dict();remote=project_remote(specimen()).to_dict();before=deepcopy((source,remote))
    with pytest.raises(ValueError):api(source,remote,**kwargs)
    assert (source,remote)==before


def test_cycle_rejected_before_copy_and_terminal_site_does_not_publish():
    remote=project_remote(specimen()).to_dict();remote['metadata']=remote
    with pytest.raises(ValueError):api(local(),remote)
    assert remote['metadata'] is remote
    source=local().to_dict()
    for node in source['technical_view']['nodes']:
        if node['id']=='local-call': node['kind']='exceptional_exit'
    result=api(source,project_remote(specimen()),target_processes=consumers())
    assert not role(result,'publish')


def test_duplicate_declared_membership_is_not_two_valid_consumers():
    inputs=specimen();mapping=deepcopy(inputs[0]['remote_mapping']['mappings'][0]);mapping['id']='duplicate'
    inputs[0]['remote_mapping']['mappings'].append(mapping);refresh_handoff(*inputs)
    result=api(local(),project_remote(inputs),target_processes=consumers())
    assert len(role(result,'subscription'))==2
    assert not imported(result,'consumer-a')
    assert all(n.attributes['boundary_reason']=='ASYNC_MEMBERSHIP_SELECTOR_CONFLICT' for n in role(result,'subscription'))


def test_legacy_t014_original_ids_join_without_new_metadata():
    remote=project_remote(specimen()).to_dict()
    for node in remote['nodes']:
        for key in ['origin_id','subscription_id','subscription_logical_id']:
            node['attributes'].pop(key,None)
    result=api(local(),remote,target_processes=consumers())
    assert imported(result,'consumer-a')
    assert 'subscription:one' in role(result,'subscription')[0].original_ids


def test_same_group_consumers_are_potential_alternatives_without_order():
    inputs=specimen(fanout=True)
    for node in next(d for d in inputs[2] if d['nodes'])['nodes']:
        if node['attributes']['direction']=='CONSUMER':node['attributes']['consumer_group']='shared-group'
    refresh_handoff(*inputs)
    result=api(local(),project_remote(inputs),target_processes=consumers())
    left,right=imported(result,'consumer-a'),imported(result,'consumer-b')
    assert left and right and len(role(result,'subscription'))==2
    assert not any(reaches(result,a.id,b.id) or reaches(result,b.id,a.id) for a in left for b in right)
    assert all(n.attributes['delivery']=='NOT_OBSERVED' for n in role(result,'subscription'))


def test_target_collection_and_combined_payload_budget_precede_copy():
    target=consumers()[0];source=local();remote=project_remote(specimen())
    with pytest.raises(ValueError,match='ASYNC_INVALID_LIMITS_OR_TARGETS'):
        api(source,remote,target_processes=[target]*129)
    oversized=target.to_dict();oversized['technical_view']['limits']=['x'*300000]
    with pytest.raises(ValueError,match='Input text budget exceeded'):
        api(source,remote,target_processes=[oversized]*128)
    assert oversized['technical_view']['limits']==['x'*300000]


def test_kafka_identity_allowlist_does_not_change_http_extra_attributes():
    inputs=trusted_protocol_specimen('HTTP')
    for doc in inputs[2]:
        for node in doc['nodes']:
            node['attributes'].update(origin_id='http-opaque-extra',subscription_id='not-kafka',subscription_logical_id='opaque')
    refresh_handoff(*inputs)
    remote=project_remote(inputs)
    assert all(not {'origin_id','subscription_id','subscription_logical_id'} & set(n.attributes)
        for n in remote.nodes if n.kind=='http_interface')


def remote_proof_records(view):
    return [p.get('original_provenance', p) for p in view.technical_view.provenance]


@pytest.mark.parametrize('subject', ['client', 'provider', 'binding'])
@pytest.mark.parametrize('damage', ['stale', 'contradicting', 'foreign-scope'])
def test_referenced_endpoint_and_binding_proofs_gate_expansion_and_survive(subject, damage):
    remote = project_remote(specimen()).to_dict()
    node = next(n for n in remote['nodes'] if n['kind']=='remote_binding') if subject=='binding' else next(n for n in remote['nodes'] if n['id']==subject)
    if subject=='binding':
        proof = next(p for p in remote['provenance'] if p['id'] in node['evidence_refs'])
    else:
        proof = {'id':'endpoint-proof:'+subject,'evidence_kind':'SYMBOL_RESOLVED',
            'freshness':'CURRENT','polarity':'SUPPORTING','scope':'production',
            'context_ids':[node['attributes']['context_id']]}
        remote['provenance'].append(proof)
        node.update(evidence_refs=[proof['id']], evidence_kinds=['SYMBOL_RESOLVED'],
            supporting_refs=[proof['id']], freshness='UNKNOWN')
        # Keep the candidate's endpoint reference set coherent; prove that the
        # proof itself is rejected, not merely an obsolete refs list.
        binding = next(n for n in remote['nodes'] if n['kind']=='remote_binding')
        binding['attributes']['candidates'][0]['evidence_refs']=[proof['id']]
        remote['edges'][0]['attributes']['evidence_refs']=[proof['id']]
        remote['edges'][0]['attributes']['original_evidence_refs']=[proof['id']]
    if damage=='stale': proof['freshness']='STALE'
    elif damage=='contradicting':
        proof['polarity']='CONTRADICTING'
        node.update(supporting_refs=[],unknown_refs=[],contradicting_refs=[proof['id']])
    else: proof['scope']='test'
    before=deepcopy(remote)
    result=api(local(),remote,target_processes=consumers())
    assert not imported(result,'consumer-a') and remote==before
    assert len(role(result,'subscription'))==1
    assert reaches(result,'local-call',role(result,'subscription')[0].id)
    assert proof in remote_proof_records(result)
    assert 'test' not in {p['scope'] for p in result.technical_view.provenance}
    assert result.technical_status=='PARTIAL'


@pytest.mark.parametrize('damage',['mapping-id','capture-id','kind','missing-proof'])
def test_binding_declaration_authority_must_match_membership(damage):
    remote=project_remote(specimen()).to_dict()
    binding=next(n for n in remote['nodes'] if n['kind']=='remote_binding')
    proof=next(p for p in remote['provenance'] if p['id'] in binding['evidence_refs'])
    if damage=='mapping-id': proof['mapping_ids']=['unrelated']
    elif damage=='capture-id': proof['capture_id']='f'*64
    elif damage=='kind': proof['evidence_kind']='SYMBOL_RESOLVED';binding['evidence_kinds']=['SYMBOL_RESOLVED']
    else: binding.update(evidence_refs=[],unknown_refs=[],evidence_kinds=[])
    result=api(local(),remote,target_processes=consumers())
    assert not imported(result,'consumer-a') and len(role(result,'subscription'))==1
    if damage!='missing-proof': assert proof in remote_proof_records(result)


def aliased_release_specimen():
    inputs=specimen(); workspace=inputs[0]
    source=deepcopy(workspace['remote_mapping']['releases'][0]);source['id']='client-other'
    target=deepcopy(workspace['remote_mapping']['releases'][1]);target['id']='provider-other'
    workspace['remote_mapping']['releases'].extend([source,target])
    workspace['remote_mapping']['mappings'].append({'id':'other','transport':'KAFKA',
        'source_release_id':source['id'],'target_release_id':target['id'],'compatibility_id':None})
    refresh_handoff(*inputs)
    return inputs


def test_release_aliases_across_bindings_preserve_conflicts_without_duplicate_consumer_paths():
    remote=project_remote(aliased_release_specimen()); before=remote.to_json()
    assert [n.resolution_status for n in remote.nodes if n.kind=='remote_binding']==['RESOLVED','RESOLVED']
    result=api(local(),remote,target_processes=consumers())
    subscriptions=role(result,'subscription')
    assert len(subscriptions)==2 and all(reaches(result,'local-call',n.id) for n in subscriptions)
    assert not imported(result,'consumer-a') and remote.to_json()==before
    assert all(n.attributes['boundary_reason']=='ASYNC_MEMBERSHIP_SELECTOR_CONFLICT' for n in subscriptions)
    assert len({n.attributes['binding_id'] for n in subscriptions})==2
    assert any(d['code']=='ASYNC_MEMBERSHIP_SELECTOR_CONFLICT' for d in result.technical_view.diagnostics)
    assert result.technical_view.coverage['async_expansion_count']==0


def test_distinct_versioned_endpoints_across_bindings_keep_independent_paths():
    inputs=specimen(fanout=True);workspace,_,documents,_=inputs
    source=deepcopy(workspace['remote_mapping']['releases'][0]);source['id']='client-second'
    workspace['remote_mapping']['releases'].append(source)
    versioned=next(n for d in documents for n in d['nodes'] if n['id']=='consumer-two')
    versioned['attributes']['message_contract_ref']['release']='v2'
    release=next(r for r in workspace['remote_mapping']['releases'] if r['interface_id']=='consumer-two')
    release['release']='v2'
    mapping=next(m for m in workspace['remote_mapping']['mappings'] if m['id']=='two')
    mapping.update(source_release_id=source['id'],compatibility_id='explicit-v2')
    workspace['remote_mapping']['compatibilities']=[{'id':'explicit-v2','source_release_id':source['id'],
        'target_release_id':release['id'],'assertion':'DECLARED_OPERATION_COMPATIBILITY'}]
    refresh_handoff(*inputs)
    result=api(local(),project_remote(inputs),target_processes=consumers())
    left,right=imported(result,'consumer-a'),imported(result,'consumer-b')
    assert left and right and len(role(result,'subscription'))==2
    assert not any(reaches(result,a.id,b.id) or reaches(result,b.id,a.id) for a in left for b in right)
    assert not any(d['code']=='ASYNC_MEMBERSHIP_SELECTOR_CONFLICT' for d in result.technical_view.diagnostics)


def test_unknown_scopeless_framework_proof_is_retained_as_reference_without_uplift():
    remote=project_remote(specimen()).to_dict();source=next(n for n in remote['nodes'] if n['id']=='client')
    proof={'id':'raw-framework','evidence_kind':'FRAMEWORK_DERIVED','freshness':'UNKNOWN',
        'polarity':'SUPPORTING','context_ids':['virtual:kafka','client-context'],'original_payload_hash':'a'*64}
    remote['provenance'].append(proof)
    source.update(evidence_refs=[proof['id']],evidence_kinds=['FRAMEWORK_DERIVED'],supporting_refs=[proof['id']],freshness='UNKNOWN')
    binding=next(n for n in remote['nodes'] if n['kind']=='remote_binding')
    binding['attributes']['candidates'][0]['evidence_refs']=[proof['id']]
    remote['edges'][0]['attributes'].update(evidence_refs=[proof['id']],original_evidence_refs=[proof['id']])
    result=api(local(),remote,target_processes=consumers())
    assert imported(result,'consumer-a') and proof in remote_proof_records(result)
    envelopes=[p for p in result.technical_view.provenance if p.get('original_id')==proof['id']]
    assert envelopes and all(p['authority']=='PROVENANCE_REFERENCE_ONLY' and p['evidence_kind']=='UNKNOWN'
        and p['freshness']=='UNKNOWN' and p['polarity']=='UNKNOWN' and p['original_provenance']==proof for p in envelopes)
    assert 'virtual:kafka' not in result.definition.to_dict()['context_ids']
    assert any(d['code']=='ASYNC_REMOTE_PROOF_REFERENCE_ONLY' and d['original_proof_id']==proof['id']
        for d in result.technical_view.diagnostics)
    assert result.technical_status=='PARTIAL'
    # A previously constructed process-scope envelope cannot make its changed
    # raw authority current on the next projection.
    proof['freshness']='STALE'
    refused=api(local(),remote,target_processes=consumers())
    assert not imported(refused,'consumer-a') and proof in remote_proof_records(refused)

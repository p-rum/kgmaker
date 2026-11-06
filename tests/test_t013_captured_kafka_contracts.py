"""T013 Kafka revision projection over the same explicit actual T012 setup."""
from pathlib import Path

from test_t012_catalog_kafka_interfaces import capture
from kgmaker.interfaces import project_kafka_interfaces,capture_interface_contracts,attach_interface_contracts
from kgmaker.workspace import snapshot_workspace,load_workspace


def attached(workspace,graph,coverage):
    catalogue=project_kafka_interfaces(workspace,graph,source_coverage=coverage)
    return attach_interface_contracts(workspace,graph,catalogue,captured=capture_interface_contracts(workspace,graph))


def test_actual_kafka_contract_revisions_keep_realm_group_logical_identity(capture):
    workspace,graph,coverage=capture
    first=attached(workspace,graph,coverage)
    subscriptions=[n for n in first.nodes if n.kind=='kafka_interface' and n.attributes.get('subscription_id')]
    assert len(subscriptions)==2
    assert {n.attributes['broker_realm'] for n in subscriptions}=={'cluster-a','cluster-b'}
    assert {n.attributes['consumer_group'] for n in subscriptions}=={'group-one','group-two'}
    assert all(n.attributes['contract_bindings'][0]['status']=='BOUND_DECLARATION' for n in subscriptions)
    revisions={n.attributes['logical_id']:n.attributes['contract_bindings'][0]['revision_fingerprint'] for n in subscriptions}
    # Even an actual canonical class declaration is not a message payload proof.
    from dataclasses import replace
    catalogue=project_kafka_interfaces(workspace,graph,source_coverage=coverage)
    canonical=next(s for s in graph.symbols if s.get('kind')=='class' and s.get('owner')=='demo.Code' and s.get('path','').startswith('@producer/'))
    changed=replace(catalogue,nodes=tuple(replace(n,attributes={**dict(n.attributes),'message_type_id':canonical['id']}) if n.kind=='kafka_interface' and n.attributes.get('direction')=='PRODUCER' else n for n in catalogue.nodes))
    type_result=attach_interface_contracts(workspace,graph,changed,captured=capture_interface_contracts(workspace,graph))
    producer=next(n for n in type_result.nodes if n.kind=='kafka_interface' and n.attributes.get('direction')=='PRODUCER')
    assert producer.attributes['message_type_id'] is None
    assert producer.attributes['contract_bindings'][0]['status']=='BOUND_DECLARATION'
    assert any(d.get('code')=='TYPE_REFERENCE_UNKNOWN' and d.get('reason')=='PAYLOAD_TYPE_PROOF_UNAVAILABLE' for d in type_result.diagnostics)

    schema=next(Path(r['_root'])/'Order.json' for r in workspace['repositories'] if r['id']=='schemas')
    before=schema.read_bytes();schema.write_bytes(before.replace(b'"Order"',b'"Other"'))
    assert len(schema.read_bytes())==len(before) and schema.read_bytes()!=before
    manifest=Path(workspace['_manifest_path']);workspace=load_workspace(manifest)
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    second=attached(workspace,graph,coverage)
    current=[n for n in second.nodes if n.kind=='kafka_interface' and n.attributes.get('subscription_id')]
    assert {n.attributes['logical_id'] for n in current}==set(revisions)
    assert all(n.attributes['contract_bindings'][0]['revision_fingerprint']!=revisions[n.attributes['logical_id']] for n in current)
    assert all(n.attributes['payload_compatibility']=='UNKNOWN' for n in current)
    # The regex code occurrence has no proved message schema or broker binding.
    regex=next(n for n in second.nodes if n.kind=='kafka_interface' and n.attributes.get('subscription_kind')=='REGEX')
    assert regex.attributes['contract_bindings']==[]
    assert any(d.get('code')=='MESSAGE_SCHEMA_BINDING_UNKNOWN' and d.get('interface_id')==regex.id for d in second.diagnostics)
    schema.unlink()
    _,coverage,_,graph,_=snapshot_workspace(manifest)
    missing=attached(load_workspace(manifest),graph,coverage)
    assert all(b['status']!='BOUND_DECLARATION' for n in missing.nodes for b in n.attributes.get('contract_bindings',[]))
    assert any(d.get('code')=='MESSAGE_SCHEMA_BINDING_UNKNOWN' for d in missing.diagnostics)

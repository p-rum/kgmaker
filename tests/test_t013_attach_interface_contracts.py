"""Public attachment over explicit real contract/generated files; no generator."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.interfaces import project_http_providers
from kgmaker.workspace import load_workspace,snapshot_workspace


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def fixture(tmp_path):
    backend=tmp_path/'backend';client=tmp_path/'client'
    (backend/'src/main/resources').mkdir(parents=True);(client/'src').mkdir(parents=True)
    contract=backend/'src/main/resources/openapi.json'
    contract.write_text(json.dumps({'openapi':'3.0.3','info':{'title':'Orders','version':'v1'},
        'paths':{'/orders':{'post':{'operationId':'submit',
            'requestBody':{'content':{'application/json':{'schema':{'$ref':'#/components/schemas/Order'}}}},
            'responses':{'200':{'content':{'application/json':{'schema':{'$ref':'#/components/schemas/Order'}}}}}}}},
        'components':{'schemas':{'Order':{'type':'object','properties':{'id':{'type':'string'}}}}}}))
    (backend/'src/main/java').mkdir(parents=True)
    (backend/'src/main/java/Order.java').write_text('class Order { String id; }')
    generated=client/'src/api.generated.ts';generated.write_text('export interface Order { id: string; }\n')
    metadata=client/'generation.json'
    metadata.write_text(json.dumps({'source_contract':{'repo_id':'backend','path':'src/main/resources/openapi.json','sha256':sha(contract)},
        'generated_files':['src/api.generated.ts']}))
    manifest=tmp_path/'workspace.json'
    manifest.write_text(json.dumps({'schema_version':1,'workspace_id':'contract-fixture',
        'repositories':[{'id':'backend','role':'backend','path':'backend'},{'id':'client','role':'frontend','path':'client'}],
        'services':[{'id':'orders','backend_repo':'backend','frontend_repos':['client'],'test_repos':[],
            'contract':{'repo_id':'backend','path':'src/main/resources/openapi.json'},
            'generated_clients':[{'repo_id':'client','path':'src/api.generated.ts','metadata_path':'generation.json','consumers':[]}]}],
        'service_ownership':{'schema_version':1,'services':[{'id':'orders',
            'roots':[{'repo_id':'backend','path':'src'},{'repo_id':'client','path':'src'}],
            'modules':[],'external_systems':[]}]}}))
    return manifest,contract,generated,metadata


def inputs(fixture):
    manifest,_,_,_=fixture
    workspace=load_workspace(manifest);_,coverage,_,graph,_=snapshot_workspace(manifest)
    catalog=project_http_providers(workspace,graph,source_coverage=coverage)
    assert any(n.kind=='http_interface' for n in catalog.nodes)
    return workspace,graph,catalog


def capture(workspace,graph):
    from kgmaker.interfaces import capture_interface_contracts
    return capture_interface_contracts(workspace,graph)


def attach(workspace,graph,catalog,captured):
    from kgmaker.interfaces import attach_interface_contracts
    return attach_interface_contracts(workspace,graph,catalog,captured=captured)


def test_ac01_explicit_operation_versions_preserve_logical_interface(fixture):
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    first=attach(workspace,graph,catalog,captured)
    node=next(n for n in first.nodes if n.kind=='http_interface')
    binding=node.attributes['contract_bindings'][0]
    assert binding['status']=='BOUND_DECLARATION' and binding['operation_pointer']=='#/paths/~1orders/post'
    assert binding['revision']=='v1' and binding['role']=='PROVIDER_DECLARATION'
    old_ids={n.id for n in catalog.nodes};assert old_ids.issubset({n.id for n in first.nodes})
    contract=fixture[1];contract.write_text(contract.read_text().replace('"v1"','"v2"'))
    workspace,graph,catalog=inputs(fixture)
    second=attach(workspace,graph,catalog,capture(workspace,graph))
    new=next(n for n in second.nodes if n.kind=='http_interface')
    assert new.attributes['logical_id']==node.attributes['logical_id']
    assert new.attributes['contract_bindings'][0]['revision_fingerprint']!=binding['revision_fingerprint']


def test_ac02_roles_and_equal_dto_names_do_not_prove_compatibility(fixture):
    workspace,graph,catalog=inputs(fixture);result=attach(workspace,graph,catalog,capture(workspace,graph))
    provider=next(n for n in result.nodes if n.kind=='http_interface')
    generated=next(n for n in result.nodes if n.kind=='generated_client')
    assert provider.attributes['contract_bindings'][0]['role']=='PROVIDER_DECLARATION'
    assert generated.attributes['contract_bindings'][0]['role']=='CLIENT_EXPECTATION'
    assert generated.attributes['contract_bindings'][0]['status']=='BOUND_DECLARATION'
    assert provider.attributes['payload_compatibility']=='UNKNOWN'
    assert generated.attributes['payload_compatibility']=='UNKNOWN'
    assert provider.attributes.get('request_type_id') is None
    assert 'Order.java' not in json.dumps(provider.attributes['contract_bindings'])


def test_ac03_stale_generated_origin_survives_contract_change(fixture):
    workspace,graph,catalog=inputs(fixture);initial=attach(workspace,graph,catalog,capture(workspace,graph))
    client=next(n for n in initial.nodes if n.kind=='generated_client')
    origin=copy.deepcopy(client.attributes['generation_origin'])
    contract=fixture[1];contract.write_text(contract.read_text().replace('"v1"','"v2"'))
    workspace,graph,catalog=inputs(fixture)
    assert not any(n.kind=='generated_client' for n in graph.nodes) # existing legacy behavior
    result=attach(workspace,graph,catalog,capture(workspace,graph))
    stale=next(n for n in result.nodes if n.kind=='generated_client')
    assert stale.id==client.id and stale.attributes['generation_origin']==origin
    assert stale.attributes['contract_bindings'][0]['status']=='STALE'
    assert any(d.get('code')=='GENERATED_CONTRACT_STALE' for d in result.diagnostics)


def test_ac04_offline_inputs_and_files_are_immutable(fixture):
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    before=copy.deepcopy(workspace),graph.to_dict(),catalog.to_dict(),copy.deepcopy(captured)
    paths=[p for root in [fixture[1].parents[3],fixture[2].parents[1]] for p in root.rglob('*') if p.is_file()]
    hashes={str(p):sha(p) for p in paths}
    with patch('subprocess.Popen',side_effect=AssertionError('implicit process')),patch('socket.socket',side_effect=AssertionError('network')):
        result=attach(workspace,graph,catalog,captured)
    assert (workspace,graph.to_dict(),catalog.to_dict(),captured)==before
    assert hashes=={p:sha(Path(p)) for p in hashes}
    assert result.kind=='interfaces'


@pytest.mark.parametrize('file_index',[1,2,3])
def test_ac04_capture_to_projection_mutation_never_repairs_hashes(fixture,file_index):
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    path=fixture[file_index];path.write_bytes(path.read_bytes()+b' ')
    before=copy.deepcopy(captured),catalog.to_dict(),graph.to_dict()
    result=attach(workspace,graph,catalog,captured)
    clients=[n for n in result.nodes if n.kind=='generated_client']
    assert any(b['status']=='STALE' for n in result.nodes for b in n.attributes.get('contract_bindings',[]))
    assert (captured,catalog.to_dict(),graph.to_dict())==before


def test_capture_version_and_unapproved_file_fail_closed(fixture):
    from kgmaker.interfaces import InterfaceProjectionError
    from kgmaker.analysis_model import digest
    workspace,graph,catalog=inputs(fixture);original=capture(workspace,graph)
    for kind in ['version','extra-file']:
        damaged=copy.deepcopy(original)
        if kind=='version':damaged['schema_version']=2
        else:damaged['files']['@backend/unapproved.json']={'repo_id':'backend','path':'unapproved.json','status':'UNKNOWN'}
        damaged['capture_id']=digest({k:v for k,v in damaged.items() if k!='capture_id'})
        before=copy.deepcopy(damaged),graph.to_dict(),catalog.to_dict()
        with pytest.raises(InterfaceProjectionError):attach(workspace,graph,catalog,damaged)
        assert (damaged,graph.to_dict(),catalog.to_dict())==before


def test_captured_document_cannot_be_repaired_by_copying_raw_hash(fixture):
    from kgmaker.analysis_model import digest
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    record=captured['files']['@backend/src/main/resources/openapi.json']
    record['document']['info']['version']='forged'
    captured['capture_id']=digest({k:v for k,v in captured.items() if k!='capture_id'})
    before=copy.deepcopy(captured)
    result=attach(workspace,graph,catalog,captured)
    assert all(b['status']!='BOUND_DECLARATION' for n in result.nodes for b in n.attributes.get('contract_bindings',[]))
    assert captured==before


def test_external_schema_reference_is_not_fetched_or_bound(fixture):
    document=json.loads(fixture[1].read_text())
    document['paths']['/orders']['post']['requestBody']['content']['application/json']['schema']={'$ref':'https://invalid.example/Order.json'}
    fixture[1].write_text(json.dumps(document))
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    with patch('subprocess.Popen',side_effect=AssertionError('process')),patch('socket.socket',side_effect=AssertionError('network')):
        result=attach(workspace,graph,catalog,captured)
    binding=next(n for n in result.nodes if n.kind=='http_interface').attributes['contract_bindings'][0]
    assert binding['status']=='BOUND_DECLARATION' # exact explicit file/operation only
    assert 'SCHEMA_REFERENCE_UNSUPPORTED' in binding['reasons']
    assert all(r['role']!='REQUEST' for r in binding['schema_references'])
    assert binding['payload_compatibility']=='UNKNOWN'


def test_ambiguous_normalized_operation_remains_unknown(fixture):
    document=json.loads(fixture[1].read_text());operation=document['paths']['/orders']['post']
    document['paths']={'/orders/{id}':{'post':operation}}
    fixture[1].write_text(json.dumps(document))
    workspace,graph,catalog=inputs(fixture)
    # Attach the changed explicit contract to the prior real catalogue. No new
    # provider projection or repaired catalogue identity is manufactured here.
    document['paths']['/orders/{name}']={'post':operation}
    fixture[1].write_text(json.dumps(document))
    workspace=load_workspace(fixture[0]);_,_,_,graph,_=snapshot_workspace(fixture[0])
    result=attach(workspace,graph,catalog,capture(workspace,graph))
    providers=[n for n in result.nodes if n.kind=='http_interface']
    assert providers and all(n.attributes['contract_bindings'][0]['status']!='BOUND_DECLARATION' for n in providers)
    assert all('CONTRACT_OPERATION_AMBIGUOUS_OR_MISSING' in n.attributes['contract_bindings'][0]['reasons'] for n in providers)


@pytest.mark.parametrize('field',['normalized_route','source_path','context_ids','scope'])
def test_foreign_or_changed_catalogue_tuple_cannot_attach_current_operation(fixture,field):
    from dataclasses import replace
    from kgmaker.workspace import qualified
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    if field=='scope':damaged=replace(catalog,scope='test')
    else:
        changed=[]
        for node in catalog.nodes:
            if node.kind!='http_interface':changed.append(node);continue
            attrs=dict(node.attributes)
            attrs[field]=('/foreign' if field=='normalized_route' else '@client/src/api.generated.ts' if field=='source_path' else [qualified('backend','foreign')])
            changed.append(replace(node,attributes=attrs))
        damaged=replace(catalog,nodes=tuple(changed))
    before=damaged.to_dict()
    result=attach(workspace,graph,damaged,captured)
    assert all(b['status']!='BOUND_DECLARATION' for n in result.nodes if n.kind=='http_interface' for b in n.attributes.get('contract_bindings',[]))
    assert damaged.to_dict()==before


@pytest.mark.parametrize('kind',['missing','symlink','oversize'])
def test_invalid_explicit_file_never_reads_outside_or_mutates_inputs(fixture,kind):
    from kgmaker.scanner import MAX_FILE_BYTES
    workspace,graph,catalog=inputs(fixture)
    contract=fixture[1]
    if kind=='missing':contract.unlink()
    elif kind=='symlink':
        outside=contract.parents[4]/'outside.json';outside.write_text('{"private":"DO_NOT_READ"}')
        contract.unlink();contract.symlink_to(outside)
    else:contract.write_bytes(b' '* (MAX_FILE_BYTES+1))
    captured=capture(workspace,graph);before=copy.deepcopy(captured),catalog.to_dict(),graph.to_dict()
    result=attach(workspace,graph,catalog,captured)
    assert all(b['status']!='BOUND_DECLARATION' for n in result.nodes for b in n.attributes.get('contract_bindings',[]))
    assert (captured,catalog.to_dict(),graph.to_dict())==before
    assert 'DO_NOT_READ' not in json.dumps(captured)


def test_input_replaced_during_attachment_preserves_last_valid_artifact(fixture):
    from kgmaker import contract_inputs
    from kgmaker.interfaces import InterfaceProjectionError
    workspace,graph,catalog=inputs(fixture);captured=capture(workspace,graph)
    initial=attach(workspace,graph,catalog,captured)
    artifact=fixture[0].parent/'last-view.json';artifact.write_text(initial.to_json())
    saved=artifact.read_bytes();before=copy.deepcopy(captured),catalog.to_dict(),graph.to_dict()
    original=contract_inputs.capture_file;changed=False
    def replace_after_capture(root,path,**kwargs):
        nonlocal changed
        result=original(root,path,**kwargs)
        if path=='generation.json' and not changed:
            changed=True;fixture[3].write_bytes(fixture[3].read_bytes()+b' ')
        return result
    with patch.object(contract_inputs,'capture_file',side_effect=replace_after_capture):
        with pytest.raises(InterfaceProjectionError):attach(workspace,graph,catalog,captured)
    assert changed and artifact.read_bytes()==saved
    assert (captured,catalog.to_dict(),graph.to_dict())==before

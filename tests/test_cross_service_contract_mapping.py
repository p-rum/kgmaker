"""W07 public acceptance RED; no producer implementation or implicit discovery."""
import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

from test_t013_attach_interface_contracts import fixture as explicit_contract_fixture
from test_t013_attach_interface_contracts import inputs, capture as contract_capture, attach
from test_t012_catalog_kafka_interfaces import capture as kafka_capture
from test_t011_catalog_http_consumers import captured as http_capture


def api():
    name='kgmaker.remote_mapping'
    assert importlib.util.find_spec(name) is not None, 'W07 pure remote mapping/capture API is not implemented'
    module=importlib.import_module(name)
    assert callable(getattr(module,'capture_remote_mapping_inputs',None))
    assert callable(getattr(module,'resolve_remote_mappings',None))
    return module


def test_public_canonical_capture_and_offline_empty_mapping(explicit_contract_fixture):
    workspace,graph,catalog=inputs(explicit_contract_fixture)
    catalog=attach(workspace,graph,catalog,contract_capture(workspace,graph))
    module=api()
    captured=module.capture_remote_mapping_inputs(workspace,graph,scope='production')
    assert set(captured)=={'schema_version','rule_version','workspace_id',
        'workspace_manifest_sha256','workspace_fingerprint','graph_fingerprint','selection',
        'remote_declarations','contract_capture','canonical_interfaces','diagnostics','capture_id'}
    assert captured['canonical_interfaces']
    before=copy.deepcopy(workspace),graph.to_dict(),catalog.to_dict(),copy.deepcopy(captured)
    def forbidden(*args,**kwargs):raise AssertionError('Pure W07 resolver invoked I/O/upstream projector')
    with patch('pathlib.Path.open',forbidden),patch('pathlib.Path.read_bytes',forbidden),patch('pathlib.Path.read_text',forbidden),\
            patch('subprocess.Popen',forbidden),patch('socket.socket',forbidden),\
            patch('kgmaker.interfaces.project_http_providers',forbidden),\
            patch('kgmaker.interfaces.project_http_consumers',forbidden),\
            patch('kgmaker.interfaces.project_kafka_interfaces',forbidden),\
            patch('kgmaker.interfaces.capture_interface_contracts',forbidden),\
            patch('kgmaker.interfaces.attach_interface_contracts',forbidden):
        result=module.resolve_remote_mappings(workspace,graph,captured['canonical_interfaces'],
            captured=captured,scope='production')
    assert result['bindings']==[]  # no explicit mapping: no name/URL auto-binding
    assert (workspace,graph.to_dict(),catalog.to_dict(),captured)==before


def persist(kind,workspace,graph,coverage):
    directory=os.environ.get('KGMAKER_REMOTE_CAPTURE_RED_DIR')
    if directory:
        target=Path(directory);target.mkdir(parents=True,exist_ok=True)
        (target/(kind+'.json')).write_text(json.dumps({'workspace_id':workspace['workspace_id'],
            'graph':graph.to_dict(),'coverage':coverage},indent=2))


def test_actual_kafka_canonical_capture_contract_before_resolution(kafka_capture):
    workspace,graph,coverage=kafka_capture
    assert any(n.kind=='kafka_code_listener' for n in graph.nodes)
    assert any(n.kind=='kafka_code_producer' for n in graph.nodes)
    persist('kafka',workspace,graph,coverage)  # completed native fixture before feature RED
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    assert any(n['kind']=='kafka_interface' for doc in captured['canonical_interfaces'] for n in doc['nodes'])
    assert captured['selection']['scope']=='production'


def test_actual_http_canonical_capture_contract_before_resolution(http_capture):
    workspace,graph,coverage=http_capture
    assert any(n.kind=='http_request_definition' for n in graph.nodes)
    persist('http',workspace,graph,coverage)
    captured=api().capture_remote_mapping_inputs(workspace,graph,scope='production',source_coverage=coverage)
    assert any(n['kind']=='http_interface' for doc in captured['canonical_interfaces'] for n in doc['nodes'])
    assert captured['selection']['scope']=='production'

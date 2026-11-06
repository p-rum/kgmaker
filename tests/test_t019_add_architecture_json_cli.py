"""T019 real CLI entrypoint and immutable captured-input contracts."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from kgmaker.service_topology import aggregate_service_topology
from test_t016_aggregate_service_topology import labelled_handoff
from test_cross_service_contract_mapping import trusted_protocol_specimen

ROOT=Path(__file__).resolve().parents[1]


def run_cli(*args):
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    return subprocess.run([sys.executable,'-B','-m','kgmaker','architecture',*map(str,args)],
        cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False));return path


def test_public_topology_snapshot_emits_whole_filter_envelope_and_strict_partial_exit(tmp_path):
    captured=labelled_handoff();path=write(tmp_path/'capture.json',captured);before=path.read_bytes()
    result=run_cli('topology','--capture-snapshot',path,'--format','json')
    assert result.returncode==0,result.stderr
    envelope=json.loads(result.stdout)
    assert set(envelope)=={'schema_version','rules_version','document','filtering'}
    assert envelope['document']['kind']=='topology' and envelope['filtering']['status']=='UNRESTRICTED'
    strict=run_cli('topology','--capture-snapshot',path,'--strict')
    assert strict.returncode==4 and json.loads(strict.stdout)==envelope
    assert path.read_bytes()==before


def test_public_interfaces_snapshot_returns_exact_canonical_requested_catalog(tmp_path):
    workspace,graph,docs,captured=trusted_protocol_specimen()
    # Specimen uses hand-labelled IDs; use the canonical published role IDs.
    for doc in docs:
        name=next(name for name in ['http-providers','http-consumers','kafka-interfaces'] if doc['rules_version'].startswith(name))
        doc['view_id']='view:'+name+':'+workspace['workspace_id']+':production'
    from test_cross_service_contract_mapping import refresh_handoff
    from kgmaker.remote_mapping import _workspace
    refresh_handoff(workspace,graph,docs,captured)
    bundle={'schema_version':1,'rules_version':'architecture-interface-inputs-1',
        'workspace':_workspace(workspace),'graph':graph.to_dict(),'captured':captured}
    path=write(tmp_path/'interfaces.json',bundle)
    result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path)
    assert result.returncode==0,result.stderr
    document=json.loads(result.stdout)
    assert document['kind']=='interfaces' and document['view_id']=='view:http-consumers:manual-protocol:production'
    assert any(n['id']=='client' for n in document['nodes'])


def test_public_explain_uses_original_handoff_without_current_source_observation(tmp_path):
    captured=labelled_handoff();view=aggregate_service_topology(captured)
    cap=write(tmp_path/'capture.json',captured);snapshot=write(tmp_path/'view.json',view.to_dict())
    result=run_cli('explain','--snapshot',snapshot,'--capture-snapshot',cap,'--element',view.edges[0].id)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['status']=='EXPLAINED' and report['current_source_status']=='NOT_CHECKED'
    assert report['view_fingerprint']==view.content_fingerprint


@pytest.mark.parametrize('args',[
    ['--format','password=PRIVATE_SENTINEL'],
    ['--unknown-PRIVATE_SENTINEL'],
    ['--max-nodes','PRIVATE_SENTINEL'],
    ['--direction','secret:PRIVATE_SENTINEL'],
])
def test_safe_parser_never_reflects_invalid_credential_arguments(tmp_path,args):
    captured=write(tmp_path/'capture.json',labelled_handoff())
    result=run_cli('topology','--capture-snapshot',captured,*args)
    assert result.returncode==2 and result.stdout==''
    assert 'PRIVATE_SENTINEL' not in result.stderr and 'Traceback' not in result.stderr
    assert json.loads(result.stderr)['code']=='INVALID_ARGUMENTS'


@pytest.mark.parametrize('selection',[
    {'schema_version':True,'contexts':[]},
    {'schema_version':1,'contexts':[{'service_id':'checkout','repo_id':'backend','module':'root','context_id':'foreign'}]},
    {'schema_version':1,'contexts':[{'service_id':'checkout','repo_id':'backend','module':'root','context_id':'x'}]*2},
])
def test_snapshot_selection_asserts_original_pins_and_never_reselects(tmp_path,selection):
    cap=write(tmp_path/'capture.json',labelled_handoff());pins=write(tmp_path/'pins.json',selection)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    result=run_cli('topology','--capture-snapshot',cap,'--context-selection',pins)
    assert result.returncode==2 and result.stdout==''
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==before


def test_snapshot_empty_pins_preserve_captured_selection_and_scope_is_assertion(tmp_path):
    cap=write(tmp_path/'capture.json',labelled_handoff());pins=write(tmp_path/'pins.json',{'schema_version':1,'contexts':[]})
    result=run_cli('topology','--capture-snapshot',cap,'--context-selection',pins)
    assert result.returncode==0
    wrong=run_cli('topology','--capture-snapshot',cap,'--scope','test')
    assert wrong.returncode==2 and wrong.stdout=='' and json.loads(wrong.stderr)['code']=='CAPTURED_SCOPE_MISMATCH'


def test_expected_fingerprint_is_explicit_conflict_not_snapshot_repair(tmp_path):
    from kgmaker.topology_filter import filter_topology
    from kgmaker.architecture_model import ViewDocument
    captured=labelled_handoff();cap=write(tmp_path/'capture.json',captured)
    view=ViewDocument.from_dict(filter_topology(aggregate_service_topology(captured))['document'])
    result=run_cli('topology','--capture-snapshot',cap,'--expected-fingerprint',view.content_fingerprint)
    assert result.returncode==0
    conflict=run_cli('topology','--capture-snapshot',cap,'--expected-fingerprint','0'*64)
    assert conflict.returncode==3 and conflict.stdout==''
    assert json.loads(conflict.stderr)['code']=='EXPECTED_FINGERPRINT_MISMATCH'


def test_node_cutoff_keeps_entire_filter_omission_frontier(tmp_path):
    cap=write(tmp_path/'capture.json',labelled_handoff())
    result=run_cli('topology','--capture-snapshot',cap,'--focus','service:checkout','--max-nodes','1','--strict')
    assert result.returncode==4
    value=json.loads(result.stdout)
    assert len(value['document']['nodes'])==1 and value['filtering']['omitted_edge_ids']
    assert value['filtering']['frontier'] and value['filtering']['omitted_original_interface_ids']==['client','provider']
    empty=run_cli('topology','--capture-snapshot',cap,'--relations')
    assert empty.returncode==0 and json.loads(empty.stdout)['document']['edges']==[]


def test_snapshot_replay_never_calls_live_source_or_projector(tmp_path,monkeypatch,capsys):
    import kgmaker.architecture_cli as cli
    import kgmaker.workspace,kgmaker.feature,kgmaker.remote_mapping,kgmaker.service_topology
    cap=write(tmp_path/'capture.json',labelled_handoff())
    def forbidden(*args,**kwargs):raise AssertionError('snapshot mode performed live work')
    monkeypatch.setattr(kgmaker.workspace,'snapshot_workspace',forbidden)
    monkeypatch.setattr(kgmaker.workspace,'load_workspace',forbidden)
    monkeypatch.setattr(kgmaker.feature,'current_graph',forbidden)
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',forbidden)
    monkeypatch.setattr(kgmaker.service_topology,'capture_topology_inputs',forbidden)
    assert cli.run(['topology','--capture-snapshot',str(cap)])==0
    assert json.loads(capsys.readouterr().out)['document']['kind']=='topology'


@pytest.mark.parametrize('raw',['{"schema_version":1,"schema_version":2}', '{"x":NaN}', '['*2000+']'*2000, 'not-json'])
def test_bounded_input_errors_leave_stdout_empty_and_last_artifact_unchanged(tmp_path,raw):
    cap=tmp_path/'capture.json';cap.write_text(raw);saved=tmp_path/'last-valid.json';saved.write_text('previous')
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    result=run_cli('topology','--capture-snapshot',cap)
    assert result.returncode==2 and result.stdout=='' and 'Traceback' not in result.stderr
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==before


def test_cancel_file_is_read_only_exit130_before_input_capture(tmp_path):
    cancel=tmp_path/'cancel';cancel.write_text('cancel')
    result=run_cli('topology','--capture-snapshot',tmp_path/'does-not-exist','--cancel-file',cancel)
    assert result.returncode==130 and result.stdout==''
    assert json.loads(result.stderr)['code']=='CANCELLED' and cancel.read_text()=='cancel'


def test_keyboard_interrupt_in_command_boundary_has_no_partial_output(tmp_path,monkeypatch,capsys):
    import kgmaker.architecture_cli as cli
    cap=write(tmp_path/'capture.json',labelled_handoff())
    def interrupted(*args,**kwargs):raise KeyboardInterrupt
    monkeypatch.setattr(cli,'_topology',interrupted)
    assert cli.run(['topology','--capture-snapshot',str(cap)])==130
    output=capsys.readouterr();assert output.out=='' and json.loads(output.err)['code']=='CANCELLED'


def test_broken_pipe_is_controlled_without_traceback_or_second_json(tmp_path,monkeypatch):
    import kgmaker.architecture_cli as cli
    cap=write(tmp_path/'capture.json',labelled_handoff())
    class ClosedPipe:
        def write(self,value):raise BrokenPipeError
        def fileno(self):raise OSError('not a real descriptor')
    monkeypatch.setattr(sys,'stdout',ClosedPipe())
    assert cli.run(['topology','--capture-snapshot',str(cap)])==141


def test_unexpected_internal_error_is_fixed_exit1_without_input_echo(tmp_path,monkeypatch,capsys):
    import kgmaker.architecture_cli as cli
    cap=write(tmp_path/'capture.json',labelled_handoff())
    def broken(*args,**kwargs):raise RuntimeError('PRIVATE_SENTINEL')
    monkeypatch.setattr(cli,'_topology',broken)
    assert cli.run(['topology','--capture-snapshot',str(cap)])==1
    output=capsys.readouterr();assert output.out=='' and 'PRIVATE_SENTINEL' not in output.err
    assert json.loads(output.err)['code']=='INTERNAL_ERROR'


from test_t013_attach_interface_contracts import fixture as explicit_contract_fixture


@pytest.mark.parametrize('corrupt',[False,True])
def test_capture_local_missing_or_corrupt_original_index_never_runs_parser(tmp_path,explicit_contract_fixture,monkeypatch,capsys,corrupt):
    import kgmaker.architecture_cli as cli
    import kgmaker.workspace,kgmaker.feature
    manifest,*_=explicit_contract_fixture
    if corrupt:
        for name in ['backend','client']:
            index=manifest.parent/name/'.kgmaker/graph.json';index.parent.mkdir();index.write_text('not-json')
    def forbidden(*args,**kwargs):raise AssertionError('missing index triggered parser or capture')
    monkeypatch.setattr(kgmaker.workspace,'snapshot_workspace',forbidden)
    monkeypatch.setattr(kgmaker.feature,'current_graph',forbidden)
    assert cli.run(['topology','--capture-local','--workspace',str(manifest)])==2
    output=capsys.readouterr();assert output.out=='' and 'ORIGINAL_INDEX_' in output.err


def test_capture_local_is_explicit_real_parser_replay_without_any_index_or_store_write(explicit_contract_fixture):
    from kgmaker.model import KnowledgeGraph
    manifest,*_=explicit_contract_fixture
    for name in ['backend','client']:
        index=manifest.parent/name/'.kgmaker/graph.json';index.parent.mkdir();write(index,KnowledgeGraph(3,'.','old',[],[],{}).to_dict())
    before={str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}
    result=run_cli('topology','--capture-local','--workspace',manifest)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['document']['kind']=='topology'
    assert {str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}==before
    assert not any(p.name=='workspace-cache' for p in manifest.parent.rglob('*'))


def test_explicit_check_source_uses_original_graph_and_preserves_snapshot_hash(tmp_path):
    from test_t018_explain_view_elements import bound_source
    workspace,graph,captured,source,ref=bound_source(tmp_path);view=aggregate_service_topology(captured)
    cap=write(tmp_path/'capture.json',captured);snapshot=write(tmp_path/'view.json',view.to_dict());graphfile=write(tmp_path/'graph.json',graph.to_dict())
    source.write_text('changed file\n')
    result=run_cli('explain','--snapshot',snapshot,'--capture-snapshot',cap,'--element',view.edges[0].id,
        '--graph-snapshot',graphfile,'--check-source','--workspace',workspace['_manifest_path'])
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['current_source_status']=='SOURCE_STALE' and report['view_fingerprint']==view.content_fingerprint
    assert report['freshness']=='UNKNOWN' and str(tmp_path) not in result.stdout


def test_legacy_version_and_graph_flow_help_remain_available():
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    for args in [['--version'],['graph','view','--help'],['flow','render','--help']]:
        result=subprocess.run([sys.executable,'-B','-m','kgmaker',*args],env=env,cwd=ROOT,text=True,capture_output=True,timeout=30)
        assert result.returncode==0,result.stderr


def test_capture_local_interfaces_uses_existing_canonical_catalog_without_writes(explicit_contract_fixture):
    from kgmaker.model import KnowledgeGraph
    manifest,*_=explicit_contract_fixture
    for name in ['backend','client']:
        index=manifest.parent/name/'.kgmaker/graph.json';index.parent.mkdir();write(index,KnowledgeGraph(3,'.','old',[],[],{}).to_dict())
    before={str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}
    result=run_cli('interfaces','--catalog','http-providers','--capture-local','--workspace',manifest)
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout)
    assert value['kind']=='interfaces' and any(n['kind']=='http_interface' for n in value['nodes'])
    assert {str(p):p.read_bytes() for p in manifest.parent.rglob('*') if p.is_file()}==before


def test_source_status_sidecar_is_pure_and_does_not_reopen_checkout(tmp_path,monkeypatch,capsys):
    import kgmaker.architecture_cli as cli
    import kgmaker.workspace
    from kgmaker.view_explanation import capture_explanation_source_status
    from test_t018_explain_view_elements import bound_source
    workspace,graph,captured,source,ref=bound_source(tmp_path);view=aggregate_service_topology(captured)
    status=capture_explanation_source_status(workspace,graph,captured=captured,reference_ids=[ref])
    cap=write(tmp_path/'capture.json',captured);snapshot=write(tmp_path/'view.json',view.to_dict())
    graphfile=write(tmp_path/'graph.json',graph.to_dict());sidecar=write(tmp_path/'status.json',status)
    source.unlink()
    def forbidden(*args,**kwargs):raise AssertionError('sidecar replay read current source')
    monkeypatch.setattr(kgmaker.workspace,'load_workspace',forbidden)
    assert cli.run(['explain','--snapshot',str(snapshot),'--capture-snapshot',str(cap),'--element',view.edges[0].id,
        '--graph-snapshot',str(graphfile),'--source-status',str(sidecar)])==0
    value=json.loads(capsys.readouterr().out)
    assert value['current_source_status']=='CONTENT_MATCH' # supplied observation, not a new physical read
    assert value['source_status_fingerprint']==status['status_id']


def test_explain_preserves_filtered_snapshot_frontiers_and_unknown_element(tmp_path):
    from kgmaker.topology_filter import filter_topology
    captured=labelled_handoff();original=aggregate_service_topology(captured)
    filtered=filter_topology(original,focus_service='service:checkout',max_nodes=1)
    cap=write(tmp_path/'capture.json',captured);snapshot=write(tmp_path/'filtered.json',filtered)
    result=run_cli('explain','--snapshot',snapshot,'--capture-snapshot',cap,'--element','service:checkout')
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['filtering']['omitted_edge_ids']==filtered['filtering']['omitted_edge_ids']
    missing=run_cli('explain','--snapshot',snapshot,'--capture-snapshot',cap,'--element','missing','--strict')
    assert missing.returncode==4 and json.loads(missing.stdout)['status']=='UNKNOWN_ELEMENT'


def test_unsafe_interface_output_is_rejected_without_redacting_bound_ids(tmp_path):
    from kgmaker.remote_mapping import _workspace
    from test_cross_service_contract_mapping import refresh_handoff
    workspace,graph,docs,captured=specimen=trusted_protocol_specimen()
    for doc in docs:
        role=next(name for name in ['http-providers','http-consumers','kafka-interfaces'] if doc['rules_version'].startswith(name))
        doc['view_id']='view:'+role+':'+workspace['workspace_id']+':production'
        for node in doc['nodes']:node['label']='password=PRIVATE_SENTINEL'
    refresh_handoff(*specimen)
    bundle={'schema_version':1,'rules_version':'architecture-interface-inputs-1','workspace':_workspace(workspace),'graph':graph.to_dict(),'captured':captured}
    path=write(tmp_path/'interfaces.json',bundle);before=path.read_bytes()
    result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path)
    assert result.returncode==2 and result.stdout=='' and 'PRIVATE_SENTINEL' not in result.stderr
    assert path.read_bytes()==before


def test_interface_capture_graph_and_private_workspace_tamper_fail_consistency(tmp_path):
    from kgmaker.remote_mapping import _workspace
    workspace,graph,docs,captured=trusted_protocol_specimen()
    bundle={'schema_version':1,'rules_version':'architecture-interface-inputs-1','workspace':_workspace(workspace),'graph':graph.to_dict(),'captured':captured}
    for damage in ['graph','private']:
        changed=deepcopy(bundle)
        if damage=='graph':changed['graph']['files']['foreign']='a'*64
        else:changed['workspace']['_root']='PRIVATE_SENTINEL'
        path=write(tmp_path/(damage+'.json'),changed)
        result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path)
        assert result.returncode==2 and result.stdout=='' and 'PRIVATE_SENTINEL' not in result.stderr


def test_complete_model_exit_policy_does_not_depend_on_runtime_observation():
    from kgmaker.architecture_cli import _incomplete
    from kgmaker.architecture_model import ViewDocument
    complete=ViewDocument('v','interfaces','b','model-fixture','production',{},coverage={'status':'COMPLETE_WITHIN_SELECTED_SCOPE'})
    assert _incomplete(complete.to_dict()) is False
    partial=ViewDocument('v','interfaces','b','model-fixture','production',{},coverage={'status':'UNKNOWN'})
    assert _incomplete(partial.to_dict()) is True


def test_unsupported_output_and_input_bounds_never_publish_partial_document(tmp_path,monkeypatch,capsys):
    import kgmaker.architecture_cli as cli
    cap=write(tmp_path/'capture.json',labelled_handoff())
    monkeypatch.setattr(cli,'_MAX_INPUT_BYTES',10)
    assert cli.run(['topology','--capture-snapshot',str(cap)])==2
    output=capsys.readouterr();assert output.out==''
    monkeypatch.setattr(cli,'_MAX_INPUT_BYTES',32_000_000);monkeypatch.setattr(cli,'_MAX_OUTPUT_CHARS',10)
    assert cli.run(['topology','--capture-snapshot',str(cap)])==2
    assert capsys.readouterr().out==''

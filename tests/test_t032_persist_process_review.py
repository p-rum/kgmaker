"""Explicit local review does not mutate the technical ProcessView."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from kgmaker.process_semantics import prepare_process_label_packet
from test_t023_define_business_process_model import sample_process
from test_t031_validate_process_annotations import proposed


def api():
    from kgmaker import process_store
    return process_store


def inputs():
    p=sample_process(); packet=prepare_process_label_packet(p)['packet']
    return p,packet,proposed(packet)


def write(root,source,packet,candidate,**overrides):
    m=api(); prepared=m.prepare_process_review(source,packet,candidate)
    args=dict(action='APPROVE',reviewer='local:reviewer',operation_id='operation:one',expected_head=None,
        expected_payload_hash=prepared['payload_hash'],expected_baseline_hash=prepared['baseline_hash'])
    args.update(overrides)
    return m.persist_process_review(root,source,packet,candidate,**args)


def test_public_approve_is_explicit_separate_and_immutable(tmp_path):
    p,packet,candidate=inputs();before=deepcopy((p,packet,candidate))
    receipt=write(tmp_path,p,packet,candidate)
    assert receipt['status']=='COMMITTED' and receipt['semantic_revision']==1
    report=api().read_process_reviews(tmp_path,p)
    assert report['effective_status']=='APPROVED'
    assert report['active_annotations'][0]['label']=='Ověřit objednávku'
    assert report['identity_assurance']=='LOCAL_DECLARATION_NOT_AUTHENTICATED'
    assert (p,packet,candidate)==before
    assert not (tmp_path/'.kgmaker/graph.json').exists()


def test_public_same_operation_retry_does_not_rewrite(tmp_path):
    p,packet,candidate=inputs();first=write(tmp_path,p,packet,candidate)
    paths=list((tmp_path/'.kgmaker/process-reviews').glob('*.json'))
    assert len(paths)==1
    before=(paths[0].read_bytes(),paths[0].stat().st_mtime_ns)
    retry=write(tmp_path,p,packet,candidate)
    assert retry['head']==first['head'] and retry['idempotent'] is True
    assert before==(paths[0].read_bytes(),paths[0].stat().st_mtime_ns)


def test_public_stale_cas_cannot_overwrite(tmp_path):
    p,packet,candidate=inputs();write(tmp_path,p,packet,candidate)
    candidate['annotations'][0]['label']='Jiný popis'
    with pytest.raises(api().ProcessReviewError,match='CAS_CONFLICT'):
        write(tmp_path,p,packet,candidate,operation_id='operation:two')
    assert len(api().read_process_reviews(tmp_path,p)['history'])==1


def test_public_cancel_before_publication_preserves_empty_semantic_store(tmp_path):
    p,packet,candidate=inputs()
    with pytest.raises(api().ProcessReviewError,match='CANCELLED'):
        write(tmp_path,p,packet,candidate,cancelled=lambda:True)
    assert not list(tmp_path.rglob('*.json'))


def test_public_changed_explicit_baseline_needs_revalidation(tmp_path):
    p,packet,candidate=inputs();write(tmp_path,p,packet,candidate)
    p['technical_view']['nodes'][0]['label']='Changed technical presentation'
    result=api().read_process_reviews(tmp_path,p)
    assert result['effective_status']=='NEEDS_REVALIDATION'
    assert result['active_annotations']==[]
    assert result['history'][0]['action']=='APPROVE'


def test_public_reject_records_decision_without_active_labels(tmp_path):
    p,packet,candidate=inputs();write(tmp_path,p,packet,candidate,action='REJECT')
    result=api().read_process_reviews(tmp_path,p)
    assert result['effective_status']=='REJECTED' and result['active_annotations']==[]
    assert result['history'][0]['action']=='REJECT'


def _race_worker(root,barrier,queue,index):
    p,packet,candidate=inputs();candidate['annotations'][0]['label']=f'Varianta {index}'
    barrier.wait(timeout=15)
    try:
        result=write(Path(root),p,packet,candidate,operation_id=f'operation:{index}')
        queue.put(result['status'])
    except api().ProcessReviewError as e:
        queue.put(str(e))


def test_real_processes_cas_exactly_one_publishes(tmp_path):
    import multiprocessing
    ctx=multiprocessing.get_context('fork');barrier=ctx.Barrier(2);queue=ctx.Queue()
    children=[ctx.Process(target=_race_worker,args=(str(tmp_path),barrier,queue,i)) for i in range(2)]
    for child in children:child.start()
    for child in children:
        child.join(20)
        assert not child.is_alive() and child.exitcode==0
    assert sorted(queue.get(timeout=2) for _ in children)==['CAS_CONFLICT','COMMITTED']
    report=api().read_process_reviews(tmp_path,inputs()[0])
    assert len(report['history'])==1 and report['active_annotations'][0]['label'] in ['Varianta 0','Varianta 1']


def test_real_threads_cas_exactly_one_publishes(tmp_path):
    import threading,queue
    barrier=threading.Barrier(2);q=queue.Queue()
    threads=[threading.Thread(target=_race_worker,args=(str(tmp_path),barrier,q,i)) for i in range(2)]
    for thread in threads:thread.start()
    for thread in threads:thread.join(20);assert not thread.is_alive()
    assert sorted(q.get(timeout=2) for _ in threads)==['CAS_CONFLICT','COMMITTED']


def test_historical_idempotent_retry_never_rewinds_head(tmp_path):
    p,packet,c=inputs();first=write(tmp_path,p,packet,c)
    second=write(tmp_path,p,packet,c,operation_id='operation:two',expected_head=first['head'],action='REJECT')
    before=next((tmp_path/'.kgmaker/process-reviews').glob('*.json')).read_bytes()
    old=write(tmp_path,p,packet,c)
    assert old['head']==first['head'] and not old['is_current'] and old['idempotent']
    report=api().read_process_reviews(tmp_path,p)
    assert report['head']==second['head'] and len(report['history'])==2
    assert report['active_annotations'][0]['label']=='Ověřit objednávku'
    assert report['active_annotations'][0]['source_refs']==['ev:card','origin:card']
    assert next((tmp_path/'.kgmaker/process-reviews').glob('*.json')).read_bytes()==before


def test_operation_id_reuse_with_different_action_is_conflict(tmp_path):
    p,packet,c=inputs();write(tmp_path,p,packet,c)
    with pytest.raises(api().ProcessReviewError,match='OPERATION_CONFLICT'):
        write(tmp_path,p,packet,c,action='REJECT')


@pytest.mark.parametrize('kind',['proposal','document'])
def test_approval_cannot_acknowledge_conflicts_but_reject_can_record(tmp_path,kind):
    p,packet,c=inputs();conflicts=[];docs=[]
    if kind=='proposal':
        c['annotations'].append({**c['annotations'][0],'id':'proposal:two','label':'Jiný význam'})
    else:
        from test_t030_prepare_process_label_packet import document
        docs=[document()]
        conflicts=[{'document_ref':'doc:guide','target_id':'card','status':'CONFLICT','source_refs':['origin:card']}]
        packet=prepare_process_label_packet(p,documents=docs,conflicts=conflicts)['packet'];c=proposed(packet)
    m=api();prepared=m.prepare_process_review(p,packet,c,documents=docs,conflicts=conflicts)
    kwargs=dict(reviewer='local:reviewer',operation_id='operation:conflict',expected_head=None,
        expected_payload_hash=prepared['payload_hash'],expected_baseline_hash=prepared['baseline_hash'],documents=docs,conflicts=conflicts)
    with pytest.raises(m.ProcessReviewError,match='CONFLICT_REQUIRES_REVISION'):
        m.persist_process_review(tmp_path,p,packet,c,action='APPROVE',**kwargs)
    assert not list(tmp_path.rglob('*.json'))
    m.persist_process_review(tmp_path,p,packet,c,action='REJECT',**kwargs)
    assert m.read_process_reviews(tmp_path,p,documents=docs,conflicts=conflicts)['active_annotations']==[]


def test_documentary_citation_is_separate_not_fake_technical_provenance(tmp_path):
    from test_t030_prepare_process_label_packet import document
    p,_,_=inputs();docs=[document()];packet=prepare_process_label_packet(p,documents=docs)['packet']
    c=proposed(packet,source_refs=['doc:guide']);before=deepcopy(p)
    m=api();prepared=m.prepare_process_review(p,packet,c,documents=docs)
    m.persist_process_review(tmp_path,p,packet,c,action='APPROVE',reviewer='local:one',operation_id='op:doc',
        expected_head=None,expected_payload_hash=prepared['payload_hash'],expected_baseline_hash=prepared['baseline_hash'],documents=docs)
    report=m.read_process_reviews(tmp_path,p,documents=docs)
    assert report['active_annotations'][0]['source_refs']==['doc:guide']
    assert report['history'][0]['prepared']['document_bindings'][0]['ref']=='doc:guide'
    assert p==before and all(e['id']!='doc:guide' for e in p['technical_view']['provenance'])
    assert 'content' not in report['history'][0]['prepared']['document_bindings'][0]


@pytest.mark.parametrize('point',['write','replace','directory_fsync'])
def test_publication_failure_is_old_or_complete_new_with_honest_status(tmp_path,monkeypatch,point):
    import os
    m=api();p,packet,c=inputs();first=write(tmp_path,p,packet,c)
    path=next((tmp_path/'.kgmaker/process-reviews').glob('*.json'));before=path.read_bytes()
    real_fsync=os.fsync
    calls=[]
    def fsync(fd):
        calls.append(fd)
        if point=='write' or (point=='directory_fsync' and len(calls)==2):raise OSError('PRIVATE_FAULT_SENTINEL')
        return real_fsync(fd)
    monkeypatch.setattr(m.os,'fsync',fsync)
    if point=='replace':
        def replace(*args):raise OSError('PRIVATE_FAULT_SENTINEL')
        monkeypatch.setattr(m.os,'replace',replace)
    if point=='directory_fsync':
        result=write(tmp_path,p,packet,c,operation_id='operation:second',expected_head=first['head'])
        assert result['status']=='INDETERMINATE' and len(json.loads(path.read_bytes())['history'])==2
        retry=write(tmp_path,p,packet,c,operation_id='operation:second',expected_head=first['head'])
        assert retry['idempotent'] and retry['head']==result['head']
    else:
        with pytest.raises(m.ProcessReviewError,match='STORE_IO_ERROR') as e:
            write(tmp_path,p,packet,c,operation_id='operation:second',expected_head=first['head'])
        assert 'PRIVATE_FAULT_SENTINEL' not in repr(e.value) and path.read_bytes()==before
    assert not list(path.parent.glob('*.tmp'))


def test_cancellation_after_temp_write_cleans_temp_and_retains_previous(tmp_path):
    p,packet,c=inputs();first=write(tmp_path,p,packet,c)
    path=next((tmp_path/'.kgmaker/process-reviews').glob('*.json'));before=path.read_bytes();calls=[]
    def cancelled():calls.append(1);return len(calls)==3
    with pytest.raises(api().ProcessReviewError,match='CANCELLED'):
        write(tmp_path,p,packet,c,operation_id='op:cancel',expected_head=first['head'],cancelled=cancelled)
    assert path.read_bytes()==before and not list(path.parent.glob('*.tmp'))


@pytest.mark.parametrize('damage',['duplicate','unknown','head','number','huge','secret_key'])
def test_corrupt_store_generic_failclosed_without_rewrite(tmp_path,damage):
    p,packet,c=inputs();write(tmp_path,p,packet,c);path=next((tmp_path/'.kgmaker/process-reviews').glob('*.json'))
    value=json.loads(path.read_bytes())
    if damage=='duplicate':raw='{"schema_version":1,"schema_version":1}'
    elif damage=='huge':raw=' '* (api().MAX_STORE_BYTES+1)
    else:
        if damage=='unknown':value['extra']='x'
        if damage=='head':value['head']='0'*64
        if damage=='number':value['history'][0]['semantic_revision']=True
        if damage=='secret_key':value['PRIVATE_STORE_SENTINEL_523']='private'
        raw=json.dumps(value)
    path.write_text(raw);before=path.read_bytes()
    with pytest.raises(api().ProcessReviewError) as e:api().read_process_reviews(tmp_path,p)
    assert 'PRIVATE_STORE_SENTINEL' not in repr(e.value) and path.read_bytes()==before


@pytest.mark.parametrize('field,value',[('reviewer','//alice:PRIVATE_CREDENTIAL@example.org/path'),
    ('operation_id','Basic UFJJVkFURQ=='),('expected_payload_hash','PRIVATE_TOKEN')])
def test_unsafe_explicit_metadata_never_echoes_or_publishes(tmp_path,field,value):
    p,packet,c=inputs()
    with pytest.raises(api().ProcessReviewError) as e:write(tmp_path,p,packet,c,**{field:value})
    assert 'PRIVATE' not in repr(e.value) and not list(tmp_path.rglob('*.json'))


def test_no_subprocess_network_or_other_apply_and_no_input_mutation(tmp_path,monkeypatch):
    import subprocess,socket
    def forbidden(*args,**kwargs):raise AssertionError('unexpected external execution')
    monkeypatch.setattr(subprocess,'Popen',forbidden);monkeypatch.setattr(socket,'socket',forbidden)
    p,packet,c=inputs();before=deepcopy((p,packet,c));write(tmp_path,p,packet,c)
    assert (p,packet,c)==before


def test_symlink_store_refused_without_touching_target(tmp_path):
    p,packet,c=inputs();outside=tmp_path/'external';outside.mkdir();kg=tmp_path/'.kgmaker';kg.mkdir()
    (kg/'process-reviews').symlink_to(outside,target_is_directory=True)
    with pytest.raises(api().ProcessReviewError):write(tmp_path,p,packet,c)
    assert list(outside.iterdir())==[]


@pytest.mark.parametrize('limit',['history','bytes'])
def test_versioned_cap_hard_fails_without_pruning_or_rewrite(tmp_path,monkeypatch,limit):
    p,packet,c=inputs();first=write(tmp_path,p,packet,c)
    path=next((tmp_path/'.kgmaker/process-reviews').glob('*.json'));before=path.read_bytes()
    if limit=='history':monkeypatch.setattr(api(),'MAX_HISTORY',1)
    else:monkeypatch.setattr(api(),'MAX_STORE_BYTES',len(before)+10)
    with pytest.raises(api().ProcessReviewError,match='HISTORY_LIMIT|STORE_SIZE_LIMIT'):
        write(tmp_path,p,packet,c,operation_id='op:cap',expected_head=first['head'])
    assert path.read_bytes()==before and len(json.loads(before)['history'])==1


def test_unsupported_platform_controlled_before_store_creation(tmp_path,monkeypatch):
    p,packet,c=inputs();m=api()
    # Replace only this module's OS view, not global pathlib platform detection.
    from types import SimpleNamespace
    monkeypatch.setattr(m,'os',SimpleNamespace(name='nt'))
    with pytest.raises(m.ProcessReviewError,match='UNSUPPORTED_PLATFORM'):
        write(tmp_path,p,packet,c)
    assert not list(tmp_path.rglob('*.json'))


def test_cancel_racing_after_replace_returns_committed_not_false_rollback(tmp_path,monkeypatch):
    p,packet,c=inputs();m=api();state={'cancelled':False};real=m.os.replace
    def replace(*args):real(*args);state['cancelled']=True
    monkeypatch.setattr(m.os,'replace',replace)
    result=write(tmp_path,p,packet,c,cancelled=lambda:state['cancelled'])
    assert state['cancelled'] and result['status']=='COMMITTED'
    assert m.read_process_reviews(tmp_path,p)['head']==result['head']


def test_valid_unicode_space_identity_and_local_reviewer_preserved(tmp_path):
    from kgmaker.process_model import ProcessDefinition
    p,_,_=inputs();identity='process:Česká cesta/orders checkout.kt'
    p['process_id']=p['definition']['process_id']=identity;p['technical_view']['view_id']=identity
    p['definition_fingerprint']=ProcessDefinition.from_dict(p['definition']).content_fingerprint
    packet=prepare_process_label_packet(p)['packet'];c=proposed(packet)
    write(tmp_path,p,packet,c,reviewer='lokální:Žaneta Nováková',operation_id='operace:číslo 1')
    report=api().read_process_reviews(tmp_path,p)
    assert report['history'][0]['reviewer']=='lokální:Žaneta Nováková'
    assert report['history'][0]['prepared']['identity']['process_id']==identity


def test_invalid_secret_key_never_appears_in_exception_or_store(tmp_path):
    p,packet,c=inputs();p['PRIVATE_MALFORMED_KEY_81fa']='unsafe'
    with pytest.raises(api().ProcessReviewError) as e:write(tmp_path,p,packet,c)
    assert 'PRIVATE_MALFORMED_KEY' not in repr(e.value) and e.value.__cause__ is None
    assert not list(tmp_path.rglob('*.json'))


def test_cyclic_and_nonfinite_inputs_fail_before_writes(tmp_path):
    p,packet,c=inputs();c['loop']=c
    with pytest.raises(api().ProcessReviewError):write(tmp_path,p,packet,c)
    assert not list(tmp_path.rglob('*.json'))


def test_same_visible_process_in_other_scope_has_no_approval(tmp_path):
    from kgmaker.process_model import ProcessDefinition
    p,packet,c=inputs();write(tmp_path,p,packet,c)
    p['definition']['scope']=p['technical_view']['scope']='test'
    for item in p['technical_view']['nodes']+p['technical_view']['edges']:item['attributes']['scope']='test'
    for proof in p['technical_view']['provenance']:proof['scope']='test'
    p['definition_fingerprint']=ProcessDefinition.from_dict(p['definition']).content_fingerprint
    report=api().read_process_reviews(tmp_path,p)
    assert report['effective_status']=='EMPTY' and report['active_annotations']==[]

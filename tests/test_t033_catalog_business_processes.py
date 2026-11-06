"""Catalog identities and lifecycle remain separate from semantic labels."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from kgmaker.process_model import ProcessDefinition
from kgmaker.process_semantics import prepare_process_label_packet
from test_t023_define_business_process_model import sample_process
from test_t031_validate_process_annotations import proposed
from test_t032_persist_process_review import write


def api():
    from kgmaker import process_catalog
    return process_catalog


def process(identity='process:checkout',trigger='request',revision=3):
    p=sample_process();p['process_id']=p['definition']['process_id']=identity
    p['technical_view']['view_id']=identity;p['revision']=p['definition']['revision']=revision
    if trigger!='request':
        node=next(n for n in p['technical_view']['nodes'] if n['id']=='request');node['id']=trigger
        p['definition']['trigger_ids']=[trigger];p['entry_ids']=[trigger]
        for edge in p['technical_view']['edges']:
            if edge['source']=='request':edge['source']=trigger
            if edge['target']=='request':edge['target']=trigger
    p['definition_fingerprint']=ProcessDefinition.from_dict(p['definition']).content_fingerprint
    return p



def add_trigger(p,trigger):
    node=deepcopy(next(n for n in p['technical_view']['nodes'] if n['kind']=='trigger'))
    node['id']=trigger;p['technical_view']['nodes'].append(node)
    p['definition']['trigger_ids'].append(trigger);p['entry_ids'].append(trigger)
    p['definition_fingerprint']=ProcessDefinition.from_dict(p['definition']).content_fingerprint


def inventory(*processes):
    p=processes[0] if processes else process();v=deepcopy(p['technical_view'])
    v.update(view_id='trigger-inventory:fixture:production',rules_version='t024-proved-trigger-inventory-1',nodes=[],edges=[],provenance=[])
    for source in processes:
        trigger=source['definition']['trigger_ids'][0]
        n=deepcopy(next(n for n in source['technical_view']['nodes'] if n['id']==trigger))
        n.update(kind='trigger',owner_id='service:orders')
        n['attributes'].update(trigger_kind='HTTP',entry_symbol_id='symbol:'+trigger,entrypoint_id='endpoint:'+trigger,
            repo_id='orders',owner_status='RESOLVED',candidate_owner_ids=[],body_status='AVAILABLE',
            registration_status='UNKNOWN',execution_status='UNKNOWN',data_availability='UNKNOWN')
        v['nodes'].append(n)
        for proof in source['technical_view']['provenance']:
            if proof['id'] in n['evidence_refs'] and proof not in v['provenance']:v['provenance'].append(deepcopy(proof))
    v['coverage']={'status':'PARTIAL' if processes else 'UNKNOWN','counts':{'found':len(processes),'resolved':len(processes),'unresolved':0,'excluded':0}}
    return v


def catalog(root,triggers,**kw):
    return api().catalog_business_processes(root,triggers,**kw)


def test_same_business_label_distinct_trigger_identity_stays_two(tmp_path):
    a=process();b=process('process:other','request:other')
    for p in [a,b]:
        packet=prepare_process_label_packet(p)['packet'];write(tmp_path,p,packet,proposed(packet))
    before=deepcopy((a,b));result=catalog(tmp_path,inventory(a,b),current_processes=[a,b])
    assert len(result['rows'])==2
    assert {r['process_id'] for r in result['rows']}=={'process:checkout','process:other'}
    assert len({r['selection_id'] for r in result['rows']})==2
    assert all(r['members'][0]['current']['lifecycle']=='REVIEWED' for r in result['rows'])
    assert (a,b)==before


def test_candidate_never_becomes_approved_or_runtime_available(tmp_path):
    p=process();result=catalog(tmp_path,inventory(p),current_processes=[p]);current=result['rows'][0]['members'][0]['current']
    assert current['lifecycle']=='CANDIDATE' and current['review']['effective_status']=='EMPTY'
    assert current['review']['active_annotations']==[]
    assert current['triggers'][0]['execution_status']=='UNKNOWN'
    assert not (tmp_path/'.kgmaker').exists()


def test_removed_trigger_keeps_inactive_historical_record_qualified_by_inventory(tmp_path):
    p=process();packet=prepare_process_label_packet(p)['packet'];write(tmp_path,p,packet,proposed(packet))
    result=catalog(tmp_path,inventory(),historical_processes=[p]);member=result['rows'][0]['members'][0]
    assert member['current'] is None and len(member['historical'])==1
    record=member['historical'][0]
    assert record['lifecycle']=='HISTORICAL' and record['in_current_selection'] is False
    assert record['triggers'][0]['presence']=='NOT_IN_CURRENT_INVENTORY'
    assert record['review']['active_annotations']==[] and record['review']['history'][0]['action']=='APPROVE'
    assert result['inventory_coverage']['status']=='UNKNOWN'


def test_explicit_alias_keeps_original_members_and_does_not_borrow_approval(tmp_path):
    a=process();b=process('process:alias','request:alias')
    packet=prepare_process_label_packet(a)['packet'];write(tmp_path,a,packet,proposed(packet))
    result=catalog(tmp_path,inventory(a,b),current_processes=[a,b],aliases=[{'alias_process_id':b['process_id'],'canonical_process_id':a['process_id']}])
    assert len(result['rows'])==1
    members={m['process_id']:m['current'] for m in result['rows'][0]['members']}
    assert members[a['process_id']]['lifecycle']=='REVIEWED' and members[b['process_id']]['lifecycle']=='CANDIDATE'
    assert members[b['process_id']]['review']['active_annotations']==[]
    assert 'active_annotations' not in result['rows'][0]


def test_stale_review_remains_readable_but_not_current_approval(tmp_path):
    p=process();packet=prepare_process_label_packet(p)['packet'];write(tmp_path,p,packet,proposed(packet))
    p['technical_view']['nodes'][0]['label']='Changed technical text'
    result=catalog(tmp_path,inventory(p),current_processes=[p]);current=result['rows'][0]['members'][0]['current']
    assert current['lifecycle']=='NEEDS_REVALIDATION'
    assert current['review']['effective_status']=='NEEDS_REVALIDATION' and current['review']['active_annotations']==[]


def test_ambiguous_current_identity_rejected_without_any_write(tmp_path):
    a=process();b=deepcopy(a);b['technical_view']['nodes'][0]['label']='Different content'
    with pytest.raises(api().ProcessCatalogError,match='CONFLICTING_PROCESS_SNAPSHOT'):
        catalog(tmp_path,inventory(a),current_processes=[a,b])
    assert list(tmp_path.iterdir())==[]


def test_exact_duplicates_deduplicate_and_selection_survives_order_and_revision(tmp_path):
    a=process();b=process('process:other','request:other');inv=inventory(a,b)
    first=catalog(tmp_path,inv,current_processes=[a,b,a])
    second=catalog(tmp_path,inv,current_processes=[b,a])
    assert first==second and first['counts']['members']==2
    newer=process(revision=4)
    third=catalog(tmp_path,inv,current_processes=[newer,b],historical_processes=[a,a])
    assert third['rows'][0]['selection_id']==first['rows'][0]['selection_id']
    member=third['rows'][0]['members'][0]
    assert member['current']['revision']==4 and [r['revision'] for r in member['historical']]==[3]
    assert third['counts']['historical_snapshots']==1


def test_one_process_declares_multiple_exact_triggers_without_implicit_merge(tmp_path):
    a=process();b=process('process:other','request:other');add_trigger(a,'request:other')
    result=catalog(tmp_path,inventory(process(),b),current_processes=[a,b])
    assert len(result['rows'])==2
    current=result['rows'][0]['members'][0]['current']
    assert [t['id'] for t in current['triggers']]==['request','request:other']


def test_some_missing_triggers_keep_per_reference_status_and_no_active_labels(tmp_path):
    p=process();add_trigger(p,'request:missing')
    packet=prepare_process_label_packet(p)['packet'];write(tmp_path,p,packet,proposed(packet))
    record=catalog(tmp_path,inventory(process()),current_processes=[p])['rows'][0]['members'][0]['current']
    assert [t['presence'] for t in record['triggers']]==['PRESENT','NOT_IN_CURRENT_INVENTORY']
    assert record['lifecycle']=='HISTORICAL' and not record['in_current_selection']
    assert record['review']['active_annotations']==[]


@pytest.mark.parametrize('aliases',[
    [{'alias_process_id':'process:checkout','canonical_process_id':'unknown'}],
    [{'alias_process_id':'process:checkout','canonical_process_id':'process:checkout'}],
    [{'alias_process_id':'process:checkout','canonical_process_id':'process:b'},
     {'alias_process_id':'process:b','canonical_process_id':'process:c'}],
    [{'alias_process_id':'process:checkout','canonical_process_id':'process:b'},
     {'alias_process_id':'process:b','canonical_process_id':'process:checkout'}],
    [{'alias_process_id':'process:checkout','canonical_process_id':'process:b'},
     {'alias_process_id':'process:checkout','canonical_process_id':'process:c'}],
])
def test_alias_unknown_self_chain_cycle_and_multiple_winners_rejected(tmp_path,aliases):
    a=process();b=process('process:b','request:b');c=process('process:c','request:c')
    with pytest.raises(api().ProcessCatalogError,match='INVALID_ALIAS'):
        catalog(tmp_path,inventory(a,b,c),current_processes=[a,b,c],aliases=aliases)
    assert list(tmp_path.iterdir())==[]


def test_aliases_cannot_borrow_context_selection_or_cross_scope(tmp_path):
    a=process();b=process('process:b','request:b');b['definition']['context_selection']={'other':['ctx-prod']}
    b['technical_view']['context_selection']={'other':['ctx-prod']}
    b['definition_fingerprint']=ProcessDefinition.from_dict(b['definition']).content_fingerprint
    with pytest.raises(api().ProcessCatalogError,match='ALIAS_CONTEXT_MISMATCH'):
        catalog(tmp_path,inventory(a,b),current_processes=[a,b],aliases=[{'alias_process_id':b['process_id'],'canonical_process_id':a['process_id']}])


def test_alias_keeps_all_explicit_revisions_without_arbitrary_payload_winner(tmp_path):
    a=process();old=process(revision=2);b=process('process:b','request:b')
    packet=prepare_process_label_packet(a)['packet'];write(tmp_path,a,packet,proposed(packet,label='První'))
    packet=prepare_process_label_packet(b)['packet'];write(tmp_path,b,packet,proposed(packet,label='Druhý'))
    result=catalog(tmp_path,inventory(a,b),current_processes=[b,a],historical_processes=[old],
        aliases=[{'alias_process_id':b['process_id'],'canonical_process_id':a['process_id']}])
    row=result['rows'][0]
    assert row['member_ids']==['process:b','process:checkout']
    assert {m['current']['review']['active_annotations'][0]['label'] for m in row['members']}=={'První','Druhý'}
    assert [r['revision'] for m in row['members'] for r in m['historical']]==[2]
    assert 'label' not in row and 'active_annotations' not in row


def test_conflicting_same_revision_in_current_history_rejected(tmp_path):
    a=process();b=deepcopy(a);b['technical_view']['nodes'][0]['label']='Conflicting old snapshot'
    with pytest.raises(api().ProcessCatalogError,match='CONFLICTING_PROCESS_SNAPSHOT'):
        catalog(tmp_path,inventory(a),current_processes=[a],historical_processes=[b])


def test_two_different_current_revisions_are_not_chosen_by_max_or_input_order(tmp_path):
    a=process();b=process(revision=4)
    for rows in ([a,b],[b,a]):
        with pytest.raises(api().ProcessCatalogError,match='CONFLICTING_PROCESS_SNAPSHOT'):
            catalog(tmp_path,inventory(a),current_processes=rows)


def test_plain_and_typed_inventory_process_snapshots_are_equivalent(tmp_path):
    from kgmaker.architecture_model import ViewDocument
    from kgmaker.process_model import ProcessView
    p=process();inv=inventory(p)
    assert catalog(tmp_path,inv,current_processes=[p])==catalog(tmp_path,ViewDocument.from_dict(inv),current_processes=[ProcessView.from_dict(p)])


@pytest.mark.parametrize('case',['stale','context','scope'])
def test_stale_foreign_context_or_scope_trigger_never_borrows_active_review(tmp_path,case):
    p=process();packet=prepare_process_label_packet(p)['packet'];write(tmp_path,p,packet,proposed(packet));inv=inventory(p)
    if case=='stale':inv['nodes'][0]['freshness']='STALE'
    elif case=='context':inv['nodes'][0]['attributes']['context_ids']=['ctx-other']
    else:inv['nodes'][0]['attributes']['scope']='test'
    if case=='scope':
        with pytest.raises(api().ProcessCatalogError):catalog(tmp_path,inv,current_processes=[p])
    else:
        record=catalog(tmp_path,inv,current_processes=[p])['rows'][0]['members'][0]['current']
        assert not record['in_current_selection'] and record['review']['active_annotations']==[]
        assert record['lifecycle']=='HISTORICAL'


def test_technical_coverage_outcomes_owner_and_uncertainty_are_not_reviewed_into_runtime(tmp_path):
    p=process();p['technical_status']=p['technical_view']['coverage']['status']='PARTIAL'
    inv=inventory(p);inv['nodes'][0]['owner_id']=None
    inv['nodes'][0]['attributes'].update(owner_status='AMBIGUOUS',candidate_owner_ids=['orders','billing'])
    result=catalog(tmp_path,inv,current_processes=[p]);record=result['rows'][0]['members'][0]['current']
    assert record['technical_status']==p['technical_status']=='PARTIAL'
    assert record['outcome_ids']==['done'] and record['outcomes'][0]['original_ids']==['origin:done']
    assert record['outcomes'][0]['evidence_kinds']==['SYMBOL_RESOLVED']
    assert record['triggers'][0]['owner_id'] is None and record['triggers'][0]['owner_status']=='AMBIGUOUS'
    assert record['triggers'][0]['candidate_owner_ids']==['billing','orders']
    assert result['data_availability']==record['data_availability']=='UNKNOWN'


def test_raw_technical_prose_and_config_never_exported_but_bound(tmp_path):
    p=process();p['technical_view']['nodes'][0]['label']='PRIVATE_RAW_CATALOG_SENTINEL'
    p['technical_view']['nodes'][0]['attributes']['proof_prose']='PRIVATE_RAW_CATALOG_SENTINEL'
    inv=inventory(p);inv['nodes'][0]['label']='PRIVATE_RAW_CATALOG_SENTINEL'
    result=catalog(tmp_path,inv,current_processes=[p])
    assert 'PRIVATE_RAW_CATALOG_SENTINEL' not in json.dumps(result)
    assert result['rows'][0]['members'][0]['current']['process_content_hash']


@pytest.mark.parametrize('case',['process','inventory','alias','review_input'])
def test_secret_malformed_keys_are_not_reflected_in_errors(tmp_path,case):
    p=process();inv=inventory(p);kwargs={'current_processes':[p]};secret='PRIVATE_CATALOG_KEY_72bb'
    if case=='process':p[secret]='x'
    elif case=='inventory':inv[secret]='x'
    elif case=='alias':kwargs['aliases']=[{secret:'x'}]
    else:kwargs['review_inputs']=[{secret:'x'}]
    with pytest.raises(api().ProcessCatalogError) as e:catalog(tmp_path,inv,**kwargs)
    assert secret not in repr(e.value) and e.value.__cause__ is None
    assert list(tmp_path.iterdir())==[]


def test_forged_approved_bundle_is_not_an_api_input(tmp_path):
    p=process()
    with pytest.raises(api().ProcessCatalogError,match='INVALID_REVIEW_INPUTS'):
        catalog(tmp_path,inventory(p),current_processes=[p],review_inputs=[{'process_id':p['process_id'],'approved':True}])


def test_direct_reader_honors_doc_bindings_and_changed_capture_requires_revalidation(tmp_path):
    from test_t030_prepare_process_label_packet import document
    from kgmaker.process_store import prepare_process_review,persist_process_review
    p=process();docs=[document()];packet=prepare_process_label_packet(p,documents=docs)['packet'];c=proposed(packet,source_refs=['doc:guide'])
    prepared=prepare_process_review(p,packet,c,documents=docs)
    persist_process_review(tmp_path,p,packet,c,documents=docs,action='APPROVE',reviewer='local:reviewer',operation_id='op:doc',expected_head=None,
        expected_payload_hash=prepared['payload_hash'],expected_baseline_hash=prepared['baseline_hash'])
    current=catalog(tmp_path,inventory(p),current_processes=[p],review_inputs=[{'process_id':p['process_id'],'documents':docs,'conflicts':[]}])['rows'][0]['members'][0]['current']
    assert current['review']['active_annotations'][0]['source_refs']==['doc:guide']
    changed=catalog(tmp_path,inventory(p),current_processes=[p])['rows'][0]['members'][0]['current']
    assert changed['lifecycle']=='NEEDS_REVALIDATION' and changed['review']['active_annotations']==[]


def test_empty_store_catalog_performs_no_writes_process_execution_or_network(tmp_path,monkeypatch):
    import subprocess,socket,os
    p=process();inv=inventory(p);before=deepcopy((p,inv))
    def forbidden(*args,**kwargs):raise AssertionError('unexpected external action')
    monkeypatch.setattr(subprocess,'Popen',forbidden);monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(os,'replace',forbidden);monkeypatch.setattr(Path,'mkdir',forbidden)
    catalog(tmp_path,inv,current_processes=[p]);assert (p,inv)==before
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('limit',['snapshots','output','cyclic'])
def test_resource_caps_fail_before_implicit_store_changes(tmp_path,monkeypatch,limit):
    p=process();inv=inventory(p);rows=[p]
    if limit=='snapshots':monkeypatch.setattr(api(),'MAX_SNAPSHOTS',1);rows=[p,p]
    elif limit=='output':monkeypatch.setattr(api(),'MAX_OUTPUT_BYTES',10)
    else:p['loop']=p
    with pytest.raises(api().ProcessCatalogError):catalog(tmp_path,inv,current_processes=rows)
    assert list(tmp_path.iterdir())==[]


def test_boundary_and_truncation_survive_without_raw_diagnostic_prose(tmp_path):
    p=process();p['technical_status']=p['technical_view']['coverage']['status']='PARTIAL'
    p['technical_view']['coverage']['truncated']=True
    p['technical_view']['diagnostics']=[{'code':'BUDGET_BOUNDARY','message':'PRIVATE_DIAGNOSTIC_SENTINEL'}]
    result=catalog(tmp_path,inventory(p),current_processes=[p]);record=result['rows'][0]['members'][0]['current']
    assert record['uncertainty']['truncated'] and 'send' in record['uncertainty']['target_ids']
    assert record['uncertainty']['diagnostic_count']==1 and record['uncertainty']['diagnostics_hash']
    assert record['omissions'][0]['reason']=='RAW_TECHNICAL_PROSE_OMITTED'
    assert 'PRIVATE_DIAGNOSTIC_SENTINEL' not in json.dumps(result)


def test_duplicate_inventory_trigger_ids_rejected_instead_of_arbitrary_last(tmp_path):
    p=process();inv=inventory(p);inv['nodes'].append(deepcopy(inv['nodes'][0]))
    with pytest.raises(api().ProcessCatalogError):catalog(tmp_path,inv,current_processes=[p])


def test_valid_unicode_space_process_identity_keeps_original_and_stable_selection(tmp_path):
    p=process('process:Česká cesta/orders checkout.kt')
    record=catalog(tmp_path,inventory(p),current_processes=[p])['rows'][0]
    assert record['process_id']==record['member_ids'][0]==p['process_id']
    assert record['selection_id'].startswith('process-selection:')

"""T031 validates proposals against current explicit input, never applies them."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.process_model import ProcessView, ProcessDefinition
from kgmaker.process_semantics import prepare_process_label_packet
from test_t023_define_business_process_model import sample_process
from test_t030_prepare_process_label_packet import document

SENTINEL = 'PRIVATE_VALIDATOR_SENTINEL_148f'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def validate(*args, **kwargs):
    from kgmaker.process_semantics import validate_process_annotations
    return validate_process_annotations(*args, **kwargs)


def proposed(packet, **changes):
    candidate={'schema_version':1,'packet_hash':packet['packet_hash'],'annotations':[
        {'id':'proposal:ověřit 1','target_id':'card','label':'Ověřit objednávku',
         'description':'Zkontrolovat podklady objednávky.','source_refs':['origin:card','ev:card'],
         'semantic_review_status':'PROPOSED'}]}
    candidate['annotations'][0].update(changes)
    return candidate


def rejected(report):
    assert report['valid'] is False and report['validation_status']=='REJECTED'
    assert report['annotations']==[] and report['diagnostics']
    assert report['review_status'] in {'PENDING','CONFLICT'}
    assert SENTINEL not in canonical(report)


def rebind(source):
    source['definition_fingerprint']=ProcessDefinition.from_dict(source['definition']).content_fingerprint


def test_valid_czech_label_group_and_existing_outcome_are_only_proposed_without_technical_change():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet,grouping_proposal=['cash','card'])
    candidate['annotations'].append({'id':'proposal:outcome','target_id':'done','label':'Objednávka dokončena',
        'source_refs':['origin:done'],'semantic_review_status':'PROPOSED'})
    before=deepcopy((source,packet,candidate));technical=canonical(source['technical_view'])
    report=validate(ProcessView.from_dict(source),packet,candidate)
    assert report['valid'] is True and report['validation_status']=='VALID'
    assert report['review_status']=='PENDING' and report['requires_review'] is True
    assert {a['semantic_review_status'] for a in report['annotations']}=={'PROPOSED'}
    label=next(a for a in report['annotations'] if a['target_id']=='card')
    assert label['label']=='Ověřit objednávku' and label['grouping_proposal']==['card','cash']
    assert report['technical_binding']['technical_fingerprint']==ProcessView.from_dict(source).technical_fingerprint
    assert report['packet_hash']==packet['packet_hash'] and report['technical_status']==source['technical_status']
    assert any(i['kind']=='GROUPING_REQUIRES_REVIEW' for i in report['review_items'])
    assert (source,packet,candidate)==before and canonical(source['technical_view'])==technical


@pytest.mark.parametrize('field,value',[('target_id','invented'),('source_refs',['proof:foreign']),('grouping_proposal',['pay-card']),('grouping_proposal',['origin:card'])])
def test_forged_targets_sources_and_nonstep_groups_are_rejected(field,value):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet,**{field:value})
    before=deepcopy((source,packet,candidate));rejected(validate(source,packet,candidate));assert (source,packet,candidate)==before


@pytest.mark.parametrize('case',['target','source','group','evidence'])
def test_self_rehashed_poisoned_packet_cannot_define_its_own_authority(case):
    source=sample_process();packet=prepare_process_label_packet(source)['packet']
    if case=='target':packet['allowed_target_ids'].append('invented')
    elif case=='source':packet['allowed_source_refs'].append('foreign')
    elif case=='group':packet['annotation_schema']['grouping_target_ids'].append('invented')
    else:packet['technical_inventory'][0]['evidence_kinds']=['RUNTIME_OBSERVED']
    packet['packet_hash']=hashlib.sha256(canonical({k:v for k,v in packet.items() if k!='packet_hash'}).encode()).hexdigest()
    report=validate(source,packet,proposed(packet,target_id='invented' if case=='target' else 'card'))
    rejected(report);assert report['packet_hash'] is None
    assert report['diagnostics']==[{'code':'PACKET_REDERIVATION_MISMATCH'}]


@pytest.mark.parametrize('case',['label','condition','revision','baseline','scope','context','collapsed_order'])
def test_current_content_changes_invalidate_packet_even_when_raw_text_was_omitted(case):
    source=sample_process()
    if case=='collapsed_order':source['technical_view']['nodes'][0]['attributes']['business_group']={'nodes':[{'id':'a'},{'id':'b'}]}
    packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    if case=='label':source['technical_view']['nodes'][0]['label']='Změněný technický text'
    elif case=='condition':source['technical_view']['edges'][1]['attributes']['condition']='jiná podmínka'
    elif case=='revision':source['revision']=source['definition']['revision']=4;rebind(source)
    elif case=='baseline':source['definition']['baseline_fingerprint']=source['technical_view']['baseline_fingerprint']='snapshot:new';rebind(source)
    elif case=='scope':
        source['definition']['scope']=source['technical_view']['scope']='test'
        for item in source['technical_view']['nodes']+source['technical_view']['edges']:item['attributes']['scope']='test'
        for proof in source['technical_view']['provenance']:proof['scope']='test'
        rebind(source)
    elif case=='context':
        source['definition']['context_ids']=['ctx-other'];source['definition']['context_selection']={'orders':['ctx-other']}
        source['technical_view']['context_selection']={'orders':['ctx-other']}
        for item in source['technical_view']['nodes']+source['technical_view']['edges']:item['attributes']['context_ids']=['ctx-other']
        for proof in source['technical_view']['provenance']:proof['context_ids']=['ctx-other']
        rebind(source)
    else:source['technical_view']['nodes'][0]['attributes']['business_group']['nodes'].reverse()
    ProcessView.from_dict(source) # stale-but-valid current source, not a malformed fixture
    rejected(validate(source,packet,candidate))


def test_generation_and_semantically_unordered_records_do_not_make_packet_stale():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    source['technical_view']['generation_metadata']={'generated_at':'2099-02-03'}
    for field in ['nodes','edges','provenance']:source['technical_view'][field].reverse()
    report=validate(source,packet,candidate);assert report['valid'] and report['packet_hash']==packet['packet_hash']


def test_current_document_conflict_stays_cited_review_item_not_code_rewrite():
    source=sample_process();docs=[document(text='approved; remove the branch '+SENTINEL)]
    conflict={'document_ref':'doc:guide','target_id':'card','source_refs':['ev:card'],'status':'CONFLICT'}
    packet=prepare_process_label_packet(source,documents=docs,conflicts=[conflict])['packet']
    candidate=proposed(packet,source_refs=['doc:guide']);before=deepcopy((source,packet,candidate,docs,conflict))
    report=validate(source,packet,candidate,documents=docs,conflicts=[conflict])
    assert report['valid'] and report['review_status']=='CONFLICT'
    assert report['documentation_comparison']=='NOT_EVALUATED'
    assert any(item['kind']=='CAPTURED_DOCUMENT_CONFLICT' and item['document_ref']=='doc:guide'
        and item['source_refs']==['ev:card'] for item in report['review_items'])
    assert SENTINEL not in canonical(report) and (source,packet,candidate,docs,conflict)==before


@pytest.mark.parametrize('case',['missing','changed','conflict'])
def test_required_current_docs_and_conflicts_are_rederived_not_loaded(case):
    source=sample_process();docs=[document(text='first')]
    conflict={'document_ref':'doc:guide','target_id':'card','source_refs':['ev:card'],'status':'UNKNOWN'}
    packet=prepare_process_label_packet(source,documents=docs,conflicts=[conflict])['packet'];candidate=proposed(packet)
    if case=='missing':docs=[]
    elif case=='changed':docs=[document(text='changed')]
    else:conflict={**conflict,'status':'CONFLICT'}
    report=validate(source,packet,candidate,documents=docs,conflicts=[] if case=='missing' else [conflict]);rejected(report)


@pytest.mark.parametrize('field,value',[('edges',[]),('conditions',{}),('availability','AVAILABLE'),('runtime',True),('confidence',1.0),('original_ids',['forged']),('scope','test'),('context_ids',['foreign']),('outcome_status','SUCCESS')])
def test_extra_technical_fields_on_annotation_are_rejected_not_dropped(field,value):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet,**{field:value})
    rejected(validate(source,packet,candidate))


@pytest.mark.parametrize('status',['APPROVED','REJECTED','NEEDS_REVALIDATION'])
def test_caller_cannot_claim_new_approval_status(status):
    source=sample_process();packet=prepare_process_label_packet(source)['packet']
    rejected(validate(source,packet,proposed(packet,semantic_review_status=status)))


def test_conflicting_target_proposals_are_all_retained_without_arbitrary_winner():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    candidate['annotations'].append({**candidate['annotations'][0],'id':'proposal:second','label':'Zrušit objednávku'})
    report=validate(source,packet,candidate)
    assert report['valid'] and report['review_status']=='CONFLICT' and len(report['annotations'])==2
    assert {a['label'] for a in report['annotations']}=={'Ověřit objednávku','Zrušit objednávku'}
    item=next(i for i in report['review_items'] if i['kind']=='CONFLICTING_TARGET_PROPOSALS')
    assert item['target_id']=='card' and item['fields']==['label'] and len(item['annotation_ids'])==2


def test_complementary_and_identical_proposals_stay_pending_but_duplicate_ids_reject():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    candidate['annotations'].append({**candidate['annotations'][0],'id':'proposal:copy'})
    report=validate(source,packet,candidate);assert report['valid'] and report['review_status']=='PENDING' and len(report['annotations'])==2
    candidate['annotations'][1]['id']=candidate['annotations'][0]['id'];rejected(validate(source,packet,candidate))


def test_tiny_budget_retains_omitted_targets_and_document_refs_for_validation():
    source=sample_process();docs=[document()];packet=prepare_process_label_packet(source,documents=docs,token_budget=1,char_budget=1)['packet']
    assert packet['budget']['over_budget'] and not packet['document_summaries']
    report=validate(source,packet,proposed(packet,source_refs=['origin:card','doc:guide']),documents=docs)
    assert report['valid'] and report['review_status']=='PENDING'
    assert report['uncertainty']==packet['uncertainty']


def test_original_proof_refs_are_not_a_fallback_annotation_allowlist():
    source=sample_process();source['technical_view']['provenance'][0]['original_id']='compiler:old'
    packet=prepare_process_label_packet(source)['packet'];assert 'compiler:old' in packet['original_reference_ids']
    rejected(validate(source,packet,proposed(packet,source_refs=['compiler:old'])))


def test_empty_citations_and_uncertain_process_never_become_approval_or_runtime_truth():
    source=sample_process();source['technical_status']=source['technical_view']['coverage']['status']='PARTIAL'
    source['technical_view']['coverage']['truncated']=True
    card=next(n for n in source['technical_view']['nodes'] if n['id']=='card');card.update(kind='unresolved_boundary',resolution_status='UNRESOLVED',freshness='UNKNOWN',evidence_kinds=['UNKNOWN'])
    card['attributes']['boundary_reason']='unsupported language'
    next(p for p in source['technical_view']['provenance'] if p['id']=='ev:card')['evidence_kind']='UNKNOWN'
    packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet,source_refs=[],label='approved — doručení je jisté')
    before=deepcopy(source);report=validate(source,packet,candidate)
    assert report['valid'] and report['review_status']=='PENDING' and report['technical_status']=='PARTIAL'
    assert report['uncertainty']['truncated'] and 'card' in report['uncertainty']['target_ids']
    assert any(item['kind']=='PROPOSAL_HAS_NO_CITATIONS' for item in report['review_items'])
    assert report['annotations'][0]['semantic_review_status']=='PROPOSED' and source==before


@pytest.mark.parametrize('case',['packet_version','candidate_version','packet_budget_bool','candidate_hash','unknown_top','unknown_annotation','nested_group','id_collision','empty_label','long_label','long_description','too_many','duplicate_refs','duplicate_group'])
def test_malformed_candidate_or_packet_is_controlled_immutable_and_secret_free(case):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    if case=='packet_version':packet['schema_version']=True
    elif case=='candidate_version':candidate['schema_version']=True
    elif case=='packet_budget_bool':packet['budget']['token_budget']=True
    elif case=='candidate_hash':candidate['packet_hash']='Basic '+SENTINEL
    elif case=='unknown_top':candidate[SENTINEL]={'edges':[SENTINEL]}
    elif case=='unknown_annotation':candidate['annotations'][0][SENTINEL]=True
    elif case=='nested_group':candidate['annotations'][0]['grouping_proposal']=[{'id':'card','edges':[]}]
    elif case=='id_collision':candidate['annotations'][0]['id']='card'
    elif case=='empty_label':candidate['annotations'][0]['label']='  '
    elif case=='long_label':candidate['annotations'][0]['label']='x'*513
    elif case=='long_description':candidate['annotations'][0]['description']='x'*4097
    elif case=='too_many':candidate['annotations']=[{**candidate['annotations'][0],'id':'annotation:'+str(i)} for i in range(257)]
    elif case=='duplicate_refs':candidate['annotations'][0]['source_refs']=['ev:card','ev:card']
    else:candidate['annotations'][0]['grouping_proposal']=['card','card']
    before=deepcopy((source,packet,candidate));rejected(validate(source,packet,candidate));assert (source,packet,candidate)==before


@pytest.mark.parametrize('text',['password='+SENTINEL,'//alice:'+SENTINEL+'@host/path','Basic '+SENTINEL,'Bearer '+SENTINEL,'nul\x00'+SENTINEL])
def test_recognized_credentials_and_controls_are_rejected_without_echo(text):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet,label=text)
    rejected(validate(source,packet,candidate))


def test_readonly_validation_performs_no_file_model_network_process_apply_or_grouping_io(tmp_path):
    from kgmaker.process_semantics import validate_process_annotations
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    saved=tmp_path/'last-valid';saved.write_text('previous');before=deepcopy((source,packet,candidate))
    with patch('builtins.open',side_effect=AssertionError('file IO')),patch.object(Path,'read_bytes',side_effect=AssertionError('file IO')),patch.object(Path,'write_text',side_effect=AssertionError('file IO')),patch('subprocess.Popen',side_effect=AssertionError('process')),patch('socket.socket',side_effect=AssertionError('network')),patch('kgmaker.feature.prepare',side_effect=AssertionError('feature IO')),patch('kgmaker.business_process.collapse_business_steps',side_effect=AssertionError('collapse')):
        report=validate_process_annotations(source,packet,candidate)
    assert report['valid'] and (source,packet,candidate)==before
    assert saved.read_text()=='previous' and list(tmp_path.iterdir())==[saved]


@pytest.mark.parametrize('case',['cycle','deep','shared','nonjson'])
def test_bounds_precede_model_copy_and_produce_controlled_invalid_reports(case):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    if case=='cycle':candidate['bad']=candidate
    elif case=='deep':
        child={};candidate['bad']=child
        for _ in range(80):child['next']={};child=child['next']
    elif case=='shared':candidate['bad']=['x'*1000]*5000
    else:candidate['bad']=object()
    with patch.object(ProcessView,'from_dict',side_effect=AssertionError('copy before bounds')):
        report=validate(source,packet,candidate)
    rejected(report)


def test_invalid_later_annotation_returns_no_partially_accepted_proposals():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    candidate['annotations'].append({**candidate['annotations'][0],'id':'proposal:unsafe','label':'password='+SENTINEL})
    before=deepcopy(candidate);report=validate(source,packet,candidate);rejected(report)
    assert candidate==before and not any(i['kind']=='PROPOSAL_REQUIRES_REVIEW' for i in report['review_items'])


def test_complementary_fields_and_empty_template_are_pending_not_approval():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    del candidate['annotations'][0]['description']
    candidate['annotations'].append({'id':'proposal:description','target_id':'card','description':'Doplnit podklady.',
        'source_refs':['card'],'semantic_review_status':'PROPOSED'})
    report=validate(source,packet,candidate)
    assert report['valid'] and report['review_status']=='PENDING' and len(report['annotations'])==2
    empty=validate(source,packet,{'schema_version':1,'packet_hash':packet['packet_hash'],'annotations':[]})
    assert empty['valid'] and empty['annotations']==[] and empty['review_status']=='PENDING'


@pytest.mark.parametrize('case',['packet-null','candidate-null','annotations-null','process-key','document-prose'])
def test_supported_malformed_inputs_return_invalid_report_instead_of_exceptions(case):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet);docs=[]
    if case=='packet-null':packet=None
    elif case=='candidate-null':candidate=None
    elif case=='annotations-null':candidate['annotations']=None
    elif case=='process-key':source['technical_view'][SENTINEL]='bad'
    else:
        docs=[document()];docs[0]['selection_provenance']={'note':SENTINEL}
    before=deepcopy((source,packet,candidate,docs));report=validate(source,packet,candidate,documents=docs)
    rejected(report);assert (source,packet,candidate,docs)==before


def test_existing_approved_prose_is_hash_bound_but_not_new_approval_or_exported_text():
    source=sample_process();source['semantic_annotations']=[{'id':'old:label','target_id':'card','label':SENTINEL,
        'source_refs':['card'],'semantic_review_status':'APPROVED'}]
    packet=prepare_process_label_packet(source)['packet'];before=deepcopy(source)
    report=validate(source,packet,proposed(packet))
    assert report['valid'] and report['review_status']=='PENDING'
    assert {a['semantic_review_status'] for a in report['annotations']}=={'PROPOSED'}
    assert SENTINEL not in canonical(report) and source==before


@pytest.mark.parametrize('case',['packet-rule','packet-schema','packet-hash','candidate-schema'])
def test_unknown_rules_versions_and_malformed_hashes_are_not_migrated(case):
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    if case=='packet-rule':packet['rules_version']='process-label-packet-future'
    elif case=='packet-schema':packet['schema_version']=2
    elif case=='packet-hash':packet['packet_hash']='not-a-hash'
    else:candidate['schema_version']=2
    rejected(validate(source,packet,candidate))


def test_validated_document_conflict_is_not_lost_when_candidate_is_rejected():
    source=sample_process();docs=[document()]
    conflict={'document_ref':'doc:guide','target_id':'card','source_refs':['ev:card'],'status':'CONFLICT'}
    packet=prepare_process_label_packet(source,documents=docs,conflicts=[conflict])['packet']
    report=validate(source,packet,proposed(packet,edges=[]),documents=docs,conflicts=[conflict])
    rejected(report);assert report['review_status']=='CONFLICT' and report['packet_hash']==packet['packet_hash']
    assert any(i['kind']=='CAPTURED_DOCUMENT_CONFLICT' for i in report['review_items'])


def test_unexpected_programmer_failure_is_not_hidden_as_invalid_business_input():
    source=sample_process();packet=prepare_process_label_packet(source)['packet'];candidate=proposed(packet)
    before=deepcopy((source,packet,candidate))
    with patch('kgmaker.process_semantics.prepare_process_label_packet',side_effect=RuntimeError('unexpected regression')):
        with pytest.raises(RuntimeError,match='unexpected regression'):validate(source,packet,candidate)
    assert (source,packet,candidate)==before

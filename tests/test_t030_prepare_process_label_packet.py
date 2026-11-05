"""T030 public pure packets preserve authority without exporting prose."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.process_model import ProcessView, ProcessDefinition
from test_t023_define_business_process_model import sample_process

SENTINEL = 'PRIVATE_SENTINEL_56fa19'

def prepare(*args, **kwargs):
    from kgmaker.process_semantics import prepare_process_label_packet
    return prepare_process_label_packet(*args, **kwargs)

def serialized(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def cost(value):
    text = serialized(value)
    return {'characters': len(text), 'utf8_bytes': len(text.encode()), 'tokens': (len(text.encode()) + 3) // 4}

def document(ref='doc:guide', text='Untrusted instructions '+SENTINEL):
    return {'ref': ref, 'format': 'HTML', 'content_hash': hashlib.sha256(text.encode()).hexdigest(),
        'scope': 'production', 'context_ids': ['ctx-prod'],
        'selection_provenance': {'capture_id': 'capture:guide', 'source_ref': ref}, 'content': text}


def test_identity_template_and_original_proofs_are_complete_without_new_targets():
    source = sample_process(); before = deepcopy(source)
    result = prepare(ProcessView.from_dict(source)); packet = result['packet']; template = result['candidate_template']
    expected = {'process:checkout', 'request', 'choose', 'card', 'cash', 'retry', 'send', 'done',
        'start', 'pay-card', 'pay-cash', 'card-retry', 'try-again', 'card-send', 'cash-send', 'dispatch'}
    assert packet['allowed_target_ids'] == sorted(expected)
    assert packet['identity']['process_id'] == 'process:checkout' and packet['identity']['revision'] == 3
    assert packet['identity']['baseline_fingerprint'] == 'snapshot:checkout-v3'
    assert packet['identity']['context_ids'] == ['ctx-prod']
    assert packet['identity']['context_selection'] == {'orders': ['ctx-prod']}
    assert packet['entry_ids'] == ['request'] and packet['outcome_ids'] == packet['exit_ids'] == ['done']
    assert {'ev:card', 'origin:card', 'card'} <= set(packet['allowed_source_refs'])
    card = next(n for n in packet['technical_inventory'] if n['id'] == 'card')
    assert card['original_ids'] == ['origin:card'] and card['evidence_refs'] == ['ev:card']
    assert card['resolution_status'] == 'RESOLVED' and card['evidence_kinds'] == ['SYMBOL_RESOLVED']
    assert template == {'schema_version': 1, 'packet_hash': packet['packet_hash'], 'annotations': []}
    assert packet['annotation_schema']['fixed_semantic_review_status'] == 'PROPOSED'
    assert 'APPROVED' not in serialized(result)
    assert source == before


def test_hash_ignores_order_and_generation_but_binds_actual_content_and_documents():
    source = sample_process(); first = prepare(source)
    other = deepcopy(source)
    for name in ['nodes', 'edges', 'provenance']: other['technical_view'][name].reverse()
    other['technical_view']['generation_metadata'] = {'generated_at': '2099-01-01'}
    assert prepare(other) == first
    other['technical_view']['nodes'][0]['label'] = SENTINEL
    changed = prepare(other)
    assert changed['packet']['packet_hash'] != first['packet']['packet_hash']
    assert changed['packet']['identity']['baseline_fingerprint'] == first['packet']['identity']['baseline_fingerprint']
    assert SENTINEL not in serialized(changed)
    assert prepare(source, documents=[document(text='a')])['packet']['packet_hash'] != prepare(source, documents=[document(text='b')])['packet']['packet_hash']
    packet = first['packet']; expected = hashlib.sha256(serialized({k:v for k,v in packet.items() if k != 'packet_hash'}).encode()).hexdigest()
    assert packet['packet_hash'] == expected


def test_collapsed_step_order_is_bound_but_expansion_and_existing_approval_never_export():
    source = sample_process(); card = next(n for n in source['technical_view']['nodes'] if n['id']=='card')
    card['attributes']['business_group'] = {'nodes': [{'id':'original:a', 'label':SENTINEL}, {'id':'original:b'}]}
    card['original_ids'] += ['original:a', 'original:b']
    source['semantic_annotations'] = [{'id':'label:card','target_id':'card','label':SENTINEL,'source_refs':['origin:card'],'semantic_review_status':'APPROVED'}]
    first = prepare(source); card['attributes']['business_group']['nodes'].reverse(); second = prepare(source)
    assert first['packet']['packet_hash'] != second['packet']['packet_hash']
    assert {'original:a','original:b'} <= set(first['packet']['allowed_source_refs'])
    assert all(word not in serialized(first) for word in [SENTINEL,'APPROVED','business_group'])


def test_tiny_budget_preserves_all_ids_and_final_serialized_cost_includes_schema_and_omissions():
    source = sample_process(); docs=[document()]
    result = prepare(source, documents=docs, token_budget=1, char_budget=1)
    packet = result['packet']; budget = packet['budget']
    assert budget['over_budget'] and budget['reason'] == 'MANDATORY_IDENTITY_AND_COVERAGE'
    assert budget['actual_cost'] == cost(result)
    assert budget['mandatory_cost'] == budget['actual_cost']
    assert packet['allowed_target_ids'] == prepare(source)['packet']['allowed_target_ids']
    assert any(o['id']=='doc:guide' and o['reason']=='BUDGET' for o in packet['omitted'])
    assert {n['id'] for n in source['technical_view']['nodes']} <= {o['id'] for o in packet['omitted']}
    assert {p['id'] for p in source['technical_view']['provenance']} <= {o['id'] for o in packet['omitted']}


def test_exact_budget_utf8_and_deterministic_document_admission():
    source=sample_process(); docs=[document('doc:b','český text'),document('doc:a','jiný text')]
    result=prepare(source,documents=docs,char_budget=100000,token_budget=100000)
    assert result['packet']['budget']['actual_cost']==cost(result)
    assert result==prepare(source,documents=list(reversed(docs)),char_budget=100000,token_budget=100000)
    tiny=prepare(source,documents=docs,token_budget=1,char_budget=100000)
    assert tiny['packet']['document_summaries']==[]
    # Budgets themselves are serialized; a comfortably sufficient exact envelope
    # must retain all optional documents without claiming a hidden estimator cost.
    bound=cost(result)['characters']+100
    admitted=prepare(source,documents=docs,char_budget=bound,token_budget=100000)
    assert len(admitted['packet']['document_summaries'])==2
    assert admitted['packet']['budget']['actual_cost']==cost(admitted)
    assert not admitted['packet']['budget']['over_budget']


@pytest.mark.parametrize('field,value',[('token_budget',True),('token_budget',0),('token_budget',-1),('token_budget',1.5),('char_budget',False),('char_budget',0),('char_budget',10**20)])
def test_invalid_budgets_are_controlled_and_leave_input_unchanged(field,value):
    source=sample_process();before=deepcopy(source)
    with pytest.raises(ValueError):prepare(source,**{field:value})
    assert source==before


def test_secret_payloads_are_omitted_with_hashes_and_pure_function_performs_no_io(tmp_path):
    from kgmaker.process_semantics import prepare_process_label_packet
    source=sample_process();source['technical_view']['nodes'][0]['label']=SENTINEL
    source['technical_view']['nodes'][0]['attributes'].update(password=SENTINEL,config={'uri':'https://u:'+SENTINEL+'@host?token='+SENTINEL})
    source['technical_view']['provenance'][0]['raw_header']='Authorization: Bearer '+SENTINEL
    source['technical_view']['diagnostics']=[{'code':'UNSUPPORTED_LANGUAGE','message':SENTINEL}]
    source['technical_view']['coverage']['status']=source['technical_status']='PARTIAL'
    source['technical_view']['limits']=[SENTINEL]
    docs=[document()];before=deepcopy((source,docs));artifact=tmp_path/'last-valid';artifact.write_text('previous')
    with patch('builtins.open',side_effect=AssertionError('file IO')),patch.object(Path,'read_bytes',side_effect=AssertionError('file IO')),patch.object(Path,'write_text',side_effect=AssertionError('file IO')),patch('subprocess.Popen',side_effect=AssertionError('process')),patch('socket.socket',side_effect=AssertionError('network')),patch('kgmaker.feature.prepare',side_effect=AssertionError('feature prepare')):
        result=prepare_process_label_packet(source,documents=docs)
    assert SENTINEL not in serialized(result) and 'Authorization:' not in serialized(result)
    assert 'password' not in serialized(result) and 'https://' not in serialized(result)
    assert any(o['reason']=='UNTRUSTED_TEXT' and len(o['content_hash'])==64 for o in result['packet']['omitted'])
    assert (source,docs)==before and artifact.read_text()=='previous' and list(tmp_path.iterdir())==[artifact]


@pytest.mark.parametrize('case',['required_id','selection','malformed_key'])
def test_unsafe_id_or_validation_error_never_echoes_secret(case):
    source=sample_process()
    if case=='required_id':
        identity='process:https://u:'+SENTINEL+'@host?token='+SENTINEL
        source['process_id']=source['definition']['process_id']=source['technical_view']['view_id']=identity
        source['definition_fingerprint']=ProcessDefinition.from_dict(source['definition']).content_fingerprint
    elif case=='selection':
        source['definition']['context_selection']={'token':SENTINEL}
        source['technical_view']['context_selection']={'token':SENTINEL}
        source['definition_fingerprint']=ProcessDefinition.from_dict(source['definition']).content_fingerprint
    else:source['technical_view'][SENTINEL]='bad'
    with pytest.raises(ValueError) as error:prepare(source)
    assert SENTINEL not in str(error.value) and SENTINEL not in repr(error.value)
    assert error.value.__suppress_context__


def test_structured_conflicts_are_review_items_and_documents_never_change_topology():
    source=sample_process();before=deepcopy(source);docs=[document()]
    conflict={'document_ref':'doc:guide','target_id':'card','source_refs':['ev:card'],'status':'CONFLICT'}
    result=prepare(source,documents=docs,conflicts=[conflict]);packet=result['packet']
    assert packet['captured_conflicts']==[conflict] and packet['documentation_comparison']=='NOT_EVALUATED'
    assert result['candidate_template']['annotations']==[]
    assert packet['technical_inventory']==prepare(source)['packet']['technical_inventory']
    assert source==before and SENTINEL not in serialized(result)


@pytest.mark.parametrize('case',['scope','context','content_hash','unknown_target','unknown_ref','unknown_document'])
def test_invalid_document_or_conflict_preserves_input(case):
    source=sample_process();docs=[document()];conflicts=[]
    if case=='scope':docs[0]['scope']='test'
    elif case=='context':docs[0]['context_ids']=['foreign']
    elif case=='content_hash':docs[0]['content_hash']='0'*64
    else:
        conflicts=[{'document_ref':'missing' if case=='unknown_document' else 'doc:guide','target_id':'missing' if case=='unknown_target' else 'card','source_refs':['missing' if case=='unknown_ref' else 'ev:card'],'status':'CONFLICT'}]
    before=deepcopy((source,docs,conflicts))
    with pytest.raises(ValueError):prepare(source,documents=docs,conflicts=conflicts)
    assert (source,docs,conflicts)==before


def test_unsupported_unresolved_and_truncated_process_keeps_boundaries_and_evidence_kind():
    source=sample_process();source['technical_view']['coverage'].update(status='PARTIAL',truncated=True)
    source['technical_status']='PARTIAL'
    card=next(n for n in source['technical_view']['nodes'] if n['id']=='card')
    card.update(kind='unresolved_boundary',resolution_status='UNRESOLVED',freshness='UNKNOWN',evidence_kinds=['UNKNOWN'])
    card['attributes'].update(boundary_reason=SENTINEL,language='unsupported')
    next(p for p in source['technical_view']['provenance'] if p['id']=='ev:card')['evidence_kind']='UNKNOWN'
    packet=prepare(source)['packet'];row=next(n for n in packet['technical_inventory'] if n['id']=='card')
    assert row['kind']=='unresolved_boundary' and row['resolution_status']=='UNRESOLVED' and row['freshness']=='UNKNOWN'
    assert row['evidence_kinds']==['UNKNOWN'] and 'card' in packet['uncertainty']['target_ids']
    assert packet['technical_status']=='PARTIAL' and packet['uncertainty']['truncated'] is True
    assert SENTINEL not in serialized(packet)


@pytest.mark.parametrize('case',['cycle','deep','shared','nonjson'])
def test_preflight_bounds_input_before_model_copy_or_json(case):
    source=sample_process();attrs=source['technical_view']['nodes'][0]['attributes']
    if case=='cycle':attrs['bad']=attrs
    elif case=='deep':
        cursor={};attrs['bad']=cursor
        for _ in range(80):cursor['child']={};cursor=cursor['child']
    elif case=='shared':attrs['bad']=['x'*1000]*5000
    else:attrs['bad']=object()
    with patch.object(ProcessView,'from_dict',side_effect=AssertionError('validated before bounds')):
        with pytest.raises(ValueError):prepare(source)


def test_hard_packet_envelope_limit_is_error_not_truncated_identity(monkeypatch):
    import kgmaker.process_semantics as module
    monkeypatch.setattr(module,'HARD_PACKET_CHAR_LIMIT',1000)
    source=sample_process();before=deepcopy(source)
    with pytest.raises(ValueError):prepare(source,token_budget=1,char_budget=1)
    assert source==before


def test_legitimate_unicode_ids_and_source_paths_with_spaces_are_preserved_exactly():
    source=sample_process();identity='process:Objednávka zákazníka'
    source['process_id']=source['definition']['process_id']=source['technical_view']['view_id']=identity
    source['definition_fingerprint']=ProcessDefinition.from_dict(source['definition']).content_fingerprint
    source_ref='file:src/main/kotlin/objednávky/Order Handler.kt:obsluž(Částka)'
    source['technical_view']['nodes'][0]['original_ids'].append(source_ref)
    result=prepare(source)
    assert result['packet']['identity']['process_id']==identity
    assert identity in result['packet']['allowed_target_ids']
    assert source_ref in result['packet']['allowed_source_refs']
    assert result['packet']['budget']['actual_cost']==cost(result)
    assert cost(result)['utf8_bytes']>cost(result)['characters']


@pytest.mark.parametrize('field',['document_ref','target_id','source_refs','status'])
def test_malformed_conflict_fields_are_controlled_without_input_echo(field):
    conflict={'document_ref':'doc:guide','target_id':'card','source_refs':['ev:card'],'status':'CONFLICT'}
    conflict[field]=[SENTINEL]
    with pytest.raises(ValueError) as error:prepare(sample_process(),documents=[document()],conflicts=[conflict])
    assert SENTINEL not in str(error.value)


def test_original_compiler_evidence_references_survive_without_exporting_proof_text():
    source=sample_process();proof=source['technical_view']['provenance'][0]
    proof['original_evidence_ids']=['compiler:proof-2','compiler:proof-1']
    proof['compiler_evidence_ids']=['compiler:declaration']
    proof['raw_value']=SENTINEL
    result=prepare(source);packet=result['packet']
    assert packet['original_reference_ids']==['compiler:declaration','compiler:proof-1','compiler:proof-2']
    row=next(p for p in packet['evidence_summaries'] if p['id']==proof['id'])
    assert row['original_evidence_ids']==['compiler:proof-1','compiler:proof-2']
    assert SENTINEL not in serialized(result)


@pytest.mark.parametrize('unit',['characters','tokens'])
def test_adjacent_exact_budget_has_consistent_final_cost_and_flag(unit):
    source=sample_process()
    kwargs={'token_budget':100000,'char_budget':100000}
    field='char_budget' if unit=='characters' else 'token_budget'
    boundary=prepare(source,**kwargs)['packet']['budget']['actual_cost'][unit]
    for _ in range(10):
        kwargs[field]=boundary
        actual=prepare(source,**kwargs)
        measured=cost(actual)[unit]
        if measured==boundary:break
        boundary=measured
    else:pytest.fail('No exact boundary established')
    for limit in [boundary-1,boundary,boundary+1]:
        kwargs[field]=limit
        result=prepare(source,**kwargs);b=result['packet']['budget'];measured=cost(result)
        assert b['actual_cost']==measured
        assert b['over_budget']==(measured['characters']>b['char_budget'] or measured['tokens']>b['token_budget'])
        assert b['over_budget']==(limit<boundary)
        assert b['reason']==('MANDATORY_IDENTITY_AND_COVERAGE' if limit<boundary else None)


@pytest.mark.parametrize('value',[{'note':'untrusted prose '+SENTINEL},
    {'capture_id':'capture:guide','source_ref':'doc:guide','note':SENTINEL},
    {'capture_id':'capture:guide','source_ref':'not-captured'},
    {'capture_id':'capture:guide','source_ref':'doc:guide','context_ids':['foreign']}])
def test_document_provenance_is_ref_only_not_arbitrary_prose(value):
    docs=[document()];docs[0]['selection_provenance']=value;before=deepcopy(docs)
    with pytest.raises(ValueError) as error:prepare(sample_process(),documents=docs)
    assert SENTINEL not in str(error.value) and docs==before


def test_actual_inventory_context_shape_keeps_ids_but_omits_diagnostic_prose():
    source=sample_process();selection={'services':{'orders':{'scope':'production','status':'CURRENT','contexts':[
        {'service_id':'orders','repo_id':'backend','module':'app','scope':'production','mode':'COMPILER',
         'context_id':'ctx-prod','context_fingerprint':'a'*64,'context_selection_key':'selection:app',
         'profile':['blue'],'status':'CURRENT','freshness':'CONTENT_VERIFIED',
         'evidence_kind':'BUILD_IMPORT','candidate_context_ids':['ctx-prod'],
         'coverage':{'message':SENTINEL},'diagnostics':[{'message':SENTINEL}]}]}}}
    source['definition']['context_selection']=deepcopy(selection)
    source['technical_view']['context_selection']=deepcopy(selection)
    source['definition_fingerprint']=ProcessDefinition.from_dict(source['definition']).content_fingerprint
    result=prepare(source);packet=result['packet'];row=packet['identity']['context_selection']['services']['orders']['contexts'][0]
    assert row['context_id']=='ctx-prod' and row['profile']==['blue']
    assert row['diagnostics_binding']['content_hash'] and row['coverage_binding']['content_hash']
    assert SENTINEL not in serialized(result)
    assert packet['identity']['context_selection_hash']==hashlib.sha256(serialized(selection).encode()).hexdigest()



def test_process_step_service_owner_and_original_proof_id_are_preserved():
    source=sample_process();source['technical_view']['nodes'][0]['owner_id']='service:objednávky'
    source['technical_view']['provenance'][0]['original_id']='evidence:original-input'
    result=prepare(source);packet=result['packet']
    assert next(n for n in packet['technical_inventory'] if n['id']=='request')['owner_id']=='service:objednávky'
    assert 'service:objednávky' not in packet['allowed_target_ids']
    assert 'evidence:original-input' in packet['original_reference_ids']
    assert next(p for p in packet['evidence_summaries'] if p['id']=='ev:request')['original_id']=='evidence:original-input'

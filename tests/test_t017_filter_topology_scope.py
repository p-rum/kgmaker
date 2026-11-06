"""Public T017 contracts over hand-labelled topology, not compiler acceptance."""
from copy import deepcopy
import importlib
import importlib.util
from dataclasses import replace
import pytest

from kgmaker.architecture_model import ViewDocument, ViewNode, ViewEdge


def api():
    assert importlib.util.find_spec('kgmaker.topology_filter'), 'T017 filter API is absent'
    return importlib.import_module('kgmaker.topology_filter').filter_topology


def star():
    proof={'id':'proof:declared','source_id':'source:declaration','scope':'production',
        'context_ids':['context:main'],'evidence_kind':'SOURCE_ONLY','freshness':'UNKNOWN','polarity':'UNKNOWN'}
    nodes=tuple(ViewNode(i,'service',i,attributes={'scope':'production','context_ids':['context:main']},
        resolution_status='RESOLVED') for i in ('service:a','service:b','service:c'))
    edges=tuple(ViewEdge('edge:a-'+i,'service:a','service:'+i,'remote_http_request_response',
        original_ids=('original:'+i,),evidence_refs=('proof:declared',),unknown_refs=('proof:declared',),
        evidence_kinds=('SOURCE_ONLY',),resolution_status='AMBIGUOUS',
        attributes={'scope':'production','context_ids':['context:main'],
            'origin_interface_ids':['interface:client','interface:'+i],
            'origin_mapping_ids':['mapping:'+i],'origin_release_ids':['release:a','release:'+i]})
        for i in ('b','c'))
    return ViewDocument('topology:fixture','topology','baseline:fixture','service-topology-view-1',
        'production',{'requested_selection':{'scope':'production','selected_contexts':[]},
        'actual_selection_fingerprint':'0'*64},nodes=nodes,edges=edges,provenance=(proof,),
        coverage={'status':'PARTIAL','truncated':False})


def test_public_budget_is_stable_and_retains_ambiguity_and_full_omission_inventory():
    source=star();before=deepcopy(source.to_dict())
    result=api()(source,focus_service='service:a',direction='outgoing',max_hops=1,max_nodes=2)
    view=ViewDocument.from_dict(result['document']);f=result['filtering']
    assert [n.id for n in view.nodes]==['service:a','service:b']
    assert [(e.id,e.resolution_status) for e in view.edges]==[('edge:a-b','AMBIGUOUS')]
    assert f['omitted_node_ids']==['service:c'] and f['omitted_edge_ids']==['edge:a-c']
    assert f['omitted_original_interface_ids']==['interface:c','interface:client']
    assert f['omitted_mapping_ids']==['mapping:c'] and f['truncated'] is True
    assert view.coverage['status']=='PARTIAL' and source.to_dict()==before


def test_public_single_node_budget_does_not_overflow_with_synthetic_boundaries():
    result=api()(star(),focus_service='service:a',max_nodes=1)
    assert [n['id'] for n in result['document']['nodes']]==['service:a']
    assert result['document']['edges']==[]
    assert result['filtering']['frontier']
    assert all(b['anchor_id']=='service:a' for b in result['filtering']['frontier'])


def test_shuffled_input_and_reordered_filter_sets_have_identical_output():
    original=star();shuffled=replace(original,nodes=tuple(reversed(original.nodes)),
        edges=tuple(reversed(original.edges)),provenance=tuple(reversed(original.provenance)))
    first=api()(original,focus_service='service:a',max_nodes=2,
        relations=['remote_http_request_response','depends_on'],context_ids=['context:main'])
    second=api()(shuffled,focus_service='service:a',max_nodes=2,
        relations=['depends_on','remote_http_request_response'],context_ids=['context:main'])
    assert first==second


@pytest.mark.parametrize('direction,expected',[('incoming',['service:a']),
    ('outgoing',['service:a','service:b','service:c']),('both',['service:a','service:b','service:c'])])
def test_direction_selects_real_neighborhood(direction,expected):
    result=api()(star(),focus_service='service:a',direction=direction)
    assert [n['id'] for n in result['document']['nodes']]==expected


def test_zero_hops_has_visible_hop_frontier_and_no_edge():
    result=api()(star(),focus_service='service:a',max_hops=0)
    assert [n['id'] for n in result['document']['nodes']]==['service:a']
    assert result['document']['edges']==[]
    assert {b['reason'] for b in result['filtering']['frontier']}=={'HOP_LIMIT'}


def test_unknown_focus_is_distinct_from_empty_relation_filter_and_unfocused_selection():
    unknown=api()(star(),focus_service='service:absent')
    empty=api()(star(),relations=[])
    all_nodes=api()(star())
    assert unknown['filtering']['status']=='UNKNOWN_FOCUS'
    assert unknown['document']['nodes']==[] and unknown['document']['coverage']['status']=='UNKNOWN'
    assert len(empty['document']['nodes'])==3 and empty['document']['edges']==[]
    assert empty['filtering']['status']=='FILTERED'
    assert all_nodes['filtering']['status']=='UNRESTRICTED' and len(all_nodes['document']['edges'])==2


@pytest.mark.parametrize('kwargs',[{'max_nodes':0},{'max_nodes':True},{'max_nodes':2.5},
    {'max_nodes':-1},{'max_hops':True},{'max_hops':-1},{'direction':'sideways'},
    {'focus_service':''},{'scope':'test'},{'context_ids':['context:foreign']}])
def test_invalid_selector_has_fixed_error_and_preserves_input(kwargs):
    source=star();before=deepcopy(source.to_dict())
    with pytest.raises(ValueError) as error:api()(source,**kwargs)
    assert str(error.value).startswith('FILTER_') and source.to_dict()==before


def test_middle_node_context_exclusion_never_creates_shortcut():
    source=star();ab=source.edges[0]
    bc=replace(ab,id='edge:b-c',source='service:b',target='service:c')
    nodes=tuple(replace(n,attributes={**n.attributes,'context_ids':['context:other']})
        if n.id=='service:b' else n for n in source.nodes)
    source=replace(source,nodes=nodes,edges=(ab,bc))
    result=api()(source,context_ids=['context:main'])
    assert [n['id'] for n in result['document']['nodes']]==['service:a','service:c']
    assert result['document']['edges']==[]
    assert {b['reason'] for b in result['filtering']['frontier']}=={'CONTEXT_FILTER'}


def test_cross_context_tuple_is_not_shrunk_to_fit():
    source=star();edge=replace(source.edges[0],attributes={**source.edges[0].attributes,
        'context_ids':['context:main','context:other']})
    result=api()(replace(source,edges=(edge,)),context_ids=['context:main'])
    assert result['document']['edges']==[]
    boundary=result['filtering']['frontier'][0]
    assert boundary['context_ids']==['context:main','context:other']


def test_kafka_channel_counts_two_hops_and_is_never_reconnected_as_service_call():
    source=star();channel=ViewNode('channel:k','kafka_channel','Channel',
        attributes={'scope':'production','context_ids':['context:main']})
    first=replace(source.edges[0],id='edge:publish',target='channel:k',relation='publishes_to_channel')
    second=replace(source.edges[1],id='edge:consume',source='channel:k',target='service:b',
        relation='consumes_from_channel')
    source=replace(source,nodes=source.nodes+(channel,),edges=(first,second))
    result=api()(source,focus_service='service:a',direction='outgoing',max_hops=1)
    assert {n['id'] for n in result['document']['nodes']}=={'service:a','channel:k'}
    assert [e['id'] for e in result['document']['edges']]==['edge:publish']
    assert result['filtering']['omitted_edge_ids']==['edge:consume']


def test_cycles_terminate_and_do_not_change_original_edges_or_evidence():
    source=star();back=replace(source.edges[0],id='edge:b-a',source='service:b',target='service:a')
    source=replace(source,edges=source.edges+(back,))
    result=api()(source,focus_service='service:a')
    assert len(result['document']['nodes'])==3 and len(result['document']['edges'])==3
    assert result['document']['edges']==source.to_dict()['edges']
    assert result['document']['provenance']==source.to_dict()['provenance']
    assert result['document']['baseline_fingerprint']==source.baseline_fingerprint
    assert result['document']['context_selection']==source.context_selection


def test_upstream_truncation_is_not_erased_by_unrestricted_filter():
    source=replace(star(),coverage={'status':'PARTIAL','truncated':True})
    result=api()(source)
    assert result['filtering']['truncated'] and not result['filtering']['omission_inventory_complete']
    assert result['filtering']['frontier'][0]['reason']=='UPSTREAM_TRUNCATION'
    assert result['document']['coverage']['status']=='PARTIAL'


def test_contradicting_unknown_buckets_and_stale_freshness_are_preserved_exactly():
    source=star();proof={**source.provenance[0],'id':'proof:contradiction','polarity':'CONTRADICTING',
        'freshness':'STALE'}
    edge=replace(source.edges[0],evidence_refs=('proof:declared','proof:contradiction'),
        contradicting_refs=('proof:contradiction',),freshness='STALE')
    source=replace(source,edges=(edge,),provenance=source.provenance+(proof,))
    result=api()(source)
    assert result['document']['edges']==source.to_dict()['edges']
    assert result['document']['provenance']==source.to_dict()['provenance']
    assert result['document']['edges'][0]['freshness']=='STALE'


def test_generation_timestamp_does_not_change_selection_fingerprint():
    first=api()(replace(star(),generated_at='2026-11-05T01:00:00Z'),max_nodes=1)
    second=api()(replace(star(),generated_at='2026-11-05T02:00:00Z'),max_nodes=1)
    assert first==second


def test_shared_acyclic_input_is_counted_without_becoming_a_cycle():
    source=star().to_dict();shared=['context:main']
    for row in source['nodes']:row['attributes']['context_ids']=shared
    assert len(api()(source)['document']['nodes'])==3


def test_no_file_process_network_or_upstream_capture_is_called(monkeypatch):
    from pathlib import Path
    import socket,subprocess,kgmaker.service_topology
    source=star();function=api()
    def forbidden(*args,**kwargs):raise AssertionError('Unexpected I/O')
    monkeypatch.setattr(Path,'open',forbidden);monkeypatch.setattr(Path,'read_text',forbidden)
    monkeypatch.setattr(Path,'write_text',forbidden);monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(kgmaker.service_topology,'capture_topology_inputs',forbidden)
    assert len(function(source)['document']['nodes'])==3


@pytest.mark.parametrize('retained',[True,False])
def test_credential_expansion_id_is_rejected_even_when_retained(retained):
    source=star();edge=replace(source.edges[0],attributes={**source.edges[0].attributes,
        'origin_interface_ids':['//alice:PRIVATE_SENTINEL@example.org/path']})
    source=replace(source,edges=(edge,))
    with pytest.raises(ValueError) as error:api()(source,max_nodes=200 if retained else 1)
    assert 'PRIVATE_SENTINEL' not in repr(error.value)


def test_unicode_spaces_preserve_original_identity():
    source=star();node=replace(source.nodes[0],id='service:Česká cesta/main app')
    source=replace(source,nodes=(node,*source.nodes[1:]),edges=tuple(
        replace(e,source=node.id) for e in source.edges))
    result=api()(source,focus_service=node.id,max_nodes=1)
    assert result['document']['nodes'][0]['id']==node.id


@pytest.mark.parametrize('damage',['cycle','deep','budget'])
def test_resource_bounds_fail_controlled_without_partial_result(damage,monkeypatch):
    source=star().to_dict()
    if damage=='cycle':source['nodes'][0]['attributes']['cycle']=source
    elif damage=='deep':
        nested={};source['nodes'][0]['attributes']['deep']=nested
        for _ in range(100):nested['next']={};nested=nested['next']
    else:
        module=importlib.import_module('kgmaker.topology_filter')
        monkeypatch.setattr(module,'_MAX_OUTPUT_CHARS',10)
    with pytest.raises(ValueError):api()(source)

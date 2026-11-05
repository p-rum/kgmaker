"""T026 actual certified CFG projection and lossless pure business grouping."""
from copy import deepcopy
from unittest.mock import patch

import pytest

# Real workspace -> Javac inspection -> T024 inventory -> T025 certificate path.
from test_local_operation_proofs import pipeline


def test_actual_javac_literal_local_chain_collapses_and_expands_exactly(pipeline):
    from kgmaker.process_paths import build_local_process
    source_graph, inventory, triggers, root = pipeline
    original = build_local_process(source_graph, inventory, triggers['entry'].id,
                                   process_id='process:business-locals')
    assert len([n for n in original.steps if n.attributes.get('local_operation')]) == 6
    before = deepcopy(original.to_dict())
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    with patch('subprocess.Popen', side_effect=AssertionError('pure projection executed process')), \
         patch('socket.socket', side_effect=AssertionError('pure projection used network')):
        grouped = collapse_business_steps(original)
        actions = [n for n in grouped.steps if n.kind == 'action']
        assert len(actions) == 1
        assert len(actions[0].attributes['business_group']['nodes']) == 6
        assert actions[0].resolution_status == 'UNRESOLVED'
        assert 'SYNTAX_CANDIDATE' in actions[0].evidence_kinds
        assert grouped.technical_status == 'PARTIAL'
        assert expand_business_steps(grouped).to_dict() == before
        assert collapse_business_steps(original).to_json() == grouped.to_json()
    assert original.to_dict() == before
    assert any(n.kind == 'exceptional_exit' for n in grouped.steps)


@pytest.fixture(scope='module')
def technical(pipeline):
    from kgmaker.process_paths import build_local_process
    graph, inventory, triggers, _ = pipeline
    return build_local_process(graph, inventory, triggers['entry'].id, process_id='process:matrix').to_dict()


def operation_nodes(document):
    return [n for n in document['technical_view']['nodes'] if n['attributes'].get('local_operation')]


def actions(process):
    return [n for n in process.steps if n.attributes.get('business_group')]


def test_ordered_origins_are_topology_not_id_sort_and_no_mutation(technical):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    from kgmaker.process_model import ProcessView
    source = deepcopy(technical); source['technical_view']['nodes'].reverse(); source['technical_view']['edges'].reverse()
    before = deepcopy(source)
    grouped = collapse_business_steps(source); group = actions(grouped)[0].attributes['business_group']
    assert [e['source'] for e in group['edges']] == [n['id'] for n in group['nodes'][:-1]]
    assert [e['target'] for e in group['edges']] == [n['id'] for n in group['nodes'][1:]]
    assert expand_business_steps(grouped).to_json() == ProcessView.from_dict(source).to_json()
    assert collapse_business_steps(grouped).to_json() == grouped.to_json()
    assert source == before


@pytest.mark.parametrize('boundary', ['decision', 'call', 'loop_header', 'service_boundary',
    'transaction_boundary', 'async_boundary', 'unresolved_boundary'])
def test_boundaries_never_disappear_or_merge_across_them(technical, boundary):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    source = deepcopy(technical); node = operation_nodes(source)[2]; identity = node['id']
    node['kind'] = boundary
    if boundary == 'unresolved_boundary':
        node['resolution_status'] = 'UNRESOLVED'; node['attributes']['boundary_reason'] = 'unsupported expression'
    grouped = collapse_business_steps(source)
    assert any(n.id == identity and n.kind == boundary for n in grouped.steps)
    assert all(identity not in {n['id'] for n in a.attributes['business_group']['nodes']} for a in actions(grouped))
    from kgmaker.process_model import ProcessView
    assert expand_business_steps(grouped).to_dict() == ProcessView.from_dict(source).to_dict()


@pytest.mark.parametrize('relation', ['true', 'exception', 'finally', 'loop', 'call', 'async', 'unknown'])
def test_conditional_or_exceptional_topology_is_not_internal_adjacency(technical, relation):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    from kgmaker.process_model import ProcessView
    source = deepcopy(technical); opids = {n['id'] for n in operation_nodes(source)}
    edge = next(e for e in source['technical_view']['edges'] if e['source'] in opids and e['target'] in opids)
    edge['relation'] = relation
    if relation == 'true': edge['attributes']['condition'] = 'compiler condition'
    grouped = collapse_business_steps(source)
    assert any(e.id == edge['id'] and e.relation == relation for e in grouped.transitions)
    assert all(edge['id'] not in {e['id'] for e in a.attributes['business_group']['edges']} for a in actions(grouped))
    assert expand_business_steps(grouped).to_dict() == ProcessView.from_dict(source).to_dict()


def test_cycle_cannot_be_hidden_inside_a_business_group(technical):
    from kgmaker.business_process import collapse_business_steps
    source = deepcopy(technical); ops = operation_nodes(source); edges = source['technical_view']['edges']
    opids = {n['id'] for n in ops}; internals = [e for e in edges if e['source'] in opids and e['target'] in opids]
    first = next(n for n in ops if not any(e['target'] == n['id'] for e in internals))
    last = next(n for n in ops if not any(e['source'] == n['id'] for e in internals))
    loop = deepcopy(internals[0]); loop.update(id='loop-back', source=last['id'], target=first['id'], relation='loop')
    loop['attributes']['loop_back'] = True; edges.append(loop)
    assert not actions(collapse_business_steps(source))


def test_parallel_external_edges_are_distinct_and_exactly_restored(technical):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    from kgmaker.process_model import ProcessView
    source = deepcopy(technical); opids = {n['id'] for n in operation_nodes(source)}
    edge = next(e for e in source['technical_view']['edges'] if e['target'] in opids and e['source'] not in opids)
    parallel = deepcopy(edge); parallel['id'] += ':parallel'; parallel['attributes']['note'] = 'distinct provenance path'
    # A non-normal endpoint boundary is conservatively excluded; remaining chain still groups.
    source['technical_view']['edges'].append(parallel)
    grouped = collapse_business_steps(source)
    assert actions(grouped)
    assert {edge['id'], parallel['id']} <= {e.id for e in grouped.transitions}
    assert expand_business_steps(grouped).to_dict() == ProcessView.from_dict(source).to_dict()


def test_disconnected_equal_dto_or_label_does_not_create_adjacency(technical):
    from kgmaker.business_process import collapse_business_steps
    source = deepcopy(technical); ops = operation_nodes(source); ids = {n['id'] for n in ops}
    source['technical_view']['edges'] = [e for e in source['technical_view']['edges']
        if not (e['source'] in ids and e['target'] in ids)]
    for n in ops: n['label'] = 'Same DTO'; n['attributes']['dto'] = 'OrderDto'
    assert not actions(collapse_business_steps(source))


@pytest.mark.parametrize('change', ['hash', 'scope', 'context', 'method', 'cfg_block', 'operation_ref',
    'missing_proof', 'legacy', 'stale', 'unsupported', 'node_unknown'])
def test_invalid_stale_foreign_and_opaque_inputs_do_not_borrow_operation_proof(technical, change):
    from kgmaker.business_process import collapse_business_steps, BusinessProcessError
    source = deepcopy(technical); nodes = operation_nodes(source)
    for node in nodes:
        ref = node['evidence_refs'][0]
        record = next(p for p in source['technical_view']['provenance'] if p['id'] == ref)
        if change == 'hash': record['content_hash'] = '0' * 64
        elif change in ('scope', 'context', 'method'):
            key = {'scope':'scope', 'context':'context_ids', 'method':'source_id'}[change]
            record[key] = ['foreign'] if change == 'context' else 'foreign'
        elif change in ('cfg_block', 'operation_ref'): node['attributes']['local_operation'][change] = 'borrowed'
        elif change == 'missing_proof': record.pop('local_operation_proof')
        elif change == 'legacy': node['attributes'].pop('local_operation')
        elif change == 'stale': node['freshness'] = record['freshness'] = 'STALE'
        elif change == 'node_unknown': node['resolution_status'] = 'UNRESOLVED'
        elif change == 'unsupported': node['attributes']['local_operation']['schema_version'] = 42
    if change == 'stale':
        from kgmaker.views import _summarize_view_evidence
        provenance = {p['id']: p for p in source['technical_view']['provenance']}
        for edge in source['technical_view']['edges']:
            if edge['evidence_refs']:
                edge.update(_summarize_view_evidence(edge['evidence_refs'], provenance))
    before = deepcopy(source)
    if change in ('legacy', 'stale', 'node_unknown'):
        assert not actions(collapse_business_steps(source))
    else:
        with pytest.raises(BusinessProcessError): collapse_business_steps(source)
    assert source == before


@pytest.mark.parametrize('change', ['member_order', 'internal_edge', 'external_endpoint', 'summary', 'version', 'nested'])
def test_tampered_expansion_is_rejected_without_mutation(technical, change):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps, BusinessProcessError
    source = collapse_business_steps(technical).to_dict()
    group = next(n for n in source['technical_view']['nodes'] if 'business_group' in n['attributes'])
    payload = group['attributes']['business_group']
    if change == 'member_order': payload['nodes'].reverse()
    elif change == 'internal_edge': payload['edges'][0]['target'] = payload['edges'][0]['source']
    elif change == 'external_endpoint':
        edge = next(e for e in source['technical_view']['edges'] if e['target'] == group['id'])
        edge['source'] = next(n['id'] for n in source['technical_view']['nodes'] if n['kind'] == 'exceptional_exit')
    elif change == 'summary': group['evidence_kinds'] = ['SYMBOL_RESOLVED']
    elif change == 'version': payload['version'] = 'future-42'
    elif change == 'nested': payload['nodes'][0]['attributes']['business_group'] = {}
    before = deepcopy(source)
    with pytest.raises(BusinessProcessError): expand_business_steps(source)
    assert source == before


def test_actual_field_call_and_finally_boundaries_remain_visible(pipeline):
    from kgmaker.process_paths import build_local_process
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    graph, inventory, triggers, _ = pipeline
    for name in ('unsafe', 'cleanup'):
        source = build_local_process(graph, inventory, triggers[name].id, process_id='process:' + name)
        result = collapse_business_steps(source)
        assert not actions(result)
        assert expand_business_steps(result).to_json() == source.to_json()


@pytest.mark.parametrize('change', ['deep', 'cycle', 'wide', 'unhashable'])
def test_public_input_budgets_and_malformed_shapes_fail_without_projection_io(technical, change):
    from kgmaker.business_process import collapse_business_steps, BusinessProcessError
    source = deepcopy(technical)
    if change == 'deep':
        value = {}; source['technical_view']['nodes'][0]['attributes']['extra'] = value
        for _ in range(85): value['next'] = {}; value = value['next']
    elif change == 'cycle': source['technical_view']['nodes'][0]['attributes']['cycle'] = source
    elif change == 'wide': source['technical_view']['nodes'][0]['attributes']['wide'] = [None] * 50_001
    elif change == 'unhashable': source['technical_view']['nodes'][0]['kind'] = []
    with patch('subprocess.Popen', side_effect=AssertionError('projection used subprocess')), \
         patch('socket.socket', side_effect=AssertionError('projection used network')):
        with pytest.raises(BusinessProcessError): collapse_business_steps(source)


def test_digest_consistent_but_wrong_origin_order_is_not_a_valid_group(technical):
    from kgmaker.business_process import collapse_business_steps, expand_business_steps, BusinessProcessError
    from kgmaker.analysis_model import digest
    source = collapse_business_steps(technical).to_dict()
    group = next(n for n in source['technical_view']['nodes'] if 'business_group' in n['attributes'])
    old = group['id']; group['attributes']['business_group']['nodes'].reverse()
    group['id'] = 'business-step:' + digest(group['attributes']['business_group'])
    for edge in source['technical_view']['edges']:
        for key in ('source', 'target'):
            if edge[key] == old: edge[key] = group['id']
    with pytest.raises(BusinessProcessError): expand_business_steps(source)


def test_diamond_and_two_field_writes_are_not_inferred_pure():
    # Explicit process-model specimen, not compiler certification: absence of
    # calls / equal DTOs / labels never certifies either field write as pure.
    from test_t023_define_business_process_model import sample_process
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    from kgmaker.process_model import ProcessView
    source = sample_process()
    for node in source['technical_view']['nodes']:
        if node['id'] in ('card', 'cash'):
            node.update(kind='basic_block', label='assign')
            node['attributes'].update(field='SameDto.value', side_effect='FIELD_WRITE')
    original = ProcessView.from_dict(source)
    grouped = collapse_business_steps(original)
    assert not actions(grouped)
    assert expand_business_steps(grouped).to_json() == original.to_json()
    assert {('choose', 'card', 'true'), ('choose', 'cash', 'false')} <= {
        (e.source, e.target, e.relation) for e in grouped.transitions}


def test_same_proof_finally_clones_and_unused_exit_are_preserved(pipeline):
    from kgmaker.process_paths import build_local_process
    from kgmaker.business_process import collapse_business_steps, expand_business_steps
    graph, inventory, triggers, _ = pipeline
    source = build_local_process(graph, inventory, triggers['cleanup'].id, process_id='process:cleanup-clones')
    groups = {}
    for node in source.steps:
        proof = node.attributes.get('local_operation')
        if proof: groups.setdefault(proof['operation_ref'], []).append(node.id)
    assert groups and any(len(ids) > 1 for ids in groups.values())
    result = collapse_business_steps(source)
    assert all(set(ids) <= {n.id for n in result.steps} for ids in groups.values())
    assert expand_business_steps(result).to_dict() == source.to_dict()
    positive = build_local_process(graph, inventory, triggers['entry'].id, process_id='process:unused-exit')
    unused = next(n.id for n in positive.steps if n.kind == 'exceptional_exit')
    assert not any(e.target == unused for e in positive.transitions)
    assert unused in {n.id for n in collapse_business_steps(positive).steps}


@pytest.mark.parametrize('boundary', ['side_effect', 'transaction', 'service_boundary', 'loop_back'])
def test_additional_operation_boundary_metadata_is_not_discarded(technical, boundary):
    from kgmaker.business_process import collapse_business_steps
    source = deepcopy(technical)
    for node in operation_nodes(source): node['attributes'][boundary] = True
    assert not actions(collapse_business_steps(source))

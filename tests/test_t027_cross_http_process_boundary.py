"""Public T027 process-boundary projection contract tests."""
from copy import deepcopy

import pytest

from kgmaker.architecture_model import ViewDocument, ViewEdge, ViewNode
from kgmaker.business_process import project_http_process_boundary
from kgmaker.process_model import ProcessDefinition, ProcessView


def process(process_id, context, service, *, trigger_id='trigger', handler_id='handler', with_cfg=True):
    selection={'services':{service:{'scope':'production','status':'CURRENT','contexts':[
        {'context_id':context,'status':'CURRENT'}]}}}
    proof={'id':'proof:'+process_id,'evidence_kind':'SOURCE_ONLY','freshness':'UNKNOWN',
        'polarity':'UNKNOWN','scope':'production','context_ids':[context]}
    def node(identity,kind,attrs):
        return ViewNode(identity,kind,kind,original_ids=(identity,),evidence_refs=(proof['id'],),
            attributes={'scope':'production','context_ids':[context],**attrs},
            evidence_kinds=('SOURCE_ONLY',),resolution_status='UNRESOLVED',freshness='UNKNOWN',unknown_refs=(proof['id'],))
    trigger=node(trigger_id,'trigger',{'entry_symbol_id':handler_id})
    call=node('local-call','call',{'call_site_ids':['site:client']})
    exit_node=node('exit','exit',{})
    nodes=[trigger,call,exit_node] if with_cfg else [trigger,exit_node]
    if with_cfg:
        edges=[ViewEdge('e1',trigger_id,'local-call','unknown',original_ids=('e1',),evidence_refs=(proof['id'],),
            attributes={'scope':'production','context_ids':[context]},evidence_kinds=('SOURCE_ONLY',),
            resolution_status='UNRESOLVED',freshness='UNKNOWN',unknown_refs=(proof['id'],)),
            ViewEdge('e2','local-call','exit','normal',original_ids=('e2','site:client'),evidence_refs=(proof['id'],),
            attributes={'scope':'production','context_ids':[context],'call_site':'site:client'},evidence_kinds=('SOURCE_ONLY',),
            resolution_status='UNRESOLVED',freshness='UNKNOWN',unknown_refs=(proof['id'],))]
    else:
        edges=[ViewEdge('e-no-cfg',trigger_id,'exit','unknown',original_ids=('e-no-cfg',),evidence_refs=(proof['id'],),
            attributes={'scope':'production','context_ids':[context],'boundary_reason':'source body unavailable'},
            evidence_kinds=('SOURCE_ONLY',),resolution_status='UNRESOLVED',freshness='UNKNOWN',unknown_refs=(proof['id'],))]
    view=ViewDocument(process_id,'process','a'*64,'t025','production',selection,nodes=tuple(nodes),edges=tuple(edges),
        coverage={'status':'PARTIAL'},provenance=(proof,))
    definition=ProcessDefinition.from_dict({'schema_version':1,'process_id':process_id,'revision':1,'baseline_fingerprint':'a'*64,
        'scope':'production','context_selection':selection,'context_ids':[context],
        'trigger_ids':[trigger_id],'semantic_review_status':'PROPOSED'})
    return ProcessView.from_dict({'schema_version':1,'process_id':process_id,'revision':1,
        'definition':definition.to_dict(),
        'definition_fingerprint':definition.content_fingerprint,'technical_status':'PARTIAL','technical_view':view.to_dict(),
        'entry_ids':[trigger_id],'exit_ids':['exit'],'outcome_ids':[],'semantic_annotations':[]})


def remote_view(*, release='v1', status='RESOLVED', context='ctx-target', target_service='ledger'):
    selection={'services':{'client':{'scope':'production','contexts':[{'context_id':'ctx-client'}]},
        target_service:{'scope':'production','contexts':[{'context_id':context}]}}}
    proof={'id':'remote-proof','evidence_kind':'SOURCE_ONLY','freshness':'UNKNOWN','polarity':'UNKNOWN',
        'scope':'production','context_ids':['ctx-client',context]}
    consumer=ViewNode('client','http_interface','POST /ledger',original_ids=('client','site:client'),evidence_refs=('remote-proof',),
        attributes={'scope':'production','context_ids':['ctx-client'],'service_id':'client','context_id':'ctx-client','direction':'CONSUMER',
            'origin_call_site':'site:client','http_method':'POST','route_expression':'/ledger'},
        evidence_kinds=('SOURCE_ONLY',),resolution_status='RESOLVED',freshness='UNKNOWN')
    provider=ViewNode('provider','http_interface','POST /ledger',original_ids=('provider','handler'),evidence_refs=('remote-proof',),
        attributes={'scope':'production','context_ids':[context],'service_id':target_service,'context_id':context,'direction':'PROVIDER',
            'handler_ids':['handler'],'http_method':'POST','normalized_route':'/ledger'},
        evidence_kinds=('SOURCE_ONLY',),resolution_status='RESOLVED',freshness='UNKNOWN')
    attrs={'scope':'production','context_ids':['ctx-client',context],'binding_id':'binding','mapping_ids':['mapping'],
        'target_service_id':target_service,'target_interface_id':'provider','target_release_id':release,'context_ids':['ctx-client',context],
        'capture_freshness':'CAPTURE_TIME_ONLY','execution_intent':'UNKNOWN','runtime_execution':'NOT_OBSERVED','delivery':'NOT_OBSERVED','runtime_availability':'UNKNOWN'}
    edge=ViewEdge('remote-edge','client','provider','remote_http_request_response',original_ids=('mapping',),
        evidence_refs=('remote-proof',),attributes=attrs,evidence_kinds=('SOURCE_ONLY',),
        resolution_status=status,freshness='UNKNOWN',unknown_refs=('remote-proof',))
    return ViewDocument('remote','topology','b'*64,'remote-interface-view-1','production',selection,
        nodes=(consumer,provider),edges=(edge,),coverage={'status':'PARTIAL'},provenance=(proof,))


def test_ac01_resolved_binding_expands_exact_remote_service_context_and_keeps_evidence():
    local=process('process:client','ctx-client','client')
    target=process('process:ledger','ctx-target','ledger',handler_id='handler')
    result=project_http_process_boundary(local,remote_view(),target_processes=[target])
    assert any(n.kind=='service_boundary' and n.attributes['target_service_id']=='ledger' for n in result.steps)
    assert any(n.attributes.get('source_process_id')=='process:ledger' for n in result.steps)
    assert {'ctx-client','ctx-target'} <= set(result.to_dict()['definition']['context_ids'])
    assert all(n.freshness=='UNKNOWN' or n.freshness=='CURRENT' for n in result.steps)
    assert result.technical_status=='PARTIAL'


def test_ac02_incompatible_or_nonresolved_release_stays_external():
    result=project_http_process_boundary(process('process:client','ctx-client','client'),
        remote_view(release='v2',status='UNRESOLVED'),target_processes=[process('process:ledger','ctx-target','ledger',handler_id='handler')])
    assert any(n.kind=='service_boundary' and n.attributes.get('boundary_reason') for n in result.steps)
    assert not any(n.attributes.get('source_process_id')=='process:ledger' for n in result.steps)


def test_ac03_missing_target_cfg_retains_external_boundary_and_local_continuation():
    local=process('process:client','ctx-client','client')
    before=local.to_json()
    result=project_http_process_boundary(local,remote_view(),target_processes=[])
    assert any(n.kind=='service_boundary' and n.attributes.get('boundary_reason')=='TARGET_PROCESS_UNAVAILABLE' for n in result.steps)
    assert any(e.source=='local-call' and e.target=='exit' for e in result.transitions)
    assert local.to_json()==before


def test_ac04_bad_input_and_failure_boundary_do_not_mutate_inputs():
    local=process('process:client','ctx-client','client');remote=remote_view();before=(local.to_json(),remote.to_json())
    bad=remote.to_dict();bad['scope']='test'
    with pytest.raises(ValueError):project_http_process_boundary(local,bad)
    result=project_http_process_boundary(local,remote,target_processes=[])
    assert (local.to_json(),remote.to_json())==before
    boundary=next(n for n in result.steps if n.kind=='service_boundary')
    assert boundary.attributes['error_semantics']=='TRANSPORT_BOUNDARY_ONLY'
    assert not any(n.kind in {'outcome','decision'} and n.attributes.get('boundary_reason') for n in result.steps)


def test_ac05_other_scope_context_ambiguity_and_missing_callsite_never_choose_target():
    remote=remote_view(status='AMBIGUOUS')
    result=project_http_process_boundary(process('process:client','ctx-client','client'),remote,
        target_processes=[process('process:ledger','ctx-target','ledger',handler_id='handler')])
    assert not any(n.attributes.get('source_process_id')=='process:ledger' for n in result.steps)
    ambiguous=next(n for n in result.steps if n.kind=='service_boundary')
    assert ambiguous.attributes['boundary_reason']=='AMBIGUOUS_REMOTE_BINDING'
    assert ambiguous.attributes['target_candidates']
    local=process('process:client','ctx-client','client')
    for field,value in [('context_id','foreign-context'),('scope','test')]:
        doc=remote_view().to_dict()
        consumer=next(n for n in doc['nodes'] if n['id']=='client')
        consumer['attributes'][field]=value
        foreign=ViewDocument.from_dict(doc)
        unchanged=project_http_process_boundary(local,foreign,target_processes=[])
        assert unchanged.to_json()==local.to_json()
    no_site=process('process:no-site','ctx-client','client')
    doc=no_site.to_dict()
    for node in doc['technical_view']['nodes']:
        if node['id']=='local-call':node['attributes']['call_site_ids']=[]
    # Rebuild the canonical fingerprinted process contract with no local callsite.
    from kgmaker.process_model import ProcessDefinition
    doc['definition_fingerprint']=ProcessDefinition.from_dict(doc['definition']).content_fingerprint
    no_site=ProcessView.from_dict(doc)
    result=project_http_process_boundary(no_site,remote_view(),target_processes=[])
    assert not any(n.kind=='service_boundary' for n in result.steps)


def test_ac06_invalid_remote_binding_rejects_without_input_mutation():
    local=process('process:client','ctx-client','client');remote=remote_view();doc=remote.to_dict()
    doc['unexpected']='bad';before=(local.to_json(),deepcopy(doc))
    with pytest.raises(ValueError):project_http_process_boundary(local,doc)
    assert (local.to_json(),doc)==before


def test_public_t014_projection_links_cross_repository_client_callsite_to_target_process():
    from test_cross_service_contract_mapping import trusted_protocol_specimen, refresh_handoff
    from kgmaker.remote_interfaces import project_remote_interfaces
    specimen=trusted_protocol_specimen('HTTP')
    workspace,graph,documents,captured=specimen
    client=next(node for doc in documents for node in doc['nodes'] if node['id']=='client')
    provider=next(node for doc in documents for node in doc['nodes'] if node['id']=='provider')
    client_context='repo:checkout:context:production'
    target_context='repo:orders:context:production'
    client_site='repo:checkout:call-site:submit-order'
    target_handler='repo:orders:method:OrderController.create'
    client['attributes'].update(origin_call_site=client_site,context_id=client_context)
    provider['attributes'].update(handler_ids=[target_handler],context_id=target_context)
    workspace['remote_mapping']['releases'][0]['context_id']=client_context
    workspace['remote_mapping']['releases'][1]['context_id']=target_context
    graph.contexts=[{'id':client_context,'scope':'production','freshness':'CONTENT_VERIFIED'},
                    {'id':target_context,'scope':'production','freshness':'CONTENT_VERIFIED'}]
    refresh_handoff(workspace,graph,documents,captured)
    remote=project_remote_interfaces(workspace,graph,documents,captured=captured,scope='production')
    local=process('process:client',client_context,'checkout',trigger_id='local-trigger',handler_id='local-handler')
    local_doc=local.to_dict()
    for node in local_doc['technical_view']['nodes']:
        if node['id']=='local-call':node['attributes']['call_site_ids']=[client_site]
    for edge in local_doc['technical_view']['edges']:
        if edge['id']=='e2':edge['attributes']['call_site']=client_site;edge['original_ids'].append(client_site)
    local=ProcessView.from_dict(local_doc)
    target=process('process:orders',target_context,'orders',handler_id=target_handler)
    result=project_http_process_boundary(local,remote,target_processes=[target])
    boundary=next(node for node in result.steps if node.kind=='service_boundary')
    assert boundary.attributes['target_service_id']=='orders'
    assert boundary.attributes['target_context_id']==target_context
    assert any(node.attributes.get('source_process_id')=='process:orders' for node in result.steps)


def test_public_t014_incompatible_release_without_candidate_edge_remains_external():
    from test_cross_service_contract_mapping import trusted_protocol_specimen, refresh_handoff
    from kgmaker.remote_interfaces import project_remote_interfaces
    specimen=trusted_protocol_specimen('HTTP')
    workspace,graph,documents,captured=specimen
    client=next(node for doc in documents for node in doc['nodes'] if node['id']=='client')
    client['attributes']['origin_call_site']='site:client'
    next(release for release in workspace['remote_mapping']['releases'] if release['id']=='provider-v1')['release']='v2'
    refresh_handoff(workspace,graph,documents,captured)
    remote=project_remote_interfaces(workspace,graph,documents,captured=captured,scope='production')
    assert not any(edge.relation=='remote_http_request_response' for edge in remote.edges)
    result=project_http_process_boundary(process('process:client','client-context','checkout'),remote)
    boundary=next(node for node in result.steps if node.kind=='service_boundary')
    assert boundary.attributes['boundary_reason']=='REMOTE_BINDING_UNRESOLVED'
    assert boundary.attributes['target_service_id']=='orders'


def exceptional_process(value):
    doc = value.to_dict()
    failure = deepcopy(next(n for n in doc['technical_view']['nodes'] if n['id'] == 'exit'))
    failure.update(id='failure', kind='exceptional_exit', label='failure', original_ids=['failure'])
    doc['technical_view']['nodes'].append(failure)
    edge = deepcopy(next(e for e in doc['technical_view']['edges'] if e['id'] == 'e2'))
    edge.update(id='e3', target='failure', relation='exception')
    doc['technical_view']['edges'].append(edge)
    doc['exit_ids'].append('failure')
    return ProcessView.from_dict(doc)


def test_normal_and_exceptional_http_continuations_do_not_cross():
    local = exceptional_process(process('local', 'ctx-client', 'client'))
    target = exceptional_process(process('target', 'ctx-target', 'ledger'))
    result = project_http_process_boundary(local, remote_view(), target_processes=[target])
    nodes = {node.id: node for node in result.steps}
    crossed = [(nodes[e.source].kind, nodes[e.target].kind, e.relation)
               for e in result.transitions if e.attributes.get('http_transition') == 'RESPONSE'
               and ((nodes[e.source].kind == 'exceptional_exit') !=
                    (nodes[e.target].kind == 'exceptional_exit'))]
    assert not crossed, crossed


@pytest.mark.parametrize('damage', ['wrong_version', 'stale_edge', 'target_kind',
                                  'target_direction', 'target_scope', 'target_resolution'])
def test_invalid_remote_endpoint_or_binding_cannot_authorize_expansion(damage):
    local = process('local', 'ctx-client', 'client')
    target = process('target', 'ctx-target', 'ledger')
    remote = remote_view().to_dict()
    provider = next(node for node in remote['nodes'] if node['id'] == 'provider')
    if damage == 'wrong_version': remote['rules_version'] = 'not-a-t014-view'
    elif damage == 'stale_edge': remote['edges'][0]['freshness'] = 'STALE'
    elif damage == 'target_kind': provider['kind'] = 'data_resource'
    elif damage == 'target_direction': provider['attributes']['direction'] = 'CONSUMER'
    elif damage == 'target_scope': provider['attributes']['scope'] = 'test'
    else: provider['resolution_status'] = 'UNRESOLVED'
    before = deepcopy(remote)
    try:
        result = project_http_process_boundary(local, ViewDocument.from_dict(remote),
                                               target_processes=[target])
    except ValueError:
        assert remote == before
        return
    assert remote == before
    assert not any(node.attributes.get('source_process_id') == 'target' for node in result.steps), damage


def test_imported_target_truncation_and_limits_remain_visible():
    local = process('local', 'ctx-client', 'client').to_dict()
    local['technical_view']['coverage']['truncated'] = False
    target = process('target', 'ctx-target', 'ledger').to_dict()
    target['technical_view']['coverage']['truncated'] = True
    target['technical_view']['diagnostics'] = [{'code': 'TARGET_NODE_LIMIT'}]
    target['technical_view']['limits'] = ['TARGET_MAX_DEPTH=1']
    result = project_http_process_boundary(ProcessView.from_dict(local), remote_view(),
        target_processes=[ProcessView.from_dict(target)]).to_dict()['technical_view']
    assert result['coverage'].get('truncated') is True, result['coverage']
    assert any(item.get('code') == 'TARGET_NODE_LIMIT' for item in result['diagnostics'])
    assert 'TARGET_MAX_DEPTH=1' in result['limits']


@pytest.mark.parametrize('damage', ['service_scope', 'context_scope', 'stale_context'])
def test_target_selection_must_match_boundary_scope(damage):
    local = process('local', 'ctx-client', 'client')
    target = process('target', 'ctx-target', 'ledger').to_dict()
    selection = target['definition']['context_selection']
    row = selection['services']['ledger']
    if damage == 'service_scope': row['scope'] = 'test'
    elif damage == 'context_scope': row['contexts'][0]['scope'] = 'test'
    else: row['contexts'][0]['freshness'] = 'STALE'
    target['technical_view']['context_selection'] = deepcopy(selection)
    target['definition_fingerprint'] = ProcessDefinition.from_dict(target['definition']).content_fingerprint
    before = deepcopy(target)
    result = project_http_process_boundary(local, remote_view(), target_processes=[target])
    assert not any(n.attributes.get('source_process_id') == 'target' for n in result.steps)
    assert any(n.attributes.get('boundary_reason') == 'TARGET_PROCESS_UNAVAILABLE' for n in result.steps)
    assert target == before


def test_normal_response_retains_original_witness_without_mapping_server_errors():
    local = exceptional_process(process('local', 'ctx-client', 'client'))
    target = exceptional_process(process('target', 'ctx-target', 'ledger'))
    before = local.to_json(), target.to_json()
    result = project_http_process_boundary(local, remote_view(), target_processes=[target])
    nodes = {n.id: n for n in result.steps}
    responses = [e for e in result.transitions if e.attributes.get('http_transition') == 'RESPONSE']
    assert len(responses) == 1
    assert nodes[responses[0].source].kind == 'exit'
    assert responses[0].target == 'exit'
    assert responses[0].attributes['original_continuation_id'] == 'e2'
    assert next(e for e in result.transitions if e.id == 'e3').to_dict() == next(e for e in local.transitions if e.id == 'e3').to_dict()
    assert any(d['code'] == 'HTTP_TARGET_ERROR_BOUNDARY' for d in result.to_dict()['technical_view']['diagnostics'])
    assert (local.to_json(), target.to_json()) == before


@pytest.mark.parametrize('damage', ['source_stale', 'provider_stale', 'edge_scope', 'provider_context'])
def test_remote_stale_or_foreign_binding_preserves_external_boundary(damage):
    local = process('local', 'ctx-client', 'client')
    remote = remote_view().to_dict()
    if damage == 'source_stale': remote['nodes'][0]['freshness'] = 'STALE'
    elif damage == 'provider_stale': next(n for n in remote['nodes'] if n['id'] == 'provider')['freshness'] = 'STALE'
    elif damage == 'edge_scope': remote['edges'][0]['attributes']['scope'] = 'test'
    else: next(n for n in remote['nodes'] if n['id'] == 'provider')['attributes']['context_id'] = 'foreign'
    before = deepcopy(remote)
    result = project_http_process_boundary(local, remote, target_processes=[process('target', 'ctx-target', 'ledger')])
    assert not any(n.attributes.get('source_process_id') == 'target' for n in result.steps)
    assert remote == before


def test_local_and_remote_and_imported_coverage_are_preserved():
    local = process('local', 'ctx-client', 'client').to_dict()
    local['technical_view'].update(limits=['LOCAL_LIMIT'], diagnostics=[{'code': 'LOCAL_DIAGNOSTIC'}])
    remote = remote_view().to_dict()
    remote.update(limits=['REMOTE_LIMIT'], diagnostics=[{'code': 'REMOTE_DIAGNOSTIC'}])
    remote['coverage']['truncated'] = True
    target = process('target', 'ctx-target', 'ledger').to_dict()
    target['technical_view'].update(limits=['TARGET_LIMIT'], diagnostics=[{'code': 'TARGET_DIAGNOSTIC'}])
    target['technical_view']['coverage']['omitted_nodes'] = ['missing-callee']
    before = deepcopy((local, remote, target))
    result = project_http_process_boundary(local, remote, target_processes=[target]).to_dict()['technical_view']
    assert result['coverage']['truncated'] is True
    assert {'LOCAL_LIMIT', 'REMOTE_LIMIT', 'TARGET_LIMIT'} <= set(result['limits'])
    assert {'LOCAL_DIAGNOSTIC', 'REMOTE_DIAGNOSTIC', 'TARGET_DIAGNOSTIC'} <= {d['code'] for d in result['diagnostics']}
    target_coverage = next(c for c in result['coverage']['http_upstream_coverage'] if c['kind'] == 'target_process')
    assert target_coverage['coverage']['omitted_nodes'] == ['missing-callee']
    assert (local, remote, target) == before


def test_terminal_only_target_does_not_supply_a_cfg_body():
    target = process('target', 'ctx-target', 'ledger', with_cfg=False).to_dict()
    failure = deepcopy(next(n for n in target['technical_view']['nodes'] if n['id'] == 'exit'))
    failure.update(id='failure', kind='exceptional_exit', label='failure', original_ids=['failure'])
    target['technical_view']['nodes'].append(failure)
    target['exit_ids'].append('failure')
    result = project_http_process_boundary(process('local', 'ctx-client', 'client'), remote_view(), target_processes=[target])
    assert not any(n.attributes.get('source_process_id') == 'target' for n in result.steps)
    assert any(n.attributes.get('boundary_reason') == 'TARGET_PROCESS_UNAVAILABLE' for n in result.steps)


@pytest.mark.parametrize('mode', ['resolved', 'ambiguous', 'unresolved_selector'])
def test_expanded_local_callee_exception_cannot_start_remote_request_and_return_normally(mode):
    doc = exceptional_process(process('local', 'ctx-client', 'client')).to_dict()
    view = doc['technical_view']
    # Exact structural shape emitted by flow.process expansion (flow.py:181-195):
    # caller -> child entry; child normal exit -> normal continuation;
    # child exceptional exit -> exception continuation, all bound to one site.
    for identity, kind in [('callee-entry', 'entry'), ('callee-exit', 'exit'),
                           ('callee-error', 'exceptional_exit')]:
        node = deepcopy(next(n for n in view['nodes'] if n['id'] == 'exit'))
        node.update(id=identity, kind=kind, label=kind, original_ids=[identity])
        view['nodes'].append(node)
    for edge in view['edges']:
        if edge['id'] == 'e2':
            edge.update(source='callee-exit', relation='returns_to')
            edge['attributes']['caller_block'] = 'local-call'
        if edge['id'] == 'e3':
            edge.update(source='callee-error', relation='exception')
            edge['attributes']['caller_block'] = 'local-call'
    template = deepcopy(view['edges'][0])
    for identity, source, target, relation in [
        ('callee-call', 'local-call', 'callee-entry', 'call'),
        ('callee-success', 'callee-entry', 'callee-exit', 'normal'),
        ('callee-failure', 'callee-entry', 'callee-error', 'exception'),
    ]:
        edge = deepcopy(template)
        edge.update(id=identity, source=source, target=target, relation=relation,
                    original_ids=[identity])
        if identity == 'callee-call':
            edge['attributes'].update(call_site='site:client', caller_block='local-call')
            edge['original_ids'].append('site:client')
        view['edges'].append(edge)
    local = ProcessView.from_dict(doc)
    remote = remote_view(status='AMBIGUOUS' if mode == 'ambiguous' else 'RESOLVED').to_dict()
    if mode == 'unresolved_selector':
        binding = deepcopy(next(n for n in remote['nodes'] if n['id'] == 'provider'))
        binding.update(id='binding', kind='remote_binding', original_ids=['binding'], resolution_status='UNRESOLVED')
        binding['attributes'].update(source_interface_id='client', unresolved_selectors=[{
            'id': 'v1', 'context_id': 'ctx-target', 'service_id': 'ledger'}])
        remote['nodes'].append(binding)
        remote['edges'] = []
    result = project_http_process_boundary(local, remote,
        target_processes=[process('target', 'ctx-target', 'ledger')])
    requests = [e for e in result.transitions if e.attributes.get('http_transition') == 'REQUEST']
    assert len(requests) == 1 and requests[0].source == 'local-call'
    adjacency = {}
    for edge in result.transitions:
        adjacency.setdefault(edge.source, []).append(edge.target)
    seen = set()
    pending = ['callee-error']
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency.get(current, []))
    assert 'exit' not in seen, 'Expanded local exception acquired a remote request/normal response path'
    assert 'failure' in seen, 'Original local exception continuation must remain'

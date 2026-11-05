"""Pure T014 public contracts; hand-labelled W07 inputs are not compiler proof."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from test_cross_service_contract_mapping import trusted_protocol_specimen, refresh_handoff


def project(specimen):
    assert importlib.util.find_spec('kgmaker.remote_interfaces'), 'T014 projection API is absent'
    module = importlib.import_module('kgmaker.remote_interfaces')
    workspace, graph, documents, captured = specimen
    return module.project_remote_interfaces(workspace, graph, documents,
        captured=captured, scope='production')


@pytest.mark.parametrize('transport,relation',[('HTTP','remote_http_request_response'),
                                             ('KAFKA','remote_kafka_publish_subscribe')])
def test_public_explicit_mapping_is_static_remote_view_with_original_endpoints(transport,relation):
    specimen=trusted_protocol_specimen(transport)
    before=deepcopy((specimen[0],specimen[1].to_dict(),specimen[2:]))
    view=project(specimen)
    assert view.kind=='topology' and view.scope=='production'
    edges=[e for e in view.edges if e.relation==relation]
    assert len(edges)==1 and edges[0].source=='client' and edges[0].target=='provider'
    edge=edges[0]
    assert edge.freshness=='UNKNOWN' and edge.resolution_status=='RESOLVED'
    assert edge.attributes['capture_freshness']=='CAPTURE_TIME_ONLY'
    assert edge.attributes['runtime_execution']=='NOT_OBSERVED'
    assert edge.attributes['payload_compatibility']=='UNKNOWN'
    assert edge.evidence_kinds==('SOURCE_ONLY',) and edge.supporting_refs==()
    assert edge.unknown_refs==edge.evidence_refs
    assert not any(e.relation in {'calls','next','dispatches_to'} for e in view.edges)
    assert (specimen[0],specimen[1].to_dict(),specimen[2:])==before


def test_same_url_without_explicit_mapping_retains_unresolved_source_boundary():
    specimen=trusted_protocol_specimen();specimen[0]['remote_mapping']['mappings']=[]
    refresh_handoff(*specimen)
    view=project(specimen)
    assert not view.edges
    assert {'client','provider'} <= {n.id for n in view.nodes}
    boundaries=[n for n in view.nodes if n.kind=='unresolved_remote_target']
    assert len(boundaries)==1 and boundaries[0].attributes['source_interface_id']=='client'
    assert boundaries[0].attributes['reason']=='NO_EXPLICIT_REMOTE_MAPPING'


@pytest.mark.parametrize('field',['release','sha256','pointer'])
def test_incompatible_pair_never_projects_confirmed_edge(field):
    specimen=trusted_protocol_specimen();target=specimen[0]['remote_mapping']['releases'][1]
    if field=='release':target[field]='v2'
    else:target['contract'][field]='b'*64 if field=='sha256' else '#/paths/~1foreign/post'
    refresh_handoff(*specimen);view=project(specimen)
    assert not view.edges
    binding=next(n for n in view.nodes if n.kind=='remote_binding')
    assert binding.resolution_status=='UNRESOLVED'
    assert 'REMOTE_CONTRACT_OR_RELEASE_INCOMPATIBLE' in binding.attributes['reasons']


def add_target(specimen, *, valid=True):
    workspace,graph,docs,captured=specimen
    document=next(d for d in docs if any(n['id']=='provider' for n in d['nodes']))
    node=deepcopy(next(n for n in document['nodes'] if n['id']=='provider'));node['id']='provider-two'
    document['nodes'].append(node)
    release=deepcopy(workspace['remote_mapping']['releases'][1]);release.update(id='provider-two-release',interface_id='provider-two')
    if not valid:release['release']='v2'
    workspace['remote_mapping']['releases'].append(release)
    workspace['remote_mapping']['mappings'].append({'id':'two','transport':'HTTP',
        'source_release_id':'client-v1','target_release_id':release['id'],'compatibility_id':None})
    refresh_handoff(*specimen)


def test_ambiguity_preserves_all_candidates_without_selected_winner():
    specimen=trusted_protocol_specimen();add_target(specimen)
    view=project(specimen)
    assert {e.target for e in view.edges}=={'provider','provider-two'}
    assert all(e.resolution_status=='AMBIGUOUS' for e in view.edges)
    binding=next(n for n in view.nodes if n.kind=='remote_binding')
    assert len(binding.attributes['candidates'])==2
    specimen[0]['remote_mapping']['mappings'].reverse();refresh_handoff(*specimen)
    reordered=project(specimen)
    assert {e.target for e in reordered.edges}=={'provider','provider-two'}
    assert {e.id for e in reordered.edges}=={e.id for e in view.edges}
    assert all(e.resolution_status=='AMBIGUOUS' for e in reordered.edges)


def test_one_candidate_and_incomplete_mapping_does_not_claim_unique_resolved():
    specimen=trusted_protocol_specimen();add_target(specimen,valid=False)
    view=project(specimen)
    assert len(view.edges)==1 and view.edges[0].resolution_status=='UNRESOLVED'
    binding=next(n for n in view.nodes if n.kind=='remote_binding')
    assert binding.attributes['unresolved_mapping_ids']==['two']
    assert 'REMOTE_CANDIDATE_SET_INCOMPLETE' in binding.attributes['reasons']


@pytest.mark.parametrize('case',['workspace','graph','interface','selection','capture'])
def test_foreign_or_changed_captured_inputs_reject_without_mutation(case):
    specimen=trusted_protocol_specimen()
    if case=='workspace':specimen[0]['workspace_id']='foreign'
    elif case=='graph':specimen[1].files['foreign']='a'*64
    elif case=='interface':specimen[2][0]['nodes'][0]['owner_id']='service:foreign'
    elif case=='selection':specimen[3]['selection']['scope']='test'
    else:specimen[3]['contract_capture']['files'].clear()
    before=deepcopy((specimen[0],specimen[1].to_dict(),specimen[2:]))
    with pytest.raises(ValueError):project(specimen)
    assert (specimen[0],specimen[1].to_dict(),specimen[2:])==before


def test_pure_projection_does_not_capture_read_files_or_invoke_upstream_projectors(monkeypatch):
    from pathlib import Path
    import socket,subprocess
    import kgmaker.interfaces,kgmaker.remote_mapping
    specimen=trusted_protocol_specimen()
    def forbidden(*args,**kwargs):raise AssertionError('No I/O or upstream projection')
    for name in ['read_text','read_bytes','open','write_text']:monkeypatch.setattr(Path,name,forbidden)
    monkeypatch.setattr(socket,'socket',forbidden);monkeypatch.setattr(subprocess,'Popen',forbidden)
    for name in ['project_http_providers','project_http_consumers','project_kafka_interfaces',
                 'capture_interface_contracts','attach_interface_contracts']:
        monkeypatch.setattr(kgmaker.interfaces,name,forbidden)
    monkeypatch.setattr(kgmaker.remote_mapping,'capture_remote_mapping_inputs',forbidden)
    assert project(specimen).kind=='topology'


def test_raw_labels_attributes_proof_payloads_are_omitted_but_original_proof_buckets_preserved():
    from kgmaker.architecture_model import ViewDocument
    from kgmaker.remote_mapping import _views
    specimen=trusted_protocol_specimen();workspace,graph,docs,captured=specimen
    node=next(n for d in docs for n in d['nodes'] if n['id']=='client')
    node['label']='PRIVATE_SENTINEL';node['attributes']['password']='PRIVATE_SENTINEL'
    node.update(evidence_refs=['e:client'],evidence_kinds=['SYMBOL_RESOLVED'],supporting_refs=['e:client'],unknown_refs=[])
    doc=next(d for d in docs if node in d['nodes'])
    doc['provenance']=[{'id':'e:client','evidence_kind':'SYMBOL_RESOLVED','polarity':'SUPPORTING',
        'freshness':'CURRENT','scope':'production','context_ids':['client-context'],'raw_secret':'PRIVATE_SENTINEL'}]
    refresh_handoff(*specimen);view=project(specimen);value=view.to_dict()
    import json
    assert 'PRIVATE_SENTINEL' not in json.dumps(value)
    original=next(n for n in view.nodes if n.id=='client')
    assert original.supporting_refs==('e:client',) and original.evidence_kinds==('SYMBOL_RESOLVED',)
    edge=view.edges[0]
    assert edge.evidence_kinds==('SOURCE_ONLY',) and edge.supporting_refs==()
    assert 'e:client' in edge.attributes['original_evidence_refs']
    ViewDocument.from_dict(value)


@pytest.mark.parametrize('case',['cycle','shared','deep','object_limit'])
def test_projection_bounds_are_controlled_before_publication(case,monkeypatch):
    import kgmaker.remote_interfaces as module
    specimen=trusted_protocol_specimen()
    if case=='object_limit':monkeypatch.setattr(module,'_MAX_OBJECTS',1)
    elif case=='cycle':specimen[3]['extra']=specimen[3]
    elif case=='shared':specimen[3]['extra']=['x'*1000]*33000
    else:
        child={};specimen[3]['extra']=child
        for _ in range(90):child['next']={};child=child['next']
    with pytest.raises(ValueError):project(specimen)


def test_unknown_source_selector_is_retained_without_fabricating_endpoint():
    specimen=trusted_protocol_specimen();specimen[0]['remote_mapping']['releases'][0]['interface_id']='absent'
    refresh_handoff(*specimen);view=project(specimen)
    assert not view.edges and not any(n.id=='absent' for n in view.nodes)
    boundary=next(n for n in view.nodes if n.attributes.get('reason')=='REMOTE_SOURCE_INTERFACE_UNAVAILABLE')
    assert boundary.original_ids==('absent',) and boundary.resolution_status=='UNRESOLVED'


def test_kafka_realm_groups_and_http_origin_refs_remain_explicit():
    specimen=trusted_protocol_specimen('KAFKA');view=project(specimen)
    provider=next(n for n in view.nodes if n.id=='provider')
    assert provider.attributes['broker_realm']=='alpha'
    assert provider.attributes['consumer_group']=='group-one'
    assert provider.attributes['topics']==['orders']
    assert view.edges[0].attributes['consumer_group']=='group-one'
    specimen=trusted_protocol_specimen();node=next(n for d in specimen[2] for n in d['nodes'] if n['id']=='client')
    node['attributes'].update(caller='caller:one',origin_call_site='site:origin',terminal_call_site='site:terminal')
    refresh_handoff(*specimen);view=project(specimen)
    original=next(n for n in view.nodes if n.id=='client')
    assert original.attributes['caller']=='caller:one'
    assert original.attributes['origin_call_site']=='site:origin'
    assert original.attributes['terminal_call_site']=='site:terminal'


@pytest.mark.parametrize('identity',['//alice:PRIVATE_SENTINEL@host/path','prefix //alice:PRIVATE_SENTINEL@host/path'])
def test_unsafe_required_source_reference_has_fixed_error_and_no_mutation(identity):
    specimen=trusted_protocol_specimen();node=next(n for d in specimen[2] for n in d['nodes'] if n['id']=='client')
    node['original_ids'].append(identity);refresh_handoff(*specimen)
    before=deepcopy((specimen[0],specimen[1].to_dict(),specimen[2:]))
    with pytest.raises(ValueError) as error:project(specimen)
    assert str(error.value)=='REMOTE_VIEW_UNSAFE_REFERENCE' and 'PRIVATE_SENTINEL' not in repr(error.value)
    assert (specimen[0],specimen[1].to_dict(),specimen[2:])==before


def test_unresolved_declared_target_selector_stays_visible_without_endpoint_invention():
    specimen=trusted_protocol_specimen();target=specimen[0]['remote_mapping']['releases'][1]
    target['interface_id']='missing-provider';refresh_handoff(*specimen)
    view=project(specimen)
    boundary=next(n for n in view.nodes if n.attributes.get('target_selector'))
    assert boundary.attributes['target_selector']['interface_id']=='missing-provider'
    assert not any(n.id=='missing-provider' for n in view.nodes)
    binding=next(n for n in view.nodes if n.kind=='remote_binding')
    assert binding.attributes['unresolved_selectors'][0]['interface_id']=='missing-provider'
    assert binding.resolution_status=='UNRESOLVED' and view.coverage['status']=='PARTIAL'

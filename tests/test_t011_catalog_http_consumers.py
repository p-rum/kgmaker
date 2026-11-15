"""T011 projection over captured, actual pinned W06 compiler output."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.inspection import inspect_jvm, command
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import load_workspace, snapshot_workspace, split_id
from test_http_client_execution import api_jars

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''package demo;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.beans.factory.annotation.Value;
@FeignClient(name="remote",url="https://remote.example.invalid") interface Remote {
 @GetMapping("/remote") String get();
}
class Clients {
 @Value("${orders.base}") String base;
 void configured(){WebClient.create(base).get().uri("/configured").retrieve().bodyToMono(String.class);}
 void lazy(){WebClient.create("https://orders.example.invalid").get().uri("/lazy").retrieve().bodyToMono(String.class);}
 String active(){return WebClient.create("https://orders.example.invalid").get().uri("/active").retrieve().bodyToMono(String.class).block();}
 void dynamic(String route){WebClient.create("https://orders.example.invalid").get().uri(route).retrieve().bodyToMono(String.class);}
 void shared(){var r=WebClient.create("https://orders.example.invalid").get().uri("/shared").retrieve().bodyToMono(String.class);r.block();r.block();}
 void twins(){WebClient.create("https://orders.example.invalid").get().uri("/same").retrieve().bodyToMono(String.class);WebClient.create("https://orders.example.invalid").get().uri("/same").retrieve().bodyToMono(String.class);}
 String first(Remote client){return client.get();}
 String second(Remote client){return client.get();}
}
'''


@pytest.fixture(scope='module', params=['k1', 'k2'])
def captured(request, tmp_path_factory):
    base = tmp_path_factory.mktemp('t011-' + request.param)
    repo = base / 'alpha'; path = repo / 'src/main/java/demo/Clients.java'
    path.parent.mkdir(parents=True); path.write_text(SOURCE)
    contract = repo / 'contracts/http.json'; contract.parent.mkdir(); contract.write_text('{"openapi":"3.0.3","paths":{}}')
    subprocess.run(['git','init','-q',str(repo)],check=True)
    try:
        command('jvm', ROOT/'workers', kotlin_backend=request.param)
        jars = api_jars()
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1': pytest.fail(str(error))
        pytest.skip(str(error))
    prop=repo/'src/main/resources/application-test.properties';prop.parent.mkdir(parents=True);prop.write_text('orders.base=https://orders.example.invalid\n')
    result = inspect_jvm(repo, home=ROOT/'workers', classpath=jars, kotlin_backend=request.param,
                         repo_id='alpha', module='client-app', build_context={'spring_profiles':['test'],
                         'spring_properties':{'orders.base':'https://orders.example.invalid'}})
    assert not any('.err.' in item.get('code','') for item in result['diagnostics'])
    manifest = base/'workspace.json'
    manifest.write_text(json.dumps({'schema_version':1,'workspace_id':'consumers',
        'repositories':[{'id':'alpha','role':'backend','path':'alpha'}],
        'services':[{'id':'orders','backend_repo':'alpha','frontend_repos':[],'test_repos':[],
                     'contract':{'repo_id':'alpha','path':'contracts/http.json'}}],
        'service_ownership':{'schema_version':1,'services':[{'id':'orders',
            'roots':[{'repo_id':'alpha','path':'src'}],'modules':[],'external_systems':[]}]}}))
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    assert any(n.kind=='http_request_definition' for n in graph.nodes)
    (base / ('captured-' + request.param + '.json')).write_text(json.dumps(graph.to_dict(), indent=2))
    return load_workspace(manifest),graph,coverage


def project(captured):
    from kgmaker.interfaces import project_http_consumers
    workspace,graph,coverage = captured
    return project_http_consumers(workspace,graph,source_coverage=coverage)


def consumers(document):
    return [n for n in document.nodes if n.kind=='http_interface']


def test_actual_lazy_definition_and_static_trigger_are_not_network_observations(captured):
    document = project(captured)
    nodes = consumers(document)
    lazy = next(n for n in nodes if n.attributes['route_expression']=='/lazy')
    active = next(n for n in nodes if n.attributes['route_expression']=='/active')
    assert lazy.attributes['execution_status']=='UNSUBSCRIBED_WITHIN_SCOPE'
    assert active.attributes['execution_status']=='STATIC_TRIGGER'
    assert all(n.attributes['runtime_execution']=='NOT_OBSERVED' for n in nodes)
    assert all(n.attributes['service_binding'] is None for n in nodes)
    assert all(n.attributes['direction']=='CONSUMER' for n in nodes)
    assert document.kind=='interfaces' and document.coverage['status']=='PARTIAL'


def test_dynamic_uri_and_same_path_calls_keep_original_occurrences(captured):
    nodes = consumers(project(captured))
    dynamic = [n for n in nodes if n.attributes['route_expression'] is None]
    assert dynamic and all(n.attributes['origin_call_site'] for n in dynamic)
    assert all(n.resolution_status=='UNRESOLVED' and n.attributes['unresolved_reasons'] for n in dynamic)
    twins = [n for n in nodes if n.attributes['route_expression']=='/same']
    assert len(twins)==2 and len({n.id for n in twins})==2
    assert len({n.attributes['origin_call_site'] for n in twins})==2


def test_feign_terminals_are_owned_by_actual_distinct_callers(captured):
    nodes = [n for n in consumers(project(captured)) if n.attributes['family']=='FEIGN']
    assert len(nodes)==2 and len({n.id for n in nodes})==2
    assert len({n.attributes['caller'] for n in nodes})==2
    assert len({n.attributes['terminal_call_site'] for n in nodes})==2
    assert all(n.attributes['execution_status']=='FEIGN_INVOCATION_INTENT' for n in nodes)


def test_projection_is_offline_and_preserves_input_snapshots(captured):
    w,g,c = captured; before=deepcopy((w,g.to_dict(),c))
    with patch('subprocess.Popen',side_effect=AssertionError('projection spawned process')),\
         patch('socket.socket',side_effect=AssertionError('projection opened network')):
        document=project(captured)
    assert consumers(document)
    assert (w,g.to_dict(),c)==before


@pytest.mark.parametrize('case', ['caller_shape','chain_shape','state_shape','wrong_owner',
    'node_scope','source_hash','request_identity','route_mirror','edge_source','proof_source',
    'terminal_caller','uri_private','route_shape','uri_kind_shape','uri_extra','uri_missing_sha'])
def test_captured_malformed_source_and_proof_fail_closed_without_mutation(captured, case):
    from kgmaker.interfaces import project_http_consumers, InterfaceProjectionError
    w,original,c = captured; graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition'
                 and n.metadata.get('path')=='/active')
    md=request.metadata
    if case=='caller_shape':md['caller']=[]
    elif case=='chain_shape':md['chain_call_site_ids']={}
    elif case=='state_shape':md['execution_status']=[]
    elif case=='wrong_owner':md['caller']=next(n.id for n in graph.nodes if n.kind=='method' and n.id!=md['caller'])
    elif case=='node_scope':
        caller=next(n for n in graph.nodes if n.id==md['caller'])
        graph.nodes[graph.nodes.index(caller)]=replace(caller,scope='test')
    elif case=='source_hash':
        site=next(s for s in graph.call_sites if s['id']==md['origin_call_site']);site['sha256']='0'*64
    elif case=='request_identity':graph.nodes[graph.nodes.index(request)]=replace(request,id='repo:alpha:forged-request')
    elif case=='route_mirror':md['path']='/forged'
    elif case=='edge_source':
        edge=next(e for e in graph.edges if e.target==request.id and e.kind=='defines_http_request')
        graph.edges[graph.edges.index(edge)]=replace(edge,source_file='@alpha/src/main/java/Foreign.java')
    elif case=='proof_source':
        proof=next(p for p in graph.evidence if p.get('target')==request.id);proof['sha256']='0'*64
    elif case=='terminal_caller':
        site=next(s for s in graph.call_sites if s['id']==md['terminal_call_site_ids'][0]);site['caller']=[]
    elif case=='uri_private':md['path']='/orders?secret-marker=1'
    elif case=='route_shape':md['path']=['/bad']
    elif case=='uri_kind_shape':md['uri_provenance'][0]['kind']=[]
    elif case=='uri_extra':md['uri_provenance'][0]['private']='secret-marker'
    elif case=='uri_missing_sha':md['uri_provenance'][0].update(source_file='@alpha/absent',sha256=None)
    before=deepcopy((w,graph.to_dict(),c))
    with pytest.raises(InterfaceProjectionError):project_http_consumers(w,graph,source_coverage=c)
    assert (w,graph.to_dict(),c)==before


def test_explicitly_selected_context_ignores_malformed_stale_sibling(captured):
    from kgmaker.interfaces import project_http_consumers
    from kgmaker.workspace import qualified
    w,original,c=captured;graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition')
    cid=request.metadata['context_id'];ctx=deepcopy(next(x for x in graph.contexts if x['id']==cid))
    ctx['id']=qualified('alpha','stale-sibling');ctx['freshness']='STALE';ctx['stale_reason']='historical'
    graph.contexts.append(ctx)
    md=deepcopy(request.metadata);md.update(context_id=ctx['id'],caller=[])
    graph.nodes.append(replace(request,id=qualified('alpha','stale-request'),metadata=md))
    doc=project_http_consumers(w,graph,source_coverage=c,
        selected_contexts={('orders','alpha','client-app'):cid})
    assert len(consumers(doc))==len(consumers(project(captured)))
    assert any(d['code']=='HTTP_CONSUMER_CONTEXT_NOT_SELECTED' for d in doc.diagnostics)


def test_configured_uri_preserves_only_captured_property_provenance(captured):
    node=next(n for n in consumers(project(captured)) if n.attributes['route_expression']=='/configured')
    assert any(p.get('status')=='MATCHED' and p['source_file'].endswith('application-test.properties')
               for p in node.attributes['uri_provenance'])
    assert node.attributes['service_binding'] is None


def test_existing_evidence_polarity_buckets_remain_distinct(captured):
    from kgmaker.interfaces import project_http_consumers
    w,original,c=captured;graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition' and n.metadata['path']=='/active')
    proof=next(p for p in graph.evidence if p.get('target')==request.id)
    proof['polarity']='CONTRADICTING'
    node=next(n for n in consumers(project_http_consumers(w,graph,source_coverage=c))
              if n.attributes['request_definition_id']==request.id)
    assert proof['id'] in node.contradicting_refs
    assert proof['id'] not in node.supporting_refs and proof['id'] not in node.unknown_refs


def test_two_terminals_of_same_publisher_remain_distinct_occurrences(captured):
    nodes=[n for n in consumers(project(captured)) if n.attributes['route_expression']=='/shared']
    assert len(nodes)==2 and len({n.id for n in nodes})==2
    assert len({n.attributes['request_definition_id'] for n in nodes})==1
    assert len({n.attributes['terminal_call_site'] for n in nodes})==2


def test_scope_selection_never_promotes_production_calls_to_test(captured):
    from kgmaker.interfaces import project_http_consumers
    w,g,c=captured
    document=project_http_consumers(w,g,scope='test',source_coverage=c)
    assert consumers(document)==[] and document.scope=='test'


def test_unknown_request_rule_is_visible_without_strong_claim(captured):
    from kgmaker.interfaces import project_http_consumers
    w,original,c=captured;graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition' and n.metadata['path']=='/lazy')
    request.metadata['rule_version']='future-version'
    doc=project_http_consumers(w,graph,source_coverage=c)
    assert all(n.attributes['request_definition_id']!=request.id for n in consumers(doc))
    assert any(d['code']=='HTTP_CONSUMER_RULE_UNKNOWN' for d in doc.diagnostics)


@pytest.mark.parametrize('unproved', ['repo:alpha:unproved-declaration', {'private':'unproved'}, ['unproved']])
def test_non_feign_extra_declaration_is_not_emitted_as_proved_reference(captured, unproved):
    from kgmaker.interfaces import project_http_consumers
    w,original,c=captured;graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition' and n.metadata['path']=='/active')
    request.metadata['declaration']=unproved
    before=deepcopy((w,graph.to_dict(),c))
    node=next(n for n in consumers(project_http_consumers(w,graph,source_coverage=c))
              if n.attributes['request_definition_id']==request.id)
    assert node.attributes['declaration_id'] is None
    assert (w,graph.to_dict(),c)==before


@pytest.mark.parametrize('field,value', [('key','missing.property'), ('profiles',['other']), ('source_file','caller')])
def test_configured_uri_requires_exact_hash_bound_context_record(captured, field, value):
    from kgmaker.interfaces import project_http_consumers, InterfaceProjectionError
    w,original,c=captured;graph=deepcopy(original)
    request=next(n for n in graph.nodes if n.kind=='http_request_definition' and n.metadata['path']=='/configured')
    record=next(p for p in request.metadata['uri_provenance'] if p.get('status')=='MATCHED')
    if field=='source_file':
        record['source_file']=request.path;record['sha256']=graph.files[request.path]
    else:
        record[field]=value
    before=deepcopy((w,graph.to_dict(),c))
    with pytest.raises(InterfaceProjectionError):project_http_consumers(w,graph,source_coverage=c)
    assert (w,graph.to_dict(),c)==before

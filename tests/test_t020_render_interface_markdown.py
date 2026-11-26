"""T020 public Markdown AST and snapshot contracts; no native/app observations."""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import os
import re

import pytest

# Explicit development-only preparation; product imports never require this.
try:
    from markdown_it import MarkdownIt
except ImportError:
    if os.environ.get('KGMAKER_REQUIRE_MARKDOWN_PARSER')=='1':
        pytest.fail('Required dev parser unavailable; prepare tests/requirements-markdown.txt explicitly.',pytrace=False)
    pytest.skip('prepare tests/requirements-markdown.txt explicitly',allow_module_level=True)
from kgmaker.architecture_model import ViewDocument,ViewNode


def render(value):
    return importlib.import_module('kgmaker.architecture_render').render_interface_markdown(value)


def parsed(markdown):
    return MarkdownIt('commonmark',{'html':True,'linkify':False}).enable('table').parse(markdown)


def visible(tokens):
    return '\n'.join(''.join(child.content for child in token.children or [] if child.type in {'text','code_inline'})
                     for token in tokens if token.type=='inline')


def catalogue():
    """Hand-labelled ViewDocument, not a compiler/native fixture."""
    provider=ViewNode('interface:provided','http_interface','POST /orders',owner_id='service:orders',
        original_ids=('handler:orders',),evidence_refs=('proof:declaration',),evidence_kinds=('SOURCE_ONLY',),
        freshness='CURRENT',resolution_status='RESOLVED',unknown_refs=('proof:declaration',),
        attributes={'service_id':'orders','direction':'PROVIDED','protocol':'HTTP','http_method':'POST',
            'normalized_route':'/orders','context_ids':['server-context'],'implementation_status':'CONTRACT_ONLY',
            'runtime_status':'UNKNOWN','deployment_status':'UNKNOWN','contract_bindings':[{
                'version':1,'role':'PROVIDER_DECLARATION','status':'BOUND_DECLARATION',
                'contract':{'repo_id':'contract','path':'orders.json'},'raw_sha256':'a'*64,
                'revision':'v1','revision_fingerprint':'b'*64,'operation_pointer':'#/paths/~1orders/post',
                'schema_references':[],'payload_compatibility':'UNKNOWN','reasons':[],
                'evidence_ref':'proof:declaration'}]})
    consumer=ViewNode('interface:consumer','http_interface','POST /orders',owner_id='service:checkout',
        attributes={'service_id':'checkout','direction':'CONSUMER','family':'SPRING_WEBCLIENT',
            'context_id':'client-context','http_method':'POST','route_expression':'/orders',
            'execution_status':'UNSUBSCRIBED_WITHIN_SCOPE','runtime_execution':'NOT_OBSERVED',
            'unresolved_reasons':['TERMINAL_NOT_PROVED']})
    generated=ViewNode('generated:client','generated_client','Client.java',owner_id='service:checkout',
        attributes={'generation_status':'STALE','payload_compatibility':'UNKNOWN'})
    return ViewDocument('view:interfaces:fixture','interfaces','c'*64,'catalog-fixture-1','production',
        {'services':{'checkout':{'contexts':[{'context_id':'client-context'}]},'orders':{'contexts':[{'context_id':'server-context'}]}}},
        nodes=(provider,consumer,generated),provenance=({'id':'proof:declaration','evidence_kind':'SOURCE_ONLY',
            'freshness':'CURRENT','polarity':'UNKNOWN','source_file':'@contract/orders.json','raw_sha256':'a'*64},),
        diagnostics=({'code':'SCOPE_PARTIAL','message':'Selected source declarations only.'},),
        coverage={'status':'PARTIAL','counts':{'found':2,'resolved':1,'unresolved':1,'excluded':0},
            'reasons':['Captured interfaces only.']},limits=('Runtime availability is not observed.',))


def test_public_golden_keeps_original_ids_statuses_contexts_and_evidence_links():
    doc=catalogue();ViewDocument.from_dict(doc.to_dict()) # baseline fixture validity independent of renderer
    before=deepcopy(doc.to_dict());markdown=render(doc);tokens=parsed(markdown);text=visible(tokens)
    for expected in ('interface:provided','interface:consumer','generated:client','handler:orders',
                     'proof:declaration','server-context','client-context','RESOLVED','UNRESOLVED',
                     'CURRENT','UNKNOWN','SOURCE_ONLY','BOUND_DECLARATION','PROVIDER_DECLARATION',
                     'UNSUBSCRIBED_WITHIN_SCOPE','NOT_OBSERVED','STALE','PARTIAL'):
        assert expected in text,expected
    headings=[tokens[i+1].content for i,t in enumerate(tokens[:-1]) if t.type=='heading_open' and t.tag=='h2']
    assert headings==['Snapshot','Provided interfaces','Used interfaces','Generated and unclassified',
        'Contract bindings','Unresolved and stale','Evidence and origins','Diagnostics and limits']
    hrefs=[c.attrGet('href') for t in tokens for c in t.children or [] if c.type=='link_open']
    assert hrefs and all(re.fullmatch(r'#evidence-[a-f0-9]{64}',href) for href in hrefs)
    assert all('id="'+href[1:]+'"' in markdown for href in hrefs)
    assert doc.to_dict()==before


def test_public_hostile_label_keeps_table_and_block_structure():
    doc=catalogue();baseline=parsed(render(doc))
    hostile='evil | `code` \\ \\|\r\n# injected\n```html\n<script>x</script>\n![x](https://evil.invalid)\n[x](javascript:alert(1))\u2028- list'
    changed=replace(doc,nodes=(replace(doc.nodes[0],label=hostile),*doc.nodes[1:]));before=deepcopy(changed.to_dict())
    markdown=render(changed);tokens=parsed(markdown)
    shape=lambda values:[(t.type,t.tag) for t in values]
    assert shape(tokens)==shape(baseline)
    for token in tokens:
        assert token.type!='fence'
        if token.type in {'html_block','html_inline'}:assert re.fullmatch(r'<a id="evidence-[a-f0-9]{64}"></a>\n?',token.content)
        for child in token.children or []:
            assert child.type!='image'
            if child.type=='html_inline':assert child.content=='</a>' or re.fullmatch(r'<a id="evidence-[a-f0-9]{64}">',child.content)
            if child.type=='link_open':assert child.attrGet('href').startswith('#evidence-')
    assert 'evil | `code`' in visible(tokens)
    assert changed.to_dict()==before


def test_public_empty_scope_retains_unknown_coverage_and_diagnostics():
    doc=replace(catalogue(),nodes=(),provenance=(),scope='test',context_selection={},
        coverage={'status':'UNKNOWN','counts':{'found':0,'resolved':0,'unresolved':0,'excluded':0},
            'reasons':['NO_CAPTURED_INPUTS']},diagnostics=({'code':'NO_SELECTED_CONTEXT','message':'No captured context.'},))
    text=visible(parsed(render(doc)))
    assert all(x in text for x in ('test','UNKNOWN','NO_CAPTURED_INPUTS','NO_SELECTED_CONTEXT'))
    assert 'no integrations' not in text.lower()


def test_public_cli_markdown_uses_same_snapshot_and_strict_exit(tmp_path):
    from test_t019_add_architecture_json_cli import run_cli,write
    from test_cross_service_contract_mapping import trusted_protocol_specimen,refresh_handoff
    from kgmaker.remote_mapping import _workspace
    workspace,graph,docs,captured=trusted_protocol_specimen()
    for doc in docs:
        name=next(n for n in ['http-providers','http-consumers','kafka-interfaces'] if doc['rules_version'].startswith(n))
        doc['view_id']='view:'+name+':'+workspace['workspace_id']+':production'
    refresh_handoff(workspace,graph,docs,captured)
    bundle={'schema_version':1,'rules_version':'architecture-interface-inputs-1','workspace':_workspace(workspace),
        'graph':graph.to_dict(),'captured':captured};path=write(tmp_path/'bundle.json',bundle);before=path.read_bytes()
    json_result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path)
    assert json_result.returncode==0,json_result.stderr
    result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path,'--format','markdown')
    assert result.returncode==0,result.stderr
    assert result.stdout==render(json.loads(json_result.stdout))
    strict=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path,'--format','markdown','--strict')
    assert strict.returncode==4 and strict.stdout==result.stdout
    assert path.read_bytes()==before


@pytest.mark.parametrize('identity',['interface:one|`x`[0]','interface:Unicode-žluťoučký'])
def test_escaped_ids_remain_exact_decoded_text_and_have_generated_anchor(identity):
    doc=catalogue();doc=replace(doc,nodes=(replace(doc.nodes[0],id=identity),*doc.nodes[1:]))
    markdown=render(doc);assert identity in visible(parsed(markdown))
    import hashlib
    anchor='evidence-'+hashlib.sha256(identity.encode()).hexdigest()
    assert '(#'+anchor+')' in markdown and 'id="'+anchor+'"' in markdown


def test_row_order_and_json_mapping_input_are_deterministic_without_mutation():
    doc=catalogue();second=replace(doc.nodes[0],id='interface:alpha',owner_id='service:alpha',attributes={**doc.nodes[0].attributes,'service_id':'alpha'})
    first=replace(doc,nodes=(*doc.nodes,second),diagnostics=(*doc.diagnostics,{'code':'AAA'}))
    mapping=first.to_dict();mapping['nodes'].reverse();mapping['diagnostics'].reverse();before=deepcopy(mapping)
    assert render(first)==render(mapping)
    assert mapping==before
    text=visible(parsed(render(first)));assert text.index('interface:alpha')<text.index('interface:provided')


def test_kafka_same_topic_distinct_realms_groups_and_regex_are_never_merged():
    nodes=[]
    for i,(realm,group,pattern) in enumerate([('one','a',None),('one','b',None),('two','a',None),('one','a','orders.*')]):
        nodes.append(ViewNode('interface:kafka:'+str(i),'kafka_interface','Orders',owner_id='orders',
            attributes={'service_id':'orders','direction':'CONSUMER','broker_realm':realm,
                'consumer_group':group,'topics':['orders'] if pattern is None else [],'topic_pattern':pattern,
                'subscription_kind':'TOPICS' if pattern is None else 'PATTERN'}))
    doc=replace(catalogue(),nodes=tuple(nodes),provenance=())
    text=visible(parsed(render(doc)))
    assert all(n.id in text for n in nodes)
    assert all(s in text for s in ('realm=one','realm=two','group=a','group=b','orders.*','PATTERN'))
    assert 'RUNTIME_OBSERVED' not in text


def test_contradictory_evidence_contract_revisions_and_runtime_are_separate():
    doc=catalogue();proof={'id':'proof:against','evidence_kind':'SOURCE_ONLY','freshness':'STALE','polarity':'CONTRADICTING'}
    node=replace(doc.nodes[0],freshness='STALE',evidence_refs=(*doc.nodes[0].evidence_refs,'proof:against'),
        contradicting_refs=('proof:against',),attributes=deepcopy(doc.nodes[0].attributes))
    newer=deepcopy(node.attributes['contract_bindings'][0]);newer.update(status='STALE',revision='v2',revision_fingerprint='d'*64)
    node.attributes['contract_bindings'].append(newer)
    doc=replace(doc,nodes=(node,*doc.nodes[1:]),provenance=(*doc.provenance,proof))
    text=visible(parsed(render(doc)))
    assert all(s in text for s in ('proof:against','Contradicting','STALE','v1','v2','UNKNOWN','NOT_OBSERVED'))
    assert 'RUNTIME_OBSERVED' not in text


@pytest.mark.parametrize('case',['kind','schema','missing_proof','scope','context_list','context_id','contract_list','contract_shape','reason_container','proof_context','diagnostic_context','nan','opaque_object','surrogate'])
def test_malformed_or_foreign_input_is_fixed_error_and_immutable(case):
    from kgmaker.architecture_render import InterfaceMarkdownError
    doc=catalogue().to_dict()
    if case=='kind':doc['kind']='topology'
    elif case=='schema':doc['schema_version']=True
    elif case=='missing_proof':doc['provenance']=[]
    elif case=='scope':doc['nodes'][0]['attributes']['scope']='test'
    elif case=='context_list':doc['nodes'][0]['attributes']['context_ids']={}
    elif case=='context_id':doc['nodes'][0]['attributes']['context_id']='context\nforeign'
    elif case=='contract_list':doc['nodes'][0]['attributes']['contract_bindings']={}
    elif case=='contract_shape':doc['nodes'][0]['attributes']['contract_bindings']=[False]
    elif case=='reason_container':doc['nodes'][0]['attributes']['unresolved_reasons']={}
    elif case=='proof_context':doc['provenance'][0]['context_ids']={}
    elif case=='diagnostic_context':doc['diagnostics'][0]['context_ids']={}
    elif case=='nan':doc['coverage']['value']=float('nan')
    elif case=='opaque_object':doc['coverage']['value']=object()
    elif case=='surrogate':doc['nodes'][0]['label']='\ud800'
    before=repr(doc)
    with pytest.raises(InterfaceMarkdownError) as error:render(doc)
    assert str(error.value) in {'INVALID_INTERFACE_MARKDOWN','UNSAFE_INTERFACE_MARKDOWN','INTERFACE_MARKDOWN_LIMIT'}
    assert repr(doc)==before


@pytest.mark.parametrize('location',['id','label','diagnostic','opaque'])
@pytest.mark.parametrize('secret',['password=PRIVATE_SENTINEL','Bearer PRIVATE_SENTINEL','https://user:PRIVATE_SENTINEL@host.invalid/'])
def test_existing_public_privacy_guard_rejects_secret_without_echo(location,secret):
    from kgmaker.architecture_render import InterfaceMarkdownError
    doc=catalogue().to_dict()
    if location=='id':doc['nodes'][0]['id']=secret
    elif location=='label':doc['nodes'][0]['label']=secret
    elif location=='diagnostic':doc['diagnostics'][0]['message']=secret
    else:doc['nodes'][0]['attributes']['opaque']=secret
    with pytest.raises(InterfaceMarkdownError) as error:render(doc)
    assert 'PRIVATE_SENTINEL' not in str(error.value)


@pytest.mark.parametrize('case',['deep','cycle','shared','scalar','output'])
def test_projection_budgets_fail_before_emission(case,monkeypatch):
    import kgmaker.architecture_render as module
    doc=catalogue().to_dict()
    if case=='cycle':doc['nodes'][0]['attributes']['opaque']=doc
    elif case=='deep':
        value=[]
        for _ in range(45):value=[value]
        doc['nodes'][0]['attributes']['opaque']=value
    elif case=='shared':
        value=['x']*1000;doc['nodes'][0]['attributes']['opaque']=[value]*200
    elif case=='scalar':doc['nodes'][0]['label']='x'*17000
    elif case=='output':monkeypatch.setattr(module,'_MAX_OUTPUT_BYTES',100)
    with pytest.raises(module.InterfaceMarkdownError):render(doc)


def test_pure_renderer_never_uses_provider_io_store_network_or_process(monkeypatch,tmp_path):
    import pathlib,socket,subprocess
    import kgmaker.architecture_render
    doc=catalogue();before=deepcopy(doc.to_dict());sentinel=tmp_path/'last-valid';sentinel.write_bytes(b'untouched')
    with monkeypatch.context() as guard:
        def denied(*a,**kw):pytest.fail('renderer crossed pure boundary')
        guard.setattr(pathlib.Path,'open',denied);guard.setattr(subprocess,'Popen',denied)
        guard.setattr(socket,'socket',denied)
        guard.setattr('kgmaker.scanner.scan_repository',denied);guard.setattr('kgmaker.store.save_graph',denied)
        guard.setattr('kgmaker.workspace.snapshot_workspace',denied)
        assert 'Interface catalog' in render(doc)
        with pytest.raises(ValueError):render({'schema_version':True})
    assert doc.to_dict()==before and sentinel.read_bytes()==b'untouched'


def test_unknown_record_is_visible_without_guessing_protocol_or_direction():
    unknown=ViewNode('future:one','future_interface','Looks like HTTP POST',attributes={'opaque':{'schema':'not displayed'}})
    doc=replace(catalogue(),nodes=(unknown,),provenance=())
    text=visible(parsed(render(doc)))
    assert 'future:one' in text and 'UNKNOWN' in text and 'not displayed' not in text


from test_t013_attach_interface_contracts import fixture as contract_files


def test_actual_explicit_contract_and_generated_file_capture_renders_without_recapture(contract_files,monkeypatch):
    from test_t013_attach_interface_contracts import capture,attach
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from kgmaker.interfaces import project_http_providers
    workspace=load_workspace(contract_files[0]);_,coverage,_,graph,_=snapshot_workspace(contract_files[0],persist_cache=False)
    doc=attach(workspace,graph,project_http_providers(workspace,graph,source_coverage=coverage),capture(workspace,graph))
    original=deepcopy(doc.to_dict())
    def denied(*a,**kw):pytest.fail('renderer recaptured source')
    monkeypatch.setattr('kgmaker.workspace.snapshot_workspace',denied)
    monkeypatch.setattr('kgmaker.interfaces.capture_interface_contracts',denied)
    text=visible(parsed(render(doc)))
    assert all(n.id in text for n in doc.nodes if n.kind!='service')
    assert 'PROVIDER_DECLARATION' in text and 'CLIENT_EXPECTATION' in text and 'BOUND_DECLARATION' in text
    assert '#/components/schemas/Order' in text
    assert doc.to_dict()==original


def test_explain_remains_json_only_and_preserves_last_artifact(tmp_path):
    from test_t019_add_architecture_json_cli import run_cli,write
    from test_t016_aggregate_service_topology import labelled_handoff
    from kgmaker.service_topology import aggregate_service_topology
    captured=labelled_handoff();cap=write(tmp_path/'capture.json',captured)
    view=write(tmp_path/'view.json',aggregate_service_topology(captured).to_dict())
    sentinel=tmp_path/'last-valid';sentinel.write_bytes(b'last valid')
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    result=run_cli('explain','--capture-snapshot',cap,'--format','markdown',
                   '--snapshot',view,'--element','service:checkout')
    assert result.returncode==2 and result.stdout=='' and 'Traceback' not in result.stderr
    assert {p.name:p.read_bytes() for p in tmp_path.iterdir()}==before


def test_snapshot_fingerprint_conflict_does_not_emit_partial_markdown(tmp_path):
    from test_t019_add_architecture_json_cli import run_cli,write
    from test_cross_service_contract_mapping import trusted_protocol_specimen,refresh_handoff
    from kgmaker.remote_mapping import _workspace
    workspace,graph,docs,captured=trusted_protocol_specimen()
    for doc in docs:
        name=next(n for n in ['http-providers','http-consumers','kafka-interfaces'] if doc['rules_version'].startswith(n))
        doc['view_id']='view:'+name+':'+workspace['workspace_id']+':production'
    refresh_handoff(workspace,graph,docs,captured)
    path=write(tmp_path/'bundle.json',{'schema_version':1,'rules_version':'architecture-interface-inputs-1',
        'workspace':_workspace(workspace),'graph':graph.to_dict(),'captured':captured})
    result=run_cli('interfaces','--catalog','http-consumers','--interface-capture',path,
        '--format','markdown','--expected-fingerprint','0'*64)
    assert result.returncode==3 and result.stdout==''
    assert json.loads(result.stderr)['code']=='EXPECTED_FINGERPRINT_MISMATCH'



def test_valid_node_and_proof_namespace_overlap_has_distinct_internal_anchors():
    doc=catalogue();node=replace(doc.nodes[0],id='proof:declaration')
    doc=replace(doc,nodes=(node,*doc.nodes[1:]));ViewDocument.from_dict(doc.to_dict())
    markdown=render(doc);anchors=re.findall(r'<a id="([^"]+)">',markdown)
    assert len(anchors)==len(set(anchors))
    targets=[c.attrGet('href')[1:] for t in parsed(markdown) for c in t.children or [] if c.type=='link_open']
    assert all(target in anchors for target in targets)



def test_bare_url_domain_and_email_are_visible_text_but_not_autolink_source():
    label='https://evil.invalid/path www.evil.invalid user@evil.invalid'
    doc=catalogue();doc=replace(doc,nodes=(replace(doc.nodes[0],label=label),*doc.nodes[1:]))
    markdown=render(doc);tokens=parsed(markdown)
    assert label in visible(tokens)
    assert 'https://evil.invalid' not in markdown and 'www.evil.invalid' not in markdown and 'user@evil.invalid' not in markdown
    assert all(c.attrGet('href').startswith('#evidence-') for t in tokens for c in t.children or [] if c.type=='link_open')



def test_snapshot_content_fingerprint_matches_independently_hashed_supplied_json():
    import hashlib
    document=replace(catalogue(),generated_at='2026-01-01T00:00:00Z')
    supplied=document.to_dict(include_generation_metadata=False)
    canonical_bytes=json.dumps(supplied,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    expected=hashlib.sha256(canonical_bytes).hexdigest()
    assert expected==document.content_fingerprint
    for value in (document,supplied):
        text=visible(parsed(render(value)))
        assert 'Content fingerprint: '+expected in text
    changed=deepcopy(supplied);changed['nodes'][0]['label']='Changed declaration label'
    changed_expected=hashlib.sha256(json.dumps(changed,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert changed_expected!=expected
    assert 'Content fingerprint: '+changed_expected in visible(parsed(render(changed)))


def test_first_interface_markdown_render_is_io_free_in_fresh_python_process(tmp_path):
    """Ordinary API import before strong Python I/O denial; no helper preloading."""
    import subprocess,sys
    from pathlib import Path
    payload=catalogue().to_dict()
    payload['nodes'][0]['label']='cold <script> [orders] Žluťoučký'
    expected=render(payload)
    before=json.dumps(payload,sort_keys=True,ensure_ascii=False)
    input_path=tmp_path/'cold-payload.json';input_path.write_text(before,encoding='utf-8')
    expected_path=tmp_path/'cold-expected.txt';expected_path.write_text(expected,encoding='utf-8')
    script='import json, os, socket, subprocess, sys\nfrom pathlib import Path\nfrom kgmaker.architecture_render import render_interface_markdown\npayload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))\nexpected = Path(sys.argv[2]).read_text(encoding="utf-8")\nbefore = json.dumps(payload, sort_keys=True, ensure_ascii=False)\ndef denied(*args, **kwargs):\n    raise RuntimeError("PURE_RENDER_IO_DENIED")\ndef audit(event, args):\n    if event == "open" or event.startswith(("os.", "socket.", "subprocess.", "shutil.", "ctypes.")):\n        raise RuntimeError("PURE_RENDER_IO_DENIED:" + event)\n# Audit detects importlib open; these bindings also cover unaudited stat/readlink APIs.\nfor name in ("open", "stat", "lstat", "scandir", "listdir", "readlink", "read", "write", "mkdir", "makedirs", "rmdir", "remove", "unlink", "rename", "replace", "chmod", "chown", "access", "getcwd", "system", "fork", "forkpty", "posix_spawn", "posix_spawnp"):\n    if hasattr(os, name): setattr(os, name, denied)\nfor name in dir(os):\n    if name.startswith(("exec", "spawn")): setattr(os, name, denied)\nfor name in ("open", "read_text", "read_bytes", "write_text", "write_bytes", "stat", "lstat", "exists", "is_file", "is_dir", "is_symlink", "iterdir", "glob", "rglob", "readlink", "resolve", "absolute", "cwd", "touch", "mkdir", "rmdir", "unlink", "rename", "replace", "chmod", "lchmod"):\n    if hasattr(Path, name): setattr(Path, name, denied)\nfor name in ("socket", "create_connection", "socketpair", "getaddrinfo", "getnameinfo"):\n    if hasattr(socket, name): setattr(socket, name, denied)\nfor name in ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):\n    if hasattr(subprocess, name): setattr(subprocess, name, denied)\nclass DeniedStream:\n    write = read = readline = readinto = fileno = denied\n    def flush(self): pass\nsys.addaudithook(audit)\nstdout, stderr, stdin = sys.stdout, sys.stderr, sys.stdin\nsys.stdout = sys.stderr = sys.stdin = DeniedStream()\ntry:\n    output = render_interface_markdown(payload)  # FIRST public renderer invocation in this fresh process\nfinally:\n    sys.stdout, sys.stderr, sys.stdin = stdout, stderr, stdin\nassert output == expected\nassert json.dumps(payload, sort_keys=True, ensure_ascii=False) == before\nprint(json.dumps({"output": output, "input_unchanged": True}))\n'
    source=Path(__file__).resolve().parents[1]/'src'
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(source)+os.pathsep+os.environ.get('PYTHONPATH','')}
    result=subprocess.run([sys.executable,'-c',script,str(input_path),str(expected_path)],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    captured=json.loads(result.stdout);actual=captured['output']
    assert actual==expected and captured['input_unchanged']
    assert input_path.read_text(encoding='utf-8')==before
    assert expected_path.read_text(encoding='utf-8')==expected
    tokens=parsed(actual)
    assert '<script>' not in actual
    assert not [t for t in tokens if t.type in {'html_inline','html_block'}]
    decoded=visible(tokens)
    assert all(n['id'] in decoded for n in payload['nodes'])

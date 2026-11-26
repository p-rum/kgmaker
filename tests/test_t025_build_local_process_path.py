"""Public topology and snapshot-proof expectations; never a second CFG builder."""
from copy import deepcopy
from dataclasses import replace
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch
import pytest

from kgmaker.control_flow import from_body
from kgmaker.flow import process
from kgmaker.model import Node, Edge
from kgmaker.process_model import ProcessDefinition, ProcessView
from kgmaker.process_triggers import discover_process_triggers
from kgmaker.process_paths import build_local_process, ProcessPathError
from test_t024_discover_process_triggers import inputs


def setup(tmp_path):
    workspace, graph, coverage, entries = inputs(tmp_path)
    # Explicit schema model, not a claim that this fixture executed a compiler.
    for context in graph.contexts:
        if context.get('analyzer_version'):
            context.update(mode='BUILD_IMPORT', origin_trust='LOCAL_COMPILER_INPUTS',
                worker={'protocol_version':1,'worker':'model-only','compiler_version':'model-only'})
    graph.nodes=[replace(node,role='executable_code') if node.kind in {'method','call_site'} else node for node in graph.nodes]
    method = entries[('production', 'http')][0]
    symbol = next(s for s in graph.symbols if s['id'] == method)
    return workspace, graph, coverage, method, symbol


def ir(symbol, kind, **kwargs):
    return {'kind': kind, 'label': kwargs.pop('label', kind), 'path': symbol['path'],
        'sha256': symbol['sha256'], 'range': {'start': 0, 'end': 1, 'start_line': 1}, **kwargs}


def add_cfg(graph, method, symbol, body):
    cfg = from_body({'method': method, 'context_id': symbol['context_id'], 'body': body})
    proof = 'cfg-proof:' + method
    graph.evidence.append({'id': proof, 'kind': 'SYNTAX_CANDIDATE', 'source': method,
        'target': method, 'relation': 'control_flow', 'context_ids': [symbol['context_id']],
        'representation': 'SOURCE', 'source_file': symbol['path'], 'sha256': symbol['sha256'],
        'source_range': body['range'],
        'freshness': 'CURRENT'})
    cfg['evidence_ids'] = [proof]; graph.cfgs.append(cfg)
    return cfg


def helper(graph, parent, name):
    value = {**deepcopy(parent), 'id': parent['id'] + ':' + name, 'name': name, 'annotations': []}
    graph.symbols.append(value)
    graph.nodes.append(Node(value['id'], 'method', name, value['path'], 1,
        scope='production', role='executable_code', metadata=deepcopy(value)))
    return value


def call(graph, caller, target, name, **extra):
    site = {'id': caller['id'] + ':site:' + name, 'caller': caller['id'], 'declared_target': target['id'],
        'path': caller['path'], 'sha256': caller['sha256'], 'range': {'start': 0, 'end': 1, 'start_line': 1},
        'context_id': caller['context_id'], 'invocation_kind': 'STATIC', 'dispatch_complete': True,
        'dispatch_candidates': [target['id']], 'evidence_kind': 'SYMBOL_RESOLVED',
        'evidence_ids': ['invoke-proof:' + name, 'resolve-proof:' + name], 'resolution_reason': 'EXPLICIT_FIXTURE', **extra}
    graph.call_sites.append(site)
    graph.nodes.append(Node(site['id'], 'call_site', site['invocation_kind'], caller['path'], 1,
        scope='production', role='executable_code', metadata=deepcopy(site)))
    for ref, source, dest, relation in [(site['evidence_ids'][0], caller['id'], site['id'], 'declares_call'),
            (site['evidence_ids'][1], site['id'], target['id'], 'resolves_to')]:
        graph.evidence.append({'id': ref, 'kind': 'SYMBOL_RESOLVED', 'source': source,
            'target': dest, 'relation': relation, 'context_ids': [caller['context_id']],
            'source_file': caller['path'], 'source_range': site['range'], 'sha256': caller['sha256']})
    for ref, source, dest, relation in [(site['evidence_ids'][0], caller['id'], site['id'], 'declares_call'),
            (site['evidence_ids'][1], site['id'], target['id'], 'resolves_to')]:
        graph.edges.append(Edge(source,dest,relation,evidence_kind='SYMBOL_RESOLVED',
            context_ids=(caller['context_id'],),evidence_ids=(ref,),source_file=caller['path'],source_line=1))
    return ir(caller, 'call', call_site=site['id'], label=name, arguments=[])


def inventory(workspace, graph, coverage, method):
    view = discover_process_triggers(workspace, graph, source_coverage=coverage)
    trigger = next(n.id for n in view.nodes if n.attributes['entry_symbol_id'] == method)
    return view, trigger


def paths(edges, start, end):
    out = defaultdict(list)
    for edge in edges: out[edge.source].append(edge.target)
    seen=set(); pending=[start]
    while pending:
        node=pending.pop()
        if node == end:return True
        if node in seen:continue
        seen.add(node);pending.extend(out[node])
    return False


def test_ac01_diamond_never_joins_opposite_branches(tmp_path):
    w,g,c,m,s=setup(tmp_path)
    b=helper(g,s,'B');d=helper(g,s,'C')
    add_cfg(g,b['id'],b,ir(b,'statement',label='B-body'))
    add_cfg(g,d['id'],d,ir(d,'statement',label='C-body'))
    yes=call(g,s,b,'B');no=call(g,s,d,'C')
    add_cfg(g,m,s,ir(s,'if',condition=ir(s,'statement',label='flag'),then=yes,**{'else':no}))
    inv,t=inventory(w,g,c,m);before=deepcopy((g.to_dict(),inv.to_dict()))
    with patch('subprocess.Popen',side_effect=AssertionError('offline process projection')):
        result=build_local_process(g,inv,t,process_id='process:diamond')
    assert isinstance(result,ProcessView)
    bs=next(n.id for n in result.steps if n.label=='B-body');cs=next(n.id for n in result.steps if n.label=='C-body')
    assert not paths(result.transitions,bs,cs) and not paths(result.transitions,cs,bs)
    assert {e.attributes['condition'] for e in result.transitions if e.relation in {'true','false'}}=={'condition evaluates TRUE','condition evaluates FALSE'}
    assert all(n.original_ids for n in result.steps) and all(e.original_ids for e in result.transitions)
    assert all(n.resolution_status!='RESOLVED' for n in result.steps if 'SYNTAX_CANDIDATE' in n.evidence_kinds)
    assert (g.to_dict(),inv.to_dict())==before


@pytest.mark.parametrize('reason', ['recursive', 'dispatch', 'depth', 'async'])
def test_ac02_call_boundaries_keep_original_site(tmp_path,reason):
    w,g,c,m,s=setup(tmp_path);target=s if reason=='recursive' else helper(g,s,'helper')
    if reason!='recursive':add_cfg(g,target['id'],target,ir(target,'statement'))
    extra={'invocation_kind':'VIRTUAL','dispatch_complete':False} if reason=='dispatch' else {}
    if reason=='async':
        target['suspend']=True
        g.nodes=[replace(n,metadata=deepcopy(target)) if n.id==target['id'] else n for n in g.nodes]
    expr=call(g,s,target,'invoke',**extra);add_cfg(g,m,s,expr)
    inv,t=inventory(w,g,c,m);result=build_local_process(g,inv,t,process_id='process:boundary',max_depth=0 if reason=='depth' else 3)
    boundary=[n for n in result.steps if n.attributes.get('boundary_reason')]
    assert any(g.call_sites[-1]['id'] in n.original_ids for n in boundary)
    assert result.technical_status=='PARTIAL'


def test_ac03_root_cfg_budget_is_not_bypassed(tmp_path):
    w,g,c,m,s=setup(tmp_path)
    add_cfg(g,m,s,ir(s,'block',statements=[ir(s,'statement',label=str(i)) for i in range(12)]))
    report=process(g,m,max_nodes=2)
    assert len(report['cfg']['blocks'])<=2 and report['truncated']
    assert report['status']=='PARTIAL' and report['boundaries']
    inv,t=inventory(w,g,c,m)
    for budget in (1,2,3):
        result=build_local_process(g,inv,t,process_id='process:budget',max_nodes=budget)
        assert len(result.steps)<=budget and result.technical_status=='PARTIAL'
        assert any(n.attributes.get('boundary_reason')=='node limit' for n in result.steps)


def test_missing_cfg_retains_trigger_and_opaque_entry(tmp_path):
    w,g,c,m,s=setup(tmp_path);inv,t=inventory(w,g,c,m)
    result=build_local_process(g,inv,t,process_id='process:no-body')
    assert t in result.definition.trigger_ids
    assert any(n.kind=='unresolved_boundary' for n in result.steps)
    assert result.technical_status=='PARTIAL' and not result.outcome_ids


@pytest.mark.parametrize('mutation',['trigger_context','trigger_scope','trigger_symbol','trigger_hash','proof_tuple','source_symbol','cfg_context','cfg_proof','file_scope','endpoint_context'])
def test_ac04_invalid_or_foreign_proof_never_mutates_input_or_last_valid(tmp_path,mutation):
    w,g,c,m,s=setup(tmp_path);add_cfg(g,m,s,ir(s,'statement'))
    inv,t=inventory(w,g,c,m);doc=inv.to_dict()
    n=next(x for x in doc['nodes'] if x['id']==t)
    if mutation=='trigger_context':n['attributes']['context_ids']=['foreign']
    elif mutation=='trigger_scope':n['attributes']['scope']='test'
    elif mutation=='trigger_symbol':n['attributes']['entry_symbol_id']=next(x['id'] for x in g.symbols if x['id']!=m)
    elif mutation=='trigger_hash':next(x for x in doc['provenance'] if x['id'] in n['evidence_refs'])['content_hash']='0'*64
    elif mutation=='proof_tuple':next(x for x in g.evidence if x['relation']=='exposes_endpoint')['target']='foreign'
    elif mutation=='source_symbol':next(x for x in g.symbols if x['id']==m)['name']='forged'
    elif mutation=='cfg_context':g.cfgs[-1]['context_id']='foreign'
    elif mutation=='file_scope':g.nodes=[replace(n,scope='test') if n.kind=='file' and n.path==s['path'] else n for n in g.nodes]
    elif mutation=='endpoint_context':
        endpoint=n['attributes']['entrypoint_id'];g.nodes=[replace(x,metadata={**(x.metadata or {}),'context_id':'foreign'}) if x.id==endpoint else x for x in g.nodes]
    elif mutation=='cfg_proof':next(x for x in g.evidence if x['relation']=='control_flow')['sha256']='0'*64
    before=deepcopy((g.to_dict(),doc));saved=tmp_path/'last.json';saved.write_bytes(b'valid')
    try:
        result=build_local_process(g,doc,t,process_id='process:invalid')
    except ProcessPathError:pass
    else:
        assert result.technical_status=='PARTIAL'
        assert not any(n.kind=='basic_block' for n in result.steps)
    assert (g.to_dict(),doc)==before and saved.read_bytes()==b'valid'


def test_nested_call_returns_exceptions_and_input_order_are_preserved(tmp_path):
    w,g,c,m,s=setup(tmp_path);outer=helper(g,s,'outer');inner=helper(g,s,'inner')
    add_cfg(g,inner['id'],inner,ir(inner,'statement',label='inner-body'))
    add_cfg(g,outer['id'],outer,ir(outer,'block',statements=[call(g,outer,inner,'nested'),ir(outer,'statement',label='after-inner')]))
    add_cfg(g,m,s,call(g,s,outer,'outer'))
    inv,t=inventory(w,g,c,m);a=build_local_process(g,inv,t,process_id='process:nested')
    x=next(n.id for n in a.steps if n.label=='inner-body');y=next(n.id for n in a.steps if n.label=='after-inner')
    assert paths(a.transitions,x,y) and not paths(a.transitions,y,x)
    assert any(e.relation=='returns_to' and e.original_ids for e in a.transitions)
    assert len(a.to_dict()['exit_ids'])==2
    for values in (g.nodes,g.edges,g.contexts,g.symbols,g.call_sites,g.cfgs,g.evidence):values.reverse()
    assert a.to_json()==build_local_process(g,inv,t,process_id='process:nested').to_json()


@pytest.mark.parametrize('mutation',['site_target','site_hash','site_caller','site_scope','site_proof','cfg_block_hash','cfg_block_kind','site_node_kind','missing_resolves_edge'])
def test_callee_or_cfg_proof_tampering_retains_explicit_boundary(tmp_path,mutation):
    w,g,c,m,s=setup(tmp_path);child=helper(g,s,'child');other=helper(g,s,'other')
    add_cfg(g,child['id'],child,ir(child,'statement',label='child-body'))
    add_cfg(g,other['id'],other,ir(other,'statement',label='other-body'))
    add_cfg(g,m,s,call(g,s,child,'child'))
    inv,t=inventory(w,g,c,m)
    if mutation=='site_target':g.call_sites[-1]['declared_target']=other['id']
    elif mutation=='site_hash':g.call_sites[-1]['sha256']='0'*64
    elif mutation=='site_caller':g.call_sites[-1]['caller']=child['id']
    elif mutation=='site_scope':g.nodes=[replace(n,scope='test') if n.id==g.call_sites[-1]['id'] else n for n in g.nodes]
    elif mutation=='site_proof':next(p for p in g.evidence if p['relation']=='resolves_to')['target']=other['id']
    elif mutation=='site_node_kind':g.nodes=[replace(n,kind='method') if n.id==g.call_sites[-1]['id'] else n for n in g.nodes]
    elif mutation=='missing_resolves_edge':g.edges=[e for e in g.edges if e.kind!='resolves_to']
    elif mutation=='cfg_block_hash':next(b for b in g.cfgs[-1]['blocks'] if b.get('source_file'))['sha256']='0'*64
    else:next(b for b in g.cfgs[-1]['blocks'] if b.get('source_file'))['kind']=[]
    before=deepcopy(g.to_dict())
    result=build_local_process(g,inv,t,process_id='process:tampered')
    assert not any(n.label in ('child-body','other-body') for n in result.steps)
    assert any(n.attributes.get('boundary_reason') for n in result.steps)
    assert g.to_dict()==before


@pytest.mark.parametrize('backend',['javac','k1'])
def test_actual_public_compiler_diamond_nested_recursion_and_root_budget(tmp_path,backend):
    from kgmaker.inspection import inspect_jvm
    from kgmaker.workspace import load_workspace,snapshot_workspace
    from kgmaker.analysis_model import write_json
    from test_t024_discover_process_triggers import actual_prerequisites
    # Explicit matching pinned API preparation was performed before this test;
    # neither provider projection nor this preflight fetches or builds anything.
    jars=actual_prerequisites('k1')
    root=tmp_path/'backend';folder=root/('src/main/java/demo' if backend=='javac' else 'src/main/kotlin/demo');folder.mkdir(parents=True)
    if backend=='javac':
        (folder/'Controller.java').write_text('''package demo;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
@RestController public class Controller {
 @GetMapping("/path") public String entry(boolean flag) {
   if(flag) return left(); else return right();
 }
 private static String left() { return nested(); }
 private static String right() { return "right"; }
 private static String nested() { return "nested"; }
 @GetMapping("/recursive") public String recursive() { return recursive(); }
 @GetMapping("/finally") public String withFinally(boolean flag) {
  try { if(flag) return left(); throw new IllegalStateException(); }
  finally { cleanup(); }
 }
 private static void cleanup() {}
 @GetMapping("/twice") public String twice() { left(); return left(); }
 @GetMapping("/virtual") public String virtualEntry() { return virtualChild(); }
 public String virtualChild() { return "virtual"; }
}''')
    else:
        (folder/'Controller.kt').write_text('''package demo
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.GetMapping
@RestController class Controller {
 @GetMapping("/path") fun entry(flag: Boolean): String {
   if(flag) return left()
   return right()
 }
 @GetMapping("/recursive") fun recursive(): String { return recursive() }
 @GetMapping("/finally") fun withFinally(flag: Boolean): String {
  try { if(flag) return left(); throw IllegalStateException() }
  finally { cleanup() }
 }
 @GetMapping("/twice") fun twice(): String { left(); return left() }
 @GetMapping("/virtual") fun virtualEntry(): String { return virtualChild() }
 fun virtualChild(): String { return "virtual" }
}
private fun left(): String { return nested() }
private fun right(): String { return "right" }
private fun nested(): String { return "nested" }
private fun cleanup() {}
''')
    manifest=tmp_path/'workspace.json'
    write_json(manifest,{'schema_version':1,'workspace_id':'real','repositories':[{'id':'backend','role':'backend','path':'backend'}],
        'services':[{'id':'svc','backend_repo':'backend','frontend_repos':[],'test_repos':[],'contract':{'repo_id':'backend','path':'api.json'}}],
        'service_ownership':{'schema_version':1,'services':[{'id':'svc','roots':[{'repo_id':'backend','path':'src'}],
            'modules':[{'repo_id':'backend','id':'app'}],'external_systems':[]}]}})
    inspected=inspect_jvm(root,home=Path(__file__).resolve().parents[1]/'workers',repo_id='local',module='app',source_set='main',scope='production',
        kotlin_backend='k1',classpath=jars,build_context={'spring_component_packages':['demo']})
    assert not any('.err.' in d.get('code','') or d.get('reason','').startswith('ERROR:') for d in inspected['diagnostics'])
    workspace=load_workspace(manifest);_,coverage,_,graph,_=snapshot_workspace(manifest)
    inv=discover_process_triggers(workspace,graph,source_coverage=coverage)
    entry=next(n for n in inv.nodes if next(s for s in graph.symbols if s['id']==n.attributes['entry_symbol_id'])['name']=='entry')
    assert entry.attributes['body_status']=='AVAILABLE'
    before=deepcopy((graph.to_dict(),inv.to_dict()));saved={p.relative_to(root).as_posix():p.read_bytes() for p in (root/'.kgmaker').rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('no implicit execution')),patch('socket.socket',side_effect=AssertionError('no network')):
        result=build_local_process(graph,inv,entry.id,process_id='process:real')
        bounded=build_local_process(graph,inv,entry.id,process_id='process:bounded',max_nodes=2)
    assert any(e.relation=='true' for e in result.transitions) and any(e.relation=='false' for e in result.transitions)
    method_names={s['id']:s['name'] for s in graph.symbols}
    assert {'entry','left','right','nested'} <= {method_names.get(n.attributes.get('method')) for n in result.steps}
    left_ids={n.id for n in result.steps if method_names.get(n.attributes.get('method'))=='left'}
    right_ids={n.id for n in result.steps if method_names.get(n.attributes.get('method'))=='right'}
    assert not any(paths(result.transitions,a,b) or paths(result.transitions,b,a) for a in left_ids for b in right_ids)
    assert any(e.relation=='returns_to' for e in result.transitions)
    assert len(bounded.steps)<=2 and bounded.technical_view.coverage['truncated']
    assert any(n.attributes.get('boundary_reason')=='node limit' for n in bounded.steps)
    assert result.technical_status=='PARTIAL'
    assert result.definition.to_dict()['context_selection'] == inv.context_selection
    assert (graph.to_dict(),inv.to_dict())==before
    assert saved=={p.relative_to(root).as_posix():p.read_bytes() for p in (root/'.kgmaker').rglob('*') if p.is_file()}
    recursive=next(n for n in inv.nodes if next(s for s in graph.symbols if s['id']==n.attributes['entry_symbol_id'])['name']=='recursive')
    recursive_view=build_local_process(graph,inv,recursive.id,process_id='process:recursive')
    # A virtual self-call can remain dispatch-uncertain before recursion is
    # considered; either retains the original site and never expands forever.
    assert any(n.attributes.get('boundary_reason') in ('recursive call','dispatch candidates')
        and n.attributes.get('call_site_ids') for n in recursive_view.steps)

    twice=next(n for n in inv.nodes if method_names[n.attributes['entry_symbol_id']]=='twice')
    twice_view=ProcessView.from_dict(build_local_process(graph,inv,twice.id,process_id='process:twice').to_dict())
    proof_index={p['id']:p for p in twice_view.technical_view.provenance}
    sites=[site for site in graph.call_sites if site['caller']==twice.attributes['entry_symbol_id']]
    assert len(sites)==2 and len({site['declared_target'] for site in sites})==1
    for site in sites:
        transitions=[e for e in twice_view.transitions if e.attributes.get('call_site')==site['id']]
        assert {'call','returns_to','exception'}<={e.relation for e in transitions}
        originals={p['id'] for p in graph.evidence if p['id'] in site['evidence_ids']
            and p['relation'] in ('declares_call','resolves_to') and p['kind']=='SYMBOL_RESOLVED'}
        assert len(originals)==2
        for edge in transitions:
            assert site['id'] in edge.original_ids
            assert originals<={proof_index[ref].get('original_id') for ref in edge.evidence_refs}
    final=next(n for n in inv.nodes if method_names[n.attributes['entry_symbol_id']]=='withFinally')
    cfg=next(cfg for cfg in graph.cfgs if cfg['method']==final.attributes['entry_symbol_id'])
    cleanup=next(site for site in graph.call_sites if site['caller']==final.attributes['entry_symbol_id']
        and method_names.get(site.get('declared_target'))=='cleanup')
    final_before=deepcopy(graph.to_dict())
    final_result=build_local_process(graph,inv,final.id,process_id='process:finally-real')
    assert_finally_clone_topology(final_result,cfg,cleanup['id'])
    assert len({edge.id for edge in final_result.transitions})==len(final_result.transitions)
    bounded_final=build_local_process(graph,inv,final.id,process_id='process:finally-bounded',max_nodes=4)
    assert len(bounded_final.steps)<=4 and bounded_final.technical_view.coverage['truncated']
    assert graph.to_dict()==final_before
    # Actual captured sites have no independent receiver/complete-dispatch
    # metadata mirror. A changed site-table flag cannot turn this virtual call
    # into a proved unique body expansion.
    virtual=next(n for n in inv.nodes if method_names[n.attributes['entry_symbol_id']]=='virtualEntry')
    for mutation in ('complete','receiver','invocation'):
        altered=deepcopy(graph)
        site=next(s for s in altered.call_sites if s['caller']==virtual.attributes['entry_symbol_id'])
        if mutation=='complete':site['dispatch_complete']=True;site['dispatch_candidates']=[site['declared_target']]
        elif mutation=='receiver':site['receiver_type']='foreign.Owner';site['dispatch_complete']=True
        else:site['invocation_kind']='STATIC';site['dispatch_complete']=True
        old=deepcopy(altered.to_dict())
        guarded=build_local_process(altered,inv,virtual.id,process_id='process:virtual')
        assert not any(method_names.get(n.attributes.get('method'))=='virtualChild' for n in guarded.steps)
        assert any(n.attributes.get('boundary_reason') for n in guarded.steps)
        assert altered.to_dict()==old
    # A real declared target replaced with another existing method still has
    # its original resolves_to edge/proof, and cannot borrow the other's body.
    altered=deepcopy(graph);site=next(s for s in altered.call_sites if s['caller']==entry.attributes['entry_symbol_id'])
    site['declared_target']=next(s['id'] for s in graph.symbols if s.get('name')=='virtualChild')
    guarded=build_local_process(altered,inv,entry.id,process_id='process:wrong-target')
    assert not any(method_names.get(n.attributes.get('method'))=='virtualChild' for n in guarded.steps)
    assert any(site['id'] in n.original_ids and n.attributes.get('boundary_reason') for n in guarded.steps)


def test_actual_local_process_carries_only_its_selected_context_to_label_packet(tmp_path):
    from kgmaker.analysis_model import file_hash, write_json
    from kgmaker.inspection import inspect_jvm
    from kgmaker.process_semantics import ProcessLabelPacketError, prepare_process_label_packet
    from kgmaker.workspace import load_workspace, snapshot_workspace
    from test_t024_discover_process_triggers import actual_prerequisites

    jars = actual_prerequisites('k1')
    worker_home = Path(__file__).resolve().parents[1] / 'workers'
    services = ('orders', 'payments')
    for name in services:
        root = tmp_path / name
        source = root / 'src/main/java/demo/Controller.java'
        source.parent.mkdir(parents=True)
        source.write_text('''package demo;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
@RestController public class Controller {
 @GetMapping("/entry") public String entry(boolean flag) {
   if (flag) return "left"; else return "right";
 }
}''')
        inspected = inspect_jvm(root, home=worker_home, module='app', classpath=jars,
            build_context={'spring_component_packages': ['demo']})
        assert not any(row.get('reason', '').startswith('ERROR:') for row in inspected['diagnostics'])
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, {'schema_version': 1, 'workspace_id': 'separate-process-contexts',
        'repositories': [{'id': name, 'role': 'backend', 'path': name} for name in services],
        'services': [{'id': name, 'backend_repo': name, 'frontend_repos': [], 'test_repos': [],
                      'contract': {'repo_id': name, 'path': 'api.json'}} for name in services],
        'service_ownership': {'schema_version': 1, 'services': [
            {'id': name, 'roots': [{'repo_id': name, 'path': 'src'}],
             'modules': [{'repo_id': name, 'id': 'app'}], 'external_systems': []} for name in services]}})

    def files():
        return {path.relative_to(tmp_path): file_hash(path) for path in tmp_path.rglob('*') if path.is_file()}

    before_files = files()
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest, persist_cache=False)
    with patch('subprocess.Popen', side_effect=AssertionError('offline projection started a process')), \
            patch('socket.socket', side_effect=AssertionError('offline projection opened a connection')):
        inventory = discover_process_triggers(workspace, graph, source_coverage=coverage)
        before = deepcopy((workspace, graph.to_dict(), inventory.to_dict()))
        selected = inventory.context_selection['services']
        orders, = [row for row in selected['orders']['contexts'] if row['status'] == 'CURRENT']
        payment, = [row for row in selected['payments']['contexts'] if row['status'] == 'CURRENT']
        assert orders['context_id'] != payment['context_id']
        trigger, = [node for node in inventory.nodes if node.owner_id == 'service:orders']
        process_view = build_local_process(graph, inventory, trigger.id, process_id='process:orders')
        packet = prepare_process_label_packet(process_view)['packet']
        assert packet['identity']['context_ids'] == [orders['context_id']]
        assert set(packet['identity']['context_selection']['services']) == {'orders'}
        assert packet['identity']['baseline_fingerprint'] == process_view.technical_view.baseline_fingerprint
        assert packet['identity']['process_content_hash'] == process_view.content_fingerprint
        document = process_view.to_dict()
        expected_selection = {'services': {'orders': selected['orders']}}
        assert document['definition']['context_selection'] == expected_selection
        assert document['technical_view']['context_selection'] == expected_selection
        assert {row['scope'] for row in document['technical_view']['provenance']} == {'production'}
        assert {cid for row in document['technical_view']['provenance'] for cid in row['context_ids']} == {orders['context_id']}
        assert process_view.technical_status == 'PARTIAL'
        assert {'true', 'false'} <= {edge.relation for edge in process_view.transitions}

        # ProcessView still decodes the previous representation. The strict
        # packet validator must reject its genuinely foreign context, not repair it.
        foreign = deepcopy(document)
        old_selection = deepcopy(inventory.context_selection)
        foreign['definition']['context_selection'] = old_selection
        foreign['technical_view']['context_selection'] = old_selection
        foreign['definition_fingerprint'] = ProcessDefinition.from_dict(foreign['definition']).content_fingerprint
        with pytest.raises(ProcessLabelPacketError, match='SELECTION_CONTEXT_MISMATCH'):
            prepare_process_label_packet(ProcessView.from_dict(foreign))
    assert (workspace, graph.to_dict(), inventory.to_dict()) == before
    assert files() == before_files


def test_local_process_preserves_selection_envelope_for_strict_label_packet(tmp_path):
    from kgmaker.architecture_model import ViewDocument
    from kgmaker.process_semantics import ProcessLabelPacketError, prepare_process_label_packet

    workspace, graph, coverage, method, _ = setup(tmp_path)
    trigger_inventory, trigger_id = inventory(workspace, graph, coverage, method)
    captured = trigger_inventory.to_dict()
    captured['context_selection']['extra_capture_metadata'] = {'version': 1}
    current = ViewDocument.from_dict(captured)
    last_valid = tmp_path / 'last-valid.json'
    last_valid.write_text('previous generation')

    def files():
        return {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}

    before_files = files()
    before = deepcopy((graph.to_dict(), current.to_dict()))
    with patch('subprocess.Popen', side_effect=AssertionError('offline projection started a process')), \
            patch('socket.socket', side_effect=AssertionError('offline projection opened a connection')):
        valid = build_local_process(graph, trigger_inventory, trigger_id, process_id='process:orders')
        assert prepare_process_label_packet(valid)['packet']['identity']['process_id'] == 'process:orders'
        result = build_local_process(graph, current, trigger_id, process_id='process:orders')
        with pytest.raises(ProcessLabelPacketError, match='UNSUPPORTED_SELECTION_SHAPE'):
            prepare_process_label_packet(result)
        assert result.definition.to_dict()['context_selection'] == current.context_selection
        assert result.technical_view.context_selection == current.context_selection
    assert (graph.to_dict(), current.to_dict()) == before
    assert files() == before_files


@pytest.mark.parametrize('version',[1,2])
def test_legacy_graph_remains_readable_without_promoting_missing_compiler_proof(tmp_path,version):
    from kgmaker.model import KnowledgeGraph
    w,g,c,m,s=setup(tmp_path);inv,t=inventory(w,g,c,m)
    old={'schema_version':version,'root':'.','generated_at':'old','nodes':[],'edges':[],'files':{}}
    loaded=KnowledgeGraph.from_dict(old)
    assert loaded.schema_version==version
    with pytest.raises(ProcessPathError):build_local_process(loaded,inv,t,process_id='process:legacy')
    assert loaded.to_dict()['schema_version']==version


@pytest.mark.parametrize('kwargs',[{'max_nodes':True},{'max_nodes':0},{'max_depth':-1},{'revision':True},{'process_id':''}])
def test_invalid_request_is_structured_and_never_mutates(tmp_path,kwargs):
    w,g,c,m,s=setup(tmp_path);inv,t=inventory(w,g,c,m);before=deepcopy((g.to_dict(),inv.to_dict()))
    with pytest.raises(ProcessPathError):build_local_process(g,inv,t,**{'process_id':'process:x',**kwargs})
    assert (g.to_dict(),inv.to_dict())==before


@pytest.mark.parametrize('checksum',[None,'missing','not-a-sha','A'*64])
def test_uncaptured_callee_missing_none_or_malformed_checksum_cannot_be_current(tmp_path,checksum):
    w,g,c,m,s=setup(tmp_path);child=helper(g,s,'uncaptured')
    add_cfg(g,child['id'],child,ir(child,'statement',label='UNCAPTURED-CALLEE-BODY'))
    add_cfg(g,m,s,call(g,s,child,'uncaptured'));inv,t=inventory(w,g,c,m)
    path='@backend/src/main/java/demo/Uncaptured.java'
    child['path']=path
    if checksum=='missing':child.pop('sha256',None)
    else:child['sha256']=checksum
    g.nodes=[replace(n,path=path,metadata=deepcopy(child)) if n.id==child['id'] else n for n in g.nodes]
    g.nodes.append(Node('uncaptured-file','file','Uncaptured.java',path,scope='production'))
    if checksum!='missing':
        g.files[path]=checksum
        next(ctx for ctx in g.contexts if ctx.get('id')==s['context_id'])['source_files'][path]=checksum
    cfg=next(x for x in g.cfgs if x['method']==child['id'])
    for block in cfg['blocks']:
        if block.get('source_file'):
            block['source_file']=path
            if checksum=='missing':block.pop('sha256',None)
            else:block['sha256']=checksum
    proof=next(p for p in g.evidence if p['relation']=='control_flow' and p['source']==child['id'])
    proof['source_file']=path
    if checksum=='missing':proof.pop('sha256',None)
    else:proof['sha256']=checksum
    before=deepcopy(g.to_dict())
    result=build_local_process(g,inv,t,process_id='process:uncaptured')
    assert not any(n.label=='UNCAPTURED-CALLEE-BODY' for n in result.steps)
    assert any(n.attributes.get('boundary_reason') for n in result.steps)
    assert g.to_dict()==before


def test_same_callee_two_calls_keep_each_original_site_on_call_return_and_exception(tmp_path):
    w,g,c,m,s=setup(tmp_path);child=helper(g,s,'child')
    add_cfg(g,child['id'],child,ir(child,'statement',label='child-body'))
    first=call(g,s,child,'first');second=call(g,s,child,'second')
    add_cfg(g,m,s,ir(s,'block',statements=[first,second]))
    inv,t=inventory(w,g,c,m)
    result=build_local_process(g,inv,t,process_id='process:two-sites')
    roundtrip=ProcessView.from_dict(result.to_dict())
    proofs={p['id']:p for p in roundtrip.technical_view.provenance}
    for site in g.call_sites:
        transitions=[e for e in roundtrip.transitions if e.attributes.get('call_site')==site['id']]
        assert {'call','returns_to','exception'}<={e.relation for e in transitions}
        for edge in transitions:
            assert site['id'] in edge.original_ids
            assert set(site['evidence_ids'])<={proofs[ref].get('original_id') for ref in edge.evidence_refs}
        calls=[e for e in transitions if e.relation=='call'];returns=[e for e in transitions if e.relation=='returns_to']
        assert len(calls)==1 and returns
        assert all(paths(roundtrip.transitions,calls[0].target,e.source) for e in returns)


def assert_finally_clone_topology(result,cfg,site_id):
    view=ProcessView.from_dict(result.to_dict());nodes={n.id:n for n in view.steps}
    originals={b['id'] for b in cfg['blocks'] if site_id in b.get('call_site_ids',[])}
    assert len(originals)>=2
    calls=[e for e in view.transitions if e.relation=='call' and e.attributes.get('call_site')==site_id]
    assert len(calls)==len(originals) and len({e.target for e in calls})==len(calls)
    assert {e.attributes['caller_block'] for e in calls}==originals
    for call_edge in calls:
        origin=call_edge.attributes['caller_block']
        assert origin in call_edge.original_ids
        for relation,original_kind in [('returns_to','normal'),('exception','exception')]:
            expected={e['target'] for e in cfg['edges'] if e['source']==origin and e['kind']==original_kind}
            edges=[e for e in view.transitions if e.relation==relation and e.attributes.get('caller_block')==origin]
            assert edges and all(set(nodes[e.target].original_ids)&expected for e in edges)
            assert all(e.attributes.get('call_site')==site_id and origin in e.original_ids for e in edges)


def test_finally_return_throw_clones_do_not_share_callee_continuations(tmp_path):
    w,g,c,m,s=setup(tmp_path);child=helper(g,s,'cleanup')
    add_cfg(g,child['id'],child,ir(child,'statement',label='cleanup-body'))
    cleanup=call(g,s,child,'cleanup')
    body=ir(s,'try',body=ir(s,'if',condition=ir(s,'statement',label='flag'),
        then=ir(s,'return',value=ir(s,'statement',label='returned')),
        **{'else':ir(s,'throw',value=ir(s,'statement',label='thrown'))}),catches=[],**{'finally':cleanup})
    cfg=add_cfg(g,m,s,body);inv,t=inventory(w,g,c,m);before=deepcopy((g.to_dict(),inv.to_dict()))
    result=build_local_process(g,inv,t,process_id='process:finally')
    assert_finally_clone_topology(result,cfg,g.call_sites[-1]['id'])
    for limit in (1,2,len(cfg['blocks'])+3):
        bounded=build_local_process(g,inv,t,process_id='process:finally-limit',max_nodes=limit)
        assert len(bounded.steps)<=limit and bounded.technical_status=='PARTIAL'
    assert (g.to_dict(),inv.to_dict())==before


def test_bare_legacy_context_does_not_expand_interprocedural_cfg(tmp_path):
    w,g,c,m,s=setup(tmp_path)
    for context in g.contexts:
        if context.get('analyzer_version'):
            context.update(mode='SYMBOL_RESOLVED');context.pop('worker',None);context.pop('origin_trust',None)
    child=helper(g,s,'legacy-child')
    add_cfg(g,child['id'],child,ir(child,'statement',label='legacy-child-body'))
    add_cfg(g,m,s,call(g,s,child,'legacy'))
    report=process(g,m)
    assert report['status']=='UNKNOWN'
    assert not any(b.get('label')=='legacy-child-body' for b in report['cfg']['blocks'])
    assert not any(e['kind']=='call' for e in report['cfg']['edges'])
    assert any(x['code']=='EXECUTION_AUTHORITY_UNKNOWN' for x in report['coverage']['gaps'])

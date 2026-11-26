"""W09: schema fixtures and separately identified actual compiler/parser evidence."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from kgmaker import flow
from kgmaker.analysis_model import AnalysisError
from kgmaker.model import KnowledgeGraph, Node

ROOT = Path(__file__).parents[1]
SOURCE = 'src/main/java/Checkout.java'


def model_graph():
    """Producer-shaped schema input, explicitly not an executed worker result."""
    checksum = hashlib.sha256((ROOT / 'fixtures/unified-flow' / SOURCE).read_bytes()).hexdigest()
    context = {'id':'ctx','mode':'BUILD_IMPORT','scope':'production','origin_trust':'LOCAL_COMPILER_INPUTS',
               'freshness':'CONTENT_VERIFIED','analyzer_version':'model-only',
               'worker':{'protocol_version':1,'worker':'model-only','compiler_version':'model-only'},
               'source_files':{SOURCE:checksum},'coverage':'COMPLETE'}
    blocks = [{'id':i,'kind':k,'label':label,'source_file':SOURCE,'sha256':checksum,
               'source_range':{'start_line':4},'original_ids':['ast:'+i]}
              for i,k,label in [('entry','entry','entry'),('choice','condition','approved?'),
                               ('left','basic_block','charge "<amount>" | accepted'),
                               ('right','async_boundary','enqueue'),('join','loop_header','retry?'),
                               ('unknown','unresolved_boundary','unknown callee'),('exit','exit','return'),
                               ('error','exceptional_exit','error')]]
    edges = [{'source':a,'target':b,'kind':k} for a,b,k in [
        ('entry','choice','normal'),('choice','left','true'),('choice','right','false'),
        ('left','join','normal'),('right','join','resume'),('right','error','exception'),
        ('join','unknown','true'),('unknown','join','normal'),('join','exit','false')]]
    edges[-2]['loop_back'] = True
    graph = KnowledgeGraph(schema_version=3,root='.',generated_at='model-only',
        nodes=[Node('method','method','checkout',SOURCE,scope='production',role='executable_code')],
        edges=[],files={SOURCE:checksum},contexts=[context],diagnostics=[],
        evidence=[{'id':'cfg-proof','kind':'SYNTAX_CANDIDATE','context_ids':['ctx'],'freshness':'CURRENT'}],
        symbols=[{'id':'method','context_id':'ctx'}],call_sites=[],
        cfgs=[{'method':'method','context_id':'ctx','representation':'SOURCE','entry':'entry','exit':'exit',
               'exceptional_exit':'error','blocks':blocks,'edges':edges,'evidence_ids':['cfg-proof']}])
    return KnowledgeGraph.from_dict(graph.to_dict())


def test_three_formats_share_cfg_order_provenance_and_gaps():
    graph = model_graph(); before = copy.deepcopy(graph.to_dict())
    report = flow.build_report(graph,'method')
    assert report['flow_model_version'] == 'flow-view-1'
    assert report['ordering']['kind'] == 'CFG_PARTIAL_ORDER'
    assert report['ordering']['display_order'][0] == 'entry'
    assert [b['id'] for b in report['cfg']['blocks']] == report['ordering']['display_order']
    assert report['execution'] == 'NOT_OBSERVED' and report['availability'] == 'UNKNOWN'
    assert {'ASYNC_ORDER_UNKNOWN','UNRESOLVED_BOUNDARY'} <= {g['code'] for g in report['coverage']['gaps']}
    assert not any(e['source'] == 'left' and e['target'] == 'right' for e in report['cfg']['edges'])
    for fmt, extension in [('json','json'),('mermaid','mmd'),('markdown','md')]:
        text = flow.render(report,fmt)
        assert text == (ROOT/'tests/golden/unified-flow'/('branch.'+extension)).read_text()
    assert graph.to_dict() == before


@pytest.mark.parametrize('version',[1,2,3])
def test_legacy_source_only_missing_cfg_is_unknown_not_empty_complete(version):
    graph = KnowledgeGraph(version,'.','legacy',[Node('method','method','checkout',SOURCE,
        scope='production',role='executable_code')],[],{SOURCE:'legacy'})
    report = flow.build_report(graph,'method',scope='all' if version==1 else 'production')
    assert report['status'] == 'UNKNOWN'
    assert report['cfg']['blocks'] == []
    assert any(g['code']=='CFG_UNAVAILABLE' for g in report['coverage']['gaps'])
    assert 'UNKNOWN' in flow.render(report,'markdown')


def test_order_is_stable_under_snapshot_permutations_and_cycles():
    graph=model_graph(); before=flow.build_report(graph,'method')
    graph.cfgs[0]['blocks'].reverse();graph.cfgs[0]['edges'].reverse()
    assert flow.build_report(graph,'method') == before
    assert any(e.get('loop_back') for e in before['cfg']['edges'])


def test_truncation_retains_bounded_original_endpoints():
    report=flow.build_report(model_graph(),'method',max_nodes=3)
    assert report['truncated'] and report['status']=='PARTIAL'
    assert any(g['code']=='NODE_LIMIT' for g in report['coverage']['gaps'])
    assert all(e['target'] in {b['id'] for b in report['cfg']['blocks']} for e in report['cfg']['edges'])
    assert len(report['cfg']['blocks']) <= 3
    assert report['cfg']['exit'] is None and report['cfg']['omitted_exit']=='exit'


@pytest.mark.parametrize('branches', [64, 128])
def test_truncation_visits_fanout_edges_a_bounded_number_of_times(branches, monkeypatch):
    graph = model_graph()
    cfg = graph.cfgs[0]
    root, normal_exit, error_exit = (cfg['blocks'][index] for index in (0, -2, -1))
    leaves = [{**root, 'id': f'leaf-{i:03d}', 'kind': 'basic_block'} for i in range(branches)]
    cfg['blocks'] = [root, *leaves, normal_exit, error_exit]
    cfg['edges'] = [{'source': 'entry', 'target': leaf['id'], 'kind': 'true'} for leaf in leaves]
    cfg['edges'] += [{'source': leaf['id'], 'target': 'exit', 'kind': 'normal'} for leaf in leaves]
    before = copy.deepcopy(graph.to_dict())
    edge_visits = 0

    class CountedEdges(list):
        def __iter__(self):
            nonlocal edge_visits
            for edge in super().__iter__():
                edge_visits += 1
                yield edge

    project = flow.project

    def count_projected_edges(*args, **kwargs):
        scoped = project(*args, **kwargs)
        scoped.cfgs = [item if isinstance(item['edges'], CountedEdges)
                       else {**item, 'edges': CountedEdges(item['edges'])} for item in scoped.cfgs]
        return scoped

    monkeypatch.setattr(flow, 'project', count_projected_edges)
    report = flow.build_report(graph, 'method', max_nodes=branches // 2)
    assert report['truncated']
    block, = report['cfg']['blocks']
    assert block['kind'] == 'unresolved_boundary'
    assert block['original_ids'] == ['entry', 'error', 'exit', 'method']
    assert report['cfg']['edges'] == []
    assert graph.to_dict() == before
    assert 0 < edge_visits <= 8 * len(cfg['edges'])


def cyclic_frontier_graph():
    graph = model_graph()
    cfg = graph.cfgs[0]
    entry, normal_exit, error_exit = (cfg['blocks'][index] for index in (0, -2, -1))
    internal = [{**entry, 'id': key, 'kind': 'basic_block', 'original_ids': [f'ast:{key}']}
                for key in ('a', 'b', 'c', 'unused')]
    cfg['blocks'] = [entry, *internal, normal_exit, error_exit]
    cfg['edges'] = [
        {'source': source, 'target': target, 'kind': relation}
        for source, target, relation in (
            ('entry', 'a', 'normal'), ('entry', 'b', 'true'), ('entry', 'c', 'false'),
            ('a', 'b', 'normal'), ('a', 'c', 'true'),
            ('b', 'a', 'normal'), ('b', 'c', 'false'), ('b', 'error', 'exception'),
            ('c', 'a', 'normal'), ('c', 'b', 'resume'), ('c', 'exit', 'normal'),
        )
    ]
    for edge in cfg['edges']:
        if edge['target'] == 'a' and edge['source'] in {'b', 'c'}:
            edge['loop_back'] = True
    return graph


@pytest.mark.parametrize(('budget', 'retained', 'omitted'), [
    (4, {'entry', 'a'}, {'b', 'c'}),
    (5, {'entry', 'a', 'b'}, {'c', 'error'}),
    (6, {'entry', 'a', 'b', 'c', 'exit', 'error'}, set()),
])
def test_truncation_preserves_exact_shared_frontier_and_dense_cycle(budget, retained, omitted):
    graph = cyclic_frontier_graph()
    before = copy.deepcopy(graph.to_dict())
    report = flow.build_report(graph, 'method', max_nodes=budget)
    blocks = report['cfg']['blocks']
    boundaries = {row['id']: row['original_ids'][0] for row in blocks if row['kind'] == 'unresolved_boundary'}
    assert {row['id'] for row in blocks} - boundaries.keys() == retained
    assert set(boundaries.values()) == omitted
    assert len(blocks) == budget
    actual_edges = {(edge['source'], boundaries.get(edge['target'], edge['target']), edge['kind'],
                     edge.get('loop_back', False)) for edge in report['cfg']['edges']}
    expected_edges = {(edge['source'], edge['target'], edge['kind'], edge.get('loop_back', False))
                      for edge in graph.cfgs[0]['edges'] if edge['source'] in retained}
    assert actual_edges == expected_edges
    assert report['truncated'] is True and report['status'] == 'PARTIAL'
    assert report['execution'] == 'NOT_OBSERVED' and report['availability'] == 'UNKNOWN'
    assert report['provenance']['evidence_ids'] == ['cfg-proof']
    assert graph.to_dict() == before


def test_invalid_snapshot_cannot_be_hidden_by_projection():
    graph=model_graph();graph.cfgs[0]['edges'][0]['target']='missing'
    before=copy.deepcopy(graph.to_dict())
    with pytest.raises((AnalysisError,ValueError)):
        flow.build_report(graph,'method')
    assert graph.to_dict()==before


def process_graph():
    from kgmaker.model import Edge
    graph=model_graph()
    graph.nodes.extend([Node(i,k,i,SOURCE,scope='production',role='executable_code')
                        for i,k in [('callee','method'),('site','call_site')]])
    graph.symbols.append({'id':'callee','context_id':'ctx','annotations':[]})
    graph.evidence.append({'id':'call-proof','kind':'SYMBOL_RESOLVED','context_ids':['ctx'],'freshness':'CURRENT'})
    graph.call_sites=[{'id':'site','caller':'method','context_id':'ctx','declared_target':'callee',
        'dispatch_candidates':[],'dispatch_complete':True,'invocation_kind':'STATIC',
        'evidence_kind':'SYMBOL_RESOLVED','evidence_ids':['call-proof'],'resolution_reason':'MODEL_ONLY'}]
    graph.edges=[Edge('method','site','declares_call',evidence_kind='SYMBOL_RESOLVED',context_ids=('ctx',),evidence_ids=('call-proof',)),
                 Edge('site','callee','resolves_to',evidence_kind='SYMBOL_RESOLVED',context_ids=('ctx',),evidence_ids=('call-proof',))]
    graph.cfgs[0]['blocks'][2].update(kind='call',call_site_ids=['site'])
    graph.cfgs.append({'method':'callee','context_id':'ctx','representation':'SOURCE',
        'entry':'child-entry','exit':'child-exit','exceptional_exit':'child-error',
        'evidence_ids':['cfg-proof'],'blocks':[{'id':i,'kind':k} for i,k in
        [('child-entry','entry'),('child-exit','exit'),('child-error','exceptional_exit')]],
        'edges':[{'source':'child-entry','target':'child-exit','kind':'normal'}]})
    checksum=graph.files[SOURCE];span={'start':60,'end':65,'start_line':4}
    graph.call_sites[0].update(path=SOURCE,sha256=checksum,range=span)
    graph.cfgs[0]['blocks'][2]['source_range']=span
    for cfg in graph.cfgs:
        proof_id='body-proof:'+cfg['method']
        cfg['evidence_ids']=[proof_id]
        graph.evidence.append({'id':proof_id,'kind':'SYNTAX_CANDIDATE','relation':'control_flow',
            'source':cfg['method'],'target':cfg['method'],'context_ids':['ctx'],
            'source_file':SOURCE,'sha256':checksum,'representation':'SOURCE','freshness':'CURRENT',
            'source_range':{'start':0,'end':len((ROOT/'fixtures/unified-flow'/SOURCE).read_bytes()),'start_line':1}})
    return KnowledgeGraph.from_dict(graph.to_dict())


@pytest.mark.parametrize('damage',[None,'reference','stale','source_only','missing_edge','missing_cfg','callee_cfg_stale','context_stale'])
def test_process_expansion_requires_current_executable_authority(damage):
    graph=process_graph()
    if damage=='reference': graph.call_sites[0]['invocation_kind']='METHOD_REFERENCE'
    elif damage=='stale': next(p for p in graph.evidence if p['id']=='call-proof')['freshness']='STALE'
    elif damage=='source_only': graph.contexts[0]['mode']='SOURCE_ONLY'
    elif damage=='missing_edge': graph.edges.pop()
    elif damage=='missing_cfg': graph.cfgs.pop()
    elif damage=='context_stale': graph.contexts[0]['freshness']='STALE'
    elif damage=='callee_cfg_stale':
        graph.evidence.append({'id':'stale-body','kind':'SYNTAX_CANDIDATE','freshness':'STALE','context_ids':['ctx']})
        graph.cfgs[-1]['evidence_ids']=['stale-body']
    report=flow.build_report(graph,'method',view='process')
    expanded={b.get('method') for b in report['cfg']['blocks']}
    assert ('callee' in expanded) == (damage is None)
    assert any(e['kind']=='call' for e in report['cfg']['edges']) == (damage is None)
    if damage is not None:
        assert report['status'] in {'UNKNOWN','PARTIAL'} and report['boundaries']
    assert report['execution']=='NOT_OBSERVED'
    if damage=='stale':
        assert any(g['code']=='STALE_EVIDENCE' and 'call-proof' in g.get('evidence_ids',[]) for g in report['coverage']['gaps'])


@pytest.mark.parametrize('view',['integrations','data-flow'])
def test_relation_views_support_three_formats_without_execution_order(view):
    graph=process_graph()
    report=flow.build_report(graph,'method',view=view,max_nodes=2)
    assert report['ordering']['kind']=='RELATIONSHIP_ONLY'
    assert report['status']=='PARTIAL' and report['truncated']
    assert len(report['nodes'])==2
    for fmt in ('json','markdown','mermaid'):
        assert 'RELATIONSHIP_ONLY' in flow.render(report,fmt)


@pytest.mark.parametrize('failure',['cancel','timeout','interrupt','error'])
def test_atomic_failure_after_temp_write_preserves_last_valid_and_cleans_temp(tmp_path,monkeypatch,failure):
    import os
    from kgmaker.flow_report import RenderBudget
    report=flow.build_report(model_graph(),'method');output=tmp_path/'last.json'
    output.write_text('last-valid');cancel=tmp_path/'cancel';budget=RenderBudget(30,cancel)
    real_fsync=os.fsync
    def after_write(fd):
        real_fsync(fd)
        if failure=='cancel': cancel.touch()
        elif failure=='timeout': budget.deadline=0
        elif failure=='interrupt': raise KeyboardInterrupt()
        else: raise OSError('injected disk failure')
    monkeypatch.setattr(os,'fsync',after_write)
    with pytest.raises((AnalysisError,KeyboardInterrupt,OSError)):
        flow.publish(report,'json',output,budget=budget)
    assert output.read_text()=='last-valid'
    assert not list(tmp_path.glob('.kgmaker-*'))


def test_abort_new_parent_contract_and_invalid_report_no_side_effect(tmp_path,monkeypatch):
    import os
    target=tmp_path/'new'/'nested'/'report.json'
    bad=flow.build_report(model_graph(),'method');bad['cfg']['edges'][0]['target']='absent'
    with pytest.raises(AnalysisError): flow.publish(bad,'json',target)
    assert not target.parent.exists()
    def stop(fd): raise KeyboardInterrupt()
    monkeypatch.setattr(os,'fsync',stop)
    with pytest.raises(KeyboardInterrupt): flow.publish(flow.build_report(model_graph(),'method'),'json',target)
    assert not (tmp_path/'new').exists()


def test_output_protects_store_sources_symlinks_hardlinks_and_cancel(tmp_path):
    from kgmaker.flow_report import output_path
    graph=model_graph();exports=tmp_path/'.kgmaker/flows';exports.mkdir(parents=True)
    cancel=exports/'cancel';cancel.touch()
    for path in ['.kgmaker/graph.json',SOURCE,'.kgmaker/flows/../graph.json',tmp_path/'outside.json']:
        with pytest.raises(AnalysisError): output_path(tmp_path,path,graph)
    with pytest.raises(AnalysisError): output_path(tmp_path,cancel,graph,cancel)
    alias=exports/'alias';alias.symlink_to(cancel)
    with pytest.raises((AnalysisError,ValueError)): output_path(tmp_path,alias,graph)
    import os
    alias.unlink();os.link(cancel,alias)
    with pytest.raises((AnalysisError,ValueError)): output_path(tmp_path,alias,graph)


@pytest.mark.parametrize('failure',['timeout','cancel','interrupt'])
def test_late_abort_removes_only_attempt_created_empty_directories(tmp_path,monkeypatch,failure):
    import os
    from kgmaker.flow_report import RenderBudget
    existing=tmp_path/'existing';existing.mkdir();(existing/'keep').write_text('unchanged')
    before={p.relative_to(tmp_path) for p in tmp_path.rglob('*')}
    cancel=tmp_path/'cancel';budget=RenderBudget(30,cancel)
    def fail(fd):
        if failure=='timeout': budget.deadline=0
        elif failure=='cancel': cancel.touch()
        else: raise KeyboardInterrupt()
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises((AnalysisError,KeyboardInterrupt)):
        flow.publish(flow.build_report(model_graph(),'method'),'json',existing/'new/nested/report',budget=budget)
    if cancel.exists(): cancel.unlink()  # External cancellation input is not publication mutation.
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob('*')}==before
    assert (existing/'keep').read_text()=='unchanged'


def test_abort_preserves_concurrent_content_in_created_parent(tmp_path,monkeypatch):
    import os
    target=tmp_path/'new/report'
    def fail(fd):
        (target.parent/'other').write_text('concurrent')
        raise KeyboardInterrupt()
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises(KeyboardInterrupt): flow.publish(flow.build_report(model_graph(),'method'),'json',target)
    assert (target.parent/'other').read_text()=='concurrent'
    assert not target.exists() and not list(target.parent.glob('.kgmaker-*'))


def test_actual_javac_public_formats_parser_and_readonly_failures(tmp_path,monkeypatch):
    import io
    import os
    import shutil
    import subprocess
    from contextlib import redirect_stdout
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    from kgmaker.cli import main
    shutil.copytree(ROOT/'fixtures/unified-flow/src',tmp_path/'src')
    try:
        capture=inspect_jvm(tmp_path,classpath=[],publish=True)
    except WorkerError as error:
        if error.status=='TOOLCHAIN_UNAVAILABLE' and os.environ.get('KGMAKER_REQUIRE_WORKERS')!='1': pytest.skip(str(error))
        raise
    graph=KnowledgeGraph.from_dict(capture['graph'])
    entry=next(n.id for n in graph.nodes if n.kind=='method' and n.name=='checkout')
    unresolved=next(n.id for n in graph.nodes if n.kind=='method' and n.name=='unresolved')
    before=(tmp_path/'.kgmaker/graph.json').read_bytes()
    native=flow.build_report(graph,entry,view='process')
    assert any(e['kind']=='call' for e in native['cfg']['edges'])
    assert any(e.get('loop_back') for e in native['cfg']['edges'])
    assert any(e['kind']=='true' for e in native['cfg']['edges'])
    assert any(g['code']=='UNRESOLVED_CALL' for g in flow.build_report(graph,unresolved)['coverage']['gaps'])
    from kgmaker.dataflow import argument_parameter_bindings
    site=next(s for s in graph.call_sites if s['caller']==entry and '.charge(' in str(s.get('declared_target')))
    bindings=argument_parameter_bindings(graph,site['id']);assert bindings
    for damage in ('weak_context','stale_caller'):
        weak=KnowledgeGraph.from_dict(copy.deepcopy(graph.to_dict()))
        root_cfg=next(c for c in weak.cfgs if c['method']==entry)
        if damage=='weak_context':
            next(c for c in weak.contexts if c['id']==root_cfg['context_id']).update(mode='BUILD_AWARE',origin_trust='LOCAL_SOURCE',worker={})
        else:
            for proof in weak.evidence:
                if proof['id'] in root_cfg['evidence_ids']: proof['freshness']='STALE'
        before_weak=copy.deepcopy(weak.to_dict())
        reference=flow.build_report(weak,entry,view='process')
        block=next(b for b in reference['cfg']['blocks'] if b.get('argument_parameter_bindings')==bindings)
        assert block['binding_projection']=='REFERENCE_ONLY'
        assert block['argument_binding_status']['execution']=='NOT_OBSERVED'
        assert not any(e['kind'] in {'call','returns_to'} for e in reference['cfg']['edges'])
        assert not any(b.get('method')==site['declared_target'] for b in reference['cfg']['blocks'])
        if damage=='stale_caller':
            assert any(g['code']=='STALE_EVIDENCE' for g in reference['coverage']['gaps'])
            assert any(p['id'] in root_cfg['evidence_ids'] and p['freshness']=='STALE' for p in reference['provenance']['evidence'])
        assert weak.to_dict()==before_weak
    texts={}
    def cli(extra):
        out=io.StringIO()
        with monkeypatch.context() as m, redirect_stdout(out):
            m.setattr('subprocess.Popen',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('implicit process')))
            m.setattr('socket.socket',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('implicit network')))
            m.setattr('sys.argv',['kgmaker','flow','render','--root',str(tmp_path),'--entry',entry,
                                  '--context',capture['context']['id'],'--view','process',*extra])
            with pytest.raises(SystemExit) as outcome: main()
        return outcome.value.code,out.getvalue()
    for fmt in ('json','markdown','mermaid'):
        code,text=cli(['--format',fmt]);assert code==0,text
        texts[fmt]=text
    report=json.loads(texts['json'])
    assert report==native
    assert texts['markdown'].split('```mermaid\n',1)[1].split('```',1)[0]==texts['mermaid']
    rendered=tmp_path/'.kgmaker/flows';rendered.mkdir(parents=True)
    for filename,content in [('actual.json',texts['json']),('actual.mmd',texts['mermaid'])]: (rendered/filename).write_text(content)
    parser=ROOT/'tests/rendering/node_modules/mermaid/package.json'
    if not parser.exists(): pytest.fail('Prepared pinned Mermaid parser is required for this acceptance')
    assert json.loads(parser.read_text())['version']=='11.4.1'
    parsed=subprocess.run(['node',str(ROOT/'tests/rendering/validate_unified.mjs'),str(rendered/'actual.mmd'),str(rendered/'actual.json')],capture_output=True,text=True)
    assert parsed.returncode==0,parsed.stderr
    assert json.loads(parsed.stdout)['vertices']==len(report['cfg']['blocks'])
    target=tmp_path/'.kgmaker/flows/report.json'
    published=cli(['--format','json','--output','.kgmaker/flows/report.json'])
    assert published[0]==0,published
    valid=target.read_bytes()
    for args in [['--max-nodes','0'],['--timeout','nan'],['--timeout','-1'],['--entry','missing']]:
        assert cli(['--output','.kgmaker/flows/report.json',*args])[0]!=0
        assert target.read_bytes()==valid
    cancel=tmp_path/'cancel';cancel.touch()
    assert cli(['--output','.kgmaker/flows/report.json','--cancel-file',str(cancel)])[0]==4
    assert target.read_bytes()==valid
    assert cli(['--output','.kgmaker/graph.json'])[0]==2
    assert (tmp_path/'.kgmaker/graph.json').read_bytes()==before
    source=tmp_path/SOURCE;source_bytes=source.read_bytes();real_fsync=os.fsync
    for mutation in ('source','index'):
        def after_write(fd):
            real_fsync(fd)
            if mutation=='source': source.write_bytes(source_bytes+b'\n// concurrent edit\n')
            else: (tmp_path/'.kgmaker/graph.json').write_bytes(before+b'\n')
        with monkeypatch.context() as m:
            m.setattr(os,'fsync',after_write)
            code,text=cli(['--format','json','--output','.kgmaker/flows/report.json'])
        assert code==3 and json.loads(text)['status']=='STALE',text
        assert target.read_bytes()==valid
        assert not list(rendered.glob('.kgmaker-*'))
        source.write_bytes(source_bytes);(tmp_path/'.kgmaker/graph.json').write_bytes(before)


@pytest.mark.parametrize('refs',[[],['site','site']])
def test_ambiguous_call_block_is_partial_without_guessed_expansion(refs):
    graph=process_graph();graph.cfgs[0]['blocks'][2]['call_site_ids']=refs
    report=flow.build_report(graph,'method',view='process')
    assert report['status']=='PARTIAL'
    assert any(g['code']=='AMBIGUOUS_CALL_BLOCK' for g in report['coverage']['gaps'])
    assert not any(e['kind']=='call' for e in report['cfg']['edges'])


def test_invalid_representation_is_not_an_unknown_empty_success():
    with pytest.raises(AnalysisError): flow.build_report(model_graph(),'method',representation='INVALID')


@pytest.mark.parametrize('damage',['configuration','type','test_scope'])
def test_process_never_expands_non_execution_roles_or_cross_scope(damage):
    from dataclasses import replace
    graph=process_graph()
    if damage=='configuration': graph.nodes=[replace(n,role='configuration') if n.id=='method' else n for n in graph.nodes]
    elif damage=='type': graph.nodes=[replace(n,kind='class') if n.id=='callee' else n for n in graph.nodes]
    else: graph.nodes=[replace(n,scope='test') if n.id=='callee' else n for n in graph.nodes]
    report=flow.build_report(graph,'method',view='process',scope='all')
    assert not any(e['kind']=='call' for e in report['cfg']['edges'])
    assert not any(b.get('method')=='callee' for b in report['cfg']['blocks'])
    assert report['status']=='PARTIAL' and report['boundaries']


def test_actual_frontend_value_relations_survive_unified_single_context_view(tmp_path,monkeypatch):
    """Reuse merged W05 capture; no invented cross-compiler context selection."""
    import subprocess
    from test_backend_frontend_value_flow import capture_workspace
    from kgmaker.store import load_graph
    root,_=capture_workspace(tmp_path)
    graph=load_graph(root/'frontend');before=copy.deepcopy(graph.to_dict())
    entry=next(s['id'] for s in graph.symbols if s.get('value_role')=='HTTP_RESPONSE')
    target=next(s['id'] for s in graph.symbols if s.get('value_role')=='JSX_CONSUMER')
    with monkeypatch.context() as m:
        m.setattr('subprocess.Popen',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('implicit process')))
        report=flow.build_report(graph,entry,view='data-flow')
        outputs={fmt:flow.render(report,fmt) for fmt in ['json','mermaid','markdown']}
    assert report['ordering']['kind']=='RELATIONSHIP_ONLY'
    assert report['execution']=='NOT_OBSERVED' and report['availability']=='UNKNOWN'
    seen=set();pending=[entry]
    while pending:
        identity=pending.pop()
        if identity in seen: continue
        seen.add(identity)
        pending.extend(e['target'] for e in report['cfg']['edges'] if e['source']==identity)
    assert target in seen
    # passes_value is an ordinary argument consumer; this frontend fixture
    # uses a state setter (writes_value), not that separate test path.
    assert {'writes_value','displayed_in'} <= {e['kind'] for e in report['cfg']['edges']}
    assert all(e['evidence_ids'] for e in report['cfg']['edges'] if e['kind'] in {'passes_value','writes_value','displayed_in'})
    assert graph.to_dict()==before
    (tmp_path/'view.mmd').write_text(outputs['mermaid']);(tmp_path/'view.json').write_text(outputs['json'])
    parsed=subprocess.run(['node',str(ROOT/'tests/rendering/validate_unified.mjs'),str(tmp_path/'view.mmd'),str(tmp_path/'view.json')],capture_output=True,text=True)
    assert parsed.returncode==0,parsed.stderr


def test_relation_renderer_keeps_mixed_compiler_claim_omitted_with_gap():
    from kgmaker.model import Edge
    graph=process_graph();graph.contexts.append({**graph.contexts[0],'id':'other'})
    graph.evidence.append({'id':'mixed-proof','kind':'SYMBOL_RESOLVED','context_ids':['ctx','other']})
    graph.edges.append(Edge('method','callee','writes_value',evidence_kind='SYMBOL_RESOLVED',
                           context_ids=('ctx','other'),evidence_ids=('mixed-proof',)))
    before=copy.deepcopy(graph.to_dict())
    report=flow.build_report(graph,'method',view='data-flow',context_id='ctx')
    assert {c['id'] for c in report['contexts']}=={'ctx'}
    assert not any(e['kind']=='writes_value' for e in report['cfg']['edges'])
    assert 'mixed-proof' not in report['provenance']['evidence_ids']
    assert any(g['code']=='COMPILER_CONTEXT_BOUNDARY_UNKNOWN' for g in report['coverage']['gaps'])
    for fmt in ('json','markdown','mermaid'):
        assert 'COMPILER_CONTEXT_BOUNDARY_UNKNOWN' in flow.render(report,fmt)
    assert graph.to_dict()==before


@pytest.mark.parametrize('schema',[1,2,3])
@pytest.mark.parametrize('mutation',['source','index','addition','classification'])
@pytest.mark.parametrize('new_parent',[False,True])
def test_publication_rechecks_legacy_source_only_after_fsync(tmp_path,monkeypatch,schema,mutation,new_parent):
    import io
    import os
    from contextlib import redirect_stdout
    from kgmaker.cli import main
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    source=tmp_path/'app.py';source.write_text('def entry():\n    return 1\n')
    graph=scan_repository(tmp_path);graph.schema_version=schema
    save_graph(graph,tmp_path,generate_docs=False)
    index=tmp_path/'.kgmaker/graph.json';original=index.read_bytes()
    entry=next(n.id for n in graph.nodes if n.name=='entry')
    target=tmp_path/'.kgmaker/flows/new/nested/report.json'
    if not new_parent: target.parent.mkdir(parents=True);target.write_bytes(b'last-valid')
    baseline={p.relative_to(tmp_path):p.read_bytes() if p.is_file() else None for p in tmp_path.rglob('*')}
    real_fsync=os.fsync;mutations=[]
    def mutate(fd):
        real_fsync(fd);mutations.append(mutation)
        if mutation=='source': source.write_text('def entry():\n    return 2\n')
        elif mutation=='index': index.write_bytes(original+b'\n')
        elif mutation=='classification': (tmp_path/'.kgmaker/classification.json').write_text('{"schema_version":1,"overrides":[]}')
        else: (tmp_path/'added.py').write_text('def added(): pass\n')
    with monkeypatch.context() as m,redirect_stdout(io.StringIO()) as out:
        m.setattr(os,'fsync',mutate)
        m.setattr('subprocess.Popen',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('implicit process')))
        m.setattr('socket.socket',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('implicit network')))
        m.setattr('sys.argv',['kgmaker','flow','render','--root',str(tmp_path),'--entry',entry,
                             '--scope','all','--format','json','--output',str(target)])
        with pytest.raises(SystemExit) as outcome: main()
    assert outcome.value.code==3,out.getvalue()
    assert mutations==[mutation]
    assert json.loads(out.getvalue())['status']=='STALE'
    # Restore only the independently injected concurrent mutation. Publication
    # must have left every preexisting byte and directory exactly as before.
    source.write_bytes(baseline[Path('app.py')]);index.write_bytes(original)
    (tmp_path/'added.py').unlink(missing_ok=True)
    (tmp_path/'.kgmaker/classification.json').unlink(missing_ok=True)
    assert {p.relative_to(tmp_path):p.read_bytes() if p.is_file() else None for p in tmp_path.rglob('*')}==baseline
    # The syntax-only report is supported but never gains compiler authority.
    assert flow.build_report(KnowledgeGraph.from_dict(graph.to_dict()),entry,scope='all')['status']=='UNKNOWN'


@pytest.mark.parametrize('mutation',['index','addition','source','classification'])
def test_publication_never_binds_new_inputs_to_previously_loaded_graph(tmp_path,monkeypatch,mutation):
    import io
    from contextlib import redirect_stdout
    from kgmaker import inspection_cli
    from kgmaker.cli import main
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    (tmp_path/'app.py').write_text('def entry(): pass\n')
    graph=scan_repository(tmp_path);save_graph(graph,tmp_path,generate_docs=False)
    entry=next(n.id for n in graph.nodes if n.name=='entry')
    original_indexed=inspection_cli.indexed
    def changed(args):
        result=original_indexed(args)
        if mutation=='index':
            index=tmp_path/'.kgmaker/graph.json';index.write_bytes(index.read_bytes()+b'\n')
        elif mutation=='addition': (tmp_path/'added.py').write_text('def added(): pass\n')
        elif mutation=='classification': (tmp_path/'.kgmaker/classification.json').write_text(json.dumps({'schema_version':1,'overrides':[{'path':'app.py','scope':'test','reason':'concurrent edit'}]}))
        else: (tmp_path/'app.py').write_text('def entry(): return 2\n')
        return result
    monkeypatch.setattr(inspection_cli,'indexed',changed)
    monkeypatch.setattr('sys.argv',['kgmaker','flow','render','--root',str(tmp_path),'--entry',entry,
        '--scope','all','--output','.kgmaker/flows/new/report.json'])
    with redirect_stdout(io.StringIO()) as out,pytest.raises(SystemExit) as outcome: main()
    assert outcome.value.code==3 and json.loads(out.getvalue())['status']=='STALE'
    assert not (tmp_path/'.kgmaker/flows').exists()


@pytest.mark.parametrize('suffix',['.xlsx','.xls'])
@pytest.mark.parametrize('mutation',['changed','added','deleted'])
def test_publication_preserves_binary_fingerprints_and_inventory(tmp_path,monkeypatch,suffix,mutation):
    import io
    import os
    from contextlib import redirect_stdout
    from kgmaker.cli import main
    from kgmaker.scanner import scan_repository
    from kgmaker.store import save_graph
    from kgmaker.workbooks import attach_workbooks, workbook_hash
    from test_workbooks import write_xlsx
    (tmp_path/'app.py').write_text('def entry(): pass\n')
    workbook=tmp_path/('input'+suffix)
    if suffix=='.xlsx': write_xlsx(workbook)
    else: workbook.write_bytes(b'unsupported binary XLS')
    graph=attach_workbooks(tmp_path,scan_repository(tmp_path))
    assert graph.files[workbook.name]==workbook_hash(workbook)
    assert any(n.kind=='workbook_cell' for n in graph.nodes) if suffix=='.xlsx' else any(d['code']=='BINARY_XLS_UNSUPPORTED' for d in graph.diagnostics)
    save_graph(graph,tmp_path,generate_docs=False)
    entry=next(n.id for n in graph.nodes if n.name=='entry')
    target=tmp_path/'.kgmaker/flows/report.json'
    def cli():
        with monkeypatch.context() as m,redirect_stdout(io.StringIO()) as out:
            m.setattr('sys.argv',['kgmaker','flow','render','--root',str(tmp_path),'--entry',entry,
                                 '--scope','all','--format','json','--output',str(target)])
            m.setattr('kgmaker.workbooks.extract',lambda *a,**k: (_ for _ in ()).throw(AssertionError('renderer re-parsed workbook')))
            m.setattr('subprocess.Popen',lambda *a,**k: (_ for _ in ()).throw(AssertionError('implicit process')))
            with pytest.raises(SystemExit) as outcome: main()
        return outcome.value.code,out.getvalue()
    code,text=cli();assert code==0,text
    valid=target.read_bytes();assert json.loads(valid)['status']=='UNKNOWN'
    real_fsync=os.fsync
    def mutate(fd):
        real_fsync(fd)
        if mutation=='changed': workbook.write_bytes(workbook.read_bytes()+b'changed')
        elif mutation=='added': (tmp_path/('another'+suffix)).write_bytes(workbook.read_bytes())
        else: workbook.unlink()
    monkeypatch.setattr(os,'fsync',mutate)
    code,text=cli()
    assert code==3 and json.loads(text)['status']=='STALE',text
    assert target.read_bytes()==valid and not list(target.parent.glob('.kgmaker-*'))


def nested_process_graph():
    from dataclasses import replace
    from kgmaker.model import Edge
    graph=process_graph()
    graph.nodes.extend([replace(next(n for n in graph.nodes if n.id==old),id=new,name=new)
                        for old,new in [('callee','leaf'),('site','nested-site')]])
    graph.symbols.append({'id':'leaf','context_id':'ctx','annotations':[]})
    site={**copy.deepcopy(graph.call_sites[0]),'id':'nested-site','caller':'callee','declared_target':'leaf',
          'evidence_ids':['nested-call-proof'],'range':{'start':80,'end':85,'start_line':5}}
    graph.call_sites.append(site)
    graph.evidence.append({'id':'nested-call-proof','kind':'SYMBOL_RESOLVED','context_ids':['ctx'],'freshness':'CURRENT'})
    graph.edges.extend([Edge('callee','nested-site','declares_call',evidence_kind='SYMBOL_RESOLVED',context_ids=('ctx',),evidence_ids=('nested-call-proof',)),
                        Edge('nested-site','leaf','resolves_to',evidence_kind='SYMBOL_RESOLVED',context_ids=('ctx',),evidence_ids=('nested-call-proof',))])
    child=graph.cfgs[1]
    child['blocks'].append({'id':'nested-block','kind':'call','call_site_ids':['nested-site'],
                           'source_file':SOURCE,'sha256':graph.files[SOURCE],'source_range':site['range']})
    child['edges']=[{'source':'child-entry','target':'nested-block','kind':'normal'},
                    {'source':'nested-block','target':'child-exit','kind':'normal'}]
    leaf=copy.deepcopy(process_graph().cfgs[1]);leaf.update(method='leaf',evidence_ids=['body-proof:leaf'])
    graph.cfgs.append(leaf)
    proof=copy.deepcopy(next(p for p in graph.evidence if p['id']=='body-proof:callee'))
    proof.update(id='body-proof:leaf',source='leaf',target='leaf');graph.evidence.append(proof)
    return KnowledgeGraph.from_dict(graph.to_dict())


@pytest.mark.parametrize('nested',[False,True])
@pytest.mark.parametrize('damage',['foreign_caller','stale_cfg','missing_cfg_proof','foreign_cfg_proof',
    'cfg_source_hash','cfg_source_path','cfg_source_range','site_source_path','site_source_hash',
    'site_source_range','block_source_path','block_source_hash','block_source_range','outside_body'])
def test_process_expansion_is_owned_by_current_caller_cfg_and_occurrence(nested,damage):
    from dataclasses import replace
    graph=nested_process_graph() if nested else process_graph()
    positive=flow.build_report(graph,'method',view='process')
    assert {e['call_site'] for e in positive['cfg']['edges'] if e['kind']=='call'} == ({'site','nested-site'} if nested else {'site'})
    cfg=graph.cfgs[1 if nested else 0];site=graph.call_sites[1 if nested else 0]
    block=next(b for b in cfg['blocks'] if b.get('call_site_ids')==[site['id']])
    proof=next(p for p in graph.evidence if p['id']==cfg['evidence_ids'][0])
    if damage=='foreign_caller':
        graph.nodes.append(Node('foreign','method','foreign',SOURCE,scope='production',role='executable_code'))
        graph.symbols.append({'id':'foreign','context_id':'ctx'})
        site['caller']='foreign'
        graph.edges=[replace(e,source='foreign') if e.kind=='declares_call' and e.target==site['id'] else e for e in graph.edges]
    elif damage=='stale_cfg': proof['freshness']='STALE'
    elif damage=='missing_cfg_proof': cfg['evidence_ids']=[]
    elif damage=='foreign_cfg_proof': proof['source']=proof['target']='method' if nested else 'callee'
    elif damage=='cfg_source_hash': proof['sha256']='a'*64
    elif damage=='cfg_source_path': proof['source_file']='elsewhere.java'
    elif damage=='cfg_source_range': proof.pop('source_range')
    elif damage=='site_source_path': site['path']='elsewhere.java'
    elif damage=='site_source_hash': site['sha256']='a'*64
    elif damage=='site_source_range': site['range']={**site['range'],'end':site['range']['end']+1}
    elif damage=='block_source_path': block['source_file']='elsewhere.java'
    elif damage=='block_source_hash': block['sha256']='a'*64
    elif damage=='block_source_range': block['source_range']={**block['source_range'],'end':block['source_range']['end']+1}
    else:
        site['range']=block['source_range']={'start':1000,'end':1001,'start_line':100}
    graph=KnowledgeGraph.from_dict(graph.to_dict());before=copy.deepcopy(graph.to_dict())
    report=flow.build_report(graph,'method',view='process')
    assert not any(e.get('call_site')==site['id'] and e['kind'] in {'call','returns_to'} for e in report['cfg']['edges'])
    assert not any(b.get('method')==site['declared_target'] for b in report['cfg']['blocks'])
    assert report['boundaries'] and report['status'] in {'UNKNOWN','PARTIAL'}
    # A rejected nested body may remain outside the expanded path. Otherwise
    # retain the original caller block and local normal successor, not a rewired call.
    retained=[b for b in report['cfg']['blocks'] if block['id'] in b.get('original_ids',[]) and b.get('method')==cfg['method']]
    if retained:
        boundary=retained[0]
        assert boundary['boundary_reason'] and site['id'] in boundary['original_ids']
        if damage in {'foreign_caller','site_source_path','site_source_hash','site_source_range',
                      'block_source_path','block_source_hash','block_source_range','outside_body'}:
            assert 'argument_parameter_bindings' not in boundary
        else:
            assert boundary['binding_projection']=='REFERENCE_ONLY'
            assert boundary['argument_binding_status']['execution']=='NOT_OBSERVED'
        expected={e['target'] for e in cfg['edges'] if e['source']==block['id']}
        actual={original for e in report['cfg']['edges'] if e['source']==boundary['id']
                for b in report['cfg']['blocks'] if b['id']==e['target'] for original in b.get('original_ids',[])}
        assert expected <= actual
    if damage=='stale_cfg' and not nested:
        assert report['status']=='UNKNOWN'
        assert any(g['code']=='STALE_EVIDENCE' for g in report['coverage']['gaps'])
    for fmt in ('json','markdown','mermaid'):
        assert report['status'] in flow.render(report,fmt)
    assert graph.to_dict()==before


@pytest.mark.parametrize('damage',['context_scope','symbol_scope','symbol_context','symbol_path','symbol_hash','site_scope'])
def test_caller_cfg_declared_context_scope_and_source_identity_are_consistent(damage):
    graph=process_graph()
    assert any(e['kind']=='call' for e in flow.build_report(graph,'method',view='process')['cfg']['edges'])
    symbol=next(s for s in graph.symbols if s['id']=='method')
    if damage=='context_scope': graph.contexts[0]['scope']='test'
    elif damage=='symbol_scope': symbol['scope']='test'
    elif damage=='symbol_context':
        graph.contexts.append({**copy.deepcopy(graph.contexts[0]),'id':'other'})
        symbol['context_id']='other'
    elif damage=='symbol_path': symbol['path']='elsewhere.java'
    elif damage=='symbol_hash': symbol['sha256']='a'*64
    else: graph.call_sites[0]['scope']='test'
    graph=KnowledgeGraph.from_dict(graph.to_dict());before=copy.deepcopy(graph.to_dict())
    report=flow.build_report(graph,'method',view='process',scope='all',context_id='ctx')
    assert not any(e['kind']=='call' for e in report['cfg']['edges'])
    assert not any(b.get('method')=='callee' for b in report['cfg']['blocks'])
    assert report['status'] in {'UNKNOWN','PARTIAL'}
    assert graph.to_dict()==before

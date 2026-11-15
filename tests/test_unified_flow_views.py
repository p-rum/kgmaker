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
    return KnowledgeGraph.from_dict(graph.to_dict())


@pytest.mark.parametrize('damage',[None,'reference','stale','source_only','missing_edge','missing_cfg','callee_cfg_stale','context_stale'])
def test_process_expansion_requires_current_executable_authority(damage):
    graph=process_graph()
    if damage=='reference': graph.call_sites[0]['invocation_kind']='METHOD_REFERENCE'
    elif damage=='stale': graph.evidence[-1]['freshness']='STALE'
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

"""Actual Javac21 + TS5.7.3/React capture, separate source-only template/PDF.

The explicit impact artifact covers multiple contexts. Feature packets continue
selecting one context; they do not adopt artifact IDs as feature impact proofs.
"""
import copy
from dataclasses import asdict
import json
import subprocess
from unittest.mock import patch

import pytest

from kgmaker import feature
from kgmaker.analysis_model import inventory_candidate, write_json
from kgmaker.dataflow import impact_paths
from kgmaker.workspace import qualified, snapshot_workspace, source_key
from test_backend_frontend_value_flow import capture_workspace, consumers, path_between
from test_complete_analysis_report import cli, files, item
from test_templates import fixture as template_fixture


@pytest.fixture(scope='module')
def captured_report(tmp_path_factory):
    root,origin=capture_workspace(tmp_path_factory.mktemp('complete-report'))
    reports=root/'reports';reports.mkdir()
    subprocess.run(['git','init','-q',str(reports)],check=True)
    template_fixture(reports)
    # Known binary-XLS signature: deterministic unsupported-tool coverage,
    # never a claim that the business value is absent.
    (reports/'legacy.xls').write_bytes(bytes.fromhex('d0cf11e0a1b11ae1')+b'\x00'*64)
    manifest=json.loads((root/'workspace.json').read_text())
    manifest['repositories'].append({'id':'reports','role':'backend','path':'reports'})
    write_json(root/'workspace.json',manifest)
    baseline,coverage,sources,graph,_=snapshot_workspace(root/'workspace.json')
    start=qualified('backend',origin['id'])
    targets=consumers(graph,'frontend','JSX_CONSUMER')+consumers(graph,'tests','ARGUMENT')
    routes=[path_between(graph,start,target['id']) for target in targets]
    assert len(routes)==2 and all(routes)
    artifact={'schema_version':1,'kind':'EXPLICIT_DERIVED_IMPACT_ARTIFACT',
        'producer':'snapshot_workspace + dataflow.impact_paths', 'baseline':baseline,
        'source_manifest':sources, 'contexts':graph.contexts, 'evidence':graph.evidence,
        'impact':impact_paths(graph,start), 'routes':[[asdict(edge) for edge in route] for route in routes],
        'execution':'NOT_OBSERVED','availability':'UNKNOWN'}
    (reports/'evidence').mkdir();write_json(reports/'evidence/befe.json',artifact)
    (root/'requirement.md').write_text('Display exposure decline and issue a PDF; define the monetary unit.')
    ctx=next(c['id'] for c in graph.contexts if c.get('repo_id')=='frontend' and c.get('analyzer_version'))
    packet=feature.prepare(root,'requirement.md','report',2_000_000,
                           workspace=root/'workspace.json',context_id=ctx)
    return root,packet,artifact,start,targets


def citation(root,packet,identity,repo,path, *, pointer=None,value=None):
    source=root/repo/path
    # Use the manifest key instead of assuming path normalization.
    meta=next(m for m in packet['source_manifest'].values() if m.get('repo_id')==repo and m.get('path')==path)
    if pointer is None:
        location={'type':'lines','start':1,'end':len(source.read_text().splitlines())}
        extra={'quote':source.read_text().strip()}
    else:
        location={'type':'json_pointer','pointer':pointer};extra={'value':value}
    return {'id':'analysis:report:evidence:'+str(len(identity))+repo+path.replace('/','_'),
        'source_id':identity,'repo_id':repo,'path':path,'sha256':meta['sha256'],
        'kind':meta['kind'],'location':location,**extra,'supports':'Exact supplied source; no runtime/data assertion.',
        'method':'EXTRACTED','confidence':1,'validity':'VALID'}


def candidate_for(root,packet,artifact):
    candidate=inventory_candidate(packet);req=candidate['requirements'][0]['id']
    selected=feature.graph_for_packet(root,packet)
    frontend=next(n for n in selected.nodes if n.kind=='value_occurrence' and
        n.metadata.get('value_role')=='JSX_CONSUMER')
    fe=citation(root,packet,frontend.id,'frontend','src/page.tsx')
    artifact_id=next(n.id for n in selected.nodes if n.path==source_key('reports','evidence/befe.json') and n.kind=='file')
    artifact_evidence=citation(root,packet,artifact_id,'reports','evidence/befe.json',
                               pointer='/impact',value=artifact['impact'])
    report_method=next(n for n in selected.nodes if n.name=='report' and n.kind=='function')
    template=next(n for n in selected.nodes if n.kind=='template')
    pdf=next(n for n in selected.nodes if n.id==qualified('reports','external_service:pdf-renderer'))
    request=next(n for n in selected.nodes if n.kind=='value_occurrence' and
                 n.metadata.get('value_role')=='HTTP_RESPONSE')
    route=next(p for p in impact_paths(selected,request.id)['paths'] if p['entity_ids'][-1]==frontend.id)
    evidence=[fe,artifact_evidence]
    for source in sorted({report_method.path,template.path}):
        meta=packet['source_manifest'][source]
        node=next(n for n in selected.nodes if n.path==source and n.line)
        evidence.append(citation(root,packet,node.id,meta['repo_id'],meta['path']))
    candidate['evidence']=evidence
    candidate['impact_paths']=[{'id':'analysis:report:path:local-ui',**route,'evidence_ids':[fe['id']]}]
    candidate['capability_matches']=[{'id':'analysis:report:capability:template-pdf',
        'entity_ids':[report_method.id,template.id,pdf.id],'requirement_ids':[req],
        'evidence_ids':[e['id'] for e in evidence[2:]],'state':'AS_IS','method':'INFERRED','validity':'VALID',
        'rationale':'Literal model/template and external PDF boundary exist in the selected source inventory.',
        'limitations':'SOURCE_ONLY syntax candidates; template edges are outside feature impact traversal. No rendering or compiler BEFE join.'}]
    candidate['input_requirements']=[item(candidate,'decline',acquisition='EXISTING',
        source_ids=[frontend.id],evidence_ids=[fe['id']],definition='Exposure decline; monetary unit unresolved.'),
        item(candidate,'pdf',acquisition='EXTERNAL',definition='External PDF renderer capability; output unobserved.')]
    candidate['questions']=[{'id':'analysis:report:question:'+kind.lower(),'text':text,'owner_role':owner,
        'status':'OPEN','blocking':True,'blocker_kind':kind,'requirement_ids':[req]}
        for kind,text,owner in [('BUSINESS','Define the monetary unit and approve reporting policy.','Business owner'),
            ('TOOL','Feature impact paths select one compiler context and do not traverse template/PDF relations; BEFE is a separately cited multi-context artifact.','Tool maintainer')]]
    candidate['changes']=[{'id':'analysis:report:change:format','repo_id':'frontend','requirement_ids':[req],
        'entity_ids':[frontend.id],'dependency_ids':[],'layer':'UI','reason':'Apply approved formatting after unit decision.',
        'inputs':'Exposure decline','outputs':'Formatted display','test_impact':'Check selected currency and null policy.','state':'TO_BE'}]
    candidate['acceptance_criteria']=[{'id':'analysis:report:ac:display','text':'Display approved currency and explicit missing value.', 'requirement_ids':[req]}]
    candidate['test_plan']=[{'id':'analysis:report:test:display','text':'Exercise approved formatting; PDF output test requires external renderer.',
        'requirement_ids':[req],'state':'TO_BE','entity_ids':[frontend.id],'evidence_ids':[fe['id']]}]
    return candidate


def test_actual_cross_layer_report_retains_separate_evidence_and_both_blockers(captured_report):
    root,packet,artifact,start,targets=captured_report
    candidate=candidate_for(root,packet,artifact)
    # These exact full-workspace IDs were captured by real workers, not model fixtures.
    for target,route in zip(targets,artifact['routes']):
        assert route[0]['source']==start and route[-1]['target']==target['id']
        assert all(e['evidence_ids'] and e['context_ids'] for e in route)
        assert all(e['evidence_kind'] in {'SYMBOL_RESOLVED','FRAMEWORK_DERIVED'} for e in route)
    assert artifact['impact']['frontend_value_bindings']
    selected=feature.graph_for_packet(root,packet)
    assert not path_between(selected,start,targets[0]['id'])
    before=files(root)
    run=subprocess.Popen
    def git_only(argv,*a,**kw):
        assert isinstance(argv,list) and argv[0]=='git',argv
        return run(argv,*a,**kw)
    with patch('subprocess.Popen',git_only),patch('socket.socket',side_effect=AssertionError('network')):
        applied=feature.apply(root,'report',candidate);assert applied['valid'],applied
        assert cli(root,'report','--analysis','report','--format','json')[0]==0
        assert cli(root,'report','--analysis','report')[0]==0
    result=json.loads((root/'docs/generated/features/report.json').read_text())
    projection=result['report_projection']
    assert projection['status']=='PARTIAL' and projection['graph_selection']==packet['graph_selection']
    assert {'BUSINESS','TOOL'} <= {b['kind'] for b in projection['blockers']}
    assert any('BINARY_XLS_UNSUPPORTED' in json.dumps(b) for b in projection['blockers'])
    assert projection['inputs'][0]['facets']==['Required','Existing','Unresolved']
    assert all(i['availability']=='UNKNOWN' for i in projection['inputs'])
    assert projection['impact_paths']==candidate['impact_paths']
    assert len(projection['impact_paths'])==1 and start not in projection['impact_paths'][0]['entity_ids']
    assert projection['impact_paths'][0]['entity_ids'][-1]==targets[0]['id']
    assert result['analysis']['capability_matches']==candidate['capability_matches']
    template_edges=[e for e in selected.edges if e.kind in {'renders_template','rendered_by'}]
    assert len(template_edges)==2 and all(e.evidence_kind=='SYNTAX_CANDIDATE' for e in template_edges)
    template_edges.sort(key=lambda e:e.kind=='rendered_by')
    assert template_edges[0].target==template_edges[1].source
    assert template_edges[-1].target==qualified('reports','external_service:pdf-renderer')
    assert next(e['value'] for e in projection['evidence'] if e.get('path')=='evidence/befe.json')==artifact['impact']
    assert projection['delivery_plan'][0]['change_ids']==['analysis:report:change:format']
    assert projection['delivery_plan'][0]['test_ids']==['analysis:report:test:display']
    # Analysis receipt/report publication is allowed; captured source/compiler stores stay byte-identical.
    after=files(root)
    assert all(after[p]==raw for p,raw in before.items())


def test_actual_foreign_path_and_artifact_drift_never_become_feature_proof(captured_report):
    root,packet,artifact,start,targets=captured_report
    candidate=candidate_for(root,packet,artifact)
    foreign=next(p for p in artifact['impact']['paths'] if p['entity_ids'][-1]==targets[0]['id'])
    bad=copy.deepcopy(candidate)
    bad['impact_paths'].append({'id':'analysis:report:path:forged',**foreign,'evidence_ids':[e['id'] for e in bad['evidence']]})
    before=files(root)
    assert feature.apply(root,'report',bad)['exit_code']==2
    assert files(root)==before
    # Captured artifact is evidence of supplied bytes; changing it invalidates the packet.
    path=root/'reports/evidence/befe.json';raw=path.read_bytes()
    try:
        path.write_bytes(raw+b'\n')
        assert feature.validate(root,'report',candidate)['exit_code']==3
    finally:path.write_bytes(raw)
    assert feature.validate(root,'report',candidate)['valid']


@pytest.mark.parametrize('name',['workspace.json','frontend/.kgmaker/graph.json','reports/evidence/befe.json'])
def test_actual_late_workspace_context_or_artifact_change_preserves_report(captured_report,name):
    root,packet,artifact,_,_=captured_report
    candidate=candidate_for(root,packet,artifact)
    assert feature.apply(root,'report',candidate)['valid']
    assert cli(root,'report','--analysis','report')[0]==0
    target=root/'docs/generated/features/report.md';previous=target.read_bytes()
    path=root/name;raw=path.read_bytes()
    from kgmaker import feature_cli
    render=feature_cli.render_report
    def change(*args,**kwargs):
        result=render(*args,**kwargs)
        if name.endswith('graph.json'):
            graph=json.loads(raw)
            # Change actual compiler context provenance, not formatting ignored by graph hashing.
            graph['contexts'][0]['status']='changed-during-report'
            path.write_text(json.dumps(graph))
        else:path.write_bytes(raw+b'\n')
        return result
    try:
        with patch.object(feature_cli,'render_report',change):
            assert cli(root,'report','--analysis','report')[0]==3
        assert target.read_bytes()==previous
    finally:path.write_bytes(raw)
    assert feature.validate(root,'report',candidate)['valid']

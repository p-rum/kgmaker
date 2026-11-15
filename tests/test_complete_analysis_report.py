"""S09-W05 public report dimensions, truthful trace gaps and atomic publication."""
import copy
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest

from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA, inventory_candidate, write_json
from kgmaker.cli import main


@pytest.fixture
def analysis(tmp_path):
    (tmp_path/'service.ts').write_text('export function balance() { return 10; }\n')
    (tmp_path/'requirement.md').write_text('Display balance and issue a PDF.')
    packet = feature.prepare(tmp_path, 'requirement.md', 'report', 100000)
    return tmp_path, packet, inventory_candidate(packet)


def item(candidate, name='balance', **updates):
    return {'id': f'analysis:report:input:{name}', 'name': name,
        **{key: None for key in INPUT_METADATA},
        'requirement_ids': [candidate['requirements'][0]['id']], 'availability': 'UNKNOWN',
        'acquisition': 'UNRESOLVED', 'usability': 'UNASSESSED',
        'verification_scope': 'Supplied local sources only; no populated data.',
        'next_step': 'Resolve source and define scope.', 'owner_role': 'Analyst',
        'transformation': None, 'evidence_ids': [], 'source_ids': [], 'dependency_ids': [],
        'question_ids': [], **updates}


def cli(root, *args):
    output = io.StringIO()
    with patch('sys.argv', ['kgmaker','feature',*args,'--root',str(root)]), redirect_stdout(output):
        with pytest.raises(SystemExit) as result:
            main()
    return result.value.code, json.loads(output.getvalue())


def files(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def project(candidate, packet, stale=()):
    from kgmaker.analysis_report import report_projection
    return report_projection(candidate, packet, list(stale))


def test_independent_dimensions_preserve_unknown_and_declarations(analysis):
    root, packet, candidate = analysis
    candidate['input_requirements'] = [item(candidate, acquisition='EXTERNAL'),
        item(candidate,'derived',acquisition='DERIVED',transformation='balance * 2',
             dependency_ids=['analysis:report:input:balance']),
        item(candidate,'existing',acquisition='EXISTING')]
    assert feature.validate(root,'report',candidate)['valid']
    before = copy.deepcopy((candidate,packet))
    result = project(candidate,packet)
    rows = {r['id']:r for r in result['inputs']}
    assert result['schema_version'] == 1
    assert rows['analysis:report:input:balance']['facets'] == ['Required','External','Unresolved']
    assert rows['analysis:report:input:derived']['facets'] == ['Required','Derived','Unresolved']
    # Acquisition is an agent declaration, not proof that a source exists.
    assert 'Existing' not in rows['analysis:report:input:existing']['facets']
    assert all('Missing' not in r['facets'] and r['availability']=='UNKNOWN' for r in rows.values())
    assert (candidate,packet) == before
    assert result['status'] == 'PARTIAL'


def test_explicit_blocker_type_and_legacy_unknown(analysis):
    root, packet, candidate = analysis
    req = candidate['requirements'][0]['id']
    candidate['questions'] = [{'id':f'analysis:report:question:{name}','text':text,
        'owner_role':'Owner','status':'OPEN','blocking':True,'requirement_ids':[req],**extra}
        for name,text,extra in [('business','Approve the definition',{'blocker_kind':'BUSINESS'}),
                               ('tool','Missing parser',{'blocker_kind':'TOOL'}),
                               ('old','A business-looking legacy text',{})]]
    assert feature.validate(root,'report',candidate)['valid']
    p = project(candidate,packet)
    assert [r['kind'] for r in p['blockers'] if r['origin']=='QUESTION'] == ['BUSINESS','TOOL','UNCLASSIFIED']
    for value in ['business','MISSING',None,True,{}]:
        bad=copy.deepcopy(candidate);bad['questions'][0]['blocker_kind']=value
        before=files(root)
        assert feature.apply(root,'report',bad)['exit_code']==2
        assert files(root)==before


def test_delivery_trace_uses_only_explicit_requirement_links(analysis):
    _, packet, candidate = analysis
    req=candidate['requirements'][0]['id']
    candidate['input_requirements']=[item(candidate)]
    candidate['acceptance_criteria']=[{'id':'analysis:report:ac:display','text':'Display balance','requirement_ids':[req]}]
    candidate['test_plan']=[{'id':'analysis:report:test:display','text':'Assert displayed balance','requirement_ids':[req],
                            'state':'TO_BE','entity_ids':[],'evidence_ids':[]}]
    result=project(candidate,packet);row=result['delivery_plan'][0]
    assert row['requirement_id']==req
    assert row['input_ids']==['analysis:report:input:balance']
    assert row['acceptance_ids']==['analysis:report:ac:display']
    assert row['test_ids']==['analysis:report:test:display']
    assert row['association']=='DECLARED_REQUIREMENT_IDS' and row['execution_status']=='NOT_RUN'
    assert row['gaps'] == ['REQUIREMENT_UNRESOLVED']
    candidate['test_plan']=[]
    assert 'TEST_PLAN_MISSING' in project(candidate,packet)['delivery_plan'][0]['gaps']


def test_missing_is_current_proof_only_not_search_absence(analysis):
    _, packet, candidate=analysis
    candidate['input_requirements']=[item(candidate,availability='NOT_FOUND_IN_SCOPE'),
        item(candidate,'missing',availability='CONFIRMED_MISSING',availability_proof={'kind':'APPROVED_MISSING'}),
        item(candidate,'static',availability='UNKNOWN',acquisition='EXISTING',source_ids=['source'],evidence_ids=['e'])]
    candidate['evidence']=[{'id':'e','source_id':'source','kind':'CODE','validity':'VALID','method':'EXTRACTED'}]
    packet['evidence_inventory']=[{'graph_id':'source'}]
    p=project(candidate,packet)
    assert 'Missing' not in p['inputs'][0]['facets']
    assert 'Missing' in p['inputs'][1]['facets']
    assert p['inputs'][2]['facets']==['Required','Existing','Unresolved']
    stale=project(candidate,packet,['Source changed'])
    assert all(r['availability']=='UNKNOWN' and 'Missing' not in r['facets'] and 'Existing' not in r['facets'] for r in stale['inputs'])
    assert stale['inputs'][1]['historical_availability']=='CONFIRMED_MISSING'


def test_json_and_markdown_share_projection_without_input_mutation(analysis):
    root,packet,candidate=analysis
    candidate['input_requirements']=[item(candidate,acquisition='EXTERNAL')]
    assert feature.apply(root,'report',candidate)['valid']
    before=files(root)
    assert cli(root,'report','--analysis','report','--format','json')[0]==0
    payload=json.loads((root/'docs/generated/features/report.json').read_text())
    assert payload['report_projection']==project(candidate,packet)
    assert payload['analysis']==candidate
    assert cli(root,'report','--analysis','report')[0]==0
    text=(root/'docs/generated/features/report.md').read_text()
    assert 'Required / Existing / Missing / Derived / External / Unresolved' in text
    assert 'DECLARED_REQUIREMENT_IDS' in text and 'NOT_RUN' in text
    assert all(files(root)[path]==raw for path,raw in before.items())


@pytest.mark.parametrize('mutation',['source','packet','analysis','receipt','already_stale'])
def test_late_input_drift_preserves_last_report(analysis,mutation):
    root,packet,candidate=analysis
    assert feature.apply(root,'report',candidate)['valid']
    assert cli(root,'report','--analysis','report')[0]==0
    target=root/'docs/generated/features/report.md'; previous=target.read_bytes()
    if mutation=='already_stale':(root/'service.ts').write_text('export const changed=1;')
    from kgmaker import feature_cli
    render=feature_cli.render_report
    def changing(*args,**kwargs):
        text=render(*args,**kwargs)
        path={'source':root/'service.ts','already_stale':root/'service.ts',
              'packet':root/'.kgmaker/analyses/report/packet.json',
              'analysis':root/'.kgmaker/analyses/report/analysis.json',
              'receipt':root/'.kgmaker/analyses/report/receipts/1.json'}[mutation]
        path.write_bytes(path.read_bytes()+b'\n')
        return text
    with patch.object(feature_cli,'render_report',changing):
        code,result=cli(root,'report','--analysis','report')
    assert code==3,result
    assert 'changed' in result['error'].lower()
    assert target.read_bytes()==previous
    assert not list(target.parent.glob('.*.tmp'))


@pytest.mark.parametrize('error',[TimeoutError,KeyboardInterrupt])
def test_late_abort_preserves_inputs_and_last_generation(analysis,error):
    root,packet,candidate=analysis
    assert feature.apply(root,'report',candidate)['valid']
    assert cli(root,'report','--analysis','report')[0]==0
    before=files(root)
    from kgmaker import feature_cli
    atomic=feature_cli.atomic_write
    def abort(target,text,*,before_replace):
        def fail():
            before_replace()
            raise error('cancelled')
        return atomic(target,text,before_replace=fail)
    with patch.object(feature_cli,'atomic_write',abort):
        if error is KeyboardInterrupt:
            with pytest.raises(KeyboardInterrupt):cli(root,'report','--analysis','report')
        else:assert cli(root,'report','--analysis','report')[0]==1
    assert files(root)==before


def test_scoped_missing_proof_is_validated_and_stale_report_retracts_it(analysis):
    root,_,_=analysis
    contract={'type':'object','additionalProperties':False,'properties':{'balance':{'type':'number'}}}
    write_json(root/'contract.json',contract)
    packet=feature.prepare(root,'requirement.md','report',100000)
    candidate=inventory_candidate(packet)
    evidence={'id':'analysis:report:evidence:contract','source_id':'file:contract.json',
        'kind':'CONTRACT','path':'contract.json','sha256':packet['source_manifest']['contract.json']['sha256'],
        'location':{'type':'json_pointer','pointer':''},'value':contract,'supports':'Closed contract only',
        'method':'EXTRACTED','confidence':1,'validity':'VALID'}
    candidate['evidence']=[evidence]
    candidate['input_requirements']=[item(candidate,'maturity',acquisition='EXTERNAL',
        availability='CONFIRMED_MISSING',usability='INCOMPATIBLE',
        verification_scope='Only contract ./contract.json#',evidence_ids=[evidence['id']],
        availability_proof={'kind':'CLOSED_CONTRACT_ABSENCE','evidence_id':evidence['id'],'field':'maturity'})]
    applied=feature.apply(root,'report',candidate)
    assert applied['valid'],applied
    assert cli(root,'report','--analysis','report','--format','json')[0]==0
    output=root/'docs/generated/features/report.json'
    row=json.loads(output.read_text())['report_projection']['inputs'][0]
    assert row['facets']==['Required','Missing','External','Unresolved']
    (root/'contract.json').write_text('{}')
    assert cli(root,'report','--analysis','report','--format','json')[0]==3
    row=json.loads(output.read_text())['report_projection']['inputs'][0]
    assert 'Missing' not in row['facets'] and row['availability']=='UNKNOWN'
    assert row['historical_availability']=='CONFIRMED_MISSING'


@pytest.mark.parametrize('method,kind',[('AMBIGUOUS','CODE'),('INFERRED','CODE'),('EXTRACTED','DOCUMENTATION')])
def test_uncertain_or_documentary_evidence_is_not_existing_value_source(analysis,method,kind):
    root,packet,candidate=analysis
    source=next(e['graph_id'] for e in packet['evidence_inventory'] if e['path']=='service.ts')
    candidate['evidence']=[{'id':'analysis:report:evidence:source','source_id':source,
        'kind':kind,'path':'service.ts','sha256':packet['source_manifest']['service.ts']['sha256'],
        'location':{'type':'lines','start':1,'end':1},'quote':'export function balance() { return 10; }',
        'supports':'Candidate only','method':method,'confidence':0.2,'validity':'VALID'}]
    candidate['input_requirements']=[item(candidate,acquisition='EXISTING',source_ids=[source],
                                        evidence_ids=[candidate['evidence'][0]['id']])]
    # DOCUMENTATION over a code file is rejected by the normal evidence validator.
    if kind=='DOCUMENTATION':assert not feature.validate(root,'report',candidate)['valid']
    else:assert feature.validate(root,'report',candidate)['valid']
    assert 'Existing' not in project(candidate,packet)['inputs'][0]['facets']


def test_observation_expiring_during_render_preserves_last_generation(analysis):
    root,_,candidate=analysis
    assert feature.apply(root,'report',candidate)['valid']
    assert cli(root,'report','--analysis','report')[0]==0
    before=files(root)
    # Wall-clock freshness may change although all source bytes remain identical.
    with patch('kgmaker.availability.observation_staleness',side_effect=[[],['observation expired']]):
        code,result=cli(root,'report','--analysis','report')
    assert code==3 and 'freshness changed' in result['error']
    assert files(root)==before


@pytest.mark.parametrize('version',[1,2,3])
def test_report_reads_legacy_graph_store_without_rewriting_it(analysis,version):
    root,_,_=analysis
    from kgmaker.scanner import scan_repository
    from kgmaker.model import KnowledgeGraph
    graph=scan_repository(root).to_dict();graph['schema_version']=version
    stored=KnowledgeGraph.from_dict(graph).to_dict()
    store=root/'.kgmaker/graph.json';write_json(store,stored)
    packet=feature.prepare(root,'requirement.md','report',100000)
    candidate=inventory_candidate(packet)
    assert feature.apply(root,'report',candidate)['valid']
    before=files(root)
    assert cli(root,'report','--analysis','report','--format','json')[0]==0
    assert all(files(root)[p]==raw for p,raw in before.items())
    report=json.loads((root/'docs/generated/features/report.json').read_text())
    assert report['report_projection']['status']=='PARTIAL'
    assert report['analysis']['schema_version']==1

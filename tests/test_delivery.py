"""T046: behavioural tests for proposals, evidence, gates and traceability."""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker import provenance as p, testgen as t, workflow as w
from kgmaker.analysis_model import AnalysisError, digest, write_json
from kgmaker.cli import build_parser


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 2\n')
        (self.root/'tests').mkdir()
        (self.root/'tests/test_existing.py').write_text('import unittest\n')

    def tree(self):
        return {str(x.relative_to(self.root)):x.read_bytes() for x in self.root.rglob('*') if x.is_file()}

    def prepare(self):
        return t.prepare(self.root,'double','calculator.py',scope='all')

    def candidate(self,packet):
        c={'path':'calculator.py','sha256':packet['source_manifest']['calculator.py']['sha256'],
           'start':1,'end':2,'quote':'return value * 2'}
        dataset={'id':'numbers','purpose':'Positive, negative and zero inputs',
                 'schema':{'type':'array','items':{'type':'object','required':['input','expected'],
                    'properties':{'input':{'type':'integer'},'expected':{'type':'integer'}}}},
                 'data':[{'input':2,'expected':4},{'input':0,'expected':0},{'input':-2,'expected':-4}],
                 'negative':False,'expected_violations':[],'citations':[c],'foreign_keys':[]}
        case={'id':'double-values','title':'Double values','target_ids':[packet['target']['id']],
              'requirement_refs':[],'category':'characterization','preconditions':'Calculator is importable',
              'steps':['Call double for every input'],
              'expected':{'text':'Return twice the input','basis':'CODE_CHARACTERIZATION','citations':[c]},
              'dataset_ids':['numbers']}
        content='''import json
import pathlib
import unittest
from calculator import double
class GeneratedTest(unittest.TestCase):
    def test_double(self):
        rows=json.loads((pathlib.Path(__file__).parent/'fixtures/kgmaker/double_numbers.json').read_text())
        for row in rows:
            self.assertEqual(row['expected'],double(row['input']))
'''
        return {'schema_version':1,'suite_id':'double','packet_id':packet['packet_id'],
                'cases':[case],'datasets':[dataset],
                'files':[{'path':'tests/test_generated.py','content':content,'case_ids':['double-values']}],
                'questions':[]}

    def test_end_to_end_test_is_sensitive_to_behaviour(self):
        packet=self.prepare();candidate=self.candidate(packet)
        self.assertTrue(t.validate(self.root,'double',candidate)['valid'])
        applied=t.apply(self.root,'double',candidate)
        self.assertEqual(applied,t.apply(self.root,'double',candidate))
        exported=t.export(self.root,'double')
        self.assertEqual('NOT_RUN',exported['execution'])
        run=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_generated.py'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(0,run.returncode,run.stderr)
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 3\n')
        run=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_generated.py'],cwd=self.root,capture_output=True,text=True)
        self.assertNotEqual(0,run.returncode)
        self.assertTrue(t.report(self.root,'double')['stale'])

    def test_invalid_and_stale_candidates_do_not_mutate(self):
        packet=self.prepare();candidate=self.candidate(packet)
        before=self.tree()
        candidate['cases'][0]['expected']['citations'][0]['sha256']='0'*64
        with self.assertRaises(AnalysisError):t.apply(self.root,'double',candidate)
        self.assertEqual(before,self.tree())
        candidate=self.candidate(packet)
        candidate['datasets'][0]['data'][0]['input']='not a number'
        with self.assertRaises(AnalysisError):t.apply(self.root,'double',candidate)
        self.assertEqual(before,self.tree())
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 3\n')
        before=self.tree()
        with self.assertRaises(AnalysisError):t.apply(self.root,'double',self.candidate(packet))
        self.assertEqual(before,self.tree())

    def test_negative_dataset_and_foreign_keys(self):
        packet=self.prepare();candidate=self.candidate(packet)
        data=candidate['datasets'][0]
        data['data'][0]['input']='bad';data['negative']=True
        data['expected_violations']=['$[0].input:type']
        self.assertTrue(t.validate(self.root,'double',candidate)['valid'])
        data['expected_violations']=['$[1].input:type']
        with self.assertRaises(AnalysisError):t.validate(self.root,'double',candidate)
        data['data'][0]['input']=2;data['negative']=False;data['expected_violations']=[]
        data['foreign_keys']=[{'field':'input','dataset_id':'numbers','target_field':'expected'}]
        with self.assertRaises(AnalysisError):t.validate(self.root,'double',candidate)

    def test_export_collision_preflight(self):
        packet=self.prepare();candidate=self.candidate(packet);t.apply(self.root,'double',candidate)
        (self.root/'tests/test_generated.py').write_text('keep')
        before=self.tree()
        with self.assertRaises(AnalysisError):t.export(self.root,'double')
        self.assertEqual(before,self.tree())
        self.assertFalse((self.root/'tests/fixtures').exists())

    def test_framework_unknown_and_ambiguous(self):
        (self.root/'tests/test_existing.py').unlink()
        packet=self.prepare();self.assertIsNone(packet['framework'])
        candidate=self.candidate(packet)
        with self.assertRaises(AnalysisError):t.validate(self.root,'double',candidate)
        candidate['files']=[]
        self.assertEqual('BLOCKED',t.validate(self.root,'double',candidate)['code_status'])
        (self.root/'tests/test_existing.py').write_text('import unittest\nimport pytest\n')
        with self.assertRaisesRegex(AnalysisError,'Ambiguous'):self.prepare()
        self.assertEqual('unittest',t.prepare(self.root,'double','calculator.py',scope='all',framework='unittest')['framework'])

    def test_ambiguous_target_and_idempotent_prepare(self):
        packet=self.prepare();self.assertEqual(packet,self.prepare())
        (self.root/'other.py').write_text('def double(value):\n    return value * 2\n')
        with self.assertRaises(AnalysisError):t.prepare(self.root,'double','double',scope='all')
        with self.assertRaises(AnalysisError):t.prepare(self.root,'double','calculator.py',scope='all',expected_revision=0)



    def plan(self,task):
        return {'task_id':task['id'],'role':'architect','phase':'plan','iteration':task['iteration'],
          'summary':'Implement calculator','status':'completed','cited_paths':['calculator.py'],
          'cited_node_ids':[],'packet_id':None,'disposition':None,
          'steps':[{'id':'s1','intent':'Implement','paths':['calculator.py'],'tests':['tests/test_existing.py']}],
          'out_of_scope':[]}

    def test_optional_gates_work_at_api_and_save_boundaries(self):
        task=w.add_task(self.root,'Change calculator')
        for status in ('analyze','plan'):task=w.advance_task(self.root,task['id'],status)
        task=w.record_artifact(self.root,task['id'],'architect',self.plan(task))
        with p.transaction(self.root) as data:
            refs=p.sync_task(data,task);data['identity']={'id':'bob','kind':'human'}
            data['policy']['before_implement']=True
        before=self.tree()
        with self.assertRaises(w.WorkflowError):w.advance_task(self.root,task['id'],'implement')
        self.assertEqual(before,self.tree())
        forged=copy.deepcopy(task);forged['status']='implement'
        with self.assertRaises(w.WorkflowError):w.save_task(self.root,forged)
        with p.transaction(self.root) as data:
            for r in refs:
                if r['kind'] in {'requirement','plan'}:p.event(data,r['key'],'approved','Exact revision reviewed')
        self.assertEqual('implement',w.advance_task(self.root,task['id'],'implement')['status'])
        # Default policy preserves v1 workflow behaviour without requiring actors.
        other=w.add_task(self.root,'Other task')
        with p.transaction(self.root) as data:data['policy']['before_implement']=False
        for status in ('analyze','plan','implement'):other=w.advance_task(self.root,other['id'],status)
        self.assertEqual('implement',other['status'])

    def test_testgen_trace_references_and_cli_routing(self):
        packet=self.prepare();candidate=self.candidate(packet)
        req=p.register_file(self.root,'requirement','REQ','1','calculator.py')
        candidate['cases'][0]['requirement_refs']=[req]
        t.apply(self.root,'double',candidate);suite=p.sync_testgen(self.root,'double')
        forward=p.trace(self.root,req);backward=p.trace(self.root,suite)
        self.assertEqual({r['key'] for r in forward['references']},{r['key'] for r in backward['references']})
        self.assertIn('uses_dataset',{l['relation'] for l in forward['links']})
        self.assertIn('REQ',p.markdown(forward))
        args=build_parser().parse_args(['testgen','prepare','--id','x','--target','calculator.py','--workspace','workspace.json'])
        self.assertEqual('testgen',args.command)

    def test_completion_gate_binds_review_to_source_and_preserves_v1_identity(self):
        task=w.add_task(self.root,'Review calculator')
        original_id=task['id']
        for status in ('analyze','plan'):task=w.advance_task(self.root,task['id'],status)
        task=w.record_artifact(self.root,task['id'],'architect',self.plan(task))
        task=w.advance_task(self.root,task['id'],'implement')
        implementation={'task_id':task['id'],'role':'implementation','phase':'implement','iteration':0,
            'summary':'Changed calculator','status':'completed','cited_paths':['calculator.py'],
            'cited_node_ids':[],'packet_id':None,'disposition':None,
            'changed_paths':['calculator.py'],'notes':'Ready for review'}
        task=w.record_artifact(self.root,task['id'],'implementation',implementation)
        self.assertEqual(original_id,task['id']);self.assertEqual(2,task['schema_version'])
        for status in ('test','review'):task=w.advance_task(self.root,task['id'],status)
        review={'task_id':task['id'],'role':'review','phase':'review','iteration':0,
            'summary':'Calculator reviewed','status':'completed','cited_paths':['calculator.py'],
            'cited_node_ids':[],'packet_id':None,'disposition':None,'findings':[],'overall':'approve'}
        task=w.record_artifact(self.root,task['id'],'review',review)
        with p.transaction(self.root) as data:
            refs=p.sync_task(data,task);data['identity']={'id':'reviewer','kind':'human'}
            data['policy']['before_done']=True
            for ref in refs:
                if ref['kind'] in {'requirement','plan','review'}:p.event(data,ref['key'],'approved','Reviewed exact content')
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 3\n')
        before=self.tree()
        with self.assertRaisesRegex(w.WorkflowError,'stale'):w.advance_task(self.root,task['id'],'done')
        self.assertEqual(before,self.tree())
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 2\n')
        self.assertEqual('done',w.advance_task(self.root,task['id'],'done')['status'])


    def test_workspace_duplicate_entities_keep_repository_identity(self):
        top=self.root
        for repo in ('a','b'):
            folder=top/repo;folder.mkdir()
            (folder/'calculator.py').write_text('def double(value):\n    return value * 2\n')
            subprocess.run(['git','init','-q',str(folder)],check=True)
        coordinator=top/'coordinator';coordinator.mkdir()
        manifest=top/'workspace.json'
        write_json(manifest,{'schema_version':1,'workspace_id':'twins','repositories':[
            {'id':'a','role':'backend','path':'a'}, {'id':'b','role':'backend','path':'b'}]})
        with self.assertRaises(AnalysisError):t.prepare(coordinator,'twins','double',scope='all',workspace=manifest)
        packet=t.prepare(coordinator,'twins','@a/calculator.py',scope='all',workspace=manifest,framework='unittest')
        self.assertEqual('@a/calculator.py',packet['target']['path'])
        self.assertNotEqual('@b/calculator.py',packet['target']['path'])
        self.assertEqual(str(manifest),packet['workspace_manifest'])
        self.assertEqual([],list((top/'a/.git').glob('*.lock')))

    def test_no_implicit_commands_other_than_existing_git_metadata_reads(self):
        real=subprocess.run
        calls=[]
        def guarded(argv,*args,**kwargs):
            calls.append(argv)
            if argv[0]!='git':raise AssertionError('Unexpected execution: '+repr(argv))
            return real(argv,*args,**kwargs)
        with patch('subprocess.run',side_effect=guarded):
            packet=self.prepare();candidate=self.candidate(packet)
            t.validate(self.root,'double',candidate);t.apply(self.root,'double',candidate)
            t.report(self.root,'double');t.export(self.root,'double')
        self.assertTrue(calls)
        self.assertTrue(all(v[0]=='git' for v in calls))

    def test_export_uses_pinned_filename_template(self):
        from kgmaker.artifact_templates import install
        packet=self.prepare();candidate=self.candidate(packet)
        t.apply(self.root,'double',candidate)
        install(self.root)
        path=self.root/'.kgmaker/templates/filename.txt'
        path.write_text('changed_${id}_${slug}.${extension}')
        receipt=t.export(self.root,'double')
        self.assertIn('tests/fixtures/kgmaker/double_numbers.json',receipt['files'])
        self.assertFalse((self.root/'tests/fixtures/kgmaker/changed_double_numbers.json').exists())

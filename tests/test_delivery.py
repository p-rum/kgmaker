"""T046: behavioural tests for proposals, evidence, gates and traceability."""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
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

    def test_schema_valued_additional_properties_validate_and_apply(self):
        candidate = self.candidate(self.prepare())
        dataset = candidate['datasets'][0]
        schema = {'type': 'object', 'properties': {'input': {'type': 'integer'}},
                  'additionalProperties': {'type': 'integer', 'minimum': 1}}
        dataset.update(schema=schema, data={'input': 0, 'extra': 1})
        self.assertTrue(t.validate(self.root, 'double', candidate)['valid'])
        before = self.tree()
        for value, expected in (('bad', '$.extra:type'), (0, '$.extra:minimum')):
            dataset['data']['extra'] = value
            with self.subTest(value=value), self.assertRaises(AnalysisError) as error:
                t.apply(self.root, 'double', candidate)
            self.assertIn(expected, str(error.exception))
            self.assertEqual(self.tree(), before)
        dataset.update(negative=True, expected_violations=['$.extra:minimum'])
        self.assertTrue(t.validate(self.root, 'double', candidate)['valid'])

    def test_additional_properties_nested_unchecked_constraints(self):
        candidate = self.candidate(self.prepare())
        dataset = candidate['datasets'][0]
        dataset.update(schema={'type': 'object', 'additionalProperties': {
            'type': 'array', 'items': {'type': 'object', 'properties': {
                'name': {'type': 'string', 'pattern': '^a'},
                'count': {'type': 'integer', 'minimum': 1}}}}},
            data={'metrics.v2': [{'name': 'example', 'count': 1}]})
        result = t.validate(self.root, 'double', candidate)
        self.assertEqual(result['unchecked_constraints'], ['numbers:$["metrics.v2"][0].name:pattern'])
        self.assertEqual(result['execution'], 'NOT_RUN')
        dataset['data']['metrics.v2'][0]['count'] = 0
        with self.assertRaises(AnalysisError) as error:
            t.validate(self.root, 'double', candidate)
        self.assertIn('$["metrics.v2"][0].count:minimum', str(error.exception))

    def test_additional_properties_booleans_and_malformed_values(self):
        data = {'extra': 0}
        self.assertEqual(t.schema_errors(data, {'type': 'object'}), ([], []))
        self.assertEqual(t.schema_errors(data, {'type': 'object', 'additionalProperties': True}), ([], []))
        self.assertEqual(t.schema_errors(data, {'type': 'object', 'additionalProperties': False}),
                         (['$.extra:additionalProperties'], []))
        for malformed in (None, 1, 'integer', [], {}, {'type': ['integer']}):
            with self.subTest(malformed=malformed), self.assertRaisesRegex(AnalysisError, 'additionalProperties'):
                t.schema_errors({}, {'type': 'object', 'additionalProperties': malformed})

    def test_additional_properties_distinguish_literal_dotted_keys_from_nested_properties(self):
        child = {'type': 'object', 'properties': {'x.y': {'type': 'integer'},
                 'x': {'type': 'object', 'properties': {'y': {'type': 'integer'}}}}}
        schema = {'type': 'object', 'additionalProperties': child}
        literal = {'x.y': 'bad', 'x': {'y': 1}}
        nested = {'x.y': 1, 'x': {'y': 'bad'}}
        self.assertEqual(t.schema_errors({'extra': literal}, schema),
                         (['$.extra["x.y"]:type'], []))
        self.assertEqual(t.schema_errors({'extra': nested}, schema),
                         (['$.extra.x.y:type'], []))
        self.assertEqual(t.schema_errors(literal, child), (['$.x.y:type'], []))

    def test_additional_properties_retain_precise_prefix_through_legacy_parents(self):
        extra_map = {'type': 'object', 'additionalProperties': {'type': 'integer'}}
        array = {'type': 'array', 'items': extra_map}
        schema = {'type': 'object', 'properties': {'a.b': array,
                  'a': {'type': 'object', 'properties': {'b': array}}}}
        literal = {'a.b': [{'extra': 'bad'}], 'a': {'b': [{'extra': 1}]}}
        nested = {'a.b': [{'extra': 1}], 'a': {'b': [{'extra': 'bad'}]}}
        self.assertEqual(t.schema_errors(literal, schema), (['$["a.b"][0].extra:type'], []))
        self.assertEqual(t.schema_errors(nested, schema), (['$.a.b[0].extra:type'], []))

    def test_export_collision_preflight(self):
        packet=self.prepare();candidate=self.candidate(packet);t.apply(self.root,'double',candidate)
        (self.root/'tests/test_generated.py').write_text('keep')
        before=self.tree()
        with self.assertRaises(AnalysisError):t.export(self.root,'double')
        self.assertEqual(before,self.tree())
        self.assertFalse((self.root/'tests/fixtures').exists())

    def test_csv_export_preflights_collision_and_writes_valid_rows(self):
        packet=self.prepare();candidate=self.candidate(packet);t.apply(self.root,'double',candidate)
        collision=self.root/'tests/fixtures/kgmaker/double_numbers.csv'
        collision.parent.mkdir(parents=True);collision.write_text('keep\n')
        before=self.tree()
        with self.assertRaises(AnalysisError):t.export(self.root,'double',data_format='csv')
        self.assertEqual(before,self.tree())
        self.assertFalse((self.root/'tests/test_generated.py').exists())
        collision.unlink()
        receipt=t.export(self.root,'double',data_format='csv')
        self.assertIn('tests/fixtures/kgmaker/double_numbers.csv',receipt['files'])
        text=collision.read_text()
        self.assertEqual('expected,input',text.splitlines()[0])
        self.assertIn('4,2',text.splitlines()[1:])

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
        with self.assertRaises(AnalysisError):
            t.prepare(self.root,'double','calculator.py',scope='all',expected_revision=True)
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

    def test_reserved_export_paths_and_aliases_fail_without_mutation(self):
        packet = self.prepare()
        for path in ('./.github/new-workflow.yml', './.git/config', './.kgmaker/injected.json',
                     './/.github/workflow.yml', '.GitHub/workflow.yml', 'tests/.git/config'):
            candidate = self.candidate(packet)
            candidate['files'][0]['path'] = path
            before = self.tree()
            with self.subTest(path=path), self.assertRaises(AnalysisError):
                t.apply(self.root, 'double', candidate)
            self.assertEqual(before, self.tree())
        candidate = self.candidate(packet)
        duplicate = copy.deepcopy(candidate['files'][0])
        duplicate['path'] = './tests/test_generated.py'
        candidate['files'].append(duplicate)
        with self.assertRaises(AnalysisError):
            t.validate(self.root, 'double', candidate)
        t.apply(self.root, 'double', self.candidate(packet))
        before = self.tree()
        for data_dir in ('./.github', '.github', './.git', '.kgmaker', 'tests/.git',
                         'tests/fixtures/kgmaker/'):
            with self.subTest(data_dir=data_dir), self.assertRaises(AnalysisError):
                t.export(self.root, 'double', data_dir=data_dir)
            self.assertEqual(before, self.tree())

    def test_export_rolls_back_new_directories_after_late_write_failure(self):
        packet=self.prepare();candidate=self.candidate(packet);t.apply(self.root,'double',candidate)
        original_open=Path.open
        def fail_dataset(path,*args,**kwargs):
            if path.name=='double_numbers.json' and args and args[0]=='x':
                raise OSError('injected dataset write failure')
            return original_open(path,*args,**kwargs)
        before_tree=self.tree()
        before_dirs={str(path.relative_to(self.root)) for path in self.root.rglob('*') if path.is_dir()}
        with patch.object(Path,'open',fail_dataset):
            with self.assertRaisesRegex(OSError,'injected dataset write failure'):
                t.export(self.root,'double')
        self.assertEqual(before_tree,self.tree())
        self.assertEqual(before_dirs,{str(path.relative_to(self.root)) for path in self.root.rglob('*') if path.is_dir()})

    def test_foreign_key_requires_present_json_equal_target(self):
        packet = self.prepare()
        candidate = self.candidate(packet)
        child = candidate['datasets'][0]
        parent = copy.deepcopy(child)
        parent.update(id='parents', data=[{}], schema={'type': 'array', 'items': {'type': 'object'}})
        child.update(data=[{'input': None}], schema={'type': 'array', 'items': {'type': 'object'}},
                     foreign_keys=[{'field': 'input', 'dataset_id': 'parents', 'target_field': 'id'}])
        candidate['datasets'].append(parent)
        before = self.tree()
        with self.assertRaises(AnalysisError):
            t.apply(self.root, 'double', candidate)
        self.assertEqual(before, self.tree())
        parent['data'] = [{'id': None}]
        self.assertTrue(t.validate(self.root, 'double', candidate)['valid'])
        child['data'] = [{'input': 0}]
        parent['data'] = [{'id': False}]
        with self.assertRaises(AnalysisError):
            t.validate(self.root, 'double', candidate)
        parent['data'] = [{'id': 0.0}]
        self.assertTrue(t.validate(self.root, 'double', candidate)['valid'])

    def test_record_and_direct_save_cannot_inject_implementation_before_gate(self):
        task = w.add_task(self.root, 'Gate recording')
        for status in ('analyze', 'plan'):
            task = w.advance_task(self.root, task['id'], status)
        with p.transaction(self.root) as data:
            data['policy']['before_implement'] = True
        implementation = {'task_id': task['id'], 'role': 'implementation', 'phase': 'implement',
                          'iteration': 0, 'summary': 'Ungated change', 'status': 'completed',
                          'cited_paths': ['calculator.py'], 'cited_node_ids': [], 'packet_id': None,
                          'disposition': None, 'changed_paths': ['calculator.py'], 'notes': ''}
        before = self.tree()
        with self.assertRaises(w.WorkflowError):
            w.record_artifact(self.root, task['id'], 'implementation', implementation)
        self.assertEqual(before, self.tree())
        implementation['id'] = w.artifact_id(implementation)
        for target in ('plan', 'implement', 'test', 'review'):
            forged = copy.deepcopy(task)
            forged.update(status=target, artifacts=[implementation], artifact_ids=[implementation['id']])
            with self.subTest(target=target), self.assertRaises(w.WorkflowError):
                w.save_task(self.root, forged, expected_revision=digest(task))
            self.assertEqual(before, self.tree())

    def test_old_delivery_bindings_are_immutable_on_save(self):
        task = w.add_task(self.root, 'Keep reviewed history')
        for status in ('analyze', 'plan', 'implement'):
            task = w.advance_task(self.root, task['id'], status)
        artifact = {'task_id': task['id'], 'role': 'implementation', 'phase': 'implement',
                    'iteration': 0, 'summary': 'Implemented', 'status': 'completed',
                    'cited_paths': ['calculator.py'], 'cited_node_ids': [], 'packet_id': None,
                    'disposition': None, 'changed_paths': ['calculator.py'], 'notes': ''}
        task = w.record_artifact(self.root, task['id'], 'implementation', artifact)
        before = self.tree()
        changed = copy.deepcopy(task)
        changed['delivery']['bindings'][task['artifact_ids'][0]]['source_fingerprint'] = '0' * 64
        with self.assertRaises(w.WorkflowError):
            w.save_task(self.root, changed, expected_revision=digest(task))
        self.assertEqual(before, self.tree())

        legacy = w.add_task(self.root, 'Preserve unknown historical binding')
        legacy = w.advance_task(self.root, legacy['id'], 'analyze')
        old = {'task_id': legacy['id'], 'role': 'architect', 'phase': 'analyze',
               'iteration': 0, 'summary': 'Old evidence', 'status': 'completed',
               'cited_paths': [], 'cited_node_ids': [], 'packet_id': None, 'disposition': None}
        legacy = w.record_artifact(self.root, legacy['id'], 'architect', old)
        before = self.tree()
        injected = copy.deepcopy(legacy)
        injected['schema_version'] = 2
        injected['delivery'] = {'schema_version': 1, 'bindings': {
            legacy['artifact_ids'][0]: {'head_commit': None, 'source_fingerprint': '0' * 64}}}
        with self.assertRaises(w.WorkflowError):
            w.save_task(self.root, injected, expected_revision=digest(legacy))
        self.assertEqual(before, self.tree())

    def test_trace_sync_commands_enforce_expected_revision_atomically(self):
        from kgmaker import feature, delivery_cli
        from kgmaker.analysis_model import inventory_candidate
        (self.root / 'requirement.md').write_text('Double the calculator input.')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for key, value in [('user.name', 'Test'), ('user.email', 'test@local.invalid')]:
            subprocess.run(['git', '-C', str(self.root), 'config', key, value], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'commit', '-qm', 'Baseline'], check=True)
        (self.root / 'calculator.py').write_text('def double(value):\n    return value * 2\n# change\n')
        analysis_packet = feature.prepare(self.root, 'requirement.md', 'analysis')
        self.assertTrue(feature.apply(self.root, 'analysis', inventory_candidate(analysis_packet))['valid'])
        packet = self.prepare()
        t.apply(self.root, 'double', self.candidate(packet))
        task = w.add_task(self.root, 'Trace change')
        p.register_file(self.root, 'requirement', 'REQ', '1', 'requirement.md')
        commands = [('sync-analysis', '--id', 'analysis'), ('sync-testgen', '--id', 'double'),
                    ('capture-change', '--task', task['id'], '--base', 'HEAD')]
        for command in commands:
            revision = p.load(self.root)['revision']
            before = self.tree()
            argv = ['trace', *command, '--root', str(self.root), '--expected-revision', '0']
            with self.subTest(command=command), redirect_stdout(io.StringIO()):
                self.assertEqual(2, delivery_cli.run(build_parser().parse_args(argv)))
            self.assertEqual(before, self.tree())
            argv[-1] = str(revision)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, delivery_cli.run(build_parser().parse_args(argv)))
            self.assertEqual(revision + 1, p.load(self.root)['revision'])

    def test_read_only_trace_commands_reject_revision_preconditions(self):
        for command in ('show', 'check'):
            with self.subTest(command=command), redirect_stdout(io.StringIO()), \
                    redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    build_parser().parse_args(['trace', command, '--expected-revision', '0'])
                self.assertEqual(2, error.exception.code)

    def test_direct_save_verifies_or_captures_new_source_bindings(self):
        from kgmaker.feature import source_inventory
        task = w.add_task(self.root, 'Capture actual direct-save evidence')
        for status in ('analyze', 'plan', 'implement'):
            task = w.advance_task(self.root, task['id'], status)
        artifact = {'task_id': task['id'], 'role': 'implementation', 'phase': 'implement',
                    'iteration': 0, 'summary': 'Captured change', 'status': 'completed',
                    'cited_paths': ['calculator.py'], 'cited_node_ids': [], 'packet_id': None,
                    'disposition': None, 'changed_paths': ['calculator.py'], 'notes': ''}
        artifact['id'] = w.artifact_id(artifact)
        proposed = copy.deepcopy(task)
        proposed.update(artifacts=[artifact], artifact_ids=[artifact['id']])
        actual = {'head_commit': w._git_head(self.root),
                  'source_fingerprint': digest(source_inventory(self.root)[0])}
        before = self.tree()
        for field, value in (('head_commit', '0' * 40), ('source_fingerprint', '0' * 64)):
            forged = copy.deepcopy(proposed)
            binding = {**actual, field: value}
            forged.update(schema_version=2, delivery={'schema_version': 1,
                          'bindings': {artifact['id']: binding}})
            with self.subTest(field=field), self.assertRaises(w.WorkflowError):
                w.save_task(self.root, forged, expected_revision=digest(task))
            self.assertEqual(before, self.tree())
        w.save_task(self.root, proposed, expected_revision=digest(task))
        saved = w.load_task(self.root, task['id'])
        self.assertEqual(2, saved['schema_version'])
        self.assertEqual(actual, saved['delivery']['bindings'][artifact['id']])
        self.assertEqual(actual['source_fingerprint'], saved['worktree_fingerprint'])

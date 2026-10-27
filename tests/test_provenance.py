"""T046-S01 references, journal integrity and compatibility."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from kgmaker import provenance as p, workflow as w
from kgmaker.analysis_model import AnalysisError, digest

class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'calculator.py').write_text('def double(value):\n    return value * 2\n')
    def tree(self):
        return {str(x.relative_to(self.root)):x.read_bytes() for x in self.root.rglob('*') if x.is_file()}

    def test_lineage_local_identity_decisions_and_staleness(self):
        key=p.register_file(self.root,'requirement','REQ-1','1','calculator.py')
        with p.transaction(self.root) as data:
            data['identity']={'id':'alice','kind':'human'}
            p.event(data,key,'requested','Requested by product')
            p.event(data,key,'approved','Reviewed this content')
        report=p.trace(self.root,key)
        self.assertTrue(report['references'][0]['approved'])
        self.assertEqual('alice',report['references'][0]['requested_by']['id'])
        with p.transaction(self.root) as data:p.event(data,key,'revoked','Changed decision')
        self.assertFalse(p.trace(self.root,key)['references'][0]['approved'])
        (self.root/'calculator.py').write_text('changed')
        self.assertTrue(p.trace(self.root,key)['references'][0]['stale'])
        with self.assertRaises(AnalysisError):p.register_file(self.root,'requirement','REQ-1','1','calculator.py')

    def test_journal_integrity_concurrency_and_agent_approval(self):
        key=p.register_file(self.root,'requirement','REQ-1','1','calculator.py')
        before=self.tree()
        with self.assertRaises(AnalysisError):
            with p.transaction(self.root,0):pass
        self.assertEqual(before,self.tree())
        with self.assertRaises(AnalysisError):
            with p.transaction(self.root) as data:
                data['identity']={'id':'host','kind':'agent'};p.event(data,key,'approved','Auto approval')
        self.assertEqual(before,self.tree())
        with p.transaction(self.root):
            with self.assertRaises(AnalysisError):
                with p.transaction(self.root):pass
        path=self.root/p.JOURNAL
        value=json.loads(path.read_text());value['data']['events'].append({})
        path.write_text(json.dumps(value))
        with self.assertRaises(AnalysisError):p.load(self.root)

    def test_task_compare_and_swap_and_historical_reference_stability(self):
        task=w.add_task(self.root,'Concurrent calculator')
        old=digest(task)
        task=w.advance_task(self.root,task['id'],'analyze')
        with self.assertRaisesRegex(w.WorkflowError,'concurrently'):w.save_task(self.root,task,expected_revision=old)
        self.assertEqual('analyze',w.load_task(self.root,task['id'])['status'])


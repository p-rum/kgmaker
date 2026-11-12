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

    def test_transaction_preserves_append_only_event_history(self):
        key = p.register_file(self.root, 'requirement', 'REQ-1', '1', 'calculator.py')
        with p.transaction(self.root) as data:
            data['identity'] = {'id': 'alice', 'kind': 'human'}
            p.event(data, key, 'approved', 'Approved current content')
            p.event(data, key, 'revoked', 'Approval withdrawn')
        before = self.tree()
        self.assertFalse(p.trace(self.root, key)['references'][0]['approved'])

        for mutation in ('remove', 'rewrite'):
            with self.subTest(mutation=mutation), self.assertRaisesRegex(
                    AnalysisError, 'history is immutable'):
                with p.transaction(self.root) as data:
                    if mutation == 'remove':
                        data['events'].pop()
                    else:
                        data['events'][0]['reason'] = 'Rewritten decision'
            self.assertEqual(before, self.tree())
            self.assertFalse(p.trace(self.root, key)['references'][0]['approved'])

    def test_task_compare_and_swap_and_historical_reference_stability(self):
        task=w.add_task(self.root,'Concurrent calculator')
        old=digest(task)
        task=w.advance_task(self.root,task['id'],'analyze')
        with self.assertRaisesRegex(w.WorkflowError,'concurrently'):w.save_task(self.root,task,expected_revision=old)
        self.assertEqual('analyze',w.load_task(self.root,task['id'])['status'])

    def test_delayed_creator_returns_advanced_task_without_reset(self):
        import threading
        from unittest.mock import patch
        ready = threading.Event()
        release = threading.Event()
        result, errors = [], []
        from contextlib import contextmanager
        original = p.transaction
        @contextmanager
        def delayed(*args, **kwargs):
            if threading.current_thread().name == 'delayed-creator':
                ready.set()
                if not release.wait(5):
                    raise RuntimeError('Creator was not released')
            with original(*args, **kwargs) as data:
                yield data
        def create():
            try:
                result.append(w.add_task(self.root, 'Same request'))
            except BaseException as exc:
                errors.append(exc)
        with patch.object(p, 'transaction', delayed):
            thread = threading.Thread(target=create, name='delayed-creator')
            thread.start()
            try:
                self.assertTrue(ready.wait(5))
                task = w.add_task(self.root, 'Same request')
                task = w.advance_task(self.root, task['id'], 'analyze')
                before = self.tree()
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
        self.assertEqual('analyze', result[0]['status'])
        self.assertEqual(before, self.tree())

    def test_direct_save_requires_revision_and_preserves_artifact_history(self):
        task = w.add_task(self.root, 'Preserve history')
        task = w.advance_task(self.root, task['id'], 'analyze')
        artifact = {'task_id': task['id'], 'role': 'architect', 'phase': 'analyze',
                    'iteration': 0, 'summary': 'Read calculator', 'status': 'completed',
                    'cited_paths': ['calculator.py'], 'cited_node_ids': [],
                    'packet_id': None, 'disposition': None}
        task = w.record_artifact(self.root, task['id'], 'architect', artifact)
        before = self.tree()
        removed = copy.deepcopy(task)
        removed['artifacts'] = []
        removed['artifact_ids'] = []
        for revision in (None, digest(task)):
            with self.subTest(revision=revision), self.assertRaises(w.WorkflowError):
                w.save_task(self.root, removed, expected_revision=revision)
            self.assertEqual(before, self.tree())

    def test_journal_revision_rejects_boolean_and_negative_values(self):
        p.register_file(self.root, 'requirement', 'REQ', '1', 'calculator.py')
        before = self.tree()
        for value in (True, -1, '1'):
            with self.subTest(value=value), self.assertRaises(AnalysisError):
                with p.transaction(self.root, value):
                    pass
            self.assertEqual(before, self.tree())

    def test_transaction_owns_revision_and_preserves_cas_progress(self):
        p.register_file(self.root, 'requirement', 'REQ', '1', 'calculator.py')
        observed = p.load(self.root)['revision']
        before = self.tree()
        with self.assertRaisesRegex(AnalysisError, 'revision is managed'):
            with p.transaction(self.root, observed) as data:
                data['policy']['before_done'] = True
                data['revision'] = observed - 1
        self.assertEqual(before, self.tree())
        self.assertFalse(p.load(self.root)['policy']['before_done'])

        with p.transaction(self.root, observed) as data:
            data['policy']['before_done'] = True
        self.assertEqual(observed + 1, p.load(self.root)['revision'])
        with self.assertRaisesRegex(AnalysisError, 'Stale journal revision'):
            with p.transaction(self.root, observed):
                pass

    def test_trace_marks_test_suite_stale_without_later_testgen_stage(self):
        (self.root / 'test_calculator.py').write_text('def test_double():\n    pass\n')
        key = p.register_file(
            self.root, 'test_suite', 'calculator-tests', '1', 'test_calculator.py')

        report = p.trace(self.root, key)

        self.assertEqual(1, len(report['references']))
        self.assertTrue(report['references'][0]['stale'])
        self.assertFalse(report['references'][0]['approved'])

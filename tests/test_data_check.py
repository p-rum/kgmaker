"""Offline data audit acceptance cases; no model, shell or source mutation."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA, write_json
from kgmaker.cli import main
from kgmaker.data_check import data_check


class DataCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Account.kt').write_text('data class Account(val balance: Double)\n')
        (self.root / 'requirement.md').write_text('Calculate using balance; $(touch injected) `echo forbidden`.')
        self.packet = feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        self.spec = {
            'schema_version': 1, 'analysis_id': 'audit', 'requirement_hash': self.packet['requirement_hash'],
            'requirements': [{'id': 'analysis:audit:requirement:balance', 'text': 'Use balance',
                              'kind': 'InputRequirement', 'source_quote': 'balance'}],
            'inputs': [{'id': 'analysis:audit:input:balance', 'name': 'balance',
                        'requirement_ids': ['analysis:audit:requirement:balance'],
                        **{key: None for key in INPUT_METADATA}}],
        }

    def tree(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def cli(self, *args):
        output = io.StringIO()
        with patch('sys.argv', ['kgmaker', 'feature', 'data-check', '--root', str(self.root),
                                '--analysis', 'audit', *args]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as exit:
                main()
        return exit.exception.code, output.getvalue()

    def test_fa66_68_static_candidates_are_unknown_and_use_existing_validation(self):
        before = self.tree()
        result = data_check(self.root, 'audit', self.spec)
        self.assertEqual(0, result['exit_code'])
        self.assertEqual(before, self.tree())
        candidate = result['candidate']
        self.assertTrue(feature.validate(self.root, 'audit', candidate)['valid'])
        self.assertEqual('UNKNOWN', candidate['input_requirements'][0]['availability'])
        self.assertIn('data_field:Account.kt:Account.balance', candidate['input_requirements'][0]['source_ids'])
        self.assertTrue(result['candidate_sources'][0]['static_impact'])
        self.assertEqual([], result['data_delivery_gaps'])
        self.assertTrue(result['coverage_gaps'])
        self.assertTrue(result['ambiguity_queue'])
        self.assertEqual(result, data_check(self.root, 'audit', self.spec))

    def test_fa69_source_and_answer_hash_drift_fail_closed(self):
        (self.root / 'Account.kt').write_text('data class Account(val modified: String)\n')
        result = data_check(self.root, 'audit', self.spec)
        self.assertEqual(3, result['exit_code'])
        self.assertNotIn('candidate', result)
        self.packet = feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        self.spec['requirement_hash'] = 'previous-answer-hash'
        with self.assertRaises(AnalysisError) as error:
            data_check(self.root, 'audit', self.spec)
        self.assertEqual(3, error.exception.code)

    def test_fa70_coverage_gaps_are_not_delivery_gaps(self):
        (self.root / 'unsupported.xls').write_bytes(b'not an xlsx file')
        self.packet = feature.prepare(self.root, 'requirement.md', 'audit', 1)
        self.spec['inputs'][0]['name'] = 'not_found_field'
        result = data_check(self.root, 'audit', self.spec)
        self.assertEqual('UNKNOWN', result['candidate']['input_requirements'][0]['availability'])
        self.assertEqual([], result['data_delivery_gaps'])
        kinds = {gap['kind'] for gap in result['coverage_gaps']}
        self.assertTrue({'OMITTED_SOURCES', 'UNSUPPORTED_SOURCES'} <= kinds)
        self.assertIn('What the tool cannot verify yet', result['report'])

    def test_forged_reference_and_injected_availability_rejected(self):
        for fields in ({'availability': 'AVAILABLE'}, {'candidate_entity_ids': ['fake']},
                       {'name': {}}, {'nullable': 'false'}, {'definition': []}):
            with self.subTest(fields=fields):
                spec = copy.deepcopy(self.spec)
                spec['inputs'][0].update(fields)
                before = self.tree()
                try:
                    result = data_check(self.root, 'audit', spec)
                    self.assertEqual(2, result['exit_code'])
                except AnalysisError as error:
                    self.assertEqual(2, error.code)
                self.assertEqual(before, self.tree())
        spec = copy.deepcopy(self.spec)
        spec['requirements'][0]['source_reference'] = {
            'path': 'Account.kt', 'location': {'type': 'lines', 'start': 99, 'end': 99}, 'quote': 'balance'}
        self.assertEqual(2, data_check(self.root, 'audit', spec)['exit_code'])

    def test_derivation_cycles_reuse_validator(self):
        self.spec['inputs'][0].update({'dependency_ids': ['analysis:audit:input:balance'],
                                     'transformation': 'balance / 2'})
        result = data_check(self.root, 'audit', self.spec)
        self.assertEqual(2, result['exit_code'])
        self.assertTrue(any('Cyclic' in error for error in result['diagnostics']))

    def test_fa71_72_cli_no_shell_and_incomplete_exit(self):
        write_json(self.root / 'inputs.json', self.spec)
        feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        before = self.tree()
        # Only the existing git provenance probe is permitted, no prose is executed.
        import subprocess
        real_run = subprocess.run
        calls = []
        def probe(args, **kwargs):
            calls.append(args)
            self.assertEqual('git', args[0])
            return real_run(args, **kwargs)
        with patch('subprocess.run', side_effect=probe):
            code, output = self.cli('--inputs', 'inputs.json', '--format', 'json', '--require-complete')
        self.assertEqual(4, code)
        self.assertTrue(json.loads(output)['valid'])
        self.assertEqual(before, self.tree())
        code, output = self.cli('--inputs', 'inputs.json', '--format', 'markdown')
        self.assertEqual(0, code)
        self.assertIn('Tool uncertainty does not prove missing business data.', output)

    def test_workspace_never_falls_back_to_root(self):
        code, output = self.cli('--workspace', 'workspace.json', '--inputs', 'absent.json')
        self.assertEqual(2, code)
        self.assertIn('workspace differs', json.loads(output)['error'])

    def test_fa74_validate_apply_report_preserve_sources_and_as_is(self):
        (self.root / '.kgmaker' / 'graph.json').write_text('{}')
        (self.root / '.kgmaker' / 'semantic.json').write_text('{}')
        feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        result = data_check(self.root, 'audit', self.spec)
        before = self.tree()
        self.assertTrue(feature.apply(self.root, 'audit', result['candidate'])['valid'])
        for path, content in before.items():
            self.assertEqual(content, (self.root / path).read_bytes())
        from kgmaker.analysis_report import render_report
        report = render_report(result['candidate'], feature.load_packet(self.root, 'audit'), [])
        self.assertIn('What the tool cannot verify yet', report)

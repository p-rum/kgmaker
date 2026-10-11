"""Offline end-to-end acceptance with prepared agent output, no fabricated availability."""
import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker.analysis_model import read_json, write_json
from kgmaker.cli import main

FIXTURE = Path(__file__).parents[1] / 'fixtures/feature-analysis'


def bind(candidate, packet):
    result = copy.deepcopy(candidate)
    for key in ('revision', 'packet_id', 'requirement_hash', 'baseline', 'coverage'):
        result[key] = packet[key]
    for evidence in result['evidence']:
        evidence['sha256'] = packet['source_manifest'][evidence['path']]['sha256']
    result['completion']['pending'] += packet['coverage']['pending']
    return result


class FeatureFixtureTests(unittest.TestCase):
    def test_fixture_cli_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
            state = root / '.kgmaker/analyses/additional-hedge'
            def run(*args):
                output = io.StringIO()
                with patch('sys.argv', ['kgmaker', 'feature', *args, '--root', str(root)]), redirect_stdout(output):
                    with self.assertRaises(SystemExit) as result:
                        main()
                return result.exception.code, json.loads(output.getvalue())
            self.assertEqual(0, run('prepare', '--id', 'additional-hedge', '--requirement', 'requirements/additional-hedge.md', '--token-budget', '100000')[0])
            packet = read_json(state / 'packet.json')
            bad = bind(read_json(root / 'expected/candidate-invalid.json'), packet)
            write_json(state / 'candidate.json', bad)
            arguments = ['--analysis', 'additional-hedge', '--candidate', '.kgmaker/analyses/additional-hedge/candidate.json']
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(2, run('apply', *arguments)[0])
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            good = bind(read_json(root / 'expected/candidate-valid.json'), packet)
            write_json(state / 'candidate.json', good)
            self.assertEqual(0, run('validate', *arguments)[0])
            self.assertEqual(0, run('apply', *arguments)[0])
            self.assertEqual(0, run('report', '--analysis', 'additional-hedge')[0])
            report = (root / 'docs/generated/features/additional-hedge.md').read_text(encoding='utf-8')
            self.assertIn('backend/ExposureService.kt:3', report)
            self.assertIn('UNKNOWN', report)
            self.assertIn('TO_BE', report)
            self.assertEqual(0, run('compare', '--analysis', 'additional-hedge', '--variant', 'no-new-api')[0])
            self.assertEqual(2, run('compare', '--analysis', 'additional-hedge', '--variant', 'imaginary')[0])
            self.assertEqual(0, run('revise', '--analysis', 'additional-hedge', '--answers', 'requirements/additional-hedge-answers.json')[0])
            revised = bind(good, read_json(state / 'packet.json'))
            revised['questions'][0]['status'] = 'ANSWERED'
            write_json(state / 'candidate.json', revised)
            self.assertEqual(0, run('validate', *arguments)[0])
            self.assertEqual(0, run('apply', *arguments)[0])
            self.assertTrue((state / 'history/analysis-1.json').exists())
            self.assertEqual(4, run('report', '--analysis', 'additional-hedge', '--require-complete')[0])

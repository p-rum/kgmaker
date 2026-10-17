from __future__ import annotations

import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA, inventory_candidate, read_json, write_json
from kgmaker.cli import main
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'service.kt').write_text('class Account {\n    val accountBalance = 100\n}\n', encoding='utf-8')
        (self.root / 'requirement.md').write_text('Doporuč zajištění podle disponibilních prostředků.', encoding='utf-8')
        self.packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        self.candidate = inventory_candidate(self.packet)
        self.directory = self.root / '.kgmaker/analyses/hedge'

    def tree(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def cli(self, *args):
        output = io.StringIO()
        with patch('sys.argv', ['kgmaker', 'feature', *args, '--root', str(self.root)]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as exit:
                main()
        return exit.exception.code, json.loads(output.getvalue())

    def evidence(self):
        return {'id': 'analysis:hedge:evidence:balance', 'source_id': 'service.kt', 'kind': 'CODE',
                'path': 'service.kt', 'sha256': self.packet['source_manifest']['service.kt']['sha256'],
                'location': {'type': 'lines', 'start': 2, 'end': 2}, 'quote': 'val accountBalance = 100',
                'supports': 'A constant declaration exists; this does not prove available liquidity.',
                'method': 'EXTRACTED', 'confidence': 1, 'validity': 'VALID'}

    def input(self):
        return {'id': 'analysis:hedge:input:liquidity', 'name': 'Available liquidity',
                **{key: None for key in INPUT_METADATA}, 'requirement_ids': [self.candidate['requirements'][0]['id']],
                'availability': 'UNKNOWN', 'acquisition': 'UNRESOLVED', 'usability': 'UNASSESSED',
                'verification_scope': 'Only this backend root; other banking systems not supplied.',
                'next_step': 'Business must define liquidity; inspect runtime data path.', 'owner_role': 'Business analyst',
                'transformation': None, 'evidence_ids': [], 'source_ids': [], 'dependency_ids': [], 'question_ids': []}

    def test_fa12_prepare_is_idempotent_and_preserves_candidate(self):
        write_json(self.directory / 'candidate.json', self.candidate)
        before = self.tree()
        self.assertEqual(self.packet, feature.prepare(self.root, 'requirement.md', 'hedge', 100000))
        self.assertEqual(before, self.tree())
        self.assertTrue(feature.validate(self.root, 'hedge', self.candidate)['valid'])

    def test_fa07_apply_isolated_and_idempotent(self):
        for name in ['graph.json', 'semantic.json']:
            (self.root / '.kgmaker' / name).write_text('{}', encoding='utf-8')
        # Reprepare because semantic.json is baseline input, even when invalid.
        packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        candidate = inventory_candidate(packet)
        before = {name: (self.root / '.kgmaker' / name).read_bytes() for name in ['graph.json', 'semantic.json']}
        self.assertTrue(feature.apply(self.root, 'hedge', candidate)['valid'])
        for name, raw in before.items():
            self.assertEqual(raw, (self.root / '.kgmaker' / name).read_bytes())
        tree = self.tree()
        self.assertTrue(feature.apply(self.root, 'hedge', candidate)['valid'])
        self.assertEqual(tree, self.tree())

    def test_fa10_forged_citations_and_no_mutation(self):
        self.candidate['evidence'] = [self.evidence()]
        self.assertTrue(feature.validate(self.root, 'hedge', self.candidate)['valid'])
        for mutation in [{'sha256': '0' * 64}, {'location': {'type': 'lines', 'start': 99, 'end': 99}},
                         {'quote': 'availableLiquidity'}, {'path': '../outside.kt'}, {'kind': 'DOCUMENTATION'}]:
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(self.candidate)
                bad['evidence'][0].update(mutation)
                before = self.tree()
                self.assertEqual(2, feature.apply(self.root, 'hedge', bad)['exit_code'])
                self.assertEqual(before, self.tree())

    def test_json_pointer_requires_existing_field_and_value(self):
        (self.root / 'api.json').write_text('{"properties":{"balance":{"type":"number"}}}', encoding='utf-8')
        packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        candidate = inventory_candidate(packet)
        evidence = self.evidence()
        evidence.update({'kind': 'CONTRACT', 'path': 'api.json', 'sha256': packet['source_manifest']['api.json']['sha256'],
                         'location': {'type': 'json_pointer', 'pointer': '/properties/balance/type'}, 'value': 'number'})
        candidate['evidence'] = [evidence]
        self.assertTrue(feature.validate(self.root, 'hedge', candidate)['valid'])
        evidence['location']['pointer'] = '/properties/liquidity/type'
        self.assertEqual(2, feature.apply(self.root, 'hedge', candidate)['exit_code'])

    def test_fa11_packet_and_revision_mismatch(self):
        for key, value in [('packet_id', 'old-packet'), ('revision', 99)]:
            bad = copy.deepcopy(self.candidate)
            bad[key] = value
            before = self.tree()
            result = feature.apply(self.root, 'hedge', bad)
            self.assertEqual(3, result['exit_code'])
            self.assertIn('regenerate candidate', result['next_step'])
            self.assertEqual(before, self.tree())

    def test_fa13_uncommitted_changes_and_requirement_invalidate(self):
        for name in ['service.kt', 'requirement.md']:
            with self.subTest(name=name):
                path = self.root / name
                previous = path.read_bytes()
                path.write_bytes(previous + b'\n// changed')
                before = self.tree()
                self.assertEqual(3, feature.apply(self.root, 'hedge', self.candidate)['exit_code'])
                self.assertEqual(before, self.tree())
                path.write_bytes(previous)
        (self.root / 'service.kt').write_text('class Changed {}', encoding='utf-8')
        new_packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        self.assertEqual(2, new_packet['revision'])
        self.assertEqual(self.packet, read_json(self.directory / 'history/packet-1.json'))
        self.assertEqual(3, feature.apply(self.root, 'hedge', self.candidate)['exit_code'])

    def test_fa18_19_small_budget_produces_incomplete_inventory(self):
        packet = feature.prepare(self.root, 'requirement.md', 'hedge', 1)
        candidate = inventory_candidate(packet)
        self.assertTrue(packet['coverage']['omitted_sources'])
        self.assertEqual(0, packet['budget']['included_count'])
        candidate['input_requirements'] = [self.input()]
        self.assertTrue(feature.apply(self.root, 'hedge', candidate)['valid'])
        code, _ = self.cli('report', '--analysis', 'hedge', '--require-complete')
        self.assertEqual(4, code)
        self.assertTrue((self.root / 'docs/generated/features/hedge.md').exists())
        candidate['completion'].update(processing_status='COMPLETE', pending=[])
        self.assertEqual(2, feature.validate(self.root, 'hedge', candidate)['exit_code'])

    def test_fa02_04_no_automatic_liquidity_or_absence_claim(self):
        item = self.input()
        self.candidate['input_requirements'] = [item]
        self.assertTrue(feature.validate(self.root, 'hedge', self.candidate)['valid'])
        for status in ['AVAILABLE', 'CONFIRMED_MISSING', 'PARTIAL', 'NOT_FOUND_IN_SCOPE']:
            item['availability'] = status
            self.assertEqual(2, feature.validate(self.root, 'hedge', self.candidate)['exit_code'])

    def test_fa27_dangling_proposal_and_traversal_rejected(self):
        self.candidate['proposal']['edges'] = [{'source': 'proposal:hedge:new', 'target': 'missing', 'kind': 'reuses_entity', 'state': 'TO_BE'}]
        before = self.tree()
        self.assertEqual(2, feature.apply(self.root, 'hedge', self.candidate)['exit_code'])
        self.assertEqual(before, self.tree())
        for name in ['../hedge', '/hedge', 'a/b', 'a\\b']:
            with self.assertRaises(AnalysisError):
                feature.prepare(self.root, 'requirement.md', name)
        code, _ = self.cli('report', '--analysis', 'hedge', '--output', '../escape.md')
        self.assertEqual(2, code)

    def test_fa25_cli_workflow_without_semantic_packet_or_git(self):
        write_json(self.directory / 'candidate.json', self.candidate)
        before = self.tree()
        code, result = self.cli('validate', '--analysis', 'hedge', '--candidate',
                                '.kgmaker/analyses/hedge/candidate.json', '--scope', 'production')
        self.assertEqual(2, code)
        self.assertIn('selection differs', result['error'])
        self.assertEqual(before, self.tree())
        code, result = self.cli('validate', '--analysis', 'hedge', '--candidate', '.kgmaker/analyses/hedge/candidate.json')
        self.assertEqual(0, code)
        self.assertTrue(result['valid'])
        self.assertEqual(before, self.tree())
        self.assertEqual(0, self.cli('apply', '--analysis', 'hedge', '--candidate', '.kgmaker/analyses/hedge/candidate.json')[0])
        self.assertEqual(0, self.cli('status', '--analysis', 'hedge')[0])
        self.assertEqual(0, self.cli('report', '--analysis', 'hedge')[0])
        report = (self.root / 'docs/generated/features/hedge.md').read_text(encoding='utf-8')
        self.assertIn('Business cíl', report)
        self.assertIn('Graph scope: `all`', report)
        self.assertEqual(11, report.count('\n## '))

    def test_fa33_report_not_used_as_source_evidence(self):
        before = scan_repository(self.root).files
        self.assertEqual(0, self.cli('report', '--analysis', 'hedge')[0])
        self.assertEqual(before, scan_repository(self.root).files)
        self.assertEqual(self.packet, feature.prepare(self.root, 'requirement.md', 'hedge', 100000))

    def test_stale_report_is_labelled_and_returns_three(self):
        self.candidate['evidence'] = [self.evidence()]
        feature.apply(self.root, 'hedge', self.candidate)
        (self.root / 'service.kt').write_text('class Modified {}', encoding='utf-8')
        self.assertEqual(3, self.cli('report', '--analysis', 'hedge')[0])
        self.assertIn('STALE', (self.root / 'docs/generated/features/hedge.md').read_text(encoding='utf-8'))

    def test_fa34_processing_complete_with_business_decision_blocked(self):
        req = self.candidate['requirements'][0]
        req['status'] = 'OPEN_QUESTION'
        self.candidate['questions'] = [{'id': 'analysis:hedge:question:definition', 'text': 'Define liquidity',
            'status': 'OPEN', 'blocking': True, 'owner_role': 'Business', 'requirement_ids': [req['id']]}]
        self.candidate['completion'] = {'processing_status': 'COMPLETE', 'decision_readiness': 'BLOCKED', 'pending': []}
        self.assertTrue(feature.validate(self.root, 'hedge', self.candidate)['valid'])
        self.candidate['completion']['decision_readiness'] = 'READY'
        self.assertEqual(2, feature.validate(self.root, 'hedge', self.candidate)['exit_code'])

    def test_malformed_structures_never_raise_or_mutate(self):
        for key, value in [('completion', []), ('evidence', [None]), ('schema_version', True), ('requirements', [{}]),
                           ('proposal', {'nodes': [None], 'edges': []}), ('input_requirements', [{'id': []}])]:
            with self.subTest(key=key):
                bad = copy.deepcopy(self.candidate)
                bad[key] = value
                before = self.tree()
                self.assertEqual(2, feature.apply(self.root, 'hedge', bad)['exit_code'])
                self.assertEqual(before, self.tree())

    def test_fa31_graph_version_compatibility(self):
        old = {'nodes': [], 'edges': [], 'files': {}}
        self.assertEqual(1, KnowledgeGraph.from_dict(old).schema_version)
        self.assertEqual(2, KnowledgeGraph.from_dict({**old, 'schema_version': 2}).schema_version)
        self.assertEqual(3, KnowledgeGraph.from_dict({**old, 'schema_version': 3}).schema_version)
        for version in [True, 4, '1']:
            with self.assertRaisesRegex(ValueError, 'Unsupported graph schema_version'):
                KnowledgeGraph.from_dict({**old, 'schema_version': version})

    def test_output_symlink_cannot_overwrite_source(self):
        directory = self.root / 'docs/generated/features'
        directory.mkdir(parents=True)
        (directory / 'hedge.md').symlink_to(self.root / 'service.kt')
        before = (self.root / 'service.kt').read_bytes()
        code, _ = self.cli('report', '--analysis', 'hedge')
        self.assertEqual(2, code)
        self.assertEqual(before, (self.root / 'service.kt').read_bytes())

    def test_revise_preserves_history_and_accepts_new_answer_file(self):
        req = self.candidate['requirements'][0]
        req['status'] = 'OPEN_QUESTION'
        qid = 'analysis:hedge:question:definition'
        self.candidate['questions'] = [{'id': qid, 'text': 'Define liquidity', 'status': 'OPEN',
            'blocking': True, 'owner_role': 'Business', 'requirement_ids': [req['id']]}]
        self.candidate['completion'] = {'processing_status': 'COMPLETE', 'decision_readiness': 'BLOCKED', 'pending': []}
        self.assertTrue(feature.apply(self.root, 'hedge', self.candidate)['valid'])
        answers = {'answers': [{'question_id': qid, 'decision_id': 'liquidity-definition', 'answer': 'Balance less reserved funds',
                    'revision': 1, 'approval_status': 'UNAPPROVED'}]}
        write_json(self.root / 'answers.json', answers)
        code, result = self.cli('revise', '--analysis', 'hedge', '--answers', 'answers.json')
        self.assertEqual(0, code)
        self.assertEqual(2, result['revision'])
        self.assertEqual(self.candidate, read_json(self.directory / 'analysis.json'))
        self.assertEqual(self.packet, read_json(self.directory / 'history/packet-1.json'))
        packet = feature.load_packet(self.root, 'hedge')
        self.assertNotEqual(self.packet['requirement_hash'], packet['requirement_hash'])
        self.assertEqual(packet, feature.revise(self.root, 'hedge', answers))
        self.assertEqual(packet, feature.prepare(self.root, 'requirement.md', 'hedge', 100000))
        revised = inventory_candidate(packet)
        revised['questions'] = copy.deepcopy(self.candidate['questions'])
        revised['questions'][0]['status'] = 'ANSWERED'
        revised['requirements'][0]['status'] = 'OPEN_QUESTION'
        revised['completion'] = {'processing_status': 'COMPLETE', 'decision_readiness': 'BLOCKED', 'pending': []}
        revised['evidence'] = [{'id': 'analysis:hedge:evidence:decision', 'kind': 'HUMAN_DECISION',
            'source_id': 'liquidity-definition', 'supports': 'User supplied a definition, pending approval',
            'method': 'EXTRACTED', 'confidence': 1, 'validity': 'VALID', **answers['answers'][0]}]
        self.assertTrue(feature.apply(self.root, 'hedge', revised)['valid'])
        self.assertEqual(self.candidate, read_json(self.directory / 'history/analysis-1.json'))
        revised['completion']['decision_readiness'] = 'READY'
        self.assertEqual(2, feature.validate(self.root, 'hedge', revised)['exit_code'])
        self.assertEqual(0, self.cli('report', '--analysis', 'hedge')[0])

    def test_init_preserves_user_analyst_and_junie_files(self):
        from kgmaker.cli import init
        from kgmaker.data_agent import (
            DATA_AUDITOR_FILE, DATA_AUDITOR_CONTENT,
            DATA_AUDITOR_JUNIE_FILE, DATA_AUDITOR_JUNIE_CONTENT,
        )
        with redirect_stdout(io.StringIO()):
            init(self.root)
        analyst = self.root / '.github/agents/kgmaker-analyst.agent.md'
        junie = self.root / '.junie/commands/kgmaker-analyze-feature.md'
        auditor = self.root / DATA_AUDITOR_FILE
        auditor_command = self.root / DATA_AUDITOR_JUNIE_FILE
        self.assertEqual(DATA_AUDITOR_CONTENT, auditor.read_text(encoding='utf-8'))
        self.assertEqual(DATA_AUDITOR_JUNIE_CONTENT, auditor_command.read_text(encoding='utf-8'))
        for path in [analyst, junie, auditor, auditor_command]:
            path.write_text('user instructions', encoding='utf-8')
        with redirect_stdout(io.StringIO()):
            init(self.root)
        for path in [analyst, junie, auditor, auditor_command]:
            self.assertEqual('user instructions', path.read_text(encoding='utf-8'))
        with redirect_stdout(io.StringIO()):
            init(self.root, force=True)
        self.assertEqual(DATA_AUDITOR_CONTENT, auditor.read_text(encoding='utf-8'))
        self.assertEqual(DATA_AUDITOR_JUNIE_CONTENT, auditor_command.read_text(encoding='utf-8'))

    def test_scope_and_proposal_are_explicit_in_query(self):
        from kgmaker.feature_cli import query_analysis
        self.candidate['proposal']['nodes'] = [{'id': 'proposal:hedge:liquidity', 'kind': 'Calculation',
            'name': 'liquidity recommendation', 'description': 'Proposed only', 'state': 'TO_BE'}]
        self.assertTrue(feature.apply(self.root, 'hedge', self.candidate)['valid'])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, query_analysis(self.root, 'hedge', 'liquidity', 10))
        result = json.loads(output.getvalue())
        self.assertEqual('TO_BE', result['matches'][0]['state'])
        self.assertFalse(any(n.id.startswith('proposal:') for n in scan_repository(self.root).nodes))

    def test_fake_human_approval_is_rejected(self):
        self.candidate['evidence'] = [{'id': 'analysis:hedge:evidence:fake', 'kind': 'HUMAN_DECISION',
            'source_id': 'someone', 'supports': 'Approved', 'method': 'EXTRACTED', 'confidence': 1,
            'validity': 'VALID', 'decision_id': 'fake', 'answer': 'yes', 'revision': 1, 'approval_status': 'APPROVED'}]
        self.assertEqual(2, feature.validate(self.root, 'hedge', self.candidate)['exit_code'])

    def test_cyclic_derivation_and_document_only_reuse_are_rejected(self):
        a, b = self.input(), self.input()
        b['id'] += '-other'
        for item, dependency in [(a, b['id']), (b, a['id'])]:
            item.update(acquisition='DERIVED', transformation='Needs another input', dependency_ids=[dependency])
        self.candidate['input_requirements'] = [a, b]
        result = feature.validate(self.root, 'hedge', self.candidate)
        self.assertTrue(any('Cyclic' in e for e in result['diagnostics']))
        self.candidate['input_requirements'] = []
        evidence = self.evidence()
        evidence.update(kind='REQUIREMENT', quote=self.packet['requirement'], sha256=self.packet['requirement_file_hash'])
        self.candidate['evidence'] = [evidence]
        self.candidate['capability_matches'] = [{'id': 'analysis:hedge:match:fake',
            'entity_ids': [self.packet['allowed_graph_ids'][0]], 'requirement_ids': [self.candidate['requirements'][0]['id']],
            'evidence_ids': [evidence['id']], 'rationale': 'Same words', 'limitations': 'Unknown',
            'state': 'AS_IS', 'method': 'INFERRED', 'validity': 'VALID'}]
        self.assertEqual(2, feature.validate(self.root, 'hedge', self.candidate)['exit_code'])

    def test_verified_impact_path_and_reversed_forgery(self):
        from dataclasses import asdict
        from kgmaker.dataflow import impact_paths
        (self.root / 'service.kt').write_text('data class Input(val value: Double)\nfun twice(input: Input): Double = input.value * 2\n', encoding='utf-8')
        packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        candidate = inventory_candidate(packet)
        graph = scan_repository(self.root)
        seed = next(n.id for n in graph.nodes if n.name == 'Input.value')
        path = impact_paths(graph, seed)['paths'][0]
        evidence = self.evidence()
        evidence.update(sha256=packet['source_manifest']['service.kt']['sha256'], quote='input.value * 2')
        candidate['evidence'] = [evidence]
        candidate['impact_paths'] = [{**path, 'id': 'analysis:hedge:impact:twice', 'evidence_ids': [evidence['id']]}]
        self.assertTrue(feature.validate(self.root, 'hedge', candidate)['valid'])
        candidate['impact_paths'][0]['entity_ids'].reverse()
        result = feature.validate(self.root, 'hedge', candidate)
        self.assertEqual(2, result['exit_code'])

    def test_impact_cli_json_uses_current_sources(self):
        (self.root / 'service.kt').write_text('data class Input(val value: Double)\nfun twice(input: Input): Double = input.value * 2\n', encoding='utf-8')
        graph = scan_repository(self.root)
        seed = next(n.id for n in graph.nodes if n.name == 'Input.value')
        output = io.StringIO()
        with patch('sys.argv', ['kgmaker', 'impact', '--root', str(self.root), '--entity', seed, '--include-data-flow', '--format', 'json']), redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                main()
        self.assertEqual(0, result.exception.code)
        self.assertEqual(seed, json.loads(output.getvalue())['seed'])
        self.assertTrue(json.loads(output.getvalue())['paths'])

    def test_stale_impact_report_keeps_historical_proof_with_warning(self):
        from kgmaker.dataflow import impact_paths
        (self.root / 'service.kt').write_text('data class Input(val value: Double)\nfun twice(input: Input): Double = input.value * 2\n', encoding='utf-8')
        packet = feature.prepare(self.root, 'requirement.md', 'hedge', 100000)
        candidate = inventory_candidate(packet)
        graph = scan_repository(self.root)
        seed = next(n.id for n in graph.nodes if n.name == 'Input.value')
        evidence = self.evidence()
        evidence.update(sha256=packet['source_manifest']['service.kt']['sha256'], quote='input.value * 2')
        candidate['evidence'] = [evidence]
        candidate['impact_paths'] = [{**impact_paths(graph, seed)['paths'][0],
            'id': 'analysis:hedge:impact:twice', 'evidence_ids': [evidence['id']]}]
        self.assertTrue(feature.apply(self.root, 'hedge', candidate)['valid'])
        (self.root / 'service.kt').write_text('class New {}', encoding='utf-8')
        self.assertEqual(3, self.cli('report', '--analysis', 'hedge')[0])
        candidate['requirements'][0]['text'] = 'Tampered after apply'
        write_json(self.directory / 'analysis.json', candidate)
        self.assertEqual(2, self.cli('report', '--analysis', 'hedge')[0])

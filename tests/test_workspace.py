import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, inventory_candidate, write_json
from kgmaker.cli import main
from kgmaker.dataflow import impact_paths
from kgmaker.workspace import qualified, snapshot_workspace, load_workspace, _REPO_CACHE


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.coordinator = self.root / 'coordinator'; self.coordinator.mkdir()
        fixture = Path(__file__).parents[1] / 'fixtures/multirepo-analysis'
        for repo in ('backend', 'frontend', 'tests'):
            shutil.copytree(fixture / repo, self.root / repo)
            subprocess.run(['git', 'init', '-q', str(self.root / repo)], check=True)
        self.manifest = self.root / 'workspace.json'
        self.config = {'schema_version': 1, 'workspace_id': 'fixture', 'repositories': [
            {'id': 'backend', 'role': 'backend', 'path': 'backend', 'flyway': {'database_id': 'fixture-db', 'stream_id': 'main'}},
            {'id': 'frontend', 'role': 'frontend', 'path': 'frontend'},
            {'id': 'tests', 'role': 'automated-tests', 'path': 'tests'}],
            'services': [{'id': 'exposure-api', 'backend_repo': 'backend', 'frontend_repos': ['frontend'],
                          'test_repos': ['tests'], 'contract': {'repo_id': 'backend', 'path': 'contracts/exposure.json'},
                          'consumer_path_prefix': '/api', 'provider_path_prefix': ''}]}
        write_json(self.manifest, self.config)
        (self.coordinator / 'requirement.md').write_text('Add a new decline input.')

    def packet(self):
        return feature.prepare(self.coordinator, 'requirement.md', 'decline', 1000000, workspace=self.manifest)

    def test_fa46_47_identity_and_cross_repo_impact(self):
        _, coverage, sources, graph, _ = snapshot_workspace(self.manifest)
        identities = {n.id for n in graph.nodes}
        self.assertTrue(all(e.source in identities and e.target in identities for e in graph.edges))
        for repo in ('backend', 'frontend', 'tests'):
            self.assertIn(qualified(repo, 'data_field:src/model.ts:Client.balance'), {n.id for n in graph.nodes})
        result = impact_paths(graph, qualified('backend', 'data_field:src/model.kt:ExposureOutput.decline'))
        reached = {p['entity_ids'][-1] for p in result['paths']}
        self.assertIn(qualified('frontend', 'ui_element:src/page.tsx:decline'), reached)
        self.assertTrue(any('test_assertion' in node for node in reached))
        self.assertTrue(any(p['weakest_confidence'] == 'INFERRED' for p in result['paths']))
        self.assertEqual('COMPLETE', coverage['schemas']['backend'][0]['status'])

    def test_fa48_duplicate_service_identity_not_confirmed(self):
        other = copy.deepcopy(self.config['services'][0]); other['id'] = 'another-service'
        self.config['services'].append(other); write_json(self.manifest, self.config)
        _, coverage, _, graph, _ = snapshot_workspace(self.manifest)
        self.assertTrue(any('Ambiguous service' in reason for reason in coverage['limitations']))
        self.assertFalse(any(edge.kind == 'displayed_in' for edge in graph.edges))

    def test_fa50_request_only_not_field_coverage(self):
        graph = snapshot_workspace(self.manifest)[3]
        request_only = qualified('tests', 'test_case:e2e/exposure.spec.ts:9')
        self.assertFalse(any(edge.source == request_only and edge.kind == 'asserts_field' for edge in graph.edges))
        self.assertTrue(any(edge.kind == 'tests_endpoint' for edge in graph.edges))

    def test_fa52_59_missing_checkout_and_reappearance(self):
        self.config['repositories'][1]['path'] = 'not-yet-present'; write_json(self.manifest, self.config)
        packet = self.packet()
        self.assertEqual('MISSING', packet['baseline']['repositories']['frontend']['status'])
        shutil.copytree(self.root / 'frontend', self.root / 'not-yet-present')
        self.assertTrue(feature.freshness(self.coordinator, packet))

    def test_fa53_unchanged_backend_not_reparsed(self):
        _REPO_CACHE.clear(); snapshot_workspace(self.manifest)
        (self.root / 'frontend/src/page.tsx').write_text('interface Other { value: string; }')
        real = feature.current_graph
        roots = []
        def capture(root, *args):
            roots.append(root.name); return real(root, *args)
        with patch('kgmaker.feature.current_graph', side_effect=capture):
            snapshot_workspace(self.manifest)
        self.assertEqual(['frontend'], roots)

    def test_fa54_evidence_repo_mismatch_and_idempotent_prepare(self):
        packet = self.packet()
        self.assertEqual(packet, self.packet())
        candidate = inventory_candidate(packet)
        candidate['evidence'] = [{'id': 'analysis:decline:evidence:balance',
                                  'source_id': qualified('backend', 'data_field:src/model.ts:Client.balance'),
                                  'repo_id': 'frontend', 'path': 'src/model.ts', 'kind': 'CODE',
                                  'sha256': packet['source_manifest']['@frontend/src/model.ts']['sha256'],
                                  'location': {'type': 'lines', 'start': 1, 'end': 1}, 'quote': 'interface Client',
                                  'supports': 'declaration', 'method': 'EXTRACTED', 'confidence': 1, 'validity': 'VALID'}]
        result = feature.validate(self.coordinator, 'decline', candidate)
        self.assertEqual(2, result['exit_code'])
        self.assertTrue(any('different repository' in d for d in result['diagnostics']))

    def test_fa55_57_apply_no_source_write_or_execution(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}
        packet = self.packet(); candidate = inventory_candidate(packet)
        self.assertTrue(feature.apply(self.coordinator, 'decline', candidate)['valid'])
        for path, content in before.items():
            self.assertEqual(content, Path(path).read_bytes())

    def test_fa58_mixed_snapshot_rejected(self):
        real = feature.source_inventory
        calls = 0
        def racing(root):
            nonlocal calls
            calls += 1
            result = real(root)
            if calls == 4:
                result[0]['new.ts'] = {'sha256': 'changed', 'kind': 'CODE', 'bytes': 1, 'supported': True}
            return result
        with patch('kgmaker.feature.source_inventory', side_effect=racing):
            with self.assertRaises(AnalysisError):
                snapshot_workspace(self.manifest)

    def test_cli_workspace_prepare_and_schema(self):
        for args in [
            ['feature', 'prepare', '--workspace', str(self.manifest), '--requirement', 'requirement.md', '--id', 'decline'],
            ['schema', 'inspect', '--workspace', str(self.manifest), '--repo', 'backend'],
            ['scan', '--workspace', str(self.manifest)]]:
            output = io.StringIO()
            with patch('sys.argv', ['kgmaker', *args, '--root', str(self.coordinator)]), redirect_stdout(output):
                with self.assertRaises(SystemExit) as code:
                    main()
            self.assertEqual(0, code.exception.code, output.getvalue())

    def test_overlap_duplicate_and_traversal_manifest_rejected(self):
        self.config['repositories'][1]['path'] = 'backend/src'; write_json(self.manifest, self.config)
        with self.assertRaises(AnalysisError):
            load_workspace(self.manifest)

    def test_fa63_test_sql_mismatch_and_fa51_fixture_impact(self):
        _, coverage, _, graph, _ = snapshot_workspace(self.manifest)
        self.assertTrue(any('Test data/schema mismatch' in d and 'old_decline' in d for d in coverage['limitations']))
        paths = impact_paths(graph, qualified('tests', 'file:e2e/fixture.ts:fixture.ts'))['paths']
        self.assertTrue(any('test_case' in path['entity_ids'][-1] for path in paths))

    def test_workspace_data_check_and_report_are_valid(self):
        from kgmaker.data_check import data_check
        from kgmaker.analysis_model import INPUT_METADATA
        packet = self.packet()
        spec = {'schema_version': 1, 'analysis_id': 'decline', 'requirement_hash': packet['requirement_hash'],
                'requirements': [{'id': 'analysis:decline:requirement:input', 'text': 'decline', 'kind': 'InputRequirement', 'source_quote': 'decline'}],
                'inputs': [{'id': 'analysis:decline:input:decline', 'name': 'decline',
                            'requirement_ids': ['analysis:decline:requirement:input'],
                            'candidate_entity_ids': [qualified('backend', 'data_field:src/model.kt:ExposureOutput.decline')],
                            **{k: None for k in INPUT_METADATA}}]}
        result = data_check(self.coordinator, 'decline', spec)
        self.assertTrue(result['valid'], result)
        self.assertEqual('backend', result['candidate']['evidence'][0]['repo_id'])
        self.assertIn('MIGRATION_DERIVED', result['report'])
        self.assertIn('Schema: backend', result['report'])
        self.assertTrue(feature.apply(self.coordinator, 'decline', result['candidate'])['valid'])

    def test_fa49_generation_origin_and_stale_contract(self):
        from kgmaker.analysis_model import file_hash
        metadata = {'source_contract': {'repo_id': 'backend', 'path': 'contracts/exposure.json',
                                       'sha256': file_hash(self.root / 'backend/contracts/exposure.json')},
                    'generated_files': ['generated/client.ts']}
        write_json(self.root / 'frontend/generation.json', metadata)
        self.config['services'][0]['generated_clients'] = [{'repo_id': 'frontend', 'path': 'generated/client.ts',
                                                           'metadata_path': 'generation.json', 'consumers': ['src/page.tsx']}]
        write_json(self.manifest, self.config)
        graph = snapshot_workspace(self.manifest)[3]
        self.assertTrue(any(e.kind == 'depends_on_contract' for e in graph.edges))
        (self.root / 'backend/contracts/exposure.json').write_text((self.root / 'backend/contracts/exposure.json').read_text() + '\n')
        _, coverage, _, graph, _ = snapshot_workspace(self.manifest)
        self.assertTrue(any('contract version mismatch' in d for d in coverage['limitations']))
        self.assertFalse(any(e.kind == 'depends_on_contract' for e in graph.edges))

    def test_comment_call_not_confirmed(self):
        (self.root / 'frontend/src/page.tsx').write_text("// fetch('/api/exposure');\nconst example = \"fetch('/api/exposure')\";\n")
        graph = snapshot_workspace(self.manifest)[3]
        frontend = qualified('frontend', 'file:src/page.tsx:page.tsx')
        self.assertFalse(any(e.target == frontend and e.kind == 'sent_to' for e in graph.edges))

    def test_disk_cache_survives_process_cache_clear_and_validation_is_read_only(self):
        snapshot_workspace(self.manifest, cache_root=self.coordinator, persist_cache=True)
        _REPO_CACHE.clear()
        with patch('kgmaker.feature.current_graph', side_effect=AssertionError('unchanged repo reparsed')):
            snapshot_workspace(self.manifest, cache_root=self.coordinator)
        packet = self.packet()
        before = {str(p): p.read_bytes() for p in self.coordinator.rglob('*') if p.is_file()}
        feature.validate(self.coordinator, 'decline', inventory_candidate(packet))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.coordinator.rglob('*') if p.is_file()})

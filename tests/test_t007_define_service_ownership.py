import copy
import tempfile
import unittest
from pathlib import Path

from kgmaker.analysis_model import AnalysisError, write_json
from kgmaker.workspace import load_workspace, resolve_service_ownership


class T007ServiceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('backend', 'shared'):
            (self.root / name).mkdir()
        self.manifest = self.root / 'workspace.json'
        self.service = {'id': 'orders', 'backend_repo': 'backend', 'frontend_repos': [],
                        'test_repos': [], 'contract': {'repo_id': 'backend', 'path': 'api.json'}}
        self.payload = {
            'schema_version': 1, 'workspace_id': 'example',
            'repositories': [
                {'id': 'backend', 'role': 'backend', 'path': 'backend'},
                {'id': 'shared', 'role': 'shared', 'path': 'shared'},
            ],
            'services': [copy.deepcopy(self.service),
                         {**copy.deepcopy(self.service), 'id': 'billing'}],
            'service_ownership': {'schema_version': 1, 'services': [
                {'id': 'orders', 'roots': [{'repo_id': 'backend', 'path': 'orders'}],
                 'modules': [{'repo_id': 'backend', 'id': 'com.example.orders'}],
                 'external_systems': [{'id': 'ledger'}]},
                {'id': 'billing', 'roots': [{'repo_id': 'backend', 'path': 'billing'}],
                 'modules': [{'repo_id': 'backend', 'id': 'com.example.billing'}],
                 'external_systems': [{'id': 'ledger'}]},
            ]},
        }
        write_json(self.manifest, self.payload)

    def test_ac01_two_declared_services_and_shared_library_is_unassigned(self):
        workspace = load_workspace(self.manifest)
        declaration = workspace['service_ownership']
        self.assertEqual({'orders', 'billing'}, {item['id'] for item in declaration['services']})
        self.assertEqual('RESOLVED', resolve_service_ownership(
            {'repo_id': 'backend', 'path': 'orders/OrderService.kt', 'module': 'com.example.orders', 'context_id': 'jvm:orders'},
            declaration, context_id='jvm:orders')["status"])
        shared = resolve_service_ownership(
            {'repo_id': 'shared', 'path': 'src/DateUtil.kt', 'module': 'com.example.shared', 'context_id': 'jvm:shared'},
            declaration, context_id='jvm:shared')
        self.assertEqual('UNASSIGNED', shared['status'])
        self.assertIsNone(shared['owner_id'])

    def test_ac02_overlapping_roots_and_module_mapping_remain_ambiguous(self):
        declaration = copy.deepcopy(self.payload['service_ownership'])
        declaration['services'][1]['roots'] = [{'repo_id': 'backend', 'path': 'orders/internal'}]
        declaration['services'][1]['modules'] = [{'repo_id': 'backend', 'id': 'com.example.orders'}]
        result = resolve_service_ownership(
            {'repo_id': 'backend', 'path': 'orders/internal/Payment.kt', 'module': 'com.example.orders', 'context_id': 'jvm:orders'},
            declaration, context_id='jvm:orders')
        self.assertEqual('AMBIGUOUS', result['status'])
        self.assertIsNone(result['owner_id'])
        self.assertEqual(['billing', 'orders'], result['candidate_owner_ids'])

    def test_ac03_legacy_manifest_without_ownership_preserves_service_identity(self):
        legacy = copy.deepcopy(self.payload)
        legacy.pop('service_ownership')
        write_json(self.manifest, legacy)
        loaded = load_workspace(self.manifest)
        self.assertEqual('orders', loaded['services'][0]['id'])
        self.assertNotIn('service_ownership', loaded)

    def test_ac04_invalid_ownership_is_rejected_without_manifest_mutation(self):
        invalid = copy.deepcopy(self.payload)
        invalid['service_ownership']['services'][1]['id'] = 'orders'
        write_json(self.manifest, invalid)
        before = self.manifest.read_bytes()
        with self.assertRaises(AnalysisError):
            load_workspace(self.manifest)
        self.assertEqual(before, self.manifest.read_bytes())

    def test_ac05_resolution_preserves_selected_context_and_never_guesses(self):
        declaration = self.payload['service_ownership']
        with self.assertRaises(AnalysisError):
            resolve_service_ownership(
                {'repo_id': 'backend', 'path': 'orders/OrderService.kt', 'context_id': 'other'},
                declaration, context_id='jvm:orders')
        result = resolve_service_ownership(
            {'repo_id': 'backend', 'path': 'unmapped/OrderService.kt', 'module': 'unknown', 'context_id': 'jvm:unmapped'},
            declaration, context_id='jvm:unmapped')
        self.assertEqual('UNASSIGNED', result['status'])
        self.assertEqual('jvm:unmapped', result['context_id'])
        self.assertEqual([], result['external_system_ids'])
        self.assertEqual('ledger', resolve_service_ownership(
            {'repo_id': 'backend', 'path': 'orders/OrderService.kt', 'module': None, 'context_id': 'jvm:orders'},
            declaration, context_id='jvm:orders')['external_system_ids'][0])
        repo_scoped = copy.deepcopy(declaration)
        repo_scoped['services'][0]['roots'] = []
        result = resolve_service_ownership(
            {'repo_id': 'shared', 'path': 'src/Order.kt', 'module': 'com.example.orders',
             'context_id': 'jvm:shared'}, repo_scoped, context_id='jvm:shared')
        self.assertEqual('UNASSIGNED', result['status'])

    def test_duplicate_service_identity_is_invalid_even_with_different_roots(self):
        invalid = copy.deepcopy(self.payload)
        invalid['services'][1]['id'] = invalid['services'][0]['id']
        write_json(self.manifest, invalid)
        with self.assertRaises(AnalysisError):
            load_workspace(self.manifest)


if __name__ == '__main__':
    unittest.main()

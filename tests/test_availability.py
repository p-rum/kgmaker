import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA, file_hash, inventory_candidate, write_json
from kgmaker.data_check import data_check


class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'Account.kt').write_text('data class Account(val balance: Double)\n')
        (self.root / 'requirement.md').write_text('Use the balance input.')
        self.entity = 'data_field:Account.kt:Account.balance'
        self.input_id = 'analysis:audit:input:balance'
        self.metadata = {key: 'N/A' for key in INPUT_METADATA}
        self.metadata.update({'definition': 'Current available balance', 'data_type': 'Double',
                              'unit': 'money', 'currency': 'CZK', 'keys': ['accountId'],
                              'quality': ['nonnegative'], 'fallbacks': [], 'nullable': False,
                              'freshness': 'PT1H', 'as_of': 'observation collection time'})
        self.observation = {'schema_version': 1, 'kind': 'SUPPLIED_DATA_OBSERVATION', 'entity_id': self.entity,
                            'scope': 'fixture sandbox account 1 only', 'value': 100.0,
                            'source_hashes': {'Account.kt': file_hash(self.root / 'Account.kt')},
                            'metadata': self.metadata, 'collected_at': datetime.now(timezone.utc).isoformat(),
                            'max_age_seconds': 3600}
        write_json(self.root / 'observation.json', {'observation': self.observation,
                                                   'closed': {'type': 'object', 'additionalProperties': False,
                                                              'properties': {'balance': {'type': 'number'}}}})
        packet = feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        candidate = inventory_candidate(packet)
        candidate['questions'] = [{'id': 'analysis:audit:question:mapping', 'text': 'Approve this exact input mapping?',
                                  'owner_role': 'Analyst', 'status': 'OPEN', 'requirement_ids': [candidate['requirements'][0]['id']], 'blocking': True}]
        feature.apply(self.root, 'audit', candidate)
        answer = {'input_id': self.input_id, 'entity_id': self.entity, 'metadata': self.metadata}
        self.packet = feature.revise(self.root, 'audit', {'answers': [{'question_id': 'analysis:audit:question:mapping',
                                       'decision_id': 'mapping', 'answer': json.dumps(answer),
                                       'revision': 1, 'approval_status': 'APPROVED'}]})
        self.candidate = inventory_candidate(self.packet)
        self.candidate['evidence'] = [self.evidence()]
        self.candidate['input_requirements'] = [self.input()]

    def evidence(self):
        return {'id': 'analysis:audit:evidence:observation', 'source_id': 'observation.json',
                'kind': 'CONTRACT', 'path': 'observation.json', 'sha256': file_hash(self.root / 'observation.json'),
                'location': {'type': 'json_pointer', 'pointer': '/observation'}, 'value': self.observation,
                'supports': 'Explicit scoped supplied observation', 'method': 'EXTRACTED', 'confidence': 1, 'validity': 'VALID'}

    def input(self):
        return {'id': self.input_id, 'name': 'balance', **self.metadata,
                'requirement_ids': ['analysis:audit:requirement:original'], 'source_ids': [self.entity],
                'evidence_ids': ['analysis:audit:evidence:observation'], 'dependency_ids': [], 'question_ids': [],
                'availability': 'AVAILABLE', 'acquisition': 'EXISTING', 'usability': 'FIT',
                'verification_scope': self.observation['scope'], 'next_step': 'Reuse only within observed scope',
                'owner_role': 'Analyst', 'transformation': None,
                'availability_proof': {'kind': 'OBSERVED_VALUE_PATH', 'source_entity_id': self.entity,
                                       'target_entity_id': self.entity, 'observation_evidence_id': 'analysis:audit:evidence:observation',
                                       'mapping_decision_id': 'mapping'}}

    def test_observed_approved_input_available(self):
        result = feature.validate(self.root, 'audit', self.candidate)
        self.assertTrue(result['valid'], result)
        self.assertTrue(feature.apply(self.root, 'audit', self.candidate)['valid'])

    def test_dto_or_migration_declaration_alone_not_available(self):
        candidate = copy.deepcopy(self.candidate)
        candidate['input_requirements'][0].pop('availability_proof')
        self.assertEqual(2, feature.validate(self.root, 'audit', candidate)['exit_code'])

    def test_scoped_contract_absence_not_bankwide_absence(self):
        candidate = copy.deepcopy(self.candidate)
        closed = json.loads((self.root / 'observation.json').read_text())['closed']
        candidate['evidence'][0].update({'location': {'type': 'json_pointer', 'pointer': '/closed'}, 'value': closed})
        item = candidate['input_requirements'][0]
        item.update({'availability': 'CONFIRMED_MISSING', 'usability': 'INCOMPATIBLE',
                     'verification_scope': 'Only contract ./observation.json#/closed',
                     'availability_proof': {'kind': 'CLOSED_CONTRACT_ABSENCE', 'evidence_id': 'analysis:audit:evidence:observation', 'field': 'maturity'}})
        self.assertTrue(feature.validate(self.root, 'audit', candidate)['valid'])
        item['verification_scope'] = 'Missing in the whole bank'
        self.assertEqual(2, feature.validate(self.root, 'audit', candidate)['exit_code'])

    def test_source_mutation_invalidates_positive_proof(self):
        (self.root / 'Account.kt').write_text('data class Account(val balance: String)\n')
        result = feature.validate(self.root, 'audit', self.candidate)
        self.assertEqual(3, result['exit_code'])

    def test_unapproved_or_different_business_mapping_rejected(self):
        candidate = copy.deepcopy(self.candidate)
        candidate['input_requirements'][0]['definition'] = 'All customer wealth'
        self.assertEqual(2, feature.validate(self.root, 'audit', candidate)['exit_code'])
        candidate = copy.deepcopy(self.candidate)
        candidate['input_requirements'][0]['availability_proof']['mapping_decision_id'] = 'nonexistent'
        self.assertEqual(2, feature.validate(self.root, 'audit', candidate)['exit_code'])

    def test_partial_metadata_and_expired_observation(self):
        self.observation['metadata'] = {k: v for k, v in self.metadata.items() if k != 'unit'}
        write_json(self.root / 'observation.json', {'observation': self.observation})
        packet = feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        candidate = inventory_candidate(packet)
        candidate['evidence'] = [self.evidence()]
        item = self.input(); item.update({'availability': 'PARTIAL', 'usability': 'UNASSESSED'})
        candidate['input_requirements'] = [item]
        self.assertTrue(feature.validate(self.root, 'audit', candidate)['valid'])
        self.observation['collected_at'] = '2020-01-01T00:00:00Z'
        write_json(self.root / 'observation.json', {'observation': self.observation})
        packet = feature.prepare(self.root, 'requirement.md', 'audit', 100000)
        candidate = inventory_candidate(packet); candidate['evidence'] = [self.evidence()]
        candidate['input_requirements'] = [item]
        self.assertEqual(3, feature.validate(self.root, 'audit', candidate)['exit_code'])

    def test_data_check_classifies_proof_without_llm(self):
        spec = {'schema_version': 1, 'analysis_id': 'audit', 'requirement_hash': self.packet['requirement_hash'],
                'requirements': [{'id': 'analysis:audit:requirement:original', 'text': 'Use balance',
                                  'kind': 'InputRequirement', 'source_quote': 'balance'}],
                'evidence_references': [{'id': 'analysis:audit:evidence:observation', 'path': 'observation.json',
                                         'location': {'type': 'json_pointer', 'pointer': '/observation'}, 'value': self.observation}],
                'inputs': [{'id': self.input_id, 'name': 'balance', **self.metadata,
                            'requirement_ids': ['analysis:audit:requirement:original'],
                            'candidate_entity_ids': [self.entity], 'availability_proof': self.input()['availability_proof']}]}
        result = data_check(self.root, 'audit', spec)
        self.assertEqual(0, result['exit_code'], result)
        self.assertEqual('AVAILABLE', result['candidate']['input_requirements'][0]['availability'])
        self.assertFalse(result['ambiguity_queue'])

    def test_explicit_approved_missing_decision_is_scoped(self):
        candidate = copy.deepcopy(self.candidate)
        candidate['questions'] = [{'id': 'analysis:audit:question:missing', 'text': 'Is this feed input absent?',
                                  'owner_role': 'Data owner', 'status': 'OPEN', 'blocking': True,
                                  'requirement_ids': ['analysis:audit:requirement:original']}]
        self.assertTrue(feature.apply(self.root, 'audit', candidate)['valid'])
        scope = 'Only declared sandbox external feed v1'
        decision = {'question_id': 'analysis:audit:question:missing', 'decision_id': 'missing',
                    'answer': json.dumps({'input_id': self.input_id, 'scope': scope, 'confirmed_missing': True}),
                    'revision': 1, 'approval_status': 'APPROVED'}
        packet = feature.revise(self.root, 'audit', {'answers': [decision]})
        candidate = inventory_candidate(packet)
        candidate['evidence'] = [{'id': 'analysis:audit:evidence:missing', 'source_id': 'missing',
                                  'kind': 'HUMAN_DECISION', 'supports': 'Explicit scoped absence decision',
                                  'method': 'EXTRACTED', 'confidence': 1, 'validity': 'VALID', **decision}]
        item = self.input()
        item.update({'availability': 'CONFIRMED_MISSING', 'usability': 'INCOMPATIBLE',
                     'verification_scope': scope, 'evidence_ids': ['analysis:audit:evidence:missing'],
                     'availability_proof': {'kind': 'APPROVED_MISSING', 'decision_id': 'missing', 'scope': scope}})
        candidate['input_requirements'] = [item]
        self.assertTrue(feature.validate(self.root, 'audit', candidate)['valid'])
        item['availability_proof']['scope'] = 'All bank data'
        self.assertEqual(2, feature.validate(self.root, 'audit', candidate)['exit_code'])

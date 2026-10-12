import copy
import tempfile
import unittest
from pathlib import Path
from kgmaker.flyway import migration_plan, version
from kgmaker.schema_replay import reconstruct, schema_diff, statements, _CHECKPOINTS


class FlywayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dir = self.root / 'src/main/resources/db/migration'; self.dir.mkdir(parents=True)
        self.write('V1__initial.sql', 'CREATE TABLE client (id bigint PRIMARY KEY, old_balance numeric(12,2), obsolete text);')
        self.write('V2__rename.sql', 'ALTER TABLE client RENAME COLUMN old_balance TO balance; ALTER TABLE client DROP COLUMN obsolete;')
        self.write('V10__type.sql', 'ALTER TABLE client ALTER COLUMN balance TYPE numeric(18,4), ALTER COLUMN balance SET NOT NULL;')

    def write(self, name, text):
        (self.dir / name).write_text(text)

    def test_fa36_37_order_lifecycle_and_constraints(self):
        state = reconstruct(self.root)
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertEqual(['1', '2', '10'], [m['version'] for m in state['migrations']])
        self.assertNotIn('column:public.client.old_balance', state['objects'])
        self.assertNotIn('column:public.client.obsolete', state['objects'])
        column = state['objects']['column:public.client.balance']
        self.assertEqual('numeric ( 18 , 4 )', column['data_type'])
        self.assertFalse(column['nullable'])
        self.assertEqual([['public', 'client', 'old_balance']], column['previous_names'])
        self.assertTrue(any(o['lifecycle'] == 'DROPPED' for o in state['history']))
        self.assertFalse(state['deployment_verified'])
        self.assertEqual('MIGRATION_DERIVED', state['provenance'])

    def test_fa38_repeatables_and_historical_diff(self):
        self.write('R__balance_view.sql', 'CREATE OR REPLACE VIEW balances AS SELECT balance FROM client;')
        latest = reconstruct(self.root)
        self.assertEqual('COMPLETE', latest['status'], latest['diagnostics'])
        self.assertIn('view:public.balances', latest['objects'])
        historical = reconstruct(self.root, {'target': '2'})
        self.assertEqual('PARTIAL', historical['status'])
        self.assertNotIn('view:public.balances', historical['objects'])
        self.assertFalse(schema_diff(self.root, {}, '2', 'latest')['exact'])

    def test_fa39_44_equivalent_versions_but_no_gap_guess(self):
        self.assertEqual(version('01.0'), version('1'))
        self.assertEqual('COMPLETE', reconstruct(self.root)['status'])
        self.write('V01_0__duplicate.sql', 'CREATE TABLE nope(id bigint);')
        self.assertFalse(migration_plan(self.root)['valid'])
        self.assertEqual('INVALID', reconstruct(self.root)['status'])

    def test_fa40_placeholders_quoting_and_search_path(self):
        self.write('V20__schema.sql', 'CREATE SCHEMA ${tenant}; SET search_path TO ${tenant}; CREATE TABLE "Mixed" ("Amount" integer);')
        partial = reconstruct(self.root)
        self.assertEqual('PARTIAL', partial['status'])
        state = reconstruct(self.root, {'placeholders': {'tenant': 'tenant'}})
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertIn('column:tenant.Mixed.Amount', state['objects'])

    def test_fa41_61_unknown_body_and_literals(self):
        self.write('V20__body.sql', "-- CREATE TABLE fake(a int);\nDO $body$ BEGIN RAISE NOTICE 'x; CREATE TABLE fake(a int)'; END; $body$;\nINSERT INTO client(id) VALUES(1);")
        state = reconstruct(self.root)
        self.assertEqual('PARTIAL', state['status'])
        self.assertNotIn('table:public.fake', state['objects'])
        self.assertEqual(2, len(statements("SELECT 'x;y'; /* a; /* b; */ */ DO $$ SELECT ';'; $$;")))
        self.assertTrue(any(op['data_effect_only'] for op in state['operations']))

    def test_fa43_checkpoint_replay_matches_full_after_old_change(self):
        _CHECKPOINTS.clear()
        first = reconstruct(self.root)
        again = reconstruct(self.root)
        self.assertTrue(all(c['reused'] for c in again['checkpoints']))
        self.write('V1__initial.sql', 'CREATE TABLE client (id bigint PRIMARY KEY, old_balance numeric(12,2), obsolete text, added int);')
        incremental, full = reconstruct(self.root), reconstruct(self.root, use_cache=False)
        self.assertFalse(any(c['reused'] for c in incremental['checkpoints']))
        for key in ('objects', 'history', 'operations', 'diagnostics'):
            self.assertEqual(incremental[key], full[key])

    def test_fa62_baseline_script_and_undo(self):
        self.write('B2__baseline.sql', 'CREATE TABLE client(id bigint PRIMARY KEY, balance numeric(12,2));')
        self.write('U10__undo.sql', 'DROP TABLE client;')
        state = reconstruct(self.root, {'mode': 'baseline_script'})
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertEqual(['BASELINE', 'VERSIONED'], [m['kind'] for m in state['migrations']])
        self.assertIn('table:public.client', state['objects'])

    def test_constraints_indexes_views_and_table_rename(self):
        self.write('V20__objects.sql', 'CREATE UNIQUE INDEX idx ON client(id); ALTER INDEX idx RENAME TO idx2; ALTER TABLE client ADD CONSTRAINT balance_check CHECK(balance >= 0); ALTER TABLE client RENAME TO customer;')
        state = reconstruct(self.root)
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertIn('table:public.customer', state['objects'])
        self.assertIn('column:public.customer.balance', state['objects'])
        self.assertIn('index:public.idx2', state['objects'])

    def test_fa64_independent_streams_have_no_version_collision(self):
        second = self.root / 'other'; second.mkdir()
        (second / 'V1__other.sql').write_text('CREATE TABLE client(other_id integer);')
        first = reconstruct(self.root)
        other = reconstruct(self.root, {'locations': ['other'], 'stream_id': 'other'})
        self.assertEqual('COMPLETE', other['status'])
        self.assertNotEqual(first['objects']['table:public.client']['id'], other['objects']['table:public.client']['id'])

    def test_quoted_dot_does_not_collide_with_qualified_name(self):
        self.write('V20__quoted.sql', 'CREATE TABLE "a.b" (id int); CREATE SCHEMA a; CREATE TABLE a.b(id int);')
        state = reconstruct(self.root)
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertIn('table:public.a%2Eb', state['objects'])
        self.assertIn('table:a.b', state['objects'])

    def test_drop_recreate_has_new_identity(self):
        old = reconstruct(self.root)['objects']['table:public.client']['id']
        self.write('V20__recreate.sql', 'DROP TABLE client; CREATE TABLE client(new_id int);')
        state = reconstruct(self.root)
        self.assertEqual('COMPLETE', state['status'], state['diagnostics'])
        self.assertNotEqual(old, state['objects']['table:public.client']['id'])

    def test_configuration_profile_literals_and_no_credentials(self):
        resources = self.root / 'src/main/resources'
        (resources / 'application.properties').write_text('spring.flyway.target=2\nspring.flyway.password=DO_NOT_LEAK\n')
        (resources / 'application-test.properties').write_text('spring.flyway.target=10\n')
        plan = migration_plan(self.root, {'profile': 'test'})
        self.assertEqual('10', plan['config']['target'])
        self.assertNotIn('DO_NOT_LEAK', str(plan))
        (self.root / 'build.gradle.kts').write_text('flyway {\n locations = arrayOf("src/main/resources/db/migration")\n}\n')
        plan = migration_plan(self.root, {'target': 'latest'})
        self.assertEqual('COMPLETE', reconstruct(self.root, {'target': 'latest'})['status'])

    def test_fa45_schema_mapping_precision_nullability_and_absent_column(self):
        from kgmaker.feature import current_graph
        from kgmaker.schema_replay import schema_mappings
        (self.root / 'Client.kt').write_text('''@Entity
@Table(name="client")
data class Client(
  @Column(name="balance", precision=12, scale=2) val balance: BigDecimal?,
  @Column(name="missing") val missing: Int
)
''')
        graph = current_graph(self.root)[0]
        edges, diagnostics = schema_mappings(self.root, reconstruct(self.root), graph)
        self.assertTrue(any(e.kind == 'persisted_in' for e in edges))
        reasons = ' '.join(d['reason'] for d in diagnostics)
        self.assertIn('precision mismatch', reasons)
        self.assertIn('scale mismatch', reasons)
        self.assertIn('nullability mismatch', reasons)
        self.assertIn('absent from selected schema', reasons)


if __name__ == '__main__':
    unittest.main()

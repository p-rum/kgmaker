"""S06-W04 explicit migration/persistence realm isolation; no database execution."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError, write_json
from kgmaker.scanner import scan_repository
from kgmaker.schema_replay import reconstruct, graph_entities, schema_mappings
from kgmaker.workspace import snapshot_workspace, _REPO_CACHE, qualified


def two_datasources(tmp_path):
    app = tmp_path / 'app'; app.mkdir()
    subprocess.run(['git', 'init', '-q', str(app)], check=True)
    for folder, first, second in [('one', 'bigint', 'text'), ('two', 'text', 'bigint')]:
        migrations = app / 'src/main/resources' / folder; migrations.mkdir(parents=True)
        (migrations / 'V1__base.sql').write_text(f'CREATE TABLE public.orders (id {first} NOT NULL);\n')
        (migrations / 'V2__extra.sql').write_text(f'ALTER TABLE public.orders ADD COLUMN external_id {second};\n')
    (app / 'Order.kt').write_text('@Entity\n@Table(name="orders", schema="public")\ndata class Order(@Column(name="id") val id: Long)\n')
    configs = [dict(database_id='orders-one', stream_id='main', locations=['src/main/resources/one'], target='1'),
               dict(database_id='orders-two', stream_id='main', locations=['src/main/resources/two'], target='2')]
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, dict(schema_version=1, workspace_id='realms', repositories=[
        dict(id='app', role='backend', path='app', flyway=configs)],
        services=[dict(id='orders', backend_repo='app', frontend_repos=[], test_repos=[],
                       contract=dict(repo_id='app', path='api.json'))],
        service_ownership=dict(schema_version=1, services=[dict(id='orders',
            roots=[dict(repo_id='app', path='src/main')], modules=[dict(repo_id='app', id='app')], external_systems=[])])))
    return app, configs, manifest


def test_two_databases_can_share_stream_name_without_cross_realm_bindings(tmp_path):
    app, configs, manifest = two_datasources(tmp_path)
    real_popen = subprocess.Popen
    def read_only_git(argv, *args, **kwargs):
        assert Path(argv[0]).name == 'git', argv
        return real_popen(argv, *args, **kwargs)
    with patch('subprocess.Popen', side_effect=read_only_git):
        _, coverage, _, graph, _ = snapshot_workspace(manifest)
    schemas = coverage['schemas']['app']
    assert {(s['config']['database_id'], s['config']['stream_id']) for s in schemas} == {
        ('orders-one', 'main'), ('orders-two', 'main')}
    by_database = {s['config']['database_id']: s for s in schemas}
    assert 'column:public.orders.external_id' not in by_database['orders-one']['objects']
    assert 'column:public.orders.external_id' in by_database['orders-two']['objects']
    assert not any(e.kind == 'persisted_in' for e in graph.edges)  # source-only field has no realm proof


def test_workspace_keeps_table_level_foreign_keys_for_two_explicit_realms(tmp_path):
    app, configs, manifest = two_datasources(tmp_path)
    for config, sql_type in zip(configs, ('bigint', 'text'), strict=True):
        path = app / config['locations'][0] / 'V1__base.sql'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('ALTER TABLE orders ADD CONSTRAINT orders_key UNIQUE(id);\n'
                         f'CREATE TABLE invoices (parent {sql_type}, '
                         'CONSTRAINT invoice_order FOREIGN KEY(parent) REFERENCES orders(id));\n')
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    assert all(replay['status'] == 'COMPLETE' for replay in coverage['schemas']['app'])
    table_references = [edge for edge in graph.edges if edge.kind == 'foreign_key_to']
    assert len(table_references) == 2
    assert all(edge.source.startswith('repo:app:') and edge.target.startswith('repo:app:') for edge in table_references)
    assert not any(edge.kind == 'foreign_key_references_column' for edge in graph.edges)
    assert not any((node.metadata or {}).get('foreign_key_targets') for node in graph.nodes)


def test_replayed_schema_nodes_expose_structured_realm_and_target_provenance(tmp_path):
    app, configs, _ = two_datasources(tmp_path)
    for config in configs:
        schema = reconstruct(app, config)
        nodes, _ = graph_entities(schema)
        table = next(n for n in nodes if n.kind == 'db_table')
        realm = table.metadata['persistence_realm']
        assert realm['database_id'] == config['database_id'] and realm['stream_id'] == 'main'
        assert realm['schema'] == 'public' and realm['target'] == config['target']
        assert {'database_id', 'stream_id'} <= set(realm['explicit_keys'])
        assert realm['config_fingerprint']


def test_legacy_source_only_mapping_never_chooses_globally_unique_schema(tmp_path):
    app, configs, _ = two_datasources(tmp_path)
    graph = scan_repository(app)
    schema = reconstruct(app, configs[0])
    before = deepcopy(graph.to_dict())
    edges, diagnostics = schema_mappings(app, schema, graph)
    assert not any(e.kind == 'persisted_in' for e in edges)
    assert any(d.get('code') == 'PERSISTENCE_REALM_UNPROVEN' for d in diagnostics)
    assert graph.to_dict() == before


def test_duplicate_exact_database_stream_pair_preserves_existing_cache(tmp_path):
    app, configs, manifest = two_datasources(tmp_path)
    data = json.loads(manifest.read_text()); data['repositories'][0]['flyway'] = [configs[0], configs[0]]
    write_json(manifest, data)
    before = deepcopy(_REPO_CACHE)
    with pytest.raises(AnalysisError, match='Duplicate migration'):
        snapshot_workspace(manifest)
    assert _REPO_CACHE == before


def test_shared_migration_path_keeps_two_distinct_realm_objects_and_operations(tmp_path):
    from kgmaker.feature import attach_schema
    app, configs, _ = two_datasources(tmp_path)
    configs[1]['locations'] = list(configs[0]['locations'])
    graph = scan_repository(app)
    for config in configs:
        graph = attach_schema(graph, reconstruct(app, config), app)
    tables = [n for n in graph.nodes if n.kind == 'db_table']
    assert len(tables) == 2
    assert {n.metadata['persistence_realm']['database_id'] for n in tables} == {'orders-one', 'orders-two'}
    operations = [n for n in graph.nodes if n.kind == 'migration_operation']
    assert len(operations) == 3 and len({n.id for n in operations}) == 3
    assert not any(e.kind == 'persisted_in' for e in graph.edges)


def test_delimiter_percent_and_dot_database_identities_do_not_collide(tmp_path):
    from kgmaker.feature import attach_schema
    app, configs, _ = two_datasources(tmp_path)
    pairs = [('a:b', 'c'), ('a', 'b:c'), ('a%3Ab', 'c'), ('a.b', 'c')]
    graph = scan_repository(app)
    for database, stream in pairs:
        config = dict(configs[0], database_id=database, stream_id=stream)
        graph = attach_schema(graph, reconstruct(app, config), app)
    tables = [n for n in graph.nodes if n.kind == 'db_table']
    assert len(tables) == 4 and len({n.id for n in tables}) == 4
    assert {(n.metadata['persistence_realm']['database_id'], n.metadata['persistence_realm']['stream_id'])
            for n in tables} == set(pairs)


@pytest.fixture(scope='module', params=['k1', 'k2'])
def actual_realm_workspace(tmp_path_factory, request):
    """Two genuine compiler contexts joined to distinct offline replay targets."""
    import os
    from kgmaker.inspection import command, inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    from test_t015_project_data_resources import jpa_api_jars
    home = Path(__file__).resolve().parents[1] / 'workers'
    backend = request.param
    try:
        command('jvm', home, kotlin_backend=backend)
        jars = jpa_api_jars()
        stdlib = home / 'jvm' / ('target-k2' if backend == 'k2' else 'target') / 'lib/kotlin-stdlib.jar'
        if not stdlib.is_file():
            raise WorkerError('Explicit pinned worker Kotlin stdlib unavailable', 'TOOLCHAIN_UNAVAILABLE')
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1'):
            pytest.fail(str(error))
        pytest.skip('actual persistence realm prerequisites: ' + str(error))
    app, configs, manifest = two_datasources(tmp_path_factory.mktemp('actual-realms-' + backend))
    (app / 'Order.kt').unlink()
    source = app / 'src/main/java/demo/RealmInput.java'; source.parent.mkdir(parents=True)
    source.write_text(r'''package demo;
import jakarta.persistence.Entity; import jakarta.persistence.Id; import jakarta.persistence.Table;
import jakarta.persistence.Column;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
@Entity @Table(name="orders", schema="public") class Order { @Id @Column(name="id") Long id; }
@Entity @Table(name="c", schema="\"a.b\"") class DotSchema { @Id @Column(name="id") Long id; }
@Entity @Table(name="\"b.c\"", schema="a") class DotTable { @Id @Column(name="id") Long id; }
interface OrderRepository extends JpaRepository<Order, Long> {
  @Query(value="select * from orders", nativeQuery=true) java.util.List<Order> nativeRows();
  @Query("select o from Order o") java.util.List<Order> entityRows();
}
''')
    anchor = app / 'src/main/kotlin/demo/RealmAnchor.kt'; anchor.parent.mkdir(parents=True)
    anchor.write_text('package demo\nclass RealmAnchor\n')
    for config in configs:
        path = app / config['locations'][0] / 'V1__base.sql'
        path.write_text(path.read_text() + 'CREATE TABLE "a.b".c (id bigint); CREATE TABLE a."b.c" (id bigint);\n')
        config['schemas'] = ['public', 'a.b', 'a']
    manifest_data = json.loads(manifest.read_text())
    manifest_data['repositories'][0]['flyway'] = configs
    write_json(manifest, manifest_data)
    contexts = []
    for index, config in enumerate(configs):
        result = inspect_jvm(app, home=home, kotlin_backend=backend, classpath=[*jars, str(stdlib)],
            repo_id='app', module='app', publish=True,
            build_context={'database_id': config['database_id'], 'schema_stream_id': config['stream_id'],
                           'persistence_schema': 'public' if index == 0 else None, 'flyway_target': config['target']})
        assert not any('.err.' in d.get('code', '') for d in result['diagnostics'])
        contexts.append(result['context']['id'])
    snapshot = snapshot_workspace(manifest)
    return app, configs, manifest, contexts, snapshot


def test_actual_compiler_contexts_join_only_their_own_replay_targets(actual_realm_workspace):
    app, configs, _, context_ids, snapshot = actual_realm_workspace
    graph = snapshot[3]
    nodes = {n.id: n for n in graph.nodes}
    proofs = {p['id']: p for p in graph.evidence}
    contexts = {c['id']: c for c in graph.contexts}
    selected = [c for c in graph.contexts if c.get('language') == 'jvm']
    assert len(selected) == 2
    bindings = [e for e in graph.edges if e.kind == 'resolves_to_schema_table'
                and (nodes[e.source].metadata or {}).get('logical_name') == 'orders']
    reads = [e for e in graph.edges if e.kind == 'query_reads' and nodes[e.target].kind == 'orm_table']
    assert len(bindings) == 2 and len(reads) == 2
    for edge in bindings + reads:
        target = edge.target if nodes[edge.target].kind == 'db_table' else next(
            e.target for e in bindings if e.source == edge.target and e.context_ids == edge.context_ids)
        realm = nodes[target].metadata['persistence_realm']
        ctx = contexts[edge.context_ids[0]]
        assert (realm['database_id'], realm['stream_id'], realm['target']) == (
            ctx['database_id'], ctx['schema_stream_id'], ctx['flyway_target'])
        assert realm['schema'] == 'public'
        assert all(proofs[p]['persistence_realm'] == realm for p in edge.evidence_ids)
        assert all(proofs[p]['persistence_selection']['database_id'] == realm['database_id'] for p in edge.evidence_ids)


def test_actual_replay_reprojection_is_idempotent_and_preserves_foreign_context(actual_realm_workspace):
    from kgmaker.feature import attach_schema
    from kgmaker.framework import augment_framework_graph
    from kgmaker.store import load_graph
    app, configs, _, _, _ = actual_realm_workspace
    local = load_graph(app)
    for config in configs:
        local = attach_schema(local, reconstruct(app, config), app)
    selected = [c for c in local.contexts if c.get('language') == 'jvm']
    compiler_before = deepcopy((local.symbols, local.call_sites, local.cfgs))
    with patch('subprocess.Popen', side_effect=AssertionError('reprojection must not run processes')):
        for ctx in selected:
            local = augment_framework_graph(app, local, ctx)
        once = local.to_dict()
        for ctx in selected:
            local = augment_framework_graph(app, local, ctx)
    assert local.to_dict() == once
    assert (local.symbols, local.call_sites, local.cfgs) == compiler_before
    foreign = selected[1]['id']
    before = deepcopy([e for e in local.edges if e.context_ids == (foreign,)])
    local = augment_framework_graph(app, local, selected[0])
    assert [e for e in local.edges if e.context_ids == (foreign,)] == before


def test_actual_resource_access_tracks_selected_realm_and_target(actual_realm_workspace):
    from kgmaker.workspace import load_workspace
    from kgmaker.data_resources import project_data_resources
    app, configs, manifest, _, snapshot = actual_realm_workspace
    graph = snapshot[3]
    for context in [c for c in graph.contexts if c.get('language') == 'jvm']:
        before = deepcopy(graph.to_dict())
        with patch('subprocess.Popen', side_effect=AssertionError('projection must remain offline')):
            view = project_data_resources(load_workspace(manifest), graph, source_coverage=snapshot[1],
                selected_contexts={('orders', 'app', 'app'): context['id']})
        reads = [e for e in view.edges if e.relation == 'reads']
        assert reads
        targets = {n.id: n for n in view.nodes}
        assert {targets[e.target].attributes['database_id'] for e in reads} == {context['database_id']}
        assert graph.to_dict() == before


def test_reprojection_preserves_another_framework_producer_in_same_context(tmp_path):
    from kgmaker.framework import augment_framework_graph
    from kgmaker.model import KnowledgeGraph, Node, Edge
    ctx = {'id': 'same-context', 'language': 'jvm', 'scope': 'production', 'framework_rule_versions': {}}
    proof = {'id': 'http-proof', 'kind': 'FRAMEWORK_DERIVED', 'source': 'caller', 'target': 'http-request',
             'relation': 'defines_http_request', 'rule': 'http-client-execution-1', 'context_ids': [ctx['id']]}
    edge = Edge('caller', 'http-request', 'defines_http_request', evidence_kind='FRAMEWORK_DERIVED',
                context_ids=(ctx['id'],), evidence_ids=('http-proof',))
    graph = KnowledgeGraph(3, str(tmp_path), 'now',
        [Node('caller', 'method', 'caller', 'Caller.java'),
         Node('http-request', 'http_request_definition', 'GET /orders', 'Caller.java')], [edge], {}, [ctx], [], [proof])
    result = augment_framework_graph(tmp_path, graph, ctx)
    assert edge in result.edges and proof in result.evidence
    assert next(n for n in result.nodes if n.id == 'http-request') == graph.nodes[1]
    assert not any(d.get('code') == 'PERSISTENCE_REALM_UNPROVEN' for d in result.diagnostics)


@pytest.mark.parametrize('mutation', ['missing_pair', 'partial_pair', 'wrong_target', 'wrong_schema',
    'invalid_selector', 'foreign_schema_metadata', 'malformed_explicit_keys', 'missing_schema_provenance',
    'wrong_display_name', 'tampered_realm_hash'])
def test_actual_missing_partial_or_foreign_proof_never_uses_unique_name(actual_realm_workspace, mutation):
    from dataclasses import replace
    from kgmaker.feature import attach_schema
    from kgmaker.framework import augment_framework_graph
    from kgmaker.store import load_graph
    app, configs, _, _, _ = actual_realm_workspace
    graph = load_graph(app)
    for config in configs:
        graph = attach_schema(graph, reconstruct(app, config), app)
    context = deepcopy(next(c for c in graph.contexts if c.get('database_id') == configs[0]['database_id']))
    if mutation == 'missing_pair':
        context.pop('database_id'); context.pop('schema_stream_id')
    elif mutation == 'partial_pair':
        context.pop('schema_stream_id')
    elif mutation == 'wrong_target':
        context['flyway_target'] = '2'
    elif mutation == 'wrong_schema':
        context['persistence_schema'] = 'archive'
    elif mutation == 'invalid_selector':
        context['persistence_schema'] = []
    else:
        changed = []
        for node in graph.nodes:
            metadata = deepcopy(node.metadata or {})
            realm = metadata.get('persistence_realm')
            if isinstance(realm, dict) and realm.get('database_id') == configs[0]['database_id']:
                if mutation == 'foreign_schema_metadata':
                    realm['database_id'] = configs[1]['database_id']
                elif mutation == 'malformed_explicit_keys':
                    realm['explicit_keys'] = None
                elif mutation == 'tampered_realm_hash':
                    realm['target'] = '999'
                elif mutation == 'wrong_display_name':
                    node = replace(node, name=node.name + '_foreign')
                else:
                    metadata.pop('persistence_realm')
                node = replace(node, metadata=metadata)
            changed.append(node)
        graph = replace(graph, nodes=changed)
    before = deepcopy(graph.to_dict())
    with patch('subprocess.Popen', side_effect=AssertionError('bounded proof replay must stay offline')):
        result = augment_framework_graph(app, graph, context)
    assert not any(e.kind in {'resolves_to_schema_table', 'resolves_to_schema_column'}
                   and e.context_ids == (context['id'],) for e in result.edges)
    assert graph.to_dict() == before


def test_public_replay_preserves_quoted_dot_components_despite_same_display_name(tmp_path):
    from dataclasses import replace
    from kgmaker.schema_replay import schema_node_realm
    folder = tmp_path / 'sql'; folder.mkdir()
    (folder / 'V1__dots.sql').write_text('CREATE TABLE "a.b".c (id bigint); CREATE TABLE a."b.c" (id bigint);')
    schema = reconstruct(tmp_path, dict(database_id='dots', stream_id='main', locations=['sql'], schemas=['a.b', 'a']))
    tables = [n for n in graph_entities(schema)[0] if n.kind == 'db_table']
    assert len(tables) == 2 and {n.name for n in tables} == {'a.b.c'}
    assert len({n.id for n in tables}) == 2
    assert {tuple(n.metadata['schema_object']) for n in tables} == {('a.b', 'c'), ('a', 'b.c')}
    assert all(schema_node_realm(n) is not None for n in tables)
    assert schema_node_realm(replace(tables[0], name='other.name')) is None
    changed = deepcopy(tables[0].metadata); changed['persistence_realm']['target'] = '999'
    assert schema_node_realm(replace(tables[0], metadata=changed)) is None


def test_actual_quoted_dot_binding_uses_components_not_flat_display(actual_realm_workspace):
    app, configs, _, _, snapshot = actual_realm_workspace
    graph = snapshot[3]; nodes = {n.id: n for n in graph.nodes}
    bindings = [e for e in graph.edges if e.kind == 'resolves_to_schema_table'
                and tuple((nodes[e.target].metadata or {}).get('schema_object', [])) in {('a.b', 'c'), ('a', 'b.c')}]
    assert len(bindings) == 2
    assert {tuple(nodes[e.target].metadata['schema_object']) for e in bindings} == {('a.b', 'c'), ('a', 'b.c')}
    assert {nodes[e.target].name for e in bindings} == {'a.b.c'}
    assert len({e.target for e in bindings}) == 2
    assert {nodes[e.target].metadata['persistence_realm']['database_id'] for e in bindings} == {configs[1]['database_id']}


def test_actual_two_persistence_units_choose_their_own_physical_realm(actual_realm_workspace, tmp_path):
    import shutil
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    from kgmaker.store import load_graph
    from kgmaker.framework import augment_framework_graph
    from test_t015_project_data_resources import jpa_api_jars
    original, configs, _, _, _ = actual_realm_workspace
    root = tmp_path / 'app'
    shutil.copytree(original, root, ignore=shutil.ignore_patterns('.kgmaker', '.git'))
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    meta = root / 'META-INF'; meta.mkdir()
    mapping_one = 'src/main/resources/orm-one.xml'
    mapping_two = 'src/main/resources/orm-two.xml'
    (meta / 'persistence.xml').write_text('''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
<persistence-unit name="unit-one"><mapping-file>src/main/resources/orm-one.xml</mapping-file></persistence-unit>
<persistence-unit name="unit-two"><mapping-file>src/main/resources/orm-two.xml</mapping-file></persistence-unit>
</persistence>''')
    (root / mapping_one).write_text('''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
<entity class="demo.Order"><table name="orders" schema="public"/><attributes><id name="id"><column name="id"/></id></attributes></entity>
</entity-mappings>''')
    (root / mapping_two).write_text('''<entity-mappings xmlns="https://jakarta.ee/xml/ns/persistence/orm" version="3.1">
<entity class="demo.Order"><table name="c" schema="&quot;a.b&quot;"/><attributes><id name="id"><column name="id"/></id></attributes></entity>
</entity-mappings>''')
    write_json(root / '.kgmaker/classification.json', {'schema_version': 1, 'overrides': [
        {'path': 'META-INF', 'scope': 'production', 'role': 'resource',
         'reason': 'Explicit production JPA descriptor location for this actual compiler fixture'}]})
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, dict(schema_version=1, workspace_id='two-pu', repositories=[
        dict(id='app', role='backend', path='app', flyway=configs)]))
    home = Path(__file__).resolve().parents[1] / 'workers'
    backend = next(c['kotlin_backend'] for c in load_graph(original).contexts if c.get('language') == 'jvm')
    # Context records identify the backend as K1_COMPATIBILITY/K2_ANALYSIS_API;
    # inspection input uses the public k1/k2 selector.
    backend = 'k2' if 'k2' in backend.lower() else 'k1'
    stdlib = home / 'jvm' / ('target-k2' if backend == 'k2' else 'target') / 'lib/kotlin-stdlib.jar'
    jars = [*jpa_api_jars(), str(stdlib)]
    for index, config in enumerate(configs):
        inspect_jvm(root, home=home, kotlin_backend=backend, classpath=jars,
            repo_id='app', module='app', publish=True,
            build_context={'database_id': config['database_id'], 'schema_stream_id': config['stream_id'],
                           'persistence_unit': 'unit-one' if index == 0 else 'unit-two',
                           'persistence_schema': 'public' if index == 0 else None, 'flyway_target': config['target']})
    _, _, _, graph, _ = snapshot_workspace(manifest)
    nodes = {n.id: n for n in graph.nodes}; proofs = {p['id']: p for p in graph.evidence}
    expected = {'unit-one': (configs[0]['database_id'], ('public', 'orders'), mapping_one),
                'unit-two': (configs[1]['database_id'], ('a.b', 'c'), mapping_two)}
    for context in [c for c in graph.contexts if c.get('language') == 'jvm']:
        database, sql_name, mapping_path = expected[context['persistence_unit']]
        entity = next(n for n in graph.nodes if n.kind == 'class' and (n.metadata or {}).get('owner') == 'demo.Order'
                      and qualified('app', str((n.metadata or {}).get('context_id'))) == context['id'])
        orm = next(e.target for e in graph.edges if e.source == entity.id and e.kind == 'maps_to_table'
                   and e.context_ids == (context['id'],))
        binding = next(e for e in graph.edges if e.source == orm and e.kind == 'resolves_to_schema_table'
                       and e.context_ids == (context['id'],))
        target = nodes[binding.target]
        assert tuple(target.metadata['schema_object']) == sql_name
        assert target.metadata['persistence_realm']['database_id'] == database
        assert nodes[orm].metadata['persistence_unit'] == context['persistence_unit']
        assert all(proofs[p]['xml_mapping_file'] == mapping_path for p in binding.evidence_ids)
        assert all(proofs[p]['persistence_selection']['persistence_unit'] == context['persistence_unit'] for p in binding.evidence_ids)
    local = load_graph(root)
    contexts = [c for c in local.contexts if c.get('language') == 'jvm']
    foreign = contexts[1]['id']
    foreign_nodes = deepcopy([n for n in local.nodes if (n.metadata or {}).get('context_id') == foreign])
    fresh = augment_framework_graph(root, local, contexts[0])
    assert [n for n in fresh.nodes if (n.metadata or {}).get('context_id') == foreign] == foreign_nodes
    before = (root / '.kgmaker/graph.json').read_bytes()
    ambiguous = inspect_jvm(root, home=home, kotlin_backend=backend, classpath=jars, publish=False,
        repo_id='app', module='app', build_context={'database_id': configs[0]['database_id'], 'schema_stream_id': 'main'})
    assert any(d.get('code') == 'ORM_XML_PERSISTENCE_UNIT_AMBIGUOUS' for d in ambiguous['diagnostics'])
    from kgmaker.model import KnowledgeGraph
    from kgmaker.feature import attach_schema
    ambiguous_graph = KnowledgeGraph.from_dict(ambiguous['graph'])
    with patch('subprocess.Popen', side_effect=AssertionError('ambiguous replay must stay offline')):
        for config in configs:
            ambiguous_graph = attach_schema(ambiguous_graph, reconstruct(root, config), root)
        ambiguous_graph = augment_framework_graph(root, ambiguous_graph, ambiguous['context'])
    assert not any(e.kind in {'maps_to_table', 'resolves_to_schema_table'}
                   and e.context_ids == (ambiguous['context']['id'],) for e in ambiguous_graph.edges)
    assert (root / '.kgmaker/graph.json').read_bytes() == before


def test_new_persistence_selectors_change_jvm_identity_without_changing_typescript():
    from kgmaker.graph_provider import _selection_key
    baseline = dict(repo_id='app', module='app', source_set='main', scope='production')
    ts = dict(baseline, language='typescript')
    assert _selection_key(ts) == _selection_key(dict(ts, persistence_schema='public', flyway_target='2'))
    jvm = dict(baseline, language='jvm')
    assert _selection_key(jvm) != _selection_key(dict(jvm, persistence_schema='public'))
    assert _selection_key(jvm) != _selection_key(dict(jvm, flyway_target='2'))

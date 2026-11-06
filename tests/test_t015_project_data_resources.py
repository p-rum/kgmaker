"""T015: actual offline Flyway/workspace inputs and bounded upstream facts."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import digest, file_hash, write_json
from kgmaker.architecture_model import ViewDocument
from kgmaker.inspection import source_snapshot
from kgmaker.model import Edge, Node
from kgmaker.scanner import scan_repository
from kgmaker.workspace import load_workspace, qualified, snapshot_workspace
from kgmaker.data_resources import DataResourceError, project_data_resources


def inputs(tmp_path, *, explicit=True):
    root = tmp_path / 'backend'
    source = root / 'src/main/java/Orders.java'
    source.parent.mkdir(parents=True)
    source.write_text('class Orders { void read() {} void write() {} }\n')
    configs = []
    for name in ['one', 'two']:
        path = root / f'src/main/resources/db-{name}/V1__orders.sql'
        path.parent.mkdir(parents=True)
        path.write_text('CREATE TABLE orders (id BIGINT);\n')
        cfg = {'stream_id': name, 'locations': [f'src/main/resources/db-{name}']}
        if explicit:
            cfg['database_id'] = 'db-' + name
        configs.append(cfg)
    manifest = tmp_path / 'workspace.json'
    write_json(manifest, {'schema_version': 1, 'workspace_id': 'retail',
        'repositories': [{'id': 'backend', 'role': 'backend', 'path': 'backend', 'flyway': configs}],
        'services': [{'id': 'orders', 'backend_repo': 'backend', 'frontend_repos': [], 'test_repos': [],
                      'contract': {'repo_id': 'backend', 'path': 'api.json'}}],
        'service_ownership': {'schema_version': 1, 'services': [{'id': 'orders',
            'roots': [{'repo_id': 'backend', 'path': 'src/main'}],
            'modules': [{'repo_id': 'backend', 'id': 'app'}], 'external_systems': []}]}})
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    return workspace, graph, coverage


def resources(view):
    return [n for n in view.nodes if n.kind in {'database_resource', 'unresolved_data_resource'}]


def access_inputs(tmp_path):
    workspace, graph, coverage = inputs(tmp_path)
    root = Path(workspace['repositories'][0]['_root'])
    ctx = {'id': qualified('backend', 'prod'), 'repo_id': 'backend', 'module': 'app',
           'source_set': 'main', 'scope': 'production', 'mode': 'SYMBOL_RESOLVED',
           'analyzer_version': 'upstream-fixture', 'freshness': 'CURRENT', 'classpath': [],
           'database_id': 'db-one', 'schema_stream_id': 'one'}
    ctx['source_files'] = {'@backend/' + p: h for p, h in source_snapshot(root, scan_repository(root), ctx).items()}
    graph.contexts.append(ctx)
    path = '@backend/src/main/java/Orders.java'
    query = qualified('backend', 'query:orders')
    table = qualified('backend', 'orm:orders')
    graph.nodes.extend([
        Node(query, 'orm_query', 'orders query', path, 1, scope='production'),
        Node(table, 'orm_table', 'orders', path, 1, scope='production',
             metadata={'database_id': 'db-one', 'schema_stream_id': 'one'})])
    for action in ['query_reads', 'query_writes']:
        identity = 'proof:' + action
        graph.evidence.append({'id': identity, 'kind': 'FRAMEWORK_DERIVED', 'source': query, 'target': table,
            'relation': action, 'context_ids': [ctx['id']], 'source_file': path,
            'sha256': graph.files[path], 'polarity': 'SUPPORTING'})
        graph.edges.append(Edge(query, table, action, evidence_kind='FRAMEWORK_DERIVED',
            context_ids=(ctx['id'],), evidence_ids=(identity,), source_file=path, source_line=1))
    return workspace, graph, coverage, ctx, query, table


def test_two_actual_datasources_keep_distinct_resources_and_table_drilldown(tmp_path):
    workspace, graph, coverage = inputs(tmp_path)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('pure projection')):
        view = project_data_resources(workspace, graph, source_coverage=coverage)
    values = resources(view)
    assert len(values) == 2
    assert {n.attributes['database_id'] for n in values} == {'db-one', 'db-two'}
    assert len({n.id for n in values}) == 2
    assert all(len(n.attributes['table_ids']) == 1 for n in values)
    assert all(n.attributes['derivation'] == ['MIGRATION_DERIVED'] for n in values)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert all(n.attributes['deployment_status'] == n.attributes['data_availability'] == 'UNKNOWN' for n in values)
    assert (workspace, graph.to_dict(), coverage) == before
    assert ViewDocument.from_dict(json.loads(view.to_json())).content_fingerprint == view.content_fingerprint


def test_only_existing_context_bound_read_write_is_projected(tmp_path):
    workspace, graph, coverage, ctx, query, table = access_inputs(tmp_path)
    with patch('subprocess.Popen', side_effect=AssertionError('no process')):
        view = project_data_resources(workspace, graph, source_coverage=coverage)
    access = [e for e in view.edges if e.relation in {'reads', 'writes', 'deletes'}]
    assert {e.relation for e in access} == {'reads', 'writes'}
    assert all(e.source == 'service:orders' and e.attributes['context_ids'] == [ctx['id']] for e in access)
    target = next(n for n in view.nodes if n.id == access[0].target)
    assert target.attributes['database_id'] == 'db-one'
    assert all(e.evidence_kinds == ('FRAMEWORK_DERIVED',) for e in access)
    assert all(e.supporting_refs and not e.unknown_refs for e in access)


def test_default_database_and_dto_never_gain_access_or_a_resolved_realm(tmp_path):
    workspace, graph, coverage = inputs(tmp_path, explicit=False)
    graph.nodes.append(Node('dto', 'class', 'OrderDto', '@backend/src/main/java/Orders.java', scope='production'))
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert resources(view) and all(n.resolution_status == 'UNRESOLVED' for n in resources(view))
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert any(d['code'] == 'DATASOURCE_MAPPING_UNKNOWN' for d in view.diagnostics)
    assert view.coverage['status'] in {'PARTIAL', 'UNKNOWN'}


@pytest.mark.parametrize('mutation', ['foreign_context', 'test_scope', 'missing_realm', 'conflicting_realm', 'candidate', 'missing_evidence'])
def test_invalid_or_ambiguous_access_does_not_become_read_write(tmp_path, mutation):
    workspace, graph, coverage, ctx, query, table = access_inputs(tmp_path)
    from dataclasses import replace
    if mutation == 'foreign_context':
        graph.contexts.append({'id': 'foreign', 'repo_id': 'foreign', 'scope': 'production'})
        graph.edges = [replace(e, context_ids=('foreign',)) if e.source == query else e for e in graph.edges]
        for proof in graph.evidence:
            if proof.get('source') == query: proof['context_ids'] = ['foreign']
    elif mutation == 'test_scope':
        graph.nodes = [replace(n, scope='test') if n.id == query else n for n in graph.nodes]
    elif mutation == 'missing_realm':
        graph.nodes = [replace(n, metadata={}) if n.id == table else n for n in graph.nodes]
    elif mutation == 'conflicting_realm':
        graph.nodes = [replace(n, metadata={'database_id': 'db-two', 'schema_stream_id': 'two'}) if n.id == table else n for n in graph.nodes]
    elif mutation == 'candidate':
        graph.edges = [replace(e, evidence_kind='SYNTAX_CANDIDATE') if e.source == query else e for e in graph.edges]
        for proof in graph.evidence:
            if proof.get('source') == query: proof['kind'] = 'SYNTAX_CANDIDATE'
    else:
        graph.edges = [replace(e, evidence_ids=()) if e.source == query else e for e in graph.edges]
    before = deepcopy(graph.to_dict())
    if mutation == 'missing_evidence':
        with pytest.raises(DataResourceError):
            project_data_resources(workspace, graph, source_coverage=coverage)
        assert graph.to_dict() == before
        return
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert view.coverage['status'] == 'PARTIAL'
    assert graph.to_dict() == before


def test_stale_migration_fails_without_mutating_last_valid_artifact(tmp_path):
    workspace, graph, coverage = inputs(tmp_path)
    artifact = tmp_path / 'last-view.json'
    artifact.write_text('last valid generation')
    path = Path(workspace['repositories'][0]['_root']) / coverage['schemas']['backend'][0]['inventory'][0]['path']
    path.write_text(path.read_text() + '-- changed\n')
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with pytest.raises(DataResourceError, match='snapshot'):
        project_data_resources(workspace, graph, source_coverage=coverage)
    assert artifact.read_text() == 'last valid generation'
    assert (workspace, graph.to_dict(), coverage) == before


def test_identity_ignores_table_details_and_input_order(tmp_path):
    workspace, graph, coverage = inputs(tmp_path)
    original = project_data_resources(workspace, graph, source_coverage=coverage)
    graph.nodes.reverse(); graph.edges.reverse(); graph.contexts.reverse()
    coverage['schemas']['backend'].reverse()
    reordered = project_data_resources(workspace, graph, source_coverage=coverage)
    assert original.to_json() == reordered.to_json()
    before_ids = {n.id for n in resources(original)}
    # A real migration adds drill-down detail without changing DB identity.
    path = Path(workspace['repositories'][0]['_root']) / coverage['schemas']['backend'][0]['inventory'][0]['path']
    path.write_text(path.read_text() + 'CREATE TABLE line_items (id BIGINT);\n')
    _, changed_coverage, _, changed_graph, _ = snapshot_workspace(Path(workspace['_manifest_path']))
    changed = project_data_resources(workspace, changed_graph, source_coverage=changed_coverage)
    assert {n.id for n in resources(changed)} == before_ids
    assert max(len(n.attributes['table_ids']) for n in resources(changed)) == 2


def test_stale_selected_context_does_not_retain_read_write(tmp_path):
    workspace, graph, coverage, ctx, _, _ = access_inputs(tmp_path)
    ctx['freshness'] = 'STALE'
    result = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in result.edges)
    assert result.coverage['status'] == 'PARTIAL'
    assert any('STALE' in d['code'] for d in result.diagnostics)


def test_unknown_file_scope_is_not_promoted_from_repository_identity(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage = inputs(tmp_path)
    graph.nodes = [replace(n, scope='unknown') if n.kind == 'file' and n.path.endswith('.sql') else n for n in graph.nodes]
    result = project_data_resources(workspace, graph, source_coverage=coverage)
    assert all(n.resolution_status == 'UNRESOLVED' and n.attributes['scope'] == 'unknown' for n in resources(result))
    assert not any(e.relation == 'depends_on' for e in result.edges)


@pytest.mark.parametrize('mutation', ['config', 'foreign_repo', 'fingerprint', 'malformed'])
def test_invalid_schema_snapshot_cannot_be_republished(tmp_path, mutation):
    workspace, graph, coverage = inputs(tmp_path)
    schema = coverage['schemas']['backend'][0]
    if mutation == 'config':
        schema['config']['database_id'] = 'invented-db'
        schema['fingerprint'] = digest({'config': schema['config'], 'inventory': schema['inventory']})
    elif mutation == 'foreign_repo':
        coverage['schemas']['foreign'] = coverage['schemas'].pop('backend')
    elif mutation == 'fingerprint':
        schema['fingerprint'] = '0' * 64
    else:
        schema['inventory'] = [None]
    before = deepcopy((workspace, graph.to_dict(), coverage))
    with patch('subprocess.Popen', side_effect=AssertionError('no process')):
        with pytest.raises(DataResourceError):
            project_data_resources(workspace, graph, source_coverage=coverage)
    assert (workspace, graph.to_dict(), coverage) == before


def test_entity_mapping_is_only_a_dependency_not_read_or_write(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage, _, query, _ = access_inputs(tmp_path)
    original = next(e for e in graph.edges if e.source == query)
    graph.edges = [e for e in graph.edges if e.source != query]
    graph.edges.append(replace(original, kind='maps_to_table'))
    next(p for p in graph.evidence if p['id'] == original.evidence_ids[0])['relation'] = 'maps_to_table'
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert any(e.relation == 'depends_on' for e in view.edges)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)


def test_plain_connection_configuration_never_creates_database_access(tmp_path):
    workspace, _, _ = inputs(tmp_path)
    manifest = Path(workspace['_manifest_path'])
    declaration = json.loads(manifest.read_text())
    declaration['repositories'][0].pop('flyway')
    write_json(manifest, declaration)
    root = Path(workspace['repositories'][0]['_root'])
    path = root / 'src/main/resources/application.properties'
    path.write_text('spring.datasource.url=jdbc:postgresql://user:privatePass@example.invalid/orders\n')
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not resources(view)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert 'privatePass' not in view.to_json()


def test_truncation_is_visible_and_orm_node_label_does_not_mint_evidence(tmp_path):
    workspace, graph, coverage, _, _, _ = access_inputs(tmp_path)
    graph.diagnostics.append({'code': 'TRUNCATED_UPSTREAM_ORM', 'reason': 'unsupported persistence variant'})
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert any(d['code'] == 'TRUNCATED_UPSTREAM_ORM' for d in view.diagnostics)
    assert view.coverage['status'] == 'PARTIAL'
    assert any(p['evidence_kind'] == 'UNKNOWN' for p in view.provenance if p.get('source_id', '').endswith('orm%3Aorders'))


@pytest.mark.parametrize('value', [[], {}, 3, None, 'unsupported'])
def test_malformed_extra_polarity_is_unknown_without_input_mutation(tmp_path, value):
    workspace, graph, coverage, _, _, _ = access_inputs(tmp_path)
    for proof in graph.evidence:
        proof['polarity'] = value
    before = deepcopy(graph.to_dict())
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    access = [e for e in view.edges if e.relation in {'reads', 'writes'}]
    assert access and all(e.unknown_refs and not e.supporting_refs for e in access)
    assert any(d['code'] == 'DATA_RESOURCE_EVIDENCE_POLARITY_UNKNOWN' for d in view.diagnostics)
    assert graph.to_dict() == before


@pytest.mark.parametrize('freshness', ['STALE', 'UNKNOWN', [], {}])
def test_stale_or_malformed_evidence_freshness_never_becomes_current_access(tmp_path, freshness):
    workspace, graph, coverage, _, _, _ = access_inputs(tmp_path)
    for proof in graph.evidence:
        proof['freshness'] = freshness
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert any(d['code'] == 'DATA_RESOURCE_EVIDENCE_FRESHNESS_UNKNOWN' for d in view.diagnostics)


def test_missing_table_inventory_is_rejected_against_the_existing_graph(tmp_path):
    workspace, graph, coverage = inputs(tmp_path)
    schema = coverage['schemas']['backend'][0]
    schema['objects'] = {k: v for k, v in schema['objects'].items() if v['kind'] != 'table'}
    with pytest.raises(DataResourceError, match='table inventory snapshot'):
        project_data_resources(workspace, graph, source_coverage=coverage)


def test_explicit_conflicting_access_evidence_keeps_both_polarities(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage, _, query, _ = access_inputs(tmp_path)
    read = next(e for e in graph.edges if e.source == query and e.kind == 'query_reads')
    contrary = deepcopy(next(p for p in graph.evidence if p['id'] == read.evidence_ids[0]))
    contrary.update(id='proof:contrary-read', polarity='CONTRADICTING')
    graph.evidence.append(contrary)
    graph.edges = [replace(e, evidence_ids=(*e.evidence_ids, contrary['id'])) if e == read else e for e in graph.edges]
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    read_view = next(e for e in view.edges if e.relation == 'reads')
    assert read_view.resolution_status == 'AMBIGUOUS'
    assert read_view.supporting_refs and read_view.contradicting_refs
    assert any(d['code'] == 'CONTRADICTORY_VIEW_EVIDENCE' for d in view.diagnostics)
    assert view.coverage['status'] == 'PARTIAL'


@pytest.mark.parametrize('mutation', ['test_file', 'unknown_file', 'foreign_target_context', 'missing_context_snapshot'])
def test_shared_migration_resource_cannot_mask_foreign_target_scope_or_snapshot(tmp_path, mutation):
    from dataclasses import replace
    workspace, graph, coverage, ctx, _, table = access_inputs(tmp_path)
    if mutation in {'test_file', 'unknown_file'}:
        root = Path(workspace['repositories'][0]['_root'])
        path = root / 'src/test/java/TestEntity.java'
        path.parent.mkdir(parents=True); path.write_text('class TestEntity {}\n')
        qualified_path = '@backend/src/test/java/TestEntity.java'
        graph.files[qualified_path] = file_hash(path)
        graph.nodes.append(Node('test-file', 'file', 'TestEntity.java', qualified_path,
                                scope='test' if mutation == 'test_file' else 'unknown'))
        # The endpoint's claimed scope alone cannot override its qualified file.
        graph.nodes = [replace(n, path=qualified_path) if n.id == table else n for n in graph.nodes]
    elif mutation == 'foreign_target_context':
        graph.nodes = [replace(n, metadata={**n.metadata, 'context_id': 'foreign'}) if n.id == table else n for n in graph.nodes]
    else:
        ctx['source_files'].pop('@backend/src/main/java/Orders.java')
    before = deepcopy(graph.to_dict())
    with patch('subprocess.Popen', side_effect=AssertionError('no process')):
        view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert any(n.attributes['database_id'] == 'db-one' for n in resources(view))
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert not any(p.get('original_id', '').startswith('proof:') for p in view.provenance)
    assert graph.to_dict() == before


def test_valid_access_carries_both_endpoint_hashes_from_selected_context(tmp_path):
    workspace, graph, coverage, ctx, _, _ = access_inputs(tmp_path)
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    proofs = [p for p in view.provenance if p.get('original_id', '').startswith('proof:')]
    assert len(proofs) == 2
    for proof in proofs:
        assert proof['context_ids'] == [ctx['id']]
        assert proof['content_hash'] == ctx['source_files'][proof['source_file']]
        assert proof['target_content_hash'] == ctx['source_files'][proof['target_source_file']]


def test_optional_fact_hash_uses_only_validated_context_source_provenance(tmp_path):
    workspace, graph, coverage, ctx, query, _ = access_inputs(tmp_path)
    for proof in graph.evidence:
        if proof.get('source') == query:
            proof.pop('sha256', None)
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    access = [e for e in view.edges if e.relation in {'reads', 'writes'}]
    assert {e.relation for e in access} == {'reads', 'writes'}
    for proof in view.provenance:
        if proof.get('original_id', '').startswith('proof:'):
            assert proof['hash_provenance'] == 'VALIDATED_CONTEXT_SOURCE'
            assert proof['content_hash'] == ctx['source_files'][proof['source_file']]
    assert all('sha256' not in p for p in graph.evidence if p.get('source') == query)


@pytest.mark.parametrize('checksum', [[], {}, '0' * 64])
def test_malformed_or_stale_optional_fact_hash_is_a_boundary(tmp_path, checksum):
    workspace, graph, coverage, _, query, _ = access_inputs(tmp_path)
    for proof in graph.evidence:
        if proof.get('source') == query:
            proof['sha256'] = checksum
    before = deepcopy(graph.to_dict())
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert any(d['code'] == 'DATA_RESOURCE_FACT_HASH_UNKNOWN_OR_STALE' for d in view.diagnostics)
    assert graph.to_dict() == before


def entity_access_inputs(tmp_path):
    from dataclasses import replace
    workspace, graph, coverage, ctx, query, table = access_inputs(tmp_path)
    path = '@backend/src/main/java/Orders.java'
    entity = qualified('backend', 'entity:orders')
    graph.nodes.append(Node(entity, 'class', 'Order', path, scope='production', metadata={'context_id': 'prod'}))
    graph.edges = [replace(e, target=entity) if e.source == query else e for e in graph.edges]
    for proof in graph.evidence:
        if proof.get('source') == query:
            proof['target'] = entity
    identity = 'proof:maps-to-table'
    graph.evidence.append({'id': identity, 'source': entity, 'target': table, 'relation': 'maps_to_table',
        'kind': 'FRAMEWORK_DERIVED', 'context_ids': [ctx['id']], 'source_file': path})
    graph.edges.append(Edge(entity, table, 'maps_to_table', evidence_kind='FRAMEWORK_DERIVED',
        context_ids=(ctx['id'],), evidence_ids=(identity,), source_file=path))
    return workspace, graph, coverage, ctx, query, entity, table


def test_entity_access_composes_only_existing_mapping_and_preserves_both_refs(tmp_path):
    workspace, graph, coverage, _, query, entity, table = entity_access_inputs(tmp_path)
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    access = [e for e in view.edges if e.relation in {'reads', 'writes'}]
    assert {e.relation for e in access} == {'reads', 'writes'}
    assert all({query, entity, table, 'proof:maps-to-table'} <= set(e.original_ids) for e in access)
    for edge in access:
        proofs = [p for p in view.provenance if p['id'] in edge.evidence_refs]
        assert {p['original_edge']['relation'] for p in proofs} in ({'query_reads', 'maps_to_table'}, {'query_writes', 'maps_to_table'})


@pytest.mark.parametrize('mutation', ['ambiguous', 'foreign_mapping', 'test_entity', 'stale_mapping_hash'])
def test_entity_mapping_ambiguity_and_foreign_or_stale_proof_never_create_access(tmp_path, mutation):
    from dataclasses import replace
    workspace, graph, coverage, _, _, entity, _ = entity_access_inputs(tmp_path)
    mapping = next(e for e in graph.edges if e.kind == 'maps_to_table')
    if mutation == 'ambiguous':
        proof = deepcopy(next(p for p in graph.evidence if p['id'] == 'proof:maps-to-table'))
        proof['id'] = 'proof:other-mapping'; graph.evidence.append(proof)
        graph.edges.append(replace(mapping, evidence_ids=(proof['id'],)))
    elif mutation == 'foreign_mapping':
        graph.contexts.append({'id': 'foreign', 'repo_id': 'foreign', 'scope': 'production'})
        graph.edges = [replace(e, context_ids=('foreign',)) if e == mapping else e for e in graph.edges]
        next(p for p in graph.evidence if p['id'] == 'proof:maps-to-table')['context_ids'] = ['foreign']
    elif mutation == 'test_entity':
        graph.nodes = [replace(n, scope='test') if n.id == entity else n for n in graph.nodes]
    else:
        next(p for p in graph.evidence if p['id'] == 'proof:maps-to-table')['sha256'] = '0' * 64
    view = project_data_resources(workspace, graph, source_coverage=coverage)
    assert not any(e.relation in {'reads', 'writes', 'deletes'} for e in view.edges)
    assert view.coverage['status'] == 'PARTIAL'


def jpa_api_jars():
    import hashlib
    import os
    import xml.etree.ElementTree as ET
    from kgmaker.worker_protocol import WorkerError
    repository = Path(os.environ.get('KGMAKER_TEST_MAVEN_REPOSITORY', Path.home() / '.m2/repository'))
    lock = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/data-resources/dependencies.lock.json').read_text())
    jars = []
    for item in lock['artifacts']:
        jar, pom = repository / item['path'], repository / item['license_pom']
        artifact_pom = repository / item['artifact_pom']
        if (not artifact_pom.is_file() or hashlib.sha256(artifact_pom.read_bytes()).hexdigest() != item['artifact_pom_sha256']
                or not jar.is_file() or not pom.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest() != item['sha256']
                or hashlib.sha256(pom.read_bytes()).hexdigest() != item['license_pom_sha256']):
            raise WorkerError('Pinned existing JPA API/POM unavailable: ' + item['path'], 'TOOLCHAIN_UNAVAILABLE')
        license_name = ET.parse(pom).getroot().findtext('{http://maven.apache.org/POM/4.0.0}licenses/{http://maven.apache.org/POM/4.0.0}license/{http://maven.apache.org/POM/4.0.0}name')
        assert license_name == item['license_name']
        jars.append(str(jar))
    return jars


@pytest.mark.parametrize('backend', ['k1', 'k2'])
def test_actual_existing_jpa_native_and_entity_query_facts_project_offline(tmp_path, backend):
    import os
    from kgmaker.inspection import command, inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    home = Path(__file__).resolve().parents[1] / 'workers'
    try:
        command('jvm', home, kotlin_backend=backend)
        jars = jpa_api_jars()
    except WorkerError as error:
        if os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1' or (backend == 'k2' and os.environ.get('KGMAKER_REQUIRE_K2') == '1'):
            pytest.fail(str(error))
        pytest.skip('actual JPA/worker prerequisites: ' + str(error))
    workspace, _, _ = inputs(tmp_path)
    root = Path(workspace['repositories'][0]['_root'])
    source = root / 'src/main/java/demo/RepositoryInput.java'
    source.parent.mkdir(parents=True)
    source.write_text('''package demo;
import jakarta.persistence.Entity; import jakarta.persistence.Id; import jakarta.persistence.Table;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.stereotype.Repository;
@Entity @Table(name="orders") class Order { @Id Long id; }
@Repository interface OrdersRepository extends JpaRepository<Order,Long> {
 @Query(value="select * from orders",nativeQuery=true) java.util.List<Order> readNative();
 @Modifying @Query(value="update orders set id = 1",nativeQuery=true) int writeNative();
 @Query("select o from Order o") java.util.List<Order> readJpql();
}
''')
    captured = inspect_jvm(root, home=home, classpath=jars, kotlin_backend=backend,
        repo_id='backend', module='app', publish=True,
        build_context={'database_id': 'db-one', 'schema_stream_id': 'one', 'spring_profiles': [],
                       'spring_properties': {}, 'spring_component_packages': ['demo']})
    assert not any('.err.' in d.get('code', '') for d in captured['diagnostics'])
    manifest = Path(workspace['_manifest_path'])
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    before = deepcopy((workspace, graph.to_dict(), coverage))
    persisted = {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
    with patch('subprocess.Popen', side_effect=AssertionError('projection may not run a worker')):
        view = project_data_resources(workspace, graph, source_coverage=coverage)
    access = [e for e in view.edges if e.relation in {'reads', 'writes'}]
    assert {e.relation for e in access} == {'reads', 'writes'}
    queries = {n.id: n for n in graph.nodes if n.kind == 'orm_query'}
    covered_queries = {identity for e in access for identity in e.original_ids if identity in queries}
    assert len(covered_queries) == 3  # both native calls and the JPQL entity path
    target = next(n for n in view.nodes if n.id == access[0].target)
    assert target.attributes['database_id'] == 'db-one'
    assert not any(e.target != target.id for e in access)
    input_evidence = {p['id']: p for p in graph.evidence}
    proofs = [p for p in view.provenance if p.get('original_id') in input_evidence]
    assert proofs and any(p['hash_provenance'] == 'VALIDATED_CONTEXT_SOURCE' for p in proofs)
    for proof in proofs:
        context = next(c for c in graph.contexts if c['id'] == proof['context_ids'][0])
        assert proof['content_hash'] == context['source_files'][proof['source_file']]
        assert proof['target_content_hash'] == context['source_files'][proof['target_source_file']]
    assert (workspace, graph.to_dict(), coverage) == before
    assert persisted == {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.kgmaker').rglob('*') if p.is_file()}
    assert all(n.attributes['data_availability'] == 'UNKNOWN' for n in resources(view))

from pathlib import Path

from kgmaker.framework import _jpa_xml_model


ORM = "https://jakarta.ee/xml/ns/persistence/orm"


def write_orm(root: Path, body: str) -> None:
    target = root / "META-INF" / "orm.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'<entity-mappings xmlns="{ORM}" version="3.1">{body}</entity-mappings>',
        encoding="utf-8",
    )


def test_xml_named_query_and_native_query_are_captured_with_provenance(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.byTenant"><query>select o from Order o where o.tenant = :tenant</query></named-query>'
        '<named-native-query name="Order.raw"><query>select * from orders</query></named-native-query>',
    )
    model = _jpa_xml_model(tmp_path, {})
    assert [item["name"] for item in model["named_queries"]] == ["Order.byTenant", "Order.raw"]
    assert {item["language"] for item in model["named_queries"]} == {"JPQL", "NATIVE_SQL"}
    assert all(item["provenance"]["xml_mapping_file"] == "META-INF/orm.xml" for item in model["named_queries"])


def test_xml_named_query_duplicate_is_ambiguous_and_missing_body_is_unresolved(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.duplicate"><query>select o from Order o</query></named-query>'
        '<named-query name="Order.duplicate"><query>select o from Order o where o.id = 1</query></named-query>'
        '<named-native-query name="Order.missing"/>',
    )
    model = _jpa_xml_model(tmp_path, {})
    duplicate = [item for item in model["named_queries"] if item["name"] == "Order.duplicate"]
    assert len(duplicate) == 2 and all(item["ambiguous"] for item in duplicate)
    codes = {item["code"] for item in model["diagnostics"]}
    assert "ORM_XML_NAMED_QUERY_AMBIGUOUS" in codes
    assert "ORM_XML_NAMED_QUERY_UNRESOLVED" in codes


def test_xml_incomplete_duplicate_name_cannot_fall_back_to_valid_definition(tmp_path):
    write_orm(
        tmp_path,
        '<named-query name="Order.same"/>'
        '<named-query name="Order.same"><query>select o from Order o</query></named-query>',
    )
    model = _jpa_xml_model(tmp_path, {})
    assert any(item["name"] == "Order.same" and item.get("ambiguous") for item in model["named_queries"])
    assert "ORM_XML_NAMED_QUERY_AMBIGUOUS" in {item["code"] for item in model["diagnostics"]}


# These APIs model the compiler contracts only. No JPA/Spring runtime is started.
STUBS = {
    "Entity": '@Target(ElementType.TYPE) public @interface Entity { String name() default ""; }',
    "Table": '@Target(ElementType.TYPE) public @interface Table { String name() default ""; }',
    "Id": '@Target(ElementType.FIELD) public @interface Id {}',
    "Column": '@Target(ElementType.FIELD) public @interface Column {}',
    "NamedQuery": '@Target(ElementType.TYPE) @Repeatable(NamedQueries.class) public @interface NamedQuery { String name(); String query(); }',
    "NamedQueries": '@Target(ElementType.TYPE) public @interface NamedQueries { NamedQuery[] value(); }',
    "NamedNativeQuery": '@Target(ElementType.TYPE) @Repeatable(NamedNativeQueries.class) public @interface NamedNativeQuery { String name(); String query(); Class<?> resultClass() default void.class; String resultSetMapping() default ""; }',
    "NamedNativeQueries": '@Target(ElementType.TYPE) public @interface NamedNativeQueries { NamedNativeQuery[] value(); }',
}


def project(root):
    import shutil
    fixture = Path(__file__).resolve().parents[1] / 'fixtures/named-queries'
    sources = {f'jakarta/persistence/{name}.java':
               f'package jakarta.persistence; import java.lang.annotation.*; @Retention(RetentionPolicy.RUNTIME) {body}'
               for name, body in STUBS.items()}
    sources.update({
        'org/springframework/data/jpa/repository/JpaRepository.java':
            'package org.springframework.data.jpa.repository; public interface JpaRepository<T, ID> {}',
        'org/springframework/data/jpa/repository/Query.java':
            'package org.springframework.data.jpa.repository; import java.lang.annotation.*; '
            '@Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME) public @interface Query { '
            'String value() default ""; String name() default ""; boolean nativeQuery() default false; }',
        'demo/Model.java': (fixture / 'Model.java').read_text(),
    })
    for relative, text in sources.items():
        target = root / 'src/main/java' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    (root / 'META-INF').mkdir(exist_ok=True)
    shutil.copyfile(fixture / 'orm.xml', root / 'META-INF/orm.xml')
    return root


def inspect(root, **kwargs):
    import os
    import pytest
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    try:
        return inspect_jvm(root, classpath=[], **kwargs)
    except WorkerError as error:
        if error.status != 'TOOLCHAIN_UNAVAILABLE' or os.environ.get('KGMAKER_REQUIRE_WORKERS') == '1':
            raise
        pytest.skip(str(error))


def queries(graph):
    return {node.name.split(':')[0]: node for node in graph.nodes if node.kind == 'orm_query'}


def test_actual_javac_named_query_containers_reference_parameters_and_projections(tmp_path):
    from kgmaker.model import KnowledgeGraph
    result = inspect(project(tmp_path), publish=False)
    graph = KnowledgeGraph.from_dict(result['graph'])
    q = queries(graph)
    nodes = {node.id: node for node in graph.nodes}
    definitions = {node.name: node for node in graph.nodes if node.kind == 'orm_named_query'}
    for method in ['summary', 'positional', 'nativeResult', 'xml', 'xmlNative', 'classXml',
                   'repeatedFirst', 'repeatedSecond', 'repeatedNative1', 'repeatedNative2',
                   'singleJpql', 'singleNative']:
        assert q[method].metadata['validated'] is True, (method, graph.diagnostics)
        bindings = [edge for edge in graph.edges if edge.source == q[method].id and edge.kind == 'uses_named_query']
        assert len(bindings) == 1
        assert nodes[bindings[0].target].metadata['context_id'] == q[method].metadata['context_id']
        assert any(edge.source == q[method].id and edge.kind == 'query_reads' for edge in graph.edges)
    for method in ['summary', 'nativeResult', 'xml', 'xmlNative']:
        assert q[method].metadata['parameters'] == ['status']
        assert any(edge.source == q[method].id and edge.kind == 'returns_projection'
                   and nodes[edge.target].name == 'Summary' for edge in graph.edges)
    assert q['positional'].metadata['positional_parameters'] == [1]
    assert q['unbound'].metadata['unbound_parameters'] == ['status']
    assert q['unbound'].metadata['validated'] is False
    assert q['positionalUnbound'].metadata['unbound_parameters'] == ['?1']
    assert q['positionalUnbound'].metadata['validated'] is False
    assert definitions['Order.summary'].metadata['query'].endswith("'name=:literal'")
    for method in ['duplicate', 'incomplete', 'collision', 'xmlDuplicate', 'xmlIncomplete', 'absent']:
        assert q[method].metadata['analysis_status'] == 'UNKNOWN'
        assert not q[method].metadata['validated']
        assert not any(edge.source == q[method].id for edge in graph.edges)
    assert q['malformed'].metadata['analysis_status'] == 'UNKNOWN'
    assert not any(edge.source == q['malformed'].id and edge.kind == 'query_reads' for edge in graph.edges)
    assert q['unsupportedMapping'].metadata['analysis_status'] == 'PARTIAL'
    assert q['unsupportedMapping'].metadata['validated'] is False
    assert {'ORM_NAMED_QUERY_UNRESOLVED', 'ORM_XML_NAMED_QUERY_UNRESOLVED'} <= {
        item['code'] for item in graph.diagnostics}
    xml = definitions['Order.xml'].metadata
    import hashlib
    assert xml['xml_sha256'] == hashlib.sha256((tmp_path / 'META-INF/orm.xml').read_bytes()).hexdigest()
    proof_ids = next(edge.evidence_ids for edge in graph.edges
                     if edge.source == q['xml'].id and edge.kind == 'uses_named_query')
    assert any(proof['id'] in proof_ids and proof.get('xml_sha256') == xml['xml_sha256'] for proof in graph.evidence)
    # Defining class is not a query root: Other.first reads Order through its body.
    assert not any(edge.source == definitions['Other.first'].id and edge.kind == 'query_reads' for edge in graph.edges)
    assert KnowledgeGraph.from_dict(graph.to_dict()).to_dict() == graph.to_dict()


def test_actual_named_queries_select_xml_persistence_realm_without_cross_binding(tmp_path):
    from kgmaker.model import KnowledgeGraph
    root = project(tmp_path)
    meta = root / 'META-INF'
    (meta / 'orm.xml').unlink()
    (meta / 'persistence.xml').write_text('''<persistence xmlns="https://jakarta.ee/xml/ns/persistence" version="3.1">
      <persistence-unit name="orders"><mapping-file>META-INF/orders.xml</mapping-file></persistence-unit>
      <persistence-unit name="reports"><mapping-file>META-INF/reports.xml</mapping-file></persistence-unit>
    </persistence>''')
    (meta / 'orders.xml').write_text(f'''<entity-mappings xmlns="{ORM}" version="3.1">
      <named-query name="Order.xml"><query>select new demo.Summary(o.id,o.status) from Order o where o.status=:status</query></named-query>
    </entity-mappings>''')
    (meta / 'reports.xml').write_text(f'<entity-mappings xmlns="{ORM}" version="3.1"/>')
    first = inspect(root, build_context={'persistence_unit': 'orders'})
    second = inspect(root, build_context={'persistence_unit': 'reports'})
    graph = KnowledgeGraph.from_dict(second['graph'])
    by_context = {}
    for node in graph.nodes:
        if node.kind == 'orm_query' and node.name.startswith('xml:'):
            by_context[node.metadata['context_id']] = node
    orders_id, reports_id = first['context']['id'], second['context']['id']
    assert orders_id != reports_id
    assert by_context[orders_id].metadata['validated'] is True
    assert by_context[reports_id].metadata['validated'] is False
    assert any(edge.source == by_context[orders_id].id and edge.kind == 'uses_named_query' for edge in graph.edges)
    assert not any(edge.source == by_context[reports_id].id for edge in graph.edges)
    for edge in graph.edges:
        if edge.kind == 'uses_named_query':
            endpoints = [node for node in graph.nodes if node.id in {edge.source, edge.target}]
            assert {node.metadata['context_id'] for node in endpoints} == set(edge.context_ids)


def test_actual_named_query_strict_rejection_cancel_timeout_preserve_store(tmp_path):
    import pytest
    from kgmaker.worker_protocol import WorkerError
    root = project(tmp_path)
    inspect(root)
    store = root / '.kgmaker/graph.json'
    before = store.read_bytes()
    write_orm(root, '<named-query name="Order.summary"/>')
    assert inspect(root, strict=True)['exit_code'] == 4
    assert store.read_bytes() == before
    cancel = root / 'cancel'
    cancel.touch()
    for kwargs, status in [({'cancel_file': cancel}, 'CANCELLED'), ({'timeout': 0.000001}, 'TIMED_OUT')]:
        with pytest.raises(WorkerError) as rejected:
            inspect(root, **kwargs)
        assert rejected.value.status == status
        assert store.read_bytes() == before


def test_container_structured_facts_projection_is_pure_and_context_scoped(tmp_path, monkeypatch):
    from copy import deepcopy
    from test_jpql_hql_grammar import _fixture
    from kgmaker.framework import augment_framework_graph
    from kgmaker.model import KnowledgeGraph
    _, graph, context = _fixture(tmp_path)
    order = next(symbol for symbol in graph.symbols if symbol['id'] == 'order')
    order['annotations'].append({'name': 'jakarta.persistence.NamedQueries', 'values': {'value': [
        {'name': 'jakarta.persistence.NamedQuery', 'values': {
            'name': 'Order.one', 'query': 'select o from PurchaseOrder o where o.status=:name'}},
    ]}})
    method = next(symbol for symbol in graph.symbols if symbol['id'] == 'hql')
    method['annotations'][0]['values'] = {'name': 'Order.one'}
    before = deepcopy(graph.to_dict())
    monkeypatch.setattr('subprocess.Popen', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('implicit process')))
    projected = augment_framework_graph(tmp_path, graph, context)
    assert graph.to_dict() == before
    assert queries(projected)['hqlWith'].metadata['validated'] is True
    assert KnowledgeGraph.from_dict(projected.to_dict()).to_dict() == projected.to_dict()
    # An identically named foreign declaration never participates in this catalog.
    foreign = deepcopy(order)
    foreign.update(id='foreign', context_id='foreign')
    graph.symbols.append(foreign)
    from dataclasses import replace
    graph.nodes.append(replace(next(node for node in graph.nodes if node.id == 'order'), id='foreign'))
    graph.contexts.append({**context, 'id': 'foreign'})
    order['annotations'] = order['annotations'][:1]
    projected = augment_framework_graph(tmp_path, graph, context)
    assert queries(projected)['hqlWith'].metadata['analysis_status'] == 'UNKNOWN'
    assert not any(edge.source == queries(projected)['hqlWith'].id for edge in projected.edges)


def test_annotation_duplicate_missing_body_and_foreign_container_fail_closed(tmp_path):
    from test_jpql_hql_grammar import _fixture
    from kgmaker.framework import augment_framework_graph
    _, graph, context = _fixture(tmp_path)
    order = next(symbol for symbol in graph.symbols if symbol['id'] == 'order')
    method = next(symbol for symbol in graph.symbols if symbol['id'] == 'hql')
    method['annotations'][0]['values'] = {'name': 'Order.one'}
    declarations = [
        {'name': 'jakarta.persistence.NamedQuery', 'values': {'name': 'Order.one', 'query': 'select o from PurchaseOrder o'}},
        {'name': 'jakarta.persistence.NamedQuery', 'values': {'name': 'Order.one', 'query': None}},
        {'name': 'jakarta.persistence.NamedQuery', 'values': {'name': 'Order.one', 'query': 'select o from PurchaseOrder o'}},
    ]
    for annotations in [declarations, list(reversed(declarations)),
                        [{'name': 'fake.NamedQueries', 'values': {'value': declarations[:1]}}],
                        [{'name': 'jakarta.persistence.NamedQueries', 'values_resolved': False,
                          'values': {'value': declarations[:1]}}]]:
        order['annotations'] = order['annotations'][:1] + annotations
        projected = augment_framework_graph(tmp_path, graph, context)
        assert queries(projected)['hqlWith'].metadata['validated'] is False
        assert not any(edge.source == queries(projected)['hqlWith'].id for edge in projected.edges)


def test_xml_multiple_query_bodies_and_malformed_document_do_not_bind(tmp_path):
    from test_jpql_hql_grammar import _fixture
    from kgmaker.framework import augment_framework_graph
    _, graph, context = _fixture(tmp_path)
    method = next(symbol for symbol in graph.symbols if symbol['id'] == 'hql')
    method['annotations'][0]['values'] = {'name': 'Order.one'}
    for body in [
        '<named-query name="Order.one"><query>select o from PurchaseOrder o</query><query>select o from PurchaseOrder o</query></named-query>',
        '<named-query name="Order.one"><query>select o from PurchaseOrder o</query></named-query><broken>',
    ]:
        write_orm(tmp_path, body)
        projected = augment_framework_graph(tmp_path, graph, context)
        assert queries(projected)['hqlWith'].metadata['validated'] is False
        assert not any(edge.source == queries(projected)['hqlWith'].id for edge in projected.edges)


def test_actual_offline_scan_and_hook_preserve_named_query_evidence(tmp_path, monkeypatch):
    from kgmaker.cli import scan, hook_context
    from kgmaker.store import load_graph
    root = project(tmp_path)
    inspect(root)
    before = load_graph(root)
    bindings = {edge for edge in before.edges if edge.kind == 'uses_named_query'}
    assert bindings
    monkeypatch.setattr('subprocess.Popen', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('implicit process')))
    assert scan(root, generate_docs=False) == 0
    assert hook_context(root) == 0
    after = load_graph(root)
    assert {edge for edge in after.edges if edge.kind == 'uses_named_query'} == bindings


def test_legacy_named_query_metadata_remains_readable():
    from kgmaker.model import KnowledgeGraph, Node
    for version in (1, 2, 3):
        old = KnowledgeGraph(version, '.', 'historical', [Node('legacy-named', 'orm_named_query', 'Order.legacy',
                             'Order.java', metadata={'query_language': 'JPQL', 'query': 'select o from Order o'})], [], {})
        loaded = KnowledgeGraph.from_dict(old.to_dict())
        assert loaded.nodes[0].id == 'legacy-named'
        assert loaded.nodes[0].metadata == old.nodes[0].metadata
        assert not loaded.evidence


def test_xml_class_owned_query_requires_valid_compiler_class(tmp_path):
    from test_jpql_hql_grammar import _fixture
    from kgmaker.framework import augment_framework_graph
    _, graph, context = _fixture(tmp_path)
    method = next(symbol for symbol in graph.symbols if symbol['id'] == 'hql')
    method['annotations'][0]['values'] = {'name': 'Order.one'}
    write_orm(tmp_path, '<entity class="missing.Entity"><named-query name="Order.one">'
              '<query>select o from PurchaseOrder o</query></named-query></entity>')
    projected = augment_framework_graph(tmp_path, graph, context)
    assert queries(projected)['hqlWith'].metadata['validated'] is False
    assert not any(edge.source == queries(projected)['hqlWith'].id for edge in projected.edges)


def test_named_native_query_binds_final_xml_table_and_metadata_complete(tmp_path):
    from test_jpql_hql_grammar import _fixture
    from kgmaker.framework import augment_framework_graph
    _, graph, context = _fixture(tmp_path)
    method = next(symbol for symbol in graph.symbols if symbol['id'] == 'hql')
    method['annotations'][0]['values'] = {'name': 'Order.one'}
    order = next(symbol for symbol in graph.symbols if symbol['id'] == 'order')
    order['annotations'].append({'name': 'jakarta.persistence.NamedNativeQuery', 'values': {
        'name': 'Order.one', 'query': 'select * from stale_annotation_table'}})
    write_orm(tmp_path, '<entity class="example.Order" metadata-complete="true"><table name="xml_orders"/>'
              '<named-native-query name="Order.one"><query>select * from xml_orders where status=:name</query>'
              '</named-native-query></entity>')
    projected = augment_framework_graph(tmp_path, graph, context)
    query = queries(projected)['hqlWith']
    assert query.metadata['validated'] is True
    nodes = {node.id: node for node in projected.nodes}
    assert {nodes[edge.target].name for edge in projected.edges
            if edge.source == query.id and edge.kind == 'query_reads'} == {'xml_orders'}
    assert any(edge.source == query.id and edge.kind == 'uses_named_query'
               and nodes[edge.target].metadata['mapping_source'] == 'ORM_XML' for edge in projected.edges)

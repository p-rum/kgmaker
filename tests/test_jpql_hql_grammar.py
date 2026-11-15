"""T003-S06-W05 bounded JPQL/HQL grammar acceptance."""
from copy import deepcopy
import os

import pytest

from kgmaker.analysis_model import digest, file_hash
from kgmaker.framework import JPA_RULE_VERSION, augment_framework_graph, _parse_jpql_hql
from kgmaker.graph_provider import validate_context_snapshot
from kgmaker.inspection import inspect_jvm
from kgmaker.model import KnowledgeGraph, Node
from kgmaker.schema_replay import persistence_selection
from kgmaker.worker_protocol import WorkerError


def _line(source: str, marker: str) -> int:
    return next(index for index, value in enumerate(source.splitlines(), 1) if marker in value)


def _fixture(tmp_path):
    source = """package example;
import jakarta.persistence.*;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
@Entity class Customer {
  @Id Long id;
  @Column String name;
}
@Entity(name="PurchaseOrder") class Order {
  @Id Long id;
  @Column String status;
  @ManyToOne Customer customer;
}
@Entity(name="Duplicate") class DuplicateA { @Id Long id; }
@Entity(name="Duplicate") class DuplicateB { @Id Long id; }
class OrderSummary { OrderSummary(Long id, String name) {} }
interface OrderRepository extends JpaRepository<Order,Long> {
  @Query("select new example.OrderSummary(o.id, c.name) from PurchaseOrder o join o.customer c where c.id in (select c2.id from Customer c2 where c2.name = :name)")
  java.util.List<example.OrderSummary> summaries(String name);
  @Query("update PurchaseOrder o set o.status = :status where o.customer.id = :customerId")
  int updateStatus(String status, Long customerId);
  @Query("delete from PurchaseOrder o where o.status = :status")
  int deleteByStatus(String status);
  @Query("select o from PurchaseOrder o join o.customer c with c.name = :name")
  java.util.List<example.Order> hqlWith(String name);
  @Query("select o from PurchaseOrder o join lateral (select c from Customer c) x")
  java.util.List<example.Order> partialLateral();
  @Query("select o from PurchaseOrder o where (o.id = :id")
  java.util.List<example.Order> malformed(Long id);
  @Query("select o from PurchaseOrder o where o.missing = :value")
  java.util.List<example.Order> unknownPath(String value);
  @Query("select d from Duplicate d where d.id = :id")
  java.util.List<example.Order> ambiguousEntity(Long id);
  @Query("update PurchaseOrder o set") int invalidUpdate();
  @Query("delete from PurchaseOrder o where o.status = :status and") int danglingAnd(String status);
  @Query("select o from PurchaseOrder o where o.id = :id order by") java.util.List<example.Order> danglingOrder(Long id);
  @Query("select x from PurchaseOrder o") java.util.List<example.Order> undeclaredBare();
  @Query("select o from PurchaseOrder o where exists (select c.id from Customer c) and exists (select c.id from PurchaseOrder c)") java.util.List<example.Order> siblingScopes();
  @Query("select o from PurchaseOrder o where o.id = :id and exists (select o.id from Customer o where o.id = :id)") java.util.List<example.Order> correlatedScope(Long id);
}
"""
    relative = "src/main/java/example/Model.java"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text(source)
    context = {"id": "jpql", "language": "jvm", "scope": "production",
               "framework_rule_versions": {"jpa": JPA_RULE_VERSION},
               "database_id": "primary", "schema_stream_id": "main",
               "persistence_unit": "orders"}
    context["persistence_selection_hash"] = digest(persistence_selection(context))
    nodes = []
    symbols = []

    def declaration(identity, name, kind, owner, marker, *, annotations=None, supertypes=None,
                    return_type=None, parameter_names=None):
        line = _line(source, marker)
        nodes.append(Node(identity, kind, name, relative, line=line, scope="production",
                          role="contract" if kind == "interface" else "executable_code",
                          origin="handwritten"))
        symbol = {"id": identity, "name": name, "kind": kind, "owner": owner,
                  "path": relative, "range": {"start_line": line}, "context_id": context["id"],
                  "annotations": annotations or []}
        if supertypes is not None:
            symbol["supertypes"] = supertypes
        if return_type is not None:
            symbol["return_type"] = return_type
        if parameter_names is not None:
            symbol["parameter_names"] = parameter_names
        symbols.append(symbol)

    entity = lambda name=None: [{"name": "jakarta.persistence.Entity",
                                 "values": {} if name is None else {"name": name}}]
    declaration("customer", "Customer", "class", "example.Customer", "@Entity class Customer", annotations=entity())
    declaration("order", "Order", "class", "example.Order", "class Order", annotations=entity("PurchaseOrder"))
    declaration("duplicate-a", "DuplicateA", "class", "example.DuplicateA", "class DuplicateA", annotations=entity("Duplicate"))
    declaration("duplicate-b", "DuplicateB", "class", "example.DuplicateB", "class DuplicateB", annotations=entity("Duplicate"))
    declaration("summary", "OrderSummary", "class", "example.OrderSummary", "class OrderSummary")
    declaration("repository", "OrderRepository", "interface", "example.OrderRepository", "interface OrderRepository",
                supertypes=["org.springframework.data.jpa.repository.JpaRepository<example.Order,java.lang.Long>"])
    query = "org.springframework.data.jpa.repository.Query"
    methods = [
        ("summaries", "summaries", "select new example.OrderSummary(o.id, c.name) from PurchaseOrder o join o.customer c where c.id in (select c2.id from Customer c2 where c2.name = :name)", "java.util.List<example.OrderSummary>", ["name"]),
        ("update", "updateStatus", "update PurchaseOrder o set o.status = :status where o.customer.id = :customerId", "int", ["status", "customerId"]),
        ("delete", "deleteByStatus", "delete from PurchaseOrder o where o.status = :status", "int", ["status"]),
        ("hql", "hqlWith", "select o from PurchaseOrder o join o.customer c with c.name = :name", "java.util.List<example.Order>", ["name"]),
        ("partial", "partialLateral", "select o from PurchaseOrder o join lateral (select c from Customer c) x", "java.util.List<example.Order>", []),
        ("malformed", "malformed", "select o from PurchaseOrder o where (o.id = :id", "java.util.List<example.Order>", ["id"]),
        ("unknown", "unknownPath", "select o from PurchaseOrder o where o.missing = :value", "java.util.List<example.Order>", ["value"]),
        ("ambiguous", "ambiguousEntity", "select d from Duplicate d where d.id = :id", "java.util.List<example.Order>", ["id"]),
        ("invalid-update", "invalidUpdate", "update PurchaseOrder o set", "int", []),
        ("dangling-and", "danglingAnd", "delete from PurchaseOrder o where o.status = :status and", "int", ["status"]),
        ("dangling-order", "danglingOrder", "select o from PurchaseOrder o where o.id = :id order by", "java.util.List<example.Order>", ["id"]),
        ("undeclared-bare", "undeclaredBare", "select x from PurchaseOrder o", "java.util.List<example.Order>", []),
        ("sibling-scopes", "siblingScopes", "select o from PurchaseOrder o where exists (select c.id from Customer c) and exists (select c.id from PurchaseOrder c)", "java.util.List<example.Order>", []),
        ("correlated-scope", "correlatedScope", "select o from PurchaseOrder o where o.id = :id and exists (select o.id from Customer o where o.id = :id)", "java.util.List<example.Order>", ["id"]),
    ]
    for identity, name, text, return_type, parameters in methods:
        declaration(identity, name, "method", "example.OrderRepository", f"{name}(",
                    annotations=[{"name": query, "values": {"value": text}}],
                    return_type=return_type, parameter_names=parameters)
    graph = KnowledgeGraph(3, ".", "now", nodes, [], {relative: file_hash(path)}, [context],
                           [], [], symbols, [], [])
    return source, graph, context


def _queries(graph):
    return {node.name: node for node in graph.nodes if node.kind == "orm_query"}


def test_bounded_jpql_hql_joins_subqueries_dml_and_constructor_projection(tmp_path):
    _, graph, context = _fixture(tmp_path)
    before = deepcopy(graph.to_dict())
    result = augment_framework_graph(tmp_path, graph, context)
    assert graph.to_dict() == before
    queries = _queries(result)
    nodes = {node.id: node for node in result.nodes}

    summaries = queries["summaries:JPQL"]
    assert summaries.metadata["analysis_status"] == "COMPLETE"
    assert summaries.metadata["grammar_version"] == JPA_RULE_VERSION
    assert summaries.metadata["validated"] is True
    reads = {nodes[edge.target].name for edge in result.edges
             if edge.source == summaries.id and edge.kind == "query_reads"}
    assert reads == {"Order", "Customer"}
    assert any(edge.source == summaries.id and edge.kind == "joins_by"
               and nodes[edge.target].name == "Order.customer" for edge in result.edges)
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == summaries.id and edge.kind == "filters_by"} == {"Customer.id", "Customer.name"}
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == summaries.id and edge.kind == "projects_attribute"} == {"Order.id", "Customer.name", "Customer.id"}
    assert any(edge.source == summaries.id and edge.kind == "returns_projection"
               and edge.target == "summary" for edge in result.edges)

    update = queries["updateStatus:JPQL"]
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == update.id and edge.kind == "query_writes"} == {"Order"}
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == update.id and edge.kind == "query_reads"} == {"Customer"}
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == update.id and edge.kind == "updates_attribute"} == {"Order.status"}
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == update.id and edge.kind == "filters_by"} == {"Customer.id"}

    deleting = queries["deleteByStatus:JPQL"]
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == deleting.id and edge.kind == "query_deletes"} == {"Order"}
    assert {nodes[edge.target].name for edge in result.edges
            if edge.source == deleting.id and edge.kind == "filters_by"} == {"Order.status"}

    hql = queries["hqlWith:JPQL"]
    assert hql.metadata["analysis_status"] == "COMPLETE"
    assert hql.metadata["provider_extensions"] == ["HQL_JOIN_WITH"]
    assert any(edge.source == hql.id and edge.kind == "filters_by"
               and nodes[edge.target].name == "Customer.name" for edge in result.edges)


def test_partial_invalid_and_ambiguous_queries_never_publish_stronger_evidence(tmp_path):
    _, graph, context = _fixture(tmp_path)
    result = augment_framework_graph(tmp_path, graph, context)
    queries = _queries(result)
    nodes = {node.id: node for node in result.nodes}

    partial = queries["partialLateral:JPQL"]
    assert partial.metadata["analysis_status"] == "PARTIAL"
    assert partial.metadata["validated"] is False
    fragment = partial.metadata["unsupported_fragments"][0]
    assert fragment["token"].casefold() == "lateral"
    query_text = partial.metadata["query"]
    assert query_text[fragment["query_offset"]:fragment["query_offset"] + len(fragment["token"])] == "lateral"
    assert any(item.get("code") == "JPQL_HQL_UNSUPPORTED_FRAGMENT"
               and item.get("method") == "partial" for item in result.diagnostics)

    malformed = queries["malformed:JPQL"]
    assert malformed.metadata["analysis_status"] == "UNKNOWN"
    assert malformed.metadata["validated"] is False
    assert not any(edge.source == malformed.id and edge.kind in {
        "query_reads", "query_writes", "query_deletes", "filters_by", "projects_attribute"
    } for edge in result.edges)
    assert any(item.get("code") == "JPQL_HQL_SYNTAX_INVALID"
               and item.get("method") == "malformed" for item in result.diagnostics)

    unknown = queries["unknownPath:JPQL"]
    assert unknown.metadata["analysis_status"] == "UNKNOWN"
    assert unknown.metadata["validated"] is False
    assert not any(edge.source == unknown.id and edge.kind == "filters_by" for edge in result.edges)
    assert any(item.get("code") == "JPQL_ATTRIBUTE_UNRESOLVED"
               and item.get("method") == "unknown" for item in result.diagnostics)

    ambiguous = queries["ambiguousEntity:JPQL"]
    assert ambiguous.metadata["analysis_status"] == "UNKNOWN"
    assert ambiguous.metadata["validated"] is False
    assert not any(edge.source == ambiguous.id and edge.kind in {
        "query_reads", "query_writes", "query_deletes", "filters_by"
    } for edge in result.edges)
    assert any(item.get("code") == "JPQL_ENTITY_UNRESOLVED"
               and item.get("method") == "ambiguous" and len(item.get("candidates", [])) == 2
               for item in result.diagnostics)

    for name in ("invalidUpdate", "danglingAnd", "danglingOrder"):
        assert queries[f"{name}:JPQL"].metadata["analysis_status"] == "UNKNOWN"
        assert not any(edge.source == queries[f"{name}:JPQL"].id
                       and edge.kind in {"query_reads", "query_writes", "query_deletes", "filters_by"}
                       for edge in result.edges)
    undeclared = queries["undeclaredBare:JPQL"]
    assert undeclared.metadata["analysis_status"] == "UNKNOWN"
    sibling = queries["siblingScopes:JPQL"]
    assert sibling.metadata["analysis_status"] == "COMPLETE"
    correlated = queries["correlatedScope:JPQL"]
    assert correlated.metadata["analysis_status"] == "COMPLETE"
    assert any(edge.source == correlated.id and edge.kind == "filters_by"
               and nodes[edge.target].name == "Customer.id" for edge in result.edges)


@pytest.mark.parametrize("query", [
    "delete from PurchaseOrder o where",
    "select o from PurchaseOrder o where o.status =",
    "select from PurchaseOrder o",
])
def test_incomplete_jpql_clauses_are_unknown(query):
    parsed = _parse_jpql_hql(query)
    assert parsed["status"] == "UNKNOWN"
    assert parsed["invalid_fragments"]


def test_jpql_aliases_are_case_insensitive_and_scoped():
    parsed = _parse_jpql_hql(
        "select O.id from PurchaseOrder o where exists "
        "(select o.id from Customer o where o.name = :name)"
    )
    assert parsed["status"] == "COMPLETE"
    assert {path["alias"].casefold() for path in parsed["paths"]} == {"o"}
    assert {path["depth"] for path in parsed["paths"]} == {0, 1}
    assert all(path["alias"].casefold() == "o" for path in parsed["paths"])


@pytest.mark.parametrize("query", [
    "select o from PurchaseOrder o where o.status = :status garbage",
    "update PurchaseOrder o set",
])
def test_unbound_alias_and_trailing_tokens_are_not_complete(query):
    parsed = _parse_jpql_hql(query)
    assert parsed["status"] == "UNKNOWN"


@pytest.mark.parametrize("old", [
    "annotation-source-v6-persistence-realms",
    "annotation-source-v7-persistence-realms-jpql",
    "annotation-source-v7-schema-compatibility",
])
def test_legacy_jpa_rules_remain_readable_but_require_reinspection(tmp_path, old):
    context = {"id": "old", "language": "jvm", "framework_rule_versions": {"jpa": old}}
    graph = KnowledgeGraph.from_dict({"schema_version": 3, "root": str(tmp_path), "generated_at": "",
                                     "files": {}, "nodes": [], "edges": [], "contexts": [context]})
    assert graph.contexts[0] == context
    with pytest.raises(WorkerError, match="persistence realm rules changed"):
        validate_context_snapshot(tmp_path, context)


def test_actual_javac_extended_jpql_fixture(tmp_path):
    annotations = {
        "Entity": "@Target(ElementType.TYPE) public @interface Entity { String name() default \"\"; }",
        "Id": "@Target({ElementType.FIELD,ElementType.METHOD}) public @interface Id {}",
        "Column": "@Target({ElementType.FIELD,ElementType.METHOD}) public @interface Column {}",
        "ManyToOne": "@Target({ElementType.FIELD,ElementType.METHOD}) public @interface ManyToOne {}",
    }
    sources = {
        **{f"jakarta/persistence/{name}.java": f"package jakarta.persistence; import java.lang.annotation.*; @Retention(RetentionPolicy.RUNTIME) {body}"
           for name, body in annotations.items()},
        "org/springframework/data/jpa/repository/JpaRepository.java":
            "package org.springframework.data.jpa.repository; public interface JpaRepository<T,ID> {}",
        "org/springframework/data/jpa/repository/Query.java": """package org.springframework.data.jpa.repository;
import java.lang.annotation.*; @Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME)
public @interface Query { String value() default ""; }""",
        "example/Model.java": """package example;
import jakarta.persistence.*; import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
@Entity class Customer { @Id Long id; @Column String name; }
@Entity(name="PurchaseOrder") class Order { @Id Long id; @Column String status; @ManyToOne Customer customer; }
class OrderSummary { OrderSummary(Long id, String name) {} }
interface Orders extends JpaRepository<Order,Long> {
 @Query("select new example.OrderSummary(o.id,c.name) from PurchaseOrder o join o.customer c where c.name=:name")
 List<OrderSummary> summaries(String name);
 @Query("update PurchaseOrder o set o.status=:status where o.customer.id=:customerId")
 int updateStatus(String status, Long customerId);
 @Query("delete from PurchaseOrder o where o.status=:status") int deleteStatus(String status);
}""",
    }
    for relative, text in sources.items():
        path = tmp_path / "src/main/java" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    try:
        result = inspect_jvm(tmp_path, classpath=[], publish=False)
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    graph = KnowledgeGraph.from_dict(result["graph"])
    queries = _queries(graph)
    assert queries["summaries:JPQL"].metadata["validated"] is True
    assert queries["summaries:JPQL"].metadata["analysis_status"] == "COMPLETE"
    assert any(edge.source == queries["summaries:JPQL"].id and edge.kind == "joins_by" for edge in graph.edges)
    assert any(edge.source == queries["updateStatus:JPQL"].id and edge.kind == "query_writes" for edge in graph.edges)
    assert any(edge.source == queries["deleteStatus:JPQL"].id and edge.kind == "query_deletes" for edge in graph.edges)


@pytest.mark.parametrize("query", [
    "select o from PurchaseOrder o where o.id = = :name",
    "select o from PurchaseOrder o where o.id :name",
    "select o from PurchaseOrder o where o.id = :name and not",
    "update PurchaseOrder o set o.status",
    "update PurchaseOrder o set o.status=:name,",
    "delete from PurchaseOrder o garbage",
    "select o from PurchaseOrder o where ()",
    "select o from PurchaseOrder o order by x",
])
def test_review_invalid_expressions_publish_no_persistence_evidence(tmp_path, query):
    _, graph, context = _fixture(tmp_path)
    symbol = next(item for item in graph.symbols if item['id'] == 'hql')
    symbol['annotations'][0]['values']['value'] = query
    result = augment_framework_graph(tmp_path, graph, context)
    node = _queries(result)['hqlWith:JPQL']
    assert node.metadata['analysis_status'] == 'UNKNOWN'
    assert node.metadata['validated'] is False
    assert not any(edge.source == node.id and edge.kind in {
        'query_reads', 'query_writes', 'query_deletes', 'filters_by', 'updates_attribute',
        'projects_attribute', 'orders_by', 'groups_by',
    } for edge in result.edges)


@pytest.mark.parametrize("query", [
    "select o from PurchaseOrder o where exists (select c.id from Customer c where (c.id=:name))",
    "select o from PurchaseOrder o where exists (select c.id from Customer c where c.id=o.customer.id)",
])
def test_review_nested_grouping_and_correlation_keep_exact_paths(tmp_path, query):
    _, graph, context = _fixture(tmp_path)
    symbol = next(item for item in graph.symbols if item['id'] == 'hql')
    symbol['annotations'][0]['values']['value'] = query
    result = augment_framework_graph(tmp_path, graph, context)
    node = _queries(result)['hqlWith:JPQL']
    assert node.metadata['analysis_status'] == 'COMPLETE'
    nodes = {item.id: item for item in result.nodes}
    assert any(edge.source == node.id and edge.kind == 'filters_by'
               and nodes[edge.target].name == 'Customer.id' for edge in result.edges)


@pytest.mark.parametrize('query', [
    'select count(o.id) from PurchaseOrder o where o.id between 1 and 10',
    'select o from PurchaseOrder o where not (o.id = :id or o.status is null)',
    "select o from PurchaseOrder o where o.status not in ('A', 'B') and o.id >= 1",
    "select o from PurchaseOrder o where lower(o.status) like 'a%'",
    'update PurchaseOrder o set o.id=o.id+1, o.status=:status where o.id in (select c.id from Customer c)',
    'select o.id, c.id from PurchaseOrder o left outer join o.customer c on c.id=o.customer.id group by o.id,c.id having count(c.id)>0 order by o.id desc',
])
def test_bounded_expression_and_clause_grammar(query):
    assert _parse_jpql_hql(query)['status'] == 'COMPLETE'


@pytest.mark.parametrize('query', [
    'select o from PurchaseOrder o where o.id > < :id',
    'select o from PurchaseOrder o where o.id = :id = :id',
    'select o from PurchaseOrder o where not o.id',
    'select o from PurchaseOrder o where o.id between 1 and',
    'select o from PurchaseOrder o where o.id in ()',
    'select o from PurchaseOrder o where o.id is',
    'select o from PurchaseOrder o where o.id + :id',
    'select o from PurchaseOrder o order by o.id,',
    'select o from PurchaseOrder o where exists (select c.id from Customer c where ())',
    'select o from PurchaseOrder o where exists (select c.id from Customer c) and c.id=:id',
    'select o from PurchaseOrder o where exists (select c.id from Customer c) and exists (select c.id from PurchaseOrder x)',
    'update PurchaseOrder o set o.id=:id where o.id=:id order by o.id',
])
def test_unconsumed_or_invalid_expression_is_unknown(query):
    parsed = _parse_jpql_hql(query)
    assert parsed['status'] == 'UNKNOWN'
    assert parsed['invalid_fragments']

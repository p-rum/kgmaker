import json
import tempfile
import unittest
from pathlib import Path

from kgmaker.analysis_model import AnalysisError, file_hash
from kgmaker.build_maven import discover
from kgmaker.callgraph import adjacency
from kgmaker.framework import augment_framework_graph
from kgmaker.model import KnowledgeGraph, Node
from kgmaker.runtime_evidence import import_manifest


class BuildAwareContractsTest(unittest.TestCase):
    def test_maven_discovery_is_declared_and_reports_missing_reactor_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text(
                """<project xmlns="http://maven.apache.org/POM/4.0.0">
                  <modelVersion>4.0.0</modelVersion>
                  <groupId>example</groupId><artifactId>parent</artifactId><version>1</version>
                  <modules><module>api</module><module>missing</module></modules>
                </project>"""
            )
            (root / "api").mkdir()
            (root / "api/pom.xml").write_text(
                """<project xmlns="http://maven.apache.org/POM/4.0.0">
                  <modelVersion>4.0.0</modelVersion>
                  <parent><groupId>example</groupId><artifactId>parent</artifactId><version>1</version></parent>
                  <artifactId>api</artifactId>
                </project>"""
            )
            result = discover(root)
            self.assertEqual(result["status"], "SOURCE_ONLY_DECLARED_MODEL")
            self.assertEqual([item["artifact_id"] for item in result["modules"]], ["api", "parent"])
            self.assertEqual(result["effective_model"], "UNAVAILABLE_WITHOUT_EXPLICIT_BUILD_EXPORT")
            self.assertEqual(result["diagnostics"][0]["code"], "MAVEN_MODULE_POM_MISSING")

    def test_framework_projection_keeps_framework_evidence_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "src/Payment.java"
            source_path.parent.mkdir(parents=True)
            source_path.write_text(
                """package example;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.GetMapping;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.springframework.data.jpa.repository.JpaRepository;
@Service class Payment {
  @GetMapping(\"/payments\") String list() { return \"ok\"; }
}
@Entity @Table(name=\"payments\") class PaymentEntity { @jakarta.persistence.Id Long id; }
interface PaymentRepository extends JpaRepository<PaymentEntity, Long> {
  PaymentEntity findById(Long id);
}
"""
            )
            context = {"id": "ctx", "scope": "production", "framework_rule_versions": {}}
            class_node = Node("class-payment", "class", "Payment", "src/Payment.java", line=5,
                              scope="production", role="executable_code", origin="handwritten")
            method_node = Node("method-list", "method", "list", "src/Payment.java", line=6,
                               scope="production", role="executable_code", origin="handwritten")
            entity_node = Node("class-entity", "class", "PaymentEntity", "src/Payment.java", line=9,
                               scope="production", role="executable_code", origin="handwritten")
            repository_node = Node("repo-payment", "interface", "PaymentRepository", "src/Payment.java", line=10,
                                   scope="production", role="contract", origin="handwritten")
            query_method_node = Node("method-find", "method", "findById", "src/Payment.java", line=11,
                                    scope="production", role="executable_code", origin="handwritten")
            table_node = Node("table-payments", "db_table", "payments", "db/V1__payments.sql", line=1,
                              scope="production", role="migration", origin="handwritten")
            symbols = [
                {"id": "class-payment", "name": "Payment", "kind": "class", "path": "src/Payment.java",
                 "range": {"start_line": 5}, "context_id": "ctx", "owner": "example.Payment",
                 "annotations": [{"name": "org.springframework.stereotype.Service", "values": {}}]},
                {"id": "method-list", "name": "list", "kind": "method", "path": "src/Payment.java",
                 "range": {"start_line": 6}, "context_id": "ctx", "owner": "example.Payment",
                 "annotations": [{"name": "org.springframework.web.bind.annotation.GetMapping", "values": {"value": ["/payments"]}}]},
                {"id": "class-entity", "name": "PaymentEntity", "kind": "class", "path": "src/Payment.java",
                 "range": {"start_line": 9}, "context_id": "ctx", "owner": "example.PaymentEntity",
                 "annotations": [{"name": "jakarta.persistence.Entity", "values": {}},
                 {"name": "jakarta.persistence.Table", "values": {"name": "payments"}}]},
                {"id": "repo-payment", "name": "PaymentRepository", "kind": "interface", "path": "src/Payment.java",
                 "range": {"start_line": 10}, "context_id": "ctx", "owner": "example.PaymentRepository",
                 "supertypes": ["java.lang.Object", "org.springframework.data.jpa.repository.JpaRepository<example.PaymentEntity,java.lang.Long>"],
                 "annotations": []},
                {"id": "method-find", "name": "findById", "kind": "method", "path": "src/Payment.java",
                 "range": {"start_line": 11}, "context_id": "ctx", "owner": "example.PaymentRepository",
                 "annotations": []},
            ]
            graph = KnowledgeGraph(3, ".", "now",
                                   [class_node, method_node, entity_node, repository_node, query_method_node, table_node], [],
                                   {"src/Payment.java": file_hash(source_path), "db/V1__payments.sql": "0"},
                                   [context], [], [], symbols, [], [])
            result = augment_framework_graph(root, graph, context)
            self.assertTrue(any(n.kind == "spring_endpoint" and n.name == "GET /payments" for n in result.nodes))
            self.assertTrue(any(n.kind == "orm_table" and n.name == "payments" for n in result.nodes))
            self.assertTrue(any(n.kind == "orm_query" and n.name == "findById:DERIVED" for n in result.nodes))
            self.assertTrue(any(e.kind == "repository_for" for e in result.edges))
            query = next(n for n in result.nodes if n.kind == "orm_query" and n.name == "findById:DERIVED")
            self.assertTrue(query.metadata["validated"])
            self.assertTrue(any(e.kind == "query_reads" and e.source == query.id for e in result.edges))
            self.assertTrue(any(e.kind == "filters_by" and e.source == query.id for e in result.edges))
            self.assertTrue(any(e.kind == "resolves_to_schema_table" and e.evidence_kind == "FRAMEWORK_DERIVED" for e in result.edges))

    def test_runtime_import_is_bound_to_context_and_rejects_stale_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/A.java"
            source.parent.mkdir(parents=True)
            source.write_text("class A {}\n")
            checksum = file_hash(source)
            context = {"id": "ctx", "scope": "production", "build_id": "build-1", "config_fingerprint": "cfg",
                       "source_files": {"src/A.java": checksum}, "worker": {"distribution": []}}
            nodes = [Node("caller", "method", "caller", "src/A.java", line=1, scope="production",
                          role="executable_code", origin="handwritten"),
                     Node("target", "method", "target", "src/A.java", line=1, scope="production",
                          role="executable_code", origin="handwritten")]
            graph = KnowledgeGraph(3, ".", "now", nodes, [], {"src/A.java": checksum}, [context], [], [], [], [], [])
            manifest = {"schema_version": 1, "runtime_id": "run-1", "context_id": "ctx", "build_id": "build-1",
                        "config_fingerprint": "cfg", "source_hashes": {"src/A.java": checksum},
                        "worker_distribution": [], "observations": [{"caller": "caller", "target": "target", "kind": "dispatch"}]}
            result = import_manifest(root, manifest, graph=graph)
            self.assertEqual(result["observations_imported"], 1)
            stored = KnowledgeGraph.from_dict(json.loads((root / ".kgmaker/graph.json").read_text()))
            self.assertTrue(any(edge.evidence_kind == "RUNTIME_OBSERVED" for edge in stored.edges))
            self.assertEqual(adjacency(stored)["caller"][0]["kind"], "RUNTIME_OBSERVED")
            source.write_text("class A { int changed; }\n")
            with self.assertRaises(AnalysisError) as error:
                import_manifest(root, manifest, graph=graph)
            self.assertEqual(error.exception.code, 3)

    def test_hb02_schema_realm_and_unverified_naming_do_not_silently_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/Entity.java"
            source.parent.mkdir(parents=True)
            source.write_text('''import jakarta.persistence.Entity;
import jakarta.persistence.Table;
@Entity @Table(name="payments") class Payment { }
@Entity class AuditLog { }
''')
            context = {"id": "ctx", "scope": "production", "framework_rule_versions": {},
                       "database_id": "primary", "schema_stream_id": "main",
                       "persistence_unit": "payments", "naming_strategy": "custom.Unverified"}
            payment = Node("payment", "class", "Payment", "src/Entity.java", line=3,
                           scope="production", role="executable_code", origin="handwritten")
            audit = Node("audit", "class", "AuditLog", "src/Entity.java", line=4,
                         scope="production", role="executable_code", origin="handwritten")
            tables = [
                Node("schema:primary:main:table:public.payments", "db_table", "public.payments", "db/primary.sql", 1),
                Node("schema:audit:main:table:public.payments", "db_table", "public.payments", "db/audit.sql", 1),
                Node("schema:primary:main:table:public.audit_log", "db_table", "public.audit_log", "db/primary.sql", 2),
            ]
            symbols = [
                {"id": "payment", "name": "Payment", "kind": "class", "path": "src/Entity.java",
                 "range": {"start_line": 3}, "context_id": "ctx",
                 "annotations": [{"name": "jakarta.persistence.Entity", "values": {}},
                                 {"name": "jakarta.persistence.Table", "values": {"name": "payments"}}]},
                {"id": "audit", "name": "AuditLog", "kind": "class", "path": "src/Entity.java",
                 "range": {"start_line": 4}, "context_id": "ctx",
                 "annotations": [{"name": "jakarta.persistence.Entity", "values": {}}]},
            ]
            graph = KnowledgeGraph(3, ".", "now", [payment, audit, *tables], [],
                                   {"src/Entity.java": file_hash(source)}, [context], [], [], symbols, [], [])
            result = augment_framework_graph(root, graph, context)
            resolved = [edge for edge in result.edges if edge.kind == "resolves_to_schema_table"]
            self.assertEqual(["schema:primary:main:table:public.payments"], [edge.target for edge in resolved])
            self.assertFalse(any(edge.target.endswith("audit_log") for edge in resolved))
            self.assertTrue(any(item.get("code") == "ORM_NAMING_STRATEGY_UNVERIFIED"
                                for item in result.diagnostics))

    def test_hb01_embedded_id_and_bidirectional_association_preserve_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/Model.java"
            source.parent.mkdir(parents=True)
            source.write_text('''package example;
import jakarta.persistence.*;
import java.util.List;
@Embeddable class OrderId { @Column(name="tenant_id") String tenant; @Column(name="order_no") String number; }
@Entity @Table(name="orders") class Order {
  @EmbeddedId @AttributeOverride(name="tenant", column=@Column(name="order_tenant")) OrderId id;
  @ManyToOne @JoinColumn(name="customer_id") Customer customer;
}
@Entity @Table(name="customers") class Customer {
  @Id @Column(name="id") Long id;
  @OneToMany(mappedBy="customer") List<Order> orders;
}
@Entity @Table(name="profiles") class Profile {
  private Long id;
  @Id @Column(name="profile_id") public Long getId() { return id; }
}
''')
            context = {"id": "ctx", "scope": "production", "framework_rule_versions": {},
                       "database_id": "primary", "schema_stream_id": "main", "persistence_unit": "orders"}
            declarations = [
                ("order-id", "OrderId", "class", 4,
                 [{"name": "jakarta.persistence.Embeddable", "values": {}}]),
                ("order", "Order", "class", 5,
                 [{"name": "jakarta.persistence.Entity", "values": {}},
                  {"name": "jakarta.persistence.Table", "values": {"name": "orders"}}]),
                ("customer", "Customer", "class", 9,
                 [{"name": "jakarta.persistence.Entity", "values": {}},
                  {"name": "jakarta.persistence.Table", "values": {"name": "customers"}}]),
                ("profile", "Profile", "class", 13,
                 [{"name": "jakarta.persistence.Entity", "values": {}},
                  {"name": "jakarta.persistence.Table", "values": {"name": "profiles"}}]),
            ]
            graph_nodes = [Node(identity, kind, name, "src/Model.java", line=line,
                                scope="production", role="executable_code", origin="handwritten")
                           for identity, name, kind, line, _ in declarations]
            graph_nodes.extend([
                Node("order-id-tenant", "field", "tenant", "src/Model.java", line=4,
                     scope="production", role="executable_code", origin="handwritten"),
                Node("order-id-number", "field", "number", "src/Model.java", line=4,
                     scope="production", role="executable_code", origin="handwritten"),
            ])
            symbols = [{"id": identity, "owner": f"example.{name}", "name": name, "kind": kind,
                        "path": "src/Model.java", "range": {"start_line": line},
                        "context_id": "ctx", "annotations": annotations}
                       for identity, name, kind, line, annotations in declarations]
            symbols.extend([
                {"id": "order-id-tenant", "owner": "example.OrderId", "name": "tenant", "kind": "field",
                 "path": "src/Model.java", "range": {"start_line": 4}, "type": "java.lang.String",
                 "context_id": "ctx", "annotations": [{"name": "jakarta.persistence.Column", "values": {"name": "tenant_id"}}]},
                {"id": "order-id-number", "owner": "example.OrderId", "name": "number", "kind": "field",
                 "path": "src/Model.java", "range": {"start_line": 4}, "type": "java.lang.String",
                 "context_id": "ctx", "annotations": [{"name": "jakarta.persistence.Column", "values": {"name": "order_no"}}]},
            ])
            schema = [
                Node("schema:primary:main:table:public.orders", "db_table", "public.orders", "db/V1.sql", 1),
                Node("schema:primary:main:table:public.customers", "db_table", "public.customers", "db/V1.sql", 2),
                Node("schema:primary:main:table:public.profiles", "db_table", "public.profiles", "db/V1.sql", 3),
            ]
            graph = KnowledgeGraph(3, ".", "now", [*graph_nodes, *schema], [],
                                   {"src/Model.java": file_hash(source)}, [context], [], [], symbols, [], [])
            result = augment_framework_graph(root, graph, context)
            by_name = {node.name: node for node in result.nodes}
            self.assertIn("OrderId", {node.name for node in result.nodes if node.kind == "orm_embeddable"})
            self.assertNotIn("OrderId", {node.name for node in result.nodes if node.kind == "orm_table"})
            order_id = by_name["Order.id"]
            self.assertTrue(order_id.metadata["identifier"])
            self.assertTrue(order_id.metadata["embedded"])
            self.assertTrue(any(edge.kind == "has_embedded_id" and edge.target == order_id.id for edge in result.edges))
            self.assertTrue(any(edge.kind == "embeds_type" and edge.source == order_id.id for edge in result.edges))
            self.assertTrue(any(node.kind == "orm_column" and node.name == "order_tenant" for node in result.nodes))
            embedded_attribute = by_name["OrderId.tenant"]
            self.assertEqual("tenant_id", embedded_attribute.metadata["default_column"])
            self.assertTrue(any(edge.kind == "overrides_attribute" and edge.target == embedded_attribute.id
                                for edge in result.edges))
            associations = {node.name: node for node in result.nodes if node.kind == "orm_association"}
            self.assertEqual("OWNING", associations["Order.customer"].metadata["association_role"])
            self.assertEqual("INVERSE", associations["Customer.orders"].metadata["association_role"])
            self.assertTrue(any(edge.kind == "inverse_of" and edge.source == associations["Customer.orders"].id
                                and edge.target == associations["Order.customer"].id for edge in result.edges))
            self.assertTrue(any(edge.kind == "targets_entity" for edge in result.edges
                                if edge.source in {item.id for item in associations.values()}))
            scalar_columns = {node.name for node in result.nodes if node.kind == "orm_column"}
            self.assertNotIn("customer", scalar_columns)
            self.assertNotIn("orders", scalar_columns)
            profile_id = by_name["Profile.id"]
            self.assertEqual("PROPERTY", profile_id.metadata["access"])
            self.assertEqual("PROPERTY", by_name["profiles"].metadata["access_strategy"])
            self.assertIn("profile_id", scalar_columns)


if __name__ == "__main__":
    unittest.main()

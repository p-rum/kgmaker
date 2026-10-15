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
@Entity @Table(name=\"payments\") class PaymentEntity { }
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
                 "range": {"start_line": 5}, "context_id": "ctx",
                 "annotations": [{"name": "org.springframework.stereotype.Service", "values": {}}]},
                {"id": "method-list", "name": "list", "kind": "method", "path": "src/Payment.java",
                 "range": {"start_line": 6}, "context_id": "ctx",
                 "annotations": [{"name": "org.springframework.web.bind.annotation.GetMapping", "values": {"value": ["/payments"]}}]},
                {"id": "class-entity", "name": "PaymentEntity", "kind": "class", "path": "src/Payment.java",
                 "range": {"start_line": 9}, "context_id": "ctx",
                 "annotations": [{"name": "jakarta.persistence.Entity", "values": {}},
                 {"name": "jakarta.persistence.Table", "values": {"name": "payments"}}]},
                {"id": "repo-payment", "name": "PaymentRepository", "kind": "interface", "path": "src/Payment.java",
                 "range": {"start_line": 10}, "context_id": "ctx", "annotations": []},
                {"id": "method-find", "name": "findById", "kind": "method", "path": "src/Payment.java",
                 "range": {"start_line": 11}, "context_id": "ctx", "annotations": []},
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


if __name__ == "__main__":
    unittest.main()

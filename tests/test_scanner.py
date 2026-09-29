from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kgmaker.cli import check, docs, hook_context, impact, init, main
from kgmaker.scanner import scan_repository
from kgmaker.store import load_graph, save_graph


class ScannerTests(unittest.TestCase):
    def test_extracts_python_symbols_and_internal_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("from service import build\n\ndef main():\n    return build()\n", encoding="utf-8")
            (root / "service.py").write_text("def build():\n    return object()\n", encoding="utf-8")

            graph = scan_repository(root)

            names = {(node.kind, node.name) for node in graph.nodes}
            self.assertIn(("function", "main"), names)
            self.assertIn(("function", "build"), names)
            imports = [edge for edge in graph.edges if edge.kind == "imports"]
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0].evidence, "service")

    def test_skips_secrets_and_dependency_folders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("def ok():\n    pass\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=never-index-this", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "lib.js").write_text("function privateThing() {}", encoding="utf-8")

            graph = scan_repository(root)

            self.assertEqual(set(graph.files), {"app.py"})
            self.assertNotIn("never-index-this", json.dumps(graph.to_dict()))

    def test_persists_and_loads_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "readme.md").write_text("# Architecture\n", encoding="utf-8")
            graph = scan_repository(root)
            save_graph(graph, root)

            loaded = load_graph(root)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.files, graph.files)
            self.assertTrue((root / ".kgmaker" / "GRAPH.md").exists())

    def test_resolves_python_package_relative_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "pkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "routes.py").write_text("from .service import build\n", encoding="utf-8")
            (package / "service.py").write_text("def build():\n    return True\n", encoding="utf-8")

            graph = scan_repository(root)

            imports = [edge for edge in graph.edges if edge.kind == "imports"]
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0].evidence, ".service")

    def test_init_preserves_existing_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / ".github" / "hooks" / "kgmaker.json"
            existing.parent.mkdir(parents=True)
            existing.write_text("user-managed", encoding="utf-8")

            init(root)

            self.assertEqual(existing.read_text(encoding="utf-8"), "user-managed")
            self.assertTrue((root / ".github" / "agents" / "kgmaker.agent.md").exists())

    def test_hook_emits_session_context_json(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("def main():\n    pass\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(hook_context(root), 0)

            result = json.loads(output.getvalue())
            self.assertIn("additionalContext", result)
            self.assertIn("app.py", result["additionalContext"])

    def test_impact_reports_exact_transitive_import_dependents(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core.py").write_text("def load():\n    return True\n", encoding="utf-8")
            (root / "service.py").write_text("from core import load\n", encoding="utf-8")
            (root / "api.py").write_text("from service import handle\n", encoding="utf-8")
            save_graph(scan_repository(root), root)
            output = io.StringIO()

            with redirect_stdout(output):
                result = impact(root, ["core.py"])

            self.assertEqual(result, 0)
            self.assertIn("service.py (1 hop; exact: import)", output.getvalue())
            self.assertIn("api.py (2 hops; exact: import)", output.getvalue())

    def test_check_detects_stale_graph_and_docs_regenerate_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.py"
            source.write_text("def first():\n    pass\n", encoding="utf-8")
            save_graph(scan_repository(root), root)
            self.assertEqual(check(root), 0)

            source.write_text("def second():\n    pass\n", encoding="utf-8")
            self.assertEqual(check(root), 2)
            markdown = root / ".kgmaker" / "GRAPH.md"
            markdown.write_text("stale", encoding="utf-8")
            self.assertEqual(docs(root), 0)
            self.assertIn("first", markdown.read_text(encoding="utf-8"))

    def test_check_command_works_without_local_json_index(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("def start():\n    pass\n", encoding="utf-8")
            save_graph(scan_repository(root), root)
            (root / ".kgmaker" / "graph.json").unlink()
            with patch("sys.argv", ["kgmaker", "check", "--root", str(root)]):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 0)

    def test_maps_kotlin_entities_repositories_and_columns_to_postgres_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "V1__orders.sql").write_text(
                "CREATE TABLE customer_orders (\n"
                "  id BIGINT PRIMARY KEY,\n"
                "  status VARCHAR(32) NOT NULL\n"
                ");\n",
                encoding="utf-8",
            )
            (root / "OrderEntity.kt").write_text(
                "import jakarta.persistence.Entity\n"
                "import jakarta.persistence.Table\n"
                "import jakarta.persistence.Column\n"
                "import org.springframework.data.jpa.repository.JpaRepository\n"
                "@Entity\n"
                "@Table(name = \"customer_orders\")\n"
                "data class OrderEntity(val id: Long) {\n"
                "  @Column(name = \"status\")\n"
                "  var status: String = \"\"\n"
                "}\n"
                "interface OrderRepository : JpaRepository<OrderEntity, Long>\n",
                encoding="utf-8",
            )

            graph = scan_repository(root)

            kinds = {node.kind for node in graph.nodes}
            self.assertIn("db_table", kinds)
            self.assertEqual(sum(node.kind == "db_column" for node in graph.nodes), 2)
            edges = {(edge.kind, edge.evidence) for edge in graph.edges}
            self.assertIn(("maps_to_table", "@Table annotation"), edges)
            self.assertIn(("maps_to_column", "@Column annotation"), edges)
            self.assertTrue(any(edge.kind == "repository_for" for edge in graph.edges))

    def test_finds_kafka_topics_and_postgres_connection_from_kotlin_and_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Events.kt").write_text(
                "import org.springframework.kafka.annotation.KafkaListener\n"
                "import org.springframework.kafka.core.KafkaTemplate\n"
                "class Events(val kafkaTemplate: KafkaTemplate<String, String>) {\n"
                "  fun publish() { kafkaTemplate.send(\"order-created\", \"payload\") }\n"
                "  @KafkaListener(topics = [\"order-created\", \"order-updated\"])\n"
                "  fun consume() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "application.yml").write_text(
                "spring:\n"
                "  kafka:\n"
                "    consumer:\n"
                "      topic: order-created\n"
                "  datasource:\n"
                "    url: jdbc:postgresql://localhost:5432/app\n",
                encoding="utf-8",
            )

            graph = scan_repository(root)

            topics = {node.name for node in graph.nodes if node.kind == "kafka_topic"}
            self.assertEqual(topics, {"order-created", "order-updated"})
            self.assertTrue(any(edge.kind == "consumes" for edge in graph.edges))
            self.assertTrue(any(edge.kind == "produces" for edge in graph.edges))
            self.assertTrue(any(edge.kind == "configures_topic" for edge in graph.edges))
            self.assertTrue(any(node.kind == "technology" and node.name == "PostgreSQL" for node in graph.nodes))

    def test_links_openapi_server_and_typescript_client_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "openapi.yaml").write_text(
                "openapi: 3.0.0\n"
                "paths:\n"
                "  /api/orders/{id}:\n"
                "    get:\n"
                "      operationId: getOrder\n",
                encoding="utf-8",
            )
            (root / "OrderController.kt").write_text(
                "import org.springframework.web.bind.annotation.GetMapping\n"
                "import org.springframework.web.bind.annotation.RequestMapping\n"
                "@RequestMapping(\"/api\")\n"
                "class OrderController {\n"
                "  @GetMapping(\"/orders/{id}\")\n"
                "  fun getOrder() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "BillingClient.kt").write_text(
                "import org.springframework.cloud.openfeign.FeignClient\n"
                "import org.springframework.web.service.annotation.GetExchange\n"
                "@FeignClient(name = \"billing\", url = \"https://billing.example\")\n"
                "interface BillingClient {\n"
                "  @GetExchange(\"/invoices/{id}\")\n"
                "  fun invoice()\n"
                "}\n",
                encoding="utf-8",
            )
            page = root / "frontend" / "app" / "orders" / "page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text(
                "export type OrderDto = { id: string };\n"
                "export function OrdersPage() { return fetch(`/api/orders/${id}`); }\n",
                encoding="utf-8",
            )

            graph = scan_repository(root)

            endpoints = [node for node in graph.nodes if node.kind == "api_endpoint"]
            endpoint_names = {node.name for node in endpoints}
            self.assertEqual(endpoint_names, {"GET /api/orders/{param}", "GET /invoices/{param}"})
            self.assertTrue(any(edge.kind == "declares_endpoint" for edge in graph.edges))
            self.assertTrue(any(edge.kind == "calls_endpoint" for edge in graph.edges))
            self.assertTrue(any(edge.kind == "defines_route" for edge in graph.edges))
            self.assertTrue(any(node.kind == "frontend_route" for node in graph.nodes))
            self.assertTrue(any(node.kind == "component" and node.name == "OrdersPage" for node in graph.nodes))
            self.assertTrue(any(node.kind == "type" and node.name == "OrderDto" for node in graph.nodes))
            self.assertTrue(any(node.kind == "external_service" and node.name == "billing" for node in graph.nodes))
            self.assertTrue(any(edge.kind == "uses_external_service" for edge in graph.edges))


if __name__ == "__main__":
    unittest.main()

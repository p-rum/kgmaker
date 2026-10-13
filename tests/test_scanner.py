from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kgmaker.cli import check, docs, hook_context, impact, init, main, semantic_apply, semantic_extract, semantic_update, semantic_validate
from kgmaker.confluence import documentation_check, ingest_export, merge_into_graph, render_report, validate_documents
from kgmaker.scanner import scan_repository
from kgmaker.semantic import (
    SEMANTIC_FILE, SEMANTIC_PATCH_FILE, SEMANTIC_UPDATE_FILE, SEMANTIC_EXTRACT_MARKDOWN,
    apply_semantic_layer, build_semantic_input, concept_id,
)
from kgmaker.store import load_graph, render_context, render_markdown, render_mermaid, save_graph


class ScannerTests(unittest.TestCase):
    def test_semantic_extract_can_run_as_standalone_initial_workflow(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "service.py").write_text("def service():\n    return True\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(semantic_extract(root, "HEAD~1"), 0)
            self.assertTrue((root / ".kgmaker" / "semantic-input.json").exists())
            instructions = (root / SEMANTIC_EXTRACT_MARKDOWN).read_text(encoding="utf-8")
            self.assertIn("Mode: `initial`", instructions)
            self.assertIn("semantic.json", instructions)

    def test_confluence_html_parser_resolves_pages_mermaid_and_drawio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "export"
            source_fixture = Path(__file__).parents[1] / "fixtures" / "confluence-export"
            import shutil
            shutil.copytree(source_fixture, export)

            documents, attachments, _ = ingest_export(export, root)

            payment = next(document for document in documents if document.file == "Payment-Architecture.html")
            self.assertEqual(payment.title, "Payment Architecture")
            self.assertIn("Customer-Onboarding.html", next(document for document in documents if document.file == "index.html").internal_links)
            self.assertIn("attachments/payment-flow.drawio", payment.attachments)
            self.assertTrue(any(diagram["kind"] == "MERMAID" for diagram in payment.diagrams))
            self.assertTrue(any(item["file"] == "attachments/payment-flow.drawio" for item in attachments))
            self.assertIn(("PaymentService", "CONNECTS_TO", "LegacyGateway"), next(item for item in attachments if item["file"].endswith("payment-flow.drawio"))["relations"])

    def test_confluence_code_is_truth_and_report_preserves_stale_documentation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "confluence-export"
            source_fixture = Path(__file__).parents[1] / "fixtures" / "confluence-export"
            import shutil
            shutil.copytree(source_fixture, export)
            (root / "payment.py").write_text(
                "from fraud import FraudService\n\nclass PaymentService:\n    def process(self):\n        return FraudService()\n",
                encoding="utf-8",
            )
            (root / "fraud.py").write_text("class FraudService:\n    pass\n", encoding="utf-8")
            graph = scan_repository(root)
            documents, attachments, _ = ingest_export(export, root)
            assertions = validate_documents(documents, graph)

            payment_assertions = [item for item in assertions if item.subject == "PaymentService"]
            self.assertTrue(any(item.status == "VERIFIED_BY_CODE" for item in payment_assertions))
            self.assertTrue(any(item.status == "DIAGRAM_CONTRADICTS_CODE" for item in payment_assertions))
            self.assertTrue(any(item.status == "NOT_VERIFIABLE_FROM_CODE" for item in assertions))
            merged = merge_into_graph(graph, documents, attachments, assertions)
            report_path = root / "docs/generated/confluence-inconsistencies.md"
            render_report(assertions, report_path, export)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("DIAGRAM_CONTRADICTS_CODE", report)
            self.assertIn("LegacyGateway", report)
            self.assertIn("Fraud validation exists", report)
            self.assertTrue(any(node.kind == "confluence_document" for node in merged.nodes))

    def test_docs_check_accepts_external_export_and_custom_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export = root / "external-docs"
            export.mkdir()
            (export / "page.html").write_text("<html><title>Page</title><body><h1>Page</h1><p>External process must be approved.</p></body></html>", encoding="utf-8")
            (root / "service.py").write_text("class Service: pass\n", encoding="utf-8")
            result, contradictions, review, report = documentation_check(root, str(export), "out/report.md", scan_repository(root))
            self.assertEqual((result, contradictions), (1, 0))
            self.assertGreaterEqual(review, 1)
            self.assertTrue(report.exists())
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
            call = next(edge for edge in graph.edges if edge.kind == "calls")
            self.assertEqual(call.confidence, "INFERRED")
            self.assertEqual(call.confidence_score, 0.85)

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
            self.assertTrue((root / ".kgmaker" / "GRAPH.mmd").exists())

    def test_scan_no_docs_skips_markdown_and_mermaid_but_keeps_index(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("def start():\n    pass\n", encoding="utf-8")
            with patch("sys.argv", ["kgmaker", "scan", "--root", str(root), "--no-docs"]):
                with self.assertRaises(SystemExit) as error:
                    main()

            self.assertEqual(error.exception.code, 0)
            self.assertTrue((root / ".kgmaker" / "graph.json").exists())
            self.assertFalse((root / ".kgmaker" / "GRAPH.md").exists())
            self.assertFalse((root / ".kgmaker" / "GRAPH.mmd").exists())
            self.assertEqual(docs(root), 0)
            self.assertTrue((root / ".kgmaker" / "GRAPH.md").exists())
            self.assertTrue((root / ".kgmaker" / "GRAPH.mmd").exists())

    def test_mermaid_visualization_groups_symbols_and_shows_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text("from service import build\n", encoding="utf-8")
            (root / "service.py").write_text("def build():\n    pass\n", encoding="utf-8")
            graph = scan_repository(root)

            diagram = render_mermaid(graph, scope="all")

            self.assertIn("flowchart LR", diagram)
            self.assertIn("app.py", diagram)
            self.assertIn("service.py", diagram)
            self.assertIn("|imports|", diagram)
            self.assertNotIn("build()", diagram)

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
            architect_agent = root / ".github" / "agents" / "kgmaker-architect.agent.md"
            self.assertTrue(architect_agent.exists())
            architect_content = architect_agent.read_text(encoding="utf-8")
            self.assertIn("infer: true", architect_content)
            self.assertIn("read-only repository context scout", architect_content)
            self.assertIn("kgmaker query", architect_content)
            instructions = (root / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
            self.assertIn("consult the `kgmaker-architect` custom agent", instructions)
            extract_agent = root / ".github" / "agents" / "kgmaker-extract.agent.md"
            self.assertTrue(extract_agent.exists())
            self.assertIn("semantic validate", extract_agent.read_text(encoding="utf-8"))
            self.assertIn("semantic update", extract_agent.read_text(encoding="utf-8"))
            ignored = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(".kgmaker/semantic-update.json", ignored)
            self.assertIn(".kgmaker/semantic-patch.json", ignored)

    def test_semantic_layer_uses_stable_ids_and_rejects_stale_or_dangling_edges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "OrderService.kt").write_text(
                "class OrderService {\n  fun publish() {}\n}\n", encoding="utf-8"
            )
            docs_dir = root / "docs"
            docs_dir.mkdir()
            (docs_dir / "domain.md").write_text(
                "# Domain\nThe order lifecycle rule is enforced before publishing.\n", encoding="utf-8"
            )
            structural = scan_repository(root)
            manifest = build_semantic_input(structural)
            manifest_text = json.dumps(manifest)
            self.assertNotIn("The order lifecycle rule", manifest_text)
            service = next(node for node in structural.nodes if node.name == "OrderService")
            concept = {
                "id": concept_id("docs/domain.md", "Order lifecycle rule"),
                "name": "Order lifecycle rule",
                "source_file": "docs/domain.md",
                "source_line": 2,
                "summary": "The rule is checked before publishing an order.",
            }
            artifact = {
                "schema_version": 2,
                "files": manifest["files"],
                "nodes": [concept],
                "edges": [{
                    "source": service.id,
                    "target": concept["id"],
                    "kind": "implements",
                    "confidence": "INFERRED",
                    "confidence_score": 0.85,
                    "source_file": "docs/domain.md",
                    "source_line": 2,
                    "evidence": "The domain document says the check occurs before publishing.",
                }],
            }
            semantic_path = root / SEMANTIC_FILE
            semantic_path.parent.mkdir(parents=True, exist_ok=True)
            semantic_path.write_text(json.dumps(artifact), encoding="utf-8")

            self.assertEqual(semantic_validate(root), 0)
            merged, counts, error = apply_semantic_layer(structural, root)
            self.assertIsNone(error)
            self.assertEqual(counts, (1, 1))
            relation = next(edge for edge in merged.edges if edge.kind == "implements")
            self.assertEqual(relation.source_file, "docs/domain.md")
            self.assertEqual(relation.confidence, "INFERRED")
            self.assertIn("INFERRED 0.85", render_markdown(merged, scope="all"))
            self.assertNotIn("Order lifecycle rule", render_context(merged, root=root))
            self.assertIn("unknown scope omitted", render_context(merged, root=root))

            artifact["edges"][0]["source_line"] = 999
            semantic_path.write_text(json.dumps(artifact), encoding="utf-8")
            _, _, error = apply_semantic_layer(scan_repository(root), root)
            self.assertIn("points past the end", error or "")

            artifact["edges"][0]["source_line"] = 2
            artifact["edges"][0]["target"] = "missing-node"
            semantic_path.write_text(json.dumps(artifact), encoding="utf-8")
            _, _, error = apply_semantic_layer(scan_repository(root), root)
            self.assertIn("reference removed or stale nodes", error or "")

            artifact["edges"][0]["target"] = concept["id"]
            semantic_path.write_text(json.dumps(artifact), encoding="utf-8")
            (root / "docs" / "domain.md").write_text(
                "# Domain\nThe order lifecycle rule changed after publishing.\n", encoding="utf-8"
            )
            _, counts, error = apply_semantic_layer(scan_repository(root), root)
            self.assertEqual(counts, (0, 0))
            self.assertIn("docs/domain.md", error or "")

    def test_semantic_update_refreshes_only_affected_entries(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "service.py").write_text("def before():\n    return True\n", encoding="utf-8")
            (root / "other.py").write_text("def stable():\n    return True\n", encoding="utf-8")
            (root / "domain.md").write_text("# Domain\nOrder rules are documented.\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "add", "service.py", "other.py", "domain.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
            base = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

            baseline = scan_repository(root)
            save_graph(baseline, root)
            service = next(node for node in baseline.nodes if node.name == "before")
            stable = next(node for node in baseline.nodes if node.name == "stable")
            concept = {
                "id": concept_id("domain.md", "Order rules"), "name": "Order rules",
                "source_file": "domain.md", "source_line": 2, "summary": "Order rules.",
            }
            artifact = {
                "schema_version": 2,
                "files": baseline.files,
                "nodes": [concept],
                "edges": [
                    {"source": service.id, "target": concept["id"], "kind": "implements", "confidence": "INFERRED", "confidence_score": 0.85, "source_file": "domain.md", "source_line": 2, "evidence": "Service implements documented order rules."},
                    {"source": stable.id, "target": concept["id"], "kind": "references", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": "domain.md", "source_line": 2, "evidence": "The domain note explicitly references stable."},
                ],
            }
            semantic_path = root / SEMANTIC_FILE
            semantic_path.parent.mkdir(parents=True, exist_ok=True)
            semantic_path.write_text(json.dumps(artifact), encoding="utf-8")
            (root / "service.py").write_text("def after():\n    return True\n", encoding="utf-8")
            current = scan_repository(root)
            from contextlib import redirect_stdout
            import io
            with redirect_stdout(io.StringIO()):
                self.assertEqual(semantic_update(root, base, token_budget=10), 0)
            update = json.loads((root / SEMANTIC_UPDATE_FILE).read_text(encoding="utf-8"))
            self.assertTrue((root / ".kgmaker" / "semantic-update.md").exists())
            review_note = (root / ".kgmaker" / "semantic-update.md").read_text(encoding="utf-8")
            self.assertEqual(update["token_budget"], 10)
            self.assertLessEqual(update["estimated_diff_tokens"], 10)
            self.assertIn("Requested token budget (approx.): 10", review_note)
            self.assertIn("before", review_note)
            self.assertIn("after", review_note)
            self.assertEqual([item["path"] for item in update["changed_files"]], ["service.py"])
            self.assertEqual(len(update["affected_semantic_edges"]), 1)
            stale_patch = root / SEMANTIC_PATCH_FILE
            stale_patch.write_text(json.dumps({"schema_version": 1, "update_id": "stale"}), encoding="utf-8")
            (root / "service.py").write_text("def after_again():\n    return False\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(semantic_update(root, base, token_budget=10), 0)
            refreshed_update = json.loads((root / SEMANTIC_UPDATE_FILE).read_text(encoding="utf-8"))
            self.assertFalse(stale_patch.exists())
            self.assertNotEqual(refreshed_update["update_id"], update["update_id"])
            # Continue the normal flow with a patch scoped to the refreshed packet.
            (root / "service.py").write_text("def after():\n    return True\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(semantic_update(root, base, token_budget=10), 0)
            update = json.loads((root / SEMANTIC_UPDATE_FILE).read_text(encoding="utf-8"))
            new_service = next(node for node in current.nodes if node.name == "after")
            patch = {
                "schema_version": 1,
                "update_id": update["update_id"],
                "nodes": [],
                "edges": [{"source": new_service.id, "target": concept["id"], "kind": "implements", "confidence": "INFERRED", "confidence_score": 0.85, "source_file": "domain.md", "source_line": 2, "evidence": "Updated service implements documented order rules."}],
                "remove_nodes": [], "remove_edges": [],
            }
            (root / SEMANTIC_UPDATE_FILE).write_text(json.dumps(update), encoding="utf-8")
            (root / SEMANTIC_PATCH_FILE).write_text(json.dumps(patch), encoding="utf-8")
            self.assertEqual(semantic_apply(root), 0)
            saved = json.loads(semantic_path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["edges"]), 2)
            self.assertIn(new_service.id, {edge["source"] for edge in saved["edges"]})
            self.assertIn(stable.id, {edge["source"] for edge in saved["edges"]})
            self.assertEqual(semantic_validate(root), 0)
            (root / "service.py").write_text("def changed_again():\n    return False\n", encoding="utf-8")
            from contextlib import redirect_stderr
            with redirect_stderr(io.StringIO()):
                self.assertEqual(semantic_apply(root), 2)

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
            self.assertNotIn("app.py", result["additionalContext"])
            self.assertIn("1 files with unknown scope omitted", result["additionalContext"])

            limited = io.StringIO()
            with redirect_stdout(limited):
                self.assertEqual(hook_context(root, token_budget=100), 0)
            limited_result = json.loads(limited.getvalue())
            self.assertLessEqual(len(limited_result["additionalContext"]), 400)

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
            (root / "src").mkdir()
            source = root / "src/app.py"
            source.write_text("def first():\n    pass\n", encoding="utf-8")
            save_graph(scan_repository(root), root)
            self.assertEqual(check(root), 0)

            mermaid = root / ".kgmaker" / "GRAPH.mmd"
            mermaid.write_text("stale", encoding="utf-8")
            self.assertEqual(check(root), 2)

            source.write_text("def second():\n    pass\n", encoding="utf-8")
            self.assertEqual(check(root), 2)
            markdown = root / ".kgmaker" / "GRAPH.md"
            mermaid = root / ".kgmaker" / "GRAPH.mmd"
            markdown.write_text("stale", encoding="utf-8")
            self.assertEqual(docs(root), 0)
            self.assertIn("first", markdown.read_text(encoding="utf-8"))
            self.assertIn("flowchart LR", mermaid.read_text(encoding="utf-8"))

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

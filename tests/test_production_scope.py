"""Metamorphic scope invariants and conservative evidence migration."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from kgmaker.analysis_model import AnalysisError
from kgmaker.classification import Classifier
from kgmaker.cli import main
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.scanner import scan_repository
from kgmaker.store import load_graph, query_nodes, render_mermaid, save_graph
from kgmaker.views import project, rank


class ProductionScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def cli(self, *args):
        output = io.StringIO()
        with patch("sys.argv", ["kgmaker", *args, "--root", str(self.root)]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                main()
        return result.exception.code, json.loads(output.getvalue())

    def production(self, graph):
        result = project(graph).to_dict()
        result.pop("generated_at")
        return result

    def test_cl01_cl02_tests_do_not_change_production_candidates_projection_or_ranking(self):
        self.write("src/main/kotlin/Service.kt", "fun handle() = process()\n")
        self.write("src/main/kotlin/Processor.kt", "fun process() = 1\n")
        before = scan_repository(self.root)
        self.assertEqual(1, len([e for e in project(before).edges if e.kind == "calls"]))
        self.write("src/test/kotlin/Processor.kt", "fun process() = 2\n")
        for i in range(500):
            self.write(f"tests/test_{i}.py", f"def test_case_{i}(): pass\n")
            self.write(f"docs/document_{i}.md", f"# Note {i}\nprocess()\n")
        after = scan_repository(self.root)
        self.assertEqual(self.production(before), self.production(after))
        self.assertEqual(rank(before), rank(after))
        self.assertEqual(render_mermaid(before), render_mermaid(after))
        self.assertEqual(query_nodes(before, "process", scope="production"),
                         query_nodes(after, "process", scope="production"))

    def test_cl03_multiple_build_memberships_custom_roots_generated_and_integration(self):
        model = {"source_sets": [
            {"id": "main", "module": "client", "scope": "production", "roots": ["custom"], "generated": True},
            {"id": "shared", "module": "api", "scope": "production", "files": ["custom/Api.kt"]},
            {"id": "integrationTest", "module": "api", "scope": "test", "roots": ["it"]}]}
        classifier = Classifier(self.root, model)
        result = classifier.classify("custom/Api.kt")
        self.assertEqual(("production", "executable_code", "generated"), (result.scope, result.role, result.origin))
        self.assertEqual(("api:shared", "client:main"), result.build_membership)
        self.assertEqual("test", classifier.classify("it/Flow.kt").scope)
        self.write("build/generated/Api.kt", "fun getApi() = 1\n")
        generated_model = {"source_sets": [{"id": "main", "module": "client", "scope": "production",
                                            "roots": ["build/generated"], "generated": True}]}
        self.assertFalse(scan_repository(self.root).nodes)
        generated = scan_repository(self.root, project_model=generated_model)
        self.assertTrue(generated.nodes)
        self.assertTrue(all(n.origin == "generated" for n in generated.nodes))

    def test_cl04_colocated_test_build_conflict_not_hidden(self):
        self.write("src/api.test.ts", "export function mock() {}\n")
        model = {"source_sets": [{"id": "main", "module": "web", "scope": "production", "files": ["src/api.test.ts"]}]}
        graph = scan_repository(self.root, project_model=model)
        self.assertEqual("production", graph.nodes[0].scope)
        self.assertTrue(any(d["code"] == "BUILD_SCOPE_CONFLICT" for d in graph.diagnostics))
        with self.assertRaises(AnalysisError):
            scan_repository(self.root, project_model=model, strict=True)

    def test_overrides_require_reason_retain_conflict_and_invalidate_context(self):
        self.write("src/main/App.kt", "fun start() = 1\n")
        before = scan_repository(self.root)
        self.write(".kgmaker/classification.json", json.dumps({"schema_version": 1, "overrides": [
            {"path": "src/main", "scope": "test", "reason": "Dedicated harness"}]}))
        after = scan_repository(self.root)
        self.assertNotEqual(before.contexts, after.contexts)
        self.assertFalse(project(after).nodes)
        model = {"source_sets": [{"module": "app", "id": "main", "scope": "production", "roots": ["src/main"]}]}
        self.assertTrue(scan_repository(self.root, project_model=model).diagnostics)
        self.write(".kgmaker/classification.json", '{"schema_version":1,"overrides":[{"path":"src"}]}')
        with self.assertRaises(AnalysisError):
            scan_repository(self.root)

    def test_cl05_configuration_documentation_and_migration_are_distinct(self):
        self.write("src/main/resources/application.yml", "url: https://example.invalid\n")
        self.write("src/main/resources/db/migration/V1__table.sql", "CREATE TABLE demo(id int);\n")
        self.write("src/main/Config.kt", "@Bean\nfun component() = buildComponent()\n")
        files = {n.path: n for n in scan_repository(self.root).nodes if n.kind == "file"}
        self.assertEqual("configuration", files["src/main/resources/application.yml"].role)
        self.assertEqual("migration", files["src/main/resources/db/migration/V1__table.sql"].role)
        self.assertEqual("executable_code", files["src/main/Config.kt"].role)

    def test_ev01_migration_does_not_promote_legacy_confidence_or_scope(self):
        legacy = KnowledgeGraph.from_dict({"schema_version": 1, "nodes": [
            {"id": "a", "kind": "function", "name": "a", "path": "App.kt", "scope": "production"},
            {"id": "b", "kind": "function", "name": "b", "path": "App.kt"}],
            "edges": [{"source": "a", "target": "b", "kind": "calls", "confidence_score": 1.0}], "files": {}})
        migrated = legacy.migrate_legacy()
        self.assertEqual(2, migrated.schema_version)
        self.assertTrue(all(n.scope == "unknown" for n in migrated.nodes))
        self.assertEqual("SYNTAX_CANDIDATE", migrated.edges[0].evidence_kind)
        self.assertEqual({"a": "a", "b": "b"}, migrated.contexts[0]["identity_mapping"])
        self.assertFalse(project(migrated).nodes)
        self.assertEqual(migrated, KnowledgeGraph.from_dict(migrated.to_dict()))

    def test_rk01_rk02_rk03_rk04_type_references_and_test_overlay_do_not_raise_execution_score(self):
        nodes = [Node("currency", "enum", "Currency", "src/Currency.kt", scope="production", role="executable_code"),
                 Node("decision", "method", "decide", "src/Currency.kt", scope="production", role="executable_code"),
                 Node("entry", "method", "entry", "src/Entry.kt", scope="production", role="executable_code")]
        graph = KnowledgeGraph(2, ".", "", nodes, [Edge("entry", "decision", "resolves_to", evidence_kind="SYMBOL_RESOLVED")], {})
        before = rank(graph, "entry")
        overlay = replace(graph, nodes=nodes + [Node("mock", "method", "mock", "test/Mock.kt", scope="test", role="executable_code")],
                          edges=graph.edges + [Edge("entry", "currency", "references_type") for _ in range(500)] + [Edge("mock", "currency", "resolves_to")])
        after = rank(overlay, "entry")
        self.assertEqual([(r["id"], r["score"]) for r in before["results"]], [(r["id"], r["score"]) for r in after["results"]])
        self.assertGreater(next(r["score"] for r in after["results"] if r["id"] == "decision"), next(r["score"] for r in after["results"] if r["id"] == "currency"))
        self.assertEqual(after, rank(overlay, "entry"))
        self.assertEqual(500, next(r["shared_references"] for r in after["results"] if r["id"] == "currency"))

    def test_bc03_failed_atomic_publication_keeps_last_valid_index(self):
        self.write("src/main.py", "def run(): pass\n")
        graph = scan_repository(self.root)
        save_graph(graph, self.root, generate_docs=False)
        old = (self.root / ".kgmaker/graph.json").read_bytes()
        with patch("kgmaker.analysis_model.os.replace", side_effect=OSError("cancelled")):
            with self.assertRaises(OSError):
                save_graph(graph, self.root, generate_docs=False)
        self.assertEqual(old, (self.root / ".kgmaker/graph.json").read_bytes())
        self.assertEqual(graph.to_dict(), load_graph(self.root).to_dict())

    def test_ev02_forged_evidence_reference_and_promoted_candidate_are_rejected(self):
        self.write("src/main.py", "def run(): pass\n")
        graph = scan_repository(self.root)
        self.assertTrue(graph.evidence)
        for edge in graph.edges:
            self.assertTrue(edge.context_ids)
            self.assertTrue(edge.evidence_ids)
        data = graph.to_dict()
        data["edges"][0]["evidence_ids"] = ["evidence:invented"]
        with self.assertRaisesRegex(ValueError, "Dangling"):
            KnowledgeGraph.from_dict(data)
        data = graph.to_dict()
        data["edges"][0]["evidence_kind"] = "SYMBOL_RESOLVED"
        with self.assertRaisesRegex(ValueError, "does not support"):
            KnowledgeGraph.from_dict(data)
        data = graph.to_dict()
        data["edges"][0]["context_ids"] = "not-an-array"
        with self.assertRaisesRegex(ValueError, "array"):
            KnowledgeGraph.from_dict(data)

    def test_ev04_mixed_source_snapshot_is_rejected(self):
        self.write("src/main.py", "def run(): pass\n")
        from kgmaker.scanner import _safe_source
        reads = []
        def changing(path):
            text = _safe_source(path)
            reads.append(path)
            if len(reads) == 1:
                path.write_text("def changed(): pass\n")
            return text
        with patch("kgmaker.scanner._safe_source", side_effect=changing):
            with self.assertRaisesRegex(AnalysisError, "snapshot changed"):
                scan_repository(self.root)

    def test_cli_partial_strict_and_freshness_are_distinct(self):
        self.write("src/main.py", "def run(): pass\n")
        code, report = self.cli("project", "classify", "--explain", "--format", "json")
        self.assertEqual((0, "PARTIAL"), (code, report["status"]))
        self.assertEqual(4, self.cli("project", "inspect", "--strict")[0])
        self.assertEqual("MISSING_INDEX", self.cli("coverage", "report")[1]["freshness"])
        save_graph(scan_repository(self.root), self.root, generate_docs=False)
        self.assertEqual("FRESH", self.cli("coverage", "report")[1]["freshness"])
        self.write("src/main.py", "def changed(): pass\n")
        self.assertEqual("STALE", self.cli("coverage", "report")[1]["freshness"])
        self.assertEqual(0, self.cli("graph", "rank", "--profile", "execution", "--explain")[0])

    def test_bc01_existing_build_scan_and_hook_never_launch_project_tools(self):
        from kgmaker.cli import hook_context, scan
        self.write("src/main.py", "def run(): pass\n")
        self.write("pom.xml", "<project/>\n")
        self.write("build.gradle.kts", "throw RuntimeException(\"must not execute\")\n")
        self.write("package.json", '{"scripts":{"test":"exit 99"}}')
        with patch("subprocess.run", side_effect=AssertionError("unexpected execution")), redirect_stdout(io.StringIO()):
            self.assertEqual(0, scan(self.root, generate_docs=False))
            self.assertEqual(0, hook_context(self.root))
            self.assertEqual(0, self.cli("project", "inspect")[0])
            with patch("sys.argv", ["kgmaker", "build", "--root", str(self.root), "--no-docs"]):
                with self.assertRaises(SystemExit) as result:
                    main()
            self.assertEqual(0, result.exception.code)


if __name__ == "__main__":
    unittest.main()

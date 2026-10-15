import hashlib
import json
import subprocess
import tempfile
import unittest
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker.cli import main, memory_capture, memory_recall
from kgmaker.memory import episode_id, episode_freshness, recall, validate_episode
from kgmaker.scanner import scan_repository
from kgmaker.semantic import SEMANTIC_FILE, apply_semantic_layer, build_semantic_input, concept_id
from kgmaker.store import render_context, render_markdown, render_mermaid, save_graph


class MemoryContractTests(unittest.TestCase):
    def _repository(self, root: Path) -> str:
        (root / "service.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
        (root / "removed.py").write_text("def obsolete():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
        save_graph(scan_repository(root), root, generate_docs=False)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    def _episode(self, node_id: str, digest: str) -> dict:
        record = {
            "base_commit": "a" * 40,
            "head_commit": "b" * 40,
            "worktree_fingerprint": "c" * 64,
            "title": "Implement greeting",
            "changed_files": [{"path": "service.py", "status": "M", "sha256": digest}],
            "affected_node_ids": [node_id],
            "graph_delta": {"added": [node_id], "removed": [], "changed": []},
            "validations": [{"label": "unit-tests", "status": "passed"}],
        }
        record["id"] = episode_id(record)
        return record

    def test_episode_id_is_stable_and_contract_rejects_malformed_records(self) -> None:
        episode = self._episode("function:service.py:greet", "d" * 64)
        self.assertEqual(episode_id(episode), episode["id"])
        self.assertEqual(validate_episode(episode), episode)
        malformed = {**episode, "changed_files": [{"path": "service.py", "status": "M", "sha256": "bad"}]}
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_episode(malformed)

    def test_v3_projects_episode_and_omits_dangling_affected_edges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "service.py"
            source.write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
            graph = scan_repository(root)
            function = next(node for node in graph.nodes if node.name == "greet")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            episode = self._episode(function.id, digest)
            episode["affected_node_ids"].append("function:removed.py:gone")
            episode["id"] = episode_id(episode)
            artifact = {"schema_version": 3, "files": graph.files, "nodes": [], "edges": [], "episodes": [episode]}
            path = root / SEMANTIC_FILE
            path.parent.mkdir()
            path.write_text(json.dumps(artifact), encoding="utf-8")

            original_node_ids = [node.id for node in graph.nodes]
            original_edge_count = len(graph.edges)
            merged, counts, error = apply_semantic_layer(graph, root)
            self.assertIsNone(error)
            self.assertEqual(counts, (1, 1))
            self.assertEqual(original_node_ids, [node.id for node in graph.nodes])
            self.assertEqual(original_edge_count, len(graph.edges))
            projected = next(node for node in merged.nodes if node.id == episode["id"])
            self.assertEqual(projected.kind, "implementation_episode")
            self.assertEqual(projected.metadata["base_commit"], "a" * 40)
            self.assertEqual(episode_freshness(episode, graph.files), "current")
            self.assertFalse(any(edge.target == "function:removed.py:gone" for edge in merged.edges))

            markdown = render_markdown(merged)
            diagram = render_mermaid(merged)
            self.assertIn("Implementation history", markdown)
            self.assertIn("Implement greeting", markdown)
            self.assertIn("unit-tests=passed", markdown)
            self.assertNotIn("implementation_episode", diagram)
            self.assertNotIn("affected", diagram)
            self.assertNotIn("service.py", diagram)

            source.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")
            current = scan_repository(root)
            merged, counts, error = apply_semantic_layer(current, root)
            self.assertEqual(counts, (1, 1))
            self.assertIsNone(error)
            projected = next(node for node in merged.nodes if node.id == episode["id"])
            self.assertEqual(projected.metadata["freshness"], "changed")

    def test_v2_concepts_remain_readable_and_v3_preserves_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "domain.md"
            source.write_text("# Domain\nGreeting policy.\n", encoding="utf-8")
            graph = scan_repository(root)
            concept = {
                "id": concept_id("domain.md", "Greeting policy"), "name": "Greeting policy",
                "source_file": "domain.md", "source_line": 2, "summary": "Greeting policy.",
            }
            base = {"files": build_semantic_input(graph)["files"], "nodes": [concept], "edges": []}
            for version, episodes in ((2, None), (3, [])):
                artifact = {"schema_version": version, **base}
                if episodes is not None:
                    artifact["episodes"] = episodes
                path = root / SEMANTIC_FILE
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(artifact), encoding="utf-8")
                merged, counts, error = apply_semantic_layer(scan_repository(root), root)
                self.assertIsNone(error)
                self.assertEqual(counts, (1, 0))
                self.assertIn(concept["id"], {node.id for node in merged.nodes})

    def test_capture_records_dirty_untracked_deleted_and_filters_sensitive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._repository(root)
            old_artifact = {"schema_version": 2, "files": scan_repository(root).files, "nodes": [], "edges": []}
            semantic = root / SEMANTIC_FILE
            semantic.write_text(json.dumps(old_artifact), encoding="utf-8")
            (root / "service.py").write_text("def greet(name):\n    return name\n", encoding="utf-8")
            (root / "removed.py").unlink()
            (root / "new.py").write_text("def added():\n    pass\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=must-not-leak", encoding="utf-8")

            self.assertEqual(memory_capture(root, base, ["unit-tests=passed"]), 0)
            artifact = json.loads(semantic.read_text(encoding="utf-8"))
            self.assertEqual(artifact["schema_version"], 3)
            self.assertEqual((artifact["nodes"], artifact["edges"]), ([], []))
            episode = artifact["episodes"][0]
            by_path = {item["path"]: item for item in episode["changed_files"]}
            self.assertEqual(set(by_path), {"new.py", "removed.py", "service.py"})
            self.assertEqual(by_path["removed.py"], {"path": "removed.py", "status": "D", "sha256": None})
            self.assertEqual(episode["validations"], [{"label": "unit-tests", "status": "passed"}])
            self.assertNotIn("must-not-leak", json.dumps(artifact))
            self.assertTrue(episode["affected_node_ids"])

            before = semantic.read_bytes()
            self.assertEqual(memory_capture(root, base, ["other=failed"]), 0)
            self.assertEqual(semantic.read_bytes(), before)

    def test_capture_clean_sensitive_only_and_invalid_inputs_do_not_mutate_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._repository(root)
            semantic = root / SEMANTIC_FILE
            semantic.write_text(json.dumps({
                "schema_version": 3, "files": scan_repository(root).files,
                "nodes": [], "edges": [], "episodes": [],
            }), encoding="utf-8")
            before = semantic.read_bytes()
            self.assertEqual(memory_capture(root, base, []), 2)
            self.assertEqual(semantic.read_bytes(), before)
            (root / ".env").write_text("TOKEN=private", encoding="utf-8")
            self.assertEqual(memory_capture(root, base, []), 2)
            self.assertEqual(memory_capture(root, "not-a-ref", []), 2)
            self.assertEqual(memory_capture(root, base, ["tests=maybe"]), 2)
            self.assertEqual(semantic.read_bytes(), before)

    def test_capture_accepts_a_clean_committed_change_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._repository(root)
            (root / "service.py").write_text("def greet():\n    return 'committed'\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "service.py"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "Improve greeting"], check=True)

            self.assertEqual(memory_capture(root, base, []), 0)
            artifact = json.loads((root / SEMANTIC_FILE).read_text(encoding="utf-8"))
            episode = artifact["episodes"][0]
            self.assertEqual(episode["title"], "Improve greeting")
            self.assertNotEqual(episode["base_commit"], episode["head_commit"])
            self.assertEqual(episode["changed_files"][0]["path"], "service.py")

    def test_capture_rejects_malformed_artifact_and_cli_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._repository(root)
            semantic = root / SEMANTIC_FILE
            semantic.write_text('{"schema_version": 3, "nodes": "bad"}', encoding="utf-8")
            (root / "service.py").write_text("def greet():\n    return 'hello'\n", encoding="utf-8")
            before = semantic.read_bytes()
            self.assertEqual(memory_capture(root, base, []), 2)
            self.assertEqual(semantic.read_bytes(), before)
            semantic.unlink()
            with patch("sys.argv", [
                "kgmaker", "memory", "capture", "--root", str(root), "--base", base,
                "--validation", "tests=passed",
            ]):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 0)

    def test_recall_ranks_relevant_episode_and_enforces_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "billing.py").write_text("def refund_invoice():\n    pass\n", encoding="utf-8")
            (root / "unrelated.py").write_text("def render_avatar():\n    pass\n", encoding="utf-8")
            graph = scan_repository(root)
            billing = next(node for node in graph.nodes if node.name == "refund_invoice")
            avatar = next(node for node in graph.nodes if node.name == "render_avatar")
            current = self._episode(billing.id, graph.files["billing.py"])
            current["title"] = "Implement invoice refund"
            current["changed_files"] = [{"path": "billing.py", "status": "M", "sha256": graph.files["billing.py"]}]
            current["id"] = episode_id(current)
            unrelated = self._episode(avatar.id, graph.files["unrelated.py"])
            unrelated["title"] = "Render user avatar"
            unrelated["changed_files"] = [{"path": "unrelated.py", "status": "M", "sha256": graph.files["unrelated.py"]}]
            unrelated["id"] = episode_id(unrelated)
            from kgmaker.memory import project_episode
            for episode in (current, unrelated):
                node, edges = project_episode(episode, {item.id for item in graph.nodes}, graph.files)
                graph.nodes.append(node)
                graph.edges.extend(edges)

            result = recall(graph, "invoice refund", limit=1, token_budget=120,
                            baseline=render_context(graph, root=root))
            self.assertIn("Implement invoice refund", result)
            self.assertNotIn("Render user avatar", result)
            self.assertIn("Estimated tokens:", result)
            self.assertIn("reduction vs broad context", result)
            self.assertLessEqual((len(result) + 3) // 4, 120)
            self.assertEqual(result.count("- **Episode"), 1)

    def test_recall_falls_back_to_current_locations_and_labels_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "orders.py").write_text("def submit_order():\n    pass\n", encoding="utf-8")
            graph = scan_repository(root)
            result = recall(graph, "submit order", limit=2, token_budget=100,
                            baseline=render_context(graph, root=root))
            self.assertIn("orders.py:1", result)
            self.assertIn("submit_order", result)

            target = next(node for node in graph.nodes if node.name == "submit_order")
            episode = self._episode(target.id, "d" * 64)
            from kgmaker.memory import project_episode
            node, edges = project_episode(episode, {item.id for item in graph.nodes}, graph.files)
            graph.nodes.append(node)
            graph.edges.extend(edges)
            historical = recall(graph, "greeting", limit=2, token_budget=120,
                                baseline=render_context(graph, root=root))
            self.assertIn("HISTORICAL—removed", historical)

    def test_memory_recall_cli_dispatches_and_rejects_invalid_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "search.py").write_text("def locate_customer():\n    pass\n", encoding="utf-8")
            save_graph(scan_repository(root), root, generate_docs=False)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(memory_recall(root, "locate customer", 3, 100), 0)
            self.assertIn("locate_customer", output.getvalue())
            self.assertEqual(memory_recall(root, "customer", 0, 100), 2)
            with patch("sys.argv", [
                "kgmaker", "memory", "recall", "locate", "customer", "--root", str(root),
                "--limit", "2", "--token-budget", "100",
            ]):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

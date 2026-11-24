import io
import json
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from kgmaker.cli import init, main, task_add, task_advance, task_context, task_list, task_record, task_show, task_stop
from kgmaker.context import prepare_packet
from kgmaker.scanner import scan_repository
from kgmaker.semantic import SEMANTIC_FILE
from kgmaker.store import save_graph
from kgmaker.workflow import (
    WorkflowError,
    add_task,
    advance_task,
    artifact_id,
    create_task,
    legal_transitions,
    record_artifact,
    save_task,
    stop_task,
    task_id,
    validate_task,
)


class WorkflowContractTests(unittest.TestCase):
    def _task(self, root: Path, request: str = "Add a workflow task store", title: str = "Workflow store") -> dict:
        return add_task(root, request, title=title)

    def _architect_artifact(self, task: dict, summary: str = "Inspected cli and store.") -> dict:
        payload = {
            "task_id": task["id"],
            "role": "architect",
            "phase": "analyze",
            "iteration": task["iteration"],
            "summary": summary,
            "status": "completed",
            "cited_paths": ["src/kgmaker/cli.py"],
            "cited_node_ids": ["function:src/kgmaker/cli.py:main"],
            "packet_id": None,
            "disposition": None,
        }
        payload["id"] = artifact_id(payload)
        return payload

    def _plan_artifact(self, task: dict) -> dict:
        payload = {
            "task_id": task["id"],
            "role": "architect",
            "phase": "plan",
            "iteration": task["iteration"],
            "summary": "Plan workflow module and CLI wiring.",
            "status": "completed",
            "cited_paths": ["src/kgmaker/cli.py"],
            "cited_node_ids": [],
            "packet_id": None,
            "disposition": None,
            "steps": [{
                "id": "schema",
                "intent": "Add task schema and persistence",
                "paths": ["src/kgmaker/workflow.py"],
                "tests": ["tests/test_workflow.py"],
            }],
            "out_of_scope": ["src/kgmaker/model.py"],
        }
        payload["id"] = artifact_id(payload)
        return payload

    def test_task_id_is_stable_and_unknown_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = create_task(root, "Add durable workflow state", title="Workflow MVP")
            self.assertEqual(task["id"], task_id(task["title"], task["request"], task["max_iterations"], task["base_commit"]))
            self.assertEqual(validate_task(task), task)
            self.assertEqual(task["status"], "intake")
            self.assertIsNone(task["base_commit"])
            malformed = {**task, "extra": True}
            with self.assertRaisesRegex(WorkflowError, "exactly the workflow contract fields"):
                validate_task(malformed)
            with self.assertRaisesRegex(WorkflowError, "sensitive"):
                validate_task({**task, "accepted_paths": [".env"]})

    def test_phase_machine_rejects_skipping_analyze_and_enforces_retry_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self._task(root, title="Phase machine", request="Do not skip analysis")
            with self.assertRaisesRegex(WorkflowError, "cannot advance"):
                advance_task(root, task["id"], "implement")
            self.assertEqual(legal_transitions(task), ["analyze"])
            current = advance_task(root, task["id"], "analyze")
            current = advance_task(root, current["id"], "plan")
            current = advance_task(root, current["id"], "implement")
            current = advance_task(root, current["id"], "test")
            self.assertEqual(current["iteration"], 0)
            current = advance_task(root, current["id"], "implement")
            self.assertEqual(current["status"], "implement")
            self.assertEqual(current["iteration"], 1)
            current = advance_task(root, current["id"], "test")
            current = advance_task(root, current["id"], "implement")
            current = advance_task(root, current["id"], "test")
            self.assertEqual(current["iteration"], 2)
            self.assertIn("failed", legal_transitions(current))
            self.assertNotIn("implement", legal_transitions(current))
            current = advance_task(root, current["id"], "failed")
            self.assertEqual(current["status"], "failed")
            self.assertEqual(current["stop_reason"], "advanced to failed")
            with self.assertRaisesRegex(WorkflowError, "cannot advance"):
                advance_task(root, current["id"], "review")

    def test_atomic_save_and_isolation_from_semantic_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self._task(root)
            path = save_task(root, task)
            self.assertTrue(path.exists())
            self.assertFalse((root / SEMANTIC_FILE).exists())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["id"], task["id"])
            self.assertEqual(add_task(root, task["request"], title=task["title"])["id"], task["id"])

    def test_record_plan_updates_accepted_paths_and_rejects_packet_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self._task(root)
            advance_task(root, task["id"], "analyze")
            task = record_artifact(root, task["id"], "architect", self._architect_artifact(task))
            self.assertEqual(len(task["artifacts"]), 1)
            advance_task(root, task["id"], "plan")
            task = record_artifact(root, task["id"], "architect", self._plan_artifact({**task, "status": "plan"}))
            self.assertEqual(task["plan_revision"], 1)
            self.assertIn("src/kgmaker/workflow.py", task["accepted_paths"])
            bad = self._architect_artifact({**task, "status": "analyze", "iteration": 0})
            bad["packet_id"] = "packet:" + ("a" * 64)
            bad["phase"] = "plan"
            del bad["id"]
            with self.assertRaisesRegex(WorkflowError, "exactly the architect artifact fields"):
                record_artifact(root, task["id"], "architect", bad)
            plan = self._plan_artifact(task)
            plan["packet_id"] = "packet:" + ("b" * 64)
            plan["id"] = artifact_id(plan)
            with self.assertRaisesRegex(WorkflowError, "packet is missing"):
                record_artifact(root, task["id"], "architect", plan)

    def test_stop_requires_reason_and_blocks_further_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self._task(root)
            stopped = stop_task(root, task["id"], "out of scope")
            self.assertEqual(stopped["status"], "failed")
            self.assertEqual(stopped["stop_reason"], "out of scope")
            with self.assertRaisesRegex(WorkflowError, "terminal"):
                record_artifact(root, task["id"], "orchestrator", {
                    "summary": "halt", "status": "blocked", "cited_paths": [],
                    "cited_node_ids": [], "packet_id": None, "disposition": None,
                })


class WorkflowContextTests(unittest.TestCase):
    def _repo(self, root: Path) -> None:
        (root / "src").mkdir()
        (root / "src" / "billing.py").write_text("def refund_invoice():\n    return True\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_billing.py").write_text("def test_refund_invoice():\n    assert True\n", encoding="utf-8")
        (root / ".env").write_text("TOKEN=private\n", encoding="utf-8")
        save_graph(scan_repository(root), root, generate_docs=False)

    def test_packet_uses_graph_memory_and_omits_secrets_and_semantic_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._repo(root)
            task = add_task(root, "refund invoice workflow", title="Refund invoice")
            packet = prepare_packet(root, task, "architect", token_budget=400)
            self.assertEqual(packet["graph_status"], "current")
            self.assertEqual(packet["task_id"], task["id"])
            self.assertTrue(packet["packet_id"].startswith("packet:"))
            self.assertLessEqual(packet["token_estimate"], 400)
            names = {node["name"] for node in packet["nodes"]}
            self.assertTrue({"refund_invoice", "billing.py", "test_refund_invoice"} & names)
            self.assertTrue(all(node["origin"] in {"scan", "semantic", "episode"} for node in packet["nodes"]))
            self.assertIn("heuristic calls are leads", packet["warnings"])
            encoded = json.dumps(packet)
            self.assertNotIn("TOKEN=private", encoded)
            self.assertFalse((root / SEMANTIC_FILE).exists())
            self.assertTrue((root / ".kgmaker/workflow/packets").exists())

    def test_missing_graph_is_warned_and_budget_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = add_task(root, "no graph yet", title="Missing graph")
            packet = prepare_packet(root, task, "orchestrator", token_budget=128)
            self.assertEqual(packet["graph_status"], "missing")
            self.assertEqual(packet["nodes"], [])
            self.assertEqual(packet["legal_next"], ["analyze"])
            self.assertLessEqual(packet["token_estimate"], 128)
            with self.assertRaisesRegex(ValueError, "token budget"):
                prepare_packet(root, task, "orchestrator", token_budget=8)

    def test_stale_graph_status_does_not_rewrite_the_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._repo(root)
            task = add_task(root, "refund invoice", title="Stale graph")
            (root / "src" / "billing.py").write_text("def refund_invoice():\n    return False\n", encoding="utf-8")
            before = (root / ".kgmaker/graph.json").read_bytes()
            packet = prepare_packet(root, task, "implementation", token_budget=200)
            self.assertEqual(packet["graph_status"], "stale")
            self.assertEqual((root / ".kgmaker/graph.json").read_bytes(), before)

    def test_packet_freshness_uses_same_workbook_inputs_as_scan(self) -> None:
        from kgmaker.cli import scan
        from kgmaker.store import load_graph

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = Path(__file__).resolve().parents[1] / "fixtures/workbooks/legacy-biff2.xls"
            workbook = root / fixture.name
            workbook.write_bytes(fixture.read_bytes())
            with redirect_stdout(io.StringIO()):
                self.assertEqual(scan(root, generate_docs=False), 0)
            self.assertIn(workbook.name, load_graph(root).files)
            task = add_task(root, "check workbook evidence")
            stored = root / ".kgmaker/graph.json"
            before = stored.read_bytes()
            with patch("subprocess.Popen", side_effect=AssertionError("offline packet launched a process")):
                current = prepare_packet(root, task, "architect", persist=False)
                self.assertEqual(current["graph_status"], "current")
                workbook.write_bytes(workbook.read_bytes() + b"\x00")
                stale = prepare_packet(root, task, "architect", persist=False)
                self.assertEqual(stale["graph_status"], "stale")
            self.assertEqual(stored.read_bytes(), before)
            self.assertFalse((root / ".kgmaker/workflow/packets").exists())

    def test_packet_freshness_handles_unparseable_workbook_edit(self) -> None:
        from kgmaker.cli import scan
        from kgmaker.store import GRAPH_FILE, load_graph

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "model.xlsx"
            with ZipFile(workbook, "w") as archive:
                archive.writestr("xl/workbook.xml", "<workbook/>")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(scan(root, generate_docs=False), 0)
            self.assertIn(workbook.name, load_graph(root).files)
            task = add_task(root, "check workbook drift")
            stored = root / GRAPH_FILE
            before = stored.read_bytes()
            with ZipFile(workbook, "w") as archive:
                archive.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="invalid-encoding"?><workbook/>')
            with patch("subprocess.Popen", side_effect=AssertionError("offline packet launched a process")):
                stale = prepare_packet(root, task, "architect", persist=False)
            self.assertEqual(stale["graph_status"], "stale")
            self.assertEqual(stored.read_bytes(), before)


class WorkflowCliTests(unittest.TestCase):
    def _git_repo(self, root: Path) -> str:
        (root / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()

    def test_cli_add_show_list_advance_stop_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            head = self._git_repo(root)
            save_graph(scan_repository(root), root, generate_docs=False)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(task_add(root, "wire task CLI", "Task CLI", 3), 0)
            task_identifier = output.getvalue().splitlines()[0]
            self.assertTrue(task_identifier.startswith("task:"))
            listed = io.StringIO()
            with redirect_stdout(listed):
                self.assertEqual(task_list(root, None), 0)
            self.assertIn(task_identifier, listed.getvalue())
            shown = io.StringIO()
            with redirect_stdout(shown):
                self.assertEqual(task_show(root, task_identifier), 0)
            document = json.loads(shown.getvalue())
            self.assertEqual(document["base_commit"], head)
            self.assertEqual(task_advance(root, task_identifier, "analyze"), 0)
            artifact = {
                "summary": "CLI wiring is local.",
                "status": "completed",
                "cited_paths": ["app.py"],
                "cited_node_ids": [],
                "packet_id": None,
                "disposition": None,
            }
            artifact_path = root / "artifact.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            self.assertEqual(task_record(root, task_identifier, "architect", artifact_path), 0)
            context_out = io.StringIO()
            with redirect_stdout(context_out):
                self.assertEqual(task_context(root, task_identifier, "architect", 200), 0)
            self.assertIn("packet_id", context_out.getvalue())
            self.assertEqual(task_stop(root, task_identifier, "pause work"), 0)
            self.assertFalse((root / SEMANTIC_FILE).exists())
            with patch("sys.argv", ["kgmaker", "task", "list", "--root", str(root), "--status", "failed"]):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 0)

    def test_init_ignores_workflow_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(init(root), 0)
            ignored = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(".kgmaker/workflow/", ignored)


if __name__ == "__main__":
    unittest.main()

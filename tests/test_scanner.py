from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kgmaker.cli import hook_context, init
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


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path

from kgmaker.analysis_model import AnalysisError, file_hash
from kgmaker.model import KnowledgeGraph, Node
from kgmaker.runtime_evidence import produce_manifest
from kgmaker.store import save_graph


class RuntimeTraceProducerTest(unittest.TestCase):
    def _root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        source = root / "src/App.java"
        source.parent.mkdir(parents=True)
        source.write_text("class App {}\n", encoding="utf-8")
        checksum = file_hash(source)
        context = {"id": "ctx", "scope": "production", "build_id": "build-7",
                   "config_fingerprint": "cfg-7", "content_hash": "context-hash",
                   "source_files": {"src/App.java": checksum}, "worker": {"distribution": []}}
        graph = KnowledgeGraph(3, ".", "now", [Node("app", "class", "App", "src/App.java", line=1,
                          scope="production", role="executable_code", origin="handwritten")], [],
                               {"src/App.java": checksum}, [context], [], [], [], [], [])
        save_graph(graph, root, generate_docs=False)
        return directory, root

    def test_explicit_fixture_producer_emits_redacted_facts_and_fingerprints(self):
        holder, root = self._root()
        try:
            code = ("import json; print(json.dumps({'facts': ["
                    "{'kind':'bean','name':'app','password':'do-not-leak'},"
                    "{'kind':'mapping','url':'https://x.test/a?token=secret'}]}))")
            manifest = produce_manifest(root, [sys.executable, "-c", code], context_id="ctx",
                                       runtime_id="run-7", build_id="build-7", config_fingerprint="cfg-7",
                                       service_id="fixture-app", service_version="1.2.3",
                                       output=Path("trace.json"))
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["service_id"], "fixture-app")
            self.assertEqual(manifest["source_identity"]["context_fingerprint"], "context-hash")
            self.assertEqual(manifest["facts"][0]["password"], "[REDACTED]")
            self.assertNotIn("secret", json.dumps(manifest))
            self.assertTrue((root / "trace.json").is_file())
        finally:
            holder.cleanup()

    def test_failed_or_ambiguous_producer_keeps_existing_artifact(self):
        holder, root = self._root()
        try:
            artifact = root / "trace.json"
            artifact.write_text("old\n", encoding="utf-8")
            with self.assertRaises(AnalysisError):
                produce_manifest(root, [sys.executable, "-c", "print('not json')"], context_id="ctx",
                                 runtime_id="run-7", build_id="build-7", config_fingerprint="cfg-7",
                                 service_id="fixture-app", service_version="1.2.3", output=artifact)
            self.assertEqual(artifact.read_text(encoding="utf-8"), "old\n")
            code = "import json; print(json.dumps({'facts':[{'kind':'unknown'}]}))"
            with self.assertRaises(AnalysisError):
                produce_manifest(root, [sys.executable, "-c", code], context_id="ctx",
                                 runtime_id="run-7", build_id="build-7", config_fingerprint="cfg-7",
                                 service_id="fixture-app", service_version="1.2.3", output=artifact)
            self.assertEqual(artifact.read_text(encoding="utf-8"), "old\n")
        finally:
            holder.cleanup()


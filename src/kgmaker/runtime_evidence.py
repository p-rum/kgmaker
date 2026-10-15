"""Import-only runtime observations with build/config scope binding.

The importer consumes a sanitized export produced elsewhere. It never starts
the application, enables an actuator endpoint, or treats an absent observation
as a negative fact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest, file_hash, safe_path
from .model import Edge, KnowledgeGraph

SCHEMA_VERSION = 1


def _check_hashes(root: Path, context: dict[str, Any], manifest: dict[str, Any]) -> None:
    expected = context.get("source_files", {})
    supplied = manifest.get("source_hashes", expected)
    if not isinstance(supplied, dict) or supplied != expected:
        raise AnalysisError("STALE_RUNTIME: runtime source snapshot does not match compiler context", 3)
    for path, checksum in expected.items():
        target = safe_path(root, path)
        if not target.is_file() or file_hash(target) != checksum:
            raise AnalysisError("STALE_RUNTIME: source changed: " + path, 3)
    worker = context.get("worker", {})
    expected_distribution = worker.get("distribution", []) if isinstance(worker, dict) else []
    supplied_distribution = manifest.get("worker_distribution", expected_distribution)
    if supplied_distribution != expected_distribution:
        raise AnalysisError("STALE_RUNTIME: worker distribution does not match compiler context", 3)
    for item in expected_distribution:
        path = Path(item["path"])
        if not path.is_file() or file_hash(path) != item["sha256"]:
            raise AnalysisError("STALE_RUNTIME: worker distribution changed", 3)


def validate_manifest(graph: KnowledgeGraph, root: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise AnalysisError("RuntimeManifest schema_version must be 1")
    for key in ("runtime_id", "context_id", "build_id", "config_fingerprint"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise AnalysisError("RuntimeManifest requires " + key)
    observations = manifest.get("observations")
    if not isinstance(observations, list) or len(observations) > 50_000:
        raise AnalysisError("Runtime observations must be a bounded array")
    contexts = [context for context in graph.contexts if context.get("id") == manifest["context_id"]]
    if len(contexts) != 1:
        raise AnalysisError("Runtime context is absent from the stored compiler graph", 3)
    context = contexts[0]
    if context.get("build_id") != manifest["build_id"]:
        raise AnalysisError("STALE_RUNTIME: build identity differs from compiler context", 3)
    if manifest.get("config_fingerprint") != context.get("config_fingerprint", manifest["config_fingerprint"]):
        raise AnalysisError("STALE_RUNTIME: configuration fingerprint differs", 3)
    _check_hashes(root, context, manifest)
    ids = {node.id for node in graph.nodes}
    for index, item in enumerate(observations):
        if not isinstance(item, dict) or set(item) - {"caller", "target", "kind", "scenario", "async", "source"}:
            raise AnalysisError(f"Runtime observations[{index}] has unknown fields")
        if not isinstance(item.get("caller"), str) or not isinstance(item.get("target"), str):
            raise AnalysisError(f"Runtime observations[{index}] requires caller and target IDs")
        if item["caller"] not in ids or item["target"] not in ids:
            raise AnalysisError(f"Runtime observations[{index}] references an unknown graph symbol")
        if item.get("kind", "call") not in {"call", "dispatch", "framework"}:
            raise AnalysisError(f"Runtime observations[{index}] has unsupported kind")
        if not isinstance(item.get("scenario", ""), str) or len(item.get("scenario", "")) > 200:
            raise AnalysisError(f"Runtime observations[{index}].scenario is invalid")
    return manifest, context


def import_manifest(root: Path, manifest: dict[str, Any], *, graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    root = root.resolve()
    if graph is None:
        from .store import load_graph
        graph = load_graph(root)
    if graph is None or graph.schema_version != 3:
        raise AnalysisError("Runtime import requires a stored schema 3 compiler graph")
    manifest, context = validate_manifest(graph, root, manifest)
    evidence = {item["id"]: item for item in graph.evidence}
    edges = {(edge.source, edge.target, edge.kind): edge for edge in graph.edges}
    for item in manifest["observations"]:
        source, target = item["caller"], item["target"]
        relation = "observed_dispatch_to" if item.get("kind", "call") in {"dispatch", "call"} else "runtime_framework_observation"
        record = {"kind": "RUNTIME_OBSERVED", "source": source, "target": target, "relation": relation,
                  "runtime_id": manifest["runtime_id"], "context_id": manifest["context_id"],
                  "build_id": manifest["build_id"], "scenario": item.get("scenario", ""),
                  "async": bool(item.get("async", False)), "observation_source": item.get("source")}
        evidence_id = "evidence:" + digest(record)
        evidence.setdefault(evidence_id, {"id": evidence_id, **record})
        edges[(source, target, relation)] = Edge(
            source, target, relation,
            "Observed in supplied runtime export; scope is limited to this runtime/configuration.",
            evidence_kind="RUNTIME_OBSERVED", context_ids=(manifest["context_id"],), evidence_ids=(evidence_id,))
    from dataclasses import replace
    updated = replace(graph,
        edges=sorted(edges.values(), key=lambda edge: (edge.source, edge.kind, edge.target)),
        evidence=sorted(evidence.values(), key=lambda item: item["id"]),
        diagnostics=graph.diagnostics + [{"code": "RUNTIME_IMPORT_SCOPED", "runtime_id": manifest["runtime_id"],
                                          "observations": len(manifest["observations"]), "context_id": context["id"]}])
    from .store import save_graph
    save_graph(updated, root)
    return {"status": "COMPLETE", "mode": "RUNTIME_IMPORT", "runtime_id": manifest["runtime_id"],
            "context_id": context["id"], "observations_imported": len(manifest["observations"]),
            "limitations": ["Observed calls are scoped to the supplied run; absent calls prove nothing.",
                            "Runtime observations do not establish data availability or deployment state."]}


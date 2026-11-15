"""Explicit bounded runtime capture and offline, scope-bound observation import."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest, file_hash, safe_path
from .model import Edge, KnowledgeGraph

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
MAX_FACTS = 50_000
MAX_OUTPUT = 8 * 1024 * 1024
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,199}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
STATUSES = {"COMPLETE", "PARTIAL", "UNKNOWN"}
DIAGNOSTICS = {"INSTRUMENTED_SCOPE_ONLY", "NO_FACTS", "CAPTURE_INCOMPLETE", "CAPTURE_UNKNOWN", "FACT_LIMIT"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
_FACT_FIELDS = {
    "call": {"kind", "caller", "target", "outcome"},
    "bean": {"kind", "factory", "bean_type", "outcome"},
    "condition": {"kind", "owner", "predicate", "matched"},
    "mapping": {"kind", "owner", "handler", "method", "route_sha256"},
}


def _label(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _LABEL.fullmatch(value):
        raise AnalysisError("Runtime requires a nonempty bounded non-secret identifier: " + field)


def _context_for(graph: KnowledgeGraph, context_id: str) -> dict[str, Any]:
    contexts = [item for item in graph.contexts if item.get("id") == context_id]
    if len(contexts) != 1:
        raise AnalysisError("Runtime context is absent from the stored compiler graph", 3)
    context = contexts[0]
    if context.get("freshness") == "STALE":
        raise AnalysisError("STALE_RUNTIME: compiler context is stale", 3)
    return context


def _validate_capture(graph: KnowledgeGraph, context: dict, capture: dict) -> None:
    """Closed schema: no arbitrary strings, diagnostic text, URLs or payloads."""
    if set(capture) != {"facts", "status", "diagnostics"}:
        raise AnalysisError("Runtime capture requires only facts, status and diagnostics")
    if not isinstance(capture["status"], str) or capture["status"] not in STATUSES:
        raise AnalysisError("Runtime capture requires status COMPLETE/PARTIAL/UNKNOWN")
    diagnostics = capture["diagnostics"]
    if (not isinstance(diagnostics, list) or len(diagnostics) > len(DIAGNOSTICS)
            or any(not isinstance(code, str) or code not in DIAGNOSTICS for code in diagnostics)):
        raise AnalysisError("Runtime diagnostics must contain supported codes only")
    facts = capture["facts"]
    if not isinstance(facts, list) or len(facts) > MAX_FACTS:
        raise AnalysisError("Runtime facts must be a bounded array")
    if capture["status"] == "COMPLETE" and (not facts or diagnostics):
        raise AnalysisError("Runtime COMPLETE requires facts and no incomplete-scope diagnostics")
    if capture["status"] != "COMPLETE" and not diagnostics:
        raise AnalysisError("Runtime PARTIAL/UNKNOWN requires a diagnostic code")
    nodes = {n.id: n for n in graph.nodes}
    symbols = {s["id"]: s for s in graph.symbols if s.get("context_id") == context["id"]}

    def symbol(value, kinds):
        # Node existence alone does not prove membership in the selected compiler context.
        if (not isinstance(value, str) or value not in symbols or value not in nodes
                or symbols[value].get("kind") not in kinds
                or nodes[value].path not in context["source_files"]):
            raise AnalysisError("Runtime fact references an unknown or out-of-context symbol")

    for index, fact in enumerate(facts):
        kind = fact.get("kind") if isinstance(fact, dict) else None
        if not isinstance(kind, str) or kind not in _FACT_FIELDS or set(fact) != _FACT_FIELDS[kind]:
            raise AnalysisError(f"Runtime facts[{index}] has missing or unsupported fields")
        methods = {"method", "function", "constructor"}
        if kind == "call":
            symbol(fact["caller"], methods)
            symbol(fact["target"], methods)
            if fact["outcome"] not in ("RETURNED", "THREW"):
                raise AnalysisError("Runtime call outcome is invalid")
        elif kind == "bean":
            symbol(fact["factory"], methods)
            symbol(fact["bean_type"], {"class", "interface", "object"})
            if fact["outcome"] not in ("CREATED", "NULL", "THREW"):
                raise AnalysisError("Runtime bean outcome is invalid")
        elif kind == "condition":
            symbol(fact["owner"], methods | {"class"})
            symbol(fact["predicate"], methods)
            if type(fact["matched"]) is not bool:
                raise AnalysisError("Runtime condition matched must be boolean")
        else:
            symbol(fact["owner"], methods | {"class"})
            symbol(fact["handler"], methods)
            if (not isinstance(fact["method"], str) or fact["method"] not in METHODS
                    or not isinstance(fact["route_sha256"], str)
                    or not _SHA256.fullmatch(fact["route_sha256"])):
                raise AnalysisError("Runtime mapping requires HTTP method and route SHA-256")


def _output_path(root: Path, output: Path | None, context: dict) -> Path | None:
    if output is None:
        return None
    if not isinstance(output, Path):
        raise AnalysisError("Runtime output must be a path")
    try:
        relative = output.relative_to(root) if output.is_absolute() else output
    except ValueError:
        raise AnalysisError("Runtime output must stay inside the project root") from None
    target = safe_path(root, relative.as_posix())
    if (relative.parts[:2] != (".kgmaker", "runtime")
            or target.suffix != ".json" or relative.as_posix() in context["source_files"]):
        raise AnalysisError("Runtime output must be a separate JSON artifact under .kgmaker/runtime")
    protected = [Path(i["path"]).resolve() for i in context.get("worker", {}).get("distribution", [])]
    protected += [Path(i["path"]).resolve() for i in context.get("classpath", []) + context.get("bytecode_artifacts", [])]
    if any(target == path or (path.is_dir() and target.is_relative_to(path)) for path in protected):
        raise AnalysisError("Runtime output overlaps captured inputs")
    if target.exists() and (not target.is_file() or not os.access(target, os.W_OK)):
        raise AnalysisError("Runtime output is not a writable file")
    parent = target.parent
    while not parent.exists():
        parent = parent.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        raise AnalysisError("Runtime output parent is not writable")
    return target


def _run_capture(root: Path, command: list[str], timeout: float, cancel_file: Path | None) -> dict:
    # Reuse the bounded worker pipe reader and process-group cleanup. Runtime
    # capture has a separate closed protocol and never publishes child stderr.
    from .worker_protocol import _exchange, _terminate, WorkerError
    process = None
    aborted = False

    def abort():
        nonlocal aborted
        if process is not None and not aborted:
            aborted = True
            _terminate(process)

    try:
        process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True,
                                   env={**os.environ, "KGMAKER_RUNTIME_TRACE": "1"})
        output, _, code = _exchange(process, b"", deadline=time.monotonic() + timeout,
            cancel_file=cancel_file, max_response=MAX_OUTPUT, abort=abort)
        if code:
            raise AnalysisError("RUNTIME_PRODUCER_FAILED: no artifact was published", 3)
    except WorkerError as exc:
        raise AnalysisError("RUNTIME_PRODUCER_" + exc.status + ": no artifact was published", 3) from None
    except OSError:
        raise AnalysisError("RUNTIME_PRODUCER_UNAVAILABLE: no artifact was published", 3) from None
    finally:
        # Also remove descendants left behind by an otherwise successful leader.
        abort()
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def finite(value):
        raise ValueError("nonfinite number")

    try:
        raw = json.loads(output, object_pairs_hook=unique, parse_constant=finite)
    except (ValueError, UnicodeError, RecursionError):
        raise AnalysisError("Runtime producer stdout must be one bounded JSON capture", 3) from None
    if not isinstance(raw, dict):
        raise AnalysisError("Runtime producer stdout must be a capture object", 3)
    return raw


def produce_manifest(root: Path, command: list[str], *, context_id: str, runtime_id: str,
                     build_id: str, config_fingerprint: str, service_id: str,
                     service_version: str, timeout: float = 120,
                     output: Path | None = None, cancel_file: Path | None = None) -> dict[str, Any]:
    """Explicit POSIX execution; preflight, bounded capture, recheck, atomic publish."""
    if os.name != "posix":
        raise AnalysisError("Runtime producer process cleanup is supported on POSIX only", 3)
    if (not isinstance(command, list) or not command
            or any(not isinstance(x, str) or not x or "\0" in x for x in command)):
        raise AnalysisError("Runtime producer command must be a non-empty argv array")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 900:
        raise AnalysisError("Runtime producer timeout is outside the bounded range")
    root = root.resolve()
    if cancel_file is not None:
        if not isinstance(cancel_file, Path):
            raise AnalysisError("Runtime cancel file must be a path")
        cancel_file = cancel_file if cancel_file.is_absolute() else root / cancel_file
        if cancel_file.exists():
            raise AnalysisError("RUNTIME_PRODUCER_CANCELLED: cancelled before launch", 3)
    from .store import load_graph
    graph = load_graph(root)
    if graph is None or graph.schema_version != 3:
        raise AnalysisError("Runtime producer requires a stored schema 3 compiler graph", 3)
    context = _context_for(graph, context_id)
    manifest = {
        "schema_version": 2, "runtime_id": runtime_id, "context_id": context_id,
        "build_id": build_id, "config_fingerprint": config_fingerprint,
        "service_id": service_id, "service_version": service_version,
        "source_identity": {"context_fingerprint": digest(context),
                            "source_manifest_fingerprint": digest(context.get("source_files"))},
        "source_hashes": context.get("source_files"),
        "worker_distribution": context.get("worker", {}).get("distribution", []),
        "facts": [], "observations": [], "status": "UNKNOWN", "diagnostics": ["CAPTURE_UNKNOWN"],
        "producer": {"command_fingerprint": digest(command), "opt_in": True},
    }
    validate_manifest(graph, root, manifest)
    target = _output_path(root, output, context)
    before = digest(graph.to_dict())
    raw = _run_capture(root, command, timeout, cancel_file)
    _validate_capture(graph, context, raw)
    manifest.update(raw)
    current = load_graph(root)
    if current is None or digest(current.to_dict()) != before:
        raise AnalysisError("STALE_RUNTIME: stored compiler graph changed during capture", 3)
    validate_manifest(current, root, manifest)
    _output_path(root, output, context)
    if cancel_file is not None and cancel_file.exists():
        raise AnalysisError("RUNTIME_PRODUCER_CANCELLED: no artifact was published", 3)
    if target is not None:
        from .analysis_model import atomic_write
        atomic_write(target, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return manifest


def _check_hashes(root: Path, context: dict[str, Any], manifest: dict[str, Any]) -> None:
    expected = context.get("source_files", {})
    supplied = manifest.get("source_hashes", expected)
    if not isinstance(supplied, dict) or supplied != expected:
        raise AnalysisError("STALE_RUNTIME: runtime source snapshot does not match compiler context", 3)
    for path, checksum in expected.items():
        target = safe_path(root, path)
        if not target.is_file() or file_hash(target) != checksum:
            raise AnalysisError("STALE_RUNTIME: source changed", 3)
    worker = context.get("worker", {})
    expected_distribution = worker.get("distribution", []) if isinstance(worker, dict) else []
    if manifest.get("worker_distribution", expected_distribution) != expected_distribution:
        raise AnalysisError("STALE_RUNTIME: worker distribution does not match compiler context", 3)
    for item in expected_distribution:
        path = Path(item["path"])
        if not path.is_file() or file_hash(path) != item["sha256"]:
            raise AnalysisError("STALE_RUNTIME: worker distribution changed", 3)


def validate_manifest(graph: KnowledgeGraph, root: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS):
        raise AnalysisError("RuntimeManifest schema_version must be 1 or 2")
    for key in ("runtime_id", "context_id", "build_id", "config_fingerprint"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise AnalysisError("RuntimeManifest requires " + key)
    context = _context_for(graph, manifest["context_id"])
    if context.get("build_id") != manifest["build_id"]:
        raise AnalysisError("STALE_RUNTIME: build identity differs from compiler context", 3)
    if manifest["config_fingerprint"] != context.get("config_fingerprint", manifest["config_fingerprint"]):
        raise AnalysisError("STALE_RUNTIME: configuration fingerprint differs", 3)
    _check_hashes(root, context, manifest)
    v2 = manifest["schema_version"] == 2
    if v2:
        fields = {"schema_version", "runtime_id", "context_id", "build_id", "config_fingerprint", "service_id",
                  "service_version", "source_identity", "source_hashes", "worker_distribution", "facts",
                  "observations", "status", "diagnostics", "producer"}
        if set(manifest) != fields:
            raise AnalysisError("RuntimeManifest v2 has missing or unsupported fields")
        for key in ("runtime_id", "context_id", "build_id", "config_fingerprint", "service_id", "service_version"):
            _label(manifest[key], key)
        if not context.get("source_files") or not context.get("config_fingerprint"):
            raise AnalysisError("RuntimeManifest v2 requires captured source/config/context identity", 3)
        if manifest["source_identity"] != {"context_fingerprint": digest(context),
                                          "source_manifest_fingerprint": digest(context["source_files"])}:
            raise AnalysisError("STALE_RUNTIME: source identity differs from compiler context", 3)
        producer = manifest["producer"]
        if (not isinstance(producer, dict) or set(producer) != {"command_fingerprint", "opt_in"}
                or producer["opt_in"] is not True or not isinstance(producer["command_fingerprint"], str)
                or not _SHA256.fullmatch(producer["command_fingerprint"])):
            raise AnalysisError("RuntimeManifest v2 requires producer identity and explicit opt-in")
        from .graph_provider import validate_context_snapshot
        validate_context_snapshot(root, context)
        _validate_capture(graph, context, {key: manifest[key] for key in ("facts", "status", "diagnostics")})
    observations = manifest.get("observations")
    if not isinstance(observations, list) or len(observations) > MAX_FACTS:
        raise AnalysisError("Runtime observations must be a bounded array")
    if v2 and manifest["status"] == "UNKNOWN" and observations:
        raise AnalysisError("Runtime UNKNOWN cannot establish observed call evidence")
    ids = {node.id for node in graph.nodes}
    for index, item in enumerate(observations):
        allowed = {"caller", "target", "kind"} if v2 else {"caller", "target", "kind", "scenario", "async", "source"}
        if not isinstance(item, dict) or set(item) - allowed:
            raise AnalysisError(f"Runtime observations[{index}] has unknown fields")
        if not isinstance(item.get("caller"), str) or not isinstance(item.get("target"), str):
            raise AnalysisError(f"Runtime observations[{index}] requires caller and target IDs")
        if item["caller"] not in ids or item["target"] not in ids:
            raise AnalysisError(f"Runtime observations[{index}] references an unknown graph symbol")
        if item.get("kind", "call") not in ("call", "dispatch", "framework"):
            raise AnalysisError(f"Runtime observations[{index}] has unsupported kind")
        if not isinstance(item.get("scenario", ""), str) or len(item.get("scenario", "")) > 200:
            raise AnalysisError(f"Runtime observations[{index}].scenario is invalid")
        if v2:
            selected = {s["id"] for s in graph.symbols if s.get("context_id") == context["id"]}
            if item["caller"] not in selected or item["target"] not in selected:
                raise AnalysisError("Runtime observation references an out-of-context symbol")
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
    return {"status": manifest.get("status", "COMPLETE"), "mode": "RUNTIME_IMPORT", "runtime_id": manifest["runtime_id"],
            "context_id": context["id"], "observations_imported": len(manifest["observations"]),
            "limitations": ["Observed calls are scoped to the supplied run; absent calls prove nothing.",
                            "Runtime observations do not establish data availability or deployment state."]}


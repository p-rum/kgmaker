"""Explicit bounded runtime capture and offline, scope-bound observation import."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analysis_model import AnalysisError, digest, file_hash, safe_path
from .model import Edge, KnowledgeGraph
from . import runtime_value

SCHEMA_VERSION = 2
INTERFACE_DISPATCH_VERSION = 3
VALUE_PRESENCE_VERSION = 4
SUPPORTED_SCHEMA_VERSIONS = {1, SCHEMA_VERSION, INTERFACE_DISPATCH_VERSION, VALUE_PRESENCE_VERSION}
MAX_FACTS = 50_000
MAX_OUTPUT = 8 * 1024 * 1024
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,199}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
STATUSES = {"COMPLETE", "PARTIAL", "UNKNOWN"}
DIAGNOSTICS = {"INSTRUMENTED_SCOPE_ONLY", "NO_FACTS", "CAPTURE_INCOMPLETE", "CAPTURE_UNKNOWN", "FACT_LIMIT"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
_CALLABLE_KINDS = ("method", "function", "constructor")
_FACT_FIELDS = {
    "call": {"kind", "caller", "target", "outcome"},
    "bean": {"kind", "factory", "bean_type", "outcome"},
    "condition": {"kind", "owner", "predicate", "matched"},
    "mapping": {"kind", "owner", "handler", "method", "route_sha256"},
}
_INTERFACE_DISPATCH_FIELDS = {
    "kind", "caller_owner", "caller_name", "caller_descriptor", "source_line",
    "receiver_type", "target_owner", "target_name", "target_descriptor",
}
_CAPTURE_FIELDS = {"facts", "status", "diagnostics"}


def _label(value: Any, field: str) -> None:
    if type(value) is not str or not _LABEL.fullmatch(value):
        raise AnalysisError("Runtime requires a nonempty bounded non-secret identifier: " + field)


def _context_for(graph: KnowledgeGraph, context_id: str) -> dict[str, Any]:
    contexts = [item for item in graph.contexts if item.get("id") == context_id]
    if len(contexts) != 1:
        raise AnalysisError("Runtime context is absent from the stored compiler graph", 3)
    context = contexts[0]
    if context.get("freshness") == "STALE":
        raise AnalysisError("STALE_RUNTIME: compiler context is stale", 3)
    return context


def _jvm_signature(symbol: dict) -> tuple:
    return symbol.get("owner"), symbol.get("name"), symbol.get("descriptor")


class _InterfaceDispatch:
    def __init__(self, graph: KnowledgeGraph, context: dict, symbols: dict, nodes: dict):
        if (context.get("language") != "jvm" or context.get("freshness") != "EXECUTION_BOUND"
                or not context.get("bytecode_artifacts")):
            raise AnalysisError("RUNTIME_DISPATCH_CONTEXT: expected execution-bound JVM bytecode", 3)
        self.context = context
        self.symbols = symbols
        self.classes = defaultdict(list)
        self.sites = defaultdict(list)
        self.unlocated_callers = set()
        self.candidates = {}
        for item in symbols.values():
            if item.get("kind") == "class" and item["id"] in nodes and self._java_source(item):
                self.classes[item.get("owner")].append(item)
        for site in graph.call_sites:
            caller = symbols.get(site.get("caller"), {})
            if (site.get("context_id") == context["id"] and site.get("representation") == "BYTECODE"
                    and caller.get("kind") == "bytecode_method"):
                signature = _jvm_signature(caller)
                line = site.get("source_line")
                if (type(line) is not int or line <= 0
                        or site.get("artifact_hashes") != context["bytecode_artifacts"]):
                    self.unlocated_callers.add(signature)
                else:
                    self.sites[(*signature, line)].append(site)

    def _java_source(self, symbol: dict) -> bool:
        path = symbol.get("path")
        return isinstance(path, str) and path.endswith(".java") and path in self.context["source_files"]

    def resolve(self, fact: dict) -> dict:
        line = fact["source_line"]
        if (type(line) is not int or line <= 0 or any(type(fact[field]) is not str or not 0 < len(fact[field]) <= 2048
                for field in _INTERFACE_DISPATCH_FIELDS - {"kind", "source_line"})):
            raise AnalysisError("RUNTIME_DISPATCH_FACT: invalid frame or receiver identity", 3)
        caller = fact["caller_owner"], fact["caller_name"], fact["caller_descriptor"]
        if caller in self.unlocated_callers:
            raise AnalysisError("RUNTIME_DISPATCH_SITE: selected caller has an instruction without a bound source line", 3)
        sites = self.sites.get((*caller, line), ())
        if len(sites) != 1:
            raise AnalysisError("RUNTIME_DISPATCH_SITE: expected one selected interface instruction at the frame line", 3)
        site, = sites
        physical = self.symbols[site["caller"]]
        mapped_callers = [self.symbols.get(identity, {}) for identity in physical.get("source_mapping_ids", ())]
        if (site.get("invocation_kind") != "INTERFACE" or site.get("evidence_kind") != "SYMBOL_RESOLVED"
                or physical.get("synthetic") or physical.get("bridge")
                or len(mapped_callers) != 1
                or mapped_callers[0].get("kind") != "method" or not self._java_source(mapped_callers[0])
                or _jvm_signature(mapped_callers[0]) != caller):
            raise AnalysisError("RUNTIME_DISPATCH_SITE: missing selected Java caller proof", 3)
        receiver = self.classes.get(fact["receiver_type"], ())
        if len(receiver) != 1 or "abstract" in receiver[0].get("modifiers", ()):
            raise AnalysisError("RUNTIME_DISPATCH_RECEIVER: expected one selected concrete Java class", 3)
        if fact["receiver_type"] != fact["target_owner"]:
            raise AnalysisError("RUNTIME_DISPATCH_TARGET: expected a direct override on the receiver", 3)
        if site["id"] not in self.candidates:
            candidates = defaultdict(list)
            for identity in site.get("dispatch_candidates", ()):
                item = self.symbols.get(identity, {})
                if (item.get("kind") == "method" and self._java_source(item) and item.get("jvm_static") is False
                        and "abstract" not in item.get("modifiers", ())):
                    candidates[_jvm_signature(item)].append(identity)
            self.candidates[site["id"]] = candidates
        target = fact["target_owner"], fact["target_name"], fact["target_descriptor"]
        candidates = self.candidates[site["id"]].get(target, ())
        if len(candidates) != 1:
            raise AnalysisError("RUNTIME_DISPATCH_TARGET: no unique selected override at the interface instruction", 3)
        return {"kind": "dispatch", "caller": mapped_callers[0]["id"], "target": candidates[0],
                "call_site": site["id"], "receiver_type": receiver[0]["id"]}


def _validate_capture(graph: KnowledgeGraph, context: dict, capture: dict, *, interface_dispatch=False,
                      value_presence=False) -> list[dict]:
    """Closed schema: no arbitrary strings, diagnostic text, URLs or payloads."""
    if set(capture) != _CAPTURE_FIELDS:
        raise AnalysisError("Runtime capture requires only facts, status and diagnostics")
    if type(capture["status"]) is not str or capture["status"] not in STATUSES:
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
    observations = []
    if value_presence:
        kinds = [fact.get("kind") if isinstance(fact, dict) else None for fact in facts]
        if (kinds.count(runtime_value.FACT) != 1 or any(kind not in (runtime_value.FACT, "call") for kind in kinds)
                or capture["status"] != "PARTIAL" or diagnostics != ["INSTRUMENTED_SCOPE_ONLY"]):
            raise AnalysisError("RUNTIME_VALUE_FACT: expected one complete presence sample within the instrumented scope", 3)
        observations.append(runtime_value.resolve_capture(graph, context, facts[kinds.index(runtime_value.FACT)]))
        if len(facts) == 1:
            return observations
    nodes = {n.id: n for n in graph.nodes}
    symbols = {s["id"]: s for s in graph.symbols if s.get("context_id") == context["id"]}
    dispatch = None

    def symbol(value, kinds):
        # Node existence alone does not prove membership in the selected compiler context.
        if (not isinstance(value, str) or value not in symbols or value not in nodes
                or symbols[value].get("kind") not in kinds
                or nodes[value].path not in context["source_files"]):
            raise AnalysisError("Runtime fact references an unknown or out-of-context symbol")

    for index, fact in enumerate(facts):
        kind = fact.get("kind") if isinstance(fact, dict) else None
        if value_presence and kind == runtime_value.FACT:
            continue  # Only the presence sample becomes a typed observation.
        if interface_dispatch and kind == "interface_dispatch":
            fact = dict(fact)
            if (set(fact) != _INTERFACE_DISPATCH_FIELDS or type(fact["kind"]) is not str
                    or any(type(key) is not str for key in fact)):
                raise AnalysisError("RUNTIME_DISPATCH_FACT: missing or unsupported fields", 3)
            if capture["status"] == "UNKNOWN":
                raise AnalysisError("Runtime UNKNOWN cannot establish observed call evidence")
            if dispatch is None:
                dispatch = _InterfaceDispatch(graph, context, symbols, nodes)
            observations.append(dispatch.resolve(fact))
            continue
        if not isinstance(kind, str) or kind not in _FACT_FIELDS or set(fact) != _FACT_FIELDS[kind]:
            raise AnalysisError(f"Runtime facts[{index}] has missing or unsupported fields")
        if kind == "call":
            symbol(fact["caller"], _CALLABLE_KINDS)
            symbol(fact["target"], _CALLABLE_KINDS)
            if fact["outcome"] not in ("RETURNED", "THREW"):
                raise AnalysisError("Runtime call outcome is invalid")
        elif kind == "bean":
            symbol(fact["factory"], _CALLABLE_KINDS)
            symbol(fact["bean_type"], {"class", "interface", "object"})
            if fact["outcome"] not in ("CREATED", "NULL", "THREW"):
                raise AnalysisError("Runtime bean outcome is invalid")
        elif kind == "condition":
            symbol(fact["owner"], _CALLABLE_KINDS + ("class",))
            symbol(fact["predicate"], _CALLABLE_KINDS)
            if type(fact["matched"]) is not bool:
                raise AnalysisError("Runtime condition matched must be boolean")
        else:
            symbol(fact["owner"], _CALLABLE_KINDS + ("class",))
            symbol(fact["handler"], _CALLABLE_KINDS)
            if (not isinstance(fact["method"], str) or fact["method"] not in METHODS
                    or not isinstance(fact["route_sha256"], str)
                    or not _SHA256.fullmatch(fact["route_sha256"])):
                raise AnalysisError("Runtime mapping requires HTTP method and route SHA-256")
    return observations


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
        "schema_version": SCHEMA_VERSION, "runtime_id": runtime_id, "context_id": context_id,
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
    run_started_at = datetime.now(timezone.utc).isoformat()
    raw = _run_capture(root, command, timeout, cancel_file)
    if set(raw) != _CAPTURE_FIELDS:
        raise AnalysisError("Runtime capture requires only facts, status and diagnostics")
    manifest.update(raw)
    facts = raw["facts"]
    if isinstance(facts, list) and len(facts) <= MAX_FACTS:
        if any(isinstance(fact, dict) and fact.get("kind") == runtime_value.FACT for fact in facts):
            manifest.update(schema_version=VALUE_PRESENCE_VERSION, run_started_at=run_started_at)
        elif any(isinstance(fact, dict) and fact.get("kind") == "interface_dispatch" for fact in facts):
            manifest["schema_version"] = INTERFACE_DISPATCH_VERSION
    current = load_graph(root)
    if current is None or digest(current.to_dict()) != before:
        raise AnalysisError("STALE_RUNTIME: stored compiler graph changed during capture", 3)
    validate_manifest(current, root, manifest)
    _output_path(root, output, context)
    if cancel_file is not None and cancel_file.exists():
        raise AnalysisError("RUNTIME_PRODUCER_CANCELLED: no artifact was published", 3)
    if target is not None:
        from .analysis_model import atomic_write
        rendered = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

        def recheck_value_output():
            from .graph_provider import validate_context_snapshot
            latest = load_graph(root)
            if latest is None or digest(latest.to_dict()) != before:
                raise AnalysisError("STALE_RUNTIME: stored compiler graph changed before capture publication", 3)
            _check_hashes(root, context)
            validate_context_snapshot(root, context)
            if _output_path(root, output, context) != target:
                raise AnalysisError("STALE_RUNTIME: capture output path changed before publication", 3)
            if cancel_file is not None and cancel_file.exists():
                raise AnalysisError("RUNTIME_PRODUCER_CANCELLED: no artifact was published", 3)

        if manifest["schema_version"] == VALUE_PRESENCE_VERSION:
            atomic_write(target, rendered, before_replace=recheck_value_output)
        else:
            atomic_write(target, rendered)
    return manifest


def _check_hashes(root: Path, context: dict[str, Any], manifest: dict[str, Any] | None = None) -> None:
    """Check captured files and bind supplied declarations during initial validation."""
    expected = context.get("source_files", {})
    if manifest is not None:
        supplied = manifest.get("source_hashes", expected)
        if not isinstance(supplied, dict) or supplied != expected:
            raise AnalysisError("STALE_RUNTIME: runtime source snapshot does not match compiler context", 3)
    for path, checksum in expected.items():
        target = safe_path(root, path)
        if not target.is_file() or file_hash(target) != checksum:
            raise AnalysisError("STALE_RUNTIME: source changed", 3)
    worker = context.get("worker", {})
    expected_distribution = worker.get("distribution", []) if isinstance(worker, dict) else []
    if manifest is not None and manifest.get("worker_distribution", expected_distribution) != expected_distribution:
        raise AnalysisError("STALE_RUNTIME: worker distribution does not match compiler context", 3)
    for item in expected_distribution:
        path = Path(item["path"])
        if not path.is_file() or file_hash(path) != item["sha256"]:
            raise AnalysisError("STALE_RUNTIME: worker distribution changed", 3)


def validate_manifest(graph: KnowledgeGraph, root: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(manifest, dict):
        raise AnalysisError("RuntimeManifest schema_version must be 1, 2, 3 or 4")
    # Bind the envelope before any preflight checks can read caller-owned values.
    manifest = dict(manifest)
    version = manifest.get("schema_version")
    if type(version) is not int or version not in SUPPORTED_SCHEMA_VERSIONS:
        raise AnalysisError("RuntimeManifest schema_version must be 1, 2, 3 or 4")
    bound = version >= SCHEMA_VERSION
    value_presence = version == VALUE_PRESENCE_VERSION
    for key in ("runtime_id", "context_id", "build_id", "config_fingerprint"):
        value = manifest.get(key)
        if not isinstance(value, str) or (bound and type(value) is not str) or not value:
            raise AnalysisError("RuntimeManifest requires " + key)
    context = _context_for(graph, manifest["context_id"])
    if context.get("build_id") != manifest["build_id"]:
        raise AnalysisError("STALE_RUNTIME: build identity differs from compiler context", 3)
    if manifest["config_fingerprint"] != context.get("config_fingerprint", manifest["config_fingerprint"]):
        raise AnalysisError("STALE_RUNTIME: configuration fingerprint differs", 3)
    _check_hashes(root, context, manifest)
    if bound:
        fields = {"schema_version", "runtime_id", "context_id", "build_id", "config_fingerprint", "service_id",
                  "service_version", "source_identity", "source_hashes", "worker_distribution", "facts",
                  "observations", "status", "diagnostics", "producer"}
        if value_presence:
            fields.add("run_started_at")
        if set(manifest) != fields or any(type(key) is not str for key in manifest):
            raise AnalysisError(f"RuntimeManifest v{version} has missing or unsupported fields")
        for key in ("runtime_id", "context_id", "build_id", "config_fingerprint", "service_id", "service_version"):
            _label(manifest[key], key)
        if not context.get("source_files") or not context.get("config_fingerprint"):
            raise AnalysisError(f"RuntimeManifest v{version} requires captured source/config/context identity", 3)
        if value_presence:
            runtime_value.run_start(manifest["run_started_at"])
        source_identity = {"context_fingerprint": digest(context),
                           "source_manifest_fingerprint": digest(context["source_files"])}
        if manifest["source_identity"] != source_identity:
            raise AnalysisError("STALE_RUNTIME: source identity differs from compiler context", 3)
        # Keep the verified identity independent of the caller's mapping.
        manifest["source_identity"] = source_identity
        producer = manifest["producer"]
        if (not isinstance(producer, dict) or set(producer) != {"command_fingerprint", "opt_in"}
                or producer["opt_in"] is not True or not isinstance(producer["command_fingerprint"], str)
                or not _SHA256.fullmatch(producer["command_fingerprint"])):
            raise AnalysisError(f"RuntimeManifest v{version} requires producer identity and explicit opt-in")
        from .graph_provider import validate_context_snapshot
        validate_context_snapshot(root, context)
        derived = _validate_capture(graph, context, {key: manifest[key] for key in _CAPTURE_FIELDS},
                                    interface_dispatch=version == INTERFACE_DISPATCH_VERSION, value_presence=value_presence)
    observations = manifest.get("observations")
    if not isinstance(observations, list) or len(observations) > MAX_FACTS:
        raise AnalysisError("Runtime observations must be a bounded array")
    if value_presence:
        if observations:
            raise AnalysisError("RuntimeManifest v4 requires a typed value sample and no supplied observations")
        manifest["observations"] = derived
        return manifest, context
    if version == INTERFACE_DISPATCH_VERSION:
        if observations or not derived:
            raise AnalysisError("RuntimeManifest v3 requires typed interface dispatch facts and no supplied observations")
        manifest["observations"] = derived
        return manifest, context
    unknown = bound and manifest["status"] == "UNKNOWN"
    ids = {node.id for node in graph.nodes}
    selected = {
        symbol["id"]: symbol.get("kind") for symbol in graph.symbols
        if symbol.get("context_id") == context["id"]
    } if bound else {}
    allowed = {"caller", "target", "kind"} if bound else {"caller", "target", "kind", "scenario", "async", "source"}
    admitted = []
    for index, observation in enumerate(observations):
        if unknown:
            raise AnalysisError("Runtime UNKNOWN cannot establish observed call evidence")
        if index >= MAX_FACTS:
            raise AnalysisError("Runtime observations must be a bounded array")
        if not isinstance(observation, dict):
            raise AnalysisError(f"Runtime observations[{index}] has unknown fields")
        item = dict(observation)
        if any((bound and type(key) is not str) or key not in allowed for key in item):
            raise AnalysisError(f"Runtime observations[{index}] has unknown fields")
        caller, target = item.get("caller"), item.get("target")
        if (not isinstance(caller, str) or not isinstance(target, str)
                or (bound and (type(caller) is not str or type(target) is not str))):
            raise AnalysisError(f"Runtime observations[{index}] requires caller and target IDs")
        if caller not in ids or target not in ids:
            raise AnalysisError(f"Runtime observations[{index}] references an unknown graph symbol")
        kind = item.get("kind", "call")
        if (bound and type(kind) is not str) or kind not in ("call", "dispatch", "framework"):
            raise AnalysisError(f"Runtime observations[{index}] has unsupported kind")
        if bound:
            if caller not in selected or target not in selected:
                raise AnalysisError("Runtime observation references an out-of-context symbol")
            if kind != "framework" and (selected[caller] not in _CALLABLE_KINDS
                                        or selected[target] not in _CALLABLE_KINDS):
                raise AnalysisError("Runtime call and dispatch observations require callable symbols")
        elif not isinstance(item.get("scenario", ""), str) or len(item.get("scenario", "")) > 200:
            raise AnalysisError(f"Runtime observations[{index}].scenario is invalid")
        admitted.append(item)
    manifest["observations"] = admitted
    return manifest, context


def import_manifest(root: Path, manifest: dict[str, Any], *, graph: KnowledgeGraph | None = None) -> dict[str, Any]:
    from .store import GraphPublicationConflict, graph_revision, load_graph, save_graph

    root = root.resolve()
    previous = graph_revision(root)
    if previous is not None or graph is None:
        stored = load_graph(root)
        if graph is not None and (stored is None or
                digest(graph.to_dict(include_cache=True)) != digest(stored.to_dict(include_cache=True))):
            raise GraphPublicationConflict("Explicit runtime graph does not match stored graph generation")
        graph = stored
    if graph is None or graph.schema_version != 3:
        raise AnalysisError("Runtime import requires a stored schema 3 compiler graph")
    manifest, context = validate_manifest(graph, root, manifest)
    evidence = {item["id"]: item for item in graph.evidence}
    edges = list(graph.edges)
    observed_edges = {(edge.source, edge.target, edge.kind, edge.context_ids): index
                      for index, edge in enumerate(edges) if edge.evidence_kind == "RUNTIME_OBSERVED"}
    context_ids = (context["id"],)
    imported = {}
    value_evidence_ids = []
    for item in manifest["observations"]:
        is_value = item.get("kind") == runtime_value.FACT
        source, target = item["source" if is_value else "caller"], item["target"]
        if is_value:
            relation = runtime_value.RELATION
        else:
            relation = "observed_dispatch_to" if item.get("kind", "call") in {"dispatch", "call"} else "runtime_framework_observation"
        record = {"kind": "RUNTIME_OBSERVED", "source": source, "target": target, "relation": relation,
                  "runtime_id": manifest["runtime_id"], "context_id": manifest["context_id"],
                  "build_id": manifest["build_id"]}
        if not is_value:
            record.update({"scenario": item.get("scenario", ""), "async": bool(item.get("async", False)),
                           "observation_source": item.get("source")})
        if manifest["schema_version"] >= SCHEMA_VERSION:
            record.update({key: manifest[key] for key in (
                "config_fingerprint", "service_id", "service_version", "source_identity",
            )})
        if manifest["schema_version"] == INTERFACE_DISPATCH_VERSION:
            record.update({key: item[key] for key in ("call_site", "receiver_type")})
        if is_value:
            record.update({key: item[key] for key in ("presence", "field_mapping_evidence_id", "hook_call_site")})
            record["run_started_at"] = manifest["run_started_at"]
        evidence_id = "evidence:" + digest(record)
        if is_value:
            same_run = ("runtime_id", "context_id", "service_id", "service_version", "field_mapping_evidence_id")
            if any(old.get("relation") == runtime_value.RELATION and old["id"] != evidence_id
                   and all(old.get(key) == record[key] for key in same_run) for old in evidence.values()):
                raise AnalysisError("RUNTIME_VALUE_AMBIGUOUS: run already has a different sample for this field transfer", 3)
            value_evidence_ids.append(evidence_id)
        evidence.setdefault(evidence_id, {"id": evidence_id, **record})
        imported.setdefault((source, target, relation), set()).add(evidence_id)
    for (source, target, relation), evidence_ids in imported.items():
        # Keep each edge in a single context so scoped views can retain its proof.
        key = (source, target, relation, context_ids)
        index = observed_edges.get(key)
        if index is not None:
            edge = edges[index]
            edges[index] = replace(edge, evidence_ids=tuple(sorted(evidence_ids.union(edge.evidence_ids))))
            continue
        edges.append(Edge(
            source, target, relation,
            "Observed in supplied runtime export; scope is limited to this runtime/configuration.",
            evidence_kind="RUNTIME_OBSERVED", context_ids=context_ids, evidence_ids=tuple(sorted(evidence_ids))))
    updated = replace(graph,
        edges=sorted(edges, key=lambda edge: (edge.source, edge.kind, edge.target, edge.context_ids)),
        evidence=sorted(evidence.values(), key=lambda item: item["id"]),
        diagnostics=graph.diagnostics + [{"code": "RUNTIME_IMPORT_SCOPED", "runtime_id": manifest["runtime_id"],
                                          "observations": len(manifest["observations"]), "context_id": context["id"]}])

    def revalidate_inputs():
        # The generation check serializes graph writers. Source and worker inputs
        # can still change while the store prepares and replaces individual outputs.
        _check_hashes(root, context)
        if manifest["schema_version"] >= SCHEMA_VERSION:
            from .graph_provider import validate_context_snapshot
            validate_context_snapshot(root, context)

    save_graph(updated, root, before_replace=revalidate_inputs, expected_revision=previous)
    return {"status": manifest.get("status", "COMPLETE"), "mode": "RUNTIME_IMPORT", "runtime_id": manifest["runtime_id"],
            "context_id": context["id"], "observations_imported": len(manifest["observations"]),
            "limitations": ["Observed calls are scoped to the supplied run; absent calls prove nothing.",
                            "Runtime observations do not establish data availability or deployment state."],
            **({"value_evidence_ids": value_evidence_ids} if value_evidence_ids else {})}


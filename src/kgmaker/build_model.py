"""Versioned content-bound build import; content integrity is not authenticity."""
from __future__ import annotations

import copy
import re
from pathlib import Path

from .analysis_model import AnalysisError, ID_PATTERN, digest, file_hash, safe_path, write_json
from .classification import SCOPES
from .inspection import artifact_hash

VERSION = "build-manifest-1"
STATUSES = {"SUCCESS", "FAILED", "PARTIAL", "TIMED_OUT", "CANCELLED", "TOOLCHAIN_UNAVAILABLE", "DEPENDENCY_UNAVAILABLE"}
HASH = re.compile(r"[0-9a-f]{64}\Z")


def validate_manifest(root: Path, manifest: dict) -> dict:
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise AnalysisError("BuildManifest schema_version must be 1")
    if not isinstance(manifest.get("build_id"), str) or not ID_PATTERN.fullmatch(manifest["build_id"]):
        raise AnalysisError("Invalid build ID")
    result = manifest.get("build_result")
    snapshot = manifest.get("snapshot")
    if not isinstance(result, dict) or result.get("status") not in STATUSES:
        raise AnalysisError("BuildManifest requires a truthful distinct build_result status")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("sources"), dict):
        raise AnalysisError("BuildManifest requires source content snapshot")
    if snapshot.get("content_hash") != digest(snapshot["sources"]):
        raise AnalysisError("Build snapshot fingerprint mismatch")
    for path, expected in snapshot["sources"].items():
        source = safe_path(root, path)
        if not isinstance(expected, str) or not HASH.fullmatch(expected) or not source.is_file() or file_hash(source) != expected:
            raise AnalysisError("STALE_SOURCE: " + path, 3)
    if not isinstance(manifest.get("contexts"), list):
        raise AnalysisError("BuildManifest contexts are missing")
    ids = set()
    for context in manifest["contexts"]:
        if not isinstance(context, dict) or not isinstance(context.get("id"), str) or context["id"] in ids:
            raise AnalysisError("Duplicate/invalid build context")
        ids.add(context["id"])
        if context.get("scope") not in SCOPES or not all(isinstance(context.get(k), str) and context[k] for k in ("module", "source_set", "repo_id")):
            raise AnalysisError("Build context requires repo/module/source-set/scope")
        if not isinstance(context.get("source_roots"), list) or not isinstance(context.get("source_files"), list):
            raise AnalysisError("Build source roots/files must be arrays")
        for path in context["source_roots"] + context["source_files"]:
            safe_path(root, path)
        if not isinstance(context.get("classpath"), list):
            raise AnalysisError("Build classpath must be an ordered array")
        for artifact in context["classpath"]:
            if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str) or not HASH.fullmatch(str(artifact.get("sha256", ""))):
                raise AnalysisError("Invalid classpath artifact/checksum")
            path = Path(artifact["path"])
            if not path.is_absolute():
                path = safe_path(root, artifact["path"])
            if path.is_symlink() or artifact_hash(path) != artifact["sha256"]:
                raise AnalysisError("STALE_ARTIFACT: " + artifact["path"], 3)
        if not isinstance(context.get("outputs", []), list) or any(not isinstance(o, dict) for o in context.get("outputs", [])):
            raise AnalysisError("Build outputs must be objects in an array")
        if context.get("outputs") and (not isinstance(result.get("execution_id"), str) or not result["execution_id"]):
            raise AnalysisError("Outputs require a nonempty build execution ID")
        for source in context["source_files"]:
            if source not in snapshot["sources"]:
                raise AnalysisError("Compiler input absent from captured snapshot: " + source)
        for artifact in context.get("outputs", []):
            if (result["status"] != "SUCCESS" or result.get("freshness") in {"MIXED_BUILD_INPUTS", "STALE_SOURCE"}) and artifact.get("freshness") == "EXECUTION_BOUND":
                raise AnalysisError("Failed/partial build cannot supply fresh bytecode")
            if artifact.get("execution_id") != result.get("execution_id") or artifact.get("snapshot_hash") != snapshot["content_hash"]:
                raise AnalysisError("Output is not bound to the captured build execution/snapshot")
            path = Path(artifact["path"])
            if not path.is_absolute():
                path = safe_path(root, artifact["path"])
            if artifact_hash(path) != artifact.get("sha256"):
                raise AnalysisError("STALE_OUTPUT: " + str(path), 3)
    if snapshot.get("inventory") == "ALL_BUILD_INPUTS_V1":
        from .build_runner import snapshot as inventory
        if inventory(root) != snapshot["sources"]:
            raise AnalysisError("STALE_SOURCE: complete build inventory changed", 3)
    elif any(o.get("freshness") == "EXECUTION_BOUND" for c in manifest["contexts"] for o in c.get("outputs", [])):
        raise AnalysisError("Fresh outputs require a complete build-input inventory")
    return copy.deepcopy(manifest)


def import_manifest(root: Path, manifest: dict) -> dict:
    validated = validate_manifest(root, manifest)
    # Never transform a supplied result into a host observation. Hash checks only
    # bind its contents; the exporter may be unauthenticated or mistaken.
    validated["mode"] = "BUILD_IMPORT"
    validated["origin_trust"] = "SUPPLIED_EXPORT_UNVERIFIED"
    validated["import_validation"] = {"version": VERSION, "content_integrity": "VERIFIED", "authenticity": "UNVERIFIED"}
    target = safe_path(root, ".kgmaker/builds/" + validated["build_id"] + "/manifest.json")
    write_json(target, validated)
    return {"status": "COMPLETE" if validated["build_result"]["status"] == "SUCCESS" and bool(validated["contexts"]) and not validated.get("diagnostics") and not any(c.get("diagnostics") for c in validated["contexts"]) else "PARTIAL",
            "build_id": validated["build_id"], "manifest_path": str(target), "mode": "BUILD_IMPORT",
            "origin_trust": validated["origin_trust"], "build_result": validated["build_result"],
            "contexts": [{k: c[k] for k in ("id", "module", "source_set", "scope")} for c in validated["contexts"]]}


def inspection_inputs(root: Path, manifest: dict, *, context_id: str | None, scope: str) -> dict:
    manifest = validate_manifest(root, manifest)
    if manifest["build_result"]["status"] != "SUCCESS" or manifest["build_result"].get("freshness") in {"MIXED_BUILD_INPUTS", "STALE_SOURCE"}:
        raise AnalysisError("BUILD_ARTIFACT_UNAVAILABLE: non-successful build has no fresh compiler outputs", 3)
    if not manifest["contexts"]:
        raise AnalysisError("BUILD_CONTEXT_UNAVAILABLE: imported result has no analysis variants", 3)
    candidates = [c for c in manifest["contexts"] if c["scope"] == scope and (context_id is None or c["id"] == context_id)]
    if len(candidates) != 1:
        raise AnalysisError("Explicit --context required; variants: " + ", ".join(c["id"] for c in candidates))
    selected = candidates[0]
    def absolute(raw):
        path = Path(raw)
        return str(path.resolve() if path.is_absolute() else safe_path(root, raw))
    classpath = [{**artifact, "path": absolute(artifact["path"])} for artifact in selected["classpath"]]
    model = {"source_sets": [{"module": selected["module"], "id": selected["source_set"], "scope": selected["scope"],
                               "roots": selected["source_roots"], "files": selected["source_files"]}]}
    return {"sources": selected["source_files"], "java_release": int((selected.get("compiler_options") or {}).get("release", 21)),
            "repo_id": selected["repo_id"], "module": selected["module"], "source_set": selected["source_set"],
            "classpath": classpath, "bytecode_roots": [absolute(o["path"]) for o in selected.get("outputs", []) if o.get("freshness") == "EXECUTION_BOUND"],
            "project_model": model,
            "build_context": {"mode": "BUILD_IMPORT", "build_id": manifest["build_id"], "build_context_id": selected["id"],
                "freshness": "EXECUTION_BOUND", "origin_trust": manifest.get("origin_trust", "SUPPLIED_EXPORT_UNVERIFIED"),
                "build_profiles": selected.get("build_profiles", []), "spring_profiles": selected.get("spring_profiles"),
                "diagnostics": manifest.get("diagnostics", []) + selected.get("diagnostics", []),
                "compiler_options": selected.get("compiler_options"), "generated_source_roots": selected.get("generated_source_roots", []),
                "toolchain": selected.get("toolchain"), "build_system": selected.get("build_system"),
                "database_id": selected.get("database_id"), "schema_stream_id": selected.get("schema_stream_id"),
                "persistence_unit": selected.get("persistence_unit"), "naming_strategy": selected.get("naming_strategy"),
                "manifest_hash": digest(manifest)}}

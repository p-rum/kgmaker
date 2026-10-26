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


def _validate_toolchain_selection(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("selection") != "EXPLICIT_JAVA_HOME":
        raise AnalysisError("Invalid explicit toolchain selection")
    home = value.get("java_home")
    executables = value.get("executables")
    if not isinstance(home, str) or not home or not Path(home).is_absolute() or not isinstance(executables, dict):
        raise AnalysisError("Explicit toolchain requires an absolute Java home and executable records")
    for name in ("java", "javac"):
        record = executables.get(name)
        if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                or not Path(record["path"]).is_absolute() or not HASH.fullmatch(str(record.get("sha256", "")))):
            raise AnalysisError("Explicit toolchain executable record is invalid")
    expected = digest({key: item for key, item in value.items() if key != "fingerprint"})
    if value.get("fingerprint") != expected:
        raise AnalysisError("Explicit toolchain fingerprint mismatch")
    for name in ("java", "javac"):
        record = executables[name]
        path = Path(record["path"])
        if not path.is_file() or file_hash(path) != record["sha256"]:
            raise AnalysisError("STALE_TOOLCHAIN: selected Java toolchain changed", 3)
    return value


def validate_kotlin_options(options: dict) -> None:
    """Captured configuration is not evidence that our frontend implements it."""
    if not isinstance(options, dict) or type(options.get("schema_version")) is not int or options["schema_version"] != 1:
        raise AnalysisError("Kotlin options require schema_version 1")
    if options.get("status") not in {"CAPTURED_CONFIGURATION", "PARTIAL", "NOT_OBSERVED"}:
        raise AnalysisError("Kotlin options require an explicit capture status")
    for key in ("language_version", "api_version", "jvm_target", "compiler_version"):
        value = options.get(key)
        if value is not None and (not isinstance(value, str) or not value or "${" in value):
            raise AnalysisError("Kotlin option is not resolved: " + key)
    for key in ("free_args", "plugins", "plugin_options", "opt_in"):
        value = options.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or "${" in item for item in value):
            raise AnalysisError("Kotlin option requires resolved strings: " + key)
    artifacts = options.get("plugin_artifacts")
    if artifacts is not None:
        if (not isinstance(artifacts, list)
                or (options.get("status") == "CAPTURED_CONFIGURATION" and options.get("plugins") and not artifacts)):
            raise AnalysisError("Kotlin plugin artifacts require resolved files")
        seen = set()
        for artifact in artifacts:
            if (not isinstance(artifact, dict)
                    or set(artifact) != {"coordinates", "path", "sha256"}
                    or not isinstance(artifact.get("coordinates"), str) or not artifact["coordinates"]
                    or not isinstance(artifact.get("path"), str) or not Path(artifact["path"]).is_absolute()
                    or not HASH.fullmatch(str(artifact.get("sha256", "")))
                    or artifact["path"] in seen):
                raise AnalysisError("Kotlin plugin artifact record is invalid")
            seen.add(artifact["path"])
            path = Path(artifact["path"])
            if path.is_symlink() or not path.is_file() or file_hash(path) != artifact["sha256"]:
                raise AnalysisError("STALE_KOTLIN_PLUGIN: Kotlin plugin artifact changed", 3)
    for key in ("java_parameters", "all_warnings_as_errors", "suppress_warnings", "progressive"):
        if key in options and type(options[key]) is not bool:
            raise AnalysisError("Kotlin option requires boolean: " + key)


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
    selected_toolchain = _validate_toolchain_selection(manifest.get("toolchain_selection"))
    ids = set()
    output_producers: dict[str, list[tuple[str, dict[str, str]]]] = {}
    build_repos = {}; repo_builds = {}
    for context in manifest["contexts"]:
        if not isinstance(context, dict) or not isinstance(context.get("id"), str) or context["id"] in ids:
            raise AnalysisError("Duplicate/invalid build context")
        ids.add(context["id"])
        if context.get("scope") not in SCOPES or not all(isinstance(context.get(k), str) and context[k] for k in ("module", "source_set", "repo_id")):
            raise AnalysisError("Build context requires repo/module/source-set/scope")
        build_root = context.get("build_root")
        if build_root is not None:
            if not isinstance(build_root, str) or not build_root:
                raise AnalysisError("Build root must be a snapshot-relative identity")
            safe_path(root, build_root)
            repo = context["repo_id"]
            if (build_root != "." and repo == "local") or (build_root in build_repos and build_repos[build_root] != repo) or (repo in repo_builds and repo_builds[repo] != build_root):
                raise AnalysisError("Ambiguous included build repository identity")
            build_repos[build_root] = repo; repo_builds[repo] = build_root
        scope_origin = context.get("scope_origin")
        if scope_origin is not None and (not isinstance(scope_origin, str) or scope_origin not in {"GRADLE_CONVENTION", "EXPLICIT_MAPPING", "UNKNOWN"}
                or (scope_origin == "UNKNOWN" and context["scope"] != "unknown")
                or (scope_origin == "GRADLE_CONVENTION" and
                    {"main": "production", "test": "test", "testFixtures": "test_fixture"}.get(context["source_set"]) != context["scope"])):
            raise AnalysisError("Invalid source-set scope provenance")
        if not isinstance(context.get("source_roots"), list) or not isinstance(context.get("source_files"), list):
            raise AnalysisError("Build source roots/files must be arrays")
        for path in context["source_roots"] + context["source_files"]:
            safe_path(root, path)
        generated = context.get("generated_source_roots", [])
        if (not isinstance(generated, list) or any(not isinstance(path, str) for path in generated)
                or not set(generated) <= set(context["source_roots"])):
            raise AnalysisError("Generated source roots must be a subset of source_roots")
        generated_sources = context.get("generated_sources", [])
        if not isinstance(generated_sources, list) or any(not isinstance(item, dict) for item in generated_sources):
            raise AnalysisError("Generated sources must be content-bound objects")
        generated_by_path = {}
        for item in generated_sources:
            path = item.get("path")
            if (not isinstance(path, str) or path in generated_by_path
                    or not any(path == root_path or path.startswith(root_path.rstrip("/") + "/") for root_path in generated)
                    or not HASH.fullmatch(str(item.get("sha256", "")))
                    or item.get("execution_id") != result.get("execution_id")
                    or item.get("snapshot_hash") != snapshot["content_hash"]
                    or item.get("freshness") != "EXECUTION_BOUND"):
                raise AnalysisError("Generated source is not bound to this successful execution")
            source = safe_path(root, path)
            if result["status"] != "SUCCESS" or not source.is_file() or file_hash(source) != item["sha256"]:
                raise AnalysisError("STALE_GENERATED_SOURCE: " + path, 3)
            generated_by_path[path] = item
        profiles = context.get("build_profiles", [])
        if not isinstance(profiles, list) or any(not isinstance(profile, str) or not profile for profile in profiles):
            raise AnalysisError("Build profiles must be nonempty strings")
        if not isinstance(context.get("compiler_options", {}), dict):
            raise AnalysisError("Compiler options must be an object")
        if "kotlin" in context.get("compiler_options", {}):
            validate_kotlin_options(context["compiler_options"]["kotlin"])
        toolchain = context.get("toolchain")
        if toolchain is not None and (not isinstance(toolchain, dict)
                or not isinstance(toolchain.get("java_version"), str) or not toolchain["java_version"]
                or ("java_home" in toolchain and
                    (not isinstance(toolchain["java_home"], str) or not toolchain["java_home"]))):
            raise AnalysisError("Toolchain requires a captured Java version and valid optional home")
        if selected_toolchain is not None and result["status"] == "SUCCESS":
            if toolchain is None or Path(toolchain.get("java_home", "")).resolve() != Path(selected_toolchain["java_home"]).resolve():
                raise AnalysisError("Explicit toolchain does not match the toolchain reported by the build")
        coordinates = ("group_id", "artifact_id", "version")
        for field in ("effective_dependencies", "dependency_management", "imported_boms"):
            values = context.get(field, [])
            if (not isinstance(values, list) or any(
                    not isinstance(item, dict)
                    or any(not isinstance(item.get(key), str) or not item[key] for key in coordinates)
                    for item in values)):
                raise AnalysisError(field + " must contain effective dependency coordinates")
        if any(item.get("scope") != "import" or item.get("type") != "pom"
               for item in context.get("imported_boms", [])):
            raise AnalysisError("Imported BOM provenance requires pom/import coordinates")
        parent = context.get("parent")
        if parent is not None and (not isinstance(parent, dict)
                or any(not isinstance(parent.get(key), str) or not parent[key] for key in coordinates)):
            raise AnalysisError("Effective parent coordinates are invalid")
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
            if source not in snapshot["sources"] and source not in generated_by_path:
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
            if artifact.get("freshness") == "EXECUTION_BOUND":
                realm = {key: context[key] for key in ("repo_id", "module", "source_set", "scope")}
                output_producers.setdefault(str(path.resolve()), []).append((artifact["sha256"], realm))
    for context in manifest["contexts"]:
        for artifact in context["classpath"]:
            claimed_realm = artifact.get("realm")
            if claimed_realm is None:
                continue
            if (not isinstance(claimed_realm, dict)
                    or set(claimed_realm) != {"repo_id", "module", "source_set", "scope"}
                    or any(not isinstance(value, str) or not value for value in claimed_realm.values())):
                raise AnalysisError("Invalid classpath artifact realm")
            path = Path(artifact["path"])
            if not path.is_absolute():
                path = safe_path(root, artifact["path"])
            producers = output_producers.get(str(path.resolve()), [])
            if len(producers) != 1 or producers[0] != (artifact["sha256"], claimed_realm):
                raise AnalysisError("Classpath realm requires one matching execution-bound producer output")
    if snapshot.get("inventory") == "ALL_BUILD_INPUTS_V1":
        from .build_runner import snapshot as inventory
        if inventory(root) != snapshot["sources"]:
            raise AnalysisError("STALE_SOURCE: complete build inventory changed", 3)
    elif any(o.get("freshness") == "EXECUTION_BOUND" for c in manifest["contexts"] for o in c.get("outputs", [])):
        raise AnalysisError("Fresh outputs require a complete build-input inventory")
    return copy.deepcopy(manifest)


def resolve_content_bound_output(root: Path, manifest: dict, *, context_id: str,
                                 sha256: str) -> dict:
    """Resolve one successful build output by context and content.

    Coordinates and filenames are deliberately absent from the identity.  A
    workspace mapping may only consume an execution-bound output from a
    currently valid BuildManifest.
    """
    if not isinstance(context_id, str) or not context_id or not HASH.fullmatch(sha256):
        raise AnalysisError("Invalid release output selector")
    validated = validate_manifest(root, manifest)
    contexts = [item for item in validated["contexts"] if item["id"] == context_id]
    if not contexts:
        raise AnalysisError("RELEASE_OUTPUT_CONTEXT_UNAVAILABLE: " + context_id, 3)
    if len(contexts) != 1:
        raise AnalysisError("RELEASE_OUTPUT_CONTEXT_AMBIGUOUS: " + context_id, 3)
    matches = [
        item for item in contexts[0].get("outputs", [])
        if item.get("sha256") == sha256 and item.get("freshness") == "EXECUTION_BOUND"
    ]
    if not matches:
        raise AnalysisError("RELEASE_OUTPUT_HASH_MISMATCH: " + sha256, 3)
    if len(matches) != 1:
        raise AnalysisError("RELEASE_OUTPUT_AMBIGUOUS: " + sha256, 3)
    selected = matches[0]
    path = Path(selected["path"])
    if not path.is_absolute():
        path = safe_path(root, selected["path"])
    if path.is_symlink() or not path.is_file():
        raise AnalysisError("RELEASE_OUTPUT_KIND_UNSUPPORTED: regular file required", 3)
    return copy.deepcopy(selected)


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
    dependency_model = {key: selected.get(key, [] if key != "parent" else None) for key in (
        "parent", "effective_dependencies", "dependency_management", "imported_boms")}
    generated_roots = selected.get("generated_source_roots", [])
    generated_files = {item["path"] for item in selected.get("generated_sources", [])}
    handwritten_roots = [path for path in selected["source_roots"] if path not in generated_roots]
    handwritten_files = [path for path in selected["source_files"] if path not in generated_files]
    source_sets = [{"module": selected["module"], "id": selected["source_set"], "scope": selected["scope"],
                    "scope_origin": selected.get("scope_origin"), "roots": handwritten_roots, "files": handwritten_files}]
    if generated_roots or generated_files:
        source_sets.append({"module": selected["module"], "id": selected["source_set"] + ":generated",
                            "scope": selected["scope"], "roots": generated_roots,
                            "files": sorted(generated_files), "generated": True})
    model = {"source_sets": source_sets}
    return {"sources": selected["source_files"], "java_release": int((selected.get("compiler_options") or {}).get("release", 21)),
            "repo_id": selected["repo_id"], "module": selected["module"], "source_set": selected["source_set"],
            "classpath": classpath, "bytecode_roots": [absolute(o["path"]) for o in selected.get("outputs", []) if o.get("freshness") == "EXECUTION_BOUND"],
            "project_model": model,
            "build_context": {"mode": "BUILD_IMPORT", "build_id": manifest["build_id"], "build_context_id": selected["id"],
                "freshness": "EXECUTION_BOUND", "origin_trust": manifest.get("origin_trust", "SUPPLIED_EXPORT_UNVERIFIED"),
                "build_profiles": selected.get("build_profiles", []), "spring_profiles": selected.get("spring_profiles"),
                "diagnostics": manifest.get("diagnostics", []) + selected.get("diagnostics", []),
                "compiler_options": selected.get("compiler_options"), "generated_source_roots": generated_roots,
                "generated_sources": selected.get("generated_sources", []),
                "toolchain": selected.get("toolchain"), "build_system": selected.get("build_system"),
                "dependency_model": dependency_model, "dependency_model_hash": digest(dependency_model),
                "database_id": selected.get("database_id"), "schema_stream_id": selected.get("schema_stream_id"),
                "persistence_unit": selected.get("persistence_unit"), "naming_strategy": selected.get("naming_strategy"),
                "manifest_hash": digest(manifest)}}

"""Compiler inspection orchestration over the existing graph/store.

The worker owns symbols and AST IR. Python validates transport, provenance and
snapshot consistency, builds CFG deterministically and publishes graph schema 3.
No project build, npm script, migration or DB connection is implicit here.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

from .analysis_model import AnalysisError, digest, file_hash, read_json, safe_path
from .classification import Classifier
from .compiler_sources import (
    JVM_JPA_SOURCE_SNAPSHOTS, JVM_RAW_SOURCE_SNAPSHOT, JVM_SOURCE_SNAPSHOTS,
    jvm_raw_capture_id, normalized_source_projection, unsupported_kotlin_source,
)
from .control_flow import from_body
from .model import Edge, KnowledgeGraph, Node
from .scanner import scan_repository
from .store import graph_revision, save_graph
from .worker_protocol import WorkerError, handshake, request_worker
from .http_execution import redact_uri_text

VERSION = "inspection-1"
UI_RULE_VERSION = "react-jsx-events-4"


def artifact_hash(path: Path) -> str:
    if path.is_file():
        return file_hash(path)
    if path.is_dir():
        values = {}
        for file in sorted(path.rglob("*.class")):
            if file.is_symlink():
                raise AnalysisError("Symlink bytecode artifacts are unsupported")
            values[file.relative_to(path).as_posix()] = file_hash(file)
        return digest(values)
    raise AnalysisError("Artifact unavailable: " + str(path))


def worker_home(path: Path | None = None) -> Path:
    """Explicit selection wins; installed resources precede checkout fallback.

    A missing explicit directory is never replaced by another distribution.
    Resource lookup does not require or execute either optional runtime.
    """
    if path is not None:
        return path.expanduser().resolve()
    if os.environ.get("KGMAKER_WORKERS_HOME"):
        return Path(os.environ["KGMAKER_WORKERS_HOME"]).expanduser().resolve()
    from importlib.util import find_spec
    resources = find_spec("kgmaker_workers")
    if resources is not None and resources.origin is not None:
        return Path(resources.origin).resolve().parent
    return Path(__file__).resolve().parents[2] / "workers"


def _jvm_worker_jar(home: Path, *, kotlin_backend="k1") -> Path:
    """Resolve the packaged JVM worker without assuming a Maven finalName.

    Maven's default artifact name contains the project version.  Development
    checkouts may also provide the versionless name used by older packaging
    scripts, but accepting an arbitrary first jar would make a stale or
    unrelated worker look valid.  Therefore a versioned fallback is accepted
    only when it is unambiguous.
    """
    target = home / "jvm" / ("target-k2" if kotlin_backend == "k2" else "target")
    plain = target / "kgmaker-jvm-worker.jar"
    if plain.is_file():
        return plain
    candidates = sorted(target.glob("kgmaker-jvm-worker-*.jar"))
    if len(candidates) == 1 and candidates[0].is_file():
        return candidates[0]
    raise WorkerError(
        "Optional JVM worker unavailable or ambiguous for Kotlin backend " + kotlin_backend + " at " + str(target) + "; scan remains usable. "
        "Build exactly one trusted JVM worker artifact explicitly, or select --worker-home / KGMAKER_WORKERS_HOME.",
        "TOOLCHAIN_UNAVAILABLE",
    )


def command(language: str, home: Path | None = None, *, kotlin_backend="k1") -> list[str]:
    if language not in {"jvm", "typescript"}:
        raise WorkerError("Unsupported worker language: " + language, "TOOLCHAIN_UNAVAILABLE")
    home = worker_home(home)
    if language == "jvm":
        if not isinstance(kotlin_backend, str) or kotlin_backend not in {"k1", "k2"}:
            raise AnalysisError("Unsupported Kotlin backend; select k1 or k2")
        java = shutil.which("java")
        if not java:
            raise WorkerError("Optional JVM worker/JDK unavailable; scan remains usable. Build the trusted worker explicitly.", "TOOLCHAIN_UNAVAILABLE")
        # Anchor the lookup before the worker changes cwd and keep any selected alias.
        java_path = Path(java).absolute()
        java_root = java_path.resolve().parent.parent
        if not any((java_root / 'bin' / name).is_file() for name in ('javac', 'javac.exe')):
            raise WorkerError('JVM inspection requires a full JDK 21+ (javac beside java); a runtime-only JRE is unsupported. SOURCE_ONLY remains usable.', 'TOOLCHAIN_UNAVAILABLE')
        release = java_root / 'release'
        if release.is_file():
            import re
            version = re.search(r'^JAVA_VERSION="(\d+)', release.read_text(encoding='utf-8'), re.M)
            if version and int(version.group(1)) < 21:
                raise WorkerError('JVM inspection requires JDK 21+; selected Java runtime is older. SOURCE_ONLY remains usable.', 'TOOLCHAIN_UNAVAILABLE')
        jar = _jvm_worker_jar(home, kotlin_backend=kotlin_backend)
        return [str(java_path), "-Xmx1536m", "-jar", str(jar)]
    node = shutil.which("node")
    script = home / "typescript/worker.cjs"
    if not node or not script.is_file() or not (home / "typescript/node_modules/typescript/lib/typescript.js").is_file():
        raise WorkerError("Optional TypeScript worker/Node unavailable at " + str(home)
                          + "; install pinned dependencies explicitly or select --worker-home / KGMAKER_WORKERS_HOME."
                          + " SOURCE_ONLY scan remains usable.", "TOOLCHAIN_UNAVAILABLE")
    package = home / "typescript/package.json"
    if package.is_file():
        try:
            package_data = json.loads(package.read_text(encoding="utf-8"))
            marker = package_data.get("kgmaker_input_snapshot")
        except (OSError, ValueError, AttributeError) as error:
            raise WorkerError("Invalid TypeScript worker package metadata: " + str(package), "TOOLCHAIN_UNAVAILABLE") from error
        if marker is not None and (type(marker) is not int or marker != 1):
            raise WorkerError("Unsupported TypeScript worker input snapshot distribution", "TOOLCHAIN_UNAVAILABLE")
        if marker == 1 and not (home / "typescript/input_snapshot.cjs").is_file():
            raise WorkerError("TypeScript input snapshot helper unavailable at " + str(home) + "; prepare the complete trusted distribution explicitly", "TOOLCHAIN_UNAVAILABLE")
        ui_marker = package_data.get("kgmaker_ui_adapter")
        if ui_marker is not None and (type(ui_marker) is not int or ui_marker != 1
                or not (home / "typescript/ui_events.cjs").is_file()):
            raise WorkerError("TypeScript UI adapter helper unavailable or unsupported", "TOOLCHAIN_UNAVAILABLE")
        value_marker = package_data.get("kgmaker_frontend_values")
        if value_marker is not None and (type(value_marker) is not int or value_marker != 1
                or not (home / "typescript/frontend_values.cjs").is_file()):
            raise WorkerError("TypeScript value flow helper unavailable or unsupported", "TOOLCHAIN_UNAVAILABLE")
    return [str(Path(node).absolute()), str(script)]


def distribution(language: str, home=None, *, kotlin_backend="k1") -> list[dict]:
    root = worker_home(home)
    target = root / "jvm" / ("target-k2" if kotlin_backend == "k2" else "target")
    paths = ([_jvm_worker_jar(root, kotlin_backend=kotlin_backend)] + sorted((target / "lib").glob("*.jar"))) if language == "jvm" else [root / "typescript/worker.cjs", root / "typescript/node_modules/typescript/lib/typescript.js"]
    helper = root / "typescript/input_snapshot.cjs"
    if language == "typescript":
        if helper.is_file():
            paths.append(helper)
        ui_helper = root / "typescript/ui_events.cjs"
        if ui_helper.is_file():
            paths.append(ui_helper)
        flow_helper = root / "typescript/frontend_values.cjs"
        if flow_helper.is_file():
            paths.append(flow_helper)
        package = root / "typescript/package.json"
        if package.is_file():
            paths.append(package)
    return [{"path": str(path.resolve()), "sha256": file_hash(path)} for path in paths]


def sanitize(value, *, key="", semantic=False):
    """Persistent graph metadata contains declarations, never secret payloads."""
    if isinstance(value, dict):
        return {k: sanitize(v, key=k, semantic=semantic or k in {"annotations", "literal", "spring_properties"}) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, key=key, semantic=semantic) for v in value]
    if isinstance(value, str):
        import re
        if any(word in key.lower() for word in ("password", "secret", "authorization", "access_token", "api_key")):
            return "<redacted>"
        value = re.sub(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*", r"\1 [redacted]", value, flags=re.I)
        value = re.sub(r"(\b(?:X-Api-Key|Api-Key)\s*[:=]\s*)[^,;\r\n]+", r"\1[redacted]", value, flags=re.I)
        value = re.sub(r"(\$\{[^}:]*(?:password|secret|token|api[_-]?key)[^}:]*:)[^}]*\}", r"\1[redacted]}", value, flags=re.I)
        value = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", value)
        value = re.sub(r"([?&](?:token|password|secret|api[_-]?key|authorization)=)[^&\s]*", r"\1[redacted]", value, flags=re.I)
        return redact_uri_text(value, relative=semantic)
    return value


def _selected_jvm_source_sets(project_model, module, source_set):
    return [item for item in (project_model or {}).get("source_sets", [])
            if item["module"] == module and item["id"] in {source_set, source_set + ":generated"}]


def source_snapshot(root: Path, graph: KnowledgeGraph, selected: dict) -> dict:
    """One capture/replay policy; legacy contexts retain their original scope gate."""
    version = selected.get("source_snapshot_version")
    if version == "typescript-input-discovery-1":
        from .typescript_snapshot import captured_sources
        return captured_sources(root, selected.get("project"))
    source_hashes = graph.files
    if version == JVM_RAW_SOURCE_SNAPSHOT:
        if graph.raw_file_hashes is None:
            raise WorkerError("JVM byte snapshot requires a fresh source scan", "STALE")
        source_hashes = graph.files | graph.raw_file_hashes
    files = [node for node in graph.nodes if node.kind == "file"]
    if (version not in JVM_SOURCE_SNAPSHOTS
            or (version in JVM_JPA_SOURCE_SNAPSHOTS and not (selected.get("project_model") or {}).get("source_sets"))):
        return dict(sorted((node.path, source_hashes[node.path]) for node in files
                           if node.scope == selected["scope"] or (node.scope == "unknown" and node.role == "configuration")))
    source_sets = _selected_jvm_source_sets(selected.get("project_model"), selected["module"], selected["source_set"])
    memberships = {item["module"] + ":" + item["id"] for item in source_sets}
    # Root/module build configuration is shared; sibling source-set resources are not.
    parents = {Path(".")}
    for item in source_sets:
        for raw in item.get("roots", []) + item.get("files", []):
            parents.update(Path(raw).parents)
    paths = {node.path for node in files if memberships.intersection(node.build_membership)
             or (not node.build_membership and node.role == "configuration" and Path(node.path).parent in parents
                 and node.scope == "unknown")
             or (not node.build_membership and node.role == "configuration"
                 and any(node.path.startswith((parent / "gradle").as_posix() + "/") for parent in parents))}
    result = {path: source_hashes[path] for path in paths}
    # Groovy build scripts are not scanner source languages, but remain shared inputs.
    for parent in parents:
        for name in ("build.gradle", "settings.gradle", "build.gradle.kts", "settings.gradle.kts", "gradle.properties", "pom.xml"):
            relative = (parent / name).as_posix()
            target = safe_path(root, relative)
            if target.is_file():
                if version == JVM_RAW_SOURCE_SNAPSHOT and relative in source_hashes:
                    result[relative] = source_hashes[relative]
                else:
                    result[relative] = file_hash(target)
    return dict(sorted(result.items()))


def jpa_xml_input_snapshot(root: Path, selected: dict) -> dict:
    """Capture the selected JVM persistence XML closure, including absent candidates."""
    from .framework import _safe_jpa_xml, _xml_local
    # The framework contract currently selects only project-root JPA defaults;
    # retain absent candidates so their later appearance invalidates replay.
    candidate_paths = {"META-INF/persistence.xml", "META-INF/orm.xml"}
    descriptor = "META-INF/persistence.xml"
    try:
        descriptor_target = (root / descriptor).resolve(strict=True)
        descriptor_is_confined_file = descriptor_target.is_relative_to(root.resolve()) and descriptor_target.is_file()
    except (OSError, RuntimeError, ValueError):
        descriptor_is_confined_file = False
    if descriptor in candidate_paths and descriptor_is_confined_file:
        document, _ = _safe_jpa_xml(root, descriptor)
        if document is not None:
            units = [child for child in document if _xml_local(child)[1] == "persistence-unit"]
            name = selected.get("persistence_unit")
            units = [unit for unit in units if unit.get("name") == name] if name else units
            if len(units) == 1:
                for child in units[0]:
                    if _xml_local(child)[1] == "mapping-file" and child.text and child.text.strip():
                        candidate_paths.add(child.text.strip())
    captured = []
    for relative in sorted(candidate_paths):
        path = root / relative
        try:
            try:
                target = path.resolve(strict=True)
            except FileNotFoundError:
                # Keep the resolved locator for missing files and dangling links.
                target = path.resolve(strict=False)
            if not target.is_relative_to(root.resolve()):
                captured.append({"path": relative, "status": "invalid", "resolved": str(target)})
            elif target.is_file():
                hasher = __import__("hashlib").sha256()
                with target.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(chunk)
                captured.append({"path": relative, "status": "present", "resolved": str(target),
                                 "sha256": hasher.hexdigest()})
            else:
                captured.append({"path": relative, "status": "missing", "resolved": str(target)})
        except (OSError, RuntimeError, ValueError):
            captured.append({"path": relative, "status": "invalid"})
    return {"version": "jpa-xml-input-capture-1", "persistence_unit": selected.get("persistence_unit"),
            "inputs": captured}


def context(root: Path, base: KnowledgeGraph, language: str, metadata: dict, *, repo_id: str,
            module: str, source_set: str, scope: str, build_context: dict | None = None) -> dict:
    raw_jvm_snapshot = language == "jvm" and "compiler_inputs" in (build_context or {})
    value = {"mode": "BUILD_IMPORT", "repo_id": repo_id, "module": module, "source_set": source_set,
             "scope": scope, "language": language, "origin_trust": "LOCAL_COMPILER_INPUTS", "coverage": "PARTIAL",
             "freshness": "CONTENT_VERIFIED",
             "classification_override_hash": digest(Classifier(root).config),
             "classifier_contexts": [c for c in base.contexts if c.get("scope") == scope], "worker": metadata, "analyzer_version": VERSION}
    if build_context:
        value.update(build_context)
    if language == "jvm":
        from .schema_replay import persistence_selection
        value["persistence_selection_hash"] = digest(persistence_selection(value))
        value["source_snapshot_version"] = JVM_RAW_SOURCE_SNAPSHOT if raw_jvm_snapshot else "selected-source-set-2"
        value["jpa_xml_inputs"] = jpa_xml_input_snapshot(root, value)
    if language == "typescript" and isinstance(value.get("project"), dict) and "input_discovery" in value["project"]:
        value["source_snapshot_version"] = "typescript-input-discovery-1"
    value["source_files"] = source_snapshot(root, base, value)
    if raw_jvm_snapshot:
        value["normalized_source_files"] = normalized_source_projection(base.files, value["source_files"])
    from .framework import JPA_RULE_VERSION, SPRING_RULE_VERSION
    # Spring augmentation is JVM-only. Preserve the legacy TS context metadata
    # and selection identity, including its pre-existing React overwrite behavior.
    value["framework_rule_versions"] = {"spring": SPRING_RULE_VERSION if language == "jvm" else "annotation-source-v3",
                                        "jpa": JPA_RULE_VERSION if language == "jvm" else "annotation-source-v4"}
    if language == "jvm":
        from .kafka_retry import VERSION as KAFKA_RETRY_VERSION
        value["framework_rule_versions"]["kafka_retry"] = KAFKA_RETRY_VERSION
        from .http_execution import prepare_context
        value = prepare_context(root, value)
        from .spring_conditions import condition_inputs
        value["spring_condition_inputs_hash"] = digest(condition_inputs(value))
    if (language == "typescript" and value.get("ui_framework") == "react"
            and "ui_adapters" in value.get("project", {})):
        value["framework_rule_versions"] = {"react": UI_RULE_VERSION}
    from .return_flow import VERSION as RETURN_VERSION
    value["return_flow_rule_version"] = RETURN_VERSION
    if language == "jvm":
        from .field_flow import VERSION as FIELD_VERSION
        value["field_flow_rule_version"] = FIELD_VERSION
        from .local_operations import VERSION as LOCAL_OPERATION_VERSION
        value["local_operation_rule_version"] = LOCAL_OPERATION_VERSION
    from .graph_provider import _selection_key
    value["selection_key"] = _selection_key({key: item for key, item in value.items()
                                              if key != "selection_key"})
    identity = digest(value)
    if raw_jvm_snapshot:
        value["source_capture_base"] = identity
        identity = jvm_raw_capture_id(value)
        if identity is None:
            raise WorkerError("Invalid selected JVM compiler input snapshot", "INVALID_PROTOCOL")
    value["id"] = identity
    return value


def validate_response(response: dict, selected_context: dict):
    if response.get("context_id") != selected_context["id"]:
        raise WorkerError("Worker returned another analysis context", "INVALID_PROTOCOL")
    for key in ("symbols", "call_sites", "bodies", "facts", "diagnostics"):
        if not isinstance(response.get(key), list) or not all(isinstance(v, dict) for v in response[key]):
            raise WorkerError("Malformed worker collection: " + key, "INVALID_PROTOCOL")
    if any(not isinstance(s.get("id"), str) for s in response["symbols"]):
        raise WorkerError("Malformed worker symbol identity", "INVALID_PROTOCOL")
    ids = {s["id"] for s in response["symbols"]}
    if None in ids or len(ids) != len(response["symbols"]):
        raise WorkerError("Ambiguous/duplicate worker symbol identity", "INVALID_PROTOCOL")
    from .symbol_identity import valid_declaration
    if any("logical_key" in symbol or ("kotlin_declaration" in symbol and
               not valid_declaration(symbol["kotlin_declaration"])) for symbol in response["symbols"]):
        raise WorkerError("Invalid Kotlin declaration identity witness", "INVALID_PROTOCOL")
    sites = set()
    for site in response["call_sites"]:
        if not isinstance(site.get("id"), str) or site["id"] in sites or not isinstance(site.get("caller"), str) or site["caller"] not in ids:
            raise WorkerError("Dangling/duplicate worker call site", "INVALID_PROTOCOL")
        sites.add(site["id"])
        if site.get("declared_target") is not None and (not isinstance(site["declared_target"], str) or site["declared_target"] not in ids):
            raise WorkerError("Unknown declared target", "INVALID_PROTOCOL")
        if not isinstance(site.get("dispatch_candidates", []), list) or any(not isinstance(t, str) or t not in ids for t in site.get("dispatch_candidates", [])):
            raise WorkerError("Unknown dispatch candidate", "INVALID_PROTOCOL")
        if any(key in site and not isinstance(site[key], str) for key in ("invocation_kind", "evidence_kind")):
            raise WorkerError("Malformed worker call classification", "INVALID_PROTOCOL")
        if site.get("evidence_kind") == "SYMBOL_RESOLVED" and not site.get("declared_target"):
            raise WorkerError("Resolved call has no declared target", "INVALID_PROTOCOL")
    for body in response["bodies"]:
        if not isinstance(body, dict) or not isinstance(body.get("method"), str) or body["method"] not in ids or body.get("context_id") != selected_context["id"]:
            raise WorkerError("Unknown method body/context", "INVALID_PROTOCOL")
    # Additive typed binding/literal fields are optional for legacy workers.
    pending = [(body.get("body", {}), 0) for body in response["bodies"]]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 200000 or depth > 512:
            raise WorkerError("Typed IR size/depth exceeded", "INVALID_PROTOCOL")
        if isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, dict):
            for key in ("binding", "binding_ref"):
                if key in value and value[key] is not None:
                    record = value[key]
                    if (not isinstance(record, dict) or (record.get("id") is not None and (not isinstance(record["id"], str) or not record["id"]))
                            or not isinstance(record.get("kind"), str)
                            or (record.get("symbol") is not None and record["symbol"] not in ids)):
                        raise WorkerError("Malformed typed binding", "INVALID_PROTOCOL")
            for key in ("captured_bindings", "referenced_bindings"):
                if key in value and (not isinstance(value[key], list) or len(value[key]) > 128
                        or any(not isinstance(r, dict) or not isinstance(r.get("id"), str)
                               or not isinstance(r.get("kind"), str) for r in value[key])):
                    raise WorkerError("Malformed typed binding references", "INVALID_PROTOCOL")
            if "binding_references_complete" in value and type(value["binding_references_complete"]) is not bool:
                raise WorkerError("Malformed typed binding completeness", "INVALID_PROTOCOL")
            if "literal" in value:
                literal = value["literal"]
                if (not isinstance(literal, dict) or not isinstance(literal.get("type"), str)
                        or literal.get("source") not in {"COMPILER_LITERAL", "COMPILER_CONSTANT"}
                        or isinstance(literal.get("value"), (dict, list))):
                    raise WorkerError("Malformed typed literal", "INVALID_PROTOCOL")
            pending.extend((item, depth + 1) for item in value.values() if isinstance(item, (dict, list)))
    for fact in response["facts"]:
        if not isinstance(fact.get("source"), str) or not isinstance(fact.get("target"), str) or fact["source"] not in ids or fact["target"] not in ids:
            raise WorkerError("Dangling compiler fact", "INVALID_PROTOCOL")

    from .frontend_flow import validate_frontend_values
    validate_frontend_values(response, selected_context)
    from .return_flow import validate_return_ir
    from .local_operations import validate_operations
    from .criteria_queries import validate_query_ir
    try:
        validate_return_ir(response, selected_context)
        validate_operations(response, selected_context)
        validate_query_ir(response, selected_context)
    except ValueError as error:
        raise WorkerError(str(error), "INVALID_PROTOCOL") from error

    from .dataflow import validate_argument_bindings
    try:
        validate_argument_bindings(response)
    except ValueError as error:
        raise WorkerError(str(error), "INVALID_PROTOCOL") from None


def graph_from_response(root: Path, base: KnowledgeGraph, response: dict, selected_context: dict,
                        *, project_model: dict | None = None) -> KnowledgeGraph:
    response = sanitize(response)
    validate_response(response, selected_context)
    classifier = Classifier(root, project_model)
    nodes = {n.id: n for n in base.nodes}
    edges = set(base.edges)
    evidence = {e["id"]: e for e in base.evidence}
    metadata = sanitize(response["symbols"])
    call_sites = sanitize(response["call_sites"])
    ui_diagnostics = []
    context_id = selected_context["id"]

    from .kafka_code import declaration_witness, call_witness
    from .runtime_value import is_physical_value_hook, physical_field_operands
    symbols_by_id = {s["id"]: s for s in metadata}
    presence_hooks = {}
    if selected_context.get("freshness") == "EXECUTION_BOUND" and selected_context.get("language") == "jvm":
        for site in call_sites:
            if is_physical_value_hook(site, selected_context, symbols_by_id):
                presence_hooks.setdefault(site["caller"], []).append(site)
    presence_accesses = {caller: [] for caller, hooks in presence_hooks.items() if len(hooks) == 1}
    # Preserve the original compiler realm only for prospective Kafka declarations.
    kafka_sources = {s.get("id") for s in metadata
                     if any(isinstance(a, dict) and str(a.get("name", "")).rsplit(".", 1)[-1]
                            in {"KafkaListener", "KafkaListeners", "RetryableTopic", "DltHandler"}
                            for a in (s.get("annotations") if isinstance(s.get("annotations"), list) else []))}
    kafka_targets = {s.get("id") for s in metadata if s.get("name") == "send"
                     and s.get("owner") in {"org.springframework.kafka.core.KafkaTemplate",
                                            "org.springframework.kafka.core.KafkaOperations"}}
    kafka_sources.update(s.get("caller") for s in call_sites if s.get("declared_target") in kafka_targets)

    def proof(fact: dict, kind: str, *, source: str, target: str, relation: str) -> str:
        record = {"kind": kind, "source": source, "target": target, "relation": relation,
                  "context_ids": [context_id], "extractor": response["worker"],
                  "source_file": fact.get("path"), "source_range": fact.get("range"),
                  "sha256": fact.get("sha256"), "bytecode_offset": fact.get("bytecode_offset"),
                  "instruction_index": fact.get("instruction_index"), "artifact_hashes": fact.get("artifact_hashes"),
                  "representation": fact.get("representation"),
                  "compiler_backend": fact.get("compiler_backend", "javac" if str(fact.get("path", "")).endswith(".java") else None),
                  "compiler_version": fact.get("compiler_version", selected_context.get("worker", {}).get("compiler_version")),
                  "worker_backend": selected_context.get("kotlin_backend"),
                  "resolution_reason": fact.get("resolution_reason"),
                  "dispatch_algorithm": fact.get("dispatch_algorithm"),
                  "dispatch_completeness_reason": fact.get("dispatch_completeness_reason"),
                  "dispatch_classpath": fact.get("dispatch_classpath"),
                  "origin_trust": selected_context["origin_trust"], "freshness": selected_context["freshness"]}
        if (relation == "contains" and isinstance(fact.get("annotations"), list)
                and any(isinstance(a, dict) and str(a.get("name", "")).rsplit(".", 1)[-1]
                        in {"KafkaListener", "KafkaListeners", "RetryableTopic", "DltHandler"} for a in fact["annotations"])):
            record["compiler_annotation_fingerprint"] = digest(fact["annotations"])
        if relation == "contains" and fact.get("id") in kafka_sources:
            record["compiler_realm"] = {key: selected_context.get(key)
                                        for key in ("repo_id", "module", "source_set", "scope")}
            record["compiler_declaration"] = declaration_witness(fact)
        if relation == "declares_call" and fact.get("declared_target") in kafka_targets:
            record["compiler_call"] = call_witness(fact, symbols_by_id[fact["declared_target"]])
        if fact.get("argument_mapping_version") == 1:
            record.update({key: fact.get(key) for key in ("argument_mapping_version", "call_site", "argument_index",
                          "parameter_index", "parameter_name", "transformation", "binding_kind")})
        if fact.get("kind") == "handles_event" and fact.get("ui_adapter"):
            record.update(ui_adapter=fact["ui_adapter"], execution="NOT_OBSERVED")
        if fact.get("value_flow_version") == 1:
            record.update(value_flow_version=1, runtime_execution="NOT_OBSERVED", availability="UNKNOWN")
            if fact.get("ui_adapter"):
                record["ui_adapter"] = fact["ui_adapter"]
        if relation == "control_flow" and "physical_field_operands" in fact:
            record["physical_field_operands"] = fact["physical_field_operands"]
        identity = "evidence:" + digest(record)
        evidence[identity] = {"id": identity, **record}
        return identity

    def relation(source, target, name, fact, kind="SYMBOL_RESOLVED"):
        identity = proof(fact, kind, source=source, target=target, relation=name)
        source_range = fact.get("range") or {}
        edges.add(Edge(source, target, name, evidence_kind=kind, context_ids=(context_id,),
                       evidence_ids=(identity,), source_file=fact.get("path"), source_line=source_range.get("start_line")))
        return identity

    file_nodes = {n.path: n.id for n in base.nodes if n.kind == "file"}
    for symbol in metadata:
        path = symbol.get("path")
        c = classifier.classify(path) if path and not path.startswith("dependency/") else None
        origin = symbol.get("origin", "unknown")
        if origin not in {"handwritten", "generated", "dependency", "unknown"}:
            origin = "unknown"
        kind = symbol.get("kind", "symbol")
        if kind in {"enum_class", "enum"}:
            kind = "enum"
        scope = c.scope if c is not None else symbol.get("scope", selected_context["scope"])
        role = "contract" if kind in {"interface", "enum", "TypeAliasDeclaration", "InterfaceDeclaration"} else "executable_code"
        location = symbol.get("range") or {}
        nodes[symbol["id"]] = Node(symbol["id"], kind, symbol.get("name", "<unknown>"),
            path or "dependency/" + str(symbol.get("owner", "unknown")).replace(".", "/") + ".class",
            line=location.get("start_line"), signature=symbol.get("descriptor") or symbol.get("type"),
            scope=scope, role=role, origin=c.origin if c is not None and c.origin != "unknown" else origin,
            build_membership=c.build_membership if c else (),
            classification_evidence=c.classification_evidence if c else ("compiler-context:" + context_id,),
            metadata={key: value for key, value in sanitize(symbol).items() if key != "kotlin_declaration"})
        if path in file_nodes:
            relation(file_nodes[path], symbol["id"], "contains", symbol)
    from .symbol_identity import kotlin_source_omissions, occurrence_keys
    keys = ({} if kotlin_source_omissions(selected_context, base.diagnostics) else
            occurrence_keys(metadata, nodes, {context_id: selected_context}))
    for symbol in metadata:
        if symbol["id"] in keys:
            symbol["logical_key"] = keys[symbol["id"]]
    for site in call_sites:
        caller = nodes[site["caller"]]
        position = site.get("range") or {}
        nodes[site["id"]] = Node(site["id"], "call_site", site.get("invocation_kind", "call"),
            site.get("path") or caller.path, line=position.get("start_line"),
            scope=caller.scope, role="executable_code", origin=site.get("origin", caller.origin))
        kind = site.get("evidence_kind", "UNRESOLVED")
        site["evidence_ids"] = [relation(site["caller"], site["id"], "declares_reference" if site.get("invocation_kind") == "METHOD_REFERENCE" else "declares_call", site, kind)]
        if site.get("declared_target"):
            site["evidence_ids"].append(relation(site["id"], site["declared_target"], "resolves_to", site))
        for target in site.get("dispatch_candidates", []):
            site["evidence_ids"].append(relation(site["id"], target, "may_dispatch_to", site, "DISPATCH_CANDIDATE"))
        if kind == "UNRESOLVED":
            boundary = "boundary:" + digest({"site": site["id"], "reason": site["resolution_reason"]})
            nodes[boundary] = Node(boundary, "unresolved_boundary", site["resolution_reason"], caller.path,
                                   scope=caller.scope, role="unknown", origin="unknown")
            relation(site["id"], boundary, "unresolved_boundary", site, "UNRESOLVED")
    for fact in sanitize(response["facts"]):
        if fact["source"] in presence_accesses and fact["kind"] in {"reads_field", "writes_field"}:
            presence_accesses[fact["source"]].append(fact)
        if fact.get("kind") == "handles_event" and selected_context.get("ui_framework") == "react":
            adapter = fact.get("ui_adapter")
            wrapper = adapter.get("wrapper") if isinstance(adapter, dict) else None
            selected_scope = selected_context["scope"]
            valid = (isinstance(adapter, dict) and adapter.get("rule") == UI_RULE_VERSION
                     and nodes[fact["source"]].scope == selected_scope
                     and nodes[fact["target"]].scope == selected_scope)
            if wrapper is not None:
                valid = (valid and isinstance(wrapper, dict) and isinstance(wrapper.get("path"), str)
                         and classifier.classify(wrapper["path"]).scope == selected_scope)
            if not valid:
                ui_diagnostics.append({"code": "UI_CONTEXT_SCOPE_UNPROVEN", "path": fact.get("path"),
                    "source": fact["source"], "target": fact["target"], "context_id": context_id,
                    "reason": "UI handler and wrapper proof must belong to the selected classified scope and rule."})
                continue
        relation(fact["source"], fact["target"], fact["kind"], fact, fact.get("evidence_kind", "SYMBOL_RESOLVED"))
    for diagnostic in response["diagnostics"]:
        if "CFG_UNSUPPORTED" not in diagnostic.get("code", ""):
            continue
        path = diagnostic.get("path") or diagnostic.get("source_file")
        if path not in file_nodes:
            continue
        c = classifier.classify(path)
        boundary = "boundary:" + digest({"diagnostic": diagnostic, "context": context_id})
        nodes[boundary] = Node(boundary, "unresolved_boundary", diagnostic["code"], path, scope=c.scope, role="unknown", origin=c.origin)
        relation(file_nodes[path], boundary, "unresolved_boundary", diagnostic, "UNRESOLVED")
    from .local_operations import annotated_bodies, materialize_operations
    verified_bodies, local_operations = annotated_bodies(response, selected_context)
    cfgs = [from_body(body) for body in verified_bodies]
    cfgs.extend(response.get("bytecode_cfgs", []))
    body_metadata = {b["method"]: b for b in response["bodies"]}
    for cfg in cfgs:
        source_fact = {**body_metadata.get(cfg["method"], {}).get("body", {}), "resolution_reason": "COMPILER_AST_IR", "representation": "SOURCE"}
        if cfg.get("representation") == "BYTECODE":
            source_fact = {"resolution_reason": "ASM_BYTECODE_INSTRUCTIONS", "representation": "BYTECODE",
                           "artifact_hashes": selected_context.get("bytecode_artifacts", [])}
            method = cfg["method"]
            if method in presence_accesses:
                operands = physical_field_operands(cfg, presence_hooks[method][0], selected_context,
                                                   symbols_by_id, presence_accesses[method])
                if operands is not None:
                    source_fact["physical_field_operands"] = operands
        cfg["evidence_ids"] = [proof(source_fact, "SYNTAX_CANDIDATE", source=cfg["method"], target=cfg["method"], relation="control_flow")]
    selected_context = {**selected_context, "project": response.get("project"), "coverage": response["coverage"], "status": response["status"],
                        "diagnostics": selected_context.get("diagnostics", []) + response["diagnostics"]}
    graph = KnowledgeGraph(3, base.root, base.generated_at, sorted(nodes.values(), key=lambda n: n.id),
        sorted(edges, key=lambda e: (e.source, e.kind, e.target, e.evidence_ids)), base.files,
        base.contexts + [selected_context], base.diagnostics + selected_context.get("diagnostics", []) + classifier.diagnostics + ui_diagnostics + [d for cfg in cfgs for d in cfg.get("diagnostics", [])],
        [evidence[i] for i in sorted(evidence)], metadata, call_sites, cfgs)
    from .return_flow import augment_return_flow
    graph = materialize_operations(graph, local_operations, selected_context)
    graph = augment_return_flow(graph, sanitize(response["bodies"]), selected_context)
    from .field_flow import augment_field_flow
    graph = augment_field_flow(graph, sanitize(response["bodies"]), selected_context)
    from .criteria_queries import capture_query_facts
    graph = capture_query_facts(graph, sanitize(response["bodies"]), selected_context)
    KnowledgeGraph.from_dict(graph.to_dict())
    return graph


def _stage_response(response, selected):
    """A matching digest does not substitute for worker/context validation."""
    validate_response(response, selected)
    if any(symbol.get('context_id') != selected['id'] for symbol in response['symbols']):
        raise WorkerError('Dangling/duplicate compiler symbol or context', 'INVALID_PROTOCOL')
    worker = selected['worker']
    if (response.get('status') not in {'COMPLETE', 'PARTIAL'}
            or not isinstance(response.get('coverage'), dict)
            or any(response.get(key) != worker.get(key)
                   for key in ('protocol_version', 'worker', 'compiler_version'))):
        raise WorkerError('Stage response does not match selected worker/context', 'INVALID_PROTOCOL')
    return response


def _stage_graph(payload, base, selected, response):
    graph = KnowledgeGraph.from_dict(payload)
    expected_ids = {c['id'] for c in base.contexts} | {selected['id']}
    if (graph.schema_version != 3 or graph.extraction_cache or graph.files != base.files
            or {c.get('id') for c in graph.contexts} != expected_ids
            or any(s.get('context_id') != selected['id'] for s in
                   [*graph.symbols, *graph.call_sites, *graph.cfgs])
            or any(e.evidence_kind == 'RUNTIME_OBSERVED' for e in graph.edges)):
        raise WorkerError('Stage graph has foreign facts/context', 'INVALID_PROTOCOL')
    current = next(c for c in graph.contexts if c.get('id') == selected['id'])
    derived = {'project': response.get('project'), 'coverage': response['coverage'],
               'status': response['status'],
               'diagnostics': selected.get('diagnostics', []) + response['diagnostics']}
    if any(current.get(key) != value for key, value in derived.items()):
        raise WorkerError('Stage graph differs from upstream worker result', 'INVALID_PROTOCOL')
    if any(item not in graph.diagnostics for item in [*base.diagnostics, *derived['diagnostics']]):
        raise WorkerError('Stage graph removed upstream diagnostic', 'INVALID_PROTOCOL')
    for key, value in selected.items():
        if key in {'project', 'framework_rule_versions', 'coverage', 'status', 'diagnostics'}:
            continue  # Exact project closure is validated before this stage.
        if current.get(key) != value:
            raise WorkerError('Stage graph input binding differs: ' + key, 'INVALID_PROTOCOL')
    if any(current.get('framework_rule_versions', {}).get(k) != v
           for k, v in selected.get('framework_rule_versions', {}).items()):
        raise WorkerError('Stage graph has different framework rules', 'INVALID_PROTOCOL')
    if any(c not in graph.contexts for c in base.contexts):
        raise WorkerError('Stage graph replaced source context', 'INVALID_PROTOCOL')
    graph.generated_at = base.generated_at
    return graph


def inspect_frontend(root: Path, *, tsconfig="tsconfig.json", scope="production", repo_id="local",
                     module="frontend", source_set="main", ui_framework=None, home=None,
                     timeout=120, cancel_file=None, publish=True, strict=False) -> dict:
    root = root.resolve()
    argv = command("typescript", home)
    meta = handshake(argv, cwd=root)
    meta["distribution"] = distribution("typescript", home)
    before = scan_repository(root)
    selected = context(root, before, "typescript", meta, repo_id=repo_id, module=module, source_set=source_set, scope=scope)
    preflight = request_worker(argv, {"operation": "project", "root": str(root), "tsconfig": tsconfig,
        "ui_framework": ui_framework, "context": selected}, cwd=root, timeout=timeout, cancel_file=cancel_file)

    def input_closure(project: dict) -> dict[str, str]:
        records = project.get("input_files") if isinstance(project, dict) else None
        if not isinstance(records, list):
            raise WorkerError("Malformed frontend compiler input closure", "INVALID_PROTOCOL")
        inputs = {}
        for record in records:
            path = record.get("path") if isinstance(record, dict) else None
            checksum = record.get("sha256") if isinstance(record, dict) else None
            if (not isinstance(path, str) or not Path(path).is_absolute() or path in inputs
                    or not isinstance(checksum, str) or len(checksum) != 64
                    or any(character not in "0123456789abcdef" for character in checksum)):
                raise WorkerError("Malformed frontend compiler input closure", "INVALID_PROTOCOL")
            inputs[path] = checksum
        return inputs

    from .typescript_snapshot import replay as replay_typescript, validate_capture
    if "input_discovery" in preflight.get("project", {}):
        validate_capture(preflight["project"])
    if ui_framework == "react" and (not isinstance(preflight.get("project", {}).get("ui_adapters"), list) or any(not isinstance(adapter, dict) or adapter.get("rule") != UI_RULE_VERSION for adapter in preflight["project"]["ui_adapters"])):
        raise WorkerError("TypeScript worker lacks versioned UI adapter snapshot; prepare the supported distribution", "INVALID_PROTOCOL")
    preflight_inputs = input_closure(preflight.get("project"))
    selected = context(root, before, "typescript", meta, repo_id=repo_id, module=module, source_set=source_set, scope=scope,
                       build_context={"project": preflight["project"], "tsconfig": tsconfig, "ui_framework": ui_framework,
                                      "framework_rule_versions": {"react": UI_RULE_VERSION} if ui_framework == "react" else {}})
    from .extraction_cache import InspectionStages, graph_payload
    stages = InspectionStages(root, selected, argv, timeout=timeout, cancel_file=cancel_file)
    response = stages.run('worker-analysis', lambda: sanitize(request_worker(argv,
        {"operation": "analyze", "root": str(root), "tsconfig": tsconfig,
         "ui_framework": ui_framework, "context": selected}, cwd=root, timeout=timeout,
        cancel_file=cancel_file)), lambda value: _stage_response(value, selected))
    if input_closure(response.get("project")) != preflight_inputs:
        raise WorkerError("Frontend compiler input closure changed between preflight and analysis", "STALE")
    for path, expected in preflight_inputs.items():
        try:
            actual = file_hash(Path(path))
        except OSError as error:
            raise WorkerError("Frontend compiler inputs changed between preflight and analysis", "STALE") from error
        if actual != expected:
            raise WorkerError("Frontend compiler inputs changed between preflight and analysis", "STALE")
    if response["project"].get("input_discovery") != preflight["project"].get("input_discovery"):
        raise WorkerError("Frontend compiler discovery changed between preflight and analysis", "STALE")
    scoped = selected.get("source_snapshot_version") == "typescript-input-discovery-1"
    if scoped:
        replay_typescript(root, response["project"])
    if response["project"]["compiler_options"] != preflight["project"]["compiler_options"]:
        raise WorkerError("Frontend compiler options changed", "STALE")
    if response["project"].get("ui_adapters") != preflight["project"].get("ui_adapters"):
        raise WorkerError("Frontend UI adapter inputs changed", "STALE")
    if response["project"].get("project_graph") != preflight["project"].get("project_graph"):
        raise WorkerError("Frontend project reference graph changed", "STALE")
    model = {"source_sets": [{"module": module, "id": source_set, "scope": scope,
                              "files": [f["path"] for f in response["project"]["program_files"]]}]}
    after = scan_repository(root)
    if scoped:
        if digest(Classifier(root).config) != selected["classification_override_hash"]:
            raise WorkerError("Classifier configuration changed during frontend analysis", "STALE")
    elif before.files != after.files or before.contexts != after.contexts:
        raise WorkerError("Source/config snapshot changed during frontend analysis", "STALE")
    model_base = scan_repository(root, project_model=model, strict=strict)
    graph = stages.run('compiler-graph',
        lambda: graph_payload(graph_from_response(root, model_base, response, selected, project_model=model)),
        lambda value: _stage_graph(value, model_base, selected, response), base=model_base, upstream=response)
    result = {"status": "PARTIAL" if graph.diagnostics or response["status"] == "PARTIAL" else "COMPLETE_WITHIN_SUPPORTED_MATRIX",
              "mode": selected["mode"], "context": selected, "coverage": response["coverage"],
              "diagnostics": graph.diagnostics, "graph": graph.to_dict()}
    if strict and result["status"] == "PARTIAL":
        return {**result, "cache": stages.report(), "exit_code": 4}
    for item in response.get("project", {}).get("input_files", []):
        if file_hash(Path(item["path"])) != item["sha256"]:
            raise WorkerError("Frontend compiler input changed before publishing", "STALE")
    final = scan_repository(root)
    if scoped:
        replay_typescript(root, response["project"])
        if digest(Classifier(root).config) != selected["classification_override_hash"]:
            raise WorkerError("Classifier configuration changed before publishing", "STALE")
    elif final.files != before.files or final.contexts != before.contexts:
        raise WorkerError("Source/config snapshot changed before publishing", "STALE")
    if any(file_hash(Path(item["path"])) != item["sha256"] for item in meta["distribution"]):
        raise WorkerError("Worker distribution changed before publishing", "STALE")
    def final_guard():
        stages.guard()
        from .graph_provider import validate_context_snapshot
        validate_context_snapshot(root, selected)
        if (distribution('typescript', home) != meta['distribution']
                or graph_payload(scan_repository(root, project_model=model, strict=strict)) != graph_payload(model_base)):
            raise WorkerError('Worker distribution or source-stage inputs changed before commit', 'STALE')
        for captured in graph.contexts:
            if captured.get('analyzer_version') and captured.get('freshness') != 'STALE':
                validate_context_snapshot(root, captured)
    final_guard()
    if publish:
        from .graph_provider import merge_compiler_context
        previous = graph_revision(root)
        graph = merge_compiler_context(root, stages.attach(graph), selected)
        save_graph(graph, root, before_replace=final_guard, expected_revision=previous)
    return {**result, "graph": graph.to_dict(), "cache": stages.report(), "exit_code": 0}


def inspect_jvm(root: Path, *, classpath: list | None = None, bytecode_roots: list | None = None,
                scope="production", repo_id="local", module="root", source_set="main", home=None,
                timeout=120, cancel_file=None, project_model=None, build_context=None,
                publish=True, strict=False, sources=None, java_release=21,
                kotlin_backend="k1", kotlin_version="2.1.10") -> dict:
    root = root.resolve()
    if not isinstance(kotlin_backend, str) or kotlin_backend not in {"k1", "k2"} or kotlin_version != "2.1.10":
        raise AnalysisError("Unsupported Kotlin backend/version; supported: k1 compatibility or K2 Analysis API, compiler 2.1.10")
    if build_context is not None and not isinstance(build_context, dict):
        raise AnalysisError("Kotlin build context must be an object")
    compiler_options = (build_context or {}).get("compiler_options", {})
    if not isinstance(compiler_options, dict) or not isinstance(compiler_options.get("kotlin", {}), dict):
        raise AnalysisError("Kotlin compiler options must be an object")
    kotlin_options = compiler_options.get("kotlin", {})
    if kotlin_backend == "k2" and kotlin_options.get("compiler_version") is not None and kotlin_options.get("compiler_version") != "2.1.10":
        raise AnalysisError("K2 Analysis API supports compiler 2.1.10 only; imported compiler version differs")
    if kotlin_backend == "k2":
        for name, supported in (("language_version", "2.1"), ("api_version", "2.1"), ("jvm_target", "21")):
            if kotlin_options.get(name) is not None and kotlin_options.get(name) != supported:
                raise AnalysisError("Unsupported K2 captured option: " + name + "; supported value: " + supported)
        if any(kotlin_options.get(name) for name in ("free_args", "plugins", "plugin_options", "plugin_artifacts", "opt_in", "progressive")):
            raise AnalysisError("Unsupported K2 compiler flags/plugins; this backend does not silently ignore captured options")
    allow_stale_peer = (publish and project_model and project_model.get('source_sets')
                        and build_context is None and sources is None and not bytecode_roots)
    argv = command("jvm", home, kotlin_backend=kotlin_backend)
    meta = handshake(argv, cwd=root)
    expected_backend = "k2-analysis-api-2.1.10-v1" if kotlin_backend == "k2" else "k1-compat-1"
    # Legacy protocol-v1 K1 distributions remain readable; K2 requires an exact
    # handshake and must never silently execute a K1 distribution.
    if (kotlin_backend == "k2" or meta.get("kotlin_backend")) and meta.get("kotlin_backend") != expected_backend:
        raise WorkerError("Worker Kotlin backend differs from explicit selection", "INVALID_PROTOCOL")
    meta["distribution"] = distribution("jvm", home, kotlin_backend=kotlin_backend)
    base = scan_repository(root, project_model=project_model, strict=strict)
    memberships = None
    if (project_model or {}).get("source_sets"):
        memberships = {item["module"] + ":" + item["id"]
                       for item in _selected_jvm_source_sets(project_model, module, source_set)}
    available = {n.path for n in base.nodes if n.kind == "file" and n.scope == scope
                 and Path(n.path).suffix in {".java", ".kt"}
                 and (memberships is None or memberships.intersection(n.build_membership))}
    if sources is not None and (not isinstance(sources, list)
                                or any(not isinstance(p, str) or p not in available for p in sources)):
        raise AnalysisError("Compiler inputs absent from selected source-set scope")
    sources = sorted(available if sources is None else set(sources))
    unsupported = unsupported_kotlin_source(base.raw_file_hashes, sources)
    if unsupported is not None:
        raise WorkerError("Selected Kotlin source uses unsupported raw byte coordinates: " + unsupported,
                          "INVALID_PROTOCOL")
    if type(java_release) is not int or not 8 <= java_release <= 21:
        raise AnalysisError("Unsupported Java release; worker accepts release 8 through 21; only release 21 integration fixture is verified")
    entries = []
    for item in classpath or []:
        entry = {"path": item} if isinstance(item, str) else dict(item)
        entry["path"] = str(Path(entry["path"]).resolve())
        if "realm" in entry:
            realm = entry["realm"]
            if not isinstance(realm, dict) or any(not isinstance(realm.get(k), str) for k in ("repo_id", "module", "source_set")):
                raise AnalysisError("Invalid classpath artifact realm")
            if scope == "production" and realm.get("scope") in {"test", "test_fixture"}:
                raise AnalysisError("Classpath realm conflicts with selected source-set scope")
            entry["realm"] = {"scope": scope, **realm}
        actual = artifact_hash(Path(entry["path"]))
        if entry.get("sha256") is not None and entry["sha256"] != actual:
            raise AnalysisError("Classpath artifact checksum mismatch")
        entry["sha256"] = actual
        entries.append(entry)
    if bytecode_roots and (not build_context or build_context.get("freshness") != "EXECUTION_BOUND" or not build_context.get("build_id")):
        raise AnalysisError("Bytecode requires a validated execution-bound build manifest; use build-import")
    selected = context(root, base, "jvm", meta, repo_id=repo_id, module=module, source_set=source_set, scope=scope,
                       build_context={**(build_context or {}), "classpath": entries, "project_model": project_model,
                                      "compiler_inputs": sources, "java_release": java_release,
                                      "kotlin_backend": kotlin_backend, "kotlin_version": kotlin_version,
                                      "bytecode_artifacts": [{"path": str(Path(p if isinstance(p, str) else p["path"]).resolve()), "sha256": artifact_hash(Path(p if isinstance(p, str) else p["path"]))} for p in bytecode_roots or []]})
    from .extraction_cache import InspectionStages, graph_payload
    stages = InspectionStages(root, selected, argv, timeout=timeout, cancel_file=cancel_file)
    response = stages.run('worker-analysis', lambda: sanitize(request_worker(argv,
        {"operation": "analyze", "root": str(root), "context": selected,
         "sources": sources, "classpath": entries, "bytecode_roots": bytecode_roots or [], "java_release": java_release,
         "kotlin_backend": kotlin_backend, "kotlin_version": kotlin_version},
        cwd=root, timeout=timeout, cancel_file=cancel_file)), lambda value: _stage_response(value, selected))
    if (kotlin_backend == "k2" or response.get("kotlin_backend")) and response.get("kotlin_backend") != expected_backend:
        raise WorkerError("Worker analysis backend differs from selected context", "INVALID_PROTOCOL")
    after = scan_repository(root, project_model=project_model)
    if (source_snapshot(root, after, selected) != selected["source_files"]
            or jpa_xml_input_snapshot(root, selected) != selected.get("jpa_xml_inputs")
            or base.contexts != after.contexts
            or any(artifact_hash(Path(e["path"])) != e["sha256"] for e in entries + selected.get("bytecode_artifacts", []))):
            raise WorkerError("Source/config/classpath snapshot changed during JVM analysis", "STALE")
    graph = stages.run('compiler-graph',
        lambda: graph_payload(graph_from_response(root, base, response, selected, project_model=project_model)),
        lambda value: _stage_graph(value, base, selected, response), base=base, upstream=response)
    # Framework rules consume the compiler-resolved graph; they never replace
    # or upgrade a worker fact.  Keep this phase in the explicit inspection
    # workflow so scan/build/feature commands remain offline and source-only.
    def augment():
        from .framework import augment_framework_graph
        from .http_execution import augment_http_graph
        from .kafka_code import augment_kafka_graph
        from .kafka_retry import augment_retry_graph
        augmented = augment_framework_graph(root, graph, selected)
        augmented = augment_http_graph(augmented, response["bodies"], selected)
        augmented = augment_kafka_graph(root, augmented, response["bodies"], selected)
        selected_retry = next(c for c in augmented.contexts if c.get("id") == selected["id"])
        return graph_payload(augment_retry_graph(root, augmented, selected_retry))
    graph = stages.run('framework-graph', augment,
        lambda value: _stage_graph(value, base, selected, response), base=graph, upstream=response)
    result = {"status": "PARTIAL" if graph.diagnostics or response["status"] == "PARTIAL" else "COMPLETE_WITHIN_SUPPORTED_MATRIX",
              "mode": selected["mode"], "context": selected, "coverage": response["coverage"], "diagnostics": graph.diagnostics,
              "graph": graph.to_dict()}
    if strict and result["status"] == "PARTIAL":
        return {**result, "cache": stages.report(), "exit_code": 4}
    from .kafka_code import validate_analysis
    for captured in graph.contexts:
        if captured.get("id") == selected["id"]:
            validate_analysis(root, captured)
    final = scan_repository(root, project_model=project_model)
    if (source_snapshot(root, final, selected) != selected["source_files"]
            or jpa_xml_input_snapshot(root, selected) != selected.get("jpa_xml_inputs")
            or final.contexts != base.contexts
            or any(artifact_hash(Path(e["path"])) != e["sha256"] for e in entries + selected.get("bytecode_artifacts", []))):
        raise WorkerError("Source/config/classpath snapshot changed before publishing", "STALE")
    if any(file_hash(Path(item["path"])) != item["sha256"] for item in meta["distribution"]):
        raise WorkerError("Worker distribution changed before publishing", "STALE")
    retired_paths = set()
    deleted_paths = set()

    def final_guard():
        stages.guard()
        from .graph_provider import _compiler_input_absent, validate_context_snapshot
        if any(not _compiler_input_absent(root, path) for path in deleted_paths):
            raise WorkerError('Deleted compiler input reappeared or became unavailable before commit', 'STALE')
        validate_context_snapshot(root, selected)
        current = scan_repository(root, project_model=project_model, strict=strict)
        raw_before, raw_now = base.raw_file_hashes, current.raw_file_hashes
        retired_changed = retired_paths and (raw_before is None or raw_now is None or any(
            raw_before.get(path) != raw_now.get(path) for path in retired_paths))
        if (distribution('jvm', home, kotlin_backend=kotlin_backend) != meta['distribution']
                or graph_payload(current) != graph_payload(base)
                or retired_changed):
            raise WorkerError('Worker distribution or source-stage inputs changed before commit', 'STALE')
        for captured in graph.contexts:
            if captured.get('analyzer_version') and captured.get('freshness') != 'STALE':
                validate_context_snapshot(root, captured)
    final_guard()
    if publish:
        from .graph_provider import _prepare_compiler_context, merge_compiler_context
        previous = graph_revision(root)
        graph = stages.attach(graph)
        if allow_stale_peer:
            graph, retired_paths, deleted_paths = _prepare_compiler_context(root, graph, selected, initial_scan=base)
        else:
            graph = merge_compiler_context(root, graph, selected)
        save_graph(graph, root, before_replace=final_guard, expected_revision=previous)
    return {**result, "graph": graph.to_dict(), "cache": stages.report(), "exit_code": 0}

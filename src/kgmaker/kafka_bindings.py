"""Bounded, declared Kafka configuration identities; never a transport client."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .analysis_model import AnalysisError, ID_PATTERN, digest, safe_path
from .classification import Classifier
from .model import Edge, Node
from .spring_conditions import _profile

VERSION = "kafka-binding-2"
MAX_BYTES = 1_000_000
MAX_BINDINGS = 512
TOPIC = re.compile(r"[A-Za-z0-9._-]{1,249}\Z")


def _identifier(value):
    return isinstance(value, str) and len(value) <= 128 and ID_PATTERN.fullmatch(value)


def _path(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ".." in Path(relative).parts:
        raise AnalysisError("Invalid Kafka artifact path")
    from .scanner import SENSITIVE_NAMES
    if any(part.startswith(".") or part.lower() in SENSITIVE_NAMES or any(t in part.lower() for t in (".pem", ".key", "secret", "credential")) for part in Path(relative).parts):
        raise AnalysisError("Kafka artifacts must not use hidden/sensitive paths")
    path = safe_path(root, relative)
    lexical = root / relative
    if any(part.is_symlink() for part in (lexical, *lexical.parents)):
        raise AnalysisError("Kafka artifacts must not use symlinks")
    if path.exists() and (not path.is_file() or path.stat().st_size > MAX_BYTES):
        raise AnalysisError("Kafka artifact is not a bounded regular file")
    return path


def validate(workspace):
    config = workspace.get("kafka_bindings")
    if config is None:
        return
    if (not isinstance(config, dict) or set(config) != {"schema_version", "clusters", "bindings"}
            or type(config["schema_version"]) is not int or config["schema_version"] != 1
            or not isinstance(config["clusters"], list) or len(config["clusters"]) > 128
            or not isinstance(config["bindings"], list) or len(config["bindings"]) > MAX_BINDINGS):
        raise AnalysisError("Invalid Kafka binding schema/budget")
    clusters = set()
    for item in config["clusters"]:
        if not isinstance(item, dict) or set(item) != {"id"} or not _identifier(item["id"]) or item["id"] in clusters:
            raise AnalysisError("Invalid/duplicate declared Kafka cluster identity")
        clusters.add(item["id"])
    roots = {r["id"]: Path(r["_root"]) for r in workspace["repositories"]}
    services = {s["id"]: s for s in workspace.get("services", [])}
    fields = {"id", "repo_id", "service_id", "module", "source_set", "scope", "context_id", "binding",
              "direction", "profiles", "config_files", "binders", "contract", "payload"}
    ids = set()
    from .workspace import resolve_service_ownership
    for binding in config["bindings"]:
        if (not isinstance(binding, dict) or set(binding) != fields
                or not _identifier(binding["id"]) or binding["id"] in ids
                or not isinstance(binding["repo_id"], str) or binding["repo_id"] not in roots
                or not isinstance(binding["service_id"], str) or binding["service_id"] not in services
                or not all(_identifier(binding[k]) for k in ("module", "source_set", "binding"))
                or not isinstance(binding["scope"], str) or binding["scope"] not in {"production", "test", "test_fixture", "unknown"}
                or not isinstance(binding["direction"], str) or binding["direction"] not in {"producer", "consumer"}
                or binding["context_id"] is not None and not isinstance(binding["context_id"], str)
                or binding["payload"] is not None and not _identifier(binding["payload"])):
            raise AnalysisError("Invalid Kafka binding declaration")
        ids.add(binding["id"])
        service = services[binding["service_id"]]
        if service.get("transport") != "kafka" or service["backend_repo"] != binding["repo_id"]:
            raise AnalysisError("Kafka binding service/repository mismatch")
        profiles = binding["profiles"]
        if profiles is not None and (not isinstance(profiles, list) or len(profiles) > 32
                or any(not _identifier(p) for p in profiles) or len(set(profiles)) != len(profiles)):
            raise AnalysisError("Invalid Kafka profile selection")
        binders = binding["binders"]
        if (not isinstance(binders, dict) or len(binders) > 128
                or any(not _identifier(k) or not isinstance(v, str) or v not in clusters for k, v in binders.items())):
            raise AnalysisError("Invalid Kafka binder/cluster declaration")
        contract = binding["contract"]
        if (not isinstance(contract, dict) or set(contract) != {"repo_id", "path", "release"}
                or not isinstance(contract["repo_id"], str) or contract["repo_id"] not in roots
                or contract["release"] is not None and not _identifier(contract["release"])
                or {k: contract[k] for k in ("repo_id", "path")} != service["contract"]):
            raise AnalysisError("Kafka contract/release must match the declared service contract")
        _path(roots[contract["repo_id"]], contract["path"])
        files = binding["config_files"]
        if not isinstance(files, list) or not 1 <= len(files) <= 32:
            raise AnalysisError("Invalid Kafka configuration file budget")
        seen, profiled = set(), False
        for item in files:
            if (not isinstance(item, dict) or set(item) != {"path", "profile"}
                    or not isinstance(item["path"], str) or item["path"] in seen
                    or item["profile"] is not None and (not isinstance(item["profile"], str) or not 0 < len(item["profile"]) <= 4096)):
                raise AnalysisError("Invalid Kafka configuration/profile declaration")
            if item["profile"] is None and profiled:
                raise AnalysisError("Kafka base configuration must precede profile overrides")
            seen.add(item["path"]); profiled |= item["profile"] is not None
            _path(roots[binding["repo_id"]], item["path"])
            ownership = resolve_service_ownership({"repo_id": binding["repo_id"], "module": binding["module"],
                "path": item["path"], "context_id": "kafka-declaration:" + binding["id"]},
                workspace.get("service_ownership"), context_id="kafka-declaration:" + binding["id"])
            if ownership["status"] != "RESOLVED" or ownership["owner_id"] != binding["service_id"]:
                raise AnalysisError("Kafka binding requires unique explicit service ownership")


def _snapshot(root, path):
    target = _path(root, path)
    if not target.is_file():
        return None, None
    with target.open("rb") as stream:
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise AnalysisError("Kafka artifact grew beyond its budget", 3)
    import hashlib
    return content, hashlib.sha256(content).hexdigest()


def _properties(content):
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeError:
        return {}, ["CONFIG_ENCODING_UNSUPPORTED"]
    if len(lines) > 10_000:
        return {}, ["CONFIG_LINE_BUDGET"]
    result, reasons = {}, []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)\s*[=:]\s*(.*?)\s*", line)
        if not match or "\\" in line:
            reasons.append("CONFIG_SYNTAX_UNSUPPORTED")
            continue
        key, value = match.groups()
        if key in result:
            reasons.append("DUPLICATE_CONFIG_PROPERTY")
        result[key] = value
    return result, reasons


def sensitive_property(key):
    """Conservative property-key privacy boundary, shared by lookup/projection."""
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(word in normalized for word in ("password", "passwd", "secret", "credential",
        "authorization", "apikey", "token", "username", "jaas", "bootstrapservers"))


def project_captured_context(context):
    """Redact only the public view; original captured inputs/hashes stay intact."""
    import copy
    from .inspection import sanitize
    result = copy.deepcopy(context)
    properties = context.get("spring_properties")
    if not isinstance(properties, dict):
        return result
    sanitized = sanitize(properties)
    projected = {key: "<redacted>" if sensitive_property(key) else sanitized[key] for key in properties}
    if projected != properties:
        result["spring_properties"] = projected
        result["spring_properties_projection"] = {"redacted": True, "sha256": digest(properties),
            "original_context_id": context["id"]}
    return result


def _resolve(key, properties):
    seen = set()
    for _ in range(16):
        # Never fetch a sensitive value, including through a benign alias chain.
        if sensitive_property(key) or key in seen:
            return None
        seen.add(key)
        value = properties.get(key)
        if not isinstance(value, str) or len(value) > 4096:
            return None
        match = re.fullmatch(r"\$\{([A-Za-z0-9_.-]+)\}", value)
        if match:
            key = match.group(1)
        else:
            return value if "${" not in value and "#{" not in value else None
    return None


def _context(binding, graph, root):
    contexts = [c for c in graph.contexts if c.get("analyzer_version") and c.get("language") == "jvm"]
    matches = [c for c in contexts if all(c.get(k) == binding[k] for k in ("module", "source_set", "scope"))]
    selected = binding["context_id"]
    if selected is not None:
        matches = [c for c in matches if c["id"] == selected]
        if len(matches) != 1:
            raise AnalysisError("Unknown or incompatible Kafka compiler context")
    elif len(matches) > 1:
        raise AnalysisError("Ambiguous Kafka compiler context")
    if not matches:
        return None, ["COMPILER_CONTEXT_UNAVAILABLE"] if contexts else []
    context = matches[0]
    if context.get("repo_id") not in {binding["repo_id"], "local"}:
        raise AnalysisError("Kafka compiler context repository mismatch")
    from .graph_provider import validate_context_snapshot
    from .worker_protocol import WorkerError
    try:
        validate_context_snapshot(root, context)
    except WorkerError:
        return context, ["COMPILER_CONTEXT_STALE"]
    if context.get("spring_profiles") != binding["profiles"]:
        raise AnalysisError("Kafka profile selection disagrees with compiler context")
    return context, []


def build_links(workspace, graphs):
    """Compose static configured bindings in the existing workspace graph."""
    if workspace.get("kafka_bindings") is None:
        return [], [], [], [], [], None
    roots = {r["id"]: Path(r["_root"]) for r in workspace["repositories"]}
    from .workspace import qualified, source_key
    nodes, edges, evidence, contexts, diagnostics, rows, snapshots = {}, [], [], [], [], [], {}
    for binding in workspace["kafka_bindings"]["bindings"]:
        repo, reasons, properties = binding["repo_id"], [], {}
        if repo not in graphs:
            diagnostics.append({"code": "KAFKA_BINDING_UNKNOWN", "binding_id": binding["id"], "reasons": ["CHECKOUT_UNAVAILABLE"]})
            continue
        selected, context_reasons = _context(binding, graphs[repo], roots[repo])
        reasons.extend(context_reasons)
        classifier = Classifier(roots[repo], model=selected.get("project_model") if selected else None)
        if binding["profiles"] is None:
            reasons.append("PROFILE_INPUTS_UNAVAILABLE")
        inputs = {}
        for config in binding["config_files"]:
            content, checksum = _snapshot(roots[repo], config["path"])
            snapshots[(repo, config["path"])] = checksum
            inputs[source_key(repo, config["path"])] = checksum
            classification = classifier.classify(config["path"])
            expected_membership = binding["module"] + ":" + binding["source_set"]
            conventional = (binding["module"] == "root" and binding["source_set"] in {"main", "test"}
                            and config["path"].startswith("src/" + binding["source_set"] + "/"))
            if any(d.get("path") == config["path"] for d in classifier.diagnostics):
                reasons.append("CONFIG_CLASSIFICATION_CONFLICT")
            if classification.scope != binding["scope"] or (classification.build_membership and expected_membership not in classification.build_membership) or not classification.build_membership and not conventional:
                reasons.append("CONFIG_SCOPE_UNPROVEN")
            active = True
            if config["profile"] is not None:
                if binding["profiles"] is None:
                    reasons.append("PROFILE_INPUTS_UNAVAILABLE"); active = False
                else:
                    try:
                        active = _profile(config["profile"], set(binding["profiles"] or ["default"]))
                    except (ValueError, RecursionError):
                        reasons.append("PROFILE_EXPRESSION_UNSUPPORTED"); active = False
            if not active:
                continue
            if content is None:
                reasons.append("CONFIG_FILE_UNAVAILABLE")
            elif Path(config["path"]).suffix != ".properties":
                reasons.append("CONFIG_FORMAT_UNSUPPORTED")
            else:
                values, gaps = _properties(content)
                properties.update(values); reasons.extend(gaps)
        if selected is not None:
            overrides = selected.get("spring_properties")
            if isinstance(overrides, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in overrides.items()):
                properties.update(overrides)
            elif overrides is not None:
                reasons.append("CONTEXT_PROPERTIES_UNSUPPORTED")
        prefix = "spring.cloud.stream.bindings." + binding["binding"]
        topic = _resolve(prefix + ".destination", properties)
        if topic is None or not TOPIC.fullmatch(topic) or topic in {".", ".."}:
            topic = None; reasons.append("TOPIC_UNRESOLVED")
        binder = _resolve(prefix + ".binder", properties)
        cluster = binding["binders"].get(binder)
        if cluster is None:
            reasons.append("CLUSTER_UNRESOLVED")
        contract = binding["contract"]
        content, checksum = _snapshot(roots[contract["repo_id"]], contract["path"])
        snapshots[(contract["repo_id"], contract["path"])] = checksum
        inputs[source_key(contract["repo_id"], contract["path"])] = checksum
        try:
            if content is None or not isinstance(json.loads(content), dict):
                raise ValueError()
        except (ValueError, UnicodeError, RecursionError):
            reasons.append("CONTRACT_UNAVAILABLE_OR_UNSUPPORTED")
        if contract["release"] is None:
            reasons.append("RELEASE_UNAVAILABLE")
        if binding["payload"] is None:
            reasons.append("PAYLOAD_DECLARATION_UNAVAILABLE")
        status = "UNKNOWN" if reasons else "RESOLVED"
        context_id = "workspace:kafka-context:" + digest({"workspace": workspace["workspace_id"], "binding": binding,
            "inputs": inputs, "version": VERSION, "selected": selected.get("id") if selected else None})
        contexts.append({"id": context_id, "mode": "SOURCE_ONLY", "scope": binding["scope"], "coverage": "PARTIAL",
            "freshness": "CONTENT_VERIFIED", "origin_trust": "WORKSPACE_DECLARATION", "repo_id": repo,
            "module": binding["module"], "source_set": binding["source_set"], "source_files": inputs,
            "selected_compiler_context": qualified(repo, selected["id"]) if selected else None,
            "kafka_binding_version": VERSION})
        identity = "workspace:kafka-binding:" + digest({"context": context_id, "declaration": binding["id"]})
        metadata = {"binding_id": binding["id"], "repo_id": repo, "service_id": binding["service_id"],
            "module": binding["module"], "source_set": binding["source_set"], "direction": binding["direction"],
            "status": status, "reasons": sorted(set(reasons)), "topic": topic, "cluster_id": cluster,
            "cluster_origin": "DECLARED", "contract_sha256": checksum, "release": contract["release"],
            "payload": binding["payload"], "payload_origin": "DECLARED", "delivery": "NOT_OBSERVED",
            "code_binding": "UNPROVEN", "input_files": inputs, "context_id": context_id, "kafka_binding_version": VERSION}
        nodes[identity] = Node(identity, "kafka_binding", binding["id"], "@workspace/manifest.json", scope=binding["scope"],
                               role="contract", origin="generated", metadata=metadata)
        row = {"id": identity, **metadata}; rows.append(row)
        if status == "UNKNOWN":
            diagnostics.append({"code": "KAFKA_BINDING_UNKNOWN", "binding_id": binding["id"], "reasons": metadata["reasons"]})
            continue
        topic_id = "workspace:kafka-topic:" + digest({"workspace": workspace["workspace_id"], "cluster": cluster,
            "topic": topic, "contract": checksum, "release": contract["release"], "scope": binding["scope"]})
        row["topic_id"] = topic_id
        nodes.setdefault(topic_id, Node(topic_id, "kafka_topic", topic, "@workspace/manifest.json", scope=binding["scope"],
            role="contract", origin="generated", metadata={"cluster_id": cluster, "cluster_origin": "DECLARED",
                "contract_sha256": checksum, "release": contract["release"], "delivery": "NOT_OBSERVED", "kafka_binding_version": VERSION}))
        relation = "produces" if binding["direction"] == "producer" else "consumes"
        proof = {"kind": "FRAMEWORK_DERIVED", "source": identity, "target": topic_id, "relation": relation,
                 "source_file": "@workspace/manifest.json", "context_ids": [context_id], "input_files": inputs,
                 "manifest_sha256": workspace["_manifest_hash"], "detail": "Declared configuration binding; no transport executed."}
        proof["id"] = "evidence:" + digest(proof); evidence.append(proof)
        edges.append(Edge(identity, topic_id, relation, proof["detail"], evidence_kind="FRAMEWORK_DERIVED",
                          context_ids=(context_id,), evidence_ids=(proof["id"],), source_file="@workspace/manifest.json"))
    for producer in rows:
        for consumer in rows:
            if (producer["status"] != "RESOLVED" or consumer["status"] != "RESOLVED"
                    or producer["direction"] != "producer" or consumer["direction"] != "consumer"
                    or producer["topic_id"] != consumer["topic_id"]):
                continue
            proof = {"kind": "FRAMEWORK_DERIVED", "source": producer["id"], "target": consumer["id"],
                "relation": "kafka_binding_match", "source_file": "@workspace/manifest.json",
                "context_ids": [producer["context_id"], consumer["context_id"]], "manifest_sha256": workspace["_manifest_hash"],
                "input_files": {**producer["input_files"], **consumer["input_files"]},
                "detail": "Exact declared cluster/topic/contract SHA/release; delivery is not observed."}
            proof["id"] = "evidence:" + digest(proof); evidence.append(proof)
            edges.append(Edge(producer["id"], consumer["id"], "kafka_binding_match", proof["detail"],
                evidence_kind="FRAMEWORK_DERIVED", context_ids=tuple(proof["context_ids"]),
                evidence_ids=(proof["id"],), source_file="@workspace/manifest.json"))
    report = {"schema_version": 1, "version": VERSION, "bindings": rows,
              "snapshots": [{"repo_id": repo, "path": path, "sha256": checksum} for (repo, path), checksum in sorted(snapshots.items())]}
    return list(nodes.values()), edges, evidence, contexts, diagnostics, report


def validate_snapshot(workspace, report):
    if report is None:
        return
    roots = {r["id"]: Path(r["_root"]) for r in workspace["repositories"]}
    for item in report["snapshots"]:
        _, checksum = _snapshot(roots[item["repo_id"]], item["path"])
        if checksum != item["sha256"]:
            raise AnalysisError("Kafka artifact changed during workspace snapshot", 3)

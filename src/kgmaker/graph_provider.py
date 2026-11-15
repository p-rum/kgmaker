"""Offline graph refresh preserving validated compiler evidence in the shared store."""
from pathlib import Path
import shlex

from .model import KnowledgeGraph
from .store import load_graph
from .worker_protocol import WorkerError


def _compiler_contexts(graph: KnowledgeGraph, *, include_stale: bool = True) -> list[dict]:
    return [context for context in graph.contexts
            if context.get("analyzer_version")
            and (include_stale or context.get("freshness") != "STALE")]


def view_context_fingerprint(graph: KnowledgeGraph | dict) -> str:
    """Fingerprint complete context inventory for derived-view invalidation.

    Context rows include selected and unselected compiler variants. Sorting by
    stable ID removes incidental storage ordering while retaining every captured
    context field, including freshness and rule/configuration snapshots.
    """
    from .analysis_model import digest

    contexts = graph.contexts if isinstance(graph, KnowledgeGraph) else graph.get("contexts", [])
    if not isinstance(contexts, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str)
            for item in contexts):
        raise ValueError("Invalid graph context inventory")
    return digest(sorted(contexts, key=lambda item: item["id"]))


def _inspection_command(context: dict) -> str:
    kind = "frontend" if context.get("language") == "typescript" else "code"
    values = ["kgmaker", "inspect", kind,
              "--repo-id", str(context.get("repo_id", "local")),
              "--module", str(context.get("module", "root")),
              "--source-set", str(context.get("source_set", "main")),
              "--scope", str(context.get("scope", "production"))]
    if kind == "frontend":
        values += ["--tsconfig", str(context.get("tsconfig", "tsconfig.json"))]
        if context.get("ui_framework"):
            values += ["--ui-framework", str(context["ui_framework"])]
    elif context.get("build_id"):
        values += ["--build-id", str(context["build_id"])]
        if context.get("build_context_id"):
            values += ["--context", str(context["build_context_id"])]
    else:
        for item in context.get("classpath", []):
            values += ["--classpath", item["path"]]
    if kind == "code" and context.get("kotlin_backend") == "k2":
        values += ["--kotlin-backend", "k2", "--kotlin-version", str(context.get("kotlin_version", "2.1.10"))]
    return shlex.join(values)


def _stale_context(context: dict, reason: str) -> dict:
    diagnostic = {
        "code": "STALE_COMPILER_CONTEXT",
        "reason": reason,
        "context_id": context["id"],
        "selection_key": _selection_key(context),
        "next_command": _inspection_command(context),
    }
    diagnostics = [item for item in context.get("diagnostics", [])
                   if item.get("code") != "STALE_COMPILER_CONTEXT"]
    return {**context, "freshness": "STALE", "status": "STALE",
            "diagnostics": [*diagnostics, diagnostic],
            "stale_reason": reason, "next_command": diagnostic["next_command"]}


def _selection_key(context: dict) -> str:
    recorded = context.get("selection_key")
    if isinstance(recorded, str) and context.get("language") != "typescript":
        return recorded
    from .analysis_model import digest
    payload = {key: context.get(key) for key in (
        "repo_id", "module", "source_set", "scope", "language", "build_context_id",
        "build_profiles", "spring_profiles", "config_fingerprint", "compiler_options",
        "manifest_hash", "toolchain", "dependency_model_hash", "generated_source_roots",
        "spring_properties", "spring_available_classes",
        "spring_component_packages",
        "framework_rule_versions",
        "ui_framework", "tsconfig", "database_id", "schema_stream_id",
        "persistence_unit", "naming_strategy",
    )}
    if context.get("language") == "typescript" and context.get("ui_framework") == "react" and "ui_adapters" in context.get("project", {}):
        payload["ui_adapters"] = context["project"]["ui_adapters"]
    if isinstance(payload.get("framework_rule_versions"), dict):
        # An additive HTTP capture layer replaces the same logical selection;
        # legacy contexts remain readable with HTTP coverage UNKNOWN.
        payload["framework_rule_versions"] = {key: value for key, value in payload["framework_rule_versions"].items() if key != "http"}
    if context.get("language") == "jvm":
        payload.update(persistence_schema=context.get("persistence_schema"), flyway_target=context.get("flyway_target"),
                       kotlin_backend=context.get("kotlin_backend"),
                       kotlin_version=context.get("kotlin_version"))
    if isinstance(recorded, str):
        # K2 briefly added two irrelevant None fields to frontend selectors.
        # Recognize that exact digest, without reinterpreting opaque variants.
        interim = digest({**payload, "kotlin_backend": None, "kotlin_version": None})
        if recorded != interim:
            return recorded
    return digest(payload)


def validate_context_snapshot(root: Path, context: dict) -> None:
    """Validate one captured context without executing a worker or build."""
    if context.get("freshness") == "STALE":
        raise WorkerError(
            "STALE_INDEX: " + str(context.get("stale_reason", "compiler context requires inspection"))
            + "; run `" + str(context.get("next_command", _inspection_command(context))) + "`",
            "STALE",
        )
    # Compare every captured source and classpath; timestamps never establish freshness.
    from .analysis_model import file_hash, safe_path
    from .inspection import artifact_hash
    if "return_flow_rule_version" in context:
        from .return_flow import VERSION as RETURN_VERSION
        if context["return_flow_rule_version"] != RETURN_VERSION:
            raise WorkerError("STALE_INDEX: return/consumer rules changed; inspect again", "STALE")

    if "field_flow_rule_version" in context:
        from .field_flow import VERSION as FIELD_VERSION
        if context["field_flow_rule_version"] != FIELD_VERSION:
            raise WorkerError("STALE_INDEX: field mapping rules changed; inspect again", "STALE")

    if "local_operation_rule_version" in context:
        from .local_operations import VERSION as LOCAL_OPERATION_VERSION
        if context["local_operation_rule_version"] != LOCAL_OPERATION_VERSION:
            raise WorkerError("STALE_INDEX: local operation rules changed; inspect again", "STALE")
    if context.get("language") == "typescript" and context.get("ui_framework") == "react":
        from .inspection import UI_RULE_VERSION
        if (context.get("framework_rule_versions", {}).get("react") != UI_RULE_VERSION
                or "ui_adapters" not in context.get("project", {})):
            raise WorkerError("STALE_INDEX: UI adapter rules changed; inspect frontend again", "STALE")
    if context.get("language") == "jvm":
        from .kafka_retry import VERSION as RETRY_VERSION, validate_analysis as validate_retry_analysis
        validate_retry_analysis(context)
        retry_rules = context.get("framework_rule_versions", {})
        if isinstance(retry_rules, dict) and "kafka_retry" in retry_rules and retry_rules["kafka_retry"] != RETRY_VERSION:
            raise WorkerError("STALE_INDEX: Kafka retry rule changed; inspect again", "STALE")
    if context.get("language") == "jvm" and "kafka_code_analysis" in context:
        from .kafka_code import validate_analysis
        validate_analysis(root, context)
    rules = context.get("framework_rule_versions")
    if context.get("language") == "jvm" and rules is not None and not isinstance(rules, dict):
        raise WorkerError("STALE_INDEX: malformed Spring rule snapshot", "STALE")
    if context.get("language") == "jvm" and isinstance(rules, dict) and "spring" in rules:
        from .framework import SPRING_RULE_VERSION
        from .spring_conditions import condition_inputs
        from .analysis_model import digest
        if context["framework_rule_versions"]["spring"] != SPRING_RULE_VERSION:
            raise WorkerError("STALE_INDEX: Spring condition rules changed; inspect again", "STALE")
        try:
            valid_conditions = context.get("spring_condition_inputs_hash") == digest(condition_inputs(context))
        except (ValueError, TypeError, RecursionError):
            valid_conditions = False
        if not valid_conditions:
            raise WorkerError("STALE_INDEX: Spring condition configuration changed; inspect again", "STALE")
    if context.get("language") == "jvm" and isinstance(rules, dict) and "jpa" in rules:
        from .framework import JPA_RULE_VERSION
        from .schema_replay import persistence_selection
        from .analysis_model import digest
        if rules['jpa'] != JPA_RULE_VERSION:
            raise WorkerError('STALE_INDEX: persistence realm rules changed; inspect again', 'STALE')
        try:
            valid_realm = context.get('persistence_selection_hash') == digest(persistence_selection(context))
        except (ValueError, TypeError, RecursionError):
            valid_realm = False
        if not valid_realm:
            raise WorkerError('STALE_INDEX: persistence selection changed; inspect again', 'STALE')

    if context.get("language") == "jvm" and isinstance(rules, dict) and "http" in rules:
        from .http_execution import VERSION as HTTP_VERSION
        from .analysis_model import digest
        expected_http = digest({'sources': context.get('http_config_provenance', {}),
                                'redacted': context.get('http_redacted_input_hash')})
        if rules['http'] != HTTP_VERSION or context.get('http_inputs_hash') != expected_http:
            raise WorkerError("STALE_INDEX: HTTP rule/configuration proof changed; inspect again", "STALE")
    options = (context.get("compiler_options") or {}).get("kotlin")
    if options is not None:
        from .analysis_model import AnalysisError
        from .build_model import validate_kotlin_options
        try:
            validate_kotlin_options(options)
        except AnalysisError as error:
            raise WorkerError("STALE_INDEX: invalid Kotlin configuration: " + str(error), "STALE") from error
        if context.get("selection_key") and context["selection_key"] != _selection_key(
                {key: value for key, value in context.items() if key != "selection_key"}):
            raise WorkerError("STALE_INDEX: Kotlin compiler context configuration changed", "STALE")
    scoped_typescript = context.get("source_snapshot_version") == "typescript-input-discovery-1"
    snapshot_version = context.get("source_snapshot_version")
    if context.get("language") == "jvm" and snapshot_version is not None \
            and (not isinstance(snapshot_version, str)
                 or snapshot_version not in {"selected-source-set-1", "selected-source-set-2"}):
        raise WorkerError("STALE_INDEX: unsupported JVM source snapshot version", "STALE")
    if isinstance(snapshot_version, str) and snapshot_version in {"selected-source-set-1", "selected-source-set-2"} \
            and context.get("language") != "jvm":
        raise WorkerError("STALE_INDEX: JVM source snapshot on a non-JVM context", "STALE")
    if context.get("source_snapshot_version") == "selected-source-set-2":
        from .inspection import jpa_xml_input_snapshot
        if context.get("jpa_xml_inputs") != jpa_xml_input_snapshot(root, context):
            raise WorkerError("STALE_INDEX: selected persistence XML inputs changed; inspect again", "STALE")
    elif context.get("language") == "jvm" and context.get("source_snapshot_version") == "selected-source-set-1":
        # Older JVM contexts did not capture mapping XML. Keep XML-free legacy
        # snapshots readable, but never trust one when a mapping input exists.
        from .inspection import jpa_xml_input_snapshot
        legacy_xml = jpa_xml_input_snapshot(root, context)
        if any(item.get("status") != "missing" for item in legacy_xml["inputs"]):
            raise WorkerError("STALE_INDEX: legacy JVM context has uncaptured persistence XML; inspect again", "STALE")
    elif context.get("language") == "jvm" and context.get("source_snapshot_version") is None:
        from .inspection import jpa_xml_input_snapshot
        legacy_xml = jpa_xml_input_snapshot(root, context)
        if any(item.get("status") != "missing" for item in legacy_xml["inputs"]):
            raise WorkerError("STALE_INDEX: legacy JVM context has uncaptured persistence XML; inspect again", "STALE")
    if scoped_typescript:
        if context.get("language") != "typescript":
            raise WorkerError("STALE_INDEX: TypeScript snapshot on a non-TypeScript context", "STALE")
        from .typescript_snapshot import replay
        replay(root, context.get("project"))
    elif str(context.get("source_snapshot_version", "")).startswith("typescript-"):
        raise WorkerError("STALE_INDEX: unsupported TypeScript snapshot version", "STALE")
    project_inputs = [] if scoped_typescript else (context.get("project") or {}).get("input_files", [])
    for item in project_inputs + context.get("worker", {}).get("distribution", []):
        if not Path(item["path"]).is_file() or file_hash(Path(item["path"])) != item["sha256"]:
            raise WorkerError("STALE_INDEX: project input or worker distribution changed", "STALE")
    if context.get("classification_override_hash"):
        from .classification import Classifier
        from .analysis_model import digest
        if digest(Classifier(root).config) != context["classification_override_hash"]:
            raise WorkerError("STALE_INDEX: classifier override changed", "STALE")
    if context.get("analyzer_version") and not scoped_typescript:
        from .scanner import scan_repository
        current = scan_repository(root, project_model=context.get("project_model"))
        from .inspection import source_snapshot
        current_files = source_snapshot(root, current, context)
        if current_files != context.get("source_files", {}):
            raise WorkerError("STALE_INDEX: source/config inputs changed; inspect again", "STALE")
    for path, expected in context.get("source_files", {}).items():
        target = safe_path(root, path)
        if not target.is_file() or file_hash(target) != expected:
            raise WorkerError("STALE_INDEX: source/config changed; inspect again", "STALE")
    for entry in context.get("classpath", []) + context.get("bytecode_artifacts", []):
        try:
            if artifact_hash(Path(entry["path"])) != entry["sha256"]:
                raise WorkerError("STALE_INDEX: classpath changed; import/inspect again", "STALE")
        except (OSError, ValueError):
            raise WorkerError("STALE_INDEX: classpath unavailable; import/inspect again", "STALE") from None


def validate_compiler_snapshot(root: Path, graph: KnowledgeGraph) -> None:
    """Validate every usable compiler context without executing a process."""
    for context in _compiler_contexts(graph, include_stale=False):
        validate_context_snapshot(root, context)


def resolve_context_classpath_artifact(root: Path, context: dict, sha256: str) -> dict:
    """Resolve one fresh compiler classpath entry by content, never by GAV/name."""
    from .analysis_model import AnalysisError
    from .build_model import HASH
    if not isinstance(context, dict) or not context.get("analyzer_version"):
        raise AnalysisError("RELEASE_CONSUMER_CONTEXT_UNAVAILABLE", 3)
    if not isinstance(sha256, str) or not HASH.fullmatch(sha256):
        raise AnalysisError("Invalid release classpath selector")
    validate_context_snapshot(root, context)
    matches = [item for item in context.get("classpath", [])
               if isinstance(item, dict) and item.get("sha256") == sha256]
    if not matches:
        raise AnalysisError("RELEASE_CLASSPATH_HASH_MISMATCH: " + sha256, 3)
    if len(matches) != 1:
        raise AnalysisError("RELEASE_CLASSPATH_AMBIGUOUS: " + sha256, 3)
    selected = matches[0]
    path = Path(selected["path"])
    if not path.is_absolute():
        from .analysis_model import safe_path
        path = safe_path(root, selected["path"])
    if path.is_symlink() or not path.is_file():
        raise AnalysisError("RELEASE_CLASSPATH_KIND_UNSUPPORTED: regular file required", 3)
    return dict(selected)


def _merge_contexts(fresh: KnowledgeGraph, stored: KnowledgeGraph,
                    preserved_contexts: list[dict], *,
                    layer_context_ids: set[str] | None = None) -> KnowledgeGraph:
    """Merge isolated compiler layers whose IDs and snapshots remain valid."""
    from dataclasses import replace
    preserve_ids = ({context["id"] for context in preserved_contexts}
                    if layer_context_ids is None else layer_context_ids)
    old_edges = []
    for edge in stored.edges:
        selected = tuple(context_id for context_id in edge.context_ids if context_id in preserve_ids)
        if selected:
            old_edges.append(replace(edge, context_ids=selected))
    old_symbols = [item for item in stored.symbols if item.get("context_id") in preserve_ids]
    old_sites = [item for item in stored.call_sites if item.get("context_id") in preserve_ids]
    old_cfgs = [item for item in stored.cfgs if item.get("context_id") in preserve_ids]
    old_ids = {item["id"] for item in [*old_symbols, *old_sites] if isinstance(item.get("id"), str)}
    old_ids.update(item.get("method") for item in old_cfgs if isinstance(item.get("method"), str))
    old_ids.update(identity for edge in old_edges for identity in (edge.source, edge.target))
    fresh_nodes = {node.id: node for node in fresh.nodes}
    collisions = old_ids & set(fresh_nodes)
    compiler_fresh_ids = {item.get("id") for item in [*fresh.symbols, *fresh.call_sites]}
    collisions &= compiler_fresh_ids
    if collisions:
        raise WorkerError(
            "Compiler context identity collision; rebuild workers with context-qualified IDs: "
            + ", ".join(sorted(collisions)[:3]), "INVALID_PROTOCOL"
        )
    for node in stored.nodes:
        if node.id in old_ids:
            fresh_nodes.setdefault(node.id, node)
    edges = sorted(set(fresh.edges) | set(old_edges),
                   key=lambda edge: (edge.source, edge.kind, edge.target, edge.context_ids))
    evidence_ids = {identity for edge in edges for identity in edge.evidence_ids}
    for item in [*fresh.call_sites, *old_sites, *fresh.cfgs, *old_cfgs]:
        evidence_ids.update(item.get("evidence_ids", []))
    for cfg in [*fresh.cfgs, *old_cfgs]:
        for block in cfg.get('blocks', []):
            if type(block.get('local_operation_version')) is int and block['local_operation_version'] == 1:
                refs = block.get('local_operation_evidence_ids', [])
                if isinstance(refs, list) and all(isinstance(identity, str) for identity in refs):
                    evidence_ids.update(refs)
    contexts = []
    seen_contexts = set()
    for context in [*fresh.contexts, *preserved_contexts]:
        if context.get("id") not in seen_contexts:
            contexts.append(context)
            seen_contexts.add(context.get("id"))
    diagnostics = list(fresh.diagnostics)
    for context in preserved_contexts:
        for diagnostic in context.get("diagnostics", []):
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
    selected_annotations = [item for item in [*fresh.analysis_annotations, *stored.analysis_annotations]
                            if set(item.get("target_ids", [])) <= set(fresh_nodes)]
    annotations = list({item["id"]: item for item in selected_annotations}.values())
    for item in annotations:
        evidence_ids.update(item.get("evidence_ids", []))
    evidence = {item["id"]: item for item in [*fresh.evidence, *stored.evidence]
                if item["id"] in evidence_ids}
    result = replace(
        fresh, schema_version=3,
        nodes=sorted(fresh_nodes.values(), key=lambda node: node.id), edges=edges,
        contexts=contexts, diagnostics=diagnostics,
        evidence=[evidence[key] for key in sorted(evidence)],
        symbols=[*fresh.symbols, *old_symbols], call_sites=[*fresh.call_sites, *old_sites],
        cfgs=[*fresh.cfgs, *old_cfgs], analysis_annotations=annotations,
    )
    KnowledgeGraph.from_dict(result.to_dict())
    return result


def merge_compiler_context(root: Path, fresh: KnowledgeGraph, selected_context: dict) -> KnowledgeGraph:
    """Publish one context while preserving other valid module/variant contexts."""
    stored = load_graph(root)
    if stored is None or not _compiler_contexts(stored):
        return fresh
    selection = _selection_key(selected_context)
    preserved = [context for context in _compiler_contexts(stored)
                 if _selection_key(context) != selection]
    active_ids = set()
    for context in preserved:
        if context.get("freshness") == "STALE":
            continue
        validate_context_snapshot(root, context)
        active_ids.add(context["id"])
    return _merge_contexts(fresh, stored, preserved, layer_context_ids=active_ids)


def retain_compiler_layer(root: Path, syntax: KnowledgeGraph) -> KnowledgeGraph:
    """Refresh syntax while retaining the saved, content-validated compiler layer.

    A stale context loses its compiler facts but remains as an explicit marker
    with the exact inspection command. Other valid contexts remain available.
    """
    stored = load_graph(root)
    if stored is None or not any(c.get("analyzer_version") for c in stored.contexts):
        return syntax
    contexts = _compiler_contexts(stored)
    published, active_ids = [], set()
    for context in contexts:
        if context.get("freshness") == "STALE":
            published.append(context)
            continue
        try:
            validate_context_snapshot(root, context)
        except WorkerError as error:
            published.append(_stale_context(context, str(error)))
        else:
            published.append(context)
            active_ids.add(context["id"])
    return _merge_contexts(syntax, stored, published, layer_context_ids=active_ids)

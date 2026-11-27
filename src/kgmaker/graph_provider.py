"""Offline graph refresh preserving validated compiler evidence in the shared store."""
from collections import defaultdict, deque
from functools import cache
from pathlib import Path
import re
import shlex

from .compiler_sources import (
    JVM_JPA_SOURCE_SNAPSHOTS, JVM_RAW_CAPTURE_PREFIX, JVM_RAW_SOURCE_SNAPSHOT, JVM_SOURCE_SNAPSHOTS,
    compiler_source_digest, jvm_raw_capture_id, normalized_source_projection, unsupported_kotlin_source,
)
from .model import KnowledgeGraph, Node
from .store import load_graph, load_graph_generation
from .worker_protocol import WorkerError


class _JvmSourceDrift(WorkerError):
    def __init__(self, changed: dict[str, str], deleted: set[str]):
        super().__init__("STALE_INDEX: source/config inputs changed; inspect again", "STALE")
        self.changed = changed
        self.deleted = deleted


def _compiler_input_absent(root: Path, path: str) -> bool:
    """Require physical absence, independently of source discovery and decoding."""
    from .analysis_model import safe_path

    # Recheck the confined path after a missing stat so a dangling symlink or
    # a disappearing path does not supply an absence observation on its own.
    for _ in range(2):
        try:
            safe_path(root, path).lstat()
        except FileNotFoundError:
            continue
        except (OSError, ValueError, RuntimeError):
            return False
        return False
    return True


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


def validate_context_snapshot(root: Path, context: dict) -> tuple[dict, ...]:
    """Validate a capture offline and report omissions affecting optional Kotlin identity."""
    if context.get("freshness") == "STALE":
        raise WorkerError(
            "STALE_INDEX: " + str(context.get("stale_reason", "compiler context requires inspection"))
            + "; run `" + str(context.get("next_command", _inspection_command(context))) + "`",
            "STALE",
        )
    # Compare every captured source and classpath; timestamps never establish freshness.
    from .analysis_model import file_hash, safe_path
    from .inspection import artifact_hash
    kotlin_omissions = ()
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
                 or snapshot_version not in JVM_SOURCE_SNAPSHOTS):
        raise WorkerError("STALE_INDEX: unsupported JVM source snapshot version", "STALE")
    if isinstance(snapshot_version, str) and snapshot_version in JVM_SOURCE_SNAPSHOTS \
            and context.get("language") != "jvm":
        raise WorkerError("STALE_INDEX: JVM source snapshot on a non-JVM context", "STALE")
    identity = context.get("id")
    if snapshot_version == JVM_RAW_SOURCE_SNAPSHOT or (
            isinstance(identity, str) and identity.startswith(JVM_RAW_CAPTURE_PREFIX)):
        expected = jvm_raw_capture_id(context)
        if expected is None or identity != expected:
            raise WorkerError("STALE_INDEX: JVM compiler input capture identity changed; inspect again", "STALE")
    if isinstance(snapshot_version, str) and snapshot_version in JVM_JPA_SOURCE_SNAPSHOTS:
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
    if snapshot_version == JVM_RAW_SOURCE_SNAPSHOT or (context.get("analyzer_version") and not scoped_typescript):
        from .scanner import scan_repository
        current = scan_repository(root, project_model=context.get("project_model"))
        from .inspection import source_snapshot
        from .symbol_identity import kotlin_source_omissions
        current_files = source_snapshot(root, current, context)
        recorded_files = context.get("source_files", {})
        if current_files != recorded_files:
            if snapshot_version == JVM_RAW_SOURCE_SNAPSHOT and unsupported_kotlin_source(
                    current.raw_file_hashes, context['compiler_inputs']) is None:
                inputs = set(context['compiler_inputs'])
                changed = {path: value for path, value in current_files.items() if recorded_files.get(path) != value}
                deleted = recorded_files.keys() - current_files.keys()
                if (current_files.keys() <= recorded_files.keys()
                        and changed.keys() <= inputs and changed.keys() <= current.files.keys()
                        and deleted <= inputs
                        and all(_compiler_input_absent(root, path) for path in deleted)):
                    raise _JvmSourceDrift(changed, deleted)
            raise WorkerError("STALE_INDEX: source/config inputs changed; inspect again", "STALE")
        if snapshot_version == JVM_RAW_SOURCE_SNAPSHOT:
            if normalized_source_projection(current.files, current_files) != context.get("normalized_source_files"):
                raise WorkerError("STALE_INDEX: normalized JVM source projection changed; inspect again", "STALE")
            unsupported = unsupported_kotlin_source(current.raw_file_hashes, context["compiler_inputs"])
            if unsupported is not None:
                raise WorkerError("STALE_INDEX: selected Kotlin source uses unsupported raw byte coordinates: "
                                  + unsupported, "STALE")
        kotlin_omissions = kotlin_source_omissions(context, current.diagnostics)
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
    return kotlin_omissions


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
                    layer_context_ids: set[str] | None = None,
                    source_omissions: dict[str, tuple[dict, ...]] | None = None) -> KnowledgeGraph:
    """Merge isolated compiler layers whose IDs and snapshots remain valid."""
    from dataclasses import replace
    from .symbol_identity import without_logical_key
    preserve_ids = ({context["id"] for context in preserved_contexts}
                    if layer_context_ids is None else layer_context_ids)
    old_edges = []
    for edge in stored.edges:
        selected = tuple(context_id for context_id in edge.context_ids if context_id in preserve_ids)
        if selected:
            old_edges.append(replace(edge, context_ids=selected))
    omissions = source_omissions or {}
    old_symbols = [without_logical_key(item) if item["context_id"] in omissions else item
                   for item in stored.symbols if item.get("context_id") in preserve_ids]
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
        for diagnostic in [*context.get("diagnostics", []), *omissions.get(context["id"], ())]:
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
    selected_annotations = [item for item in [*fresh.analysis_annotations, *stored.analysis_annotations]
                            if set(item.get("target_ids", [])) <= set(fresh_nodes)]
    annotations = list({item["id"]: item for item in selected_annotations}.values())
    for item in annotations:
        evidence_ids.update(item.get("evidence_ids", []))
    # A refreshed context owns its regenerated evidence, even if an earlier
    # stored record has the same identifier.
    evidence = {item["id"]: item for item in [*stored.evidence, *fresh.evidence]
                if item["id"] in evidence_ids}
    result = replace(
        fresh, schema_version=3,
        nodes=sorted(fresh_nodes.values(), key=lambda node: node.id), edges=edges,
        contexts=contexts, diagnostics=diagnostics,
        evidence=[evidence[key] for key in sorted(evidence)],
        symbols=[*fresh.symbols, *old_symbols], call_sites=[*fresh.call_sites, *old_sites],
        cfgs=[*fresh.cfgs, *old_cfgs], analysis_annotations=annotations,
    )
    from .extraction_cache import retain, decode, MAX_ENTRIES
    eligible = {c['id'] for c in contexts if c.get('analyzer_version') and c.get('freshness') != 'STALE'}
    candidates = (retain(fresh.extraction_cache, eligible).get('entries', [])
                  + retain(stored.extraction_cache, eligible).get('entries', []))
    entries = list({entry['key_sha256']: entry for entry in reversed(candidates)}.values())[::-1]
    # Prefer this selected generation. Oversized optimization metadata never
    # prevents publication of valid graph facts.
    while entries and not decode({'schema_version': 1, 'entries': entries[:MAX_ENTRIES]}):
        entries.pop()
    result.extraction_cache = ({'schema_version': 1, 'entries': entries[:MAX_ENTRIES]} if entries else {})
    KnowledgeGraph.from_dict(result.to_dict())
    return result


def _reference_ids(value) -> bool:
    return isinstance(value, (list, tuple)) and all(isinstance(item, str) and item for item in value)


def _proof_owners(proof: dict) -> set[str] | None:
    """Read compiler arrays and the runtime importer's singular owner."""
    plural = proof.get('context_ids', [])
    if not _reference_ids(plural):
        return None
    owners = set(plural)
    if len(owners) != len(plural):
        return None
    if 'context_id' not in proof:
        return owners
    singular = proof['context_id']
    if not isinstance(singular, str) or not singular:
        return None
    if 'context_ids' in proof and owners != {singular}:
        return None
    return {singular}


def _proof_dependencies(proof: dict, owners: set[str], symbols: dict, sites: dict) -> set[str] | None:
    """Resolve the extra compiler and runtime references stored by typed producers."""
    dependencies = set()
    if 'compiler_symbol_id' in proof:
        reference = proof['compiler_symbol_id']
        # Framework proxy proofs use this field for a compiler call site.
        if not isinstance(reference, str) or (reference not in symbols and reference not in sites):
            return None
        dependencies.add(reference)
    sources = proof.get('compiler_sources', [])
    if not isinstance(sources, list):
        return None
    for source in sources:
        if not isinstance(source, dict):
            return None
        identity = source.get('symbol_id')
        if not isinstance(identity, str) or identity not in symbols:
            return None
        symbol = symbols[identity]
        if source.get('context_id') != symbol['context_id'] or source.get('path') != symbol.get('path'):
            return None
        dependencies.add(identity)
    if proof.get('kind') == 'RUNTIME_OBSERVED' and ('call_site' in proof or 'receiver_type' in proof):
        call_site, receiver = proof.get('call_site'), proof.get('receiver_type')
        if not isinstance(call_site, str) or not isinstance(receiver, str):
            return None
        site, receiver_symbol = sites.get(call_site, {}), symbols.get(receiver, {})
        if (len(owners) != 1 or site.get('context_id') not in owners
                or receiver_symbol.get('context_id') not in owners or receiver_symbol.get('kind') != 'class'):
            return None
        dependencies.update((call_site, receiver))
    return dependencies


def _isolated_peer_evidence(graph: KnowledgeGraph, context: dict) -> bool:
    if graph.analysis_annotations:
        return False
    peer = context['id']
    paths = context['source_files'].keys()
    other_ids = {item['id'] for item in _compiler_contexts(graph) if item['id'] != peer}
    known_ids = {item['id'] for item in graph.contexts if isinstance(item.get('id'), str)}
    symbols = {item['id']: item for item in graph.symbols}
    sites = {item['id']: item for item in graph.call_sites}
    peer_nodes = {item['id'] for item in [*graph.symbols, *graph.call_sites] if item.get('context_id') == peer}
    for node in graph.nodes:
        metadata = node.metadata if node.metadata is not None else {}
        if not isinstance(metadata, dict):
            return False
        support = _proof_owners(metadata)
        if support is None or not support <= known_ids or (peer in support and support != {peer}):
            return False
        if node.path in paths or peer in support:
            peer_nodes.add(node.id)
    peer_evidence = set()
    for item in graph.evidence:
        support = _proof_owners(item)
        source, target, path = (item.get(key) for key in ('source', 'target', 'source_file'))
        if (support is None or not support <= known_ids
                or any(value is not None and not isinstance(value, str) for value in (source, target, path))):
            return False
        dependencies = _proof_dependencies(item, support, symbols, sites)
        if dependencies is None:
            return False
        if (peer in support or source in peer_nodes or target in peer_nodes or path in paths
                or peer_nodes.intersection(dependencies)):
            if other_ids.intersection(support) or (peer in support and support != {peer}):
                return False
            peer_evidence.add(item['id'])
    for edge in graph.edges:
        if peer in edge.context_ids and edge.context_ids != (peer,):
            return False
        if other_ids.intersection(edge.context_ids) and (
                edge.source in peer_nodes or edge.target in peer_nodes or edge.source_file in paths
                or peer_evidence.intersection(edge.evidence_ids)):
            return False
    for site in graph.call_sites:
        if site.get('context_id') in other_ids and (
                site.get('path') in paths or site.get('caller') in peer_nodes
                or site.get('declared_target') in peer_nodes
                or peer_nodes.intersection(site.get('dispatch_candidates', []))
                or peer_evidence.intersection(site.get('evidence_ids', []))):
            return False
    for cfg in graph.cfgs:
        if cfg.get('context_id') not in other_ids:
            continue
        refs = cfg.get('evidence_ids', [])
        if not _reference_ids(refs) or cfg.get('method') in peer_nodes or peer_evidence.intersection(refs):
            return False
        for block in cfg['blocks']:
            path = block.get('source_file')
            calls, refs = block.get('call_site_ids', []), block.get('local_operation_evidence_ids', [])
            if ((path is not None and not isinstance(path, str)) or path in paths
                    or not _reference_ids(calls) or not _reference_ids(refs)
                    or peer_nodes.intersection(calls) or peer_evidence.intersection(refs)):
                return False
    return not any(item.get('context_id') in other_ids and item.get('path') in paths
                   for item in graph.symbols)


def _owns_deleted_jvm_inputs(initial: KnowledgeGraph, stored: KnowledgeGraph,
                             context: dict, deleted: set[str]) -> bool:
    from .classification import source_set_contains

    previous = defaultdict(list)
    for node in stored.nodes:
        if node.kind == 'file' and node.path in deleted:
            previous[node.path].append(node)
    module, source_set, scope = (context[key] for key in ('module', 'source_set', 'scope'))
    membership = (module + ':' + source_set,)
    unanalyzed = [row['path'] for row in initial.diagnostics if row.get('code') == 'SOURCE_NOT_ANALYZED']
    for path in deleted:
        owners = [item for item in context['project_model']['source_sets'] if source_set_contains(item, path)]
        if len(owners) != 1:
            return False
        owner, = owners
        if ((owner['module'], owner['id'], owner['scope']) != (module, source_set, scope)
                or path not in owner.get('files', [])
                or any(source_set_contains(owner, unscanned) for unscanned in unanalyzed)
                or len(previous[path]) != 1
                or (previous[path][0].build_membership, previous[path][0].scope) != (membership, scope)
                or compiler_source_digest(stored.files, context, path) is None):
            return False
    return True


def _isolated_jvm_peer(initial: KnowledgeGraph, fresh: KnowledgeGraph, stored: KnowledgeGraph,
                       context: dict, peers: list[dict], selected: dict, error: _JvmSourceDrift) -> bool:
    scope = selected.get('scope')
    if (context.get('scope') != scope or initial.raw_file_hashes is None
            or error.deleted.intersection(initial.files) or any(
                initial.raw_file_hashes.get(path, initial.files.get(path)) != value
                for path, value in error.changed.items())):
        return False
    files = {node.path: (node.build_membership, node.scope) for node in initial.nodes if node.kind == 'file'}
    active = [selected, *(item for item in peers if item.get('freshness') != 'STALE')]
    distribution = selected.get('worker', {}).get('distribution', [])
    if not distribution:
        return False
    try:
        library_root = (Path(distribution[0]['path']).parent / 'lib').resolve()
        libraries = {(Path(item['path']).resolve(strict=True), item['sha256']) for item in distribution[1:]}
        libraries = {(path, checksum) for path, checksum in libraries if path.parent == library_root}
        for item in active:
            item_id = item.get('id')
            module, source_set = item.get('module'), item.get('source_set')
            item_scope = item.get('scope')
            worker = item.get('worker')
            if (not isinstance(item_id, str) or not item_id
                    or not isinstance(module, str) or not isinstance(source_set, str)
                    or not isinstance(item_scope, str) or not isinstance(worker, dict)
                    or jvm_raw_capture_id(item) != item_id
                    or item.get('freshness') != 'CONTENT_VERIFIED'
                    or item.get('origin_trust') != 'LOCAL_COMPILER_INPUTS'
                    or item.get('repo_id') != selected.get('repo_id')
                    or item.get('project_model') != selected.get('project_model')
                    or worker.get('distribution') != distribution
                    or any(item.get(key) for key in ('build_id', 'build_context_id', 'manifest_hash',
                                                     'toolchain', 'dependency_model_hash', 'compiler_options',
                                                     'generated_source_roots', 'bytecode_artifacts'))
                    or not item.get('compiler_inputs')
                    or any(files.get(path) != ((module + ':' + source_set,), item_scope)
                           for path in item['source_files']
                           if item_id != context['id'] or path not in error.deleted)):
                return False
            if item_id != context['id'] and (item['module'] == context['module']
                    or context['source_files'].keys() & item['source_files'].keys()):
                return False
            classpath = item.get('classpath')
            if not isinstance(classpath, list) or any(
                   not isinstance(entry, dict) or set(entry) != {'path', 'sha256'}
                   or not all(isinstance(value, str) for value in entry.values())
                   or not Path(entry['path']).is_absolute()
                   or (Path(entry['path']).resolve(strict=True), entry['sha256']) not in libraries
                   for entry in classpath):
                return False
    except (OSError, RuntimeError):
        return False
    other_scopes = [item for item in active if item.get('scope') != scope]
    if other_scopes:
        # Other-scope control captures must be independent of both versions of the selected layer.
        control_paths = {path for item in other_scopes for path in item['source_files']}
        control_scope = {'production': 'test', 'test': 'production'}.get(scope)
        if (control_scope is None or selected['source_files'].keys() & control_paths or any(
                item.get('scope') != control_scope or item['module'] == selected['module']
                or not _isolated_peer_evidence(fresh, item) for item in other_scopes)):
            return False
        stored_contexts = _compiler_contexts(stored)
        stored_ids = [item.get('id') for item in stored_contexts]
        if not _reference_ids(stored_ids) or len(set(stored_ids)) != len(stored_ids):
            return False
        selection = _selection_key(selected)
        replaced = (item for item in stored_contexts if _selection_key(item) == selection)
        if any(jvm_raw_capture_id(item) != item['id'] or control_paths.intersection(item['source_files'])
               or not _isolated_peer_evidence(stored, item) for item in replaced):
            return False
    if error.deleted and not _owns_deleted_jvm_inputs(initial, stored, context, error.deleted):
        return False
    return _isolated_peer_evidence(stored, context) and _isolated_peer_evidence(fresh, context)


def merge_compiler_context(root: Path, fresh: KnowledgeGraph, selected_context: dict) -> KnowledgeGraph:
    """Publish one context while preserving other valid module/variant contexts."""
    graph, _, _ = _prepare_compiler_context(root, fresh, selected_context)
    return graph


def _prepare_compiler_context(root: Path, fresh: KnowledgeGraph, selected_context: dict, *,
                              initial_scan: KnowledgeGraph | None = None) -> tuple[KnowledgeGraph, set[str], set[str]]:
    """Compose the candidate and report retired source paths and confirmed deletions."""
    stored = load_graph(root)
    if stored is None or not _compiler_contexts(stored):
        return fresh, set(), set()
    selection = _selection_key(selected_context)
    preserved = [context for context in _compiler_contexts(stored)
                 if _selection_key(context) != selection]
    published, active_ids, omissions = [], set(), {}
    retired_paths = set()
    deleted_paths = set()
    for context in preserved:
        if context.get("freshness") == "STALE":
            published.append(context)
            continue
        try:
            omitted = validate_context_snapshot(root, context)
        except _JvmSourceDrift as error:
            if initial_scan is None or not _isolated_jvm_peer(initial_scan, fresh, stored, context,
                                                               preserved, selected_context, error):
                raise
            reason = str(error)
            if error.deleted:
                reason += "; deleted compiler inputs: " + ", ".join(sorted(error.deleted))
                if error.changed:
                    reason += "; changed compiler inputs: " + ", ".join(sorted(error.changed))
            published.append(_stale_context(context, reason))
            retired_paths.update(context['source_files'])
            deleted_paths.update(error.deleted)
            continue
        published.append(context)
        if omitted:
            omissions[context["id"]] = omitted
        active_ids.add(context["id"])
    graph = _merge_contexts(fresh, stored, published, layer_context_ids=active_ids, source_omissions=omissions)
    return graph, retired_paths, deleted_paths


def retain_compiler_layer(root: Path, syntax: KnowledgeGraph) -> KnowledgeGraph:
    """Refresh syntax while retaining the saved, content-validated compiler layer.

    A stale context loses its compiler facts but remains as an explicit marker
    with the exact inspection command. Other valid contexts remain available.
    """
    stored = load_graph(root)
    if stored is None or not any(c.get("analyzer_version") for c in stored.contexts):
        return syntax
    contexts = _compiler_contexts(stored)
    published, active_ids, omissions = [], set(), {}
    for context in contexts:
        if context.get("freshness") == "STALE":
            published.append(context)
            continue
        try:
            omitted = validate_context_snapshot(root, context)
        except WorkerError as error:
            published.append(_stale_context(context, str(error)))
        else:
            published.append(context)
            active_ids.add(context["id"])
            if omitted:
                omissions[context["id"]] = omitted
    return _merge_contexts(syntax, stored, published, layer_context_ids=active_ids, source_omissions=omissions)


def _fk_operation_owns_column(operation: Node, column_id: str) -> bool:
    """Bind the named target to the operation that actually replayed it."""
    metadata = operation.metadata
    witness = metadata.get('foreign_key_operation_targets') if isinstance(metadata, dict) else None
    if not isinstance(witness, dict):
        return False
    line = witness.get('source_line')
    snapshot = metadata.get('schema_snapshot_fingerprint')
    columns = witness.get('column_ids')
    return (witness.get('operation_id') == operation.id and witness.get('source_file') == operation.path
            and type(line) is int and line > 0 and type(operation.line) is int and line == operation.line
            and isinstance(snapshot, str) and witness.get('schema_snapshot_fingerprint') == snapshot
            and isinstance(columns, list) and _reference_ids(columns) and len(set(columns)) == len(columns)
            and column_id in columns)


def _reverse_dependency_index(graph: KnowledgeGraph) -> dict[str, list[dict]]:
    """Derive positive relationships from one already-published generation."""
    from .analysis_model import digest
    from .schema_replay import FK_COLUMN_RELATION, Replay, persistence_pair, realm_prefix

    index = defaultdict(list)
    if graph.schema_version == 1:
        return index
    files = {path: checksum for path, checksum in graph.files.items()
             if re.fullmatch(r"[a-f0-9]{64}", checksum)}
    nodes = {node.id: node for node in graph.nodes}
    contexts = {c.get("id"): c for c in graph.contexts
                if isinstance(c.get("id"), str) and c.get("analyzer_version")
                and c.get("origin_trust") == "LOCAL_COMPILER_INPUTS"
                and c.get("freshness") == "CONTENT_VERIFIED" and isinstance(c.get("source_files"), dict)
                and ((c.get("source_snapshot_version") != JVM_RAW_SOURCE_SNAPSHOT
                      and not c["id"].startswith(JVM_RAW_CAPTURE_PREFIX))
                     or jvm_raw_capture_id(c) == c["id"])}
    symbols = {item["id"]: item for item in graph.symbols} if graph.schema_version == 3 else {}
    proofs = {item["id"]: item for item in graph.evidence}
    compiler_edges = defaultdict(set)

    @cache
    def source_digest(context_id, path):
        return compiler_source_digest(files, contexts[context_id], path)

    def add(path, dependent_path, target, kind, *, target_raw_sha256=None, **witness):
        if path in files and dependent_path in files:
            index[path].append({"kind": kind, "id": target, "path": dependent_path,
                                "target_raw_sha256": target_raw_sha256,
                                "reason": {"dependency_path": path, "before_sha256": files[path], **witness}})

    def realm(node):
        record = node.metadata.get("persistence_realm") if isinstance(node.metadata, dict) else None
        if isinstance(record, dict) and record.get("derivation") == "MIGRATION_DERIVED":
            return persistence_pair(record.get("database_id"), record.get("stream_id"))
        return None

    @cache
    def replay_scope(node_id):
        node = nodes[node_id]
        pair = realm(node)
        if pair is None:
            return None
        record = node.metadata['persistence_realm']
        config = record.get('config_fingerprint')
        snapshot = node.metadata.get('schema_snapshot_fingerprint')
        target = record.get('target')
        if (isinstance(target, str) and target and all(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value)
                                                       for value in (config, snapshot))):
            return pair, config, target, snapshot
        return None

    def schema_relation(edge, source, target):
        left = realm(source)
        return (left and left == realm(target) and edge.source_file == source.path
                and edge.confidence == 'EXTRACTED' and edge.evidence_kind == 'SYNTAX_CANDIDATE'
                and type(edge.source_line) is int and edge.source_line > 0)

    foreign_key_tables = defaultdict(list)
    migration_operations = defaultdict(list)
    for edge in graph.edges:
        if edge.kind == 'foreign_key_to':
            source, target = nodes[edge.source], nodes[edge.target]
            if (source.kind == 'db_constraint' and target.kind == 'db_table'
                    and edge.source_line == source.line and schema_relation(edge, source, target)):
                foreign_key_tables[source.id].append(target)
        if edge.kind != "operation_targets" or nodes[edge.target].kind not in {"db_table", "db_column", "db_constraint"}:
            continue
        operations = migration_operations[edge.target]
        operation = nodes[edge.source]
        stream = realm(operation)
        if (operation.kind == "migration_operation" and operation.summary is None
                and stream and stream == realm(nodes[edge.target]) and operation.path in files
                and edge.source_file == operation.path and edge.source_line == operation.line
                and type(edge.source_line) is int and edge.source_line > 0
                and edge.confidence == "EXTRACTED" and edge.evidence_kind == "SYNTAX_CANDIDATE"):
            operations.append(operation)

    @cache
    def creation_operation(node_id, command, scope):
        node = nodes[node_id]
        pair, config, horizon, _ = scope
        creation = node.metadata.get('schema_identity')
        origin = creation.get('origin') if isinstance(creation, dict) else None
        if not isinstance(origin, dict):
            return None
        kind = node.kind[3:]
        name = creation.get('name')
        path, line, statement = (origin.get(key) for key in ('path', 'line', 'statement'))
        # Flyway captured raw bytes. A normalized hash cannot establish a different raw history.
        if (type(creation.get('schema_version')) is not int or creation['schema_version'] != 1
                or creation.get('kind') != kind or 'incarnation' not in creation
                or (creation.get('database_id'), creation.get('stream_id')) != pair
                or not _reference_ids(name) or len(name) != len(node.metadata['schema_object'])
                or not isinstance(path, str) or path not in files or origin.get('sha256') != files[path]
                or type(line) is not int or line < 1 or type(statement) is not int or statement < 1):
            return None
        prefix = realm_prefix({'database_id': pair[0], 'stream_id': pair[1]})
        identity = 'schema:' + prefix + ':' + Replay.key(kind, tuple(name))
        incarnation = creation['incarnation']
        try:
            if incarnation is not None:
                if incarnation != digest(origin)[:12]:
                    return None
                identity += ':incarnation:' + incarnation
            if (node_id != identity or creation.get('proof_hash') != digest({
                    key: value for key, value in creation.items() if key != 'proof_hash'})):
                return None
        except (TypeError, ValueError, RecursionError):
            return None
        operation_prefix = f'migration-operation:{prefix}:{path}:'
        prior = []
        for operation in migration_operations.get(node_id, ()):
            persisted = operation.metadata['persistence_realm']
            if (operation.path != path or persisted.get('config_fingerprint') != config
                    or persisted.get('target') != horizon):
                continue
            ordinal = operation.id[len(operation_prefix):]
            if not operation.id.startswith(operation_prefix) or not re.fullmatch(r'[1-9][0-9]*', ordinal):
                return None
            prior.append((len(ordinal), ordinal, operation))
        if not prior:
            return None
        # A later operation on the same object can share the original SQL line.
        _, ordinal, operation = min(prior, key=lambda item: item[:2])
        if (ordinal != str(statement) or operation.name != command
                or type(operation.line) is not int or operation.line != line):
            return None
        return operation

    for edge in graph.edges:
        source, target = nodes[edge.source], nodes[edge.target]
        if edge.kind in {"declares_call", "declares_reference", "resolves_to"} and edge.evidence_kind == "SYMBOL_RESOLVED":
            if len(edge.context_ids) != 1 or edge.context_ids[0] not in contexts or edge.source_file not in files:
                continue
            context_id = edge.context_ids[0]
            checksum = source_digest(context_id, edge.source_file)
            if checksum is None:
                continue
            for identity in edge.evidence_ids:
                proof = proofs[identity]
                if (proof.get("source") == edge.source and proof.get("target") == edge.target
                        and proof.get("relation") == edge.kind and proof.get("kind") == "SYMBOL_RESOLVED"
                        and proof.get("context_ids") == [context_id] and proof.get("freshness") == "CONTENT_VERIFIED"
                        and proof.get("origin_trust") == "LOCAL_COMPILER_INPUTS"
                        and proof.get("source_file") == edge.source_file and proof.get("sha256") == checksum):
                    compiler_edges[(edge.source, edge.target, edge.kind, context_id, edge.source_file)].add(identity)
        elif (edge.kind, source.kind, target.kind) == (FK_COLUMN_RELATION, 'db_constraint', 'db_column'):
            scope = replay_scope(source.id)
            if (scope is None or replay_scope(target.id) != scope or edge.source_line != source.line
                    or not schema_relation(edge, source, target)):
                continue
            reference = source.metadata.get('foreign_key_targets')
            ids = reference.get('column_ids') if isinstance(reference, dict) else None
            if not _reference_ids(ids) or target.id not in ids or len(set(ids)) != len(ids):
                continue
            column = target.metadata.get('schema_object')
            tables = [table for table in foreign_key_tables[source.id] if replay_scope(table.id) == scope]
            if (len(tables) != 1 or tables[0].id != reference.get('table_id')
                    or not isinstance(column, list) or len(column) != 3
                    or any(not isinstance(component, str) or not component for component in column)
                    or tables[0].metadata.get('schema_object') != column[:-1]):
                continue
            for operation in migration_operations.get(target.id, ()):
                if replay_scope(operation.id) == scope and _fk_operation_owns_column(operation, target.id):
                    add(operation.path, source.path, source.id, 'SCHEMA_DEPENDENT', relation=edge.kind,
                        source_line=edge.source_line, evidence_kind='MIGRATION_DERIVED', dependency_id=target.id,
                        operation_id=operation.id, operation_line=operation.line)
        elif (edge.kind, source.kind, target.kind) == ('contains_constraint', 'db_table', 'db_constraint'):
            table, constraint = source, target
            scope = replay_scope(table.id)
            if (scope is None or replay_scope(constraint.id) != scope
                    or table.summary != 'MIGRATION_DERIVED; COMPLETE' or constraint.summary != table.summary
                    or edge.source_line != constraint.line or not schema_relation(edge, constraint, table)):
                continue
            table_name = table.metadata.get('schema_object')
            constraint_name = constraint.metadata.get('schema_object')
            if (not _reference_ids(table_name) or len(table_name) != 2 or table.name != '.'.join(table_name)
                    or not _reference_ids(constraint_name) or constraint_name[:-1] != table_name
                    or constraint.name != '.'.join(constraint_name)):
                continue
            declaration = creation_operation(constraint.id, 'ALTER', scope)
            if declaration is None or (declaration.path, declaration.line) != (constraint.path, constraint.line):
                continue
            operation = creation_operation(table.id, 'CREATE', scope)
            if operation is not None and operation.path != declaration.path:
                add(operation.path, constraint.path, constraint.id, 'SCHEMA_DEPENDENT', relation=edge.kind,
                    source_line=edge.source_line, evidence_kind='MIGRATION_DERIVED', dependency_id=table.id,
                    operation_id=operation.id, operation_line=operation.line)
        elif (edge.kind, source.kind, target.kind) in {
            ("foreign_key_to", "db_constraint", "db_table"),
            ("derived_from", "db_view_field", "db_column"),
        }:
            if schema_relation(edge, source, target):
                witness = {"relation": edge.kind, "source_line": edge.source_line,
                           "evidence_kind": "MIGRATION_DERIVED", "dependency_id": target.id}
                operations = migration_operations.get(target.id)
                if operations is None:
                    add(target.path, source.path, source.id, "SCHEMA_DEPENDENT", **witness)
                else:
                    for operation in operations:
                        add(operation.path, source.path, source.id, "SCHEMA_DEPENDENT",
                            operation_id=operation.id, operation_line=operation.line, **witness)
        elif edge.kind == "declares_endpoint" and source.kind == "file" and target.kind == "api_endpoint":
            registrations = target.metadata.get("http_registrations") if isinstance(target.metadata, dict) else None
            if source.path not in files or edge.source_file != source.path or not isinstance(registrations, list):
                continue
            # Source graph evidence covers normalized text. Registration records bind raw bytes.
            binding = {"source": source.id, "target": target.id, "relation": edge.kind,
                       "kind": "SYNTAX_CANDIDATE", "extractor": "source-patterns-2",
                       "source_file": source.path, "sha256": files[source.path],
                       "freshness": "CONTENT_VERIFIED", "origin_trust": "LOCAL_SOURCE",
                       "context_ids": list(edge.context_ids)}
            if not any(all(proofs[identity].get(key) == value for key, value in binding.items())
                       for identity in edge.evidence_ids):
                continue
            for record in registrations:
                if not isinstance(record, dict):
                    continue
                checksum = record.get("source_sha256")
                if (record.get("provider") in ("openapi-json", "openapi-yaml")
                        and record.get("source_path") == source.path and isinstance(checksum, str)
                        and re.fullmatch(r"[a-f0-9]{64}", checksum)
                        and record.get("unresolved_reasons") == [] and isinstance(record.get("variant_fingerprint"), str)):
                    add(source.path, source.path, target.id, "CONTRACT_DECLARATION", relation=edge.kind,
                        evidence_kind="OPENAPI_DECLARATION", variant_fingerprint=record["variant_fingerprint"],
                        before_sha256=checksum)

    for site in graph.call_sites if graph.schema_version == 3 else ():
        context_id, caller_id, target_id = site.get("context_id"), site.get("caller"), site.get("declared_target")
        if (site.get("evidence_kind") != "SYMBOL_RESOLVED" or context_id not in contexts
                or caller_id not in symbols or target_id not in symbols):
            continue
        caller, target = nodes[caller_id], nodes[target_id]
        if (site.get("path") != caller.path or caller.path not in files or target.path not in files
                or any(symbols[identity].get("context_id") != context_id for identity in (caller_id, target_id))
                or source_digest(context_id, caller.path) is None):
            continue
        target_checksum = source_digest(context_id, target.path)
        if target_checksum is None:
            continue
        relation = "declares_reference" if site.get("invocation_kind") == "METHOD_REFERENCE" else "declares_call"
        ids = set(site.get("evidence_ids", []))
        declaration = ids & compiler_edges[(caller_id, site["id"], relation, context_id, caller.path)]
        resolution = ids & compiler_edges[(site["id"], target_id, "resolves_to", context_id, caller.path)]
        if declaration and resolution:
            target_locator = symbols[target_id]
            target_raw_sha256 = target_locator.get("sha256")
            if target_locator.get("path") != target.path or target_raw_sha256 != target_checksum:
                target_raw_sha256 = None
            add(target.path, caller.path, caller_id, "COMPILER_CALLER", relation=relation, dependency_id=target_id,
                call_site_id=site["id"], context_id=context_id, evidence_ids=sorted(declaration | resolution),
                target_raw_sha256=target_raw_sha256)
    return index


def dependency_impact(root: Path, changed_files: list[str]) -> dict:
    """Plan revalidation of evidenced dependents, without modifying a store or running workers."""
    from .analysis_model import AnalysisError, canonical, safe_path
    from .feature import applied_dependency_citations, inherited_input_dependency_citations
    from .scanner import EXTENSIONS
    from .workspace import _regular_file_hashes

    root = root.resolve()
    targets = {safe_path(root, value).relative_to(root).as_posix() for value in changed_files}
    if not targets or "." in targets:
        raise AnalysisError("Supply at least one repository-relative file")
    generation = load_graph_generation(root)
    if generation is None:
        raise AnalysisError("No readable graph found. Run kgmaker scan before recording the changed files.", 1)
    graph, fingerprint = generation
    index = _reverse_dependency_index(graph)
    citations, diagnostics, input_revisions = applied_dependency_citations(root, targets)
    citation_paths = {item["path"] for item in citations}
    diagnostics.append({"code": "POSITIVE_HISTORICAL_EVIDENCE_ONLY",
                        "reason": "Negative lookups, uncaptured relationships and cross-workspace bindings are outside this index."})
    if graph.schema_version < 3:
        diagnostics.append({"code": "LEGACY_COMPILER_INDEX_UNAVAILABLE", "graph_schema_version": graph.schema_version})
    elif not any(c.get("freshness") == "CONTENT_VERIFIED" for c in _compiler_contexts(graph)):
        diagnostics.append({"code": "VERIFIED_COMPILER_LAYER_UNAVAILABLE"})
    observed, changed, seeds = {}, [], set()
    for path in sorted(targets):
        if path not in graph.files and path not in citation_paths:
            diagnostics.append({"code": "DEPENDENCY_PATH_NOT_CAPTURED", "path": path})
            continue
        try:
            target = safe_path(root, path)
            try:
                target.lstat()
            except FileNotFoundError:
                if safe_path(root, path).exists():
                    raise OSError("Unstable source path") from None
                raw_after = graph_after = None
            else:
                # Disappearance after the initial stat is an unavailable read.
                hashes = _regular_file_hashes(target, normalize_newlines=target.suffix.lower() in EXTENSIONS)
                if hashes is None:
                    raise OSError("Expected stable regular file")
                raw_after, graph_after = hashes
        except (ValueError, OSError):
            diagnostics.append({"code": "DEPENDENCY_PATH_UNAVAILABLE", "path": path})
            continue
        observed[path] = raw_after
        before = graph.files.get(path)
        if before is not None and before != graph_after:
            changed.append({"path": path, "before_sha256": before, "after_sha256": graph_after})
            seeds.add((path, None))
        elif before is not None and raw_after is not None:
            # A matching compiler locator proves the target's historical raw bytes.
            seeds.update((path, item["reason"]["dependency_id"])
                         for item in index.get(path, ()) if item["target_raw_sha256"] is not None
                         and item["target_raw_sha256"] != raw_after)

    affected = {}

    def add(kind, path, identity, status, reason):
        record = affected.setdefault((kind, path, identity), {"kind": kind, "path": path, "id": identity,
                                                              "status": status, "reasons": {}})
        record["reasons"][canonical(reason)] = reason

    seen = set(seeds)
    queue = deque(sorted(seeds))
    while queue:
        path, identity = queue.popleft()
        for item in index.get(path, ()):
            if item["kind"] == "CONTRACT_DECLARATION":
                continue
            reason = item["reason"]
            if identity is not None and reason.get("dependency_id") != identity:
                continue
            dependent = item["path"], item["id"]
            add(item["kind"], *dependent, "RECHECK", reason)
            if dependent not in seen:
                seen.add(dependent)
                queue.append(dependent)
    for path, current_hash in observed.items():
        for item in index.get(path, ()):
            reason = item["reason"]
            if item["kind"] == "CONTRACT_DECLARATION" and reason["before_sha256"] != current_hash:
                add(item["kind"], path, item["id"], "RECHECK", reason)
    changed_citations = [item for item in citations
                         if item["path"] in observed and item["before_sha256"] != observed[item["path"]]]
    inherited, dependency_diagnostics = inherited_input_dependency_citations(changed_citations, input_revisions)
    diagnostics.extend(dependency_diagnostics)
    changed_citations.extend(inherited)
    for item in changed_citations:
        add("FEATURE_CONCLUSION", None, item["conclusion_id"], "STALE",
            {**item, "after_sha256": observed[item["path"]]})
    values = []
    for _, record in sorted(affected.items()):
        record["reasons"] = [value for _, value in sorted(record["reasons"].items())]
        values.append(record)
    return {"schema_version": 1, "graph_sha256": fingerprint, "coverage": "PARTIAL",
            "changed_sources": changed, "affected": values, "diagnostics": diagnostics}

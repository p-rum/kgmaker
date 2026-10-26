"""Scope projections and deterministic, purpose-specific ranking.

Navigation hints and execution evidence remain separate. References never
contribute to execution centrality, even for heavily reused DTOs and enums.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, replace
from pathlib import Path
from typing import Mapping

from .model import KnowledgeGraph

EXECUTION_EDGES = {"resolves_to", "may_dispatch_to", "declares_call", "observed_dispatch_to"}
SIDE_EFFECTS = {"persistence_intent", "query_writes", "query_deletes", "publishes", "consumes", "calls_endpoint"}
TYPE_EDGES = {"references_type", "reads_constant"}
PROFILES = {"execution": "execution-1", "impact": "impact-1"}


class ContextSelectionError(ValueError):
    """A fail-closed service context selection diagnostic."""

    def __init__(self, diagnostic: dict):
        self.diagnostic = diagnostic
        super().__init__(diagnostic["message"])


def _release_mapping_pair(graph: KnowledgeGraph, mapping: Mapping, report: Mapping,
                          selected_contexts: Mapping[str, dict], repo_roots: Mapping[str, Path] | None
                          ) -> tuple[str | None, str | None, str | None]:
    """Return selected producer/consumer context IDs only for a bound proof."""
    from .build_model import HASH
    from .workspace import qualified

    mapping_id = mapping.get("id")
    producer, consumer = mapping.get("producer", {}), mapping.get("consumer", {})
    producer_repo, consumer_repo = producer.get("repo_id"), consumer.get("repo_id")
    build_context_id = producer.get("context_id")
    consumer_context_id = consumer.get("context_id")
    output_hash = mapping.get("output_sha256")
    if (report.get("status") != "CONTENT_VERIFIED"
            or report.get("producer_repo") != producer_repo
            or report.get("consumer_repo") != consumer_repo
            or report.get("sha256") != output_hash
            or not isinstance(output_hash, str) or not HASH.fullmatch(output_hash)
            or not isinstance(report.get("manifest_sha256"), str)
            or not HASH.fullmatch(report["manifest_sha256"])
            or not isinstance(report.get("producer_output_path"), str)
            or not report["producer_output_path"]
            or not isinstance(report.get("consumer_classpath_path"), str)
            or not report["consumer_classpath_path"]):
        return None, None, "RELEASE_MAPPING_REPORT_MISMATCH"

    producer_contexts = [context for context in selected_contexts.values()
                         if context.get("repo_id") == producer_repo
                         and context.get("build_context_id") == build_context_id]
    consumer_id = qualified(consumer_repo or "", consumer_context_id or "")
    consumer_context = selected_contexts.get(consumer_id)
    if len(producer_contexts) != 1 or consumer_context is None:
        return None, None, "RELEASE_MAPPING_CONTEXT_MISMATCH"
    producer_context = producer_contexts[0]

    output_node_id = "workspace:release-output:" + str(mapping_id)
    classpath_node_id = "workspace:classpath-artifact:" + str(mapping_id)
    nodes = {node.id: node for node in graph.nodes}
    output_node, classpath_node = nodes.get(output_node_id), nodes.get(classpath_node_id)
    output_metadata = output_node.metadata or {} if output_node else {}
    classpath_metadata = classpath_node.metadata or {} if classpath_node else {}
    manifest_source = "@" + str(producer_repo) + "/" + str(producer.get("manifest_path", ""))
    edge_bound = any(
        edge.kind == "supplies_classpath" and edge.source == output_node_id
        and edge.target == classpath_node_id and consumer_id in edge.context_ids
        and edge.evidence_kind == "SYMBOL_RESOLVED"
        for edge in graph.edges)
    graph_bound = (
        output_node is not None and output_node.kind == "workspace_release_output"
        and output_node.path == manifest_source
        and output_metadata.get("repo_id") == producer_repo
        and output_metadata.get("build_context_id") == build_context_id
        and output_metadata.get("sha256") == output_hash
        and classpath_node is not None and classpath_node.kind == "workspace_classpath_artifact"
        and classpath_metadata.get("repo_id") == consumer_repo
        and classpath_metadata.get("compiler_context_id") == consumer_context_id
        and classpath_metadata.get("sha256") == output_hash
        and producer_context.get("build_context_id") == build_context_id
        and consumer_context.get("repo_id") == consumer_repo
        and edge_bound
    )
    if not graph_bound:
        return None, None, "RELEASE_MAPPING_EVIDENCE_UNAVAILABLE"

    if repo_roots is not None:
        try:
            from .analysis_model import file_hash, safe_path
            from .inspection import artifact_hash
            producer_root, consumer_root = Path(repo_roots[producer_repo]), Path(repo_roots[consumer_repo])
            manifest = safe_path(producer_root, producer["manifest_path"])
            output_path, classpath_path = Path(report["producer_output_path"]), Path(report["consumer_classpath_path"])
            if not output_path.is_absolute():
                output_path = safe_path(producer_root, report["producer_output_path"])
            if not classpath_path.is_absolute():
                classpath_path = safe_path(consumer_root, report["consumer_classpath_path"])
            # Producer outputs belong to the producer checkout. Consumer
            # classpath entries may legitimately live in an external Maven or
            # Gradle cache, so bind that path to the exact selected context
            # entry instead of requiring checkout containment.
            output_resolved = output_path.resolve(strict=True)
            if (not output_resolved.is_relative_to(producer_root.resolve())
                    or output_path.is_symlink()):
                return None, None, "RELEASE_MAPPING_PATH_INVALID"
            classpath_entries = [item for item in consumer_context.get("classpath", [])
                                 if isinstance(item, dict) and item.get("sha256") == output_hash]
            if len(classpath_entries) != 1:
                return None, None, "RELEASE_MAPPING_PATH_INVALID"
            selected_classpath = Path(classpath_entries[0].get("path", ""))
            if not selected_classpath.is_absolute():
                selected_classpath = safe_path(consumer_root, str(selected_classpath))
            try:
                classpath_resolved = classpath_path.resolve(strict=True)
                selected_resolved = selected_classpath.resolve(strict=True)
            except OSError:
                return None, None, "RELEASE_MAPPING_PATH_INVALID"
            if (classpath_path.is_symlink() or selected_classpath.is_symlink()
                    or classpath_resolved != selected_resolved
                    or not classpath_resolved.is_file()):
                return None, None, "RELEASE_MAPPING_PATH_INVALID"
            if (file_hash(manifest) != report["manifest_sha256"]
                    or artifact_hash(output_path) != output_hash
                    or artifact_hash(classpath_path) != output_hash):
                return None, None, "RELEASE_MAPPING_STALE"
        except (KeyError, OSError, ValueError):
            return None, None, "RELEASE_MAPPING_STALE"
    return producer_context["id"], consumer_id, None


def select_service_contexts(graph: KnowledgeGraph, requests: list[dict], *,
                            scope: str, repo_roots: Mapping[str, Path] | None = None,
                            source_coverage: Mapping | None = None,
                            release_mapping: Mapping | None = None) -> dict:
    """Build an explicit, read-only service→repo/module→context projection.

    Each request identifies one service, repository, module and scope. If that
    tuple has multiple compiler variants, ``context_id`` is mandatory. A
    SOURCE_ONLY request must explicitly name the source coverage it represents.
    ``release_mapping`` is the workspace declaration plus its snapshot report;
    only CONTENT_VERIFIED artifact mappings can establish a mapped build pair.
    """
    from .analysis_model import digest

    if scope not in {"production", "test", "test_fixture", "development", "unknown"}:
        raise ContextSelectionError({"code": "INVALID_SCOPE", "message": "Select one concrete supported scope"})
    if not isinstance(requests, list) or not requests:
        raise ContextSelectionError({"code": "INVALID_SELECTION", "message": "At least one service selection is required"})
    if source_coverage is not None and not isinstance(source_coverage, Mapping):
        raise ContextSelectionError({"code": "INVALID_SOURCE_COVERAGE", "message": "Source coverage must be a workspace coverage object"})
    if release_mapping is not None and (
            not isinstance(release_mapping, Mapping)
            or not isinstance(release_mapping.get("declaration"), Mapping)
            or not isinstance(release_mapping.get("report"), Mapping)
            or type(release_mapping["declaration"].get("schema_version")) is not int
            or release_mapping["declaration"].get("schema_version") != 1
            or type(release_mapping["report"].get("schema_version")) is not int
            or release_mapping["report"].get("schema_version") != 1
            or not isinstance(release_mapping["declaration"].get("mappings"), list)
            or not isinstance(release_mapping["report"].get("mappings"), list)):
        raise ContextSelectionError({"code": "INVALID_RELEASE_MAPPING", "message": "Release selection requires a validated declaration and snapshot report"})
    if release_mapping is not None:
        mapping_ids: set[str] = set()
        for mapping in release_mapping["declaration"]["mappings"]:
            if (not isinstance(mapping, Mapping)
                    or not isinstance(mapping.get("id"), str) or not mapping["id"]
                    or mapping["id"] in mapping_ids
                    or not isinstance(mapping.get("producer"), Mapping)
                    or not isinstance(mapping.get("consumer"), Mapping)
                    or not isinstance(mapping.get("output_sha256"), str)):
                raise ContextSelectionError({"code": "INVALID_RELEASE_MAPPING",
                                             "message": "Release mapping declaration has malformed or duplicate selectors"})
            mapping_ids.add(mapping["id"])
            producer, consumer = mapping["producer"], mapping["consumer"]
            if (not all(isinstance(producer.get(key), str) and producer[key]
                        for key in ("repo_id", "manifest_path", "context_id"))
                    or not all(isinstance(consumer.get(key), str) and consumer[key]
                               for key in ("repo_id", "context_id"))):
                raise ContextSelectionError({"code": "INVALID_RELEASE_MAPPING",
                                             "message": "Release mapping declaration has incomplete producer or consumer selectors"})
    before = graph.to_dict()
    seen_services: set[str] = set()
    selected: list[dict] = []
    diagnostics: list[dict] = []
    selected_contexts: dict[str, dict] = {}
    for index, request in enumerate(requests):
        if not isinstance(request, Mapping):
            raise ContextSelectionError({"code": "INVALID_SELECTION", "path": f"requests[{index}]",
                                         "message": "Selection must be an object"})
        service, repo, module = (request.get("service_id"), request.get("repo_id"), request.get("module"))
        wanted_scope = request.get("scope", scope)
        mode = request.get("mode", "COMPILER")
        if (not all(isinstance(value, str) and value for value in (service, repo, module, wanted_scope))
                or service in seen_services or wanted_scope != scope):
            raise ContextSelectionError({"code": "INVALID_SELECTION", "path": f"requests[{index}]",
                                         "message": "Unique service_id, repo_id, module and matching scope are required"})
        seen_services.add(service)
        if mode == "SOURCE_ONLY":
            roots = set((source_coverage or {}).get("roots", []))
            artifacts = (source_coverage or {}).get("artifacts", [])
            covered = sorted(path for path in artifacts if isinstance(path, str)
                             and path.startswith("@" + repo + "/"))
            if repo not in roots or not covered:
                raise ContextSelectionError({"code": "SOURCE_COVERAGE_UNAVAILABLE", "service_id": service,
                                             "repo_id": repo, "message": "SOURCE_ONLY requires explicit source coverage for this repo"})
            selected.append({"service_id": service, "repo_id": repo, "module": module,
                             "scope": scope, "mode": "SOURCE_ONLY", "context_id": None,
                             "context_fingerprint": None, "source_coverage": covered,
                             "status": "PARTIAL", "module_coverage": "UNKNOWN",
                             "evidence_kind": "SOURCE_ONLY"})
            diagnostics.append({"code": "SOURCE_ONLY", "service_id": service,
                                "message": "Compiler context is unavailable; source coverage only"})
            diagnostics.append({"code": "SOURCE_MODULE_SCOPE_UNKNOWN", "service_id": service,
                                "message": "Repository source coverage does not prove module-level compiler coverage"})
            continue
        if mode != "COMPILER":
            raise ContextSelectionError({"code": "INVALID_SELECTION_MODE", "service_id": service,
                                         "message": "mode must be COMPILER or SOURCE_ONLY"})
        candidates = [context for context in graph.contexts
                      if context.get("analyzer_version") and context.get("repo_id") == repo
                      and context.get("module") == module and context.get("scope") == scope]
        chosen_id = request.get("context_id")
        if "context_id" in request and (not isinstance(chosen_id, str) or not chosen_id):
            raise ContextSelectionError({"code": "INVALID_CONTEXT_ID", "service_id": service,
                                         "message": "context_id must be a non-empty string when supplied"})
        choices = sorted(item["id"] for item in candidates if isinstance(item.get("id"), str))
        if chosen_id is None and len(candidates) > 1:
            raise ContextSelectionError({"code": "AMBIGUOUS_CONTEXT", "service_id": service,
                                         "choices": choices, "message": "Select one compiler context explicitly"})
        matches = [item for item in candidates if item.get("id") == chosen_id] if chosen_id else candidates
        if len(matches) != 1:
            raise ContextSelectionError({"code": "CONTEXT_UNAVAILABLE", "service_id": service,
                                         "choices": choices, "message": "No unique compiler context matches the requested repo/module/scope"})
        context = matches[0]
        if context.get("freshness") == "STALE":
            raise ContextSelectionError({"code": "STALE_CONTEXT", "service_id": service,
                                         "context_id": context["id"], "next_command": context.get("next_command", "kgmaker inspect"),
                                         "message": context.get("stale_reason", "Compiler context is stale")})
        if repo_roots and repo in repo_roots:
            try:
                # Check content-bound artifacts first so a hash mismatch gets
                # the precise diagnostic even on providers that wrap stale
                # WorkerError subclasses as an unavailable-file error.
                from .inspection import artifact_hash
                for artifact in context.get("classpath", []) + context.get("bytecode_artifacts", []):
                    if artifact_hash(Path(artifact["path"])) != artifact["sha256"]:
                        raise ValueError("STALE_INDEX: classpath changed; import/inspect again")
                from .graph_provider import validate_context_snapshot
                validation_context = dict(context)
                if context.get("id", "").startswith("repo:"):
                    # Workspace contexts qualify source paths as @repo/path.
                    # The provider validator consumes a single checkout.
                    prefix = "@" + repo + "/"
                    source_files = context.get("source_files", {})
                    if not isinstance(source_files, Mapping) or any(
                            not isinstance(path, str) or not path.startswith(prefix)
                            for path in source_files):
                        raise ValueError("STALE_INDEX: workspace source snapshot has invalid repo-qualified paths")
                    validation_context["source_files"] = {
                        path[len(prefix):]: checksum for path, checksum in source_files.items()}
                validate_context_snapshot(Path(repo_roots[repo]), validation_context)
            except (ValueError, OSError) as error:
                raise ContextSelectionError({"code": "STALE_CONTEXT", "service_id": service,
                                             "context_id": context["id"], "next_command": context.get("next_command", "kgmaker inspect"),
                                             "message": str(error)}) from error
        selected_contexts[context["id"]] = context
        fingerprint_data = {key: context.get(key) for key in (
            "id", "repo_id", "module", "source_set", "scope", "language", "build_context_id",
            "build_profiles", "spring_profiles", "manifest_hash", "dependency_model_hash",
            "config_fingerprint", "selection_key")}
        fingerprint_data["source_files"] = dict(sorted((context.get("source_files") or {}).items()))
        fingerprint_data["classpath"] = [
            {key: item.get(key) for key in ("sha256", "coordinates", "kind") if key in item}
            for item in context.get("classpath", [])]
        fingerprint_data["bytecode_artifacts"] = [
            {key: item.get(key) for key in ("sha256", "coordinates", "kind") if key in item}
            for item in context.get("bytecode_artifacts", [])]
        selected.append({"service_id": service, "repo_id": repo, "module": module,
                         "scope": scope, "mode": "COMPILER", "context_id": context["id"],
                         "context_fingerprint": digest(fingerprint_data),
                         "context_selection_key": context.get("selection_key"),
                         "profile": context.get("spring_profiles") or context.get("build_profiles"),
                         "status": ("CURRENT" if context.get("freshness") in
                                    {"CURRENT", "CONTENT_VERIFIED", "EXECUTION_BOUND"} else "UNKNOWN"),
                         "freshness": context.get("freshness", "UNKNOWN"),
                         "coverage": context.get("coverage", "UNKNOWN"),
                         "evidence_kind": context.get("mode", "UNKNOWN"),
                         "diagnostics": list(context.get("diagnostics", []))})

    # A content-verified release mapping proves only the declared artifact to
    # classpath relationship. It does not establish deployment/environment.
    compatible_pairs: list[dict] = []
    if release_mapping is not None:
        declaration = release_mapping.get("declaration", {})
        report = release_mapping.get("report", {})
        results: dict[str, list[Mapping]] = {}
        for item in report.get("mappings", []):
            if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                results.setdefault(item["id"], []).append(item)
        for mapping in declaration.get("mappings", []):
            if not isinstance(mapping, Mapping):
                raise ContextSelectionError({"code": "INVALID_RELEASE_MAPPING",
                                             "message": "Release mapping declaration row must be an object"})
            mapping_id = mapping.get("id")
            rows = results.get(mapping_id, [])
            if len(rows) != 1:
                diagnostics.append({"code": "RELEASE_MAPPING_REPORT_AMBIGUOUS" if rows else "RELEASE_MAPPING_REPORT_MISSING",
                                    "mapping_id": mapping_id,
                                    "message": "Release mapping report must contain exactly one row for the declaration"})
                continue
            producer_id, consumer_id, error_code = _release_mapping_pair(
                graph, mapping, rows[0], selected_contexts, repo_roots)
            if error_code:
                diagnostics.append({"code": error_code, "mapping_id": mapping_id,
                                    "message": "Declared release mapping has no matching verified report, context, and graph evidence"})
                continue
            producer_services = [item["service_id"] for item in selected
                                 if item.get("context_id") == producer_id]
            consumer_services = [item["service_id"] for item in selected
                                 if item.get("context_id") == consumer_id]
            if len(producer_services) != 1 or len(consumer_services) != 1:
                diagnostics.append({"code": "RELEASE_MAPPING_SERVICE_AMBIGUOUS", "mapping_id": mapping_id,
                                    "message": "A mapped context must identify exactly one selected service"})
                continue
            compatible_pairs.append({"mapping_id": mapping_id,
                                     "producer_service": producer_services[0],
                                     "consumer_service": consumer_services[0],
                                     "status": "CONTENT_VERIFIED"})
    deployment_status = "UNKNOWN"
    diagnostics.append({"code": "DEPLOYMENT_UNKNOWN",
                        "message": "Context/profile selection does not establish deployment or environment compatibility"})
    context_selection = {
        item["service_id"]: {"repo_id": item["repo_id"], "module": item["module"],
                             "scope": item["scope"], "context_id": item["context_id"],
                             "context_fingerprint": item["context_fingerprint"]}
        for item in selected
    }
    result = {"scope": scope, "services": sorted(selected, key=lambda item: item["service_id"]),
              "context_selection": context_selection,
              "release_compatibility": compatible_pairs, "deployment_compatibility": deployment_status,
              "diagnostics": diagnostics,
              "fingerprint": digest({"scope": scope, "context_selection": context_selection,
                                     "services": sorted(selected, key=lambda item: item["service_id"]),
                                     "release_compatibility": compatible_pairs})}
    if graph.to_dict() != before:
        raise RuntimeError("Context selection mutated its graph input")
    return result


def select_context(graph: KnowledgeGraph, scope: str, context_id: str | None = None, *,
                   allow_stale: bool = False) -> str | None:
    """Choose one usable compiler context or fail on an ambiguous variant set."""
    all_contexts = [item for item in graph.contexts if item.get("analyzer_version")]
    if context_id is not None:
        selected = [item for item in all_contexts if item.get("id") == context_id]
        if len(selected) != 1:
            raise ValueError("Unknown compiler context; available: "
                             + ", ".join(sorted(item["id"] for item in all_contexts)))
        if selected[0].get("freshness") == "STALE" and not allow_stale:
            raise ValueError("STALE_INDEX: " + str(selected[0].get("stale_reason", "context is stale"))
                             + "; run `" + str(selected[0].get("next_command", "kgmaker inspect")) + "`")
        if scope != "all" and selected[0].get("scope") != scope:
            raise ValueError("Compiler context is outside selected scope")
        return context_id
    active = [item for item in all_contexts
              if item.get("freshness") != "STALE"
              and (scope == "all" or item.get("scope") == scope)]
    if len(active) > 1:
        raise ValueError("Explicit --context required; available: "
                         + ", ".join(sorted(item["id"] for item in active)))
    return active[0]["id"] if active else None


def project(graph: KnowledgeGraph, scope: str = "production", *, view: str = "architecture", context_id: str | None = None) -> KnowledgeGraph:
    if scope not in {"production", "test", "test_fixture", "development", "unknown", "all"}:
        raise ValueError("invalid scope: " + scope)
    # Implementation episodes are repository history, not source-set code.
    # Keep them in the default documentation projection even though their
    # synthetic nodes have no compiler scope.
    nodes = [n for n in graph.nodes if scope == "all" or n.scope == scope or n.kind == "implementation_episode"]
    if context_id is not None:
        compiler_ids = {item.get("id") for item in [*graph.symbols, *graph.call_sites]}
        compiler_ids.update(item.get("method") for item in graph.cfgs)
        selected_ids = {item.get("id") for item in graph.symbols if item.get("context_id") == context_id}
        selected_ids.update(item.get("id") for item in graph.call_sites if item.get("context_id") == context_id)
        selected_ids.update(item.get("method") for item in graph.cfgs if item.get("context_id") == context_id)
        selected_ids.update(identity for edge in graph.edges if context_id in edge.context_ids
                            for identity in (edge.source, edge.target))
        nodes = [node for node in nodes if node.id not in compiler_ids or node.id in selected_ids]
    ids = {n.id for n in nodes}
    compiler_context_ids = {item.get("id") for item in graph.contexts
                            if item.get("analyzer_version") and isinstance(item.get("id"), str)}
    edges = [e for e in graph.edges if e.source in ids and e.target in ids and (
        context_id is None
        or context_id in e.context_ids
        or not (set(e.context_ids) & compiler_context_ids)
    )]
    if view == "calls":
        edges = [e for e in edges if e.kind in EXECUTION_EDGES or e.kind == "calls"]
    elif view == "configuration":
        edges = [e for e in edges if e.kind in {"configured_by", "resolves_property", "conditional_on",
                                                "imports_configuration", "uses_import_selector", "selects_import", "may_select_import",
                                                "defines_bean", "injects_bean", "advised_by",
                                                "declares_entrypoint", "bypasses_proxy"}]
    elif view == "data-flow":
        edges = [e for e in edges if e.kind in {"reads_field", "writes_field", "argument_to_parameter", "returns_to",
                                                "maps_field", "maps_to_table", "maps_to_column", "declared_on_table",
                                                "resolves_to_schema_table", "resolves_to_schema_column", "repository_for",
                                                "declares_query", "defines_named_query", "uses_named_query",
                                                "query_reads", "query_writes", "query_deletes", "filters_by",
                                                "orders_by", "returns_entity", "returns_projection", "persistence_intent"}]
    elif view == "integrations":
        edges = [e for e in edges if e.kind in SIDE_EFFECTS | {"implements_contract", "exposes_endpoint",
                                                               "declares_entrypoint", "uses_external_service"}]
    sites = []
    for original in graph.call_sites:
        if original.get("id") not in ids or original.get("caller") not in ids:
            continue
        if context_id is not None and original.get("context_id") != context_id:
            continue
        site = dict(original)
        target = site.get("declared_target")
        if target is not None and target not in ids:
            site.update(declared_target=None, omitted_declared_target=target,
                        resolution_reason="RESOLVED_TARGET_EXCLUDED_BY_SCOPE")
        site["dispatch_candidates"] = [c for c in site.get("dispatch_candidates", []) if c in ids]
        sites.append(site)
    selected_evidence = {identity for edge in edges for identity in edge.evidence_ids}
    selected_evidence.update(identity for site in sites for identity in site.get("evidence_ids", []))
    selected_cfgs = [c for c in graph.cfgs if c.get("method") in ids and (context_id is None or c.get("context_id") == context_id)]
    selected_evidence.update(identity for cfg in selected_cfgs for identity in cfg.get("evidence_ids", []))
    return replace(graph, nodes=nodes, edges=edges,
                   files={p: h for p, h in graph.files.items() if any(n.path == p for n in nodes)},
                   contexts=[c for c in graph.contexts if (scope == "all" or c.get("scope") == scope) and (context_id is None or c.get("id") == context_id)],
                   diagnostics=[d for d in graph.diagnostics if not (d.get("path") or d.get("source_file")) or (d.get("path") or d.get("source_file")) in {n.path for n in nodes}],
                   evidence=[e for e in graph.evidence if e.get("id") in selected_evidence],
                   symbols=[s for s in graph.symbols if s.get("id") in ids], call_sites=sites,
                   cfgs=selected_cfgs)


def rank(graph: KnowledgeGraph, entry: str | None = None, profile: str = "execution", scope: str = "production") -> dict:
    if profile not in PROFILES:
        raise ValueError("unsupported ranking profile")
    graph = project(graph, scope)
    nodes = {n.id: n for n in graph.nodes}
    if entry is not None and entry not in nodes:
        raise ValueError("entry is absent from selected scope")
    adjacency = defaultdict(set)
    degree, references, effects = defaultdict(int), defaultdict(int), defaultdict(int)
    evidence = defaultdict(list)
    for e in graph.edges:
        proven_call = e.evidence_kind in {"SYMBOL_RESOLVED", "DISPATCH_CANDIDATE", "FRAMEWORK_DERIVED", "RUNTIME_OBSERVED"}
        if e.kind in EXECUTION_EDGES and (proven_call or e.kind == "declares_call"):
            adjacency[e.source].add(e.target)
            degree[e.source] += 1
            degree[e.target] += 1
            evidence[e.source].append(asdict(e))
        if e.kind in TYPE_EDGES:
            references[e.target] += 1
        if e.kind in SIDE_EFFECTS and proven_call:
            effects[e.source] += 1
            evidence[e.source].append(asdict(e))
    visited = set()
    queue = deque([entry] if entry else [])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(sorted(adjacency[node] - visited))
    rows = []
    for n in graph.nodes:
        if n.kind not in {"method", "function", "constructor", "component", "bytecode_method", "source_initializer", "class", "enum", "interface", "type"} or n.role not in {"executable_code", "contract"}:
            continue
        breakdown = {"entry_relevance": 10 if n.id == entry else 0,
                     "execution_path": 5 if n.id in visited else 0,
                     "execution_centrality": min(degree[n.id], 10),
                     "side_effects": min(effects[n.id], 10),
                     "type_reference_impact": references[n.id] if profile == "impact" else 0}
        rows.append({"id": n.id, "score": sum(breakdown.values()), "breakdown": breakdown,
                     "shared_references": references[n.id], "evidence": evidence[n.id]})
    rows.sort(key=lambda r: (-r["score"], r["id"]))
    return {"profile": PROFILES[profile], "scope": scope, "entry": entry, "status": "PARTIAL",
            "contexts": graph.contexts, "results": rows,
            "limitations": ["Ranking expresses graph evidence, not business importance or path feasibility.",
                            "Legacy name-match calls have zero execution contribution."]}

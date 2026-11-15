"""Scope projections and deterministic, purpose-specific ranking.

Navigation hints and execution evidence remain separate. References never
contribute to execution centrality, even for heavily reused DTOs and enums.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

from .model import KnowledgeGraph
from .architecture_model import EVIDENCE_KINDS, EVIDENCE_POLARITIES, FRESHNESS_STATUSES, aggregate_view_edges

EXECUTION_EDGES = {"resolves_to", "may_dispatch_to", "declares_call", "observed_dispatch_to"}
SIDE_EFFECTS = {"persistence_intent", "query_writes", "query_deletes", "publishes", "consumes", "calls_endpoint"}
TYPE_EDGES = {"references_type", "reads_constant"}
PROFILES = {"execution": "execution-2", "impact": "impact-2"}
EXECUTABLE_NODE_KINDS = {"method", "function", "constructor", "component", "bytecode_method", "source_initializer", "call_site"}
CURRENT_COMPILER_FRESHNESS = {"CONTENT_VERIFIED", "CURRENT", "EXECUTION_BOUND"}
COMPILER_MODES = {"BUILD_IMPORT", "BUILD_EXECUTE"}
COMPILER_ORIGINS = {"LOCAL_COMPILER_INPUTS", "LOCAL_TRUSTED", "SUPPLIED_EXPORT_UNVERIFIED"}


def _compiler_authority(context: Mapping[str, Any], files: Mapping[str, str]) -> bool:
    """Recognize the existing inspection producer tuple, not a build label.

    This checks captured authority; public indexed() separately verifies files,
    source selection and worker distribution on disk. A supplied build export
    only participates after an actual inspection has added compiler metadata.
    """
    worker = context.get('worker')
    sources = context.get('source_files')
    artifacts = context.get('bytecode_artifacts', [])
    def checksum(value):
        return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
    source_bound = (isinstance(sources, Mapping) and bool(sources)
                    and all(isinstance(path, str) and checksum(value) and files.get(path) == value
                            for path, value in sources.items()))
    bytecode_bound = (isinstance(sources, Mapping) and not sources and isinstance(artifacts, list)
                      and bool(artifacts) and all(isinstance(a, Mapping) and checksum(a.get('sha256'))
                                                for a in artifacts))
    return (context.get('mode') in COMPILER_MODES
            and context.get('origin_trust') in COMPILER_ORIGINS
            and isinstance(context.get('analyzer_version'), str) and bool(context['analyzer_version'])
            and context.get('freshness') in CURRENT_COMPILER_FRESHNESS
            and isinstance(worker, Mapping) and type(worker.get('protocol_version')) is int
            and worker.get('protocol_version') == 1
            and isinstance(worker.get('worker'), str) and bool(worker['worker'])
            and isinstance(worker.get('compiler_version'), str) and bool(worker['compiler_version'])
            and (source_bound or bytecode_bound))



def _canonical_kind(value: Any) -> str:
    return value if isinstance(value, str) and value in EVIDENCE_KINDS else "UNKNOWN"


def _canonical_polarity(value: Any) -> str:
    return value if isinstance(value, str) and value in EVIDENCE_POLARITIES else "UNKNOWN"


def _canonical_freshness(value: Any) -> str:
    return value if isinstance(value, str) and value in FRESHNESS_STATUSES else "UNKNOWN"


def _summarize_view_evidence(refs, provenance):
    records = [provenance[ref] for ref in refs if ref in provenance]
    kinds = sorted({_canonical_kind(item.get("evidence_kind")) for item in records} or {"UNKNOWN"})
    supporting = sorted({item["id"] for item in records if _canonical_polarity(item.get("polarity")) == "SUPPORTING"})
    contradicting = sorted({item["id"] for item in records if _canonical_polarity(item.get("polarity")) == "CONTRADICTING"})
    unknown = sorted(set(refs) - set(supporting) - set(contradicting))
    freshness_values = [_canonical_freshness(item.get("freshness")) for item in records]
    freshness = ("STALE" if "STALE" in freshness_values else
                 "CURRENT" if freshness_values and all(value == "CURRENT" for value in freshness_values)
                 and len(records) == len(set(refs)) else "UNKNOWN")
    return {"evidence_kinds": kinds, "freshness": freshness,
            "supporting_refs": supporting, "contradicting_refs": contradicting,
            "unknown_refs": unknown}


class ContextSelectionError(ValueError):
    """A fail-closed service context selection diagnostic."""

    def __init__(self, diagnostic: dict):
        self.diagnostic = diagnostic
        super().__init__(diagnostic["message"])


class ServiceInventoryError(ValueError):
    """Invalid ownership/provider input for the T008 service inventory."""

    def __init__(self, diagnostic: dict):
        self.diagnostic = diagnostic
        super().__init__(diagnostic["message"])


def project_service_inventory(workspace: Mapping[str, Any], graph: KnowledgeGraph, *,
                              scope: str = "production",
                              service_labels: Mapping[str, str] | None = None,
                              selected_contexts: Mapping[tuple[str, str, str], str] | None = None,
                              source_coverage: Mapping | None = None):
    """Project explicitly owned services and declared external systems.

    ``workspace`` must be the loaded workspace returned by ``load_workspace``;
    ``graph`` must be its content-bound workspace/provider snapshot. Compiler
    contexts are selected through T006, ownership is resolved through T007, and
    no framework annotation or configuration value creates an inventory node.
    ``service_labels`` affects presentation only. ``selected_contexts`` keys are
    ``(service_id, repo_id, module)`` and pin a compiler variant through T006.
    """
    import copy

    from .analysis_model import digest, AnalysisError
    from .context_roles import classify_context_role
    from .architecture_model import ViewDocument, ViewEdge, ViewNode
    from .model import KnowledgeGraph as Graph
    from .workspace import load_workspace, resolve_service_ownership

    def fail(code: str, message: str) -> None:
        raise ServiceInventoryError({"code": code, "message": message})

    supported_scopes = {"production", "test", "test_fixture", "development", "unknown"}
    if not isinstance(scope, str) or scope not in supported_scopes:
        fail("INVALID_SCOPE", "Select one concrete supported inventory scope")
    if not isinstance(workspace, Mapping) or not isinstance(graph, Graph):
        fail("INVALID_SNAPSHOT", "Inventory requires a loaded workspace and KnowledgeGraph snapshot")
    manifest_path = workspace.get("_manifest_path")
    manifest_hash = workspace.get("_manifest_hash")
    if not isinstance(manifest_path, str) or not isinstance(manifest_hash, str):
        fail("UNVERIFIED_WORKSPACE", "Workspace must come from load_workspace")
    try:
        verified_workspace = load_workspace(Path(manifest_path))
        Graph.from_dict(graph.to_dict())
    except (OSError, ValueError, TypeError, KeyError) as error:
        fail("INVALID_SNAPSHOT", "Cannot validate workspace/provider snapshot: " + str(error))
    if (verified_workspace.get("_manifest_hash") != manifest_hash
            or graph.files.get("@workspace/manifest.json") != manifest_hash):
        fail("WORKSPACE_SNAPSHOT_MISMATCH", "Workspace manifest hash does not match the provider snapshot")
    declaration = verified_workspace.get("service_ownership")
    workspace_id = verified_workspace.get("workspace_id")
    if not isinstance(workspace_id, str) or not workspace_id:
        fail("INVALID_WORKSPACE_ID", "Workspace snapshot has no stable workspace_id")
    ownership_services = (declaration or {}).get("services", []) if isinstance(declaration, Mapping) else []
    owner_by_id = {item["id"]: item for item in ownership_services}
    if len(owner_by_id) != len(ownership_services):
        fail("INVALID_OWNERSHIP", "Ownership service IDs must be unique")

    labels = {} if service_labels is None else service_labels
    if (not isinstance(labels, Mapping)
            or any(key not in owner_by_id or not isinstance(value, str) or not value.strip()
                   for key, value in labels.items())):
        fail("INVALID_SERVICE_LABEL", "Display labels must map declared service IDs to non-empty strings")
    pinned = {} if selected_contexts is None else selected_contexts
    if (not isinstance(pinned, Mapping)
            or any(not isinstance(key, tuple) or len(key) != 3
                   or any(not isinstance(part, str) or not part for part in key)
                   or key[0] not in owner_by_id or not isinstance(value, str) or not value
                   for key, value in pinned.items())):
        fail("INVALID_CONTEXT_SELECTION", "Context selectors must map (service_id, repo_id, module) to context IDs")

    before_workspace = copy.deepcopy(dict(workspace))
    before_graph = graph.to_dict()
    diagnostics: list[dict] = []
    provenance: dict[str, dict] = {}
    manifest_evidence_id = "ev:workspace-manifest:" + workspace_id
    provenance[manifest_evidence_id] = {
        "id": manifest_evidence_id, "evidence_kind": "SOURCE_ONLY",
        "freshness": "CURRENT", "polarity": "UNKNOWN",
        "source_id": "@workspace/manifest.json", "content_hash": manifest_hash,
    }

    # Use the upstream T007 resolver on snapshot-owned source paths and module
    # identities. SOURCE_ONLY workspace contexts have no compiler source_files;
    # their roots come only from the exact repository-qualified artifact list
    # and matching provider source nodes in the supplied workspace snapshot.
    coverage_artifacts: set[str] = set()
    if source_coverage is not None:
        artifacts = source_coverage.get("artifacts") if isinstance(source_coverage, Mapping) else None
        if not isinstance(artifacts, list) or any(not isinstance(path, str) for path in artifacts):
            fail("INVALID_SOURCE_COVERAGE", "Source coverage must contain a list of qualified artifact paths")
        coverage_artifacts = set(artifacts)
    source_nodes_by_path: dict[str, list] = defaultdict(list)
    if coverage_artifacts:
        for node in graph.nodes:
            path = getattr(node, "path", None)
            # Only the provider's file node establishes source membership here;
            # declarations and arbitrary symbols inherit no scope on their own.
            if (getattr(node, "kind", None) == "file" and isinstance(path, str)
                    and path in coverage_artifacts and path in graph.files):
                source_nodes_by_path[path].append(node)
    contexts_by_service: dict[str, dict[tuple[str, str], list[dict]]] = defaultdict(lambda: defaultdict(list))
    all_owner_scopes: dict[str, set[str]] = defaultdict(set)
    ambiguous_by_service: dict[str, list[dict]] = defaultdict(list)
    context_records = {context['id']: context for context in graph.contexts}
    for context in graph.contexts:
        role, reason = classify_context_role(context, workspace=verified_workspace, contexts=context_records)
        if role in {'WORKSPACE_DERIVED', 'UNKNOWN'}:
            if context.get('id') in pinned.values():
                fail('INVALID_CONTEXT_SELECTION', 'A derived or unknown context cannot be pinned as service source')
            if reason is not None:
                diagnostics.append({'code': 'UNKNOWN_CONTEXT_ROLE', 'context_id': context.get('id'),
                                    'reason': reason, 'message': 'Derived declaration is not service source authority'})
            continue
        repo_id, context_id = context.get("repo_id"), context.get("id")
        if not isinstance(repo_id, str) or not repo_id or not isinstance(context_id, str) or not context_id:
            continue
        module = context.get("module")
        module = module if isinstance(module, str) and module else ""
        source_files = context.get("source_files", {})
        paths = list(source_files) if isinstance(source_files, Mapping) and source_files else []
        if not paths and context.get("mode") == "SOURCE_ONLY":
            # Workspace snapshot paths carry an authoritative repo qualifier;
            # the context itself supplies the exact repository realm and scope.
            prefix = "@" + repo_id + "/"
            context_scope = context.get("scope")
            paths = sorted(path for path, nodes_at_path in source_nodes_by_path.items()
                           if path.startswith(prefix) and context_scope == scope and any(
                               getattr(node, "scope", None) == context_scope for node in nodes_at_path))
        owner_ids: set[str] = set()
        # Workspace projection qualifies a symbol's ID/path/context but does not
        # add repo/module fields to that public symbol. Join only by the exact
        # context_id, then enrich those fields from the selected context. A
        # dependency or bytecode symbol without a local source snapshot path is
        # intentionally not treated as owned service code.
        for symbol in graph.symbols:
            if symbol.get("context_id") != context_id:
                continue
            source_path = symbol.get("path")
            if (not isinstance(source_files, Mapping) or not isinstance(source_path, str)
                    or source_path not in source_files):
                continue
            if ((symbol.get("repo_id") is not None and symbol.get("repo_id") != repo_id)
                    or (symbol.get("module") is not None and symbol.get("module") != module)):
                diagnostics.append({"code": "SYMBOL_CONTEXT_IDENTITY_MISMATCH",
                                    "context_id": context_id, "repo_id": repo_id,
                                    "module": module,
                                    "message": "Compiler symbol identity disagrees with its exact provider context"})
                continue
            enriched_symbol = {**symbol, "repo_id": repo_id, "module": module}
            try:
                result = resolve_service_ownership(enriched_symbol, declaration, context_id=context_id)
            except AnalysisError as error:
                fail('INVALID_OWNERSHIP', str(error))
            owner_ids.update(result["candidate_owner_ids"])
        for source_path in paths:
            try:
                result = resolve_service_ownership(
                    {"repo_id": repo_id, "path": source_path, "module": module or None,
                     "context_id": context_id}, declaration, context_id=context_id)
            except AnalysisError as error:
                fail('INVALID_OWNERSHIP', str(error))
            owner_ids.update(result["candidate_owner_ids"])
        for service_id in owner_ids:
            context_scope = context.get("scope")
            if isinstance(context_scope, str):
                all_owner_scopes[service_id].add(context_scope)
            if len(owner_ids) > 1:
                ambiguous_by_service[service_id].append({
                    "repo_id": repo_id, "module": module, "scope": context_scope,
                    "context_id": context_id, "candidate_owner_ids": sorted(owner_ids),
                })
            elif context_scope == scope:
                contexts_by_service[service_id][(repo_id, module)].append(context)

    for item in graph.diagnostics:
        code = item.get("code", "") if isinstance(item, Mapping) else str(item)
        if any(term in str(code).upper() for term in ("TRUNCAT", "UNRESOLVED", "AMBIGUOUS", "OMITTED", "LIMIT")):
            diagnostics.append(dict(item) if isinstance(item, Mapping) else {
                "code": "PROVIDER_BOUNDARY_UNKNOWN", "message": str(item)})

    selected_rows: dict[str, list[dict]] = defaultdict(list)
    context_statuses: dict[str, list[str]] = defaultdict(list)
    used_pins: set[tuple[str, str, str]] = set()
    repo_roots = {repo["id"]: Path(repo["_root"])
                  for repo in verified_workspace["repositories"] if "_root" in repo}
    for service_id, ambiguous_contexts in ambiguous_by_service.items():
        for context in ambiguous_contexts:
            if context.get("scope") != scope:
                continue
            selected_rows[service_id].append({
                "repo_id": context["repo_id"], "module": context["module"], "scope": scope,
                "status": "AMBIGUOUS", "context_id": None,
                "candidate_context_ids": [context["context_id"]],
                "candidate_owner_ids": context["candidate_owner_ids"],
            })
            context_statuses[service_id].append("AMBIGUOUS")
            diagnostics.append({"code": "AMBIGUOUS_SERVICE_OWNERSHIP", "service_id": service_id,
                                "repo_id": context["repo_id"], "module": context["module"],
                                "context_id": context["context_id"],
                                "candidate_owner_ids": context["candidate_owner_ids"],
                                "message": "Provider context matches multiple explicit ownership declarations"})
            context_record = next((item for item in graph.contexts if item.get("id") == context["context_id"]), {})
            evidence_id = "ev:compiler-context:" + context["context_id"]
            provenance[evidence_id] = {
                "id": evidence_id, "evidence_kind": _canonical_kind(context_record.get("mode")),
                "freshness": _canonical_freshness(context_record.get("freshness")),
                "polarity": _canonical_polarity(context_record.get("polarity", "UNKNOWN")),
                "source_id": context["context_id"], "content_hash": digest(context_record),
            }

    for service_id, groups in contexts_by_service.items():
        for (repo_id, module), candidates in groups.items():
            key = (service_id, repo_id, module)
            requested_context = pinned.get(key)
            if key in pinned:
                used_pins.add(key)
            candidate_ids = sorted({item["id"] for item in candidates})
            if not module:
                source_only = all(item.get("mode") == "SOURCE_ONLY" for item in candidates)
                status = "PARTIAL" if source_only else "UNKNOWN"
                diagnostics.append({"code": "MODULE_ID_UNAVAILABLE", "service_id": service_id,
                                    "repo_id": repo_id, "candidate_context_ids": candidate_ids,
                                    "message": "Source ownership is known but no compiler module identity is available"})
                context_statuses[service_id].append(status)
                selected_rows[service_id].append({"repo_id": repo_id, "module": None,
                                                  "scope": scope, "status": status,
                                                  "evidence_kind": "SOURCE_ONLY" if source_only else "UNKNOWN",
                                                  "module_coverage": "UNKNOWN",
                                                  "context_id": None, "candidate_context_ids": candidate_ids})
                if source_only:
                    for context in candidates:
                        evidence_id = "ev:source-context:" + context["id"]
                        provenance[evidence_id] = {
                            "id": evidence_id, "evidence_kind": "SOURCE_ONLY",
                            "freshness": "UNKNOWN", "polarity": "UNKNOWN",
                            "source_id": context["id"],
                            "content_hash": context.get("content_hash") or digest(context),
                        }
                else:
                    for context in candidates:
                        evidence_id = "ev:compiler-context:" + context["id"]
                        provenance[evidence_id] = {
                            "id": evidence_id, "evidence_kind": _canonical_kind(context.get("mode")),
                            "freshness": _canonical_freshness(context.get("freshness")),
                            "polarity": _canonical_polarity(context.get("polarity", "UNKNOWN")),
                            "source_id": context["id"], "content_hash": digest(context),
                        }
                continue
            source_only = all(item.get("mode") == "SOURCE_ONLY" or not item.get("analyzer_version")
                              for item in candidates)
            if source_only and requested_context is not None:
                fail("INVALID_CONTEXT_SELECTION", "A compiler context cannot be pinned for SOURCE_ONLY coverage")
            request = {"service_id": service_id, "repo_id": repo_id, "module": module,
                       "scope": scope, "mode": "SOURCE_ONLY" if source_only else "COMPILER"}
            if requested_context is not None:
                request["context_id"] = requested_context
            try:
                selection = select_service_contexts(
                    graph, [request], scope=scope, repo_roots=repo_roots or None,
                    source_coverage=source_coverage)
            except ContextSelectionError as error:
                diagnostic = dict(error.diagnostic)
                diagnostic.update({"service_id": service_id, "repo_id": repo_id, "module": module,
                                   "candidate_context_ids": candidate_ids})
                diagnostics.append(diagnostic)
                code = diagnostic.get("code", "CONTEXT_UNAVAILABLE")
                status = "AMBIGUOUS" if code == "AMBIGUOUS_CONTEXT" else "STALE" if code == "STALE_CONTEXT" else "UNKNOWN"
                context_statuses[service_id].append(status)
                selected_rows[service_id].append({"repo_id": repo_id, "module": module,
                                                  "scope": scope, "status": status,
                                                  "evidence_kind": "SOURCE_ONLY" if source_only else
                                                  _canonical_kind(candidates[0].get("mode")),
                                                  "context_id": None, "candidate_context_ids": candidate_ids})
                for context in candidates:
                    evidence_id = ("ev:source-context:" if source_only else "ev:compiler-context:") + context["id"]
                    provenance[evidence_id] = {
                        "id": evidence_id,
                        "evidence_kind": "SOURCE_ONLY" if source_only else _canonical_kind(context.get("mode")),
                        "freshness": _canonical_freshness(context.get("freshness")),
                        "polarity": _canonical_polarity(context.get("polarity", "UNKNOWN")),
                        "source_id": context["id"], "content_hash": digest(context.get("source_files", context)),
                    }
                continue
            row = dict(selection["services"][0])
            row["candidate_context_ids"] = candidate_ids
            selected_rows[service_id].append(row)
            context_statuses[service_id].append(row.get("status", "UNKNOWN"))
            for context_diagnostic in row.get("diagnostics", []):
                if isinstance(context_diagnostic, Mapping):
                    diagnostics.append({**dict(context_diagnostic), "service_id": service_id,
                                        "context_id": row.get("context_id")})
            if row.get("context_id") and row.get("context_fingerprint"):
                evidence_id = "ev:compiler-context:" + row["context_id"]
                provenance[evidence_id] = {
                    "id": evidence_id, "evidence_kind": _canonical_kind(row.get("evidence_kind")),
                    "freshness": _canonical_freshness(row.get("freshness", row.get("status"))),
                    "polarity": _canonical_polarity(row.get("polarity", "UNKNOWN")),
                    "source_id": row["context_id"], "content_hash": row["context_fingerprint"],
                }
            elif source_only:
                for context in candidates:
                    evidence_id = "ev:source-context:" + context["id"]
                    provenance[evidence_id] = {
                        "id": evidence_id, "evidence_kind": "SOURCE_ONLY",
                        "freshness": "UNKNOWN", "polarity": "UNKNOWN",
                        "source_id": context["id"],
                        "content_hash": digest(context.get("source_files", {})),
                    }

    unused_pins = set(pinned) - used_pins
    if unused_pins:
        fail("UNKNOWN_CONTEXT_SELECTION", "A pinned context does not match any declared service/repo/module")

    nodes: list[ViewNode] = []
    edges: list[ViewEdge] = []
    context_selection: dict[str, dict] = {}
    external_ids: set[str] = set()
    for service_id, rows in sorted(selected_rows.items()):
        if not rows:
            continue
        service = owner_by_id[service_id]
        statuses = context_statuses[service_id]
        service_status = ("AMBIGUOUS" if "AMBIGUOUS" in statuses else
                          "STALE" if "STALE" in statuses else
                          "UNKNOWN" if "UNKNOWN" in statuses else
                          "PARTIAL" if "PARTIAL" in statuses else "CURRENT")
        refs = [manifest_evidence_id]
        for row in rows:
            context_id = row.get("context_id")
            if context_id:
                evidence_id = "ev:compiler-context:" + context_id
                if evidence_id in provenance:
                    refs.append(evidence_id)
            else:
                for candidate_id in row.get("candidate_context_ids", []):
                    for prefix in ("ev:source-context:", "ev:compiler-context:"):
                        evidence_id = prefix + candidate_id
                        if evidence_id in provenance:
                            refs.append(evidence_id)
        service_node_id = f"service:{service_id}"
        external_system_ids = sorted(system["id"] for system in service["external_systems"])
        module_ids = sorted({row["module"] for row in rows if isinstance(row.get("module"), str)})
        repo_ids = sorted({row["repo_id"] for row in rows})
        selected_ids = sorted({row["context_id"] for row in rows if row.get("context_id")})
        summary = _summarize_view_evidence(refs, provenance)
        # The service's explicit manifest identity remains resolved even when
        # its selected compiler context is partial/stale; that state is carried
        # independently by freshness, context_status, and coverage.
        resolution_status = "AMBIGUOUS" if service_status == "AMBIGUOUS" else "RESOLVED"
        nodes.append(ViewNode(
            id=service_node_id, kind="service", label=labels.get(service_id, service_id),
            original_ids=(service_id,), evidence_refs=tuple(sorted(set(refs))),
            attributes={"scope": scope, "context_status": service_status,
                        "repo_ids": repo_ids, "modules": module_ids, "context_ids": selected_ids,
                        "external_system_ids": external_system_ids,
                        "evidence_kinds": summary["evidence_kinds"]},
            evidence_kinds=tuple(summary["evidence_kinds"]), resolution_status=resolution_status,
            freshness=summary["freshness"], supporting_refs=tuple(summary["supporting_refs"]),
            contradicting_refs=tuple(summary["contradicting_refs"]), unknown_refs=tuple(summary["unknown_refs"]),
        ))
        context_selection[service_id] = {"scope": scope, "status": service_status,
                                         "contexts": sorted(rows, key=lambda item: (
                                             item.get("repo_id", ""), item.get("module") or "",
                                             item.get("context_id") or ""))}
        for system_id in external_system_ids:
            external_node_id = f"external-system:{system_id}"
            external_ids.add(system_id)
            if not any(node.id == external_node_id for node in nodes):
                nodes.append(ViewNode(
                    id=external_node_id, kind="external_system", label=system_id,
                    original_ids=(system_id,), evidence_refs=(manifest_evidence_id,),
                    attributes={"implementation_status": "UNKNOWN", "checkout_status": "UNKNOWN",
                                "endpoint_ids": [], "scope": scope},
                    evidence_kinds=("SOURCE_ONLY",), resolution_status="RESOLVED", freshness="CURRENT",
                    unknown_refs=(manifest_evidence_id,),
                ))
            edge_id = f"edge:declares-external-system:{service_id}:{system_id}"
            edges.append(ViewEdge(
                id=edge_id, source=service_node_id, target=external_node_id,
                relation="declares_external_system", original_ids=(service_id, system_id),
                evidence_refs=(manifest_evidence_id,), resolution_status="RESOLVED",
                attributes={"implementation_status": "UNKNOWN", "scope": scope,
                            "context_ids": selected_ids},
                evidence_kinds=("SOURCE_ONLY",), freshness="CURRENT",
                unknown_refs=(manifest_evidence_id,),
            ))

    if declaration is None:
        diagnostics.append({"code": "OWNERSHIP_DECLARATION_MISSING",
                            "message": "No explicit service_ownership declaration is available"})
    else:
        for service_id in sorted(owner_by_id):
            if service_id in selected_rows:
                continue
            scopes = sorted(all_owner_scopes.get(service_id, set()))
            if scopes and scope not in scopes:
                # Known out-of-scope contexts are intentionally filtered.
                continue
            diagnostics.append({"code": "SERVICE_CONTEXT_UNAVAILABLE", "service_id": service_id,
                                "available_scopes": scopes,
                                "message": "Explicit service ownership has no provider context in the selected scope"})
    diagnostics.append({"code": "DEPLOYMENT_UNKNOWN",
                        "message": "A source/compiler context does not prove deployment or runtime availability"})

    edge_aggregation = aggregate_view_edges(edges, tuple(provenance.values()), scope=scope,
                                            diagnostics=diagnostics)
    edges = list(edge_aggregation["edges"])
    diagnostics = list(edge_aggregation["diagnostics"])

    if not selected_rows:
        coverage_status = "UNKNOWN"
    elif diagnostics or external_ids or any(status != "CURRENT" for values in context_statuses.values() for status in values):
        coverage_status = "PARTIAL"
    else:
        coverage_status = "COMPLETE_WITHIN_SELECTED_SCOPE"
    context_rows = {"services": context_selection}
    unavailable_service_ids = {item.get("service_id") for item in diagnostics
                               if item.get("code") == "SERVICE_CONTEXT_UNAVAILABLE"}
    found_count = len(nodes) + len(unavailable_service_ids)
    resolved_count = sum(node.resolution_status == "RESOLVED" for node in nodes)
    unresolved_count = found_count - resolved_count
    excluded_count = sum(bool(scopes) and scope not in scopes for scopes in all_owner_scopes.values())
    baseline_fingerprint = digest({"manifest_hash": manifest_hash, "source_hashes": graph.files,
                                   "scope": scope, "context_selection": context_rows})
    result = ViewDocument(
        view_id=f"service-inventory:{workspace_id}:{scope}", kind="topology",
        baseline_fingerprint=baseline_fingerprint, rules_version="t008-service-inventory-2",
        scope=scope, context_selection=context_rows, nodes=tuple(nodes), edges=tuple(edges),
        diagnostics=tuple(diagnostics),
        coverage={"status": coverage_status,
                  "reasons": ["Inventory contains only explicit ownership declarations and selected provider contexts.",
                              "External-system implementation and deployment remain UNKNOWN.",
                              "Counts describe explicit service declarations and emitted external-system objects only.",
                              "Excluded counts include declarations proven to belong to a different selected scope."],
                  "selected_service_ids": sorted(context_selection),
                  "external_system_ids": sorted(external_ids),
                  "counts": {"found": found_count, "resolved": resolved_count,
                             "unresolved": unresolved_count, "excluded": excluded_count}},
        limits=("Undeclared repositories, modules and framework beans are not services.",
                "External-system checkout, endpoints, deployment and runtime availability are UNKNOWN."),
        provenance=tuple(provenance[key] for key in sorted(provenance)),
    )
    # Validate through the T005 public model before returning the projection.
    from .architecture_model import validate_view_document
    validate_view_document(result.to_dict())
    if graph.to_dict() != before_graph or dict(workspace) != before_workspace:
        raise RuntimeError("Service inventory mutated its workspace or provider graph input")
    return result


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
    from .context_roles import classify_context_role, derived_context_claim

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
        chosen_id = request.get('context_id')
        if "context_id" in request and (not isinstance(chosen_id, str) or not chosen_id):
            raise ContextSelectionError({"code": "INVALID_CONTEXT_ID", "service_id": service,
                                         "message": "context_id must be a non-empty string when supplied"})
        if chosen_id is not None and any(context.get('id') == chosen_id and derived_context_claim(context)
                                         for context in graph.contexts):
            raise ContextSelectionError({'code': 'INVALID_CONTEXT_ROLE', 'service_id': service,
                                         'message': 'A derived declaration is not a source/compiler context'})
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
                      and context.get("module") == module and context.get("scope") == scope
                      and classify_context_role(context)[0] == 'COMPILER']
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
        projected = "spring_properties_projection" in context
        if projected and (not repo_roots or repo not in repo_roots):
            raise ContextSelectionError({"code": "STALE_CONTEXT", "service_id": service,
                                         "context_id": context["id"],
                                         "message": "Redacted context requires an explicit original checkout"})
        if repo_roots and repo in repo_roots:
            try:
                if projected:
                    from .workspace import validate_projected_context
                    validate_projected_context(Path(repo_roots[repo]), repo, context)
                else:
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
    context_index = {c.get('id'): c for c in graph.contexts}
    # Extra provenance may only come from source contexts. A mixed-variant
    # witness is omitted as a whole; stripping its context IDs would forge it.
    provenance_contexts = {c.get('id') for c in graph.contexts
                           if c.get('mode') == 'SOURCE_ONLY' and not c.get('analyzer_version')}
    allowed_contexts = provenance_contexts | {context_id}
    proof_index = {p.get('id'): p for p in graph.evidence}
    def isolated_proof(identity):
        if context_id is None:
            return True
        proof = proof_index.get(identity, {})
        refs = proof.get('context_ids', [])
        if not isinstance(refs, (list, tuple)) or any(not isinstance(c, str) for c in refs):
            return False
        refs = set(refs)
        if 'context_id' in proof:
            refs.add(proof['context_id'])
        return refs <= allowed_contexts
    def isolated_edge(edge):
        return context_id is None or (set(edge.context_ids) <= allowed_contexts
                                      and all(isolated_proof(i) for i in edge.evidence_ids))
    # Implementation episodes are repository history, not source-set code.
    nodes = [n for n in graph.nodes if scope == "all" or n.scope == scope or n.kind == "implementation_episode"]
    if context_id is not None:
        compiler_ids = {item.get("id") for item in [*graph.symbols, *graph.call_sites]}
        compiler_ids.update(item.get("method") for item in graph.cfgs)
        selected_ids = {item.get("id") for item in graph.symbols if item.get("context_id") == context_id}
        selected_ids.update(item.get("id") for item in graph.call_sites if item.get("context_id") == context_id)
        selected_ids.update(item.get("method") for item in graph.cfgs if item.get("context_id") == context_id)
        for node in graph.nodes:
            owner = (node.metadata or {}).get('context_id')
            if owner in context_index and owner not in provenance_contexts:
                compiler_ids.add(node.id)
                if owner == context_id:
                    selected_ids.add(node.id)
        nodes = [node for node in nodes if node.id not in compiler_ids or node.id in selected_ids]
    ids = {n.id for n in nodes}
    omitted_edges = [e for e in graph.edges if context_id is not None and not isolated_edge(e)
                     and e.source in ids and (e.target in ids or context_id in e.context_ids)]
    edges = [e for e in graph.edges if e.source in ids and e.target in ids and isolated_edge(e)]
    retained_proofs = {identity for e in edges for identity in e.evidence_ids}
    omitted_proofs = {identity for e in omitted_edges for identity in e.evidence_ids} - retained_proofs
    boundary_diagnostics = [{'code': 'COMPILER_CONTEXT_BOUNDARY_UNKNOWN', 'context_id': context_id,
        'source': e.source, 'target': e.target, 'relation': e.kind,
        'omitted_context_ids': sorted(set(e.context_ids) - allowed_contexts),
        'reason': 'Relation omitted because its context/proof belongs to another compiler variant.'}
        for e in sorted(omitted_edges, key=lambda e: (e.source, e.target, e.kind, e.context_ids))]
    if view == "calls":
        edges = [e for e in edges if e.kind in EXECUTION_EDGES or e.kind == "calls"]
    elif view == "configuration":
        edges = [e for e in edges if e.kind in {"configured_by", "resolves_property", "conditional_on",
                                                "imports_configuration", "uses_import_selector", "selects_import", "may_select_import",
                                                "uses_bean_registrar", "registers_bean", "produces_bean",
                                                "defines_bean", "injects_bean", "advised_by",
                                                "declares_entrypoint", "bypasses_proxy",
                                                "enables_proxy_policy", "may_traverse_proxy",
                                                "governs_proxy_path", "may_apply_advice",
                                                "proxy_resolution_unknown", "declares_async_transition",
                                                "declares_event_transition", "declares_reactive_transition",
                                                "crosses_async_boundary"}]
    elif view == "data-flow":
        from .dataflow import FORWARD, REVERSE
        edges = [e for e in edges if e.kind in FORWARD | REVERSE | {"reads_field", "writes_field", "argument_to_parameter", "returns_to",
                                                "maps_field", "maps_to_table", "maps_to_column", "declared_on_table",
                                                "resolves_to_schema_table", "resolves_to_schema_column", "repository_for",
                                                "declares_query", "defines_named_query", "uses_named_query",
                                                "query_reads", "query_writes", "query_deletes", "filters_by",
                                                "orders_by", "returns_entity", "returns_projection", "persistence_intent",
                                                "defines_http_request", "may_execute_http_request"}]
    elif view == "integrations":
        edges = [e for e in edges if e.kind in SIDE_EFFECTS | {"implements_contract", "exposes_endpoint",
                                                               "declares_entrypoint", "uses_external_service",
                                                               "defines_http_request", "may_execute_http_request"}]
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
                        resolution_reason="RESOLVED_TARGET_EXCLUDED_BY_SCOPE", dispatch_complete=False)
        site["dispatch_candidates"] = [c for c in site.get("dispatch_candidates", []) if c in ids]
        if len(site['dispatch_candidates']) != len(original.get('dispatch_candidates', [])):
            site['dispatch_complete'] = False
        omitted_site_refs = [i for i in site.get('evidence_ids', []) if i in omitted_proofs or not isolated_proof(i)]
        if omitted_site_refs:
            site['evidence_ids'] = [i for i in site.get('evidence_ids', []) if i not in omitted_site_refs]
            site.update(declared_target=None, omitted_declared_target=original.get('declared_target'),
                        dispatch_candidates=[], dispatch_complete=False,
                        resolution_reason='COMPILER_CONTEXT_BOUNDARY_OMITTED')
            boundary_diagnostics.append({'code':'COMPILER_CONTEXT_BOUNDARY_UNKNOWN', 'context_id':context_id,
                'call_site':site['id'], 'reason':'Call target omitted with its cross-variant evidence.'})
        sites.append(site)
    selected_evidence = {identity for edge in edges for identity in edge.evidence_ids}
    selected_evidence.update(identity for site in sites for identity in site.get("evidence_ids", []))
    selected_cfgs = []
    for cfg in graph.cfgs:
        if cfg.get('method') not in ids or (context_id is not None and cfg.get('context_id') != context_id):
            continue
        refs = list(cfg.get('evidence_ids', []))
        refs += [i for block in cfg.get('blocks', []) for i in block.get('local_operation_evidence_ids', [])]
        if any(not isolated_proof(i) or i in omitted_proofs for i in refs):
            boundary_diagnostics.append({'code':'COMPILER_CONTEXT_BOUNDARY_UNKNOWN', 'context_id':context_id,
                'method':cfg['method'], 'reason':'CFG omitted with its cross-variant evidence.'})
            continue
        selected_cfgs.append(cfg)
    selected_evidence.update(identity for cfg in selected_cfgs for identity in cfg.get("evidence_ids", []))
    selected_evidence.update(identity for cfg in selected_cfgs for block in cfg.get('blocks', [])
        if type(block.get('local_operation_version')) is int and block['local_operation_version'] == 1
        for refs in [block.get('local_operation_evidence_ids', [])]
        if isinstance(refs, list) and all(isinstance(identity, str) for identity in refs)
        for identity in refs)
    selected_symbols = [symbol for symbol in graph.symbols if symbol.get('id') in ids
                        and (context_id is None or symbol.get('context_id') == context_id)]
    # Retained structural/source edges still need their original provenance
    # contexts when an explicit compiler variant is selected. Keep only contexts
    # actually referenced by selected records; this does not select more variants.
    referenced_contexts = {identity for edge in edges for identity in edge.context_ids}
    referenced_contexts.update(record.get("context_id") for record in [
        *sites, *selected_cfgs, *selected_symbols])
    for proof in graph.evidence:
        if proof.get('id') in selected_evidence:
            referenced_contexts.update(proof.get('context_ids', []))
            if isinstance(proof.get('context_id'), str):
                referenced_contexts.add(proof['context_id'])
    return replace(graph, nodes=nodes, edges=edges,
                   files={p: h for p, h in graph.files.items() if any(n.path == p for n in nodes)},
                   contexts=[c for c in graph.contexts if c.get("id") in referenced_contexts or
                             (scope == "all" or c.get("scope") == scope) and (context_id is None or c.get("id") == context_id)],
                   diagnostics=[d for d in graph.diagnostics
                                if (context_id is None or not d.get('context_id') or d['context_id'] in allowed_contexts)
                                and (not (d.get('path') or d.get('source_file'))
                                     or (d.get('path') or d.get('source_file')) in {n.path for n in nodes})] + boundary_diagnostics,
                   evidence=[e for e in graph.evidence if e.get("id") in selected_evidence],
                   symbols=selected_symbols, call_sites=sites, cfgs=selected_cfgs,
                   analysis_annotations=[a for a in graph.analysis_annotations
                                         if set(a.get('target_ids', [])) <= ids
                                         and set(a.get('evidence_ids', [])) <= selected_evidence])


def is_execution_entity(node) -> bool:
    """Shared role boundary: type/configuration references are not execution."""
    return node is not None and node.kind in EXECUTABLE_NODE_KINDS and node.role == 'executable_code'


def is_execution_callsite(site: Mapping[str, Any]) -> bool:
    """Shared invocation boundary for call navigation, scoring and completeness.

    Missing kind is the supported legacy form. Explicit unsupported kinds are
    not promoted to calls; in particular references and invokedynamic are not
    execution evidence in the current compiler matrix.
    """
    return site.get("invocation_kind") in {None, "CALL", "STATIC", "VIRTUAL", "INTERFACE",
                                            "SPECIAL", "CONSTRUCTOR", "EXTENSION", "OPERATOR", "ACCESSOR"}


def evidence_freshness_gaps(proofs, evidence_ids):
    result = []
    for evidence_id in sorted(set(evidence_ids)):
        proof = proofs.get(evidence_id, {})
        # Older valid v2/v3 proofs omit freshness; retain their existing
        # context-bound behavior. An explicit state always takes precedence.
        if 'freshness' not in proof:
            continue
        if proof['freshness'] == 'STALE':
            result.append({'code': 'STALE_EVIDENCE', 'penalty': 5,
                'reason': 'A stale proof contributes no execution or impact weight.',
                'evidence_ids': [evidence_id]})
        elif proof['freshness'] not in CURRENT_COMPILER_FRESHNESS:
            result.append({'code': 'EVIDENCE_FRESHNESS_UNKNOWN', 'penalty': 2,
                'reason': 'The proof does not establish current content.',
                'evidence_ids': [evidence_id]})
    return result

def execution_authority_gaps(contexts, files, proofs, context_ids, evidence_ids, site=None):
    """Shared admission contract for ranking and interprocedural CFG expansion."""
    result = []
    authority_contexts = set(context_ids)
    if site:
        authority_contexts.add(site['context_id'])
    proof_contexts = set()
    for identity in evidence_ids:
        proof = proofs.get(identity, {})
        declared_contexts = proof.get('context_ids', [])
        if isinstance(declared_contexts, (list, tuple)):
            proof_contexts.update(c for c in declared_contexts if isinstance(c, str))
        if isinstance(proof.get('context_id'), str):
            proof_contexts.add(proof['context_id'])
    mismatched_proof_contexts = proof_contexts - authority_contexts
    authority_contexts.update(proof_contexts)
    invalid_contexts = sorted(c for c in authority_contexts
                              if not _compiler_authority(contexts.get(c, {}), files))
    invalid_proofs = sorted({identity for identity in evidence_ids
        if (('mode' in proofs.get(identity, {}) and proofs[identity]['mode'] not in COMPILER_MODES)
            or ('origin_trust' in proofs.get(identity, {})
                and proofs[identity]['origin_trust'] not in COMPILER_ORIGINS))})
    if not authority_contexts or invalid_contexts or invalid_proofs or mismatched_proof_contexts:
        result.append({'code': 'EXECUTION_AUTHORITY_UNKNOWN', 'penalty': 3,
            'reason': 'Execution requires a current content-bound inspection context and compatible proof authority.',
            'context_ids': sorted(set(invalid_contexts) | mismatched_proof_contexts),
            'evidence_ids': invalid_proofs or list(evidence_ids)})
    return result

def rank(graph: KnowledgeGraph, entry: str | None = None, profile: str = "execution", scope: str = "production") -> dict:
    """Read-only, versioned priority from validated graph evidence, not confidence.

    Contributions retain the exact edges (including incoming edges), paths and
    missing-proof records used by each term. Caps and penalties are fixed policy;
    no score is a probability, runtime availability or business importance.
    """
    import json

    if profile not in PROFILES:
        raise ValueError("unsupported ranking profile")
    # Validate before projection: a dangling/forged ref cannot disappear through
    # scope filtering. Rehydrate a private copy, preserving graph/store v1–v3.
    graph = project(KnowledgeGraph.from_dict(graph.to_dict()), scope)
    nodes = {n.id: n for n in graph.nodes}
    if entry is not None and entry not in nodes:
        raise ValueError("entry is absent from selected scope")
    executable = EXECUTABLE_NODE_KINDS
    rankable = executable - {"call_site"} | {"class", "enum", "interface", "type"}
    contexts = {c['id']: c for c in graph.contexts if isinstance(c.get('id'), str)}
    sites = {s['id']: s for s in graph.call_sites}
    proofs = {p['id']: p for p in graph.evidence}
    known_kinds = {"SYMBOL_RESOLVED", "DISPATCH_CANDIDATE", "FRAMEWORK_DERIVED", "RUNTIME_OBSERVED"}
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False)
    unique = lambda values: [json.loads(key) for key in sorted({canonical(value) for value in values})]
    def runnable(identity):
        return is_execution_entity(nodes[identity])
    gaps = defaultdict(list)
    def gap(identity, code, reason, penalty, **refs):
        gaps[identity].append({'code': code, 'reason': reason, 'penalty': penalty, **refs})
    def proof_gaps(evidence_ids):
        return evidence_freshness_gaps(proofs, evidence_ids)

    def context_gaps(identity, ids):
        if not ids:
            gap(identity, 'CONTEXT_UNKNOWN', 'No compiler/evidence context is available for this entity.', 3)
        for context_id in sorted(ids):
            c = contexts.get(context_id, {})
            if c.get('freshness') == 'STALE':
                gap(identity, 'STALE_CONTEXT', 'Stale context contributes no execution evidence.', 5, context_id=context_id)
            elif c.get('freshness') not in CURRENT_COMPILER_FRESHNESS:
                gap(identity, 'CONTEXT_FRESHNESS_UNKNOWN', 'The context does not establish current content.', 2, context_id=context_id)
            if c.get('mode') == 'SOURCE_ONLY':
                gap(identity, 'SOURCE_ONLY', 'Syntax does not establish compiler call resolution.', 3, context_id=context_id)
            coverage = c.get('coverage')
            if isinstance(coverage, dict):
                complete = (coverage.get('calls_found') is not None
                            and coverage.get('calls_found') == coverage.get('calls_resolved')
                            and c.get('status') == 'COMPLETE')
            else:
                complete = coverage in {'COMPLETE', 'COMPLETE_WITHIN_INDEXED_SCOPE', 'COMPLETE_WITHIN_SELECTED_SCOPE'}
            if not complete:
                gap(identity, 'CONTEXT_COVERAGE_PARTIAL', 'Complete call coverage is not evidenced for the selected context.', 2, context_id=context_id)

    node_contexts = defaultdict(set)
    for symbol in graph.symbols:
        node_contexts[symbol['id']].add(symbol['context_id'])
    adjacency = defaultdict(list)
    witness_gaps = {}
    degree, references, effects = defaultdict(list), defaultdict(list), defaultdict(list)
    shared = defaultdict(int)
    for edge in graph.edges:
        if edge.kind in TYPE_EDGES:
            shared[edge.target] += 1
    # The proof tuple, not legacy confidence or presentation text, defines one
    # contribution. Retain a deterministic representative of duplicate records.
    witness_records = {}
    for edge in graph.edges:
        record = asdict(edge)
        record['context_ids'] = sorted(record['context_ids'])
        record['evidence_ids'] = sorted(record['evidence_ids'])
        key = canonical([record[k] for k in ('source', 'target', 'kind', 'evidence_kind', 'context_ids', 'evidence_ids')])
        if key not in witness_records or canonical(record) < canonical(witness_records[key]):
            witness_records[key] = record
    for record in sorted(witness_records.values(), key=canonical):
        source, target, kind = record['source'], record['target'], record['kind']
        related_site = sites.get(source) or sites.get(target)
        relevant_proofs = list(record['evidence_ids'])
        if related_site and kind in EXECUTION_EDGES | SIDE_EFFECTS:
            relevant_proofs += related_site.get('evidence_ids', [])
        record_gaps = proof_gaps(relevant_proofs)
        stale_proof = any(g['code'] == 'STALE_EVIDENCE' for g in record_gaps)
        stale_context = any(contexts.get(c, {}).get('freshness') == 'STALE' for c in record['context_ids'])
        if kind in TYPE_EDGES:
            node_contexts[target].update(record['context_ids'])
            gaps[target].extend(record_gaps)
            if not stale_context and not stale_proof:
                references[target].append(record)
            elif stale_context:
                gap(target, 'STALE_CONTEXT', 'Stale relation contributes no impact evidence.', 5,
                    context_ids=record['context_ids'], evidence_ids=record['evidence_ids'])
        if kind not in EXECUTION_EDGES | SIDE_EFFECTS:
            continue
        record_gaps.extend(execution_authority_gaps(
            contexts, graph.files, proofs, record['context_ids'], relevant_proofs, related_site))
        affected = {source, target}
        if related_site:
            affected.add(related_site['caller'])
        for identity in affected:
            node_contexts[identity].update(record['context_ids'])
            gaps[identity].extend(record_gaps)
        if not runnable(source):
            continue
        if record['evidence_kind'] not in known_kinds or (related_site and related_site.get('evidence_kind') not in known_kinds):
            # An unresolved site cannot be promoted by a stronger-looking edge.
            if kind in EXECUTION_EDGES:
                for identity in affected:
                    gap(identity, 'EXECUTION_EVIDENCE_UNRESOLVED', 'This relation has no resolved execution evidence.', 3,
                        source=source, target=target, evidence_ids=record['evidence_ids'])
            continue
        if stale_context:
            for identity in affected:
                gap(identity, 'STALE_CONTEXT', 'Stale relation contributes no execution evidence.', 5,
                    context_ids=record['context_ids'], evidence_ids=record['evidence_ids'])
        if stale_context or stale_proof or any(g['code'] == 'EXECUTION_AUTHORITY_UNKNOWN' for g in record_gaps):
            continue
        if related_site and not is_execution_callsite(related_site):
            continue
        if kind in SIDE_EFFECTS:
            effects[source].append(record)
        elif runnable(target) and nodes[source].scope == nodes[target].scope:
            adjacency[source].append(record)
            witness_gaps[canonical(record)] = record_gaps
            degree[source].append(record)
            degree[target].append(record)

    for site in sorted(graph.call_sites, key=lambda s: s['id']):
        if not is_execution_callsite(site):
            continue
        refs = {'call_site': site['id'], 'context_id': site['context_id'],
                'evidence_ids': sorted(site.get('evidence_ids', []))}
        affected = {site['id'], site['caller'], site.get('declared_target')} | set(site.get('dispatch_candidates', []))
        for identity in sorted(affected - {None}):
            if not site.get('declared_target') or site.get('evidence_kind') == 'UNRESOLVED':
                gap(identity, 'UNRESOLVED_CALL', site.get('resolution_reason', 'Target unknown'), 5, **refs)
            if site.get('dispatch_complete') is not True:
                gap(identity, 'INCOMPLETE_DISPATCH', 'The static target set is not proved complete.', 2, **refs)
            if len(set(site.get('dispatch_candidates', []))) > 1:
                gap(identity, 'AMBIGUOUS_DISPATCH', 'Multiple possible targets do not prove a selected runtime target.', 3, **refs)

    # An observed pair is positive sampled evidence. It cannot close a static
    # target set; independently complete static call sites remain intact.
    # Completeness must have the same admitted executable path as scoring.
    # Metadata alone (or a filtered/stale/reference edge) cannot close a pair.
    static_links = {(r['source'], r['target'], r['kind']) for values in adjacency.values() for r in values
                    if r['evidence_kind'] != 'RUNTIME_OBSERVED'
                    and not proof_gaps(r['evidence_ids'])}
    complete_pairs = set()
    for site in graph.call_sites:
        if (not is_execution_callsite(site) or site.get('dispatch_complete') is not True
                or site.get('evidence_kind') not in known_kinds - {'RUNTIME_OBSERVED'}
                or not _compiler_authority(contexts.get(site['context_id'], {}), graph.files)
                or not site.get('evidence_ids') or proof_gaps(site['evidence_ids'])
                or (site['caller'], site['id'], 'declares_call') not in static_links):
            continue
        for target in [site.get('declared_target'), *site.get('dispatch_candidates', [])]:
            if ((site['id'], target, 'resolves_to') in static_links
                    or (site['id'], target, 'may_dispatch_to') in static_links):
                complete_pairs.add((site['caller'], target))
    for source, edges in sorted(adjacency.items()):
        for record in edges:
            if record['kind'] == 'observed_dispatch_to' and (source, record['target']) not in complete_pairs:
                observation_gap = {'code': 'RUNTIME_SAMPLE_ONLY', 'penalty': 2,
                    'reason': 'Observed dispatch does not establish static dispatch completeness.',
                    'source': source, 'target': record['target'], 'evidence_ids': record['evidence_ids']}
                witness_gaps[canonical(record)].append(observation_gap)
                for identity in (source, record['target']):
                    gaps[identity].append(observation_gap)

    paths = {}
    if entry is not None and runnable(entry) and (degree[entry] or effects[entry]):
        paths[entry] = {'entity_ids': [entry], 'steps': []}
        queue = deque([entry])
        while queue:
            source = queue.popleft()
            for record in sorted(adjacency[source], key=canonical):
                target = record['target']
                if target not in paths:
                    paths[target] = {'entity_ids': paths[source]['entity_ids'] + [target],
                                     'steps': paths[source]['steps'] + [record]}
                    queue.append(target)

    for identity in sorted(nodes):
        if nodes[identity].kind not in rankable or nodes[identity].role not in {'executable_code', 'contract'}:
            continue
        context_gaps(identity, node_contexts[identity])
        if graph.schema_version < 3 and degree[identity]:
            gap(identity, 'CALLSITE_COVERAGE_UNKNOWN', 'Legacy graph has no per-call-site dispatch completeness inventory.', 2)
        if not degree[identity] and not effects[identity]:
            gap(identity, 'EXECUTION_COVERAGE_UNKNOWN', 'No admissible call/side-effect witness establishes execution relevance.', 3)
    for diagnostic in graph.diagnostics:
        code = str(diagnostic.get('code', ''))
        if not any(term in code.upper() for term in ('UNRESOLVED', 'AMBIGUOUS', 'UNKNOWN', 'MISSING',
                                                     'TRUNCAT', 'TIMEOUT', 'CANCEL', 'UNSUPPORTED', 'STALE')):
            continue
        diagnostic_path = diagnostic.get('path') or diagnostic.get('source_file')
        for identity, node in sorted(nodes.items()):
            if node.kind not in rankable:
                continue
            if diagnostic_path and node.path != diagnostic_path:
                continue
            location = diagnostic.get('range') or {}
            if node.line is not None and isinstance(location.get('start_line'), int) and not (
                    location['start_line'] <= node.line <= location.get('end_line', location['start_line'])):
                continue
            if diagnostic.get('context_id') and diagnostic['context_id'] not in node_contexts[identity]:
                continue
            gap(identity, 'PROVIDER_DIAGNOSTIC', diagnostic.get('reason', diagnostic.get('message', code)), 1,
                diagnostic=diagnostic)
    # Local incompleteness along the selected witness also limits its descendants.
    local_gaps = {identity: unique(values) for identity, values in gaps.items()}
    rows = []
    for n in sorted(graph.nodes, key=lambda node: node.id):
        if n.kind not in rankable or n.role not in {'executable_code', 'contract'}:
            continue
        selected_path = paths.get(n.id, {'entity_ids': [], 'steps': []})
        row_gaps = list(local_gaps.get(n.id, []))
        for identity in selected_path['entity_ids']:
            if identity != n.id and identity in sites:
                row_gaps.extend(local_gaps.get(identity, []))
        for step in selected_path['steps']:
            row_gaps.extend(witness_gaps.get(canonical(step), []))
        row_gaps = unique(row_gaps)
        has_execution = bool(degree[n.id] or effects[n.id])
        breakdown = {'entry_relevance': 10 if n.id == entry and has_execution else 0,
                     'execution_path': 5 if n.id in paths else 0,
                     'execution_centrality': min(len(degree[n.id]), 10),
                     'side_effects': min(len(effects[n.id]), 10),
                     'type_reference_impact': len(references[n.id]) if profile == 'impact' else 0}
        raw = sum(breakdown.values())
        penalty = min(raw, 10, sum(g['penalty'] for g in row_gaps))
        breakdown['incompleteness_penalty'] = -penalty
        witnesses = unique(degree[n.id] + effects[n.id] + selected_path['steps'] +
                           (references[n.id] if profile == 'impact' else []))
        status = ('UNKNOWN' if not has_execution and not (profile == 'impact' and references[n.id]) else
                  'PARTIAL' if row_gaps else 'COMPLETE_WITHIN_INDEXED_SCOPE')
        contributions = {'entry_relevance': [{'selected_entry': entry, 'evidence': degree[n.id] + effects[n.id]}] if breakdown['entry_relevance'] else [],
                         'execution_path': [selected_path] if n.id in paths else [],
                         'execution_centrality': degree[n.id], 'side_effects': effects[n.id],
                         'type_reference_impact': references[n.id] if profile == 'impact' else [],
                         'incompleteness_penalty': row_gaps}
        rows.append({'id': n.id, 'score': raw - penalty, 'breakdown': breakdown,
                     'shared_references': shared[n.id], 'evidence': witnesses,
                     'contributions': contributions, 'path': selected_path,
                     'coverage': {'status': status, 'gaps': row_gaps,
                                  'penalty_points': sum(g['penalty'] for g in row_gaps), 'penalty_applied': penalty}})
    rows.sort(key=lambda r: (-r['score'], r['id']))
    return {'profile': PROFILES[profile], 'scope': scope, 'entry': entry,
            'status': 'PARTIAL' if any(r['coverage']['status'] != 'UNKNOWN' for r in rows) else 'UNKNOWN',
            'contexts': sorted(graph.contexts, key=canonical), 'results': rows,
            'scoring_policy': {'entry_relevance': 10, 'execution_path': 5,
                'execution_centrality_cap': 10, 'side_effects_cap': 10,
                'type_reference_impact': 'unique type/constant reference witnesses; impact profile only',
                'incompleteness_penalty': 'min(raw score, 10, sum of localized gap penalties)'},
            'limitations': ['Ranking expresses graph evidence, not business importance, runtime availability or path feasibility.',
                            'Legacy name-match calls, configuration, and type references have zero execution contribution.',
                            'Runtime observations do not establish complete static dispatch; no project tools are executed.']}

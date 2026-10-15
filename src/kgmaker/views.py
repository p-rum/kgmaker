"""Scope projections and deterministic, purpose-specific ranking.

Navigation hints and execution evidence remain separate. References never
contribute to execution centrality, even for heavily reused DTOs and enums.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, replace

from .model import KnowledgeGraph

EXECUTION_EDGES = {"resolves_to", "may_dispatch_to", "declares_call", "observed_dispatch_to"}
SIDE_EFFECTS = {"persistence_intent", "query_writes", "publishes", "consumes", "calls_endpoint"}
TYPE_EDGES = {"references_type", "reads_constant"}
PROFILES = {"execution": "execution-1", "impact": "impact-1"}


def select_context(graph: KnowledgeGraph, scope: str, context_id: str | None = None) -> str | None:
    """Choose one usable compiler context or fail on an ambiguous variant set."""
    all_contexts = [item for item in graph.contexts if item.get("analyzer_version")]
    if context_id is not None:
        selected = [item for item in all_contexts if item.get("id") == context_id]
        if len(selected) != 1:
            raise ValueError("Unknown compiler context; available: "
                             + ", ".join(sorted(item["id"] for item in all_contexts)))
        if selected[0].get("freshness") == "STALE":
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
    edges = [e for e in graph.edges if e.source in ids and e.target in ids and (context_id is None or context_id in e.context_ids)]
    if view == "calls":
        edges = [e for e in edges if e.kind in EXECUTION_EDGES or e.kind == "calls"]
    elif view == "configuration":
        edges = [e for e in edges if e.kind in {"configured_by", "resolves_property", "conditional_on",
                                                "defines_bean", "injects_bean", "advised_by",
                                                "declares_entrypoint", "bypasses_proxy"}]
    elif view == "data-flow":
        edges = [e for e in edges if e.kind in {"reads_field", "writes_field", "argument_to_parameter", "returns_to",
                                                "maps_field", "maps_to_table", "maps_to_column", "declared_on_table",
                                                "resolves_to_schema_table", "resolves_to_schema_column", "repository_for",
                                                "declares_query", "query_reads", "query_writes", "persistence_intent"}]
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

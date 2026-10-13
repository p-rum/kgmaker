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


def project(graph: KnowledgeGraph, scope: str = "production", *, view: str = "architecture") -> KnowledgeGraph:
    if scope not in {"production", "test", "test_fixture", "development", "unknown", "all"}:
        raise ValueError("invalid scope: " + scope)
    nodes = [n for n in graph.nodes if scope == "all" or n.scope == scope]
    ids = {n.id for n in nodes}
    edges = [e for e in graph.edges if e.source in ids and e.target in ids]
    if view == "calls":
        edges = [e for e in edges if e.kind in EXECUTION_EDGES or e.kind == "calls"]
    elif view == "configuration":
        edges = [e for e in edges if e.kind in {"configured_by", "resolves_property", "conditional_on", "defines_bean"}]
    elif view == "integrations":
        edges = [e for e in edges if e.kind in SIDE_EFFECTS | {"implements_contract"}]
    return replace(graph, nodes=nodes, edges=edges,
                   files={p: h for p, h in graph.files.items() if any(n.path == p for n in nodes)},
                   contexts=[c for c in graph.contexts if scope == "all" or c.get("scope") == scope],
                   diagnostics=[d for d in graph.diagnostics if d.get("path") in {n.path for n in nodes}],
                   evidence=[e for e in graph.evidence if e.get("id") in {i for edge in edges for i in edge.evidence_ids}])


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
        if n.kind == "file" or n.role != "executable_code":
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

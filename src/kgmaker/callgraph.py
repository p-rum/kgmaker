"""Call-site-aware navigation; unresolved coverage never proves absence."""
from __future__ import annotations

from collections import defaultdict, deque

from .analysis_model import AnalysisError
from .model import KnowledgeGraph
from .views import is_execution_callsite, project


def adjacency(graph: KnowledgeGraph, include_candidates=True, *, include_runtime=True):
    result = defaultdict(list)
    for site in graph.call_sites:
        if not is_execution_callsite(site) or site.get("evidence_kind") == "RUNTIME_OBSERVED":
            continue
        target = site.get("declared_target")
        if target:
            result[site["caller"]].append({"target": target, "call_site": site["id"],
                "kind": "DECLARED_TARGET", "evidence_ids": site.get("evidence_ids", []),
                "dispatch_complete": site.get("dispatch_complete", False)})
        if include_candidates:
            for candidate in site.get("dispatch_candidates", []):
                if candidate != target:
                    result[site["caller"]].append({"target": candidate, "call_site": site["id"],
                        "kind": "DISPATCH_CANDIDATE", "evidence_ids": site.get("evidence_ids", []),
                        "dispatch_complete": site.get("dispatch_complete", False)})
    # Callers/callees label supplied runtime samples. Static analyses opt out.
    if include_runtime:
        for edge in graph.edges:
            if edge.kind != "observed_dispatch_to" or edge.evidence_kind != "RUNTIME_OBSERVED":
                continue
            result[edge.source].append({"target": edge.target,
                                        "call_site": edge.evidence_ids[0] if edge.evidence_ids else f"runtime:{edge.source}:{edge.target}",
                                        "kind": "RUNTIME_OBSERVED",
                                        "evidence_ids": list(edge.evidence_ids),
                                        "dispatch_complete": False,
                                        "completeness_reason": "RUNTIME_SAMPLE_NOT_STATIC_DISPATCH"})
    for key in result:
        result[key].sort(key=lambda e: (e["target"], e["call_site"], e["kind"]))
    return result


def callees(graph, symbol, *, scope="production", include_candidates=False):
    graph = project(graph, scope)
    if symbol not in {n.id for n in graph.nodes}:
        raise AnalysisError("Symbol missing from selected scope")
    return {"symbol": symbol, "scope": scope, "contexts": graph.contexts,
            "results": adjacency(graph, include_candidates)[symbol],
            "status": "PARTIAL" if graph.diagnostics else "COMPLETE_WITHIN_INDEXED_SCOPE"}


def callers(graph, symbol, *, scope="production"):
    graph = project(graph, scope)
    if symbol not in {n.id for n in graph.nodes}:
        raise AnalysisError("Symbol missing from selected scope")
    result = []
    for caller, edges in adjacency(graph).items():
        result.extend({"caller": caller, **edge} for edge in edges if edge["target"] == symbol)
    return {"symbol": symbol, "scope": scope, "contexts": graph.contexts,
            "results": sorted(result, key=lambda r: (r["caller"], r["call_site"], r["kind"]))}


def path(graph, source, target, *, scope="production", max_depth=30, max_nodes=5000, include_candidates=True):
    graph = project(graph, scope)
    ids = {n.id for n in graph.nodes}
    if source not in ids or target not in ids:
        raise AnalysisError("Path endpoint missing from selected scope")
    edges = adjacency(graph, include_candidates, include_runtime=False)
    queue = deque([(source, [], [source])])
    visited, truncated = set(), False
    while queue:
        node, steps, chain = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        if node == target:
            return {"status": "STATIC_PATH", "scope": scope, "entity_ids": chain, "steps": steps,
                    "contexts": graph.contexts, "visited_count": len(visited), "truncated": truncated,
                    "interpretation": "Declared/candidate call path; feasibility, runtime dispatch and data availability are not established."}
        if len(steps) >= max_depth or len(visited) >= max_nodes:
            truncated |= bool(edges[node])
            continue
        for edge in edges[node]:
            if edge["target"] in ids:
                queue.append((edge["target"], steps + [edge], chain + [edge["target"]]))
    return {"status": "UNKNOWN", "scope": scope, "entity_ids": [], "steps": [], "contexts": graph.contexts,
            "visited_count": len(visited), "truncated": truncated,
            "reason": "No path within indexed static coverage; this is not proof of unreachability."}


def strongly_connected(graph: KnowledgeGraph) -> list[list[str]]:
    """Find static cycles with iterative Kosaraju."""
    edges = adjacency(graph, include_runtime=False)
    vertices = {n.id for n in graph.nodes if n.kind in {"method", "function", "constructor", "bytecode_method"}}
    reverse = defaultdict(set)
    for source, values in edges.items():
        for edge in values:
            reverse[edge["target"]].add(source)
    seen, order = set(), []
    for start in sorted(vertices):
        stack = [(start, False)]
        while stack:
            node, done = stack.pop()
            if done:
                order.append(node)
                continue
            if node in seen:
                continue
            seen.add(node)
            stack.append((node, True))
            stack.extend((e["target"], False) for e in reversed(edges[node]) if e["target"] in vertices and e["target"] not in seen)
    seen, components = set(), []
    for start in reversed(order):
        if start in seen:
            continue
        component, stack = [], [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node); component.append(node)
            stack.extend(sorted(reverse[node] - seen))
        if len(component) > 1 or any(e["target"] == start for e in edges[start]):
            components.append(sorted(component))
    return sorted(components)

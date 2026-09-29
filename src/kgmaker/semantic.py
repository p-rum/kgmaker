"""Validation and merging for the optional agent-authored semantic graph layer."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .model import Edge, KnowledgeGraph, Node

SEMANTIC_FILE = Path(".kgmaker/semantic.json")
SEMANTIC_INPUT_FILE = Path(".kgmaker/semantic-input.json")
SEMANTIC_SCHEMA_VERSION = 1
SEMANTIC_RELATIONS = {
    "calls", "implements", "references", "cites", "owns", "models", "validates",
    "persists_to", "publishes", "consumes", "calls_endpoint", "depends_on", "uses",
    "shares_data_with", "rationale_for", "conceptually_related_to",
    "semantically_similar_to", "coordinates", "extends", "specializes", "part_of",
}
INFERRED_SCORES = {0.55, 0.65, 0.75, 0.85, 0.95}


class SemanticValidationError(ValueError):
    """The agent-authored semantic artifact is malformed or stale."""


def concept_id(source_file: str, name: str) -> str:
    """Return a deterministic concept ID shared by prepare/validate and the agent."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_") or "concept"
    return f"concept:{source_file}:{slug}"


def graph_fingerprint(graph: KnowledgeGraph) -> str:
    """Fingerprint a structural graph without its timestamp or semantic overlay."""
    payload = {
        "files": sorted(graph.files.items()),
        "nodes": sorted((n.id, n.kind, n.name, n.path, n.line, n.signature) for n in graph.nodes),
        "edges": sorted((e.source, e.target, e.kind, e.evidence, e.confidence, e.confidence_score) for e in graph.edges),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_semantic_input(graph: KnowledgeGraph) -> dict[str, Any]:
    """Prepare stable IDs and file digests; source contents stay in the repository."""
    return {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "graph_fingerprint": graph_fingerprint(graph),
        "files": [
            {"path": path, "sha256": digest}
            for path, digest in sorted(graph.files.items())
        ],
        "nodes": [
            {
                "id": node.id,
                "kind": node.kind,
                "name": node.name,
                "path": node.path,
                "line": node.line,
                "signature": node.signature,
                "summary": node.summary,
            }
            for node in sorted(graph.nodes, key=lambda n: (n.path, n.line or 0, n.kind, n.name))
        ],
        "relations": sorted(SEMANTIC_RELATIONS),
    }


def _positive_line(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SemanticValidationError(f"{field} must be a positive line number or null")
    return value


def _check_line(root: Path, source_file: str, line: int | None, field: str, line_counts: dict[str, int]) -> None:
    """Require cited lines to exist in the indexed, unchanged source file."""
    if line is None:
        return
    if source_file not in line_counts:
        path = root / source_file
        try:
            path.resolve().relative_to(root.resolve())
            line_counts[source_file] = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeError, ValueError):
            raise SemanticValidationError(f"{field} source file cannot be read safely") from None
    if line > line_counts[source_file]:
        raise SemanticValidationError(f"{field} points past the end of {source_file}")


def validate_semantic_data(data: Any, graph: KnowledgeGraph, root: Path) -> tuple[list[Node], list[Edge]]:
    """Validate IDs, provenance, confidence, and graph freshness before merging."""
    if not isinstance(data, dict) or data.get("schema_version") != SEMANTIC_SCHEMA_VERSION:
        raise SemanticValidationError(f"semantic artifact must use schema_version {SEMANTIC_SCHEMA_VERSION}")
    if data.get("graph_fingerprint") != graph_fingerprint(graph):
        raise SemanticValidationError("semantic artifact was prepared against a different graph; run `kgmaker semantic prepare` again")
    if not isinstance(data.get("nodes"), list) or not isinstance(data.get("edges"), list):
        raise SemanticValidationError("semantic artifact must contain `nodes` and `edges` arrays")

    base_nodes = {node.id: node for node in graph.nodes}
    semantic_nodes: list[Node] = []
    semantic_ids: set[str] = set()
    line_counts: dict[str, int] = {}
    for index, item in enumerate(data["nodes"]):
        if not isinstance(item, dict):
            raise SemanticValidationError(f"nodes[{index}] must be an object")
        name = item.get("name")
        source_file = item.get("source_file")
        if not isinstance(name, str) or not name.strip():
            raise SemanticValidationError(f"nodes[{index}].name must be a non-empty string")
        if not isinstance(source_file, str) or source_file not in graph.files:
            raise SemanticValidationError(f"nodes[{index}].source_file must name an indexed repository file")
        node_id = item.get("id")
        expected_id = concept_id(source_file, name)
        if node_id != expected_id:
            raise SemanticValidationError(f"nodes[{index}].id must be `{expected_id}`")
        if node_id in base_nodes or node_id in semantic_ids:
            raise SemanticValidationError(f"nodes[{index}].id duplicates an existing graph node")
        line = _positive_line(item.get("source_line"), f"nodes[{index}].source_line")
        _check_line(root, source_file, line, f"nodes[{index}].source_line", line_counts)
        summary = item.get("summary", "")
        if not isinstance(summary, str) or len(summary) > 500:
            raise SemanticValidationError(f"nodes[{index}].summary must be text no longer than 500 characters")
        semantic_ids.add(node_id)
        semantic_nodes.append(Node(node_id, "concept", name.strip(), source_file, line, summary=summary.strip() or None))

    valid_ids = set(base_nodes) | semantic_ids
    semantic_edges: list[Edge] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for index, item in enumerate(data["edges"]):
        if not isinstance(item, dict):
            raise SemanticValidationError(f"edges[{index}] must be an object")
        source, target, relation = item.get("source"), item.get("target"), item.get("kind")
        if not isinstance(source, str) or not isinstance(target, str) or source not in valid_ids or target not in valid_ids:
            raise SemanticValidationError(f"edges[{index}] references an unknown node ID")
        if source == target:
            raise SemanticValidationError(f"edges[{index}] cannot be a self-link")
        if not isinstance(relation, str) or relation not in SEMANTIC_RELATIONS:
            raise SemanticValidationError(f"edges[{index}].kind must be one of {', '.join(sorted(SEMANTIC_RELATIONS))}")
        confidence = item.get("confidence")
        score = item.get("confidence_score")
        if not isinstance(confidence, str) or confidence not in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}:
            raise SemanticValidationError(f"edges[{index}].confidence must be EXTRACTED, INFERRED, or AMBIGUOUS")
        if isinstance(score, bool) or not isinstance(score, (float, int)):
            raise SemanticValidationError(f"edges[{index}].confidence_score must be numeric")
        score = float(score)
        if confidence == "EXTRACTED" and score != 1.0:
            raise SemanticValidationError(f"edges[{index}] EXTRACTED confidence_score must be 1.0")
        if confidence == "INFERRED" and score not in INFERRED_SCORES:
            raise SemanticValidationError(f"edges[{index}] INFERRED confidence_score must be one of {sorted(INFERRED_SCORES)}")
        if confidence == "AMBIGUOUS" and not 0.1 <= score <= 0.3:
            raise SemanticValidationError(f"edges[{index}] AMBIGUOUS confidence_score must be between 0.1 and 0.3")
        source_file = item.get("source_file")
        if not isinstance(source_file, str) or source_file not in graph.files:
            raise SemanticValidationError(f"edges[{index}].source_file must name an indexed repository file")
        source_line = _positive_line(item.get("source_line"), f"edges[{index}].source_line")
        _check_line(root, source_file, source_line, f"edges[{index}].source_line", line_counts)
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 600:
            raise SemanticValidationError(f"edges[{index}].evidence must be non-empty text no longer than 600 characters")
        # Reject paths that escape the repository, including symlink targets.
        try:
            (root.resolve() / source_file).resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            raise SemanticValidationError(f"edges[{index}].source_file resolves outside the repository") from None
        key = (source, target, relation)
        if key in seen_edges:
            raise SemanticValidationError(f"edges[{index}] duplicates a semantic relationship")
        seen_edges.add(key)
        semantic_edges.append(Edge(source, target, relation, evidence.strip(), confidence, score, source_file, source_line))

    structural_keys = {(edge.source, edge.target, edge.kind) for edge in graph.edges}
    duplicates = [edge for edge in semantic_edges if (edge.source, edge.target, edge.kind) in structural_keys]
    if duplicates:
        first = duplicates[0]
        raise SemanticValidationError(f"semantic edge duplicates structural relationship {first.kind}: {first.source} -> {first.target}")
    return semantic_nodes, semantic_edges


def apply_semantic_layer(graph: KnowledgeGraph, root: Path) -> tuple[KnowledgeGraph, tuple[int, int], str | None]:
    """Merge a fresh semantic artifact; return the base graph unchanged if stale/invalid."""
    path = root / SEMANTIC_FILE
    if not path.exists():
        return graph, (0, 0), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes, edges = validate_semantic_data(data, graph, root)
    except (OSError, UnicodeError, json.JSONDecodeError, SemanticValidationError) as error:
        return graph, (0, 0), str(error)
    graph.nodes.extend(nodes)
    graph.edges.extend(edges)
    graph.nodes.sort(key=lambda n: (n.path, n.line or 0, n.kind, n.name))
    graph.edges.sort(key=lambda e: (e.source, e.kind, e.target, e.evidence or ""))
    return graph, (len(nodes), len(edges)), None

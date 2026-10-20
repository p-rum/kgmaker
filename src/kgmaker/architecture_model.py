"""Versioned, deterministic high-level view documents.

This module deliberately models projections only. It does not load or mutate the
knowledge graph and does not infer evidence that is absent from the input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping


VIEW_SCHEMA_VERSION = 1
VIEW_KINDS = frozenset({"interfaces", "topology", "process"})
RESOLUTION_STATUSES = frozenset({"RESOLVED", "AMBIGUOUS", "UNRESOLVED"})
COVERAGE_STATUSES = frozenset({"COMPLETE_WITHIN_SELECTED_SCOPE", "PARTIAL", "UNKNOWN"})


class ViewValidationError(ValueError):
    """Invalid view input with stable machine-readable diagnostics."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = tuple(errors)
        super().__init__("; ".join(f"{e['code']}: {e['path']}" for e in errors))


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class ViewNode:
    id: str
    kind: str
    label: str
    original_ids: tuple[str, ...] = ()
    owner_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "label": self.label,
                "original_ids": sorted(set(self.original_ids)), "owner_id": self.owner_id,
                "evidence_refs": sorted(set(self.evidence_refs)),
                "attributes": dict(self.attributes)}


@dataclass(frozen=True)
class ViewEdge:
    id: str
    source: str
    target: str
    relation: str
    original_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    resolution_status: str = "UNRESOLVED"
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "source": self.source, "target": self.target,
                "relation": self.relation, "original_ids": sorted(set(self.original_ids)),
                "evidence_refs": sorted(set(self.evidence_refs)),
                "resolution_status": self.resolution_status,
                "attributes": dict(self.attributes)}


@dataclass(frozen=True)
class ViewDocument:
    view_id: str
    kind: str
    baseline_fingerprint: str
    rules_version: str
    scope: str
    context_selection: Mapping[str, Any]
    nodes: tuple[ViewNode, ...] = ()
    edges: tuple[ViewEdge, ...] = ()
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    coverage: Mapping[str, Any] = field(default_factory=lambda: {"status": "UNKNOWN"})
    limits: tuple[str, ...] = ()
    provenance: tuple[Mapping[str, Any], ...] = ()
    schema_version: int = VIEW_SCHEMA_VERSION
    generated_at: str | None = None

    def to_dict(self, *, include_generation_metadata: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "view_id": self.view_id,
            "kind": self.kind,
            "baseline_fingerprint": self.baseline_fingerprint,
            "rules_version": self.rules_version,
            "scope": self.scope,
            "context_selection": dict(self.context_selection),
            "nodes": [n.to_dict() for n in sorted(self.nodes, key=lambda n: n.id)],
            "edges": [e.to_dict() for e in sorted(self.edges, key=lambda e: e.id)],
            "diagnostics": sorted((dict(d) for d in self.diagnostics), key=_canonical),
            "coverage": dict(self.coverage),
            "limits": sorted(set(self.limits)),
            "provenance": sorted((dict(p) for p in self.provenance), key=_canonical),
        }
        if include_generation_metadata and self.generated_at is not None:
            result["generation_metadata"] = {"generated_at": self.generated_at}
        return result

    def to_json(self, *, include_generation_metadata: bool = True) -> str:
        return _canonical(self.to_dict(include_generation_metadata=include_generation_metadata))

    @property
    def content_fingerprint(self) -> str:
        return hashlib.sha256(self.to_json(include_generation_metadata=False).encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ViewDocument":
        validate_view_document(data)
        generation = data.get("generation_metadata", {})
        return cls(
            schema_version=data["schema_version"], view_id=data["view_id"], kind=data["kind"],
            baseline_fingerprint=data["baseline_fingerprint"],
            rules_version=data["rules_version"], scope=data["scope"],
            context_selection=dict(data["context_selection"]),
            nodes=tuple(ViewNode(id=n["id"], kind=n["kind"], label=n["label"],
                                 original_ids=tuple(n.get("original_ids", ())), owner_id=n.get("owner_id"),
                                 evidence_refs=tuple(n.get("evidence_refs", ())),
                                 attributes=dict(n.get("attributes", {}))) for n in data["nodes"]),
            edges=tuple(ViewEdge(id=e["id"], source=e["source"], target=e["target"],
                                 relation=e["relation"], original_ids=tuple(e.get("original_ids", ())),
                                 evidence_refs=tuple(e.get("evidence_refs", ())),
                                 resolution_status=e.get("resolution_status", "UNRESOLVED"),
                                 attributes=dict(e.get("attributes", {}))) for e in data["edges"]),
            diagnostics=tuple(dict(d) for d in data["diagnostics"]),
            coverage=dict(data["coverage"]), limits=tuple(data["limits"]),
            provenance=tuple(dict(p) for p in data["provenance"]),
            generated_at=generation.get("generated_at"),
        )


def validate_view_document(data: Mapping[str, Any]) -> None:
    """Validate the v1 public contract without modifying the supplied mapping."""
    errors: list[dict[str, str]] = []

    def err(code: str, path: str) -> None:
        errors.append({"code": code, "path": path})

    if not isinstance(data, Mapping):
        raise ViewValidationError([{"code": "INVALID_DOCUMENT", "path": "$"}])
    allowed = {"schema_version", "view_id", "kind", "baseline_fingerprint", "rules_version", "scope",
               "context_selection", "nodes", "edges", "diagnostics", "coverage", "limits", "provenance",
               "generation_metadata"}
    for key in set(data) - allowed:
        err("UNKNOWN_FIELD", str(key))
    try:
        json.dumps(data, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        err("NON_JSON_VALUE", "$")
    if type(data.get("schema_version")) is not int or data.get("schema_version") != VIEW_SCHEMA_VERSION:
        err("UNSUPPORTED_SCHEMA_VERSION", "schema_version")
    for key in ("view_id", "kind", "baseline_fingerprint", "rules_version", "scope"):
        if not isinstance(data.get(key), str) or not data.get(key):
            err("REQUIRED_STRING", key)
    if not isinstance(data.get("kind"), str) or data.get("kind") not in VIEW_KINDS:
        err("INVALID_KIND", "kind")
    if not isinstance(data.get("context_selection"), Mapping):
        err("INVALID_CONTEXT_SELECTION", "context_selection")
    for key in ("nodes", "edges", "diagnostics", "limits", "provenance"):
        if not isinstance(data.get(key), list):
            err("INVALID_COLLECTION", key)
    coverage = data.get("coverage")
    if (not isinstance(coverage, Mapping) or not isinstance(coverage.get("status"), str)
            or coverage.get("status") not in COVERAGE_STATUSES):
        err("INVALID_COVERAGE_STATUS", "coverage.status")
    generation = data.get("generation_metadata", {})
    if not isinstance(generation, Mapping):
        err("INVALID_GENERATION_METADATA", "generation_metadata")
    elif "generated_at" in generation and not isinstance(generation.get("generated_at"), str):
        err("INVALID_GENERATION_METADATA", "generation_metadata.generated_at")
    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    edges = data.get("edges") if isinstance(data.get("edges"), list) else []
    provenance = data.get("provenance") if isinstance(data.get("provenance"), list) else []
    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        path = f"nodes[{i}]"
        if not isinstance(node, Mapping):
            err("INVALID_NODE", path); continue
        node_fields = {"id", "kind", "label", "original_ids", "owner_id", "evidence_refs", "attributes"}
        for key in set(node) - node_fields:
            err("UNKNOWN_FIELD", f"{path}.{key}")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            err("REQUIRED_STRING", path + ".id")
        elif node_id in node_ids:
            err("DUPLICATE_NODE_ID", path + ".id")
        else:
            node_ids.add(node_id)
        for key in ("kind", "label"):
            if not isinstance(node.get(key), str) or not node.get(key): err("REQUIRED_STRING", path + "." + key)
        if node.get("owner_id") is not None and not isinstance(node.get("owner_id"), str):
            err("INVALID_OWNER_ID", path + ".owner_id")
        for key in ("original_ids", "evidence_refs"):
            values = node.get(key, [])
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
                err("INVALID_STRING_ARRAY", path + "." + key)
        if not isinstance(node.get("attributes", {}), Mapping):
            err("INVALID_ATTRIBUTES", path + ".attributes")
    edge_ids: set[str] = set()
    unresolved_edges = False
    for i, edge in enumerate(edges):
        path = f"edges[{i}]"
        if not isinstance(edge, Mapping):
            err("INVALID_EDGE", path); continue
        edge_fields = {"id", "source", "target", "relation", "original_ids", "evidence_refs",
                       "resolution_status", "attributes"}
        for key in set(edge) - edge_fields:
            err("UNKNOWN_FIELD", f"{path}.{key}")
        eid = edge.get("id")
        if not isinstance(eid, str) or not eid: err("REQUIRED_STRING", path + ".id")
        elif eid in edge_ids: err("DUPLICATE_EDGE_ID", path + ".id")
        else: edge_ids.add(eid)
        for key in ("source", "target", "relation"):
            if not isinstance(edge.get(key), str) or not edge.get(key): err("REQUIRED_STRING", path + "." + key)
        for end in ("source", "target"):
            if isinstance(edge.get(end), str) and edge[end] not in node_ids and not any(
                    isinstance(n, Mapping) and n.get("id") == edge[end] for n in nodes):
                err("DANGLING_EDGE_ENDPOINT", path + "." + end)
        status = edge.get("resolution_status", "UNRESOLVED")
        if not isinstance(status, str) or status not in RESOLUTION_STATUSES:
            err("INVALID_RESOLUTION_STATUS", path + ".resolution_status")
        elif status != "RESOLVED":
            unresolved_edges = True
        for key in ("original_ids", "evidence_refs"):
            values = edge.get(key, [])
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
                err("INVALID_STRING_ARRAY", path + "." + key)
        if not isinstance(edge.get("attributes", {}), Mapping):
            err("INVALID_ATTRIBUTES", path + ".attributes")
    diagnostics = data.get("diagnostics") if isinstance(data.get("diagnostics"), list) else []
    for i, diagnostic in enumerate(diagnostics):
        if not isinstance(diagnostic, Mapping):
            err("INVALID_DIAGNOSTIC", f"diagnostics[{i}]")
    limits = data.get("limits") if isinstance(data.get("limits"), list) else []
    for i, limit in enumerate(limits):
        if not isinstance(limit, str):
            err("INVALID_LIMIT", f"limits[{i}]")
    evidence_ids: set[str] = set()
    for i, item in enumerate(provenance):
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item.get("id"):
            err("INVALID_PROVENANCE", f"provenance[{i}]")
        elif item["id"] in evidence_ids:
            err("DUPLICATE_EVIDENCE_ID", f"provenance[{i}].id")
        else:
            evidence_ids.add(item["id"])
        if isinstance(item, Mapping) and "evidence_kind" in item and not isinstance(item["evidence_kind"], str):
            err("INVALID_EVIDENCE_KIND", f"provenance[{i}].evidence_kind")
    if unresolved_edges and isinstance(coverage, Mapping) and coverage.get("status") == "COMPLETE_WITHIN_SELECTED_SCOPE":
        err("UNRESOLVED_EDGE_WITH_COMPLETE_COVERAGE", "coverage.status")
    for collection_name in ("nodes", "edges"):
        collection = data.get(collection_name) if isinstance(data.get(collection_name), list) else []
        for i, item in enumerate(collection):
            if not isinstance(item, Mapping): continue
            refs = item.get("evidence_refs", [])
            if not isinstance(refs, list) and not isinstance(refs, tuple):
                err("INVALID_EVIDENCE_REFS", f"{collection_name}[{i}].evidence_refs"); continue
            for j, ref in enumerate(refs):
                if not isinstance(ref, str) or ref not in evidence_ids:
                    err("INVALID_EVIDENCE_REFERENCE", f"{collection_name}[{i}].evidence_refs[{j}]")
    if errors:
        raise ViewValidationError(errors)


"""Versioned, deterministic high-level view documents.

This module deliberately models projections only. It does not load or mutate the
knowledge graph and does not infer evidence that is absent from the input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence


VIEW_SCHEMA_VERSION = 1
VIEW_KINDS = frozenset({"interfaces", "topology", "process"})
RESOLUTION_STATUSES = frozenset({"RESOLVED", "AMBIGUOUS", "UNRESOLVED"})
COVERAGE_STATUSES = frozenset({"COMPLETE_WITHIN_SELECTED_SCOPE", "PARTIAL", "UNKNOWN"})
FRESHNESS_STATUSES = frozenset({"CURRENT", "STALE", "UNKNOWN"})
EVIDENCE_KINDS = frozenset({"SYNTAX_CANDIDATE", "SYMBOL_RESOLVED", "DISPATCH_CANDIDATE",
                            "FRAMEWORK_DERIVED", "RUNTIME_OBSERVED", "UNRESOLVED",
                            "SOURCE_ONLY", "UNKNOWN"})
EVIDENCE_POLARITIES = frozenset({"SUPPORTING", "CONTRADICTING", "UNKNOWN"})


class ViewValidationError(ValueError):
    """Invalid view input with stable machine-readable diagnostics."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = tuple(errors)
        super().__init__("; ".join(f"{e['code']}: {e['path']}" for e in errors))


def _reference_buckets(refs: Sequence[str], supporting: Sequence[str] = (),
                       contradicting: Sequence[str] = (), unknown: Sequence[str] | None = None):
    all_refs = set(refs)
    support = set(supporting)
    contra = set(contradicting)
    unknown_set = set(unknown) if unknown is not None else all_refs - support - contra
    return all_refs, support, contra, unknown_set


def _canonical_freshness(value: Any) -> str:
    return value if isinstance(value, str) and value in FRESHNESS_STATUSES else "UNKNOWN"


def aggregate_view_edges(edges: Sequence[ViewEdge], provenance: Sequence[Mapping[str, Any]], *,
                         scope: str | None = None, context_ids: Sequence[str] | None = None,
                         diagnostics: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Aggregate duplicate view claims without hiding evidence, uncertainty, or realm.

    Claims are combined only when source, target, relation, scope, and exact context
    selection agree. ``polarity`` is consumed only from an explicit, valid field on
    the claim or referenced provenance; otherwise the reference remains UNKNOWN.
    ``coverage`` describes only the supplied claim set, never an inferred whole system.
    """
    if scope is not None and (not isinstance(scope, str) or not scope):
        raise ViewValidationError([{"code": "INVALID_SCOPE", "path": "scope"}])
    if not isinstance(edges, (list, tuple)):
        raise ViewValidationError([{"code": "INVALID_EDGES", "path": "edges"}])
    if context_ids is not None and (not isinstance(context_ids, (list, tuple, set))
                                    or any(not isinstance(item, str) or not item for item in context_ids)):
        raise ViewValidationError([{"code": "INVALID_CONTEXT_IDS", "path": "context_ids"}])
    if not isinstance(provenance, (list, tuple)) or any(not isinstance(item, Mapping) for item in provenance):
        raise ViewValidationError([{"code": "INVALID_PROVENANCE", "path": "provenance"}])
    evidence = {item.get("id"): item for item in provenance
                if isinstance(item.get("id"), str)}
    if len(evidence) != len(provenance):
        raise ViewValidationError([{"code": "INVALID_PROVENANCE", "path": "provenance"}])
    if not isinstance(diagnostics, (list, tuple)) or any(not isinstance(item, Mapping) for item in diagnostics):
        raise ViewValidationError([{"code": "INVALID_DIAGNOSTIC", "path": "diagnostics"}])
    selected_contexts = set(context_ids) if context_ids is not None else None
    groups: dict[tuple, list[ViewEdge]] = {}
    excluded_identities: set[tuple] = set()
    result_diagnostics = [dict(item) for item in diagnostics]
    for index, edge in enumerate(edges):
        if not isinstance(edge, ViewEdge):
            raise ViewValidationError([{"code": "INVALID_EDGE", "path": f"edges[{index}]"}])
        if not isinstance(edge.resolution_status, str) or edge.resolution_status not in RESOLUTION_STATUSES:
            raise ViewValidationError([{"code": "INVALID_RESOLUTION_STATUS", "path": f"edges[{index}].resolution_status"}])
        if any(not isinstance(value, str) or not value for value in (edge.id, edge.source, edge.target, edge.relation)):
            raise ViewValidationError([{"code": "INVALID_EDGE_IDENTITY", "path": f"edges[{index}]"}])
        if not isinstance(edge.attributes, Mapping):
            raise ViewValidationError([{"code": "INVALID_ATTRIBUTES", "path": f"edges[{index}].attributes"}])
        if not isinstance(edge.evidence_refs, (list, tuple)) or any(not isinstance(ref, str) for ref in edge.evidence_refs):
            raise ViewValidationError([{"code": "INVALID_EVIDENCE_REFERENCE", "path": f"edges[{index}].evidence_refs"}])
        for field_name in ("original_ids", "evidence_kinds", "supporting_refs", "contradicting_refs", "unknown_refs"):
            values = getattr(edge, field_name)
            if not isinstance(values, (list, tuple)) or any(not isinstance(value, str) for value in values):
                raise ViewValidationError([{"code": "INVALID_STRING_ARRAY", "path": f"edges[{index}].{field_name}"}])
        if not set(edge.evidence_refs).issubset(evidence):
            raise ViewValidationError([{"code": "INVALID_EVIDENCE_REFERENCE", "path": f"edges[{index}].evidence_refs"}])
        if not isinstance(edge.freshness, str) or edge.freshness not in FRESHNESS_STATUSES:
            raise ViewValidationError([{"code": "INVALID_FRESHNESS", "path": f"edges[{index}].freshness"}])
        attrs = dict(edge.attributes)
        edge_scope = attrs.get("scope")
        if edge_scope is not None and (not isinstance(edge_scope, str) or not edge_scope):
            raise ViewValidationError([{"code": "INVALID_SCOPE", "path": f"edges[{index}].attributes.scope"}])
        raw_contexts = attrs.get("context_ids", [])
        if not isinstance(raw_contexts, (list, tuple)) or any(not isinstance(item, str) or not item for item in raw_contexts):
            raise ViewValidationError([{"code": "INVALID_CONTEXT_IDS", "path": f"edges[{index}].attributes.context_ids"}])
        claim_contexts = tuple(sorted(set(raw_contexts)))
        identity = (edge.source, edge.target, edge.relation,
                    edge_scope if edge_scope is not None else "UNKNOWN", claim_contexts)
        if scope is not None and edge_scope is not None and edge_scope != scope:
            excluded_identities.add(identity)
            continue
        if selected_contexts is not None and claim_contexts and not set(claim_contexts).issubset(selected_contexts):
            excluded_identities.add(identity)
            continue
        groups.setdefault(identity, []).append(edge)

    result_edges: list[ViewEdge] = []
    for identity, claims in sorted(groups.items(), key=lambda item: _canonical(item[0])):
        all_refs: set[str] = set()
        supporting: set[str] = set()
        contradicting: set[str] = set()
        unknown: set[str] = set()
        kinds: set[str] = set()
        freshness_values: list[str] = []
        statuses: set[str] = set()
        originals: set[str] = set()
        claim_sources = []
        for claim in claims:
            statuses.add(claim.resolution_status)
            all_refs.update(claim.evidence_refs)
            originals.update(claim.original_ids)
            originals.add(claim.id)
            if claim.evidence_kinds:
                kinds.update(kind for kind in claim.evidence_kinds
                              if isinstance(kind, str) and kind in EVIDENCE_KINDS)
                if any(not isinstance(kind, str) or kind not in EVIDENCE_KINDS
                       for kind in claim.evidence_kinds):
                    result_diagnostics.append({"code": "INVALID_EVIDENCE_KIND", "edge_id": claim.id,
                                               "message": "Unsupported evidence kind was retained as UNKNOWN"})
            freshness_values.append(_canonical_freshness(claim.freshness))
            refs, supports, contras, unknowns = _reference_buckets(
                claim.evidence_refs, claim.supporting_refs, claim.contradicting_refs,
                claim.unknown_refs if claim.unknown_refs else None)
            if not refs:
                result_diagnostics.append({"code": "VIEW_EVIDENCE_MISSING", "edge_id": claim.id,
                                           "message": "Claim has no evidence reference and cannot establish completeness"})
            if supports & contras or (supports | contras | unknowns) != refs:
                raise ViewValidationError([{"code": "INVALID_EVIDENCE_POLARITY_PARTITION", "path": claim.id}])
            for ref in refs:
                record = evidence.get(ref, {})
                kind = record.get("evidence_kind", "UNKNOWN")
                kinds.add(kind if isinstance(kind, str) and kind in EVIDENCE_KINDS else "UNKNOWN")
                if "evidence_kind" in record and (not isinstance(kind, str) or kind not in EVIDENCE_KINDS):
                    result_diagnostics.append({"code": "INVALID_EVIDENCE_KIND", "evidence_ref": ref,
                                               "message": "Unsupported evidence kind was retained as UNKNOWN"})
                pol = record.get("polarity")
                if ((ref in supports and pol not in (None, "SUPPORTING"))
                        or (ref in contras and pol not in (None, "CONTRADICTING"))
                        or (ref in unknowns and pol in ("SUPPORTING", "CONTRADICTING"))):
                    raise ViewValidationError([{"code": "EVIDENCE_POLARITY_NOT_PRESERVED", "path": claim.id}])
                if ref in supports or pol == "SUPPORTING":
                    supporting.add(ref)
                elif ref in contras or pol == "CONTRADICTING":
                    contradicting.add(ref)
                else:
                    unknown.add(ref)
                    if pol is not None and (not isinstance(pol, str) or pol not in EVIDENCE_POLARITIES):
                        result_diagnostics.append({"code": "INVALID_EVIDENCE_POLARITY",
                                                   "evidence_ref": ref,
                                                   "message": "Invalid explicit polarity was retained as UNKNOWN"})
                record_freshness = record.get("freshness", "UNKNOWN")
                freshness_values.append(_canonical_freshness(record_freshness))
                if "freshness" in record and _canonical_freshness(record_freshness) == "UNKNOWN" \
                        and record_freshness != "UNKNOWN":
                    result_diagnostics.append({"code": "INVALID_FRESHNESS", "evidence_ref": ref,
                                               "message": "Unsupported freshness was retained as UNKNOWN"})
            if not raw_contexts_for_claim(claim):
                result_diagnostics.append({"code": "VIEW_CONTEXT_UNKNOWN", "edge_id": claim.id,
                                           "message": "Claim has no explicit context identity; it was kept separate"})
            claim_sources.append({"id": claim.id, "resolution_status": claim.resolution_status,
                                  "freshness": claim.freshness,
                                  "attributes": dict(claim.attributes)})
        if supporting & contradicting:
            # A single source ref cannot be both polarities.
            raise ViewValidationError([{"code": "CONFLICTING_REFERENCE_POLARITY", "path": identity[0]}])
        conflict = bool(supporting and contradicting)
        resolution = ("AMBIGUOUS" if conflict or "AMBIGUOUS" in statuses else
                      "UNRESOLVED" if "UNRESOLVED" in statuses or identity[3] == "UNKNOWN" else
                      "RESOLVED")
        freshness = ("STALE" if "STALE" in freshness_values else
                     "CURRENT" if freshness_values and all(value == "CURRENT" for value in freshness_values)
                     and all(claim.freshness in FRESHNESS_STATUSES for claim in claims) else "UNKNOWN")
        # Preserve all source claim status/attributes so a stronger constituent
        # cannot erase a weaker or unresolved one during presentation.
        attrs = {"scope": identity[3], "context_ids": list(identity[4]),
                 "source_claims": sorted(claim_sources, key=_canonical)}
        if conflict:
            result_diagnostics.append({"code": "CONTRADICTORY_VIEW_EVIDENCE",
                                       "source": identity[0], "target": identity[1],
                                       "relation": identity[2],
                                       "message": "Explicit supporting and contradicting evidence remain visible"})
        if unknown:
            result_diagnostics.append({"code": "VIEW_EVIDENCE_POLARITY_UNKNOWN",
                                       "source": identity[0], "target": identity[1],
                                       "relation": identity[2], "evidence_refs": sorted(unknown),
                                       "message": "Evidence without explicit valid polarity remains UNKNOWN"})
        edge_id = claims[0].id if len(claims) == 1 else "aggregate-edge:" + hashlib.sha256(
            _canonical(identity).encode("utf-8")).hexdigest()[:24]
        result_edges.append(ViewEdge(
            id=edge_id, source=identity[0], target=identity[1], relation=identity[2],
            original_ids=tuple(sorted(originals)), evidence_refs=tuple(sorted(all_refs)),
            resolution_status=resolution, attributes=attrs, evidence_kinds=tuple(sorted(kinds)),
            freshness=freshness, supporting_refs=tuple(sorted(supporting)),
            contradicting_refs=tuple(sorted(contradicting)), unknown_refs=tuple(sorted(unknown)),
        ))
    found = len(result_edges)
    resolved = sum(edge.resolution_status == "RESOLVED" for edge in result_edges)
    unresolved = found - resolved
    excluded = len(excluded_identities)
    coverage_status = ("UNKNOWN" if not found else
                       "PARTIAL" if unresolved or excluded or result_diagnostics
                       or any(edge.freshness != "CURRENT" for edge in result_edges) else
                       "COMPLETE_WITHIN_SELECTED_SCOPE")
    return {"edges": tuple(result_edges), "provenance": tuple(sorted((dict(item) for item in provenance), key=_canonical)),
            "diagnostics": tuple(sorted(result_diagnostics, key=_canonical)),
            "coverage": {"status": coverage_status,
                         "counts": {"found": found, "resolved": resolved,
                                    "unresolved": unresolved, "excluded": excluded}}}


def raw_contexts_for_claim(edge: ViewEdge) -> tuple[str, ...]:
    value = (edge.attributes or {}).get("context_ids", [])
    return tuple(value) if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value) else ()


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
    evidence_kinds: tuple[str, ...] = ()
    resolution_status: str = "UNRESOLVED"
    freshness: str = "UNKNOWN"
    supporting_refs: tuple[str, ...] = ()
    contradicting_refs: tuple[str, ...] = ()
    unknown_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        refs = set(self.evidence_refs)
        support = set(self.supporting_refs)
        contra = set(self.contradicting_refs)
        unknown = set(self.unknown_refs) | (refs - support - contra)
        return {"id": self.id, "kind": self.kind, "label": self.label,
                "original_ids": sorted(set(self.original_ids)), "owner_id": self.owner_id,
                "evidence_refs": sorted(set(self.evidence_refs)),
                "attributes": dict(self.attributes),
                "evidence_kinds": sorted(set(self.evidence_kinds)),
                "resolution_status": self.resolution_status, "freshness": self.freshness,
                "supporting_refs": sorted(support),
                "contradicting_refs": sorted(contra),
                "unknown_refs": sorted(unknown)}


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
    evidence_kinds: tuple[str, ...] = ()
    freshness: str = "UNKNOWN"
    supporting_refs: tuple[str, ...] = ()
    contradicting_refs: tuple[str, ...] = ()
    unknown_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        refs = set(self.evidence_refs)
        support = set(self.supporting_refs)
        contra = set(self.contradicting_refs)
        unknown = set(self.unknown_refs) | (refs - support - contra)
        return {"id": self.id, "source": self.source, "target": self.target,
                "relation": self.relation, "original_ids": sorted(set(self.original_ids)),
                "evidence_refs": sorted(set(self.evidence_refs)),
                "resolution_status": self.resolution_status,
                "attributes": dict(self.attributes),
                "evidence_kinds": sorted(set(self.evidence_kinds)), "freshness": self.freshness,
                "supporting_refs": sorted(support),
                "contradicting_refs": sorted(contra),
                "unknown_refs": sorted(unknown)}


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
            "provenance": sorted(({"evidence_kind": "UNKNOWN", "freshness": "UNKNOWN",
                                   "polarity": "UNKNOWN", **dict(p)} for p in self.provenance), key=_canonical),
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
        provenance_index = {item["id"]: item for item in data["provenance"]}

        def ref_buckets(item: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
            refs = set(item.get("evidence_refs", ()))
            supporting = set(item.get("supporting_refs", ()))
            contradicting = set(item.get("contradicting_refs", ()))
            if not any(key in item for key in ("supporting_refs", "contradicting_refs", "unknown_refs")):
                for ref in refs:
                    polarity = provenance_index.get(ref, {}).get("polarity", "UNKNOWN")
                    if polarity == "SUPPORTING": supporting.add(ref)
                    elif polarity == "CONTRADICTING": contradicting.add(ref)
            unknown = set(item.get("unknown_refs", ())) | (refs - supporting - contradicting)
            return tuple(sorted(supporting)), tuple(sorted(contradicting)), tuple(sorted(unknown))

        return cls(
            schema_version=data["schema_version"], view_id=data["view_id"], kind=data["kind"],
            baseline_fingerprint=data["baseline_fingerprint"],
            rules_version=data["rules_version"], scope=data["scope"],
            context_selection=dict(data["context_selection"]),
            nodes=tuple(ViewNode(id=n["id"], kind=n["kind"], label=n["label"],
                                 original_ids=tuple(n.get("original_ids", ())), owner_id=n.get("owner_id"),
                                 evidence_refs=tuple(n.get("evidence_refs", ())),
                                 attributes=dict(n.get("attributes", {})),
                                 evidence_kinds=tuple(n.get("evidence_kinds", ())),
                                 resolution_status=n.get("resolution_status", "UNRESOLVED"),
                                 freshness=n.get("freshness", "UNKNOWN"),
                                 supporting_refs=ref_buckets(n)[0],
                                 contradicting_refs=ref_buckets(n)[1], unknown_refs=ref_buckets(n)[2])
                        for n in data["nodes"]),
            edges=tuple(ViewEdge(id=e["id"], source=e["source"], target=e["target"],
                                 relation=e["relation"], original_ids=tuple(e.get("original_ids", ())),
                                 evidence_refs=tuple(e.get("evidence_refs", ())),
                                 resolution_status=e.get("resolution_status", "UNRESOLVED"),
                                 attributes=dict(e.get("attributes", {})),
                                 evidence_kinds=tuple(e.get("evidence_kinds", ())),
                                 freshness=e.get("freshness", "UNKNOWN"),
                                 supporting_refs=ref_buckets(e)[0],
                                 contradicting_refs=ref_buckets(e)[1], unknown_refs=ref_buckets(e)[2])
                        for e in data["edges"]),
            diagnostics=tuple(dict(d) for d in data["diagnostics"]),
            coverage=dict(data["coverage"]), limits=tuple(data["limits"]),
            provenance=tuple({"evidence_kind": "UNKNOWN", "freshness": "UNKNOWN", "polarity": "UNKNOWN", **dict(p)}
                             for p in data["provenance"]),
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
    if isinstance(coverage, Mapping) and "counts" in coverage:
        counts = coverage.get("counts")
        count_names = {"found", "resolved", "unresolved", "excluded"}
        if (not isinstance(counts, Mapping) or set(counts) != count_names
                or any(type(counts.get(name)) is not int or counts.get(name) < 0 for name in count_names)
                or (isinstance(counts, Mapping) and type(counts.get("found")) is int
                    and type(counts.get("resolved")) is int and type(counts.get("unresolved")) is int
                    and counts["found"] != counts["resolved"] + counts["unresolved"])):
            err("INVALID_COVERAGE_COUNTS", "coverage.counts")
    generation = data.get("generation_metadata", {})
    if not isinstance(generation, Mapping):
        err("INVALID_GENERATION_METADATA", "generation_metadata")
    else:
        for key in set(generation) - {"generated_at"}:
            err("UNKNOWN_FIELD", f"generation_metadata.{key}")
        if "generated_at" in generation and not isinstance(generation.get("generated_at"), str):
            err("INVALID_GENERATION_METADATA", "generation_metadata.generated_at")
    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    edges = data.get("edges") if isinstance(data.get("edges"), list) else []
    provenance = data.get("provenance") if isinstance(data.get("provenance"), list) else []
    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        path = f"nodes[{i}]"
        if not isinstance(node, Mapping):
            err("INVALID_NODE", path); continue
        node_fields = {"id", "kind", "label", "original_ids", "owner_id", "evidence_refs", "attributes",
                       "evidence_kinds", "resolution_status", "freshness", "supporting_refs",
                       "contradicting_refs", "unknown_refs"}
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
        for key in ("original_ids", "evidence_refs", "evidence_kinds", "supporting_refs",
                    "contradicting_refs", "unknown_refs"):
            values = node.get(key, [])
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
                err("INVALID_STRING_ARRAY", path + "." + key)
        kinds = node.get("evidence_kinds", [])
        if isinstance(kinds, (list, tuple)) and any(not isinstance(kind, str) or kind not in EVIDENCE_KINDS
                                                    for kind in kinds):
            err("INVALID_EVIDENCE_KIND", path + ".evidence_kinds")
        status = node.get("resolution_status", "UNRESOLVED")
        if not isinstance(status, str) or status not in RESOLUTION_STATUSES:
            err("INVALID_RESOLUTION_STATUS", path + ".resolution_status")
        freshness = node.get("freshness", "UNKNOWN")
        if not isinstance(freshness, str) or freshness not in FRESHNESS_STATUSES:
            err("INVALID_FRESHNESS", path + ".freshness")
        refs = node.get("evidence_refs", [])
        bucket_values = [refs, node.get("supporting_refs", []), node.get("contradicting_refs", []),
                         node.get("unknown_refs", [])]
        if all(isinstance(values, (list, tuple)) and all(isinstance(ref, str) for ref in values)
               for values in bucket_values):
            _, support, contra, unknown = _reference_buckets(
                refs, node.get("supporting_refs", []), node.get("contradicting_refs", []),
                node.get("unknown_refs") if "unknown_refs" in node else None)
            if support & contra or (support | contra | unknown) != set(refs):
                err("INVALID_EVIDENCE_POLARITY_PARTITION", path)
        if not isinstance(node.get("attributes", {}), Mapping):
            err("INVALID_ATTRIBUTES", path + ".attributes")
    edge_ids: set[str] = set()
    unresolved_edges = False
    for i, edge in enumerate(edges):
        path = f"edges[{i}]"
        if not isinstance(edge, Mapping):
            err("INVALID_EDGE", path); continue
        edge_fields = {"id", "source", "target", "relation", "original_ids", "evidence_refs",
                       "resolution_status", "attributes", "evidence_kinds", "freshness",
                       "supporting_refs", "contradicting_refs", "unknown_refs"}
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
        for key in ("original_ids", "evidence_refs", "evidence_kinds", "supporting_refs",
                    "contradicting_refs", "unknown_refs"):
            values = edge.get(key, [])
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
                err("INVALID_STRING_ARRAY", path + "." + key)
        kinds = edge.get("evidence_kinds", [])
        if isinstance(kinds, (list, tuple)) and any(not isinstance(kind, str) or kind not in EVIDENCE_KINDS
                                                    for kind in kinds):
            err("INVALID_EVIDENCE_KIND", path + ".evidence_kinds")
        freshness = edge.get("freshness", "UNKNOWN")
        if not isinstance(freshness, str) or freshness not in FRESHNESS_STATUSES:
            err("INVALID_FRESHNESS", path + ".freshness")
        refs = edge.get("evidence_refs", [])
        bucket_values = [refs, edge.get("supporting_refs", []), edge.get("contradicting_refs", []),
                         edge.get("unknown_refs", [])]
        if all(isinstance(values, (list, tuple)) and all(isinstance(ref, str) for ref in values)
               for values in bucket_values):
            _, support, contra, unknown = _reference_buckets(
                refs, edge.get("supporting_refs", []), edge.get("contradicting_refs", []),
                edge.get("unknown_refs") if "unknown_refs" in edge else None)
            if support & contra or (support | contra | unknown) != set(refs):
                err("INVALID_EVIDENCE_POLARITY_PARTITION", path)
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
    provenance_index: dict[str, Mapping[str, Any]] = {}
    for i, item in enumerate(provenance):
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item.get("id"):
            err("INVALID_PROVENANCE", f"provenance[{i}]")
        elif item["id"] in evidence_ids:
            err("DUPLICATE_EVIDENCE_ID", f"provenance[{i}].id")
        else:
            evidence_ids.add(item["id"])
            provenance_index[item["id"]] = item
        if isinstance(item, Mapping):
            kind = item.get("evidence_kind", "UNKNOWN")
            if not isinstance(kind, str) or kind not in EVIDENCE_KINDS:
                err("INVALID_EVIDENCE_KIND", f"provenance[{i}].evidence_kind")
            freshness = item.get("freshness", "UNKNOWN")
            if not isinstance(freshness, str) or freshness not in FRESHNESS_STATUSES:
                err("INVALID_FRESHNESS", f"provenance[{i}].freshness")
            polarity = item.get("polarity", "UNKNOWN")
            if not isinstance(polarity, str) or polarity not in EVIDENCE_POLARITIES:
                err("INVALID_EVIDENCE_POLARITY", f"provenance[{i}].polarity")
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
            existing_records = [provenance_index[ref] for ref in refs if isinstance(ref, str) and ref in provenance_index]
            explicit_polarities = {record.get("id"): record.get("polarity", "UNKNOWN")
                                   for record in existing_records}
            bucket_values = [item.get("supporting_refs", []), item.get("contradicting_refs", []),
                             item.get("unknown_refs", [])]
            if all(isinstance(values, (list, tuple)) and all(isinstance(ref, str) for ref in values)
                   for values in bucket_values):
                supporting = set(bucket_values[0])
                contradicting = set(bucket_values[1])
                unknown_refs = (set(bucket_values[2]) if "unknown_refs" in item
                                else set(refs) - supporting - contradicting)
                for ref, polarity in explicit_polarities.items():
                    if ((polarity == "SUPPORTING" and ref not in supporting)
                            or (polarity == "CONTRADICTING" and ref not in contradicting)
                            or (polarity == "UNKNOWN" and ref not in unknown_refs)):
                        err("EVIDENCE_POLARITY_NOT_PRESERVED", f"{collection_name}[{i}].evidence_refs")
            kinds = set(item.get("evidence_kinds", []))
            ref_kinds = {record.get("evidence_kind", "UNKNOWN") for record in existing_records}
            if kinds and kinds != ref_kinds:
                err("EVIDENCE_KIND_NOT_PRESERVED", f"{collection_name}[{i}].evidence_kinds")
            freshness = item.get("freshness", "UNKNOWN")
            ref_freshness = {record.get("freshness", "UNKNOWN") for record in existing_records}
            if freshness == "CURRENT" and ref_freshness and ref_freshness != {"CURRENT"}:
                err("FRESHNESS_UPGRADE", f"{collection_name}[{i}].freshness")
    if errors:
        raise ViewValidationError(errors)

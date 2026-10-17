"""Small serializable graph model shared by the scanner and renderers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    name: str
    path: str
    line: int | None = None
    signature: str | None = None
    summary: str | None = None
    scope: str = "unknown"
    role: str = "unknown"
    origin: str = "unknown"
    build_membership: tuple[str, ...] = ()
    classification_evidence: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str
    evidence: str | None = None
    confidence: str = "EXTRACTED"
    confidence_score: float = 1.0
    source_file: str | None = None
    source_line: int | None = None
    evidence_kind: str = "SYNTAX_CANDIDATE"
    context_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass
class KnowledgeGraph:
    schema_version: int
    root: str
    generated_at: str
    nodes: list[Node]
    edges: list[Edge]
    files: dict[str, str]
    contexts: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    symbols: list[dict[str, Any]] = field(default_factory=list)
    call_sites: list[dict[str, Any]] = field(default_factory=list)
    cfgs: list[dict[str, Any]] = field(default_factory=list)
    analysis_annotations: list[dict[str, Any]] = field(default_factory=list)

    def migrate_legacy(self) -> "KnowledgeGraph":
        """Keep original IDs as legacy identities; do not claim JVM/TS resolution."""
        if self.schema_version in {2, 3}:
            return self
        mapping = {n.id: n.id for n in self.nodes}
        if len(mapping) != len(self.nodes):
            raise ValueError("Ambiguous legacy IDs; prepare a new semantic packet")
        return replace(self, schema_version=2,
                       nodes=[replace(n, scope="unknown", role="unknown", origin="unknown",
                                      build_membership=(), classification_evidence=("legacy-v1:no-scope-proof",)) for n in self.nodes],
                       edges=[replace(e, evidence_kind="SYNTAX_CANDIDATE", context_ids=(), evidence_ids=()) for e in self.edges],
                       contexts=[{"mode": "SOURCE_ONLY", "coverage": "PARTIAL", "origin_trust": "LEGACY_UNKNOWN",
                                  "identity_mapping": mapping, "identity_kind": "LEGACY", "freshness": "UNKNOWN"}],
                       diagnostics=[{"code": "LEGACY_RESOLUTION_UNKNOWN", "reason": "v1 confidence does not prove symbol resolution"}])

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "root": self.root,
            "generated_at": self.generated_at,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "files": self.files,
            "contexts": self.contexts,
            "diagnostics": self.diagnostics,
            "evidence": self.evidence,
        }
        if self.schema_version == 3:
            result.update(symbols=self.symbols, call_sites=self.call_sites, cfgs=self.cfgs,
                          analysis_annotations=self.analysis_annotations)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGraph":
        version = data.get("schema_version", 1)
        if type(version) is not int or version not in {1, 2, 3}:
            raise ValueError(f"Unsupported graph schema_version {version!r}; expected 1, 2 or 3")
        nodes = []
        for item in data.get("nodes", []):
            item = dict(item)
            if version == 1:
                for key in ("scope", "role", "origin"):
                    item[key] = "unknown"
                item["build_membership"] = ()
                item["classification_evidence"] = ()
            for key in ("build_membership", "classification_evidence"):
                if key in item:
                    if not isinstance(item[key], (list, tuple)) or not all(isinstance(v, str) for v in item[key]):
                        raise ValueError("Invalid node metadata array")
                    item[key] = tuple(item[key])
            nodes.append(Node(**item))
        edges = []
        for item in data.get("edges", []):
            item = dict(item)
            for key in ("context_ids", "evidence_ids"):
                if key in item:
                    if not isinstance(item[key], (list, tuple)) or not all(isinstance(v, str) for v in item[key]):
                        raise ValueError("Invalid edge reference array")
                    item[key] = tuple(item[key])
            if version == 1:
                item["evidence_kind"] = "SYNTAX_CANDIDATE"
            edges.append(Edge(**item))
        if version in {2, 3}:
            from .classification import SCOPES, ROLES, ORIGINS
            ids = {n.id for n in nodes}
            if len(ids) != len(nodes):
                raise ValueError("Duplicate graph node IDs")
            for n in nodes:
                if n.scope not in SCOPES or n.role not in ROLES or n.origin not in ORIGINS:
                    raise ValueError("Invalid graph classification")
            kinds = {"SYNTAX_CANDIDATE", "SYMBOL_RESOLVED", "DISPATCH_CANDIDATE", "FRAMEWORK_DERIVED", "RUNTIME_OBSERVED", "UNRESOLVED"}
            contexts = data.get("contexts", [])
            evidence = data.get("evidence", [])
            if not isinstance(contexts, list) or not all(isinstance(c, dict) for c in contexts):
                raise ValueError("Invalid analysis contexts")
            if not isinstance(evidence, list) or not all(isinstance(e, dict) and isinstance(e.get("id"), str) for e in evidence):
                raise ValueError("Invalid evidence inventory")
            context_ids = {c.get("id") for c in contexts if isinstance(c.get("id"), str)}
            evidence_ids = {e["id"] for e in evidence}
            evidence_index = {e["id"]: e for e in evidence}
            if len(evidence_ids) != len(evidence):
                raise ValueError("Duplicate evidence IDs")
            for e in edges:
                if e.source not in ids or e.target not in ids:
                    raise ValueError("Dangling graph edge")
                if e.evidence_kind not in kinds:
                    raise ValueError("Invalid evidence kind")
                if set(e.context_ids) - context_ids or set(e.evidence_ids) - evidence_ids:
                    raise ValueError("Dangling context/evidence reference")
                if any(evidence_index[i].get("kind") != e.evidence_kind for i in e.evidence_ids):
                    raise ValueError("Evidence kind does not support the claimed relationship")
                if e.evidence_kind not in {"SYNTAX_CANDIDATE", "UNRESOLVED"} and (not e.context_ids or not e.evidence_ids):
                    raise ValueError("Resolved/derived evidence requires context and evidence IDs")
            if version == 3:
                for key in ("symbols", "call_sites", "cfgs", "analysis_annotations"):
                    if not isinstance(data.get(key, []), list) or not all(isinstance(v, dict) for v in data.get(key, [])):
                        raise ValueError("Invalid inspection collection: " + key)
                symbol_ids = set()
                for symbol in data.get("symbols", []):
                    if symbol.get("id") not in ids or symbol.get("id") in symbol_ids or symbol.get("context_id") not in context_ids:
                        raise ValueError("Dangling/duplicate compiler symbol or context")
                    symbol_ids.add(symbol["id"])
                site_ids = set()
                for site in data.get("call_sites", []):
                    if site.get("id") not in ids or site["id"] in site_ids or site.get("caller") not in ids:
                        raise ValueError("Dangling/duplicate call site")
                    if site.get("context_id") not in context_ids or site.get("evidence_kind") not in kinds or set(site.get("evidence_ids", [])) - evidence_ids:
                        raise ValueError("Dangling call-site context/evidence")
                    if site.get("evidence_kind") == "SYMBOL_RESOLVED" and site.get("declared_target") is None and not site.get("omitted_declared_target"):
                        raise ValueError("Resolved call site has no declared target")
                    site_ids.add(site["id"])
                    if site.get("declared_target") is not None and site["declared_target"] not in ids:
                        raise ValueError("Dangling declared target")
                    if not isinstance(site.get("dispatch_candidates", []), list) or any(c not in ids for c in site.get("dispatch_candidates", [])):
                        raise ValueError("Dangling dispatch candidate")
                    if not site.get("resolution_reason"):
                        raise ValueError("Call site requires resolution reason")
                for cfg in data.get("cfgs", []):
                    if cfg.get("context_id") not in context_ids or cfg.get("method") not in ids or not isinstance(cfg.get("blocks"), list) or not isinstance(cfg.get("edges"), list):
                        raise ValueError("Invalid CFG")
                    blocks = {b.get("id") for b in cfg["blocks"] if isinstance(b, dict)}
                    if len(blocks) != len(cfg["blocks"]) or cfg.get("entry") not in blocks or cfg.get("exit") not in blocks:
                        raise ValueError("Invalid CFG blocks/entry/exit")
                    if any(not isinstance(e, dict) or e.get("source") not in blocks or e.get("target") not in blocks for e in cfg["edges"]):
                        raise ValueError("Dangling CFG edge")
                for annotation in data.get("analysis_annotations", []):
                    if set(annotation) - {"id", "origin", "target_ids", "evidence_ids", "label", "explanation", "language", "model_id"}:
                        raise ValueError("Annotation cannot add technical fields")
                    if set(annotation.get("target_ids", [])) - ids:
                        raise ValueError("Annotation cannot invent target IDs")
                    if annotation.get("origin") != "LLM_ANNOTATION" or set(annotation.get("evidence_ids", [])) - evidence_ids:
                        raise ValueError("Annotation cannot create technical evidence")
        return cls(
            schema_version=version,
            root=str(data.get("root", ".")),
            generated_at=str(data.get("generated_at", "")),
            nodes=nodes,
            edges=edges,
            files={str(k): str(v) for k, v in data.get("files", {}).items()},
            contexts=list(data.get("contexts", [])),
            diagnostics=list(data.get("diagnostics", [])),
            evidence=list(data.get("evidence", [])),
            symbols=list(data.get("symbols", [])),
            call_sites=list(data.get("call_sites", [])),
            cfgs=list(data.get("cfgs", [])),
            analysis_annotations=list(data.get("analysis_annotations", [])),
        )

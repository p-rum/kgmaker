"""Small serializable graph model shared by the scanner and renderers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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


@dataclass
class KnowledgeGraph:
    schema_version: int
    root: str
    generated_at: str
    nodes: list[Node]
    edges: list[Edge]
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root": self.root,
            "generated_at": self.generated_at,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGraph":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            root=str(data.get("root", ".")),
            generated_at=str(data.get("generated_at", "")),
            nodes=[Node(**item) for item in data.get("nodes", [])],
            edges=[Edge(**item) for item in data.get("edges", [])],
            files={str(k): str(v) for k, v in data.get("files", {}).items()},
        )

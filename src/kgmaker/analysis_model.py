"""Versioned feature-analysis contract and shared deterministic primitives.

The candidate is JSON data, never an instruction to mutate the AS_IS graph.
Unknown input metadata is represented by null, not a guessed default.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z")
COLLECTIONS = (
    "requirements", "input_requirements", "capability_matches", "changes", "impact_paths",
    "questions", "assumptions", "alternatives", "acceptance_criteria", "test_plan", "evidence",
)
INPUT_METADATA = (
    "definition", "data_type", "unit", "currency", "granularity", "keys", "as_of",
    "validity_interval", "horizon", "freshness", "nullable", "quality", "fallbacks",
)
PROPOSAL_RELATIONS = {
    "requires_input", "satisfies_requirement", "reuses_entity", "proposes_change_to",
    "blocked_by", "depends_on_decision",
}


class AnalysisError(ValueError):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, value: str) -> Path:
    """Require a relative path contained in root, including existing symlink targets."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise AnalysisError(f"Invalid repository-relative path: {value!r}")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise AnalysisError(f"Path must stay inside the approved root: {value!r}")
    current = root.resolve()
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise AnalysisError(f"Symlink paths are not supported: {value!r}")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise AnalysisError(f"Path escapes the approved root: {value!r}")
    return target


def analysis_dir(root: Path, analysis_id: str) -> Path:
    if not isinstance(analysis_id, str) or not ID_PATTERN.fullmatch(analysis_id):
        raise AnalysisError("analysis ID must contain only letters, digits, hyphens or underscores (1–80 characters)")
    return safe_path(root, f".kgmaker/analyses/{analysis_id}")


def read_regular_bytes(path: Path) -> bytes:
    """Read one open regular file, rejecting replaced symlinks and special files."""
    if not stat.S_ISREG(path.lstat().st_mode):
        raise OSError(f"Not a regular file: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise OSError(f"Not a regular file: {path.name}")
        return stream.read()


def read_json(path: Path, *, regular_only: bool = False) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value: {value}")
    def unique(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        text = read_regular_bytes(path).decode("utf-8") if regular_only else path.read_text(encoding="utf-8")
        return json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise AnalysisError(f"Invalid JSON in {path.name}: {exc}") from exc


def atomic_write(path: Path, text: str, *, before_replace=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".kgmaker-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if before_replace is not None:
            before_replace()
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")


@dataclass(frozen=True)
class FeatureAnalysis:
    """Serializable envelope. Nested contracts are checked by analysis_validation."""
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: Any) -> "FeatureAnalysis":
        if not isinstance(data, dict):
            raise AnalysisError("FeatureAnalysis must be an object")
        if type(data.get("schema_version")) is not int or data["schema_version"] != SCHEMA_VERSION:
            raise AnalysisError(f"Unsupported FeatureAnalysis schema_version; expected {SCHEMA_VERSION}")
        for key in ("analysis_id", "packet_id", "requirement_hash", "language"):
            if not isinstance(data.get(key), str) or not data[key]:
                raise AnalysisError(f"{key} must be a non-empty string")
        if type(data.get("revision")) is not int or data["revision"] < 1:
            raise AnalysisError("revision must be a positive integer")
        for key in ("baseline", "coverage", "proposal", "completion"):
            if not isinstance(data.get(key), dict):
                raise AnalysisError(f"{key} must be an object")
        for key in COLLECTIONS:
            if not isinstance(data.get(key), list) or any(not isinstance(x, dict) for x in data[key]):
                raise AnalysisError(f"{key} must be an array of objects")
        return cls(json.loads(canonical(data)))

    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical(self.data))


def inventory_candidate(packet: dict) -> dict:
    """Explicitly incomplete starting point; the CLI makes no semantic conclusions."""
    prefix = f"analysis:{packet['analysis_id']}:"
    result = {key: [] for key in COLLECTIONS}
    result.update({key: packet[key] for key in (
        "schema_version", "analysis_id", "revision", "packet_id", "requirement_hash", "baseline", "coverage",
    )})
    result.update({
        "language": "cs" if re.search(r"[áčďéěíňóřšťúůýž]", packet["requirement"], re.I) else "en",
        "requirements": [{"id": prefix + "requirement:original", "text": packet["requirement"],
                          "kind": "Goal", "source_quote": packet["requirement"], "status": "UNRESOLVED"}],
        "proposal": {"nodes": [], "edges": []},
        "completion": {"processing_status": "SEMANTIC_PENDING", "decision_readiness": "BLOCKED",
                       "pending": ["Agent must decompose the requirement and verify sources."] + packet["coverage"]["pending"]},
    })
    return result

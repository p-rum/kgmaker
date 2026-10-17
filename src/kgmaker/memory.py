"""Validated, deterministic contracts for Git-provenanced implementation memory."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any

from .model import Edge, KnowledgeGraph, Node

EPISODE_KIND = "implementation_episode"
EPISODE_EDGE_KIND = "affected"
VALIDATION_STATUSES = {"passed", "failed", "skipped", "unknown"}
CHANGE_STATUSES = {"A", "M", "D", "R", "C", "T", "U"}
_HEX_40 = re.compile(r"[0-9a-f]{40}")
_HEX_64 = re.compile(r"[0-9a-f]{64}")
_WORD = re.compile(r"[A-Za-z0-9]+")
_CHARS_PER_TOKEN = 4


class EpisodeValidationError(ValueError):
    """An implementation episode does not satisfy the persisted contract."""


class CaptureError(ValueError):
    """A capture request is unsafe, malformed, or has no recordable changes."""


def _canonical_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in {"id", "freshness"}}


def episode_id(record: dict[str, Any]) -> str:
    """Derive an ID from persisted episode content, independent of key ordering."""
    encoded = json.dumps(
        _canonical_payload(record), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "episode:" + hashlib.sha256(encoded).hexdigest()


def _safe_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EpisodeValidationError(f"{field} must be a non-empty repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value != path.as_posix():
        raise EpisodeValidationError(f"{field} must be a safe repository-relative path")
    return value


def _string_list(value: Any, field: str, limit: int = 2_000) -> list[str]:
    if not isinstance(value, list) or len(value) > limit or any(
        not isinstance(item, str) or not item or len(item) > 500 for item in value
    ):
        raise EpisodeValidationError(f"{field} must be a bounded array of non-empty strings")
    if len(set(value)) != len(value):
        raise EpisodeValidationError(f"{field} must not contain duplicates")
    return value


def validate_episode(record: Any, index: int | None = None) -> dict[str, Any]:
    """Validate episode provenance without applying source-line concept rules."""
    prefix = f"episodes[{index}]" if index is not None else "episode"
    if not isinstance(record, dict):
        raise EpisodeValidationError(f"{prefix} must be an object")
    required = {
        "id", "base_commit", "head_commit", "worktree_fingerprint", "title",
        "changed_files", "affected_node_ids", "graph_delta", "validations",
    }
    if set(record) != required:
        raise EpisodeValidationError(f"{prefix} must contain exactly the episode contract fields")
    if not isinstance(record["base_commit"], str) or not _HEX_40.fullmatch(record["base_commit"]):
        raise EpisodeValidationError(f"{prefix}.base_commit must be a lowercase 40-character Git SHA")
    head = record["head_commit"]
    if head is not None and (not isinstance(head, str) or not _HEX_40.fullmatch(head)):
        raise EpisodeValidationError(f"{prefix}.head_commit must be a lowercase 40-character Git SHA or null")
    if not isinstance(record["worktree_fingerprint"], str) or not _HEX_64.fullmatch(record["worktree_fingerprint"]):
        raise EpisodeValidationError(f"{prefix}.worktree_fingerprint must be a lowercase SHA-256")
    if not isinstance(record["title"], str) or not record["title"].strip() or len(record["title"]) > 200:
        raise EpisodeValidationError(f"{prefix}.title must be non-empty text no longer than 200 characters")

    changed = record["changed_files"]
    if not isinstance(changed, list) or not changed or len(changed) > 2_000:
        raise EpisodeValidationError(f"{prefix}.changed_files must be a bounded non-empty array")
    seen_paths: set[str] = set()
    for offset, item in enumerate(changed):
        field = f"{prefix}.changed_files[{offset}]"
        if not isinstance(item, dict) or set(item) != {"path", "status", "sha256"}:
            raise EpisodeValidationError(f"{field} must contain path, status, and sha256")
        path = _safe_path(item["path"], f"{field}.path")
        if path in seen_paths:
            raise EpisodeValidationError(f"{prefix}.changed_files paths must be unique")
        seen_paths.add(path)
        if item["status"] not in CHANGE_STATUSES:
            raise EpisodeValidationError(f"{field}.status is unsupported")
        digest = item["sha256"]
        if item["status"] == "D":
            if digest is not None:
                raise EpisodeValidationError(f"{field}.sha256 must be null for a deleted file")
        elif not isinstance(digest, str) or not _HEX_64.fullmatch(digest):
            raise EpisodeValidationError(f"{field}.sha256 must be a lowercase SHA-256")

    _string_list(record["affected_node_ids"], f"{prefix}.affected_node_ids")
    delta = record["graph_delta"]
    if not isinstance(delta, dict) or set(delta) != {"added", "removed", "changed"}:
        raise EpisodeValidationError(f"{prefix}.graph_delta must contain added, removed, and changed arrays")
    for name in ("added", "removed", "changed"):
        _string_list(delta[name], f"{prefix}.graph_delta.{name}")
    validations = record["validations"]
    if not isinstance(validations, list) or len(validations) > 100:
        raise EpisodeValidationError(f"{prefix}.validations must be a bounded array")
    labels: set[str] = set()
    for offset, item in enumerate(validations):
        field = f"{prefix}.validations[{offset}]"
        if not isinstance(item, dict) or set(item) != {"label", "status"}:
            raise EpisodeValidationError(f"{field} must contain label and status")
        label = item["label"]
        if not isinstance(label, str) or not label or len(label) > 80 or label in labels:
            raise EpisodeValidationError(f"{field}.label must be unique bounded text")
        labels.add(label)
        if item["status"] not in VALIDATION_STATUSES:
            raise EpisodeValidationError(f"{field}.status is unsupported")
    expected = episode_id(record)
    if record["id"] != expected:
        raise EpisodeValidationError(f"{prefix}.id must be `{expected}`")
    return record


def episode_freshness(record: dict[str, Any], current_files: dict[str, str]) -> str:
    """Classify recorded file evidence against current indexed file hashes."""
    removed = False
    changed = False
    for item in record["changed_files"]:
        current = current_files.get(item["path"])
        if item["status"] == "D":
            changed |= current is not None
        elif current is None:
            removed = True
        elif current != item["sha256"]:
            changed = True
    return "removed" if removed else "changed" if changed else "current"


def project_episode(record: dict[str, Any], current_nodes: set[str], current_files: dict[str, str]) -> tuple[Node, list[Edge]]:
    """Project one valid episode and only its live affected-node relationships."""
    metadata = {key: value for key, value in record.items() if key != "title"}
    metadata["freshness"] = episode_freshness(record, current_files)
    first_path = record["changed_files"][0]["path"]
    node = Node(record["id"], EPISODE_KIND, record["title"], first_path, metadata=metadata)
    edges = [
        Edge(record["id"], node_id, EPISODE_EDGE_KIND, confidence="EXTRACTED")
        for node_id in record["affected_node_ids"] if node_id in current_nodes
    ]
    return node, edges


def _terms(text: str) -> list[str]:
    return [word.casefold() for word in _WORD.findall(text)]


def _text_score(query: list[str], exact_query: str, fields: list[str]) -> int:
    texts = [field.casefold() for field in fields if field]
    combined = " ".join(texts)
    score = 12 if exact_query and exact_query in combined else 0
    for term in query:
        score += max((8 if term == text else 4 if term in _terms(text) else 2 if term in text else 0)
                     for text in texts) if texts else 0
    return score


def recall(graph: KnowledgeGraph, query: str, limit: int = 8, token_budget: int = 1_000,
           baseline: str = "") -> str:
    """Render deterministic, budgeted episode and current-location recall."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    if isinstance(token_budget, bool) or not isinstance(token_budget, int) or token_budget < 64:
        raise ValueError("token budget must be an integer of at least 64")
    words = _terms(query)
    if not words:
        raise ValueError("recall query must contain a word or number")
    exact = " ".join(words)
    nodes = {node.id: node for node in graph.nodes}
    neighbors: dict[str, set[str]] = {}
    for edge in graph.edges:
        neighbors.setdefault(edge.source, set()).add(edge.target)
        neighbors.setdefault(edge.target, set()).add(edge.source)

    ranked: list[tuple[int, int, str, str]] = []
    episode_scores: dict[str, int] = {}
    for node in graph.nodes:
        if node.kind != EPISODE_KIND:
            continue
        metadata = node.metadata or {}
        changed = metadata.get("changed_files", [])
        affected = [nodes[item] for item in metadata.get("affected_node_ids", []) if item in nodes]
        nearby = [nodes[item] for item in neighbors.get(node.id, set()) if item in nodes]
        fields = [node.name, *[item.get("path", "") for item in changed if isinstance(item, dict)]]
        fields.extend(value for item in affected + nearby for value in (item.name, item.path, item.summary or ""))
        score = _text_score(words, exact, fields)
        freshness = str(metadata.get("freshness", "changed"))
        if freshness == "current":
            score += 3
        else:
            score = max(1, score - 3) if score else 0
        if not score:
            continue
        episode_scores[node.id] = score
        label = "current" if freshness == "current" else f"HISTORICAL—{freshness}"
        paths = ", ".join(item.get("path", "") for item in changed[:3] if isinstance(item, dict))
        validations = ", ".join(f"{item.get('label')}={item.get('status')}"
                                for item in metadata.get("validations", [])[:3] if isinstance(item, dict)) or "none"
        head = metadata.get("head_commit") or metadata.get("base_commit") or ""
        line = f"- **Episode [{label}]** {node.name} — {paths}; validation: {validations}; git: {str(head)[:12]}"
        ranked.append((score, 0, node.id, line))

    for node in graph.nodes:
        if node.kind == EPISODE_KIND:
            continue
        fields = [node.name, node.path, node.signature or "", node.summary or ""]
        fields.extend(value for item_id in neighbors.get(node.id, set())
                      if (item := nodes.get(item_id)) is not None and item.kind != EPISODE_KIND
                      for value in (item.name, item.path, item.summary or ""))
        score = _text_score(words, exact, fields)
        if not score:
            continue
        location = f"{node.path}:{node.line}" if node.line else node.path
        signature = f" — `{node.signature}`" if node.signature else ""
        ranked.append((score, 1, node.id, f"- **Current [{node.kind}]** `{location}` — {node.name}{signature}"))

    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    selected = ranked[:limit]
    broad_tokens = (len(baseline) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN
    max_chars = token_budget * _CHARS_PER_TOKEN
    while True:
        body = ["## kgmaker implementation recall", f"Request: {query}", ""]
        body.extend(item[3] for item in selected)
        if not selected:
            body.append("- No relevant implementation memory or current graph location found.")
        provisional = "\n".join(body)
        estimated = 0
        while True:
            reduction = max(0, broad_tokens - estimated)
            percent = round(100 * reduction / broad_tokens) if broad_tokens else 0
            result = provisional + f"\n\nEstimated tokens: {estimated}; broad context: {broad_tokens}; reduction vs broad context: {reduction} ({percent}%)."
            actual = (len(result) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN
            if actual == estimated:
                break
            estimated = actual
        if len(result) <= max_chars or not selected:
            return result[:max_chars]
        selected.pop()


def parse_validations(values: list[str]) -> list[dict[str, str]]:
    """Parse bounded LABEL=STATUS command-line values."""
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or "=" not in value:
            raise CaptureError("validation must use LABEL=STATUS")
        label, status = value.split("=", 1)
        if (not label or len(label) > 80 or label != label.strip() or label in seen
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]*", label)):
            raise CaptureError("validation label must be unique bounded text")
        if status not in VALIDATION_STATUSES:
            raise CaptureError("validation status must be passed, failed, skipped, or unknown")
        seen.add(label)
        result.append({"label": label, "status": status})
    if len(result) > 100:
        raise CaptureError("no more than 100 validations may be recorded")
    return result


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise CaptureError(detail or f"Git command failed: {' '.join(args)}")
    return result.stdout


def is_sensitive_path(path: str) -> bool:
    """Return True when a repository-relative path must not store file contents."""
    parts = PurePosixPath(path).parts
    name = parts[-1].casefold() if parts else ""
    sensitive_names = {
        ".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials",
        "secrets.yaml", "secrets.yml", "secret.json", "service-account.json",
    }
    return (any(part.casefold() in {".git", ".kgmaker"} for part in parts)
            or name in sensitive_names
            or any(token in name for token in (".pem", ".key", "secret", "credential")))


def _sensitive_path(path: str) -> bool:
    return is_sensitive_path(path)


def _changed_paths(root: Path, base_commit: str) -> list[tuple[str, str]]:
    output = _git(root, "diff", "--name-status", "-z", "--find-renames", base_commit, "--")
    fields = output.decode("utf-8", errors="surrogateescape").split("\0")
    changes: dict[str, str] = {}
    index = 0
    while index < len(fields) and fields[index]:
        status_field = fields[index]
        index += 1
        status = status_field[0]
        if status not in CHANGE_STATUSES:
            raise CaptureError(f"unsupported Git change status: {status_field}")
        if status in {"R", "C"}:
            if index + 1 >= len(fields):
                raise CaptureError("malformed Git rename record")
            index += 1  # The old path is provenance supplied by Git, not current evidence.
        if index >= len(fields):
            raise CaptureError("malformed Git change record")
        path = fields[index]
        index += 1
        _safe_path(path, "changed file")
        changes[path] = status

    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    for path in untracked.decode("utf-8", errors="surrogateescape").split("\0"):
        if path:
            _safe_path(path, "untracked file")
            changes.setdefault(path, "A")
    return sorted(changes.items())


def _file_hash(root: Path, path: str) -> str:
    candidate = root / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve())
        if not resolved.is_file():
            raise OSError("not a regular file")
        return hashlib.sha256(resolved.read_bytes()).hexdigest()
    except (OSError, ValueError) as error:
        raise CaptureError(f"cannot hash changed file safely: {path}: {error}") from None


def _node_payload(node: Node) -> tuple[Any, ...]:
    return node.kind, node.name, node.path, node.line, node.signature, node.summary


def build_capture_episode(
    root: Path,
    base_ref: str,
    previous_graph: KnowledgeGraph,
    current_graph: KnowledgeGraph,
    validations: list[dict[str, str]],
) -> dict[str, Any]:
    """Build one deterministic episode without persisting source or diff content."""
    if not base_ref or len(base_ref) > 500:
        raise CaptureError("base ref must be non-empty bounded text")
    base_commit = _git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}").decode().strip()
    head_commit = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    raw_changes = _changed_paths(root, base_commit)
    changed_files = []
    for path, status in raw_changes:
        if _sensitive_path(path):
            continue
        digest = None if status == "D" else _file_hash(root, path)
        changed_files.append({"path": path, "status": status, "sha256": digest})
    if not changed_files:
        raise CaptureError("no non-sensitive changes to capture")

    old_nodes = {node.id: node for node in previous_graph.nodes if node.kind != EPISODE_KIND}
    new_nodes = {node.id: node for node in current_graph.nodes if node.kind != EPISODE_KIND}
    added = sorted(set(new_nodes) - set(old_nodes))
    removed = sorted(set(old_nodes) - set(new_nodes))
    changed = sorted(node_id for node_id in set(old_nodes) & set(new_nodes)
                     if _node_payload(old_nodes[node_id]) != _node_payload(new_nodes[node_id]))
    changed_paths = {item["path"] for item in changed_files}
    affected = sorted(set(added) | set(removed) | set(changed) | {
        node.id for node in [*old_nodes.values(), *new_nodes.values()] if node.path in changed_paths
    })
    if any(len(items) > 2_000 for items in (added, removed, changed, affected)):
        raise CaptureError("graph change exceeds the safe episode size limit")

    fingerprint_payload = {
        "base_commit": base_commit, "head_commit": head_commit, "changed_files": changed_files,
        "graph_delta": {"added": added, "removed": removed, "changed": changed},
    }
    fingerprint = hashlib.sha256(json.dumps(
        fingerprint_payload, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    subject = _git(root, "show", "-s", "--format=%s", head_commit).decode("utf-8", errors="replace").strip()
    if head_commit == base_commit:
        names = sorted({new_nodes[node_id].name for node_id in affected if node_id in new_nodes
                        and new_nodes[node_id].kind != "file"})
        subject = "Change " + ", ".join(names[:3]) if names else "Change " + ", ".join(
            item["path"] for item in changed_files[:3]
        )
    title = subject[:200].strip() or "Repository implementation change"
    record = {
        "base_commit": base_commit,
        "head_commit": head_commit,
        "worktree_fingerprint": fingerprint,
        "title": title,
        "changed_files": changed_files,
        "affected_node_ids": affected,
        "graph_delta": {"added": added, "removed": removed, "changed": changed},
        "validations": validations,
    }
    record["id"] = episode_id(record)
    return validate_episode(record)
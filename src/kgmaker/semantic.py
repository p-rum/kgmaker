"""Validation and merging for the optional agent-authored semantic graph layer."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from .model import Edge, KnowledgeGraph, Node

SEMANTIC_FILE = Path(".kgmaker/semantic.json")
SEMANTIC_INPUT_FILE = Path(".kgmaker/semantic-input.json")
SEMANTIC_UPDATE_FILE = Path(".kgmaker/semantic-update.json")
SEMANTIC_UPDATE_MARKDOWN = Path(".kgmaker/semantic-update.md")
SEMANTIC_EXTRACT_MARKDOWN = Path(".kgmaker/semantic-extract.md")
SEMANTIC_PATCH_FILE = Path(".kgmaker/semantic-patch.json")
LEGACY_SEMANTIC_SCHEMA_VERSION = 2
SEMANTIC_SCHEMA_VERSION = 3
SEMANTIC_UPDATE_SCHEMA_VERSION = 1
DEFAULT_SEMANTIC_TOKEN_BUDGET = 4_000
CHARS_PER_TOKEN_ESTIMATE = 4
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
        "contexts": graph.contexts,
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
        "analysis_contexts": graph.contexts,
        "files": dict(sorted(graph.files.items())),
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
    if (not isinstance(data, dict) or isinstance(data.get("schema_version"), bool)
            or data.get("schema_version") not in {1, LEGACY_SEMANTIC_SCHEMA_VERSION, SEMANTIC_SCHEMA_VERSION}):
        raise SemanticValidationError(
            f"semantic artifact must use schema_version 1, {LEGACY_SEMANTIC_SCHEMA_VERSION}, "
            f"or {SEMANTIC_SCHEMA_VERSION}"
        )
    version = data["schema_version"]
    if version == 1 and data.get("graph_fingerprint") != graph_fingerprint(graph):
        raise SemanticValidationError("legacy semantic artifact is stale; run `kgmaker semantic prepare` to upgrade it")
    snapshots = data.get("files")
    if version in {LEGACY_SEMANTIC_SCHEMA_VERSION, SEMANTIC_SCHEMA_VERSION}:
        if not isinstance(snapshots, dict) or any(
            not isinstance(path, str) or not isinstance(digest, str)
            for path, digest in snapshots.items()
        ):
            raise SemanticValidationError("semantic artifact must contain a `files` map of path to SHA-256")
    if not isinstance(data.get("nodes"), list) or not isinstance(data.get("edges"), list):
        raise SemanticValidationError("semantic artifact must contain `nodes` and `edges` arrays")
    if version == SEMANTIC_SCHEMA_VERSION and not isinstance(data.get("episodes"), list):
        raise SemanticValidationError("semantic schema_version 3 artifact must contain an `episodes` array")

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
        if version in {LEGACY_SEMANTIC_SCHEMA_VERSION, SEMANTIC_SCHEMA_VERSION} \
                and snapshots.get(source_file) != graph.files[source_file]:
            raise SemanticValidationError(f"nodes[{index}] is stale because {source_file} changed; run `kgmaker semantic update`")
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
        if version in {LEGACY_SEMANTIC_SCHEMA_VERSION, SEMANTIC_SCHEMA_VERSION} \
                and snapshots.get(source_file) != graph.files[source_file]:
            raise SemanticValidationError(f"edges[{index}] is stale because {source_file} changed; run `kgmaker semantic update`")
        source_line = _positive_line(item.get("source_line"), f"edges[{index}].source_line")
        if source_line is None:
            raise SemanticValidationError(f"edges[{index}].source_line is required for evidence provenance")
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
    if version == SEMANTIC_SCHEMA_VERSION:
        from .memory import EpisodeValidationError, project_episode, validate_episode

        current_ids = valid_ids.copy()
        episode_ids: set[str] = set()
        for index, item in enumerate(data["episodes"]):
            try:
                episode = validate_episode(item, index)
            except EpisodeValidationError as error:
                raise SemanticValidationError(str(error)) from None
            if episode["id"] in current_ids or episode["id"] in episode_ids:
                raise SemanticValidationError(f"episodes[{index}].id duplicates an existing node")
            episode_ids.add(episode["id"])
            node, edges = project_episode(episode, current_ids, graph.files)
            semantic_nodes.append(node)
            semantic_edges.extend(edges)
    return semantic_nodes, semantic_edges


def _run_git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode:
        message = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise SemanticValidationError(message)
    return result.stdout


def _is_sensitive_path(path: str) -> bool:
    parts = [part.casefold() for part in Path(path).parts]
    names = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials", "secrets.yaml", "secrets.yml", "secret.json", "service-account.json"}
    return any(part in names or "secret" in part or "credential" in part for part in parts)


def build_semantic_update(
    graph: KnowledgeGraph,
    root: Path,
    base_ref: str = "HEAD~1",
    note_path: str | None = None,
    previous_graph: KnowledgeGraph | None = None,
    max_diff_chars: int = 16_000,
    token_budget: int | None = None,
) -> dict[str, Any]:
    """Build a token-bounded change packet from Git diff and the relevant graph neighborhood."""
    if token_budget is not None and (isinstance(token_budget, bool) or not isinstance(token_budget, int) or token_budget < 1):
        raise SemanticValidationError("token budget must be a positive integer")
    if isinstance(max_diff_chars, bool) or not isinstance(max_diff_chars, int) or max_diff_chars < 1:
        raise SemanticValidationError("max diff chars must be a positive integer")
    effective_token_budget = token_budget or min(
        DEFAULT_SEMANTIC_TOKEN_BUDGET, max(1, max_diff_chars // CHARS_PER_TOKEN_ESTIMATE)
    )
    diff_budget = min(max_diff_chars, effective_token_budget * CHARS_PER_TOKEN_ESTIMATE)
    root = root.resolve()
    repo_root = Path(_run_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
    if repo_root != root:
        raise SemanticValidationError(f"run this command from the repository root ({repo_root})")
    resolved_base = _run_git(root, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}").strip()
    status_fields = _run_git(root, "diff", "--name-status", "--no-renames", "-z", resolved_base, "--").split("\0")
    changed: dict[str, str] = {}
    cursor = 0
    while cursor + 1 < len(status_fields):
        status, path = status_fields[cursor], status_fields[cursor + 1]
        cursor += 2
        if path:
            changed[path] = status
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    for path in untracked:
        if path:
            changed.setdefault(path, "A")
    eligible_paths = set(graph.files)
    if previous_graph:
        eligible_paths.update(previous_graph.files)
    changed = {path: status for path, status in changed.items() if path in eligible_paths}

    changed_files: list[dict[str, Any]] = []
    budget = diff_budget
    for path, status in sorted(changed.items()):
        if _is_sensitive_path(path):
            changed_files.append({"path": path, "status": status, "sensitive": True, "diff": ""})
            continue
        file_path = root / path
        exists = file_path.is_file()
        current_hash = graph.files.get(path)
        if exists and current_hash is None:
            current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        base_blob = _run_git(root, "rev-parse", "--verify", f"{resolved_base}:{path}", check=False).strip() or None
        if status == "A" and path in untracked:
            try:
                source = file_path.read_text(encoding="utf-8")
                diff_text = "".join(f"+{line}\n" for line in source.splitlines())
                diff_text = f"--- /dev/null\n+++ b/{path}\n@@ new file @@\n" + diff_text
            except (OSError, UnicodeError):
                diff_text = "[new file is not readable UTF-8 text]"
        else:
            diff_text = _run_git(root, "diff", "--no-ext-diff", "--no-color", "--unified=3", resolved_base, "--", path, check=False)
        truncated = len(diff_text) > budget
        if truncated:
            marker = "\n[diff truncated]\n"
            diff_text = diff_text[:max(0, budget - len(marker))] + marker
        budget = max(0, budget - len(diff_text))
        changed_files.append({
            "path": path,
            "status": status,
            "base_blob": base_blob,
            "current_sha256": current_hash,
            "indexed": path in graph.files,
            "sensitive": False,
            "diff_truncated": truncated,
            "diff": diff_text,
        })

    changed_paths = {item["path"] for item in changed_files}
    old_graph = previous_graph
    old_nodes = {node.id: node for node in old_graph.nodes} if old_graph else {}
    current_nodes = {node.id: node for node in graph.nodes}
    changed_node_ids = {
        node.id for node in [*graph.nodes, *(old_graph.nodes if old_graph else [])]
        if node.path in changed_paths
    }
    neighbors: set[str] = set(changed_node_ids)
    for edge in graph.edges:
        if edge.source in changed_node_ids or edge.target in changed_node_ids:
            neighbors.update((edge.source, edge.target))
    if old_graph:
        for edge in old_graph.edges:
            if edge.source in changed_node_ids or edge.target in changed_node_ids:
                neighbors.update((edge.source, edge.target))

    context_nodes = []
    for node_id in sorted(neighbors):
        node = current_nodes.get(node_id) or old_nodes.get(node_id)
        if node:
            context_nodes.append({
                "id": node.id, "kind": node.kind, "name": node.name, "path": node.path,
                "line": node.line, "signature": node.signature, "summary": node.summary,
                "present_now": node.id in current_nodes,
            })
    artifact_path = root / SEMANTIC_FILE
    if artifact_path.exists():
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SemanticValidationError(f"existing semantic artifact cannot be read: {error}") from None
        if not isinstance(artifact, dict) or not isinstance(artifact.get("nodes"), list) or not isinstance(artifact.get("edges"), list):
            raise SemanticValidationError("existing semantic artifact is malformed; repair it before preparing an update")
    else:
        artifact = {"nodes": [], "edges": []}
    old_semantic_nodes = artifact.get("nodes", []) if isinstance(artifact, dict) else []
    old_semantic_edges = artifact.get("edges", []) if isinstance(artifact, dict) else []
    legacy_artifact = isinstance(artifact, dict) and artifact.get("schema_version") == 1
    affected_semantic_nodes = [
        item for item in old_semantic_nodes if isinstance(item, dict)
        and (legacy_artifact or item.get("source_file") in changed_paths or item.get("id") in changed_node_ids)
    ]
    affected_semantic_ids = {item.get("id") for item in affected_semantic_nodes}
    all_semantic_ids = {
        item.get("id") for item in old_semantic_nodes if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    affected_semantic_edges = [
        item for item in old_semantic_edges if isinstance(item, dict)
        and (legacy_artifact or item.get("source_file") in changed_paths
             or item.get("source") in changed_node_ids or item.get("target") in changed_node_ids
             or item.get("source") in affected_semantic_ids or item.get("target") in affected_semantic_ids
             or item.get("source") not in current_nodes and item.get("source") not in all_semantic_ids
             or item.get("target") not in current_nodes and item.get("target") not in all_semantic_ids)
    ]
    note = ""
    if note_path:
        try:
            note_file = (root / note_path).resolve()
            note_file.relative_to(root)
            note = note_file.read_text(encoding="utf-8")[:4_000]
        except (OSError, UnicodeError) as error:
            raise SemanticValidationError(f"cannot read change note {note_path}: {error}") from None
        except ValueError:
            raise SemanticValidationError("change note must be inside the repository") from None
    all_context_edges = [
        {"source": edge.source, "target": edge.target, "kind": edge.kind, "evidence": edge.evidence}
        for edge in graph.edges
        if edge.source in neighbors or edge.target in neighbors
    ]
    context_nodes_truncated = len(context_nodes) > 300
    context_edges_truncated = len(all_context_edges) > 600
    context_nodes = context_nodes[:300]
    context_edges = all_context_edges[:600]
    evidence_paths = set(changed_paths)
    evidence_paths.update(
        item.get("source_file") for item in [*affected_semantic_nodes, *affected_semantic_edges]
        if isinstance(item.get("source_file"), str)
    )
    evidence_paths.update(
        item.get("source_file") for item in [*old_semantic_nodes, *old_semantic_edges]
        if isinstance(item, dict) and isinstance(item.get("source_file"), str)
    )
    for item in old_semantic_edges:
        if not isinstance(item, dict):
            continue
        for endpoint in (item.get("source"), item.get("target")):
            node = current_nodes.get(endpoint) or old_nodes.get(endpoint)
            if node:
                evidence_paths.add(node.path)
    core = {
        "schema_version": SEMANTIC_UPDATE_SCHEMA_VERSION,
        "analysis_contexts": graph.contexts,
        "base_ref": base_ref,
        "base_commit": resolved_base,
        "file_hashes": {path: graph.files.get(path) for path in sorted(evidence_paths)},
        "changed_files": changed_files,
        "context_nodes": context_nodes,
        "context_edges": context_edges,
        "relations": sorted(SEMANTIC_RELATIONS),
        "context_nodes_truncated": context_nodes_truncated,
        "context_edges_truncated": context_edges_truncated,
        "affected_semantic_nodes": affected_semantic_nodes,
        "affected_semantic_edges": affected_semantic_edges,
        "change_note": note,
        "legacy_artifact": legacy_artifact,
        "token_budget": effective_token_budget,
        "estimated_diff_tokens": sum(len(item.get("diff", "")) for item in changed_files) // CHARS_PER_TOKEN_ESTIMATE,
    }
    core["update_id"] = hashlib.sha256(
        json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return core


def apply_semantic_patch(patch: Any, update: Any, graph: KnowledgeGraph, root: Path) -> dict[str, Any]:
    """Apply a scoped agent patch while preserving semantic facts outside the change impact."""
    if (not isinstance(update, dict) or isinstance(update.get("schema_version"), bool)
            or update.get("schema_version") != SEMANTIC_UPDATE_SCHEMA_VERSION):
        raise SemanticValidationError("semantic update packet is missing or unsupported; run `kgmaker semantic update`")
    if (not isinstance(patch, dict) or isinstance(patch.get("schema_version"), bool)
            or patch.get("schema_version") != 1):
        raise SemanticValidationError("semantic patch must use schema_version 1")
    if patch.get("update_id") != update.get("update_id"):
        patch_id = patch.get("update_id") if isinstance(patch.get("update_id"), str) else "<missing>"
        update_id = update.get("update_id") if isinstance(update.get("update_id"), str) else "<missing>"
        raise SemanticValidationError(
            "semantic patch belongs to a different change packet "
            f"(patch={patch_id[:12]}, packet={update_id[:12]}); "
            "delete `.kgmaker/semantic-patch.json`, run `kgmaker semantic update` once, "
            "then recreate the patch using the new packet's exact update_id"
        )
    integrity_payload = {key: value for key, value in update.items() if key != "update_id"}
    integrity_id = hashlib.sha256(
        json.dumps(integrity_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if integrity_id != update.get("update_id"):
        raise SemanticValidationError("semantic update packet was modified after preparation; regenerate it")
    if graph.schema_version == 2 and update.get("analysis_contexts") != graph.contexts:
        raise SemanticValidationError("analysis context changed or is missing; regenerate the semantic update packet")
    if (not isinstance(update.get("changed_files"), list) or not isinstance(update.get("context_nodes"), list)
            or not isinstance(update.get("affected_semantic_nodes"), list)
            or not isinstance(update.get("affected_semantic_edges"), list)):
        raise SemanticValidationError("semantic update packet is malformed")
    if any(not isinstance(item, dict) or not isinstance(item.get("path"), str)
           for item in update["changed_files"]) or any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str)
        for item in update["context_nodes"]
    ):
        raise SemanticValidationError("semantic update paths and context node IDs must be valid")
    if any(not isinstance(item, dict) for item in [*update["affected_semantic_nodes"], *update["affected_semantic_edges"]]):
        raise SemanticValidationError("affected semantic entries in the update packet are malformed")
    expected_hashes = update.get("file_hashes")
    if (not isinstance(expected_hashes, dict)
            or any(not isinstance(path, str) or (digest is not None and not isinstance(digest, str))
                   for path, digest in expected_hashes.items())
            or any(graph.files.get(path) != digest for path, digest in expected_hashes.items())):
        raise SemanticValidationError("source files changed after the update packet was prepared; regenerate it before applying the patch")
    changed_paths = {item["path"] for item in update.get("changed_files", []) if isinstance(item, dict)}
    changed_ids = {
        item["id"] for item in update.get("context_nodes", [])
        if isinstance(item, dict) and item.get("path") in changed_paths
    }
    prior_nodes = update.get("affected_semantic_nodes", [])
    prior_edges = update.get("affected_semantic_edges", [])
    allowed_remove_nodes = {item.get("id") for item in prior_nodes if isinstance(item, dict)}
    allowed_remove_edges = {
        (item.get("source"), item.get("target"), item.get("kind"))
        for item in prior_edges if isinstance(item, dict)
    }
    remove_nodes = patch.get("remove_nodes", [])
    remove_edges = patch.get("remove_edges", [])
    if not isinstance(remove_nodes, list) or any(not isinstance(item, str) or item not in allowed_remove_nodes for item in remove_nodes):
        raise SemanticValidationError("remove_nodes may only contain affected concept IDs from the update packet")
    if not isinstance(remove_edges, list) or any(
        not isinstance(item, dict)
        or not all(isinstance(item.get(field), str) for field in ("source", "target", "kind"))
        or (item.get("source"), item.get("target"), item.get("kind")) not in allowed_remove_edges
        for item in remove_edges
    ):
        raise SemanticValidationError("remove_edges may only contain affected relationships from the update packet")

    old_path = root / SEMANTIC_FILE
    if old_path.exists():
        try:
            old = json.loads(old_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SemanticValidationError(f"existing semantic artifact cannot be read: {error}") from None
    else:
        old = {"nodes": [], "edges": []}
    if not isinstance(old, dict) or not isinstance(old.get("nodes", []), list) or not isinstance(old.get("edges", []), list):
        raise SemanticValidationError("existing semantic artifact is malformed; repair it before applying an update")
    if old.get("schema_version") == 1 and old.get("graph_fingerprint") != graph_fingerprint(graph):
        if not update.get("legacy_artifact"):
            raise SemanticValidationError("legacy artifact has no per-file baseline; rerun full `kgmaker semantic prepare` and extraction before incremental updates")
        # Schema v1 cannot prove which source files remained unchanged. The update
        # packet therefore asked the agent to re-validate every old semantic entry.
        old = {"nodes": [], "edges": []}

    explicitly_removed_nodes = set(remove_nodes)
    replaced_node_ids = allowed_remove_nodes | explicitly_removed_nodes
    nodes = [item for item in old.get("nodes", []) if isinstance(item, dict)
             and item.get("source_file") not in changed_paths and item.get("id") not in replaced_node_ids]
    explicit_edge_keys = {
        (item["source"], item["target"], item["kind"]) for item in remove_edges
    }
    replace_edge_keys = allowed_remove_edges | explicit_edge_keys
    edges = [item for item in old.get("edges", []) if isinstance(item, dict)
             and item.get("source_file") not in changed_paths
             and item.get("source") not in changed_ids and item.get("target") not in changed_ids
             and item.get("source") not in replaced_node_ids and item.get("target") not in replaced_node_ids
             and (item.get("source"), item.get("target"), item.get("kind")) not in replace_edge_keys]
    new_nodes, new_edges = patch.get("nodes"), patch.get("edges")
    if not isinstance(new_nodes, list) or not isinstance(new_edges, list):
        raise SemanticValidationError("semantic patch must contain `nodes` and `edges` arrays")
    changed_indexed_paths = {item["path"] for item in update.get("changed_files", [])
                             if isinstance(item, dict) and item.get("indexed") and not item.get("sensitive")}
    allowed_evidence = changed_indexed_paths | {
        item.get("source_file") for item in [*prior_nodes, *prior_edges]
        if isinstance(item, dict) and isinstance(item.get("source_file"), str)
    }
    for kind, entries in (("nodes", new_nodes), ("edges", new_edges)):
        for index, item in enumerate(entries):
            if not isinstance(item, dict) or item.get("source_file") not in allowed_evidence:
                raise SemanticValidationError(f"patch {kind}[{index}] must cite a changed or previously affected file")

    candidate = {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "files": dict(graph.files),
        "nodes": [*nodes, *new_nodes],
        "edges": [*edges, *new_edges],
        "episodes": list(old.get("episodes", [])),
    }
    validate_semantic_data(candidate, graph, root)
    return candidate


def apply_semantic_layer(graph: KnowledgeGraph, root: Path, *,
                         artifact: dict[str, Any] | None = None) -> tuple[KnowledgeGraph, tuple[int, int], str | None]:
    """Project a supplied or persisted artifact and report stale or invalid entries."""
    path = root / SEMANTIC_FILE
    if artifact is None and not path.exists():
        return graph, (0, 0), None
    error: str | None = None
    try:
        data = artifact if artifact is not None else json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema_version") in {LEGACY_SEMANTIC_SCHEMA_VERSION, SEMANTIC_SCHEMA_VERSION} \
                and isinstance(data.get("files"), dict) and isinstance(data.get("nodes"), list) \
                and isinstance(data.get("edges"), list):
            if any(not isinstance(item, dict) for item in [*data["nodes"], *data["edges"]]):
                raise SemanticValidationError("semantic nodes and edges must be objects")
            snapshots = data.get("files", {})
            stale_sources = {
                item.get("source_file") for item in [*data.get("nodes", []), *data.get("edges", [])]
                if isinstance(item, dict) and isinstance(item.get("source_file"), str)
                and snapshots.get(item.get("source_file")) != graph.files.get(item.get("source_file"))
            }
            fresh_nodes = [item for item in data.get("nodes", [])
                           if not isinstance(item.get("source_file"), str)
                           or item.get("source_file") not in stale_sources]
            fresh_node_ids = {item.get("id") for item in fresh_nodes}
            structural_ids = {node.id for node in graph.nodes}
            structural_keys = {(edge.source, edge.target, edge.kind) for edge in graph.edges}
            valid_ids = structural_ids | fresh_node_ids
            fresh_edges = []
            for item in data.get("edges", []):
                source_file = item.get("source_file")
                if isinstance(source_file, str) and source_file in stale_sources:
                    continue
                source, target, kind = item.get("source"), item.get("target"), item.get("kind")
                if not all(isinstance(value, str) for value in (source, target, kind)):
                    fresh_edges.append(item)  # Let the strict validator report malformed fields.
                    continue
                if source in valid_ids and target in valid_ids and (source, target, kind) not in structural_keys:
                    fresh_edges.append(item)
            filtered = {**data, "nodes": fresh_nodes, "edges": fresh_edges}
            nodes, edges = validate_semantic_data(filtered, graph, root)
            if stale_sources:
                error = "stale semantic evidence in: " + ", ".join(sorted(stale_sources)) + "; run `kgmaker semantic update`"
            dropped = len(data.get("edges", [])) - len(fresh_edges)
            if dropped:
                detail = f"{dropped} semantic relationship(s) reference removed or stale nodes"
                error = f"{error}; {detail}" if error else detail
        else:
            nodes, edges = validate_semantic_data(data, graph, root)
    except (OSError, UnicodeError, json.JSONDecodeError, SemanticValidationError) as error:
        return graph, (0, 0), str(error)
    merged = replace(
        graph,
        nodes=sorted([*graph.nodes, *nodes], key=lambda n: (n.path, n.line or 0, n.kind, n.name)),
        edges=sorted([*graph.edges, *edges], key=lambda e: (e.source, e.kind, e.target, e.evidence or "")),
    )
    return merged, (len(nodes), len(edges)), error

"""Offline analysis packet lifecycle. No model calls and no semantic-patch coupling."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from .analysis_model import (
    AnalysisError, SCHEMA_VERSION, analysis_dir, atomic_write, canonical, digest,
    file_hash, inventory_candidate, read_json, safe_path, write_json,
)
from .scanner import EXTENSIONS, MAX_FILE_BYTES, SKIP_DIRS, SENSITIVE_NAMES, scan_repository
from .semantic import apply_semantic_layer
from .dataflow import CAPABILITIES, extract_dataflow

PARSER_VERSION = "feature-inventory-2"
GENERATED_PREFIX = "docs/generated/features/"
REPORT_MARKER = "<!-- kgmaker-feature-report:v1 -->"


def source_inventory(root: Path) -> tuple[dict, list]:
    """Full file manifest, including unsupported artifacts and concrete exclusions."""
    sources, excluded = {}, []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".") and not d.endswith(".egg-info"))
        for name in sorted(names):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if name.startswith(".") or name.lower() in SENSITIVE_NAMES or any(t in name.lower() for t in (".pem", ".key", "secret", "credential")):
                excluded.append({"path": relative, "reason": "sensitive or hidden filename"})
                continue
            if "/" + GENERATED_PREFIX in "/" + relative:
                continue
            if path.is_symlink():
                excluded.append({"path": relative, "reason": "symlink is not a supported source"})
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                excluded.append({"path": relative, "reason": "file exceeds source size limit"})
                continue
            raw = path.read_bytes()
            if raw.startswith(REPORT_MARKER.encode()):
                continue
            suffix = path.suffix.lower()
            kind = "CODE" if suffix in {".py", ".java", ".kt", ".kts", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"} else (
                "SCHEMA" if suffix == ".sql" else "CONTRACT" if suffix == ".json" else
                "CONFIG" if suffix in {".yml", ".yaml", ".properties"} else "DOCUMENTATION")
            sources[relative] = {"sha256": file_hash(path), "kind": kind, "bytes": len(raw),
                                 "supported": suffix in EXTENSIONS}
    return sources, excluded


def current_graph(root: Path, workspace: Path | None = None):
    """Current AS_IS graph in memory; shared by packets and deterministic audits."""
    if workspace is not None:
        from .workspace import snapshot_workspace
        return snapshot_workspace(workspace, cache_root=root)[3], (0, 0), None
    graph, counts, error = apply_semantic_layer(scan_repository(root), root)
    from .schema_replay import reconstruct, graph_entities
    from .flyway import DEFAULT_LOCATION
    from .flyway import configuration
    cfg = configuration(root)
    configured = any('path' in p for p in cfg['provenance'])
    if (root / DEFAULT_LOCATION).is_dir() or configured:
        schema = reconstruct(root)
        graph = attach_schema(graph, schema, root)
    return graph, counts, error


def attach_schema(graph, schema, root: Path | None = None):
    """Replace migration-union SQL entities with the effective target schema."""
    from .schema_replay import graph_entities
    from .model import KnowledgeGraph
    migration_paths = {m['path'] for m in schema['inventory']}
    removed = {n.id for n in graph.nodes if n.path in migration_paths and
               (n.kind.startswith('db_') or n.kind in {'migration', 'migration_operation'})}
    nodes, edges = graph_entities(schema)
    remaining = {n.id: n for n in graph.nodes if n.id not in removed}
    remaining.update({n.id: n for n in nodes})
    all_edges = [e for e in graph.edges if e.source not in removed and e.target not in removed] + edges
    # Exact declared ORM table/column identity, not fuzzy field-name matching.
    from .model import Edge
    for old_edge in graph.edges:
        if old_edge.target not in removed or old_edge.kind not in {'maps_to', 'persisted_in', 'maps_to_column'}:
            continue
        old = next(n for n in graph.nodes if n.id == old_edge.target)
        owners = [n for n in graph.nodes if n.kind == 'db_table' and any(
            e.source == n.id and e.target == old.id and e.kind == 'contains_column' for e in graph.edges)]
        targets = [n for n in nodes if n.kind == old.kind and any(
            n.name.endswith('.' + owner.name + '.' + old.name) for owner in owners)]
        if len(targets) == 1:
            all_edges.append(Edge(old_edge.source, targets[0].id, 'persisted_in', old_edge.evidence,
                                  old_edge.confidence, old_edge.confidence_score, old_edge.source_file, old_edge.source_line))
    from .schema_replay import schema_mappings
    mappings, _ = schema_mappings(root, schema, graph) if root is not None else ([], [])
    all_edges += mappings
    return KnowledgeGraph(graph.schema_version, graph.root, graph.generated_at,
                          sorted(remaining.values(), key=lambda n: n.id), all_edges, graph.files)


def source_path(root: Path, key: str, packet: dict) -> Path:
    if packet.get('workspace'):
        from .workspace import source_path as resolve
        return resolve(packet, key)
    return safe_path(root, key)


def graph_for_packet(root: Path, packet: dict):
    workspace = Path(packet['workspace']['manifest_path']) if packet.get('workspace') else None
    return current_graph(root, workspace)[0]


def snapshot(root: Path, *, workspace: Path | None = None, _details: dict | None = None, _persist_cache: bool = False) -> tuple[dict, dict, dict, list]:
    if workspace is not None:
        from .workspace import snapshot_workspace
        baseline, coverage, sources, graph, metadata = snapshot_workspace(workspace, cache_root=root, persist_cache=_persist_cache)
        if _details is not None:
            _details['workspace'] = metadata
        return baseline, coverage, sources, graph.nodes
    graph, _, semantic_error = current_graph(root)
    graph_data = graph.to_dict()
    graph_data.pop("generated_at", None)
    sources, excluded = source_inventory(root)
    try:
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    semantic_path = safe_path(root, ".kgmaker/semantic.json")
    baseline = {"git_commit": commit, "graph_fingerprint": digest(graph_data),
                "working_tree_fingerprint": digest(sources), "parser_version": PARSER_VERSION,
                "semantic_hash": file_hash(semantic_path) if semantic_path.exists() else None}
    limitations = ["Static paths do not prove runtime availability; scoped supplied observations require approved mappings.",
                   "No XLSX, template data-flow, or complete interprocedural parser in this milestone.",
                   "Only the supplied repository root is covered; external systems are not inspected."]
    if semantic_error:
        limitations.append("Semantic layer omitted invalid entries: " + semantic_error)
    flow = extract_dataflow({p: safe_path(root, p).read_text(encoding="utf-8", errors="replace") for p, item in sources.items() if item["supported"]})
    coverage = {"roots": ["."], "artifacts": sorted(sources), "exclusions": excluded,
                "excluded_directories": sorted(SKIP_DIRS) + ["hidden directories", GENERATED_PREFIX],
                "parser_capabilities": {"structural": PARSER_VERSION, "data_flow": CAPABILITIES, "workbooks": False},
                "dataflow_diagnostics": flow.diagnostics,
                "limitations": limitations,
                "unsupported_sources": sorted(p for p, x in sources.items() if not x["supported"])}
    from .flyway import configuration, DEFAULT_LOCATION
    config = configuration(root)
    if (root / DEFAULT_LOCATION).is_dir() or any('path' in p for p in config['provenance']):
        from .schema_replay import reconstruct, schema_mappings
        schema = reconstruct(root); schema.pop('checkpoints', None)
        _, schema['mapping_diagnostics'] = schema_mappings(root, schema, graph)
        coverage['schemas'] = {'.': [schema]}
        coverage['parser_capabilities']['flyway'] = schema['schema_parser_version']
        coverage['pending'] = schema['diagnostics'] + [d['reason'] for d in schema['mapping_diagnostics']]
    return baseline, coverage, sources, graph.nodes


def packet_identity(packet: dict) -> str:
    return digest({key: value for key, value in packet.items() if key != "packet_id"})


def load_packet(root: Path, analysis_id: str) -> dict:
    packet = read_json(analysis_dir(root, analysis_id) / "packet.json")
    if not isinstance(packet, dict) or packet.get("schema_version") != SCHEMA_VERSION or packet.get("analysis_id") != analysis_id:
        raise AnalysisError("Unsupported or inconsistent analysis packet")
    if packet.get("packet_id") != packet_identity(packet):
        raise AnalysisError("Packet integrity mismatch; prepare a fresh packet", 3)
    return packet


def freshness(root: Path, packet: dict) -> list[str]:
    workspace = Path(packet['workspace']['manifest_path']) if packet.get('workspace') else None
    baseline, _, sources, _ = snapshot(root, workspace=workspace)
    changes = []
    for key in ("graph_fingerprint", "working_tree_fingerprint", "parser_version", "semantic_hash"):
        if baseline[key] != packet["baseline"][key]:
            changes.append(f"baseline.{key} changed")
    if workspace is not None and baseline.get('manifest_hash') != packet['baseline'].get('manifest_hash'):
        changes.append('Workspace manifest changed')
    expected = packet["source_manifest"]
    for path in sorted(set(sources) | set(expected)):
        if sources.get(path) != expected.get(path):
            changes.append(f"source changed/added/removed: {path}")
    requirement = safe_path(root, packet["requirement_path"])
    if not requirement.exists() or file_hash(requirement) != packet["requirement_file_hash"]:
        changes.append("original requirement changed or was removed")
    return changes


def prepare(root: Path, requirement: str, analysis_id: str, token_budget: int = 8000, *, _answers: list | None = None, workspace: Path | None = None) -> dict:
    if type(token_budget) is not int or token_budget < 1:
        raise AnalysisError("token-budget must be a positive integer")
    directory = analysis_dir(root, analysis_id)
    source = safe_path(root, requirement)
    if source.is_relative_to(root / ".kgmaker") or requirement.startswith(GENERATED_PREFIX):
        raise AnalysisError("Requirement must be a source document outside generated analysis artifacts")
    text = source.read_text(encoding="utf-8")
    requirement_file_hash = file_hash(source)
    if not text.strip():
        raise AnalysisError("Requirement must not be empty")
    old = load_packet(root, analysis_id) if (directory / "packet.json").exists() else None
    if workspace is None and old and old.get('workspace'):
        workspace = Path(old['workspace']['manifest_path'])
    details = {}
    baseline, coverage, manifest, nodes = snapshot(root, workspace=workspace, _details=details, _persist_cache=True)
    if file_hash(source) != requirement_file_hash:
        raise AnalysisError('Requirement changed during packet preparation', 3)
    answers = _answers if _answers is not None else old.get("answers", []) if old else []
    packet = {"schema_version": SCHEMA_VERSION, "analysis_id": analysis_id,
              "revision": old["revision"] if old else 1, "requirement": text,
              "requirement_path": requirement, "requirement_file_hash": requirement_file_hash,
              "answers": answers, "requirement_hash": digest({"text": text, "answers": answers}),
              "baseline": baseline, "coverage": coverage, "source_manifest": manifest,
              "allowed_graph_ids": sorted(node.id for node in nodes),
              "evidence_inventory": [{"graph_id": n.id, "path": manifest[n.path].get('path', n.path), "line": n.line,
                                      **({'repo_id': manifest[n.path]['repo_id']} if 'repo_id' in manifest[n.path] else {}),
                                      "sha256": manifest[n.path]["sha256"]}
                                     for n in nodes if n.path in manifest and n.line],
              "budget": {"requested_tokens": token_budget, "estimator": "ceil(UTF-8 context bytes / 4)"},
              "context": []}
    packet.update(details)
    # Commit changes alone do not invalidate identical working-tree content.
    if old and all(baseline[k] == old["baseline"][k] for k in baseline if k != "git_commit"):
        packet["baseline"]["git_commit"] = old["baseline"]["git_commit"]
    terms = set(text.lower().split())
    ranked = sorted(manifest, key=lambda p: (-sum(t in p.lower() for t in terms if len(t) > 3), p))
    # The full manifest is mandatory. The budget applies to optional source context;
    # explicitly account for mandatory metadata that can itself exceed the budget.
    mandatory_tokens = (len(canonical(packet).encode("utf-8")) + 3) // 4
    remaining = max(0, token_budget - mandatory_tokens)
    included = []
    for path in ranked:
        if not manifest[path]["supported"]:
            continue
        content = source_path(root, path, packet).read_text(encoding="utf-8", errors="replace")
        # Config provenance uses raw hashes, but credentials never enter model context.
        if manifest[path]['kind'] == 'CONFIG':
            content = '\n'.join('[REDACTED CONFIG LINE]' if re.search(r'(?i)password|passwd|secret|credential|api[_-]?key|access[_-]?token', line)
                                else line for line in content.splitlines())
        entry = {"path": path, "content": content}
        cost = (len(canonical(entry).encode("utf-8")) + 3) // 4
        if cost <= remaining:
            packet["context"].append(entry)
            remaining -= cost
            included.append(path)
    omitted = sorted(set(manifest) - set(included))
    packet["coverage"].update({"included_sources": included, "omitted_sources": omitted,
                               "pending": [f"Source not included in agent context: {p}" for p in omitted] +
                               [f"Data-flow unresolved: {d['path']}:{d['line']}: {d['reason']}" for d in coverage["dataflow_diagnostics"]] + coverage.get('pending', [])})
    packet["budget"].update({"mandatory_metadata_tokens": mandatory_tokens,
                            "included_count": len(included), "omitted_count": len(omitted)})
    if packet.get('workspace'):
        for repo, scope in packet['coverage']['repositories'].items():
            scope['included_sources'] = sorted(manifest[k]['path'] for k in included if manifest[k]['repo_id'] == repo)
            scope['omitted_sources'] = sorted(manifest[k]['path'] for k in omitted if manifest[k]['repo_id'] == repo)
    if old:
        comparable = {k: v for k, v in old.items() if k not in {"packet_id", "revision"}}
        if comparable != {k: v for k, v in packet.items() if k != "revision"}:
            packet["revision"] += 1
    packet["packet_id"] = packet_identity(packet)
    if old and packet == old:
        return old
    if old:
        write_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/history/packet-{old['revision']}.json"), old)
    atomic_write(safe_path(root, f".kgmaker/analyses/{analysis_id}/requirement.md"), text)
    write_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/packet.json"), packet)
    # Never overwrite the agent's candidate, including a now-stale candidate.
    write_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/candidate-template.json"), inventory_candidate(packet))
    return packet


def validate(root: Path, analysis_id: str, candidate: dict) -> dict:
    from .analysis_validation import validate_candidate
    packet = load_packet(root, analysis_id)
    try:
        errors = validate_candidate(root, packet, candidate)
    except (TypeError, KeyError, ValueError, RecursionError) as exc:
        errors = [f"Malformed candidate structure: {exc}"]
    stale = freshness(root, packet)
    if isinstance(candidate, dict):
        from .availability import observation_staleness
        stale += observation_staleness(candidate)
        for key in ("packet_id", "revision", "requirement_hash", "baseline"):
            if candidate.get(key) != packet[key]:
                stale.append(f"candidate.{key} does not match current packet")
    completion = candidate.get("completion", {}) if isinstance(candidate, dict) else {}
    return {"valid": not errors and not stale, "diagnostics": errors, "stale": stale,
            "completion": completion, "exit_code": 3 if stale else 2 if errors else 0,
            "next_step": f"kgmaker feature prepare --root . --requirement {packet['requirement_path']} --id {analysis_id}; regenerate candidate from the new packet" if stale else None}


def apply(root: Path, analysis_id: str, candidate: dict) -> dict:
    result = validate(root, analysis_id, candidate)
    if not result["valid"]:
        return result
    target = safe_path(root, f".kgmaker/analyses/{analysis_id}/analysis.json")
    if target.exists():
        previous = read_json(target)
        if previous == candidate:
            return result
        if previous["revision"] == candidate["revision"]:
            raise AnalysisError("Applied revision is immutable; revise before replacing it")
        write_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/history/analysis-{previous['revision']}.json"), previous)
    write_json(safe_path(root, f".kgmaker/analyses/{analysis_id}/receipts/{candidate['revision']}.json"),
               {"candidate_hash": digest(candidate), "packet_id": candidate["packet_id"], "revision": candidate["revision"]})
    write_json(target, candidate)
    return result


def status(root: Path, analysis_id: str) -> dict:
    packet = load_packet(root, analysis_id)
    path = safe_path(root, f".kgmaker/analyses/{analysis_id}/analysis.json")
    candidate = read_json(path) if path.exists() else inventory_candidate(packet)
    result = validate(root, analysis_id, candidate)
    return {**result, "analysis_id": analysis_id, "revision": packet["revision"],
            "applied": path.exists(), "coverage": packet["coverage"], "answers": packet["answers"]}


def revise(root: Path, analysis_id: str, answers: dict) -> dict:
    """Prepare a new immutable revision; do not silently rebind old conclusions."""
    packet = load_packet(root, analysis_id)
    target = safe_path(root, f".kgmaker/analyses/{analysis_id}/analysis.json")
    if not target.exists():
        raise AnalysisError("Apply an analysis with question IDs before revise")
    candidate = read_json(target)
    questions = {q["id"] for q in candidate["questions"]}
    if not isinstance(answers, dict) or set(answers) != {"answers"} or not isinstance(answers["answers"], list) or not answers["answers"]:
        raise AnalysisError('Answers must be a non-empty {"answers": [...]} object')
    seen = set()
    updated = {a["question_id"]: a for a in packet["answers"]}
    for answer in answers["answers"]:
        fields = {"question_id", "decision_id", "answer", "revision", "approval_status"}
        if not isinstance(answer, dict) or set(answer) != fields:
            raise AnalysisError("Each answer requires question_id, decision_id, answer, revision and approval_status")
        if any(not isinstance(answer[k], str) or not answer[k].strip() for k in fields - {"revision"}):
            raise AnalysisError("Answer text and identifiers must be non-empty strings")
        qid = answer["question_id"]
        if qid not in questions or qid in seen:
            raise AnalysisError("Answer must reference a unique existing question")
        if answer["approval_status"] not in {"APPROVED", "UNAPPROVED", "UNKNOWN"} or type(answer["revision"]) is not int or answer["revision"] < 1:
            raise AnalysisError("Invalid decision revision or approval status")
        previous = updated.get(qid)
        if previous and previous != answer and answer["revision"] <= previous["revision"]:
            raise AnalysisError("Changed decision requires a higher decision revision")
        seen.add(qid)
        updated[qid] = answer
    if len({a["decision_id"] for a in updated.values()}) != len(updated):
        raise AnalysisError("Decision IDs must be unique")
    new_answers = sorted(updated.values(), key=lambda a: a["question_id"])
    if new_answers == packet["answers"]:
        return packet
    if candidate.get("packet_id") != packet["packet_id"]:
        raise AnalysisError("Apply a candidate for the current packet before revising answers", 3)
    return prepare(root, packet["requirement_path"], analysis_id,
                   packet["budget"]["requested_tokens"], _answers=new_answers)

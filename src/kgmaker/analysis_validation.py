"""Fail-closed validation of agent candidates against a deterministic packet.

Citation integrity is checked; truth of arbitrary prose is not mechanically
proved. Positive availability is delegated to the explicit scoped proof checker;
unsupported claims cannot be upgraded by confidence or name similarity.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from .analysis_model import (
    AnalysisError, COLLECTIONS, FeatureAnalysis, INPUT_METADATA, PROPOSAL_RELATIONS,
    file_hash, read_json, safe_path,
)


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" or (tag == "a" and key == "name"):
                self.anchors.add(value)


def _location(root: Path, item: dict, packet: dict) -> None:
    kind = item.get("kind")
    if kind == "HUMAN_DECISION":
        decision = next((a for a in packet["answers"] if a["decision_id"] == item.get("decision_id")), None)
        if decision is None or any(item.get(k) != decision[k] for k in ("answer", "revision", "approval_status")):
            raise AnalysisError("Human decision must match an explicit packet answer and approval status")
        return
    if kind == "REQUIREMENT":
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote or quote not in packet["requirement"]:
            raise AnalysisError("Requirement quote is not present in the exact requirement")
        if item.get("sha256") != packet["requirement_file_hash"]:
            raise AnalysisError("Requirement evidence hash mismatch")
        return
    path = item.get("path")
    from .feature import source_path
    key = path
    if packet.get('workspace'):
        from .workspace import source_key, split_id
        repo = item.get('repo_id')
        if not isinstance(repo, str) or repo not in packet['workspace']['roots']:
            raise AnalysisError('Workspace evidence requires an approved repo_id')
        safe_path(Path(packet['workspace']['roots'][repo]), path)
        key = source_key(repo, path)
        if item.get('source_id') in packet['allowed_graph_ids'] and item['source_id'].startswith('repo:'):
            if split_id(item['source_id'])[0] != repo:
                raise AnalysisError('Evidence source_id belongs to a different repository')
        declared_source = packet['source_manifest'].get(item.get('source_id'))
        if declared_source and declared_source.get('repo_id') != repo:
            raise AnalysisError('Evidence source_id belongs to a different repository')
    elif item.get('repo_id') is not None:
        raise AnalysisError('Single-repo evidence must not invent repo_id')
    target = source_path(root, key, packet)
    manifest = packet["source_manifest"].get(key)
    if not manifest or not target.is_file():
        raise AnalysisError("Evidence source is not in the packet source manifest")
    if item.get("sha256") != manifest["sha256"] or file_hash(target) != item.get("sha256"):
        raise AnalysisError("Evidence source hash mismatch")
    if kind != manifest["kind"]:
        raise AnalysisError(f"Evidence kind must be {manifest['kind']} for this source")
    location = item.get("location")
    if not isinstance(location, dict):
        raise AnalysisError("Evidence location must be an object")
    form = location.get("type")
    if form == "lines":
        text = target.read_text(encoding="utf-8")
        start, end = location.get("start"), location.get("end")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(text.splitlines()):
            raise AnalysisError("Evidence line range does not exist")
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote or quote not in "\n".join(text.splitlines()[start - 1:end]):
            raise AnalysisError("Evidence quote is not present in the cited line range")
    elif form == "json_pointer":
        pointer = location.get("pointer")
        if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
            raise AnalysisError("Invalid JSON pointer")
        value = read_json(target)
        for part in pointer.split("/")[1:] if pointer else []:
            if re.search(r"~(?![01])", part):
                raise AnalysisError("Invalid JSON pointer escape")
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", part):
                    raise AnalysisError("Invalid JSON array index")
                value = value[int(part)]
            elif isinstance(value, dict):
                value = value[part]
            else:
                raise AnalysisError("JSON pointer traverses a scalar")
        if "value" not in item or item["value"] != value:
            raise AnalysisError("Evidence value does not match cited JSON pointer")
    elif form == "workbook_cell":
        if kind != "WORKBOOK":
            raise AnalysisError("Workbook cell evidence requires a WORKBOOK source")
        from .workbooks import locate_cell
        value = locate_cell(target, location.get("sheet"), location.get("cell"))
        if item.get("value") != value:
            raise AnalysisError("Evidence value does not match cited workbook cell")
    elif form == "html_anchor":
        text = target.read_text(encoding="utf-8")
        parser = _Anchors()
        parser.feed(text)
        if location.get("anchor") not in parser.anchors:
            raise AnalysisError("HTML anchor does not exist")
        # Checking an anchor alone cannot locate a prose claim within its section.
        raise AnalysisError("HTML section evidence is not supported yet; use exact line evidence")
    else:
        raise AnalysisError(f"Unsupported evidence location: {form!r}; use lines, json_pointer or workbook_cell")


def validate_candidate(root: Path, packet: dict, data: object) -> list[str]:
    try:
        return _validate_candidate(root, packet, data)
    except (TypeError, KeyError, ValueError, RecursionError) as exc:
        return [f"Malformed candidate structure: {exc}"]


def _validate_candidate(root: Path, packet: dict, data: object) -> list[str]:
    errors = []
    try:
        candidate = FeatureAnalysis.from_dict(data).to_dict()
    except (AnalysisError, TypeError, ValueError) as exc:
        return [str(exc)]
    prefix = f"analysis:{packet['analysis_id']}:"
    proposal_prefix = f"proposal:{packet['analysis_id']}:"
    if candidate["analysis_id"] != packet["analysis_id"]:
        errors.append("analysis_id mismatch")
    if candidate["language"] not in {"cs", "en"}:
        errors.append("language must be cs or en")
    if candidate["coverage"] != packet["coverage"]:
        errors.append("coverage must preserve the packet inventory and limitations")
    allowed_top = set(COLLECTIONS) | {"schema_version", "analysis_id", "revision", "packet_id", "requirement_hash", "language", "baseline", "coverage", "proposal", "completion"}
    if set(candidate) - allowed_top:
        errors.append("Unknown top-level fields: " + ", ".join(sorted(set(candidate) - allowed_top)))
    ids = {}
    by_collection = {}
    allowed_fields = {
        "requirements": {"id", "text", "kind", "source_quote", "status"},
        "input_requirements": {"id", "name", "requirement_ids", "source_ids", "evidence_ids", "dependency_ids", "question_ids", "availability", "acquisition", "usability", "verification_scope", "next_step", "owner_role", "transformation", "search_fingerprint", "availability_proof"} | set(INPUT_METADATA),
        "capability_matches": {"id", "entity_ids", "requirement_ids", "evidence_ids", "rationale", "limitations", "state", "method", "validity"},
        "changes": {"id", "repo_id", "requirement_ids", "entity_ids", "dependency_ids", "layer", "reason", "inputs", "outputs", "test_impact", "state"},
        "questions": {"id", "text", "owner_role", "status", "requirement_ids", "blocking", "blocker_kind"},
        "assumptions": {"id", "text", "state", "requirement_ids"},
        "alternatives": {"id", "name", "constraints", "limitations", "proposal_ids", "question_ids", "requirement_ids"},
        "acceptance_criteria": {"id", "text", "requirement_ids"},
        "test_plan": {"id", "text", "requirement_ids", "state", "entity_ids", "evidence_ids"},
        "evidence": {"id", "source_id", "kind", "path", "repo_id", "sha256", "location", "quote", "value", "supports", "method", "validity", "confidence", "decision_id", "answer", "revision", "approval_status", "question_id"},
        "impact_paths": {"id", "entity_ids", "edges", "weakest_confidence", "unresolved_boundary", "evidence_ids"},
    }
    for collection in COLLECTIONS:
        by_collection[collection] = {}
        for item in candidate[collection]:
            if set(item) - allowed_fields[collection]:
                errors.append(f"{collection}: unknown fields {sorted(set(item) - allowed_fields[collection])}")
            identity = item.get("id")
            if not isinstance(identity, str) or not identity.startswith(prefix) or identity == prefix:
                errors.append(f"{collection}: ID must use {prefix}<kind>:<name>")
                continue
            if identity in ids:
                errors.append(f"Duplicate ID: {identity}")
            ids[identity] = item
            by_collection[collection][identity] = item
    graph_ids = set(packet["allowed_graph_ids"])
    proposal = candidate["proposal"]
    if set(proposal) != {"nodes", "edges"} or any(not isinstance(proposal.get(k), list) for k in ("nodes", "edges")):
        return errors + ["proposal must contain nodes and edges arrays only"]
    for node in proposal["nodes"]:
        if not isinstance(node, dict):
            errors.append("Proposal node must be an object")
            continue
        identity = node.get("id")
        if not isinstance(identity, str) or not identity.startswith(proposal_prefix) or identity == proposal_prefix or identity in ids or identity in graph_ids:
            errors.append("Proposal node must have a unique proposal-scoped ID")
        else:
            ids[identity] = node
        if set(node) != {"id", "state", "name", "kind", "description"}:
            errors.append("Unsupported proposal node fields")
        if node.get("state") != "TO_BE":
            errors.append("Proposal nodes must stay TO_BE")
        for key in ("name", "kind", "description"):
            if not isinstance(node.get(key), str) or not node[key].strip():
                errors.append(f"Proposal node requires {key}")
    for edge in proposal["edges"]:
        if not isinstance(edge, dict):
            errors.append("Proposal edge must be an object")
            continue
        if set(edge) != {"source", "target", "kind", "state"}:
            errors.append("Unsupported proposal edge fields")
        if edge.get("kind") not in PROPOSAL_RELATIONS or edge.get("state") != "TO_BE":
            errors.append("Proposal edge must use a supported relation and TO_BE state")
        for key in ("source", "target"):
            if not isinstance(edge.get(key), str) or edge[key] not in ids.keys() | graph_ids:
                errors.append(f"Dangling proposal {key}: {edge.get(key)!r}")

    def strings(item, key, choices=None, nullable=False):
        value = item.get(key)
        if value is None and nullable and key in item:
            return
        if not isinstance(value, str) or not value.strip() or (choices and value not in choices):
            errors.append(f"{item.get('id', '?')}: invalid/missing {key}")

    def refs(item, key, targets, required=False):
        value = item.get(key)
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
            errors.append(f"{item.get('id', '?')}: {key} must be an array of IDs")
            return []
        if required and not value:
            errors.append(f"{item.get('id', '?')}: {key} must not be empty")
        if len(value) != len(set(value)) or any(x not in targets for x in value):
            errors.append(f"{item.get('id', '?')}: dangling or duplicate {key}")
        return value

    evidence = by_collection["evidence"]
    for item in candidate["evidence"]:
        strings(item, "source_id")
        strings(item, "supports")
        strings(item, "kind", {"CODE", "CONTRACT", "SCHEMA", "CONFIG", "DOCUMENTATION", "WORKBOOK", "REQUIREMENT", "HUMAN_DECISION"})
        strings(item, "method", {"EXTRACTED", "INFERRED", "AMBIGUOUS"})
        strings(item, "validity", {"VALID", "STALE", "UNRESOLVED"})
        if type(item.get("confidence")) not in {int, float} or not 0 <= item["confidence"] <= 1:
            errors.append(f"{item.get('id')}: confidence must be between 0 and 1")
        try:
            _location(root, item, packet)
        except (AnalysisError, OSError, UnicodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            errors.append(f"{item.get('id')}: {exc}")
    requirements = by_collection["requirements"]
    if not requirements:
        errors.append("At least one requirement must be represented")
    for item in candidate["requirements"]:
        strings(item, "text")
        strings(item, "kind", {"Goal", "InputRequirement", "OutputRequirement", "BusinessRule", "Constraint"})
        strings(item, "status", {"ADDRESSED", "OPEN_QUESTION", "UNRESOLVED"})
        quote = item.get("source_quote")
        if not isinstance(quote, str) or not quote or quote not in packet["requirement"]:
            errors.append(f"{item.get('id')}: requirement source_quote is not in the requirement")
    for item in candidate["questions"]:
        strings(item, "text")
        strings(item, "owner_role", nullable=True)
        strings(item, "status", {"OPEN", "ANSWERED"})
        refs(item, "requirement_ids", requirements, True)
        if "blocker_kind" in item:
            strings(item, "blocker_kind", {"BUSINESS", "TOOL", "UNCLASSIFIED"})
        if type(item.get("blocking")) is not bool:
            errors.append("question.blocking must be boolean")
        if item.get("status") == "ANSWERED" and not any(a["question_id"] == item.get("id") for a in packet["answers"]):
            errors.append("Answered question has no explicit packet answer")
    for item in candidate["input_requirements"]:
        strings(item, "name")
        refs(item, "requirement_ids", requirements, True)
        refs(item, "evidence_ids", evidence)
        refs(item, "source_ids", graph_ids)
        refs(item, "dependency_ids", by_collection["input_requirements"])
        refs(item, "question_ids", by_collection["questions"])
        strings(item, "availability", {"AVAILABLE", "PARTIAL", "NOT_FOUND_IN_SCOPE", "CONFIRMED_MISSING", "UNKNOWN"})
        strings(item, "acquisition", {"EXISTING", "DERIVED", "EXTERNAL", "USER_SUPPLIED", "PROPOSED", "UNRESOLVED"})
        strings(item, "usability", {"FIT", "TRANSFORMATION_REQUIRED", "INCOMPATIBLE", "UNASSESSED"})
        strings(item, "verification_scope")
        strings(item, "next_step")
        strings(item, "owner_role", nullable=True)
        strings(item, "transformation", nullable=True)
        for key in INPUT_METADATA:
            value = item.get(key)
            if key not in item:
                errors.append(f"{item.get('id')}: input metadata {key} must be explicit (null if unknown)")
            elif value is not None:
                expected = list if key in {"keys", "quality", "fallbacks"} else bool if key == "nullable" else str
                if type(value) is not expected or (expected is list and any(not isinstance(x, str) for x in value)):
                    errors.append(f"{item.get('id')}: invalid input metadata {key}")
        availability = item.get("availability")
        # Positive proof support is an explicit milestone B gate, never a confidence heuristic.
        if availability in {"AVAILABLE", "PARTIAL", "CONFIRMED_MISSING"}:
            from .availability import evaluate_proof
            try:
                checked = evaluate_proof(root, packet, candidate, item)
                if checked['availability'] != availability or checked['usability'] != item.get('usability'):
                    errors.append('Availability/usability differ from deterministic proof result')
                if checked['scope'] != item.get('verification_scope'):
                    errors.append('Positive proof verification_scope must preserve its exact limited scope')
                if item.get('acquisition') == 'DERIVED' and any(by_collection['input_requirements'].get(dep, {}).get('availability') != 'AVAILABLE' for dep in item.get('dependency_ids', [])):
                    errors.append('Positive derived availability requires all dependency inputs AVAILABLE')
            except (AnalysisError, TypeError, KeyError, ValueError) as exc:
                errors.append(f"{item.get('id')}: {exc}; use UNKNOWN without a valid proof")
        if availability == "NOT_FOUND_IN_SCOPE":
            if packet["coverage"]["omitted_sources"] or packet["coverage"]["unsupported_sources"]:
                errors.append("Incomplete source inspection requires UNKNOWN, not NOT_FOUND_IN_SCOPE")
            if item.get("search_fingerprint") != packet["baseline"]["working_tree_fingerprint"]:
                errors.append("Negative lookup must identify its searched inventory fingerprint")
        if item.get("acquisition") == "DERIVED" and (not item.get("dependency_ids") or not item.get("transformation")):
            errors.append("DERIVED requires a transformation and explicit dependencies")
    # Reject unanchored cycles; a recursive walk must also tolerate malformed references.
    dependencies = {k: [x for x in v.get("dependency_ids", []) if isinstance(x, str)]
                    for k, v in by_collection["input_requirements"].items() if isinstance(v.get("dependency_ids"), list)}
    visiting, done = set(), set()
    def visit(identity):
        if identity in visiting:
            errors.append("Cyclic derivation without a proven input anchor")
            return
        if identity in done:
            return
        visiting.add(identity)
        for other in dependencies.get(identity, []):
            visit(other)
        visiting.remove(identity)
        done.add(identity)
    for identity in dependencies:
        visit(identity)
    for item in candidate["capability_matches"]:
        refs(item, "entity_ids", graph_ids, True)
        refs(item, "requirement_ids", requirements, True)
        selected = refs(item, "evidence_ids", evidence, True)
        strings(item, "rationale")
        strings(item, "limitations")
        strings(item, "state", {"AS_IS"})
        strings(item, "method", {"EXTRACTED", "INFERRED", "AMBIGUOUS"})
        strings(item, "validity", {"VALID", "STALE", "UNRESOLVED"})
        if not any(evidence.get(e, {}).get("kind") in {"CODE", "SCHEMA", "CONTRACT", "CONFIG"} for e in selected):
            errors.append("Existing implementation cannot be supported solely by business documentation")
        if item.get("method") == "EXTRACTED":
            errors.append("Capability reuse is a semantic inference; use INFERRED or AMBIGUOUS")
    for item in candidate["changes"]:
        if 'repo_id' in item and item['repo_id'] not in packet.get('workspace', {}).get('roots', {}):
            errors.append('Change repo_id must identify a declared workspace repository')
        refs(item, "requirement_ids", requirements, True)
        refs(item, "entity_ids", graph_ids | set(ids), True)
        refs(item, "dependency_ids", ids.keys() | graph_ids)
        for key in ("layer", "reason", "inputs", "outputs", "test_impact"):
            strings(item, key)
        strings(item, "state", {"TO_BE"})
    if candidate["impact_paths"]:
        from .dataflow import impact_paths
        from .scanner import scan_repository
        from .semantic import apply_semantic_layer
        from .feature import graph_for_packet
        graph = graph_for_packet(root, packet)
        computed = {}
        for item in candidate["impact_paths"]:
            entities = refs(item, "entity_ids", graph_ids, True)
            citations = refs(item, "evidence_ids", evidence, True)
            if len(entities) < 2 or any(entity not in graph_ids for entity in entities):
                errors.append("Impact path requires at least two existing graph entities")
                continue
            seed = entities[0]
            if seed not in computed:
                computed[seed] = impact_paths(graph, seed)["paths"]
            proof = {k: item.get(k) for k in ("entity_ids", "edges", "weakest_confidence", "unresolved_boundary")}
            if proof not in computed[seed]:
                errors.append("Impact path does not match a supported directed path in the current graph")
                continue
            from .workspace import source_key
            cited_paths = {(source_key(evidence[e]['repo_id'], evidence[e]['path']) if packet.get('workspace') else evidence[e].get('path'))
                           for e in citations if e in evidence and evidence[e].get('validity') == 'VALID'}
            needed_paths = {edge["source_file"] for edge in proof["edges"] if edge["source_file"]}
            if not needed_paths <= cited_paths:
                errors.append("Impact path needs valid evidence for every edge source file")
    for item in candidate["assumptions"]:
        strings(item, "text")
        strings(item, "state", {"UNKNOWN"})
        refs(item, "requirement_ids", requirements, True)
    for item in candidate["alternatives"]:
        strings(item, "name")
        strings(item, "constraints")
        strings(item, "limitations")
        refs(item, "proposal_ids", {k for k in ids if k.startswith(proposal_prefix)}, True)
        refs(item, "question_ids", by_collection["questions"])
        refs(item, "requirement_ids", requirements, True)
    for collection in ("acceptance_criteria", "test_plan"):
        for item in candidate[collection]:
            strings(item, "text")
            refs(item, "requirement_ids", requirements, True)
            if collection == "test_plan":
                strings(item, "state", {"AS_IS", "TO_BE"})
                refs(item, "entity_ids", graph_ids, item.get("state") == "AS_IS")
                refs(item, "evidence_ids", evidence, item.get("state") == "AS_IS")
    for identity, item in requirements.items():
        if item.get("status") == "OPEN_QUESTION" and not any(identity in q.get("requirement_ids", []) for q in candidate["questions"]):
            errors.append(f"{identity}: OPEN_QUESTION has no question")
        if item.get("status") == "ADDRESSED" and not any(identity in x.get("requirement_ids", []) for x in candidate["changes"] + candidate["capability_matches"]):
            errors.append(f"{identity}: ADDRESSED has no solution or reuse candidate")
    completion = candidate["completion"]
    strings(completion, "processing_status", {"SEMANTIC_PENDING", "PARTIAL", "COMPLETE"})
    strings(completion, "decision_readiness", {"READY", "BLOCKED"})
    pending = completion.get("pending")
    if not isinstance(pending, list) or any(not isinstance(x, str) or not x for x in pending):
        errors.append("completion.pending must be an array of non-empty strings")
    if completion.get("processing_status") == "COMPLETE":
        if pending or packet["coverage"]["pending"] or any(r.get("status") == "UNRESOLVED" for r in requirements.values()):
            errors.append("COMPLETE cannot have pending work or unresolved requirements")
        if any(e.get("validity") != "VALID" for e in candidate["evidence"]):
            errors.append("COMPLETE cannot depend on stale/unresolved evidence")
    if completion.get("decision_readiness") == "READY":
        if (completion.get("processing_status") != "COMPLETE" or candidate["assumptions"]
                or any(q.get("blocking") and (q.get("status") != "ANSWERED" or not any(a["question_id"] == q.get("id") and a["approval_status"] == "APPROVED" for a in packet["answers"])) for q in candidate["questions"])):
            errors.append("READY requires complete processing and approved blocking decisions")
    return sorted(set(errors))

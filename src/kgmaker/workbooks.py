"""Bounded, read-only XLSX extraction using only the Python standard library.

Formulas are recorded as text and dependencies; they are never evaluated. Cached
values remain separate evidence with explicitly unknown freshness.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import replace
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from .analysis_model import AnalysisError, digest, file_hash
from .classification import Classifier
from .model import Edge, KnowledgeGraph, Node

VERSION = "xlsx-offline-1"
BINARY_DIAGNOSTICS_VERSION = "xls-unsupported-1"
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_ENTRIES = 2_000
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_XML_BYTES = 8 * 1024 * 1024

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CELL = re.compile(r"\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})\Z", re.I)
_REFERENCE = re.compile(
    r"(?:(?:'((?:[^']|'')+)'|([A-Za-z_][\w. ]*))!)?"
    r"(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?",
    re.I,
)


def binary_format(header: bytes) -> str | None:
    """Recognize container/BOF signatures, not workbook validity or cell values.

    CFB is shared by other Office formats; it cannot prove a valid Excel file.
    BIFF BOF markers cover the legacy standalone and compound workbook streams.
    """
    if header.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
        return "OLE_COMPOUND"
    if len(header) >= 8 and header[:2] in {b"\x09\x00", b"\x09\x02", b"\x09\x04", b"\x09\x08"}:
        length = int.from_bytes(header[2:4], "little")
        if length in {4, 6, 8, 16}:
            return "BIFF"
    return None


def unsupported_binary(path: Path, relative: str) -> dict | None:
    """Bounded preflight for declared .xls or binary content renamed to .xlsx."""
    with path.open("rb") as stream:
        detected = binary_format(stream.read(8))
    if path.suffix.lower() != ".xls" and detected is None:
        return None
    return {"path": relative, "code": "BINARY_XLS_UNSUPPORTED", "status": "UNSUPPORTED",
            "detected_format": detected or "UNKNOWN", "sha256": file_hash(path),
            "locator": {"type": "file", "path": relative}, "extractor": BINARY_DIAGNOSTICS_VERSION,
            "reason": "Legacy .xls or binary spreadsheet container is unsupported; no cells or values were read. "
                      "A signature or extension does not establish a valid workbook. "
                      "Provide bounded .xlsx without macros/external links."}


def _identity(kind: str, path: str, name: str) -> str:
    return f"{kind}:{path}:{name}"


def _xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise AnalysisError(f"XLSX is missing required part: {name}") from exc
    if info.file_size > MAX_XML_BYTES:
        raise AnalysisError(f"XLSX XML part exceeds {MAX_XML_BYTES} bytes: {name}")
    raw = archive.read(info)
    upper = raw[:4096].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise AnalysisError(f"XLSX XML declarations/entities are unsupported: {name}")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise AnalysisError(f"Invalid XLSX XML part {name}: {exc}") from exc


def _part(target: str) -> str:
    target = target.replace("\\", "/")
    candidate = PurePosixPath("xl") / target if not target.startswith("/") else PurePosixPath(target[1:])
    parts: list[str] = []
    for item in candidate.parts:
        if item in {"", "."}:
            continue
        if item == "..":
            if not parts:
                raise AnalysisError("XLSX relationship escapes the archive root")
            parts.pop()
        else:
            parts.append(item)
    value = "/".join(parts)
    if not value.startswith("xl/"):
        raise AnalysisError("XLSX relationship escapes the workbook root")
    return value


def _cell_value(cell: ET.Element, shared: list[str]) -> tuple[str | None, str | None]:
    kind = cell.get("t")
    value = cell.findtext(f"{{{_MAIN}}}v")
    if kind == "s" and value is not None:
        try:
            return shared[int(value)], "shared_string"
        except (ValueError, IndexError):
            return None, "invalid_shared_string"
    if kind == "inlineStr":
        text = "".join(cell.itertext())
        return text, "inline_string"
    return value, kind or "number"


def _column_number(value: str) -> int:
    result = 0
    for char in value.upper():
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def _column_name(value: int) -> str:
    result = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _range_cells(start: str, end: str | None) -> list[str]:
    start_match = _CELL.fullmatch(start.upper().replace("$", ""))
    end_match = _CELL.fullmatch((end or start).upper().replace("$", ""))
    if not start_match or not end_match:
        return []
    first_column, last_column = sorted((_column_number(start_match.group(1)), _column_number(end_match.group(1))))
    first_row, last_row = sorted((int(start_match.group(2)), int(end_match.group(2))))
    if (last_column - first_column + 1) * (last_row - first_row + 1) > 10_000:
        return []
    return [f"{_column_name(column)}{row}" for column in range(first_column, last_column + 1)
            for row in range(first_row, last_row + 1)]


def _references(expression: str) -> list[tuple[str | None, str, str | None, str]]:
    # Double-quoted Excel string literals are values, not cell references.
    cleaned = re.sub(r'"(?:[^"]|"")*"', '""', expression)
    return [((match.group(1) or match.group(2)), match.group(3), match.group(4), match.group(0))
            for match in _REFERENCE.finditer(cleaned)]


def extract(path: Path, relative: str, classifier: Classifier) -> tuple[list[Node], list[Edge], list[dict], dict, list[dict]]:
    """Extract workbook nodes, dependency edges, diagnostics, context and evidence."""
    unsupported = unsupported_binary(path, relative)
    if unsupported is not None:
        raise AnalysisError(unsupported["reason"])
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise AnalysisError(f"XLSX archive exceeds {MAX_ARCHIVE_BYTES} bytes")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise AnalysisError(f"Invalid XLSX archive: {relative}") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise AnalysisError(f"XLSX archive exceeds {MAX_ENTRIES} entries")
        if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
            raise AnalysisError(f"XLSX expanded content exceeds {MAX_EXPANDED_BYTES} bytes")
        for info in infos:
            name = PurePosixPath(info.filename)
            if info.flag_bits & 1 or name.is_absolute() or ".." in name.parts or "\\" in info.filename:
                raise AnalysisError("Encrypted or unsafe XLSX archive entry")

        workbook = _xml(archive, "xl/workbook.xml")
        relationships = _xml(archive, "xl/_rels/workbook.xml.rels")
        rels = {
            item.get("Id"): _part(item.get("Target", ""))
            for item in relationships.findall(f"{{{_PKG_REL}}}Relationship")
            if item.get("TargetMode") != "External"
        }
        external_relationships = [
            item for item in relationships.findall(f"{{{_PKG_REL}}}Relationship")
            if item.get("TargetMode") == "External"
        ]
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = _xml(archive, "xl/sharedStrings.xml")
            shared = ["".join(item.itertext()) for item in strings.findall(f"{{{_MAIN}}}si")]

        classification = classifier.classify(relative)
        workbook_id = _identity("workbook", relative, Path(relative).name)
        nodes = [Node(workbook_id, "workbook", Path(relative).name, relative,
                      **classification.__dict__, metadata={"format": "xlsx", "parser": VERSION})]
        edges: list[Edge] = []
        diagnostics: list[dict] = []
        evidence: list[dict] = []
        sheet_ids: dict[str, str] = {}
        cell_ids: dict[tuple[str, str], str] = {}
        formula_cells: list[tuple[str, str, str]] = []

        for sheet in workbook.findall(f".//{{{_MAIN}}}sheet"):
            name = sheet.get("name")
            target = rels.get(sheet.get(f"{{{_REL}}}id"))
            if not name or not target or target not in archive.namelist():
                diagnostics.append({"path": relative, "code": "XLSX_SHEET_UNRESOLVED",
                                    "reason": f"Worksheet relationship is missing: {name or '<unnamed>'}"})
                continue
            sheet_id = _identity("workbook_sheet", relative, name)
            sheet_ids[name] = sheet_id
            nodes.append(Node(sheet_id, "workbook_sheet", name, relative, scope=classification.scope,
                              role=classification.role, origin=classification.origin,
                              build_membership=classification.build_membership,
                              classification_evidence=classification.classification_evidence,
                              metadata={"sheet": name, "part": target, "parser": VERSION}))
            edges.append(Edge(workbook_id, sheet_id, "contains_sheet", f"worksheet {name}"))
            root = _xml(archive, target)
            for cell in root.findall(f".//{{{_MAIN}}}c"):
                reference = (cell.get("r") or "").upper().replace("$", "")
                if not _CELL.fullmatch(reference):
                    diagnostics.append({"path": relative, "code": "XLSX_CELL_REFERENCE_INVALID",
                                        "reason": f"Invalid cell reference in {name}: {reference!r}"})
                    continue
                identity = _identity("workbook_cell", relative, f"{name}!{reference}")
                value, value_type = _cell_value(cell, shared)
                formula_node = cell.find(f"{{{_MAIN}}}f")
                formula = formula_node.text if formula_node is not None else None
                metadata = {"sheet": name, "cell": reference, "locator": f"{name}!{reference}",
                            "value_type": value_type, "cached_value": value,
                            "cached_value_freshness": "UNKNOWN", "formula": formula, "parser": VERSION}
                nodes.append(Node(identity, "workbook_cell", f"{name}!{reference}", relative,
                                  signature=value_type, summary=formula, scope=classification.scope,
                                  role=classification.role, origin=classification.origin,
                                  build_membership=classification.build_membership,
                                  classification_evidence=classification.classification_evidence,
                                  metadata=metadata))
                cell_ids[(name.casefold(), reference)] = identity
                edges.append(Edge(sheet_id, identity, "contains_cell", f"cell {reference}"))
                if formula_node is not None:
                    unsupported = False
                    if formula_node.get("t") == "shared":
                        unsupported = True
                        diagnostics.append({"path": relative, "code": "XLSX_SHARED_FORMULA_UNSUPPORTED",
                                            "reason": f"Shared formula at {name}!{reference} is unresolved"})
                    if formula and re.search(r"\bINDIRECT\s*\(", formula, re.I):
                        unsupported = True
                        diagnostics.append({"path": relative, "code": "XLSX_INDIRECT_UNSUPPORTED",
                                            "reason": f"INDIRECT at {name}!{reference} is unresolved"})
                    if formula and "[" in formula:
                        unsupported = True
                        diagnostics.append({"path": relative, "code": "XLSX_EXTERNAL_REFERENCE_UNSUPPORTED",
                                            "reason": f"External workbook reference at {name}!{reference} is unresolved"})
                    if formula and not unsupported:
                        formula_cells.append((name, identity, formula))

        for sheet_name, source, formula in formula_cells:
            for raw_sheet, start, end, token in _references(formula):
                referenced_sheet = (raw_sheet or sheet_name).replace("''", "'")
                expanded = _range_cells(start, end)
                if not expanded:
                    diagnostics.append({"path": relative, "code": "XLSX_FORMULA_RANGE_UNSUPPORTED",
                                        "reason": f"Formula range {token} exceeds the supported bound"})
                for cell_reference in expanded:
                    target = cell_ids.get((referenced_sheet.casefold(), cell_reference.upper().replace("$", "")))
                    if target:
                        edges.append(Edge(source, target, "formula_references", token))
                    else:
                        diagnostics.append({"path": relative, "code": "XLSX_FORMULA_REFERENCE_UNRESOLVED",
                                            "reason": f"Formula reference {token} is outside extracted cells"})

        defined = workbook.find(f"{{{_MAIN}}}definedNames")
        if defined is not None:
            for item in defined.findall(f"{{{_MAIN}}}definedName"):
                name, expression = item.get("name"), item.text
                if not name or not expression:
                    continue
                identity = _identity("workbook_named_range", relative, name)
                nodes.append(Node(identity, "workbook_named_range", name, relative, summary=expression,
                                  scope=classification.scope, role=classification.role,
                                  origin=classification.origin, build_membership=classification.build_membership,
                                  classification_evidence=classification.classification_evidence,
                                  metadata={"name": name, "expression": expression, "parser": VERSION}))
                edges.append(Edge(workbook_id, identity, "defines_named_range", expression))
                if re.search(r"\b(?:INDIRECT|OFFSET)\s*\(", expression, re.I) or "[" in expression:
                    diagnostics.append({"path": relative, "code": "XLSX_DYNAMIC_NAMED_RANGE_UNSUPPORTED",
                                        "reason": f"Named range {name} uses a dynamic or external expression"})
                    continue
                for raw_sheet, start, end, token in _references(expression):
                    sheet = (raw_sheet or "").replace("''", "'")
                    for ref in _range_cells(start, end):
                        target = cell_ids.get((sheet.casefold(), ref.upper().replace("$", "")))
                        if target:
                            edges.append(Edge(identity, target, "range_contains", token))

        if external_relationships or any(name.startswith("xl/externalLinks/") for name in archive.namelist()):
            diagnostics.append({"path": relative, "code": "XLSX_EXTERNAL_LINK_UNSUPPORTED",
                                "reason": "External workbook links are recorded as unresolved and were not loaded"})

    checksum = file_hash(path)
    context = {"id": digest({"path": relative, "sha256": checksum, "parser": VERSION}),
               "mode": "WORKBOOK_OFFLINE", "scope": classification.scope, "path": relative,
               "content_hash": checksum, "parser_version": VERSION, "origin_trust": "LOCAL_SOURCE",
               "freshness": "CONTENT_VERIFIED", "coverage": "PARTIAL" if diagnostics else "SUPPORTED_MATRIX"}
    evidenced: list[Edge] = []
    for edge in edges:
        record = {"kind": "SYNTAX_CANDIDATE", "extractor": VERSION, "source_file": relative,
                  "sha256": checksum, "source": edge.source, "target": edge.target,
                  "relation": edge.kind, "locator": edge.evidence, "context_ids": [context["id"]],
                  "origin_trust": "LOCAL_SOURCE", "freshness": "CONTENT_VERIFIED"}
        evidence_id = "evidence:" + digest(record)
        evidence.append({"id": evidence_id, **record})
        evidenced.append(replace(edge, context_ids=(context["id"],), evidence_ids=(evidence_id,)))
    return nodes, evidenced, diagnostics, context, evidence


def attach_workbooks(root: Path, graph: KnowledgeGraph) -> KnowledgeGraph:
    """Attach all supported workbooks and explicit binary-XLS diagnostics."""
    root = root.resolve()
    classifier = Classifier(root)
    nodes, edges = {n.id: n for n in graph.nodes}, set(graph.edges)
    diagnostics = list(graph.diagnostics)
    contexts = list(graph.contexts)
    evidence = {item["id"]: item for item in graph.evidence}
    files = dict(graph.files)
    candidates = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()
                        and not any(part.startswith(".") or part.lower() in {
                            "node_modules", "target", "build", "dist", "out", "coverage"
                        } for part in p.relative_to(root).parts[:-1])
                        and p.suffix.lower() in {".xlsx", ".xls"})
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        unsupported = unsupported_binary(path, relative)
        if unsupported is not None:
            diagnostics.append({**unsupported, "scope": classifier.classify(relative).scope})
            files[relative] = unsupported["sha256"]
            continue
        try:
            local_nodes, local_edges, local_diagnostics, context, local_evidence = extract(path, relative, classifier)
        except AnalysisError as exc:
            checksum = file_hash(path)
            diagnostics.append({"path": relative, "code": "XLSX_PARSE_FAILED", "status": "UNSUPPORTED",
                                "scope": classifier.classify(relative).scope,
                                "sha256": checksum, "locator": {"type": "file", "path": relative},
                                "reason": str(exc)})
            files[relative] = checksum
            continue
        nodes.update({node.id: node for node in local_nodes})
        edges.update(local_edges)
        diagnostics.extend(local_diagnostics)
        contexts.append(context)
        evidence.update({item["id"]: item for item in local_evidence})
        files[relative] = file_hash(path)
    result = replace(graph, nodes=sorted(nodes.values(), key=lambda n: (n.path, n.kind, n.name)),
                     edges=sorted(edges, key=lambda e: (e.source, e.kind, e.target)), files=files,
                     contexts=contexts, diagnostics=diagnostics,
                     evidence=[evidence[key] for key in sorted(evidence)])
    KnowledgeGraph.from_dict(result.to_dict())
    return result


def locate_cell(path: Path, sheet: str, cell: str) -> dict:
    """Re-read one workbook locator for citation validation."""
    if not isinstance(sheet, str) or not sheet or not isinstance(cell, str):
        raise AnalysisError("Workbook evidence requires sheet and cell")
    normalized = cell.upper().replace("$", "")
    if not _CELL.fullmatch(normalized):
        raise AnalysisError("Invalid workbook cell locator")
    nodes, _, _, _, _ = extract(path, path.name, Classifier(path.parent))
    match = next((node for node in nodes if node.kind == "workbook_cell"
                  and node.metadata and node.metadata.get("sheet") == sheet
                  and node.metadata.get("cell") == normalized), None)
    if match is None:
        raise AnalysisError("Workbook cell locator does not exist")
    metadata = match.metadata or {}
    return {"formula": metadata.get("formula"), "cached_value": metadata.get("cached_value"),
            "cached_value_freshness": metadata.get("cached_value_freshness")}

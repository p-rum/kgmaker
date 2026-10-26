"""T001 FA-22/23 workbook extraction and evidence acceptance."""
import copy
import zipfile
from pathlib import Path

import pytest

from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA
from kgmaker.data_check import data_check


WORKBOOK = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Scenario" sheetId="1" r:id="rId1"/></sheets>
 <definedNames><definedName name="Input">Scenario!$A$1</definedName></definedNames>
</workbook>"""
RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
SHEET = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
 <row r="1"><c r="A1"><v>10</v></c></row>
 <row r="2"><c r="A2"><f>A1*2</f><v>20</v></c></row>
 <row r="3"><c r="A3"><f t="shared" si="0">A1+1</f><v>11</v></c></row>
 <row r="4"><c r="A4"><f>INDIRECT(&quot;A1&quot;)</f><v>10</v></c></row>
 <row r="5"><c r="A5"><f>[other.xlsx]Sheet1!A1</f><v>99</v></c></row>
</sheetData></worksheet>"""


def write_xlsx(path: Path, *, target: str = "worksheets/sheet1.xml") -> None:
    rels = RELS.replace('worksheets/sheet1.xml', target)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", SHEET)
        archive.writestr("xl/externalLinks/externalLink1.xml", "<externalLink/>")


def test_fa22_extracts_cells_formula_dependencies_named_ranges_and_cache(tmp_path):
    write_xlsx(tmp_path / "scenarios.xlsx")
    graph = feature.current_graph(tmp_path)[0]
    nodes = {node.id: node for node in graph.nodes}
    a1 = "workbook_cell:scenarios.xlsx:Scenario!A1"
    a2 = "workbook_cell:scenarios.xlsx:Scenario!A2"
    assert nodes[a2].metadata["formula"] == "A1*2"
    assert nodes[a2].metadata["cached_value"] == "20"
    assert nodes[a2].metadata["cached_value_freshness"] == "UNKNOWN"
    assert any(edge.source == a2 and edge.target == a1 and edge.kind == "formula_references"
               for edge in graph.edges)
    assert any(node.kind == "workbook_named_range" and node.name == "Input" for node in graph.nodes)
    assert any(context.get("mode") == "WORKBOOK_OFFLINE" for context in graph.contexts)


def test_fa23_reports_shared_indirect_external_and_binary_xls(tmp_path):
    write_xlsx(tmp_path / "scenarios.xlsx")
    (tmp_path / "legacy.xls").write_bytes(b"binary workbook")
    graph = feature.current_graph(tmp_path)[0]
    codes = {item["code"] for item in graph.diagnostics}
    assert {"XLSX_SHARED_FORMULA_UNSUPPORTED", "XLSX_INDIRECT_UNSUPPORTED",
            "XLSX_EXTERNAL_REFERENCE_UNSUPPORTED", "XLSX_EXTERNAL_LINK_UNSUPPORTED",
            "BINARY_XLS_UNSUPPORTED"} <= codes
    (tmp_path / "requirement.md").write_text("Use the scenario input.")
    packet = feature.prepare(tmp_path, "requirement.md", "workbook", 100_000)
    assert packet["coverage"]["parser_capabilities"]["workbooks"] == "xlsx-offline-2"
    assert "legacy.xls" in packet["coverage"]["unsupported_sources"]
    assert "scenarios.xlsx" not in packet["coverage"]["unsupported_sources"]


def test_data_check_uses_hash_bound_workbook_cell_locator(tmp_path):
    write_xlsx(tmp_path / "scenarios.xlsx")
    (tmp_path / "requirement.md").write_text("Use the scenario input.")
    packet = feature.prepare(tmp_path, "requirement.md", "workbook", 100_000)
    requirement_id = "analysis:workbook:requirement:scenario"
    cell_id = "workbook_cell:scenarios.xlsx:Scenario!A1"
    spec = {
        "schema_version": 1, "analysis_id": "workbook",
        "requirement_hash": packet["requirement_hash"],
        "requirements": [{"id": requirement_id, "text": "Use scenario input",
                          "kind": "InputRequirement", "source_quote": "scenario input"}],
        "inputs": [{"id": "analysis:workbook:input:scenario", "name": "scenario input",
                    "requirement_ids": [requirement_id], "candidate_entity_ids": [cell_id],
                    **{key: None for key in INPUT_METADATA}}],
    }
    result = data_check(tmp_path, "workbook", spec)
    assert result["valid"]
    evidence = next(item for item in result["candidate"]["evidence"]
                    if item.get("source_id") == cell_id)
    assert evidence["kind"] == "WORKBOOK"
    assert evidence["location"] == {"type": "workbook_cell", "sheet": "Scenario", "cell": "A1"}
    assert evidence["value"] == {"formula": None, "cached_value": "10",
                                  "cached_value_freshness": "UNKNOWN"}
    assert feature.validate(tmp_path, "workbook", result["candidate"])["valid"]
    forged = copy.deepcopy(result["candidate"])
    next(item for item in forged["evidence"] if item.get("source_id") == cell_id)["value"]["cached_value"] = "11"
    assert feature.validate(tmp_path, "workbook", forged)["exit_code"] == 2


def test_unsafe_relationship_and_archive_limit_fail_closed(tmp_path, monkeypatch):
    write_xlsx(tmp_path / "unsafe.xlsx", target="../../../outside.xml")
    graph = feature.current_graph(tmp_path)[0]
    assert any(item["code"] == "XLSX_PARSE_FAILED" and "escapes" in item["reason"]
               for item in graph.diagnostics)
    monkeypatch.setattr("kgmaker.workbooks.MAX_ENTRIES", 2)
    graph = feature.current_graph(tmp_path)[0]
    assert any(item["code"] == "XLSX_PARSE_FAILED" and "entries" in item["reason"]
               for item in graph.diagnostics)

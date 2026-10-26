"""T003-S09-W01: actual ZIP inputs, exact static tokens, explicit boundaries."""
import copy
import json
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import pytest

from kgmaker import feature
from kgmaker.analysis_model import INPUT_METADATA
from kgmaker.data_check import data_check
from kgmaker.store import save_graph

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def write_formula_book(path: Path, formulas: dict, *, defined_name=None):
    workbook = ET.Element(f"{{{MAIN}}}workbook")
    sheets = ET.SubElement(workbook, f"{{{MAIN}}}sheets")
    ET.SubElement(sheets, f"{{{MAIN}}}sheet", name="Scenario", sheetId="1", **{f"{{{REL}}}id": "rId1"})
    if defined_name is not None:
        names = ET.SubElement(workbook, f"{{{MAIN}}}definedNames")
        ET.SubElement(names, f"{{{MAIN}}}definedName", name="Input").text = defined_name
    relationships = ET.Element(f"{{{PKG}}}Relationships")
    ET.SubElement(relationships, f"{{{PKG}}}Relationship", Id="rId1", Type=REL + "/worksheet", Target="worksheets/sheet1.xml")
    sheet = ET.Element(f"{{{MAIN}}}worksheet")
    data = ET.SubElement(sheet, f"{{{MAIN}}}sheetData")
    # LOG10 and E10 are real cells: a false lexical match would create an edge.
    rows = {}
    for number, address in enumerate(("A1", "B1", "C1", "E10", "LOG10", *formulas), 1):
        row = "".join(character for character in address if character.isdigit())
        rows.setdefault(int(row), []).append((address, number))
    for row, entries in sorted(rows.items()):
        row_node = ET.SubElement(data, f"{{{MAIN}}}row", r=str(row))
        for address, number in sorted(entries):
            cell = ET.SubElement(row_node, f"{{{MAIN}}}c", r=address)
            if address in formulas:
                formula, attributes = formulas[address] if isinstance(formulas[address], tuple) else (formulas[address], {})
                ET.SubElement(cell, f"{{{MAIN}}}f", **attributes).text = formula
            ET.SubElement(cell, f"{{{MAIN}}}v").text = str(number)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                         '<Default Extension="xml" ContentType="application/xml"/>'
                         '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                         '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr("_rels/.rels", f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", ET.tostring(workbook))
        archive.writestr("xl/_rels/workbook.xml.rels", ET.tostring(relationships))
        archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(sheet))


@pytest.mark.parametrize("formula,expected", [
    ("1E10", set()), ("1e-10", set()), (".1E+10", set()),
    ("A1+1E10", {"A1"}), ("LOG10(A1)", {"A1"}),
    ("LOG10 (A1)", {"A1"}), ("SUM($A$1:$B$1)", {"A1", "B1"}),
    ("'Scenario'!$A$1:$B$1", {"A1", "B1"}),
    ("_xlfn.LOG10(A1)", {"A1"}), ("E10_rate", set()),
    ('IF(A1="OFFSET(""A1"")",B1,C1)', {"A1", "B1", "C1"}),
    ('"[external.xlsx]Sheet1!A1 INDIRECT("', set()),
])
def test_formula_tokens_do_not_invent_cell_dependencies(tmp_path, formula, expected):
    write_formula_book(tmp_path / "scenario.xlsx", {"A2": formula})
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")), \
            patch("socket.socket.connect", side_effect=AssertionError("external access")):
        graph = feature.current_graph(tmp_path)[0]
    references = [edge for edge in graph.edges if edge.kind == "formula_references"]
    assert {edge.target.rsplit("!", 1)[-1] for edge in references} == expected
    assert not graph.diagnostics
    assert all(node.metadata["cached_value_freshness"] == "UNKNOWN"
               for node in graph.nodes if node.kind == "workbook_cell")


@pytest.mark.parametrize("formula,code", [
    ("OFFSET(A1,0,1)", "XLSX_OFFSET_UNSUPPORTED"),
    ('INDIRECT("A1")', "XLSX_INDIRECT_UNSUPPORTED"),
    ("[other.xlsx]Scenario!A1", "XLSX_EXTERNAL_REFERENCE_UNSUPPORTED"),
    ("SUM(Scenario:Other!A1)", "XLSX_REFERENCE_FORM_UNSUPPORTED"),
    ("SUM('Scenario:Other'!A1)", "XLSX_REFERENCE_FORM_UNSUPPORTED"),
    ("SUM(A:A)", "XLSX_REFERENCE_FORM_UNSUPPORTED"),
    ("SUM(1:10)", "XLSX_REFERENCE_FORM_UNSUPPORTED"),
    (("A1+1", {"t": "shared", "si": "0"}), "XLSX_SHARED_FORMULA_UNSUPPORTED"),
    ((None, {"t": "shared", "si": "0"}), "XLSX_SHARED_FORMULA_UNSUPPORTED"),
])
def test_unsupported_formula_forms_are_boundaries(tmp_path, formula, code):
    write_formula_book(tmp_path / "scenario.xlsx", {"A2": formula})
    graph = feature.current_graph(tmp_path)[0]
    diagnostic, = graph.diagnostics
    assert diagnostic["code"] == code
    assert "Scenario!A2" in diagnostic["reason"]
    assert not [edge for edge in graph.edges if edge.kind == "formula_references"]
    assert next(context for context in graph.contexts if context.get("mode") == "WORKBOOK_OFFLINE")["coverage"] == "PARTIAL"


def test_named_range_tokens_and_dynamic_boundary_use_same_rules(tmp_path):
    path = tmp_path / "scenario.xlsx"
    write_formula_book(path, {}, defined_name="LOG10(Scenario!A1)+1E10")
    graph = feature.current_graph(tmp_path)[0]
    assert {edge.target.rsplit("!", 1)[-1] for edge in graph.edges if edge.kind == "range_contains"} == {"A1"}
    write_formula_book(path, {}, defined_name="OFFSET(Scenario!A1,0,1)")
    graph = feature.current_graph(tmp_path)[0]
    assert any(item["code"] == "XLSX_DYNAMIC_NAMED_RANGE_UNSUPPORTED" for item in graph.diagnostics)
    assert not [edge for edge in graph.edges if edge.kind == "range_contains"]


def test_dynamic_audit_stays_unknown_and_forged_locator_preserves_store(tmp_path):
    write_formula_book(tmp_path / "scenario.xlsx", {"A2": "OFFSET(A1,0,1)"})
    (tmp_path / "requirement.md").write_text("Use the scenario amount.")
    save_graph(feature.current_graph(tmp_path)[0], tmp_path)
    packet = feature.prepare(tmp_path, "requirement.md", "scenario", 100_000)
    requirement_id = "analysis:scenario:requirement:amount"
    specification = {"schema_version": 1, "analysis_id": "scenario", "requirement_hash": packet["requirement_hash"],
                     "requirements": [{"id": requirement_id, "text": "Use scenario amount", "kind": "InputRequirement", "source_quote": "scenario amount"}],
                     "inputs": [{"id": "analysis:scenario:input:amount", "name": "amount", "requirement_ids": [requirement_id],
                                 "candidate_entity_ids": ["workbook_cell:scenario.xlsx:Scenario!A2"],
                                 **{key: None for key in INPUT_METADATA}}]}
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    real_popen = subprocess.Popen
    def git_baseline_only(argv, *args, **kwargs):
        assert argv == ["git", "-C", str(tmp_path), "rev-parse", "HEAD"]
        return real_popen(argv, *args, **kwargs)
    with patch("subprocess.Popen", side_effect=git_baseline_only):
        result = data_check(tmp_path, "scenario", specification)
    assert result["valid"]
    assert result["candidate"]["input_requirements"][0]["availability"] == "UNKNOWN"
    assert not result["data_delivery_gaps"]
    for field, value in (("sheet", "Missing"), ("cell", "Z999")):
        forged = copy.deepcopy(result["candidate"])
        next(item for item in forged["evidence"] if item["kind"] == "WORKBOOK")["location"][field] = value
        assert not feature.validate(tmp_path, "scenario", forged)["valid"]
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_workspace_does_not_reuse_dependencies_from_old_workbook_parser(tmp_path):
    from kgmaker import workbooks
    from kgmaker.workspace import snapshot_workspace
    repository = tmp_path / "repo"
    repository.mkdir()
    write_formula_book(repository / "scenario.xlsx", {"A2": "1E10"})
    manifest = tmp_path / "workspace.json"
    manifest.write_text(json.dumps({"schema_version": 1, "workspace_id": "formula",
                                    "repositories": [{"id": "repo", "path": "repo", "role": "shared"}]}))
    # Reproduce a real v1 parser result in its versioned cache generation.
    with patch.object(workbooks, "VERSION", "xlsx-offline-1"), \
            patch.object(feature, "WORKBOOK_VERSION", "xlsx-offline-1"), \
            patch.object(workbooks, "_references", return_value=[(None, "E10", None, "E10")]):
        old = snapshot_workspace(manifest, cache_root=tmp_path, persist_cache=True)
    assert any(edge.kind == "formula_references" for edge in old[3].edges)
    current = snapshot_workspace(manifest, cache_root=tmp_path)
    assert not [edge for edge in current[3].edges if edge.kind == "formula_references"]
    assert old[0]["repositories"]["repo"]["cache_key"] != current[0]["repositories"]["repo"]["cache_key"]

import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from kgmaker.analysis_model import AnalysisError, canonical, digest
from kgmaker.excel import inventory, jira, plan
from kgmaker.excel.source import preflight, worker_command
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "excel-migration"


def write_json(path, value):
    path.write_text(canonical(value), encoding="utf-8")
    return path


def cli(tmp_path, *args, env=None, executable=None):
    if executable is None:
        executable = [sys.executable, "-m", "kgmaker.cli"]
        env = {**(os.environ if env is None else env), "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([*executable, "excel", *map(str, args)], cwd=tmp_path, env=env,
                          capture_output=True, encoding="utf-8", check=False)


def config(main="migration.xlsm", dependency="Rates.xlsx", *, linked=True):
    entries = [{"id": "invoice", "path": main}]
    if dependency:
        entries.append({"id": "rates", "path": dependency})
    links = [{"from": "invoice", "reference": "Rates.xlsx", "to": "rates"}] if dependency and linked else []
    return {"schema_version": 1, "main": "invoice", "workbooks": entries, "links": links}


@pytest.fixture
def actual_worker():
    try:
        worker_command()
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_EXCEL_WORKER"):
            pytest.fail(str(error))
        pytest.skip(str(error))


@pytest.fixture
def sample(tmp_path):
    for name in ("migration.xlsm", "Rates.xlsx"):
        shutil.copyfile(FIXTURES / name, tmp_path / name)
    return write_json(tmp_path / "manifest.json", config())


def evidence_at(value, kind, **fields):
    results = [row for row in value["evidence"]
               if row["kind"] == kind and all(row["locator"].get(k) == v for k, v in fields.items())]
    assert len(results) == 1, results
    return results[0]


def edge_sources(value, source, role, target):
    edges = [row for row in value["relations"]
             if (row["source"], row["kind"], row["target"]) == (source["id"], role, target["id"])]
    assert len(edges) == 1, (source, role, target)
    all_evidence = {row["id"]: row for row in value["evidence"]}
    return [all_evidence[key] for key in edges[0]["evidence"]]


def test_real_multi_workbook_evidence_and_data_stays_local(tmp_path, sample, actual_worker):
    digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.iterdir()}
    result = cli(tmp_path, "analyze", "--manifest", sample, "--out", "inventory.json")
    assert result.returncode == 0, result.stderr
    observed = plan.load_inventory(tmp_path / "inventory.json")
    assert observed["status"] == "ANALYZED"
    event = evidence_at(observed, "entrypoint", event="Workbook_Open")
    handler = evidence_at(observed, "vba-procedure", procedure="Workbook_Open")
    macro = evidence_at(observed, "vba-procedure", procedure="RecalculateInvoice")
    sheet_event = evidence_at(observed, "entrypoint", event="Worksheet_Change")
    change_handler = evidence_at(observed, "vba-procedure", procedure="Worksheet_Change")
    control = evidence_at(observed, "entrypoint", control="rId1/1")
    input_cell = evidence_at(observed, "cell", workbook="invoice", cell="A1")
    output = evidence_at(observed, "cell", workbook="invoice", cell="B1")
    workbook_formula = evidence_at(observed, "cell", workbook="invoice", cell="D1")
    udf_formula = evidence_at(observed, "cell", workbook="invoice", cell="C1")
    udf = evidence_at(observed, "vba-procedure", procedure="RoundExtra")
    rates = evidence_at(observed, "cell", workbook="rates", cell="B2")
    assert rates["value"] == 0.25
    assert output["cached_freshness"] == "UNKNOWN"
    assert evidence_at(observed, "sheet", sheet="Sheet3")["visibility"] == "VERY_HIDDEN"
    edge_sources(observed, event, "calls", handler)
    edge_sources(observed, sheet_event, "calls", change_handler)
    edge_sources(observed, handler, "calls", macro)
    edge_sources(observed, control, "calls", macro)
    assert edge_sources(observed, macro, "writes", input_cell)[0]["locator"]["line"] == 3
    edge_sources(observed, macro, "reads", rates)
    edge_sources(observed, workbook_formula, "reads", rates)
    edge_sources(observed, output, "reads", input_cell)
    edge_sources(observed, udf_formula, "calls", udf)
    edge_sources(observed, evidence_at(observed, "defined-name", name="InvoiceTotal"), "reads", output)
    scoped = cli(tmp_path, "behavior", "--inventory", "inventory.json", "--sheet", "Sheet1")
    assert scoped.returncode == 0, scoped.stderr
    report_entries = scoped.stdout.split("## Entry points", 1)[1].split("## Declared data sources", 1)[0]
    assert "Worksheet_Change" in report_entries and "Workbook_Open" not in report_entries

    base = cli(tmp_path, "packet", "--inventory", "inventory.json", "--entity", macro["id"])
    assert base.returncode == 0, base.stderr
    assert all("source" not in row and "value" not in row and "formula" not in row
               for row in json.loads(base.stdout)["evidence"])
    explicit = cli(tmp_path, "packet", "--inventory", "inventory.json", "--entity", macro["id"],
                   "--include-source", "--budget", "8000")
    assert explicit.returncode == 0 and len(explicit.stdout.encode("utf-8")) <= 8000
    assert any("Workbooks(\"Rates.xlsx\")" in row.get("source", "")
               for row in json.loads(explicit.stdout)["evidence"])
    assert {key: hashlib.sha256((tmp_path / key).read_bytes()).hexdigest() for key in digests} == digests
    assert not (tmp_path / ".kgmaker").exists()


def test_real_biff8_vba_and_no_dynamic_address_guess(tmp_path, actual_worker):
    shutil.copyfile(FIXTURES / "legacy.xls", tmp_path / "legacy.xls")
    manifest = write_json(tmp_path / "app.json", config("legacy.xls", None))
    observed = inventory.analyze(manifest)
    macro = evidence_at(observed, "vba-procedure", procedure="TestMacro")
    assert macro["id"] in {row["id"] for row in observed["subjects"]}
    assert observed["status"] == "PARTIAL"
    assert any(row.get("code") == "VBA_DYNAMIC_RANGE" for row in observed["evidence"])
    assert not any(row["source"] == macro["id"] and row["kind"] == "writes"
                   for row in observed["relations"])


@pytest.mark.parametrize(("name", "data", "code"), [
    ("legacy.xlsx", "legacy.xls", "EXCEL_FORMAT_MISMATCH"),
    ("encrypted.xlsx", "encrypted.xlsx", "EXCEL_ENCRYPTED"),
    ("old.xls", "../workbooks/legacy-biff2.xls", "EXCEL_BIFF_UNSUPPORTED"),
    ("broken.xlsm", None, "EXCEL_FORMAT_MISMATCH"),
    ("binary.xlsb", None, "EXCEL_FORMAT_UNSUPPORTED"),
])
def test_native_negative_cases_preserve_previous_output(tmp_path, actual_worker, name, data, code):
    target = tmp_path / name
    if data:
        shutil.copyfile(FIXTURES / data, target)
    else:
        target.write_bytes(b"not an Excel workbook")
    manifest = write_json(tmp_path / "app.json", config(name, None))
    previous = tmp_path / "inventory.json"
    previous.write_bytes(b"last good output")
    result = cli(tmp_path, "analyze", "--manifest", manifest, "--out", previous)
    assert result.returncode == 2, result.stderr
    assert code in result.stderr
    assert previous.read_bytes() == b"last good output"


def test_archive_budget_and_xml_decl_fail_closed(tmp_path, monkeypatch):
    archive = tmp_path / "test.xlsx"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("xl/workbook.xml", "<!DOCTYPE x [<!ENTITY data SYSTEM 'https://example.invalid'>]><x/>")
    assert preflight(archive, "xlsx") == "EXCEL_UNSAFE_XML"
    monkeypatch.setattr("kgmaker.excel.source.MAX_XML_BYTES", 2)
    assert preflight(archive, "xlsx") == "EXCEL_ARCHIVE_LIMIT"


def _write_currency_workbook(path):
    spreadsheet = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    packaging = "http://schemas.openxmlformats.org/package/2006"
    currency = {
        "CNB": 'WEBSERVICE("https://cnb.example.invalid/rates")',
        "ECB": None,
        "Provider": 'WEBSERVICE("https://provider.example.invalid/rates")',
        "ParseCNB": 'VALUE(FILTERXML(CNB!A1,"//rate"))',
        "ParseECB": "SUM(ECB!A2:A2)",
        "ParseProvider": 'VALUE(FILTERXML(Provider!A1,"//rate"))',
        "Selected": "IFERROR(ParseCNB!A1,ParseECB!A1)",
        "CrossRate": "Selected!A1/ParseProvider!A1",
        "Amount": None,
        "Converted": "Amount!A1*CrossRate!A1",
        "Fee": "Converted!A1*0.015",
        "Total": "Converted!A1+Fee!A1",
        "Rounded": "ROUND(Total!A1,2)",
        "Audit": "IF(CrossRate!A1>0,Total!A1,0)",
        "Display": "Rounded!A1",
    }
    types, sheets, relations = [], [], []

    def part_type(name, kind):
        types.append(f'<Override PartName="/{name}" ContentType="application/vnd.openxmlformats-officedocument.'
                     f'spreadsheetml.{kind}+xml"/>')

    def relation(kind, target, index=1):
        return f'<Relationship Id="rId{index}" Type="{office}/{kind}" Target="{target}"/>'

    def rels(*items):
        return f'<Relationships xmlns="{packaging}/relationships">{"".join(items)}</Relationships>'

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zip:
        part_type("xl/workbook.xml", "sheet.main")
        zip.writestr("_rels/.rels", rels(relation("officeDocument", "xl/workbook.xml")))
        for index, (name, formula) in enumerate(currency.items(), 1):
            filename = f"worksheets/sheet{index}.xml"
            part_type(f"xl/{filename}", "worksheet")
            sheets.append(f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>')
            relations.append(relation("worksheet", filename, index))
            table = ''
            if name == "ECB":
                data = ('<row r="1"><c r="A1" t="inlineStr"><is><t>Rate</t></is></c></row>'
                        '<row r="2"><c r="A2"><v>23.719</v></c></row>')
                table = '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
                zip.writestr(f"xl/worksheets/_rels/sheet{index}.xml.rels",
                             rels(relation("table", "../tables/table1.xml")))
            elif name == "Amount":
                data = '<row r="1"><c r="A1"><v>12345.6789</v></c></row>'
            else:
                rows = range(1, 101) if name == "Audit" else (1,)
                data = "".join(f'<row r="{row}"><c r="A{row}"><f>{escape(formula)}</f></c></row>' for row in rows)
            zip.writestr(f"xl/{filename}", f'<worksheet xmlns="{spreadsheet}" xmlns:r="{office}">'
                         f'<sheetData>{data}</sheetData>{table}</worksheet>')
        zip.writestr("xl/workbook.xml", f'<workbook xmlns="{spreadsheet}" xmlns:r="{office}">'
                     f'<sheets>{"".join(sheets)}</sheets></workbook>')
        zip.writestr("xl/_rels/workbook.xml.rels", rels(*relations, relation("connections", "connections.xml", 16)))
        part_type("xl/connections.xml", "connections")
        part_type("xl/tables/table1.xml", "table")
        part_type("xl/queryTables/queryTable1.xml", "queryTable")
        zip.writestr("xl/connections.xml", f'<connections xmlns="{spreadsheet}">'
                     '<connection id="1" name="Example ECB" type="4">'
                     '<webPr url="https://ecb.example.invalid/rates"/></connection></connections>')
        zip.writestr("xl/tables/table1.xml", f'<table xmlns="{spreadsheet}" id="1" name="DailyRates" '
                     'displayName="DailyRates" ref="A1:A2" tableType="queryTable">'
                     '<tableColumns count="1"><tableColumn id="1" name="Rate"/></tableColumns></table>')
        zip.writestr("xl/tables/_rels/table1.xml.rels", rels(relation("queryTable", "../queryTables/queryTable1.xml")))
        zip.writestr("xl/queryTables/queryTable1.xml", f'<queryTable xmlns="{spreadsheet}" connectionId="1" '
                     'name="DailyRates"/>')
        zip.writestr("[Content_Types].xml", f'<Types xmlns="{packaging}/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     f'{"".join(types)}</Types>')


def test_currency_behavior_reports_three_sources_across_fifteen_sheets(tmp_path, actual_worker):
    workbook = tmp_path / "Synthetic rates.xlsx"
    _write_currency_workbook(workbook)
    original = workbook.read_bytes()
    bundle = tmp_path / "bundle"
    result = cli(tmp_path, "migrate", "prepare", "--workbook", workbook, "--out-dir", bundle)
    assert result.returncode == 0, result.stderr
    assert workbook.read_bytes() == original
    observed = plan.load_inventory(bundle / "inventory.json")
    assert len(observed["relations"]) > 200
    assert evidence_at(observed, "address", sheet="ECB", range="A2:A2")
    names = {item["reference"]: item["id"] for item in observed["evidence"] if item["kind"] == "external-source"}
    assert len(names) == 3
    report = (bundle / "behavior.md").read_text(encoding="utf-8")
    assert "15 sheets" in report
    assert "Declared query-table binding" in report
    assert "Conditional result** · IFERROR" in report
    assert "division" in report and "multiplication" in report
    assert "https://" not in report and "12345.6789" not in report and "IFERROR(" not in report
    display_routes = [line for line in report.splitlines() if "source-to-output" in line and "Display / A1" in line]
    assert len(display_routes) == 3, report
    assert all(any(key in route and "CrossRate / A1" in route for route in display_routes) for key in names.values())
    full = cli(tmp_path, "behavior", "--inventory", bundle / "inventory.json", "--include-source")
    assert full.returncode == 0, full.stderr
    assert all(url in full.stdout for url in names)
    assert "IFERROR(ParseCNB!A1,ParseECB!A1)" in full.stdout and "12345.6789" in full.stdout
    assert full.stdout.index("## Calculations") < full.stdout.index("## Limits")
    scoped = cli(tmp_path, "behavior", "--inventory", bundle / "inventory.json", "--book", "main", "--sheet", "Display")
    assert scoped.returncode == 0, scoped.stderr
    assert sum("source-to-output" in line for line in scoped.stdout.splitlines()) == 3
    assert "Formula in source** · ` main / Display / A1 " in scoped.stdout
    assert "Formula in source** · ` main / CrossRate / A1 " in scoped.stdout
    assert "Conditional result** · IFERROR" in scoped.stdout
    assert "Formula in source** · ` main / Audit" not in scoped.stdout
    legacy = {**observed, "worker": "excel-poi-6.0.0-2"}
    legacy["inventory_id"] = digest({key: val for key, val in legacy.items() if key != "inventory_id"})
    assert plan.load_inventory(write_json(tmp_path / "legacy-inventory.json", legacy)) == legacy


def test_query_destination_connects_to_formula_read_without_cell_evidence(tmp_path):
    from kgmaker.excel import behavior
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    builder.register(selection.books[0], "test-sha", 0, {
        "links": {}, "builtin_functions": [],
        "sheets": [{"name": "Sheet1", "visibility": "VISIBLE"}],
        "cells": [{"sheet": "Sheet1", "cell": "B1", "type": "FORMULA", "formula": "=A2"}],
        "names": [], "tables": [],
        "connections": [{"part": "xl/connections.xml", "id": "1", "index": 1,
                         "mechanism": "ODBC", "reference": "rates"}],
        "query_tables": [{"part": "xl/queryTables/queryTable1.xml", "sheet": "Sheet1",
                          "id": "1", "range": "A2:A2"}],
        "modules": [],
    }, [])

    value = builder.document()
    report = behavior.markdown(value, sheet="Sheet1")

    assert not any(row["kind"] == "cell" and row["locator"].get("cell") == "A2"
                   for row in value["evidence"])
    paths = [line for line in report.splitlines() if "source-to-output path" in line]
    source = next(row for row in value["evidence"] if row["kind"] == "external-source")
    assert any(source["id"] in path and "Sheet1 / B1" in path for path in paths), report


def test_unmapped_and_missing_book_are_explicit(tmp_path, sample, actual_worker):
    write_json(sample, config(linked=False))
    observed = inventory.analyze(sample)
    assert observed["status"] == "PARTIAL"
    assert any(row.get("code") == "EXCEL_EXTERNAL_WORKBOOK" for row in observed["evidence"])
    assert not any(row["source"] == evidence_at(observed, "cell", cell="D1")["id"]
                   and row["target"] == evidence_at(observed, "cell", workbook="rates", cell="B2")["id"]
                   for row in observed["relations"])
    (tmp_path / "Rates.xlsx").unlink()
    observed = inventory.analyze(sample)
    assert observed["status"] == "PARTIAL"
    assert any(row.get("code") == "EXCEL_WORKBOOK_MISSING" for row in observed["evidence"])


def test_missing_toolchain_has_no_side_effect(tmp_path, sample, monkeypatch):
    monkeypatch.setattr("kgmaker.excel.source.shutil.which", lambda _: None)
    with pytest.raises(WorkerError, match=r"requires Java 17\+"):
        inventory.analyze(sample)
    assert not (tmp_path / "inventory.json").exists()


def candidate(value):
    template = plan.candidate_template(value)
    subjects = [row["id"] for row in value["subjects"]]
    task = {
        **template["tasks"][0],
        "id": "rates-port", "title": 'Načíst sazby, měny a "stavy"',
        "target": "RateSource", "implementation": "Načíst sazbu B2 přes explicitní port.\nOšetřit neplatný vstup.",
        "acceptance": ["Sazba 0,25 je potvrzena ve zkušebním scénáři."],
        "tests": ["Syntetická sazba s prázdným a neplatným vstupem."],
        "citations": [subjects[0]],
        "jira_fields": {"components": ["Kotlin", "Migrace"], "team": "Spojky"},
    }
    calc = {
        **task, "id": "invoice-rules", "title": "Převést pravidla faktury", "target": "InvoiceCalculation",
        "implementation": "Převést Sheet1 do čisté funkce a naplánovat porovnání všech výstupů.",
        "citations": subjects, "covers": subjects, "depends_on": ["rates-port"],
    }
    return {**template, "title": "Převést aplikaci", "tasks": [calc, task]}


def test_plan_exports_real_jira_fields_and_keeps_csv_on_errors(tmp_path, sample, actual_worker):
    inv_path = tmp_path / "inventory.json"
    value = inventory.analyze(sample)
    write_json(inv_path, value)
    proposal = candidate(value)
    # Accompanying migration tests depend on the same prerequisite.
    proposal["tasks"].append({**proposal["tasks"][1], "id": "parity", "kind": "verification",
                              "depends_on": ["rates-port"], "title": "Ověřit shodu"})
    candidate_path = write_json(tmp_path / "candidate.json", proposal)
    args = ["--manifest", sample, "--inventory", inv_path, "--candidate", candidate_path]
    assert cli(tmp_path, "plan", "validate", *args).returncode == 0
    profile = {
        **jira.DEFAULT,
        "fields": [*jira.DEFAULT["fields"],
                   {"field": "Component/s", "source": "jira_fields.components", "type": "multi-select"},
                   {"field": "Delivery team", "source": "jira_fields.team", "type": "select",
                    "required": True, "allowed_values": ["Spojky", "Integrace"]}],
    }
    profile_path = write_json(tmp_path / "jira.json", profile)
    export_args = [*args, "--format", "jira-csv", "--jira-template", profile_path, "--out", "jira.csv"]
    result = cli(tmp_path, "plan", "export", *export_args)
    assert result.returncode == 0, result.stderr
    raw = (tmp_path / "jira.csv").read_bytes()
    lines = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline="")))
    headings, epic, rates, invoice, checks = lines
    assert headings == ["Summary", "Description", "Work Type", "Work item ID", "Parent",
                        "Blocks", "Blocks", "Labels", "Component/s", "Component/s", "Delivery team"]
    assert epic[2:5] == ["Epic", "1", ""]
    assert rates[0] == 'Načíst sazby, měny a "stavy"'
    assert "Ošetřit neplatný vstup.\n" in rates[1]
    assert rates[2:7] == ["Task", "2", "1", invoice[3], checks[3]]
    assert rates[-3:] == ["Kotlin", "Migrace", "Spojky"]
    assert json.loads(result.stdout)["mapping"][5]["jira_field"] == "blocks (outward link)"
    assert cli(tmp_path, "plan", "export", *args, "--out", "plan.md").returncode == 0
    assert "Kotlin/JVM architecture" in (tmp_path / "plan.md").read_text(encoding="utf-8")

    proposal["tasks"][1]["jira_fields"]["team"] = "Neschválený"
    write_json(candidate_path, proposal)
    result = cli(tmp_path, "plan", "export", *export_args)
    assert result.returncode == 2 and "rates-port Jira field Delivery team" in result.stderr
    assert (tmp_path / "jira.csv").read_bytes() == raw

    (tmp_path / "Rates.xlsx").write_bytes(b"same output remains")
    result = cli(tmp_path, "plan", "export", *export_args)
    assert result.returncode == 2 and "inventory is stale" in result.stderr
    assert (tmp_path / "jira.csv").read_bytes() == raw


def test_plan_rejects_forged_citation_missing_subject_and_cycle(sample, actual_worker):
    value = inventory.analyze(sample)
    design = candidate(value)
    design["tasks"][0]["citations"].append("forged-citation")
    with pytest.raises(AnalysisError, match="Unknown evidence citation"):
        plan.validate(value, design)
    design = candidate(value)
    design["tasks"][0]["covers"].pop()
    with pytest.raises(AnalysisError, match="Uncovered inventory subjects"):
        plan.validate(value, design)
    design = candidate(value)
    design["tasks"][1]["depends_on"] = ["invoice-rules"]
    with pytest.raises(AnalysisError, match="contain a cycle"):
        plan.validate(value, design)


@pytest.mark.skipif(not os.environ.get("KGMAKER_REQUIRE_EXCEL_WHEEL"), reason="explicit wheel smoke")
def test_installed_worker_wheel(tmp_path, sample, actual_worker):
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    source = tmp_path / "source checkout"
    workers = source / "workers"
    workers.mkdir(parents=True)
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copyfile(ROOT / name, source / name)
    shutil.copytree(ROOT / "src", source / "src",
                    ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copyfile(ROOT / "workers" / "__init__.py", workers / "__init__.py")
    shutil.copytree(ROOT / "workers" / "excel", workers / "excel",
                    ignore=shutil.ignore_patterns("classes", "maven-*", "__pycache__"))
    command = [sys.executable, "-m", "pip", "wheel", "--no-index", "--no-deps",
               "--no-build-isolation", "--wheel-dir", str(wheel_dir), str(source)]
    subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    venv = tmp_path / "wheel space"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], cwd=tmp_path, check=True)
    runtime = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    wheel, = wheel_dir.glob("*.whl")
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTHONPATH", "KGMAKER_WORKERS_HOME"}}
    subprocess.run([str(runtime), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
                   cwd=tmp_path, env=env, check=True, capture_output=True)
    result = cli(tmp_path, "analyze", "--manifest", sample, "--out", "from-wheel.json",
                 env=env, executable=[str(runtime), "-m", "kgmaker.cli"])
    assert result.returncode == 0, result.stderr
    assert evidence_at(plan.load_inventory(tmp_path / "from-wheel.json"), "entrypoint", event="Workbook_Open")


def _register_source(builder, book, *, source, formulas=(), names=(), builtins=()):
    builder.register(book, "test-sha", 0, {
        "links": {}, "builtin_functions": list(builtins),
        "sheets": [{"name": "Sheet1", "visibility": "VISIBLE"}],
        "cells": [{"sheet": "Sheet1", "cell": f"B{row}", "type": "FORMULA", "formula": formula}
                  for row, formula in enumerate(formulas, 1)],
        "names": list(names), "tables": [],
        "modules": [{"name": "Module1", "type": "Module", "source": source}],
    }, [])


def test_vba_behavior_tracks_http_response_calculation_and_alternative_assignments(tmp_path):
    from kgmaker.excel import behavior
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = '''Public Sub Fetch()
    Dim http As Object, rate As Double, endpoint As String
    endpoint = "https://cnb.example.invalid/rates"
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", endpoint, False
    http.Send
    rate = CDbl(http.ResponseText)
    total = rate * 100
    ThisWorkbook.Worksheets("Sheet1").Range("C1").Value = total
    RateLabel.Caption = Format(total, "0.0000")
    Set http = customObject
    http.Open "GET", "https://not-an-http-client.example.invalid/"
End Sub
Public Sub ChooseRate(ByVal usePrimary As Boolean)
    If usePrimary Then
        rate = 101.25
    Else
        rate = 201.50
    End If
    MsgBox rate
End Sub
Public Sub PublishDynamic(ByVal rowNumber As Long)
    ThisWorkbook.Worksheets("Sheet1").Cells(rowNumber, 2).Value = 2 * rowNumber
End Sub'''
    _register_source(builder, selection.books[0], source=source)
    value = builder.document()
    url = evidence_at(value, "external-source", procedure="Fetch", line=5)
    assert url["reference"] == "https://cnb.example.invalid/rates"
    assert len([item for item in value["evidence"] if item["kind"] == "external-source"]) == 1
    response = evidence_at(value, "vba-operation", procedure="Fetch", line=7)
    write = evidence_at(value, "vba-operation", procedure="Fetch", line=9)
    edge_sources(value, response, "source", url)
    edge_sources(value, write, "writes", evidence_at(value, "address", range="C1"))
    message = evidence_at(value, "vba-operation", procedure="ChooseRate", line=20)
    assert len(message["alternatives"]["rate"]) == 2
    report = behavior.markdown(value)
    assert "Alternative definitions" in report and "Display property write" in report
    assert any("source-to-output" in line and url["id"] in line and "line 10" in line
               for line in report.splitlines())
    assert "101.25" not in report and "ResponseText" not in report and "https://" not in report
    full = behavior.markdown(value, include_source=True)
    assert "CDbl(http.ResponseText)" in full and "total = rate * 100" in full
    assert "101.25" in full and "201.50" in full
    assert ".Cells(rowNumber, 2).Value = 2 * rowNumber" in full
    dynamic = evidence_at(value, "vba-operation", procedure="PublishDynamic")
    assert not any(edge["source"] == dynamic["id"] and edge["kind"] == "writes" for edge in value["relations"])
    redacted = plan.packet(value)
    assert any(row["kind"] == "vba-operation" for row in redacted["evidence"])
    assert not any(set(row) & plan.SOURCE_FIELDS for row in redacted["evidence"])


def test_vba_function_lineage_follows_returns_instead_of_unrelated_effects(tmp_path):
    from kgmaker.excel import behavior
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = '''Public Function Fixed()
    Set client = CreateObject("MSXML2.XMLHTTP")
    client.Open "GET", "https://fixed.example.invalid/"
    client.Send
    unrelated = client.ResponseText
    Fixed = CDbl(unrelated)
    Fixed = 42
End Function
Public Function FixedAfterBranch()
    Set client = CreateObject("MSXML2.XMLHTTP")
    client.Open "GET", "https://branch.example.invalid/"
    client.Send
    FixedAfterBranch = CDbl(client.ResponseText)
    If flag Then
        unrelated = True
    End If
    FixedAfterBranch = 42
End Function
Public Function Quote()
    Set client = CreateObject("MSXML2.XMLHTTP")
    client.Open "GET", "https://quote.example.invalid/"
    client.Send
    Quote = CDbl(client.ResponseText)
End Function
Public Function Adjusted()
    Adjusted = Quote() * 2
End Function'''
    _register_source(builder, selection.books[0], source=source,
                     formulas=("Fixed()", "Adjusted()", "FixedAfterBranch()"))
    value = builder.document()
    report = behavior.markdown(value)
    paths = [line for line in report.splitlines() if "source-to-output path" in line]
    assert len(paths) == 1, report
    assert "Sheet1 / B2" in paths[0] and "Adjusted" in paths[0] and "Quote" in paths[0]
    assert "Fixed" not in paths[0] and "Sheet1 / B1" not in paths[0]


def test_vba_non_mutating_intrinsic_preserves_definition_for_later_write(tmp_path):
    from kgmaker.excel import behavior
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = '''Public Sub Fetch()
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", "https://rates.example.invalid/"
    http.Send
    rate = CDbl(http.ResponseText)
    Format(rate, "0.00")
    ThisWorkbook.Worksheets("Sheet1").Range("A1").Value = rate
End Sub'''
    _register_source(builder, selection.books[0], source=source)

    value = builder.document()
    report = behavior.markdown(value, sheet="Sheet1")
    source = evidence_at(value, "external-source", procedure="Fetch", line=3)
    paths = [line for line in report.splitlines() if "source-to-output path" in line]
    assert any(source["id"] in path and "line 7" in path for path in paths), report


def test_vba_keeps_endpoint_unresolved_after_opaque_call(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = '''Public Sub Refresh()
    Dim endpoint As String
    endpoint = "https://stale.example.invalid/"
    Set client = CreateObject("MSXML2.XMLHTTP")
    Call RewriteUrl(endpoint)
    observed = endpoint
    client.Open "GET", endpoint
    client.Send
End Sub
Public Sub RewriteUrl(ByRef address As String)
    address = "https://replacement.example.invalid/"
End Sub'''
    _register_source(builder, selection.books[0], source=source)
    value = builder.document()
    request = evidence_at(value, "external-source", procedure="Refresh", line=7)
    assert request["method"] == "GET" and request["reference"] is None
    observed = evidence_at(value, "vba-operation", procedure="Refresh", line=6)
    assert not any(edge["source"] == observed["id"] and edge["kind"] == "depends-on" for edge in value["relations"])


def test_vba_read_does_not_inherit_a_later_http_write_to_the_same_cell(tmp_path):
    from kgmaker.excel import behavior
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = '''Public Sub Sequence()
    ThisWorkbook.Worksheets("Sheet1").Range("A1").Value = 0
    copied = ThisWorkbook.Worksheets("Sheet1").Range("A1").Value
    ThisWorkbook.Worksheets("Sheet1").Range("B1").Value = copied
    Set client = CreateObject("MSXML2.XMLHTTP")
    client.Open "GET", "https://rates.example.invalid/"
    client.Send
    ThisWorkbook.Worksheets("Sheet1").Range("A1").Value = client.ResponseText
End Sub'''
    _register_source(builder, selection.books[0], source=source)
    report = behavior.markdown(builder.document(), sheet="Sheet1")
    paths = [line for line in report.splitlines() if "source-to-output path" in line]
    assert any("Sheet1 / A1" in path for path in paths), report
    assert all("Sheet1 / B1" not in path for path in paths)
    assert "VBA read stops at the observed cell or range" in report


def test_vba_run_resolves_only_complete_literal_arguments(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config()))
    builder = inventory.Inventory(selection)
    source = '\n'.join([
        'Public Sub Main()',
        '    Application.Run "Rates.xlsx!Forecast" & suffix',
        '    Application.Run ("Rates.xlsx!Forecast") & suffix',
        '    result = Application.Run("Rates.xlsx!Forecast", 42)',
        '    Run "Rates.xlsx!Forecast"',
        '    Call Application.Run("Rates.xlsx!Forecast")',
        '    MsgBox "Application.Run ""Rates.xlsx!Forecast"""',
        'End Sub',
    ])
    _register_source(builder, selection.books[0], source=source)
    _register_source(builder, selection.books[1], source="Public Sub Forecast()\nEnd Sub")
    result = builder.document()
    caller = evidence_at(result, "vba-procedure", procedure="Main")
    callee = evidence_at(result, "vba-procedure", procedure="Forecast")
    witnesses = edge_sources(result, caller, "calls", callee)
    assert {row["locator"]["line"] for row in witnesses} == {4, 5, 6}
    gaps = [row["locator"]["line"] for row in result["evidence"]
            if row["kind"] == "gap" and row.get("code") == "VBA_DYNAMIC_DISPATCH"]
    assert set(gaps) == {2, 3}


def test_formula_binding_distinguishes_excel_builtins_and_lexical_names(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    _register_source(builder, selection.books[0], builtins=["SUM"],
                     source="Public Function Sum()\nEnd Function\nPublic Function RoundExtra()\nEnd Function",
                     formulas=["SUM(A1:A2)", "LET(Rate,2,Rate+1)", "_xlfn.LAMBDA(Rate,Rate+1)(2)",
                               "RoundExtra(A1)", '"LET(Rate,2,Rate+1)"&Rate'],
                     names=[{"name": "Rate", "formula": "0.25"}])
    result = builder.document()
    excel_sum = evidence_at(result, "cell", cell="B1")
    sum_arg = evidence_at(result, "address", range="A1:A2")
    edge_sources(result, excel_sum, "reads", sum_arg)
    udf = evidence_at(result, "vba-procedure", procedure="RoundExtra")
    edge_sources(result, evidence_at(result, "cell", cell="B4"), "calls", udf)
    scoped_cells = {evidence_at(result, "cell", cell=cell)["id"] for cell in ("B2", "B3")}
    assert not any(edge["source"] in scoped_cells or
                   (edge["source"] == excel_sum["id"] and edge["kind"] == "calls")
                   for edge in result["relations"])
    assert {row["locator"]["cell"] for row in result["evidence"]
            if row["kind"] == "gap" and row.get("code") == "EXCEL_FORMULA_SCOPE_UNSUPPORTED"} == {"B2", "B3"}
    rate = evidence_at(result, "defined-name", name="Rate")
    edge_sources(result, evidence_at(result, "cell", cell="B5"), "reads", rate)


def test_repeated_vba_witnesses_round_trip_inventory(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    source = "Sub Main()\n" + "Call Target\n" * 1_001 + "End Sub\nSub Target()\nEnd Sub"
    _register_source(builder, selection.books[0], source=source)
    value = builder.document()
    read_back = plan.load_inventory(write_json(tmp_path / "inventory.json", value))
    source = evidence_at(read_back, "vba-procedure", procedure="Main")
    target = evidence_at(read_back, "vba-procedure", procedure="Target")
    assert len(edge_sources(read_back, source, "calls", target)) == 1_001


def test_vba_range_alias_is_a_gap_and_never_a_value_read(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    _register_source(builder, selection.books[0], source="""
Sub Main()
    Dim target As Range
    Set target = ThisWorkbook.Worksheets("Sheet1").Range("A1")
    target.Value2 = 2
    ThisWorkbook.Worksheets("Sheet1").Range("A2") = 3
    result = ThisWorkbook.Worksheets("Sheet1").Range("A3").Value2
End Sub
""".strip())
    result = builder.document()
    macro = evidence_at(result, "vba-procedure", procedure="Main")
    assert result["status"] == "PARTIAL"
    assert any(row.get("code") == "VBA_RANGE_OBJECT_UNRESOLVED" and row["locator"]["line"] == 3
               for row in result["evidence"])
    assert not any(row["kind"] == "address" and row["locator"]["range"] == "A1"
                   for row in result["evidence"])
    edge_sources(result, macro, "writes", evidence_at(result, "address", range="A2"))
    edge_sources(result, macro, "reads", evidence_at(result, "address", range="A3"))


def test_vba_run_respects_the_project_scope(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config()))
    builder = inventory.Inventory(selection)
    _register_source(builder, selection.books[0], source="""
Sub Main()
    Run "Rates.xlsx!Forecast"
    Call Run("Rates.xlsx!Forecast")
    Application.Run "Rates.xlsx!Forecast"
End Sub
Private Sub Run(ByVal x As String)
End Sub
Sub Shadowed()
    Dim Run As Object
    Run "Rates.xlsx!Forecast"
End Sub
""".strip())
    _register_source(builder, selection.books[1], source="Public Sub Forecast()\nEnd Sub")
    value = builder.document()
    main = evidence_at(value, "vba-procedure", procedure="Main")
    local_run = evidence_at(value, "vba-procedure", procedure="Run")
    forecast = evidence_at(value, "vba-procedure", procedure="Forecast")
    shadowed = evidence_at(value, "vba-procedure", procedure="Shadowed")
    assert {row["locator"]["line"] for row in edge_sources(value, main, "calls", local_run)} == {2, 3}
    assert {row["locator"]["line"] for row in edge_sources(value, main, "calls", forecast)} == {4}
    assert not any(edge["source"] == shadowed["id"] for edge in value["relations"])
    assert any(row.get("code") == "VBA_DYNAMIC_DISPATCH" and row["locator"]["line"] == 10
               for row in value["evidence"])


def test_distinct_unicode_sheet_spellings_keep_cells_and_name_scopes_separate(tmp_path):
    from kgmaker.excel.source import manifest

    selection = manifest(write_json(tmp_path / "app.json", config(dependency=None)))
    builder = inventory.Inventory(selection)
    builder.register(selection.books[0], "test-sha", 0, {
        "links": {}, "builtin_functions": [],
        "sheets": [{"name": name, "visibility": "VISIBLE", "code_name": code}
                   for name, code in [("Straße", "Straße"), ("Strasse", "Strasse"), ("Output", "Sheet3")]],
        "cells": [
            {"sheet": "Straße", "cell": "A1", "type": "NUMERIC", "value": 3},
            {"sheet": "Strasse", "cell": "A1", "type": "NUMERIC", "value": 9},
            {"sheet": "Output", "cell": "B1", "type": "FORMULA", "formula": "'Straße'!A1*2"},
            {"sheet": "Output", "cell": "B2", "type": "FORMULA", "formula": "'straße'!A1*2"},
            {"sheet": "Output", "cell": "B3", "type": "FORMULA", "formula": "output!B1"},
            {"sheet": "Strasse", "cell": "B1", "type": "FORMULA", "formula": "Rate*2"},
            {"sheet": "Straße", "cell": "B1", "type": "FORMULA", "formula": "Rate*2"},
        ],
        "names": [{"sheet": "Strasse", "name": "Rate", "formula": "0.25"}],
        "tables": [],
        "modules": [{"name": "Straße", "type": "Document",
                     "source": 'Sub Worksheet_Change()\nMe.Range("A1").Value2 = 5\nEnd Sub'}],
    }, [])
    value = builder.document()
    right_cell = evidence_at(value, "cell", sheet="Straße", cell="A1")
    formula_cell = evidence_at(value, "cell", sheet="Output", cell="B1")
    edge_sources(value, formula_cell, "reads", right_cell)
    edge_sources(value, evidence_at(value, "cell", sheet="Output", cell="B3"), "reads", formula_cell)
    assert right_cell["value"] == 3
    unresolved = evidence_at(value, "cell", sheet="Output", cell="B2")
    assert not any(edge["source"] == unresolved["id"] for edge in value["relations"])
    scoped_rate = evidence_at(value, "defined-name", sheet="Strasse", name="Rate")
    edge_sources(value, evidence_at(value, "cell", sheet="Strasse", cell="B1"), "reads", scoped_rate)
    other_sheet = evidence_at(value, "cell", sheet="Straße", cell="B1")
    assert not any(edge["source"] == other_sheet["id"] for edge in value["relations"])
    assert not any(row["kind"] == "entrypoint" for row in value["evidence"])
    codes = {row["code"] for row in value["evidence"] if row["kind"] == "gap"}
    assert codes == {"VBA_EVENT_BINDING_UNRESOLVED", "VBA_RANGE_UNRESOLVED",
                     "EXCEL_FORMULA_TARGET_UNRESOLVED"}


def test_copilot_migration_bundle_from_workbooks_produces_validated_jira_csv(
        tmp_path, sample, actual_worker):
    output = tmp_path / "excel migration"
    sources = ["--workbook", "migration.xlsm", "--dependency", "Rates.xlsx", "--out-dir", output]
    original = {file: (tmp_path / file).read_bytes() for file in ("migration.xlsm", "Rates.xlsx")}
    result = cli(tmp_path, "migrate", "prepare", *sources)
    assert result.returncode == 0, result.stderr
    assert not (output / "candidate.json").exists()
    value = plan.load_inventory(output / "inventory.json")
    packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
    assert packet["template"]["inventory_id"] == value["inventory_id"]
    assert packet["status"] == "ANALYZED"
    assert all(not {"source", "formula", "value", "cached_value"} & row.keys()
               for row in packet["evidence"])
    subjects = [json.loads(line) for line in (output / "subjects.jsonl").read_text().splitlines()]
    assert subjects == value["subjects"]
    formula = evidence_at(value, "cell", workbook="main", cell="D1")
    rate = evidence_at(value, "cell", workbook="dependency-1", cell="B2")
    edge_sources(value, formula, "reads", rate)
    assert cli(tmp_path, "migrate", "prepare", *sources).returncode == 2

    proposal = candidate(value)
    write_json(output / "candidate.json", {**proposal, "tasks": []})
    failed = cli(tmp_path, "migrate", "export", *sources)
    assert failed.returncode == 2 and not (output / "result").exists()
    write_json(output / "candidate.json", proposal)

    profile = write_json(tmp_path / "project-jira.json", {**jira.DEFAULT, "fields": [{
        "field": "Delivery team", "type": "select", "source": "jira_fields.team",
        "allowed_values": ["Spojky"], "required": True,
    }]})
    result = cli(tmp_path, "migrate", "export", *sources, "--jira-template", profile)
    assert result.returncode == 0, result.stderr
    bundle = output / "result"
    csv_path = bundle / "migration.csv"
    previous = csv_path.read_bytes()
    rows = list(csv.reader(io.StringIO(previous.decode("utf-8"), newline="")))
    assert rows[0][-1] == "Delivery team"
    assert [row[2] for row in rows[1:]] == ["Epic", "Task", "Task"]
    assert "Kotlin/JVM architecture" in (bundle / "migration.md").read_text(encoding="utf-8")
    mapping = json.loads((bundle / "jira-mapping.json").read_text())
    assert mapping["mapping"][-1]["jira_field"] == "Delivery team"
    assert cli(tmp_path, "migrate", "export", *sources).returncode == 2
    assert csv_path.read_bytes() == previous
    assert all((tmp_path / file).read_bytes() == data for file, data in original.items())


def test_copilot_migration_bundle_rejects_changed_manifest_or_workbook(tmp_path, sample, actual_worker):
    output = tmp_path / "bundle"
    args = ["--manifest", sample, "--out-dir", output]
    result = cli(tmp_path, "migrate", "prepare", *args, "--include-source")
    assert result.returncode == 0, result.stderr
    packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
    assert any("Workbook_Open" in row.get("source", "") for row in packet["evidence"])
    value = plan.load_inventory(output / "inventory.json")
    write_json(output / "candidate.json", candidate(value))
    (tmp_path / "Rates.xlsx").write_bytes(b"changed")
    result = cli(tmp_path, "migrate", "export", *args)
    assert result.returncode == 2 and "inventory is stale" in result.stderr
    assert not (output / "result").exists()


def test_direct_workbook_selection_only_maps_unique_exact_basenames(tmp_path):
    from kgmaker.excel.source import workbook_selection

    main, one, two, unique = [tmp_path / file for file in
                              ("main.xlsm", "a/Rates.xlsx", "b/rates.xlsx", "c/Lookup.xlsx")]
    for path in (main, one, two, unique):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not analyzed in this test")
    selection = workbook_selection(main, [one, two, unique])
    assert selection.links["main", "Lookup.xlsx"] == "dependency-3"
    assert ("main", "Rates.xlsx") not in selection.links
    assert ("main", "rates.xlsx") not in selection.links
    assert ("main", "c/Lookup.xlsx") not in selection.links
    assert workbook_selection(main, [unique, one, two]).sha256 == selection.sha256


@pytest.mark.parametrize(("replacement", "changed_inputs"), [
    (None, True), ("directory", True), ("file", True), ("directory", False),
])
def test_migration_bundle_rollback_only_removes_owned_paths(tmp_path, replacement, changed_inputs):
    from kgmaker.excel.migration import _write_bundle

    parent = tmp_path / "out"
    parent.mkdir()
    bundle = parent / "bundle"
    other = tmp_path / "other"
    (other / "bundle").mkdir(parents=True)
    (other / "bundle/migration.md").write_text("unrelated", encoding="utf-8")

    def check():
        output = bundle / "migration.md"
        if not output.exists():
            return
        if replacement == "directory":
            parent.rename(tmp_path / "moved")
            other.rename(parent)
        elif replacement == "file":
            output.rename(tmp_path / "moved.md")
            output.write_text("unrelated", encoding="utf-8")
        if changed_inputs:
            raise AnalysisError("inputs changed during publication")

    reason = "inputs changed" if changed_inputs else "output changed"
    with pytest.raises(AnalysisError, match=reason):
        _write_bundle(bundle, {"migration.md": "ours"}, check)
    if replacement == "directory":
        assert (tmp_path / "moved/bundle/migration.md").read_text(encoding="utf-8") == "ours"
    elif replacement == "file":
        assert (tmp_path / "moved.md").read_text(encoding="utf-8") == "ours"
    if replacement:
        assert (bundle / "migration.md").read_text(encoding="utf-8") == "unrelated"
    else:
        assert not bundle.exists()

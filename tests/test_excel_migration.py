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

import pytest

from kgmaker.analysis_model import AnalysisError, canonical
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

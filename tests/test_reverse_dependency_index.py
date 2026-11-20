import hashlib
import json
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from kgmaker import feature, workspace
from kgmaker.analysis_model import AnalysisError, inventory_candidate, read_json, write_json
from kgmaker.cli import main, scan
from kgmaker.graph_provider import dependency_impact
from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.store import GRAPH_FILE, save_graph
from kgmaker.worker_protocol import WorkerError


def _write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _store_bytes(root):
    return {path.relative_to(root): path.read_bytes()
            for path in (root / ".kgmaker").rglob("*") if path.is_file()}


def _require_javac_worker():
    try:
        command("jvm")
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            raise
        pytest.skip(str(error))


def test_actual_javac_signature_change_reaches_transitive_callers_without_workers(tmp_path):
    _require_javac_worker()
    src = "app/src/main/java/"
    target = _write(tmp_path, src + "Api.java", "class Api { static int value(int x) { return x; } }")
    _write(tmp_path, src + "Middle.java", """class Middle {
        static int helper() { return Api.value(1); }
        static int pass() { return helper(); }
        static int separate() { return 1; }
    }""")
    _write(tmp_path, src + "Caller.java", "class Caller { static int call() { return Middle.pass(); } }")
    _write(tmp_path, src + "Reference.java",
           "class Reference { static java.util.function.IntUnaryOperator bind() { return Api::value; } }")
    _write(tmp_path, src + "Independent.java",
           "class Independent { static int value(int x) { return x + Middle.separate(); } }")
    outside = "service/src/main/java/Other.java"
    _write(tmp_path, outside,
           "class Api { static int value(int x) { return x; } } class Other { int run() { return Api.value(1); } }")
    inputs = [p.relative_to(tmp_path).as_posix() for p in (tmp_path / src).glob("*.java")]
    model = {"source_sets": [{"module": module, "id": "main", "scope": "production", "files": files}
                             for module, files in (("app", inputs), ("service", [outside]))]}
    inspection = inspect_jvm(tmp_path, module="app", sources=inputs, project_model=model)
    assert inspection["exit_code"] == 0
    independent = inspect_jvm(tmp_path, module="service", sources=[outside], project_model=model)
    assert independent["exit_code"] == 0 and independent["context"]["id"] != inspection["context"]["id"]
    expected_store = _store_bytes(tmp_path)
    target.write_text("class Api { static int value(String x) { return x.length(); } }", encoding="utf-8")

    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        report = dependency_impact(tmp_path, [src + "Api.java"])
    assert report["coverage"] == "PARTIAL"
    assert report["graph_sha256"] == hashlib.sha256(expected_store[GRAPH_FILE]).hexdigest()
    assert [row["path"] for row in report["changed_sources"]] == [src + "Api.java"]
    affected = report["affected"]
    assert sorted(item["path"] for item in affected) == [src + name for name in (
        "Caller.java", "Middle.java", "Middle.java", "Reference.java",
    )]
    def dependency(path, source):
        return next(item for item in affected if item["path"] == src + path
                    and item["reasons"][0]["dependency_path"] == src + source)

    caller = dependency("Caller.java", "Middle.java")
    helper = dependency("Middle.java", "Api.java")
    local_pass = dependency("Middle.java", "Middle.java")
    reference = dependency("Reference.java", "Api.java")
    assert caller["reasons"][0]["dependency_id"] == local_pass["id"]
    assert local_pass["reasons"][0]["dependency_id"] == helper["id"]
    assert reference["reasons"][0]["relation"] == "declares_reference"
    assert all(item["kind"] == "COMPILER_CALLER" and item["status"] == "RECHECK" for item in affected)
    assert all(len(reason["evidence_ids"]) == 2 and reason["call_site_id"]
               for item in affected for reason in item["reasons"])
    assert _store_bytes(tmp_path) == expected_store


def test_replayed_schema_and_openapi_citation_invalidate_only_proven_dependents(tmp_path, monkeypatch, capsys):
    migrations = "src/main/resources/db/migration/"
    base = _write(tmp_path, migrations + "V1__customers.sql", "CREATE TABLE customer (balance INTEGER);")
    _write(tmp_path, migrations + "V2__independent.sql", "CREATE TABLE other (balance INTEGER);")
    _write(tmp_path, migrations + "R__views.sql", "CREATE OR REPLACE VIEW balances AS SELECT balance FROM customer;")
    _write(tmp_path, "requirement.md", "Validate the published API contract.")
    api = _write(tmp_path, "openapi.json", json.dumps({
        "openapi": "3.0.3", "paths": {"/balance": {"get": {"operationId": "getBalance"}}},
    }))
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "requirement.md", "contracts")
    candidate = inventory_candidate(packet)
    evidence_id = "analysis:contracts:evidence:get"
    conclusion = "analysis:contracts:test:read"
    candidate["evidence"] = [{"id": evidence_id, "source_id": "openapi.json", "kind": "CONTRACT",
                              "path": "openapi.json", "sha256": packet["source_manifest"]["openapi.json"]["sha256"],
                              "location": {"type": "json_pointer", "pointer": "/paths/~1balance/get/operationId"},
                              "value": "getBalance", "supports": "Declared operation name.", "method": "EXTRACTED",
                              "confidence": 1, "validity": "VALID"}]
    candidate["test_plan"] = [{"id": conclusion, "text": "Check the declared operation.", "state": "TO_BE",
                               "requirement_ids": [candidate["requirements"][0]["id"]],
                               "entity_ids": [], "evidence_ids": [evidence_id]}]
    assert feature.apply(tmp_path, "contracts", candidate)["valid"]
    base.write_text("CREATE TABLE customer (balance BIGINT);", encoding="utf-8")
    api.write_text(api.read_text(encoding="utf-8").replace("getBalance", "fetchBalance"), encoding="utf-8")
    # A newly prepared revision leaves the previously applied revision and its receipt readable.
    assert feature.prepare(tmp_path, "requirement.md", "contracts")["revision"] == 2
    expected_store = _store_bytes(tmp_path)

    capsys.readouterr()
    monkeypatch.setattr("sys.argv", ["kgmaker", "impact", "--root", str(tmp_path), "--evidence-only",
                                   "--format", "json", migrations + "V1__customers.sql", "openapi.json"])
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")), pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert [row["path"] for row in report["changed_sources"]] == [
        "openapi.json", migrations + "V1__customers.sql",
    ]
    assert {item["kind"] for item in report["affected"]} == {
        "CONTRACT_DECLARATION", "SCHEMA_DEPENDENT", "FEATURE_CONCLUSION",
    }
    schema = next(item for item in report["affected"] if item["kind"] == "SCHEMA_DEPENDENT")
    assert schema["path"] == migrations + "R__views.sql"
    assert schema["reasons"][0]["evidence_kind"] == "MIGRATION_DERIVED"
    stale = next(item for item in report["affected"] if item["kind"] == "FEATURE_CONCLUSION")
    assert stale["id"] == conclusion and stale["status"] == "STALE"
    assert stale["reasons"][0]["revision"] == 1
    assert stale["reasons"][0]["evidence_id"] == evidence_id
    assert _store_bytes(tmp_path) == expected_store
    assert dependency_impact(tmp_path, ["openapi.json", migrations + "V1__customers.sql"]) == report

    # The citation can no longer be trusted when the applied payload and receipt differ.
    applied = tmp_path / ".kgmaker/analyses/contracts/analysis.json"
    tampered = read_json(applied)
    tampered["test_plan"][0]["text"] = "Unrecorded conclusion"
    write_json(applied, tampered)
    expected_store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert [item["kind"] for item in report["affected"]] == ["CONTRACT_DECLARATION"]
    assert {"code": "FEATURE_REVISION_UNAVAILABLE", "analysis_id": "contracts"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == expected_store


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_and_unproven_name_matches_never_gain_positive_evidence(tmp_path, version):
    from kgmaker.analysis_model import file_hash

    target = _write(tmp_path, "target.py", "def target(): pass")
    _write(tmp_path, "caller.py", "def caller(): target()")
    graph = KnowledgeGraph(version, ".", "", [
        Node("caller", "file", "caller.py", "caller.py"),
        Node("target", "function", "target", "target.py"),
    ], [Edge("caller", "target", "calls", confidence="INFERRED")],
        {"target.py": file_hash(target), "caller.py": file_hash(tmp_path / "caller.py")})
    save_graph(graph, tmp_path, generate_docs=False)
    if version == 2:
        generated = read_json(tmp_path / GRAPH_FILE)
        generated.update(symbols=[{"id": ["not-a-v2-field"]}], call_sites=["not-a-v2-field"])
        write_json(tmp_path / GRAPH_FILE, generated)
    target.unlink()
    store = (tmp_path / GRAPH_FILE).read_bytes()
    report = dependency_impact(tmp_path, ["target.py", "new.py"])
    assert report["changed_sources"] == [{"path": "target.py", "before_sha256": graph.files["target.py"],
                                          "after_sha256": None}]
    assert not report["affected"]
    assert {"code": "DEPENDENCY_PATH_NOT_CAPTURED", "path": "new.py"} in report["diagnostics"]
    assert (tmp_path / GRAPH_FILE).read_bytes() == store


def test_invalid_graph_and_nonregular_changed_source_leave_store_untouched(tmp_path):
    _write(tmp_path, "openapi.json", '{"openapi":"3.0.3","paths":{"/items":{"get":{}}}}')
    assert scan(tmp_path, generate_docs=False) == 0
    target = tmp_path / "openapi.json"
    target.unlink()
    target.mkdir()
    store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert not report["affected"] and not report["changed_sources"]
    assert {"code": "DEPENDENCY_PATH_UNAVAILABLE", "path": "openapi.json"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store

    (tmp_path / GRAPH_FILE).write_text("[]", encoding="utf-8")
    store = _store_bytes(tmp_path)
    with pytest.raises(AnalysisError, match="No readable graph found"):
        dependency_impact(tmp_path, ["openapi.json"])
    assert _store_bytes(tmp_path) == store


def test_malformed_stored_compiler_graph_keys_fail_closed_in_public_cli(tmp_path):
    _require_javac_worker()
    dependency = "src/main/java/Api.java"
    target = _write(tmp_path, dependency, "class Api { static int value(int x) { return x; } }")
    _write(tmp_path, "src/main/java/Caller.java", "class Caller { int run() { return Api.value(1); } }")
    assert inspect_jvm(tmp_path)["exit_code"] == 0
    stored = tmp_path / GRAPH_FILE
    original = stored.read_bytes()
    target.write_text("class Api { static int value(String x) { return x.length(); } }", encoding="utf-8")

    for collection, field in (("edges", "source_file"), ("edges", "kind"),
                              ("nodes", "path"), ("nodes", "kind")):
        graph = json.loads(original)
        assert graph["schema_version"] == 3
        edge = next(item for item in graph["edges"] if item["kind"] == "declares_call"
                    and item["evidence_kind"] == "SYMBOL_RESOLVED")
        record = edge if collection == "edges" else next(node for node in graph["nodes"] if node["id"] == edge["source"])
        record[field] = [record[field]]
        stored.write_text(json.dumps(graph), encoding="utf-8")
        before = _store_bytes(tmp_path)
        result = subprocess.run([sys.executable, "-m", "kgmaker", "impact", "--root", str(tmp_path),
                                 "--evidence-only", "--format", "json", dependency],
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 1 and not result.stdout
        assert result.stderr.startswith("No readable graph found.") and "Traceback" not in result.stderr
        assert _store_bytes(tmp_path) == before


@pytest.mark.skipif(not all(hasattr(os, name) for name in ("mkfifo", "O_NONBLOCK")), reason="FIFO input requires POSIX")
def test_changed_source_swapped_to_fifo_is_unavailable(tmp_path, monkeypatch):
    target = _write(tmp_path, "openapi.json", '{"openapi":"3.0.3","paths":{"/items":{"get":{}}}}')
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    open_file = os.open

    def replace_before_open(path, flags, *args, **kwargs):
        if path == target:
            target.unlink()
            os.mkfifo(target)
            # Prove the race is covered without performing a blocking open on regression.
            assert flags & os.O_NONBLOCK
        return open_file(path, flags, *args, **kwargs)

    monkeypatch.setattr(workspace.os, "open", replace_before_open)
    report = dependency_impact(tmp_path, ["openapi.json"])
    assert report["coverage"] == "PARTIAL" and not report["changed_sources"] and not report["affected"]
    assert {"code": "DEPENDENCY_PATH_UNAVAILABLE", "path": "openapi.json"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO input requires POSIX")
@pytest.mark.parametrize("record", ["analysis.json", "receipts/1.json", "packet.json", "history/packet-1.json"])
def test_feature_record_fifos_do_not_block_or_publish(tmp_path, record):
    requirement = _write(tmp_path, "requirement.md", "Record current feature evidence.")
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "requirement.md", "record")
    assert feature.apply(tmp_path, "record", inventory_candidate(packet))["valid"]
    requirement.write_text("Change current feature evidence.", encoding="utf-8")
    if record.startswith("history/"):
        assert feature.prepare(tmp_path, "requirement.md", "record")["revision"] == 2
    target = tmp_path / ".kgmaker/analyses/record" / record
    target.unlink()
    os.mkfifo(target)
    store = _store_bytes(tmp_path)
    result = subprocess.run([sys.executable, "-m", "kgmaker", "impact", "--root", str(tmp_path),
                             "--evidence-only", "--format", "json", "requirement.md"],
                            capture_output=True, text=True, timeout=3, check=True)
    report = json.loads(result.stdout)
    assert report["coverage"] == "PARTIAL" and not report["affected"]
    assert [item["path"] for item in report["changed_sources"]] == ["requirement.md"]
    assert {"code": "FEATURE_REVISION_UNAVAILABLE", "analysis_id": "record"} in report["diagnostics"]
    assert _store_bytes(tmp_path) == store
    assert not target.is_file()

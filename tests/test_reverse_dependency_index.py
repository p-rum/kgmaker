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
    api = tmp_path / "openapi.json"
    original_api = json.dumps({
        "openapi": "3.0.3", "paths": {"/balance": {"get": {"operationId": "getBalance"}}},
    }, indent=2).replace("\n", "\r\n").encode("utf-8")
    api.write_bytes(original_api)
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
    api.write_bytes(original_api.replace(b"getBalance", b"fetchBalance"))
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
    assert stale["reasons"][0]["before_sha256"] == hashlib.sha256(original_api).hexdigest()
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


def test_schema_dependency_follows_prior_migration_operations(tmp_path):
    migrations = "src/main/resources/db/migration/"
    created = _write(tmp_path, migrations + "V1__customers.sql", "CREATE TABLE customer (balance INTEGER);")
    altered = _write(tmp_path, migrations + "V2__default.sql", "ALTER TABLE customer ALTER COLUMN balance SET DEFAULT 0;")
    other = _write(tmp_path, migrations + "V3__other.sql", "CREATE TABLE other (balance INTEGER);")
    _write(tmp_path, migrations + "R__views.sql",
           "CREATE VIEW balances AS SELECT balance FROM customer;")
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    created.write_text("CREATE TABLE customer (balance BIGINT);", encoding="utf-8")
    altered.write_text("ALTER TABLE customer ALTER COLUMN balance SET DEFAULT 1;", encoding="utf-8")
    other.write_text("CREATE TABLE other (balance BIGINT);", encoding="utf-8")
    paths = [path.relative_to(tmp_path).as_posix() for path in (created, altered, other)]

    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        report = dependency_impact(tmp_path, paths)
    assert report["coverage"] == "PARTIAL"
    assert len(report["affected"]) == 1
    dependent = report["affected"][0]
    assert (dependent["kind"], dependent["status"], dependent["path"]) == (
        "SCHEMA_DEPENDENT", "RECHECK", migrations + "R__views.sql",
    )
    assert {reason["dependency_path"] for reason in dependent["reasons"]} == set(paths[:2])
    assert all(reason["operation_id"] and reason["operation_line"] == 1 for reason in dependent["reasons"])
    assert _store_bytes(tmp_path) == store

    # A malformed earlier operation cannot stand in for the saved replay trace.
    stored = read_json(tmp_path / GRAPH_FILE)
    target_id = dependent["reasons"][0]["dependency_id"]
    operation = next(edge for edge in stored["edges"] if edge["kind"] == "operation_targets"
                     and edge["target"] == target_id and edge["source_file"] == paths[0])
    operation["source_line"] += 1
    write_json(tmp_path / GRAPH_FILE, stored)
    store = _store_bytes(tmp_path)
    report = dependency_impact(tmp_path, paths)
    assert [reason["dependency_path"] for item in report["affected"] for reason in item["reasons"]] == [paths[1]]
    assert _store_bytes(tmp_path) == store


@pytest.mark.parametrize("changed_path", ["req/requirement.md", "context.md"])
def test_applied_feature_dependency_requires_a_file_authority(tmp_path, changed_path):
    requirement_path = "req/requirement.md"
    _write(tmp_path, requirement_path, "Review the input definition.")
    _write(tmp_path, "context.md", "Context supplied alongside the decision.")
    assert scan(tmp_path, generate_docs=False) == 0
    packet = feature.prepare(tmp_path, "./req//requirement.md", "proof")
    candidate = inventory_candidate(packet)
    requirement_id = candidate["requirements"][0]["id"]
    question = {"id": "analysis:proof:question:definition", "text": "How should input be defined?",
                "status": "OPEN", "blocking": True, "owner_role": "Business",
                "requirement_ids": [requirement_id]}
    candidate["questions"] = [question]
    assert feature.apply(tmp_path, "proof", candidate)["valid"]
    answer = {"question_id": question["id"], "decision_id": "definition", "answer": "User-supplied definition",
              "revision": 1, "approval_status": "APPROVED"}
    packet = feature.revise(tmp_path, "proof", {"answers": [answer]})
    assert packet["requirement_path"] == "./req//requirement.md"
    candidate = inventory_candidate(packet)
    candidate["questions"] = [{**question, "status": "ANSWERED"}]
    requirement_evidence = "analysis:proof:evidence:requirement"
    decision_evidence = "analysis:proof:evidence:decision"
    shared = {"supports": "Review the supplied input.", "method": "EXTRACTED", "confidence": 1,
              "validity": "VALID"}
    candidate["evidence"] = [
        {**shared, "id": requirement_evidence, "source_id": requirement_id, "kind": "REQUIREMENT",
         "quote": packet["requirement"], "sha256": packet["requirement_file_hash"]},
        {**shared, **answer, "id": decision_evidence, "source_id": answer["decision_id"], "kind": "HUMAN_DECISION",
         "path": "context.md", "sha256": packet["source_manifest"]["context.md"]["sha256"]},
    ]
    candidate["test_plan"] = [
        {"id": "analysis:proof:test:" + name, "text": "Check the " + name, "state": "TO_BE",
         "requirement_ids": [requirement_id], "entity_ids": [], "evidence_ids": [evidence_id]}
        for name, evidence_id in (("requirement", requirement_evidence), ("decision", decision_evidence))
    ]
    assert feature.apply(tmp_path, "proof", candidate)["valid"]
    store = _store_bytes(tmp_path)
    (tmp_path / changed_path).write_text("Content changed.", encoding="utf-8")

    report = dependency_impact(tmp_path, [changed_path])
    if changed_path == requirement_path:
        assert [item["id"] for item in report["affected"]] == ["analysis:proof:test:requirement"]
        reason, = report["affected"][0]["reasons"]
        assert (reason["evidence_id"], reason["path"], reason["revision"]) == (requirement_evidence, requirement_path, 2)
    else:
        assert not report["affected"]
    assert _store_bytes(tmp_path) == store


@pytest.mark.parametrize("edit", ["none", "line_endings", "operation"])
def test_openapi_reverse_dependency_distinguishes_raw_and_normalized_hashes(tmp_path, edit):
    # Split a CRLF pair across the reader's chunk boundary.
    raw = b" " * 65535 + b'\r\n{"openapi":"3.0.3","paths":{"/item":{"get":{"operationId":"getItem"}}}}\r\n'
    api = tmp_path / "openapi.json"
    api.write_bytes(raw)
    assert scan(tmp_path, generate_docs=False) == 0
    store = _store_bytes(tmp_path)
    changed = {"none": raw, "line_endings": raw.replace(b"\r\n", b"\n"),
               "operation": raw.replace(b"getItem", b"fetchItem")}[edit]
    api.write_bytes(changed)

    report = dependency_impact(tmp_path, ["openapi.json"])
    normalized_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if edit == "operation":
        assert report["changed_sources"] == [{
            "path": "openapi.json", "before_sha256": normalized_hash,
            "after_sha256": hashlib.sha256(changed.replace(b"\r\n", b"\n")).hexdigest(),
        }]
    else:
        assert not report["changed_sources"]
    if edit == "none":
        assert not report["affected"]
    else:
        dependent, = report["affected"]
        assert (dependent["kind"], dependent["status"], dependent["path"]) == (
            "CONTRACT_DECLARATION", "RECHECK", "openapi.json",
        )
        assert dependent["reasons"][0]["before_sha256"] == hashlib.sha256(raw).hexdigest()
    assert _store_bytes(tmp_path) == store


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

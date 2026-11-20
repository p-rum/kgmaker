"""T047-S01 source-only workspace and explicit cold compiler oracle."""
import os
import runpy
import shutil
from pathlib import Path

import pytest

from kgmaker.analysis_model import AnalysisError, read_json, write_json
from kgmaker.dataflow import impact_paths
from kgmaker.inspection import command, inspect_jvm
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import qualified, snapshot_workspace

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/incremental-integrity"
HARNESS = runpy.run_path(str(FIXTURE / "workspace_fixture.py"))
make_workspace, snapshot, mutations = (HARNESS[key] for key in ("make_workspace", "snapshot", "mutations"))
TARGET, CALLER, INDEPENDENT = (HARNESS[key] for key in ("TARGET", "CALLER", "INDEPENDENT"))


def load_oracle(path):
    value = read_json(path)
    fields = {"overloads", "caller", "independent", "dto", "endpoint_field", "ui", "missing_call", "kafka",
              "added_declaration_path", "moved_overload_path", "flyway_mutation_object"}
    if (type(value) is not dict or set(value) != fields
            or any(not isinstance(value[key], str) or not value[key] for key in fields - {"overloads", "kafka"})
            or type(value["overloads"]) is not list or len(value["overloads"]) != 2
            or any(not isinstance(row, str) or not row for row in value["overloads"])
            or value["overloads"][0] == value["overloads"][1]
            or type(value["kafka"]) is not dict
            or set(value["kafka"]) != {"initial_topic", "mutated_consumer_topic", "reason"}
            or any(not isinstance(row, str) or not row for row in value["kafka"].values())):
        raise AnalysisError("Invalid T047 oracle")
    return value


def test_source_only_clean_workspace_matches_manual_oracle(tmp_path):
    oracle = load_oracle(FIXTURE / "oracle.json")
    _, coverage, _, graph, _ = snapshot_workspace(make_workspace(tmp_path))
    nodes = {node.id for node in graph.nodes}
    functions = {(node.path, node.signature) for node in graph.nodes if node.kind == "function"}
    assert {("@backend/" + TARGET, signature) for signature in oracle["overloads"]} <= functions
    assert ("@backend/" + CALLER, oracle["caller"]) in functions
    assert ("@backend/" + INDEPENDENT, oracle["independent"]) in functions
    dto = qualified("backend", oracle["dto"])
    ui = qualified("frontend", oracle["ui"])
    assert {dto, ui, oracle["endpoint_field"]} <= nodes
    reached = {item["entity_ids"][-1] for item in impact_paths(graph, dto)["paths"]}
    assert oracle["endpoint_field"] in reached
    assert ui not in reached
    assert not graph.call_sites
    assert all(node.name != oracle["missing_call"] for node in graph.nodes)
    assert all(edge.source in nodes and edge.target in nodes for edge in graph.edges)
    assert coverage["schemas"]["backend"][0]["status"] == "COMPLETE"
    assert any("VALUE_FLOW_COMPILER_EVIDENCE_UNAVAILABLE" in item for item in coverage["limitations"])
    bindings = coverage["kafka_bindings"]["bindings"]
    assert {item["direction"] for item in bindings} == {"producer", "consumer"}
    assert all(item["topic"] == oracle["kafka"]["initial_topic"] and item["status"] == "UNKNOWN"
               and oracle["kafka"]["reason"] in item["reasons"] for item in bindings)
    assert not any(edge.kind == "kafka_binding_match" for edge in graph.edges)
    assert coverage["release_mapping"]["status"] == "PARTIAL"
    assert coverage["release_mapping"]["mappings"][0]["diagnostic"] == "RELEASE_MANIFEST_UNAVAILABLE"
    assert not any(edge.kind == "supplies_classpath" for edge in graph.edges)


def test_malformed_oracle_is_rejected(tmp_path):
    item = read_json(FIXTURE / "oracle.json")
    item["overloads"][1] = item["overloads"][0]
    malformed = tmp_path / "oracle.json"
    write_json(malformed, item)
    with pytest.raises(AnalysisError, match="Invalid T047 oracle"):
        load_oracle(malformed)


def test_mutation_replay_and_reset(tmp_path):
    root = tmp_path / "workspace"
    make_workspace(root)
    original = snapshot(root)
    first = list(mutations(root))
    assert [label for label, _, _, _ in first] == [
        "comment", "body", "add", "move", "delete", "contract", "kafka", "flyway", "tsconfig",
    ]
    for label, _, changed, expected in first:
        assert changed == expected, label
    shutil.rmtree(root)
    make_workspace(root)
    assert snapshot(root) == original
    assert list(mutations(root)) == first


def test_source_only_mutation_states_match_manual_oracle(tmp_path):
    oracle = load_oracle(FIXTURE / "oracle.json")
    manifest = make_workspace(tmp_path)
    previous_files = snapshot_workspace(manifest)[3].files
    applied = set()

    for label, _, _, expected_paths in mutations(tmp_path):
        applied.add(label)
        _, coverage, _, graph, _ = snapshot_workspace(manifest)
        functions = [node for node in graph.nodes if node.kind == "function"]
        overload_path = oracle["moved_overload_path"] if "move" in applied else TARGET
        expected_overloads = [] if "delete" in applied else [
            ("@backend/" + overload_path, signature) for signature in oracle["overloads"]
        ]
        overloads = sorted((node.path, node.signature) for node in functions if node.name == "score")
        assert overloads == sorted(expected_overloads), label
        missing_call = oracle["missing_call"]
        expected_added = [
            ("@backend/" + oracle["added_declaration_path"], missing_call)
        ] if "add" in applied else []
        added = [(node.path, node.signature) for node in functions if node.name == missing_call]
        assert added == expected_added, label
        assert [(node.path, node.signature) for node in functions if node.name == oracle["caller"]] == [
            ("@backend/" + CALLER, oracle["caller"]),
        ], label
        assert not graph.call_sites, label

        kafka = oracle["kafka"]
        consumer_topic = kafka["mutated_consumer_topic"] if "kafka" in applied else kafka["initial_topic"]
        bindings = coverage["kafka_bindings"]["bindings"]
        assert sorted((item["direction"], item["topic"], item["status"]) for item in bindings) == [
            ("consumer", consumer_topic, "UNKNOWN"), ("producer", kafka["initial_topic"], "UNKNOWN"),
        ], label
        assert all(kafka["reason"] in item["reasons"] for item in bindings), label
        assert not any(edge.kind in {"kafka_binding_match", "supplies_classpath"} for edge in graph.edges), label

        schema = coverage["schemas"]["backend"][0]
        assert schema["provenance"] == "MIGRATION_DERIVED", label
        assert (oracle["flyway_mutation_object"] in schema["objects"]) == ("flyway" in applied), label
        assert schema["deployment_verified"] is False and schema["data_availability"] == "UNASSESSED", label

        graph_changed = {path for path in previous_files.keys() | graph.files.keys()
                         if previous_files.get(path) != graph.files.get(path)}
        assert graph_changed == {"@" + path for path in expected_paths}, label
        previous_files = graph.files


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_added_kotlin_declaration_resolves_unchanged_caller_cold(tmp_path, backend):
    home = FIXTURE.parents[1] / "workers"
    try:
        command("jvm", home, kotlin_backend=backend)
    except WorkerError as error:
        required = os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1"
        required |= backend == "k2" and os.environ.get("KGMAKER_REQUIRE_K2") == "1"
        if required:
            raise
        pytest.skip(str(error))

    make_workspace(tmp_path)
    replay = mutations(tmp_path)
    assert [next(replay)[0] for _ in range(2)] == ["comment", "body"]
    kotlin = tmp_path / "backend"
    added = Path(TARGET).with_name("Added.kt").as_posix()
    inputs = [CALLER, TARGET]
    caller_before = (kotlin / CALLER).read_bytes()
    missing = load_oracle(FIXTURE / "oracle.json")["missing_call"]

    def calls_for(sources):
        result = inspect_jvm(kotlin, repo_id="backend", module="api", sources=sources,
                             home=home, kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        graph = result["graph"]
        symbols = {symbol["id"]: symbol for symbol in graph["symbols"]}
        assert {symbol["descriptor"] for symbol in symbols.values()
                if symbol.get("owner") == "fixture.ScoringKt" and symbol.get("name") == "score"} == {
                    "(I)I", "(Ljava/lang/String;)I"}
        calls = [site for site in graph["call_sites"] if site["path"] == CALLER]
        assert len(calls) == 2
        context_id = calls[0]["context_id"]
        context = next(value for value in graph["contexts"] if value["id"] == context_id)
        assert context["module"] == "api"
        resolved, unresolved = set(), []
        for site in calls:
            caller = symbols[site["caller"]]
            assert caller["name"] == "callScore" and caller["path"] == CALLER
            assert site["context_id"] == caller["context_id"] == context_id
            if site["evidence_kind"] == "UNRESOLVED":
                assert site["declared_target"] is None and not site["dispatch_candidates"]
                unresolved.append(site)
            else:
                assert site["evidence_kind"] == "SYMBOL_RESOLVED"
                target = symbols[site["declared_target"]]
                assert target["context_id"] == context_id
                resolved.add((target["owner"], target["name"], target["descriptor"], target["path"]))
        return resolved, unresolved, context_id

    score = ("fixture.ScoringKt", "score", "(I)I", TARGET)
    before, unresolved, before_context = calls_for(inputs)
    assert before == {score} and len(unresolved) == 1
    label, _, changed, _ = next(replay)
    assert label == "add" and changed == ["backend/" + added]
    assert (kotlin / CALLER).read_bytes() == caller_before
    after, unresolved, after_context = calls_for([*inputs, added])
    assert after == {score, ("fixture.AddedKt", missing, "()I", added)}
    assert not unresolved
    assert before_context != after_context
    assert not (kotlin / ".kgmaker").exists()


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="T047-S02 scanner identities contain declaration lines")
def test_comment_does_not_change_logical_identity(tmp_path):
    manifest = make_workspace(tmp_path)

    def score_ids():
        graph = snapshot_workspace(manifest)[3]
        overloads = [node for node in graph.nodes
                     if node.name == "score" and node.path == "@backend/" + TARGET]
        expected = set(load_oracle(FIXTURE / "oracle.json")["overloads"])
        if len(overloads) != 2 or {node.signature for node in overloads} != expected:
            pytest.fail("fixture lost overload declarations while testing line movement")
        return {node.id for node in overloads}

    before = score_ids()
    if next(mutations(tmp_path))[0] != "comment":
        pytest.fail("the first mutation no longer tests line movement")
    assert score_ids() == before

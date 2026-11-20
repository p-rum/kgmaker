"""T047-S01 source-only reproduction and independent oracle."""
import runpy
import shutil
from pathlib import Path

import pytest

from kgmaker.analysis_model import AnalysisError, read_json, write_json
from kgmaker.dataflow import impact_paths
from kgmaker.workspace import qualified, snapshot_workspace

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/incremental-integrity"
HARNESS = runpy.run_path(str(FIXTURE / "workspace_fixture.py"))
make_workspace, snapshot, mutations = (HARNESS[key] for key in ("make_workspace", "snapshot", "mutations"))
TARGET, CALLER, INDEPENDENT = (HARNESS[key] for key in ("TARGET", "CALLER", "INDEPENDENT"))


def load_oracle(path):
    value = read_json(path)
    fields = {"overloads", "caller", "independent", "dto", "endpoint_field", "ui", "missing_call", "kafka"}
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
    manifest = make_workspace(root)
    original = snapshot(root)
    first = list(mutations(root))
    assert len(first) == 9
    for label, _, changed, expected in first:
        assert changed == expected, label
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    consumer = next(item for item in coverage["kafka_bindings"]["bindings"]
                    if item["direction"] == "consumer")
    assert consumer["topic"] == load_oracle(FIXTURE / "oracle.json")["kafka"]["mutated_consumer_topic"]
    assert not any(edge.kind == "kafka_binding_match" for edge in graph.edges)
    assert not any(node.name == "score" for node in graph.nodes)
    shutil.rmtree(root)
    make_workspace(root)
    assert snapshot(root) == original
    assert list(mutations(root)) == first


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

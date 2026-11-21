"""T047-S01 source-only workspace and explicit cold compiler oracle."""
import hashlib
import os
import runpy
import shutil
from pathlib import Path

import pytest

from kgmaker.analysis_model import AnalysisError, file_hash, read_json, write_json
from kgmaker.dataflow import impact_paths
from kgmaker.inspection import command, inspect_frontend, inspect_jvm
from kgmaker.worker_protocol import WorkerError
from kgmaker.workspace import qualified, snapshot_workspace

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/incremental-integrity"
HARNESS = runpy.run_path(str(FIXTURE / "workspace_fixture.py"))
make_workspace, snapshot, mutations = (HARNESS[key] for key in ("make_workspace", "snapshot", "mutations"))
TARGET, CALLER, INDEPENDENT = (HARNESS[key] for key in ("TARGET", "CALLER", "INDEPENDENT"))
KAFKA_CONFIG, change_kafka_topic = (HARNESS[key] for key in ("KAFKA_CONFIG", "change_kafka_topic"))
CONTRACT, CLIENT, PAGE, GENERATION = (HARNESS[key] for key in ("CONTRACT", "CLIENT", "PAGE", "GENERATION"))
declare_typed_client, change_contract_version = (
    HARNESS[key] for key in ("declare_typed_client", "change_contract_version"))


def load_oracle(path):
    value = read_json(path)
    fields = {"overloads", "caller", "independent", "dto", "endpoint_field", "ui", "missing_call", "kafka",
              "added_declaration_path", "moved_overload_path", "flyway_mutation_object", "befe",
              "signature_mutation", "delete_mutation"}
    objects = {"kafka", "befe", "signature_mutation", "delete_mutation"}
    if (type(value) is not dict or set(value) != fields
            or any(not isinstance(value[key], str) or not value[key]
                   for key in fields - objects - {"overloads"})
            or type(value["overloads"]) is not list or len(value["overloads"]) != 2
            or any(not isinstance(row, str) or not row for row in value["overloads"])
            or value["overloads"][0] == value["overloads"][1]
            or type(value["signature_mutation"]) is not dict
            or set(value["signature_mutation"]) != {
                "replacement_signature", "owner", "changed_call", "stable_call",
                "prior_descriptor", "replacement_descriptor", "stable_descriptor",
            }
            or any(not isinstance(row, str) or not row for row in value["signature_mutation"].values())
            or type(value["delete_mutation"]) is not dict
            or set(value["delete_mutation"]) != {
                "prior_owner", "control_call", "control_owner", "control_descriptor",
            }
            or any(not isinstance(row, str) or not row for row in value["delete_mutation"].values())
            or type(value["befe"]) is not dict
            or set(value["befe"]) != {"backend_path", "owner", "field", "descriptor", "relations",
                                      "consumer_role", "release", "mutated_release"}
            or any(not isinstance(row, str) or not row for key, row in value["befe"].items()
                   if key != "relations")
            or type(value["befe"]["relations"]) is not list or len(value["befe"]["relations"]) != 3
            or any(not isinstance(row, str) or not row for row in value["befe"]["relations"])
            or type(value["kafka"]) is not dict
            or set(value["kafka"]) != {"initial_topic", "mutated_consumer_topic", "reason",
                                        "cluster", "producer", "consumer", "release"}
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


def test_source_only_repo_isolation_survives_workspace_relocation(tmp_path):
    original_root = tmp_path / "original"
    manifest = make_workspace(original_root)
    source = b"package fixture.shared\nclass Twin\n"
    expected = {
        "backend": ("@backend/src/Twin.kt", "repo:backend:file%3Asrc%2FTwin.kt%3ATwin.kt",
                    "repo:backend:type%3Asrc%2FTwin.kt%3ATwin%3A%3A2"),
        "frontend": ("@frontend/src/Twin.kt", "repo:frontend:file%3Asrc%2FTwin.kt%3ATwin.kt",
                     "repo:frontend:type%3Asrc%2FTwin.kt%3ATwin%3A%3A2"),
    }
    for repo in expected:
        (original_root / repo / "src/Twin.kt").write_bytes(source)

    _, _, sources, graph, metadata = snapshot_workspace(manifest)
    expected_digest = hashlib.sha256(source).hexdigest()
    assert {key: checksum for key, checksum in graph.files.items() if key.endswith("/src/Twin.kt")} == {
        key: expected_digest for key, _, _ in expected.values()
    }
    assert {(node.path, node.id) for node in graph.nodes if node.path.endswith("/src/Twin.kt")} == {
        (key, identity) for key, *identities in expected.values() for identity in identities
    }
    assert {context["mode"] for context in graph.contexts} == {"SOURCE_ONLY"}
    assert not graph.symbols and not graph.call_sites

    edges = {(edge.source, edge.kind, edge.target) for edge in graph.edges}
    for repo, (_, file_id, declaration_id) in expected.items():
        assert (file_id, "contains", declaration_id) in edges
        local_ids = {file_id, declaration_id}
        prefix = f"repo:{repo}:"
        assert all(start.startswith(prefix) and end.startswith(prefix)
                   for start, _, end in edges if {start, end} & local_ids)

    original_path = original_root.resolve()
    relocated = original_root.rename(tmp_path / "relocated")
    relocated_path = relocated.resolve()
    assert relocated_path != original_path and not original_root.exists()
    _, _, moved_sources, moved_graph, moved_metadata = snapshot_workspace(relocated / manifest.name)
    assert metadata["roots"] == {repo: str(original_path / repo) for repo in expected}
    assert moved_metadata["roots"] == {repo: str(relocated_path / repo) for repo in expected}
    assert moved_sources == sources
    assert moved_graph.to_dict() == graph.to_dict()


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
        "comment", "body", "add", "signature", "move", "delete", "contract", "kafka", "flyway", "tsconfig",
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
        overload_signatures = oracle["overloads"]
        if "signature" in applied:
            overload_signatures = [oracle["signature_mutation"]["replacement_signature"],
                                   oracle["overloads"][1]]
        expected_overloads = [] if "delete" in applied else [
            ("@backend/" + overload_path, signature) for signature in overload_signatures
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


def require_jvm_worker(backend):
    home = FIXTURE.parents[1] / "workers"
    try:
        command("jvm", home, kotlin_backend=backend)
    except WorkerError as error:
        required = os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1"
        required |= backend == "k2" and os.environ.get("KGMAKER_REQUIRE_K2") == "1"
        if required:
            raise
        pytest.skip(str(error))
    return home


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_added_kotlin_declaration_resolves_unchanged_caller_cold(tmp_path, backend):
    home = require_jvm_worker(backend)
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
        calls = [site for site in graph["call_sites"]
                 if site["path"] == CALLER and symbols[site["caller"]]["name"] == "callScore"]
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


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_changed_kotlin_signature_cannot_rebind_unchanged_caller_cold(tmp_path, backend):
    home = require_jvm_worker(backend)
    make_workspace(tmp_path)
    oracle = load_oracle(FIXTURE / "oracle.json")
    signature = oracle["signature_mutation"]
    replay = mutations(tmp_path)
    assert [next(replay)[0] for _ in range(3)] == ["comment", "body", "add"]
    kotlin = tmp_path / "backend"
    caller_bytes = (kotlin / CALLER).read_bytes()
    caller_text = caller_bytes.decode("utf-8")
    string_signature = oracle["overloads"][1].encode("utf-8")
    string_line, = [line for line in (kotlin / TARGET).read_bytes().splitlines(keepends=True)
                    if string_signature in line]

    def check_snapshot(active_descriptor, changed_call_descriptor):
        result = inspect_jvm(kotlin, repo_id="backend", module="api",
                             sources=[CALLER, TARGET, oracle["added_declaration_path"]],
                             home=home, kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        graph = result["graph"]
        symbols = {symbol["id"]: symbol for symbol in graph["symbols"]}
        context = result["context"]["id"]
        assert {symbol["descriptor"] for symbol in symbols.values()
                if (symbol.get("owner"), symbol["name"], symbol["path"], symbol["context_id"])
                == (signature["owner"], "score", TARGET, context)} == {
                    active_descriptor, signature["stable_descriptor"]}
        for expression, descriptor in ((signature["changed_call"], changed_call_descriptor),
                                       (signature["stable_call"], signature["stable_descriptor"])):
            site, = [site for site in graph["call_sites"] if site["path"] == CALLER
                     and caller_text[site["range"]["start"]:site["range"]["end"]] == expression]
            assert site["context_id"] == symbols[site["caller"]]["context_id"] == context
            if descriptor is None:
                assert site["evidence_kind"] == "UNRESOLVED"
                assert site["declared_target"] is None and not site["dispatch_candidates"]
            else:
                assert site["evidence_kind"] == "SYMBOL_RESOLVED"
                target = symbols[site["declared_target"]]
                assert (target["owner"], target["name"], target["descriptor"],
                        target["path"], target["context_id"]) == (
                            signature["owner"], "score", descriptor, TARGET, context)
        return context

    before_context = check_snapshot(signature["prior_descriptor"], signature["prior_descriptor"])
    label, _, changed, _ = next(replay)
    assert label == "signature" and changed == ["backend/" + TARGET]
    assert (kotlin / CALLER).read_bytes() == caller_bytes
    assert string_line in (kotlin / TARGET).read_bytes().splitlines(keepends=True)
    assert check_snapshot(signature["replacement_descriptor"], None) != before_context
    assert not (kotlin / ".kgmaker").exists()


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_deleted_kotlin_target_leaves_unchanged_caller_unresolved_cold(tmp_path, backend):
    home = require_jvm_worker(backend)
    make_workspace(tmp_path)
    oracle = load_oracle(FIXTURE / "oracle.json")
    deletion = oracle["delete_mutation"]
    target_call = oracle["signature_mutation"]["stable_call"]
    control_call = deletion["control_call"]
    moved = oracle["moved_overload_path"]
    added = oracle["added_declaration_path"]
    replay = mutations(tmp_path)
    assert [next(replay)[0] for _ in range(5)] == ["comment", "body", "add", "signature", "move"]
    kotlin = tmp_path / "backend"
    caller_bytes = (kotlin / CALLER).read_bytes()
    caller_text = caller_bytes.decode("utf-8")

    def inspect(sources):
        result = inspect_jvm(kotlin, repo_id="backend", module="api", sources=sources,
                             home=home, kotlin_backend=backend, publish=False)
        assert result["exit_code"] == 0
        assert not (kotlin / ".kgmaker").exists()
        context = result["context"]["id"]
        graph = result["graph"]
        symbols = {symbol["id"]: symbol for symbol in graph["symbols"]}
        sites = {}
        for expression in (target_call, control_call):
            site, = [site for site in graph["call_sites"] if site["path"] == CALLER
                     and caller_text[site["range"]["start"]:site["range"]["end"]] == expression]
            assert site["context_id"] == symbols[site["caller"]]["context_id"] == context
            sites[expression] = site
        return context, symbols, sites

    before_context, before_symbols, before_sites = inspect([CALLER, moved, added])
    prior_site = before_sites[target_call]
    assert prior_site["evidence_kind"] == "SYMBOL_RESOLVED"
    prior_target = before_symbols[prior_site["declared_target"]]
    assert (prior_target["owner"], prior_target["name"], prior_target["descriptor"],
            prior_target["path"], prior_target["context_id"]) == (
                deletion["prior_owner"], "score", oracle["signature_mutation"]["stable_descriptor"],
                moved, before_context)

    label, _, changed, _ = next(replay)
    assert label == "delete" and changed == ["backend/" + moved]
    assert not (kotlin / moved).exists()
    after_context, after_symbols, after_sites = inspect([CALLER, added])
    assert (kotlin / CALLER).read_bytes() == caller_bytes
    assert after_context != before_context
    current_site = after_sites[target_call]
    assert current_site["evidence_kind"] == "UNRESOLVED"
    assert current_site["declared_target"] is None and not current_site["dispatch_candidates"]
    assert prior_target["id"] not in after_symbols
    assert all(symbol["path"] != moved for symbol in after_symbols.values())

    for context, symbols, sites in ((before_context, before_symbols, before_sites),
                                    (after_context, after_symbols, after_sites)):
        control = sites[control_call]
        assert control["evidence_kind"] == "SYMBOL_RESOLVED"
        target = symbols[control["declared_target"]]
        assert (target["owner"], target["name"], target["descriptor"],
                target["path"], target["context_id"]) == (
                    deletion["control_owner"], oracle["missing_call"],
                    deletion["control_descriptor"], added, context)


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_cold_module_evidence_matches_kafka_binding_until_consumer_topic_changes(tmp_path, backend):
    home = require_jvm_worker(backend)
    manifest = make_workspace(tmp_path)
    root = tmp_path / "backend"
    oracle = load_oracle(FIXTURE / "oracle.json")["kafka"]
    sources_by_module = {"api": [TARGET], "independent": [INDEPENDENT]}
    project_model = {"source_sets": [
        {"module": module, "id": "main", "scope": "production", "roots": [f"{module}/src/main"]}
        for module in sources_by_module
    ]}

    def cold_snapshot(consumer_topic):
        captured = {}
        for module, sources in sources_by_module.items():
            result = inspect_jvm(root, repo_id="backend", module=module, sources=sources,
                                 home=home, kotlin_backend=backend, project_model=project_model,
                                 build_context={"spring_profiles": ["blue"]})
            assert result["exit_code"] == 0
            captured[module] = qualified("backend", result["context"]["id"])
        store = root / ".kgmaker/graph.json"
        prior = store.read_bytes()
        _, coverage, _, graph, _ = snapshot_workspace(manifest)
        assert store.read_bytes() == prior
        contexts = {item["id"]: item for item in graph.contexts}
        rows = {item["binding_id"]: item for item in coverage["kafka_bindings"]["bindings"]}
        assert set(rows) == {oracle["producer"], oracle["consumer"]}
        producer, consumer = rows[oracle["producer"]], rows[oracle["consumer"]]
        assert (producer["topic"], consumer["topic"]) == (oracle["initial_topic"], consumer_topic)
        for row, module in [(producer, "api"), (consumer, "independent")]:
            assert row["status"] == "RESOLVED" and row["reasons"] == []
            assert row["cluster_id"] == oracle["cluster"] and row["release"] == oracle["release"]
            assert row["contract_sha256"] == file_hash(root / "contracts/Order.json")
            assert row["delivery"] == "NOT_OBSERVED"
            assert contexts[row["context_id"]]["selected_compiler_context"] == captured[module]
        assert consumer["input_files"]["@backend/" + KAFKA_CONFIG] == file_hash(root / KAFKA_CONFIG)
        matches = [edge for edge in graph.edges if edge.kind == "kafka_binding_match"]
        return producer, consumer, matches

    producer, consumer, matches = cold_snapshot(oracle["initial_topic"])
    assert [(edge.source, edge.target, edge.evidence_kind, edge.context_ids) for edge in matches] == [
        (producer["id"], consumer["id"], "FRAMEWORK_DERIVED", (producer["context_id"], consumer["context_id"]))
    ]
    before = snapshot(tmp_path)
    change_kafka_topic(tmp_path)
    after = snapshot(tmp_path)
    assert {path for path in before.keys() | after if before.get(path) != after.get(path)} == {"backend/" + KAFKA_CONFIG}
    shutil.rmtree(root / ".kgmaker")
    _, updated, matches = cold_snapshot(oracle["mutated_consumer_topic"])
    assert updated["input_files"] != consumer["input_files"]
    assert not matches


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_cold_kotlin_typescript_contract_path_rejects_stale_client_release(tmp_path, backend):
    home = require_jvm_worker(backend)
    try:
        command("typescript", home)
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            raise
        pytest.skip(str(error))

    manifest = make_workspace(tmp_path)
    oracle = load_oracle(FIXTURE / "oracle.json")
    befe = oracle["befe"]
    kotlin = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    capture = inspect_jvm(kotlin, repo_id="backend", sources=[befe["backend_path"]],
                          home=home, kotlin_backend=backend)
    assert capture["exit_code"] == 0
    origins = [item for item in capture["graph"]["symbols"]
               if item.get("kind") == "field" and item.get("owner") == befe["owner"]
               and item.get("name") == befe["field"] and item.get("descriptor") == befe["descriptor"]]
    assert len(origins) == 1
    origin = origins[0]
    assert origin["path"] == befe["backend_path"] and origin["sha256"] == file_hash(kotlin / origin["path"])
    declare_typed_client(tmp_path, origin)
    ts = inspect_frontend(frontend, repo_id="frontend", home=home)
    assert ts["exit_code"] == 0
    assert not any(d.get("code") == "TS_DIAGNOSTIC" and d.get("category") == "Error" for d in ts["diagnostics"])

    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    assert coverage["release_mapping"]["mappings"][0]["diagnostic"] == "RELEASE_MANIFEST_UNAVAILABLE"
    assert not any(edge.kind == "supplies_classpath" for edge in graph.edges)
    field = qualified("backend", origin["id"])
    end = oracle["endpoint_field"]
    displays = [item for item in graph.symbols if item.get("value_role") == befe["consumer_role"]
                and item.get("path") == "@frontend/" + PAGE]
    assert len(displays) == 1
    display = displays[0]["id"]
    serialized, mapping, shown = befe["relations"]
    first, = [edge for edge in graph.edges if (edge.source, edge.target, edge.kind) == (field, end, serialized)]
    second, = [edge for edge in graph.edges
               if (edge.source, edge.kind, edge.evidence_kind) == (end, mapping, "FRAMEWORK_DERIVED")]
    projection = next(item for item in graph.symbols if item["id"] == second.target)
    declaration = projection["field_declaration"]
    client_symbol = next(item for item in graph.symbols if item["id"] == declaration["symbol"])
    assert projection["path"] == "@frontend/" + PAGE
    assert declaration["path"] == client_symbol["path"] == "@frontend/" + CLIENT
    assert declaration["sha256"] == client_symbol["sha256"] == file_hash(frontend / CLIENT)
    assert client_symbol["name"] == befe["field"] and client_symbol["kind"] == "PropertySignature"
    third, = [edge for edge in graph.edges
              if (edge.source, edge.target, edge.kind) == (second.target, display, shown)]
    assert (first.evidence_kind, second.evidence_kind, third.evidence_kind) == (
        "FRAMEWORK_DERIVED", "FRAMEWORK_DERIVED", "SYMBOL_RESOLVED")
    assert first.context_ids == second.context_ids == (
        qualified("backend", capture["context"]["id"]), qualified("frontend", ts["context"]["id"]))
    evidence = {item["id"]: item for item in graph.evidence}
    for edge in (first, second, third):
        assert edge.evidence_ids and all(evidence[item]["availability"] == "UNKNOWN" for item in edge.evidence_ids)
    generation = evidence[second.evidence_ids[0]]["generation"]
    assert generation["trust"] == "LOCAL_DECLARED"
    assert generation["release"] == befe["release"]
    assert generation["metadata_path"] == "@frontend/" + GENERATION
    assert generation["generated_path"] == "@frontend/" + CLIENT
    assert generation["contract_sha256"] == file_hash(kotlin / CONTRACT)
    assert generation["generated_sha256"] == file_hash(frontend / CLIENT)

    before = snapshot(tmp_path)
    change_contract_version(tmp_path)
    after = snapshot(tmp_path)
    assert {path for path in before.keys() | after if before.get(path) != after.get(path)} == {"backend/" + CONTRACT}
    assert read_json(kotlin / CONTRACT)["info"]["version"] == befe["mutated_release"] != generation["release"]
    assert file_hash(kotlin / CONTRACT) != generation["contract_sha256"]
    _, coverage, _, updated, _ = snapshot_workspace(manifest)
    assert any("VALUE_FLOW_GENERATION_OR_RELEASE_UNKNOWN" in item for item in coverage["limitations"])
    stale_contract_edges = [edge for edge in updated.edges if edge.evidence_kind == "FRAMEWORK_DERIVED"
                            and ((edge.target, edge.kind) == (end, serialized)
                                 or (edge.source, edge.kind) == (end, mapping))]
    assert not stale_contract_edges


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


def test_actual_jvm_release_artifact_is_bound_to_matching_consumer_classpath(tmp_path):
    """The TypeScript repo can host a separate JVM contract verifier."""
    from zipfile import ZipFile

    from kgmaker.build_runner import create_plan, run_plan

    gradle = os.environ.get("KGMAKER_TEST_GRADLE")
    if not gradle or not Path(gradle).is_file():
        pytest.skip("BLOCKED: set KGMAKER_TEST_GRADLE to supported Gradle 8.13")
    home = require_jvm_worker("k1")
    workspace = make_workspace(tmp_path)
    backend, frontend = tmp_path / "backend", tmp_path / "frontend"
    (backend / "settings.gradle").write_text("rootProject.name = 'exposure-contract'\n")
    (backend / "build.gradle").write_text("""plugins { id 'java-library' }
version = '1.0'
tasks.withType(JavaCompile).configureEach { options.release = 21 }
tasks.withType(Jar).configureEach { preserveFileTimestamps = false; reproducibleFileOrder = true }
tasks.matching { it.name == 'kgmakerExport' }.configureEach { dependsOn(tasks.named('jar')) }
""")
    producer = backend / "src/main/java/fixture/release/ExposureContract.java"
    producer.parent.mkdir(parents=True)
    producer.write_text("""package fixture.release;
public class ExposureContract { public static double decline() { return 1.0; } }
""")
    plan = create_plan(backend, phase="compile", executable=gradle, home=home, offline=True,
                       environment=["PATH", "JAVA_HOME", "GRADLE_USER_HOME", "JAVA_TOOL_OPTIONS"], timeout=120)
    build = run_plan(plan)
    assert build["result"]["status"] == "SUCCESS", Path(build["result"]["log_path"]).read_text()
    build_manifest = Path(build["manifest_path"])
    manifest = read_json(build_manifest)
    assert manifest["origin_trust"] == "HOST_EXECUTION"
    production, = [item for item in manifest["contexts"] if item["scope"] == "production"]
    output, = [item for item in production["outputs"] if Path(item["path"]).suffix == ".jar"]
    assert output["freshness"] == "EXECUTION_BOUND"
    assert output["execution_id"] == build["build_id"]
    actual_jar = Path(output["path"])
    with ZipFile(actual_jar) as archive:
        assert archive.read("fixture/release/ExposureContract.class").startswith(b"\xca\xfe\xba\xbe")

    artifact = frontend / ".kgmaker/classpath" / actual_jar.name
    artifact.parent.mkdir(parents=True)
    shutil.copyfile(actual_jar, artifact)
    assert file_hash(artifact) == file_hash(actual_jar) == output["sha256"]
    verifier = frontend / "tools/release-verifier/VerificationClient.java"
    verifier.parent.mkdir(parents=True)
    verifier.write_text("""import fixture.release.ExposureContract;
class VerificationClient { double verify() { return ExposureContract.decline(); } }
""")
    captured = inspect_jvm(frontend, home=home, repo_id="frontend", module="release-verifier",
                           sources=[verifier.relative_to(frontend).as_posix()], classpath=[str(artifact)],
                           project_model={"source_sets": [{"module": "release-verifier", "id": "main",
                                                          "scope": "production", "roots": ["tools/release-verifier"]}]})
    symbols = {item["id"]: item for item in captured["graph"]["symbols"]}
    decline, = [symbols[site["declared_target"]] for site in captured["graph"]["call_sites"]
                if site["evidence_kind"] == "SYMBOL_RESOLVED"
                and symbols[site["declared_target"]].get("name") == "decline"]
    assert (decline["owner"], decline["descriptor"]) == ("fixture.release.ExposureContract", "()D")

    config = read_json(workspace)
    release, = config["release_mapping"]["mappings"]
    release["producer"].update(manifest_path=build_manifest.relative_to(backend).as_posix(),
                               context_id=production["id"])
    release["consumer"]["context_id"] = captured["context"]["id"]
    release["output_sha256"] = output["sha256"]
    write_json(workspace, config)

    def release_snapshot():
        previous = snapshot(tmp_path)
        _, coverage, _, graph, _ = snapshot_workspace(workspace)
        assert snapshot(tmp_path) == previous
        report = coverage["release_mapping"]
        edges = [edge for edge in graph.edges if edge.kind == "supplies_classpath"]
        return report, edges, graph

    report, edges, graph = release_snapshot()
    assert report["status"] == "COMPLETE"
    row, = report["mappings"]
    assert (row["id"], row["status"], row["sha256"]) == ("exposure-release", "CONTENT_VERIFIED", output["sha256"])
    edge, = edges
    assert (edge.source, edge.target) == ("workspace:release-output:exposure-release",
                                          "workspace:classpath-artifact:exposure-release")
    assert edge.evidence_kind == "SYMBOL_RESOLVED" and edge.confidence == "CONTENT_VERIFIED"
    assert edge.context_ids == (qualified("frontend", captured["context"]["id"]),)
    proof, = [item for item in graph.evidence if item["id"] in edge.evidence_ids]
    assert (proof["method"], proof["sha256"]) == ("CONTENT_HASH_MATCH_V1", output["sha256"])

    release["output_sha256"] = "0" * 64
    write_json(workspace, config)
    report, edges, _ = release_snapshot()
    assert report["status"] == "PARTIAL"
    assert report["mappings"][0]["diagnostic"] == "RELEASE_OUTPUT_HASH_MISMATCH"
    assert not edges

    release["output_sha256"] = output["sha256"]
    write_json(workspace, config)
    with ZipFile(artifact, "a") as archive:
        archive.comment = b"Same class, changed JAR bytes"
    assert file_hash(artifact) != output["sha256"]
    report, edges, _ = release_snapshot()
    assert report["status"] == "PARTIAL"
    assert report["mappings"][0]["diagnostic"] == "RELEASE_CONSUMER_CONTEXT_STALE"
    assert not edges

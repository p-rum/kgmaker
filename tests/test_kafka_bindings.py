"""T003-S07-W04 actual properties/contract/workspace fixtures, no transport."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.workspace import snapshot_workspace, load_workspace, _REPO_CACHE


@pytest.fixture
def kafka_workspace(tmp_path):
    for repo in ("producer", "consumer", "schemas"):
        (tmp_path / repo).mkdir()
    schema = tmp_path / "schemas/Order.json"
    schema.write_text(json.dumps({"title": "Order", "type": "object", "properties": {"id": {"type": "string"}}}))
    services, owners, bindings = [], [], []
    for repo, direction in (("producer", "producer"), ("consumer", "consumer")):
        config = tmp_path / repo / "src/main/resources"
        config.mkdir(parents=True)
        name = "orders-" + ("out-0" if direction == "producer" else "in-0")
        prefix = "spring.cloud.stream.bindings." + name
        (config / "application.properties").write_text(prefix + ".destination=${orders.topic}\n" + prefix + ".binder=alpha\norders.topic=orders\nspring.kafka.password=DO_NOT_EXPORT_THIS_SECRET\n")
        (config / "application-blue.properties").write_text("orders.topic=orders-blue\n")
        services.append({"id": repo + "-svc", "backend_repo": repo, "frontend_repos": [], "test_repos": [],
                         "transport": "kafka", "contract": {"repo_id": "schemas", "path": "Order.json"}})
        owners.append({"id": repo + "-svc", "roots": [{"repo_id": repo, "path": "src/main"}],
                       "modules": [], "external_systems": []})
        bindings.append({"id": repo + "-orders", "repo_id": repo, "service_id": repo + "-svc", "module": "root",
            "source_set": "main", "scope": "production", "context_id": None, "binding": name, "direction": direction,
            "profiles": ["blue"], "config_files": [{"path": "src/main/resources/application.properties", "profile": None},
                {"path": "src/main/resources/application-blue.properties", "profile": "blue"}],
            "binders": {"alpha": "cluster-a", "beta": "cluster-b"},
            "contract": {"repo_id": "schemas", "path": "Order.json", "release": "r1"}, "payload": "Order"})
    document = {"schema_version": 1, "workspace_id": "kafka-fixture", "repositories": [
        {"id": repo, "role": "shared" if repo == "schemas" else "backend", "path": repo}
        for repo in ("producer", "consumer", "schemas")], "services": services,
        "service_ownership": {"schema_version": 1, "services": owners},
        "kafka_bindings": {"schema_version": 1, "clusters": [{"id": "cluster-a"}, {"id": "cluster-b"}], "bindings": bindings}}
    manifest = tmp_path / "workspace.json"
    manifest.write_text(json.dumps(document))
    return tmp_path, manifest, document


def write_manifest(manifest, document):
    manifest.write_text(json.dumps(document))


def test_exact_cluster_topic_contract_release_and_profile_identity(kafka_workspace):
    root, manifest, document = kafka_workspace
    graph = snapshot_workspace(manifest)[3]
    bindings = [n for n in graph.nodes if n.kind == "kafka_binding"]
    assert len(bindings) == 2 and all(n.metadata["status"] == "RESOLVED" for n in bindings)
    assert all(n.metadata["topic"] == "orders-blue" and n.metadata["cluster_id"] == "cluster-a" for n in bindings)
    assert len([e for e in graph.edges if e.kind == "kafka_binding_match"]) == 1
    assert "DO_NOT_EXPORT_THIS_SECRET" not in json.dumps(graph.to_dict())
    consumer = root / "consumer/src/main/resources/application.properties"
    consumer.write_text(consumer.read_text().replace(".binder=alpha", ".binder=beta"))
    other_cluster = snapshot_workspace(manifest)[3]
    assert not any(e.kind == "kafka_binding_match" for e in other_cluster.edges)
    assert len({n.id for n in other_cluster.nodes if n.kind == "kafka_topic" and n.metadata and n.metadata.get("kafka_binding_version")}) == 2
    consumer.write_text(consumer.read_text().replace(".binder=beta", ".binder=alpha"))
    document["kafka_bindings"]["bindings"][1]["contract"]["release"] = "r2"
    write_manifest(manifest, document)
    assert not any(e.kind == "kafka_binding_match" for e in snapshot_workspace(manifest)[3].edges)


def test_dynamic_property_and_unknown_profile_remain_unresolved(kafka_workspace):
    root, manifest, document = kafka_workspace
    config = root / "consumer/src/main/resources/application-blue.properties"
    config.write_text("orders.topic=${external.dynamic.topic}\n")
    graph = snapshot_workspace(manifest)[3]
    consumer = next(n for n in graph.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "consumer")
    assert consumer.metadata["status"] == "UNKNOWN" and consumer.metadata["topic"] is None
    assert not any(e.kind == "kafka_binding_match" for e in graph.edges)
    document["kafka_bindings"]["bindings"][0]["profiles"] = None
    write_manifest(manifest, document)
    producer = next(n for n in snapshot_workspace(manifest)[3].nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    assert producer.metadata["status"] == "UNKNOWN"


@pytest.mark.parametrize("expression", ['"orders-" + suffix', "topicFromEnvironment"] )
def test_dynamic_java_prefix_is_not_a_literal_topic(tmp_path, expression):
    (tmp_path / "Producer.java").write_text('class Producer {void send(String suffix){kafkaTemplate.send(' + expression + ', payload);}}')
    with patch("subprocess.Popen", side_effect=AssertionError("transport/process")):
        graph = scan_repository(tmp_path)
    assert not any(n.kind == "kafka_topic" and n.name == "orders-" for n in graph.nodes)
    assert any(n.kind == "kafka_binding_boundary" and n.metadata["status"] == "UNKNOWN" for n in graph.nodes)


@pytest.mark.parametrize("case", ["outside", "service", "duplicate", "schema"])
def test_invalid_binding_fails_before_cache_or_store_mutation(kafka_workspace, case):
    root, manifest, document = kafka_workspace
    binding = document["kafka_bindings"]["bindings"][0]
    if case == "outside":
        binding["config_files"][0]["path"] = "../outside.properties"
    elif case == "service":
        binding["service_id"] = "consumer-svc"
    elif case == "duplicate":
        document["kafka_bindings"]["bindings"].append(copy.deepcopy(binding))
    else:
        document["kafka_bindings"]["schema_version"] = 99
    write_manifest(manifest, document)
    store = root / "producer/.kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last valid generation")
    before = copy.deepcopy(_REPO_CACHE)
    with patch("subprocess.Popen", side_effect=AssertionError("must fail before process")):
        with pytest.raises(AnalysisError):
            snapshot_workspace(manifest, cache_root=root, persist_cache=True)
    assert _REPO_CACHE == before and store.read_bytes() == b"last valid generation"


def test_config_and_contract_hash_changes_invalidate_bindings_without_source_mutation(kafka_workspace):
    root, manifest, _ = kafka_workspace
    first = snapshot_workspace(manifest)[3]
    producer = next(n for n in first.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    (root / "schemas/Order.json").write_text('{"title":"Order","type":"object","version":2}')
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    second = snapshot_workspace(manifest)[3]
    updated = next(n for n in second.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    assert updated.id != producer.id
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    for version in (1, 2, 3):
        payload = second.to_dict()
        payload["schema_version"] = version
        assert KnowledgeGraph.from_dict(payload).schema_version == version


@pytest.mark.parametrize("case", ["scope-list", "repo-list", "contract-list", "direction-list", "symlink", "oversized", "ownership"])
def test_structural_paths_and_ownership_fail_closed(kafka_workspace, case):
    root, manifest, document = kafka_workspace
    binding = document["kafka_bindings"]["bindings"][0]
    if case.endswith("-list"):
        field = case.removesuffix("-list")
        if field == "repo":
            binding["repo_id"] = []
        elif field == "contract":
            binding["contract"]["repo_id"] = []
        else:
            binding[field] = []
    elif case == "ownership":
        document["service_ownership"]["services"][0]["roots"] = []
    elif case == "oversized":
        (root / "producer/src/main/resources/application.properties").write_bytes(b"x" * 1_000_001)
    else:
        config = root / "producer/src/main/resources/application.properties"
        config.unlink()
        config.symlink_to(root / "consumer/src/main/resources/application.properties")
    write_manifest(manifest, document)
    before = copy.deepcopy(_REPO_CACHE)
    with patch("subprocess.Popen", side_effect=AssertionError("validation must precede process")):
        with pytest.raises(AnalysisError):
            snapshot_workspace(manifest, cache_root=root, persist_cache=True)
    assert _REPO_CACHE == before and not (root / ".kgmaker/workspace-cache").exists()


@pytest.mark.parametrize("value", ['orders-${suffix}', 'orders + dynamic', '${environment}', '#{bean.topic}'])
def test_config_syntax_hints_never_extract_dynamic_prefix(tmp_path, value):
    (tmp_path / "application.properties").write_text("spring.kafka.bootstrap-servers=not-used\ntopic=" + value + "\n")
    graph = scan_repository(tmp_path)
    assert not any(n.kind == "kafka_topic" for n in graph.nodes)
    assert any(n.kind == "kafka_binding_boundary" for n in graph.nodes)


@pytest.mark.parametrize("case", ["missing", "duplicate", "syntax", "cyclic", "partial", "bad-topic", "bad-contract", "profile-expression"])
def test_unsupported_config_is_unknown_and_has_no_match(kafka_workspace, case):
    root, manifest, document = kafka_workspace
    config = root / "consumer/src/main/resources/application-blue.properties"
    if case == "missing":
        config.unlink()
    elif case == "duplicate":
        config.write_text("orders.topic=orders-blue\norders.topic=orders-blue\n")
    elif case == "syntax":
        config.write_text("orders.topic=orders-blue\\\n")
    elif case == "cyclic":
        config.write_text("orders.topic=${a}\na=${orders.topic}\n")
    elif case == "partial":
        config.write_text("orders.topic=orders-${suffix}\n")
    elif case == "bad-topic":
        config.write_text("orders.topic=a,b\n")
    elif case == "bad-contract":
        (root / "schemas/Order.json").write_text("not-json")
    else:
        document["kafka_bindings"]["bindings"][1]["config_files"][1]["profile"] = "blue &"
        write_manifest(manifest, document)
    graph = snapshot_workspace(manifest)[3]
    consumer = next(n for n in graph.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "consumer")
    assert consumer.metadata["status"] == "UNKNOWN" and consumer.metadata["reasons"]
    assert not any(e.kind == "kafka_binding_match" for e in graph.edges)
    assert not any(e.evidence_kind == "COMPILER_RESOLVED" and e.source == consumer.id for e in graph.edges)


def test_config_race_fails_before_cache_publication(kafka_workspace):
    from kgmaker import kafka_bindings
    root, manifest, _ = kafka_workspace
    original = kafka_bindings.build_links
    def mutate_after_read(workspace, graphs):
        result = original(workspace, graphs)
        target = root / "producer/src/main/resources/application-blue.properties"
        target.write_text(target.read_text().replace("orders-blue", "orders-pink"))
        return result
    before = copy.deepcopy(_REPO_CACHE)
    with patch.object(kafka_bindings, "build_links", side_effect=mutate_after_read):
        with pytest.raises(AnalysisError, match="changed"):
            snapshot_workspace(manifest, cache_root=root, persist_cache=True)
    assert _REPO_CACHE == before and not (root / ".kgmaker/workspace-cache").exists()


def test_offline_workspace_uses_no_transport_or_build_process(kafka_workspace):
    import subprocess
    root, manifest, _ = kafka_workspace
    run = subprocess.run
    def git_only(command, *args, **kwargs):
        assert command[:1] == ["git"] and command[3:] == ["rev-parse", "HEAD"]
        return run(command, *args, **kwargs)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with patch("subprocess.run", side_effect=git_only):
        graph = snapshot_workspace(manifest)[3]
    assert len([e for e in graph.edges if e.kind == "kafka_binding_match"]) == 1
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_context_selection_profile_and_scope_guards(kafka_workspace, monkeypatch):
    # Selection unit case; real captured snapshot validation is covered below.
    from kgmaker.worker_protocol import WorkerError
    def validate(root, context):
        if context.get("freshness") == "STALE":
            raise WorkerError("stale", "STALE")
    monkeypatch.setattr("kgmaker.graph_provider.validate_context_snapshot", validate)
    from kgmaker.kafka_bindings import build_links
    root, manifest, document = kafka_workspace
    workspace = load_workspace(manifest)
    graphs = {repo: scan_repository(root / repo) for repo in ("producer", "consumer", "schemas")}
    context = {"id": "jvm-one", "repo_id": "producer", "language": "jvm", "analyzer_version": "test-context", "module": "root",
        "source_set": "main", "scope": "production", "spring_profiles": ["blue"], "spring_properties": {},
        "project_model": {"source_sets": [{"id": "main", "module": "root", "scope": "production", "roots": ["src/main"]}]}}
    graphs["producer"].contexts = [context, {**context, "id": "jvm-two"}]
    with pytest.raises(AnalysisError, match="Ambiguous"):
        build_links(workspace, graphs)
    workspace["kafka_bindings"]["bindings"][0]["context_id"] = "jvm-one"
    rows = build_links(workspace, graphs)[-1]["bindings"]
    assert rows[0]["status"] == "RESOLVED"
    context["spring_properties"] = {"orders.topic": "context-override"}
    rows = build_links(workspace, graphs)[-1]["bindings"]
    assert rows[0]["topic"] == "context-override"
    context["repo_id"] = "foreign"
    with pytest.raises(AnalysisError, match="repository"):
        build_links(workspace, graphs)
    context["repo_id"] = "producer"
    context["spring_profiles"] = []
    with pytest.raises(AnalysisError, match="profile"):
        build_links(workspace, graphs)
    context["spring_profiles"] = ["blue"]
    context["freshness"] = "STALE"
    assert build_links(workspace, graphs)[-1]["bindings"][0]["status"] == "UNKNOWN"
    workspace["kafka_bindings"]["bindings"][0]["context_id"] = "missing"
    with pytest.raises(AnalysisError, match="context"):
        build_links(workspace, graphs)


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_actual_captured_context_properties_and_offline_staleness(kafka_workspace, backend):
    import os
    from kgmaker.inspection import command, inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    root, manifest, document = kafka_workspace
    home = Path(__file__).resolve().parents[1] / "workers"
    try:
        command("jvm", home, kotlin_backend=backend)
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    source = root / "producer/src/main/java/app/Producer.java"
    source.parent.mkdir(parents=True)
    source.write_text("package app; public class Producer { public String value(){return \"static\";} }")
    result = inspect_jvm(root / "producer", home=home, kotlin_backend=backend, repo_id="producer",
        build_context={"spring_profiles": ["blue"], "spring_properties": {"orders.topic": "captured-topic"}})
    graph = snapshot_workspace(manifest)[3]
    binding = next(n for n in graph.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    assert binding.metadata["status"] == "RESOLVED" and binding.metadata["topic"] == "captured-topic"
    derived = next(c for c in graph.contexts if c["id"] == binding.metadata["context_id"])
    assert derived["selected_compiler_context"].endswith(result["context"]["id"])
    # Cache keys include local sources; additionally the selected snapshot is
    # content-validated on every use, never executed to repair itself.
    source.write_text(source.read_text().replace("static", "edited"))
    with patch("subprocess.run", return_value=__import__("subprocess").CompletedProcess([], 0, "unavailable", "")):
        with patch("subprocess.Popen", side_effect=AssertionError("offline refresh executed compiler")):
            updated = snapshot_workspace(manifest)[3]
    stale = next(n for n in updated.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    assert stale.metadata["status"] == "UNKNOWN" and "COMPILER_CONTEXT_STALE" in stale.metadata["reasons"]


def test_disk_cache_is_not_published_when_binding_analysis_fails(kafka_workspace):
    root, manifest, _ = kafka_workspace
    with patch.dict(_REPO_CACHE, clear=True):
        snapshot_workspace(manifest, cache_root=root, persist_cache=True)
        assert list((root / ".kgmaker/workspace-cache").glob("*.json"))
        _REPO_CACHE.clear()
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        with patch("kgmaker.kafka_bindings.build_links", side_effect=AnalysisError("cancelled", 3)):
            with pytest.raises(AnalysisError, match="cancelled"):
                snapshot_workspace(manifest, cache_root=root, persist_cache=True)
        assert not _REPO_CACHE
        assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_declared_binding_match_is_not_data_availability(kafka_workspace):
    import subprocess
    from kgmaker import feature
    from kgmaker.analysis_model import INPUT_METADATA
    from kgmaker.data_check import data_check
    root, manifest, _ = kafka_workspace
    coordinator = root / "coordinator"
    coordinator.mkdir()
    (coordinator / "requirement.md").write_text("Use the orders binding payload.")
    packet = feature.prepare(coordinator, "requirement.md", "kafka", 200_000, workspace=manifest)
    graph = feature.graph_for_packet(coordinator, packet)
    binding = next(n for n in graph.nodes if n.kind == "kafka_binding" and n.metadata["status"] == "RESOLVED")
    requirement = "analysis:kafka:requirement:payload"
    spec = {"schema_version": 1, "analysis_id": "kafka", "requirement_hash": packet["requirement_hash"],
        "requirements": [{"id": requirement, "text": "Use payload", "kind": "InputRequirement", "source_quote": "orders binding payload"}],
        "inputs": [{"id": "analysis:kafka:input:payload", "name": "payload", "requirement_ids": [requirement],
                    "candidate_entity_ids": [binding.id], **{key: None for key in INPUT_METADATA}}]}
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    popen = subprocess.Popen
    def git_only(argv, *args, **kwargs):
        assert argv[:1] == ["git"] and argv[3:] == ["rev-parse", "HEAD"]
        return popen(argv, *args, **kwargs)
    with patch("subprocess.Popen", side_effect=git_only):
        result = data_check(coordinator, "kafka", spec)
    assert result["valid"], result
    assert result["candidate"]["input_requirements"][0]["availability"] == "UNKNOWN"
    assert not result["data_delivery_gaps"]
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

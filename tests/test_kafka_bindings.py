"""T003-S07-W04 actual properties/contract/workspace fixtures, no transport."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.workspace import snapshot_workspace, load_workspace, _REPO_CACHE, split_id


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
        build_context={"spring_profiles": ["blue"], "spring_properties": {"orders.topic": "captured-topic",
            "spring.kafka.password": "SYNTHETIC_ACTUAL_CAPTURED_PRIVATE_VALUE"}})
    original_store = (root / "producer/.kgmaker/graph.json").read_bytes()
    graph = snapshot_workspace(manifest)[3]
    from kgmaker.views import select_service_contexts
    selection = select_service_contexts(graph, [{"service_id": "producer-svc", "repo_id": "producer", "module": "root"}],
        scope="production", repo_roots={"producer": root / "producer"})
    assert selection["services"][0]["status"] == "CURRENT"
    assert "SYNTHETIC_ACTUAL_CAPTURED_PRIVATE_VALUE" not in json.dumps([selection, graph.to_dict()])
    assert (root / "producer/.kgmaker/graph.json").read_bytes() == original_store
    binding = next(n for n in graph.nodes if n.kind == "kafka_binding" and n.metadata["repo_id"] == "producer")
    assert binding.metadata["status"] == "RESOLVED" and binding.metadata["topic"] == "captured-topic"
    derived = next(c for c in graph.contexts if c["id"] == binding.metadata["context_id"])
    assert split_id(derived["selected_compiler_context"]) == ("producer", result["context"]["id"])
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


@pytest.mark.parametrize("profiles,expression,expected", [([], "default", "orders-default"),
    ([], "!blue", "orders-default"), ([], "default | prod", "orders-default"),
    (["blue"], "default", "orders"), (["blue"], "!blue", "orders")])
def test_explicit_default_profile_precedence_matches_spring(kafka_workspace, profiles, expression, expected):
    root, manifest, document = kafka_workspace
    for binding in document["kafka_bindings"]["bindings"]:
        binding["profiles"] = profiles
        binding["config_files"][1]["profile"] = expression
    for repo in ("producer", "consumer"):
        (root / repo / "src/main/resources/application-blue.properties").write_text("orders.topic=orders-default\n")
    write_manifest(manifest, document)
    graph = snapshot_workspace(manifest)[3]
    bindings = [n for n in graph.nodes if n.kind == "kafka_binding"]
    assert all(n.metadata["status"] == "RESOLVED" and n.metadata["topic"] == expected for n in bindings)


@pytest.mark.parametrize("key", ["spring.kafka.password", "spring.kafka.PASSWD", "spring.kafka.secret",
    "spring.kafka.credentials", "spring.kafka.api-key", "spring.kafka.access_token", "spring.kafka.authorization",
    "spring.kafka.username", "spring.kafka.sasl.jaas.config", "spring.kafka.bootstrap-servers"])
@pytest.mark.parametrize("chain", ["direct", "transitive"])
def test_sensitive_property_reference_never_exports_topic(kafka_workspace, key, chain):
    root, manifest, _ = kafka_workspace
    sentinel = "SYNTHETIC_PRIVATE_KAFKA_VALUE"
    for repo in ("producer", "consumer"):
        value = "${" + key + "}" if chain == "direct" else "${safe.alias}"
        (root / repo / "src/main/resources/application-blue.properties").write_text(
            "orders.topic=" + value + "\nsafe.alias=${" + key + "}\n" + key + "=" + sentinel + "\n")
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    graph = snapshot_workspace(manifest)[3]
    assert all(n.metadata["status"] == "UNKNOWN" and n.metadata["topic"] is None
               for n in graph.nodes if n.kind == "kafka_binding")
    assert not any(e.kind == "kafka_binding_match" for e in graph.edges)
    assert sentinel not in json.dumps(graph.to_dict())
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def captured_config_context(root, repo, properties, *, language="jvm", classpath=None, context_repo_id=None):
    """Offline captured-input fixture, not a claim of compiler execution."""
    from kgmaker.inspection import context
    from kgmaker.store import save_graph
    from kgmaker.graph_provider import validate_context_snapshot
    checkout = root / repo
    graph = scan_repository(checkout)
    selected = context(checkout, graph, language, {}, repo_id=context_repo_id or repo, module="root", source_set="main", scope="production",
        build_context={"spring_profiles": ["blue"], "spring_properties": properties, **({"classpath": classpath} if classpath is not None else {})})
    graph.contexts.append(selected)
    save_graph(graph, checkout)
    validate_context_snapshot(checkout, selected)
    return selected


@pytest.mark.parametrize("case", ["sensitive-direct", "sensitive-chain", "file-secret-context-alias", "benign"])
def test_public_workspace_captured_property_privacy_and_freshness(kafka_workspace, case):
    from kgmaker.analysis_model import digest
    from kgmaker.graph_provider import validate_context_snapshot
    root, manifest, _ = kafka_workspace
    sentinel = "SYNTHETIC_CAPTURED_KAFKA_PRIVATE_VALUE"
    selected = {}
    for repo, direction in (("producer", "out"), ("consumer", "in")):
        target = "spring.cloud.stream.bindings.orders-" + direction + "-0.destination"
        if case == "benign":
            properties = {target: "${benign.topic}", "benign.topic": "captured-safe-topic"}
        elif case == "file-secret-context-alias":
            (root / repo / "src/main/resources/application-blue.properties").write_text("spring.kafka.password=" + sentinel + "\n")
            properties = {target: "${safe.alias}", "safe.alias": "${spring.kafka.password}"}
        else:
            properties = {target: "${spring.kafka.password}" if case == "sensitive-direct" else "${safe.alias}",
                          "safe.alias": "${spring.kafka.password}", "spring.kafka.password": sentinel}
        selected[repo] = captured_config_context(root, repo, properties)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    baseline, coverage, sources, graph, metadata = snapshot_workspace(manifest)
    rows = [n for n in graph.nodes if n.kind == "kafka_binding"]
    if case == "benign":
        assert all(n.metadata["status"] == "RESOLVED" and n.metadata["topic"] == "captured-safe-topic" for n in rows)
        assert len([e for e in graph.edges if e.kind == "kafka_binding_match"]) == 1
    else:
        assert all(n.metadata["status"] == "UNKNOWN" and n.metadata["topic"] is None for n in rows)
        assert not any(e.kind == "kafka_binding_match" for e in graph.edges)
        assert sentinel not in json.dumps([baseline, coverage, sources, graph.to_dict(), metadata])
    for repo, original in selected.items():
        validate_context_snapshot(root / repo, original)
        exported = next(c for c in graph.contexts if c.get("repo_id") == repo and c.get("analyzer_version"))
        assert exported["selection_key"] == original["selection_key"]
        assert exported["spring_condition_inputs_hash"] == original["spring_condition_inputs_hash"]
        if case in {"sensitive-direct", "sensitive-chain"}:
            assert exported["spring_properties"]["spring.kafka.password"] == "<redacted>"
            projection = exported["spring_properties_projection"]
            assert projection["redacted"] is True and projection["sha256"] == digest(original["spring_properties"])
            assert projection["original_context_id"] == original["id"]
            assert original["spring_properties"]["spring.kafka.password"] == sentinel
            assert digest(exported["spring_properties"]) != projection["sha256"]
            cached = next(c for local, _ in _REPO_CACHE.values() for c in local.contexts if c.get("id") == original["id"])
            assert cached["spring_properties"] == original["spring_properties"]
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("sensitive", [True, False])
def test_binding_cluster_alias_reference_privacy(kafka_workspace, sensitive):
    root, manifest, _ = kafka_workspace
    key = "spring.kafka.password" if sensitive else "benign.binder"
    for repo, direction in (("producer", "out"), ("consumer", "in")):
        (root / repo / "src/main/resources/application-blue.properties").write_text(
            "orders.topic=orders-blue\nspring.cloud.stream.bindings.orders-" + direction + "-0.binder=${safe.alias}\n"
            "safe.alias=${" + key + "}\n" + key + "=alpha\n")
    graph = snapshot_workspace(manifest)[3]
    rows = [n for n in graph.nodes if n.kind == "kafka_binding"]
    assert all(n.metadata["status"] == ("UNKNOWN" if sensitive else "RESOLVED") for n in rows)
    assert all(n.metadata["cluster_id"] == (None if sensitive else "cluster-a") for n in rows)
    assert len([e for e in graph.edges if e.kind == "kafka_binding_match"]) == (0 if sensitive else 1)


def test_public_kafka_projection_preserves_non_jvm_selection_identity(kafka_workspace):
    from kgmaker.graph_provider import validate_context_snapshot
    root, manifest, _ = kafka_workspace
    sentinel = "SYNTHETIC_NON_JVM_CAPTURED_PRIVATE_VALUE"
    selected = captured_config_context(root, "producer", {"spring.kafka.password": sentinel}, language="typescript")
    before = (root / "producer/.kgmaker/graph.json").read_bytes()
    graph = snapshot_workspace(manifest)[3]
    exported = next(c for c in graph.contexts if c.get("analyzer_version"))
    assert sentinel not in json.dumps(graph.to_dict())
    assert exported["id"].endswith(selected["id"])
    assert exported["selection_key"] == selected["selection_key"]
    assert exported["framework_rule_versions"] == selected["framework_rule_versions"]
    assert exported["spring_properties_projection"]["original_context_id"] == selected["id"]
    assert (root / "producer/.kgmaker/graph.json").read_bytes() == before
    from kgmaker.views import select_service_contexts
    selection = select_service_contexts(graph, [{"service_id": "producer-svc", "repo_id": "producer", "module": "root"}],
        scope="production", repo_roots={"producer": root / "producer"})
    assert selection["services"][0]["status"] == "CURRENT"
    assert sentinel not in json.dumps(selection)
    validate_context_snapshot(root / "producer", selected)


@pytest.mark.parametrize("context_repo_id", ["producer", "local"])
def test_public_redacted_context_remains_selectable_from_valid_original(kafka_workspace, context_repo_id):
    from kgmaker.views import select_service_contexts
    root, manifest, _ = kafka_workspace
    sentinel = "SYNTHETIC_T006_PRIVATE_VALUE"
    original = captured_config_context(root, "producer", {"spring.kafka.password": sentinel, "orders.topic": "orders"}, context_repo_id=context_repo_id)
    graph = snapshot_workspace(manifest)[3]
    public = next(c for c in graph.contexts if c.get("repo_id") == "producer" and c.get("analyzer_version"))
    before_graph = copy.deepcopy(graph.to_dict())
    before_files = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    before_cache = copy.deepcopy(_REPO_CACHE)
    with patch("subprocess.Popen", side_effect=AssertionError("selection must not run a process")):
        selection = select_service_contexts(graph, [{"service_id": "producer-svc", "repo_id": "producer", "module": "root"}],
            scope="production", repo_roots={"producer": root / "producer"})
    assert selection["services"][0]["context_id"] == public["id"]
    assert selection["services"][0]["status"] == "CURRENT"
    assert sentinel not in json.dumps([selection, graph.to_dict()])
    assert graph.to_dict() == before_graph and _REPO_CACHE == before_cache
    assert before_files == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert public["selection_key"] == original["selection_key"]


@pytest.mark.parametrize("case", ["marker", "marker-hash", "original-id", "map", "public-id", "public-repo", "missing-root",
    "wrong-root", "missing-store", "duplicate-original", "source", "classpath", "forged-both-selector", "forged-both-condition"])
def test_redacted_context_selection_rejects_forgery_or_stale_original(kafka_workspace, case):
    import hashlib
    from kgmaker.views import ContextSelectionError, select_service_contexts
    root, manifest, _ = kafka_workspace
    sentinel = "SYNTHETIC_T006_PRIVATE_VALUE"
    dependency = root / "dep.jar"
    dependency.write_bytes(b"original dependency")
    original = captured_config_context(root, "producer", {"spring.kafka.password": sentinel},
        classpath=[{"path": str(dependency), "sha256": hashlib.sha256(dependency.read_bytes()).hexdigest()}])
    captured_config_context(root, "consumer", {"spring.kafka.password": sentinel})
    graph = snapshot_workspace(manifest)[3]
    public = next(c for c in graph.contexts if c.get("repo_id") == "producer" and c.get("analyzer_version"))
    store = root / "producer/.kgmaker/graph.json"
    roots = {"producer": root / "producer"}
    if case == "marker":
        public["spring_properties_projection"]["redacted"] = False
    elif case == "marker-hash":
        public["spring_properties_projection"]["sha256"] = "0" * 64
    elif case == "original-id":
        public["spring_properties_projection"]["original_context_id"] = "0" * 64
    elif case == "map":
        public["spring_properties"]["orders.topic"] = "forged"
    elif case == "public-id":
        public["id"] += "-forged"
    elif case == "public-repo":
        public["repo_id"] = "consumer"
    elif case == "missing-root":
        roots = None
    elif case == "wrong-root":
        roots["producer"] = root / "consumer"
    elif case == "missing-store":
        store.unlink()
    elif case == "source":
        (root / "producer/src/main/resources/application-blue.properties").write_text("orders.topic=edited\n")
    elif case == "classpath":
        dependency.write_bytes(b"changed dependency")
    else:
        payload = json.loads(store.read_text())
        raw = next(c for c in payload["contexts"] if c.get("id") == original["id"])
        if case == "duplicate-original":
            payload["contexts"].append(copy.deepcopy(raw))
        else:
            field = "selection_key" if case == "forged-both-selector" else "spring_condition_inputs_hash"
            raw[field] = public[field] = "f" * 64
        store.write_text(json.dumps(payload))
    before_graph = copy.deepcopy(graph.to_dict())
    before_files = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    before_cache = copy.deepcopy(_REPO_CACHE)
    with patch("subprocess.Popen", side_effect=AssertionError("failed selection must not run a process")):
        with pytest.raises(ContextSelectionError):
            select_service_contexts(graph, [{"service_id": "producer-svc", "repo_id": "producer", "module": "root"}],
                scope="production", repo_roots=roots)
    assert graph.to_dict() == before_graph and _REPO_CACHE == before_cache
    assert before_files == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

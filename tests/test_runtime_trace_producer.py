"""W01 closed runtime contract, actual JDK capture, and failure atomicity."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError, digest, file_hash
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.runtime_evidence import import_manifest, produce_manifest, validate_manifest
from kgmaker.store import load_graph, save_graph

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = dict(context_id="ctx", runtime_id="run-7", build_id="build-7",
               config_fingerprint="cfg-7", service_id="fixture-app", service_version="1.2.3")
ARTIFACT = Path(".kgmaker/runtime/trace.json")
CALL = {"kind": "call", "caller": "main", "target": "greet", "outcome": "RETURNED"}


@pytest.fixture
def project(tmp_path):
    source = tmp_path / "src/App.java"
    source.parent.mkdir()
    source.write_text("class App {}\n")
    worker = tmp_path / "worker.jar"
    worker.write_bytes(b"worker-test-double")
    context = {"id": "ctx", "scope": "production", "build_id": "build-7",
               "config_fingerprint": "cfg-7", "content_hash": digest("context"),
               "source_files": {"src/App.java": file_hash(source)},
               "worker": {"distribution": [{"path": str(worker), "sha256": file_hash(worker)}]}}
    symbols = [{"id": key, "kind": kind, "context_id": "ctx"} for key, kind in
               [("main", "method"), ("greet", "method"), ("factory", "method"),
                ("predicate", "method"), ("service", "class")]]
    nodes = [Node(s["id"], s["kind"], s["id"], "src/App.java", scope="production") for s in symbols]
    graph = KnowledgeGraph(3, ".", "now", nodes, [], context["source_files"], [context], symbols=symbols)
    save_graph(graph, tmp_path, generate_docs=False)
    (tmp_path / ".kgmaker/runtime").mkdir()
    (tmp_path / ARTIFACT).write_text("last-valid-artifact\n")
    return tmp_path


def command(capture):
    return [sys.executable, "-c", "print(" + repr(json.dumps(capture)) + ")"]


def capture(status="PARTIAL", facts=None):
    return {"facts": [CALL] if facts is None else facts, "status": status,
            "diagnostics": [] if status == "COMPLETE" else ["CAPTURE_INCOMPLETE" if status == "PARTIAL" else "CAPTURE_UNKNOWN"]}


def produce(root, raw=None, **kwargs):
    return produce_manifest(root, command(capture() if raw is None else raw),
                            **{**OPTIONS, "output": ARTIFACT, **kwargs})


def saved(root):
    return ((root / ".kgmaker/graph.json").read_bytes(), (root / ARTIFACT).read_bytes())


@pytest.mark.parametrize("status", ["PARTIAL", "UNKNOWN", "COMPLETE"])
def test_capture_status_is_preserved_without_availability_claim(project, status):
    before = (project / ".kgmaker/graph.json").read_bytes()
    manifest = produce(project, capture(status))
    assert manifest["status"] == status
    assert manifest["source_identity"]["source_manifest_fingerprint"] == digest(manifest["source_hashes"])
    assert manifest["service_id"] == "fixture-app" and manifest["service_version"] == "1.2.3"
    assert "availability" not in json.dumps(manifest)
    assert (project / ".kgmaker/graph.json").read_bytes() == before
    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        result = import_manifest(project, manifest)
    assert result["status"] == status and result["observations_imported"] == 0
    assert not load_graph(project).evidence  # W01 facts are not W02 import evidence.


def test_runtime_import_retains_same_edge_observations_and_v2_variant_identity(project):
    manifest = produce(project)
    observation = {"caller": "main", "target": "greet", "kind": "dispatch"}
    manifest["observations"] = [observation]
    legacy = {"schema_version": 1, "runtime_id": "legacy-run", "context_id": "ctx",
              "build_id": "build-7", "config_fingerprint": "cfg-7",
              "observations": [{**observation, "scenario": "legacy"}]}
    other_service = {**manifest, "service_id": "fixture-other", "service_version": "2.0.0"}
    graph = load_graph(project)
    snapshot = graph.contexts[0]
    graph.contexts.append({**snapshot, "id": "other-ctx", "build_id": "other-build",
                           "config_fingerprint": "other-config"})
    other_context = {**legacy, "context_id": "other-ctx", "build_id": "other-build",
                     "config_fingerprint": "other-config"}
    static_edges = [Edge("main", "predicate", "calls", source_line=line) for line in (4, 8)]
    graph.edges.extend(static_edges)
    save_graph(graph, project)

    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        for supplied in (legacy, manifest, other_context, other_service, other_service):
            assert import_manifest(project, supplied)["observations_imported"] == 1
        before = saved(project)
        with pytest.raises(AnalysisError, match="configuration fingerprint differs"):
            import_manifest(project, {**other_service, "config_fingerprint": "wrong"})
        assert saved(project) == before

    graph = load_graph(project)
    assert set(static_edges) <= set(graph.edges)
    observations = [edge for edge in graph.edges if edge.kind == "observed_dispatch_to"]
    assert {edge.context_ids for edge in observations} == {("ctx",), ("other-ctx",)}
    records = {item["id"]: item for item in graph.evidence}
    observed_ids = {edge.context_ids[0]: edge.evidence_ids for edge in observations}
    assert len(observed_ids["other-ctx"]) == 1
    assert records[observed_ids["other-ctx"][0]]["context_id"] == "other-ctx"
    proofs = [records[identity] for identity in observed_ids["ctx"]]
    assert len(proofs) == 3
    expected_legacy = {"kind": "RUNTIME_OBSERVED", "source": "main", "target": "greet",
                       "relation": "observed_dispatch_to", "runtime_id": "legacy-run",
                       "context_id": "ctx", "build_id": "build-7", "scenario": "legacy",
                       "async": False, "observation_source": None}
    assert {"id": "evidence:" + digest(expected_legacy), **expected_legacy} in proofs
    variants = [proof for proof in proofs if proof["runtime_id"] == OPTIONS["runtime_id"]]
    assert {(proof["service_id"], proof["service_version"]) for proof in variants} == {
        ("fixture-app", "1.2.3"), ("fixture-other", "2.0.0"),
    }
    assert all(proof["config_fingerprint"] == "cfg-7" and proof["build_id"] == "build-7"
               and proof["context_id"] == "ctx" and proof["source_identity"] == manifest["source_identity"]
               for proof in variants)
    from kgmaker.views import project as select_graph
    selected = select_graph(graph, "production", context_id="ctx")
    assert {item["id"] for item in selected.evidence} == set(observed_ids["ctx"])


def test_runtime_observation_stays_visible_without_creating_static_path_or_cycle(project):
    from kgmaker import callgraph

    manifest = produce(project)
    manifest["observations"] = [{"caller": "main", "target": "greet", "kind": "dispatch"}]
    graph = load_graph(project)
    graph.nodes.append(Node("site", "call_site", "site", "src/App.java", scope="production"))
    graph.call_sites.append({"id": "site", "caller": "greet", "declared_target": "main",
                             "dispatch_candidates": [], "context_id": "ctx",
                             "evidence_kind": "SYMBOL_RESOLVED", "resolution_reason": "static-fixture"})
    save_graph(graph, project)
    import_manifest(project, manifest)
    graph = load_graph(project)

    assert callgraph.path(graph, "main", "greet")["status"] == "UNKNOWN"
    result = callgraph.path(graph, "greet", "main")
    assert result["status"] == "STATIC_PATH"
    assert [step["kind"] for step in result["steps"]] == ["DECLARED_TARGET"]
    assert not callgraph.strongly_connected(graph)
    incoming, = callgraph.callers(graph, "greet")["results"]
    outgoing, = callgraph.callees(graph, "main")["results"]
    assert incoming["caller"] == "main"
    assert incoming["kind"] == outgoing["kind"] == "RUNTIME_OBSERVED"
    assert incoming["evidence_ids"] == outgoing["evidence_ids"]
    assert outgoing["target"] == "greet" and outgoing["dispatch_complete"] is False


@pytest.mark.parametrize("raw", [
    {"facts": [{"kind": "call"}], "status": "PARTIAL", "diagnostics": ["CAPTURE_INCOMPLETE"]},
    capture(facts=[{**CALL, "target": "unknown"}]),
    capture(facts=[{**CALL, "target": "service"}]),
    capture(facts=[{**CALL, "outcome": "guessed"}]),
    capture(facts=[{"kind": "bean", "factory": "factory", "bean_type": "service"}]),
    capture(facts=[{"kind": "condition", "owner": "main", "predicate": "predicate", "matched": "yes"}]),
    capture(facts=[{"kind": "mapping", "owner": "main", "handler": "greet", "method": "GET", "route_sha256": "invalid"}]),
    capture("COMPLETE", []), {"facts": [], "status": "PARTIAL", "diagnostics": []},
    {"facts": [CALL], "status": "invented", "diagnostics": []},
    {"facts": [CALL]}, [CALL],
])
def test_invalid_or_incomplete_facts_never_publish(project, raw):
    before = saved(project)
    with pytest.raises(AnalysisError):
        produce(project, raw)
    assert saved(project) == before


@pytest.mark.parametrize("field", ["diagnostics", "message", "facts", "observations"])
def test_free_text_credentials_and_url_fields_are_rejected_without_echo(project, field):
    raw = capture()
    secrets = "Authorization: Bearer VERYPRIVATE https://user:URLPASSWORD@host/?token=QUERYSECRET"
    if field == "facts":
        raw["facts"] = [{**CALL, "text": secrets, "password": secrets, "url": secrets}]
    else:
        raw[field] = [secrets]
    before = saved(project)
    with pytest.raises(AnalysisError) as error:
        produce(project, raw)
    assert saved(project) == before
    assert "VERYPRIVATE" not in str(error.value)
    assert "URLPASSWORD" not in str(error.value)


@pytest.mark.parametrize("change", ["source", "worker", "build", "config", "service", "version",
                                    "runtime", "context", "timeout_nan", "timeout_inf", "nul_argv",
                                    "path_escape", "path_directory", "path_symlink", "path_store",
                                    "path_source", "path_worker", "cancel"])
def test_preflight_rejects_before_spawn_and_keeps_artifact(project, change):
    opts = dict(OPTIONS, output=ARTIFACT)
    argv = command(capture())
    if change == "source":
        (project / "src/App.java").write_text("changed")
    elif change == "worker":
        (project / "worker.jar").write_bytes(b"changed")
    elif change in {"build", "config", "service", "version", "runtime", "context"}:
        key = {"build": "build_id", "config": "config_fingerprint", "service": "service_id",
               "version": "service_version", "runtime": "runtime_id", "context": "context_id"}[change]
        opts[key] = "different" if change in {"build", "config"} else ""
    elif change.startswith("timeout"):
        opts["timeout"] = float("nan" if change.endswith("nan") else "inf")
    elif change == "nul_argv":
        argv = [sys.executable, "\0"]
    elif change == "path_escape":
        opts["output"] = Path("../trace.json")
    elif change == "path_directory":
        (project / ".kgmaker/runtime/folder.json").mkdir()
        opts["output"] = Path(".kgmaker/runtime/folder.json")
    elif change == "path_symlink":
        (project / ".kgmaker/runtime/linked.json").symlink_to(project / ARTIFACT)
        opts["output"] = Path(".kgmaker/runtime/linked.json")
    elif change == "path_store":
        opts["output"] = Path(".kgmaker/graph.json")
    elif change == "path_source":
        opts["output"] = Path("src/App.java")
    elif change == "path_worker":
        opts["output"] = Path("worker.jar")
    elif change == "cancel":
        (project / "cancel").touch()
        opts["cancel_file"] = Path("cancel")
    before = saved(project)
    with patch("subprocess.Popen", side_effect=AssertionError("Preflight spawned a process")):
        with pytest.raises(AnalysisError):
            produce_manifest(project, argv, **opts)
    assert saved(project) == before


@pytest.mark.parametrize("field", ["service_id", "service_version", "source_identity", "source_hashes",
                                   "worker_distribution", "producer", "config_fingerprint", "extra"])
def test_v2_import_requires_complete_bound_identity_before_store_mutation(project, field):
    manifest = produce(project)
    before = saved(project)
    if field == "source_identity":
        manifest[field]["context_fingerprint"] = "forged"
    elif field == "extra":
        manifest[field] = "Authorization: Bearer VERYPRIVATE"
    else:
        del manifest[field]
    with pytest.raises(AnalysisError):
        import_manifest(project, manifest)
    assert saved(project) == before


@pytest.mark.parametrize("field", ["source", "worker", "graph", "output"])
def test_postflight_detects_mutation_without_publishing(project, field):
    marker = {"source": "src/App.java", "worker": "worker.jar", "graph": ".kgmaker/graph.json", "output": ARTIFACT.as_posix()}[field]
    if field == "output":
        action = "p.unlink(); p.symlink_to('../../src/App.java')"
    else:
        action = "p.write_text('changed')"
    code = "from pathlib import Path; p=Path(" + repr(marker) + "); " + action + "; print(" + repr(json.dumps(capture())) + ")"
    with pytest.raises(AnalysisError):
        produce_manifest(project, [sys.executable, "-c", code], **OPTIONS, output=ARTIFACT)
    if field != "output":
        assert (project / ARTIFACT).read_text() == "last-valid-artifact\n"
    else:
        assert (project / "src/App.java").read_text() == "class App {}\n"


@pytest.mark.parametrize("mode", ["timeout", "cancel", "leader_exit"])
def test_process_tree_cleanup_preserves_last_artifact(project, mode):
    child = "import time; from pathlib import Path; time.sleep(.7); Path('descendant-marker').touch()"
    parent = ("import subprocess,sys,time; from pathlib import Path; "
              "p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); "
              "Path('child-pid').write_text(str(p.pid)); ")
    if mode == "cancel":
        parent += "Path('cancel').touch(); time.sleep(10)"
    elif mode == "leader_exit":
        parent += "sys.exit(1)"  # Descendant keeps inherited stdout/stderr open.
    else:
        parent += "time.sleep(10)"
    before = saved(project)
    with pytest.raises(AnalysisError):
        produce_manifest(project, [sys.executable, "-c", parent], **OPTIONS,
                         output=ARTIFACT, timeout=.25, cancel_file=Path("cancel"))
    time.sleep(.8)
    assert not (project / "descendant-marker").exists()
    assert saved(project) == before
    pid_file = project / "child-pid"
    if pid_file.exists():
        stat = Path("/proc") / pid_file.read_text() / "stat"
        assert not stat.exists() or stat.read_text().split()[2] == "Z", "Descendant is still running"


def test_keyboard_interrupt_cleans_up_process_group(project):
    import kgmaker.worker_protocol as transport
    original = transport._exchange

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()

    with patch.object(transport, "_exchange", interrupted), patch.object(transport, "_terminate", wraps=transport._terminate) as cleanup:
        with pytest.raises(KeyboardInterrupt):
            produce_manifest(project, [sys.executable, "-c", "import time; time.sleep(10)"], **OPTIONS)
        assert cleanup.call_count == 1
    assert original is transport._exchange


@pytest.mark.parametrize("code", ["print('not JSON')", "raise SystemExit(9)",
                                  "print('{\"facts\":[],\"facts\":[]}')", "print('x'*9000000)"])
def test_invalid_process_output_never_mutates_store_or_artifact(project, code):
    before = saved(project)
    with pytest.raises(AnalysisError):
        produce_manifest(project, [sys.executable, "-c", code], **OPTIONS, output=ARTIFACT)
    assert saved(project) == before


@pytest.fixture(scope="module")
def jdk_application(tmp_path_factory):
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    root = tmp_path_factory.mktemp("runtime-jdk21")
    java_home = Path(os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-21-openjdk-amd64"))
    java, javac = java_home / "bin/java", java_home / "bin/javac"
    if not java.is_file() or not javac.is_file():
        pytest.skip("JDK21 runtime producer fixture requires actual java and javac")
    src = root / "src/main/java"
    src.mkdir(parents=True)
    shutil.copy(ROOT / "tests/fixtures/runtime-trace/TraceApplication.java", src)
    shutil.copy(ROOT / "tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java", src)
    classes = root / "classes"
    classes.mkdir()
    subprocess.run([str(javac), "--release", "21", "-d", str(classes), *map(str, src.glob("*.java"))],
                   check=True, capture_output=True)
    try:
        result = inspect_jvm(root, home=Path(os.environ.get("KGMAKER_WORKERS_HOME", ROOT / "workers")),
                             bytecode_roots=[str(classes)], build_context={"build_id": "fixture-build",
                             "config_fingerprint": digest({"fixture_mode": "enabled"}), "freshness": "EXECUTION_BOUND"})
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    graph = load_graph(root)
    selected = result["context"]
    symbols = {s["name"]: s["id"] for s in graph.symbols if (s.get("path") or "").endswith("TraceApplication.java")}
    ids = [symbols[name] for name in ("main", "createService", "TraceApplication$Service", "enabled", "greet")]
    argv = [str(java), "-cp", str(classes), "fixture.TraceApplication", *ids]
    opts = {**OPTIONS, "context_id": selected["id"], "build_id": "fixture-build",
            "config_fingerprint": selected["config_fingerprint"]}
    return root, argv, opts


def test_actual_jdk21_application_observes_all_four_kinds_and_no_values(jdk_application):
    root, argv, opts = jdk_application
    manifest = produce_manifest(root, argv, **opts, output=ARTIFACT)
    assert manifest["status"] == "PARTIAL"
    assert {f["kind"] for f in manifest["facts"]} == {"call", "bean", "condition", "mapping"}
    assert next(f for f in manifest["facts"] if f["kind"] == "call")["outcome"] == "RETURNED"
    assert next(f for f in manifest["facts"] if f["kind"] == "bean")["outcome"] == "CREATED"
    assert next(f for f in manifest["facts"] if f["kind"] == "condition")["matched"] is True
    text = json.dumps(manifest)
    assert all(secret not in text for secret in ("VERYPRIVATE", "URLPASSWORD", "QUERYSECRET", "Authorization", "example.invalid"))
    assert manifest["worker_distribution"] and manifest["source_hashes"]
    assert next(f for f in manifest["facts"] if f["kind"] == "mapping")["route_sha256"] == hashlib.sha256(b"/orders").hexdigest()
    validate_manifest(load_graph(root), root, manifest)


def test_actual_jdk21_capture_is_opt_in_and_records_only_executed_branch(jdk_application, monkeypatch):
    root, argv, opts = jdk_application
    env = {k: v for k, v in os.environ.items() if k != "KGMAKER_RUNTIME_TRACE"}
    assert subprocess.run(argv, cwd=root, env=env, capture_output=True, check=True).stdout == b""
    monkeypatch.setenv("FIXTURE_MODE", "disabled")
    manifest = produce_manifest(root, argv, **opts)
    assert {f["kind"] for f in manifest["facts"]} == {"bean", "condition"}
    assert next(f for f in manifest["facts"] if f["kind"] == "condition")["matched"] is False


@pytest.mark.parametrize("field", ["service_id", "service_version", "source_identity", "schema_version", "observations", "foreign_symbol"])
def test_v2_import_rejects_empty_forged_and_unknown_evidence(project, field):
    manifest = produce(project, capture("UNKNOWN"))
    before = saved(project)
    if field in {"service_id", "service_version"}:
        manifest[field] = ""
    elif field == "source_identity":
        manifest[field]["source_manifest_fingerprint"] = "0" * 64
    elif field == "schema_version":
        manifest[field] = 3
    elif field == "observations":
        manifest[field] = [{"caller": "main", "target": "greet"}]
    else:
        manifest["facts"][0]["target"] = "foreign"
    with pytest.raises(AnalysisError):
        import_manifest(project, manifest)
    assert saved(project) == before


def test_cli_explicit_argv_separator_and_output(project, capsys):
    from kgmaker.cli import main
    argv = ["runtime", "produce", "--root", str(project), "--context", "ctx",
            "--runtime-id", "run-7", "--build-id", "build-7", "--config-fingerprint", "cfg-7",
            "--service-id", "fixture-app", "--service-version", "1.2.3",
            "--output", str(ARTIFACT), "--", *command(capture())]
    with patch("sys.argv", ["kgmaker", *argv]), pytest.raises(SystemExit) as exit_result:
        main()
    assert exit_result.value.code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PARTIAL"


def test_real_compiler_source_change_fails_before_application_start(jdk_application):
    root, argv, opts = jdk_application
    source = root / "src/main/java/TraceApplication.java"
    before = source.read_bytes()
    try:
        source.write_bytes(before + b"// modified after inspection\n")
        with patch("subprocess.Popen", side_effect=AssertionError("Stale real context launched application")):
            with pytest.raises(AnalysisError):
                produce_manifest(root, argv, **opts)
    finally:
        source.write_bytes(before)


@pytest.mark.parametrize("kind", [{}, [], 4, None])
def test_v2_observation_kind_type_is_rejected_without_store_write(project, kind):
    manifest = produce(project)
    manifest["observations"] = [{"caller": "main", "target": "greet", "kind": kind}]
    before = saved(project)
    with pytest.raises(AnalysisError):
        import_manifest(project, manifest)
    assert saved(project) == before


@pytest.mark.parametrize(("endpoint", "kind"), [("caller", "dispatch"), ("target", None)])
def test_v2_runtime_requires_callable_endpoints_for_real_jdk21_symbols(jdk_application, endpoint, kind):
    root, argv, opts = jdk_application
    manifest = produce_manifest(root, argv, **opts, output=ARTIFACT)
    call = next(fact for fact in manifest["facts"] if fact["kind"] == "call")
    bean = next(fact for fact in manifest["facts"] if fact["kind"] == "bean")
    symbols = {symbol["id"]: symbol for symbol in load_graph(root).symbols}
    assert symbols[bean["bean_type"]]["kind"] == "class"
    observation = {key: call[key] for key in ("caller", "target")}
    observation[endpoint] = bean["bean_type"]
    if kind is not None:
        observation["kind"] = kind
    manifest["observations"] = [observation]
    before = saved(root)

    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        with pytest.raises(AnalysisError, match="require callable symbols"):
            import_manifest(root, manifest)
    assert saved(root) == before


def test_runtime_keeps_callable_and_framework_observations_and_legacy_import(project):
    manifest = produce(project)
    manifest["observations"] = [
        {"caller": "main", "target": "greet"},
        {"caller": "factory", "target": "service", "kind": "framework"},
    ]
    legacy = {"schema_version": 1, "runtime_id": "legacy-run", "context_id": "ctx",
              "build_id": "build-7", "config_fingerprint": "cfg-7",
              "observations": [{"caller": "main", "target": "predicate", "scenario": "legacy"}]}
    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        assert import_manifest(project, manifest)["observations_imported"] == 2
        assert import_manifest(project, legacy)["observations_imported"] == 1

    assert {(edge.source, edge.target, edge.kind) for edge in load_graph(project).edges} == {
        ("main", "greet", "observed_dispatch_to"),
        ("factory", "service", "runtime_framework_observation"),
        ("main", "predicate", "observed_dispatch_to"),
    }

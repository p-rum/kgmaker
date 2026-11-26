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


def compile_runtime_fixture(tmp_path_factory, temp_name, application):
    root = tmp_path_factory.mktemp(temp_name)
    java_home = Path(os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-21-openjdk-amd64"))
    java, javac = java_home / "bin/java", java_home / "bin/javac"
    if not java.is_file() or not javac.is_file():
        pytest.skip("JDK21 runtime producer fixture requires actual java and javac")
    src = root / "src/main/java"
    src.mkdir(parents=True)
    shutil.copy(ROOT / "tests/fixtures/runtime-trace" / application, src)
    shutil.copy(ROOT / "tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java", src)
    classes = root / "classes"
    classes.mkdir()
    subprocess.run([str(javac), "--release", "21", "-d", str(classes), *map(str, src.glob("*.java"))],
                   check=True, capture_output=True)
    return root, java, classes


def inspect_runtime_fixture(root, classes, build_id, config):
    from kgmaker.inspection import inspect_jvm
    from kgmaker.worker_protocol import WorkerError
    try:
        return inspect_jvm(root, home=Path(os.environ.get("KGMAKER_WORKERS_HOME", ROOT / "workers")),
                           bytecode_roots=[str(classes)], build_context={"build_id": build_id,
                               "config_fingerprint": config, "freshness": "EXECUTION_BOUND"})["context"]
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))


@pytest.fixture(scope="module")
def jdk_application(tmp_path_factory):
    root, java, classes = compile_runtime_fixture(tmp_path_factory, "runtime-jdk21", "TraceApplication.java")
    selected = inspect_runtime_fixture(root, classes, "fixture-build", digest({"fixture_mode": "enabled"}))
    graph = load_graph(root)
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


@pytest.fixture(scope="module")
def jdk_dispatch(tmp_path_factory):
    root, java, classes = compile_runtime_fixture(tmp_path_factory, "runtime-dispatch", "DispatchApplication.java")
    contexts = {variant: inspect_runtime_fixture(root, classes, "dispatch-" + variant, digest({"variant": variant}))
                for variant in ("alpha", "beta")}
    assert contexts["alpha"]["id"] != contexts["beta"]["id"]
    (root / ARTIFACT).parent.mkdir(exist_ok=True)
    return root, [str(java), "-cp", str(classes), "fixture.DispatchApplication"], contexts


def selected_dispatch_sites(graph, context, method):
    symbols = {item["id"]: item for item in graph.symbols if item["context_id"] == context["id"]}
    sites = [site for site in graph.call_sites if site["context_id"] == context["id"]
             and site.get("invocation_kind") == "INTERFACE" and site.get("representation") == "BYTECODE"
             and symbols[site["caller"]].get("owner") == "fixture.DispatchApplication"
             and symbols[site["caller"]].get("name") == method]
    return symbols, sites


def dispatch_options(context):
    return {**OPTIONS, "context_id": context["id"], "build_id": context["build_id"],
            "config_fingerprint": context["config_fingerprint"], "runtime_id": context["build_id"]}


@pytest.mark.parametrize("variant", ["alpha", "beta"])
def test_jdk21_interface_dispatch_binds_concrete_receiver_and_call_site(jdk_dispatch, variant, capsys):
    from kgmaker.callgraph import adjacency, callees
    from kgmaker.cli import build_parser
    from kgmaker.inspection_cli import run

    root, argv, contexts = jdk_dispatch
    context = contexts[variant]
    command_args = [*argv, variant, "direct"]
    env = {key: value for key, value in os.environ.items() if key != "KGMAKER_RUNTIME_TRACE"}
    assert subprocess.run(command_args, cwd=root, env=env, capture_output=True, check=True).stdout == b""
    graph = load_graph(root)
    symbols, (site,) = selected_dispatch_sites(graph, context, "invoke")
    options = dispatch_options(context)
    args = ["runtime", "produce", "--root", str(root), "--context", options.pop("context_id"), "--output", str(ARTIFACT)]
    for key, value in options.items():
        args.extend(("--" + key.replace("_", "-"), value))
    assert run(build_parser().parse_args([*args, "--", *command_args])) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert json.loads((root / ARTIFACT).read_bytes()) == manifest
    assert manifest["schema_version"] == 3 and manifest["observations"] == [] and manifest["status"] == "PARTIAL"
    fact, = manifest["facts"]
    expected_receiver = "fixture.DispatchApplication$" + variant.capitalize()
    assert fact["receiver_type"] == fact["target_owner"] == expected_receiver
    assert fact["source_line"] == site["source_line"]
    assert fact["caller_descriptor"] == symbols[site["caller"]]["descriptor"]
    assert not any(key in json.dumps(fact) for key in ("argument", "value", "outcome", "exception"))
    assert manifest["source_hashes"] == context["source_files"]
    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        assert run(build_parser().parse_args(["runtime", "import", "--root", str(root),
                                              "--manifest", str(root / ARTIFACT)])) == 0
    assert json.loads(capsys.readouterr().out)["observations_imported"] == 1
    updated = load_graph(root)
    receiver, = [symbol for symbol in symbols.values() if symbol.get("kind") == "class"
                 and symbol.get("owner") == expected_receiver]
    runtime, = [edge for edge in updated.edges if edge.evidence_kind == "RUNTIME_OBSERVED"
                and edge.context_ids == (context["id"],)]
    proof, = [record for record in updated.evidence if record["id"] in runtime.evidence_ids]
    assert proof["call_site"] == site["id"] and proof["receiver_type"] == receiver["id"]
    assert proof["config_fingerprint"] == context["config_fingerprint"]
    assert runtime.target in site["dispatch_candidates"] and symbols[runtime.target]["owner"] == expected_receiver
    assert {symbols[item]["owner"].rsplit("$", 1)[-1] for item in site["dispatch_candidates"]} == {"Alpha", "Beta"}
    assert adjacency(updated, include_runtime=False) == adjacency(graph, include_runtime=False)
    observed, = [row for row in callees(updated, runtime.source)["results"] if row["kind"] == "RUNTIME_OBSERVED"]
    assert observed["call_site"] == site["id"] and observed["receiver_type"] == receiver["id"]
    assert not observed["dispatch_complete"]


@pytest.mark.parametrize("method", ["ambiguous", "mixed"])
def test_jdk21_interface_dispatch_rejects_indistinguishable_sites_before_capture_publication(jdk_dispatch, method):
    root, argv, contexts = jdk_dispatch
    context = contexts["alpha"]
    graph = load_graph(root)
    _, (interface, *_) = selected_dispatch_sites(graph, context, method)
    sites = [site for site in graph.call_sites if site["caller"] == interface["caller"]]
    assert len(sites) == 2 and sites[0]["source_line"] == sites[1]["source_line"]
    assert sites[0]["instruction_index"] != sites[1]["instruction_index"]
    assert {site["invocation_kind"] for site in sites} == (
        {"INTERFACE"} if method == "ambiguous" else {"INTERFACE", "VIRTUAL"})
    (root / ARTIFACT).write_bytes(b"prior capture\n")
    before = saved(root)
    with pytest.raises(AnalysisError, match="RUNTIME_DISPATCH_SITE"):
        produce_manifest(root, [*argv, "alpha", method], **dispatch_options(context), output=ARTIFACT)
    assert saved(root) == before


def test_jdk21_interface_dispatch_revalidates_sanitized_fact_offline(jdk_dispatch):
    root, argv, contexts = jdk_dispatch
    context = contexts["alpha"]
    manifest = produce_manifest(root, [*argv, "alpha", "direct"], **dispatch_options(context), output=ARTIFACT)
    _, (other,) = selected_dispatch_sites(load_graph(root), context, "alternative")
    fact, = manifest["facts"]
    before = saved(root)
    for field, wrong, code in (
        ("source_line", other["source_line"], "RUNTIME_DISPATCH_SITE"),
        ("receiver_type", "fixture.DispatchApplication$Unknown", "RUNTIME_DISPATCH_RECEIVER"),
        ("target_owner", "fixture.DispatchApplication$Beta", "RUNTIME_DISPATCH_TARGET"),
        ("target_descriptor", "()V", "RUNTIME_DISPATCH_TARGET"),
    ):
        with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
            with pytest.raises(AnalysisError, match=code):
                import_manifest(root, {**manifest, "facts": [{**fact, field: wrong}]})
        assert saved(root) == before
    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        with pytest.raises(AnalysisError, match="configuration fingerprint"):
            import_manifest(root, {**manifest, "config_fingerprint": contexts["beta"]["config_fingerprint"]})
        with pytest.raises(AnalysisError, match="no supplied observations"):
            import_manifest(root, {**manifest, "observations": [{"caller": "x", "target": "y", "kind": "dispatch"}]})
        with pytest.raises(AnalysisError, match="missing or unsupported fields"):
            import_manifest(root, {**manifest, "schema_version": 2})
    assert saved(root) == before


def test_jdk21_interface_dispatch_rejects_stale_inputs_before_launch(jdk_dispatch):
    root, argv, contexts = jdk_dispatch
    context = contexts["alpha"]
    (root / ARTIFACT).write_bytes(b"prior capture\n")
    before = saved(root)
    command_args = [*argv, "alpha", "direct"]
    source = root / "src/main/java/DispatchApplication.java"
    original = source.read_bytes()
    with patch("subprocess.Popen", side_effect=AssertionError("Stale capture spawned a process")):
        with pytest.raises(AnalysisError, match="configuration fingerprint"):
            produce_manifest(root, command_args, **{
                **dispatch_options(context), "config_fingerprint": contexts["beta"]["config_fingerprint"],
            }, output=ARTIFACT)
        try:
            source.write_bytes(original + b"\n// stale probe\n")
            with pytest.raises(AnalysisError, match="STALE_RUNTIME: source changed"):
                produce_manifest(root, command_args, **dispatch_options(context), output=ARTIFACT)
        finally:
            source.write_bytes(original)
    assert saved(root) == before


def test_jdk21_interface_dispatch_rolls_back_if_bytecode_changes_during_publication(jdk_dispatch, monkeypatch, capsys):
    root, argv, contexts = jdk_dispatch
    produce_manifest(root, [*argv, "alpha", "direct"], **dispatch_options(contexts["alpha"]), output=ARTIFACT)
    changed = Path(argv[2]) / "fixture/DispatchApplication.class"
    assert_runtime_import_rolls_back_before_graph(root, changed, "STALE_INDEX: classpath", monkeypatch, capsys)


@pytest.mark.skipif(os.name != "posix", reason="Explicit Maven and runtime execution require POSIX")
def test_actual_maven_public_runtime_uses_selected_build_configuration(tmp_path, capsys, monkeypatch):
    from kgmaker.cli import main
    from kgmaker.inspection import command as compiler_command
    from kgmaker.worker_protocol import WorkerError

    java_home = Path(os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-21-openjdk-amd64"))
    java, javac = java_home / "bin/java", java_home / "bin/javac"
    workers = Path(os.environ.get("KGMAKER_WORKERS_HOME", ROOT / "workers"))
    maven = shutil.which("mvn")
    if not maven or not java.is_file() or not javac.is_file() or not (
            workers / "build/maven/target/kgmaker-build-export.jar").is_file():
        pytest.skip("Requires Maven, JDK 21 and a trusted Maven exporter")
    version = subprocess.run([str(javac), "-version"], capture_output=True, text=True, check=True)
    if not version.stdout.startswith(("javac 21.", "javac 21\n")):
        pytest.skip("Requires JDK 21")
    try:
        compiler_command("jvm", workers)
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            raise
        pytest.skip(str(error))

    def cli(*args, expected=(0,)):
        with patch("sys.argv", ["kgmaker", *map(str, args)]), pytest.raises(SystemExit) as result:
            main()
        out, err = capsys.readouterr()
        assert result.value.code in expected, out + err
        return json.loads(out)

    root = tmp_path / "project"
    source = root / "src/main/java/fixture"
    source.mkdir(parents=True)
    shutil.copy(ROOT / "tests/fixtures/runtime-trace/TraceApplication.java", source)
    shutil.copy(ROOT / "tooling/runtime/java/org/kgmaker/runtime/RuntimeTrace.java", source)
    (root / "pom.xml").write_text(
        """<project xmlns="http://maven.apache.org/POM/4.0.0">
          <modelVersion>4.0.0</modelVersion>
          <groupId>fixture</groupId><artifactId>runtime-config</artifactId><version>1</version>
          <properties><maven.compiler.release>21</maven.compiler.release></properties>
          <build><plugins><plugin><groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version>
          </plugin></plugins></build>
        </project>""", encoding="utf-8")
    plan, supplied = tmp_path / "plan.json", tmp_path / "supplied.json"
    cli("project", "build-plan", "--root", root, "--phase", "compile", "--offline", "--executable", maven,
        "--java-home", java_home, "--worker-home", workers, "--output", plan)
    execution = cli("project", "build-run", "--root", root, "--plan", plan, expected=(0, 3))
    result = execution["result"]
    if result["status"] != "SUCCESS":
        log = Path(result["log_path"]).read_text(encoding="utf-8")
        if (os.environ.get("KGMAKER_REQUIRE_WORKERS") != "1"
                and "offline mode" in log and "has not been downloaded" in log):
            pytest.skip("Maven fixture dependencies are unavailable offline")
        pytest.fail(log)
    manifest = json.loads(Path(execution["manifest_path"]).read_text(encoding="utf-8"))
    selected = next(context for context in manifest["contexts"] if context["id"] == "root:main")
    sibling = next(context for context in manifest["contexts"] if context["id"] == "root:test")
    assert "config_fingerprint" not in selected and "config_fingerprint" not in sibling
    build_id = manifest["build_id"]
    configured = hashlib.sha256(b"fixture-mode=enabled").hexdigest()
    manifest["config_fingerprint"] = hashlib.sha256(b"top-level-only").hexdigest()
    sibling["config_fingerprint"] = hashlib.sha256(b"different-source-set").hexdigest()
    output = root / ARTIFACT
    output.parent.mkdir(parents=True)
    output.write_bytes(b"previously published artifact\n")

    import_args = ("project", "build-import", "--root", root, "--manifest", supplied)
    inspect_args = ("inspect", "code", "--root", root, "--build-id", build_id, "--context", selected["id"],
                    "--worker-home", workers)

    def import_and_inspect():
        supplied.write_text(json.dumps(manifest), encoding="utf-8")
        with patch("subprocess.Popen", side_effect=AssertionError("Build import launched a process")):
            imported = cli(*import_args)
        path = Path(imported["manifest_path"])
        result = cli(*inspect_args)
        context = result["context"]
        assert context["build_context_id"] == selected["id"]
        assert context["manifest_hash"] == digest(json.loads(path.read_text(encoding="utf-8")))
        assert context["origin_trust"] == imported["origin_trust"] == "SUPPLIED_EXPORT_UNVERIFIED"
        assert context["freshness"] == "EXECUTION_BOUND"
        symbols = {symbol["name"]: symbol["id"] for symbol in result["graph"]["symbols"]
                   if symbol["context_id"] == context["id"]
                   and (symbol.get("path") or "").endswith("TraceApplication.java")}
        names = ("main", "createService", "TraceApplication$Service", "enabled", "greet")
        argv = [java, "-cp", selected["outputs"][0]["path"], "fixture.TraceApplication", *(symbols[name] for name in names)]
        return context, argv, path

    def produce(context, fingerprint, argv, *, expected=(0,)):
        return cli("runtime", "produce", "--root", root, "--context", context["id"], "--runtime-id", "declared-config",
                   "--build-id", build_id, "--config-fingerprint", fingerprint, "--service-id", "fixture-app",
                   "--service-version", "1", "--output", ARTIFACT, "--", *argv, expected=expected)

    context, argv, stored_manifest = import_and_inspect()
    assert "config_fingerprint" not in context
    initial = saved(root), stored_manifest.read_bytes()
    with patch("subprocess.Popen", side_effect=AssertionError("Missing configuration launched a process")):
        missing = produce(context, configured, argv, expected=(3,))
    assert missing["diagnostics"] == ["RuntimeManifest v2 requires captured source/config/context identity"]
    assert (saved(root), stored_manifest.read_bytes()) == initial

    selected["config_fingerprint"] = configured
    configured_context, argv, stored_manifest = import_and_inspect()
    assert configured_context["config_fingerprint"] == configured and configured_context["id"] != context["id"]
    initial = saved(root), stored_manifest.read_bytes()
    with patch("subprocess.Popen", side_effect=AssertionError("Mismatched configuration launched a process")):
        mismatched = produce(configured_context, sibling["config_fingerprint"], argv, expected=(3,))
    assert mismatched["diagnostics"] == ["STALE_RUNTIME: configuration fingerprint differs"]
    assert (saved(root), stored_manifest.read_bytes()) == initial

    monkeypatch.setenv("FIXTURE_MODE", "enabled")
    trace = produce(configured_context, configured, argv)
    assert trace["schema_version"] == 2 and trace["config_fingerprint"] == configured
    stored_context = next(context for context in load_graph(root).contexts if context["id"] == trace["context_id"])
    assert stored_context["config_fingerprint"] == configured
    assert trace["source_identity"]["context_fingerprint"] == digest(stored_context)
    assert trace["source_hashes"] == stored_context["source_files"]
    assert trace["status"] == "PARTIAL" and {fact["kind"] for fact in trace["facts"]} == {
        "bean", "call", "condition", "mapping",
    }
    assert json.loads(output.read_text(encoding="utf-8")) == trace
    assert (saved(root)[0], stored_manifest.read_bytes()) == (initial[0][0], initial[1])

    selected["config_fingerprint"] = "invalid-config-value"
    supplied.write_text(json.dumps(manifest), encoding="utf-8")
    initial = saved(root), stored_manifest.read_bytes()
    with patch("subprocess.Popen", side_effect=AssertionError("Invalid manifest launched a process")):
        invalid = cli(*import_args, expected=(2,))
        invalid_inspection = cli("inspect", "code", "--root", root, "--manifest", supplied,
                                 "--context", selected["id"], "--worker-home", workers, expected=(2,))
    assert invalid["diagnostics"] == invalid_inspection["diagnostics"]
    assert "config_fingerprint" in invalid["diagnostics"][0]
    assert "invalid-config-value" not in invalid["diagnostics"][0]
    assert (saved(root), stored_manifest.read_bytes()) == initial


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


@pytest.mark.parametrize("edit_at", ["before_save", "after_first_view"])
def test_real_jdk21_runtime_import_rejects_source_edit_after_validation(jdk_application, monkeypatch, edit_at):
    from kgmaker import store

    root, argv, opts = jdk_application
    manifest = produce_manifest(root, argv, **opts, output=ARTIFACT)
    call = next(fact for fact in manifest["facts"] if fact["kind"] == "call")
    manifest["observations"] = [{"caller": call["caller"], "target": call["target"], "kind": "dispatch"}]
    outputs = [root / path for path in (store.GRAPH_FILE, store.MARKDOWN_FILE, store.MERMAID_FILE, ARTIFACT)]
    before = {path: path.read_bytes() for path in outputs}
    source = root / "src/main/java/TraceApplication.java"
    original = source.read_bytes()
    edited = original + b"// edited after runtime validation\n"

    if edit_at == "before_save":
        def save_after_edit(*args, **kwargs):
            source.write_bytes(edited)
            return save_graph(*args, **kwargs)

        monkeypatch.setattr(store, "save_graph", save_after_edit)
    else:
        real_replace = store.os.replace

        def replace_and_edit(temporary, destination):
            real_replace(temporary, destination)
            if destination == root / store.MERMAID_FILE and source.read_bytes() == original:
                source.write_bytes(edited)

        monkeypatch.setattr(store.os, "replace", replace_and_edit)

    try:
        with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
            with pytest.raises(AnalysisError, match="STALE_RUNTIME: source changed"):
                import_manifest(root, manifest)
        assert source.read_bytes() == edited
        assert {path: path.read_bytes() for path in outputs} == before
        assert not (root / store.PUBLICATION_LOCK).exists()
        assert not list((root / store.STATE_DIR).rglob(".kgmaker-*"))
    finally:
        source.write_bytes(original)


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


def test_runtime_import_validates_payload_once_and_rechecks_inputs_per_publication_step(project, monkeypatch):
    from kgmaker import graph_provider, runtime_evidence, store

    class CountedObservations(list):
        walks = 0

        def __iter__(self):
            self.walks += 1
            return super().__iter__()

    manifest = produce(project)
    observations = CountedObservations([{"caller": "main", "target": "greet", "kind": "dispatch"}])
    manifest["observations"] = observations
    checked = {project / "src/App.java": [], project / "worker.jar": []}
    context_checks, replaced = [], []
    actual_replace = store.os.replace
    actual_snapshot = graph_provider.validate_context_snapshot

    def publication_step():
        return (project / store.PUBLICATION_LOCK).exists(), tuple(replaced)

    def hash_tracked_input(path):
        if path in checked:
            checked[path].append(publication_step())
        return file_hash(path)

    def check_context_snapshot(root, context):
        context_checks.append(publication_step())
        return actual_snapshot(root, context)

    def replace_output(source, destination):
        actual_replace(source, destination)
        replaced.append(destination.relative_to(project))

    monkeypatch.setattr(runtime_evidence, "file_hash", hash_tracked_input)
    monkeypatch.setattr(graph_provider, "validate_context_snapshot", check_context_snapshot)
    monkeypatch.setattr(store.os, "replace", replace_output)
    with (
        patch.object(runtime_evidence, "validate_manifest", wraps=validate_manifest) as validate,
        patch.object(runtime_evidence, "_validate_capture", wraps=runtime_evidence._validate_capture) as capture_check,
        patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")),
    ):
        assert import_manifest(project, manifest)["observations_imported"] == 1

    # Initial validation, before preparing outputs, and before each replacement.
    expected = [
        (False, ()),
        (True, ()),
        (True, ()),
        (True, (store.MERMAID_FILE,)),
        (True, (store.MERMAID_FILE, store.MARKDOWN_FILE)),
    ]
    assert all(checks == expected for checks in checked.values())
    assert context_checks == expected
    assert replaced == [store.MERMAID_FILE, store.MARKDOWN_FILE, store.GRAPH_FILE]
    assert (validate.call_count, capture_check.call_count, observations.walks) == (1, 1, 1)


def assert_runtime_import_rolls_back_before_graph(root, changed_input, diagnostic, monkeypatch, capsys):
    from kgmaker import inspection_cli, store
    from kgmaker.cli import build_parser

    paths = [root / path for path in (store.GRAPH_FILE, store.MERMAID_FILE, store.MARKDOWN_FILE, ARTIFACT)]
    before = {path: path.read_bytes() for path in paths}
    original = changed_input.read_bytes()
    edited = original + b"changed after replacing both reports"
    actual_replace = store.os.replace
    views = [store.MERMAID_FILE, store.MARKDOWN_FILE]
    replaced = []

    def replace_output(source, destination):
        actual_replace(source, destination)
        replaced.append(destination.relative_to(root))
        if replaced == views:
            changed_input.write_bytes(edited)

    args = build_parser().parse_args(["runtime", "import", "--root", str(root), "--manifest", str(root / ARTIFACT)])
    monkeypatch.setattr(store.os, "replace", replace_output)
    try:
        with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
            assert inspection_cli.run(args) == 3
        assert any(diagnostic in text for text in json.loads(capsys.readouterr().out)["diagnostics"])
        assert changed_input.read_bytes() == edited
        assert replaced == views + views[::-1]
        assert {path: path.read_bytes() for path in paths} == before
        assert not (root / store.PUBLICATION_LOCK).exists()
        assert not list((root / store.STATE_DIR).rglob(".kgmaker-*"))
    finally:
        changed_input.write_bytes(original)


def test_real_jdk21_v2_cli_rechecks_bytecode_before_graph(jdk_application, monkeypatch, capsys):
    root, argv, opts = jdk_application
    manifest = produce_manifest(root, argv, **opts, output=ARTIFACT)
    call = next(fact for fact in manifest["facts"] if fact["kind"] == "call")
    manifest["observations"] = [{"caller": call["caller"], "target": call["target"], "kind": "dispatch"}]
    (root / ARTIFACT).write_text(json.dumps(manifest))
    context = next(item for item in load_graph(root).contexts if item["id"] == manifest["context_id"])
    assert context["bytecode_artifacts"]
    assert_runtime_import_rolls_back_before_graph(
        root, root / "classes/fixture/TraceApplication.class", "STALE_INDEX: classpath",
        monkeypatch, capsys,
    )


def test_v1_cli_rechecks_worker_before_graph(project, monkeypatch, capsys):
    root = project
    save_graph(load_graph(root), root)
    manifest = {"schema_version": 1, "runtime_id": "runtime-v1", "context_id": "ctx",
                "build_id": "build-7", "config_fingerprint": "cfg-7",
                "observations": [{"caller": "main", "target": "greet", "kind": "dispatch"}]}
    (root / ARTIFACT).write_text(json.dumps(manifest))
    assert_runtime_import_rolls_back_before_graph(
        root, root / "worker.jar", "STALE_RUNTIME: worker distribution changed", monkeypatch, capsys,
    )


def test_real_jdk21_v2_import_detaches_identity_before_publication(jdk_application, monkeypatch):
    from kgmaker import store

    root, argv, opts = jdk_application
    manifest = produce_manifest(root, argv, **{**opts, "runtime_id": "identity-race"}, output=ARTIFACT)
    call = next(fact for fact in manifest["facts"] if fact["kind"] == "call")
    manifest["observations"] = [{"caller": call["caller"], "target": call["target"], "kind": "dispatch"}]
    caller_identity = manifest["source_identity"]
    validated_identity = dict(caller_identity)
    capture_bytes = (root / ARTIFACT).read_bytes()

    def save_after_caller_edit(candidate, destination, **kwargs):
        caller_identity["context_fingerprint"] = "0" * 64
        return save_graph(candidate, destination, **kwargs)

    monkeypatch.setattr(store, "save_graph", save_after_caller_edit)
    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        outcome = import_manifest(root, manifest)

    assert outcome["status"] == "PARTIAL" and outcome["observations_imported"] == 1
    assert caller_identity["context_fingerprint"] == "0" * 64
    assert (root / ARTIFACT).read_bytes() == capture_bytes
    graph = load_graph(root)
    proof, = [item for item in graph.evidence if item.get("runtime_id") == "identity-race"]
    record_id = "evidence:" + digest({key: value for key, value in proof.items() if key != "id"})
    assert (proof["source_identity"], record_id) == (validated_identity, proof["id"])
    assert any(edge.kind == "observed_dispatch_to" and proof["id"] in edge.evidence_ids for edge in graph.edges)


@pytest.mark.parametrize("edit_at", ["input_hash_check", "after_admission", "second_observation_walk"])
def test_real_jdk21_v2_import_publishes_only_admitted_values(jdk_application, monkeypatch, edit_at):
    from kgmaker import callgraph, runtime_evidence, store

    root, argv, opts = jdk_application
    runtime_id = "admission-" + edit_at
    manifest = produce_manifest(root, argv, **{**opts, "runtime_id": runtime_id}, output=ARTIFACT)
    call = next(fact for fact in manifest["facts"] if fact["kind"] == "call")
    invalid_target = next(fact["bean_type"] for fact in manifest["facts"] if fact["kind"] == "bean")
    symbols = {symbol["id"]: symbol for symbol in load_graph(root).symbols}
    assert symbols[call["target"]]["kind"] == "method"
    assert symbols[invalid_target]["kind"] == "class"
    assert symbols[invalid_target]["context_id"] == manifest["context_id"]
    row = {"caller": call["caller"], "target": call["target"], "kind": "dispatch"}
    manifest["observations"] = [row]
    invalid_config = "wrong-config-after-admission"
    paths = (store.GRAPH_FILE, store.MARKDOWN_FILE, store.MERMAID_FILE, ARTIFACT)
    before = {path: (root / path).read_bytes() for path in paths}

    with patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")):
        with pytest.raises(AnalysisError, match="configuration fingerprint differs"):
            import_manifest(root, {**manifest, "config_fingerprint": invalid_config})
        with pytest.raises(AnalysisError, match="require callable symbols"):
            import_manifest(root, {**manifest, "observations": [{**row, "target": invalid_target}]})
        assert {path: (root / path).read_bytes() for path in paths} == before

    class CallerObservations(list):
        walks = 0

        def __iter__(self):
            self.walks += 1
            if self.walks == 2:
                row["target"] = invalid_target
            return super().__iter__()

    if edit_at == "input_hash_check":
        check_hashes = runtime_evidence._check_hashes

        def check_hashes_then_edit(root, context, supplied=None):
            check_hashes(root, context, supplied)
            if supplied is not None:
                manifest["config_fingerprint"] = invalid_config

        monkeypatch.setattr(runtime_evidence, "_check_hashes", check_hashes_then_edit)
    elif edit_at == "after_admission":
        def validate_then_edit(*args, **kwargs):
            admitted = validate_manifest(*args, **kwargs)
            row["target"] = invalid_target
            return admitted
    else:
        observations = CallerObservations([row])
        manifest["observations"] = observations

    validator = validate_then_edit if edit_at == "after_admission" else validate_manifest
    with (
        patch.object(runtime_evidence, "validate_manifest", wraps=validator) as validate,
        patch("subprocess.Popen", side_effect=AssertionError("Import spawned a process")),
    ):
        outcome = import_manifest(root, manifest)

    assert validate.call_count == 1
    assert outcome["status"] == "PARTIAL" and outcome["observations_imported"] == 1
    assert (root / ARTIFACT).read_bytes() == before[ARTIFACT]
    graph = load_graph(root)
    proof, = [item for item in graph.evidence if item.get("runtime_id") == runtime_id]
    assert proof["config_fingerprint"] == opts["config_fingerprint"]
    assert proof["target"] == call["target"]
    assert proof["id"] == "evidence:" + digest({key: value for key, value in proof.items() if key != "id"})
    edge, = [edge for edge in graph.edges if proof["id"] in edge.evidence_ids]
    assert (edge.kind, edge.target) == ("observed_dispatch_to", call["target"])
    reported, = [result for result in callgraph.callees(graph, call["caller"])["results"]
                 if proof["id"] in result["evidence_ids"]]
    assert (reported["kind"], reported["target"]) == ("RUNTIME_OBSERVED", call["target"])
    if edit_at == "input_hash_check":
        assert manifest["config_fingerprint"] == invalid_config
    elif edit_at == "after_admission":
        assert row["target"] == invalid_target
    else:
        assert observations.walks == 1

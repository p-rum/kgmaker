"""T003-S04-W01: real pinned FIR Analysis API, plus fail-closed selection."""
import os
import io
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.graph_provider import _inspection_command, retain_compiler_layer
from kgmaker.inspection import command, inspect_jvm
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.store import load_graph
from kgmaker.worker_protocol import WorkerError, handshake, request_worker

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "workers"


@pytest.mark.parametrize("backend,version", [("k2", "2.2.0"), ("k3", "2.1.10"), ("k1", "unknown"), (["k2"], "2.1.10")])
def test_unsupported_backend_or_version_never_runs_or_mutates(backend, version, tmp_path):
    store = tmp_path / ".kgmaker/graph.json"
    store.parent.mkdir()
    store.write_bytes(b"last valid generation")
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        with pytest.raises(AnalysisError, match="Unsupported Kotlin"):
            inspect_jvm(tmp_path, kotlin_backend=backend, kotlin_version=version, home=HOME)
    assert store.read_bytes() == b"last valid generation"


def test_imported_unsupported_k2_compiler_version_fails_before_worker(tmp_path):
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        with pytest.raises(AnalysisError, match="imported compiler version differs"):
            inspect_jvm(tmp_path, kotlin_backend="k2", home=HOME,
                        build_context={"compiler_options": {"kotlin": {"compiler_version": "2.2.20"}}})


@pytest.mark.parametrize("context", [{"compiler_options": []}, {"compiler_options": {"kotlin": []}},
                                     {"compiler_options": {"kotlin": {"language_version": []}}}])
def test_malformed_k2_options_fail_structurally_before_worker(context, tmp_path):
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        with pytest.raises(AnalysisError):
            inspect_jvm(tmp_path, kotlin_backend="k2", home=HOME, build_context=context)


@pytest.mark.parametrize("options", [{"language_version": "2.2"}, {"api_version": "1.9"},
                                     {"jvm_target": "17"}, {"plugins": ["all-open"]},
                                     {"free_args": ["-Xcontext-receivers"]}, {"progressive": True}])
def test_unsupported_captured_k2_options_are_not_silently_ignored(options, tmp_path):
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        with pytest.raises(AnalysisError, match="Unsupported K2"):
            inspect_jvm(tmp_path, kotlin_backend="k2", home=HOME,
                        build_context={"compiler_options": {"kotlin": options}})


def test_explicit_k2_fetch_rejects_wrong_bytes_without_publishing(tmp_path):
    with patch("sys.argv", ["fetch_k2.py", "--output", str(tmp_path)]), \
         patch("urllib.request.urlopen", return_value=io.BytesIO(b"wrong artifact")):
        with pytest.raises(SystemExit, match="Dependency checksum/size mismatch"):
            runpy.run_path(str(HOME / "jvm/fetch_k2.py"), run_name="__main__")
    assert list(tmp_path.iterdir()) == []


def test_missing_k2_distribution_never_falls_back_to_k1(tmp_path):
    plain = tmp_path / "jvm/target/kgmaker-jvm-worker.jar"
    plain.parent.mkdir(parents=True)
    plain.write_bytes(b"K1 exists but must never be selected")
    java = tmp_path / 'jdk/bin/java.exe'
    java.parent.mkdir(parents=True)
    java.write_bytes(b'not executed')
    (java.parent / 'javac.exe').write_bytes(b'not executed')
    with patch("subprocess.Popen", side_effect=AssertionError("implicit fallback process")), \
         patch("kgmaker.inspection.shutil.which", return_value=str(java)):
        with pytest.raises(WorkerError, match="Kotlin backend k2") as caught:
            inspect_jvm(tmp_path, kotlin_backend="k2", home=tmp_path)
    assert caught.value.status == "TOOLCHAIN_UNAVAILABLE"


@pytest.mark.parametrize("version", [1, 2, 3])
def test_existing_graph_loader_is_unchanged(version):
    graph = KnowledgeGraph.from_dict({"schema_version": version, "root": ".", "generated_at": "",
                                      "files": {}, "nodes": [], "edges": []})
    assert graph.schema_version == version


@pytest.fixture(scope="module")
def actual_k2():
    try:
        argv = command("jvm", HOME, kotlin_backend="k2")
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_K2") == "1":
            pytest.fail(str(error))
        pytest.skip("blocked: explicit K2 worker build and JDK required")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        java = root / "src/main/java/fixture/Helper.java"
        kotlin = root / "src/main/kotlin/fixture/Work.kt"
        test = root / "src/test/kotlin/Excluded.kt"
        for path in (java, kotlin, test):
            path.parent.mkdir(parents=True, exist_ok=True)
        java.write_text("package fixture; public class Helper { public static int plus(int x) { return x + 1; } }")
        kotlin.write_text("""package fixture
fun target(x: Int): Int = Helper.plus(x)
fun caller(): Int = target(3)
fun jdk(x: Int): Int = java.lang.Math.abs(x)
fun mappedBuiltin(s: String): String = s.substring(1)
fun missing(): Int = absent(4)
fun pick(x: String?): Int = 1
fun pick(x: Int?): Int = 2
fun ambiguous(): Int = pick(null)
""")
        test.write_text("fun excludedTestSymbol(): Int = 42")
        stdlib = HOME / "jvm/target-k2/lib/kotlin-stdlib.jar"
        options = {"kotlin_backend": "k2", "home": HOME, "classpath": [str(stdlib)],
                   "repo_id": "k2-fixture", "module": "core", "publish": False,
                   "build_context": {"compiler_options": {"kotlin": {"schema_version": 1,
                       "status": "CAPTURED_CONFIGURATION", "compiler_version": "2.1.10",
                       "language_version": "2.1", "api_version": "2.1", "jvm_target": "21"}}}}
        first = inspect_jvm(root, **options)
        yield root, options, first, argv


def test_real_mixed_k2_calls_have_stable_jvm_symbols_and_backend_evidence(actual_k2):
    root, options, first, _ = actual_k2
    second = inspect_jvm(root, **options)
    calls = [site for site in first["graph"]["call_sites"] if site["path"].endswith("Work.kt")]
    actual = {(c["caller"].split(":method:")[-1], c["declared_target"].split(":method:")[-1])
              for c in calls if c.get("declared_target")}
    assert actual == {("fixture.WorkKt.target(I)I", "fixture.Helper.plus(I)I"),
                      ("fixture.WorkKt.caller()I", "fixture.WorkKt.target(I)I"),
                      ("fixture.WorkKt.jdk(I)I", "java.lang.Math.abs(I)I")}
    assert [c["id"] for c in first["graph"]["call_sites"]] == [c["id"] for c in second["graph"]["call_sites"]]
    assert first["context"]["worker"]["kotlin_backend"] == "k2-analysis-api-2.1.10-v1"
    assert "kotlin-2.1-analysis-api-attribution" in first["context"]["worker"]["capabilities"]
    assert not any("excludedTestSymbol" in s["name"] for s in first["graph"]["symbols"])
    for site in calls:
        for identity in site["evidence_ids"]:
            proof = next(e for e in first["graph"]["evidence"] if e["id"] == identity)
            assert proof["compiler_backend"] == "k2-analysis-api-2.1.10-v1"
            assert proof["compiler_version"] == "2.1.10"


def test_unresolved_and_ambiguous_k2_calls_remain_partial(actual_k2):
    _, _, result, _ = actual_k2
    unresolved = [site for site in result["graph"]["call_sites"]
                  if site.get("evidence_kind") == "UNRESOLVED" and site["path"].endswith("Work.kt")]
    assert {site["caller"].split(":method:")[-1] for site in unresolved} == {
        "fixture.WorkKt.missing()I", "fixture.WorkKt.ambiguous()I",
        "fixture.WorkKt.mappedBuiltin(Ljava/lang/String;)Ljava/lang/String;"}
    assert all(site["declared_target"] is None and not site["dispatch_candidates"] for site in unresolved)
    assert all(site["resolution_reason"] == "K2_UNRESOLVED_OR_UNSUPPORTED_CALL" for site in unresolved)
    assert result["status"] == "PARTIAL"
    assert any(d["code"] == "K2_SOURCE_CFG_UNSUPPORTED" for d in result["diagnostics"])


def test_direct_worker_rejects_unsupported_version_and_backend(actual_k2):
    root, _, _, argv = actual_k2
    for selection in ({"kotlin_version": "2.2.0"}, {"kotlin_backend": "k1"}):
        with pytest.raises(WorkerError) as caught:
            request_worker(argv, {"operation": "analyze", **selection}, cwd=root)
        assert caught.value.status == "FAILED"


def test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph(actual_k2):
    root, options, _, _ = actual_k2
    result = inspect_jvm(root, **{**options, "publish": True})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    strict = inspect_jvm(root, **{**options, "strict": True, "publish": True})
    assert strict["exit_code"] == 4
    assert store.read_bytes() == before
    assert "--kotlin-backend k2" in _inspection_command(result["context"])
    with patch("subprocess.Popen", side_effect=AssertionError("offline refresh spawned process")):
        graph = retain_compiler_layer(root, scan_repository(root))
    assert any(c.get("kotlin_backend") == "k2" for c in graph.contexts)


def test_k1_distribution_stays_explicitly_limited():
    try:
        argv = command("jvm", HOME, kotlin_backend="k1")
    except WorkerError:
        pytest.skip("blocked: explicit K1 worker build and JDK required")
    meta = handshake(argv, cwd=ROOT)
    assert meta.get("kotlin_backend") == "k1-compat-1"
    assert "kotlin-1.9-compatible-attribution" in meta["capabilities"]
    assert "kotlin-2.1-analysis-api-attribution" not in meta["capabilities"]


def test_k1_and_k2_contexts_accumulate_without_replacement(actual_k2, tmp_path):
    source = tmp_path / "src/main/kotlin/Coexist.kt"
    source.parent.mkdir(parents=True)
    source.write_text("fun target(): Int = 1\nfun caller(): Int = target()\n")
    results = []
    for backend in ("k1", "k2"):
        target = "target" if backend == "k1" else "target-k2"
        results.append(inspect_jvm(tmp_path, home=HOME, kotlin_backend=backend,
                                  classpath=[str(HOME / "jvm" / target / "lib/kotlin-stdlib.jar")]))
    assert results[0]["context"]["selection_key"] != results[1]["context"]["selection_key"]
    contexts = [context for context in load_graph(tmp_path).contexts if context.get("analyzer_version")]
    assert {context["kotlin_backend"] for context in contexts} == {"k1", "k2"}
    with patch("subprocess.Popen", side_effect=AssertionError("offline process")):
        fresh = retain_compiler_layer(tmp_path, scan_repository(tmp_path))
    assert {context["kotlin_backend"] for context in fresh.contexts if context.get("analyzer_version")} == {"k1", "k2"}


def test_inner_constructor_does_not_invent_incomplete_jvm_abi(actual_k2, tmp_path):
    source = tmp_path / "src/main/kotlin/Inner.kt"
    source.parent.mkdir(parents=True)
    source.write_text("class Outer { inner class Inner }\nfun construct(outer: Outer): Any = outer.Inner()\n")
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend="k2", publish=False,
                         classpath=[str(HOME / "jvm/target-k2/lib/kotlin-stdlib.jar")])
    calls = result["graph"]["call_sites"]
    assert len(calls) == 1
    assert calls[0]["invocation_kind"] == "CONSTRUCTOR"
    # JVM ABI needs an enclosing Outer parameter absent from source light PSI.
    assert calls[0]["declared_target"] is None
    assert calls[0]["evidence_kind"] == "UNRESOLVED"


def test_intrinsic_light_method_without_jvm_member_is_unresolved(actual_k2, tmp_path):
    source = tmp_path / "src/main/kotlin/Intrinsic.kt"
    source.parent.mkdir(parents=True)
    source.write_text("fun intrinsic(): Int = 1.plus(2)\n")
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend="k2", publish=False,
                         classpath=[str(HOME / "jvm/target-k2/lib/kotlin-stdlib.jar")])
    calls = result["graph"]["call_sites"]
    assert len(calls) == 1
    assert calls[0]["declared_target"] is None
    assert calls[0]["evidence_kind"] == "UNRESOLVED"


def test_local_class_and_object_initializers_do_not_become_outer_calls(actual_k2, tmp_path):
    source = tmp_path / "src/main/kotlin/Local.kt"
    source.parent.mkdir(parents=True)
    source.write_text("""fun target(): Int = 1
fun outer() { class Local { val x = target(); init { target() } } }
fun objectLiteral() { val ref = object { val x = target(); init { target() } } }
fun outerWithLive() { class Local { val x = target() }; target() }
""")
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend="k2", publish=False,
                         classpath=[str(HOME / "jvm/target-k2/lib/kotlin-stdlib.jar")])
    calls = result["graph"]["call_sites"]
    assert len(calls) == 1, "unsupported nested initializers were attributed to outer execution"
    assert calls[0]["caller"].endswith(":method:LocalKt.outerWithLive()V")
    assert calls[0]["declared_target"].endswith(":method:LocalKt.target()I")
    assert result["status"] == "PARTIAL"
    diagnostics = [item for item in result["diagnostics"] if item["code"] in {
        "K2_LOCAL_CLASS_BODY_UNSUPPORTED", "K2_OBJECT_LITERAL_BODY_UNSUPPORTED"}]
    assert {item["code"] for item in diagnostics} == {
        "K2_LOCAL_CLASS_BODY_UNSUPPORTED", "K2_OBJECT_LITERAL_BODY_UNSUPPORTED"}
    assert all(item["path"] == "src/main/kotlin/Local.kt" and item["range"]["start_line"] in {2, 3, 4}
               for item in diagnostics)


def test_kotlin_call_preserves_authoritative_javac_declaration_metadata(actual_k2, tmp_path):
    java = tmp_path / "src/main/java/Helper.java"
    java.parent.mkdir(parents=True)
    java.write_text("public class Helper { @Deprecated public static int plus(int x) "
                    "throws IllegalArgumentException { return x+1; } }")
    options = {"home": HOME, "kotlin_backend": "k2", "publish": False,
               "classpath": [str(HOME / "jvm/target-k2/lib/kotlin-stdlib.jar")]}
    before = inspect_jvm(tmp_path, **options)
    kotlin = tmp_path / "src/main/kotlin/Caller.kt"
    kotlin.parent.mkdir(parents=True)
    kotlin.write_text("fun caller(): Int = Helper.plus(1)\n")
    mixed = inspect_jvm(tmp_path, **options)
    def declaration(result):
        return next(symbol for symbol in result["graph"]["symbols"]
                    if symbol.get("owner") == "Helper" and symbol["name"] == "plus")
    original, retained = declaration(before), declaration(mixed)
    assert original["annotations"] and original["throws"] == ["java.lang.IllegalArgumentException"]
    assert original["return_type"] == "int" and original["modifiers"] == ["public", "static"]
    for key in ("annotations", "modifiers", "return_type", "throws", "parameter_types", "parameter_names",
                "path", "range", "sha256", "compiler_backend"):
        assert retained.get(key) == original.get(key), key
    site = next(site for site in mixed["graph"]["call_sites"] if site["path"].endswith("Caller.kt"))
    assert site["declared_target"] == retained["id"]
    assert site["compiler_backend"] == "k2-analysis-api-2.1.10-v1"


def test_class_only_kotlin_never_claims_complete_source_coverage(actual_k2, tmp_path):
    source = tmp_path / "src/main/kotlin/Empty.kt"
    source.parent.mkdir(parents=True)
    source.write_text("class Empty\n")
    result = inspect_jvm(tmp_path, home=HOME, kotlin_backend="k2", publish=False,
                         classpath=[str(HOME / "jvm/target-k2/lib/kotlin-stdlib.jar")])
    assert result["status"] == "PARTIAL"
    diagnostic = next(item for item in result["diagnostics"] if item["code"] == "K2_SOURCE_MODEL_PARTIAL")
    assert diagnostic["path"] == "src/main/kotlin/Empty.kt"
    assert diagnostic["range"]["start_line"] == 1 and diagnostic["sha256"]

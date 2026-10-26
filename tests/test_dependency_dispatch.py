"""T003-S04-W04: actual ordered dependency JAR dispatch, never execution."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from kgmaker.analysis_model import AnalysisError
from kgmaker.inspection import command, inspect_jvm
from kgmaker.worker_protocol import WorkerError, request_worker

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "workers"


def compile_jar(root, name, sources, classpath=()):
    source = root / name / "src"
    classes = root / name / "classes"
    classes.mkdir(parents=True)
    paths = []
    for relative, text in sources.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        paths.append(path)
    args = [shutil.which("javac"), "--release", "21", "-d", str(classes)]
    if classpath:
        args += ["-classpath", os.pathsep.join(map(str, classpath))]
    subprocess.run([*args, *map(str, paths)], check=True, capture_output=True, text=True)
    jar = root / (name + ".jar")
    subprocess.run([shutil.which("jar"), "--create", "--file", str(jar), "--date", "2025-01-01T00:00:00Z",
                    "-C", str(classes), "."], check=True, capture_output=True, text=True)
    return jar, classes


@pytest.fixture
def real_dispatch(tmp_path):
    try:
        command("jvm", HOME)
        if not shutil.which("javac") or not shutil.which("jar"):
            raise WorkerError("actual JDK compiler required", "TOOLCHAIN_UNAVAILABLE")
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    api, _ = compile_jar(tmp_path, "api", {
        "api/Api.java": "package api; public interface Api { int run(); }",
        "api/Base.java": "package api; public abstract class Base implements Api {}",
    })
    a, _ = compile_jar(tmp_path, "impl-a", {"impl/A.java":
        "package impl; public class A extends api.Base { public int run(){return 1;} }"}, [api])
    b, _ = compile_jar(tmp_path, "impl-b", {"impl/B.java":
        "package impl; public class B implements api.Api { public int run(){return 2;} }"}, [api])
    project = tmp_path / "project"
    source = project / "src/main/java/consumer/Caller.java"
    source.parent.mkdir(parents=True)
    source.write_text("""package consumer;
public class Caller {
 public int callApi(api.Api value) { return value.run(); }
 public int callBase(api.Base value) { return value.run(); }
 public java.util.function.IntSupplier reference(api.Api value) { return value::run; }
}
""")
    entries = [{"path": str(path), "realm": {"repo_id": repo, "module": "lib", "source_set": "main", "scope": "production"}}
               for path, repo in [(api, "api-repo"), (a, "impl-a-repo"), (b, "impl-b-repo")]]
    return project, entries, (api, a, b)


def test_source_interface_call_finds_two_dependency_implementation_realms(real_dispatch):
    project, entries, _ = real_dispatch
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    site = next(s for s in result["graph"]["call_sites"] if s["caller"].endswith(":method:consumer.Caller.callApi(Lapi/Api;)I"))
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert {candidate.split(":method:")[-1] for candidate in site["dispatch_candidates"]} == {"impl.A.run()I", "impl.B.run()I"}
    assert any(":impl-a-repo:lib:" in candidate for candidate in site["dispatch_candidates"])
    assert any(":impl-b-repo:lib:" in candidate for candidate in site["dispatch_candidates"])
    assert site["dispatch_complete"] is False


def raw(project, entries, roots=()):
    return request_worker(command("jvm", HOME), {"operation": "analyze", "root": str(project),
        "context": {"id": "dispatch-test", "repo_id": "caller", "module": "main", "source_set": "main", "scope": "production"},
        "sources": [], "classpath": entries, "bytecode_roots": [str(root) for root in roots]}, cwd=project)


def test_base_receiver_narrows_candidates_and_reference_does_not_execute(real_dispatch):
    from kgmaker.callgraph import adjacency
    from kgmaker.model import KnowledgeGraph
    project, entries, _ = real_dispatch
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    sites = result["graph"]["call_sites"]
    base = next(site for site in sites if ".callBase(" in site["caller"])
    assert [c.split(":method:")[-1] for c in base["dispatch_candidates"]] == ["impl.A.run()I"]
    reference = next(site for site in sites if site["invocation_kind"] == "METHOD_REFERENCE")
    assert reference["dispatch_candidates"] == []
    assert not adjacency(KnowledgeGraph.from_dict(result["graph"])).get(reference["caller"])
    evidence = result["graph"]["evidence"]
    assert any(e.get("dispatch_algorithm") == "CHA_ORDERED_SELECTED_CLASSPATH" for e in evidence)
    assert not (project / ".kgmaker").exists()


def test_bytecode_interface_call_indexes_jars_and_preserves_realms(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    caller, _ = compile_jar(tmp_path, "caller", {"consumer/Calls.java":
        "package consumer; public class Calls { public int call(api.Api value){return value.run();} }"}, [jars[0]])
    response = raw(project, entries, [caller])
    site = next(site for site in response["call_sites"] if site["invocation_kind"] == "INTERFACE")
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert {c.split(":method:")[-1] for c in site["dispatch_candidates"]} == {"impl.A.run()I", "impl.B.run()I"}
    assert site["dispatch_complete"] is False


def test_ordered_shadow_does_not_union_same_binary_class(real_dispatch, tmp_path):
    project, entries, _ = real_dispatch
    shadow, _ = compile_jar(tmp_path, "shadow", {"impl/A.java":
        "package impl; public class A { public int run(){return 9;} }"})
    selected = [entries[0], {"path": str(shadow)}, *entries[1:]]
    result = inspect_jvm(project, classpath=selected, home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert [c.split(":method:")[-1] for c in site["dispatch_candidates"]] == ["impl.B.run()I"]
    assert "DEPENDENCY_HIERARCHY_SHADOWED" in site["dispatch_completeness_reason"]
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_SHADOWED" for d in result["diagnostics"])


def test_unmapped_artifacts_keep_hash_derived_realms(real_dispatch):
    project, _, jars = real_dispatch
    result = inspect_jvm(project, classpath=[str(jar) for jar in jars], home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert len(site["dispatch_candidates"]) == 2
    assert all(c.startswith("jvm:dependency:") for c in site["dispatch_candidates"])
    assert len({c.split(":")[2] for c in site["dispatch_candidates"]}) == 2


def test_missing_parent_excludes_unprovable_implementation(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    api_only, _ = compile_jar(tmp_path, "api-only", {"api/Api.java": "package api; public interface Api { int run(); }"})
    caller, _ = compile_jar(tmp_path, "missing-caller", {"consumer/Calls.java":
        "package consumer; public class Calls { public int call(api.Api value){return value.run();} }"}, [jars[0]])
    response = raw(project, [{"path": str(api_only)}, *entries[1:]], [caller])
    site = next(site for site in response["call_sites"] if site["invocation_kind"] == "INTERFACE")
    assert [c.split(":method:")[-1] for c in site["dispatch_candidates"]] == ["impl.B.run()I"]
    # Missing impl.A's parent can hide subtype/override relationships.
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_MISSING_TYPE" for d in response["diagnostics"])
    assert "MISSING_HIERARCHY_TYPE" in site["dispatch_completeness_reason"]


def test_corrupt_and_bounded_archives_are_partial_without_execution(real_dispatch, tmp_path):
    import zipfile
    project, entries, jars = real_dispatch
    bad = tmp_path / "bad.jar"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("bad/Broken.class", b"not a JVM class")
        for index in range(10001):
            archive.writestr(f"bounded/C{index:05}.class", b"bad")
    response = raw(project, [*entries, {"path": str(bad)}])
    codes = {d["code"] for d in response["diagnostics"]}
    assert "DEPENDENCY_HIERARCHY_INVALID_CLASS" in codes
    assert "DEPENDENCY_HIERARCHY_TRUNCATED" in codes
    assert response["status"] == "PARTIAL"
    assert not (project / ".kgmaker").exists()


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_actual_kotlin_virtual_call_uses_pinned_backend_dispatch(real_dispatch, backend):
    project, entries, _ = real_dispatch
    kotlin = project / "src/main/kotlin/Calls.kt"
    kotlin.parent.mkdir(parents=True)
    kotlin.write_text("fun call(value: api.Api): Int = value.run()\n")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False, kotlin_backend=backend)
    site = next(site for site in result["graph"]["call_sites"] if str(site.get("path", "")).endswith("Calls.kt"))
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert {c.split(":method:")[-1] for c in site["dispatch_candidates"]} == {"impl.A.run()I", "impl.B.run()I"}
    assert site["dispatch_complete"] is False


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_source_static_final_private_and_reference_do_not_gain_candidates(real_dispatch, tmp_path, backend):
    project, entries, _ = real_dispatch
    utility, _ = compile_jar(tmp_path, "utility", {"api/Utility.java": """package api;
public class Utility {
 public static int staticCall(){return 1;}
 public final int finalCall(){return 2;}
 private int privateCall(){return 3;}
 public int publicCall(){return privateCall();}
}"""})
    entries.append({"path": str(utility)})
    kotlin = project / "src/main/kotlin/Boundaries.kt"
    kotlin.parent.mkdir(parents=True)
    kotlin.write_text("""fun boundary(value: api.Utility): Int = api.Utility.staticCall() + value.finalCall()
fun reference(value: api.Api) = value::run
private fun privateCall(): Int = 3
fun callPrivate(): Int = privateCall()
fun api.Api.extension(): Int = 4
fun extensionCaller(value: api.Api): Int = value.extension()
""")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False, kotlin_backend=backend)
    sites = [site for site in result["graph"]["call_sites"] if str(site.get("path", "")).endswith("Boundaries.kt")]
    assert any((site.get("declared_target") or "").endswith("api.Utility.staticCall()I") for site in sites)
    assert any((site.get("declared_target") or "").endswith("api.Utility.finalCall()I") for site in sites)
    assert all(site["dispatch_candidates"] == [] for site in sites)


def test_source_declaration_wins_over_compiled_same_class(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    source = project / "src/main/java/impl/A.java"
    source.parent.mkdir(parents=True)
    source.write_text("package impl; public class A extends api.Base { public int run(){return 10;} }")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    symbols = result["graph"]["symbols"]
    # Public graph metadata uses the same source canonical method as candidate.
    declarations = [symbol for symbol in symbols if symbol.get("owner") == "impl.A" and symbol.get("name") == "run"]
    assert len(declarations) == 1
    assert declarations[0]["path"].endswith("impl/A.java")
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert declarations[0]["id"] in site["dispatch_candidates"]


def test_multi_release_archive_is_explicitly_unsupported(real_dispatch, tmp_path):
    import zipfile
    project, entries, jars = real_dispatch
    multi = tmp_path / "multi.jar"
    with zipfile.ZipFile(jars[1]) as original, zipfile.ZipFile(multi, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\nMulti-Release: true\r\n\r\n")
        archive.writestr("impl/A.class", original.read("impl/A.class"))
        archive.writestr("META-INF/versions/21/impl/A.class", original.read("impl/A.class"))
    response = raw(project, [entries[0], {"path": str(multi)}, entries[2]])
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED" for d in response["diagnostics"])
    assert response["status"] == "PARTIAL"


def test_invalid_input_timeout_and_cancel_preserve_published_generation(real_dispatch, tmp_path):
    project, entries, _ = real_dispatch
    inspect_jvm(project, classpath=entries, home=HOME)
    def snapshot():
        return {str(path.relative_to(project)): path.read_bytes() for path in (project / ".kgmaker").rglob("*") if path.is_file()}
    before = snapshot()
    with pytest.raises(AnalysisError):
        inspect_jvm(project, classpath=[*entries, str(tmp_path / "absent.jar")], home=HOME)
    assert snapshot() == before
    with pytest.raises(WorkerError) as timeout:
        inspect_jvm(project, classpath=entries, home=HOME, timeout=0.001)
    assert timeout.value.status == "TIMED_OUT"
    assert snapshot() == before
    cancellation = tmp_path / "cancel"
    cancellation.touch()
    with pytest.raises(WorkerError) as cancelled:
        inspect_jvm(project, classpath=entries, home=HOME, cancel_file=cancellation)
    assert cancelled.value.status == "CANCELLED"
    assert snapshot() == before


def test_aggregate_class_byte_budget_is_bounded(real_dispatch, tmp_path):
    import zipfile
    project, entries, _ = real_dispatch
    archive_path = tmp_path / "aggregate.jar"
    # Small compressed input would otherwise expand into 136 MiB of metadata input.
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        data = bytes(8 * 1024 * 1024)
        for index in range(17):
            archive.writestr(f"oversize/C{index:02}.class", data)
    response = raw(project, [*entries, {"path": str(archive_path)}])
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_TRUNCATED" and "Aggregate" in d["reason"] for d in response["diagnostics"])
    assert response["status"] == "PARTIAL"


def test_version_only_multi_release_class_shadows_later_plain_jar(real_dispatch, tmp_path):
    import zipfile
    project, entries, jars = real_dispatch
    multi = tmp_path / "version-only.jar"
    with zipfile.ZipFile(jars[1]) as original, zipfile.ZipFile(multi, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\nMulti-Release: true\r\n\r\n")
        archive.writestr("META-INF/versions/21/impl/A.class", original.read("impl/A.class"))
    result = inspect_jvm(project, classpath=[entries[0], {"path": str(multi)}, *entries[1:]], home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert [c.split(":method:")[-1] for c in site["dispatch_candidates"]] == ["impl.B.run()I"]
    assert "DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED" in site["dispatch_completeness_reason"]


def test_duplicate_archive_class_is_ambiguous_and_cannot_fall_through(real_dispatch, tmp_path):
    import warnings
    import zipfile
    project, entries, jars = real_dispatch
    duplicate = tmp_path / "duplicate.jar"
    with zipfile.ZipFile(jars[1]) as original, zipfile.ZipFile(duplicate, "w") as archive, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        archive.writestr("impl/A.class", original.read("impl/A.class"))
        archive.writestr("impl/A.class", original.read("impl/A.class"))
    result = inspect_jvm(project, classpath=[entries[0], {"path": str(duplicate)}, *entries[1:]], home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert [c.split(":method:")[-1] for c in site["dispatch_candidates"]] == ["impl.B.run()I"]
    assert "DEPENDENCY_HIERARCHY_DUPLICATE_ENTRY" in site["dispatch_completeness_reason"]


def test_unreadable_earlier_archive_prevents_later_candidate_guess(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    bad = tmp_path / "corrupt.jar"
    bad.write_bytes(b"not a zip")
    caller, _ = compile_jar(tmp_path, "corrupt-caller", {"consumer/Calls.java":
        "package consumer; public class Calls { public int call(api.Api value){return value.run();} }"}, [jars[0]])
    response = raw(project, [entries[0], {"path": str(bad)}, *entries[1:]], [caller])
    site = next(site for site in response["call_sites"] if site["invocation_kind"] == "INTERFACE")
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert site["dispatch_candidates"] == []
    assert "DEPENDENCY_HIERARCHY_UNAVAILABLE" in site["dispatch_completeness_reason"]


def test_k2_source_owner_without_hierarchy_cannot_reuse_stale_compiled_subtype(real_dispatch):
    project, entries, _ = real_dispatch
    source = project / "src/main/kotlin/A.kt"
    source.parent.mkdir(parents=True)
    source.write_text("package impl\nclass A { fun run(): Int = 10 }\n")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False, kotlin_backend="k2")
    site = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert [c.split(":method:")[-1] for c in site["dispatch_candidates"]] == ["impl.B.run()I"]
    assert "SOURCE_HIERARCHY_UNAVAILABLE" in site["dispatch_completeness_reason"]
    declarations = [symbol for symbol in result["graph"]["symbols"] if symbol.get("owner") == "impl.A" and symbol.get("name") == "run"]
    assert len(declarations) == 1 and declarations[0]["path"].endswith("A.kt")


def test_qualified_interface_super_call_is_special_not_dispatch(real_dispatch):
    project, entries, _ = real_dispatch
    source = project / "src/main/java/consumer/SuperCall.java"
    source.write_text("""package consumer;
interface DefaultApi { default int run(){return 1;} }
class SuperCall implements DefaultApi { public int run(){return DefaultApi.super.run();} }
""")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".SuperCall.run(" in site["caller"])
    assert site["invocation_kind"] == "SPECIAL"
    assert site["dispatch_candidates"] == []
    assert "dispatch_receiver" not in site


def test_package_private_declaration_does_not_invent_cross_package_override(real_dispatch, tmp_path):
    project, entries, _ = real_dispatch
    base, _ = compile_jar(tmp_path, "package-base", {"a/Base.java":
        "package a; public class Base { int hidden(){return 1;} }"})
    child, _ = compile_jar(tmp_path, "package-child", {"b/Child.java":
        "package b; public class Child extends a.Base { public int hidden(){return 2;} }"}, [base])
    source = project / "src/main/java/a/PackageCall.java"
    source.parent.mkdir(parents=True)
    source.write_text("package a; public class PackageCall { public int call(Base value){return value.hidden();} }")
    result = inspect_jvm(project, classpath=[*entries, str(base), str(child)], home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".PackageCall.call(" in site["caller"])
    assert site["declared_target"].endswith(":method:a.Base.hidden()I")
    assert site["dispatch_candidates"] == []
    assert "PACKAGE_PRIVATE_OVERRIDE_ACCESS_UNSUPPORTED" in site["dispatch_completeness_reason"]


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_real_kotlin_static_facade_lookup_survives_unknown_source_type_hierarchy(real_dispatch, tmp_path, backend):
    project, entries, _ = real_dispatch
    compiler = shutil.which("kotlinc")
    if not compiler:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail("Pinned Kotlin2.1.10 compiler required for actual facade regression")
        pytest.skip("Pinned Kotlin2.1.10 compiler required")
    version = subprocess.run([compiler, "-version"], capture_output=True, text=True, check=True)
    if "2.1.10" not in version.stdout + version.stderr:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail("Actual facade regression requires Kotlin2.1.10")
        pytest.skip("Actual facade regression requires Kotlin2.1.10")
    source = project / "src/main/kotlin/Facade.kt"
    source.parent.mkdir(parents=True)
    source.write_text("fun target(): Int = 1\nfun caller(): Int = target()\n")
    classes = tmp_path / "kotlin-classes"
    subprocess.run([compiler, "-jvm-target", "21", "-d", str(classes), str(source)],
                   check=True, capture_output=True, text=True)
    context = {"id": "facade", "repo_id": "source", "module": "main", "source_set": "main", "scope": "production"}
    stdlib = HOME / "jvm/target/lib/kotlin-stdlib.jar"
    result = request_worker(command("jvm", HOME, kotlin_backend=backend), {
        "operation": "analyze", "root": str(project), "context": context,
        "sources": ["src/main/kotlin/Facade.kt"], "classpath": [
            {"path": str(classes), "realm": context}, {"path": str(stdlib)}],
        "bytecode_roots": [str(classes)]}, cwd=project)
    site = next(site for site in result["call_sites"] if site["id"].startswith("bytecode-call:") and ".caller()I" in site["caller"])
    assert site["invocation_kind"] == "STATIC"
    assert site["declared_target"].endswith(":method:FacadeKt.target()I")
    assert site["dispatch_candidates"] == []


def intersection_source(project):
    source = project / "src/main/java/consumer/Intersections.java"
    source.write_text("""package consumer;
interface Marker {}
interface OtherApi { int run(); }
class OnlyMarker implements Marker { public int run(){return 3;} }
class BothMarker extends impl.A implements Marker {}
class OtherBody { public int run(){return 4;} }
class OtherMarker extends OtherBody implements Marker, OtherApi {}
public class Intersections {
 public <T extends Marker & api.Api> int apiFirst(T value){return value.run();}
 public <T extends Marker & OtherApi> int otherSecond(T value){return value.run();}
 public int plainOther(OtherApi value){return value.run();}
}
""")


def test_unsupported_intersection_keeps_declared_contract_and_inherited_body_positive(real_dispatch):
    project, entries, _ = real_dispatch
    intersection_source(project)
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    sites = result["graph"]["call_sites"]
    site = next(site for site in sites if ".Intersections.apiFirst(" in site["caller"])
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert site["dispatch_candidates"] == []
    assert site["dispatch_completeness_reason"] == "JAVA_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED"
    assert "dispatch_kind" not in site
    # Ordinary interface receiver remains supported. Its concrete class owns
    # the contract even when its inherited body owner does not implement it.
    plain = next(site for site in sites if ".Intersections.plainOther(" in site["caller"])
    assert [c.split(":method:")[-1] for c in plain["dispatch_candidates"]] == ["consumer.OtherBody.run()I"]


def test_unsupported_intersections_keep_distinct_contracts_without_cached_candidates(real_dispatch):
    project, entries, _ = real_dispatch
    intersection_source(project)
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    sites = result["graph"]["call_sites"]
    api = next(site for site in sites if ".Intersections.apiFirst(" in site["caller"])
    other = next(site for site in sites if ".Intersections.otherSecond(" in site["caller"])
    assert api["declared_target"].endswith(":method:api.Api.run()I")
    assert other["declared_target"].endswith(":method:consumer.OtherApi.run()I")
    assert api["dispatch_candidates"] == other["dispatch_candidates"] == []
    assert all(site["dispatch_completeness_reason"] == "JAVA_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED" for site in [api, other])


def test_missing_declared_api_bytecode_target_remains_partial_without_candidates(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    caller, _ = compile_jar(tmp_path, "unresolved-caller", {"consumer/Calls.java":
        "package consumer; public class Calls { public int call(api.Api value){return value.run();} }"}, [jars[0]])
    # The call instruction is real, but neither the API nor Base class is on
    # the selected classpath. Missing declaration must not crash contract lookup.
    response = raw(project, entries[1:], [caller])
    site = next(site for site in response["call_sites"] if site["invocation_kind"] == "INTERFACE")
    assert site["declared_target"] is None
    assert site["dispatch_candidates"] == []
    assert site["dispatch_complete"] is False
    assert site["resolution_reason"] == "MISSING_CLASS_OR_METHOD"
    assert response["status"] == "PARTIAL"
    assert any(d["code"] == "BYTECODE_UNRESOLVED_TARGET" for d in response["diagnostics"])
    assert not (project / ".kgmaker").exists()


@pytest.mark.parametrize("bounds", ["Marker & api.Api & Extra", "api.Api & Extra", "Marker & ChildApi"])
def test_java_generic_receiver_bounds_are_explicitly_unsupported(real_dispatch, bounds):
    project, entries, _ = real_dispatch
    source = project / "src/main/java/consumer/ManyBounds.java"
    source.write_text("""package consumer;
interface Marker {}
interface Extra {}
interface ChildApi extends api.Api {}
final class Bare extends impl.A implements Marker { public int run(){return 3;} }
class Legal extends impl.B implements Marker,Extra,ChildApi {}
public class ManyBounds {
 public <T extends """ + bounds + """> int generic(T value){return value.run();}
 public int plain(ChildApi value){return value.run();}
 public int explicit(Object value){return ((Marker & api.Api & Extra)value).run();}
}
""")
    result = inspect_jvm(project, classpath=entries, home=HOME, publish=False)
    site = next(site for site in result["graph"]["call_sites"] if ".ManyBounds.generic(" in site["caller"])
    assert site["declared_target"].endswith(":method:api.Api.run()I")
    assert site["dispatch_candidates"] == []
    assert site["dispatch_completeness_reason"] == "JAVA_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED"
    assert result["status"] == "PARTIAL"
    explicit = next(site for site in result["graph"]["call_sites"] if ".ManyBounds.explicit(" in site["caller"])
    assert explicit["declared_target"].endswith(":method:api.Api.run()I")
    assert explicit["dispatch_candidates"] == []
    assert explicit["dispatch_completeness_reason"] == "JAVA_INTERSECTION_RECEIVER_DISPATCH_UNSUPPORTED"
    plain = next(site for site in result["graph"]["call_sites"] if ".ManyBounds.plain(" in site["caller"])
    assert [c.split(":method:")[-1] for c in plain["dispatch_candidates"]] == ["impl.B.run()I"]


@pytest.mark.parametrize("backend", ["k1", "k2"])
def test_kotlin_generic_receiver_bounds_are_explicitly_unsupported(real_dispatch, tmp_path, backend):
    project, entries, jars = real_dispatch
    bounds, _ = compile_jar(tmp_path, "kotlin-bounds", {
        "extra/Marker.java": "package extra; public interface Marker {}",
        "extra/Extra.java": "package extra; public interface Extra {}",
        "extra/ChildApi.java": "package extra; public interface ChildApi extends api.Api {}",
        "extra/Bare.java": "package extra; public final class Bare extends impl.A implements Marker { public int run(){return 3;} }",
        "extra/Legal.java": "package extra; public class Legal extends impl.B implements Marker,Extra,ChildApi {}",
    }, jars)
    source = project / "src/main/kotlin/Bounds.kt"
    source.parent.mkdir(parents=True)
    source.write_text("""fun <T> triple(value: T): Int where T: extra.Marker, T: api.Api, T: extra.Extra = value.run()
fun <T> inherited(value: T): Int where T: extra.Marker, T: extra.ChildApi = value.run()
fun plain(value: extra.ChildApi): Int = value.run()
""")
    result = inspect_jvm(project, classpath=[*entries, str(bounds)], home=HOME, publish=False, kotlin_backend=backend)
    sites = [site for site in result["graph"]["call_sites"] if str(site.get("path", "")).endswith("Bounds.kt")]
    generic = [site for site in sites if ".plain(" not in site["caller"]]
    assert len(generic) == 2
    for site in generic:
        expected_owner="extra.ChildApi" if backend=="k1" and ".inherited(" in site["caller"] else "api.Api"
        assert site["declared_target"].endswith(":method:" + expected_owner + ".run()I")
        assert site["dispatch_candidates"] == []
        assert site["dispatch_completeness_reason"] == backend.upper() + "_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED"
    plain = next(site for site in sites if ".plain(" in site["caller"])
    assert [c.split(":method:")[-1] for c in plain["dispatch_candidates"]] == ["impl.B.run()I"]


def test_foreign_bytecode_targets_and_candidates_do_not_alias_local_source_view(real_dispatch, tmp_path):
    project, entries, jars = real_dispatch
    foreign, _ = compile_jar(tmp_path, "foreign-caller", {"foreign/Caller.java": """package foreign;
public class Caller {
 public int invoke(impl.A value){return value.run();}
 public int invokeApi(api.Api value){return value.run();}
}
"""}, jars)
    source = project / "src/main/java/impl/A.java"
    source.parent.mkdir(parents=True)
    source.write_text("package impl; public class A { public static int run(){return 99;} }")
    context = {"id": "realm-isolation", "repo_id": "local", "module": "consumer", "source_set": "main", "scope": "production"}
    foreign_realm = {"repo_id": "foreign-caller", "module": "binary", "source_set": "main", "scope": "production"}
    response = request_worker(command("jvm", HOME), {
        "operation": "analyze", "root": str(project), "context": context,
        "sources": ["src/main/java/impl/A.java", "src/main/java/consumer/Caller.java"],
        "classpath": entries, "bytecode_roots": [{"path": str(foreign), "realm": foreign_realm}],
    }, cwd=project)
    sites = response["call_sites"]
    physical = next(site for site in sites if "foreign.Caller.invoke(" in site["caller"])
    assert physical["invocation_kind"] == "VIRTUAL"
    assert ":impl-a-repo:lib:main:" in physical["declared_target"]
    assert physical["declared_target"].endswith(":method:impl.A.run()I")
    target = next(symbol for symbol in response["symbols"] if symbol["id"] == physical["declared_target"])
    assert target["path"] is None and "static" not in target.get("modifiers", [])
    local = next(symbol for symbol in response["symbols"] if symbol.get("owner") == "impl.A" and symbol.get("name") == "run" and symbol.get("path"))
    assert "static" in local["modifiers"]
    assert local["id"] != physical["declared_target"]
    # Same receiver/contract/signature, different representation: physical CP
    # contains instance A; compiler source A no longer implements Api.
    physical_api = next(site for site in sites if "foreign.Caller.invokeApi(" in site["caller"])
    source_api = next(site for site in sites if "consumer.Caller.callApi(" in site["caller"])
    assert {c.split(":method:")[-1] for c in physical_api["dispatch_candidates"]} == {"impl.A.run()I", "impl.B.run()I"}
    assert all(":impl-a-repo:" in c or ":impl-b-repo:" in c for c in physical_api["dispatch_candidates"])
    assert [c.split(":method:")[-1] for c in source_api["dispatch_candidates"]] == ["impl.B.run()I"]
    assert not (project / ".kgmaker").exists()


def test_selected_jar_cannot_shadow_actual_toolchain_object_or_its_realm(real_dispatch, tmp_path):
    from struct import pack
    import zipfile
    project, entries, _ = real_dispatch
    def utf(value):
        data = value.encode()
        return b"\x01" + pack(">H", len(data)) + data
    # Well-formed metadata class which lies that bootstrap Object implements Api.
    # Actual Javac correctly uses its JDK; the metadata index must do the same.
    fake = (pack(">IHHH", 0xCAFEBABE, 0, 65, 5) + utf("java/lang/Object") + b"\x07\x00\x01"
            + utf("api/Api") + b"\x07\x00\x03" + pack(">HHHHHHHH", 0x21, 2, 0, 1, 4, 0, 0, 0))
    shadow = tmp_path / "bootstrap-shadow.jar"
    with zipfile.ZipFile(shadow, "w") as archive:
        archive.writestr("java/lang/Object.class", fake)
    (project / "src/main/java/consumer/Unrelated.java").write_text(
        "package consumer; public final class Unrelated { public int run(){return 4;} }")
    (project / "src/main/java/consumer/ObjectName.java").write_text(
        "package consumer; public class ObjectName { public String name(Object value){return value.toString();} }")
    selected = [*entries, {"path": str(shadow), "realm": {
        "repo_id": "fake-platform", "module": "shadow", "source_set": "main", "scope": "production"}}]
    result = inspect_jvm(project, classpath=selected, home=HOME, publish=False)
    api = next(site for site in result["graph"]["call_sites"] if ".callApi(" in site["caller"])
    assert {c.split(":method:")[-1] for c in api["dispatch_candidates"]} == {"impl.A.run()I", "impl.B.run()I"}
    name = next(site for site in result["graph"]["call_sites"] if "consumer.ObjectName.name(" in site["caller"])
    assert name["declared_target"].startswith("jvm:toolchain:jdk-")
    assert name["declared_target"].endswith(":method:java.lang.Object.toString()Ljava/lang/String;")
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_PLATFORM_SHADOWED" for d in result["diagnostics"])
    assert result["status"] == "PARTIAL"
    assert not (project / ".kgmaker").exists()


@pytest.mark.parametrize("source_static,physical_static", [(True, False), (False, True), (False, False), (True, True)])
def test_same_realm_source_binary_staticness_conflict_is_partial_without_false_mapping(real_dispatch, tmp_path, source_static, physical_static):
    project, entries, _ = real_dispatch
    def declaration(static):
        return "package impl; public class A { public " + ("static " if static else "") + "int run(){return 1;} }"
    physical, _ = compile_jar(tmp_path, "same-realm", {
        "impl/A.java": declaration(physical_static),
        "foreign/AbiCaller.java": "package foreign; public class AbiCaller { public int call(impl.A value){return value.run();} }",
    })
    source = project / "src/main/java/impl/A.java"
    source.parent.mkdir(parents=True)
    source.write_text(declaration(source_static))
    context = {"id": "same-realm-abi", "repo_id": "local", "module": "consumer", "source_set": "main", "scope": "production"}
    response = request_worker(command("jvm", HOME), {
        "operation": "analyze", "root": str(project), "context": context,
        "sources": ["src/main/java/impl/A.java"],
        "classpath": [{"path": str(physical), "realm": context}, *entries],
        "bytecode_roots": [{"path": str(physical), "realm": context}],
    }, cwd=project)
    call = next(site for site in response["call_sites"] if "foreign.AbiCaller.call(" in site["caller"])
    source_method = next(symbol for symbol in response["symbols"] if symbol.get("owner") == "impl.A" and symbol.get("name") == "run" and symbol.get("path"))
    body = next(symbol for symbol in response["symbols"] if symbol.get("kind") == "bytecode_method" and symbol.get("owner") == "impl.A" and symbol.get("name") == "run")
    assert call["invocation_kind"] == ("STATIC" if physical_static else "VIRTUAL")
    if source_static != physical_static:
        assert call["declared_target"] is None and call["dispatch_candidates"] == []
    assert source_method["jvm_static"] is source_static
    assert body["jvm_static"] is physical_static
    assert body["path"] is None and body["range"] is None and body.get("sha256") is None
    if source_static != physical_static:
        assert call["declared_target"] is None and call["dispatch_candidates"] == []
        assert call["resolution_reason"] == "SOURCE_BINARY_ABI_CONFLICT"
        assert call["evidence_kind"] == "UNRESOLVED"
        assert body["source_mapping_ids"] == []
        assert body["source_mapping_reason"] == "SOURCE_BINARY_ABI_CONFLICT"
        assert any(d["code"] == "SOURCE_BINARY_ABI_CONFLICT" for d in response["diagnostics"])
        assert response["status"] == "PARTIAL"
    else:
        assert call["declared_target"] == source_method["id"]
        assert call["evidence_kind"] == "SYMBOL_RESOLVED"
        assert body["source_mapping_ids"] == [source_method["id"]]
        assert not any(d["code"] == "SOURCE_BINARY_ABI_CONFLICT" for d in response["diagnostics"])
    assert not (project / ".kgmaker").exists()


def test_actual_pinned_stdlib_multi_release_static_target_lookup_is_preserved(real_dispatch, tmp_path):
    project, _, _ = real_dispatch
    stdlib = HOME / "jvm/target/lib/kotlin-stdlib.jar"
    caller, _ = compile_jar(tmp_path, "stdlib-caller", {"foreign/StdlibCaller.java":
        'package foreign; public class StdlibCaller { public static void call(Object value){kotlin.jvm.internal.Intrinsics.checkNotNullParameter(value,"value");} }'}, [stdlib])
    response = raw(project, [{"path": str(stdlib)}], [caller])
    site = next(site for site in response["call_sites"] if "foreign.StdlibCaller.call(" in site["caller"])
    assert site["invocation_kind"] == "STATIC" and site["evidence_kind"] == "SYMBOL_RESOLVED"
    assert site["declared_target"].startswith("jvm:dependency:")
    assert site["declared_target"].endswith(":method:kotlin.jvm.internal.Intrinsics.checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V")
    assert any(d["code"] == "DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED" for d in response["diagnostics"])
    assert not any(d["code"] == "DEPENDENCY_HIERARCHY_PLATFORM_SHADOWED" for d in response["diagnostics"])


@pytest.mark.parametrize("include_base", [False, True])
def test_multi_release_effective_class_lookup_preserves_first_selected_realm(real_dispatch, tmp_path, include_base):
    import zipfile
    project, _, _ = real_dispatch
    base, _ = compile_jar(tmp_path, "mr-base", {"mr/Version.java":
        "package mr; public class Version { public static int onlyBase(){return 1;} }"})
    effective, _ = compile_jar(tmp_path, "mr-effective", {"mr/Version.java":
        "package mr; public class Version { public static int selected(){return 2;} }"})
    caller, _ = compile_jar(tmp_path, "mr-caller", {"foreign/MrCaller.java":
        "package foreign; public class MrCaller { public static int call(){return mr.Version.selected();} }"}, [effective])
    multi = tmp_path / "effective.jar"
    with zipfile.ZipFile(base) as b, zipfile.ZipFile(effective) as e, zipfile.ZipFile(multi, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\nMulti-Release: true\r\n\r\n")
        if include_base:
            archive.writestr("mr/Version.class", b.read("mr/Version.class"))
        archive.writestr("META-INF/versions/21/mr/Version.class", e.read("mr/Version.class"))
    realm = {"repo_id": "mr-first", "module": "library", "source_set": "main", "scope": "production"}
    response = raw(project, [{"path": str(multi), "realm": realm}, {"path": str(base)}], [caller])
    site = next(site for site in response["call_sites"] if "foreign.MrCaller.call(" in site["caller"])
    assert site["declared_target"] is not None
    assert site["declared_target"].startswith("jvm:mr-first:library:main:")
    assert site["declared_target"].endswith(":method:mr.Version.selected()I")
    assert site["evidence_kind"] == "SYMBOL_RESOLVED"
    assert response["status"] == "PARTIAL"  # MR candidates remain explicitly unsupported.

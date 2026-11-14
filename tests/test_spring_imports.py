"""T003-S05-W01: actual Javac and Spring6.2.2 APIs, never a Spring context."""
import copy
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pytest

from kgmaker import inspection
from kgmaker import feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA
from kgmaker.data_check import data_check
from kgmaker.graph_provider import retain_compiler_layer
from kgmaker.framework import SPRING_RULE_VERSION
from kgmaker.model import KnowledgeGraph
from kgmaker.scanner import scan_repository
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "workers"


@pytest.mark.parametrize("required", ["KGMAKER_REQUIRE_WORKERS", "KGMAKER_REQUIRE_SPRING_IMPORTS"])
@pytest.mark.parametrize("wrong_bytes", [False, True])
def test_required_api_inputs_fail_before_any_process(tmp_path, monkeypatch, required, wrong_bytes):
    monkeypatch.delenv("KGMAKER_REQUIRE_WORKERS", raising=False)
    monkeypatch.delenv("KGMAKER_REQUIRE_SPRING_IMPORTS", raising=False)
    monkeypatch.setenv(required, "1")
    monkeypatch.setenv("KGMAKER_TEST_MAVEN_REPOSITORY", str(tmp_path))
    if wrong_bytes:
        lock = json.loads((ROOT / "fixtures/spring-imports/dependencies.lock.json").read_text())
        target = tmp_path / lock["artifacts"][0]["path"]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"wrong API artifact")
    with patch("kgmaker.inspection.command", return_value=["not-executed"]), \
            patch("subprocess.Popen", side_effect=AssertionError("must fail before execution")):
        with pytest.raises(pytest.fail.Exception, match="pinned Spring6.2.2 API"):
            actual_imports.__wrapped__(SimpleNamespace(param="k1"), None)


@pytest.fixture(scope="module", params=("k1", "k2"))
def actual_imports(request, tmp_path_factory):
    repository = Path(os.environ.get("KGMAKER_TEST_MAVEN_REPOSITORY", Path.home() / ".m2/repository"))
    lock = json.loads((ROOT / "fixtures/spring-imports/dependencies.lock.json").read_text())
    jars = [repository / entry["path"] for entry in lock["artifacts"]]
    try:
        inspection.command("jvm", HOME, kotlin_backend=request.param)
        for jar, entry in zip(jars, lock["artifacts"]):
            if not jar.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest() != entry["sha256"]:
                raise WorkerError("Actual pinned Spring6.2.2 API JAR unavailable or changed: " + jar.name, "TOOLCHAIN_UNAVAILABLE")
            with zipfile.ZipFile(jar) as archive:
                if entry["license_entry"] not in archive.namelist():
                    raise WorkerError("Spring API license entry unavailable: " + jar.name, "TOOLCHAIN_UNAVAILABLE")
    except (WorkerError, OSError) as error:
        if os.environ.get("KGMAKER_REQUIRE_SPRING_IMPORTS") == "1" or os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip("blocked: " + str(error))
    root = tmp_path_factory.mktemp("spring-imports-" + request.param)
    sources = {
        "app/Main.java": '''package app;
import org.springframework.context.annotation.*;
@Configuration @Profile("blue")
@Import({Direct.class,Inherited.class,Deferred.class,Unknown.class,Filtered.class,Grouped.class,Missing.class,Limit.class,NonType.class,Lookalike.class,outside.StaticPlain.class})
public class Main {}''',
        "app/Direct.java": '''package app;
public class Direct implements org.springframework.context.annotation.ImportSelector {
  static { if (Boolean.parseBoolean("true")) throw new AssertionError("must never initialize"); }
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.DirectTarget"}; }
}''',
        "app/Parent.java": '''package app;
public abstract class Parent implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.InheritedTarget"}; }
}''',
        "app/Inherited.java": "package app; public class Inherited extends Parent {}",
        "app/Deferred.java": '''package app;
public class Deferred implements org.springframework.context.annotation.DeferredImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.DeferredTarget"}; }
}''',
        "app/Unknown.java": '''package app;
public class Unknown implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { throw new AssertionError("must never invoke"); }
}''',
        "app/Filtered.java": '''package app;
public class Filtered implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.FilteredTarget"}; }
  public java.util.function.Predicate<String> getExclusionFilter() { return name -> true; }
}''',
        "app/Grouped.java": '''package app;
public class Grouped implements org.springframework.context.annotation.DeferredImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.GroupedTarget"}; }
  public Class<? extends Group> getImportGroup() { return null; }
}''',
        "app/Missing.java": '''package app;
public class Missing implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"outside.MissingTarget","external.Absent"}; }
}''',
        "app/NonType.java": '''package app;
public class NonType implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{"NOT_A_CLASS_NAME_LITERAL"}; }
}''',
        "fake/ImportSelector.java": "package fake; public interface ImportSelector {}",
        "app/Lookalike.java": "package app; public class Lookalike implements fake.ImportSelector {}",
        "outside/StaticPlain.java": "package outside; public class StaticPlain {}",
        "app/Consumer.java": '''package app;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Qualifier;
@Service public class Consumer {
  @Qualifier("direct") String direct;
  @Qualifier("filtered") String filtered;
}''',
    }
    literals = ','.join('"outside.C' + str(index) + '"' for index in range(129))
    sources["app/Limit.java"] = '''package app;
public class Limit implements org.springframework.context.annotation.ImportSelector {
  public String[] selectImports(org.springframework.core.type.AnnotationMetadata m) { return new String[]{''' + literals + '''}; }
}'''
    for label in ("Direct", "Inherited", "Deferred", "Filtered", "Grouped", "Missing"):
        sources[f"outside/{label}Target.java"] = f'''package outside;
import org.springframework.context.annotation.*;
@Configuration public class {label}Target {{ @Bean public String {label.lower()}() {{ return "value"; }} }}'''
    for relative, text in sources.items():
        path = root / "src/main/java" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    options = {"home": HOME, "kotlin_backend": request.param, "classpath": [str(jar) for jar in jars],
               "publish": False, "build_context": {"spring_profiles": ["blue"], "spring_properties": {},
                   "spring_available_classes": [], "spring_component_packages": ["app"]}}
    result = inspection.inspect_jvm(root, **options)
    return root, options, result


def test_actual_compiler_qualified_transitive_selector_facts(actual_imports):
    _, _, result = actual_imports
    symbols = result["graph"]["symbols"]
    inherited = next(item for item in symbols if item.get("owner") == "app.Inherited" and item["kind"] == "class")
    assert inherited["type_hierarchy"]["complete"]
    assert "org.springframework.context.annotation.ImportSelector" in inherited["type_hierarchy"]["types"]
    assert inherited["import_selector"]["method_owner"] == "app.Parent"
    fake = next(item for item in symbols if item.get("owner") == "app.Lookalike" and item["kind"] == "class")
    assert "import_selector" not in fake
    method = next(item for item in symbols if item.get("owner") == "app.Parent" and item.get("name") == "selectImports")
    assert method["static_import_return"]["values"] == ["outside.InheritedTarget"]


def test_literal_and_static_imports_link_without_processor_beans(actual_imports):
    _, _, result = actual_imports
    graph = result["graph"]
    beans = {node["name"]: node for node in graph["nodes"] if node["kind"] == "spring_bean"}
    for name in ("DirectTarget", "InheritedTarget", "DeferredTarget", "StaticPlain", "Lookalike"):
        assert beans[name]["metadata"]["condition_status"] == "ACTIVE"
    assert not {"Direct", "Inherited", "Deferred", "Unknown"} & set(beans)
    assert not any(item.get("type") == "app.Lookalike" and item["code"] == "SPRING_DYNAMIC_IMPORT_BOUNDARY" for item in result["diagnostics"])
    assert {"uses_import_selector", "selects_import", "imports_configuration"} <= {edge["kind"] for edge in graph["edges"]}
    for edge in graph["edges"]:
        if edge["kind"] == "selects_import":
            assert edge["evidence_kind"] == "FRAMEWORK_DERIVED"
            assert tuple(edge["context_ids"]) == (result["context"]["id"],)
            assert all(next(e for e in graph["evidence"] if e["id"] == identity)["framework_rules"]["spring"] == SPRING_RULE_VERSION for identity in edge["evidence_ids"])


def test_unknown_filters_and_deferred_groups_remain_unknown(actual_imports):
    _, _, result = actual_imports
    graph = result["graph"]
    selectors = {node["metadata"]["selector_type"]: node for node in graph["nodes"] if node["kind"] == "spring_import_selector"}
    for name in ("app.Unknown", "app.Filtered", "app.Grouped"):
        assert selectors[name]["metadata"]["selection_status"] == "UNKNOWN"
        assert any(d["code"] == "SPRING_DYNAMIC_IMPORT_BOUNDARY" and d.get("type") == name for d in result["diagnostics"])
    beans = {node["name"]: node for node in graph["nodes"] if node["kind"] == "spring_bean"}
    assert beans["FilteredTarget"]["metadata"]["condition_status"] == "UNKNOWN"
    assert beans["GroupedTarget"]["metadata"]["condition_status"] == "UNKNOWN"
    filtered = next(node["id"] for node in graph["nodes"] if node["kind"] == "spring_injection" and node["name"] == "Consumer.filtered")
    assert any(edge["source"] == filtered and edge["kind"] == "may_inject_bean" for edge in graph["edges"])
    assert not any(edge["source"] == filtered and edge["kind"] == "injects_bean" for edge in graph["edges"])


def test_strict_failure_and_offline_refresh_preserve_generation(actual_imports):
    root, options, _ = actual_imports
    inspection.inspect_jvm(root, **{**options, "publish": True})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    strict = inspection.inspect_jvm(root, **{**options, "publish": True, "strict": True})
    assert strict["exit_code"] == 4
    assert store.read_bytes() == before
    with patch("subprocess.Popen", side_effect=AssertionError("offline process")):
        retained = retain_compiler_layer(root, scan_repository(root))
    assert any(node.kind == "spring_import_selector" for node in retained.nodes)


def test_invalid_selector_fact_rejects_before_store_mutation(actual_imports):
    root, options, _ = actual_imports
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes() if store.exists() else None
    original = inspection.request_worker
    def malformed(*args, **kwargs):
        result = original(*args, **kwargs)
        symbol = next(s for s in result["symbols"] if s.get("owner") == "app.Direct" and s.get("kind") == "class")
        symbol["import_selector"]["schema_version"] = 99
        return result
    with patch("kgmaker.inspection.request_worker", side_effect=malformed):
        with pytest.raises(AnalysisError, match="selector"):
            inspection.inspect_jvm(root, **{**options, "publish": True})
    assert (store.read_bytes() if store.exists() else None) == before


def test_bounded_missing_and_non_type_results_remain_boundaries(actual_imports):
    _, _, result = actual_imports
    graph = result["graph"]
    selectors = {node["metadata"]["selector_type"]: node for node in graph["nodes"] if node["kind"] == "spring_import_selector"}
    for name in ("app.Limit", "app.Missing", "app.NonType"):
        assert selectors[name]["metadata"]["selection_status"] == "UNKNOWN"
    assert "TARGET_LIMIT_EXCEEDED" in selectors["app.Limit"]["metadata"]["reasons"]
    assert "NON_CLASS_NAME_LITERAL" in selectors["app.NonType"]["metadata"]["reasons"]
    assert any(reason.startswith("TARGET_NOT_INDEXED:") for reason in selectors["app.Missing"]["metadata"]["reasons"])
    assert not any(node["name"] == "external.Absent" for node in graph["nodes"])
    assert next(node for node in graph["nodes"] if node["kind"] == "spring_bean" and node["name"] == "MissingTarget")["metadata"]["condition_status"] == "UNKNOWN"


def test_legacy_facts_stay_readable_without_literal_promotion(actual_imports):
    root, options, _ = actual_imports
    original = inspection.request_worker
    def legacy(*args, **kwargs):
        response = original(*args, **kwargs)
        for symbol in response["symbols"]:
            for key in ("type_hierarchy", "import_selector", "static_import_return"):
                symbol.pop(key, None)
        return response
    with patch("kgmaker.inspection.request_worker", side_effect=legacy):
        result = inspection.inspect_jvm(root, **options)
    selectors = [node for node in result["graph"]["nodes"] if node["kind"] == "spring_import_selector"]
    assert selectors and all(node["metadata"]["selection_status"] == "UNKNOWN" for node in selectors)
    assert not any(edge["kind"] == "selects_import" for edge in result["graph"]["edges"])
    for version in (1, 2, 3):
        payload = copy.deepcopy(result["graph"])
        payload["schema_version"] = version
        assert KnowledgeGraph.from_dict(payload).schema_version == version


def test_inactive_profile_does_not_reuse_another_context_selection(actual_imports):
    root, options, _ = actual_imports
    red = {**options, "build_context": {**options["build_context"], "spring_profiles": ["red"]}}
    result = inspection.inspect_jvm(root, **red)
    assert result["context"]["spring_profiles"] == ["red"]
    assert not any(node["kind"] == "spring_import_selector" for node in result["graph"]["nodes"])
    assert all(node["metadata"]["condition_status"] == "INACTIVE" for node in result["graph"]["nodes"]
               if node["kind"] == "spring_bean" and node["name"].endswith("Target"))


def test_static_import_selection_is_not_data_availability(actual_imports):
    root, _, _ = actual_imports
    (root / "requirement.md").write_text("Use the direct value.")
    packet = feature.prepare(root, "requirement.md", "selector", 200_000)
    graph = feature.graph_for_packet(root, packet)
    bean = next(node for node in graph.nodes if node.kind == "spring_bean" and node.name == "direct")
    requirement_id = "analysis:selector:requirement:direct"
    specification = {"schema_version": 1, "analysis_id": "selector", "requirement_hash": packet["requirement_hash"],
        "requirements": [{"id": requirement_id, "text": "Use direct value", "kind": "InputRequirement", "source_quote": "direct value"}],
        "inputs": [{"id": "analysis:selector:input:direct", "name": "direct", "requirement_ids": [requirement_id],
                    "candidate_entity_ids": [bean.id], **{key: None for key in INPUT_METADATA}}]}
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    real_popen = subprocess.Popen
    def baseline_only(argv, *args, **kwargs):
        assert argv == ["git", "-C", str(root), "rev-parse", "HEAD"]
        return real_popen(argv, *args, **kwargs)
    with patch("subprocess.Popen", side_effect=baseline_only):
        result = data_check(root, "selector", specification)
    assert result["valid"]
    assert result["candidate"]["input_requirements"][0]["availability"] == "UNKNOWN"
    assert not result["data_delivery_gaps"]
    assert {path: path.read_bytes() for path in root.rglob("*") if path.is_file()} == before

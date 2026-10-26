"""T003-S05-W03 bounded condition semantics and real pinned API inputs."""
import pytest
import hashlib
import json
import os
from pathlib import Path
import zipfile

from kgmaker.spring_conditions import AnnotationArguments, evaluate_conditions
from kgmaker.inspection import command, inspect_jvm
from kgmaker.worker_protocol import WorkerError
from kgmaker.graph_provider import validate_context_snapshot
from kgmaker.analysis_model import digest
from kgmaker.spring_conditions import condition_inputs
from unittest.mock import patch

PROFILE = "org.springframework.context.annotation.Profile"
PROPERTY = "org.springframework.boot.autoconfigure.condition.ConditionalOnProperty"
CLASS = "org.springframework.boot.autoconfigure.condition.ConditionalOnClass"


def evaluate(name, values, context, *, resolved=True):
    return evaluate_conditions([(name, AnnotationArguments("", values, resolved))], context)[0]


@pytest.mark.parametrize("expression,profiles,status", [
    ("dev", ["dev"], "ACTIVE"), ("!dev", ["prod"], "ACTIVE"),
    ("!dev", ["dev"], "INACTIVE"), ("dev | qa", ["qa"], "ACTIVE"),
    ("dev & cloud", ["dev"], "INACTIVE"),
    ("(dev & cloud) | qa", ["qa"], "ACTIVE"),
    ("dev & cloud | qa", ["qa"], "UNKNOWN"),
    ("dev |", ["dev"], "UNKNOWN"), ("()", ["dev"], "UNKNOWN"),
    ("default", [], "ACTIVE"), ("dev", None, "UNKNOWN"),
])
def test_profile_expressions(expression, profiles, status):
    assert evaluate(PROFILE, {"value": [expression]}, {"spring_profiles": profiles}) == status


@pytest.mark.parametrize("value,status", [("true", "ACTIVE"), ("false", "INACTIVE"),
    ("FALSE", "INACTIVE"), ("", "ACTIVE"), ("other", "ACTIVE"), (False, "UNKNOWN"),
    (None, "UNKNOWN"), ({"nested": "value"}, "UNKNOWN")])
def test_default_property_matches_strings_except_false(value, status):
    assert evaluate(PROPERTY, {"name": ["enabled"]}, {"spring_properties": {"enabled": value}}) == status


def test_property_alias_prefix_all_names_and_case_insensitive_value():
    args = {"name": ["one", "two"], "prefix": "feature", "havingValue": "TRUE"}
    assert evaluate(PROPERTY, args, {"spring_properties": {"feature.one": "true", "feature.two": "TrUe"}}) == "ACTIVE"
    assert evaluate(PROPERTY, args, {"spring_properties": {"feature.one": "true", "feature.two": "false"}}) == "INACTIVE"
    assert evaluate(PROPERTY, {**args, "value": ["other"]}, {"spring_properties": {}}) == "UNKNOWN"
    assert evaluate(PROPERTY, {"name": ["absent"], "matchIfMissing": True}, {"spring_properties": {}}) == "ACTIVE"
    assert evaluate(PROPERTY, {"name": ["absent"], "matchIfMissing": "true"}, {"spring_properties": {}}) == "UNKNOWN"


def test_all_class_names_required_and_missing_inventory_unknown():
    args = {"value": ["java.lang.String"], "name": ["fixture.Optional"]}
    assert evaluate(CLASS, args, {"spring_available_classes": ["java.lang.String", "fixture.Optional"]}) == "ACTIVE"
    assert evaluate(CLASS, args, {"spring_available_classes": ["java.lang.String"]}) == "INACTIVE"
    assert evaluate(CLASS, args, {}) == "UNKNOWN"


def test_unresolved_and_foreign_conditions_never_gain_activation():
    assert evaluate(PROPERTY, {"name": ["x"]}, {"spring_properties": {"x": "true"}}, resolved=False) == "UNKNOWN"
    assert evaluate(PROFILE, {"value": ["dev"]}, {"spring_profiles": [1]}) == "UNKNOWN"
    assert evaluate_conditions([("org.springframework.context.annotation.Conditional",
        AnnotationArguments("", {"value": ["fixture.Custom"]}))], {})[0] == "UNKNOWN"


def test_profile_array_is_or_and_inactive_condition_dominates_unknown():
    assert evaluate(PROFILE, {"value": ["dev", "qa"]}, {"spring_profiles": ["qa"]}) == "ACTIVE"
    values = [(PROFILE, AnnotationArguments("", {"value": ["dev"]})),
              (CLASS, AnnotationArguments("", {"name": ["fixture.Optional"]}))]
    assert evaluate_conditions(values, {"spring_profiles": ["prod"]})[0] == "INACTIVE"


@pytest.mark.parametrize("changed", ["spring_profiles", "spring_properties", "spring_available_classes"])
def test_tampered_condition_snapshot_is_stale_without_process_or_mutation(tmp_path, changed):
    import copy
    context = {"language": "jvm", "framework_rule_versions": {"spring": "annotation-source-v6"},
               "spring_profiles": ["prod"], "spring_properties": {"enabled": "true"},
               "spring_available_classes": ["java.lang.String"]}
    context["spring_condition_inputs_hash"] = digest(condition_inputs(context))
    before = copy.deepcopy(context)
    with patch("subprocess.Popen", side_effect=AssertionError("implicit process")):
        validate_context_snapshot(tmp_path, context)
        assert context == before
        context[changed] = None
        tampered = copy.deepcopy(context)
        with pytest.raises(WorkerError, match="condition configuration changed"):
            validate_context_snapshot(tmp_path, context)
        assert context == tampered


@pytest.mark.parametrize("old", ["annotation-source-v3", "annotation-source-v4", "annotation-source-v5"])
def test_legacy_spring_rules_remain_readable_but_require_reinspection(tmp_path, old):
    from kgmaker.model import KnowledgeGraph
    context = {"id": "old", "language": "jvm", "framework_rule_versions": {"spring": old}}
    graph = KnowledgeGraph.from_dict({"schema_version": 3, "root": str(tmp_path), "generated_at": "",
                                     "files": {}, "nodes": [], "edges": [], "contexts": [context]})
    assert graph.contexts[0] == context
    with pytest.raises(WorkerError, match="condition rules changed"):
        validate_context_snapshot(tmp_path, context)


@pytest.fixture(params=["k1", "k2"])
def actual_conditions(request, tmp_path):
    home = Path(__file__).resolve().parents[1] / "workers"
    fixture = home.parent / "fixtures/spring-conditions"
    repository = Path(os.environ.get("KGMAKER_TEST_MAVEN_REPOSITORY", Path.home() / ".m2/repository"))
    lock = json.loads((fixture / "dependencies.lock.json").read_text())
    try:
        command("jvm", home, kotlin_backend=request.param)
        jars = [repository / item["path"] for item in lock["artifacts"]]
        for path, item in zip(jars, lock["artifacts"]):
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise WorkerError("pinned Spring6.2.2/Boot3.4.2 condition API unavailable", "TOOLCHAIN_UNAVAILABLE")
            with zipfile.ZipFile(path) as archive:
                assert archive.read(item["license_entry"])
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1" or os.environ.get("KGMAKER_REQUIRE_SPRING_CONDITIONS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    source = tmp_path / "src/main/java/fixture/Conditions.java"
    source.parent.mkdir(parents=True)
    source.write_text('''package fixture;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.Profile;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
@Service("profileOr") @Profile({"dev","qa"}) class ProfileOr {}
@Service("negative") @Profile("!dev") class Negative implements Gateway {}
@Service("malformed") @Profile("dev & cloud | qa") class Malformed {}
@Service("properties") @ConditionalOnProperty(prefix="feature",name={"one","two"},havingValue="TRUE") class Properties {}
@Service("missing") @ConditionalOnProperty(name="absent",matchIfMissing=true) class Missing {}
@Service("text") @ConditionalOnProperty(name="text") class Text {}
@Service("classAbsent") @ConditionalOnClass(name={"java.lang.String","fixture.MissingApi"}) class ClassAbsent {}
@Service("classPresent") @ConditionalOnClass(value=String.class,name="fixture.Optional") class ClassPresent {}
interface Gateway {}
@Service("consumer") class Consumer { Gateway gateway; }
''')
    kotlin = tmp_path / "src/main/kotlin/fixture/KotlinConditions.kt"
    kotlin.parent.mkdir(parents=True)
    kotlin.write_text('''package fixture
import org.springframework.stereotype.Service
import org.springframework.context.annotation.Profile
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty
@Service("kotlinNegative") @Profile("!dev") class KotlinNegative
@Service("kotlinProperties") @ConditionalOnProperty(prefix="feature",name=["one","two"],havingValue="TRUE") class KotlinProperties
''')
    options = {"home": home, "kotlin_backend": request.param, "repo_id": "conditions",
               "module": "core", "publish": False,
               "classpath": [str(p) for p in jars] + [str(home / "jvm/target/lib/kotlin-stdlib.jar")]}
    return tmp_path, options


def test_actual_pinned_conditions_and_negated_profile_injection(actual_conditions):
    root, options = actual_conditions
    result = inspect_jvm(root, **options, build_context={"spring_profiles": ["qa"],
        "spring_properties": {"feature.one": "true", "feature.two": "TrUe", "text": "garbage"},
        "spring_available_classes": ["java.lang.String", "fixture.Optional"],
        "spring_component_packages": ["fixture"]})
    graph = result["graph"]
    beans = {n["name"]: n for n in graph["nodes"] if n["kind"] == "spring_bean"}
    expected = {"profileOr": "ACTIVE", "negative": "ACTIVE", "malformed": "UNKNOWN",
                "properties": "ACTIVE", "missing": "ACTIVE", "text": "ACTIVE",
                "classAbsent": "INACTIVE", "classPresent": "ACTIVE",
                "kotlinNegative": "ACTIVE", "kotlinProperties": "ACTIVE"}
    assert set(expected) <= set(beans), {"beans": sorted(beans), "diagnostics": graph["diagnostics"],
        "kotlin": [s for s in graph["symbols"] if str(s.get("path", "")).endswith(".kt")]}
    assert {name: beans[name]["metadata"]["condition_status"] for name in expected} == expected
    injection = next(n for n in graph["nodes"] if n["kind"] == "spring_injection" and n["name"] == "Consumer.gateway")
    assert any(e["kind"] == "injects_bean" and e["source"] == injection["id"] and e["target"] == beans["negative"]["id"]
               for e in graph["edges"])
    assert all(n["metadata"]["condition_reasons"] for name, n in beans.items() if name in expected)
    assert not (root / ".kgmaker/graph.json").exists()

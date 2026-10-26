"""T003-S05-W02 actual compiler declarations, never Spring execution."""
import copy
import hashlib
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kgmaker import inspection, feature
from kgmaker.analysis_model import AnalysisError, INPUT_METADATA
from kgmaker.data_check import data_check
from kgmaker.model import KnowledgeGraph
from kgmaker.graph_provider import retain_compiler_layer
from kgmaker.scanner import scan_repository
from kgmaker.worker_protocol import WorkerError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=("k1", "k2"))
def registration_project(request, tmp_path_factory):
    lock = json.loads((ROOT / "fixtures/spring-imports/dependencies.lock.json").read_text())
    repo = Path(os.environ.get("KGMAKER_TEST_MAVEN_REPOSITORY", Path.home() / ".m2/repository"))
    jars = [repo / item["path"] for item in lock["artifacts"]]
    try:
        inspection.command("jvm", ROOT / "workers", kotlin_backend=request.param)
        for jar, item in zip(jars, lock["artifacts"]):
            if hashlib.sha256(jar.read_bytes()).hexdigest() != item["sha256"]:
                raise WorkerError("Pinned Spring API changed", "TOOLCHAIN_UNAVAILABLE")
            with zipfile.ZipFile(jar) as archive:
                assert item["license_entry"] in archive.namelist()
    except (OSError, WorkerError) as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1" or os.environ.get("KGMAKER_REQUIRE_SPRING_IMPORTS") == "1":
            pytest.fail(str(error))
        pytest.skip("blocked: " + str(error))
    root = tmp_path_factory.mktemp("registrations-" + request.param)
    sources = {
        "Main": '''package app; import org.springframework.context.annotation.*;
@Configuration @Profile("blue") @Import({LiteralRegistrar.class,InheritedRegistrar.class,ConditionalRegistrar.class,CustomRegistrar.class,LimitRegistrar.class,DecoyRegistrar.class})
public class Main {
@Bean public org.springframework.beans.factory.FactoryBean<Product> methodFactory(){throw new AssertionError("never execute");}
@Bean public LiteralFactory anonymousFactory(){return new LiteralFactory(){public Product getObject(){return null;} public Class<?> getObjectType(){return Other.class;}};}
@Bean public org.springframework.beans.factory.FactoryBean<Product> literalProducer(){return new LiteralFactory();}
}''',
        "Product": "package app; public class Product implements Api {}",
        "Api": "package app; public interface Api {}",
        "Other": "package app; public class Other {}",
        "LiteralRegistrar": '''package app; public class LiteralRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){r.registerBeanDefinition("registered",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));} }''',
        "RegistrarParent": '''package app; public abstract class RegistrarParent implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){r.registerBeanDefinition("inherited",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));} }''',
        "InheritedRegistrar": "package app; public class InheritedRegistrar extends RegistrarParent {}",
        "ConditionalRegistrar": '''package app; public class ConditionalRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){if(m.hasAnnotation("app.Custom"))r.registerBeanDefinition("conditional",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));} }''',
        "DecoyRegistrar": '''package app; public class DecoyRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){new fake.Registry().registerBeanDefinition("decoy",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));} }''',
        "CustomRegistrar": '''package app; public class CustomRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){r.registerBeanDefinition("custom",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));}
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r,org.springframework.beans.factory.support.BeanNameGenerator n){throw new AssertionError("never invoke");} }''',
        "UnknownConfig": '''package app; @org.springframework.context.annotation.Configuration @org.springframework.context.annotation.Conditional(CustomCondition.class) @org.springframework.context.annotation.Import({ConditionRegistrar.class,LiteralRegistrar.class}) public class UnknownConfig {}''',
        "CustomCondition": '''package app; public class CustomCondition implements org.springframework.context.annotation.Condition {public boolean matches(org.springframework.context.annotation.ConditionContext c,org.springframework.core.type.AnnotatedTypeMetadata m){throw new AssertionError("never execute condition");}}''',
        "ConditionRegistrar": '''package app; public class ConditionRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {
public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){r.registerBeanDefinition("maybeRegistered",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));} }''',
        "LiteralFactory": '''package app; import org.springframework.stereotype.Component; import org.springframework.context.annotation.Profile;
@Component("literalFactory") @Profile("blue") public class LiteralFactory implements org.springframework.beans.factory.FactoryBean<Product> {
static {if(Boolean.parseBoolean("true"))throw new AssertionError("never initialize");}
public Product getObject(){return new Product();} public Class<?> getObjectType(){return Product.class;} }''',
        "UnknownFactory": '''package app; @org.springframework.stereotype.Component("unknownFactory") public class UnknownFactory implements org.springframework.beans.factory.FactoryBean<Product> {
public Product getObject(){throw new AssertionError("never invoke");} public Class<?> getObjectType(){return Product.class;} }''',
        "MismatchFactory": '''package app; @org.springframework.stereotype.Component("mismatchFactory") public class MismatchFactory implements org.springframework.beans.factory.FactoryBean<Product> {
public Product getObject(){return new Product();} public Class<?> getObjectType(){return Other.class;} }''',
        "OtherFactory": '''package app; @org.springframework.stereotype.Component("otherFactory") public class OtherFactory implements org.springframework.beans.factory.FactoryBean<Other> {public Other getObject(){return new Other();} public Class<?> getObjectType(){return Other.class;}}''',
        "DualFactory": "package app; @org.springframework.stereotype.Component(\"dualFactory\") public class DualFactory implements org.springframework.beans.factory.FactoryBean<Product>, fake.FactoryBean {public Product getObject(){return new Product();} public Class<?> getObjectType(){return Product.class;}}",
        "DecoyConsumer": '''package app;
import fake.FactoryBean;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.*;
@Service public class DecoyConsumer {
@Autowired @Qualifier("&literalFactory") FactoryBean wrongFactory;
@Autowired @Qualifier("&dualFactory") FactoryBean validDual;
}''',
        "FakeFactory": "package app; @org.springframework.stereotype.Component public class FakeFactory implements fake.FactoryBean {}",
        "FactoryParent": '''package app; public abstract class FactoryParent<T> implements org.springframework.beans.factory.FactoryBean<T> {public T getObject(){return null;} public Class<?> getObjectType(){return Product.class;}}''',
        "InheritedFactory": '''package app; @org.springframework.stereotype.Component("inheritedFactory") public class InheritedFactory extends FactoryParent<Product> {}''',
        "AbstractFactory": '''package app; @org.springframework.stereotype.Component("abstractFactory") public abstract class AbstractFactory implements org.springframework.beans.factory.FactoryBean<Product> {public Product getObject(){return new Product();} public Class<?> getObjectType(){return Product.class;}}''',
        "Consumer": '''package app; import org.springframework.beans.factory.annotation.*; import org.springframework.stereotype.Service; import org.springframework.beans.factory.FactoryBean;
@Service public class Consumer {
@Autowired @Qualifier("registered") Product registered;
@Autowired @Qualifier("registered") Api registeredApi;
@Autowired @Qualifier("literalFactory") Product literal;
@Autowired @Qualifier("unknownFactory") Product unknown;
@Autowired @Qualifier("&literalFactory") LiteralFactory factory;
@Autowired @Qualifier("&literalFactory") FactoryBean<Product> apiFactory;
@Autowired @Qualifier("FakeFactory") FactoryBean<Product> fakeApi;
@Autowired @Qualifier("&otherFactory") FactoryBean<Product> wrongGeneric;
}''',
    }
    calls = ''.join('r.registerBeanDefinition("limit' + str(i) + '",new org.springframework.beans.factory.support.RootBeanDefinition(Product.class));' for i in range(129))
    sources["LimitRegistrar"] = 'package app; public class LimitRegistrar implements org.springframework.context.annotation.ImportBeanDefinitionRegistrar {public void registerBeanDefinitions(org.springframework.core.type.AnnotationMetadata m,org.springframework.beans.factory.support.BeanDefinitionRegistry r){' + calls + '}}'
    for name, text in sources.items():
        path = root / "src/main/java/app" / (name + ".java")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    fake = root / "src/main/java/fake/FactoryBean.java"
    fake.parent.mkdir()
    fake.write_text("package fake; public interface FactoryBean {}")
    (fake.parent / "Registry.java").write_text("package fake; public class Registry {public void registerBeanDefinition(String name,Object definition){throw new AssertionError(\"never execute decoy\");}}")
    foreign = root / "src/main/java/other"
    foreign.mkdir()
    (foreign / "Product.java").write_text("package other; public class Product {}")
    (foreign / "ForeignConsumer.java").write_text('''package other;
import org.springframework.stereotype.Service; import org.springframework.beans.factory.annotation.*;
@Service public class ForeignConsumer {
@Autowired @Qualifier("literalFactory") Product factoryProduct;
@Autowired @Qualifier("registered") Product registeredProduct;
}''')
    options = {"home": ROOT / "workers", "kotlin_backend": request.param, "publish": False,
               "classpath": [str(jar) for jar in jars], "build_context": {"spring_profiles": ["blue"],
               "spring_properties": {}, "spring_available_classes": [], "spring_component_packages": ["app", "other"]}}
    result = inspection.inspect_jvm(root, **options)
    assert not [d for d in result["diagnostics"] if d["code"].startswith("JAVAC_")]
    return root, options, result


def test_literal_registrar_preserves_origin_and_import_condition(registration_project):
    _, _, result = registration_project
    graph = result["graph"]
    for name in ("registered", "inherited"):
        bean = next(n for n in graph["nodes"] if n["kind"] == "spring_bean" and n["name"] == name)
        assert bean["metadata"]["condition_status"] == "ACTIVE"
        assert bean["metadata"]["registration_origin"] == "REGISTRAR_LITERAL"
        proof = next(e for e in graph["edges"] if e["target"] == bean["id"] and e["kind"] == "registers_bean")
        assert proof["evidence_kind"] == "FRAMEWORK_DERIVED"
        assert tuple(proof["context_ids"]) == (result["context"]["id"],)
    assert not any(n["name"] in {"conditional", "decoy"} and n["metadata"].get("condition_status") == "ACTIVE"
                   for n in graph["nodes"] if n["kind"] == "spring_bean")
    for name in ("custom", "maybeRegistered"):
        assert next(n for n in graph["nodes"] if n["kind"] == "spring_bean" and n["name"] == name)["metadata"]["condition_status"] == "UNKNOWN"
    assert not any(n["kind"] == "spring_bean" and n["name"].startswith("limit") for n in graph["nodes"])
    limit = next(n for n in graph["nodes"] if n["kind"] == "spring_registrar" and n["name"] == "app.LimitRegistrar")
    assert "REGISTRATION_LIMIT_EXCEEDED" in limit["metadata"]["reasons"]


def test_factory_object_and_literal_product_are_distinct(registration_project):
    _, _, result = registration_project
    beans = {n["name"]: n for n in result["graph"]["nodes"] if n["kind"] == "spring_bean"}
    assert beans["&literalFactory"]["metadata"]["registration_origin"] == "FACTORY_OBJECT"
    assert beans["literalFactory"]["metadata"]["registration_origin"] == "FACTORY_PRODUCT"
    assert {"Product", "Api"} <= set(beans["literalFactory"]["metadata"]["types"])
    assert beans["literalFactory"]["metadata"]["condition_status"] == "ACTIVE"
    assert beans["FakeFactory"]["metadata"].get("registration_origin") != "FACTORY_OBJECT"
    for name in ("unknownFactory", "mismatchFactory", "methodFactory", "inheritedFactory", "abstractFactory", "&abstractFactory"):
        assert beans[name]["metadata"]["condition_status"] == "UNKNOWN"
    assert beans["inheritedFactory"]["metadata"]["declared_type"] == "app.Product"
    for field, kind in (("registered", "injects_bean"), ("registeredApi", "injects_bean"), ("literal", "injects_bean"),
                        ("factory", "injects_bean"), ("apiFactory", "injects_bean"), ("unknown", "may_inject_bean")):
        injection = next(n for n in result["graph"]["nodes"] if n["kind"] == "spring_injection" and n["name"] == "Consumer." + field)
        assert any(e["source"] == injection["id"] and e["kind"] == kind for e in result["graph"]["edges"])
    for field in ("fakeApi", "wrongGeneric"):
        invalid = next(n for n in result["graph"]["nodes"] if n["kind"] == "spring_injection" and n["name"] == "Consumer." + field)
        assert not any(e["source"] == invalid["id"] and e["kind"] in {"injects_bean", "may_inject_bean"} for e in result["graph"]["edges"])


def test_registration_profiles_do_not_cross_context(registration_project):
    root, options, blue = registration_project
    red = inspection.inspect_jvm(root, **{**options, "build_context": {**options["build_context"], "spring_profiles": ["red"]}})
    assert red["context"]["id"] != blue["context"]["id"]
    assert not any(n["name"] in {"registered", "inherited", "literalFactory"} and n["metadata"]["condition_status"] == "ACTIVE"
                   for n in red["graph"]["nodes"] if n["kind"] == "spring_bean")


def test_factory_producer_and_qualified_product_selection(registration_project):
    _, _, result = registration_project
    graph = result["graph"]
    beans = {n["name"]: n for n in graph["nodes"] if n["kind"] == "spring_bean"}
    assert beans["anonymousFactory"]["metadata"]["condition_status"] == "UNKNOWN"
    assert beans["literalProducer"]["metadata"]["condition_status"] == "ACTIVE"
    invalid_factory = next(n for n in graph["nodes"] if n["kind"] == "spring_injection" and n["name"] == "DecoyConsumer.wrongFactory")
    assert not any(e["source"] == invalid_factory["id"] and e["kind"] in {"injects_bean", "may_inject_bean"} for e in graph["edges"])
    valid_dual = next(n for n in graph["nodes"] if n["kind"] == "spring_injection" and n["name"] == "DecoyConsumer.validDual")
    assert any(e["source"] == valid_dual["id"] and e["target"] == beans["&dualFactory"]["id"] and e["kind"] == "injects_bean" for e in graph["edges"])
    for field in ("factoryProduct", "registeredProduct"):
        injection = next(n for n in graph["nodes"] if n["kind"] == "spring_injection" and n["name"] == "ForeignConsumer." + field)
        assert not any(e["source"] == injection["id"] and e["kind"] in {"injects_bean", "may_inject_bean"} for e in graph["edges"])


def test_registration_invalid_facts_and_strict_failures_preserve_store(registration_project):
    root, options, _ = registration_project
    inspection.inspect_jvm(root, **{**options, "publish": True})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    strict = inspection.inspect_jvm(root, **{**options, "publish": True, "strict": True})
    assert strict["exit_code"] == 4 and store.read_bytes() == before
    original = inspection.request_worker
    def malformed(*args, **kwargs):
        response = original(*args, **kwargs)
        symbol = next(s for s in response["symbols"] if s.get("owner") == "app.LiteralRegistrar" and s.get("kind") == "class")
        symbol["bean_registrar"] = {"schema_version": 99}
        return response
    with patch("kgmaker.inspection.request_worker", side_effect=malformed):
        with pytest.raises(AnalysisError, match="registrar"):
            inspection.inspect_jvm(root, **{**options, "publish": True})
    assert store.read_bytes() == before
    with patch("subprocess.Popen", side_effect=AssertionError("offline process")):
        graph = retain_compiler_layer(root, scan_repository(root))
    assert any(n.kind == "spring_bean" and n.name == "registered" for n in graph.nodes)


@pytest.mark.parametrize("case", ["owner", "context", "return_shape", "producer_shape"])
def test_factory_invalid_context_and_timeout_preserve_store(registration_project, case):
    root, options, _ = registration_project
    inspection.inspect_jvm(root, **{**options, "publish": True})
    store = root / ".kgmaker/graph.json"
    before = store.read_bytes()
    original = inspection.request_worker
    def malformed(*args, **kwargs):
        response = original(*args, **kwargs)
        symbol = next(s for s in response["symbols"] if s.get("owner") == "app.LiteralFactory" and s.get("kind") == "class")
        if case == "owner":
            symbol["factory_bean"]["get_object_owner"] = []
        elif case == "context":
            symbol["context_id"] = "another-context"
        elif case == "return_shape":
            method = next(s for s in response["symbols"] if s.get("owner") == "app.LiteralFactory" and s.get("name") == "getObject")
            method["factory_return"]["status"] = []
        else:
            method = next(s for s in response["symbols"] if s.get("owner") == "app.Main" and s.get("name") == "literalProducer")
            method["factory_producer"]["status"] = []
        return response
    with patch("kgmaker.inspection.request_worker", side_effect=malformed):
        with pytest.raises(ValueError if case == "context" else AnalysisError,
                           match="compiler symbol or context" if case == "context" else "factory"):
            inspection.inspect_jvm(root, **{**options, "publish": True})
    with patch("kgmaker.inspection.request_worker", side_effect=WorkerError("timeout", "TIMEOUT")):
        with pytest.raises(WorkerError):
            inspection.inspect_jvm(root, **{**options, "publish": True})
    assert store.read_bytes() == before


def test_registrar_and_factory_static_beans_are_not_data_availability(registration_project):
    import subprocess
    root, options, _ = registration_project
    inspection.inspect_jvm(root, **{**options, "publish": True})
    (root / "requirement.md").write_text("Use the registered product.")
    packet = feature.prepare(root, "requirement.md", "registrar", 200_000)
    graph = feature.graph_for_packet(root, packet)
    bean = next(n for n in graph.nodes if n.kind == "spring_bean" and n.name == "registered")
    requirement = "analysis:registrar:requirement:product"
    specification = {"schema_version": 1, "analysis_id": "registrar", "requirement_hash": packet["requirement_hash"],
        "requirements": [{"id": requirement, "text": "Use product", "kind": "InputRequirement", "source_quote": "registered product"}],
        "inputs": [{"id": "analysis:registrar:input:product", "name": "product", "requirement_ids": [requirement],
                    "candidate_entity_ids": [bean.id], **{key: None for key in INPUT_METADATA}}]}
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    popen = subprocess.Popen
    def baseline_only(argv, *args, **kwargs):
        assert argv == ["git", "-C", str(root), "rev-parse", "HEAD"]
        return popen(argv, *args, **kwargs)
    with patch("subprocess.Popen", side_effect=baseline_only):
        result = data_check(root, "registrar", specification)
    assert result["valid"] and result["candidate"]["input_requirements"][0]["availability"] == "UNKNOWN"
    assert not result["data_delivery_gaps"]
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_legacy_registration_facts_remain_readable_without_promotion(registration_project):
    root, options, _ = registration_project
    original = inspection.request_worker
    def legacy(*args, **kwargs):
        response = original(*args, **kwargs)
        for symbol in response["symbols"]:
            for field in ("bean_registrar", "bean_registrations", "factory_bean", "factory_bean_return", "factory_producer", "factory_return"):
                symbol.pop(field, None)
            if "Factory" in symbol.get("owner", ""):
                symbol.pop("type_hierarchy", None)
        return response
    with patch("kgmaker.inspection.request_worker", side_effect=legacy):
        result = inspection.inspect_jvm(root, **options)
    assert not any(n["kind"] == "spring_bean" and n["name"] == "registered" for n in result["graph"]["nodes"])
    products = [n for n in result["graph"]["nodes"] if n["kind"] == "spring_bean"
                and n["metadata"].get("registration_origin") == "FACTORY_PRODUCT"]
    assert products and all(n["metadata"]["condition_status"] == "UNKNOWN" for n in products)
    for version in (1, 2, 3):
        graph = copy.deepcopy(result["graph"])
        graph["schema_version"] = version
        assert KnowledgeGraph.from_dict(graph).schema_version == version


def test_registry_name_collision_cannot_be_promoted_by_primary(registration_project):
    root, options, _ = registration_project
    path = root / "src/main/java/app/CollisionConfig.java"
    path.write_text('''package app; @org.springframework.context.annotation.Configuration public class CollisionConfig {
@org.springframework.context.annotation.Bean("registered") @org.springframework.context.annotation.Primary
public Product duplicate(){throw new AssertionError("must never execute");}}''')
    try:
        result = inspection.inspect_jvm(root, **options)
        assert any(d["code"] == "SPRING_REGISTRATION_NAME_COLLISION" for d in result["diagnostics"])
        assert all(n["metadata"]["condition_status"] == "UNKNOWN" for n in result["graph"]["nodes"]
                   if n["kind"] == "spring_bean" and n["name"] == "registered")
        injection = next(n for n in result["graph"]["nodes"] if n["kind"] == "spring_injection" and n["name"] == "Consumer.registered")
        assert not any(e["kind"] == "injects_bean" and e["source"] == injection["id"] for e in result["graph"]["edges"])
    finally:
        path.unlink()

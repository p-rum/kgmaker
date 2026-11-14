"""T003-S05-W04 bounded Spring proxy, async and event semantics."""
import os
from pathlib import Path

import pytest

from kgmaker.analysis_model import file_hash
from kgmaker.flow import process
from kgmaker.framework import SPRING_RULE_VERSION, augment_framework_graph
from kgmaker.inspection import inspect_jvm
from kgmaker.model import Edge, KnowledgeGraph, Node
from kgmaker.worker_protocol import WorkerError


def _line(source: str, marker: str) -> int:
    return next(index for index, text in enumerate(source.splitlines(), 1) if marker in text)


def _graph(tmp_path: Path, *, cglib: bool = False, ambiguous: bool = False) -> KnowledgeGraph:
    strategy = "true" if cglib else "false"
    source = f"""package example;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.Async;
import org.springframework.context.event.EventListener;
import org.springframework.transaction.annotation.Transactional;
@Configuration @EnableAspectJAutoProxy(proxyTargetClass={strategy})
@EnableTransactionManagement(proxyTargetClass={strategy}) @EnableAsync(proxyTargetClass={strategy})
class ProxyConfig {{}}
interface WorkApi {{ @Transactional public void advised(); public void asyncWork(); }}
@Service class WorkService implements WorkApi {{
  public void advised() {{}}
  @Transactional public void classAdvised() {{}}
  @Async public void asyncWork() {{}}
  @EventListener public void onEvent(String value) {{}}
  public reactor.core.publisher.Mono<String> reactiveWork() {{ return null; }}
  void local() {{ classAdvised(); asyncWork(); }}
}}
{"@Service class OtherService implements WorkApi { public void advised() {} public void asyncWork() {} }" if ambiguous else ""}
@Service class Caller {{
  WorkApi api;
  WorkService service;
  public void callInterface() {{ api.advised(); }}
  public void callClass() {{ service.classAdvised(); }}
  public void callAsync() {{ api.asyncWork(); }}
  public void callLocal() {{ new WorkService().classAdvised(); }}
}}
"""
    path = tmp_path / "src/main/java/example/Fixture.java"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    relative = "src/main/java/example/Fixture.java"
    context = {"id": "spring-proxy", "language": "jvm", "scope": "production",
               "framework_rule_versions": {"spring": SPRING_RULE_VERSION},
               "spring_component_packages": ["example"], "spring_profiles": [],
               "spring_properties": {}, "spring_available_classes": []}
    symbols = []
    nodes = []

    def symbol(identity, name, kind, owner, marker, *, annotations=None, modifiers=None,
               supertypes=None, return_type=None, field_type=None):
        line = _line(source, marker)
        value = {"id": identity, "name": name, "kind": kind, "owner": owner,
                 "path": relative, "range": {"start_line": line}, "context_id": context["id"],
                 "annotations": annotations or [], "modifiers": modifiers or []}
        if supertypes is not None:
            value["supertypes"] = supertypes
        if return_type is not None:
            value["return_type"] = return_type
        if field_type is not None:
            value["type"] = field_type
        symbols.append(value)
        nodes.append(Node(identity, kind, name, relative, line=line, scope="production",
                          role="contract" if kind == "interface" else "executable_code",
                          origin="handwritten"))
        return value

    configuration = [{"name": "org.springframework.context.annotation.Configuration", "values": {}},
                     {"name": "org.springframework.context.annotation.EnableAspectJAutoProxy",
                      "values": {"proxyTargetClass": cglib, "exposeProxy": False}},
                     {"name": "org.springframework.transaction.annotation.EnableTransactionManagement",
                      "values": {"proxyTargetClass": cglib,
                                 "mode": "org.springframework.context.annotation.AdviceMode.PROXY"}},
                     {"name": "org.springframework.scheduling.annotation.EnableAsync",
                      "values": {"proxyTargetClass": cglib,
                                 "mode": "org.springframework.context.annotation.AdviceMode.PROXY"}}]
    service = [{"name": "org.springframework.stereotype.Service", "values": {"value": ""}}]
    transactional = [{"name": "org.springframework.transaction.annotation.Transactional", "values": {}}]
    asynchronous = [{"name": "org.springframework.scheduling.annotation.Async", "values": {"value": ""}}]
    listener = [{"name": "org.springframework.context.event.EventListener", "values": {"value": []}}]
    symbol("config", "ProxyConfig", "class", "example.ProxyConfig", "class ProxyConfig", annotations=configuration)
    symbol("api", "WorkApi", "interface", "example.WorkApi", "interface WorkApi")
    symbol("api-advised", "advised", "method", "example.WorkApi", "interface WorkApi",
           annotations=transactional, modifiers=["public"], return_type="void")
    symbol("api-async", "asyncWork", "method", "example.WorkApi", "interface WorkApi",
           modifiers=["public"], return_type="void")
    symbol("service", "WorkService", "class", "example.WorkService", "class WorkService",
           annotations=service, supertypes=["example.WorkApi"])
    if ambiguous:
        symbol("other-service", "OtherService", "class", "example.OtherService", "class OtherService",
               annotations=service, supertypes=["example.WorkApi"])
    symbol("service-advised", "advised", "method", "example.WorkService", "public void advised()",
           modifiers=["public"], return_type="void")
    symbol("class-advised", "classAdvised", "method", "example.WorkService", "classAdvised()",
           annotations=transactional, modifiers=["public"], return_type="void")
    symbol("async-work", "asyncWork", "method", "example.WorkService", "asyncWork()",
           annotations=asynchronous, modifiers=["public"], return_type="void")
    symbol("event-listener", "onEvent", "method", "example.WorkService", "onEvent(",
           annotations=listener, modifiers=["public"], return_type="void")
    symbol("reactive-work", "reactiveWork", "method", "example.WorkService", "reactiveWork()",
           modifiers=["public"], return_type="reactor.core.publisher.Mono<java.lang.String>")
    symbol("local", "local", "method", "example.WorkService", "void local()", return_type="void")
    symbol("caller", "Caller", "class", "example.Caller", "class Caller", annotations=service)
    symbol("api-field", "api", "field", "example.Caller", "WorkApi api", field_type="example.WorkApi")
    symbol("service-field", "service", "field", "example.Caller", "WorkService service", field_type="example.WorkService")
    symbol("call-interface", "callInterface", "method", "example.Caller", "callInterface()", modifiers=["public"])
    symbol("call-class", "callClass", "method", "example.Caller", "callClass()", modifiers=["public"])
    symbol("call-async", "callAsync", "method", "example.Caller", "callAsync()", modifiers=["public"])
    symbol("call-local", "callLocal", "method", "example.Caller", "callLocal()", modifiers=["public"])

    calls = [
        {"id": "site-interface", "caller": "call-interface", "declared_target": "api-advised",
         "dispatch_candidates": [], "dispatch_complete": False, "invocation_kind": "INTERFACE",
         "receiver_binding": "api-field", "receiver_binding_kind": "FIELD",
         "path": relative, "context_id": context["id"]},
        {"id": "site-class", "caller": "call-class", "declared_target": "class-advised",
         "dispatch_candidates": [], "dispatch_complete": True, "invocation_kind": "VIRTUAL",
         "receiver_binding": "service-field", "receiver_binding_kind": "FIELD",
         "path": relative, "context_id": context["id"]},
        {"id": "site-async", "caller": "call-async", "declared_target": "api-async",
         "dispatch_candidates": ["async-work"], "dispatch_complete": False, "invocation_kind": "INTERFACE",
         "receiver_binding": "api-field", "receiver_binding_kind": "FIELD",
         "path": relative, "context_id": context["id"]},
        {"id": "site-local", "caller": "call-local", "declared_target": "class-advised",
         "dispatch_candidates": [], "dispatch_complete": True, "invocation_kind": "VIRTUAL",
         "receiver_type": "example.WorkService", "path": relative, "context_id": context["id"]},
        {"id": "site-self-tx", "caller": "local", "declared_target": "class-advised",
         "dispatch_candidates": [], "dispatch_complete": True, "invocation_kind": "VIRTUAL",
         "path": relative, "context_id": context["id"]},
        {"id": "site-self-async", "caller": "local", "declared_target": "async-work",
         "dispatch_candidates": [], "dispatch_complete": True, "invocation_kind": "VIRTUAL",
         "path": relative, "context_id": context["id"]},
    ]
    for call in calls:
        call.update(evidence_kind="SYNTAX_CANDIDATE", evidence_ids=[],
                    resolution_reason="COMPILER_DECLARED_TARGET")
        nodes.append(Node(call["id"], "call_site", call["id"], relative,
                          line=_line(source, "local()") if "self" in call["id"] else _line(source, "public void call"),
                          scope="production", role="executable_code", origin="generated"))
    return KnowledgeGraph(3, str(tmp_path), "now", nodes, [], {relative: file_hash(path)},
                          [context], [], [], symbols, calls, [])


def test_jdk_proxy_async_event_and_self_invocation_are_bounded(tmp_path):
    source_graph = _graph(tmp_path)
    graph = augment_framework_graph(tmp_path, source_graph, source_graph.contexts[0])
    paths = [node for node in graph.nodes if node.kind == "spring_proxy_path"]
    assert {node.metadata["strategy"] for node in paths} == {"JDK_DYNAMIC"}
    assert any((node.metadata or {}).get("call_site") == "site-interface" for node in paths)
    assert any((node.metadata or {}).get("call_site") == "site-async" for node in paths)
    assert not any((node.metadata or {}).get("call_site") == "site-class" for node in paths)
    assert all(node.metadata["execution"] == "NOT_OBSERVED" and node.metadata["availability"] == "UNKNOWN"
               for node in paths)
    assert any(edge.kind == "may_apply_advice" for edge in graph.edges)
    assert any(edge.kind == "crosses_async_boundary" for edge in graph.edges)
    self_boundaries = [node for node in graph.nodes if node.kind == "spring_proxy_boundary"
                       and (node.metadata or {}).get("boundary_kind") == "SELF_INVOCATION"]
    assert len(self_boundaries) == 2
    assert all(node.metadata["continuation"] == "SYNCHRONOUS" for node in self_boundaries)
    assert any(node.kind == "spring_event_boundary" and node.metadata["execution"] == "NOT_OBSERVED"
               for node in graph.nodes)
    assert any(node.kind == "spring_reactive_boundary"
               and node.metadata["continuation"] == "SUBSCRIPTION_DEPENDENT" for node in graph.nodes)


def test_cglib_path_requires_interceptable_concrete_method(tmp_path):
    source_graph = _graph(tmp_path, cglib=True)
    graph = augment_framework_graph(tmp_path, source_graph, source_graph.contexts[0])
    paths = [node for node in graph.nodes if node.kind == "spring_proxy_path"]
    assert {node.metadata["strategy"] for node in paths} == {"CGLIB_SUBCLASS"}
    assert any((node.metadata or {}).get("call_site") == "site-class" for node in paths)
    assert any((node.metadata or {}).get("call_site") == "site-async" for node in paths)
    assert not any((node.metadata or {}).get("call_site") == "site-interface" for node in paths)
    assert any(item.get("code") == "SPRING_PROXY_METHOD_UNSUPPORTED" for item in graph.diagnostics)


def test_aspectj_declaration_without_weaving_proof_stays_unknown(tmp_path):
    source_graph = _graph(tmp_path)
    config = next(symbol for symbol in source_graph.symbols if symbol["id"] == "config")
    async_policy = next(annotation for annotation in config["annotations"]
                        if annotation["name"] == "org.springframework.scheduling.annotation.EnableAsync")
    async_policy["values"]["mode"] = "org.springframework.context.annotation.AdviceMode.ASPECTJ"
    graph = augment_framework_graph(tmp_path, source_graph, source_graph.contexts[0])
    policy = next(node for node in graph.nodes if node.kind == "spring_proxy_policy"
                  and node.metadata["policy_kind"] == "ASYNC")
    assert policy.metadata["strategy"] == "ASPECTJ_WEAVING"
    assert policy.metadata["activation_status"] == "UNKNOWN"
    assert not any(node.kind == "spring_proxy_path" and node.metadata["policy_kind"] == "ASYNC"
                   for node in graph.nodes)
    assert any(item.get("code") == "SPRING_WEAVING_UNVERIFIED" for item in graph.diagnostics)


def test_ambiguous_interface_injection_never_creates_stronger_proxy_evidence(tmp_path):
    source_graph = _graph(tmp_path, ambiguous=True)
    graph = augment_framework_graph(tmp_path, source_graph, source_graph.contexts[0])
    paths = [node for node in graph.nodes if node.kind == "spring_proxy_path"]
    assert not any(node.metadata["call_site"] in {"site-interface", "site-async"} for node in paths)
    assert any(edge.kind == "proxy_resolution_unknown" for edge in graph.edges)
    assert any(item.get("code") == "SPRING_PROXY_RECEIVER_UNRESOLVED" for item in graph.diagnostics)


def test_local_receiver_never_reuses_same_type_injected_field(tmp_path):
    source_graph = _graph(tmp_path, cglib=True)
    graph = augment_framework_graph(tmp_path, source_graph, source_graph.contexts[0])
    assert not any(node.kind == "spring_proxy_path"
                   and (node.metadata or {}).get("call_site") == "site-local"
                   for node in graph.nodes)
    assert any(item.get("code") == "SPRING_PROXY_RECEIVER_UNRESOLVED"
               and item.get("call_site") == "site-local" for item in graph.diagnostics)


def test_process_stops_at_async_boundary_without_claiming_execution():
    nodes = [Node(identity, "method" if identity != "site" else "call_site", identity, "A.java", line=1,
                  scope="production", role="executable_code", origin="handwritten")
             for identity in ("caller", "callee", "site")]
    nodes.extend([
        Node("proxy-path", "spring_proxy_path", "async proxy", "A.java", line=1,
             scope="production", role="framework", origin="generated", metadata={"policy_kind": "ASYNC"}),
        Node("async-boundary", "spring_async_boundary", "async boundary", "A.java", line=1,
             scope="production", role="framework", origin="generated")])
    graph = KnowledgeGraph(3, ".", "now", nodes,
        [Edge("site", "proxy-path", "may_traverse_proxy"),
         Edge("proxy-path", "async-boundary", "crosses_async_boundary")],
        {"A.java": "0"}, [], [], [],
        [{"id": "caller", "kind": "method", "owner": "example.Caller", "annotations": []},
         {"id": "callee", "kind": "method", "annotations": [
             {"name": "org.springframework.scheduling.annotation.Async", "values": {}}],
           "owner": "example.WorkService"}],
        [{"id": "site", "caller": "caller", "declared_target": "callee", "dispatch_candidates": [],
          "dispatch_complete": True, "invocation_kind": "VIRTUAL"}],
        [{"method": "caller", "representation": "SOURCE", "entry": "caller-entry", "exit": "caller-exit",
          "exceptional_exit": "caller-error", "blocks": [
              {"id": "caller-entry", "kind": "entry"}, {"id": "site", "kind": "call", "call_site_ids": ["site"]},
              {"id": "caller-exit", "kind": "exit"}, {"id": "caller-error", "kind": "exceptional_exit"}],
          "edges": [{"source": "caller-entry", "target": "site", "kind": "normal"},
                    {"source": "site", "target": "caller-exit", "kind": "normal"}]},
         {"method": "callee", "representation": "SOURCE", "entry": "callee-entry", "exit": "callee-exit",
          "exceptional_exit": "callee-error", "blocks": [
              {"id": "callee-entry", "kind": "entry"}, {"id": "callee-exit", "kind": "exit"},
              {"id": "callee-error", "kind": "exceptional_exit"}],
          "edges": [{"source": "callee-entry", "target": "callee-exit", "kind": "normal"}]}])
    report = process(graph, "caller", scope="production")
    boundary = next(block for block in report["cfg"]["blocks"] if block.get("boundary_reason") == "async boundary")
    assert boundary["boundary_kind"] == "SPRING_ASYNC"
    assert boundary["continuation"] == "SEPARATE"
    assert boundary["execution"] == "NOT_OBSERVED"
    assert report["status"] == "PARTIAL"


def test_process_expands_async_self_invocation_synchronously():
    nodes = [Node(identity, "method" if identity != "site" else "call_site", identity, "A.java", line=1,
                  scope="production", role="executable_code", origin="handwritten")
             for identity in ("caller", "callee", "site")]
    nodes.append(Node("self-boundary", "spring_proxy_boundary", "self invocation", "A.java", line=1,
                      scope="production", role="framework", origin="generated",
                      metadata={"boundary_kind": "SELF_INVOCATION"}))
    graph = KnowledgeGraph(3, ".", "now", nodes,
        [Edge("site", "self-boundary", "bypasses_proxy")], {"A.java": "0"}, [], [], [],
        [{"id": "caller", "kind": "method", "owner": "example.WorkService", "annotations": []},
         {"id": "callee", "kind": "method", "owner": "example.WorkService", "annotations": [
             {"name": "org.springframework.scheduling.annotation.Async", "values": {}}]}],
        [{"id": "site", "caller": "caller", "declared_target": "callee", "dispatch_candidates": [],
          "dispatch_complete": True, "invocation_kind": "VIRTUAL"}],
        [{"method": "caller", "representation": "SOURCE", "entry": "caller-entry", "exit": "caller-exit",
          "exceptional_exit": "caller-error", "blocks": [
              {"id": "caller-entry", "kind": "entry"}, {"id": "site", "kind": "call", "call_site_ids": ["site"]},
              {"id": "caller-exit", "kind": "exit"}, {"id": "caller-error", "kind": "exceptional_exit"}],
          "edges": [{"source": "caller-entry", "target": "site", "kind": "normal"},
                    {"source": "site", "target": "caller-exit", "kind": "normal"}]},
         {"method": "callee", "representation": "SOURCE", "entry": "callee-entry", "exit": "callee-exit",
          "exceptional_exit": "callee-error", "blocks": [
              {"id": "callee-entry", "kind": "entry"}, {"id": "callee-exit", "kind": "exit"},
              {"id": "callee-error", "kind": "exceptional_exit"}],
          "edges": [{"source": "callee-entry", "target": "callee-exit", "kind": "normal"}]}])
    report = process(graph, "caller", scope="production")
    call = next(block for block in report["cfg"]["blocks"] if "site" in block.get("original_ids", []))
    assert call["continuation"] == "SYNCHRONOUS"
    assert call["async_scheduled"] is False
    assert {block["method"] for block in report["cfg"]["blocks"]} == {"caller", "callee"}
    assert not any(block.get("boundary_kind") == "SPRING_ASYNC" for block in report["cfg"]["blocks"])


@pytest.mark.parametrize("proxy_target,expected", [(False, "JDK_DYNAMIC"), (True, "CGLIB_SUBCLASS")])
def test_actual_javac_proxy_async_event_fixture(tmp_path, proxy_target, expected):
    sources = {
        "org/springframework/stereotype/Service.java": """package org.springframework.stereotype;
import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
public @interface Service { String value() default ""; }""",
        "org/springframework/context/annotation/Configuration.java": """package org.springframework.context.annotation;
import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
public @interface Configuration {}""",
        "org/springframework/context/annotation/AdviceMode.java": """package org.springframework.context.annotation;
public enum AdviceMode { PROXY, ASPECTJ }""",
        "org/springframework/context/annotation/EnableAspectJAutoProxy.java": """package org.springframework.context.annotation;
import java.lang.annotation.*; @Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
public @interface EnableAspectJAutoProxy { boolean proxyTargetClass() default false; boolean exposeProxy() default false; }""",
        "org/springframework/scheduling/annotation/EnableAsync.java": """package org.springframework.scheduling.annotation;
import java.lang.annotation.*; import org.springframework.context.annotation.AdviceMode;
@Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
public @interface EnableAsync { boolean proxyTargetClass() default false; AdviceMode mode() default AdviceMode.PROXY; }""",
        "org/springframework/scheduling/annotation/Async.java": """package org.springframework.scheduling.annotation;
import java.lang.annotation.*; @Target({ElementType.TYPE,ElementType.METHOD}) @Retention(RetentionPolicy.RUNTIME)
public @interface Async { String value() default ""; }""",
        "org/springframework/context/event/EventListener.java": """package org.springframework.context.event;
import java.lang.annotation.*; @Target(ElementType.METHOD) @Retention(RetentionPolicy.RUNTIME)
public @interface EventListener {}""",
        "org/springframework/transaction/annotation/Transactional.java": """package org.springframework.transaction.annotation;
import java.lang.annotation.*; @Target({ElementType.TYPE,ElementType.METHOD}) @Retention(RetentionPolicy.RUNTIME)
public @interface Transactional {}""",
        "org/springframework/transaction/annotation/EnableTransactionManagement.java": """package org.springframework.transaction.annotation;
import java.lang.annotation.*; import org.springframework.context.annotation.AdviceMode;
@Target(ElementType.TYPE) @Retention(RetentionPolicy.RUNTIME)
public @interface EnableTransactionManagement { boolean proxyTargetClass() default false; AdviceMode mode() default AdviceMode.PROXY; }""",
        "example/Fixture.java": f"""package example;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.Async;
import org.springframework.context.event.EventListener;
import org.springframework.transaction.annotation.Transactional;
@Configuration @EnableAspectJAutoProxy(proxyTargetClass={str(proxy_target).lower()})
@EnableTransactionManagement(proxyTargetClass={str(proxy_target).lower()})
@EnableAsync(proxyTargetClass={str(proxy_target).lower()}) class Config {{}}
interface Api {{ @Transactional void tx(); @Async void async(); }}
@Service class Impl implements Api {{
  public void tx() {{}} public void async() {{}}
  @Transactional public void classTx() {{}}
  @Async public void classAsync() {{}}
  @EventListener public void event(String value) {{}}
  void local() {{ classTx(); classAsync(); }}
}}
@Service class Caller {{ Api api; Impl impl;
  void throughInterface() {{ api.tx(); api.async(); }}
  void throughClass() {{ impl.classTx(); impl.classAsync(); }}
}}
""",
    }
    for relative, text in sources.items():
        path = tmp_path / "src/main/java" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    try:
        result = inspect_jvm(tmp_path, classpath=[], publish=False,
                             build_context={"spring_profiles": [], "spring_properties": {},
                                            "spring_available_classes": [],
                                            "spring_component_packages": ["example"]})
    except WorkerError as error:
        if os.environ.get("KGMAKER_REQUIRE_WORKERS") == "1":
            pytest.fail(str(error))
        pytest.skip(str(error))
    graph = KnowledgeGraph.from_dict(result["graph"])
    paths = [node for node in graph.nodes if node.kind == "spring_proxy_path"
             and node.metadata["strategy"] == expected]
    assert paths
    assert {node.metadata["policy_kind"] for node in paths} == {"TRANSACTION", "ASYNC"}
    assert all(node.metadata["execution"] == "NOT_OBSERVED" for node in paths)
    assert len([node for node in graph.nodes if node.kind == "spring_proxy_boundary"
                and node.metadata.get("boundary_kind") == "SELF_INVOCATION"]) == 2
    assert any(node.kind == "spring_event_boundary" for node in graph.nodes)

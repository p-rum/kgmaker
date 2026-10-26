from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from kgmaker.analysis_model import file_hash, write_json
from kgmaker.architecture_model import ViewDocument
from kgmaker.model import KnowledgeGraph, Node
from kgmaker.scanner import scan_repository
from kgmaker.store import save_graph
from kgmaker.workspace import load_workspace, qualified, snapshot_workspace
from kgmaker.views import ServiceInventoryError, project_service_inventory


def inventory_inputs(tmp_path):
    for name in ("backend", "tests", "shared"):
        (tmp_path / name).mkdir()
    (tmp_path / "backend/src/main/kotlin").mkdir(parents=True)
    (tmp_path / "backend/src/main/kotlin/OrderService.kt").write_text("class OrderService\n", encoding="utf-8")
    (tmp_path / "tests/src/test/kotlin").mkdir(parents=True)
    (tmp_path / "tests/src/test/kotlin/OrderTest.kt").write_text("class OrderTest\n", encoding="utf-8")
    (tmp_path / "shared/src/main").mkdir(parents=True)
    (tmp_path / "shared/src/main/Util.kt").write_text("class Util\n", encoding="utf-8")
    manifest = tmp_path / "workspace.json"
    payload = {
        "schema_version": 1,
        "workspace_id": "retail",
        "repositories": [
            {"id": "backend", "role": "backend", "path": "backend"},
            {"id": "tests", "role": "automated-tests", "path": "tests"},
            {"id": "shared", "role": "shared", "path": "shared"},
        ],
        "services": [
            {"id": "orders", "backend_repo": "backend", "frontend_repos": [],
             "test_repos": [], "contract": {"repo_id": "backend", "path": "api.json"}},
            {"id": "fixture", "backend_repo": "tests", "frontend_repos": [],
             "test_repos": [], "contract": {"repo_id": "tests", "path": "api.json"}},
        ],
        "service_ownership": {"schema_version": 1, "services": [
            {"id": "orders", "roots": [{"repo_id": "backend", "path": "src/main/kotlin"}],
             "modules": [{"repo_id": "backend", "id": "orders-app"}],
             "external_systems": [{"id": "ledger"}]},
            {"id": "fixture", "roots": [{"repo_id": "tests", "path": "src/test/kotlin"}],
             "modules": [{"repo_id": "tests", "id": "fixture-app"}],
             "external_systems": []},
        ]},
    }
    write_json(manifest, payload)
    workspace = load_workspace(manifest)
    graph = KnowledgeGraph(
        3, ".", "", [], [], {"@workspace/manifest.json": workspace["_manifest_hash"]},
        [
            {"id": qualified("backend", "orders-prod"), "repo_id": "backend",
             "module": "orders-app", "scope": "production", "analyzer_version": "jvm-1",
             "freshness": "CURRENT", "mode": "SYMBOL_RESOLVED",
             "source_files": {"@backend/src/main/kotlin/OrderService.kt": file_hash(tmp_path / "backend/src/main/kotlin/OrderService.kt")},
             "classpath": []},
            {"id": qualified("tests", "fixture-tests"), "repo_id": "tests",
             "module": "fixture-app", "scope": "test", "analyzer_version": "jvm-1",
             "freshness": "CURRENT", "mode": "SYMBOL_RESOLVED",
             "source_files": {"@tests/src/test/kotlin/OrderTest.kt": file_hash(tmp_path / "tests/src/test/kotlin/OrderTest.kt")},
             "classpath": []},
            {"id": qualified("shared", "shared"), "repo_id": "shared",
             "module": "shared-lib", "scope": "production", "analyzer_version": "jvm-1",
             "freshness": "CURRENT", "mode": "SYMBOL_RESOLVED",
             "source_files": {"@shared/src/main/Util.kt": file_hash(tmp_path / "shared/src/main/Util.kt")},
             "classpath": []},
        ], [],
    )
    return manifest, workspace, graph


def node_map(document):
    return {node.id: node for node in document.nodes}


def test_ac01_inventory_includes_declared_production_service_not_fixture_or_random_beans(tmp_path, monkeypatch):
    _, workspace, graph = inventory_inputs(tmp_path)
    # A framework bean node is not a service declaration.
    graph.nodes.append(Node(id="random-service", kind="spring_component", name="RandomBean",
                            path="@backend/src/main/kotlin/OrderService.kt", scope="production",
                            role="executable_code", origin="handwritten"))
    before = graph.to_dict()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("service inventory must not run a subprocess")))

    result = project_service_inventory(workspace, graph, scope="production")
    nodes = node_map(result)

    assert result.kind == "topology"
    assert result.scope == "production"
    assert "service:orders" in nodes
    assert "service:fixture" not in nodes
    assert "service:shared-lib" not in nodes
    assert "service:random-service" not in nodes
    assert graph.to_dict() == before


def test_ac02_missing_external_checkout_keeps_declared_system_unknown_without_endpoints(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    result = project_service_inventory(workspace, graph, scope="production")
    nodes = node_map(result)

    external = nodes["external-system:ledger"]
    assert external.kind == "external_system"
    assert external.attributes["implementation_status"] == "UNKNOWN"
    assert external.attributes["endpoint_ids"] == []
    assert not any(node.kind in {"http_endpoint", "kafka_topic"} for node in result.nodes)
    assert any(edge.relation == "declares_external_system" for edge in result.edges)


def test_ac03_stable_service_identity_is_independent_of_display_label(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    original = project_service_inventory(workspace, graph, service_labels={"orders": "Orders"})
    renamed = project_service_inventory(workspace, graph, service_labels={"orders": "Order Processing"})
    original_node = node_map(original)["service:orders"]
    renamed_node = node_map(renamed)["service:orders"]

    assert original_node.id == renamed_node.id
    assert original_node.label == "Orders"
    assert renamed_node.label == "Order Processing"


def test_ac04_invalid_snapshot_fails_without_mutating_workspace_or_graph(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    manifest_before = Path(workspace["_manifest_path"]).read_bytes()
    source_before = (tmp_path / "backend/src/main/kotlin/OrderService.kt").read_bytes()
    graph.files["@workspace/manifest.json"] = "0" * 64
    before_workspace = deepcopy(workspace)
    before_graph = graph.to_dict()

    with pytest.raises(ServiceInventoryError, match="manifest"):
        project_service_inventory(workspace, graph, scope="production")

    assert workspace == before_workspace
    assert graph.to_dict() == before_graph
    assert Path(workspace["_manifest_path"]).read_bytes() == manifest_before
    assert (tmp_path / "backend/src/main/kotlin/OrderService.kt").read_bytes() == source_before


def test_workspace_alias_requalifies_default_local_compiler_context(tmp_path, monkeypatch):
    backend = tmp_path / "backend"
    (backend / "src/main/java").mkdir(parents=True)
    (backend / "src/main/java/OrderService.java").write_text("class OrderService {}\n", encoding="utf-8")
    local_graph = scan_repository(backend)
    local_graph.schema_version = 3
    from kgmaker.inspection import source_snapshot
    context = {"id": "orders-context", "repo_id": "local", "module": "orders-app",
               "source_set": "main", "scope": "production", "mode": "BUILD_IMPORT",
               "freshness": "CONTENT_VERIFIED", "coverage": "PARTIAL",
               "analyzer_version": "fixture-jvm-1"}
    context["source_files"] = source_snapshot(backend, local_graph, context)
    local_graph.contexts.append(context)
    local_graph.nodes.append(Node(id="compiler:OrderService", kind="method", name="OrderService",
                                  path="src/main/java/OrderService.java", scope="production",
                                  role="executable_code", origin="handwritten"))
    local_graph.nodes.append(Node(id="compiler:LedgerClient", kind="method", name="LedgerClient",
                                  path="external/ledger.jar", scope="production",
                                  role="executable_code", origin="dependency"))
    local_graph.symbols.extend([
        {"id": "compiler:OrderService", "name": "OrderService", "kind": "method",
         "context_id": "orders-context", "path": "src/main/java/OrderService.java",
         "range": {"start_line": 1}},
        {"id": "compiler:LedgerClient", "name": "LedgerClient", "kind": "method",
         "context_id": "orders-context", "path": "external/ledger.jar",
         "range": {"start_line": 1}},
    ])
    save_graph(local_graph, backend, generate_docs=False)
    manifest = tmp_path / "workspace.json"
    write_json(manifest, {
        "schema_version": 1, "workspace_id": "retail", "repositories": [
            {"id": "backend", "role": "backend", "path": "backend"}],
        "services": [{"id": "orders", "backend_repo": "backend", "frontend_repos": [],
                      "test_repos": [], "contract": {"repo_id": "backend", "path": "api.json"}}],
        "service_ownership": {"schema_version": 1, "services": [
            {"id": "orders", "roots": [{"repo_id": "backend", "path": "src/main/java"}],
             "modules": [{"repo_id": "backend", "id": "orders-app"}], "external_systems": []}]},
    })
    workspace = load_workspace(manifest)
    _, _, _, graph, _ = snapshot_workspace(manifest)

    compiler_context = next(item for item in graph.contexts if item.get("analyzer_version")
                            and item.get("module") == "orders-app")
    assert compiler_context["repo_id"] == "backend"
    assert compiler_context["id"] == qualified("backend", "orders-context")
    service_symbol = next(item for item in graph.symbols if item["id"] == qualified("backend", "compiler:OrderService"))
    assert service_symbol["context_id"] == compiler_context["id"]
    assert "repo_id" not in service_symbol and "module" not in service_symbol
    from kgmaker import workspace as workspace_module
    original_resolver = workspace_module.resolve_service_ownership
    enriched_symbols = []
    def recording_resolver(symbol, declaration, *, context_id):
        if symbol.get("id") == qualified("backend", "compiler:OrderService"):
            enriched_symbols.append(dict(symbol))
        return original_resolver(symbol, declaration, context_id=context_id)
    monkeypatch.setattr(workspace_module, "resolve_service_ownership", recording_resolver)
    result = project_service_inventory(workspace, graph, scope="production")
    assert result.context_selection["services"]["orders"]["contexts"][0]["context_id"] == qualified("backend", "orders-context")
    assert enriched_symbols
    assert enriched_symbols[0]["repo_id"] == "backend"
    assert enriched_symbols[0]["module"] == "orders-app"
    assert all(node.id != qualified("backend", "compiler:LedgerClient") for node in result.nodes)


def test_ac05_context_and_provenance_are_preserved_and_not_upgraded(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    graph.diagnostics.append({"code": "TRUNCATED_PROVIDER_CONTEXT", "reason": "fixture boundary"})
    selected_context = graph.contexts[0]["id"]
    result = project_service_inventory(workspace, graph, scope="production")
    service = node_map(result)["service:orders"]

    assert result.context_selection["services"]["orders"]["contexts"][0]["context_id"] == selected_context
    assert result.context_selection["services"]["orders"]["contexts"][0]["scope"] == "production"
    assert service.attributes["scope"] == "production"
    assert service.attributes["evidence_kinds"] == ["SYMBOL_RESOLVED"]
    assert result.coverage["status"] == "PARTIAL"
    assert any(item.get("evidence_kind") == "SOURCE_ONLY" for item in result.provenance)
    assert any(item["code"] == "TRUNCATED_PROVIDER_CONTEXT" for item in result.diagnostics)


def test_ambiguous_compiler_variants_remain_unknown_until_explicitly_selected(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    graph.contexts.append({**deepcopy(graph.contexts[0]), "id": qualified("backend", "orders-prod-2")})

    ambiguous = project_service_inventory(workspace, graph, scope="production")
    service = node_map(ambiguous)["service:orders"]
    assert service.attributes["context_status"] == "AMBIGUOUS"
    assert any(d["code"] == "AMBIGUOUS_CONTEXT" for d in ambiguous.diagnostics)
    selected = project_service_inventory(
        workspace, graph, scope="production",
        selected_contexts={("orders", "backend", "orders-app"): qualified("backend", "orders-prod")})
    assert node_map(selected)["service:orders"].attributes["context_status"] == "CURRENT"


def test_source_only_context_remains_partial_and_reports_unknown_module_coverage(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    context = graph.contexts[0]
    graph.contexts = [{**context, "mode": "SOURCE_ONLY", "analyzer_version": None,
                       "freshness": "UNKNOWN", "coverage": "PARTIAL"}]
    coverage = {"roots": ["backend"],
                "artifacts": ["@backend/src/main/kotlin/OrderService.kt"]}

    result = project_service_inventory(workspace, graph, scope="production", source_coverage=coverage)
    service = node_map(result)["service:orders"]
    row = result.context_selection["services"]["orders"]["contexts"][0]

    assert service.attributes["context_status"] == "PARTIAL"
    assert row["context_id"] is None
    assert row["module_coverage"] == "UNKNOWN"
    assert service.attributes["evidence_kinds"] == ["SOURCE_ONLY"]
    assert result.coverage["status"] == "PARTIAL"


def test_unknown_scope_does_not_enter_production_inventory(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    graph.contexts = [{**graph.contexts[0], "scope": "unknown", "id": qualified("backend", "orders-unknown")}]

    result = project_service_inventory(workspace, graph, scope="production")

    assert "service:orders" not in node_map(result)
    assert result.coverage["status"] == "UNKNOWN"
    assert any(item["code"] == "SERVICE_CONTEXT_UNAVAILABLE" for item in result.diagnostics)


def test_t008_view_round_trips_through_t005_validator(tmp_path):
    _, workspace, graph = inventory_inputs(tmp_path)
    result = project_service_inventory(workspace, graph, scope="production")
    decoded = ViewDocument.from_dict(json.loads(result.to_json()))
    assert decoded.content_fingerprint == result.content_fingerprint


def test_actual_workspace_source_only_snapshot_projects_declared_root_without_module(tmp_path):
    manifest, workspace, _ = inventory_inputs(tmp_path)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    before_graph = graph.to_dict()
    manifest_bytes = manifest.read_bytes()
    source_bytes = (tmp_path / "backend/src/main/kotlin/OrderService.kt").read_bytes()

    result = project_service_inventory(workspace, graph, scope="production", source_coverage=coverage)
    nodes = node_map(result)
    service = nodes["service:orders"]

    assert service.attributes["context_status"] == "PARTIAL"
    assert service.attributes["modules"] == []
    assert service.attributes["repo_ids"] == ["backend"]
    assert service.attributes["evidence_kinds"] == ["SOURCE_ONLY"]
    assert "service:fixture" not in nodes
    assert "service:shared-lib" not in nodes
    assert nodes["external-system:ledger"].attributes["implementation_status"] == "UNKNOWN"
    assert nodes["external-system:ledger"].attributes["endpoint_ids"] == []
    assert result.coverage["status"] == "PARTIAL"
    assert result.context_selection["services"]["orders"]["contexts"][0]["module_coverage"] == "UNKNOWN"
    assert any(item["id"].startswith("ev:source-context:") for item in result.provenance)
    assert graph.to_dict() == before_graph
    assert manifest.read_bytes() == manifest_bytes
    assert (tmp_path / "backend/src/main/kotlin/OrderService.kt").read_bytes() == source_bytes


def test_actual_source_only_snapshot_separates_production_and_test_within_repo(tmp_path):
    manifest, _, _ = inventory_inputs(tmp_path)
    test_source = tmp_path / "backend/src/test/kotlin/OrderTest.kt"
    test_source.parent.mkdir(parents=True)
    test_source.write_text("class OrderTest\n", encoding="utf-8")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["repositories"] = [{"id": "backend", "role": "backend", "path": "backend"}]
    data["services"][1]["backend_repo"] = "backend"
    data["services"][1]["contract"]["repo_id"] = "backend"
    data["service_ownership"]["services"][1]["roots"] = [
        {"repo_id": "backend", "path": "src/test/kotlin"}]
    data["service_ownership"]["services"][1]["modules"] = [
        {"repo_id": "backend", "id": "fixture-app"}]
    write_json(manifest, data)
    workspace = load_workspace(manifest)
    _, coverage, _, graph, _ = snapshot_workspace(manifest)
    original_graph = graph.to_dict()
    original_manifest = manifest.read_bytes()
    original_sources = {
        path: (tmp_path / "backend" / path.removeprefix("@backend/")).read_bytes()
        for path in coverage["artifacts"]
    }

    production = project_service_inventory(workspace, graph, scope="production", source_coverage=coverage)
    production_nodes = node_map(production)
    assert "service:orders" in production_nodes
    assert "service:fixture" not in production_nodes
    assert production_nodes["service:orders"].attributes["context_status"] == "PARTIAL"
    assert production_nodes["service:orders"].attributes["modules"] == []
    assert production_nodes["external-system:ledger"].attributes["implementation_status"] == "UNKNOWN"
    assert production_nodes["external-system:ledger"].attributes["endpoint_ids"] == []

    test_view = project_service_inventory(workspace, graph, scope="test", source_coverage=coverage)
    assert "service:fixture" in node_map(test_view)
    assert "service:orders" not in node_map(test_view)
    assert node_map(test_view)["service:fixture"].attributes["context_status"] == "PARTIAL"
    assert graph.to_dict() == original_graph
    assert manifest.read_bytes() == original_manifest
    assert all((tmp_path / "backend" / path.removeprefix("@backend/")).read_bytes() == content
               for path, content in original_sources.items())

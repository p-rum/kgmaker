"""Public selection contract for T006; fixtures model separate repo contexts."""

from copy import deepcopy
from pathlib import Path
import pytest

from kgmaker.model import KnowledgeGraph
from kgmaker.views import ContextSelectionError, select_service_contexts


def graph_with_contexts():
    contexts = [
        {"id": "repo:billing:billing-dev", "repo_id": "billing", "module": "app",
         "scope": "production", "spring_profiles": ["dev"], "analyzer_version": "jvm-1",
         "freshness": "CURRENT", "source_files": {"src/A.java": "a"}, "classpath": []},
        {"id": "repo:billing:billing-prod", "repo_id": "billing", "module": "app",
         "scope": "production", "spring_profiles": ["prod"], "analyzer_version": "jvm-1",
         "freshness": "CURRENT", "source_files": {"src/A.java": "b"}, "classpath": []},
        {"id": "repo:ledger:ledger-test", "repo_id": "ledger", "module": "service",
         "scope": "production", "build_profiles": ["test-env"], "analyzer_version": "jvm-1",
         "freshness": "CURRENT", "source_files": {"src/B.java": "c"}, "classpath": []},
    ]
    return KnowledgeGraph(3, ".", "", [], [], {}, contexts, [])


def test_two_services_select_distinct_contexts_and_profiles_without_mixing():
    graph = graph_with_contexts()
    selection = select_service_contexts(graph, [
        {"service_id": "billing-api", "repo_id": "billing", "module": "app",
         "context_id": "repo:billing:billing-prod"},
        {"service_id": "ledger-api", "repo_id": "ledger", "module": "service",
         "context_id": "repo:ledger:ledger-test"},
    ], scope="production")

    services = {item["service_id"]: item for item in selection["services"]}
    assert services["billing-api"]["context_id"] == "repo:billing:billing-prod"
    assert services["billing-api"]["profile"] == ["prod"]
    assert services["ledger-api"]["context_id"] == "repo:ledger:ledger-test"
    assert services["ledger-api"]["profile"] == ["test-env"]
    assert services["billing-api"]["context_fingerprint"] != services["ledger-api"]["context_fingerprint"]
    assert selection["context_selection"]["billing-api"]["context_id"] == "repo:billing:billing-prod"
    assert selection["context_selection"]["billing-api"]["context_fingerprint"] == services["billing-api"]["context_fingerprint"]
    assert selection["deployment_compatibility"] == "UNKNOWN"


def test_missing_variant_selection_returns_choices_and_does_not_mutate_graph():
    graph = graph_with_contexts()
    before = deepcopy(graph.to_dict())
    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, [{"service_id": "billing-api", "repo_id": "billing",
                                        "module": "app"}], scope="production")
    assert caught.value.diagnostic["code"] == "AMBIGUOUS_CONTEXT"
    assert caught.value.diagnostic["choices"] == ["repo:billing:billing-dev", "repo:billing:billing-prod"]
    assert graph.to_dict() == before


def test_stale_classpath_returns_diagnostic_and_next_command_without_worker(tmp_path: Path):
    graph = graph_with_contexts()
    context = graph.contexts[-1]
    context["source_files"] = {}
    artifact = tmp_path / "dep.jar"
    artifact.write_bytes(b"changed dependency bytes")
    context["classpath"] = [{"path": str(artifact), "sha256": "0" * 64}]
    context["next_command"] = "kgmaker inspect code --repo-id ledger --module service"
    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, [{"service_id": "ledger-api", "repo_id": "ledger",
                                        "module": "service", "context_id": context["id"]}],
                               scope="production", repo_roots={"ledger": tmp_path})
    assert caught.value.diagnostic["code"] == "STALE_CONTEXT"
    assert "classpath changed" in caught.value.diagnostic["message"]
    assert caught.value.diagnostic["next_command"].startswith("kgmaker inspect code")


def test_selection_reads_current_context_without_process_or_store_mutation(tmp_path: Path, monkeypatch):
    graph = graph_with_contexts()
    context = graph.contexts[-1]
    context["source_files"] = {}
    before = deepcopy(graph.to_dict())
    persisted = tmp_path / ".kgmaker" / "graph.json"
    persisted.parent.mkdir()
    persisted.write_text('{"last_valid":true}\n', encoding="utf-8")
    persisted_before = persisted.read_bytes()

    def forbidden_process(*args, **kwargs):
        raise AssertionError("context selection attempted a process")

    monkeypatch.setattr("subprocess.run", forbidden_process)
    monkeypatch.setattr("kgmaker.store.save_graph", forbidden_process)
    result = select_service_contexts(graph, [{"service_id": "ledger-api", "repo_id": "ledger",
                                             "module": "service", "context_id": context["id"]}],
                                    scope="production", repo_roots={"ledger": tmp_path})
    assert result["services"][0]["context_id"] == context["id"]
    assert graph.to_dict() == before
    assert persisted.read_bytes() == persisted_before


def test_source_only_requires_declared_repo_coverage_and_stays_partial():
    graph = KnowledgeGraph(3, ".", "", [], [], {}, [], [])
    request = [{"service_id": "catalog", "repo_id": "catalog", "module": "app", "mode": "SOURCE_ONLY"}]
    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, request, scope="production")
    assert caught.value.diagnostic["code"] == "SOURCE_COVERAGE_UNAVAILABLE"

    result = select_service_contexts(graph, request, scope="production",
                                     source_coverage={"roots": ["catalog"],
                                                      "artifacts": ["@catalog/src/Catalog.java"]})
    assert result["services"][0]["status"] == "PARTIAL"
    assert result["services"][0]["evidence_kind"] == "SOURCE_ONLY"
    assert result["services"][0]["context_id"] is None
    assert result["deployment_compatibility"] == "UNKNOWN"


def test_content_verified_release_mapping_does_not_claim_deployment_compatibility():
    graph = graph_with_contexts()
    mapping = {"id": "billing-to-ledger",
               "producer": {"repo_id": "billing", "manifest_path": "build.json",
                            "context_id": "billing-prod"},
               "consumer": {"repo_id": "ledger", "context_id": "ledger-test"},
               "output_sha256": "a" * 64}
    result = select_service_contexts(graph, [
        {"service_id": "billing-api", "repo_id": "billing", "module": "app", "context_id": "repo:billing:billing-prod"},
        {"service_id": "ledger-api", "repo_id": "ledger", "module": "service", "context_id": "repo:ledger:ledger-test"},
    ], scope="production", release_mapping={
        "declaration": {"schema_version": 1, "mappings": [mapping]},
        "report": {"schema_version": 1,
                   "mappings": [{"id": "billing-to-ledger", "status": "CONTENT_VERIFIED"}]},
    })
    assert result["release_compatibility"] == []
    assert any(item["code"] == "RELEASE_MAPPING_REPORT_MISMATCH"
               for item in result["diagnostics"])
    assert result["deployment_compatibility"] == "UNKNOWN"


def test_context_without_repo_identity_is_never_bound_to_requested_repo():
    graph = graph_with_contexts()
    legacy = {"id": "legacy-context", "module": "app", "scope": "production",
              "analyzer_version": "jvm-1", "freshness": "CURRENT", "source_files": {},
              "classpath": []}
    graph.contexts = [legacy]
    before = deepcopy(graph.to_dict())

    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, [
            {"service_id": "one", "repo_id": "repo-one", "module": "app"},
            {"service_id": "two", "repo_id": "repo-two", "module": "app"},
        ], scope="production")
    assert caught.value.diagnostic["code"] == "CONTEXT_UNAVAILABLE"
    assert graph.to_dict() == before


def test_invalid_scope_and_module_mismatch_fail_closed_without_input_mutation():
    graph = graph_with_contexts()
    before = deepcopy(graph.to_dict())
    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, [{"service_id": "billing-api", "repo_id": "billing",
                                        "module": "other", "context_id": "repo:billing:billing-prod"}],
                               scope="production")
    assert caught.value.diagnostic["code"] == "CONTEXT_UNAVAILABLE"
    assert graph.to_dict() == before

    with pytest.raises(ContextSelectionError) as caught:
        select_service_contexts(graph, [{"service_id": "billing-api", "repo_id": "billing",
                                        "module": "app", "context_id": "repo:billing:billing-prod"}],
                               scope="all")
    assert caught.value.diagnostic["code"] == "INVALID_SCOPE"

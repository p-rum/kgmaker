"""Public acceptance tests for the T005 view document contract."""

from copy import deepcopy
import json

import pytest

from kgmaker.architecture_model import ViewDocument, ViewValidationError, validate_view_document
from kgmaker.model import KnowledgeGraph


def sample_view():
    return {
        "schema_version": 1,
        "view_id": "interfaces:billing:v1",
        "kind": "interfaces",
        "baseline_fingerprint": "sha256:source-snapshot",
        "rules_version": "t005-v1",
        "scope": "production",
        "context_selection": {"billing-service": ["ctx-jvm-a"]},
        "nodes": [
            {"id": "interface:billing:get-invoice", "kind": "http_endpoint", "label": "GET /invoices",
             "original_ids": ["symbol:InvoiceController.get"], "owner_id": "service:billing",
             "evidence_refs": ["ev:route"], "attributes": {"scope": "production"}},
            {"id": "service:billing", "kind": "service", "label": "Billing",
             "original_ids": [], "owner_id": None, "evidence_refs": [], "attributes": {}},
        ],
        "edges": [{"id": "edge:owns", "source": "service:billing", "target": "interface:billing:get-invoice",
                   "relation": "owns", "original_ids": ["symbol:InvoiceController.get"],
                   "evidence_refs": ["ev:route"], "resolution_status": "RESOLVED", "attributes": {}}],
        "diagnostics": [],
        "coverage": {"status": "PARTIAL", "reasons": ["external binding unresolved"]},
        "limits": ["No runtime observation"],
        "provenance": [{"id": "ev:route", "evidence_kind": "FRAMEWORK_DERIVED",
                        "source_id": "symbol:InvoiceController.get", "content_hash": "sha256:abc"}],
    }


def test_round_trip_valid_model_preserves_public_contract():
    source = sample_view()
    decoded = ViewDocument.from_dict(source)
    serialized = json.loads(decoded.to_json())
    assert serialized["view_id"] == source["view_id"]
    assert serialized["nodes"] == sorted(source["nodes"], key=lambda n: n["id"])
    assert serialized["edges"][0]["evidence_refs"] == ["ev:route"]
    assert serialized["provenance"] == source["provenance"]
    assert serialized["coverage"] == source["coverage"]


def test_duplicate_node_id_has_structured_validation_error():
    data = sample_view()
    data["nodes"].append(deepcopy(data["nodes"][0]))
    before = deepcopy(data)
    with pytest.raises(ViewValidationError) as caught:
        validate_view_document(data)
    assert any(error["code"] == "DUPLICATE_NODE_ID" for error in caught.value.errors)
    assert data == before


def test_unknown_version_and_dangling_endpoint_or_evidence_are_rejected():
    for mutate, expected in (
        (lambda d: d.update(schema_version=99), "UNSUPPORTED_SCHEMA_VERSION"),
        (lambda d: d["edges"][0].update(target="missing"), "DANGLING_EDGE_ENDPOINT"),
        (lambda d: d["nodes"][0].update(evidence_refs=["ev:missing"]), "INVALID_EVIDENCE_REFERENCE"),
    ):
        data = sample_view()
        mutate(data)
        with pytest.raises(ViewValidationError) as caught:
            ViewDocument.from_dict(data)
        assert expected in {error["code"] for error in caught.value.errors}


def test_permuted_inputs_have_byte_identical_canonical_json():
    data = sample_view()
    reversed_data = deepcopy(data)
    reversed_data["nodes"].reverse()
    reversed_data["edges"].reverse()
    reversed_data["provenance"].reverse()
    first = ViewDocument.from_dict(data).to_json()
    second = ViewDocument.from_dict(reversed_data).to_json()
    assert first.encode() == second.encode()


def test_generation_metadata_is_outside_content_fingerprint():
    first = ViewDocument.from_dict(sample_view())
    second_data = sample_view()
    second_data["generation_metadata"] = {"generated_at": "2026-10-20T00:00:00Z"}
    second = ViewDocument.from_dict(second_data)
    assert first.content_fingerprint == second.content_fingerprint


def test_unknown_generation_metadata_is_rejected_without_silent_data_loss():
    data = sample_view()
    data["generation_metadata"] = {"generated_at": "2026-10-26T00:00:00Z", "build": "abc"}
    before = deepcopy(data)
    with pytest.raises(ViewValidationError) as caught:
        ViewDocument.from_dict(data)
    assert {"code": "UNKNOWN_FIELD", "path": "generation_metadata.build"} in caught.value.errors
    assert data == before


def test_scope_context_and_evidence_kind_are_preserved_without_upgrade():
    data = sample_view()
    data["nodes"][0]["attributes"]["scope"] = "test"
    data["scope"] = "test"
    data["context_selection"] = {"billing-service": ["ctx-test"]}
    document = ViewDocument.from_dict(data)
    result = json.loads(document.to_json())
    assert result["context_selection"] == {"billing-service": ["ctx-test"]}
    assert result["scope"] == "test"
    assert result["nodes"][0]["attributes"]["scope"] == "test"
    assert result["provenance"][0]["evidence_kind"] == "FRAMEWORK_DERIVED"


def test_complete_coverage_cannot_hide_unresolved_edges():
    data = sample_view()
    data["coverage"]["status"] = "COMPLETE_WITHIN_SELECTED_SCOPE"
    data["edges"][0]["resolution_status"] = "UNRESOLVED"
    with pytest.raises(ViewValidationError) as caught:
        validate_view_document(data)
    assert "UNRESOLVED_EDGE_WITH_COMPLETE_COVERAGE" in {e["code"] for e in caught.value.errors}


@pytest.mark.parametrize("path,value,code", [
    (("kind",), [], "INVALID_KIND"),
    (("coverage", "status"), {}, "INVALID_COVERAGE_STATUS"),
    (("edges", 0, "resolution_status"), [], "INVALID_RESOLUTION_STATUS"),
    (("nodes", 0, "attributes", "weight"), float("nan"), "NON_JSON_VALUE"),
    (("nodes", 0, "attributes"), 7, "INVALID_ATTRIBUTES"),
    (("nodes", 0, "original_ids"), 7, "INVALID_STRING_ARRAY"),
    (("diagnostics",), [7], "INVALID_DIAGNOSTIC"),
    (("limits",), [7], "INVALID_LIMIT"),
    (("generation_metadata",), 7, "INVALID_GENERATION_METADATA"),
])
def test_malformed_unhashable_or_non_json_values_return_structured_errors(path, value, code):
    data = sample_view()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ViewValidationError) as caught:
        validate_view_document(data)
    assert code in {e["code"] for e in caught.value.errors}


def test_from_dict_rejects_malformed_nested_fields_as_validation_errors():
    for path, value, code in (
        (("nodes", 0, "attributes"), 7, "INVALID_ATTRIBUTES"),
        (("diagnostics",), [7], "INVALID_DIAGNOSTIC"),
        (("generation_metadata",), 7, "INVALID_GENERATION_METADATA"),
    ):
        data = sample_view()
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(ViewValidationError) as caught:
            ViewDocument.from_dict(data)
        assert code in {e["code"] for e in caught.value.errors}


@pytest.mark.parametrize("version", [1, 2, 3])
def test_existing_graph_loader_still_accepts_legacy_schema_versions(version):
    graph_data = {"schema_version": version, "root": ".", "generated_at": "",
                  "nodes": [], "edges": [], "files": {}}
    graph = KnowledgeGraph.from_dict(graph_data)
    assert graph.schema_version == version

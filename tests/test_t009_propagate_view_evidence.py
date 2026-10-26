"""Public bounded contract for evidence aggregation in T009 views."""
from copy import deepcopy

import pytest

from kgmaker.architecture_model import (
    ViewDocument, ViewEdge, ViewValidationError, aggregate_view_edges,
)


def claim(edge_id, *, kind, status, freshness, refs, polarity_refs=(), polarity="supporting", scope="production",
          context="ctx-prod"):
    return ViewEdge(
        id=edge_id, source="service:orders", target="database:orders", relation="depends_on",
        original_ids=(edge_id,), evidence_refs=tuple(refs), resolution_status=status,
        attributes={"scope": scope, "context_ids": [context]}, evidence_kinds=(kind,), freshness=freshness,
        supporting_refs=tuple(refs) if polarity == "supporting" else (),
        contradicting_refs=tuple(refs) if polarity == "contradicting" else (),
        unknown_refs=tuple(refs) if polarity == "unknown" else (),
    )


def test_ac01_syntax_candidate_stays_syntax_candidate_and_legacy_defaults_do_not_upgrade():
    edge = ViewEdge("candidate", "a", "b", "calls", evidence_refs=("ev:syntax",),
                    resolution_status="UNRESOLVED", attributes={"scope": "production",
                    "context_ids": ["ctx-prod"]}, evidence_kinds=("SYNTAX_CANDIDATE",),
                    freshness="CURRENT", unknown_refs=("ev:syntax",))
    provenance = [{"id": "ev:syntax", "evidence_kind": "SYNTAX_CANDIDATE",
                   "freshness": "CURRENT", "polarity": "UNKNOWN"}]
    result = aggregate_view_edges([edge], provenance, scope="production", context_ids=["ctx-prod"])
    projected = result["edges"][0]
    assert projected.evidence_kinds == ("SYNTAX_CANDIDATE",)
    assert projected.resolution_status == "UNRESOLVED"
    assert projected.freshness == "CURRENT"
    assert projected.unknown_refs == ("ev:syntax",)
    assert "RUNTIME_OBSERVED" not in projected.evidence_kinds

    legacy = {
        "schema_version": 1, "view_id": "legacy", "kind": "topology",
        "baseline_fingerprint": "sha256:old", "rules_version": "old", "scope": "production",
        "context_selection": {}, "nodes": [{"id": "a", "kind": "service", "label": "A",
            "evidence_refs": ["ev:old"], "original_ids": [], "owner_id": None, "attributes": {}}],
        "edges": [], "diagnostics": [], "coverage": {"status": "UNKNOWN"}, "limits": [],
        "provenance": [{"id": "ev:old", "evidence_kind": "SYNTAX_CANDIDATE"}],
    }
    decoded = ViewDocument.from_dict(legacy).to_dict()
    node = decoded["nodes"][0]
    assert node["resolution_status"] == "UNRESOLVED"
    assert node["freshness"] == "UNKNOWN"
    assert node["unknown_refs"] == ["ev:old"]
    assert decoded["provenance"][0]["freshness"] == "UNKNOWN"
    assert decoded["provenance"][0]["polarity"] == "UNKNOWN"


def test_ac02_mixed_evidence_retains_support_conflict_unknown_refs_and_diagnostics():
    edges = [
        claim("resolved", kind="SYMBOL_RESOLVED", status="RESOLVED", freshness="CURRENT",
              refs=("ev:support",)),
        claim("candidate", kind="SYNTAX_CANDIDATE", status="UNRESOLVED", freshness="UNKNOWN",
              refs=("ev:unclassified",), polarity="unknown"),
        claim("counter", kind="FRAMEWORK_DERIVED", status="RESOLVED", freshness="CURRENT",
              refs=("ev:counter",), polarity="contradicting"),
    ]
    provenance = [
        {"id": "ev:support", "evidence_kind": "SYMBOL_RESOLVED", "freshness": "CURRENT",
         "polarity": "SUPPORTING"},
        {"id": "ev:unclassified", "evidence_kind": "SYNTAX_CANDIDATE", "freshness": "UNKNOWN"},
        {"id": "ev:counter", "evidence_kind": "FRAMEWORK_DERIVED", "freshness": "CURRENT",
         "polarity": "CONTRADICTING"},
    ]
    existing_diagnostic = {"code": "TRUNCATED_PROVIDER_CONTEXT", "context_id": "ctx-prod"}
    result = aggregate_view_edges(edges, provenance, scope="production", context_ids=["ctx-prod"],
                                  diagnostics=[existing_diagnostic])
    aggregate = result["edges"][0]

    assert aggregate.resolution_status == "AMBIGUOUS"
    assert aggregate.evidence_kinds == ("FRAMEWORK_DERIVED", "SYMBOL_RESOLVED", "SYNTAX_CANDIDATE")
    assert aggregate.supporting_refs == ("ev:support",)
    assert aggregate.contradicting_refs == ("ev:counter",)
    assert aggregate.unknown_refs == ("ev:unclassified",)
    assert set(aggregate.evidence_refs) == {"ev:support", "ev:counter", "ev:unclassified"}
    assert aggregate.freshness == "UNKNOWN"
    assert {item["code"] for item in result["diagnostics"]} >= {
        "TRUNCATED_PROVIDER_CONTEXT", "CONTRADICTORY_VIEW_EVIDENCE", "VIEW_EVIDENCE_POLARITY_UNKNOWN"}
    assert result["coverage"] == {"status": "PARTIAL",
                                  "counts": {"found": 1, "resolved": 0, "unresolved": 1, "excluded": 0}}


def test_ac03_empty_unanalyzed_input_is_unknown_with_zero_counts():
    result = aggregate_view_edges([], [], scope="production")
    assert result["coverage"] == {"status": "UNKNOWN",
                                  "counts": {"found": 0, "resolved": 0, "unresolved": 0, "excluded": 0}}
    assert result["edges"] == ()


def test_unknown_claim_freshness_is_not_upgraded_by_current_source_reference():
    edge = ViewEdge("edge", "a", "b", "calls", evidence_refs=("ev:current",),
                    resolution_status="RESOLVED", attributes={"scope": "production",
                    "context_ids": ["ctx-prod"]}, unknown_refs=("ev:current",))
    result = aggregate_view_edges(
        [edge], [{"id": "ev:current", "evidence_kind": "SYMBOL_RESOLVED",
                  "freshness": "CURRENT", "polarity": "UNKNOWN"}],
        scope="production", context_ids=["ctx-prod"],
    )
    assert result["edges"][0].freshness == "UNKNOWN"
    assert result["coverage"]["status"] == "PARTIAL"


def test_claim_without_context_identity_is_kept_separate_and_diagnostic():
    result = aggregate_view_edges(
        [ViewEdge("edge", "a", "b", "calls", evidence_refs=("ev:source",),
                  resolution_status="RESOLVED", attributes={"scope": "production"},
                  evidence_kinds=("SYMBOL_RESOLVED",), freshness="CURRENT",
                  supporting_refs=("ev:source",))],
        [{"id": "ev:source", "evidence_kind": "SYMBOL_RESOLVED",
          "freshness": "CURRENT", "polarity": "SUPPORTING"}],
        scope="production",
    )
    assert result["edges"][0].resolution_status == "RESOLVED"
    assert any(item["code"] == "VIEW_CONTEXT_UNKNOWN" for item in result["diagnostics"])
    assert result["coverage"]["status"] == "PARTIAL"


def test_ac04_invalid_claim_does_not_mutate_inputs():
    invalid = ViewEdge("bad", "a", "b", "calls", resolution_status="NOT_A_STATUS",
                       attributes={"scope": "production"})
    before = deepcopy(invalid)
    source_provenance = [{"id": "ev:x", "evidence_kind": "SYMBOL_RESOLVED",
                          "freshness": "CURRENT", "polarity": "SUPPORTING"}]
    provenance_before = deepcopy(source_provenance)
    with pytest.raises(ViewValidationError) as caught:
        aggregate_view_edges([invalid], source_provenance, scope="production")
    assert any(item["code"] == "INVALID_RESOLUTION_STATUS" for item in caught.value.errors)
    assert invalid == before
    assert source_provenance == provenance_before


def test_ac05_scope_context_exclusions_and_invalid_polarity_stay_unknown():
    production = ViewEdge("prod", "a", "b", "calls", evidence_refs=("ev:bad-polarity",),
                          resolution_status="RESOLVED", attributes={"scope": "production",
                          "context_ids": ["ctx-prod"]}, freshness="CURRENT")
    test_only = ViewEdge("test", "a", "b", "calls", evidence_refs=("ev:test",),
                         resolution_status="RESOLVED", attributes={"scope": "test",
                         "context_ids": ["ctx-test"]}, freshness="CURRENT")
    other_context = ViewEdge("other-context", "a", "b", "calls", evidence_refs=("ev:other",),
                             resolution_status="RESOLVED", attributes={"scope": "production",
                             "context_ids": ["ctx-other"]}, freshness="CURRENT")
    mixed_contexts = ViewEdge("mixed-contexts", "a", "b", "calls", evidence_refs=("ev:mixed",),
                              resolution_status="RESOLVED", attributes={"scope": "production",
                              "context_ids": ["ctx-prod", "ctx-other"]}, freshness="CURRENT")
    provenance = [
        {"id": "ev:bad-polarity", "evidence_kind": "SYMBOL_RESOLVED", "freshness": "CURRENT",
         "polarity": "SUPPORT"},
        {"id": "ev:test", "evidence_kind": "SYNTAX_CANDIDATE", "freshness": "CURRENT",
         "polarity": "SUPPORTING"},
        {"id": "ev:other", "evidence_kind": "SYMBOL_RESOLVED", "freshness": "CURRENT",
         "polarity": "SUPPORTING"},
        {"id": "ev:mixed", "evidence_kind": "SYMBOL_RESOLVED", "freshness": "CURRENT",
         "polarity": "SUPPORTING"},
    ]
    before_edges, before_provenance = deepcopy([production, test_only, other_context, mixed_contexts]), deepcopy(provenance)
    result = aggregate_view_edges([production, test_only, other_context, mixed_contexts], provenance,
                                  scope="production", context_ids=["ctx-prod"])
    assert len(result["edges"]) == 1
    assert result["edges"][0].unknown_refs == ("ev:bad-polarity",)
    assert result["coverage"]["counts"] == {"found": 1, "resolved": 1, "unresolved": 0, "excluded": 3}
    assert result["coverage"]["status"] == "PARTIAL"
    assert any(item["code"] == "INVALID_EVIDENCE_POLARITY" for item in result["diagnostics"])
    assert [production, test_only, other_context, mixed_contexts] == before_edges
    assert provenance == before_provenance


def test_explicit_unknown_polarity_cannot_be_relabelled_by_view_or_aggregation():
    edge = ViewEdge("edge", "a", "b", "calls", evidence_refs=("ev:unknown",),
                    resolution_status="RESOLVED", attributes={"scope": "production",
                    "context_ids": ["ctx-prod"]}, freshness="CURRENT",
                    supporting_refs=("ev:unknown",))
    provenance = [{"id": "ev:unknown", "evidence_kind": "SYMBOL_RESOLVED",
                   "freshness": "CURRENT", "polarity": "UNKNOWN"}]
    with pytest.raises(ViewValidationError) as caught:
        aggregate_view_edges([edge], provenance)
    assert "EVIDENCE_POLARITY_NOT_PRESERVED" in {item["code"] for item in caught.value.errors}

    data = {
        "schema_version": 1, "view_id": "view", "kind": "topology",
        "baseline_fingerprint": "sha256:test", "rules_version": "t009", "scope": "production",
        "context_selection": {}, "nodes": [], "edges": [{
            "id": "edge", "source": "a", "target": "b", "relation": "calls",
            "evidence_refs": ["ev:unknown"], "supporting_refs": ["ev:unknown"],
            "contradicting_refs": [], "unknown_refs": [], "attributes": {},
        }], "diagnostics": [], "coverage": {"status": "UNKNOWN"}, "limits": [],
        "provenance": provenance,
    }
    with pytest.raises(ViewValidationError) as caught:
        ViewDocument.from_dict(data)
    assert "EVIDENCE_POLARITY_NOT_PRESERVED" in {item["code"] for item in caught.value.errors}


def test_ac04_malformed_scope_inputs_return_structured_errors_without_mutation():
    edge = ViewEdge("edge", "a", "b", "calls", attributes={"scope": {"bad": "scope"}})
    before = deepcopy(edge)
    with pytest.raises(ViewValidationError) as caught:
        aggregate_view_edges([edge], [])
    assert "INVALID_SCOPE" in {item["code"] for item in caught.value.errors}
    assert edge == before


def test_ac04_malformed_polarity_array_returns_structured_error_without_mutation():
    edge = ViewEdge("edge", "a", "b", "calls", evidence_refs=("ev:source",),
                    attributes={"scope": "production", "context_ids": ["ctx-prod"]},
                    unknown_refs=([],))
    before = deepcopy(edge)
    provenance = [{"id": "ev:source", "evidence_kind": "UNKNOWN",
                   "freshness": "UNKNOWN", "polarity": "UNKNOWN"}]
    with pytest.raises(ViewValidationError) as caught:
        aggregate_view_edges([edge], provenance)
    assert "INVALID_STRING_ARRAY" in {item["code"] for item in caught.value.errors}
    assert edge == before


def test_ac04_non_sequence_edges_return_structured_error():
    with pytest.raises(ViewValidationError) as caught:
        aggregate_view_edges(None, [])
    assert "INVALID_EDGES" in {item["code"] for item in caught.value.errors}

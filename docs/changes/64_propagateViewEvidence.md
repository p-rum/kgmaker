# Propagace evidence a coverage do pohledů (T009)

T009 doplňuje T005 `ViewDocument` a T008 service inventory o oddělené evidence kind,
resolution status, freshness a polarity references. Edge agregace seskupuje jen
shodný source/target/relation/scope/context výběr a ponechává supporting,
contradicting i neklasifikované evidence refs spolu s diagnostikami. Nepodporovaná
polarita zůstává UNKNOWN. Coverage má counts `found`, `resolved`, `unresolved` a
`excluded`; prázdný vstup je UNKNOWN. Legacy view v1 se načítá s unresolved/unknown
výchozími hodnotami, které nic nepovyšují.

## Acceptance a ověření

- T009-AC01: `test_ac01_syntax_candidate_stays_syntax_candidate_and_legacy_defaults_do_not_upgrade` a `test_t009_additive_fields_validate_against_public_view_schema` — cílená sada PASS.
- T009-AC02: `test_ac02_mixed_evidence_retains_support_conflict_unknown_refs_and_diagnostics` a `test_explicit_unknown_polarity_cannot_be_relabelled_by_view_or_aggregation` — cílená sada PASS.
- T009-AC03: `test_ac03_empty_unanalyzed_input_is_unknown_with_zero_counts` — cílená sada PASS.
- T009-AC04: `test_ac04_invalid_claim_does_not_mutate_inputs` a `test_ac04_malformed_scope_inputs_return_structured_errors_without_mutation` — cílená sada PASS.
- T009-AC05: `test_ac05_scope_context_exclusions_and_invalid_polarity_stay_unknown`, `test_unknown_claim_freshness_is_not_upgraded_by_current_source_reference`, `test_claim_without_context_identity_is_kept_separate_and_diagnostic`, a T008 skutečné production/test workspace regressions — cílená sada PASS.
- T009-AC06: README, architecture, status, acceptance matrix a JSON Schema jsou aktualizovány. Finální full po opravě polarity: **450 passed, 109 skipped, 19.66 s**, exit0. Explicitní compiler/worker prerequisites a Windows gate byly SKIP, nikoli PASS; tato čistá projekce nemění worker runtime.

Nezávislá kontrola reprodukovala překryv UNKNOWN a SUPPORTING/CONTRADICTING bucketů: **2 FAIL, 1 PASS**. Agregace nyní odmítne všechny párové překryvy před sloučením; parametrizovaný test také ověřuje nulovou mutaci vstupů. Finální cílená T009/T005/T006/T008 sada: **56 passed, 0.23 s**. Finální full: `flock /workspace/kgmaker-heavy-tests.lock env PYTHONPATH=/workspace/t009/src /workspace/kgmaker-venv/bin/python -m pytest -q -rs` — **450 PASS /109 SKIP**. Validace semantic/apply/scan/check a diff jsou zaznamenány po finální změně.

Původní lokální číslo58 před publikací kolidovalo s novým otevřeným T046 PR; tento dosud nepublikovaný dokument byl přidělen jako64. Historické memory epizody se nepřepisují.

## Kompatibilita a omezení

Schéma view v1 je rozšířeno aditivními poli; načtení starých payloadů zůstává
konzervativní. Graph schema a CLI se nemění. Příklad čisté agregace používá
explicitní evidence a context ID:

```python
from kgmaker.architecture_model import ViewEdge, aggregate_view_edges

result = aggregate_view_edges(
    [ViewEdge("e1", "service:orders", "db:orders", "depends_on",
              evidence_refs=("ev:source",), resolution_status="UNRESOLVED",
              attributes={"scope": "production", "context_ids": ["ctx-orders"]},
              evidence_kinds=("SOURCE_ONLY",), unknown_refs=("ev:source",))],
    [{"id": "ev:source", "evidence_kind": "SOURCE_ONLY",
      "freshness": "UNKNOWN", "polarity": "UNKNOWN"}],
    scope="production", context_ids=["ctx-orders"],
)
assert result["coverage"]["status"] == "PARTIAL"
```

T003-S07-W08 evidence ranking zůstává nedodané upstream. Tato implementace
nevytváří skóre ani neodvozuje polaritu z neklasifikovaných claimů. Konflikt
označí pouze tehdy, když jsou pro stejný agregovaný vztah explicitní supporting
a contradicting refs; obě sady refs zůstávají ve výstupu. Runtime observation,
CLI a obecné T004 discovery/rendering se tím neprohlašují za hotové.

# T005: verzovaný model pohledu

## Problém

Následující katalogy rozhraní, topologie a procesů potřebují společný přenosný
kontrakt. Stávající graph v1/v2/v3 zůstává zdrojem technických faktů a nemá být
nahrazen odvozeným zobrazením.

## Změny

- Přidán `kgmaker.architecture_model` s immutable dataclasses pro node/edge/view,
  deterministickou JSON serializací a SHA-256 fingerprintem kanonického obsahu.
  View envelope nese explicitní scope, rules version a kontextový výběr.
- Přidán čistý validator pro verzi, identity, endpointy, provenance references a
  coverage/resolution invariants. Chyby mají strojově čitelný `code` a `path`.
- Přidáno JSON Schema `view-v1.schema.json`; aktualizována README, architektura,
  acceptance inventář a progress matrix tak, aby oddělily dostupný model od
  neimplementované discovery/CLI/render části.

Task: T005. Acceptance: T005-AC01–AC06.

## Kompatibilita

Existující loader `KnowledgeGraph.from_dict` a graph schémata v1/v2/v3 zůstávají
beze změny. View dokument není zapisován do graph store. Evidence kind, scope,
context selection, unresolved informace a partial coverage se zachovávají; model
nepřidává technické hrany ani runtime důkazy. Persistent migrace není potřeba.

## Ověření

- `python3 -m pytest -q tests/test_t005_add_view_model.py` — 20 passed.
- `python3 -m pytest -q` — 202 passed, 15 skipped, 18 subtests passed.
- `python3 -m json.tool docs/schemas/view-v1.schema.json` — valid JSON.
- `python3 -m compileall -q src/kgmaker/architecture_model.py tests/test_t005_add_view_model.py` — success.
- Whitespace check against the verified PR10 base for all changed lines/new files — PASS.
- `python3 bin/kgmaker semantic update --root . --base 5af76cfffaeff3aefc71ae3ea1ed06dbbbba679b`, scoped empty patch, `semantic apply`, `semantic validate`, and `scan` — PASS. No unsupported semantic relationships were added.
- `python3 bin/kgmaker check --root .` — PASS (259 files, 2279 nodes, 14517 relationships).
- Worker/compiler and Mermaid gates — NOT_APPLICABLE; T005 adds neither.

Přímé testy: `test_round_trip_valid_model_preserves_public_contract`,
`test_permuted_inputs_have_byte_identical_canonical_json`,
`test_unknown_version_and_dangling_endpoint_or_evidence_are_rejected`,
`test_duplicate_node_id_has_structured_validation_error`,
`test_existing_graph_loader_still_accepts_legacy_schema_versions`,
`test_scope_context_and_evidence_kind_are_preserved_without_upgrade` a
`test_complete_coverage_cannot_hide_unresolved_edges`; adversarial malformed
enum, nested field, NaN and non-JSON inputs return structured validation errors.

## Příklad a zbývající práce

`ViewDocument.from_dict(payload).to_json()` ověří a kanonicky serializuje view;
`content_fingerprint` nezahrnuje samostatná `generation_metadata`. Model ještě
nevybírá kontexty ani nesestavuje katalog/topologii/proces, nemá CLI ani renderer.
T006 a další tasky zůstávají samostatné SPECIFICATION. Tato změna sama
neprohlašuje T004 za dokončené. Pull request: #11.

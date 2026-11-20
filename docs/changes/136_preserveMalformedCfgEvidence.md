# Ochrana CFG projekce při neplatných odkazech na compiler evidence

Úkol [T025](../tasks/T-025_build-local-process-path.md). Lokální baseline
`465b121992aad50c2885acef0fd038531a31293a`. Stav opravy IN_PROGRESS, ověření PARTIAL.

## T025-S07 / T025-AC04, AC05, AC08, AC09

Projekce `views.project` zkoušela iterovat volitelný seznam
`local_operation_evidence_ids` před ověřením typu. Hodnota null přerušila
projekci výjimkou. Neplatné pole má zůstat v bloku pro fail-closed validaci,
bez přidělení pravomoci jakémukoli odkazu.

[Projekce](../../src/kgmaker/views.py) pro výběr evidence používá společně
jediný řetězcový odkaz verze 1 v každém bloku. Odkazy patřící platným uzlům stále procházejí existující
izolací scope/context. Neplatná metadata se zachovají pro pozdější validaci.
Schéma grafu ani veřejné parametry se nemění.

Příklad chybného bloku je `{"local_operation_version":1,"local_operation_evidence_ids":null}`.
Projekce vrací původní volitelná data a nezapočítá je mezi vybrané důkazy.

## T025-S04 a T025-S05 / T025-AC04, AC06, AC08

- RED na nezměněné baseline, `pytest -q --tb=short tests/test_local_operation_proofs.py -k test_scope_projection_preserves_invalid_operation_shape_for_fail_closed_validation` — FAIL, 1 failed, 3 passed (55 deselected).
- Po prvním patchi `pytest -p no:cacheprovider -q tests/test_local_operation_proofs.py tests/test_t025_build_local_process_path.py tests/test_stage_content_cache.py tests/test_graph_provider.py` — 137 PASS, 22 SKIP. SKIP zahrnuje nepřipravené skutečné workery.
- Finální běh `KGMAKER_REQUIRE_WORKERS=1 pytest -p no:cacheprovider -q --tb=short tests/test_local_operation_proofs.py tests/test_t025_build_local_process_path.py tests/test_graph_provider.py` — 113 PASS / 0 SKIP s připraveným JDK21 a K1/K2. Runtime důkaz K1/K2 byl připojený z identických worker zdrojů v cache worktree.
- `git diff --check` — PASS. Úplná sada nad tímto worktree, GitHub CI, review a
  merge NOT_RUN.
- Aktualizovány [README](../../README.md), [capability a API](../process-paths.md),
  [acceptance inventář](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).
  CLI syntaxe i zadání zůstávají kompatibilní. Zbývá nezávislé review a ověření PR
  proti aktuálnímu main.

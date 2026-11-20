# Ochrana CFG projekce při neplatných odkazech na compiler evidence

Úkol [T025](../tasks/T-025_build-local-process-path.md). Lokální baseline
`465b121992aad50c2885acef0fd038531a31293a`. Při prvním lokálním ověření
byla oprava IN_PROGRESS. Následný [draft #122](https://github.com/p-rum/kgmaker/pull/122) je PR_OPEN, ověření zůstává PARTIAL.

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
- Finální běh `KGMAKER_REQUIRE_WORKERS=1 pytest -p no:cacheprovider -q --tb=short tests/test_local_operation_proofs.py tests/test_t025_build_local_process_path.py tests/test_graph_provider.py` — 113 PASS / 0 SKIP s připraveným JDK21 a K1/K2. Kompilátorové workery K1/K2 byly připojené z identických worker zdrojů v cache worktree.
- `git diff --check` — PASS. Úplná sada nad tímto worktree, GitHub CI, review a
  merge NOT_RUN.
- Aktualizovány [README](../../README.md), [capability a API](../process-paths.md),
  [acceptance inventář](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).
  CLI syntaxe i zadání zůstávají kompatibilní. Zbývá nezávislé review a ověření PR
  proti aktuálnímu main.

## T025-S04, S05 a S07 / T025-AC04, AC05, AC06, AC08 a AC09 — přenos po T052

Integrační baseline je ověřený GitHub main
`8ff2529ffb50b42ed2209d97478ea3e4cbf46042` s tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. [Zdroj](../../src/kgmaker/views.py)
a [regresní test](../../tests/test_local_operation_proofs.py) jsou bajtově
shodné s draft HEAD `ebd954692259be2a86ef8ec0b9134a7889ce5d2c`. Přenesený
dokumentační diff zachovává současný T052 checkpoint a historii.
Workflow úloha `task:8c0f8a08011df6992b001f26fc3df81ef9021a730e95d10097930b92c2faa101`
zůstává v `/tmp/kgmaker-t025-projection`. Integrační kód je v samostatném
`/tmp/kgmaker-t025-after-t052`. CLI parametry, formát grafu, init a registr
zadání mají beze změny stejný kontrakt.

```sh
env JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
  PATH="/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH" \
  JAVA_TOOL_OPTIONS=-XX:-UsePerfData KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python \
  -m pytest -p no:cacheprovider -q --tb=short \
  --basetemp .kgmaker/workflow/pytest-t025-after-t052 \
  tests/test_local_operation_proofs.py tests/test_t025_build_local_process_path.py \
  tests/test_graph_provider.py
```

- PASS, 113 testů bez skipu za 22,08 s. JDK 21.0.13.1 a skutečné Kotlin
  2.1.10 K1/K2 workery. Pět tvarů neplatných odkazů se zachová v bloku bez
  vybrané evidence nebo mutace vstupního grafu.
- PASS, `git diff --check` a kontrola bajtové shody s původním draftem.
- PASS, `kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker scan`
  a `kgmaker check`. Opravené kotvy zdrojových citací zachovaly 55 konceptů,
  185 sémantických vztahů a všech 329 existujících epizod.
- NOT_RUN, úplná sada nad přeneseným kandidátem, publikované T045 review
  nového páru a nový GitHub Actions důkaz.
- BLOCKED pro merge, `completion plan` uvádí nepřímý FAIL od T003-S07-W05
  ([#126](https://github.com/p-rum/kgmaker/pull/126)). Cílený scope nedokládá
  produkční provedení procesu ani úplnou T025/T004 acceptance.

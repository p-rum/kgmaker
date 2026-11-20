# Ověřování compiler evidence při explicitní inspekci

Úkol [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md), incident
[#116](https://github.com/p-rum/kgmaker/issues/116). Zdrojová baseline
`465b121992aad50c2885acef0fd038531a31293a`; merge #114
`7c6a3dda821b55a4de6718f09504de4a861f47ae`. Aktuální cílový ref při ověření
`8f362471a8254ff9a0e44870c490a1dcb6b067b1`.

## Kroky 1 a 2 / T003-S10-W01-AC01, AC02, AC03

Spolu s kandidátem replay se v indexu ukládá i jeho digest. Vlastník
původního grafu mohl uložit nepodloženou hranu a validátor přijal strukturálně
konzistentní změnu se správně přepočteným digestem. Zdrojem pozorované chyby
byl [cache reader](../../src/kgmaker/extraction_cache.py). Merge provider
navíc dříve preferoval uložený záznam evidence při shodě ID.

## Kroky 3 a 4 / T003-S10-W01-AC01, AC02, AC03

Každá explicitní inspekce provede `worker-analysis`, projekci grafu a v JVM
framework augmentation. Před publikací stále kontroluje vstupy, timeout a zrušení.
Čerstvý důkaz vybraného kontextu má při shodě ID přednost. Formáty grafu v1–v3,
envelope v1 a existing scope/selection zůstávají kompatibilní.
[Přehled kontraktu](../stage-content-cache.md).

Příklad `kgmaker inspect code --root ./service --module core --source-set main`
hlásí pro standardní fáze `BYPASS/UNVERIFIED_REPLAY`. Opakovaný příkaz i se
stejnými vstupy znovu spustí práci. Pozdější samostatný krok může obnovit
výkon s nezávisle ověřitelnou provenance. Záznam dříve publikovaný pro jiný
kontext může vyžadovat novou explicitní inspekci tohoto kontextu.

- RED — `pytest -o pythonpath=/tmp/kgmaker-t047-oracle/src -p no:cacheprovider -q --tb=short tests/test_stage_content_cache.py tests/test_graph_provider.py -k 'rehashed or explicit_context_refresh_replaces'`
  nad původním Python modulem selhal ve všech čtyřech reprodukcích. Kontroly
  zahrnují worker coverage, compiler/graph, framework/graph a precedence evidence.
- PASS — JDK 21.0.13.1, skutečný Kotlin 2.1.10 K1 a K2 build pomocí
  `workers/jvm/build.py` nad připnutými lokálními deps. Připravený TypeScript 5.7.3.
- PASS — `KGMAKER_REQUIRE_WORKERS=1 python -m pytest -p no:cacheprovider -q tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py tests/test_argument_parameter_flow.py tests/test_graph_provider.py`,
  97 PASS, 0 SKIP. Součástí jsou fresh cold/warm, classpath/config, guardy store,
  zachování poslední validní generace a nulové spuštění workerů při offline refresh.
- `git diff --check` PASS. Publikované PR review a GH Actions NOT_RUN.

## Krok 5 / T003-S10-W01-AC04

Upřesněny [README](../../README.md), [compiler CLI](../compiler-inspection.md),
[matice](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md).
Vztah k registru, CLI argumenty, schema a init zůstávají kompatibilní.
T003-S10-W02 až W06, výkonový HIT a produkční availability nejsou doloženy
tímto během. Úplná sada a publikovaná dvojice SHA mají samostatné ověření.

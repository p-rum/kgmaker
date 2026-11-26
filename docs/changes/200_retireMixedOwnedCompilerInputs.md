# Současná úprava a odstranění JVM vstupů v izolovaném kontextu

26. listopadu 2026. [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
kroky 1–5, W02-AC01 až AC04 a T003-AC10. Výchozí `main`
`c4a1edb59f140faeafba0d5e979023bba185f3f1`, strom `b5f8b794ebadf802f52ce16c53890dcb728185ae`.
Předchozí samostatné odstranění dodalo [#178](https://github.com/p-rum/kgmaker/pull/178)
v merge `044c461dc1c63367a50522261df70a375cccb492`.

## Krok 1 — reprodukce (AC01)

Tři moduly mají vlastní platné compiler kontexty. V kontextu `edited` se
smaže původní `Example.kt` a `Caller.kt` se upraví, aby už nevolal smazanou
funkci. Nezávislý `selected` rozřeší vlastní nové volání při `publish=False`.
Původní kód však odmítne publikaci se `STALE` už před výměnou prvního
výstupu. Nová regrese selhala očekávaným způsobem v K1 i K2. Pytest exit 1,
2 FAIL, JUnit SHA-256 `3d783e4b7dfa81be6e09ce7517e992200b0bd177c9228e53ce7b2b011a385d75`.

## Krok 2 — kompatibilita (AC02)

`src/kgmaker/graph_provider.py` používá existující typovanou odchylku se sadou
smazaných cest a mapou změněných cest. Úprava vychází ze stejného raw JVM
snapshotu a formátu graph/store. Migrace není potřeba.

## Krok 3 — důkaz změny a atomický zápis (AC01, AC03)

Množina aktuálních cest musí být podmnožinou dřívějších. Změněné cesty musí
patřit mezi původní compiler vstupy a být načtené aktuálním scannerem. Smazané
cesty musí být původní compiler vstupy, fyzicky chybět a mít stále stejného
výhradního vlastníka, kterého dokládá uložená generace. Kontroly oddělení
kontextů, modelu, konfigurace, classpath, distribuce a připojených důkazů platí
i při kombinaci úpravy a smazání. `STALE` při vyřazení obsahuje obě sady cest.

Stávající publikační kontrola před výměnou i po ní potvrzuje nepřítomnost
smazaného vstupu a raw otisky původních cest. Pozdní návrat souboru nebo změna
bajtů proto zachová poslední platnou generaci a vrátí `STALE`.

## Krok 4 — nativní kontroly (AC01–AC03)

`test_actual_jvm_retirement_after_mixed_owned_peer_changes` používá skutečný
Kotlin K1 a K2 na Linuxu s Temurin JDK 21.0.6+7 a připnutými distribucemi.
Ověřuje chování při přidání nové deklarované cesty, nový přesně rozřešený call
site, odstranění starých faktů a shodu nezávislého compiler kontextu. Dvě
oddělené varianty nechají nejprve vyměnit první výstup. První znovu vytvoří
smazaný soubor, druhá změní konce řádků v přežívajícím souboru při stejném
normalizovaném obsahu. Po obou odmítnutích se shodují všechny soubory store
i revize CAS. Součástí běhu jsou i dřívější samostatné kontroly změny bajtů,
smazání, překryvu vlastnictví, nedostupných cest a nesouvisejícího raw driftu.

```sh
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 PYTHONPATH=src \
  python -m pytest -n 2 --dist load --maxschedchunk=1 -q --tb=short \
  -p no:cacheprovider -o tmp_path_retention_policy=failed \
  tests/test_reverse_dependency_index.py tests/test_graph_provider.py tests/test_completion.py \
  -k 'retirement_after_mixed_owned_peer_changes or input_absence or retirement_of_deleted_owned_peer_input or actual_jvm_isolated_stale_peer_publication_and_guards or actual_jvm_overlapping_stale_peer_still_aborts or overlapping_deleted_peer_input_still_aborts or actual_jvm_uncaptured_eol_drift_during_peer_publication or test_graph_provider or test_completion'
```

**36 PASS / 0 SKIP / 0 FAIL**, raw exit 0. JUnit SHA-256
`05bfb757f083c621cce69d266eca873bcba64fd8782296ece0a91a8d2273352d`.
Před a po běhu souhlasilo 164 zdrojových a testovacích vstupů a 33 artefaktů
JVM distribucí a JDK. Plánovač zachoval všech 135 položek a 32 rozhodnutí delegace.

## Krok 5 — použití a stav (AC04)

Po úpravě a smazání lze čtecímu reportu předat obě cesty. Nový vybraný
kontext se publikuje samostatným explicitním voláním `inspect_jvm` ve stejném
checkoutu s nezměněným `project_model`.

```sh
kgmaker impact --evidence-only --format json \
  edited/src/main/kotlin/Example.kt edited/src/main/kotlin/Caller.kt
```

[Popis CLI](../stage-content-cache.md#selektivní-dopad-změn) ·
[Příklad Python API](../compiler-inspection.md#obnova-izolovaného-jvm-kontextu) ·
[Acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy) ·
[Stav](../production-analysis-progress.md).
W02-AC01 zůstává `PARTIAL`; W03 nadále vyžaduje `VERIFIED_IN_SCOPE` pro W02.
Přidání zdrojů, negativní lookupy, sdílené moduly a zápis přes CLI s build
manifestem mají vlastní rozsah. Úplná standardní sada a nezávislé review
této revize čekají na ověření přesného kandidáta.

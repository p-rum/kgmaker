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

Před každou výměnou výstupu publikační kontrola ověřuje nepřítomnost
smazaných cest a otisky bajtů původních vstupů vyřazovaného kontextu.
Pokud po výměně mezivýstupu a před závěrečnou výměnou `graph.json` zjistí
návrat souboru nebo změnu bajtů, vrátí `STALE`. Publikace obnoví mezivýstupy,
které stále vlastní, a zachová poslední platný `graph.json`.

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
manifestem mají vlastní rozsah.

## Krok 6 — draft #184 a přenos po #181

Při otevření měl [draft #184](https://github.com/p-rum/kgmaker/pull/184) head
`fa51826bf291eb17bef9d9d14d36fe3b3e4a5686` a strom
`0009af7eaf2e9c9e3b407ae04bdc33bc148242b7`. Jeho rodič je
`c4a1edb59f140faeafba0d5e979023bba185f3f1`. Doložených 36 nativních PASS z kroku 4
patří původnímu výřezu s tímto stromem.

Přenesený kandidát zachovává zdroj i testy W02 z původního headu a runtime
změny [#181](https://github.com/p-rum/kgmaker/pull/181) z aktuálního `main`
`7919c283c4ea7b58eb99bfcfbc3971903984f438`. Nativní i úplná standardní sada
a nezávislé review složené revize mají při této přípravě stav `NOT_RUN`.
W02 zůstává `MERGED / PARTIAL` podle rozsahu dříve sloučených výřezů.

## Krok 7 — přenos po #182

Přenos po sloučení [#182](https://github.com/p-rum/kgmaker/pull/182) spojil dosavadní
head draftu #184 `1fb557b190af2fac56b08dc4d4fdae2dbf3fd9ea` s tehdejším
`main` `adca1031dede08e294c3fd1234150d27ee6379a6`.
Zdroje a testy W02 zůstaly shodné s dosavadním headem draftu. Výsledky z kroku 4
patří původnímu stromu. Při přípravě této integrace měly nový nativní běh i úplná
standardní sada stav `NOT_RUN`. W02 zůstává `MERGED / PARTIAL`.

## Krok 8 — doložení stavu W02 (T003-S10-W02-AC04, T052-AC04)

Výchozí revize je `d0dfd024fa108f74f82aef49c0a940307230f8a4`. Po
[review T045](https://github.com/p-rum/kgmaker/pull/184#issuecomment-7206793117)
uvádí řádek W02 v [implementačním inventáři](../production-analysis-progress.md)
výsledky konkrétních revizí a odkazuje na #184 bez dočasného stavu pull requestu.
Cílená sada s K1/K2 na `fa51826bf291eb17bef9d9d14d36fe3b3e4a5686` a na
výchozí revizi měla v obou případech 36 PASS / 0 SKIP. Úplná sada CPython 3.13
na výchozí revizi měla 2 673 PASS / 1 400 SKIP / 1 XFAIL, návratový kód 0.

Změna se týká `docs/production-analysis-progress.md`, tohoto záznamu a generovaného
grafu. Implementace, testy a jejich kompatibilita zůstaly beze změny. Na stromu
`1a99401e034405840750695255b496c26c0a1345` prošly `kgmaker semantic validate`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --check`.
`kgmaker completion plan --jobs 32` zachoval 135 položek a pořadí 32 delegací.
Při přípravě tohoto záznamu měly nativní a úplná sada pro novou revizi stav
`NOT_RUN`. W02 zůstává `MERGED / PARTIAL` a zahájení S10-W03 dál vyžaduje
`VERIFIED_IN_SCOPE` pro W02.

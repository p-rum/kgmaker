# Index doložených závislostí pro revalidaci

Výchozí reprodukce používá `main` `17e9e7368e6cc2d6550983c3039eb39debd65424`.
Integrační kandidát vychází z `main` `fad4fc63c76f0f9ef5a1a292e279d1269bd84540`
s tree `999b5ef61989bf91ce3df58e4d3bcc84c074eb31`. Zdrojové a testové změny se
shodují s dříve schváleným kandidátem `da9d0fd334f59f2ef7aa0b0589db2a2ca5e84e46`.
Změna pokrývá čtecí část [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md)
pod nadřazenou `T003-AC10`. Dodání je `PR_OPEN` v [#130](https://github.com/p-rum/kgmaker/pull/130)
a ověření `PARTIAL`. Samostatný kandidát nad `fad4fc6` zachovává sloučený T021.

## Krok 1 — výchozí kontrakt, AC01 a AC03

Původní `impact` v `src/kgmaker/cli.py` odhaduje dopad z importů a shod jmen.
`src/kgmaker/graph_provider.py` ověřuje celý vybraný compiler kontext.
`src/kgmaker/feature.py` porovnává snapshot celého feature packetu. Výchozí
`python -m kgmaker impact --evidence-only --format json README.md` vrátil
`unrecognized arguments: --evidence-only` (FAIL pro nový kontrakt, exit 2).
Ověření uložení a grafu doložilo jednu autoritativní generaci graph JSON.
Dosavadní zdrojový dopad a pravidla platnosti kontextu zůstávají kompatibilní.

## Krok 2 — identita generace, AC02

`src/kgmaker/store.py` načte graf a vypočte SHA-256 z týchž bajtů souboru.
`src/kgmaker/cli.py` přidává režim `impact --evidence-only --format json`.
Samostatný report JSON v1 nemění data ani verzi graph/store v1/v2/v3.
Test `test_legacy_and_unproven_name_matches_never_gain_positive_evidence`
ověřil všechny tři verze a čitelnost po smazání zachyceného zdroje (PASS).
Fixture Javac ověřila hash uložených bajtů (PASS).

## Krok 3 — důvody a zachování store, AC01 a AC03

`src/kgmaker/graph_provider.py` odvodí index z uložených grafových vazeb
a sleduje compiler callery přes přesné symboly a místně publikované důkazy.
Zahrnuje explicitní Flyway vazby a OpenAPI deklarace svázané se zdrojem.
`src/kgmaker/feature.py` váže přímé citace závěrů na kandidáta, receipt a
původní packet. Výstup označí doložené závislosti `RECHECK` a přímo zastaralé
citace `STALE`. Pro chybějící důkaz zůstává coverage `PARTIAL`. Dřívější režimy
`impact`, feature `apply`/`revise` a pravidla publikace grafu drží stávající kontrakt.
Testy `test_invalid_graph_and_nonregular_changed_source_leave_store_untouched`
a `test_replayed_schema_and_openapi_citation_invalidate_only_proven_dependents`
ověřily nulovou mutaci při nepoužitelném grafu/vstupu a změněném receipt-bound
kandidátovi (PASS). Ověření dalších workspace a negativních lookupů má vlastní
scope. Tato cesta nemá časovaný externí krok a nepoužívá procesy.

Nezávislé review našlo přerušený řetězec mezi dvěma symboly v témže souboru.
Samostatný běh Javac fixture před opravou v aktuálním kandidátu skončil
`1 FAIL`. Index nyní zachovává doložené vazby uvnitř souboru. Další průchod
sleduje identitu symbolu, takže se vazby oddělené metody neoznačí k revalidaci.
Stejná regrese po opravě prošla v cíleném běhu uvedeném níže.

Druhý nález ukázal blokaci při čtení FIFO místo souboru `analysis.json`.
Samostatný CLI test před opravou skončil `1 FAIL` na timeoutu 3 s. Sdílené
čtení v `src/kgmaker/analysis_model.py` ověří běžný soubor před otevřením a
po něm. Na platformách s příslušnými příznaky nepovolí blokující otevření FIFO
ani následování vyměněného symlinku. Graf a tři druhy záznamů feature používají
tento režim. `test_feature_record_fifos_do_not_block_or_publish` ověřil zvlášť
analýzu, receipt, aktuální packet a archivovaný packet (4 PASS na POSIX).

Correctness review prošlo na kandidátu `f68ac9ecaf9c649da31bfcf0a8a887124b283bd6`.
Steelman review stejného kandidáta našlo neobslouženou výjimku při použití
uloženého compiler `source_file` s hodnotou typu pole. Veřejný test
`test_malformed_stored_compiler_graph_keys_fail_closed_in_public_cli` ji
zopakoval nad skutečným Javac grafem v3 (1 FAIL před opravou). Čtečka jen pro
tento režim v `src/kgmaker/store.py` ověřuje skalární typy referenčních polí grafu.
Vadná generace vrací exit 1 bez tracebacku, výstupu JSON nebo zápisu.
`src/kgmaker/graph_provider.py` používá compiler kolekce pouze z grafu v3.
Původní loader a verze v1/v2/v3 si zachovávají formát.

`src/kgmaker/workspace.py` přidává neblokující otevření do sdíleného hashování,
aby při záměně zdroje za FIFO mezi kontrolou a otevřením vrátil report
`DEPENDENCY_PATH_UNAVAILABLE`. Test `test_changed_source_swapped_to_fifo_is_unavailable`
před opravou prokázal chybějící příznak bezpečnou kontrolou bez blokujícího otevření
(1 FAIL). Na POSIX ověřuje skutečnou záměnu, coverage `PARTIAL` a shodu bajtů store.

## Krok 4 — skutečné fixture, AC01–AC03

`tests/test_reverse_dependency_index.py` používá skutečný Javac/JDK21 pro
změnu signatury, volání a method reference. Nezávislá metoda ověřuje hranici
v témže souboru a samostatný compiler kontext pro druhý modul obsahuje shodnou
signaturu pod stejným názvem. Další fixture kombinuje Flyway replay změny typu,
nezávislou tabulku, aktualizaci OpenAPI JSON a aplikovanou feature revizi,
přičemž přítomnost nové neaplikované revize zachovává odkaz na původní packet.
`subprocess.Popen` je během výpočtu zakázaný a testy porovnávají bajty store.

Provedený cílený běh v Linuxu s `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`,
`KGMAKER_WORKERS_HOME=/tmp/kgmaker-cache-replay/workers`,
`KGMAKER_REQUIRE_WORKERS=1`, `JAVA_TOOL_OPTIONS=-XX:-UsePerfData` a `PYTHONPATH=src`:

```bash
python -m pytest -p no:cacheprovider -q --tb=short tests/test_reverse_dependency_index.py \
  tests/test_graph_provider.py tests/test_feature.py tests/test_feature_fixture.py tests/test_flyway.py \
  tests/test_workspace.py
```

Původní i integrační běh nad `fad4fc6` mají **77 PASS, 0 SKIP**. Integrační běh
znovu použil skutečný Javac/JDK21. Úplná sada, GitHub Actions a merge gate jsou
`NOT_RUN`. Integrační kandidát čeká na nové nezávislé review.

## Krok 5 — návod a stav, AC04

[README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
[příkaz a formát JSON](../stage-content-cache.md#selektivní-dopad-změn),
[inventář acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) popisují přesný scope.
Registr a instalované instrukce nemají dopad, protože identita, závislosti a
revize zadání ani init workflow se nemění. Migrace není potřeba.

```bash
kgmaker impact --root ./service --evidence-only --format json src/main/java/Api.java
```

Výpočet plánuje opětovné ověření. Způsob zápisu selektivní invalidace do grafu a
revizí, změny mimo uložený rozsah, zda se vazba po změně stále rozliší, a plný
workspace contract mají samostatnou evidenci. Celý T003-S10 zůstává `PARTIAL`.

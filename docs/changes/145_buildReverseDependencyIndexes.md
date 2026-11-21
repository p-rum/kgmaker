# Index doložených závislostí pro revalidaci

Výchozí reprodukce používá `main` `17e9e7368e6cc2d6550983c3039eb39debd65424`.
První integrační ověření proběhlo nad `main` `fad4fc63c76f0f9ef5a1a292e279d1269bd84540`.
Následné ověření vycházelo z merge W06 `c067f9c3c7b3266842fc4f2230b4eaf65182e4df`.
Ověření po #134 použilo `main` `d5a0b236716fd31dc1db11d9e6ae3c4f692f2d7e` se záznamem sloučeného W06.
Aktuální lokální kandidát vychází z potvrzeného `main` `c2885a6f8daf0281967e3bc5386a69f1647718e0`
s tree `17c36c142ed5cdffa0d712f961e463bdfe77a9aa`. Zachovává [#134](https://github.com/p-rum/kgmaker/pull/134)
a [#133](https://github.com/p-rum/kgmaker/pull/133).
Před níže uvedenou opravou z review se zdrojové a testové změny
shodovaly s dříve schváleným kandidátem `da9d0fd334f59f2ef7aa0b0589db2a2ca5e84e46`.
Změna pokrývá čtecí část [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md)
pod nadřazenou `T003-AC10`. Dodání je `PR_OPEN` v [#130](https://github.com/p-rum/kgmaker/pull/130)
a ověření `PARTIAL`. Kandidát zachovává sloučené T021 a W06.

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

Původní běh i integrační běhy nad `fad4fc6`, `c067f9c3` a `d5a0b236` mají každý
**77 PASS, 0 SKIP**. Stejné výsledky má integrační běh nad `c2885a6`.
Regrese souběžné publikace nad `d5a0b236` a `c2885a6` mají každý **18 PASS, 0 SKIP**.
Integrační běhy znovu použily skutečný Javac/JDK21. Úplná sada pro W02,
GitHub Actions a merge gate jsou
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

## Opakované předání po review — kroky 3 až 5, AC01–AC04

Výchozí head #130 byl `9a676a0e7cba148a375f1516dc06f909ac03e5a8` nad
`c2885a6f8daf0281967e3bc5386a69f1647718e0`. Nezávislé correctness a steelman
review vrátily nálezy do T052 iterace 1.

- **Krok 3, AC01 a AC03.** Předchozí index Flyway sledoval jen poslední cestu
  objektu. `src/kgmaker/graph_provider.py` používá také zachycené
  `operation_targets` ze stejného streamu se shodnou cestou a řádkem operace.
  Uvedený důvod obsahuje ID a řádek operace. Vadný záznam operace nemůže nahradit
  doloženou vazbu. Starší graf bez záznamu operace může doložit poslední cestu.
- **Krok 3, AC01 a AC03.** `src/kgmaker/feature.py` porovnává normalizovanou
  cestu požadavku a zachovává původní packet. Druhy souborových citací sdílí
  s `src/kgmaker/analysis_validation.py`. Citace lidské odpovědi se váže
  na rozhodnutí v packetu a nevyvolá souborovou revalidaci.
- **Krok 3, AC01–AC03.** `src/kgmaker/workspace.py` může z jediného stabilního
  čtení vypočítat hash bajtů i hash s normalizovanými konci řádků.
  `src/kgmaker/graph_provider.py` používá druhý hash pro `changed_sources`
  u textů scanneru. Doložená OpenAPI deklarace používá raw hash původní
  registrace. Compiler caller zůstává mimo výčet, když hash jeho worker
  důkazu s CRLF nesouhlasí s hashem normalizovaného textu grafu. Pokrytí
  je v tomto případě `PARTIAL`. Formát graph/store a JSON reportu zůstává
  kompatibilní.
- **Krok 4, AC01–AC03.** Cílená regrese v `tests/test_reverse_dependency_index.py`
  ověřuje změnu počátečního CREATE po ALTER, nezávislou migraci a chybný řádek
  uložené operace. Skutečný feature workflow pokrývá cestu
  `./req//requirement.md` a platnou lidskou odpověď s vedlejším údajem o souboru.
  Fixture pro OpenAPI zahrnuje nezměněné CRLF, změnu jen konců řádků a změnu
  operace, včetně rozdělení CRLF mezi čtené bloky. Citace feature v původním
  kombinovaném scénáři používá hash OpenAPI souboru s CRLF. Například
  `kgmaker impact --evidence-only --format json openapi.json` po úpravě pouze
  konců řádků může uvést `CONTRACT_DECLARATION` v `affected` při prázdném
  `changed_sources`.
- **Krok 5, AC04.** [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
  [kontrakt CLI](../stage-content-cache.md#selektivní-dopad-změn),
  [acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
  a [stav](../production-analysis-progress.md) popisují aktualizovaný rozsah.
  Registr a init nemají dopad. Automatická selektivní invalidace, negativní
  lookup a cross-workspace práce zůstávají samostatné.

- RED — `python -m pytest -p no:cacheprovider -q --tb=short tests/test_reverse_dependency_index.py -k 'prior_migration_operations or file_authority or normalized_hashes'`
  na původním kódu 6 FAIL a 12 DESELECTED.
- GREEN — cílený příkaz pro šest souborů z kroku 4 s Javac/JDK 21.0.6,
  `KGMAKER_REQUIRE_WORKERS=1` a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`
  má 83 PASS / 0 SKIP (19,40 s).
- `git diff --check` PASS. Pokrytí po úpravě dokumentace ověřují
  `kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker scan`,
  `kgmaker status` a `kgmaker check`.
- Úplná sada, GitHub Actions, nezávislé review opraveného kandidáta a merge
  zůstávají při předání NOT_RUN.

## Přenos po sloučení #132 — kroky 4 a 5, AC01–AC04

Lokální merge připravený z publikovaného headu #130
`7f174807d34a2d87ce8d7948b537cb28f7b29f30` a aktuálního `main`
`4011825b15e4b65e1f57576a0986ca05b3cf810e` zachovává historii obou větví.
Při porovnání před a po přenosu mělo všech osm zdrojových a testovacích cest
W02 i všechny tři cesty změněné v [#132](https://github.com/p-rum/kgmaker/pull/132)
identické bajty. Přenos vyřešil konflikty v generovaném grafu a sémantické vrstvě.
Třícestné sloučení zachovalo 56 konceptů, 191 vztahů a všech 339 dřívějších
epizod obou větví.

- **Krok 4, AC01–AC03.** JDK/Javac 21.0.6 a připravený worker, spuštěno s
  `PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1` a
  `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`. Příkaz níže má **144 PASS / 0 SKIP**
  za 26,60 s. Obsahuje 83 testů W02, 18 testů souběžné publikace W06 a 43
  procesních regresí T032. JUnit SHA-256 je
  `88aea8dbb5c64accd3974591a9faca67ba6d7501d6ef83f2671b8d2f2c6e31ed`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_reverse_dependency_index.py tests/test_graph_provider.py \
  tests/test_feature.py tests/test_feature_fixture.py tests/test_flyway.py \
  tests/test_workspace.py tests/test_graph_publication_concurrency.py \
  tests/test_t032_persist_process_review.py \
  --junitxml=/workspace/kgmaker-evidence/pr130-after132-scoped.xml
```

- **Krok 5, AC04.** [Inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
  a [stav](../production-analysis-progress.md) uvádějí nový základ.
  [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02)
  a [kontrakt CLI](../stage-content-cache.md#selektivní-dopad-změn) dál
  popisují zachovaný čtecí režim včetně použitého příkladu. Formáty grafu,
  stávající příkazy a registr odpovídají předchozímu dodání.

AC01 zůstává `PARTIAL`. Zápis selektivní invalidace, negativní lookupy a
cross-workspace projektové vazby mají samostatné ověření. Úplná sada W02,
review tohoto integračního stromu a GitHub Actions jsou při předání `NOT_RUN`.

## Dříve doložený Javac cíl po změně konců řádků — kroky 3–5, AC01, AC03 a AC04

Výchozí head #130 je `cbf82d9c1b4164589592982d3ffafa4996aee603`.
Změna LF na CRLF v dříve analyzovaném `Api.java` označila uložený JVM kontext
při offline ověření jako zastaralý. Report porovnal normalizovaný text a
vynechal dříve doloženého callera.

`src/kgmaker/graph_provider.py` porovnává i hash z jednoho stabilního čtení
původních bajtů. Při shodném normalizovaném textu a rozdílných bajtech
zařadí do stávajícího průchodu přesné identity compiler cílů z již doložených
vazeb, pokud původní lokátor cíle uvádí přesnou cestu a hash shodný s grafem
i kontextem. Samotná shoda normalizovaného hashe grafu a kontextu k tomu nestačí.
Report pro tuto úpravu má prázdné `changed_sources` a označí dotčené
`COMPILER_CALLER` v `affected` jako `RECHECK`. Používá graph/store v1/v2/v3
a JSON v1. Použití a hranice jsou v [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
[capability](../stage-content-cache.md#selektivní-dopad-změn),
[inventáři](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavové matici](../production-analysis-progress.md).

Nový skutečný Javac test ve `tests/test_reverse_dependency_index.py` zachytí
volání `Api.value` i nezávislé `Other.value`. Mění pouze konce řádků prvního
cíle. Ověřuje `STALE_INDEX` provideru, původní identitu callera, cíle a call
site, jediný dotčený výsledek, hash grafu a shodu bajtů store. Varianty s
chybějícím či neshodným hashem lokátoru vyřazují čistě bajtovou změnu. Běžnou
změnu normalizovaného textu směrují ke stejnému callerovi všechny tři varianty.
Offline ověření a report běží se zakázaným spouštěním podprocesů.

Běhy použily JDK/Javac 21.0.6, připravený worker, `PYTHONPATH=src`,
`KGMAKER_REQUIRE_WORKERS=1` a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short \
  tests/test_reverse_dependency_index.py::test_actual_javac_line_ending_change_rechecks_proven_caller
```

- RED na `cbf82d9` má 1 FAIL za 5,39 s kvůli chybějícímu callerovi.
  JUnit SHA-256 `32ebfdc3d1f8cee6587c288eea046d0c7290ee9659e6d7bcae842245eeb2b480`.
- Předběžné GREEN s ověřeným lokátorem má 1 PASS / 0 SKIP za 5,21 s.
  JUnit SHA-256 `a8af7dfcf07664ca6f87d8959c681ff20aec2a126a92212fd923165fcc4d71de`.
- Předběžné rozšíření bez ověření lokátoru mělo 2 FAIL / 1 DESELECTED
  za 10,28 s pro `-k 'unknown or mismatched'`. Obě varianty chybně
  označily callera po čistě bajtové změně. JUnit SHA-256
  `8766029e4c2f8b86de285e5fa6c9b3e22bb5d8603df7d2cad8edfd7cecc21e2b`.
- GREEN pro všechny tři varianty po ověření lokátoru má 3 PASS / 0 SKIP
  za 14,48 s. JUnit SHA-256
  `6b312ad5b2283f05c46416f047f74a69e4918c9829961529621bd676a7bf68f7`.
- Širší výběr osmi souborů z předchozího přenosu s `KGMAKER_REQUIRE_K2=1`
  má 147 PASS / 0 SKIP za 35,47 s. JUnit SHA-256
  `1818c0f8ac7ce90b92439a98786db8fc1f08ce2e407caee1b748cb40c4aef00e`.

W02-AC01 je `PARTIAL`. Prvotní compiler capture souborů s CRLF, zápis
selektivní invalidace a negativní lookup vyžadují vlastní kroky. Úplná sada,
nezávislé review této revize a GitHub Actions mají při předání `NOT_RUN`.

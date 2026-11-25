# Index doložených závislostí pro revalidaci

Výchozí reprodukce používá `main` `17e9e7368e6cc2d6550983c3039eb39debd65424`.
První integrační ověření proběhlo nad `main` `fad4fc63c76f0f9ef5a1a292e279d1269bd84540`.
Následné ověření vycházelo z merge W06 `c067f9c3c7b3266842fc4f2230b4eaf65182e4df`.
Ověření po #134 použilo `main` `d5a0b236716fd31dc1db11d9e6ae3c4f692f2d7e` se záznamem sloučeného W06.
Tehdejší lokální kandidát vycházel z potvrzeného `main` `c2885a6f8daf0281967e3bc5386a69f1647718e0`
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

## Přenos na main po #135 — kroky 4 a 5, AC01–AC04

Rodiče kandidáta jsou lokální oprava `90ca0e78b92a764395ee636aa723f8347bf18d1b`
a ověřený `main` `52af545bfc97396a0001432abc5d58ab7c3663af` po
[#135](https://github.com/p-rum/kgmaker/pull/135), tree
`b765680f96b23fdaa887e4901d9fbbba80e52592`. Osm zdrojových a testových
souborů W02 i deset integračních souborů základu mají přesné bajty svých
rodičů. Manifesty před a po testu jsou shodné, SHA-256
`9b4409a88005ee09ba551072b3c6459aeb2b756b2571696f7daadbcc7561d054`.
README obsahuje návody čtecího reportu i dokladu skutečného testovacího běhu.
Oba vygenerované grafy vycházejí ze společného zdroje a původní semantické
epizody obou rodičů mají samostatné identity.

Použit byl JDK/Javac 21.0.6, připravená distribuce workerů, `PYTHONPATH=src`,
`KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1` a
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.

- Cílený `test_actual_javac_line_ending_change_rechecks_proven_caller`
  má 3 PASS / 0 SKIP za 15,59 s. JUnit SHA-256
  `94e7559db9d990f1227569c9d14491781d9f7f4952634503d4c7303f5f7576e8`.
- Výběr osmi souborů W02/W06/T032 uvedený výše má 147 PASS / 0 SKIP za
  36,04 s. JUnit SHA-256
  `8fd3eecc9d0d9ae0eadd8004f4ede99d7f3250971d6f7310a2814c51d382cf43`.

Čtecí kontrakt reportu, graph/store v1/v2/v3 a postupy dokladu testovacího běhu
mají uvedený rozsah. W02-AC01 je `PARTIAL`. Prvotní sběr compiler evidence pro
CRLF, zápis selektivní invalidace a negativní lookup mají vlastní ověření.
Úplná sada, nezávislé review integrační revize a její GitHub Actions mají při
předání stav `NOT_RUN`. [Inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy),
[stavová matice](../production-analysis-progress.md).

## Přenos po #145 a raw JVM lokátory — kroky 3–5, AC01–AC04

Výchozí head #130 `d3cb64f957f0dd0c1d0bb2f60b6bbd6e7f238dbe` navazuje na ověřený
`main` `1569d5d1f3133360bb0c29d9cedf9b7cd1778ae4`. Po spojení zdrojů tři
skutečné Javac varianty vynechaly Caller.java i Outer.java. Report zároveň
přijal doložené volání ze snapshotu s pozměněným výběrem compiler vstupů pod
stejným raw ID.

`src/kgmaker/graph_provider.py` ověří identitu původního raw capture jednou na
kontext. `compiler_source_digest` ověřuje strukturální inventář a vrací bajtový
otisk pro oba důkazy callera i přesný lokátor cíle. Pro stejný normalizovaný
text report porovná aktuální bajtový otisk s uloženým bajtovým otiskem cíle.
`changed_sources` dál porovnává normalizovaný text a běžná změna textu zachovává
průchod doloženými vazbami při neúplném lokátoru. JSON v1 a graph/store v1–v3
si zachovávají formát. Report používá dříve uloženou generaci a nedělá zápisy.

`test_actual_javac_line_ending_change_rechecks_proven_caller` pokrývá oba směry
LF↔CRLF i oba styly volajícího. Ověřuje nezměněný vstup, textovou změnu, přesné
identity přímého a tranzitivního callera, chybějící a neshodný lokátor a nulovou
mutaci. `test_actual_javac_tampered_capture_cannot_ground_reverse_impact`
ověřuje odmítnutí změněného výběru. Přímý replay uchovaného Javac grafu načetl
jen zadaný Api.java, použil každý uložený pár kontext/cesta jednou a zachoval
zdrojové soubory i graf. Doklad `pr130-after145-read-scope.json`, SHA-256
`714d794831f11c42fec523fed1d8ddcf9d7bdf0150daa29d2c96b992e1bbfad7`.

- RED — 4 FAIL, 7 PASS, 0 SKIP s Javac/JDK 21.0.6 nad spojeným produktem před
  opravou, exit 1 za 55,18 s. JUnit `pr130-after145-native-red.xml`, SHA-256
  `4855e801f61b7ba53c9b729de1dad84903928901bf61b4addc92f8662b0fee43`.
- GREEN — 162 PASS, 0 FAIL, 0 ERROR, 0 SKIP v Cloud Environmentu za 120,55 s.
  Prošly všechny 25 W02 případy včetně čtyř FIFO variant s původním limitem,
  18 W06, 43 T032 a 11 raw JVM případů. Python u T032 dvakrát upozornil na
  `fork()` ve vícevláknovém procesu. JUnit `pr130-after145-strict.xml`, SHA-256
  `1b8e680aa40027f7acf259a6141b5a11b5220319a33a0d81601123f6774b7643`.
  Oba manifesty mají SHA-256
  `8af2ca7b905c8bc0aea515fc6539248b44d95ee3df95d9cc6a71b0b314f61646`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist load -p no:cacheprovider \
    -q --tb=short -ra --junitxml=/workspace/kgmaker-evidence/pr130-after145-strict.xml \
    tests/test_reverse_dependency_index.py tests/test_graph_provider.py tests/test_feature.py \
    tests/test_feature_fixture.py tests/test_flyway.py tests/test_workspace.py \
    tests/test_graph_publication_concurrency.py tests/test_t032_persist_process_review.py \
    tests/test_jvm_raw_source_snapshot.py
  ```

Obnovená sémantická vrstva zachovává 386 jedinečných epizod obou rodičů a
záznam o tomto přenosu. [Návod](../stage-content-cache.md#selektivní-dopad-změn)
a [inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
popisují čtecí kontrakt. W02-AC01 zůstává `PARTIAL`. Publikace selektivní
invalidace, negativní lookupy a cross-workspace vazby mají samostatný rozsah.
Úplná sada, Windows, vzdálené CI a nové nezávislé review jsou při tomto
lokálním předání `NOT_RUN`.

## Oprava po review — kontrola otisků raw JVM capture, kroky 3–5 a AC01–AC04

Výchozí #130 `090ef9fa6dfdd57048d1bb8418f95bfb23890060`, cílový `main`
`1569d5d1f3133360bb0c29d9cedf9b7cd1778ae4`. Nezávislá review reprodukovala
číselnou hodnotu `1e400` v `source_files` skutečného Javac capture.
Python ji načetl jako nekonečno a kanonická serializace přerušila výpočet
identity. Veřejný `impact --evidence-only --format json` selhal výjimkou.

`src/kgmaker/compiler_sources.py` před výpočtem identity ověří hodnoty v
`source_files` i `normalized_source_files` existujícím pravidlem pro SHA-256.
Poškozený kontext se vyřadí z compiler evidence. Čtecí report zachová
výsledky z nezávislého platného kontextu, `changed_sources`, `PARTIAL`
a bajty uloženého grafu. Formát JSON v1 a čtení graph/store v1–v3 zůstávají
kompatibilní. Test při obou variantách zakazuje podprocesy a automatický scan.
Příklad zůstává `kgmaker impact --evidence-only --format json app/src/main/java/Api.java`.
Chování je uvedeno v [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02),
[návodu k výstupu](../stage-content-cache.md#selektivní-dopad-změn),
[inventáři](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavové matici](../production-analysis-progress.md).

Lokální Cloud Environment použil Javac/JDK 21.0.6, připravené JVM workery,
`PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`
a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.

- RED s produktem `090ef9f` — 2 FAIL / 0 SKIP za 38,80 s. V obou mapách
  vyvolal poškozený otisk `ValueError`. JUnit `pr130-090ef9f-retry2-red.xml`,
  SHA-256 `0a42b6bb0895fa3d2f9fe3673cb4af362e21d5135f76d35606084c73563e246a`.
- GREEN — 164 PASS / 0 SKIP za 106,45 s. Prošly obě nové varianty i původní
  kontroly LF↔CRLF, lokátorů, starších schémat, W06 a T032. T032 vypsal dvě
  varování Pythonu o `fork()` ve vícevláknovém procesu. JUnit
  `pr130-090ef9f-retry2-native.xml`, SHA-256
  `bc7965f32111b881804c59ec8a3a1e4a02ca94dbc1f95fe4c3e9bee94e4c2aa5`.
  Shodný manifest zdrojů, testů a nástrojů před a po měl SHA-256
  `fcc13ba6fcc6d0c4710c5bc9261a8f98db771d15d60c2967f0113a9540387ba7`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_reverse_dependency_index.py::test_actual_javac_malformed_capture_digest_is_ignored_in_public_impact
python -m pytest -n 3 --dist load -p no:cacheprovider -q --tb=short -ra \
  tests/test_reverse_dependency_index.py tests/test_graph_provider.py tests/test_feature.py \
  tests/test_feature_fixture.py tests/test_flyway.py tests/test_workspace.py \
  tests/test_graph_publication_concurrency.py tests/test_t032_persist_process_review.py \
  tests/test_jvm_raw_source_snapshot.py
```

W02-AC01 zůstává `PARTIAL`. Publikace selektivní invalidace, negativní
lookupy a cross-workspace vazby mají vlastní rozsah. Úplná sada na nové
revizi, GitHub Actions a opakované nezávislé review mají při lokálním předání
stav `NOT_RUN`.


## Přenos po #154 a #155 — T003-S10-W02, kroky 3–5 a AC01–AC04

Přenos sjednotil změnu `beac7a80991e72a48513bb48f6e5f10d2b3c717b` s
`main` `782ac6ac0287550084e9afadbd6182756fdd2730`. Změny instalátoru,
migrace Excelu a opravené kanonické Kafka identity z #152 byly zachovány.
Report zachovává čtecí kontrakt předchozího kroku. Sémantika zachovala
396 předchozích epizod a přidala záznam integrace.

- PASS — skutečné JDK 21 a oba workery K1/K2, **247 PASS / 0 SKIP**.
  JUnit SHA-256 `41cd0df18c538f5c4daffcbfa1288bb02b277b3c0c178d0feec5dd0c14b85bcd`.
  Shodný manifest před a po a kontroly sémantiky, grafu a diffu. Dvě
  varování Pythonu se týkají `fork()` ve vícevláknovém testu T032.
- PASS — nezávisle **11 PASS / 0 SKIP** na stejném kódu s JDK 21.
  JUnit `0bb2bd2754b429a26eff2c238d577c70e8d5097b1e555fdcd3ba7a11711e6e7c`.
  Testy ověřily čtecí report, nezměněné grafy a kompatibilitu starších formátů.
- FAIL — první standardní běh CPython 3.13 na stejném produktu měl
  **2 573 PASS / 1 337 SKIP / 1 očekávaný strict XFAIL / 1 FAIL**.
  Gradle v izolovaném prostředí neměl rozhraní pro koordinaci lokálního
  zámku. Druhý pokus měl i omezený `PATH` bez Node a skončil čtyřmi FAIL,
  JUnit `c9270877491cd0954d6854a61c1ef45220b1ff8fb223da42bd6900991e0dc40d`.
- PASS — po doplnění nativního prostředí Gradle a Node prošlo **26 PASS,
  3 SKIP** v cíleném opakování modulu T021 a instalovaného offline Gradle
  exportu. Tři volitelné Mermaid testy přeskočily kvůli chybějícím
  závislostem rendereru. Úplná standardní sada v této konfiguraci zatím
  neběžela. GitHub Actions a finální review nové dvojice revizí mají samostatné
  výsledky.

```bash
python -m pytest -p no:cacheprovider -q \
  tests/test_reverse_dependency_index.py tests/test_kafka_bindings.py \
  tests/test_graph_provider.py tests/test_feature.py tests/test_feature_fixture.py \
  tests/test_flyway.py tests/test_workspace.py tests/test_graph_publication_concurrency.py \
  tests/test_t032_persist_process_review.py tests/test_jvm_raw_source_snapshot.py
```

W02-AC01 zůstává `PARTIAL`. Selektivní zápis při invalidaci a negativní
vyhledání vyžadují vlastní implementaci a ověření.

## Přenos po #136 — T003-S10-W02, kroky 4–5 a AC01–AC04

První rodič `98755cd83597fa5191a98bd36ddfd7bacdf2ac30` obsahuje čtecí
report W02 a předchozí ověření. Druhý rodič `5809e84932b1910bfc3f17c72e2a2005283389b1`
přináší runtime import a navigaci z #136. Oba rozsahy mají stejné produktové
a testové soubory jako příslušní rodiče. Sémantická vrstva zachovala všech
408 historických epizod obou rodičů a přidala záznam integrace.

**Krok 4, AC01–AC03.** Cloud Environment, CPython 3.12.14, Temurin
JDK 21.0.6+7, Maven 3.9.9 s lokálně připravenými závislostmi a existující
workery K1/K2. Prošlo **39 testů bez přeskočení**, exit 0. JUnit SHA-256
`acf2d9f92ff2cd278af5ef213a27f2e276d7ca60da115429bfb3fdc009d35a4e`.
Shodné manifesty zdrojů a nástrojů mají SHA-256
`78ff44ae8814eb08699e7c4a2d9bf836999980f8138c4d6c48d67773d8567e2f` a
`96e1d367d39dfaa4ed882d3de71d770337640eb68aa2f64f57713522de214167`.
Výběr ověřil čtecí report, odpovídající compiler důkazy a souběžný runtime
import včetně publikace ověřených hodnot, obnovy výstupu a veřejného
výběru konfigurace Maven.

```bash
runtime=tests/test_runtime_trace_producer.py
python -m pytest -n 2 --dist load -p no:cacheprovider -o tmp_path_retention_policy=failed -q -ra --tb=short \
  tests/test_reverse_dependency_index.py \
  "$runtime::test_runtime_import_retains_same_edge_observations_and_v2_variant_identity" \
  "$runtime::test_runtime_observation_stays_visible_without_creating_static_path_or_cycle" \
  "$runtime::test_runtime_keeps_callable_and_framework_observations_and_legacy_import" \
  "$runtime::test_runtime_import_validates_payload_once_and_rechecks_inputs_per_publication_step" \
  "$runtime::test_real_jdk21_v2_import_detaches_identity_before_publication" \
  "$runtime::test_real_jdk21_v2_import_publishes_only_admitted_values" \
  "$runtime::test_real_jdk21_runtime_import_rejects_source_edit_after_validation" \
  "$runtime::test_actual_maven_public_runtime_uses_selected_build_configuration" \
  tests/test_graph_publication_concurrency.py::test_runtime_import_cannot_overwrite_generation_published_during_validation
python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=failed -q -ra --tb=short \
  tests/test_graph_provider.py tests/test_workspace.py tests/test_feature.py \
  tests/test_feature_fixture.py tests/test_flyway.py
```

Druhý příkaz v CPython 3.13.18 má **65 PASS / 0 SKIP**, exit 0, JUnit
SHA-256 `b7acc3271239f548878713b25a1de748df34834cd108051454b61ffae7ef529b`.
Úplná standardní sada na této dvojici, Windows a GitHub Actions mají při
lokálním předání stav `NOT_RUN`. Předchozí chyby prostředí Gradle a Node a
cílená obnova s 26 PASS a třemi volitelnými Mermaid SKIP mají svůj záznam
výše.

**Krok 5, AC04.** [Acceptance inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) uvádějí aktuální
základ. [CLI příklady](../stage-content-cache.md#selektivní-dopad-změn),
kontrakt reportu a graph/store v1/v2/v3 se tímto přenosem nemění. W02-AC01
zůstává `PARTIAL`. Zápis selektivní invalidace a negativní vyhledání čekají
na samostatné ověření.

## Přenos po #151 — T003-S10-W02, kroky 4–5 a AC01–AC04

První rodič `4ef6471381aac892f6d711cb51754a373122fe7f` obsahuje společný
strom reverse dependency reportu a runtime navigace. Druhý rodič
`b04d064a6147436adc751f5fffa4a219b8f8c16e` přináší shodné zdrojové otisky
sešitů v pracovních packetech a ve scanu. Produktové a testové soubory
obou změn se shodují s příslušnými rodiči. Sémantická vrstva zachovala
412 historických epizod a přidala záznam přenosu.

**Krok 4, AC01–AC03.** Výběr z předchozí sekce a obě regrese sešitů
`WorkflowContextTests.test_packet_freshness_uses_same_workbook_inputs_as_scan`
a `WorkflowContextTests.test_packet_freshness_handles_unparseable_workbook_edit`
mají **41 PASS / 0 SKIP**, exit 0, CPython 3.12.14, Temurin JDK 21.0.6+7
a skutečný Maven 3.9.9. JUnit SHA-256
`6431f10b8ca62ecdf8ae20044a2ec711bec18468fc395b1c2eb0678a25fa90cd`.

```bash
python -m pytest -n 2 --dist load -p no:cacheprovider -o tmp_path_retention_policy=failed -q -ra --tb=short \
  tests/test_workflow.py::WorkflowContextTests::test_packet_freshness_uses_same_workbook_inputs_as_scan \
  tests/test_workflow.py::WorkflowContextTests::test_packet_freshness_handles_unparseable_workbook_edit
python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=failed -q -ra --tb=short
```

Druhý příkaz je úplná standardní sada s CPythonem 3.13.18, Gradle 8.13
a připravenými Maven závislostmi v Cloud Environment. Zahrnuje
**2 579 PASS / 1 343 SKIP / 1 očekávaný strict XFAIL**, exit 0.
JUnit SHA-256 `aac2f2c0aa7466c0534b2f586e0c8a30bb1d401845e088d930c9ebf62e04eec0`.
Archivovaný strom `cb3ea34bc94733c7d11ad219d388ea9fab59fbe7`
a výsledný strom mají shodný obsah `src`, `tests`, `tooling` a `workers`.
Shodný manifest před a po obou bězích má SHA-256
`fb611ee9534bfecadc223baf1ab51f260ec9587717637d58ed32b6cb8dbd9e42`.
Záznamy předchozí chyby prostředí Gradle a cílené obnovy s 26 PASS
a třemi volitelnými Mermaid SKIP jsou výše. Windows a GitHub Actions
mají při lokálním předání stav `NOT_RUN`.

**Krok 5, AC04.** [Inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) uvádějí aktuální
základ. [Rozsah čtecího příkazu](../stage-content-cache.md#selektivní-dopad-změn)
a podpora graph/store v1/v2/v3 zůstávají zachované. W02-AC01 zůstává
`PARTIAL`. Zápis selektivní invalidace a negativní vyhledání mají
samostatný rozsah.

## Přenos po #156 — T003-S10-W02, kroky 4–5 a AC01–AC04

První rodič `c3190576f348d954771ac45b143b0a516c5132b0` obsahuje ověřený čtecí
report W02. Druhý rodič `3a6b97fc9c44941e68bb390772a5eb13906bf1ff` přináší
T055 pro migraci sešitů a instalační skill. Devět produktových a testových
souborů #130 a sedm z #156 je ve společném stromu bajtově shodných se
svými rodiči. Sémantická vrstva zachovala 413 historických epizod a
přidala záznam tohoto přenosu.

**Krok 4, AC01–AC03.** Nativní výběr z předchozího přenosu rozšířený
o `tests/test_skills.py`, `tests/test_xlsx_references.py` a
`tests/test_binary_xls.py` má **124 PASS / 0 SKIP**, exit 0.
Cloud Environment použil CPython 3.12.14, Temurin JDK 21.0.6+7 a
skutečný Maven 3.9.9, včetně veřejného výběru konfigurace runtime.
Výběr pokrývá čtecí report se skutečným Javacem, workbook freshness,
lokátory Excelu a paritu instalovaného skillu. JUnit SHA-256
`33161b2a201522717cac322ad39a25b3f6d79c783ac8a7e0a91d8a35debedbf9`.

```bash
python -m pytest -p no:cacheprovider -o tmp_path_retention_policy=failed -q -ra --tb=short
```

Úplná standardní sada s CPythonem 3.13.18, Gradle 8.13 a připravenými
Maven závislostmi má **2 585 PASS / 1 345 SKIP / 1 očekávaný strict XFAIL**,
exit 0. JUnit SHA-256 `d0c3650eab54bb5be1546575ab78d24d97d916a8db66937389476e01b49e908b`.
Archiv `3cb7432c51ff580c2e2e6ac4e3ae6f5894b09886` a
finální strom mají shodný obsah `src`, `tests`, `tooling` a `workers`.
Manifest SHA-256 před a po obou bězích je
`75dcefffbf947785b43f0671c613b9d19b87c88290f8ce4b084b015b9a3333b0`.
Předchozí neúspěšné pokusy se zámkem Gradle a následný cílený výběr
26 PASS, 3 volitelné Mermaid SKIP jsou vedeny ve starší sekci.

Nový lokální build Excel workeru má stav `BLOCKED`. Připravené
repozitáře neobsahovaly POI 6 a přístup Maven Central v izolovaném běhu
skončil chybou `Network is unreachable` při načtení Maven pluginu
(exit 1, SHA-256 logu `ed4074f4f92b3bba854ff08f1dfc895337fc65232d0c33cd689a586fa25d3d9e`).
[Ověření původního T055](172_automateExcelMigration.md) platí pro jeho
nezměněné soubory. Samostatné nativní ověření Excel workeru, Windows
a GitHub Actions se pro toto spojení lokálně nedokončilo.

**Krok 5, AC04.** [Inventář](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [stavová matice](../production-analysis-progress.md) uvádějí aktuální
základ. Veřejný [CLI kontrakt](../stage-content-cache.md#selektivní-dopad-změn)
a formáty graph/store v1/v2/v3 zůstávají kompatibilní. W02-AC01 je
`PARTIAL`. Selektivní zápis a negativní vyhledání mají vlastní rozsah.

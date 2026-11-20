# První mutační workspace a ruční oracle T047-S01

Zadání [T047](../tasks/47_addReliableIncrementalContext.md), krok T047-S01 /
T047-AC01. Lokální výchozí SHA `465b121992aad50c2885acef0fd038531a31293a`.
První lokální checkpoint měl dodání IN_PROGRESS, ověření PARTIAL.

## T047-S01 / T047-AC01 — reprodukční corpus

Dřívější testy workspace, Kafka a Flyway pokrývaly jednotlivé vstupy. Nová
[fixture](../../fixtures/incremental-integrity/workspace_fixture.py) je skládá do
dvou repozitářů s Kotlin API, samostatným callerem, dvěma overloady a nezávislým
Kotlin modulem. Frontend obsahuje TypeScript klienta, komponentu a explicitní
API kontrakt. Kafka témata, release mapping a Flyway stream mají oddělené
zdrojové záznamy. Zdrojové soubory fixture se sestaví v izolovaném pytest workspace.

[Ruční oracle](../../fixtures/incremental-integrity/oracle.json) kontroluje
pozitivní cestu DTO → endpoint, očekávané overloady a hranici do frontendu bez
compiler evidence. Kafka deklarace mají bez prokázaného členství modulů UNKNOWN.
Explicitní release map vrací PARTIAL s `RELEASE_MANIFEST_UNAVAILABLE`.
Flyway evidence je migration-derived. Test nic nenavozuje v běžící databázi.

Devět mutací ověřuje komentář, změnu těla, přidání symbolu, přesun a smazání
souboru, změnu verze kontraktu, Kafka topic, Flyway skript a změnu tsconfig.
Každá vrací hash výsledného souborového stromu a přesné cesty změny. Reset
obnoví stejné bytes, opakovaný běh má stejné výsledky. Test oracle odmítá
duplicitní overload. Současné source ID se po posunu deklarace mění, kontrola
T047-S02 je proto explicitně strict XFAIL.

Příklad ověření `python -m pytest -p no:cacheprovider -q --tb=short tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py`
— 100 PASS, 2 SKIP, 1 XFAIL. Původní první běh 99 PASS, 2 SKIP, 1 XFAIL
a 1 FAIL odhalil předpoklad pozitivní Kafka hrany bez scope proof. Oracle byl
opraven podle existujícího capability kontraktu.
`git diff --check` PASS. Skutečný compiler, Windows, úplná mutační matice,
inkrementální ekvivalence a publikované PR review NOT_RUN.

Aktualizovány [README](../../README.md), [dokumentace fixture](../../fixtures/incremental-integrity/README.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).
Veřejné CLI, graf, worker formáty a init nemají změnu. Zbývá doložit zbývající
varianty a provést review. T047-S02 až S06 na tuto scoped fixture navazují.

## T047-S01 / T047-AC01 — skutečná cold mutace add, 2026-11-20

Výchozí HEAD [#121](https://github.com/p-rum/kgmaker/pull/121)
`6c210b5b58624234c6b0f91a301628df76c49e57`. Změna je jen v
[testu](../../tests/test_incremental_equivalence.py) a jeho dokumentaci.
Explicitní `inspect_jvm(..., module="api", publish=False)` před a po mutaci
`Added.kt` porovná skutečný Kotlin K1 a K2 kontext. Caller má stejné bajty.
Výchozí `missingScore()` je UNRESOLVED bez kandidátů. Poté je
SYMBOL_RESOLVED v novém kontextu na `fixture.AddedKt.missingScore()I` a
`score(2)` stále vybírá `score(I)I`. Druhý overload zůstává samostatný.
Test sleduje konkrétní kontext vybraný voláním. Graf může současně obsahovat
další kontexty, což odhalil první běh fixture. Vstupní projekt se nemění jinak
než plánovanou mutací a nevzniká publikovaný index.

- `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 python -m pytest -p no:cacheprovider -q --tb=short tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py`
  — 104 PASS, 0 SKIP, 1 strict XFAIL, 24.31 s. JDK21, Kotlin 2.1.10,
  reálné K1/K2. Během vývoje dvě FAIL ukázaly nadbytečný požadavek na jediný
  kontext a další FAIL odhalil neúplná metadata nesouvisejícího K1 symbolu.
- `git diff --check` — PASS. Plný T047 inkrementální replay, pozitivní Kafka
  a release varianty, zbytek compiler mutací, úplná sada a externí CI jsou
  NOT_RUN. Stávající command API a graph schéma jsou kompatibilní.

## T047-S01 / T047-AC01 — přenos na main po T052, 2026-11-20

Draft [#121](https://github.com/p-rum/kgmaker/pull/121) z head
`bbfa92ce659dfbac4245e5f795df3ada00fb53ea` byl připraven nad `main`
`8ff2529ffb50b42ed2209d97478ea3e4cbf46042` s Git tree
`c869302cdc2a7d9982d64058b6267ae603382e06`. Soubory v
[corpus](../../fixtures/incremental-integrity/) a
[regresní test](../../tests/test_incremental_equivalence.py) zůstaly bajtově
shodné. Přeneseny byly související části [README](../../README.md),
[acceptance](../acceptance-inventory.md) a [stavové matice](../production-analysis-progress.md).
Jde o testy a jejich návod. Kontrakt CLI, init, grafové schéma a registry
zadání zůstávají kompatibilní.

- PASS — `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra --basetemp .kgmaker/workflow/pytest-t047-after-t052 tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py`.
  JDK 21.0.13.1, Kotlin 2.1.10, skutečný K1 i K2. Výsledek 104 PASS,
  0 SKIP a 1 strict XFAIL v `test_comment_does_not_change_logical_identity`
  za 24.82 s. XFAIL dokumentuje závislost ID na řádku v T047-S02.
- PASS — `git diff --check` při přenosu dokumentace, testů a fixture.
- NOT_RUN — úplná projektová sada nad tímto kandidátem, nové exact-pair review,
  GitHub Actions, širší compiler a pozitivní Kafka/release matice, inkrementální
  ekvivalence. T047-AC01 zůstává PARTIAL.

## T047-S01 / T047-R01 a T047-AC01 — source-only mezistavy, 2026-11-20

Výchozí head [#121](https://github.com/p-rum/kgmaker/pull/121)
`856a16c1d2aa751d01fb5952ffdf9589101ffae9`, tree
`2f01e280cfc8879a2ad3017ad004be77b417b774`. Dřívější replay ověřoval hash
stromu po každé mutaci a graf až po celé sekvenci. Následné smazání tak
mohlo zakrýt chybnou deklaraci bezprostředně po přesunu.

[Regrese](../../tests/test_incremental_equivalence.py) kontroluje snapshot po
každé z devíti stávajících mutací. Porovnává přesné změny položek `graph.files`
a ruční predikce z [oracle](../../fixtures/incremental-integrity/oracle.json).
Příklad po `add` je `missingScore` v `Added.kt` a po `move` oba původní
`score` overloady výhradně v `Renamed.kt`. Po `delete` overloady chybějí,
nezměněný caller a přidaná deklarace zůstávají. SOURCE_ONLY snapshot nevytvoří
compiler call sites. Změněný Kafka topic má stále `UNKNOWN` s
`CONFIG_SCOPE_UNPROVEN`. Replayer přidá až po V11 `table:public.extra` v
konfigurovaném Flyway streamu jako `MIGRATION_DERIVED` s `UNASSESSED`
dostupností dat. Změna verze kontraktu a `tsconfig` se ověřuje na hashi
příslušného souboru. Produkční zdroj, veřejné CLI, grafové schéma, init a
pracovní tok se nemění. Aktualizovány [README](../../README.md),
[návod fixture](../../fixtures/incremental-integrity/README.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).

- RED s lokálním diagnostickým pytest pluginem `alter_overload_at_move`.
  Plugin hned po přesunu v izolovaném testovacím workspace mění signaturu
  `score(value: Int)` na `score(value: Long)` a aktualizuje checksum.
  Původní `test_mutation_replay_and_reset` v přesném výchozím tree s touto
  záměnou prošel. Se stejnou záměnou měl `python -m pytest -p no:cacheprovider -p alter_overload_at_move -q --tb=short tests/test_incremental_equivalence.py -k 'source_only_mutation_states or mutation_replay_and_reset'`
  1 očekávaný FAIL v nové kontrole ve stavu `move` a 1 PASS v reset/replay.
  Jde o záměrně poškozenou fixture pro ověření detekce, plugin není součástí PR.
- PASS — `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra --basetemp .kgmaker/workflow/pytest-intermediate-strict tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py`.
  105 PASS, 0 SKIP a 1 strict XFAIL za 26.83 s se skutečným JDK 21.0.13.1 a
  Kotlin 2.1.10 K1/K2. XFAIL zůstává dokladem potíže T047-S02 s identitou
  při posunu deklarace.
- PASS — `git diff --check`, `git diff --cached --check`, `kgmaker semantic update`,
  `kgmaker semantic apply`, `kgmaker semantic validate`, `kgmaker memory capture`,
  `kgmaker scan`, `kgmaker status` a `kgmaker check` v izolovaném kandidátu.
- NOT_RUN — úplná projektová sada, GitHub Actions, externí review této revize,
  pozitivní Kafka a release binding, zbývající compiler mutace a inkrementální
  ekvivalence. Pozitivní Kafka binding vyžaduje prokázaný scope konfigurace.
  Release binding vyžaduje bajtovou shodu zachyceného artefaktu s compiler classpath.
  T047-AC01 zůstává PARTIAL.

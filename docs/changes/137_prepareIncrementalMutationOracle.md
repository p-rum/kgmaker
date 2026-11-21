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

## T047-S01 / T047-R01 a T047-AC01 — Kafka a Kotlin → TypeScript, 2026-11-20

Lokální kandidát pro [#121](https://github.com/p-rum/kgmaker/pull/121) vychází
z jeho draft headu `e57369521f91ab5d81456fe7516f10237b4b569e` a z cílového
`main` `17e9e7368e6cc2d6550983c3039eb39debd65424`, tree
`dfb0a247ec329196190a3db182b5d1e8c549b3db`. Stanovuje ruční očekávání pro dva
protipříklady k předchozím mezerám, aby samotná přítomnost deklarací
nepostačovala pro kladný výsledek.

- Kafka oracle explicitně klasifikuje konfiguraci `api` a `independent` pod
  dva compiler kontexty profilu `blue`. Před mutací `orders-blue` prokáže
  jednu hranu `kafka_binding_match` pro přesný pár, cluster, hash kontraktu a
  release. Po změně topicu konzumenta na `isolated` znovu zachytí compiler
  evidence obou modulů v čistém indexu. Obě vazby zůstávají RESOLVED a jejich match
  zmizí. Během vývoje první pokus se starým indexem dostal STALE v obou
  variantách. Cold oracle proto pracuje výhradně s novou generací.
- BE–FE oracle používá skutečný compiler field `ExposureOutput.decline:D`,
  cestu `GET /exposure` a typovaného klienta z fixture. Přesná cesta je
  `serialized_as`, `maps_to`, `displayed_in`. Projekce na stránce odkazuje
  na deklaraci `decline` a přesný hash souboru klienta. Všechny hrany zachovají
  dostupnost UNKNOWN. Doklad klienta má důvěru `LOCAL_DECLARED`, release `1`
  a přesné hashe OpenAPI a klienta. Změna OpenAPI na release `2` současně
  změní hash souboru. Při této kombinované změně stará provenance propadne
  na `VALUE_FLOW_GENERATION_OR_RELEASE_UNKNOWN`. Kontrola sleduje všechny
  příchozí compiler hrany `serialized_as` a odchozí `maps_to` daného endpointu
  bez ohledu na ID druhého konce. SOURCE_ONLY hrany jsou mimo tuto kontrolu.
  Jde o statický doklad hran ze zdroje. Nasazení a běh Spring controlleru
  zde nejsou ověřené.

Upraveny [testy](../../tests/test_incremental_equivalence.py),
[oracle](../../fixtures/incremental-integrity/oracle.json) a
[fixture builder](../../fixtures/incremental-integrity/workspace_fixture.py).
[README](../../README.md), [návod fixture](../../fixtures/incremental-integrity/README.md),
[inventář acceptance](../acceptance-inventory.md) a
[stavová matice](../production-analysis-progress.md) odkazují na dodaný rozsah.
Runtime, CLI, init, registr zadání ani veřejná schémata se nemění. Stávající
[kontrakt BE–FE](../backend-frontend-value-flow.md) zůstává stejný. Kafka
transport, aktivace listeneru a dostupnost dat nemají nový runtime důkaz.

- PASS — samostatná pozitivní a negativní Kafka oracle, 2 PASS s reálným K1/K2
  za 36,39 s. Příkaz `python -m pytest -p no:cacheprovider -q --tb=short tests/test_incremental_equivalence.py -k kafka`.
- PASS — samostatná BE–FE oracle, 2 PASS s reálným K1/K2 a TypeScript 5.7.3
  za 21,54 s před dodatečným zpřísněním důkazu. Příkaz
  `python -m pytest -p no:cacheprovider -q --tb=short tests/test_incremental_equivalence.py -k typescript`.
- PASS — `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra --basetemp .kgmaker/workflow/pytest-t047-s01-final tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py tests/test_cross_repo_artifacts.py`.
  127 PASS, 0 SKIP a 1 strict XFAIL za 89,62 s. JDK 21.0.13.1, Kotlin
  2.1.10 K1/K2, Node 22.22.1 a TypeScript 5.7.3. JVM zdroj a TypeScript
  worker soubory odpovídají připraveným distribucím. Před finálním během dvě
  FAIL odhalily souběh SOURCE_ONLY a compiler hran `maps_to`. Oracle vybírá
  jedinou přesnou `FRAMEWORK_DERIVED` hranu z příslušného kontextu.
- Graf a diff — `kgmaker semantic update --base HEAD`, `kgmaker semantic apply`,
  `kgmaker semantic validate`, `kgmaker memory capture --base HEAD`,
  `kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --check`.
  Platný README koncept a jeho čtyři vazby zůstaly zachované s aktuálním hashem.
- NOT_RUN — externí review této revize, úplná projektová sada a GitHub Actions.
  JVM artefakt `supplies_classpath` zůstává PARTIAL při absenci manifestu.
  Pozitivní artefakt vyžaduje skutečný execution-bound output a shodný soubor
  v aktuálním JVM classpath kontextu konzumenta. TypeScript takový classpath
  nevystavuje. Plný §7 corpus a inkrementální ekvivalence zůstávají otevřené.

## T047-S01 / T047-R01 a T047-AC01 — nálezy review BE–FE oracle, 2026-11-20

Výchozí lokální tree `4da4a89822d58ec111a2b21c2e35ff985d75894d` nad
`main` `17e9e7368e6cc2d6550983c3039eb39debd65424`. Předchozí negativní
assertion v [testu](../../tests/test_incremental_equivalence.py) připouštěla
chybný `maps_to` k novému ID. Kontrola nyní zakáže compiler `maps_to` z
endpointu a `serialized_as` do endpointu pro libovolný druhý konec. Legitimní
SOURCE_ONLY hrany zůstávají dostupné. [Oracle](../../fixtures/incremental-integrity/oracle.json)
očekává release `2` a test ověřuje i změnu hashe. Kladná část testu ověřuje
occurrence v `src/page.tsx`, její odkaz na compiler symbol deklarovaný v
`generated/exposure.ts` a hash klientského zdroje. Návod popisuje zachycení
compiler evidence v čistém indexu. Produkční kód, CLI a schémata nemají dopad.

- RED — lokální pytest plugin `inject_retargeted_contract` vložil stale
  `FRAMEWORK_DERIVED maps_to` k jinému ID klienta. Předchozí predikát vloženou
  hranu propustil. Nový test K1 dal 1 očekávaný FAIL na `stale_contract_edges`
  za 9,49 s při `python -m pytest -p no:cacheprovider -p inject_retargeted_contract -q --tb=short tests/test_incremental_equivalence.py -k 'typescript and k1'`.
  Diagnostický plugin je lokální a není součástí PR.
- PASS — aktualizovaná negativní kontrola a okolní sada v
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short -ra --basetemp .kgmaker/workflow/pytest-t047-s01-review tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py tests/test_cross_repo_artifacts.py`.
  127 PASS, 0 SKIP a 1 strict XFAIL za 92,99 s se skutečnými K1/K2 a TypeScript.
- PASS — finální změněná BE–FE varianta s kontrolou deklarace, 2 PASS, 0 SKIP
  a 9 DESELECTED za 14,98 s. Stejné prostředí a `python -m pytest -p no:cacheprovider -q --tb=short -ra --basetemp .kgmaker/workflow/pytest-t047-s01-review-client tests/test_incremental_equivalence.py -k typescript`.
- PASS — `kgmaker semantic update --base HEAD`, `kgmaker semantic validate`,
  `kgmaker memory capture --base HEAD`, `kgmaker scan`, `kgmaker status`,
  `kgmaker check`, `git diff --check` a `git diff --cached --check`.
  Review oprava nezavádí nové ruční sémantické vazby.
- NOT_RUN — nová úplná projektová sada a GitHub Actions. T047-AC01 zůstává
  PARTIAL kvůli otevřenému artefaktovému mapování a širší mutační matici.

## T047-S01 / T047-R01 a T047-AC01 — skutečný JVM release artefakt, 2026-11-21

Výchozí [draft #121](https://github.com/p-rum/kgmaker/pull/121) měl head
`7ed11dae00e966ae814b5f1caf4f7da2b7f9d773` a tree
`33eb10b309b0273ce40798dcea23d44d59fb7ebd`. Přenos vychází z `main`
`fad4fc63c76f0f9ef5a1a292e279d1269bd84540`, tree
`999b5ef61989bf91ce3df58e4d3bcc84c074eb31`. Záznam sloučeného T021 je
převzat z cílové větve. Workflow ponechalo předchozí doklady s jejich původní
vazbou, odmítlo použít zastaralý test v `review/1` a výslovný retry přešel do
`implement/2`.

[Test](../../tests/test_incremental_equivalence.py) znovu používá původní dva
checkouty. Explicitní offline Gradle build zkompiluje `ExposureContract` a
dodá JAR i skutečný execution-bound `BuildManifest`. Připravený JVM worker
v samostatném modulu `release-verifier` uvnitř frontendového checkoutu
rozliší volání `fixture.release.ExposureContract.decline()D` s tímto JARem
na classpath. Workspace projde ruční oracle jediné hrany `supplies_classpath`
s `CONTENT_HASH_MATCH_V1`, oběma vybranými kontexty a přesným hashem. Chybný
selektor skončí `RELEASE_OUTPUT_HASH_MISMATCH`. Po změně bajtů JARu skončí
dřívější compiler kontext `RELEASE_CONSUMER_CONTEXT_STALE`. Oba negativní
scénáře mají `PARTIAL` bez hrany a snapshot nemění checkout. Variantě
SOURCE_ONLY stále schází build manifest. JVM důkaz je doplňkem S01 a
TypeScript evidence používá svůj stávající kontrakt bez JVM classpath.

Upraveny [README](../../README.md), [návod fixture](../../fixtures/incremental-integrity/README.md),
[inventář acceptance](../acceptance-inventory.md) a [stavová matice](../production-analysis-progress.md).
Produktový kód, CLI příznaky, registry, veřejná schémata a init nemají dopad.
Úplná projektová sada a nové externí review této revize jsou NOT_RUN.
Celá matice §7 a inkrementální ekvivalence zůstávají otevřené.

- PASS — 128 PASS, 0 SKIP a 1 strict XFAIL za 91,26 s na skutečném
  JDK 21.0.13.1, Gradle 8.13, Kotlin 2.1.10 K1/K2, Node 22.22.1 a
  TypeScript 5.7.3. Známý XFAIL je T047-S02 identita po posunu deklarace.
  SHA-256 producer JARu `2a6d4bea507112e41b339905f44b489e913f1e9015ad4f0f6ef96d893c563e9a`
  se shoduje s prvním scratch ověřením. Offline Gradle potřebuje v tomto
  prostředí přístup k lokálnímu socketu pro zámky. Příkaz:

  ```bash
  KGMAKER_TEST_GRADLE=/tmp/gradle-8.13/bin/gradle \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONPATH=src \
  python -m pytest -p no:cacheprovider -q --tb=short -ra \
    --basetemp .kgmaker/workflow/pytest-t047-fad4fc6 \
    tests/test_incremental_equivalence.py tests/test_workspace.py \
    tests/test_kafka_bindings.py tests/test_cross_repo_artifacts.py
  ```

  Použito `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`, stejný `bin`
  první v `PATH` a samostatná lokální `GRADLE_USER_HOME`.
- PASS — `kgmaker semantic update --base HEAD`, `kgmaker semantic apply`,
  `kgmaker memory capture --base HEAD`, `kgmaker semantic validate`,
  `kgmaker scan`, `kgmaker status`, `kgmaker check`, `git diff --check` a
  `git diff --cached --check`. Zachovány doklady a ruční sémantika T021 v main.

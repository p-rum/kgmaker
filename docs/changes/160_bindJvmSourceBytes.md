# Přesné bajty vybraných JVM zdrojů

T003-S02 / T003-AC02, capture a offline kontrola compiler kontextu. Evidence
pro Criteria patří do ověřeného výběru T003-S06-W07, cache metadata do
T003-S10-W01. Výchozí `main` `34591e2f45814838dd8b21390cdc43c84530f648`.

## T003-S02 / AC02 — zachycení a ověření

Před opravou odmítal Javac scénář s concrete return nebo void deklarací v
CRLF souboru publikaci s `INVALID_PROTOCOL`. Abstract deklarace končila
`STALE_INDEX` nad stejnými bajty. Kontext porovnával normalizovaný SHA-256
s raw SHA-256 v compiler evidence.

[Scanner](../../src/kgmaker/scanner.py) předá rozdílné raw otisky z téhož
ověřeného čtení do čerstvé [JVM inspekce](../../src/kgmaker/inspection.py).
`selected-source-set-raw-1` ukládá selected raw `source_files` a normalizovanou
projekci pro odlišné soubory. Lokální `graph.files` nese strukturální
normalizovaný text. [Provider](../../src/kgmaker/graph_provider.py) ověřuje obě mapy a
obsahovou vazbu JPA XML. [Workspace](../../src/kgmaker/workspace.py) kvalifikuje
oba klíče a [výběr kontextu](../../src/kgmaker/views.py) je ověřuje vůči kořenu
vybraného repozitáře. Federovaný inventář souborů používá raw otisk a evidence
jej přijímá pro shodný repo-kvalifikovaný kontext a zdroj. Existující reader rozpoznává starší JVM snapshoty a
varianty graph/store v1–v3. TypeScript používá svůj verzovaný discovery snapshot.

### Souřadnice Kotlin vstupů

Nezávislý Javac/Kotlin probe zjistil, že K1 a K2 počítají souřadnice PSI z
normalizovaného textu. Proti raw CRLF se proto rozsah skutečného `target(local)`
četl jako `return target`. Javac oprava přijímá pouze Kotlin vstupy se shodnými
bajtovými a normalizovanými otisky. Vybraný Kotlin soubor s odlišnými otisky
inspekce odmítne před operací `analyze` a offline replay odmítne jeho uložený
kontext. Hranici určuje seznam `compiler_inputs`. Ostatní Kotlin soubory ze
stejného source setu zůstanou vstupy čerstvosti i s CRLF.

Změna LF na CRLF vyvolá při offline přehrání stav `STALE`. V příkladu
`kgmaker inspect code --root ./service --module app --source-set main` nová
explicitní inspekce váže výsledek na nový raw snapshot. Detaily příkazu a
hranice ověřených variant jsou v [README](../../README.md#compiler-lifecycle),
[compiler inspection](../compiler-inspection.md#jvm-source-byte-fingerprints),
[stavové matici](../production-analysis-progress.md) a [inventáři](../acceptance-inventory.md).

## T003-S06-W07 a T003-S10-W01 — navazující důkazy

Při konstrukci [local operation](../../src/kgmaker/local_operations.py) a
[Criteria](../../src/kgmaker/criteria_queries.py) se ověří raw důkaz i odpovídající
strukturální otisk. Evidence má konkrétní kontext, soubor a rozsah. Ověřený
Criteria dotaz obsahuje compiler-grounded `filters_by` pro odpovídající
entitu. [Cache](../../src/kgmaker/extraction_cache.py) zachovává režim
`BYPASS` a ukládá přesný klíč snapshotu. [Cache kontrakt](../stage-content-cache.md).

## Provedené kontroly

- RED — proti archivovanému Python zdroji přesného `34591e2` a skutečnému
  Javac/JDK 21.0.6 selhaly všechny tři CRLF varianty. Dvě vrátily
  `INVALID_PROTOCOL`, jedna `STALE_INDEX`. Pytest vrátil 1. JUnit SHA-256
  `c446faff97dad011842ca00fdefe3cfe1ad99528ecc5a64b300e6e63ec47da7c`.

  ```bash
  PYTHONPATH=/workspace/kgmaker-evidence/jvm-raw-base.rqeozB/src \
    /workspace/kgmaker-venv/bin/python -m pytest \
    -o pythonpath=/workspace/kgmaker-evidence/jvm-raw-base.rqeozB/src \
    -p no:cacheprovider -q --tb=short \
    --junitxml=/workspace/kgmaker-evidence/jvm-raw-source-red.xml \
    tests/test_jvm_raw_source_snapshot.py -k crlf
  ```

- PASS — cíleně 8 PASS, 0 SKIP a 45 DESELECTED na stejném Javacu
  a připraveném Kotlinu 2.1.10. Zahrnuje skutečný Criteria filtr, stale
  konzumenta po LF/CRLF změně, neplatnou raw i normalizovanou projekci
  a odmítnutí nesouhlasícího worker otisku beze změny generace. JUnit SHA-256
  `2deef55e21ad4f62ed746dbab9085308afcd20caab9611ecd459904cdd1e4ca0`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short \
    --junitxml=/workspace/kgmaker-evidence/jvm-raw-source-final-focus.xml \
    tests/test_jvm_raw_source_snapshot.py tests/test_criteria_queries.py \
    -k 'jvm_raw_source_snapshot or raw_provenance_in_crlf_source'
  ```

- PASS — 3 PASS, 0 SKIP a 7 DESELECTED s konečným Kotlin guardem a
  kvalifikovanou workspace projekcí. K1 i K2 prokážou skutečný smíšený
  kontext Javac CRLF a vybraného Kotlin LF se shodnými rozsahy. Nevybraný
  Kotlin CRLF zůstane ve vstupním inventáři. Výběr Kotlin CRLF odmítne
  skutečná inspekce i offline replay. Workspace výběr vrátí `CURRENT` a
  zachová poslední generaci. JUnit SHA-256
  `79ffd1c62c9316ac026d73fd75933ae0dedb6d5b0bacf97e03dfd5c4c2e259fd`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short \
    --junitxml=/workspace/kgmaker-evidence/jvm-raw-scope-focus.xml \
    tests/test_jvm_raw_source_snapshot.py -k 'selected_kotlin_coordinate or workspace_qualified'
  ```

  V Cloud Environmentu běžely skutečné workery s JDK/Javac 21.0.6,
  Kotlinem 2.1.10, Node 24.22.3 a TypeScriptem 5.7.3. Lokální
  `KGMAKER_WORKERS_HOME` mířilo na `workers` aktuálního worktree a
  `KGMAKER_TEST_MAVEN_REPOSITORY` na připravený lokální Maven repozitář.
  Běhy vyžadovaly `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1` pro
  smíšenou sadu, `JAVA_TOOL_OPTIONS=-XX:-UsePerfData` a `PYTHONPATH=src`.

- PASS — konečná striktní sada měla 300 PASS, 0 SKIP a 0 selhání za
  363,21 s. Pytest i vytvoření a porovnání obou manifestů vrátily kód 0.
  JUnit SHA-256 `42ab80c44f96ba3ab496d6efec8d08a8a93bbcd449a3731c525bc2c6a5dc702d`.
  Shodné manifesty zahrnují zdroje, testy, fixture, JVM JARy a launchery.
  SHA-256 `b13e72a403d011fa5e49a35daeb2241f92788532727899047ad03ca8e2c94fee`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist loadfile \
    -p no:cacheprovider -q --tb=short -ra \
    --basetemp /workspace/kgmaker-evidence/jvm-raw-source-guarded-strict-pytest \
    --junitxml=/workspace/kgmaker-evidence/jvm-raw-source-guarded-strict.xml \
    tests/test_jvm_raw_source_snapshot.py tests/test_criteria_queries.py \
    tests/test_local_operation_proofs.py tests/test_orm_xml_overrides.py \
    tests/test_graph_provider.py tests/test_stage_content_cache.py \
    tests/test_stage_content_cache_actual.py tests/test_workspace.py \
    tests/test_context_roles.py tests/test_t006_select_service_contexts.py \
    tests/test_tsconfig_freshness.py
  ```

- Strukturu ověřují `kgmaker semantic update --base HEAD`,
  `kgmaker semantic apply`, `kgmaker semantic validate`,
  `kgmaker memory capture --base HEAD`, `kgmaker scan`,
  `kgmaker status`, `kgmaker check` a `git diff --cached --check`.
  Izolovaný worktree vznikl bez lokálního indexu. Dřívější zdrojový graf
  pro `memory capture` obnovil `kgmaker scan --no-docs` z archivu přesného
  výchozího `34591e2` s Python kódem této revize.
- NOT_RUN — úplná projektová pytest sada, Windows a vzdálená CI pro tuto revizi.

Ověření širších CRLF projekcí, parity Kotlin/Java a selektivní invalidace
W02-AC01 zůstává otevřené. Výkonový warm HIT má samostatnou acceptance.

## T003-S02 / AC02 — přenos na main po #121

Lokální revize opravy `4af8f12818fbb0a6d99b2e645060235b847cefaf` se
spojuje s `main` `b3bbba43304f499f96950ea4ecc2a2467919e616`.
Produktové soubory i testy JVM opravy mají stejné bloby jako `4af8f12`.
Test, fixture a změnový záznam T047-S01 souhlasí s přesným `main`. Změnový
záznam #121 popisuje oracle a další otevřené části inkrementální integrity.
[Sloučené #121](https://github.com/p-rum/kgmaker/pull/121).

Sémantické důkazy opravné větve mají ověřené souřadnice v aktuálním zdroji.
Sloučený index navazuje na historii obou rodičů se 363 jedinečnými původními
epizodami. Nová epizoda eviduje přesný přenos.

- PASS — 16 PASS, 0 SKIP a 59 DESELECTED za 67,71 s. Výběr zahrnuje
  skutečné Javac, K1, K2 a Criteria kontroly a pět rychlých scénářů
  `SOURCE_ONLY`, reset a odmítnutí neplatného oracle z #121. Pytest a obě
  kontroly manifestu vrátily kód 0. JUnit SHA-256
  `b994dbe08767e63f9c5803c9664e68276d5450c30239c8556916aaedc05b9f30`.
  Shodný SHA-256 vstupního a výstupního manifestu je
  `f593e0f542656a1acdf23785904640c3cc70455bea072162cdddb5d2fd9285c0`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -ra \
    --basetemp /workspace/kgmaker-evidence/jvm-raw-source-after121-focus-pytest \
    --junitxml=/workspace/kgmaker-evidence/jvm-raw-source-after121-focus.xml \
    tests/test_jvm_raw_source_snapshot.py tests/test_criteria_queries.py \
    tests/test_incremental_equivalence.py \
    -k 'jvm_raw_source_snapshot or raw_provenance_in_crlf_source or (incremental_equivalence and (source_only or malformed_oracle or mutation_replay_and_reset))'
  ```

- Strukturu a historii obou rodičů ověřuje `kgmaker semantic update --base HEAD`,
  `kgmaker semantic apply`, `kgmaker semantic validate`,
  `kgmaker memory capture --base HEAD`, `kgmaker scan`, `kgmaker status`,
  `kgmaker check` a kontrola diffu.
- NOT_RUN — nový úplný běh, úplná toolchain matice, Windows a vzdálené CI
  pro tuto přesnou integrační revizi. Výše uvedený striktní běh 300 případů
  je doklad produktu na parentu `4af8f12`.

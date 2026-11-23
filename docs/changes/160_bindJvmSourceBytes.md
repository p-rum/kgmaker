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

## T003-S02 / AC02 — oprava po nezávislém ověření #145

Výchozí revize opravy je `4c4973e9cd79ba6c2dc66ab1a554f03282465a32`.
Přehrání přijalo upravenou mapu bajtů a výběr, ze kterého zmizel skutečně
přeložený Kotlin vstup, se stejným ID kontextu. Ve veřejném source CFG
vypadlo rozvinutí volání s CRLF zdrojem. Skutečná Javac fixture také prokázala
vynechání dvou statických deklarací Kafka retry/DLT.

- `compiler_sources.py`, `inspection.py` a `graph_provider.py` používají ID
  s prefixem `jvm-raw-1:`. ID váže původní digest inspekce před augmentací
  na verzi snapshotu, seřazený jedinečný seznam skutečných vstupů `.java` a
  `.kt`, uloženou raw mapu a normalizovanou projekci odlišných otisků.
  Offline ověření porovná ID a aktuální stav. Samostatný `selection_key`
  dál identifikuje stejný výběr modulu a varianty pro explicitní refresh.
  Kontexty sestavené bez zaznamenaného výběru compiler vstupů dál používají
  původní formát.
- `workspace.py` a `views.py` kvalifikují výběr spolu s oběma mapami.
  Odvození source CFG, Kafka code a Kafka retry ověřuje přesný raw otisk
  k uložené strukturální projekci. Zachovává vazby na kontext, scope,
  cestu a rozsah důkazu. Kafka výstup je statická deklarace.
- Stávající formát graph/store v1–v3, legacy JVM snapshoty a samostatný
  TypeScript snapshot zůstávají čitelné. Metadata cache v1 používají nový
  tvar ID pro raw snapshot a zachovávají živý `BYPASS`.

Nezávislý replay nad původní revizí vytiskl identický záznam ze skutečných
artefaktů s exit 1 a SHA-256
`3fd787a16d3b87b28df1b371080afcba944efe4279df774473bb8e6745eb9ea8`.
Po opravě stejné porovnání z čerstvých Javac a Kotlin artefaktů odmítlo
všechny upravené výběry. LF a CRLF měly shodně 13 bloků a 11 hran CFG.
Exit 0, SHA-256 výsledku
`07f18dd4d0b4dc1286f0fd82dafdde356c5255018cffe6dd2d113b5564a6cfa4`.

- RED — čtyři cílené případy nad původním produktem měly 4 FAIL / 208
  DESELECTED za 30,44 s. Šlo o Javac CFG a Kafka retry/DLT a o každou z
  variant K1/K2 upraveného výběru. JUnit SHA-256
  `f283ddf4c0d68111a92e5934d76c2f2b00ef8cc3d31344ccc3029024d17bfe82`.
- První cílený GREEN — 12 PASS / 0 SKIP / 200 DESELECTED za 74,73 s.
  Skutečný Javac, K1, K2 a připnuté Kafka API. Testy zahrnují změnu konců řádků
  u callera i cíle, neplatný CFG otisk, legacy a workspace replay i původní
  nevybraný CRLF Kotlin. Pytest a obě kontroly manifestu vrátily kód 0.
  JUnit SHA-256
  `68810f2f9a9797f36a01fdee37838c7a1457d1edb9b4524efb74fab2b53202e8`.
  Shodný SHA-256 manifestu před a po
  `c353325b80c1dff742aedeae2d186540bf5bec22c34fc833701a49351d5e91b6`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -p no:cacheprovider -q --tb=short -ra \
    tests/test_jvm_raw_source_snapshot.py tests/test_kafka_retry_dlt.py \
    -k 'jvm_raw_source_snapshot or actual_java_crlf'
  ```

První rozšířená sada měla 534 PASS a 17 FAIL. Opravné kroky zachovaly tvorbu
legacy kontextů bez seznamu vstupů, původní diagnostiku neshodného jazyka a
samostatnou kvalifikaci workspace aliasu. Pro finální běh se doplnily
připravené fixture React a Mermaid se stejnými lockfiles.

- Finální GREEN — 551 PASS / 0 SKIP za 249,65 s. Zahrnuje skutečné Javac,
  K1/K2, JPA/Criteria, Kafka retry/DLT, TypeScript, React a parser Mermaid
  11.4.1. Pytest, vytvoření a porovnání manifestů mají kód 0.
  JUnit SHA-256
  `b5237c901170b5cc7b1a106ed4134c96fb13ef62450602ce012f43afe6129a90`.
  Oba manifesty zdrojů a toolchainu mají SHA-256
  `06bfbc87f33f1e35086c571be30d891a6ca24cd5c8410941f53f1bb9912ae825`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist loadfile \
    -p no:cacheprovider -q --tb=short -ra \
    tests/test_jvm_raw_source_snapshot.py tests/test_criteria_queries.py \
    tests/test_orm_xml_overrides.py tests/test_unified_flow_views.py \
    tests/test_graph_provider.py tests/test_stage_content_cache.py \
    tests/test_workspace.py tests/test_context_roles.py tests/test_t006_select_service_contexts.py \
    tests/test_tsconfig_freshness.py tests/test_kafka_retry_dlt.py tests/test_kafka_code_bindings.py
  ```

Běhy používají JDK 21.0.6, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`,
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData` a připravené worker a Maven distribuce.
Úplná projektová sada, Windows a GitHub Actions jsou pro tuto revizi NOT_RUN.
Selektivní invalidace W02, warm HIT a oprava PSI souřadnic Kotlinu mají
samostatné otevřené hranice.

## T003-S02 / AC02 a T025-S07 / AC07–09 — replay lokálních operací

Výchozí revize je `48318921b98925cbd21b94180a84952648348d09`. Skutečný Javac
v obou variantách publikoval tři local operation důkazy. T025 přijal všechny
tři u LF a hned u prvního CRLF důkazu vrátil `selected operation
source/CFG/proof tuple mismatch`. Kontrola očekávala, že raw otisk zdroje bude
roven normalizovanému otisku v lokálním grafu.

[T025 kontrola zdroje](../../src/kgmaker/process_paths.py) používá existující
`compiler_source_digest`. Pro lokální raw JVM kontext ověří strukturální
projekci a vrátí raw otisk pro porovnání s důkazem. Workspace dál používá
repo-kvalifikovaný raw inventář a legacy kontexty požadují shodu s uloženým
otiskem. Kontext, rozsahy a identity důkazů zůstávají vazbou na skutečné bajty.
[Použití a hranice T025](../process-paths.md#compiler-bound-local-operations).

Rozšířený `test_process_flow_preserves_javac_cfg_edges_across_line_endings`
načte dva uložené Javac grafy ze shodného LF/CRLF fixture, ověří stejné CFG
tvary a tři přesné identity operací v každém grafu. Záměna raw otisku v CRLF
operation důkazu za normalizovaný otisk vyvolá chybu. Při replay test blokuje
spuštění procesu a porovnává bajty obou zdrojů a všech tří výstupů grafu.

- RED — skutečný Javac/JDK 21.0.6, 1 FAIL za 9,65 s, exit 1.
  `pr145-retry2-t025-red.xml` má SHA-256
  `c4bb05cb924370622b3ba06a97601ad2fb9ac6db17daf72cb64bb75b5cdae3cc`.
- PASS — nezávislý offline replay na stejných uchovaných Javac LF/CRLF
  grafech na opraveném produktu přijme 3 a 3 původní důkazy, exit 0, se
  shodnými hashi zdrojů a grafů. `pr145-retry2-t025-retained-green.json`
  má SHA-256 `af076f40bbc660395c712a15a26e626d2ec7a9580673015642d972e1c2132646`.
  Záznam obsahuje společnou výchozí revizi `4831892`; oprava při běhu byla
  v pracovním stromu. Původní běh na čisté revizi vrátil exit 1 a SHA-256
  `158cc466e7096718ac91699ce3be8844e1d7db554107775509dfd28adfe3ab46`.

  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
    /workspace/kgmaker-venv/bin/python \
    /workspace/kgmaker-evidence/pr145-4831892-local-operation-probe.py
  ```

- GREEN — 164 PASS, 0 FAIL, 0 ERROR, 0 SKIP za 202,46 s v Cloud
  Environmentu. JUnit `pr145-retry2-t025-green.xml` má SHA-256
  `31b66dd99007665259b6c6a07247c69ed382bf2b787c76c5d1ae4e9bc2ec1cde`.
  Shodné manifesty zdrojů, testů, fixture a distribucí workerů mají SHA-256
  `4662f3f1330144da663abc90329ab102224fbe5054c71d584a3e8491ba84490c`.

  ```bash
  export JAVA_HOME=/workspace/kgmaker-tools/jdk-21.0.6+7
  export PATH=/workspace/kgmaker-tools/full-launchers:$JAVA_HOME/bin:$PATH
  export KGMAKER_WORKERS_HOME=/workspace/kgmaker-tools/worker-dist
  export KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/kgmaker-tools/maven-repository
  export KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1
  export JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist loadfile \
    -p no:cacheprovider -q --tb=short -ra \
    --basetemp /workspace/kgmaker-evidence/pr145-retry2-t025-green-pytest \
    --junitxml=/workspace/kgmaker-evidence/pr145-retry2-t025-green.xml \
    tests/test_jvm_raw_source_snapshot.py tests/test_local_operation_proofs.py \
    tests/test_t025_build_local_process_path.py tests/test_t024_discover_process_triggers.py \
    tests/test_control_flow.py
  ```

Úplná projektová sada, Windows a GitHub Actions jsou pro tuto opravnou revizi
NOT_RUN. Kotlin PSI souřadnice a širší acceptance T025 mají vlastní otevřený rozsah.

## T003-S02 / AC02 a T025-S07 / AC07–09 — přenos po #146

Oprava `f2b684f0c359a1ebf6b422040e59f56694e82862` je přenesena na
`main` `0dbe9a754f06cf67f5fe40db0aaa31944497fe19`. Zdrojové soubory a testy
opravy mají stejné bloby jako první rodič. Druhý rodič dodává shodné bloby
implementace ověřovací brány i aktualizaci inventáře T047 po #146.
Sémantický index zachovává 372 jedinečných záznamů z obou rodičů. Lokální
obnova přidává doklad o přenosu.

Cílený běh v Cloud Environmentu se skutečným Javac, K1 a K2 měl 97 PASS,
0 FAIL, 0 ERROR a 0 SKIP za 71,01 s. Ověřil 11 JVM scénářů, 43 T032
scénářů, plánování a workflow profily i tři kontroly aktuálního dokladu.
Python při T032 dvakrát upozornil na `fork()` ve vícevláknovém procesu.
JUnit `pr145-retry2-forward-focus.xml` má SHA-256
`54456c689ca87d169bff5f61b53f9011bc039c4452e9cba5f596a65a652296cd`.
Shodné vstupní manifesty zdrojů, testů, fixture a distribucí workerů mají
SHA-256 `d723b1e9e650de1e5c5c80dedff08a9f01d8efb91218f8bac2c23023bc338f3c`.

```bash
/workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist loadfile \
  -p no:cacheprovider -q --tb=short -ra \
  --junitxml=/workspace/kgmaker-evidence/pr145-retry2-forward-focus.xml \
  tests/test_jvm_raw_source_snapshot.py tests/test_t032_persist_process_review.py \
  tests/test_workflow.py tests/test_workflow_profiles.py \
  tests/test_verification_records.py::test_same_head_retry_requires_receipt_from_current_iteration \
  tests/test_verification_records.py::test_done_rechecks_head_after_final_input_snapshot
```

Rozšířená sada na sloučeném stromu, úplná matice, Windows, vzdálené CI a
aktuální nezávislé review mají vlastní kontroly mimo tento cílený běh.

## T003-S02 / AC02 a T003-S06-W08 / AC01–04 — JPA kompatibilita po obnovení CRLF kontextu

Výchozí revize `902158d3c6c362fb51233ecf2403e0549562da78`. Změna konců
řádků v `Money.java` a následná explicitní Javac inspekce zachovaly `COMPLETE`
Flyway snapshot a raw otisk symbolu. Lokální report, příkaz `schema compatibility`
i workspace však ztratily 14 atributů, z toho pět s výsledkem `COMPATIBLE`.

[Framework](../../src/kgmaker/framework.py) ověřuje identitu raw capture a čte
zdroje, jejichž otisk prošel kontrolou `compiler_source_digest`. Starší kontexty
bez mapy zdrojů si zachovávají původní čtení. [Schema replay](../../src/kgmaker/schema_replay.py)
stejnou funkcí ověřuje zdrojový důkaz a zachovává raw hodnotu pro porovnání s
compiler a ORM otiskem. Provider ověřuje původní raw capture před kvalifikací
workspace kontextu a replay kontroluje kvalifikované byte otisky. Změněná
verze u raw ID i chybějící raw mapa vedou k odmítnutí důkazu. Flyway inventář,
otisky migrací, vazby na vybraný stream a stav dostupnosti používají své stávající
kontroly. [Použití a ověřený rozsah](../schema-compatibility.md).

Rozšířený `test_actual_compiler_type_null_decimal_keys_and_later_target_conflict`
mění pouze konce řádků Javac zdroje. Ověří offline zastarání původního kontextu,
shodný Flyway fingerprint po explicitním refreshi, shodu všech výsledků a
raw SHA důkazu. Replay zachovává bajty zdroje, migrací, konfigurace a grafů.
CLI a workspace čtou Git metadata. Test odmítne pokus spustit worker či otevřít
síťové spojení v replay a ověří `UNASSESSED` a `deployment_verified=false`.

- RED — nativní K1/Javac test na výchozím produktu, 1 FAIL za 16,92 s,
  exit 1. `pr145-jpa-native-red.xml` má SHA-256
  `e1e7332d665b603309ec5129c1ca8e687222dcb59766c4df72f240dec17043cb`.
- První GREEN — celý `tests/test_schema_compatibility.py` má 25 PASS,
  0 FAIL a 0 SKIP za 190,58 s se skutečným Javac/K1/K2. JUnit
  `pr145-jpa-native-first-green.xml` má SHA-256
  `9b1c3dc2f2b9285f199f72af152a0ce479d0ca95ca50aaa81c5f7a45a8fbb5ac`.
- Nezávislé porovnání stejné fixture reprodukovalo výchozí ztrátu řádků
  (`7da19f10c235fe44c18dee51ad93e62c40c475b509f8a3abc323eeec18f41c20`, exit 1).
  Na opravených pracovních zdrojích měly všechny čtyři kanály 5 `COMPATIBLE` a
  9 `UNKNOWN` v LF i CRLF, exit 0. SHA-256 výsledku
  `bfa4d60aabc6685d9deb773cc7c7de37a4c61d1df1047078c2fb89fe45975268`.
- Explicitní `schema compatibility --workspace ... --repo money` na uchovaných
  CRLF artefaktech opravného běhu má stejné počty, `COMPLETE` Flyway a nezměněné
  vstupy, exit 0. SHA-256 `fa502e69525e11a7fbab1b9f0ddfed20ad1608137a949e4be5154abfec0f051c`.
- Přísný GREEN — 88 PASS, 0 FAIL, 0 ERROR, 0 SKIP za 285,93 s v Cloud Environmentu
  s JDK 21.0.6 a povinnými workery K1/K2. Zahrnuje W08, raw Javac, JPA XML a
  legacy snapshot, Criteria, persistence realms, statické Kafka retry/DLT,
  Spring a T025. JUnit `pr145-jpa-strict.xml` má SHA-256
  `4adcf1b00a18475170ad4e8e9b720172f45c24ea2095f47b9c2738dfe0fb40ed`.
  Shodné manifesty testů, zdrojů, fixture a workerů mají SHA-256
  `85b5d9ea34ac5316f88f0ecdbdb180a82f7b261c8f20808ba12602b7b81a7935`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist load \
    -p no:cacheprovider -q --tb=short -ra \
    --junitxml=/workspace/kgmaker-evidence/pr145-jpa-strict.xml \
    tests/test_schema_compatibility.py tests/test_jvm_raw_source_snapshot.py \
    tests/test_criteria_queries.py::test_actual_criteria_keeps_raw_provenance_in_crlf_source \
    tests/test_orm_xml_overrides.py::test_orm_xml_partial_overrides_take_precedence_and_record_hashed_source \
    tests/test_orm_xml_overrides.py::test_legacy_jvm_context_is_readable_without_xml_and_stale_with_xml \
    tests/test_persistence_realms.py::test_actual_compiler_contexts_join_only_their_own_replay_targets \
    tests/test_kafka_retry_dlt.py::test_actual_java_crlf_keeps_byte_bound_kafka_retry_declarations \
    tests/test_local_operation_proofs.py::test_actual_workspace_process_resolves_only_operations_not_control_order \
    tests/test_t025_build_local_process_path.py \
    tests/test_spring_proxy_async.py::test_jdk_proxy_async_event_and_self_invocation_are_bounded
  ```

Úplná projektová sada a nezávislé review přesného integračního SHA mají vlastní
doklady. Windows, vzdálené CI a širší W08 matice jsou pro tento běh NOT_RUN.

## T003-S02 / AC02 a T003-S06-W08 / AC01–04 — přenos po #147

Oprava `ee0c69db36524b31c16f5d6611753dcc6d4816b7` navazuje na už sloučený
`main` `2db5c4931bfd832908158900b2823b6c122bc3a7`. Source/test bloby opravy
odpovídají prvnímu rodiči. Implementace a testy runtime publikace odpovídají
druhému rodiči. Obnova sémantického indexu zachovává 376 jedinečných epizod
obou rodičů a přidává doklad integrace. [Doklad a rozsah #147](163_revalidateRuntimeImportPublication.md).

Na přesném prvním rodiči prošlo 729 testů s povinnou skutečnou toolchain sadou.
Standardní běh měl 2467 PASS, 1307 SKIP a jeden očekávaný XFAIL. Oddělená sada
AC02 měla pět PASS pro cache a chybu přípravy Maven fixture. Samostatný běh
skutečného JVM lifecycle s fyzicky připravenými závislostmi fixture pak prošel.
Doklady prvního rodiče jsou `pr145-ee0c69d-native.xml`, `pr145-ee0c69d-standard.xml`,
`pr145-ee0c69d-native-ac02-cache.xml` a `pr145-ee0c69d-native-ac02-lifecycle-materialized.xml`.

Aktuální kombinovaný výběr měl 7 PASS, 0 FAIL, 0 ERROR a 0 SKIP za 66,23 s
s povinnými workery a JDK 21. Pokryl W08 JPA LF/CRLF, T025 CFG a local proofs,
jednorázovou validaci runtime payloadu a rollback zdroje, bytecode a distribuce
workeru při publikaci. JUnit `pr145-jpa-forward-focus.xml` má SHA-256
`d6caae7a10e1e97939df4ee1158e4d415c72b05299e82259244baf30b51948c8`.
Shodné vstupní manifesty mají SHA-256
`b47f8d094e5cd91cf43791e1affa1de7234ce2e891495cc02e70014cdbc0e953`.
Úplná sada je doložena pro výše uvedeného rodiče. Windows a vzdálené CI
jsou pro tento lokální přenos NOT_RUN.

## T012-S04 / AC01–02, AC04–05 a T019-S01 / AC01, AC03 — Kafka katalog pro Javac CRLF

Výchozí revize `99fe4b500092b7edba2e3af6e68c6e38d7a9c6ae`. Skutečný Javac
zachytil LF i CRLF kontext se stavem `CONTENT_VERIFIED` a potvrzené konfigurace
`VERIFIED_STATIC`. T012 však u CRLF vyvolal `INVALID_KAFKA_INTERFACE`, protože
porovnával kvalifikovaný bajtový otisk se strukturálním otiskem lokálního grafu.
Vstupní chyba se promítla i do načtení katalogu T019.

[Projekce katalogu](../../src/kgmaker/interfaces.py) použije
`compiler_source_digest` nad soukromým lokálním grafem a vybraným kontextem.
Helper ověří strukturální projekci a vrátí původní bajtový otisk. Projekce
požaduje přesnou shodu s kvalifikovaným workspace inventářem a dál ověřuje
kanonický uzel, důkazy, vybraný kontext, původní odkazy a vlastníka služby.
Dodání zachovává stávající schéma výstupu a význam `delivery=NOT_OBSERVED`.
[Katalog a příkaz T019](../kafka-interfaces.md).

`test_actual_kafka_catalogue_and_t019_preserve_raw_java_authority` přehraje
stejné producer a consumer deklarace s LF a CRLF variantou Java listeneru.
Ověří rozdílné bajtové otisky, shodu katalogů, obě consumer groups, broker
realms a odmítnutí normalizovaného otisku podvrženého v bajtovém inventáři.
T012 při čtení nepouští žádný proces. CLI používá pouze lokální Git metadata.
Test porovnává soubory, graf a předané workspace vstupy před i po čtení.

- RED — nativní Javac, 1 FAIL za 79,08 s, exit 1. LF API a CLI prošly,
  CRLF API vrátilo původní chybu. JUnit `pr145-t012-native-red.xml`, SHA-256
  `819dc401b19dc4b333a6bf54a991cd30c8e7f1be0676c396e05ed3ba6013cd1c`.
- PASS — na uchovaných skutečných Javac fixture oprava vrátí v API i CLI
  pět rozhraní a obě skupiny v LF i CRLF. Oba replaye zachovaly všech 16
  souborů a podvržený CRLF inventář byl odmítnut. Exit 0, SHA-256 dokladu
  `bc14c03f0adf1d9bde59f6c6677d4a124255a845720709fa1bc40190b44274be`.
- Přísný GREEN — 144 PASS, 0 FAIL, 0 ERROR a 0 SKIP za 422,27 s v Cloud
  Environmentu s JDK 21.0.6 a povinnými workery K1/K2. Sada ověřila 106
  případů T012, 34 případů T019 a čtyři další Kafka kontroly. JUnit
  `pr145-t012-strict.xml`, SHA-256
  `a502d1bbee310dde6ad90239cd89535e325f0de1a5187ae04211f0aaeaf104a3`.
  Shodné manifesty zdrojů, testů a workerů mají SHA-256
  `870348857a444f19389c4c0c44538cf838dfe36f9edf85fde9a81a1f8f5afdd7`.

  ```bash
  /workspace/kgmaker-venv/bin/python -m pytest -n 3 --dist loadfile \
    -p no:cacheprovider -q --tb=short -ra \
    --junitxml=/workspace/kgmaker-evidence/pr145-t012-strict.xml \
    tests/test_t012_catalog_kafka_interfaces.py tests/test_t019_add_architecture_json_cli.py \
    tests/test_t013_captured_kafka_contracts.py \
    tests/test_kafka_code_bindings.py::test_actual_schema2_joins_source_code_and_group_without_exposing_private_capture \
    tests/test_kafka_retry_dlt.py::test_actual_java_crlf_keeps_byte_bound_kafka_retry_declarations
  ```

Úplná sada, Windows a vzdálené CI mají pro tuto revizi stav NOT_RUN.

## T012 / T019 a T003-S02 / AC02 — přenos po #148

Kafka oprava `f94b7f4463a9e827e7df60cdc70fce332b0be903` navazuje na sloučený
`main` `385943e48d2d2e60cec541f1f0db78beda83de22`. Všechny bloby zdrojů a
testů #145 odpovídají prvnímu rodiči. Implementace a testy build konfigurace
odpovídají druhému rodiči. Obnovený index zachovává 380 jedinečných epizod
obou rodičů. [Doklad a rozsah #148](165_forwardBuildConfiguration.md).

Na přesné revizi `99fe4b5` prošlo 729 nativních testů bez skipu a standardní
běh měl 2469 PASS, 1310 SKIP a jeden očekávaný XFAIL. Nezávislá skutečná
Spring HTTP fixture na téže revizi ověřila shodu provider a consumer katalogů
pro LF/CRLF, exit 0, SHA-256
`9b0cc396e559f759ddf8015402b79a66498c2a2a15aaaa2e3c377f7ec255381a`.
T012 sada 144 PASS a doklad čtení beze změn patří k opravě `f94b7f4`.

Kombinovaný výběr na tomto stromu měl 14 PASS, 0 FAIL, 0 ERROR a 0 SKIP za
148,86 s. Ověřil skutečný katalog T012/T019, JPA a T025 s Javac LF/CRLF i 11
kontrol fingerprintu vybraného build kontextu. JUnit `pr145-t012-forward-focus.xml`
má SHA-256 `0af3b4fd9225a6386a6f4bcca4800f0ccd79e999562a1398a08ef7ed93619b53`.
Shodné manifesty mají SHA-256
`fbf521e4e40d154cad5a114480887e2ff592e3de26da719d0655ae9d2a2fc51a`.
Úplná sada pro tento přesný strom, Windows a vzdálené CI mají stav NOT_RUN.

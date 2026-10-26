# K2 Analysis API backend vedle explicitního K1 compatibility backendu

Datum: 2026-10-26. Zadání: [T003-S04-W01](../tasks/T003-S04-01-k2AnalysisApiBackend.md),
AC01–AC04; nadřazené T003-AC04. Závislosti T003-S03-W01 a W04 jsou na main
implementovány (change10 a change28). Výchozí baseline práce: `07ad865`.

## Problém a skutečné změny

Původní worker používal Kotlin 2.1.10 distribuci, ale jeho resolver byl stále
K1 language1.9 BindingContext. Nový opt-in backend používá skutečnou FIR
Standalone Analysis API 2.1.10, `analyze` a `resolveToCall`. Nejde o přejmenování
K1 výsledku. K1 je zachována jako `k1-compat-1`; K2 má vlastní
`k2-analysis-api-2.1.10-v1`, target-k2, capability, context selection a evidence.

- K2 explicitní call expressions uvnitř non-local named-function bodies získávají
  cíle od Analysis API. JVM identity pocházejí z jednoznačné compiler light-method
  signatury; bez ní zůstává call UNRESOLVED. Java nadále používá JavacTask/Trees.
- CLI `--kotlin-backend k2 --kotlin-version 2.1.10` vybírá K2 bez fallbacku.
  Neznámá compiler/language/API/JVM verze nebo captured flags/plugins/opt-ins
  se odmítají před workerem a publikací. Worker ověřuje backend/verzi také
  při přímém protocol požadavku. K2 vyžaduje language/API2.1, JVM21 a compiler2.1.10.
- Backend/verze jsou v symbol/call metadata a evidence, SHA-256 celé distribuce
  zůstává součástí content-bound kontextu. Offline refresh nevykonává procesy
  a stale next-command zachovává explicitní K2 volbu.
- Offline builder podporuje `--backend k2 --analysis-api-home`; vstupy ověřuje
  podle `dependencies-k2.lock.json`. Explicitní oddělený `fetch_k2.py` stahuje
  sedm JetBrains API JARů2.1.10 a Caffeine2.9.3 a před publikací kontroluje SHA-256.
  Při chybě bytes se existující validní soubor nepřepíše. Nikdy se nevolá implicitně.
- K2 JAR/classpath manifest skládá standardní continuation lines; rozsáhlejší
  classpath již nepřekročí limit parseru. Worker po jediném protocol response
  explicitně končí, aby nečekal na non-daemon IntelliJ pool.
- Volitelný předem připravený K2 runtime se přenáší sdist→wheel; source-only
  balíček nemá target ani target-k2. CI explicitně sestavuje K2 a vyžaduje
  skutečné K2 testy. README, compiler docs, acceptance a progress uvádějí scope.

## Kompatibilita a omezení

Worker protocol zůstává v1, graph/store v1/v2/v3 mají původní loader. Legacy
protocol-v1 K1 handshake bez nového backend pole je dál čitelný; pro K2 se
vyžaduje přesné versioned backend ID. Bez přepínače zůstává K1 compatibility.
SOURCE_ONLY nepotřebuje JDK/Node a nespouští download, build ani worker.

K2 dodává pouze dokumentovaný call subset; source CFG, constructor ABI, property/operator/reference/
initializer call sites, local/lambda execution, default-body/coroutine mapping
a širší compiler/plugin matice zůstávají PARTIAL s diagnostikami.
T003-S04/T003 nejsou dokončeny. Připnuté hashes jsou obsahová kontrola, nikoli
nový důkaz publisher authenticity. JDK/Node/compiler distribuce se nebundlují.

## Testy a acceptance

| AC | Konkrétní test |
|---|---|
| AC01 | `test_real_mixed_k2_calls_have_stable_jvm_symbols_and_backend_evidence`, installed-wheel `test_packaged_k2_analyzes_outside_checkout` |
| AC02 | `test_existing_graph_loader_is_unchanged`, `test_k1_distribution_stays_explicitly_limited`, `test_k1_and_k2_contexts_accumulate_without_replacement` |
| AC03 | `test_unsupported_backend_or_version_never_runs_or_mutates`, `test_imported_unsupported_k2_compiler_version_fails_before_worker`, `test_unsupported_captured_k2_options_are_not_silently_ignored`, `test_missing_k2_distribution_never_falls_back_to_k1`, `test_direct_worker_rejects_unsupported_version_and_backend`, `test_unresolved_and_ambiguous_k2_calls_remain_partial`, `test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph`, `test_explicit_k2_fetch_rejects_wrong_bytes_without_publishing` |
| AC04 | Tento dokument, compiler capability matrix a acceptance inventář, skutečný pinned runtime a required K2 CI gate |

Skutečné lokální verze: Temurin21.0.6+7, compiler/AnalysisAPI2.1.10, Caffeine2.9.3,
Jackson2.18.2, Python3.12.14 a pytest8.3.4. K1 i K2 byly sestaveny skutečným
`workers/jvm/build.py`; API probe skutečně resolveoval Kotlin call před
implementací. První probe odhalil chybějící Caffeine a non-daemon pool, obojí
řešeno konkrétní připnutou dependency a jednopožadavkovým ukončením.

Průběžné běhy před finální integrací: K2 focused12 PASS/63.72s; rozšířený focused18
PASS/22.70s; první celá strict sada276 PASS,7 SKIP/95.96s. Nejde o finální CI
ani dokončení všech milníků. Finální integrační evidence je doplněna níže.

## Příklad

```bash
python workers/jvm/fetch_k2.py --output /tmp/kgmaker-k2-api
python workers/jvm/build.py --backend k2 --analysis-api-home /tmp/kgmaker-k2-api \
  --kotlin-home /opt/kotlinc-2.1.10 --maven-repository /opt/trusted-m2 --java-home /opt/jdk-21
kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10 \
  --worker-home /opt/kgmaker/workers --classpath /opt/kgmaker/workers/jvm/target-k2/lib/kotlin-stdlib.jar
```

Maven repository musí předem obsahovat připnuté Jackson2.18.2 JARy; builder nic
neřeší online. Další compiler a source mapping varianty mají samostatná zadání.

## Integrační kontrola JVM ABI

Negativní reálný probe `class Outer { inner class Inner }; fun construct(outer: Outer):
Any = outer.Inner()` odhalil v light PSI chybějící implicitní enclosing-instance
parametr. Původní cesta chybně vytvořila `Outer$Inner.<init>()V`; skutečné JVM ABI
vyžaduje `(LOuter;)V`. `test_inner_constructor_does_not_invent_incomplete_jvm_abi`
proto nejprve FAIL a backend nyní všechny dosud nemapované constructor targety
zachová UNRESOLVED. Nezaměňuje source parametry za úplný JVM descriptor.

Dependency target navíc musí mít skutečný owner class a přesnou metodu/descriptor
v explicitní classpath nebo JDK platformě; Kotlin intrinsic light PSI bez JVM class nevytváří target.
Existenci metody ověřuje sdílený ASM reader `Bytecode.hasDeclaredMethod` pouze
čtením JAR/directory/JDK resource, bez načítání
či inicializace projektové třídy. Non-method generated symboly nejsou mapovány
na náhodnou light metodu. Source named functions zůstávají podporované.

Post-PR8 integrační běh před tímto rozšířením: **295 PASS,7 SKIP/136.22s**.
SKIP: Maven runner1, druhé JDK+Maven1, Gradle included1, Gradle variants2,
Maven Kotlin options1 a Gradle Kotlin options1. Jde o chybějící execution prostředí,
nikoli PASS ani výjimku z taskových K2 testů.

## Nezávislé review — local class/object initializer boundary

Review reprodukovalo P1: `fun outer() { class Local { val x = target();
init { target() } } }` bez vytvoření Local emitovalo dvě resolved volání
`outer→target`. Přesný actual-worker test nejprve FAIL. Body visitor nyní
zastaví vnořené class/object deklarace a object-literal bodies s lokalizovanými
`K2_LOCAL_CLASS_BODY_UNSUPPORTED` / `K2_OBJECT_LITERAL_BODY_UNSUPPORTED`.
Vlastní skutečné volání `target()` za vnořenou třídou zůstává v outer funkci.
`test_local_class_and_object_initializers_do_not_become_outer_calls` ověřuje
absence vymyšleného execution, zachování skutečného calleru, range diagnostik
a PARTIAL; nejde o rozšíření na constructor/init execution.

Průběžná dodatečná pozitivní kontrola `String.substring` ukázala také dosud
nemapovaný Kotlin built-in owner; zůstává výslovně unresolved. Reálný
Java/JDK interop pozitivní test používá `java.lang.Math.abs` s fyzicky ověřeným
JVM memberem. Po ABI guardu focused23 PASS/49.67s; následující full běh byl
přerušen kvůli výše uvedenému novému P1, proto není finální evidence.

## Nezávislé review — zachování Javac declaration metadata

P2 review doložilo, že přidání Kotlin volání `Helper.plus(1)` k Java metodě
`@Deprecated public static int plus(int x) throws IllegalArgumentException`
zahodilo původní `annotations`, modifiers/throws/return_type a přejmenovalo
Java declaration provenance na K2. Actual-worker before/after test nejprve
FAIL (`annotations: None` místo `java.lang.Deprecated`).

K2 nyní použije kanonickou `State.methodIdentity` a při existující Javac source
declaration vrátí její identitu bez přepsání metadat. K2 provenance zůstává na
Kotlin call-site/evidence; deklarace a její Javac annotation/scope/throws/return
provenance zůstávají zachovány. Test
`test_kotlin_call_preserves_authoritative_javac_declaration_metadata` porovnává
Java-only a mixed reálný běh, nikoli pouze očekávaný substring.

Každý Kotlin soubor nese navíc content-bound `K2_SOURCE_MODEL_PARTIAL`, aby
ani class-only soubor bez zpracovaných metod nevydal COMPLETE pro neimplementované
source konstrukce. K2 Kotlin annotation/framework metadata nejsou dodány;
`test_class_only_kotlin_never_claims_complete_source_coverage` ověřuje range/hash
hranice a stav PARTIAL. K1 a Java podporované metadata zůstávají zachovány.

## Finální integrační ověření

Aktuální integrační base je `35033096e8a2ea5d74ae8d2195a7b27d22c7590a`
(main po XLS PR21); testovaný source HEAD `20aacfe24db889566909d59c19c736922e48bbde`.
Oba required předchůdci W01/W04 jsou ověřené ancestors.

- `PYTHONPATH=src KGMAKER_WORKERS_HOME=/workspace/k2/workers KGMAKER_REQUIRE_K2=1 /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_k2_backend.py`: **30 PASS/42.77s**.
- Celá sada po obou nezávislých review opravách a integraci main:

```bash
JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH \
PYTHONPATH=src KGMAKER_WORKERS_HOME=/workspace/k2/workers \
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
/workspace/kgmaker-venv/bin/python -m pytest -q -ra
```

Výsledek: **321 PASS,7 SKIP/136.03s**. Oba rebuilt K1/K2 workery, skutečný
TypeScript worker a sdist→wheel→outside-checkout K2 instalace skutečně běžely.
Připravený Maven mixed fixture target pochází ze skutečného trusted buildu;
Maven ani Gradle nejsou v této testové PATH, druhé JDK není připraveno.
Sedm uvedených runner/Gradle/druhé-JDK skipů zůstává SKIP, ne PASS.

- Explicitní `fetch_k2.py --output /workspace/tools/k2-verified`: **8 skutečně
  stažených artifactů, všechny připnuté SHA-256 PASS**; corrupted download
  test nic nepublikuje.
- K2 JAR testované distribuce SHA-256:
  `6d02d7e09272bf3d6d76f3e35c5e071ff352d01def29982c26e69b54daff6c6d`.
  K1 JAR: `4e4598b7e5646a0d0d260e0785544c828dbe02ad5459a78fe0629f7baa911d44`.
- Scoped semantic update/apply/validate, implementační memory capture, generovaný
  scan/check, compileall a `git diff --check`: **PASS** při lokálním předání.
  Existující sémantické identity a historie z main jsou zachovány; bez nové
  nepodložené technické vazby.
- Remote CI, GitHub PR review a merge: zde **NOT_RUN**, provede samostatný
  integrační/review workflow nad publikovaným current HEAD. Implementační agent
  nevykonal externí push/PR/merge.

Backend dodává pouze výslovně ověřený rozsah, nikoli dokončení T003-S04/T003.

## Integrace exporter distribuce před publikací

Nová base: `e656b8ef4c174d3d60600037d7c0d78fc514e39d` (main po PR22),
lokální merge `2508ad9`. K2 runtime/source/test bytes vůči `93d841a` zůstaly
byte-identické; testovaný K2 JAR má nadále SHA-256
`6d02d7e09272bf3d6d76f3e35c5e071ff352d01def29982c26e69b54daff6c6d`.
`pyproject.toml` zachovává současně K2 resources i exporter descriptor/licenci;
CI obsahuje required K2 worker gate i samostatné skutečné installed-exporter
Maven/Gradle kontroly. Konflikty byly pouze v generovaném grafu a semantic
artefaktu, historie se sloučila podle immutable episode ID.

Relevantní integrovaný běh se stejnou Temurin21 PATH a explicitním own workers home:

```bash
PYTHONPATH=src KGMAKER_WORKERS_HOME=/workspace/k2/workers \
KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
/workspace/kgmaker-venv/bin/python -m pytest -q \
  tests/test_exporter_distribution.py tests/test_k2_backend.py tests/test_worker_install.py \
  -k 'not installed_exporters_run_real_builds_outside_checkout'
```

**46 PASS,2 DESELECTED/73.98s**: exporter negative/no-process/no-mutation cases,
celá K2 acceptance a skutečná K2 instalace mimo checkout. Dvě nesouvisející
exporter execution varianty Maven/Gradle nebyly opakovány; nejsou vykázány PASS.
Celý dřívější actual suite321 PASS/7 SKIP výše nebyl opakován pouze kvůli této
upstream exporter změně; vztahuje se k uvedené dřívější base.

Scoped semantic evidence je znovu ověřena proti aktuálním README bullets
`semantic prepare` (řádek99) a `semantic update --base REF` (řádek101).
Semantic validate, generovaný scan/check, compileall a integrační diff check PASS.
Všechny upstream epizody i původní validovaná K2 epizoda jsou zachovány.
Nejde o GitHub review/merge ani nový live runtime proof.

## Integrace T006/T007 před compiler CI

Aktuální base je `3a393e451b0d7b8f83de93f05f07d2307ba66ec3` (main po
service-context a ownership PR); lokální merge `7f9865d`. K2 runtime/source/test
bytes i kombinované package resources/CI zůstaly identické vůči `6c8cc60`.
K2 JAR má stále SHA-256 `6d02d7e09272bf3d6d76f3e35c5e071ff352d01def29982c26e69b54daff6c6d`.

S own worker home a stejnou Temurin21 PATH proběhla relevantní integrační sada:

```bash
PYTHONPATH=src KGMAKER_WORKERS_HOME=/workspace/k2/workers KGMAKER_REQUIRE_K2=1 \
/workspace/kgmaker-venv/bin/python -m pytest -q \
  tests/test_t006_select_service_contexts.py tests/test_t007_define_service_ownership.py \
  tests/test_cross_repo_artifacts.py tests/test_worker_protocol.py \
  tests/test_k2_backend.py::test_real_mixed_k2_calls_have_stable_jvm_symbols_and_backend_evidence \
  tests/test_k2_backend.py::test_k1_and_k2_contexts_accumulate_without_replacement
```

**40 PASS/19.68s**: service/context/ownership a content-bound cross-repo
regrese, protocol transport a skutečný mixed K2 + společně zachované K1/K2
kontexty. Celá starší actual sada321 ani všech30 K2 testů nebyly opakovány
pouze kvůli nezávislým source view/workspace změnám; jejich výsledky zůstávají
přiřazené k dříve uvedeným source/base SHA.

Na tehdejší base byly zachovány4 concepts/6 relations včetně explicitní
ownership vazby. Následný centrální audit potvrdil, že dvě chybějící
semantic-function vazby byly neúmyslný upstream drop, nikoli neplatná fakta;
centrální obnova a jejich zachování jsou doloženy v další integraci níže.
Samotná absence v nové base není důvod odstranit jinak ověřené související fakta. Immutable episode historie je sjednocena:
66 main epizod + původní K2 epizoda =67, bez ztráty či přepisu záznamů.
Citace byly znovu ověřeny proti skutečnému textu: README prepare/update bullets
130/132; architecture scanner/store/source-authority15/19/22 a ownership140/143.
Scoped apply/validate, generovaný scan/check, compileall a diff check PASS.
GitHub povinný compiler CI a exact-pair review provede nad publikovaným HEAD
navazující integrační workflow; tento agent neprovádí externí zápis.

## Integrace Confluence25 a centrálně obnovených semantic facts

Aktuální base: `7b9a9eaecaf41c9c5bc5a6d1233cd82e2cf4f1e9`; lokální merge
`2112b77`. K2 runtime/source/tests, package resources a CI zůstaly byte-identické
vůči publikovanému `0337366`. JAR SHA-256 se nemění:
`6d02d7e09272bf3d6d76f3e35c5e071ff352d01def29982c26e69b54daff6c6d`.

Relevantní integrační běh s explicitním own worker home a Temurin21:

```bash
PYTHONPATH=src KGMAKER_WORKERS_HOME=/workspace/k2/workers KGMAKER_REQUIRE_K2=1 \
/workspace/kgmaker-venv/bin/python -m pytest -q \
  tests/test_confluence_configuration.py tests/test_confluence_sync.py tests/test_worker_protocol.py \
  tests/test_k2_backend.py::test_real_mixed_k2_calls_have_stable_jvm_symbols_and_backend_evidence \
  tests/test_k2_backend.py::test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph
```

**34 PASS/26.33s**: offline config/fake synchronization/protocol a skutečný
mixed K2 + strict/no-publication/offline-refresh smoke. Nová registrace
Confluence CLI nekoliduje s `inspect code --kotlin-backend k2`; parser ověřen
s explicitním workers home. Live Confluence zůstává NOT_RUN podle schválené
konfigurace/specifikace; nejde o live connectivity důkaz. Starší full321 se
kvůli tomuto nezávislému rozšíření neopakuje ani nepřeznačuje na current-base run.

Zachovány jsou všechny4 concepts/8 relations z main, zejména dříve
neúmyslně vypuštěné `implements` → `apply_semantic_patch::440` a `validates` →
`validate_semantic_data::100`. Skutečný `scan_repository` znovu potvrdil oba
targety; evidence def lines jsou442/102 (scanner ID offset není source line).
READMElines prepare/update134/136 a architecture15/19/22/140/143 byly
zkontrolovány proti skutečnému obsahu a scoped patch je znovu váže na current hashes.
Immutable historie obsahuje všech69 main epizod a původní K2 epizodu (union70).
Semantic apply/validate, generovaný scan/check, compileall a diff check PASS.
Externí update PR26/CI/merge přebírá parent integrační workflow; agent nic nepushuje.

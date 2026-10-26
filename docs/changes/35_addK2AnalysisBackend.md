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

K2 dodává pouze dokumentovaný call subset; source CFG, property/operator/reference/
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

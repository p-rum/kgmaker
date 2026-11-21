# Zachování dokladů opakovaného runtime importu

[T003-S13-W02](../tasks/T003-S13-02-runtimeRtaImport.md), kroky 1–5 a nadřazené
[T003-AC13](../tasks/3_finishProductionAnalysis.md#t003-s13--volitelný-runtime-import).
Výchozí `main` a implementační větev používají
`c2885a6f8daf0281967e3bc5386a69f1647718e0`.

## Krok 1 — výchozí kontrakt, AC01 a AC03

`runtime import` dosud indexoval všechny hrany klíčem
`(source, target, kind)`. Opakovaný import přepsal odkazy na starší runtime
doklad. Stejný klíč mohl při zápisu ztratit souběžné statické hrany. Statický
`callgraph path` a výpočet cyklů používaly i hrany `observed_dispatch_to`.
Baseline regresní testy pro import a statickou navigaci selhaly.

## Krok 2 — kompatibilita, AC02

`src/kgmaker/runtime_evidence.py` zachovává identitu v1 a ukládá nový v2
doklad s validovanými hodnotami `build_id`, `config_fingerprint`,
`service_id`, `service_version` a `source_identity`. Formáty manifestu
v1/v2 a graph/store v3 zůstávají čitelné bez migrace. Dřívější doklad si
ponechá původní rozsah metadat.

## Krok 3 — oddělený import a navigace, AC01 a AC03

`src/kgmaker/runtime_evidence.py` připojí unikátní ID dokladů ke stejné
pozorované hraně uvnitř jednoho compiler kontextu. Hrany jiných kontextů
a statické vazby si ponechají vlastní záznam. Kontrola manifestu a CAS původní
generace probíhají před publikací. `src/kgmaker/callgraph.py` zobrazuje
`RUNTIME_OBSERVED` v `callers` a `callees`. Statická cesta a cykly mají
vstup z compiler call sites.

Například `kgmaker callgraph path --root PROJECT --context CONTEXT_ID
--from CALLER_ID --to TARGET_ID` vrátí `UNKNOWN`, když jsou symboly spojené
pouze importovaným runtime dokladem. Závěry o receiver/type, runtime value-flow
a async/reflection patří k dalším krokům. Surové `facts` produceru dál
podléhají validaci. Grafová pozorování pocházejí z explicitního pole
`observations`.

## Krok 4 — regrese a ověření, AC01–AC03

`tests/test_runtime_trace_producer.py` pokrývá starý v1 doklad, dvě v2
service varianty se stejným runtime ID, kontexty s odlišnými build/config
identitami, opakování totožného dokladu, neplatnou konfiguraci bez zápisu
a zachování dvou statických hran. Navigační fixture má jednu statickou
hranu a opačné runtime pozorování. Statická cesta funguje ve správném směru
a statický cyklus nevznikne. Testy produceru samostatně používají skutečný
Javac/JVM worker a explicitně spuštěnou aplikaci.

- RED — `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py -k 'same_edge_observations or creating_static_path'` na baseline s novými testy, 2 FAIL.
- První rozšířený pokus skončil 227 PASS / 32 FAIL / 56 ERROR. Příčinou byla
  změna zdroje implementace během inspekce a chybějící připravené distribuce
  v explicitně vybraném `workers/`. Pro opakování se připravil připnutý
  toolchain do ignorovaných cest a Python zdroj zůstal stabilní.
- GREEN — na opraveném zdroji 315 PASS / 0 SKIP za 289,33 s. Běh v Linuxu
  používal JDK 21.0.6, skutečné JVM K1/K2 a TypeScript 5.7.3, `PYTHONPATH=src`,
  `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`, `KGMAKER_REQUIRE_WORKERS=1` a
  `KGMAKER_REQUIRE_K2=1`. JUnit SHA-256
  `6dcd27b008d6b45ce6e6bfc5b9ed60b72fd76e58ee0ba8ef3ee69c76e2c00b75`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_runtime_trace_producer.py tests/test_graph_publication_concurrency.py \
  tests/test_build_aware.py tests/test_evidence_ranking.py tests/test_return_consumer_flow.py \
  --junitxml=/workspace/kgmaker-evidence/runtime-w02-final-scoped.xml
```

- `git diff --check` PASS. Sémantická aktualizace uchovává stávající
  doložené vztahy. Graf se ověřuje příkazy `semantic validate`, `scan`,
  `status` a `check`.
- Úplná sada, GitHub Actions a nezávislé review této změny jsou při předání
  NOT_RUN. Celé RTA a T003-AC13 zůstávají otevřené.

## Krok 5 — návody a inventář, AC04

[README](../../README.md), [runtime API a CLI](../runtime-trace.md#opakovaný-import-a-navigace),
[compiler příklady](../compiler-inspection.md#pozorované-hrany-a-statické-cesty),
[acceptance](../acceptance-inventory.md#t003-s13-w02--více-dokladů-stejné-pozorované-hrany)
a [stavová matice](../production-analysis-progress.md) zachycují stejný
podporovaný rozsah. Registr používá stávající identitu i závislosti zadání.
Instalované instrukce `init` používají dosavadní příkazy.

## Přenos po sloučení #132 — kroky 4 a 5, AC01–AC04

Lokální merge pro [#136](https://github.com/p-rum/kgmaker/pull/136) připravený
z publikovaného headu `92d1506be7cd8e325819647c48a4574c6b5ae57b` a aktuálního
`main` `4011825b15e4b65e1f57576a0986ca05b3cf810e` zachovává obě historie.
Všechny tři zdrojové a testovací cesty W02 i všechny tři cesty T032 mají
stejné bajty jako v příslušných rodičích. Konflikty se týkaly generovaného
grafu a sémantické vrstvy. Třícestný přenos zachoval 55 konceptů, 188 vztahů
a všech 338 dřívějších epizod obou větví.

- **Krok 4, AC01–AC03.** Cílený Linux běh má **134 PASS / 0 SKIP** za
  19,56 s. Zahrnul 73 runtime testů včetně skutečné JDK21 aplikace,
  43 procesních regresí T032 a 18 testů W06. Použil JDK/Javac 21.0.6,
  připravený JVM worker, `PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`,
  `KGMAKER_REQUIRE_K2=1` a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.
  JUnit má SHA-256
  `d456c62c19fbff5a4c2505bed799ed9612bfd35114feb49486b28846429f8ca9`.

```bash
python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_runtime_trace_producer.py tests/test_t032_persist_process_review.py \
  tests/test_graph_publication_concurrency.py \
  --junitxml=/workspace/kgmaker-evidence/pr136-after132-scoped.xml
```

- **Krok 5, AC04.** [Inventář](../acceptance-inventory.md#t003-s13-w02--více-dokladů-stejné-pozorované-hrany)
  a [stavová matice](../production-analysis-progress.md) uvádějí nový základ.
  [Runtime příklady](../runtime-trace.md#opakovaný-import-a-navigace),
  [compiler příklady](../compiler-inspection.md#pozorované-hrany-a-statické-cesty)
  a README dál popisují ověřený rozsah importu a statické navigace.

Starší výsledek 315 PASS patří k původnímu základu. Úplná sada, nové
review integračního stromu a GitHub Actions jsou při předání `NOT_RUN`.
Odvození receiver/type ze surových facts a celá T003-AC13 zůstávají otevřené.

## V2 volatelné symboly po přenosu na `34591e2` — kroky 1–5, AC01–AC04

Přenos #136 spojuje head `4d4529304d5d311e94395208c1f3c91de0c5b162`
s `main` `34591e2f45814838dd8b21390cdc43c84530f648`. Import v2 přijímal
symbol třídy z vybraného compiler kontextu jako volajícího nebo cíl.
`runtime_evidence.py` teď pro `call` a `dispatch` používá stejnou klasifikaci
metody, funkce a konstruktoru jako capture. Vynechaný `kind` znamená `call`.
Odmítnutí proběhne v validaci před publikací. Manifest v1, v2 `framework`
a graph/store v3 používají dosavadní kontrakty bez migrace.
[Runtime import a CLI](../runtime-trace.md#opakovaný-import-a-navigace) · [Compiler příklady](../compiler-inspection.md#pozorované-hrany-a-statické-cesty)

- RED — `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py -k 'requires_callable_endpoints or keeps_callable_and_framework'`
  na `4d45293` s novými testy má 2 FAIL, 1 PASS, 73 DESELECTED.
  Oba záporné případy získaly třídu z reálného compiler kontextu skutečné
  JDK21 aplikace. Původní import třídu přijal. JUnit SHA-256
  `66925698578b9ec6b93b85501bcc6872bba2a6beb75636c71ae806192ec69a23`.
- GREEN — `python -m pytest -p no:cacheprovider -q --tb=short -ra tests/test_runtime_trace_producer.py tests/test_t032_persist_process_review.py tests/test_graph_publication_concurrency.py`
  má 137 PASS / 0 SKIP s JDK/Javac 21.0.6 a připraveným JVM workerem.
  Použil `PYTHONPATH=src`, `KGMAKER_REQUIRE_WORKERS=1`,
  `KGMAKER_REQUIRE_K2=1` a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData`.
  Záporné testy zakazují spuštění procesu při importu a srovnávají
  uložený graf i runtime artefakt po bajtech. Kladná kontrola zahrnuje
  v2 `call`, v2 `framework` a historický v1 import.
- NOT_RUN — úplná sada, GitHub Actions a nezávislé review tohoto přenosu.
  Odvození receiver/type a přesné call-site vazby ze surových facts mají
  separátní rozsah. T003-S13-W02 a T003-AC13 zůstávají `PARTIAL`.

Stav i ověřené hranice uvádějí také [README](../../README.md),
[acceptance inventář](../acceptance-inventory.md#t003-s13-w02--více-dokladů-stejné-pozorované-hrany)
a [stavová matice](../production-analysis-progress.md).

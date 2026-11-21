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

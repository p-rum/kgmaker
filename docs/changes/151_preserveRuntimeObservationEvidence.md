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

## Změna zdroje během publikace — kroky 1, 3–5, AC01–AC04

Výchozí revize [#136](https://github.com/p-rum/kgmaker/pull/136) je
`a980b753981da99505434d53b40931d7f40d6996`. Po úvodní validaci manifestu mohl
import publikovat runtime hranu i ze zdroje upraveného během přípravy zápisu.
Tehdejší `src/kgmaker/runtime_evidence.py` při publikaci použil existující
kontrolu `before_replace`. Pod zámkem znovu prověřil celý manifest a
příslušné vstupy včetně zdrojů, v2 compiler kontextu a distribuce workeru.
Při odhalené změně se uložený graf a jeho pohledy vrátily do stavu před
importem. Manifesty v1/v2 a graph/store v3 použily stávající schémata a
příkazy. Následující přenos převzal omezenou kontrolu z #147.

`test_real_jdk21_runtime_import_rejects_source_edit_after_validation` sestaví
a spustí skutečnou JDK21 aplikaci, vezme její volatelné symboly a předá platné
v2 pozorování. V jedné variantě změní zdroj před vstupem do zápisu. Ve druhé ho
změní po skutečné výměně prvního grafového pohledu. V obou případech očekává
`STALE_RUNTIME`, stejné bajty grafu, pohledů i původního runtime artefaktu
a úklid dočasných souborů. Import během kontroly nesmí spustit proces.

- RED — `python -m pytest -p no:cacheprovider -q --tb=short tests/test_runtime_trace_producer.py -k runtime_import_rejects_source_edit_after_validation`
  nad původním produktem a novými testy má 2 FAIL / 76 DESELECTED. Obě
  varianty chybně doběhly bez výjimky. JUnit SHA-256
  `4d7d71f03a818a9948e5ac53d61fb1afd1c94e533f9eeca6db56a58211b99008`.
- GREEN — cílená sada nové regrese, kompatibilního importu a ochrany
  souběžných generací má 5 PASS / 0 SKIP. JUnit SHA-256
  `618fd01c73dbacb761e7c346197dac01a1b30d87a80a5c91e1d48f4fc3ac7c9e`.
- GREEN — skutečný JDK/Javac 21.0.6 a připravený JVM worker ověřily
  139 PASS / 0 SKIP pro runtime, T032 a W06. JUnit SHA-256
  `a9feb3de280d05f620e7246a4e1c7603592d1f9e110e11de241502c96a9d8a20`,
  shodný manifest zdrojů, nástrojů a testů
  `d10a0028b7883c759ad0e7b4dc0911a391e7926d3fd75ad29a5a1bc47e54364c`.
- Úplná standardní sada `python -m pytest -p no:cacheprovider -q --tb=short -ra`
  v CPython 3.13.18 má 2 579 PASS / 1 155 SKIP. JUnit SHA-256
  `1512f7c666e6f54e45090e1e667df4c0191743028bd3d3e4b17522ceefe48276`.
  Manifest zdrojů, nástrojů a testů se před oběma sadami i po nich shoduje.

```bash
PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  python -m pytest -p no:cacheprovider -q --tb=short -ra \
  tests/test_runtime_trace_producer.py tests/test_t032_persist_process_review.py \
  tests/test_graph_publication_concurrency.py
```

[README](../../README.md), [runtime import a CLI](../runtime-trace.md#opakovaný-import-a-navigace),
[compiler příklady](../compiler-inspection.md#pozorované-hrany-a-statické-cesty),
[stavová matice](../production-analysis-progress.md) a
[acceptance inventář](../acceptance-inventory.md#t003-s13-w02--více-dokladů-stejné-pozorované-hrany)
popisují kontrolu a zachování výstupů. GitHub Actions a nezávislé review této
revize dosud čekají. Odvození receiver/type, přesná vazba na call site
a širší T003-AC13 zůstávají `PARTIAL`.

## Dopředný přenos po #147 — T003-S13-W02, kroky 4–5, AC01–AC04

První rodič připraveného přenosu je `ea7b815c4115e37ab31f5a7cada2a3da191f2e13`,
druhý je ověřený `main` `2db5c4931bfd832908158900b2823b6c122bc3a7`.
Úplná validace každého importovaného manifestu proběhne jednou před zámkem.
Při publikaci store nejprve ověří očekávanou generaci grafu. Existující
callback znovu kontroluje zdroje a distribuci workeru a u v2 zachycené
vstupy compiler kontextu včetně bytecode. Změna vstupu vyvolá odmítnutí
a obnovu již nahrazených výstupů.

`src/kgmaker/runtime_evidence.py` současně zachovává doklady jednotlivých
běhů na hraně téhož compiler kontextu, idempotentní import a kontrolu
volatelných symbolů v2 `call` a `dispatch`. `src/kgmaker/callgraph.py`
zobrazuje pozorované doklady v `callers` a `callees`, statické cesty
a cykly vycházejí z compiler call sites. Oba rodiče mají shodné dva případy
změny JDK 21 zdroje při publikaci. `tests/test_runtime_trace_producer.py`
obsahuje tuto fixture jednou, vedle počtů validací z #147, kontroly
skutečného v2 bytecode a kontrolního případu workeru v1.
[Change163](163_revalidateRuntimeImportPublication.md) · [Testy](../../tests/test_runtime_trace_producer.py)

V odděleném auditu obou rodičů skutečné běhy JDK 21 připojily na main
k téže hraně postupně 1, 1, 1 a 1 doklad a na #136 1, 2, 3 a 4.
Totožný import počet nezvýšil. #136 odmítla třídu coby volajícího
bez zápisu a `callgraph path` u pouze runtime hrany vrátil `UNKNOWN`.
Na main byl výsledek `STATIC_PATH` s krokem `RUNTIME_OBSERVED`.
SHA-256 rodičovské sondy #136 je
`151a579f9d2ff93d8f0afd870b569c65b809b24365847fb1cc2ae5b949e76f71`,
main `0cf8494411bd9cb394415396e352c957f5edd6653bd12309630e5faa9d2b653a`.

Sonda `PYTHONPATH=src python probe.py perf --count 8500` na spojeném
kódu napočítala jednu plnou validaci před zámkem. Stejný nástroj
s příkazem `python probe.py compat` ověřil čtyři kombinace v1/v2
s předchozími pohledy i bez nich. Po změně workeru publikaci odmítly
a po jeho obnově přijaly platný import. SHA-256 měření je
`480c0ad645c82dfdf3a9e989332d7cf7d27f7caef95009ebc80b1a1486368be3`
a SHA-256 kontroly kompatibility
`a6801622c54c6614c5917592521defbca837db6b1869f428fcf4804d35e8eb2d`.

Úplná standardní sada `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short`
na čistém archivu spojeného stromu běžela s CPython 3.13.18 a skončila
kódem 0. Výsledek je 2 471 PASS, 1 299 SKIP a jeden očekávaný strict
XFAIL T047-S02. SHA-256 JUnit je
`c5200bacbb23a41508169ec1d542cc54a9c91c0f282325ad81758bfd0f137e1e`.
Manifest sledovaného kódu, nástrojů a testů má před i po běhu SHA-256
`4282e32565efd55139897cde60c27b63d394daa16440f2c1673d70f7c414ff4e`.

Cílený běh s Temurin JDK 21.0.6+7, připravenými workery,
`PYTHONPATH=src:tests`, `KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`
a `JAVA_TOOL_OPTIONS=-XX:-UsePerfData` skončil kódem 0.
Výsledek je 426 PASS a 1 SKIP. Přeskočil pouze volitelný
`test_actual_maven_surefire_pass_and_fail` v rozšířené části sady, kde
nebyla nastavená explicitní cesta k offline Maven repozitáři.
Runtime, W06 a T032 prošly bez přeskočení. SHA-256 JUnit je
`fb1000ae17d6af568a514e25ea21b3f7d8b99b7b7616b43e1ed387e33941064f`.
Manifest sledovaných vstupů před a po běhu se shoduje s úplnou sadou.

```bash
python -m pytest -p no:cacheprovider -q --tb=short \
  tests/test_runtime_trace_producer.py tests/test_build_aware.py tests/test_graph_provider.py \
  tests/test_t032_persist_process_review.py tests/test_graph_publication_concurrency.py \
  tests/test_evidence_ranking.py tests/test_return_consumer_flow.py tests/test_completion.py \
  tests/test_verification_records.py runtime-publication-main-current-test.py
```

Poslední soubor je doplňková kontrola skutečného platného capture z #147,
jehož SHA-256 a příprava jsou uvedeny v [Change163](163_revalidateRuntimeImportPublication.md).

Samostatný
`python -m pytest -p no:cacheprovider -q --tb=short tests/test_verification_records.py::test_actual_maven_surefire_pass_and_fail`
s offline Maven repozitářem, Maven 3.9.9, Surefire 3.5.2 a JDK 21
ověřil dříve přeskočený případ s výsledkem 1 PASS a 0 SKIP.
SHA-256 JUnit je `678bc31d70facc42f82bd179e97703cd8abbf723dae70454c28a088010f05373`.

`PYTHONPATH=src python pr136-multiproof-forward-multirun.py PATH_TO_TRACE`
následně zopakoval čtyři spouštění skutečné JDK 21 fixture na spojeném kódu.
Na původním místě zachyceného kontextu se k hraně připojily 1, 2, 3 a 4
doklady, opakování bylo idempotentní. Třída coby volající byla odmítnuta
bez změny grafu. Import nespustil žádný proces. Přípravný pokus s přemístěnou
kopií fixture skončil odmítnutím zastaralého snapshotu persistence XML.
SHA-256 výsledné sondy je
`73ffb4c14293e35f728596b0a96acc6db13d92e6fc4a1b26c9b6977db737db5d`.

GitHub Actions a Windows na spojeném stromu mají stav `NOT_RUN`.

Sémantické vrstvy z obou rodičů uchovávají 55 konceptů, 192 vztahů
a 374 jedinečných dřívějších epizod. Stejný vztah k funkci
`provenance.event` používá aktuální deklaraci na řádku 166.

Oprava zachovává manifesty v1/v2, graph/store v3 a dosavadní CLI.
Import přijímá explicitní pozorování a surové facts ověřuje.
Skutečný JDK 21 audit ukázal, že štítek `main → greet` z fixture nemá
přímou odpovídající compiler call site. Volání se vykoná uvnitř lambdy.
Odvození typu příjemce a vazby na konkrétní call site z takového štítku
vyžaduje další důkaz. W02 a T003-AC13 zůstávají `PARTIAL`.
[README](../../README.md) · [Runtime příklady](../runtime-trace.md#opakovaný-import-a-navigace) · [Compiler navigace](../compiler-inspection.md#pozorované-hrany-a-statické-cesty) · [Acceptance](../acceptance-inventory.md#t003-s13-w02--více-dokladů-stejné-pozorované-hrany) · [Stav](../production-analysis-progress.md)

## Přenos po sloučení #148 — T003-S13-W01-AC01 a T003-S13-W02-AC01–AC04

První rodič je `c2e95614cf9d0b924aa0c390281617746a65ba49` se stromem
`d88229d3ccfb9249a0868a714eea7acbd7f75366`. Druhý rodič je
`385943e48d2d2e60cec541f1f0db78beda83de22` se sloučeným #148.
Předchozí úplná sada a sonda čtyř dokladů patří prvnímu rodiči.

Veřejný build-import a compiler inspekce z #148 předávají otisk
deklarované konfigurace vybrané varianty do v2 capture. Původ
BuildManifestu a hranice deklarovaného otisku mají stávající kontrakt.
`build_model.py` a `test_build_runner.py` se shodují s druhým rodičem.
Obsah `runtime_evidence.py` a `callgraph.py` se shoduje s prvním rodičem.
Zachovává doklady více běhů, typovou kontrolu, oddělení statického
průchodu od runtime pozorování a jednu plnou validaci před zámkem
s opakovanými kontrolami čerstvosti při publikaci. Testovací modul
uchovává všech 31 definic testů a fixture z obou rodičů.
[BuildManifest a příklad](165_forwardBuildConfiguration.md) · [Publikace](163_revalidateRuntimeImportPublication.md) · [Runtime CLI](../runtime-trace.md)

Společný kandidát s reálným Mavenem 3.9.9, Temurin JDK 21.0.6+7
a připravenými JVM/build workery má 160 PASS a 0 SKIP. Zahrnuje skutečný
veřejný Maven build → inspekce → v2 capture, typované a opakované importy,
kontrolu generačního konfliktu W06, rollback po změně zdroje i bytecode
a procesní regresi T032. JUnit SHA-256
`bace4b68f0ea1e3448c86bf2ca9fedeffa70e5063924ff4e3d3a4e8ce620cdb1`.
Před a po běhu se shoduje manifest sledovaného kódu, fixture a testů
`954b6830bee984ed0f1a57aa9c636748a1d868b67be3b4a110eec91e750fcb4d`
i manifest instalovaných nástrojů
`6fceeb1dd1d54531cca968ec9a0f8919d7fab40035838a6845c99ed8c41dffb5`.
Provozní nástroje nastavuje stejný Maven launcher jako [Change165](165_forwardBuildConfiguration.md).

```bash
python -m pytest -n 2 -p no:cacheprovider -q --tb=short \
  tests/test_runtime_trace_producer.py tests/test_build_aware.py tests/test_graph_publication_concurrency.py \
  tests/test_t032_persist_process_review.py \
  tests/test_graph_provider.py::test_scan_hook_and_feature_retain_compiler_layer_without_processes \
  tests/test_build_runner.py::test_build_context_config_fingerprint_comes_from_selected_context \
  tests/test_build_runner.py::test_build_manifest_rejects_invalid_context_config_fingerprint
```

Inventář eviduje přenos deklarovaného otisku W01 jako sloučený
v [#148](https://github.com/p-rum/kgmaker/pull/148). Ověření W01 zůstává
`PARTIAL`. W02 zůstává `PARTIAL` v rozsahu importu doložených pozorování.
Odvození skutečného typu příjemce, vazba ke konkrétnímu call site a úplná
identita okolního runtime prostředí mají další vlastní rozsah.
[Stav](../production-analysis-progress.md) · [Acceptance](../acceptance-inventory.md)

Sonda `PYTHONPATH=src python pr136-after148-multirun.py PATH_TO_TRACE`
použila skutečný v2 capture z veřejné Maven/JDK fixture výše. K hraně
připojila postupně 1, 2, 3 a 4 doložené běhy. Opakovaný import počet
nezvýšil a třídu v roli volajícího odmítl bez změny grafu. Při importu
neběžel žádný proces. Uložený BuildManifest i původní v2 capture
zůstaly po bajtech shodné. SHA-256 sondy je
`fcdd1bd10711e1629c232bacff07218a69165b1fe0aa02f243185517a1441d09`.

Sémantická vrstva uchovala 55 konceptů, 192 vztahů a 377 jedinečných
epizod z rodičů. Citace 12 konceptů a 26 vztahů v compiler příručce
ukazují po vložení textu #148 na přesně stejný text o sedm řádků níž.
Úplná sada, Windows a GitHub Actions na tomto novém stromu mají stav `NOT_RUN`.

## Revize po steelman review — T003-S13-W02, kroky 3–5, AC01 a AC03

Výchozí commit je `2f4cfad7d3d327d2a9627f57db22bd25549f32a1` a
ověřený základ `385943e48d2d2e60cec541f1f0db78beda83de22`.
Nezávislé review zjistilo, že v2 import držel odkaz na vstupní slovník
`source_identity`. Změna slovníku po výpočtu ID a před zápisem vedla
k uložení jiného otisku, než z jakého vzniklo ID dokladu.

`runtime_evidence.py` používá pro ověřený manifest v2 vlastní slovník
ze dvou již vypočtených otisků compiler kontextu. Oba jeho řetězce
prošly existujícím porovnáním v původní validaci. Doklad a jeho ID
vycházejí z týchž hodnot. Publikační callback dál opakuje jen kontrolu
měnitelných vstupů. Formáty v1/v2 a graph/store v3 zůstávají čitelné
stávajícím CLI. [Kontrakt runtime](../runtime-trace.md) · [Acceptance](../acceptance-inventory.md)

Regrese `test_real_jdk21_v2_import_detaches_identity_before_publication`
vyvolá změnu vnořeného slovníku přímo na vstupu do `save_graph`.
Ověří původní otisky, soulad ID s obsahem uloženého dokladu, nezměněný
capture a nespouštění procesů během importu.
Na výchozím kódu skončil tento test s JDK 21 kódem 1. Uložený doklad
převzal nulový otisk vložený po validaci. SHA-256 JUnit je
`0e4e97569d7fa59a778e1d2efa31b579a0d0f335d244f3833d5dc0d1960d0564`.

Obnova sémantického souboru zachovává pořadí záznamů z main a navazuje
chybějícími historickými epizodami i novým záznamem. Hodnoty původních
objektů se zachovávají při regeneraci grafu. Obsahová kontrola odděluje
změnu pořadí od skutečných přírůstků v historii.

- **Opravený kód, Maven 3.9.9 a JDK 21.** Příkaz cílené sady z
  předchozího kroku ověřil 161 PASS a 0 SKIP, včetně nové regrese,
  veřejné konfigurace a publikačních kontrol W06. JUnit SHA-256
  `292a5cf8d4bd9762d3fb6983b95520fc249f1b0adf428a36dd822c51b49ac091`.
  SHA-256 shodných manifestů před i po běhu je pro zdroj, fixture a testy
  `98d5d4d6cbdb57178c0e773e9902b2009e5171a47955afcb8424a3eddfcd238b`
  a pro externí nástroje
  `6fceeb1dd1d54531cca968ec9a0f8919d7fab40035838a6845c99ed8c41dffb5`.
- **Sonda z review.** `PYTHONPATH=src:tests python probe.py FIXTURE_DIR`
  proběhla s JDK 21 a nezměněným skriptem SHA-256
  `6e28dd6f0219b8af3c13fb68c6ac0fef5e3e0de4c4d05709fa8aeb0340d2f3b6`.
  Po změně vstupního slovníku se očekávaný a uložený otisk shodovaly
  a souhlasil i digest dokladu. Počty dokladů byly 1, 2 a 2.
  Statická cesta hlásila `UNKNOWN`, původní capture měl stejné bajty.
  Výsledný JSON má SHA-256
  `bd9976704aaae8f03e0d1510c7d5cdfbce762c82d3da16d1cf2e7940ddbce998`.
- **Úplná standardní sada.**
  `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short`
  v čistém archivu s testovanými zdroji a CPython 3.13.18 měla
  2 482 PASS, 1 301 SKIP a jeden očekávaný strict XFAIL T047-S02.
  JUnit SHA-256 `1e41aa57a5ff114e3b64a0feb77381bc2a35401301e2f65b0f53a5996e0a354b`.
  Manifest sledovaných vstupů se shoduje s cílenou sadou.
- **Příprava testgen.**
  `kgmaker testgen prepare --id pr136-source-identity --target src/kgmaker/runtime_evidence.py --scope production --framework pytest --token-budget 100000`
  na archivu výchozího commitu skončila kódem 2 s důvodem
  `Token budget cannot hold target evidence`. Regrese používá existující JDK fixture.

Windows a GitHub Actions mají pro tuto revizi stav `NOT_RUN`.
Rozsah receiver/type a skutečného call site zůstává `PARTIAL`.

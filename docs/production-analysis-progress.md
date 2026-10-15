# Aktuální stav a zbývající práce

Audit baseline: 2026-10-15, PR #5 `6b5aea13c150a75858973dd2e08debf802ff29ed`,
stacked nad PR #4 `a81def9dbc74fff3a5619cd02244be7f215f91cc`; main je
`8ac80ca30f6f680539deb7fb3590519d3a5c1460`. Tato stránka popisuje kód této baseline,
neprohlašuje změny draftů za sloučené do main.

Normativní požadavky: [registr T001–T003](tasks/README.md).
Aktivní pořadí dokončení: [T003](tasks/3_finishProductionAnalysis.md).
PARTIAL znamená existující omezený rozsah; neznamená splněný celý milník.

| Oblast / etapa dokončení | Stav baseline | Implementováno a evidence | Zbývá |
|---|---|---|---|
| T003-S01 acceptance inventář | PARTIAL | T001/T002 a mapování historických ID; tests/fixtures | Úplný řádkový požadavek→test→verze→běh inventář |
| T003-S02 lifecycle/provider | PARTIAL | v1/v2/v3 store, provenance, atomický zápis; test_inspection_contract | Scan/hook přepisují compiler index; feature/workspace nepřebírají všechny compiler kontexty |
| T003-S03 build a scope | PARTIAL | Classifier/scope před resolution, Maven EventSpy, Gradle SourceSet export, runner; test_production_scope/test_build_runner | Reactor/BOM/toolchains/generated/variant matice a cross-repo artefakty |
| T003-S04 JVM/Kotlin | PARTIAL | JavacTask, K1 compatibility, ASM, 5 ručně anotovaných direct calls; test_compiler_workers | K2, širší Kotlin/CFG a dependency dispatch |
| T003-S05 Spring | NOT_STARTED (symbolový adaptér) | Legacy annotation patterns v domain.py | Beans/injection/conditions/proxy/entrypoint model |
| T003-S06 persistence | PARTIAL | Flyway replay, explicitní omezené Kotlin ORM porovnání; test_flyway | Java/Kotlin entity access/naming/association/query model |
| T003-S07 integrations/dataflow | PARTIAL | Literály, explicitní workspace service mapping, lokální field edges; test_dataflow/test_workspace | Framework-aware Kafka/HTTP a úplné validované datové cesty |
| T003-S08 TS/UI | PARTIAL | Program/TypeChecker, overloads a React event binding | Multi-project/re-export, callback a BE–FE value flow acceptance |
| T003-S09 artifacts/report | PARTIAL | Feature lifecycle/report, offline HTML docs; test_feature/test_data_check | XLSX, template mapping, schválená metodika a plný scénář |
| T003-S10 incremental | PARTIAL | Semantic diff, workspace cache, Flyway checkpoints | Selektivní compiler/feature invalidace a negativní lookup dependencies |
| T003-S11 release/acceptance | PARTIAL | Šest CI jobů, skutečné buildy, rendering; core package | Clean-install worker distribuce, celá acceptance a benchmark budgets |
| T003-S12 Confluence boundary | NOT_STARTED | Existující read-only HTML import není sync adapter | Adapter/fake/approval/concurrency; živé připojení zvlášť |
| T003-S13 runtime | NOT_STARTED / OPTIONAL | Supplied value observations nejsou plný runtime call import | Trace/export import s build/config scope |

## Co lze nyní použít

Source-only navigaci, konzervativní impact, semantic/feature/data-audit workflow,
Flyway a explicitní workspaces v dokumentovaných mezích. Availability podporuje
OBSERVED_VALUE_PATH, CLOSED_CONTRACT_ABSENCE a APPROVED_MISSING; libovolné pole,
statická cesta ani build PASS pozitivní verdict nezískají. Compiler commands jsou
použitelné samostatně v [ověřené matici](compiler-inspection.md), nikoli jako hotová
integrovaná Spring/Kotlin analytická platforma.

## Kritická návaznost

`feature.current_graph()` sestavuje syntaktický/semantic/Flyway graf.
`cli.scan()` a `cli.hook_context()` tento typ grafu uloží přes compiler index.
`inspection.py` začíná ze scan baseline a není hotový multi-context provider.
Proto se před dalšími frameworky prioritně implementuje T003-S02. Dokumentační
sjednocení tyto runtime mezery neopravuje.

## Ověřená upstream CI evidence

[Run 38705043005](https://github.com/p-rum/kgmaker/actions/runs/38705043005) na
`6b5aea1`: SUCCESS všech šesti jobů — Python 3.11/3.12/3.13, compiler-workers,
gradle-build-export, rendering. Compiler job log: 29 passed; Maven JUnit fixture:
1 test, 0 failures/errors/skipped. Nejde o celou mandatory acceptance matrix ani
měření přesnosti na bankovním projektu.

Historické inkrementální výsledky a přesné verze jsou beze změn v
[1_addProductionScope.md](changes/1_addProductionScope.md) a
[2_addCompilerWorkers.md](changes/2_addCompilerWorkers.md). Jejich P/CL/JV apod.
označení jsou historická; aktivní číslování a převod je pouze v registru.

## Aktualizace stavu

Při implementaci u každé změněné položky uveď Task/Step/Acceptance ID, konkrétní
fixture/test/verze a odkaz na skutečný běh. PARTIAL není PASS. Neprovedená kontrola
je NOT_RUN/blocked, ne úspěch. Historické výsledky nepřepisuj na výsledky nového commitu.

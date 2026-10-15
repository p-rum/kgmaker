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
| T003-S01 acceptance inventář | VERIFIED_IN_SCOPE | [řádkový inventář T001/T002](acceptance-inventory.md) uvádí stav, verzi, konkrétní test a běh; chybějící varianty jsou PARTIAL/NOT_IMPLEMENTED | Udržovat při každé změně scope/verze/běhu; implementační mezery řádků nejsou splněním jejich etap |
| T003-S02 lifecycle/provider | PARTIAL | v1/v2/v3 store, provenance, atomický zápis; scan/hook/feature selektivně vyřadí stale compiler layer s důvodem/next command a zachovají ostatní; module/profile contexts se akumulují; workspace schema v3 přenáší repo-qualified symbols/call sites/CFG/evidence/annotations; `test_graph_provider`, `test_workspace`, `test_compiler_workers` | Jednotný explicitní context selection pro query/impact/feature/report a celý AC02 end-to-end scénář včetně profilu/classpath/packet invalidace |
| T003-S03 build a scope | PARTIAL | Classifier/scope před resolution, read-only Maven reactor discovery, Maven EventSpy, Gradle SourceSet export, runner/import; `test_production_scope`, `test_build_runner`, `test_build_aware` | Reactor/BOM/toolchains/generated/variant matice a cross-repo artefakty |
| T003-S04 JVM/Kotlin | PARTIAL | JavacTask, K1 compatibility, ASM, 5 ground-truth direct calls with overloads/CFG; `test_compiler_workers` and JVM rendering | K2, širší Kotlin/CFG, dependency dispatch a complete acceptance bank |
| T003-S05 Spring | PARTIAL | Explicit JVM inspection adds `FRAMEWORK_DERIVED` bean, injection, qualifier/primary/profile boundary, entrypoint, advice and self-invocation proxy facts; `test_build_aware` | Conditions/custom registrars, full profile/property variants, runtime proxy execution and async semantics |
| T003-S06 persistence | PARTIAL | Flyway replay plus explicit Java annotation entity/table/column binding, schema resolution and Spring Data/query projection; `test_flyway`, `test_build_aware` | Kotlin entity access, naming/association/query grammar and multi-datasource variants |
| T003-S07 integrations/dataflow | PARTIAL | Literály, explicitní workspace service mapping, lokální field edges; test_dataflow/test_workspace | Framework-aware Kafka/HTTP a úplné validované datové cesty |
| T003-S08 TS/UI | PARTIAL | Program/TypeChecker, overloads a React event binding | Multi-project/re-export, callback a BE–FE value flow acceptance |
| T003-S09 artifacts/report | PARTIAL | Feature lifecycle/report, offline HTML docs; bounded XLSX sheets/cells/named ranges/formula dependencies and hash-bound locators; literal Thymeleaf model bindings and explicit PDF boundary; `test_feature`, `test_data_check`, `test_workbooks`, `test_templates` | Širší template mapping, schválená metodika a plný scénář; formula evaluation zůstává non-goal |
| T003-S10 incremental | PARTIAL | Semantic diff, workspace cache, Flyway checkpoints | Selektivní compiler/feature invalidace a negativní lookup dependencies |
| T003-S11 release/acceptance | PARTIAL | Šest CI jobů, skutečné buildy, rendering; core package | Clean-install worker distribuce, celá acceptance a benchmark budgets |
| T003-S12 Confluence boundary | VERIFIED_IN_SCOPE / LIVE NOT_RUN | Adapter protocol, `FAKE_TEST_ONLY`, explicit pull, managed-section diff, hash+base-version approval, optimistic concurrency, TO_BE re-import and audit; `test_confluence_sync` covers FA-28–30/AC12 | Live connector requires a documented host/API/auth contract and remains separately NOT_RUN |
| T003-S13 runtime | PARTIAL / OPTIONAL | Hash-bound `runtime import` validates context/build/config/source/worker scope and adds `RUNTIME_OBSERVED`; stale source is rejected; `test_build_aware` | Trace/export producer, RTA/value flow, async/reflective capture and deployment/data availability |

## Co lze nyní použít

Source-only navigaci, konzervativní impact, semantic/feature/data-audit workflow,
Flyway a explicitní workspaces v dokumentovaných mezích. Availability podporuje
OBSERVED_VALUE_PATH, CLOSED_CONTRACT_ABSENCE a APPROVED_MISSING; libovolné pole,
statická cesta ani build PASS pozitivní verdict nezískají. Compiler commands jsou
použitelné samostatně v [ověřené matici](compiler-inspection.md). JVM inspection
navíc vytváří omezené Spring/JPA důkazy a runtime import přijímá jen hashově
svázaný export; nejde o hotovou integrovanou Spring/Kotlin analytickou platformu.

## Kritická návaznost

`graph_provider.py` nyní ověřuje každý uložený compiler context a single-root
`feature.current_graph()`, scan a hook zachovávají čerstvé vrstvy. Stale vrstva
ztratí compiler fakta, ale zůstane jako diagnostický context s next command; jiné
module/profile vrstvy se zachovají. Testy `tests/test_graph_provider.py` ověřují
nulové procesy, selektivní projekci a nulovou mutaci před explicitním scan/hook;
`test_offline_refresh_preserves_real_call_sites_and_cfg` ověřuje skutečný JVM
výstup. Multi-context module/profile akumulaci a nulovou mutaci při selhání pokrývají
další provider testy. `test_workspace_preserves_repo_qualified_compiler_collections`
ověřuje workspace schema v3. Jednotný context selection a celý T003-AC02 sled proto
ještě nejsou VERIFIED.

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

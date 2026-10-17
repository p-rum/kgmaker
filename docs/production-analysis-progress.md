# Aktuální stav a zbývající práce

Audit baseline: 2026-10-15, PR #5 `6b5aea13c150a75858973dd2e08debf802ff29ed`,
stacked nad PR #4 `a81def9dbc74fff3a5619cd02244be7f215f91cc`; main je
`8ac80ca30f6f680539deb7fb3590519d3a5c1460`. Tato stránka popisuje kód této baseline,
neprohlašuje změny draftů za sloučené do main.

Normativní požadavky: [registr T001–T003](tasks/README.md).
Aktivní pořadí dokončení: [T003](tasks/3_finishProductionAnalysis.md).
PARTIAL znamená existující omezený rozsah; neznamená splněný celý milník.

## Stav pracovního rozšíření 2026-10-16

Rozdělaný podúkol persistence/query modelu je dokončen v podporovaném rozsahu
**JPA rules v4**. Implementace rozlišuje Entity/Embeddable/MappedSuperclass,
FIELD/PROPERTY access, EmbeddedId a AttributeOverride, owning/inverse asociace,
bounded derived query parsing, compiler-owned JPQL/native `@Query`, parametry,
projekce a reference na named query. Doložené kontroly jsou
`test_ac06_real_javac_embedded_id_and_association_roles`,
`test_hb01_embedded_id_and_bidirectional_association_preserve_roles` a celý
lokální běh `python3 -m pytest -q` — **197 passed in 45.14 s**.

Tento výsledek uzavírá pouze uvedený podúkol, nikoli T003-S06 ani celý T003.
Zbývající rozsah je nyní rozdělen na atomické specifikace
[T003-S03-W01 až T003-S13-W04](tasks/README.md#atomické-work-packages-pro-dokončení-t003).
Další implementace se provádí po jednom work package ve vlastní větvi a samostatném
pull requestu. Stav každého zůstává SPECIFICATION, dokud jeho PR nedoloží požadované
testy a akceptační kritéria.

Každý z 60 work packages má projektový implementační profil v `.codex/agents`.
Profily používají `gpt-5.6-luna` s effort `medium`, odkazují na přesné zadání a
doporučenou větev a vyžadují testy, sémantickou aktualizaci, change note, commit,
push a samostatný PR. Jde pouze o připravené vykonavatele; žádný profil sám nemění
stav work package ani nedokládá splnění jeho acceptance.

| Oblast / etapa dokončení | Stav baseline | Implementováno a evidence | Zbývá |
|---|---|---|---|
| T003-S01 acceptance inventář | VERIFIED_IN_SCOPE | [řádkový inventář T001/T002](acceptance-inventory.md) uvádí stav, verzi, konkrétní test a běh; chybějící varianty jsou PARTIAL/NOT_IMPLEMENTED | Udržovat při každé změně scope/verze/běhu; implementační mezery řádků nejsou splněním jejich etap |
| T003-S02 lifecycle/provider | VERIFIED_IN_SCOPE | v1/v2/v3 store, provenance, atomický zápis; scan/hook/feature selektivně vyřadí stale compiler layer s důvodem/next command a zachovají ostatní; status/check/hook rozlišují source a compiler freshness bez spuštění procesu; module/profile contexts se akumulují; query/impact/feature/validate/report používají uložený explicitní scope/context a zachovávají společnou source/dataflow vrstvu; workspace schema v3 přenáší repo-qualified symbols/call sites/CFG/evidence/annotations; reálný `test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle` plus provider/workspace regrese | Rozšíření podporované matice patří do navazujících S03–S10; není tvrzena úplnost mimo zdokumentovaný scope |
| T003-S03 build a scope | PARTIAL | Classifier/scope před resolution, read-only Maven reactor discovery, Maven EventSpy `maven-session-2` s parent/BOM/effective dependencies/dependency management/profily/compiler release/toolchain/generated roots, Gradle SourceSet/generated-root export, runner/import; reálný `test_mv02_real_reactor_output_precedes_stale_repository_jar` ověřuje profilovou změnu manifestu, inherited BOM, přednost reactor outputu a content-bound annotation-processor source až po JVM symbol s `origin=generated`; `test_production_scope`, `test_build_runner`, `test_build_aware` | Externí toolchain selection, Gradle custom varianty/included builds, Kotlin options a cross-repo artefakty |
| T003-S04 JVM/Kotlin | PARTIAL | JavacTask, K1 compatibility, ASM, 5 ground-truth direct calls with overloads/CFG; izolované testy ověřují konstruktor, primary-constructor property/init pořadí, file-facade `<clinit>`, oddělený object constructor realm, lambda caller, callable reference, source-defined operator v CFG, custom getter/setter method+CFG+ACCESSOR a extension/default/inline/suspend metadata; when/Elvis/short-circuit/try/finally/break/continue mají strukturovaný IR/CFG; `test_compiler_workers`, `test_control_flow` a JVM rendering | K2/Analysis API, default-body/coroutine source mapping, širší corpus, dependency dispatch a úplná acceptance banka |
| T003-S05 Spring | PARTIAL | Spring rules v3 přidávají context-bound `FRAMEWORK_DERIVED` bean/injection, qualifier/primary, ACTIVE/INACTIVE/UNKNOWN pro Profile/ConditionalOnProperty/ConditionalOnClass/custom Conditional, `injects_bean` jen pro unikátní ACTIVE a `may_inject_bean` pro ambiguity/UNKNOWN; bounded compiler-symbol meta-stereotype chain, explicitní package/subpackage component-scan scope, statický `@Import` konfigurační graf s děděním conditions, validaci `@Bean` owneru a collection/map/optional/provider injection; entrypoint, advice a self-invocation proxy boundary; reálný `test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard` dokládá AC05 v podporované matici | Dynamic ImportSelector/registrars/factories, širší property/classpath varianty a runtime proxy/async execution |
| T003-S06 persistence | PARTIAL | Flyway replay plus JPA rules v4: oddělené Entity/Embeddable/MappedSuperclass, FIELD/PROPERTY identity placement, EmbeddedId/AttributeOverride, association target a OWNING/INVERSE `mappedBy`, explicitní join bez falešného scalar column, entity/table/column realm binding; bounded derived query validace; compiler-owned JPQL/native `@Query` s parametry, entity/projection return a named-query reference; reálný javac `test_ac06_real_javac_embedded_id_and_association_roles`, kontraktní `test_hb01_embedded_id_and_bidirectional_association_preserve_roles`, `test_flyway` | Kotlin use-site/access varianty, XML overrides, inheritance attributes, širší JPQL/HQL/native grammar, NamedQueries containers, Criteria/Specification/QueryDSL a úplná multi-datasource matice |
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
ověřuje workspace schema v3. `test_feature_requires_and_persists_explicit_context_for_variants`
ověřuje odmítnutí nejednoznačné varianty a stabilní packet projekci. Regrese
`test_status_separates_current_source_graph_from_stale_compiler_context` dokládá,
že source-current stav nezakrývá stale compiler context a offline status/check
nespouštějí proces. Rozšířený workspace test dokládá stejný kontrakt pro
repo-qualified context a připouští pouze read-only Git baseline proces.
`test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle` používá skutečný
JVM worker a ověřuje `inspect → scan → hook-context → query/impact → feature
prepare/validate/apply/report`, dvě profilové varianty, packet revision a classpath
invalidaci. T003-AC02 je tím VERIFIED_IN_SCOPE pro publikovanou matici; širší build,
framework a incremental varianty zůstávají v S03–S10.

## Ověřená upstream CI evidence

Lokální navazující běh 2026-10-16: `python3 -m pytest -q` — **197 passed in
45.14 s**. Přibylo skutečné Maven reactor/stale-JAR ověření včetně inherited
profilu, BOM/effective modelu, content-bound generated source s JVM origin důkazem
a toolchain metadata, TypeScript re-export
a lockfile invalidace, explicitní ORM realm/naming boundary a schválená Confluence
metodika s decision provenance. Query/impact mají explicitní context selection;
feature packets nesou uložený scope/context, context fingerprint a graph evidence
IDs. S02/AC02 jsou ověřené v podporované matici; tyto kontroly neuzavírají celé
S03/S06/S08/S09 ani další povinné etapy.

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

## T003-S09-W04 — hash-bound approved methodology

VERIFIED_IN_SCOPE: existing implementation-vs-approved-requirement conflict behavior is preserved. Feature packets now verify exported pages, attachments and approval-sidecar content before reusing conflicts. Stale/legacy indexes are omitted with a limitation; duplicate assertion decisions and unextractable approvals leave the previous cache unchanged. `tests/test_methodology_conflicts.py` covers two page versions, stale sidecar, legacy index and ambiguity; `tests/test_scanner.py::test_fa21_approved_requirement_conflict_preserves_authority` covers conflict provenance. Local `PYTHONPATH=src python3 -m pytest -q`: 203 passed in 39.44 s with `KGMAKER_REQUIRE_WORKERS=1` and reused existing baseline build outputs. This does not complete T003-S09.

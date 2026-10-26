# Aktuální stav a zbývající práce

## T003-S11-W01 — instalace workerů mimo checkout (2026-10-26)

VERIFIED_IN_SCOPE pro Linux / Python 3.12: resource package `kgmaker_workers`,
sdist/wheel s předem připravenými volitelnými JVM/TS artefakty, deterministická
precedence a chybová diagnostika bez fallbacku explicitní volby.
`tests/test_worker_install.py`: 7 PASS s reálnou Java/TypeScript analýzou mimo
checkout a core instalací bez JDK/Node nebo child procesů. Schema/protocol se
nemění. [Change note 30](changes/30_packageWorkerResources.md) zaznamenává buildy
a kontroly; compiler CI nyní vyžaduje také instalační acceptance.
Celý T003-S11 zůstává PARTIAL; Windows, immutable publication, zbývající
acceptance/benchmark matice a navazující T003/T004 nejsou tímto dokončeny.

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

T045 přidává projektový profil `code_review` pro review vytvořených PR a merge po
`APPROVE` nad aktuálním HEAD, zelených required checks a ověření cílové větve.
Jde o nakonfigurovaný proces; skutečné review a merge jednotlivých PR se
dokládají jejich GitHub stavem a nejsou tímto odstavcem prohlášeny za hotové.
Historický draft PR #4 a měnící se draft PR #8 nejsou schválené merge kandidáty.

| Oblast / etapa dokončení | Stav baseline | Implementováno a evidence | Zbývá |
|---|---|---|---|
| T003-S01 acceptance inventář | VERIFIED_IN_SCOPE | [řádkový inventář T001/T002](acceptance-inventory.md) uvádí stav, verzi, konkrétní test a běh; chybějící varianty jsou PARTIAL/NOT_IMPLEMENTED | Udržovat při každé změně scope/verze/běhu; implementační mezery řádků nejsou splněním jejich etap |
| T003-S02 lifecycle/provider | VERIFIED_IN_SCOPE | v1/v2/v3 store, provenance, atomický zápis; scan/hook/feature selektivně vyřadí stale compiler layer s důvodem/next command a zachovají ostatní; status/check/hook rozlišují source a compiler freshness bez spuštění procesu; module/profile contexts se akumulují; query/impact/feature/validate/report používají uložený explicitní scope/context a zachovávají společnou source/dataflow vrstvu; workspace schema v3 přenáší repo-qualified symbols/call sites/CFG/evidence/annotations; reálný `test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle` plus provider/workspace regrese | Rozšíření podporované matice patří do navazujících S03–S10; není tvrzena úplnost mimo zdokumentovaný scope |
| T003-S03 build a scope | PARTIAL | Maven reactor/EventSpy a content-bound `--java-home`; skutečný reactor/generated-source test. Gradle W02 validuje explicitní SourceSet scope a freshness, W03 exportuje snapshot-bound included builds s jednoznačným output realm a ordered classpath. W04 přenáší validované task/execution-level Kotlin compiler/language/API/JVM options, flags a plugin provenance do manifestu a context identity; `test_kotlin_build_options.py` ověřuje Maven 2.1.10, Gradle 8.13, selektivní invalidaci a fail-closed tamper. Workspace `release_mapping` v1 propojí validní regular-file BuildManifest output s regular-file fresh compiler classpath podle SHA-256; `test_cross_repo_artifacts.py` dokládá tento omezený scope; konflikt či adresář zůstávají PARTIAL. | Další Gradle variant API a úplná produkční matice; zachycená konfigurace nerozšiřuje K1 analyzér |
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

Revize T003-S03-W04: Maven exporter označuje nerozřešené implicitní
language/API defaults jako PARTIAL s diagnostikou místo invalidního placeholderu;
plugin descriptor classpath včetně skutečného `all-open` JAR nese SHA-256 a
změna souboru zneplatní manifest před zápisem. Plná sada s povinnými workery,
Maven, Gradle 8.13 a JDK21/22: 213 PASS, 0 SKIP. S03 zůstává PARTIAL.

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

Samostatná větev T003-S03-W01 následně ověřila explicitní `--java-home`,
content-bound JDK binárky a mismatch bez fresh outputs: focused skutečný Maven
scénář **3 passed in 4.16 s**, compiler workers **14 passed in 26.67 s** a celý
suite **199 passed in 46.03 s**. Jde o dokončení W01, nikoli celého S03.

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

T003-S03-W01: skutečná Maven fixture `test_external_toolchain_two_real_jdks` ověřuje explicitní launcher JDK21+22 a odlišné manifest fingerprints. JDK17 s aktuálním exporter bytecode není podporované; Maven compiler-plugin fork selection není tímto důkazem pokryto. Milník S03 zůstává PARTIAL; [evidence](changes/10_selectExternalToolchain.md).
## T003-S03-W02 — custom Gradle source sets

VERIFIED_IN_SCOPE for `gradle-source-sets-2`: explicit per-project custom scope
mapping, exact built-ins, unknown/invalid declaration diagnostics and additive
scope provenance. `tests/test_gradle_variants.py` uses actual Gradle 8.13 for
main/test/generated/custom/unknown plus offline ambiguity and no-mutation tests.
Android/KMP variant APIs and included builds remain outside this work package;
T003-S03 remains PARTIAL. Final mandatory full suite: 206 passed in 55.56 s (JDK21/22, JVM/TS workers, Gradle8.13), no skips. See [change note13](changes/13_importGradleSourceSetScopes.md).

## T003-S03-W02 review opravy (2026-10-19)

Source snapshot nových JVM contextů je module/source-set qualified místo pouhého
scope; offline scan/hook zachovají variantu po editaci sibling source setu stejného
scope. Vybrané resources a sdílené build/config inputs nadále invalidují kontext.
GRADLE_CONVENTION přijímá pouze main/production, test/test a testFixtures/test_fixture;
legacy manifest bez provenance zůstává čitelný. Testy a aktuální celý běh jsou v
[change note13](changes/13_importGradleSourceSetScopes.md). S03 zůstává PARTIAL.

## T003-S03-W03 — captured composite builds

VERIFIED_IN_SCOPE for `gradle-composite-1` / Gradle8.13: snapshot-contained included
builds preserve repo-qualified source/context identity, existing classpath realm
dependencies and deterministic Gradle order. Duplicate lib modules are separate;
current included output replaces a stale external artifact through actual Gradle
substitution. Ambiguous artifact ownership is diagnosed without a chosen realm.
Imported classpath realm requires a unique execution-bound producer output with
matching path/hash/identity; forged and ambiguous claims fail before store mutation.
`tests/test_gradle_included.py` provides actual toolchain and negative evidence;
rebased review-fix full suite 221 PASS, 0 SKIP (including strengthened classpath order fixture). Outside-snapshot roots remain UNBOUND/PARTIAL; T003-S03 remains PARTIAL.
See [change note17](changes/17_exportGradleIncludedBuilds.md).

T003-S03-W05: `test_cross_repo_artifacts.py` ověřuje `release_mapping` v1 nad
dvěma producenty se stejným GAV a class name, ale různými JAR bytes. Pouze shodný
BuildManifest output a compiler classpath hash vytvoří `supplies_classpath`;
mismatch/duplicate zůstává PARTIAL a invalidní kontrakt zachová poslední store.
Adresář se shodnými `.class`, ale rozdílným resource souborem je explicitně
odmítnut jako unsupported kind a nevytvoří hranu.
Runtime deployment ani mapování podle názvu tím není tvrzeno; [evidence](changes/29_mapCrossRepoArtifacts.md). Integrovaný strict běh nad W01–W05: 242 PASS, 0 SKIP.

## T005 — společný model pohledu (integrace 2026-10-26)

T005 dodává `architecture_model.py`, čistý validator a JSON Schema view v1.
Implementace nepřidává discovery, CLI ani renderery a nezvyšuje evidence.
T004 a T006–T044 zůstávají SPECIFICATION; existující graph v1/v2/v3 se nemění.
Ověření modelu a integrace s aktuálním main je uvedeno v
[change note 11](changes/11_addViewModel.md). Historické výsledky ostatních
work packages výše zůstávají beze změny.

## T003-S09-W04 — hash-bound approved methodology

VERIFIED_IN_SCOPE: existing implementation-vs-approved-requirement conflict behavior is preserved. Feature packets now verify exported pages, attachments and approval-sidecar content before reusing conflicts. Stale/legacy indexes are omitted with a limitation; duplicate assertion decisions and unextractable approvals leave the previous cache unchanged. `tests/test_methodology_conflicts.py` covers two page versions, stale sidecar, legacy index and ambiguity; `tests/test_scanner.py::test_fa21_approved_requirement_conflict_preserves_authority` covers conflict provenance. Local `PYTHONPATH=src python3 -m pytest -q`: 203 passed in 39.44 s with `KGMAKER_REQUIRE_WORKERS=1` and reused existing baseline build outputs. This does not complete T003-S09.

T003-S09-W04 integration 2026-10-26 against main `0c09028`: focused methodology/feature/scanner **56 PASS**, full suite **229 PASS, 21 SKIP** without prepared toolchain artifacts. Attachment change/deletion now has explicit offline/no-process and no-index-mutation evidence; historical strict evidence remains above. [Change note 9](changes/9_bindMethodologyApproval.md).

Prepared packets revalidate documentation conflict coverage outside checkout too; three external HTML/approval/attachment mutation tests reject stale approval without mutating packet/index.

Final integration run after external-packet freshness fix: **232 PASS, 21 SKIP** (5.00 s); focused **56 PASS**. Strict attempt blocked by missing actual Maven fixture (14 setup errors), documented in change note9; no worker PASS is claimed for this environment.

After actual Maven fixture preparation, final strict integrated run **246 PASS, 7 SKIP** (84.81 s); both real compiler workers exercised. Remaining skips require Maven/Gradle executables or a second JDK; see change note9.


## T003-S09-W02 — bezpečná diagnostika legacy XLS

VERIFIED_IN_SCOPE pro `xls-unsupported-1` / `feature-inventory-5`: deklarované
`.xls` a OLE/BIFF hlavičky přejmenované na `.xlsx` se neparsují jako XLSX.
UNSUPPORTED diagnostika nese byte SHA-256, file locator a scope; feature/data-check
ji zachovají jako coverage gap, workspace přidá repo identity. Minimální BIFF2
fixture, malformed vstupy, nejednoznačný compound container, nulové procesy při
extrakci, nulová mutace uloženého grafu a UNKNOWN availability jsou ověřeny
`tests/test_binary_xls.py`; focused 65 PASS. Skutečné XLS buňky/hodnoty se nečtou,
libovolné přípony se nesniffují a signatura není důkaz platného Excel workbooku.
Review oprava přidává streaming checksum oversized souborů a hash-only manifest
metadata; změna stejné délky invaliduje packet i workspace cache bez zápisu do
store. Přímý extractor kontroluje archive limit před hashováním. Finální focused
100 PASS, celá sada 274 PASS / 23 toolchain SKIP (viz change note).
Formula evaluation zůstává non-goal; celý S09/AC09 nadále PARTIAL.
Přesné běhy a zbývající omezení: [change note 34](changes/34_diagnoseBinaryXls.md).

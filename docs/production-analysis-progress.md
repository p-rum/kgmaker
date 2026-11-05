# Aktuální stav a zbývající práce

## T003-S06-W03 — JPA ORM XML overrides (2026-10-26)

VERIFIED_IN_SCOPE pro vybraný persistence unit a omezené ORM XML mapování:
deklarované `mapping-file` pořadí, výchozí `META-INF/orm.xml`, přesná
compiler-resolved class identity, tabulka a scalar ID/basic/version columns.
XML precedence přepisuje annotation mapping; `metadata-complete` potlačuje
annotation-only fyzické vazby. Evidence zachovává XML SHA-256, cestu, unit,
pořadí a precedence. Neznámý namespace/verze, unsupported constructs,
nevyřešené reference, DTD/entities a soubory mimo root zůstávají UNKNOWN bez
annotation fallbacku. Strict diagnostika nemění poslední uložený graph;
schema/store v3 zůstává beze změny. UTF-8/UTF-16 DTD/entity vstupy jsou
encoding-independently rejected, XML read je limitovaný, namespace reset je
UNKNOWN a nested standard metadata/default access se zpracují fail-closed.
Selected XML closure (including missing defaults/references, hashes and resolved
targets) is replayed offline; same-length edits and add/delete/retarget stale the
context. JPA context rule v2 marks legacy XML-bearing contexts stale while
XML-free legacy contexts remain readable. Shared inherited XML columns survive
an override in only one entity; the final strict full suite passed 652 tests and
skipped 10 explicit Maven/Gradle/Windows gates.
Viz [acceptance inventář](acceptance-inventory.md) a
[change note 65](changes/65_ormXmlOverrides.md). T003-S06 zůstává PARTIAL.

## T003-S06-W02 — zděděné JPA persistence atributy (2026-10-26)

VERIFIED_IN_SCOPE pro actual K2 2.1.10 a actual Javac21: JPA
`@MappedSuperclass` field/getter ID určuje zděděný FIELD/PROPERTY access; atributy
jsou projektovány na entity s odděleným `declaring_owner` a `effective_owner`.
Entity attribute indexes and Spring Data repository generic resolution use exact
compiler-qualified owners; a repository for `right.Thing` cannot resolve a
derived predicate against same-simple-name `left.Thing`. An unproven generic
owner remains unbound.
Explicit JPQL entity names and query return declarations also use exact compiler
identities; a simple source return name needs a matching canonical JVM method
descriptor. Missing qualified owners and erased generic variables do not receive
a repository-model or first-match fallback.
Řetězené mapped superclasses, compiler-qualified parent identity, entity-level
override precedence, kolize, unresolved override a SingleTable/Joined/Table-per-class
root/subclass table selection mají fixture v `tests/test_k2_backend.py`.
Původní `orm_attribute`/`orm_table`, graph/store v3 a kontextové evidence se
zachovávají; schema migrace není potřeba. Entity field collision a unresolved
override nevytvoří vybraný `maps_to_column` edge. Mapped-superclass relationship
targets, embedded-attribute overrides, deployment/naming-strategy compatibility
a širší provider matice zůstávají PARTIAL/UNKNOWN; T003-S06 zůstává PARTIAL.
Přesné testy a konečné výsledky jsou v [acceptance inventáři](acceptance-inventory.md)
a [change note49](changes/49_projectJpaInheritedAttributes.md).
## Merge politika po uživatelské změně 2026-11-03

[T045 revize 2](tasks/45_addCodeReviewAgent.md) dovoluje merge bez GH CI, pokud
pro aktuální base/head projdou všechny ostatní povinné kontroly a nezávislé
review. Historické CI_PENDING/billing-only BLOCKED řádky níže zachovávají stav
skutečných běhů; samy již merge neblokují. Chybějící acceptance/toolchain,
konkrétní chyba, konflikt, draft a nesplněná závislost nadále blokují. GH workflow
zůstávají beze změny a serverová pravidla se neobcházejí.

## T003-S08-W03 — bounded callbacks LOCAL_VERIFIED_IN_SCOPE (2026-10-26)

Explicit stacked dependency [Draft PR36](https://github.com/p-rum/kgmaker/pull/36),
W02 head8e83937 (metadata integration; runtime identical to d416e2a); dependency CI/merge is not claimed. Actual TS5.7.3/Node24.19.0 red
6FAIL1PASS and first7PASS, owner/strict/repo2PASS; wider callback/W01/provider34PASS.
Source-final expanded13PASS includes local64-bound PARTIAL, dependency65 map calls
and invalid-candidate store preservation. Further conditional-binding proof corrected
candidate evidence; final protected15PASS61.69s; source-final full582PASS10SKIP641.43s, CI billing BLOCKED.
[Note53](changes/53_resolveBoundedTypeScriptCallbacks.md), [guide](typescript-callbacks.md)
separate declared signatures, candidate bindings and runtime unknowns.
Overload signature→implementation-body navigation remains UNKNOWN/PARTIAL. No whole S08,
UI/BE–FE flow or persistent compiler cache completion is claimed.


## T003-S08-W02 — selected tsconfig freshness LOCAL_VERIFIED_IN_SCOPE (2026-10-26)

Implementována versioned positive/discovery evidence přes skutečné TS5.7.3 API;
Změna nemění resolver ani runtime/data availability. Původní tři skutečné
failure případy nyní prošly; širší snapshot/reference/provider sada46PASS a
snapshot/installed-wheel sada41PASS jsou zaznamenány v
[note45](changes/45_scopeTypeScriptConfigFreshness.md). Finální source-protected focus **70 PASS**,193.26s; source-final full **567 PASS /10 SKIP**,787.45s. CI je PENDING kvůli
GitHub Actions billing/quota; lokální výsledek není CI/merge acceptance. Explicitní legacy fallback, stable
selectors, package-helper hash a fail-closed negative/mixed metadata zachovány.
[Freshness guide](typescript-freshness.md) uvádí directory conservatism a limity.
Celý T003-S08 zůstává PARTIAL; W03 callbacks/generics a navazující UI/BE–FE nejsou
z tohoto kontraktu odvozovány.


## T003-S08-W01 — TypeScript project references (2026-10-26)

VERIFIED_IN_SCOPE pro TypeScript 5.7.3 / Node 24.19.0: solution-style config
s transitive composite projekty, repo/config-qualified identities a skutečné
Program/TypeChecker source redirects bez emitted outputs. Captured project graph
v1 ukládá config/reference/options/file kontrakt; transitive změna vyřadí starou
compiler vrstvu při offline refresh bez procesu. Missing/cycle/outside-root a
overlapping source ownership mají lokalizovanou chybu a nulovou mutaci store.
`tests/test_typescript_project_references.py` a [change note 36](changes/36_resolveTypeScriptProjectReferences.md)
uvádějí přesnou matici. Historická strict sada s vlastním workerem v2:
302 PASS / 7 SKIP po owner-checker a disabled-redirect review opravách nad
main `3503309`. Integrace K2 navíc odmítá změnu úplného compiler input closure
mezi preflight/analyze a zachovává původní TS selection slot; skutečné regrese
a aktuální strict evidence jsou v change note 36: **394 PASS / 9 SKIP**
nad main `eff0d3d` s vlastním workerem a povinným K2. Maven/Gradle/druhé JDK
mimo připravenou matici zůstávají výslovně SKIP.
T003-S08/T003-AC08 zůstávají PARTIAL; W02 stav je samostatně výše; W03,
UI/BE–FE flow, cross-repo sources ani persistent compilation cache nejsou hotové.

## T003-S11-W03 — Windows user-space VERIFIED_IN_SCOPE (2026-10-26)

Skutečný Windows Server2025 restricted-user CI
[run40351407076/job121672139333](https://github.com/p-rum/kgmaker/actions/runs/40351407076/job/121672139333)
na `d311231ed4e199ee0c19d9d5037ccfcdcdce199b`: **43 PASS / 2 SKIP**, 50.23s.
Core + Java/K1 Kotlin/TypeScript installed wheel smoke v cestách s mezerami,
non-admin token, protocol cleanup a store/legacy regresní testy prošly.
SKIP: POSIX-only setup test a K2 worker, jehož Windows podpora není tvrzena.
Všech sedm CI jobů tohoto runu je SUCCESS; metadata commit ještě vyžaduje vlastní
zelené checks a review/merge. Windows BUILD_EXECUTE zůstává unsupported před
procesem nebo mutací store/run; celý T003-S11/T003-AC11 zůstává PARTIAL.
[Change note40](changes/40_supportWindowsUserInstall.md), [Windows guide](windows-install.md).

## T003-S11-W02 — distribuce build exporterů (2026-10-26)

VERIFIED_IN_SCOPE pro Linux, Maven3.9.9 / Gradle8.13 / Temurin21.0.6:
wheel resources obsahují vlastní licenci a versioned hash descriptor.
Explicitní build-plan/run ověřuje contents a export schema/identity před manifest
publikací; původní graph store se nemění. Skutečné Maven i Gradle exporty z
čistého instalovaného wheelu mimo checkout prošly v
`tests/test_exporter_distribution.py`; přesné běhy viz
[change note37](changes/37_packageBuildExporters.md).
Legacy explicitní home/plány zachovávají dosavadní content binding. Windows BUILD_EXECUTE,
immutable publikace, úplná acceptance a benchmark matrix zůstávají otevřené;
T003-S11 a T003-AC11 zůstávají PARTIAL.

## T003-S11-W01 — instalace workerů mimo checkout (2026-10-26)

VERIFIED_IN_SCOPE pro Linux / Python 3.12: resource package `kgmaker_workers`,
sdist/wheel s předem připravenými volitelnými JVM/TS artefakty, deterministická
precedence a chybová diagnostika bez fallbacku explicitní volby.
`tests/test_worker_install.py`: 7 PASS s reálnou Java/TypeScript analýzou mimo
checkout a core instalací bez JDK/Node nebo child procesů. Schema/protocol se
nemění. [Change note 30](changes/30_packageWorkerResources.md) zaznamenává buildy
a kontroly; compiler CI nyní vyžaduje také instalační acceptance.
Celý T003-S11 zůstává PARTIAL; K2 Windows, Windows BUILD_EXECUTE, immutable publication, zbývající
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
| T003-S04 JVM/Kotlin | PARTIAL | Opt-in K2 Analysis API 2.1.10 named-function call subset (`tests/test_k2_backend.py`, change35); JavacTask, K1 compatibility, ASM, 5 ground-truth direct calls with overloads/CFG; izolované testy ověřují konstruktor, primary-constructor property/init pořadí, file-facade `<clinit>`, oddělený object constructor realm, lambda caller, callable reference, source-defined operator v CFG, custom getter/setter method+CFG+ACCESSOR a extension/default/inline/suspend metadata; when/Elvis/short-circuit/try/finally/break/continue mají strukturovaný IR/CFG; `test_compiler_workers`, `test_control_flow` a JVM rendering; W02 dodává bounded Java/Kotlin DefaultImpls a bridge declaration mapping s přesným owner/name/descriptor, realm/ABI guard a bytecode-only diagnostics (`tests/test_default_body_mapping.py`); bounded compiler suspend/async boundaries a DebugMetadata continuation declaration mapping v `test_coroutine_mapping` | K2 širší source call/CFG matice a obecné coroutine state-machine CFG/runtime scheduling, další generated shapes, default-argument masks, statement-level LOC, širší corpus, úplná acceptance banka |
| T003-S05 Spring | PARTIAL | Spring rules v6 zachovávají context-bound `FRAMEWORK_DERIVED` bean/injection, qualifier/primary, ACTIVE/INACTIVE/UNKNOWN pro Profile/ConditionalOnProperty/ConditionalOnClass/custom Conditional, `injects_bean` jen pro unikátní ACTIVE a `may_inject_bean` pro ambiguity/UNKNOWN; bounded compiler-symbol meta-stereotype chain, explicitní package/subpackage component-scan scope, statický `@Import` konfigurační graf s děděním conditions, validaci `@Bean` owneru a collection/map/optional/provider injection; entrypoint, advice a self-invocation proxy boundary; reálný `test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard` dokládá AC05 v podporované matici; typed conditions zachovávají OR profile expressions, všechny property/class members a config hash; bounded registrar/FactoryBean subset je doložen samostatně W02 | Selectors/registrars/factories mimo bounded literal subset, širší property/classpath varianty a runtime proxy/async execution |
| T003-S06 persistence | PARTIAL | Flyway replay plus JPA rules v4: Entity/Embeddable/MappedSuperclass, Java/Kotlin FIELD/PROPERTY identity, EmbeddedId/AttributeOverride, mapped-superclass and entity inheritance table projections, associations, derived queries, compiler-owned JPQL/native `@Query`; W03 selected persistence-unit XML precedence, mapping-file order, metadata-complete suppression, source hashes and fail-closed unsupported/unsafe inputs in actual Javac fixtures; Flyway tests | Broader JPQL/HQL/native grammar, NamedQueries containers, Criteria/Specification/QueryDSL, implicit Kotlin target policy and complete multi-datasource/provider matrix |
| T003-S07 integrations/dataflow | PARTIAL | Literály, service mapping, lokální field edges; S07-W01 compiler-proven Javac/K1/TS argument→declared-parameter bindings s named/default/vararg proof (change52); bounded return→consumer proof s oddělenou caller/body identity a source guards (change66); S07-W04 bounded declared Kafka cluster/topic/contract SHA/release + profile/context precedence; privacy rules `kafka-binding-2` reject sensitive aliases/redact captured public properties; `tests/test_kafka_bindings.py`, fixture `fixtures/kafka-bindings`, [note54](changes/54_scopeKafkaBindingIdentity.md) | Revize2 je draft: bounded canonical listener/send + explicit schema2 code/group join v implementaci, finální acceptance/full/review dosud neuzavřeny; runtime delivery/retry/DLT a obecné Kafka/HTTP datové cesty UNKNOWN |
| T003-S08 TS/UI | PARTIAL | Program/TypeChecker, overloads a React event binding | Multi-project/re-export, callback a BE–FE value flow acceptance |
| T003-S09 artifacts/report | PARTIAL | Feature lifecycle/report, offline HTML docs; bounded XLSX sheets/cells/named ranges/formula dependencies and hash-bound locators; literal Thymeleaf model bindings, static exact-arity fragment provenance, condition/unsupported diagnostics and explicit PDF boundary; `test_feature`, `test_data_check`, `test_workbooks`, `test_templates` | Širší template mapping, schválená metodika a plný scénář; formula/template evaluation zůstává non-goal |
| T003-S10 incremental | PARTIAL | Semantic diff, workspace cache, Flyway checkpoints | Selektivní compiler/feature invalidace a negativní lookup dependencies |
| T003-S11 release/acceptance | PARTIAL | Sedm CI jobů; worker/exporter clean install na Linuxu a skutečný Windows non-admin core/Java/K1/TS smoke (43 PASS / 2 scoped SKIP) | K2 Windows, Windows BUILD_EXECUTE, immutable publikace, celá acceptance a benchmark budgets |
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
T006 rozšiřuje `views.py` o explicitní výběr service/repo/module kontextu,
fingerprinty, odmítnutí nejednoznačných/stale variant a označený SOURCE_ONLY
fallback (module coverage zůstává UNKNOWN). CONTENT_VERIFIED release artifact pair
nepovyšuje na deployment proof.
T006 přidává jen knihovní projekci; CLI, discovery a renderery zůstávají mimo
scope. Jeho konkrétní evidence je v [acceptance inventáři](acceptance-inventory.md)
a [change note 32](changes/32_selectServiceContexts.md). T004 a T007–T044
zůstávají SPECIFICATION; graph v1/v2/v3 se nemění. Ověření T005 je v
[change note 11](changes/11_addViewModel.md); historické výsledky ostatních
work packages výše zůstávají beze změny.

## T003-S04-W01 — K2 Analysis API 2.1.10

Explicitní `--kotlin-backend k2` používá skutečnou Standalone Analysis API/FIR
2.1.10 (`k2-analysis-api-2.1.10-v1`) nad vybranými source-set vstupy a classpath.
Mixed Java/Kotlin named-function calls mají přesné JVM identity od compiler PSI;
nejednoznačné/missing call targety zůstávají UNRESOLVED. Backend/verze mají
vlastní context selection a evidence; K1 compatibility zůstává oddělená cesta.
`tests/test_k2_backend.py` ověřuje stabilitu, negativní konfigurace, protocol/loader
kompatibilitu, scope, offline refresh a strict no-publication. Instalovaný wheel
K2 ověřuje `tests/test_worker_install.py`. Skutečné běhy a verze jsou v
[change note35](changes/35_addK2AnalysisBackend.md).

K2 source CFG, constructor ABI, širší Kotlin annotation/framework metadata,
property/operator/reference/initializer call sites a local/lambda execution nejsou
dodány; konkrétní diagnostiky zachovávají PARTIAL. Kotlin JPA use-site annotation
facts jsou pouze omezenou projekcí T003-S06-W01. T003-S04-W02 mapuje jen doložené
DefaultImpls a simple bridge declarations; další default-body/coroutine tvary
zůstávají mimo podporovanou matici.
Jiné compiler/language/API/JVM verze a captured flags/plugins se odmítají bez
implicitního fallbacku či publikace. T003-S04 a T003 zůstávají PARTIAL.

## T003-S09-W04 — hash-bound approved methodology

VERIFIED_IN_SCOPE: existing implementation-vs-approved-requirement conflict behavior is preserved. Feature packets now verify exported pages, attachments and approval-sidecar content before reusing conflicts. Stale/legacy indexes are omitted with a limitation; duplicate assertion decisions and unextractable approvals leave the previous cache unchanged. `tests/test_methodology_conflicts.py` covers two page versions, stale sidecar, legacy index and ambiguity; `tests/test_scanner.py::test_fa21_approved_requirement_conflict_preserves_authority` covers conflict provenance. Local `PYTHONPATH=src python3 -m pytest -q`: 203 passed in 39.44 s with `KGMAKER_REQUIRE_WORKERS=1` and reused existing baseline build outputs. This does not complete T003-S09.

T003-S09-W04 integration 2026-10-26 against main `0c09028`: focused methodology/feature/scanner **56 PASS**, full suite **229 PASS, 21 SKIP** without prepared toolchain artifacts. Attachment change/deletion now has explicit offline/no-process and no-index-mutation evidence; historical strict evidence remains above. [Change note 9](changes/9_bindMethodologyApproval.md).

Prepared packets revalidate documentation conflict coverage outside checkout too; three external HTML/approval/attachment mutation tests reject stale approval without mutating packet/index.

Final integration run after external-packet freshness fix: **232 PASS, 21 SKIP** (5.00 s); focused **56 PASS**. Strict attempt blocked by missing actual Maven fixture (14 setup errors), documented in change note9; no worker PASS is claimed for this environment.

After actual Maven fixture preparation, final strict integrated run **246 PASS, 7 SKIP** (84.81 s); both real compiler workers exercised. Remaining skips require Maven/Gradle executables or a second JDK; see change note9.

## T003-S12-W01 — odložené živé připojení, konfigurovatelné parametry

Na explicitní pokyn uživatele z 2026-10-26 je live adapter/integrace odložena.
Revize 2 zadání přidává offline JSON nastavení host/API/sandbox/auth references
pod `documentation.confluence.connection` a read-only `confluence config`.
`test_confluence_configuration.py` a existující boundary testy: 28 PASS;
celá sada 281 PASS / 23 toolchain SKIP, Python 3.12.14. `auth_ready` je pouze
přítomnost reference, live stav zůstává NOT_RUN. AC05 je ověřené v tomto scope,
AC01 zachovává NOT_RUN a T003-AC12 není novým důkazem live integrace.
Podrobnosti a limity: [change note 38](changes/38_configureDeferredConfluence.md).


## T007 — explicitní vlastnictví služeb (ověřeno v deklarovaném rozsahu)

Workspace v1 nyní může nést samostatnou deklaraci `service_ownership` v1 s
explicitními roots, repo-qualified module IDs a external system IDs pro existující service IDs.
Resolver používá pouze tyto deklarace a volající context ID; více kandidátů
vrací AMBIGUOUS a žádný UNASSIGNED. Legacy `backend_repo` kontrakt a IDs zůstávají
čitelné; samotná existence repozitáře/modulu/Spring anotace vlastnictví nedokládá.
`tests/test_t007_define_service_ownership.py` pokrývá dvě explicitní služby,
shared library, překryvy, legacy manifest, nevalidní deklaraci bez mutace a
context mismatch, foreign repo-qualified context, qualified workspace path and
unsupported direct schema version. Cílený běh po review opravách: 45 PASS včetně
workspace/T005 regresí. Review full suite na předchozím HEAD `d00dd6a`:
264 PASS, 23 SKIP; SKIP jsou chybějící Maven/JDK, Gradle 8.13 a skutečné JVM/TS
workery. Po review opravách nebyl full suite opakován. `kgmaker check`, semantic
validation a `git diff --check` prošly.
T007-AC01–AC06 jsou VERIFIED_IN_SCOPE pro deklaraci a čistou resolver funkci;
Discovery, view aggregation ani T004 nejsou implementovány.

## T008 — explicitní service inventory (ověřeno v deklarovaném rozsahu)

`views.project_service_inventory` vytváří T005 topology document z validovaného
workspace ownership a T006 kontextů. ID service pochází z deklarovaného service ID;
display label nemění identitu. Context se filtruje přes explicitní scope a vybírá
T006 včetně freshness/variant diagnostik. SOURCE_ONLY zůstává PARTIAL a module
coverage UNKNOWN. U skutečného SOURCE_ONLY snapshotu se repo-qualified artifacty a
file nodes stejného repository i přesného scope matchují na explicitní T007 roots;
production a test kořeny v jednom checkoutu se nekříží. Module identity zůstává UNKNOWN a
produkční služba má PARTIAL status. Skutečný test zároveň vylučuje test fixture a
zachovává external ledger UNKNOWN bez endpointů. Externí systémy pocházejí pouze z T007 deklarace; chybějící checkout nevytváří interní endpointy a implementation/runtime zůstává UNKNOWN.
Workspace alias fixture ověřuje context zachycený pod `local` a kvalifikovaný při
`snapshot_workspace` na deklarované repo ID; dependency symbol bez lokálního source
path se nepřiřazuje.

`tests/test_t008_project_service_inventory.py` pokrývá explicitní service versus
test fixture/shared library/framework bean, missing external checkout, stable ID po
změně labelu, nulovou mutaci při chybě, scope/context/provenance, SOURCE_ONLY,
ambiguous variants, workspace alias a T005 round-trip. Cílená integrovaná sada
pro T008/T005–T007/workspace/cross-repo: **83 PASS**; celá sada **320 PASS, 25 SKIP**.
Skips jsou chybějící skutečný Maven/JDK, Gradle 8.13, Kotlin cache, JVM/TS worker a
Maven fixtures; jsou uvedeny jako SKIP/BLOCKED. T008 nepřidává CLI, parser, worker,
store ani runtime pozorování. Viz [change note 41](changes/41_projectServiceInventory.md).

## T009 — evidence a coverage agregovaných pohledů (omezený fallback)

View v1 nyní zachovává samostatně evidence kind, resolution status, freshness a
reference s explicitní supporting/contradicting polarity. Neoznačené nebo
nepodporované polarity zůstávají UNKNOWN a vytvářejí diagnostiku; agregace
neslučuje odlišné scope ani context ID. Coverage počítá nalezené, vyřešené,
nevyřešené a vyloučené objekty pouze v dodaném výběru; prázdný vstup je UNKNOWN.
Legacy view data se při načtení doplní pouze konzervativními unresolved/unknown
výchozími hodnotami.

T009 používá explicitně povolený PARTIAL/UNKNOWN fallback. T003-S07-W08 ranking
není implementován: nevznikají skóre, inferovaná polarita ani rozhodnutí o
konfliktu nad rámec zachování explicitních protichůdných referencí. Ověření a
zbývající omezení jsou v [change note 64](changes/64_propagateViewEvidence.md).
Cílená T009/T005/T006/T008 sada: **53 PASS**; semantic validation, scan, `kgmaker
check` a `git diff --check` prošly. Před poslední malformed-array guard proběhl
kompletní pytest **445 PASS / 109 SKIP** (19.07 s); finální zdrojový strom čeká na
kompletní `pytest -q -rs` ve frontě sdíleného JVM locku. Individuální důvody SKIP
z předchozího běhu nebyly vypisovány, proto jej nepovažuji za finální test evidence.

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

## T003-S04-W04 — Dependency dispatch hierarchy

Ordered selected JAR/directory hierarchy rozšiřuje compiler-proven Javac/K1/K2
call expressions a ASM virtual/interface sites o oddělené DISPATCH_CANDIDATE
targety. Real JDK21 fixture `tests/test_dependency_dispatch.py` pokrývá API/base
JAR, dva implementation realms, first-match shadow, derived artifact realms,
missing/corrupt/truncated negatives, generic/intersection fail-closed boundary,
oddělený physical/source hierarchy, static ABI conflicts, JDK parent-first shadow
a runtime-effective MR physical lookup. Source canonical identity a reference/nonvirtual
boundaries zůstávají zachované. Všechny dispatch výsledky zůstávají open-world incomplete; S04/T003
zůstávají PARTIAL. Přesné kontroly a zbývající hranice uvádí
[change44](changes/44_addDependencyDispatchHierarchy.md).
## T003-S09-W01 — hranice formula tokenů a dynamických referencí

VERIFIED_IN_SCOPE pro `xlsx-offline-3`: existující bounded offline XLSX extrakce
zůstává zachována; nová oprava neinterpretuje exponent `1E10` ani function name
`LOG10` jako buňku. Actual ZIP regressions ověřují quoted strings, sheet/$/range,
shared/follower, INDIRECT, OFFSET, external a nepodporované 3D/whole-row/column
formy. Tyto boundaries nevytvoří domyšlené dependency ani business missing verdict;
audit zůstává UNKNOWN. Falešné cell locators se odmítají bez změny store.
Workspace parser-version identity zahodí dřívější v1 výsledky bez worker procesů.
Oprava z nezávislého review doplňuje multi-sheet Unicode/numeric/quoted qualifiers,
literal sheet names s INDIRECT/OFFSET textem, explicitní boundary při neznámém
qualifieru a spaced row/column/A1 range tvary; nevznikne falešný local fallback.
Jde o opravu existujících AC01–AC04, ne plnou Excel grammar či dokončení S09/AC09.
Přesné ověření a omezení: [change note39](changes/39_boundXlsxFormulaReferences.md).

## T003-S09-W03 — statické Thymeleaf fragmenty

VERIFIED_IN_SCOPE pro `thymeleaf-bindings-2`: stávající literal model binding/template return IDs a PDF hranice zůstávají zachované. Unikátní same-scope fragment reference s přesnou aritou propojuje přesný caller model path s fragment-scoped parametrem a jeho literal property use, včetně vnořeného fragmentu. Dynamic/duplicate/ambiguous/wrong-arity reference vytváří diagnózu bez resolved include; conditions jsou PARTIAL/UNKNOWN a nepodporované expression selector forms UNKNOWN. `th:each`/`th:with` i data aliasy zůstávají fail-closed: lokální jména a vnořené fragmentové argumenty se nevážou na globální model. Nic se nevykonává a veškeré vztahy zůstávají SOURCE_ONLY `SYNTAX_CANDIDATE`; MVC handler ani renderovaný výsledek se netvrdí. Cílená sada: **65 PASS**; full core: **475 PASS / 114 SKIP** (JDK/JVM, Maven/exporter, Gradle, TypeScript/Node worker a Windows CI prerequisites jsou blokované/SKIP). [Change note55](changes/55_expandThymeleafFragments.md); celý T003-S09/AC09 zůstává PARTIAL.

## T003-S05-W01 — deklarace import selectorů bez execution

VERIFIED_IN_SCOPE pro `annotation-source-v4`: skutečný Javac21/Spring6.2.2
prokazuje exact/transitive ImportSelector/DeferredImportSelector identitu,
jediný literal String[] return a context-bound `selects_import` do deklarované
konfigurace. Unknown těla, filtry/groups, chybějící targets, limity a legacy
metadata mají explicitní boundary či alternativu UNKNOWN. Selector není obyčejný
ACTIVE bean jen kvůli @Import. Fake short-name interface zůstává obyčejný typ.
Profiles, strict no-publication, read-only refresh, schema v1/v2/v3 a UNKNOWN audit
jsou přímo ověřeny v `tests/test_spring_imports.py` pro K1 i K2 distribuci.
Skutečné API se připravuje jen explicitním pinned fixture Maven příkazem; mandatory
CI neoznačí chybějící API/worker za PASS. Žádný Spring context ani aplikace se
nespouští. Java subset nerozšiřuje Kotlin metadata a nedodává custom groups,
registrars/factories, libovolnou dynamickou resolution ani runtime availability.
Celý S05/AC05 a T003 zůstávají PARTIAL. Evidence a přesné běhy:
[change note42](changes/42_resolveBoundedSpringImports.md).

## T003-S11-W04 — explicit required versus optional CI prerequisites

The existing actual compiler and installed-exporter jobs remain mandatory in
their declared matrix. A focused negative matrix now exercises the same
compiler/K2 setup gates with absent JVM/TS/K2/JDK/mixed fixture inputs and
unset/0/1 requirement flags. Required paths fail, optional paths skip, and no
process runs or last-valid graph changes. Spring/exporter prerequisite
negatives are retained. This is bounded CI coverage; second-JDK exploration,
benchmark budgets, full end-to-end acceptance and release gates remain separate.
See [change note48](changes/48_enforceMandatoryWorkerCi.md) for final results.

## T003-S04-W02 — bounded source declaration mappings

The explicit bytecode path now separates generated identity from compiler-proven
source declaration mappings. Actual JDK21/Kotlin2.1.10 golden fixtures cover Java
default methods, value/void generic bridges and Kotlin DefaultImpls/JVM-default=all
under K1/K2 with and without debug attributes. Missing/mismatched source stays
bytecode-only; no source call locator or runtime availability is manufactured.
See change46 and `tests/test_default_body_mapping.py`. S04 remains PARTIAL outside
this declared matrix; coroutine/default-argument/state-machine mapping is pending.

Historical pre-ABI S04-W02 verification: **410 PASS / 9 optional toolchain SKIP**, including
all 32 actual mapping cases; focused scope/duplicate guards **16 PASS**.
Runtime/statement-level mapping remains outside this bounded declaration contract.

W02 static/instance ABI guard uses compiler flags from Javac/K1/K2, with an explicit
DefaultImpls transform and no guessed method flags. Same-realm stale ABI regression
is included in the expanded36-case matrix; final validation supersedes historical410/9.

W02 after compiler ABI guard and Windows main integration: **425 PASS /10 SKIP**,
all36 actual mapping cases; focused8 PASS. Static/instance proof comes from the
compiler, and unavailable proof is explicitly bytecode-only. Remote Windows smoke
remains a separate mandatory gate, not a local PASS.

## T003-S07-W01 — Argument → parameter binding

Explicit compiler inspection records declared-contract argument bindings using
Javac attribution, K1 resolved argument maps and TypeScript signatures. Named and
omitted/default arguments, vararg aggregates, original call-site/context and
transformation are preserved. K2 Kotlin/ASM unavailable proofs and erroneous or
ambiguous mappings remain UNKNOWN/PARTIAL; candidate dispatch never becomes
execution or data availability. Existing SOURCE_ONLY local parsing is separate.
Actual fixtures and remaining boundaries are scoped in
[change52](changes/52_bindArgumentParameterFlow.md); final results are reported
only after validation. S07/T003 are not complete.

## T003-S08-W04 — versioned React event subset

Opt-in react-jsx-events-4 binds official pinned React18.3.1/@types18.3.18 declaration
and package metadata to static handles_event evidence and frontend freshness.
Intrinsic events and sole-return source forwarding wrappers are supported;
unknown versions/fake modules/spreads/mutable bindings stay UNKNOWN. No runtime
click, data availability or full UI framework support is claimed. Explicit base is
PR46 head1e21140; its approved callback parent is now merged. Current composition
is main75d448ee plus the UI feature. Actual validation and pending gates are in change69.

S08-W04 historical pre-binding validation:624 PASS/10 SKIP762.95s and43-case focus.
Historical rule3 frozen validation:727 PASS/10 SKIP791.26s, all66 UI cases, and
36 PASS/30 DESELECTED266.43s focused binding/factory/event-control checks.
The three advertised event types include actual standard input/select/textarea/
form controls; unsupported renderer controls remain UNKNOWN. No browser/app ran,
no runtime click or data availability is inferred. Remote Actions were resumed by
root after the user upgrade. Current rule4 full785 PASS10 SKIP and parent focus189 PASS0 SKIP
are documented in change69; final exact-pair independent review remains required. GH CI is optional.

## T003-S04-W03 — coroutine boundaries

Bounded compiler source suspend/API markers and named ContinuationImpl declaration
mapping are implemented for the actual Kotlin2.1.10 fixture. K1 CFG carries source
resume/failure boundaries; K2 source CFG and unresolved dependency ABI remain
explicit UNKNOWN/PARTIAL. Generated state instructions do not become user source
calls. Validation status and exact supported matrix are recorded in change51;
runtime scheduler order and general coroutine state-machine CFG remain unsupported.

## T003-S04-W05 — JVM golden acceptance corpus

A hand-labelled, versioned compiler corpus compares exact source-call counts and
identities with explicit K1/K2 unsupported boundaries, CFG branches, non-executing
references and unresolved reflection targets. It reuses existing actual fixtures
and the application model/provider pipeline, with no production runtime change.
The local prerequisite stack is explicit; it does not imply those upstream PRs
are already merged. Current validation and remaining limits are in change62;
S04/T003 remain PARTIAL outside this bounded static matrix.

Golden corpus prepared full (2026-10-27): 646 PASS, 10 SKIP /991.96s; all21 corpus checks ran, no failures/setup errors. Source unchanged; remote gates remain paused.

## T003-S05-W02 — bounded registrar/factory deklarace

VERIFIED_IN_SCOPE pro Java/Javac21, Spring6.2.2 a obě vlastní K1/K2 distribuce,
Spring rules `annotation-source-v5`: přesná/transitivní registrar identita a
straight-line literal registry calls na skutečném registry parametru, source
method/hash/context provenance a importující configuration condition. FactoryBean
objekt `&name` a produkt `name` jsou oddělené; produkt má ACTIVE statickou
declaration condition pouze pro indexovaný konkrétní generic typ a shodné
literal constructor/class returns. Custom bodies/overload/conditions, abstract
factories, neznámé nebo neshodné typy a překročený budget zůstávají UNKNOWN.
`tests/test_spring_registrations.py` ověřuje skutečné APIs, fake namespace/receiver,
inherited generics, profiles, malformed facts, strict/timeout nulovou publikaci,
offline refresh, legacy schemas a UNKNOWN data audit. Mandatory CI APIs se
připravují explicitně, nikoli core/test fetch. Kotlin registration facts, obecné
builders, XML/factories metadata, runtime a production availability nejsou dodány.
S05/AC05 a celý T003 zůstávají PARTIAL. Přesné běhy, externě blokované Actions a
Draft stav: [change note47](changes/47_declareSpringRegistrations.md).
## T015 — explicit datasource resource projection

Bounded implementation over T008/T009: explicit workspace/repository/database/stream
resources, table drill-down references, existing selected-context read/write/delete
facts and dependency-only entity/migration declarations. Flyway derivation is
MIGRATION_DERIVED, deployment/populated-data availability remain UNKNOWN.
Default/unmapped/conflicting/stale/foreign scope is not promoted. Public36 cases
and broader pure focused115 PASS (6.79s); local strict full is queued under the
shared worker lock. [Evidence and exact current status](changes/68_projectDataResources.md).
Complete persistence/schema-compatibility S06/W08, T004 and production readiness
remain PARTIAL; this does not implement a new parser or discover datasources.

## Return → consumer bindings

T003-S07-W02 adds optional compiler-owned return IR without changing protocol v1
or graph/store v1/v2/v3. Explicit inspection records typed call-result, assignment,
return-expression and receiver occurrences with `return_mapping_version=1` evidence.
Branch guards remain alternatives; nullability is declared compiler information,
never an observed value. Process JSON/Markdown and directional impact retain the
bindings. Workspace export qualifies their original identities and context.

| Backend | Supported static proof | Explicit boundary |
|---|---|---|
| Javac/JDK21 | Declared returns, local assignment versions, branch alternatives, nested receivers | Open dispatch, recursion, callable/void/opaque bodies, unsupported control flow |
| K1/Kotlin2.1.10 | Declared/nullable returns, safe receivers, generated data-class destructuring | Custom component bodies, suspend/callable bodies, unsupported control flow |
| TypeScript5.7.3 | Typed results, local assignments, nullable receivers, exact unassigned FunctionDeclaration references / real #private member bodies and direct-body tuple/object destructuring | any, async/generator, mutable static/soft-private/namespace/script-global members, import/alias/property-based references, reassigned lexical functions (including loop/destructuring writes), direct/ambiguous eval, uncaptured source bodies, open dispatch, computed/rest/default projections |
| K2 Kotlin / ASM | Existing declared targets remain readable | Missing source return/CFG proof stays UNKNOWN |

`returns_to` value facts require versioned SYMBOL_RESOLVED evidence; a CFG control
edge of the same name cannot establish value flow. Callee body joins require a
supported direct source target, and recursion is bounded. No application executes,
network request, store mutation during failed validation, runtime value observation,
or implicit compiler refresh is introduced. Legacy indexes remain readable; an
explicit obsolete return-rule version is STALE offline.

Example after explicit compiler inspection: `kgmaker flow render --help` describes
the existing process rendering commands; their JSON call blocks include
`return_consumer_bindings`, and data-flow JSON includes the same supplemental proof.
Actual coverage is in `tests/test_return_consumer_flow.py`; broader production
interprocedural flow and complete S07 remain pending.

## T023 — ProcessDefinition / ProcessView (explicit model)

T023 přidává čisté version1 Python API pro explicitní definici/revizi a process
view nad T005/T009. Scope/context a origin/evidence refs jsou validovány;
alternativy, exception, loop/retry i async nepřecházejí na lineární pořadí.
Semantic annotations mají strict allowlist; APPROVED label nezvyšuje technical
status, druh evidence, freshness ani data availability. Missing/foreign/stale
proof je explicitní boundary nebo invalidní input.

[Capability a příklad](process-model.md), [change note70](changes/70_defineBusinessProcessModel.md).
Modelové AC mají konkrétní pozitivní/negativní testy: focused130 PASS1.00s;
required frozen full729 PASS/10 optional SKIP546.19s,0 errors/failures a515
nezměněných hashes na source95c3ed3. Nejde o discovery/projection, process
review/catalog/store ani nové CLI/render. Exact-pair review/publikace/fresh CI
zůstávají samostatnými release gates. T024–T040 a celý T004 zůstávají samostatným nedodaným rozsahem.

## T010 — scoped HTTP provider projection

`interfaces.project_http_providers` provides a pure `interfaces` ViewDocument on
explicit T008/T007 ownership and T009 evidence. Service/method/case-preserving
route identity is distinct from registration/contract variant identity. Existing
API IDs remain unchanged; additive versioned source/hash-bound declaration
metadata preserves otherwise lost route case and variants. Typed Spring mirrors
support bounded exact class/method composition; source Spring/Ktor candidates,
contract-only OpenAPI and unresolved dynamic prefixes remain distinguishable.

Final combined focused **145 PASS**,87.81s and strict full **596 PASS /10 optional
prerequisite SKIP**,479.68s passed. Mandatory WORKERS/K2/SPRING_IMPORTS/HTTP_PROVIDERS=1
cases ran with own prepared JDK21/K1/K2/TS/Spring6.2.2 worker/API fixtures; ten frozen
source/test/CI/fixture hashes matched before/after. The grouped actual fixture
covers same-line overloads/owners, mapping/method/class-prefix variants, inherited/
custom UNKNOWN and direct override, truncation, metadata and context isolation,
and actual reinspection after unrelated files, same-file comment/line shifts and
within-module relocation. Canonical compiler IDs stay stable and provenance updates.

Historical pre-owner590/10 and interrupted pre-selection257/7/pre-overload148/2
runs are not final acceptance. Root and independent architect source closure
approved the final manifest; current main ec333 integration199 PASS167.32s (own runtime/tests unchanged,
matching prepared current-main workers). Exact Git-pair review and remote CI
remain pending. Actions are billing-blocked again; no retry/bypass or
remote PASS claim. Broader production/toolchain/runtime acceptance is separate.

Bounded PARTIAL: imported runtime-to-interface binding is unsupported and retains
original references in `HTTP_RUNTIME_BINDING_UNKNOWN`; deployment/runtime/data
availability are UNKNOWN. Real application runtime test NOT_RUN. No endpoint
consumer projection, inferred contract implementation, new resolver/store or
T004 completion. Required CI and independent review are pending.
See [change67](changes/67_catalogHttpProviders.md).

## T003-S05-W03 — typed profile/property/class conditions

Implemented bounded JVM Spring v6 typed conditions: profile arrays/expressions,
property alias/prefix/multiple-name semantics and genuine boolean missing policy,
exact declared class inventories and conservative unsupported/custom boundaries.
Injection uses the computed condition state. Explicit variant inputs/classpath
are checked per context and the snapshot is tamper-bound; prior-rule contexts
require reinspection without changing graph schema. Actual pinned API results
and final full-suite evidence are recorded in
[change note50](changes/50_expandSpringConditions.md). Runtime condition execution,
custom defaults, Unicode case equivalence and unsupported dynamic expressions
remain outside this bounded proof; T003-S05 stays PARTIAL.

## T024 — proved trigger inventory, local bounded implementation

Pure API zachovává doložené selected-context HTTP/Kafka/scheduler deklarace,
owner/source/proof a oddělenou body availability. K1 genuine fixture dodává3
trigger kinds; expression-body CFG zůstává UNAVAILABLE. K2 nemá authoritative
annotation ownership ani SOURCE CFG: legacy hints se odmítají, UNKNOWN bez
trigger claims. Žádná cesta procesu ani runtime registration/execution se nehádá.
Bounded41PASS a current-base199PASS zahrnují actual K1/K2 a canonical mutations;
strict frozen full812PASS/10optionalSKIP,206hashů shodných. Main8b1eec integrace
236PASS včetně actualK1/K2 a pure conditions/inventory/query replay,221hashů shodných.
PR59 čeká na finální nezávislé review; merge zatím neproveden. [Capability](process-triggers.md), [note71](changes/71_discoverProcessTriggers.md).

## T003-S06-W04 — explicit persistence realms LOCAL_VERIFIED_IN_SCOPE

Explicit workspace replay reuses current compiler facts before qualification.
Structured DB/stream pair plus schema/target and PU/context provenance prevents
cross-realm name fallback; same stream across different databases works and exact
duplicate pair is rejected. New unqualified source-only physical mappings remain
UNKNOWN. Actual K1/K2 cases cover shared SQL paths, same entities across contexts,
quoted-dot collisions, strict malformed boundaries and two-PU physical joins.
One strict repository full passed **1348/10** with unchanged HEAD and623 inputs;
actual/source closure and all evidence are in changes/74_isolatePersistenceRealms.md.
Final remote review/merge is pending; this is not completion of T003/S06 or T004.
Physical replay support is non-renamed tables/columns; creation-stable renamed IDs
remain UNKNOWN pending S06-W08's explicit creation-identity lifecycle proof.

## T025 — local technical process path, explicit T024 stack

Python adapter reuse flow.process/T023 zachovává sourceCFG branch/call/return/
exception origin IDs. Root CFG větší než budget je explicitní opaque boundary,
ne neomezená kopie; trigger se započítává do typed output budgetu. Missing body,
recursion, dispatch/async/coroutine nejistota zůstávají PARTIAL boundaries.
Source/context/scope/hash a obě call-site edge/proof vazby se kontrolují; žádná
physical freshness ani observed execution se z dodaného JSON neodvozuje.
Explicit dependency Draft PR59 (T024 head3b24cc6) musí být merged před T025 merge.
Actual Javac/K1 bounded fixture a pure proof/legacy/nomutation matice jsou lokální
důkazy; full/review/release zůstávají pending. [Capability](process-paths.md),
[note73](changes/73_buildLocalProcessPath.md). Celý T004/T003 není dokončen.

## T011 — typed HTTP consumer catalogue

Pure `interfaces.project_http_consumers` reuses merged T008/T009/W06 snapshots,
explicit ownership/context selection and evidence buckets. Distinct request and
Feign terminal callers remain distinct; static intent is not runtime execution.
Current implementation/focus status is in [change76](changes/76_catalogHttpConsumers.md);
strict full at b1163fc passed1373 tests (10 optional skips); current9f6605 parent
focus passed205 tests without skips. Final current-pair independent review is pending. Coverage remains PARTIAL,
remote binding/runtime/data availability UNKNOWN. See [capability](http-consumers.md).

## T025 revision2 — local operation proof prerequisite (in progress)

Separate candidate over merged T025 c695/main ef3 adds a bounded Javac typed
literal/local-assignment witness, exact IR/CFG/source/context proof binding and
independent operation resolution. CFG ordering and transitions remain syntax /
UNRESOLVED. Legacy/Kotlin/unsupported operations gain no confidence or data claim.
Architecture independently reviewed; initial actual RED,11 protocol tests and120
legacy tests executed. Own fresh K1/K2 builds passed; the initial actual matrix
failed on declaration origin, then proof-retention bugs were corrected. Current
Corrected actual integration341PASS/0SKIP on a617. Descendant cff803c superset
full1566PASS/10SKIP includes every parent test (1471PASS/10SKIP), with exact
parent runtime/distributions and unchanged input closure. This is descendant
evidence, not a separate full on a617; see [change79](changes/79_certifyLocalOperations.md).
Independent final review/merge remain separate. T026 remains separate.

## T026 — reversible certified local-operation groups (candidate)

The pure `business_process.collapse_business_steps` / `expand_business_steps`
API reuses the T025 ProcessView and embedded certificates. It groups only maximal
acyclic same-owner/method/context/scope normal chains, preserves ordered origin
records and parallel external edges, and exactly restores canonical input.
Decisions, calls, fields/side effects, loops, unknown boundaries and finally
clones remain visible. Syntax adjacency keeps groups UNRESOLVED/PARTIAL; no
runtime/business approval follows. PR65 runtime a6170c18 is merged as main32a3bca and integrated; dependency gate
is satisfied. Actual Javac RED1FAIL4.78s preceded source; historical focus265PASS43.62s ran
without FIFO/prehash receipt. Source cff803c received independent APPROVE.
Final ONE strict FIFO full 1566PASS/10SKIP v 1532.43s, all95 T026 cases without skip, immutable
tracked/compiler/runtime/license/fixture receipts. Integration changes metadata
only; runtime/tests remain cff803c, no compiler/full repeat. Final exact-pair
review/publication remain separate; see change82.

## T003-S07-W05 — Kafka retry/DLT draft

IN_PROGRESS bounded static policy adapter `kafka-retry-1` on explicit Kafka rev2
parent19b0594. Exact3.3.2 API+canonical Java/K1 annotation/proof and separate async
boundaries; custom/unsupported policy UNKNOWN. Initial actual6PASS and pure-only replays remain distinct historical evidence.
Current-parent coalesced470PASS/0SKIP186.44s is verified with1620unchanged inputs;
Strict full on647:1908PASS/10SKIP1920.61s; current-parent pure23PASS; final exact-pair ready review remains pending. See [note87](changes/87_captureKafkaRetryDlt.md). Execution and
delivery NOT_OBSERVED; runtime/data availability UNKNOWN.

## T003-S06-W08 — bounded schema compatibility (VERIFIED_IN_SCOPE)

Same Replay + compiler-owned FIELD/PROPERTY/inherited witnesses support explicit
scalar type/null/decimal/PK/UK and single FIELD ManyToOne FK tuple/key comparison.
Current-name rename/drop identity and malformed/version/source/realm negatives
are covered. W04 PR62 merged; current main c193748 integrated. Strict full
ced9717:1591PASS/10optionalSKIP1646.65s,1471 hashes unchanged. Return composition
67b8341:174PASS/0SKIP248.87s,1487 hashes unchanged. Final pure parent ambiguity
4PASS/0SKIP0.56s; worker sources/core unchanged by that parent. Final independent
review/ready/merge separate. See note78 and acceptance matrix. Unsupported XML
constraints/naming/converters/composite FK remain UNKNOWN. No availability,
deployment/population promotion or whole-milestone completion inferred.

## T010 normalized variant correction (2026-11-03)

Actual JSON declarations /orders/{id} and /orders/{name} with one method caused
DUPLICATE_NODE_ID. Rule2 preserves one explicit ambiguous boundary and both
candidate/provenance sets; exact duplicates and YAML distinct locators retain
existing behavior. Public RED3FAIL1PASS1.88s; corrected pure/provider34PASS2.12s.
Actual compiler focus149PASS/0SKIP; strict full493:1605PASS/10SKIP1683.18s with2105 unchanged inputs. Return-parent e740 composition284PASS/0SKIP219.41s with2113 unchanged inputs. Final metadata-head review/merge remain separate; no execution or deployment claim. [change88](changes/88_preserveAmbiguousHttpProviders.md).

## T030 — process-label packet (candidate)

Pure `prepare_process_label_packet` preserves complete ProcessView target/ref
identity, actual content binding and captured evidence/uncertainty. Raw prose is
hash-omitted; document provenance is explicit ref-only and conflicts are supplied
review items, not NLP authority. Full serialized cost includes omissions/template
and a stable-width overflow flag. Tiny budgets keep validation IDs; invalid/hard
inputs fail without mutation or I/O. Unicode/code-path IDs are retained.
Corrected coalesced pure153PASS/0SKIP4.07s; required full and independent
exact-source review remain pending. T031/T032 apply/review and T034 CLI are not implemented here.

## T031 — validate process annotations (stacked candidate)

Pure same-module validation rederives the whole current T030 packet and accepts
only bounded semantic PROPOSED records. Invalid/stale/forged/unsafe inputs return
fixed-code REJECTED validation reports; valid input remains PENDING/CONFLICT with
all differing proposals and captured documentary review items. No approval/apply,
new outcomes, technical mutation, NLP comparison, runtime or physical freshness.
Explicit stack on T030070 retains all47T030tests and32original module AST nodes.
PublicRED6FAIL0.40s, currentcoalesced229PASS0SKIP6.22s (76new+153inherited). Required
full, independent exact source review and root publication remain pending.

## T032 — semantic review persistence (stacked candidate)

Explicit stack on reviewed T031a359. Separate version1 envelope,128history/2MiB caps,
POSIX cooperating thread/process CAS, exact idempotent operation identity and current
explicit-baseline revalidation. APPROVE blocks captured and proposal conflicts;
REJECT publishes no new labels. Technical model/evidence remains unchanged.
Current feature36PASS1.93s; coalesced269PASS94SKIP8.74s (compiler SKIPs not PASS).
Independent source review and strict full NOT_RUN. No native build, CLI, external
publication, authenticated reviewer identity or hostile-root race guarantee.

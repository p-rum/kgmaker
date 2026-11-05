# Registr implementačních zadání

Tento registr je autoritou pro identitu zadání. Implementační stav patří do
[stavové matice](../production-analysis-progress.md), technické požadavky do
níže uvedených zadání. Pravidla jsou závazná v [AGENTS.md](../../AGENTS.md).
Řádkové mapování požadavek → verze → test → skutečný běh udržuje
[acceptance inventář](../acceptance-inventory.md).

| ID | Soubor | Úloha | Stav dokumentu |
|---|---|---|---|
| T001 | [1_featureAnalysis.md](1_featureAnalysis.md) | Feature/data analýza, artefakty, incremental, Flyway, multirepo | Normativní; částečně implementováno |
| T002 | [2_buildAwareInspection.md](2_buildAwareInspection.md) | JVM build, call graph, Spring a Hibernate | Normativní; částečně implementováno |
| T003 | [3_finishProductionAnalysis.md](3_finishProductionAnalysis.md) | Integrovaný plán dokončení T001/T002 a produkční analýzy | Normativní plán; není tvrzením dokončení |
| T004 | [4_addHighLevelProjectViews.md](4_addHighLevelProjectViews.md) | Integrační katalog, topologie služeb a business procesy; T005–T044 níže | SPECIFICATION |
| T045 | [45_addCodeReviewAgent.md](45_addCodeReviewAgent.md) | Projektový code-review agent pro vytvořené PR a schválený merge | SPECIFICATION, revize 2; GH CI je doplňující, ostatní kontroly zůstávají povinné; profil není důkazem merge |

## High-level zobrazení projektu — T004

[T004 — hlavní zadání](4_addHighLevelProjectViews.md) obsahuje společné kontrakty,
migrační pravidla, dependency DAG a nadřazená acceptance. Implementace je rozdělena
do **40 samostatných úkolů T005–T044**, každý ve vlastním souboru, větvi a PR.
Všechny jsou SPECIFICATION; tato registrace neprohlašuje funkce za implementované.

Na explicitní požadavek zadavatele z 2026-10-20 mají nové atomické úkoly formát
`T-<NNN>_<kebab-case-slug>.md`, např. `T-005_add-view-model.md`.
Jde o tutéž globální číselnou řadu: T-005 = T005. T004 je nadřazené zadání;
T005–T044 nejsou další série work-package čísel. Staré soubory se nepřejmenovávají.
Pro tento balík má tato výslovná konvence přednost před starým obecným pravidlem
lowerCamelCase, včetně historických kopií v agent templates.

| Task | Soubor a cíl | Závislosti | Stav |
|---|---|---|---|
| T005 | [Verzovaný společný model pohledu](T-005_add-view-model.md) | T004 kontrakt | SPECIFICATION |
| T006 | [Výběr kontextů pro více služeb](T-006_select-service-contexts.md) | T005; T003-S02 | SPECIFICATION |
| T007 | [Explicitní vlastnictví služeb](T-007_define-service-ownership.md) | T005 | SPECIFICATION |
| T008 | [Inventář služeb a externích systémů](T-008_project-service-inventory.md) | T006, T007 | SPECIFICATION |
| T009 | [Evidence a pokrytí agregovaných objektů](T-009_propagate-view-evidence.md) | T005, T006; T003-S07-W08 | SPECIFICATION |
| T010 | [Katalog poskytovaných HTTP rozhraní](T-010_catalog-http-providers.md) | T008, T009 | SPECIFICATION |
| T011 | [Katalog používaných HTTP rozhraní](T-011_catalog-http-consumers.md) | T008, T009; T003-S07-W06 | SPECIFICATION |
| T012 | [Katalog Kafka producerů a consumerů](T-012_catalog-kafka-interfaces.md) | T008, T009; T003-S07-W04 | SPECIFICATION |
| T013 | [Připojení verzovaných integračních kontraktů](T-013_attach-interface-contracts.md) | T010, T011, T012 | SPECIFICATION |
| T014 | [Projekce ověřených vzdálených bindingů](T-014_bind-remote-interfaces.md) | T013; T003-S07-W07 | SPECIFICATION |
| T015 | [Databáze a jiné datové závislosti](T-015_project-data-resources.md) | T008, T009; T003-S06 | SPECIFICATION |
| T016 | [Agregace topologie služeb](T-016_aggregate-service-topology.md) | T014, T015 | SPECIFICATION |
| T017 | [Filtrování a omezení velikosti topologie](T-017_filter-topology-scope.md) | T016 | SPECIFICATION |
| T018 | [Dohledání zdrojů high-level objektů](T-018_explain-view-elements.md) | T009, T016 | SPECIFICATION |
| T019 | [Read-only CLI pro architektonické pohledy](T-019_add-architecture-json-cli.md) | T010, T011, T012, T013, T017, T018 | SPECIFICATION |
| T020 | [Markdown katalog integračních rozhraní](T-020_render-interface-markdown.md) | T013, T019 | SPECIFICATION |
| T021 | [Mermaid schéma služeb](T-021_render-topology-mermaid.md) | T017, T019; T003-S07-W09 | SPECIFICATION |
| T022 | [Markdown report topologie a detailů](T-022_render-topology-markdown.md) | T018, T021 | SPECIFICATION |
| T023 | [Model business procesu a jeho revizí](T-023_define-business-process-model.md) | T005, T009 | SPECIFICATION |
| T024 | [Inventář doložených spouštěčů](T-024_discover-process-triggers.md) | T008, T023 | SPECIFICATION |
| T025 | [Lokální technický průběh od vstupu](T-025_build-local-process-path.md) | T023, T024; T003-S04 | SPECIFICATION |
| T026 | [Seskupení technických uzlů do business kroků](T-026_collapse-business-steps.md) | T025 | SPECIFICATION |
| T027 | [Průchod procesu přes HTTP rozhraní](T-027_cross-http-process-boundary.md) | T014, T025 | SPECIFICATION |
| T028 | [Asynchronní návaznosti procesu](T-028_cross-async-process-boundary.md) | T012, T014, T025 | SPECIFICATION |
| T029 | [Chybové větve, retry a kompenzace](T-029_project-process-failures.md) | T025, T028; T003-S07-W05 | SPECIFICATION |
| T030 | [Packet pro business pojmenování agentem](T-030_prepare-process-label-packet.md) | T024, T026 | SPECIFICATION |
| T031 | [Validace agentových návrhů](T-031_validate-process-annotations.md) | T023, T030 | SPECIFICATION |
| T032 | [Schválení a revizní historie procesů](T-032_persist-process-review.md) | T031 | SPECIFICATION |
| T033 | [Katalog identifikovaných procesů](T-033_catalog-business-processes.md) | T024, T032 | SPECIFICATION |
| T034 | [CLI životního cyklu procesů](T-034_add-process-cli.md) | T027, T028, T029, T030, T031, T032, T033 | SPECIFICATION |
| T035 | [Mermaid business průběhu](T-035_render-business-process-mermaid.md) | T026, T027, T028, T029, T034 | SPECIFICATION |
| T036 | [Markdown business report](T-036_render-business-process-report.md) | T033, T035 | SPECIFICATION |
| T037 | [Invalidace odvozených pohledů](T-037_invalidate-derived-views.md) | T018, T032, T033 | SPECIFICATION |
| T038 | [Atomická publikace exportů](T-038_publish-view-artifacts-atomically.md) | T022, T036, T037 | SPECIFICATION |
| T039 | [Sémantický diff dvou snapshotů](T-039_diff-architecture-and-processes.md) | T037, T038 | SPECIFICATION |
| T040 | [Instrukce host agenta pro pohledy](T-040_add-agent-process-instructions.md) | T034, T036 | SPECIFICATION |
| T041 | [End-to-end acceptance architektury](T-041_verify-architecture-acceptance.md) | T020, T021, T022, T038 | SPECIFICATION |
| T042 | [End-to-end acceptance business procesů](T-042_verify-process-acceptance.md) | T035, T036, T038, T040 | SPECIFICATION |
| T043 | [Limity výkonu a velikosti](T-043_bound-view-performance.md) | T017, T025, T037 | SPECIFICATION |
| T044 | [Dokumentace a release gate](T-044_document-high-level-capabilities.md) | T039, T040, T041, T042, T043 | SPECIFICATION |

## Atomické work packages pro dokončení T003

Následující soubory rozdělují dosud nedodaný rozsah T003 na samostatně
implementovatelné work packages. Nejsou novou řadou hlavních Task ID a nemění
publikované identity T001–T003. Jejich název používá uživatelem požadovaný formát
`{milnik}-{cisloTasku}-{vystiznyNazevUkolu}`; stabilní identita uvnitř souboru je
`T003-Sxx-Wyy`. Každý work package se implementuje ve vlastní větvi a končí
samostatným pull requestem.

Pro všech 60 work packages je připraven právě jeden projektový Codex agent v
adresáři [`.codex/agents`](../../.codex/agents/README.md). Agent je svázaný s
jediným zadáním, používá `gpt-5.6-luna` s reasoning effort `medium` a vynucuje
izolovaný worktree, samostatnou větev, požadované testy, change note a samostatný
pull request bez automatického merge. Stav zadání tím zůstává `SPECIFICATION`;
existence agenta není důkazem implementace ani splnění acceptance.
Samostatný [code-review agent](../../.codex/agents/README.md) podle T045 přebírá
vytvořené PR k review a po schválení současného HEAD je může mergeovat.

| Work package | Soubor | Úloha | Stav |
|---|---|---|---|
| T003-S03-W01 | [T003-S03-01-externalToolchainSelection.md](T003-S03-01-externalToolchainSelection.md) | external toolchain selection | SPECIFICATION |
| T003-S03-W02 | [T003-S03-02-gradleCustomVariants.md](T003-S03-02-gradleCustomVariants.md) | gradle custom variants | SPECIFICATION |
| T003-S03-W03 | [T003-S03-03-gradleIncludedBuilds.md](T003-S03-03-gradleIncludedBuilds.md) | gradle included builds | SPECIFICATION |
| T003-S03-W04 | [T003-S03-04-kotlinCompilerOptions.md](T003-S03-04-kotlinCompilerOptions.md) | kotlin compiler options | SPECIFICATION |
| T003-S03-W05 | [T003-S03-05-crossRepoArtifactMapping.md](T003-S03-05-crossRepoArtifactMapping.md) | cross repo artifact mapping | SPECIFICATION |
| T003-S04-W01 | [T003-S04-01-k2AnalysisApiBackend.md](T003-S04-01-k2AnalysisApiBackend.md) | k2 analysis api backend | SPECIFICATION |
| T003-S04-W02 | [T003-S04-02-defaultBodySourceMapping.md](T003-S04-02-defaultBodySourceMapping.md) | default body source mapping | SPECIFICATION |
| T003-S04-W03 | [T003-S04-03-coroutineSourceMapping.md](T003-S04-03-coroutineSourceMapping.md) | coroutine source mapping | SPECIFICATION |
| T003-S04-W04 | [T003-S04-04-dependencyDispatchHierarchy.md](T003-S04-04-dependencyDispatchHierarchy.md) | dependency dispatch hierarchy | SPECIFICATION |
| T003-S04-W05 | [T003-S04-05-jvmGoldenAcceptanceCorpus.md](T003-S04-05-jvmGoldenAcceptanceCorpus.md) | jvm golden acceptance corpus | SPECIFICATION |
| T003-S05-W01 | [T003-S05-01-dynamicSpringImports.md](T003-S05-01-dynamicSpringImports.md) | dynamic spring imports | SPECIFICATION |
| T003-S05-W02 | [T003-S05-02-springRegistrarsFactories.md](T003-S05-02-springRegistrarsFactories.md) | spring registrars factories | SPECIFICATION |
| T003-S05-W03 | [T003-S05-03-springConditionMatrix.md](T003-S05-03-springConditionMatrix.md) | spring condition matrix | SPECIFICATION |
| T003-S05-W04 | [T003-S05-04-springProxyAsyncSemantics.md](T003-S05-04-springProxyAsyncSemantics.md) | spring proxy async semantics | SPECIFICATION |
| T003-S06-W01 | [T003-S06-01-kotlinJpaAccess.md](T003-S06-01-kotlinJpaAccess.md) | kotlin jpa access | SPECIFICATION |
| T003-S06-W02 | [T003-S06-02-jpaInheritedAttributes.md](T003-S06-02-jpaInheritedAttributes.md) | jpa inherited attributes | SPECIFICATION |
| T003-S06-W03 | [T003-S06-03-ormXmlOverrides.md](T003-S06-03-ormXmlOverrides.md) | orm xml overrides | SPECIFICATION |
| T003-S06-W04 | [T003-S06-04-multiDatasourceRealms.md](T003-S06-04-multiDatasourceRealms.md) | multi datasource realms | SPECIFICATION |
| T003-S06-W05 | [T003-S06-05-jpqlHqlGrammar.md](T003-S06-05-jpqlHqlGrammar.md) | jpql hql grammar | SPECIFICATION |
| T003-S06-W06 | [T003-S06-06-namedQueryContainers.md](T003-S06-06-namedQueryContainers.md) | named query containers | SPECIFICATION |
| T003-S06-W07 | [T003-S06-07-criteriaSpecificationQuerydsl.md](T003-S06-07-criteriaSpecificationQuerydsl.md) | criteria specification querydsl | SPECIFICATION |
| T003-S06-W08 | [T003-S06-08-schemaCompatibility.md](T003-S06-08-schemaCompatibility.md) | schema compatibility | SPECIFICATION |
| T003-S07-W01 | [T003-S07-01-argumentParameterFlow.md](T003-S07-01-argumentParameterFlow.md) | argument parameter flow | SPECIFICATION |
| T003-S07-W02 | [T003-S07-02-returnConsumerFlow.md](T003-S07-02-returnConsumerFlow.md) | return consumer flow | SPECIFICATION |
| T003-S07-W03 | [T003-S07-03-fieldAndMappingFlow.md](T003-S07-03-fieldAndMappingFlow.md) | field and mapping flow | SPECIFICATION |
| T003-S07-W04 | [T003-S07-04-kafkaBindingIdentity.md](T003-S07-04-kafkaBindingIdentity.md) | kafka binding identity; revize2 canonical code/group proofs | SPECIFICATION |
| T003-S07-W05 | [T003-S07-05-kafkaRetryDlt.md](T003-S07-05-kafkaRetryDlt.md) | kafka retry dlt | SPECIFICATION |
| T003-S07-W06 | [T003-S07-06-httpClientExecution.md](T003-S07-06-httpClientExecution.md) | http client execution | SPECIFICATION |
| T003-S07-W07 | [T003-S07-07-crossServiceContractMapping.md](T003-S07-07-crossServiceContractMapping.md) | cross service contract mapping | SPECIFICATION |
| T003-S07-W08 | [T003-S07-08-evidenceRanking.md](T003-S07-08-evidenceRanking.md) | evidence ranking | SPECIFICATION |
| T003-S07-W09 | [T003-S07-09-unifiedFlowViews.md](T003-S07-09-unifiedFlowViews.md) | unified flow views | SPECIFICATION |
| T003-S08-W01 | [T003-S08-01-typescriptProjectReferences.md](T003-S08-01-typescriptProjectReferences.md) | typescript project references | SPECIFICATION |
| T003-S08-W02 | [T003-S08-02-tsconfigPathsExclude.md](T003-S08-02-tsconfigPathsExclude.md) | tsconfig paths exclude | SPECIFICATION |
| T003-S08-W03 | [T003-S08-03-typescriptCallbacksGenerics.md](T003-S08-03-typescriptCallbacksGenerics.md) | typescript callbacks generics | SPECIFICATION |
| T003-S08-W04 | [T003-S08-04-versionedUiEvents.md](T003-S08-04-versionedUiEvents.md) | versioned ui events | SPECIFICATION |
| T003-S08-W05 | [T003-S08-05-backendFrontendValueFlow.md](T003-S08-05-backendFrontendValueFlow.md) | backend frontend value flow | SPECIFICATION |
| T003-S09-W01 | [T003-S09-01-xlsxAdvancedReferences.md](T003-S09-01-xlsxAdvancedReferences.md) | xlsx advanced references | SPECIFICATION |
| T003-S09-W02 | [T003-S09-02-binaryXlsDiagnostics.md](T003-S09-02-binaryXlsDiagnostics.md) | binary xls diagnostics | SPECIFICATION |
| T003-S09-W03 | [T003-S09-03-templateDialectExpansion.md](T003-S09-03-templateDialectExpansion.md) | template dialect expansion | SPECIFICATION |
| T003-S09-W04 | [T003-S09-04-approvedMethodologyConflicts.md](T003-S09-04-approvedMethodologyConflicts.md) | approved methodology conflicts | SPECIFICATION |
| T003-S09-W05 | [T003-S09-05-completeAnalysisReport.md](T003-S09-05-completeAnalysisReport.md) | complete analysis report | SPECIFICATION |
| T003-S10-W01 | [T003-S10-01-stageContentCache.md](T003-S10-01-stageContentCache.md) | stage content cache | SPECIFICATION |
| T003-S10-W02 | [T003-S10-02-reverseDependencyIndexes.md](T003-S10-02-reverseDependencyIndexes.md) | reverse dependency indexes | SPECIFICATION |
| T003-S10-W03 | [T003-S10-03-negativeLookupInvalidation.md](T003-S10-03-negativeLookupInvalidation.md) | negative lookup invalidation | SPECIFICATION |
| T003-S10-W04 | [T003-S10-04-filesystemMutationEquivalence.md](T003-S10-04-filesystemMutationEquivalence.md) | filesystem mutation equivalence | SPECIFICATION |
| T003-S10-W05 | [T003-S10-05-selectiveFeatureRevise.md](T003-S10-05-selectiveFeatureRevise.md) | selective feature revise | SPECIFICATION |
| T003-S10-W06 | [T003-S10-06-cacheCorruptionConcurrency.md](T003-S10-06-cacheCorruptionConcurrency.md) | cache corruption concurrency | SPECIFICATION |
| T003-S11-W01 | [T003-S11-01-workerCleanInstall.md](T003-S11-01-workerCleanInstall.md) | worker clean install | SPECIFICATION |
| T003-S11-W02 | [T003-S11-02-buildExporterPackaging.md](T003-S11-02-buildExporterPackaging.md) | build exporter packaging | SPECIFICATION |
| T003-S11-W03 | [T003-S11-03-windowsNoAdminInstall.md](T003-S11-03-windowsNoAdminInstall.md) | windows no admin install | SPECIFICATION |
| T003-S11-W04 | [T003-S11-04-mandatoryWorkerCi.md](T003-S11-04-mandatoryWorkerCi.md) | mandatory worker ci | SPECIFICATION |
| T003-S11-W05 | [T003-S11-05-benchmarkCorpus.md](T003-S11-05-benchmarkCorpus.md) | benchmark corpus | SPECIFICATION |
| T003-S11-W06 | [T003-S11-06-regressionBudgets.md](T003-S11-06-regressionBudgets.md) | regression budgets | SPECIFICATION |
| T003-S11-W07 | [T003-S11-07-fullEndToEndAcceptance.md](T003-S11-07-fullEndToEndAcceptance.md) | full end to end acceptance | SPECIFICATION |
| T003-S11-W08 | [T003-S11-08-releaseDocumentation.md](T003-S11-08-releaseDocumentation.md) | release documentation | SPECIFICATION |
| T003-S12-W01 | [T003-S12-01-liveConfluenceConnector.md](T003-S12-01-liveConfluenceConnector.md) | live confluence connector | SPECIFICATION |
| T003-S13-W01 | [T003-S13-01-runtimeTraceProducer.md](T003-S13-01-runtimeTraceProducer.md) | runtime trace producer | SPECIFICATION |
| T003-S13-W02 | [T003-S13-02-runtimeRtaImport.md](T003-S13-02-runtimeRtaImport.md) | runtime rta import | SPECIFICATION |
| T003-S13-W03 | [T003-S13-03-runtimeValueFlow.md](T003-S13-03-runtimeValueFlow.md) | runtime value flow | SPECIFICATION |
| T003-S13-W04 | [T003-S13-04-runtimeAsyncReflection.md](T003-S13-04-runtimeAsyncReflection.md) | runtime async reflection | SPECIFICATION |

## Matice pokrytí zbývající implementace

Matice je kontrolní seznam úplnosti rozpadu vůči
[T003](3_finishProductionAnalysis.md) a aktuálním mezerám ve
[stavové matici](../production-analysis-progress.md). S01 a S02 nemají nový
implementační work package, protože jsou ve zdokumentovaném scope
`VERIFIED_IN_SCOPE`; jejich budoucí údržba je součástí každého dotčeného PR.

| Milník | Zbývající samostatné oblasti | Work packages |
|---|---|---|
| T003-S01 | Pouze průběžná údržba acceptance inventáře | žádný nový; povinná aktualizace v každém relevantním tasku |
| T003-S02 | Pouze rozšíření matice navazujícími adaptéry | žádný nový; společný provider je závazná závislost |
| T003-S03 | externí toolchain; Gradle varianty; included builds; Kotlin options; cross-repo artefakty | W01–W05 |
| T003-S04 | K2 backend; default-body mapping; coroutine mapping; dependency dispatch; golden corpus | W01–W05 |
| T003-S05 | dynamic imports; registrars/factories; condition matrix; proxy/async semantika | W01–W04 |
| T003-S06 | Kotlin access; inheritance; XML overrides; datasource realms; JPQL/HQL; named queries; dynamic query APIs; schema compatibility | W01–W08 |
| T003-S07 | argumenty; návraty; fields/mapping; Kafka identity; retry/DLT; HTTP execution; cross-service contracts; ranking; jednotné pohledy | W01–W09 |
| T003-S08 | project references; tsconfig; re-export/generics/callbacks; UI events; BE–FE value flow | W01–W05 |
| T003-S09 | XLSX advanced references; XLS diagnostics; templates; approved methodology; úplný report | W01–W05 |
| T003-S10 | stage cache; reverse indexy; negative lookup; filesystem equivalence; selective revise; corruption/concurrency | W01–W06 |
| T003-S11 | worker a exporter packaging; Windows; mandatory CI; benchmark; budgets; end-to-end acceptance; release docs | W01–W08 |
| T003-S12 | živý konektor po dodání host/API/auth kontraktu | W01 |
| T003-S13 | trace producer; RTA; value flow; async/reflection | W01–W04 |

Rozsahy spojené lomítkem patří do jednoho work package jen tehdy, když sdílejí
tentýž vstupní kontrakt a nelze je otestovat nebo publikovat bez druhé části
(např. retry/DLT, corruption/concurrency a async/reflection). Každý řádek
registru má přesto samostatnou větev, PR a vlastní acceptance.

## Jednotný formát

- Soubor zadání: `docs/tasks/<N>_<shortName>.md`, N je kladné celé číslo bez nul na začátku; shortName je ASCII lowerCamelCase.
- Task ID: `T` + N s minimálně třemi číslicemi (`T001`, `T012`, `T1000`). Číslo souboru a ID se musí shodovat.
- Etapa: `<TaskID>-S<NN>`; nový požadavek: `<TaskID>-R<NN>`; nové akceptační kritérium: `<TaskID>-AC<NN>`. Číselná část má minimálně dvě číslice.
- Čísla jsou identity, nikoli pořadí vykonávání. Závislosti se píší explicitně. Historické identity se nemění, nemažou a znovu nepřidělují.
- Při vzniku nového zadání ověř registr, soubory cílové větve a otevřené PR; použij max + 1. Před publikací ověř kolize znovu. Při kolizi přiděl nové ID pouze nepublikovanému zadání a uprav jeho odkazy.
- Nová verze stejného zadání zachová soubor/ID a zvýší pole Revision; samostatné rozšíření dostane nové ID a `Depends on`/`Supersedes` odkazy. Žádné implicitní rušení scope.
- `docs/changes/<N>_<shortPrName>.md` používá stejný styl názvu, ale **samostatnou** číselnou řadu. Číslo změny není Task ID ani GitHub PR number.
- Uživatelská feature analýza (`analysis_id`, `requirement_hash`, packet/revision) není implementační zadání a nepřečísluje se tímto registrem.

## Převod starších milníků

| Historické označení | Kanonická etapa | Rozsah |
|---|---|---|
| A | T001-S01 | Analytické jádro |
| B | T001-S02 | Datové toky a matching |
| C | T001-S03 | Artefakty a dokumentace |
| D | T001-S04 | Inkrementální analýza a host agent |
| E | T001-S05 | Confluence synchronizační boundary |
| F | T001-S06 | Flyway |
| G | T001-S07 | Multirepo |
| M0 | T002-S01 | Compiler pilot |
| M1 | T002-S02 | Maven/build kontext |
| M2 | T002-S03 | Přesná volání a dispatch |
| M3 | T002-S04 | Spring |
| M4 | T002-S05 | ORM/query/Flyway |
| M5 | T002-S06 | Integrace workflow |
| M6 | T002-S07 | Volitelný runtime import |

Historické testy zůstávají dohledatelné; v nových dokumentech a PR se píší např.
`T001-FA-14`, `T002-CG-01`, `T002-MV-02`, `T002-SP-01`, `T002-HB-01`.
Původní krátká ID uvnitř přesunutých specifikací jsou lokální aliasy v namespace
svého dokumentu. Neměň názvy existujících Python testů jen kvůli číslování.

## Převod P0–P10 z předchozích progress/change dokumentů

Úplný samostatný normativní P dokument v kontrolovaném tree nebyl přítomen.
Následující mapování zachovává témata a není prohlášením ekvivalence všech
historických acceptance ID. V novém plánu se nepoužívá druhá P číselná řada.

| Starý alias | Aktivní etapa T003 |
|---|---|
| P0 | S01, S04, S11 — matice, compiler volba a měření |
| P1 | S02, S03 — scope a kontext |
| P2 | S03 — build |
| P3 | S04 — JVM |
| P4 | S05 — Spring |
| P5 | S06 — persistence |
| P6 | S07 — integrace/dataflow |
| P7 | S08 — TypeScript/UI |
| P8 | S07, S08, S11 — ranking a pohledy |
| P9 | S02, S10, S11 — lifecycle/cache/release |
| P10 | S13 — volitelný runtime |

Označení CL/JV/BL/DB/IN/TS/RK/FLOW/EV/BC v historických změnových dokumentech
jsou historické reference, nikoli automatické PASS nových kritérií T003.

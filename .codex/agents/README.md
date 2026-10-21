# Implementační agenti pro T003

Tento adresář obsahuje 60 projektových implementačních profilů pro atomické work
packages registrované v [`docs/tasks/README.md`](../../docs/tasks/README.md)
a jeden profil pro review PR. Každý implementační TOML soubor definuje agenta
s modelem `gpt-5.6-luna` a `model_reasoning_effort = "medium"`.

Implementační agent smí implementovat pouze své zadání. Jeho instrukce vyžadují kontrolu
závislostí, architektonickou rekognoskaci, izolovaný worktree, samostatnou větev,
povinné testy, dokumentaci, sémantickou aktualizaci, commit, push a samostatný
pull request. Implementační agent PR nemerguje.

Samostatný [`code_review`](code-review.toml) používá `gpt-6.1-sol` s reasoning
effort `high` a je projektovým reviewerem podle
[T045](../../docs/tasks/45_addCodeReviewAgent.md). Po vytvoření PR mu koordinátor
předá URL nebo číslo PR. Agent čte aktuální diff a kontroly, vrací konkrétní
`REQUEST_CHANGES`/`BLOCKED`, nebo vydá `APPROVE` pro přesnou base/head SHA
dvojici. Schválené ready PR merguje až po opětovném ověření obou SHA, kontrol,
závislostí a mergeability. Draft si sám nepřepíná na ready.
Vlastní GitHub PR nelze vždy schválit stejným účtem; tehdy agent zaznamená verdikt
do PR komentáře a stále respektuje pravidla cílové větve. Stará lokální aprobace
neplatí po změně base ani HEAD.

Profily jsou projektové a Codex je načítá z `.codex/agents`. Po přidání nebo
změně profilu založ novou session, aby se obnovil registr agentů. Spuštění agenta
nemění stav `SPECIFICATION`; stav se změní až po doložené implementaci a acceptance.

## Použití

Požádej koordinačního agenta například:

```text
Implementuj T003-S03-W01 pomocí agenta t003_s03_w01_external_toolchain_selection.
Po vytvoření PR předej jeho URL agentovi code_review; po APPROVE ověř a proveď merge.
```

Koordinátor smí spustit pouze agenty, jejichž závislosti jsou splněné. Agenti se
stejnými soubory nebo navazujícími kontrakty se nespouštějí souběžně.
Interní Copilot [`kgmaker-review`](../../.github/agents/kgmaker-review.agent.md)
hodnotí artifact úlohy v `kgmaker task`; nenahrazuje review GitHub PR.

## Registr

| Work package | Agent | Zadání | Doporučená větev |
|---|---|---|---|
| T003-S03-W01 | `t003_s03_w01_external_toolchain_selection` | [Výběr externího JDK/toolchainu](../../docs/tasks/T003-S03-01-externalToolchainSelection.md) | `feat/t003-s03-01-external-toolchain-selection` |
| T003-S03-W02 | `t003_s03_w02_gradle_custom_variants` | [Gradle vlastní varianty a source sets](../../docs/tasks/T003-S03-02-gradleCustomVariants.md) | `feat/t003-s03-02-gradle-custom-variants` |
| T003-S03-W03 | `t003_s03_w03_gradle_included_builds` | [Gradle included builds](../../docs/tasks/T003-S03-03-gradleIncludedBuilds.md) | `feat/t003-s03-03-gradle-included-builds` |
| T003-S03-W04 | `t003_s03_w04_kotlin_compiler_options` | [Kotlin compiler options v build manifestu](../../docs/tasks/T003-S03-04-kotlinCompilerOptions.md) | `feat/t003-s03-04-kotlin-compiler-options` |
| T003-S03-W05 | `t003_s03_w05_cross_repo_artifact_mapping` | [Obsahové mapování cross-repo artefaktů](../../docs/tasks/T003-S03-05-crossRepoArtifactMapping.md) | `feat/t003-s03-05-cross-repo-artifact-mapping` |
| T003-S04-W01 | `t003_s04_w01_k2_analysis_api_backend` | [K2 Analysis API backend](../../docs/tasks/T003-S04-01-k2AnalysisApiBackend.md) | `feat/t003-s04-01-k2-analysis-api-backend` |
| T003-S04-W02 | `t003_s04_w02_default_body_source_mapping` | [Mapování defaultních těl a generovaných členů](../../docs/tasks/T003-S04-02-defaultBodySourceMapping.md) | `feat/t003-s04-02-default-body-source-mapping` |
| T003-S04-W03 | `t003_s04_w03_coroutine_source_mapping` | [Mapování coroutine state machine](../../docs/tasks/T003-S04-03-coroutineSourceMapping.md) | `feat/t003-s04-03-coroutine-source-mapping` |
| T003-S04-W04 | `t003_s04_w04_dependency_dispatch_hierarchy` | [Dispatch přes dependency hierarchy](../../docs/tasks/T003-S04-04-dependencyDispatchHierarchy.md) | `feat/t003-s04-04-dependency-dispatch-hierarchy` |
| T003-S04-W05 | `t003_s04_w05_jvm_golden_acceptance_corpus` | [JVM golden acceptance corpus](../../docs/tasks/T003-S04-05-jvmGoldenAcceptanceCorpus.md) | `feat/t003-s04-05-jvm-golden-acceptance-corpus` |
| T003-S05-W01 | `t003_s05_w01_dynamic_spring_imports` | [Dynamické Spring importy](../../docs/tasks/T003-S05-01-dynamicSpringImports.md) | `feat/t003-s05-01-dynamic-spring-imports` |
| T003-S05-W02 | `t003_s05_w02_spring_registrars_factories` | [Spring registrars a factories](../../docs/tasks/T003-S05-02-springRegistrarsFactories.md) | `feat/t003-s05-02-spring-registrars-factories` |
| T003-S05-W03 | `t003_s05_w03_spring_condition_matrix` | [Rozšířená condition/property/classpath matice](../../docs/tasks/T003-S05-03-springConditionMatrix.md) | `feat/t003-s05-03-spring-condition-matrix` |
| T003-S05-W04 | `t003_s05_w04_spring_proxy_async_semantics` | [Proxy, weaving a async semantika](../../docs/tasks/T003-S05-04-springProxyAsyncSemantics.md) | `feat/t003-s05-04-spring-proxy-async-semantics` |
| T003-S06-W01 | `t003_s06_w01_kotlin_jpa_access` | [Kotlin JPA use-site a access](../../docs/tasks/T003-S06-01-kotlinJpaAccess.md) | `feat/t003-s06-01-kotlin-jpa-access` |
| T003-S06-W02 | `t003_s06_w02_jpa_inherited_attributes` | [Zděděné persistence atributy](../../docs/tasks/T003-S06-02-jpaInheritedAttributes.md) | `feat/t003-s06-02-jpa-inherited-attributes` |
| T003-S06-W03 | `t003_s06_w03_orm_xml_overrides` | [ORM XML overrides](../../docs/tasks/T003-S06-03-ormXmlOverrides.md) | `feat/t003-s06-03-orm-xml-overrides` |
| T003-S06-W04 | `t003_s06_w04_multi_datasource_realms` | [Více persistence units a datasource realms](../../docs/tasks/T003-S06-04-multiDatasourceRealms.md) | `feat/t003-s06-04-multi-datasource-realms` |
| T003-S06-W05 | `t003_s06_w05_jpql_hql_grammar` | [Rozšířená JPQL/HQL gramatika](../../docs/tasks/T003-S06-05-jpqlHqlGrammar.md) | `feat/t003-s06-05-jpql-hql-grammar` |
| T003-S06-W06 | `t003_s06_w06_named_query_containers` | [NamedQueries a named native queries](../../docs/tasks/T003-S06-06-namedQueryContainers.md) | `feat/t003-s06-06-named-query-containers` |
| T003-S06-W07 | `t003_s06_w07_criteria_specification_querydsl` | [Criteria, Specification a QueryDSL](../../docs/tasks/T003-S06-07-criteriaSpecificationQuerydsl.md) | `feat/t003-s06-07-criteria-specification-querydsl` |
| T003-S06-W08 | `t003_s06_w08_schema_compatibility` | [Schema typy, nullability a klíče](../../docs/tasks/T003-S06-08-schemaCompatibility.md) | `feat/t003-s06-08-schema-compatibility` |
| T003-S07-W01 | `t003_s07_w01_argument_parameter_flow` | [Argument→parameter datový tok](../../docs/tasks/T003-S07-01-argumentParameterFlow.md) | `feat/t003-s07-01-argument-parameter-flow` |
| T003-S07-W02 | `t003_s07_w02_return_consumer_flow` | [Return→consumer datový tok](../../docs/tasks/T003-S07-02-returnConsumerFlow.md) | `feat/t003-s07-02-return-consumer-flow` |
| T003-S07-W03 | `t003_s07_w03_field_and_mapping_flow` | [Field a explicitní mapping tok](../../docs/tasks/T003-S07-03-fieldAndMappingFlow.md) | `feat/t003-s07-03-field-and-mapping-flow` |
| T003-S07-W04 | `t003_s07_w04_kafka_binding_identity` | [Kafka binding a identita topicu](../../docs/tasks/T003-S07-04-kafkaBindingIdentity.md) | `feat/t003-s07-04-kafka-binding-identity` |
| T003-S07-W05 | `t003_s07_w05_kafka_retry_dlt` | [Kafka retry, DLT a subscription hranice](../../docs/tasks/T003-S07-05-kafkaRetryDlt.md) | `feat/t003-s07-05-kafka-retry-dlt` |
| T003-S07-W06 | `t003_s07_w06_http_client_execution` | [HTTP klient: request versus execution](../../docs/tasks/T003-S07-06-httpClientExecution.md) | `feat/t003-s07-06-http-client-execution` |
| T003-S07-W07 | `t003_s07_w07_cross_service_contract_mapping` | [Cross-service contract/release mapping](../../docs/tasks/T003-S07-07-crossServiceContractMapping.md) | `feat/t003-s07-07-cross-service-contract-mapping` |
| T003-S07-W08 | `t003_s07_w08_evidence_ranking` | [Vysvětlitelný execution/impact ranking](../../docs/tasks/T003-S07-08-evidenceRanking.md) | `feat/t003-s07-08-evidence-ranking` |
| T003-S07-W09 | `t003_s07_w09_unified_flow_views` | [Jednotné flow pohledy](../../docs/tasks/T003-S07-09-unifiedFlowViews.md) | `feat/t003-s07-09-unified-flow-views` |
| T003-S08-W01 | `t003_s08_w01_typescript_project_references` | [TypeScript project references](../../docs/tasks/T003-S08-01-typescriptProjectReferences.md) | `feat/t003-s08-01-typescript-project-references` |
| T003-S08-W02 | `t003_s08_w02_tsconfig_paths_exclude` | [tsconfig paths a exclude](../../docs/tasks/T003-S08-02-tsconfigPathsExclude.md) | `feat/t003-s08-02-tsconfig-paths-exclude` |
| T003-S08-W03 | `t003_s08_w03_typescript_callbacks_generics` | [TypeScript callback/generic resolution](../../docs/tasks/T003-S08-03-typescriptCallbacksGenerics.md) | `feat/t003-s08-03-typescript-callbacks-generics` |
| T003-S08-W04 | `t003_s08_w04_versioned_ui_events` | [Verzovaný UI event adaptér](../../docs/tasks/T003-S08-04-versionedUiEvents.md) | `feat/t003-s08-04-versioned-ui-events` |
| T003-S08-W05 | `t003_s08_w05_backend_frontend_value_flow` | [Backend→frontend value flow](../../docs/tasks/T003-S08-05-backendFrontendValueFlow.md) | `feat/t003-s08-05-backend-frontend-value-flow` |
| T003-S09-W01 | `t003_s09_w01_xlsx_advanced_references` | [XLSX shared, INDIRECT a external reference diagnostika](../../docs/tasks/T003-S09-01-xlsxAdvancedReferences.md) | `feat/t003-s09-01-xlsx-advanced-references` |
| T003-S09-W02 | `t003_s09_w02_binary_xls_diagnostics` | [Binární XLS diagnostika](../../docs/tasks/T003-S09-02-binaryXlsDiagnostics.md) | `feat/t003-s09-02-binary-xls-diagnostics` |
| T003-S09-W03 | `t003_s09_w03_template_dialect_expansion` | [Rozšíření template dialectu](../../docs/tasks/T003-S09-03-templateDialectExpansion.md) | `feat/t003-s09-03-template-dialect-expansion` |
| T003-S09-W04 | `t003_s09_w04_approved_methodology_conflicts` | [Schválená metodika a konflikty provenance](../../docs/tasks/T003-S09-04-approvedMethodologyConflicts.md) | `feat/t003-s09-04-approved-methodology-conflicts` |
| T003-S09-W05 | `t003_s09_w05_complete_analysis_report` | [Úplný analytický report](../../docs/tasks/T003-S09-05-completeAnalysisReport.md) | `feat/t003-s09-05-complete-analysis-report` |
| T003-S10-W01 | `t003_s10_w01_stage_content_cache` | [Content-addressed cache po stupních](../../docs/tasks/T003-S10-01-stageContentCache.md) | `feat/t003-s10-01-stage-content-cache` |
| T003-S10-W02 | `t003_s10_w02_reverse_dependency_indexes` | [Reverse dependency indexy](../../docs/tasks/T003-S10-02-reverseDependencyIndexes.md) | `feat/t003-s10-02-reverse-dependency-indexes` |
| T003-S10-W03 | `t003_s10_w03_negative_lookup_invalidation` | [Invalidace negativních lookupů](../../docs/tasks/T003-S10-03-negativeLookupInvalidation.md) | `feat/t003-s10-03-negative-lookup-invalidation` |
| T003-S10-W04 | `t003_s10_w04_filesystem_mutation_equivalence` | [Ekvivalence add/change/delete/rename](../../docs/tasks/T003-S10-04-filesystemMutationEquivalence.md) | `feat/t003-s10-04-filesystem-mutation-equivalence` |
| T003-S10-W05 | `t003_s10_w05_selective_feature_revise` | [Selektivní revise a historie](../../docs/tasks/T003-S10-05-selectiveFeatureRevise.md) | `feat/t003-s10-05-selective-feature-revise` |
| T003-S10-W06 | `t003_s10_w06_cache_corruption_concurrency` | [Corruption fallback a worker concurrency](../../docs/tasks/T003-S10-06-cacheCorruptionConcurrency.md) | `feat/t003-s10-06-cache-corruption-concurrency` |
| T003-S11-W01 | `t003_s11_w01_worker_clean_install` | [Worker distribuce mimo checkout](../../docs/tasks/T003-S11-01-workerCleanInstall.md) | `feat/t003-s11-01-worker-clean-install` |
| T003-S11-W02 | `t003_s11_w02_build_exporter_packaging` | [Maven/Gradle exporter distribuce](../../docs/tasks/T003-S11-02-buildExporterPackaging.md) | `feat/t003-s11-02-build-exporter-packaging` |
| T003-S11-W03 | `t003_s11_w03_windows_no_admin_install` | [Windows instalace bez admin práv](../../docs/tasks/T003-S11-03-windowsNoAdminInstall.md) | `feat/t003-s11-03-windows-no-admin-install` |
| T003-S11-W04 | `t003_s11_w04_mandatory_worker_ci` | [Povinné worker CI joby](../../docs/tasks/T003-S11-04-mandatoryWorkerCi.md) | `feat/t003-s11-04-mandatory-worker-ci` |
| T003-S11-W05 | `t003_s11_w05_benchmark_corpus` | [Benchmark corpus a měření](../../docs/tasks/T003-S11-05-benchmarkCorpus.md) | `feat/t003-s11-05-benchmark-corpus` |
| T003-S11-W06 | `t003_s11_w06_regression_budgets` | [Výkonové regression budgets](../../docs/tasks/T003-S11-06-regressionBudgets.md) | `feat/t003-s11-06-regression-budgets` |
| T003-S11-W07 | `t003_s11_w07_full_end_to_end_acceptance` | [Společná end-to-end acceptance](../../docs/tasks/T003-S11-07-fullEndToEndAcceptance.md) | `feat/t003-s11-07-full-end-to-end-acceptance` |
| T003-S11-W08 | `t003_s11_w08_release_documentation` | [Release a capability dokumentace](../../docs/tasks/T003-S11-08-releaseDocumentation.md) | `feat/t003-s11-08-release-documentation` |
| T003-S12-W01 | `t003_s12_w01_live_confluence_connector` | [Živý Confluence konektor](../../docs/tasks/T003-S12-01-liveConfluenceConnector.md) | `feat/t003-s12-01-live-confluence-connector` |
| T003-S13-W01 | `t003_s13_w01_runtime_trace_producer` | [Sanitizovaný runtime trace producer](../../docs/tasks/T003-S13-01-runtimeTraceProducer.md) | `feat/t003-s13-01-runtime-trace-producer` |
| T003-S13-W02 | `t003_s13_w02_runtime_rta_import` | [RTA a runtime dispatch import](../../docs/tasks/T003-S13-02-runtimeRtaImport.md) | `feat/t003-s13-02-runtime-rta-import` |
| T003-S13-W03 | `t003_s13_w03_runtime_value_flow` | [Runtime value-flow evidence](../../docs/tasks/T003-S13-03-runtimeValueFlow.md) | `feat/t003-s13-03-runtime-value-flow` |
| T003-S13-W04 | `t003_s13_w04_runtime_async_reflection` | [Async a reflective runtime capture](../../docs/tasks/T003-S13-04-runtimeAsyncReflection.md) | `feat/t003-s13-04-runtime-async-reflection` |

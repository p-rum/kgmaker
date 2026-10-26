# Inventář acceptance T001 a T002

## T003-S08-W01 — project references

| ID | Stav | Přímý test / podporovaná matice |
|---|---|---|
| T003-S08-W01-AC01 | VERIFIED_IN_SCOPE | `test_solution_programs_resolve_exact_source_project_identities_without_outputs`, `test_source_redirect_does_not_resolve_against_stale_emitted_declaration`: skutečný TS 5.7.3 / Node 24.19.0; missing/cycle/outside reference je lokalizovaná chyba |
| T003-S08-W01-AC02 | VERIFIED_IN_SCOPE | `test_graph_loader_legacy_versions_remain_accepted`; původní single-project worker regression tests; additive project_graph v1, graph/store/protocol beze změny |
| T003-S08-W01-AC03 | VERIFIED_IN_SCOPE | `test_invalid_reference_graph_is_localized_and_does_not_replace_store`, `test_overlapping_projects_do_not_arbitrarily_choose_symbol_owner`, `test_transitive_project_edit_invalidates_stored_compiler_layer_offline`: žádné falešné rozlišení, žádný zápis na chybě |
| T003-S08-W01-AC04 | VERIFIED_IN_SCOPE | [change note 36](changes/36_resolveTypeScriptProjectReferences.md), [stavová matice](production-analysis-progress.md); celý S08/AC08 nadále PARTIAL |

Review opravy W01: `test_consumer_options_do_not_fork_owner_declaration_or_lose_its_cfg`
ověřuje owner TypeChecker identity, owner CFG a argument parameter při rozdílném
`strictNullChecks`; `test_disabled_source_redirect_rejects_stale_declaration_without_store_mutation`
odmítá stale `.d.ts` přes vypnuté source redirects. Finální integrovaná strict sada
nad main `3503309`: **302 PASS / 7 SKIP**, vlastní worker v2; celý T003-AC08 zůstává PARTIAL.

## T003-S11-W02 — distribuce build exporterů

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S11-W02-AC01 | VERIFIED_IN_SCOPE | `test_installed_exporters_run_real_builds_outside_checkout` (Maven/Gradle), descriptor hash/protocol negative tests; Linux/Python3.12/JDK21 |
| T003-S11-W02-AC02 | VERIFIED_IN_SCOPE | Aditivní `exporter_contract`, původní BuildPlan/BuildManifest v1 a graph v1/v2/v3; existující build-runner regrese |
| T003-S11-W02-AC03 | VERIFIED_IN_SCOPE | `test_invalid_distribution_fails_before_process_or_store_mutation`, `test_changed_distribution_manifest_invalidates_existing_plan`, `test_output_protocol_mismatch_does_not_publish_manifest_or_graph` |
| T003-S11-W02-AC04 | VERIFIED_IN_SCOPE | [Change note37](changes/37_packageBuildExporters.md) uvádí skutečné běhy i zbývající release gates; T003-S11 zůstává PARTIAL |

## Doplnění T003-S11-W01 (2026-10-26)

| ID | Stav | Podporovaný rozsah a přímá evidence | Běh |
|---|---|---|---|
| T003-S11-W01-AC01 | VERIFIED_IN_SCOPE | `test_worker_install.py`: skutečné sdist/wheel → offline venv mimo checkout, JVM/TS compiler analýza; SOURCE_ONLY bez JDK/Node a child procesů; explicitní/env/resource precedence | 7 PASS, Python 3.12/Linux |
| T003-S11-W01-AC02 | VERIFIED_IN_SCOPE | Stejný graph/store/protocol; instalovaný scan/save/load, existující store a compiler regression tests | Bez schema migrace |
| T003-S11-W01-AC03 | VERIFIED_IN_SCOPE | Missing distribution a ambiguous JVM JAR nevyvolají proces ani nepřepíší poslední graf; žádný automatický fallback explicitní volby | 7 PASS |
| T003-S11-W01-AC04 | VERIFIED_IN_SCOPE | [Stavová matice](production-analysis-progress.md) a [change note 30](changes/30_packageWorkerResources.md) uvádějí konkrétní běhy a omezení | T003-AC11 nadále PARTIAL |

## T005 — model high-level pohledu

| Acceptance | Stav | Přímý test | Výsledek |
|---|---|---|---|
| T005-AC01 deterministická serializace | PASS | `tests/test_t005_add_view_model.py::test_permuted_inputs_have_byte_identical_canonical_json` | cílený běh |
| T005-AC02 endpoint/evidence validace | PASS | `test_unknown_version_and_dangling_endpoint_or_evidence_are_rejected` | cílený běh |
| T005-AC03 graph v1/v2/v3 kompatibilita | PASS | `test_existing_graph_loader_still_accepts_legacy_schema_versions` | cílený běh |
| T005-AC04 invalidní vstup bez mutace | PASS | `test_duplicate_node_id_has_structured_validation_error` | cílený běh |
| T005-AC05 zachování scope, kontextu, evidence a unresolved coverage | PASS | `test_scope_context_and_evidence_kind_are_preserved_without_upgrade`; `test_complete_coverage_cannot_hide_unresolved_edges` | cílený běh |
| T005-AC06 dokumentace a change note | PASS | `docs/changes/11_addViewModel.md` | PR #11 sloučen do main; finální integrované ověření je v change note |

Datum auditu: 2026-10-15. Autoritativní scénáře jsou v
[T001](tasks/1_featureAnalysis.md) a [T002](tasks/2_buildAwareInspection.md).
`VERIFIED_IN_SCOPE` platí jen pro verzi adaptéru a fixture uvedené v řádku;
`PARTIAL` a `NOT_IMPLEMENTED` nejsou PASS. Společný lokální běh aktuálního
worktree: `python3 -m pytest -q` — **184 passed in 15.93 s**, Python 3.12.

## T001

| ID | Stav | Verze / podporovaný rozsah | Přímá evidence v testech | Běh |
|---|---|---|---|---|
| T001-FA-01 | PARTIAL | `dataflow-1`, lokální explicitní mapping | `test_dataflow.py::test_kotlin_constructor_fields_expression_and_mapping` | 184 PASS |
| T001-FA-02 | VERIFIED_IN_SCOPE | `feature-inventory-4` | `test_feature.py::test_fa02_04_no_automatic_liquidity_or_absence_claim` | 184 PASS |
| T001-FA-03 | PARTIAL | `dataflow-1`, report contract | `test_feature_fixture.py::test_fixture_cli_lifecycle` | 184 PASS |
| T001-FA-04 | VERIFIED_IN_SCOPE | `feature-inventory-4` | `test_feature.py::test_fa02_04_no_automatic_liquidity_or_absence_claim` | 184 PASS |
| T001-FA-05 | VERIFIED_IN_SCOPE | availability proof v1 | `test_data_check.py::test_derivation_cycles_reuse_validator` | 184 PASS |
| T001-FA-06 | VERIFIED_IN_SCOPE | availability proof v1 | `test_feature.py::test_cyclic_derivation_and_document_only_reuse_are_rejected` | 184 PASS |
| T001-FA-07 | VERIFIED_IN_SCOPE | `feature-inventory-4` | `test_feature.py::test_fa07_apply_isolated_and_idempotent` | 184 PASS |
| T001-FA-08 | PARTIAL | `dataflow-1`, Thymeleaf subset, workspace v1 | `test_workspace.py::test_fa46_47_identity_and_cross_repo_impact`; `test_templates.py` | 184 PASS |
| T001-FA-09 | VERIFIED_IN_SCOPE | `dataflow-1` | `test_dataflow.py::test_ambiguous_types_do_not_create_maps` | 184 PASS |
| T001-FA-10 | VERIFIED_IN_SCOPE | feature validator v1 | `test_feature.py::test_fa10_forged_citations_and_no_mutation` | 184 PASS |
| T001-FA-11 | VERIFIED_IN_SCOPE | feature packet v1 | `test_feature.py::test_fa11_packet_and_revision_mismatch` | 184 PASS |
| T001-FA-12 | VERIFIED_IN_SCOPE | feature packet v1 | `test_feature.py::test_fa12_prepare_is_idempotent_and_preserves_candidate` | 184 PASS |
| T001-FA-13 | VERIFIED_IN_SCOPE | content-bound packet v1 | `test_feature.py::test_fa13_uncommitted_changes_and_requirement_invalidate` | 184 PASS |
| T001-FA-14 | NOT_IMPLEMENTED | selective feature conclusion reuse | žádný přímý acceptance test | NOT_RUN |
| T001-FA-15 | NOT_IMPLEMENTED | negative lookup reverse index | žádný přímý acceptance test | NOT_RUN |
| T001-FA-16 | PARTIAL | revise history v1 | `test_feature.py::test_revise_preserves_history_and_accepts_new_answer_file` | 184 PASS |
| T001-FA-17 | PARTIAL | proposal/report v1 | `test_feature_fixture.py::test_fixture_cli_lifecycle` | 184 PASS |
| T001-FA-18 | VERIFIED_IN_SCOPE | bounded inventory/report v1 | `test_feature.py::test_fa18_19_small_budget_produces_incomplete_inventory` | 184 PASS |
| T001-FA-19 | VERIFIED_IN_SCOPE | bounded inventory/report v1 | `test_feature.py::test_fa18_19_small_budget_produces_incomplete_inventory` | 184 PASS |
| T001-FA-20 | PARTIAL | offline Confluence document validation v1 | `test_scanner.py::test_confluence_code_is_truth_and_report_preserves_stale_documentation` | 184 PASS |
| T001-FA-21 | NOT_IMPLEMENTED | approved methodology authority model | žádný přímý acceptance test | NOT_RUN |
| T001-FA-22 | VERIFIED_IN_SCOPE | `xlsx-offline-1` | `test_workbooks.py::test_fa22_extracts_cells_formula_dependencies_named_ranges_and_cache` | 184 PASS |
| T001-FA-23 | VERIFIED_IN_SCOPE | `xlsx-offline-1` | `test_workbooks.py::test_fa23_reports_shared_indirect_external_and_binary_xls` | 184 PASS |
| T001-FA-24 | NOT_IMPLEMENTED | canonical incremental add/change/delete/rename | žádný full-vs-incremental acceptance test | NOT_RUN |
| T001-FA-25 | VERIFIED_IN_SCOPE | feature lifecycle v1 | `test_feature.py::test_fa25_cli_workflow_without_semantic_packet_or_git` | 184 PASS |
| T001-FA-26 | VERIFIED_IN_SCOPE | optional artifact coverage | `test_feature_fixture.py::test_fixture_cli_lifecycle` | 184 PASS |
| T001-FA-27 | VERIFIED_IN_SCOPE | feature validator v1 | `test_feature.py::test_fa27_dangling_proposal_and_traversal_rejected` | 184 PASS |
| T001-FA-28 | VERIFIED_IN_SCOPE | fake Confluence sync boundary v1 | `test_confluence_sync.py::test_fa28_page_version_change_after_approval_conflicts_without_overwrite` | 184 PASS |
| T001-FA-29 | VERIFIED_IN_SCOPE | fake Confluence sync boundary v1 | `test_confluence_sync.py::test_fa29_payload_change_after_approval_is_rejected_before_adapter_write` | 184 PASS |
| T001-FA-30 | VERIFIED_IN_SCOPE | fake Confluence sync boundary v1 | `test_confluence_sync.py::test_fa30_publish_preserves_owner_content_and_reimport_remains_to_be` | 184 PASS |
| T001-FA-31 | PARTIAL | graph schemas v1/v2/v3 | `test_feature.py::test_fa31_graph_version_compatibility`; `test_production_scope.py::test_bc01_existing_build_scan_and_hook_never_launch_project_tools` | 184 PASS |
| T001-FA-32 | VERIFIED_IN_SCOPE | init templates v1 | `test_feature.py::test_init_preserves_user_analyst_and_junie_files`; `test_init.py` | 184 PASS |
| T001-FA-33 | VERIFIED_IN_SCOPE | report marker v1 | `test_feature.py::test_fa33_report_not_used_as_source_evidence` | 184 PASS |
| T001-FA-34 | VERIFIED_IN_SCOPE | report state v1 | `test_feature.py::test_fa34_processing_complete_with_business_decision_blocked` | 184 PASS |
| T001-FA-35 | VERIFIED_IN_SCOPE | `dataflow-1` | `test_dataflow.py::test_fa35_direction_weakest_link_and_external_boundary` | 184 PASS |
| T001-FA-36 | VERIFIED_IN_SCOPE | `flyway-offline-1` / `postgres-ddl-1` | `test_flyway.py::test_fa36_37_order_lifecycle_and_constraints` | 184 PASS |
| T001-FA-37 | VERIFIED_IN_SCOPE | `flyway-offline-1` / `postgres-ddl-1` | `test_flyway.py::test_fa36_37_order_lifecycle_and_constraints` | 184 PASS |
| T001-FA-38 | VERIFIED_IN_SCOPE | `flyway-offline-1` | `test_flyway.py::test_fa38_repeatables_and_historical_diff` | 184 PASS |
| T001-FA-39 | VERIFIED_IN_SCOPE | `flyway-offline-1` | `test_flyway.py::test_fa39_44_equivalent_versions_but_no_gap_guess` | 184 PASS |
| T001-FA-40 | VERIFIED_IN_SCOPE | `flyway-offline-1` / `postgres-ddl-1` | `test_flyway.py::test_fa40_placeholders_quoting_and_search_path` | 184 PASS |
| T001-FA-41 | VERIFIED_IN_SCOPE | `flyway-offline-1` / `postgres-ddl-1` | `test_flyway.py::test_fa41_61_unknown_body_and_literals` | 184 PASS |
| T001-FA-42 | VERIFIED_IN_SCOPE | schema evidence v1, availability UNKNOWN | `test_workspace.py::test_workspace_data_check_and_report_are_valid`; `test_availability.py::test_dto_or_migration_declaration_alone_not_available` | 184 PASS |
| T001-FA-43 | VERIFIED_IN_SCOPE | Flyway checkpoints v1 | `test_flyway.py::test_fa43_checkpoint_replay_matches_full_after_old_change` | 184 PASS |
| T001-FA-44 | VERIFIED_IN_SCOPE | `flyway-offline-1` | `test_flyway.py::test_fa39_44_equivalent_versions_but_no_gap_guess` | 184 PASS |
| T001-FA-45 | VERIFIED_IN_SCOPE | schema mapping v1 | `test_flyway.py::test_fa45_schema_mapping_precision_nullability_and_absent_column` | 184 PASS |
| T001-FA-46 | VERIFIED_IN_SCOPE | workspace v1 | `test_workspace.py::test_fa46_47_identity_and_cross_repo_impact` | 184 PASS |
| T001-FA-47 | VERIFIED_IN_SCOPE | workspace v1 / `dataflow-1` | `test_workspace.py::test_fa46_47_identity_and_cross_repo_impact` | 184 PASS |
| T001-FA-48 | VERIFIED_IN_SCOPE | explicit service identity v1 | `test_workspace.py::test_fa48_duplicate_service_identity_not_confirmed` | 184 PASS |
| T001-FA-49 | VERIFIED_IN_SCOPE | generated contract metadata v1 | `test_workspace.py::test_fa49_generation_origin_and_stale_contract` | 184 PASS |
| T001-FA-50 | VERIFIED_IN_SCOPE | test overlay v1 | `test_workspace.py::test_fa50_request_only_not_field_coverage` | 184 PASS |
| T001-FA-51 | VERIFIED_IN_SCOPE | test impact v1 | `test_workspace.py::test_fa63_test_sql_mismatch_and_fa51_fixture_impact` | 184 PASS |
| T001-FA-52 | VERIFIED_IN_SCOPE | workspace v1 | `test_workspace.py::test_fa52_59_missing_checkout_and_reappearance` | 184 PASS |
| T001-FA-53 | VERIFIED_IN_SCOPE | content-addressed repo cache v1 | `test_workspace.py::test_fa53_unchanged_backend_not_reparsed` | 184 PASS |
| T001-FA-54 | VERIFIED_IN_SCOPE | repo-qualified validator v1 | `test_workspace.py::test_fa54_evidence_repo_mismatch_and_idempotent_prepare` | 184 PASS |
| T001-FA-55 | VERIFIED_IN_SCOPE | isolated apply v1 | `test_workspace.py::test_fa55_57_apply_no_source_write_or_execution` | 184 PASS |
| T001-FA-56 | PARTIAL | runtime/test state separation v1 | `test_build_runner.py::test_xml_build_pass_is_not_test_pass` | 184 PASS |
| T001-FA-57 | VERIFIED_IN_SCOPE | offline workspace v1 | `test_workspace.py::test_fa55_57_apply_no_source_write_or_execution` | 184 PASS |
| T001-FA-58 | VERIFIED_IN_SCOPE | coherent workspace snapshot v1 | `test_workspace.py::test_fa58_mixed_snapshot_rejected` | 184 PASS |
| T001-FA-59 | VERIFIED_IN_SCOPE | workspace presence baseline v1 | `test_workspace.py::test_fa52_59_missing_checkout_and_reappearance` | 184 PASS |
| T001-FA-60 | VERIFIED_IN_SCOPE | single-repo compatibility | `test_feature_fixture.py::test_fixture_cli_lifecycle` | 184 PASS |
| T001-FA-61 | VERIFIED_IN_SCOPE | `postgres-ddl-1` | `test_flyway.py::test_fa41_61_unknown_body_and_literals` | 184 PASS |
| T001-FA-62 | VERIFIED_IN_SCOPE | `flyway-offline-1` | `test_flyway.py::test_fa62_baseline_script_and_undo` | 184 PASS |
| T001-FA-63 | VERIFIED_IN_SCOPE | test/schema comparison v1 | `test_workspace.py::test_fa63_test_sql_mismatch_and_fa51_fixture_impact` | 184 PASS |
| T001-FA-64 | VERIFIED_IN_SCOPE | multi-stream replay v1 | `test_flyway.py::test_fa64_independent_streams_have_no_version_collision` | 184 PASS |
| T001-FA-65 | VERIFIED_IN_SCOPE | init data-auditor templates v1 | `test_init.py::test_init_generates_all_agent_templates` | 184 PASS |
| T001-FA-66 | VERIFIED_IN_SCOPE | deterministic data-check v1 | `test_data_check.py::test_fa66_68_static_candidates_are_unknown_and_use_existing_validation` | 184 PASS |
| T001-FA-67 | PARTIAL | LLM decomposition remains host-agent behavior | agent template plus `test_data_check.py`; no model integration acceptance | NOT_RUN |
| T001-FA-68 | VERIFIED_IN_SCOPE | availability proof v1 | `test_data_check.py::test_fa66_68_static_candidates_are_unknown_and_use_existing_validation` | 184 PASS |
| T001-FA-69 | VERIFIED_IN_SCOPE | content-bound data-check v1 | `test_data_check.py::test_fa69_source_and_answer_hash_drift_fail_closed` | 184 PASS |
| T001-FA-70 | VERIFIED_IN_SCOPE | coverage/delivery separation v1 | `test_data_check.py::test_fa70_coverage_gaps_are_not_delivery_gaps` | 184 PASS |
| T001-FA-71 | VERIFIED_IN_SCOPE | argv-only CLI v1 | `test_data_check.py::test_fa71_72_cli_no_shell_and_incomplete_exit` | 184 PASS |
| T001-FA-72 | VERIFIED_IN_SCOPE | Python CLI core | `test_data_check.py::test_fa71_72_cli_no_shell_and_incomplete_exit` | 184 PASS |
| T001-FA-73 | NOT_IMPLEMENTED | dependency-aware LLM extraction reuse | žádný přímý acceptance test | NOT_RUN |
| T001-FA-74 | VERIFIED_IN_SCOPE | data-check/apply isolation v1 | `test_data_check.py::test_fa74_validate_apply_report_preserve_sources_and_as_is` | 184 PASS |

## T002

| ID | Stav | Verze / podporovaný rozsah | Přímá evidence v testech | Běh |
|---|---|---|---|---|
| T002-CG-01 | VERIFIED_IN_SCOPE | `inspection-1`, Java/mixed fixture | `test_compiler_workers.py::test_p0_jv01_real_mixed_compiler_calls_exactly_match_ground_truth` | 184 PASS |
| T002-CG-02 | PARTIAL | declared target + omezené CHA | `test_compiler_workers.py::test_bytecode_is_distinct_and_cha_completeness_is_not_invented` | 184 PASS |
| T002-CG-03 | PARTIAL | bounded traversal/CFG, ne úplná konstrukční matice | `test_control_flow.py`; `test_compiler_workers.py` | 184 PASS |
| T002-CG-04 | PARTIAL | K1 compatibility backend, unsupported boundaries | `test_compiler_workers.py::test_unsupported_property_bodies_have_boundaries_instead_of_guessed_callers` | 184 PASS |
| T002-CG-05 | PARTIAL | unresolved boundary model | `test_control_flow.py::test_unknown_expression_calls_do_not_gain_invented_evaluation_order` | 184 PASS |
| T002-MV-01 | PARTIAL | `build-manifest-1`, profily bez úplného BOM/toolchain modelu | `test_build_aware.py::test_maven_discovery_is_declared_and_reports_missing_reactor_module` | 184 PASS |
| T002-MV-02 | NOT_IMPLEMENTED | reactor output precedence proti stale local JAR | žádný skutečný acceptance test | NOT_RUN |
| T002-MV-03 | VERIFIED_IN_SCOPE | `build-plan-1` | `test_build_runner.py::test_failed_build_cannot_claim_old_fresh_output` | 184 PASS |
| T002-MV-04 | PARTIAL | XML test-state import v1 | `test_build_runner.py::test_xml_build_pass_is_not_test_pass`; `test_actual_xml_test_execution_is_visible_even_before_test_phase` | 184 PASS |
| T002-MV-05 | VERIFIED_IN_SCOPE | SOURCE_ONLY fallback | `test_production_scope.py::test_bc01_existing_build_scan_and_hook_never_launch_project_tools` | 184 PASS |
| T002-SP-01 | PARTIAL | framework rules v1 | `test_build_aware.py::test_framework_projection_keeps_framework_evidence_separate` | 184 PASS |
| T002-SP-02 | PARTIAL | self-invocation/proxy evidence subset | `test_build_aware.py::test_framework_projection_keeps_framework_evidence_separate` | 184 PASS |
| T002-SP-03 | PARTIAL | explicit framework boundary subset | `test_build_aware.py::test_framework_projection_keeps_framework_evidence_separate`; `test_control_flow.py::test_flow03_await_has_explicit_resume_and_exception_boundary` | 184 PASS |
| T002-HB-01 | PARTIAL | Java annotation mapping subset | `test_build_aware.py::test_framework_projection_keeps_framework_evidence_separate` | 184 PASS |
| T002-HB-02 | NOT_IMPLEMENTED | custom naming + multi-datasource realm matrix | žádný přímý acceptance test | NOT_RUN |
| T002-HB-03 | PARTIAL | Spring Data/query projection subset | `test_build_aware.py::test_framework_projection_keeps_framework_evidence_separate` | 184 PASS |
| T002-HB-04 | PARTIAL | Flyway stream/type/nullability subset | `test_flyway.py::test_fa45_schema_mapping_precision_nullability_and_absent_column` | 184 PASS |
| T002-WS-01 | VERIFIED_IN_SCOPE | selective source/module/classpath/profile packet invalidation | `test_graph_provider.py::test_stale_module_is_projected_out_while_other_context_remains_usable`; `test_compiler_workers.py::CompilerWorkerTests::test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle`; workspace freshness tests | 197 PASS |
| T002-EV-01 | PARTIAL | hash-bound runtime import v1 | `test_build_aware.py::test_runtime_import_is_bound_to_context_and_rejects_stale_source`; `test_production_scope.py::test_ev02_forged_evidence_reference_and_promoted_candidate_are_rejected` | 184 PASS |
| T002-EV-02 | VERIFIED_IN_SCOPE | availability proof v1 | `test_availability.py::test_dto_or_migration_declaration_alone_not_available` | 184 PASS |
| T002-BC-01 | VERIFIED_IN_SCOPE | graph v1/v2/v3 migration; offline refresh | `test_production_scope.py::test_bc01_existing_build_scan_and_hook_never_launch_project_tools`; `test_graph_provider.py` | 184 PASS |
| T002-EX-01 | PARTIAL | worker timeout/cancel + copied-input mutation | `test_worker_protocol.py`; `test_build_runner.py::test_project_mutating_copied_inputs_cannot_produce_fresh_analysis` | 184 PASS |

T003-S03-W05 doplňuje bounded workspace release mapping v1. Přímá evidence
`test_content_bound_release_output_links_exact_consumer_classpath`,
`test_same_gav_and_class_name_with_different_bytes_stays_partial`,
`test_duplicate_content_match_is_ambiguous_and_creates_no_edge` a
`test_invalid_release_mapping_preserves_existing_store_and_legacy_absence`;
`test_directory_outputs_are_not_misreported_as_content_identical` drží
class-directory/resource mismatch explicitně `PARTIAL`;
`test_artifact_mutation_during_snapshot_is_stale_and_preserves_store` navíc
ověřuje nulovou publikaci/cache mutaci při závodu. Sada pokrývá
T003-S03-W05-AC01 až AC04. Stav je VERIFIED_IN_SCOPE pouze pro přesně
deklarovaný BuildManifest output a fresh compiler context; celý T003-S03 zůstává
PARTIAL a runtime deployment zůstává UNKNOWN.

## Neuzavřené blokátory

Aktualizace 2026-10-16: následující evidence nahrazuje odpovídající starší řádky
tabulky. Celý navazující běh měl **197 passed in 45.14 s**; zaměřený
worker/build/provider/feature běh měl **53 passed in 28.60 s**.

| ID | Aktuální stav | Nová přímá evidence | Zbývající rozsah |
|---|---|---|---|
| T001-FA-21 | VERIFIED_IN_SCOPE | `test_scanner.py::test_fa21_approved_requirement_conflict_preserves_authority` | Libovolná business/číselná ekvivalence není tímto tvrzena; explicitní hash-bound sidecar je dodaná provenance |
| T002-MV-02 | VERIFIED_IN_SCOPE | `test_build_runner.py::test_mv02_real_reactor_output_precedes_stale_repository_jar` — skutečný Maven/JDK/exporter | Širší packaging/variant/toolchain matrix patří do S03/S11 |
| T002-MV-01 / T003-S03-W01 / T003-S03-W04 | VERIFIED_IN_SCOPE | Testy explicitního Java home ověřují content-bound JDK selection/fingerprint, skutečné `JAVA_HOME`, změnu/chybění a mismatch bez fresh outputs. `test_kotlin_build_options.py` ověřuje reálný Maven 2.1.10 a Gradle 8.13 export task/execution-level Kotlin language/API/JVM targetu a flags; implicitní nevyřešené defaults dávají PARTIAL, skutečný Maven `all-open` plugin je SHA-256-bound a jeho výměna se odmítá před store zápisem. Změna flagu mění pouze dotčenou context identity; malformed options jsou odmítnuty bez implicitního procesu. Reactor fixture dále ověřuje `maven-session-2`, inherited profil, parent/BOM, dependency model a generated source až po JVM symbol `origin=generated` | Gradle custom varianty/included builds a cross-repo artefakty zůstávají v T003-S03; zachycené options nerozšiřují K1 podporu |
| T002-CG-03 | PARTIAL | konstrukční test ověřuje compiler-resolved constructor/lambda/reference/operator, primary-constructor initializer/init pořadí a custom accessor; `test_kotlin_file_facade_and_object_initializers_keep_distinct_callers` ověřuje file `<clinit>` proti object constructor realm; `test_control_flow.py` ověřuje when/Elvis/short-circuit/try/finally/break/continue | K2, default-body/coroutine mapping a širší ručně anotovaný corpus |
| T003-AC05 / T002-SP-01–03 | VERIFIED_IN_SCOPE | `test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard` — dva profily, qualifier, primary, collection/map/optional/provider, property/custom condition UNKNOWN, ambiguity, self-invocation, compiler-symbol meta-stereotype, explicitní component package, statický Configuration/Import/Bean graf a cizí short-name anotace; rules `annotation-source-v3` | Dynamic ImportSelector/registrars/factories a runtime proxy/async execution zůstávají mimo tvrzený scope |
| T002-HB-02 | PARTIAL | `test_build_aware.py::test_hb02_schema_realm_and_unverified_naming_do_not_silently_merge` | Kompletní multi-datasource konfigurace, entity access a naming strategie |
| T003-AC06 / T002-HB-01 | PARTIAL | `test_compiler_workers.py::test_ac06_real_javac_embedded_id_and_association_roles`; `test_build_aware.py::test_hb01_embedded_id_and_bidirectional_association_preserve_roles` — Java FIELD/PROPERTY access, EmbeddedId, AttributeOverride, owning/inverse association, derived paths, compiler-owned JPQL/native query, parameter/projection a named-query reference; JPA rules `annotation-source-v4` | Kotlin use-site/access, XML override priorita, inheritance attributes, dvě datasource se stejnou tabulkou, širší query grammar/dynamic builders a úplná schema matice |
| T003-AC08 | PARTIAL | `test_compiler_workers.py::test_ts_reexport_resolves_and_lockfile_change_marks_only_context_stale` | Multi-project references a kompletní BE–FE value flow |

Workspace cache invalidaci při publikaci další inspection bez změny zdrojů navíc
ověřuje rozšířený `test_workspace_preserves_repo_qualified_compiler_collections`.
Focused běh workspace/provider: **24 passed in 3.74 s**.

T003-AC02 je VERIFIED_IN_SCOPE v publikované JVM/Python matici. Nový
`test_graph_provider.py::test_feature_requires_and_persists_explicit_context_for_variants`
ověřuje, že feature prepare odmítne nejednoznačné module/profile varianty, uloží
explicitní scope/context a graph provider následně vrátí jen zvolenou compiler
vrstvu. Focused feature/provider/workspace běh: **49 passed in 6.13 s**.
`test_graph_provider.py::test_status_separates_current_source_graph_from_stale_compiler_context`
a rozšířený `test_workspace_preserves_repo_qualified_compiler_collections` navíc
ověřují fail-closed status/check pro single-root i repo-qualified workspace bez
spuštění workeru, buildu nebo projektu. Focused workspace/provider běh: **26 passed
in 1.81 s**.

Skutečný
`test_compiler_workers.py::CompilerWorkerTests::test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle`
navíc provádí celý inspect/refresh/query/impact/feature/report sled, dvě profilové
varianty a content změnu classpath. Focused worker/provider/workspace/feature/dataflow
běh: **68 passed in 20.07 s**. Rozšíření jazykových, buildových a framework variant
patří do S03–S10 a není součástí tohoto VERIFIED tvrzení.

Povinné mezery pro T003-S11 zůstávají viditelné zejména v T001-FA-14/15/24/73
a T002-HB-02. Řádky PARTIAL vyžadují rozšíření fixture/matice uvedené
v T003; zelený souhrnný běh jejich chybějící varianty nedokládá.

T003-S03-W01 AC01/AC03: `test_external_toolchain_two_real_jdks` ověřuje skutečný Maven/JDK21+22 export; `test_explicit_java_home_is_content_bound_and_used_by_build` ověřuje i omezený environment allowlist. Dvě JDK jsou povinná pro tuto fixture, nepřítomnost je SKIP, nikoli PASS. Detail běhu: [change note 10](changes/10_selectExternalToolchain.md).
| Work package | Acceptance | Version/scope | Test evidence |
|---|---|---|---|
| T003-S03-W02 | AC01–AC04 | gradle-source-sets-2, Gradle 8.13 Java SourceSetContainer, custom explicit scope | `tests/test_gradle_variants.py`: real Gradle main/test/generated/custom/unknown; invalid provenance rejects publication; ambiguous membership stays unknown; mandatory full suite 206 passed in 55.56 s, no skips |

T003-S03-W02 review P1 evidence: `test_selected_variant_snapshot_ignores_sibling_sources_and_configs_offline`
proves selected variant freshness across sibling edits/additions and resource changes,
while selected/shared config changes stale it without processes.
`test_forged_gradle_convention_preserves_existing_store` rejects custom or mismatched
conventional pairs before mutation; `test_conventional_pairs_and_legacy_manifest_remain_readable`
preserves the three exact conventions and absent-provenance legacy input.
Current full evidence is recorded in change note13; T003-S03 remains PARTIAL.

| Work package | Acceptance | Supported version and evidence | Actual run |
|---|---|---|---|
| T003-S03-W03 | AC01–AC04 | gradle-composite-1 / Gradle8.13; `tests/test_gradle_included.py` duplicate lib repos, stale jar substitution, exact resolved order, unique execution-bound producer realm, ambiguous ownership/no-mutation import; legacy manifests covered by existing build suite | rebased review-fix full suite 221 PASS, 0 SKIP; external roots UNBOUND/PARTIAL |

| Work package acceptance | Scope/version | Evidence | Actual run |
|---|---|---|---|
| T003-S09-W04-AC01–AC04 | Offline approval sidecar v1; optional additive index hash, graph/store v1/v2/v3 unchanged | `tests/test_methodology_conflicts.py` (11 cases, včetně změny/smazání SVG a nulových procesů při freshness kontrole), existing `test_fa21_approved_requirement_conflict_preserves_authority` | 203 passed in 39.44 s; `KGMAKER_REQUIRE_WORKERS=1`, existing baseline build outputs reused; no whole-S09 claim |

T003-S09-W04 integration against main `0c09028` (2026-10-26): focused feature/scanner/methodology **56 PASS**; full suite **229 PASS, 21 SKIP** without prepared compiler/build artifacts. Historical strict evidence above remains unchanged; see [change note 9](changes/9_bindMethodologyApproval.md).

Prepared packets revalidate documentation conflict coverage outside checkout too; three external HTML/approval/attachment mutation tests reject stale approval without mutating packet/index.

Final integration run after external-packet freshness fix: **232 PASS, 21 SKIP** (5.00 s); focused **56 PASS**. Strict attempt blocked by missing actual Maven fixture (14 setup errors), documented in change note9; no worker PASS is claimed for this environment.

After actual Maven fixture preparation, final strict integrated run **246 PASS, 7 SKIP** (84.81 s); both real compiler workers exercised. Remaining skips require Maven/Gradle executables or a second JDK; see change note9.


## T003-S09-W02 — diagnostika binárních XLS

Rozsah `xls-unsupported-1`, `feature-inventory-5`, Python 3.12, bez externího
parseru nebo runtime. [Change note 34](changes/34_diagnoseBinaryXls.md).

| ID | Stav | Přímá evidence | Běh |
|---|---|---|---|
| T003-S09-W02-AC01 | VERIFIED_IN_SCOPE | `test_binary_xls.py::test_real_biff2_fixture_is_unsupported_before_zip_parse_or_process` — BIFF2 fixture, .xls a přejmenované .xlsx; status/hash/file locator | focused 65 PASS |
| T003-S09-W02-AC02 | VERIFIED_IN_SCOPE | `test_packet_and_audit_preserve_hash_bound_gap_without_confirming_missing_data` — save/load a graph v1/v2/v3; stávající `test_workbooks.py` zachovává XLSX cell evidence | focused 65 PASS |
| T003-S09-W02-AC03 | VERIFIED_IN_SCOPE | malformed/compound-container/direct-extractor testy; UNKNOWN audit, nulová mutace store, scope a repo-qualified workspace gaps; oversized hash/freshness/cache regressions v `test_binary_xls.py` | finální focused 100 PASS |
| T003-S09-W02-AC04 | VERIFIED_IN_SCOPE | README, capability docs, tato tabulka, stavová matice a change note 34 vymezují přesný rozsah | S09/AC09 zůstávají PARTIAL |

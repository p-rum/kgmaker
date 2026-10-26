# T005–T044 dispatch report

Snapshot připraven pro větev chore/t004-configure-luna-agents a změnu docs/changes/14_configureLunaAgents.md. Task metadata byla převzata z jednotlivých zadání v PR #10. Stav zadání zůstává SPECIFICATION.

**Stav gate:** dokud PR #10 není v cílovém base, všech 40 tasků je BLOCKED na T004 společných kontraktech. Po merge PR #10 je T005 jediný task bez další implementační dependency a může být označen READY; T006–T044 zůstávají BLOCKED, dokud nejsou ověřené jejich explicitní upstream tasky a/nebo T003 work packages. READY zde znamená pouze splněný dependency gate pro koordinátorovo posouzení; neznamená spuštění agenta ani automatické povolení paralelní práce.

Profily nevytvářejí, nespouštějí ani nedokončují žádnou práci a neudržují živý stav běhů. Stav případných implementačních běhů se ověřuje v jejich samostatných session a reportech; přítomnost profilu není evidence, že agent běží.

## Dependency gates

| Task | Explicit dependencies | Dispatch |
|---|---|---|
| T005 | T004 společné kontrakty; bez dalšího implementačního předchůdce. | READY after PR #10 merged to main at `8cdc1843df9aba75908973d202a487630db1dcdc` |
| T006 | [T005](../../docs/tasks/T-005_add-view-model.md); `T003-S02` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T007 | [T005](../../docs/tasks/T-005_add-view-model.md). | BLOCKED until each dependency is verified |
| T008 | [T006](../../docs/tasks/T-006_select-service-contexts.md); [T007](../../docs/tasks/T-007_define-service-ownership.md). | BLOCKED until each dependency is verified |
| T009 | [T005](../../docs/tasks/T-005_add-view-model.md); [T006](../../docs/tasks/T-006_select-service-contexts.md); `T003-S07-W08` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T010 | [T008](../../docs/tasks/T-008_project-service-inventory.md); [T009](../../docs/tasks/T-009_propagate-view-evidence.md). | BLOCKED until each dependency is verified |
| T011 | [T008](../../docs/tasks/T-008_project-service-inventory.md); [T009](../../docs/tasks/T-009_propagate-view-evidence.md); `T003-S07-W06` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T012 | [T008](../../docs/tasks/T-008_project-service-inventory.md); [T009](../../docs/tasks/T-009_propagate-view-evidence.md); `T003-S07-W04` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T013 | [T010](../../docs/tasks/T-010_catalog-http-providers.md); [T011](../../docs/tasks/T-011_catalog-http-consumers.md); [T012](../../docs/tasks/T-012_catalog-kafka-interfaces.md). | BLOCKED until each dependency is verified |
| T014 | [T013](../../docs/tasks/T-013_attach-interface-contracts.md); `T003-S07-W07` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T015 | [T008](../../docs/tasks/T-008_project-service-inventory.md); [T009](../../docs/tasks/T-009_propagate-view-evidence.md); `T003-S06` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T016 | [T014](../../docs/tasks/T-014_bind-remote-interfaces.md); [T015](../../docs/tasks/T-015_project-data-resources.md). | BLOCKED until each dependency is verified |
| T017 | [T016](../../docs/tasks/T-016_aggregate-service-topology.md). | BLOCKED until each dependency is verified |
| T018 | [T009](../../docs/tasks/T-009_propagate-view-evidence.md); [T016](../../docs/tasks/T-016_aggregate-service-topology.md). | BLOCKED until each dependency is verified |
| T019 | [T010](../../docs/tasks/T-010_catalog-http-providers.md); [T011](../../docs/tasks/T-011_catalog-http-consumers.md); [T012](../../docs/tasks/T-012_catalog-kafka-interfaces.md); [T013](../../docs/tasks/T-013_attach-interface-contracts.md); [T017](../../docs/tasks/T-017_filter-topology-scope.md); [T018](../../docs/tasks/T-018_explain-view-elements.md). | BLOCKED until each dependency is verified |
| T020 | [T013](../../docs/tasks/T-013_attach-interface-contracts.md); [T019](../../docs/tasks/T-019_add-architecture-json-cli.md). | BLOCKED until each dependency is verified |
| T021 | [T017](../../docs/tasks/T-017_filter-topology-scope.md); [T019](../../docs/tasks/T-019_add-architecture-json-cli.md); `T003-S07-W09` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T022 | [T018](../../docs/tasks/T-018_explain-view-elements.md); [T021](../../docs/tasks/T-021_render-topology-mermaid.md). | BLOCKED until each dependency is verified |
| T023 | [T005](../../docs/tasks/T-005_add-view-model.md); [T009](../../docs/tasks/T-009_propagate-view-evidence.md). | BLOCKED until each dependency is verified |
| T024 | [T008](../../docs/tasks/T-008_project-service-inventory.md); [T023](../../docs/tasks/T-023_define-business-process-model.md). | BLOCKED until each dependency is verified |
| T025 | [T023](../../docs/tasks/T-023_define-business-process-model.md); [T024](../../docs/tasks/T-024_discover-process-triggers.md); `T003-S04` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T026 | [T025](../../docs/tasks/T-025_build-local-process-path.md). | BLOCKED until each dependency is verified |
| T027 | [T014](../../docs/tasks/T-014_bind-remote-interfaces.md); [T025](../../docs/tasks/T-025_build-local-process-path.md). | BLOCKED until each dependency is verified |
| T028 | [T012](../../docs/tasks/T-012_catalog-kafka-interfaces.md); [T014](../../docs/tasks/T-014_bind-remote-interfaces.md); [T025](../../docs/tasks/T-025_build-local-process-path.md). | BLOCKED until each dependency is verified |
| T029 | [T025](../../docs/tasks/T-025_build-local-process-path.md); [T028](../../docs/tasks/T-028_cross-async-process-boundary.md); `T003-S07-W05` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí). | BLOCKED until each dependency is verified |
| T030 | [T024](../../docs/tasks/T-024_discover-process-triggers.md); [T026](../../docs/tasks/T-026_collapse-business-steps.md). | BLOCKED until each dependency is verified |
| T031 | [T023](../../docs/tasks/T-023_define-business-process-model.md); [T030](../../docs/tasks/T-030_prepare-process-label-packet.md). | BLOCKED until each dependency is verified |
| T032 | [T031](../../docs/tasks/T-031_validate-process-annotations.md). | BLOCKED until each dependency is verified |
| T033 | [T024](../../docs/tasks/T-024_discover-process-triggers.md); [T032](../../docs/tasks/T-032_persist-process-review.md). | BLOCKED until each dependency is verified |
| T034 | [T027](../../docs/tasks/T-027_cross-http-process-boundary.md); [T028](../../docs/tasks/T-028_cross-async-process-boundary.md); [T029](../../docs/tasks/T-029_project-process-failures.md); [T030](../../docs/tasks/T-030_prepare-process-label-packet.md); [T031](../../docs/tasks/T-031_validate-process-annotations.md); [T032](../../docs/tasks/T-032_persist-process-review.md); [T033](../../docs/tasks/T-033_catalog-business-processes.md). | BLOCKED until each dependency is verified |
| T035 | [T026](../../docs/tasks/T-026_collapse-business-steps.md); [T027](../../docs/tasks/T-027_cross-http-process-boundary.md); [T028](../../docs/tasks/T-028_cross-async-process-boundary.md); [T029](../../docs/tasks/T-029_project-process-failures.md); [T034](../../docs/tasks/T-034_add-process-cli.md). | BLOCKED until each dependency is verified |
| T036 | [T033](../../docs/tasks/T-033_catalog-business-processes.md); [T035](../../docs/tasks/T-035_render-business-process-mermaid.md). | BLOCKED until each dependency is verified |
| T037 | [T018](../../docs/tasks/T-018_explain-view-elements.md); [T032](../../docs/tasks/T-032_persist-process-review.md); [T033](../../docs/tasks/T-033_catalog-business-processes.md). | BLOCKED until each dependency is verified |
| T038 | [T022](../../docs/tasks/T-022_render-topology-markdown.md); [T036](../../docs/tasks/T-036_render-business-process-report.md); [T037](../../docs/tasks/T-037_invalidate-derived-views.md). | BLOCKED until each dependency is verified |
| T039 | [T037](../../docs/tasks/T-037_invalidate-derived-views.md); [T038](../../docs/tasks/T-038_publish-view-artifacts-atomically.md). | BLOCKED until each dependency is verified |
| T040 | [T034](../../docs/tasks/T-034_add-process-cli.md); [T036](../../docs/tasks/T-036_render-business-process-report.md). | BLOCKED until each dependency is verified |
| T041 | [T020](../../docs/tasks/T-020_render-interface-markdown.md); [T021](../../docs/tasks/T-021_render-topology-mermaid.md); [T022](../../docs/tasks/T-022_render-topology-markdown.md); [T038](../../docs/tasks/T-038_publish-view-artifacts-atomically.md). | BLOCKED until each dependency is verified |
| T042 | [T035](../../docs/tasks/T-035_render-business-process-mermaid.md); [T036](../../docs/tasks/T-036_render-business-process-report.md); [T038](../../docs/tasks/T-038_publish-view-artifacts-atomically.md); [T040](../../docs/tasks/T-040_add-agent-process-instructions.md). | BLOCKED until each dependency is verified |
| T043 | [T017](../../docs/tasks/T-017_filter-topology-scope.md); [T025](../../docs/tasks/T-025_build-local-process-path.md); [T037](../../docs/tasks/T-037_invalidate-derived-views.md). | BLOCKED until each dependency is verified |
| T044 | [T039](../../docs/tasks/T-039_diff-architecture-and-processes.md); [T040](../../docs/tasks/T-040_add-agent-process-instructions.md); [T041](../../docs/tasks/T-041_verify-architecture-acceptance.md); [T042](../../docs/tasks/T-042_verify-process-acceptance.md); [T043](../../docs/tasks/T-043_bound-view-performance.md). | BLOCKED until each dependency is verified |

Všechny profily vyžadují vlastní task branch z aktuálního base, konkrétní AC/test evidence, change note, cílené a kompletní pytest běhy, git diff --check, samostatný PR a žádný auto-merge. External T003 dependencies se ověřují podle skutečného kontraktu a acceptance v cílovém base; existence souboru či profilu nestačí.

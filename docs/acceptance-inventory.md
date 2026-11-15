# Inventář acceptance T001 a T002

## T003-S13-W01 — synchronní JDK21/POSIX runtime capture, 2026-11-15

Dodání `MERGED` ([PR101](https://github.com/p-rum/kgmaker/pull/101),
commit `d2507ef465c9b4844830520de68629a3b577c0d2`);
ověření celého milníku `PARTIAL`. [Kontrakt/CLI/limity](runtime-trace.md),
[per-step evidence a historie](changes/122_runtimeTraceProducer.md).
Integrace PR102 zachovává runtime source; 88 runtime testů je součástí společného
běhu 205 PASS / 0 SKIP ([change120](changes/120_namedQueryContainers.md)).

| Acceptance | Ověření | Důkaz a limit |
|---|---|---|
| T003-S13-W01-AC01 | VERIFIED_IN_SCOPE (JDK21/POSIX) | `tests/test_runtime_trace_producer.py::test_actual_jdk21_application_observes_all_four_kinds_and_no_values` + `test_actual_jdk21_capture_is_opt_in_and_records_only_executed_branch`: skutečný javac, JVM compiler worker, aplikace a source-bound IDs; povinné identity, žádné raw credentials. `tests/test_graph_provider.py::test_scan_hook_and_feature_retain_compiler_layer_without_processes` a import pod zákazem Popen. Žádný automatický Spring capture ani deployment proof. |
| T003-S13-W01-AC02 | VERIFIED_IN_SCOPE | `tests/test_build_aware.py::BuildAwareContractsTest::test_runtime_import_is_bound_to_context_and_rejects_stale_source`: původní v1. V2 pozitivní roundtrip a `test_v2_import_requires_complete_bound_identity_before_store_mutation`, `test_v2_import_rejects_empty_forged_and_unknown_evidence`; v3 odmítnuto, graph/store beze změny schématu. |
| T003-S13-W01-AC03 | VERIFIED_IN_SCOPE (bounded) | `test_invalid_or_incomplete_facts_never_publish`, `test_capture_status_is_preserved_without_availability_claim`, `test_preflight_rejects_before_spawn_and_keeps_artifact`, `test_postflight_detects_mutation_without_publishing`, `test_process_tree_cleanup_preserves_last_artifact`, `test_keyboard_interrupt_cleans_up_process_group`; běžní potomci stejné POSIX skupiny, žádná izolace odpojených daemonů. |
| T003-S13-W01-AC04 | PARTIAL | Nové CLI/capability dokumenty a oddělené kroky v change122 odpovídají skutečným testům. Full suite dle aktuálního pokynu NOT_RUN, GH CI NOT_RUN; celé S13/T003 ani Spring/Windows/RTA/value-flow/async/reflection nejsou ověřeny. |

## T051 — projektové workflows, 2026-11-15

Baseline `6790b0e0a930089924c61c3f8a6b3aef1d44121c`; dodání MERGED
([PR #99](https://github.com/p-rum/kgmaker/pull/99), merge `6eb755ec1d4e777abe8d34dea7bee9477c90692f`, závislost #98 MERGED). [Zadání](tasks/51_connectProjectWorkflows.md),
[change118](changes/118_connectProjectWorkflows.md).

| Acceptance | Ověření | Důkaz a limit |
|---|---|---|
| T051-AC01 | VERIFIED_IN_SCOPE | tests/test_workflow_profiles.py: strict config, duplicate JSON, symlink, null mutation, commands data-only |
| T051-AC02 | VERIFIED_IN_SCOPE | Legacy ID/regrese, v3 immutable snapshot, konfigurace smazána bez změny tasku, role packet |
| T051-AC03 | VERIFIED_IN_SCOPE | Persistence gates, required label/command, skipped/unknown/failed, stale binding, retry, review major; lokálně deklarované artefakty |
| T051-AC04 | PARTIAL | Init parity/preservation a CLI handoffs PASS; wheel mimo checkout PASS; živý hostitel NOT_RUN |
| T051-AC05 | PARTIAL | 103 testů PASS a dokumentace po krocích; GH CI a review publikovaného HEAD NOT_RUN |


## T050 — cílové Agent Skills, 2026-11-15

Baseline `193c89b4d461047fd3330fd74892c5830ba8ac81`,
[T050 revize 1](tasks/50_addTargetProjectSkills.md),
[change117](changes/117_addTargetProjectSkills.md). Dodání S01/S02 MERGED ([PR #98](https://github.com/p-rum/kgmaker/pull/98),
main `31a69bcf5b72c5f1f3be4ed699cc6b5672bcdcde`);
ověření uvedené níže je lokální a neprokazuje automatickou discovery hostitelů.

| Acceptance | Ověření | Aktuální důkaz |
|---|---|---|
| T050-AC01 | VERIFIED_IN_SCOPE | tests/test_skills.py, všechny 8 resources, parity + references; čistý wheel init mimo checkout PASS |
| T050-AC02 | VERIFIED_IN_SCOPE | Opakovaný init bytes/mtime, úpravy skills/references/cizích instrukcí, explicitní force a cizí skill PASS |
| T050-AC03 | VERIFIED_IN_SCOPE | 12 symlink scénářů + 4 file/directory kolize s nulovou mutací; scan neinstaluje skilly PASS |
| T050-AC04 | PARTIAL | 5 formátových validací PASS; audit/testgen JSON ukázky prošly runtime validátory. Živý model/hostitel NOT_RUN |
| T050-AC05 | PARTIAL | Záznam obou kroků, README, capability/CLI návod, matice a registr aktualizované; nezávislé review a GH CI NOT_RUN |

## Aktuální audit dodání — 2026-11-14

T048-S01 / T048-AC01: [119 atomických řádků](production-analysis-progress.md)
odděluje delivery, verification, evidence SHA, zdroje/testy, PR, omezení a další
krok; [change111](changes/111_reconcileDeliveryStatus.md) uvádí kontroly.
Aktualizace 2026-11-15: T003/T004 mají 63 položek se sloučenou prací a 37 bez ní; [post-merge evidence](changes/119_reconcileJpqlDelivery.md). T046-S01 až S06 jsou
MERGED,
T047 PLANNED se sdílenými upstream vlastníky. Úplná produkční acceptance všech variant zůstává NOT_RUN; dostupný lokální pytest full merged main je doložen v change119 a není jejím ekvivalentem.
Historické VERIFIED_IN_SCOPE/CI_PENDING/review pending řádky níže zachovávají
původní SHA a výsledky. Již proběhlý merge není čekající gate: T020 PR87,
T014/16/17/18/19 PR80–84, T030/31/32/33 PR75/77/78/79, W05 PR71,
W07 PR76 a W08 PR64 jsou MERGED. Nepřenáší se tím PASS na nový kód.
T045 revize2 dovoluje merge bez GH CI při splnění ostatních povinných kontrol;
staré billing-only blokace níže jsou historické, konkrétní chyba zůstává blokující.

T048-S02 / T046-S01, aktualizováno 2026-11-11: head
`3083215800515e81425d4824c7db5cef0fe1ef10` byl po exact-pair review sloučen
jako `25176ad8f63e3666a051dab9c9216f50adfd6ed3`. Cíleně 83 passed a 7
subtests; full 1602 passed, 1055 skipped a 29 subtests; [záznam 56](changes/56_addDeliveryReferences.md).
Stav MERGED, Python VERIFIED_IN_SCOPE; nepřipravené toolchainy NOT_RUN/SKIP.

T048-S02 / T046-S02, aktualizováno 2026-11-11: integrace merge commitu
S01 `25176ad8f63e3666a051dab9c9216f50adfd6ed3` — po opravách review cíleně
91 passed a 23 subtests; full 1610 passed, 1055 skipped a 45 subtests;
[záznam](changes/57_addArtifactTemplates.md).
Head `351a661641b8a8f619b389c20a7cf32641c23f5a` byl po exact-pair review
sloučen jako `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10`. Stav MERGED;
Python VERIFIED_IN_SCOPE, nepřipravené toolchainy NOT_RUN/SKIP.

T048-S02 / T046-S03, aktualizováno 2026-11-11: integrace sloučeného S02 —
106 passed, 37 subtests; full 1625 passed, 1055 skipped a 59 subtests;
[záznam](changes/58_addExistingFunctionTests.md). Python VERIFIED_IN_SCOPE;
head `1b7ce435c53a2dca0168997549f0dd587b331d6c` byl po exact-pair
review sloučen jako `f000e3d5eb898031af15785bd1b80427c149ec4c`. Stav MERGED;
širší toolchain NOT_RUN/SKIP.

T048-S02 / T046-S04, aktualizováno 2026-11-12: integrace sloučeného S03 —
111 passed, 45 subtests; full 1630 passed, 1055 skipped a 67 subtests;
[záznam](changes/59_verifySyntheticTestData.md). Python VERIFIED_IN_SCOPE;
head `301bfb9f514c45176f119533303a5c1b1a435d05` byl po exact-pair
review sloučen jako `306cb83105751a7848b9efb4ba8c801e551353df`. Stav MERGED;
širší toolchain NOT_RUN/SKIP.

T048-S02 / T046-S05, aktualizováno 2026-11-12: integrace sloučeného S04 —
114 passed, 49 subtests; full 1633 passed, 1055 skipped a 71 subtests;
[záznam](changes/60_enforceOptionalLocalApprovals.md). Python VERIFIED_IN_SCOPE;
head `bdedb6cc0e4f48a4e19357458a375fe3e04a72d9`
byl po opravě dokumentačního nálezu a exact-pair re-review sloučen jako
`6dffe5e39fb847e5552f38e67b957e4b51b20bed`. Stav MERGED; širší
toolchain NOT_RUN/SKIP.

T048-S02 / T046-S06, aktualizováno 2026-11-12: integrace sloučeného S05 —
309 passed, 10 skipped a 67 subtests; full 1635 passed, 1055 skipped a 76
subtests; [záznam](changes/61_integrateDeliveryWorkflow.md). Python
VERIFIED_IN_SCOPE; head `65e6a3bbe7246ef7d3caac4d0f956cd6d3f81de5` byl po
exact-pair review sloučen jako `9bcf91db1d1349241f7e1f7114f74c0331c25802`.
Stav MERGED; širší toolchain NOT_RUN/SKIP. [Post-merge
srovnání](changes/113_reconcileT046DeliverySummary.md).

## T003-S05-W04 — Spring proxy a async semantics — MERGED / VERIFIED_IN_SCOPE

PR [#95](https://github.com/p-rum/kgmaker/pull/95), první přesně publikovaný
implementační head `d310122e757e881875eb4d498c968af4fe91434d`. Review původního
headu `cbe4a0e42ed97a51ac1c11c980f91d4c5b92fb4d` našlo dva P1; FIELD receiver
provenance a synchronní Async self-call jsou opravené v implementačním headu
`276886c55f16cf09746970342cb2b80ab814745d`.
CI původního i opravného headu je administrativní NOT_RUN (`steps=null`, bez logů).
Druhé review `PRR_kwDOUyD9Wc8AAAABYBNa9Q` na `0de66dde234d7725d06073ed81095c3abca18556`
našlo neprokázanou injection obyčejného pole a falešný same-owner self-call; obě
opravy prošly čistým exact-pair review na finálním headu
`44af09d36b69589fee882d017d22f07bdc2e3216` a PR byl sloučen jako
`39eb46ba283e526d9748e80e2572f28b4f4348ed`.

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S05-W04-AC01 | LOCAL_VERIFIED_IN_SCOPE | `tests/test_spring_proxy_async.py::test_jdk_proxy_async_event_and_self_invocation_are_bounded`, `test_cglib_path_requires_interceptable_concrete_method`, `test_process_stops_at_async_boundary_without_claiming_execution` a `test_process_expands_async_self_invocation_synchronously`: advice jen přes bounded `may_*` proxy path, self-call synchronní bypass, pouze proxied Async continuation oddělená a execution NOT_OBSERVED |
| T003-S05-W04-AC02 | LOCAL_VERIFIED_IN_SCOPE | `SPRING_RULE_VERSION=annotation-source-v9-proxy-provenance`; `test_legacy_spring_rules_remain_readable_but_require_reinspection` zahrnuje v8, graph/store schema v1/v2/v3 zůstává beze změny a framework výsledek prochází round-trip validací |
| T003-S05-W04-AC03 | LOCAL_VERIFIED_IN_SCOPE | `test_aspectj_declaration_without_weaving_proof_stays_unknown`, `test_ambiguous_interface_injection_never_creates_stronger_proxy_evidence`, `test_local_or_non_injected_field_never_reuses_injected_proxy_evidence`, `test_same_owner_parameter_receiver_is_not_self_invocation` a incompatible JDK/CGLIB receiver assertions nevytvářejí `may_apply_advice`; lokalizují UNKNOWN důvod |
| T003-S05-W04-AC04 | LOCAL_VERIFIED_IN_SCOPE / TOOLCHAIN_SKIP | `test_actual_javac_proxy_async_event_fixture` má JDK/CGLIB, Async a EventListener parametry, ale bez připraveného JVM workeru je lokálně explicitní SKIP, nikoli PASS; [change114](changes/114_modelSpringProxyAsyncSemantics.md), README a compiler-inspection uvádějí tuto hranici; T003-S05 zůstává PARTIAL |

## T003-S06-W05 — rozšířená JPQL/HQL gramatika — MERGED / LOCAL_VERIFIED_IN_SCOPE

PR [#97](https://github.com/p-rum/kgmaker/pull/97) je MERGED jako `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`.
Aktuální post-merge full a korekci base ověření dokládá [change119](changes/119_reconcileJpqlDelivery.md).
Historický první implementační head
`1f6f0a9ee63d77d5abb853dd6db057d5b0d15da9`, tree
`fbc521331a7a68a94768d636f52552917008bfba`; historický publikovaný stav. Review opravy z 2026-11-15 byly po výslovném souhlasu uživatele publikovány
v checkpointu `7369e2d`; produkční parser beze změn vůči `1dcf9ff` má
code review bez nálezu. Opravené test/build vstupy mají samostatný aktuální receipt.
Po uživatelem vyžádané opravě fixture a toolchain prostředí má aktuální
full receipt nulový FAIL/ERROR; původní branch evidence níže je odlišná od post-merge main receipt v change119.

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S06-W05-AC01 | LOCAL_VERIFIED_IN_SCOPE | `tests/test_jpql_hql_grammar.py::test_bounded_jpql_hql_joins_subqueries_dml_and_constructor_projection`: exact compiler-owned root/join/subquery reads, bulk update/delete, DTO constructor a clause-specific path edges; `partialLateral` je PARTIAL s query locatorem |
| T003-S06-W05-AC02 | LOCAL_VERIFIED_IN_SCOPE | `JPA_RULE_VERSION=annotation-source-v8-jpql-hql-grammar`; `test_legacy_jpa_rules_remain_readable_but_require_reinspection` pokrývá v6/v7, graph/store v1/v2/v3 zůstává beze změny a stávající realm/schema suite prochází |
| T003-S06-W05-AC03 | LOCAL_VERIFIED_IN_SCOPE | `test_partial_invalid_and_ambiguous_queries_never_publish_stronger_evidence` plus bounded invalid-clause regressions: malformed/incomplete query, unknown path, duplicate entity, undeclared alias a trailing token nevytvářejí silnější evidence; vstupní graph se nemutuje |
| T003-S06-W05-AC04 | PARTIAL | Finální corpus 42 PASS /0 SKIP včetně actual-javac; T015 actual 1 PASS; širší JPA 130 PASS /32 SKIP. Historický branch full na ff31433: 2264 PASS /481 SKIP /0 FAIL /0 ERROR. Předchozí šest FAIL/41 ERROR odstraněno opravou integračních fixture a přípravou pinned toolchainů. Aktuální merged-main full na 2bebab00: 2318 PASS /481 SKIP /0 FAIL /0 ERROR; viz change119 a korekce v PR97. [Change116](changes/116_parseExtendedJpqlHql.md); T003-S06 zůstává PARTIAL |

## Historická acceptance podle uvedených checkpointů


## T003-S06-W01 — Kotlin JPA use-site a access

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S06-W01-AC01 | VERIFIED_IN_SCOPE | `tests/test_k2_backend.py::test_k2_jpa_use_site_access_and_ambiguity_are_compiler_attributed`: actual K2 `@field:EmbeddedId`, `@get:Id`, explicit PROPERTY and implicit FIELD, actual dual-site ambiguity, mismatched explicit FIELD, aliased canonical-package/subpackage namespace negatives, nested `@AttributeOverride`, class literal, and embeddable access across unique FIELD, explicit PROPERTY and mixed containers |
| T003-S06-W01-AC02 | VERIFIED_IN_SCOPE | Additive annotation metadata reuses graph schema v3, existing `orm_attribute`/`orm_embeddable` IDs and JPA rules `annotation-source-v4`; existing Java JPA fixture remains unchanged |
| T003-S06-W01-AC03 | VERIFIED_IN_SCOPE | Same K2 fixture proves unknown/mismatched placement creates no persistent attribute; unresolved explicit `@Table`/`@Column` does not emit physical defaults even with matching schema; unresolved `@Access` and unproven/mixed embeddable inheritance remain UNKNOWN; `tests/test_k2_backend.py::test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph` covers strict failure without replacing the last graph |
| T003-S06-W01-AC04 | VERIFIED_IN_SCOPE | `docs/production-analysis-progress.md`, README, `docs/compiler-inspection.md`, this matrix, and [change note 43](changes/43_kotlinJpaUseSiteAccess.md); T003-S06 remains PARTIAL |
## T003-S08-W03 — bounded callbacks — LOCAL_VERIFIED_IN_SCOPE / CI_PENDING

| ID | Stav | Evidence |
|---|---|---|
| T003-S08-W03-AC01 | LOCAL_VERIFIED_IN_SCOPE | Actual `test_typescript_callbacks.py`: nested barrel generic API, overloads, named/inline binding, mutable/union/any distinctions |
| T003-S08-W03-AC02 | LOCAL_VERIFIED_IN_SCOPE | Existing protocol1/schema model reused; v3 candidate roundtrip/offline navigation, W01/provider34PASS, canonical owner/repo variants |
| T003-S08-W03-AC03 | LOCAL_VERIFIED_IN_SCOPE | Candidate-only open-world dispatch and union bindings, explicit local limit PARTIAL, corrupted candidate preserves store |
| T003-S08-W03-AC04 | LOCAL_VERIFIED_IN_SCOPE / CI_PENDING | [Note53](changes/53_resolveBoundedTypeScriptCallbacks.md) and [guide](typescript-callbacks.md) uvádějí actual15PASS/full582PASS10SKIP, overload navigation PARTIAL a pending CI billing |


## T003-S06-W02 — zděděné persistence atributy

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S06-W02-AC01 | VERIFIED_IN_SCOPE | K2 and Javac fixtures prove chain ownership, FIELD/PROPERTY IDs, overrides, and inheritance table selection; `CompilerWorkerTests.test_repository_generic_uses_exact_entity_owner_for_same_simple_names` proves derived and explicit JPQL entity/return bindings retain exact owners and do not guess missing or generic return types |
| T003-S06-W02-AC02 | VERIFIED_IN_SCOPE | Additive `orm_attribute` metadata and `inherits_attribute` reuse graph schema v3; `test_existing_graph_loader_is_unchanged` accepts store schemas v1/v2/v3; no migration is needed |
| T003-S06-W02-AC03 | VERIFIED_IN_SCOPE | K2 fixture rejects a foreign same-simple-name base and unresolved override without fallback; actual Javac repository regression leaves foreign derived predicates, ambiguous JPQL, missing indexed qualified returns, and generic `T` returns unresolved, while descriptor-proven return types bind only to exact owners; W01 strict-refresh fixture proves last-valid graph preservation |
| T003-S06-W02-AC04 | VERIFIED_IN_SCOPE | README, compiler capability documentation, this matrix and [change note49](changes/49_projectJpaInheritedAttributes.md) document exact K2/Javac fixtures and partial boundaries; T003-S06 remains PARTIAL |

## T003-S06-W03 — ORM XML overrides

| ID | Stav | Přímá evidence |
|---|---|---|
| T003-S06-W03-AC01 | VERIFIED_IN_SCOPE | `tests/test_orm_xml_overrides.py`: actual Javac entity fixture proves selected persistence-unit mapping-file order, XML table/column precedence, XML path/SHA/persistence-unit/order evidence, annotation fallback for untouched partial mappings, and owner-isolated shared mapped-superclass columns |
| T003-S06-W03-AC02 | VERIFIED_IN_SCOPE | Same fixture proves standard nested `xml-mapping-metadata-complete` and `persistence-unit-defaults/access`, annotation suppression, XML-only field mapping, mapped-superclass inherited projection and `exclude-unlisted-classes`; XML freshness replay binds selected paths, content and target identities |
| T003-S06-W03-AC03 | VERIFIED_IN_SCOPE | Same fixture covers invalid class reference with strict last-valid-store preservation, namespace reset, unsupported encoding, bounded input, UTF-8/UTF-16 DTD/entity rejection, unsupported mapping constructs and offline stale replay for changed/appeared/deleted/retargeted inputs; unsupported targets remain UNKNOWN without annotation physical fallback |
| T003-S06-W03-AC04 | VERIFIED_IN_SCOPE | README, compiler capability documentation, this matrix and [change note65](changes/65_ormXmlOverrides.md) state source precedence, provenance and unsupported boundaries; graph/store schema v3 is unchanged and T003-S06 remains PARTIAL |
## T003-S08-W02 — selected config freshness — LOCAL_VERIFIED_IN_SCOPE / CI_PENDING

| ID | Stav | Evidence |
|---|---|---|
| T003-S08-W02-AC01 | LOCAL_VERIFIED_IN_SCOPE | `test_tsconfig_freshness.py`: actual effective extends/paths/exclude, selected A/B freshness, positive/negative/discovery/lockfile changes |
| T003-S08-W02-AC02 | LOCAL_VERIFIED_IN_SCOPE | Graph v1/v2/v3 capture roundtrip, conservative legacy fallback a stable selector replacement; protocol1 |
| T003-S08-W02-AC03 | LOCAL_VERIFIED_IN_SCOPE | Mixed preflight/analysis, malformed/future capture před IO, unavailable helper před procesem, hash-bound helper a zachování store |
| T003-S08-W02-AC04 | LOCAL_VERIFIED_IN_SCOPE / CI_PENDING | [Note45](changes/45_scopeTypeScriptConfigFreshness.md) a [freshness guide](typescript-freshness.md) uvádějí final70PASS focus a567PASS/10SKIP full; CI billing/quota stále blokuje merge acceptance |


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

Další W01 integration regrese: `test_new_alias_dependency_after_preflight_cannot_replace_last_graph`
odmítá změnu úplného compiler input setu mezi fázemi bez store mutace;
`test_legacy_typescript_selection_is_replaced_without_duplicate_contexts`
ověřuje skutečné worker snapshoty pro původní klíč, chybějící klíč a dočasný
K2-era TS digest. W02 config-scoped freshness má samostatný stav výše; W03
callback/generic rozsah zůstává samostatný nedokončený úkol.

## T003-S11-W03 — Windows user-space VERIFIED_IN_SCOPE

| Kritérium | Stav | Evidence |
|---|---|---|
| T003-S11-W03-AC01 | VERIFIED_IN_SCOPE_WINDOWS | Skutečný restricted-user core/Java/K1 Kotlin/TS installed wheel smoke; Windows Server2025/Python3.12.10/JDK21.0.6/Kotlin2.1.10/Node24.19.0/TS5.7.3; paths s mezerami |
| T003-S11-W03-AC02 | VERIFIED_IN_SCOPE_WINDOWS | Protocol1 a graph/store v1/v2/v3 beze změny; installed scan/save/load a T005 legacy loader/model sada prošly také na Windows |
| T003-S11-W03-AC03 | VERIFIED_IN_SCOPE_WINDOWS | Source-only/no-process, missing/ambiguous distribution a JRE/JDK17 negatives; timeout/cancel inherited pipes, thread/stream cleanup a zachování posledního grafu; Windows BUILD_EXECUTE je explicitní unsupported před procesem/zápisem |
| T003-S11-W03-AC04 | VERIFIED_IN_SCOPE | [Note40](changes/40_supportWindowsUserInstall.md), [Windows guide](windows-install.md), skutečný [run40351407076/job121672139333](https://github.com/p-rum/kgmaker/actions/runs/40351407076/job/121672139333): 43 PASS / 2 SKIP, 50.23s; K2 Windows a celý T003-S11 nejsou dokončené |

Evidence platí pro `d311231ed4e199ee0c19d9d5037ccfcdcdce199b`; následný metadata
commit vyžaduje vlastní checks/review před merge. Dva SKIP: POSIX-only setup fault
test a nepřipravený K2 worker. Povinné deklarované Windows workery nebyly skipped.

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

## T007 — explicitní vlastnictví služeb

| Acceptance | Stav | Přímý test | Výsledek |
|---|---|---|---|
| T007-AC01 dvě explicitní služby, shared library bez vlastníka | PASS | `tests/test_t007_define_service_ownership.py::test_ac01_two_declared_services_and_shared_library_is_unassigned` | finální cílená a regresní sada 45 PASS |
| T007-AC02 překryv roots/module mapping | PASS | `tests/test_t007_define_service_ownership.py::test_ac02_overlapping_roots_and_module_mapping_remain_ambiguous` | finální cílená a regresní sada 45 PASS |
| T007-AC03 legacy workspace a service IDs | PASS | `tests/test_t007_define_service_ownership.py::test_ac03_legacy_manifest_without_ownership_preserves_service_identity` | finální cílená a regresní sada 45 PASS |
| T007-AC04 invalidní manifest bez mutace | PASS | `tests/test_t007_define_service_ownership.py::test_ac04_invalid_ownership_is_rejected_without_manifest_mutation`; duplicate identity regression | finální cílená a regresní sada 45 PASS |
| T007-AC05 kontext a nepovýšení evidence | PASS | `tests/test_t007_define_service_ownership.py::test_ac05_resolution_preserves_selected_context_and_never_guesses`; foreign repo context and qualified path regressions | finální cílená a regresní sada 45 PASS |
| T007-AC06 dokumentace a change note | PASS | README, architecture, status a tento inventář; `docs/changes/33_defineServiceOwnership.md` | `kgmaker check` PASS; `git diff --check` PASS |

## T008 — inventář služeb a externích systémů

| Acceptance | Stav | Přímý test | Výsledek |
|---|---|---|---|
| T008-AC01 production inventory uses explicit owners, excludes fixture/shared library and accidental beans | PASS | `test_ac01_inventory_includes_declared_production_service_not_fixture_or_random_beans`; `test_unknown_scope_does_not_enter_production_inventory` | T008 focused suite |
| T008-AC02 missing external checkout preserves declaration without internal endpoints | PASS | `test_ac02_missing_external_checkout_keeps_declared_system_unknown_without_endpoints` | external implementation and endpoints remain UNKNOWN |
| T008-AC03 display-label changes preserve stable service ID | PASS | `test_ac03_stable_service_identity_is_independent_of_display_label` | T008 focused suite |
| T008-AC04 invalid snapshot leaves inputs and checkout unchanged | PASS | `test_ac04_invalid_snapshot_fails_without_mutating_workspace_or_graph` | compares manifest, source file, workspace and graph bytes/state |
| T008-AC05 scope, selected context, evidence and unresolved boundaries are preserved | PASS | `test_ac05_context_and_provenance_are_preserved_and_not_upgraded`; `test_source_only_context_remains_partial_and_reports_unknown_module_coverage`; `test_actual_workspace_source_only_snapshot_projects_declared_root_without_module`; `test_actual_source_only_snapshot_separates_production_and_test_within_repo`; `test_ambiguous_compiler_variants_remain_unknown_until_explicitly_selected`; `test_workspace_alias_requalifies_default_local_compiler_context` | actual snapshot root ownership and same-repository scope separation, T006 selection, SOURCE_ONLY partial status and repo alias behavior retained |
| T008-AC06 implementation, tests, documentation and Czech change note | PASS | README, architecture, this inventory and `docs/changes/41_projectServiceInventory.md` | focused and integrated results are recorded in the change note |

## T009 — propagace evidence a coverage

| Acceptance | Stav | Přímý test / kontrakt |
|---|---|---|
| T009-AC01 evidence kind is not upgraded; legacy defaults remain unresolved/unknown | PASS | `tests/test_t009_propagate_view_evidence.py::test_ac01_syntax_candidate_stays_syntax_candidate_and_legacy_defaults_do_not_upgrade`; `tests/test_t005_add_view_model.py::test_t009_additive_fields_validate_against_public_view_schema` |
| T009-AC02 mixed support, contradiction and unknown refs remain visible; incomplete work stays PARTIAL | PASS | `test_ac02_mixed_evidence_retains_support_conflict_unknown_refs_and_diagnostics`; `test_explicit_unknown_polarity_cannot_be_relabelled_by_view_or_aggregation` |
| T009-AC03 empty unanalysed input is UNKNOWN with zero counts | PASS | `tests/test_t009_propagate_view_evidence.py::test_ac03_empty_unanalyzed_input_is_unknown_with_zero_counts` |
| T009-AC04 invalid inputs leave caller data unchanged | PASS | `test_ac04_invalid_claim_does_not_mutate_inputs`; `test_ac04_malformed_scope_inputs_return_structured_errors_without_mutation` |
| T009-AC05 selected scope/context remains isolated and unsupported polarity UNKNOWN | PASS | `test_ac05_scope_context_exclusions_and_invalid_polarity_stay_unknown`; T008 production/test workspace regressions |
| T009-AC06 implementation, test results, docs and bounded upstream limitation are recorded | PARTIAL | README, `docs/architecture.md`, this matrix, status matrix, and [change note 64](changes/64_propagateViewEvidence.md); current targeted72 PASS; final full466 PASS/109 prerequisite SKIP after all independent review guards; earlier455/109 is intermediate |

## T006 — výběr kontextů pro více služeb

| Acceptance | Stav | Přímý test | Výsledek |
|---|---|---|---|
| T006-AC01 dvě služby a různé čerstvé varianty | PASS | `test_two_services_select_distinct_contexts_and_profiles_without_mixing`; `test_t006_selects_nonempty_workspace_contexts_and_real_release_mapping` | cílený běh nad skutečným workspace/compiler snapshotem |
| T006-AC02 nejednoznačný/stale výběr s volbami nebo příkazem | PASS | `test_missing_variant_selection_returns_choices_and_does_not_mutate_graph`; `test_stale_classpath_returns_diagnostic_and_next_command_without_worker`; `test_t006_release_mapping_becomes_stale_when_reported_output_changes` | cílený běh |
| T006-AC03 bez procesu a mutace grafu/store | PASS | `test_selection_reads_current_context_without_process_or_store_mutation` | cílený běh; subprocess zakázán |
| T006-AC04 chybný výběr beze změny vstupu | PASS | `test_invalid_scope_and_module_mismatch_fail_closed_without_input_mutation`; `test_missing_variant_selection_returns_choices_and_does_not_mutate_graph` | cílený běh |
| T006-AC05 evidence, scope a SOURCE_ONLY hranice | PASS | `test_source_only_requires_declared_repo_coverage_and_stays_partial`; `test_t006_release_report_must_match_declaration_and_graph_evidence`; `test_t006_duplicate_release_report_rows_are_ambiguous`; `test_t006_release_report_without_graph_proof_stays_unresolved`; `test_t006_shared_context_does_not_choose_an_arbitrary_service_owner` | cílený běh |
| T006-AC06 dokumentace a výsledky | PARTIAL | `docs/changes/32_selectServiceContexts.md` | implementace, testy a lokální evidence jsou připraveny; samostatný PR a required CI zůstávají NOT_RUN v této větvi |

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
| T003-AC05 / T002-SP-01–03 | VERIFIED_IN_SCOPE | `test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard` — dva profily, qualifier, primary, collection/map/optional/provider, property/custom condition UNKNOWN, ambiguity, self-invocation, compiler-symbol meta-stereotype, explicitní component package, statický Configuration/Import/Bean graf a cizí short-name anotace; rules `annotation-source-v5`; bounded selector/registration testy níže | Selectors mimo bounded literal subset, registrars/factories a runtime proxy/async execution zůstávají mimo tvrzený scope |

| T002-CG-03 | PARTIAL | konstrukční test ověřuje compiler-resolved constructor/lambda/reference/operator, primary-constructor initializer/init pořadí a custom accessor; `test_kotlin_file_facade_and_object_initializers_keep_distinct_callers` ověřuje file `<clinit>` proti object constructor realm; `test_control_flow.py` ověřuje when/Elvis/short-circuit/try/finally/break/continue | K2, default-body mapping mimo W02 a coroutine mapping a širší ručně anotovaný corpus |
| T003-AC05 / T002-SP-01–03 | VERIFIED_IN_SCOPE | `test_ac05_spring_profiles_conditions_qualifier_primary_and_short_name_guard` — dva profily, qualifier, primary, collection/map/optional/provider, property/custom condition UNKNOWN, ambiguity, self-invocation, compiler-symbol meta-stereotype, explicitní component package, statický Configuration/Import/Bean graf a cizí short-name anotace; rules `annotation-source-v3` | Dynamic ImportSelector/registrars/factories a runtime proxy/async execution zůstávají mimo tvrzený scope |
| T002-HB-02 | PARTIAL | `test_build_aware.py::test_hb02_schema_realm_and_unverified_naming_do_not_silently_merge` | Kompletní multi-datasource konfigurace, entity access a naming strategie |
| T003-AC06 / T002-HB-01 | PARTIAL | Existing Java/Kotlin persistence fixtures plus `tests/test_jpql_hql_grammar.py` — bounded join/subquery/bulk DML/constructor/path grammar; current rules `annotation-source-v8-jpql-hql-grammar` | Named-query containers, Criteria/Specification/QueryDSL, broader provider grammar, implicit Kotlin annotation-target resolution and complete schema matrix |
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

## T003-S04-W01 — K2 Analysis API 2.1.10

| Acceptance | Podporovaný rozsah | Konkrétní evidence |
|---|---|---|
| AC01 | `k2-analysis-api-2.1.10-v1`, mixed Java/Kotlin, compiler PSI JVM signatures, backend/version provenance | `test_real_mixed_k2_calls_have_stable_jvm_symbols_and_backend_evidence`, `test_packaged_k2_analyzes_outside_checkout` |
| AC02 | Protocol v1; graph loader v1/v2/v3; explicit K1 compatibility | `test_existing_graph_loader_is_unchanged`, `test_k1_distribution_stays_explicitly_limited` |
| AC03 | Unsupported version/config rejected before processes; missing/ambiguous unresolved; no implicit K1 fallback, strict no-mutation | `test_unsupported_backend_or_version_never_runs_or_mutates`, `test_unsupported_captured_k2_options_are_not_silently_ignored`, `test_unresolved_and_ambiguous_k2_calls_remain_partial`, `test_direct_worker_rejects_unsupported_version_and_backend`, `test_k2_store_refresh_is_offline_and_strict_failure_preserves_graph`, `test_explicit_k2_fetch_rejects_wrong_bytes_without_publishing` |
| AC04 | Actual pinned K2/JDK fixture, honest PARTIAL boundaries | [change note35](changes/35_addK2AnalysisBackend.md), `tests/test_k2_backend.py`, required compiler CI K2 gate |

T003-AC04/S04 není tím uzavřen. K2 CFG, property/lambda execution, default-body
a coroutine source mapping, další compiler verze a širší corpus zůstávají samostatné.

| Work package acceptance | Scope/version | Evidence | Actual run |
|---|---|---|---|
| T003-S09-W04-AC01–AC04 | Offline approval sidecar v1; optional additive index hash, graph/store v1/v2/v3 unchanged | `tests/test_methodology_conflicts.py` (11 cases, včetně změny/smazání SVG a nulových procesů při freshness kontrole), existing `test_fa21_approved_requirement_conflict_preserves_authority` | 203 passed in 39.44 s; `KGMAKER_REQUIRE_WORKERS=1`, existing baseline build outputs reused; no whole-S09 claim |

T003-S09-W04 integration against main `0c09028` (2026-10-26): focused feature/scanner/methodology **56 PASS**; full suite **229 PASS, 21 SKIP** without prepared compiler/build artifacts. Historical strict evidence above remains unchanged; see [change note 9](changes/9_bindMethodologyApproval.md).

Prepared packets revalidate documentation conflict coverage outside checkout too; three external HTML/approval/attachment mutation tests reject stale approval without mutating packet/index.

Final integration run after external-packet freshness fix: **232 PASS, 21 SKIP** (5.00 s); focused **56 PASS**. Strict attempt blocked by missing actual Maven fixture (14 setup errors), documented in change note9; no worker PASS is claimed for this environment.

After actual Maven fixture preparation, final strict integrated run **246 PASS, 7 SKIP** (84.81 s); both real compiler workers exercised. Remaining skips require Maven/Gradle executables or a second JDK; see change note9.

## T003-S12-W01 revize 2 — offline konfigurace

| Acceptance | Stav | Přímá evidence |
|---|---|---|
| AC01 | LIVE NOT_RUN, odloženo uživatelem | configuration status zůstává NOT_RUN i s přítomnými auth references |
| AC02–AC03 | VERIFIED_IN_SCOPE | 5 stávajících sync testů a konfigurační negativní/no-mutation testy; žádná změna graph/store |
| AC04–AC05 | VERIFIED_IN_SCOPE | `test_confluence_configuration.py`, capability dokumentace a change note 38; focused 28 PASS, full 281 PASS / 23 toolchain SKIP |


## T003-S09-W03 — Thymeleaf fragment provenance

| Acceptance | Stav | Konkrétní evidence | Výsledek |
|---|---|---|---|
| T003-S09-W03-AC01 | VERIFIED_IN_SCOPE | `tests/test_templates.py::test_static_fragment_arguments_bind_scoped_fragment_parameters_without_collisions`, `test_nested_fragment_arguments_follow_exact_scoped_variables`; existing `test_thymeleaf_literal_binding_and_pdf_boundary`; SOURCE_ONLY `SYNTAX_CANDIDATE` edges | full core: 475 PASS / 114 SKIP; focused: 65 PASS; no expression/render execution |
| T003-S09-W03-AC02 | VERIFIED_IN_SCOPE | Existing literal template variable IDs and PDF boundary remain covered; graph/store schema unchanged; `thymeleaf-bindings-2` capability marker | existing tests plus focused template suite |
| T003-S09-W03-AC03 | VERIFIED_IN_SCOPE | `test_dynamic_ambiguous_and_wrong_arity_fragments_have_diagnostics_and_no_edges`, `test_duplicate_reference_attributes_and_aliases_are_ambiguous_without_edges`, `test_conditional_and_unsupported_expressions_remain_partial_unknown`, and `test_loop_and_local_alias_scopes_do_not_bind_model_variables`; input graph immutability | full core: 475 PASS / 114 SKIP |
| T003-S09-W03-AC04 | VERIFIED_IN_SCOPE | README, compiler-inspection capability, this matrix, progress status, and [change note55](changes/55_expandThymeleafFragments.md) bound the subset; T003-S09/AC09 remain PARTIAL | `kgmaker check` and `git diff --check` after final scan; full-suite skips and boundaries in change note55 |

Only unique same-scope static fragment targets with exact arity are linked. Conditions are not evaluated, unsupported expressions remain UNKNOWN, and no MVC-handler/runtime claim is made.

## T003-S09-W02 — diagnostika binárních XLS

Rozsah `xls-unsupported-1`, `feature-inventory-5`, Python 3.12, bez externího
parseru nebo runtime. [Change note 34](changes/34_diagnoseBinaryXls.md).

| ID | Stav | Přímá evidence | Běh |
|---|---|---|---|
| T003-S09-W02-AC01 | VERIFIED_IN_SCOPE | `test_binary_xls.py::test_real_biff2_fixture_is_unsupported_before_zip_parse_or_process` — BIFF2 fixture, .xls a přejmenované .xlsx; status/hash/file locator | focused 65 PASS |
| T003-S09-W02-AC02 | VERIFIED_IN_SCOPE | `test_packet_and_audit_preserve_hash_bound_gap_without_confirming_missing_data` — save/load a graph v1/v2/v3; stávající `test_workbooks.py` zachovává XLSX cell evidence | focused 65 PASS |
| T003-S09-W02-AC03 | VERIFIED_IN_SCOPE | malformed/compound-container/direct-extractor testy; UNKNOWN audit, nulová mutace store, scope a repo-qualified workspace gaps; oversized hash/freshness/cache regressions v `test_binary_xls.py` | finální focused 100 PASS |
| T003-S09-W02-AC04 | VERIFIED_IN_SCOPE | README, capability docs, tato tabulka, stavová matice a change note 34 vymezují přesný rozsah | S09/AC09 zůstávají PARTIAL |

## T003-S04-W04 — Dependency dispatch hierarchy

| Acceptance | Evidence within scope | Test/fixture |
|---|---|---|
| AC01 | Declared API target separate from realm-specific candidate implementations; missing hierarchy explains incomplete result | `test_source_interface_call_finds_two_dependency_implementation_realms`, `test_missing_parent_excludes_unprovable_implementation`, actual JDK21 JARs |
| AC02 | Additive protocol-v1 provenance; existing graph/store schema v1/v2/v3 retained | existing model/store/protocol suites, compiler integration |
| AC03 | Ordered shadow, generic/intersection fail-closed, physical/source realm separation, exact static ABI conflict, JDK parent-first shadow, runtime-effective MR physical lookup, unresolved declared API PARTIAL, missing/corrupt/bounded negatives, static/private/final/reference boundaries, zero store mutation | `tests/test_dependency_dispatch.py`, actual K1/K2 2.1.10 |
| AC04 | Scoped production matrix and truthful checks | [change44](changes/44_addDependencyDispatchHierarchy.md), S04 remains PARTIAL |
## T003-S09-W01 — přesné tokeny a XLSX reference boundaries

`xlsx-offline-3`; oprava již existujícího offline adaptéru z change note5,
nikoli nová implementace celé extrakce. [Change note39](changes/39_boundXlsxFormulaReferences.md).

| ID | Stav | Konkrétní evidence |
|---|---|---|
| T003-S09-W01-AC01 | VERIFIED_IN_SCOPE | `test_xlsx_references.py::test_formula_tokens_do_not_invent_cell_dependencies` — skutečné ZIP/XML, exponents, LOG10, strings, explicitní sheet/$/range včetně spaced range; `test_literal_sheet_qualifiers_never_fall_back_to_local_cells` — Unicode/numeric/quoted názvy; `test_unsupported_formula_forms_are_boundaries` — shared/follower, INDIRECT, OFFSET, external, 3D a celé řádky/sloupce včetně whitespace bez domyšlených hran |
| T003-S09-W01-AC02 | VERIFIED_IN_SCOPE | Stávající `test_workbooks.py` — hash-bound locators, jednoduché dependency a ZIP ochrany; `test_binary_xls.py` — graph v1/v2/v3 čitelnost; `test_workspace_does_not_reuse_dependencies_from_old_workbook_parser` — reparse v1 i dřívější candidate-v2 cache |
| T003-S09-W01-AC03 | VERIFIED_IN_SCOPE | `test_dynamic_audit_stays_unknown_and_forged_locator_preserves_store` — UNKNOWN, žádný business missing verdict, falešný sheet/cell odmítnut a nulová mutace; qualifier tests zakazují falešný local fallback i process/network |
| T003-S09-W01-AC04 | VERIFIED_IN_SCOPE | Tato tabulka, README, capability dokumentace a stavová matice uvádějí omezený `xlsx-offline-3` scope; S09/AC09 zůstávají PARTIAL |

Přesné finální běhy a SKIP důvody jsou v change note39; plná Excel grammar,
vyhodnocování vzorců a runtime availability nejsou tímto scope dodány.

## T003-S05-W01 — bounded dynamické Spring importy

Aktuální integrační oprava zamýšlených `@Autowired` polí a actual K1/K2 receipt
jsou v [change116](changes/116_parseExtendedJpqlHql.md); UNKNOWN/may-inject
hranice nebyla uvolněna.

`annotation-source-v4`, Java/Javac21, skutečné Spring6.2.2 API, obě JVM distribuce
K1/K2. [Change note42](changes/42_resolveBoundedSpringImports.md); celý S05/AC05 zůstává PARTIAL.

| ID | Stav | Konkrétní test/evidence |
|---|---|---|
| T003-S05-W01-AC01 | VERIFIED_IN_SCOPE | `test_spring_imports.py::test_actual_compiler_qualified_transitive_selector_facts`, `test_literal_and_static_imports_link_without_processor_beans` — exact/inherited/deferred literal selection, static import a fake-name guard |
| T003-S05-W01-AC02 | VERIFIED_IN_SCOPE | `test_legacy_facts_stay_readable_without_literal_promotion` — protocol-v1 legacy UNKNOWN a graph v1/v2/v3; existující actual AC05/compiler/K2 regrese |
| T003-S05-W01-AC03 | VERIFIED_IN_SCOPE | `test_unknown_filters_and_deferred_groups_remain_unknown`, `test_bounded_missing_and_non_type_results_remain_boundaries`, `test_invalid_selector_fact_rejects_before_store_mutation`, strict/offline refresh, profile isolation a UNKNOWN data audit |
| T003-S05-W01-AC04 | VERIFIED_IN_SCOPE | Reprodukovatelná pinned fixture POM + SHA/license lock, mandatory CI bootstrap a `test_required_api_inputs_fail_before_any_process`; README/capability/matice vymezují přesný scope |

## T003-S11-W04 — required worker CI gates

| AC | Concrete evidence | Scope |
|---|---|---|
| AC01 | `tests/test_mandatory_worker_ci.py::test_missing_prerequisite_fails_required_but_skips_optional` (5 absent prerequisites × unset/0/1); existing Spring and exporter prerequisite negatives | Required gates FAIL; optional gates SKIP; real command discovery, no processes |
| AC02 | Existing graph v1/v2/v3 loader regressions and full suite; no product/schema changes | Existing persisted formats unchanged |
| AC03 | Negative matrix checks unchanged last-valid graph bytes and absent worker home; prohibits subprocess | Missing prerequisites never manufacture compiler evidence |
| AC04 | `compiler-workers` actual K1/K2/TS/mixed fixture/Spring6.2.2, separate installed Maven/Gradle exporter job | Pinned declared matrix; second JDK remains optional |

Actual positive CI and final local outcomes are recorded in
[change note 48](changes/48_enforceMandatoryWorkerCi.md); broader production
coverage and later end-to-end/benchmark packages are separate gates.

## T003-S04-W02 — bounded default/bridge declaration mapping

| AC | Evidence | Scope |
|---|---|---|
| AC01 | `test_default_body_mapping.py::test_real_default_and_bridge_mapping` | actual Java default, generic value/void bridges, Kotlin DefaultImpls and JVM-default=all; K1/K2, debug/no-debug; mapping facts and graph roundtrip |
| AC02 | same graph roundtrip + existing graph v1/v2/v3 loader tests | additive metadata, unchanged bytecode/source IDs and store schema |
| AC03 | `test_absent_sources_remain_bytecode_only`, `test_wrong_source_signature_never_maps_generated_body`, `test_nontrivial_bridge_body_stays_bytecode_only`, `test_foreign_default_impls_realm_cannot_claim_local_source`, `test_test_scope_bytecode_never_claims_production_source`, `test_duplicate_class_bodies_do_not_prove_source_mapping` | explicit bytecode-only diagnostics, no guessed mapping; full source/class/store byte comparison |
| AC04 | change46 and compiler-inspection matrix | bounded compiler evidence, no runtime or full S04 completion |

S04 remains PARTIAL: other generated shapes, default-argument masks, coroutines,
statement-level source mapping and unrestricted dependency dispatch are not covered.

Historical pre-ABI W02 evidence: **410 PASS, 9 optional exporter/toolchain SKIP**; all 32
K1/K2/debug mapping cases ran. Commands and limits: [change46](changes/46_mapDefaultBodySources.md).

W02 ABI regression: `test_same_realm_static_instance_abi_changes_never_map` rejects
same-realm static/instance mismatches with compiler-proven flags. The expanded
matrix has 36 actual cases; historical410/9 is superseded for final ABI validation.

Final W02 ABI/main evidence superseding historical410/9: **425 PASS /10 SKIP**,
36 actual mapping cases, focused8 PASS; actual Windows smoke is a remote CI gate.

## T003-S07-W01 — Argument → parameter binding

| Acceptance | Implemented scope | Concrete evidence |
|---|---|---|
| AC01 | Attributed call-site argument → declared formal mapping with context/transformation; candidate execution not inferred | `tests/test_argument_parameter_flow.py`: actual Javac/K1/TS overload, named/default and vararg fixtures; virtual contract negative |
| AC02 | Additive mapping version1; existing worker protocol v1 and graph/store v1/v2/v3 retained; legacy unversioned facts readable | graph/process roundtrip, legacy tests and existing model/store suites |
| AC03 | Unknown K2/ASM bindings, compiler-error recovery, unresolved/reference boundaries, malformed/ambiguous and zero store mutation | actual negative compiler fixtures, atomic last-valid-store fixture, workspace qualification and candidate/legacy impact tests |
| AC04 | Bounded versioned matrix; S07/T003 remain PARTIAL | [change52](changes/52_bindArgumentParameterFlow.md), [compiler matrix](compiler-inspection.md#argument-to-parameter-bindings); final checks recorded after execution |

## T003-S08-W04 — versioned bounded React events

| AC | Actual check | Scope |
|---|---|---|
| AC01 | `test_ui_events.py::test_intrinsic_and_verified_wrapper_have_library_bound_event_evidence` | pinned versions/declaration/package hashes, direct and sole-return forwarder |
| AC02 | existing graph v1/v2/v3 and worker installation tests; legacy context equality | additive evidence, same protocol/store |
| AC03 | changed library, lexical writes/member aliases/eval/factory overwrite/duplicate bindings and conditional/spread/fake/missing-package negatives; offline old-rule/store snapshots | no stronger handler/runtime/data claims |
| AC04 | change69 and supported adapter matrix | S08 broader wrappers/versions remain PARTIAL |

Current rule4 results are recorded in change69; GH CI is optional under T045 revision2, while publication and independent exact-pair review remain required.

T003-S08-W04 historical pre-binding proof: matrix43 PASS/32 DESELECTED237.28s;
full624 PASS/10 SKIP762.95s. Historical rule3 proof: final focus36 PASS/30 DESELECTED
266.43s; prepared strict full727 PASS/10 SKIP791.26s, all66 UI cases, zero failures/errors. onChange input/select/textarea and form onSubmit are actual positives;
source/runtime availability remains UNKNOWN. Current rule4: full785 PASS10 SKIP and current-parent focused189 PASS0 SKIP; exact manifests and limits are in change69.

## T003-S04-W03 — bounded coroutine source mapping

| AC | Evidence | Scope |
|---|---|---|
| AC01 | `test_actual_suspend_source_sites_keep_boundaries`, `test_actual_k1_cfg_preserves_suspend_calls_and_resume_boundary`, `test_real_continuation_maps_declaration_without_mapping_state_instructions` | actual suspend/launch/async/await, multiple suspension points, K1/K2 debug/no-debug; K2 CFG remains unavailable |
| AC02 | Existing v1/v2/v3 graph/store loader suite; additive worker metadata | unchanged identities and persistence formats |
| AC03 | `test_missing_sources_never_map_continuation`, `test_foreign_continuation_realm_never_claims_source`, metadata-negative and ordinary-name tests | no inferred scheduler/target/source instruction locator; byte snapshots unchanged |
| AC04 | change51, pinned Kotlin2.1.10/coroutines SHA fixture | bounded static evidence; whole S04/T003 remains PARTIAL |

## T003-S04-W05 — exact hand-labelled JVM corpus

| AC | Concrete evidence | Scope |
|---|---|---|
| AC01 | `test_actual_inventory_and_unsupported_identity_match_hand_annotations`, `tests/fixtures/jvm-golden/expected.json` | five scenarios × pinned K1/K2; counts, exact owner/descriptor/source locators and unsupported identities |
| AC02 | Existing graph v1/v2/v3 loader tests + corpus graph roundtrip | no model/store/protocol change |
| AC03 | `test_inventory_rejects_missing_extra_retargeted_and_stronger_observations`, reflection/reference/CFG and offline/store snapshots | no fabricated target, source line, runtime execution or availability |
| AC04 | change62 and corpus README version/support matrix | explicit PR35+37 stack; whole S04/T003 remains PARTIAL |

Validation is recorded in change62. Resolved source declarations, unsupported CFG
results and runtime UNKNOWN are distinct; these counts are not production precision.

Prepared strict golden full on ed5ed7c: **646 PASS, 10 SKIP /991.96s**, including21 corpus cases; no failures/setup errors. Historical environment-failed run remains in change62.

## T003-S05-W02 — registrars a FactoryBean produkty

Podporovaný Java/compiler subset, Spring6.2.2, rules `annotation-source-v5`.
Skutečná pinned fixture a kontroly jsou v `tests/test_spring_registrations.py`;
[change note47](changes/47_declareSpringRegistrations.md).

| ID | Stav | Konkrétní evidence a hranice |
|---|---|---|
| T003-S05-W02-AC01 | VERIFIED_IN_SCOPE | `test_literal_registrar_preserves_origin_and_import_condition`, `test_factory_object_and_literal_product_are_distinct`: actual registry/FactoryBean APIs, inherited owner/generic, literal source facts, import conditions, distinct &object/product; custom body/overload/condition a abstract factory UNKNOWN |
| T003-S05-W02-AC02 | VERIFIED_IN_SCOPE | `test_legacy_registration_facts_remain_readable_without_promotion`: graph/store v1/v2/v3 a additive protocol1; TS ordinary/React context snapshots zůstávají současnému main stejné |
| T003-S05-W02-AC03 | VERIFIED_IN_SCOPE | namespace/decoy receiver a129-call budget, `test_registration_profiles_do_not_cross_context`, malformed schema/owner/context/return, strict/timeout nulová store mutace a offline refresh; `test_registrar_and_factory_static_beans_are_not_data_availability` zachovává UNKNOWN/bez business missing verdictu |
| T003-S05-W02-AC04 | VERIFIED_IN_SCOPE | README, compiler capability, tato matice, production progress a note47 vymezují bounded literal scope a actual toolchain evidence; celý S05/AC05 zůstává PARTIAL |
## T015 — database resource projection

| Acceptance | Concrete evidence | Scope |
|---|---|---|
| AC01 | `test_two_actual_datasources_keep_distinct_resources_and_table_drilldown`, `test_identity_ignores_table_details_and_input_order` | Actual workspace/Flyway replay; two explicit realms, stable IDs and deterministic serialization |
| AC02 | `test_only_existing_context_bound_read_write_is_projected`, `test_entity_mapping_is_only_a_dependency_not_read_or_write`, `test_plain_connection_configuration_never_creates_database_access` | Existing source/context/evidence-bound facts only; no query inference |
| AC03 | Migration-only/default-DB/DTO cases | MIGRATION_DERIVED attribute; deployment/data availability UNKNOWN |
| AC04 | `test_stale_migration_fails_without_mutating_last_valid_artifact`, invalid schema and malformed-evidence regressions | Pure reads; unchanged workspace, graph, coverage and last artifact; subprocess forbidden |
| AC05 | Foreign/test/stale/missing/conflicting realm and evidence cases; explicit conflict buckets; unknown file scope; upstream truncation | No confidence, freshness, polarity or scope upgrade; full S06 remains PARTIAL |
| AC06 | [Change note68](changes/68_projectDataResources.md) | Public36 cases; broader focused115 PASS/6.79s; final full tracked there |

## T003-S07-W02 — Return → consumer binding

| AC | Bounded delivered proof | Evidence |
|---|---|---|
| AC01 | Compiler-owned ranges/direction, branch alternatives, distinct assignments, nullable/chained consumers | `tests/test_return_consumer_flow.py`, `fixtures/return-consumer` actual Javac/K1/TS |
| AC02 | Additive protocol1/graph1/2/3; stale explicit rule stays offline | Legacy and stale-rule tests in the same module |
| AC03 | Opaque/open/recursive/callable/void/any/async/custom-projection bodies remain UNKNOWN; malformed input does not mutate store | Actual worker negatives and malformed-IR/zero-store tests |
| AC04 | `return-consumer-1` matrix; K2 Kotlin missing source CFG remains UNKNOWN; S07/T003 PARTIAL | [change66](changes/66_bindReturnConsumerFlow.md), [compiler matrix](compiler-inspection.md#return--consumer-bindings); full result pending |

## T023 — explicit process model

| Acceptance | Stav | Konkrétní důkaz | Hranice |
|---|---|---|---|
| T023-AC01 | VERIFIED_IN_SCOPE | `test_ac01_diamond_loop_exception_and_async_roundtrip_preserve_exact_ids`, `test_documented_fixture_loads_on_public_api_with_loop_and_no_guessed_branch_join` | Explicitní JSON struktura, nikoli discovery/observed execution |
| T023-AC02 | VERIFIED_IN_SCOPE | `test_ac02_approved_czech_label_never_changes_technical_truth` | Review stav je dodané metadata, ne nové approval rozhodnutí |
| T023-AC03 | VERIFIED_IN_SCOPE | `test_ac03_annotation_technical_injection_is_rejected` | Pouze allowlisted semantic overlay |
| T023-AC04 | VERIFIED_IN_SCOPE | invalidní revision/target/evidence input před/po; `test_pure_parse_and_serialization_perform_no_file_network_or_process_io` | Žádný model apply/store API |
| T023-AC05 | VERIFIED_IN_SCOPE | missing/stale/foreign/unused proof, truncation a kind/status negatives v `test_t023_define_business_process_model.py` | PARTIAL/UNKNOWN a no evidence upgrade |
| T023-AC06 | VERIFIED_IN_SCOPE | [note70](changes/70_defineBusinessProcessModel.md), [capability](process-model.md), schema/fixture; focused130 PASS; frozen full729 PASS/10 SKIP,515 hashes beze změny | Lokální model proof; publikace, exact-pair review a fresh CI jsou samostatné release gates |

## T010 — HTTP provider inventory (bounded PARTIAL)

| AC | Local evidence | Boundary |
|---|---|---|
| T010-AC01 | `test_two_services_in_same_repository_do_not_share_global_endpoint_identity` and two-repository `/orders` test | explicit service ownership; no inferred service realm |
| T010-AC02 | `test_contract_revisions_stay_separate_without_automatic_handler_binding` and contract-only test | contracts never prove handler, deployment or runtime |
| T010-AC03 | `test_actual_spring_class_method_mirrors_preserve_handlers_and_route_case` actual JDK21/K1/Spring6.2.2; dynamic-prefix test | exact annotation mirrors; unresolved/custom/inherited mappings remain UNKNOWN |
| T010-AC04 | malformed metadata/hash/edge tests and no-process/network/file/store mutation checks | pure projection only; source/declaration mismatches fail closed |
| T010-AC05 | explicit test scope, foreign context, missing ownership, legacy metadata and runtime-label/unbound-edge negatives | source evidence stays candidate; imported runtime binding unsupported UNKNOWN |
| T010-AC06 | README, architecture guide, status matrix and [change67](changes/67_catalogHttpProviders.md) |145 focused +strict596 PASS/10optional SKIP; main integration199 PASS; exact review/remote CI pending (billing blocked) |

Actual compiler is a static compiler fixture, not a real application runtime test.
Runtime acceptance NOT_RUN; no data availability or overall T004 completion claim.

## T003-S05-W03 — condition matrix

[Change116](changes/116_parseExtendedJpqlHql.md) opravuje canonical injection
v actual fixture; condition/property/profile assertions zůstaly stejné a
nový K1/K2 běh prochází.

| AC | Test and supported proof |
|---|---|
| AC01 | `test_actual_pinned_conditions_and_negated_profile_injection`; `test_actual_variant_input_and_classpath_freshness_are_isolated`: labelled real annotations, explicit variant inputs, independently stale config/JAR with unchanged second context/store |
| AC02 | `test_legacy_spring_rules_remain_readable_but_require_reinspection`; existing graph v1/v2/v3 tests, unchanged schema |
| AC03 | `test_unresolved_compiler_class_literal_never_proves_presence_or_absence`, typed malformed/unknown cases and `test_required_pinned_apis_missing_or_changed_fail_before_process`; no fabricated class absence/activation |
| AC04 | Actual pinned Spring6.2.2/Boot3.4.2 fixture and declared grammar/property/class scope; [change note50](changes/50_expandSpringConditions.md) records exact outcomes |


### T003-S07-W04 — bounded Kafka configuration identity

- AC01: `test_exact_cluster_topic_contract_release_and_profile_identity` uses
  actual base/blue properties and JSON contract: two same-topic clusters never
  match; distinct release never matches. Dynamic/cyclic/partial values and
  unsupported profile/config/contract remain UNKNOWN. No transport proof.
- AC02: optional workspace schema1 block; old HTTP services default unchanged;
  `test_config_and_contract_hash_changes_invalidate_bindings_without_source_mutation`
  reads graph/store v1/v2/v3. Legacy syntax nodes remain distinct.
- AC03: structural/path/ownership and context ambiguity fail closed; missing
  evidence creates UNKNOWN; snapshot race/cancellation and disk-cache failure
  publish no cache/source/store changes. Actual K1/K2 captured context test verifies
  precedence/freshness without implicit repair. Password sentinel is absent from
  graph; offline source-only checks allow only existing Git baseline reads.
- AC04: matrix remains PARTIAL; source contract scope/version and fixture are in
  compiler-inspection and [note54](changes/54_scopeKafkaBindingIdentity.md).


S07-W04 AC03 privacy correction: `test_sensitive_property_reference_never_exports_topic`,
`test_public_workspace_captured_property_privacy_and_freshness` and
`test_binding_cluster_alias_reference_privacy` exercise the public snapshot API
for direct/transitive property references. `kafka-binding-2` returns UNKNOWN and
no match before reading sensitive aliases; the full public graph redacts captured
sensitive values while original input bytes/cache/context hashes remain valid.
`test_public_kafka_projection_preserves_non_jvm_selection_identity` guards the
postvalidation projection boundary. Prior613 full PASS does not cover this later
review regression; note54 records separate current evidence.
## T024 — bounded trigger inventory

AC01/02: explicit and actual K1 HTTP/Kafka/scheduler candidates with production/test
separation. AC03/05: unsupported scheduler/K2 annotation capture, missing CFG,
canonical source/symbol/edge/proof/hash/scope negatives stay PARTIAL/UNKNOWN.
AC04: actual offline projection forbids subprocess and compares inputs/captured
checkout bytes; malformed inputs preserve last-valid artifact. AC06: capability
and note71 supplied; strict frozen full812PASS/10optionalSKIP is recorded in note71. Current-main
integration236PASS is recorded; final independent review/merge remain pending (PR59).
Focused41PASS and current-base199PASS (actual K1/K2 included), no runtime observation.

## T003-S06-W04 — Explicit persistence realms (VERIFIED_IN_SCOPE)

`tests/test_persistence_realms.py` covers two databases sharing stream main with
different actual offline migrations/targets, exact duplicate-pair rejection,
shared migration-path isolation, delimiter/percent IDs, quoted-dot SQL component
collisions and metadata tamper. Actual K1/K2 contexts over the same entity retain
separate native/JPQL scope, idempotent local reprojection and selected T015 access.
Two actual persistence units bind the same entity to their own DB/schema/table
with XML provenance; ambiguous PU produces no physical claim and preserves store.
The new current-JPA layer rejects missing/partial/foreign realm proof. Legacy
source-only regex fields remain readable, with no new strong physical link.

Final strict full: **1348 PASS, 10 SKIP in1583.75s**, mandatory workers/K2/Spring/
HTTP flags, XML1358 tests/0failures/0errors. Exact HEADb75370d and all623 frozen
input hashes remained unchanged. Earlier182PASS+setupERROR is a partial result,
not the final full. See change note74 and persistent validation receipts.

Supported physical bindings are non-renamed replay tables/columns. Valid renamed
objects with stable creation IDs currently remain UNKNOWN; S06-W08 supplies the
creation-identity lifecycle follow-up. Broader provider, grammar, schema lifecycle,
deployment and populated-data availability are not proved. S06 remains PARTIAL.

## T003-S07-W06 — HTTP client intent, omezený compiler subset

| ID | Stav | Přímá evidence |
|---|---|---|
| AC01 | VERIFIED_IN_SCOPE | `test_http_client_execution.py`: actual Spring6.2.2/Reactor3.7.2 Java v K1/K2; cold publisher vs same-origin terminal, RestClient retrieve/body/exchange; explicit property source/profile/SHA provenance |
| AC02 | VERIFIED_IN_SCOPE | `test_old_graph_store_versions_remain_readable` schema1/2/3; legacy coverage UNKNOWN; additive IR optional, fresh HTTP version/input fingerprint validated |
| AC03 | VERIFIED_IN_SCOPE | Escaped/captured/stored/returned/unknown operators, unrelated terminals, reference and local fake negatives; URI credentials removed; malformed IR/config snapshot reject before store write |
| AC04 | PARTIAL_MILESTONE | [Supported matrix](compiler-inspection.md#http-client-intent), [note63](changes/63_classifyHttpClientExecution.md); Kotlin missing bindings UNKNOWN, no runtime HTTP/availability or complete S07/T003 claim |

Lokální přesné výsledky a explicitní neprovedené remote gates jsou v note56.
Remote Actions billing je BLOCKED; lokální evidence nenahrazuje povinné CI.

S07-W06 review follow-up (rule2): actual K1/K2 throw/ternary/update/resource negatives, URI callback and Feign path-prefix boundaries, unsupported properties override, embedded scheme-relative URI privacy, and stale-v1/no-process/no-mutation proof are covered by `tests/test_http_client_execution.py`. Exact final checks are in change63; runtime HTTP/data availability remains UNKNOWN.

## T025 — local technical process path

| Acceptance | Bounded evidence | Remaining gate |
|---|---|---|
| AC01 | Public diamond and actual Javac/K1: no left↔right path, nested bodies and returns_to | Source closure/full/final review |
| AC02 | Recursion/dispatch/depth/async boundaries retain original call-site; actual target/complete/receiver mutations cannot expand another body | Bounded source CFG only; no runtime claim |
| AC03 | Existing flow.process root overflow + typed output budgets1/2/3 preserve explicit node-limit boundary | No unbounded root copy |
| AC04 | Input bytes and last-valid artifact unchanged for malformed/foreign proof; actual offline path forbids subprocess/network | Pure API writes nothing |
| AC05 | Canonical declaration, source file scope/hash, selected context and both call-site edges/proofs; missing CFG/unsupported legacy remains UNKNOWN/PARTIAL | Current physical snapshots are caller responsibility |
| AC06 | [Capability](process-paths.md), [note73](changes/73_buildLocalProcessPath.md), README/status updates | T024 PR59 dependency, required full and release pending |

## T011 — typed HTTP consumer inventory

AC01 lazy/static intent, AC02 dynamic URI/source identity, AC03 actual Feign and
WebClient occurrences, AC04 offline/input preservation, AC05 malformed source/
edge/scope/owner/SHA and selected stale siblings are in
`tests/test_t011_catalog_http_consumers.py`. AC06 documentation and actual outcome
are in [change76](changes/76_catalogHttpConsumers.md) (historical strict full1373PASS/10optionalSKIP). Current portable actual capture and full-suite repair are recorded in [change116](changes/116_parseExtendedJpqlHql.md); runtime NOT_RUN.

## T025 revision2 — compiler local operation evidence (candidate)

T025-AC07–09 require the actual typed local-literal chain in both JVM backends,
unsupported/error/legacy cases, exact IR/source/context/CFG proof mutation guards,
finally-clone and workspace preservation, and unresolved control transitions.
`tests/test_local_operation_proofs.py` contains these candidate checks. Executed:
pre-feature actual RED1FAIL0.73s, explicit protocol11PASS and legacy/model/protocol
120PASS2actualDESELECTED4.44s. JavaFrontend source-only javac compilation passed;
both fresh workers built successfully; initial matrix36PASS1ERROR is preserved.
After origin and proof-retention corrections,39purePASS and bounded actual K1
workspace/process1PASS4.69s; corrected complete matrix/full remain pending. No
T026 or whole T025/T003/T004 completion is implied by this row.

## T026 — lossless business-step projection (candidate)

| AC | Concrete public-contract test in `tests/test_t026_collapse_business_steps.py` | Evidence |
|---|---|---|
| AC01 | actual Javac literal-local collapse; ordered roundtrip; parallel edges; finally clones and unused exit | Actual K1/K2; final full 1566PASS/10SKIP v 1532.43s |
| AC02 | disconnected equal DTO; diamond remains separate | 95 T026 cases in strict full |
| AC03 | field/call/finally actual boundaries; decisions/loops/exception/unknown boundary matrix | Strict full includes actual and pure cases |
| AC04 | immutable inputs on invalid/stale/foreign/tampered proof, no subprocess/network; structural budgets | No write/publish API |
| AC05 | aggregate SYNTAX evidence remains UNRESOLVED/PARTIAL; scope/context/method/proof guards | No runtime promotion |
| AC06 | README, capability, status and change82 | Source APPROVE cff803c; strict full 1566PASS/10SKIP v 1532.43s; PR65 merged32a3bca, metadata-only integration |

## T027 — HTTP process boundary

Delivery PR_OPEN ([PR105](https://github.com/p-rum/kgmaker/pull/105)); approved
HEAD `82eef329` integrates main `ec05a329fe2e51dbfe0eb47888bed037a251b8bf` with MERGED
PR101–104. New targeted run: **200 PASS / 0 SKIP, 10.76 s** (191 public cases +
9 reviewer reproductions), actual Javac/K1/K2. Exact integration review remains
separate. Historical validation after the original corrections:
**187 PASS / 0 SKIP** in T027/T014/T025/T026 with prepared JDK21/Javac/K1/K2;
the final terminal-only and request-origin guards were then verified by
**38 PASS / 0 SKIP** (29 public T027 cases + 9 independent reviewer reproductions).

| Acceptance | Concrete public-contract test | Current evidence / remaining gate |
|---|---|---|
| AC01 | `test_public_t014_projection_links_cross_repository_client_callsite_to_target_process`, `test_invalid_remote_endpoint_or_binding_cannot_authorize_expansion` | VERIFIED_IN_SCOPE; exact T014 version, HTTP endpoint direction, service/context and stale guards |
| AC02 | `test_ac02_incompatible_or_nonresolved_release_stays_external`, `test_public_t014_incompatible_release_without_candidate_edge_remains_external` | VERIFIED_IN_SCOPE; incompatible selector and ambiguity have no handler winner |
| AC03 | `test_ac03_missing_target_cfg_retains_external_boundary_and_local_continuation`, `test_terminal_only_target_does_not_supply_a_cfg_body` | VERIFIED_IN_SCOPE; unavailable body remains external, local continuation survives |
| AC04 | `test_ac04_bad_input_and_failure_boundary_do_not_mutate_inputs`, `test_normal_response_retains_original_witness_without_mapping_server_errors` | VERIFIED_IN_SCOPE; immutable inputs, original exception edges retained, expanded-CFG reachability prevents false REQUEST/RESPONSE paths |
| AC05 | `test_target_selection_must_match_boundary_scope`, `test_imported_target_truncation_and_limits_remain_visible`, `test_local_and_remote_and_imported_coverage_are_preserved` | VERIFIED_IN_SCOPE; selected scope and every imported limitation preserved; runtime/availability UNKNOWN/NOT_OBSERVED |
| AC06 | [Capability](process-paths.md#explicit-http-process-boundary-t027), README, status and [change123](changes/123_crossHttpProcessBoundary.md) | PARTIAL; PR105 is open, reviewed source preserved and current integration tests/semantic audit documented in change123; new integration review and full suite/remote CI NOT_RUN |

## T003-S06-W06 — NamedQueries a named native queries (MERGED / VERIFIED_IN_SCOPE)

Aktuální integrační evidence 2026-11-15; [change120](changes/120_namedQueryContainers.md).
JPA rule `annotation-source-v9-named-query-containers`; skutečný Javac 21.0.13.0.3.
Dodání `MERGED` ([PR102](https://github.com/p-rum/kgmaker/pull/102), commit
`9f88d8463b3c968592f0f1937736b752dfccee1d`). Historická společná cílená sada nad
HEAD `00603901`: 205 PASS / 0 SKIP, 36.87 s (W06 117 + runtime 88); nezávislé
review opakovalo 205 PASS / 0 SKIP, 37.88 s. PR103 zachovává obsah W06/runtime
zdrojů; nejde o nový běh této sady ([change121](changes/121_invalidateDerivedViews.md)).

| Acceptance | Konkrétní evidence |
|---|---|
| T003-S06-W06-AC01 | `test_actual_javac_named_query_containers_reference_parameters_and_projections`: kontejnery, repeatable JPQL/native, XML root/entity, named/positional parametry a projekce; trojitá duplicita, chybějící jméno/tělo, XML/anotace a malformed tělo. `test_actual_named_queries_select_xml_persistence_realm_without_cross_binding`: dva publikované kontexty, žádný cross-realm fallback. |
| T003-S06-W06-AC02 | `test_legacy_named_query_metadata_remains_readable`: v1/v2/v3; structured compiler roundtrip; existující `test_jpql_hql_grammar.py` a `test_orm_xml_overrides.py`. Graph schema ani worker protocol se nemění; framework rule v9 vyžaduje refresh. |
| T003-S06-W06-AC03 | `test_actual_named_query_strict_rejection_cancel_timeout_preserve_store`: strict invalid XML, cancellation a skutečný worker timeout zachovají byte-identický store. `test_actual_offline_scan_and_hook_preserve_named_query_evidence`: zákaz subprocess; pure projection nemutuje vstup. Foreign container/class a malformed XML nevytvoří binding. `test_public_native_query_lexical_boundaries_and_statement_intent` a actual Javac fixture ověřují, že SQL literály/komentáře nevytváří tabulky a komentovaný UPDATE/DELETE zachová write/delete intent. |
| T003-S06-W06-AC04 | `fixtures/named-queries/Model.java`, `orm.xml`; testy výše a přesný příkaz/výsledek v change120. Ověřené compiler fakty nepovyšují runtime/data availability. |

Hranice: native SQL poskytuje statické přesné table/type bindings, nikoli provider
validaci; result-set mapping je PARTIAL. `@Param` aliasy, implicitní repository
named convention, dynamické EntityManager lookupy a samostatná actual Kotlin
container matice nejsou tímto scope garantovány. Celý T003-S06 není dokončen.

## T003-S06-W08 — bounded schema compatibility (VERIFIED_IN_SCOPE)

Dependency W04 PR62 merged. Current main c193748 (Return+Kafka+HTTP ambiguity)
is integrated; final independent exact-pair review/ready/merge remain separate.

| Acceptance | Supported proof / tests | Actual evidence |
|---|---|---|
| W08-AC01 | `tests/test_schema_compatibility.py`: actual Javac FIELD/PROPERTY/inherited, canonical descriptors, null/decimal, PK/UK, explicit ManyToOne FK, current target rename/drop/incarnation | Both K1/K2 distributions; strict full ced1591PASS/10optionalSKIP; current Return67 matrix174PASS/0SKIP |
| W08-AC02 | Legacy graphv1/v2/v3 readable; absent fingerprint/canonical witness UNKNOWN | Included own public matrix and full; no migration guessed |
| W08-AC03 | Exact selected realm/context/SHA/snapshot, custom same-name types/SQLdomain UNKNOWN, malformed member and unknown version negatives, no mutation/availability promotion | P1/P2 source findings closed, actual guard29PASS and current matrix; full1471 inputs unchanged |
| W08-AC04 | README, capability/CLI, note78, current state and exact source evidence | Final parent pure HTTP ambiguity4PASS/0SKIP0.56s; no repeated full/build solely for parent |

Full1591PASS/10optionalSKIP1646.65s is attributed only to ced9717; current
Return174PASS/0SKIP248.87s only to67b8341. No runtime/data/deployment proof.
Unsupported XML effective constraints, naming/converters/composite/defaulted FK
remain UNKNOWN; no whole S06/T003/T004 completion claim.

### T010 rev2 — colliding normalized variants (VERIFIED_IN_SCOPE)

AC03–05: `tests/test_http_provider_ambiguity.py` covers actual JSON aliases,
two service realms, method/sibling separation, deterministic order and duplicate
records, YAML distinct locators and immutable caller inputs. Original actual focus149PASS/0SKIP; strict full493:1605PASS/10SKIP1683.18s; Return-parent e740 composition284PASS/0SKIP219.41s. Full and focused source attribution stay distinct; no runtime/deployment or whole-milestone claim. See change88.
### T003-S07-W04 revize2 — draft code/group acceptance

`tests/test_kafka_code_bindings.py` přidává actual Java listener/send v obou
backendech, Kotlin K1 listener a explicitní Kotlin K2 PARTIAL negative (pinned
backend nemá method annotations). Replay mutation testy mění annotation mirrors,
realm, range a compiler witness; config-only/SOURCE_ONLY nejsou code proof.
Schema2 public snapshot ověřuje explicitní původní code refs, group property
provenance, subscription a private-property redakci; cizí ID/context/SHA se
nepovýší. Regex nikdy není exact-topic join. Current-parent19b focus102PASS/0SKIP
a strict full1576PASS/10optionalSKIP v1536.69s drží1477 frozen input hashů beze
změny; source composition má nezávislé root APPROVE. Finální metadata-head review
a publication jsou oddělené. Historická revize1 není důkaz nové revize2; K2 listener
metadata zůstávají PARTIAL a runtime/data availability UNASSESSED. Viz note77.

## T006/T008 revision2 — derived context role boundary

T006-AC07–08 and T008-AC07–09: `tests/test_context_roles.py` covers full mixed and
config-only public snapshots, T010/T011/T015/trigger consumers, historical captured
hashes versus role freshness, malformed/unknown version/identity/input/realm,
source/compiler pins, original strict foreign paths and immutable full inputs.
The coalesced existing T005–T010/T015/Kafka/trigger regressions passed294/0SKIP
(9actual deselected). A separate pure replay of the actual current-parent Kafka
capture retained2CURRENT compiler contexts across5projections with no process,
network or input/store mutation. Common runtime/test are exact in combined descendant `2df55ff`: strict full 2587 PASS / 10 exact optional SKIP, 2042.93 s, all 4897 hashes and five member inventories unchanged. All 1966 Common-parent IDs occur in that one XML: 1956 PASS / 10 optional SKIP. Current-parent actual focus 217 PASS / 0 SKIP. This is descendant superset evidence, not a standalone Common full or T016/runtime availability acceptance; final exact-pair review/merge is separate.
## T003-S07-W05 — retry/DLT policy draft

AC01–04 map to `tests/test_kafka_retry_dlt.py` and [note87](changes/87_captureKafkaRetryDlt.md).
Current-parent coalesced actual/pure470PASS/0SKIP186.44s preserves1620input hashes.
Historical initial6PASS and pure-only replays remain distinct in note87. Current
source has independent focus closure; strict full647 passed1908/10; current-parent pure23PASS,
final exact-pair review/ready pending. No runtime/delivery or whole-S07 completion follows.


## T012 — Kafka interface catalogue (verified bounded scope)

T012-AC01–AC05 map to `tests/test_t012_catalog_kafka_interfaces.py`: separate realms
and consumer groups, canonical send versus config-only/NewTopic, immutable public
and private proof inputs, exact qualified Node/source/edge tuple guards, selected
and historical contexts, regex and Kotlin K2 annotation UNKNOWN. All105 own IDs
PASS in combined descendant2df55 strict full2587PASS10exactoptionalSKIP2042.93s;
all2071 parent IDs present there are2061PASS10SKIP. Corrected own actual selection
10PASS/0SKIP36.89s; current-parent coalesced444PASS/0SKIP370.90s. AC06 docs and
preserved failures/limits are in note81. Main/Common dependencies merged; exact
finalpair review/merge separate. No standalone parent full or transport observation.


## T013 — explicit versioned contract attachments (verified bounded scope)

T013-AC01 content revisions/stable original IDs, AC02 no DTO-name compatibility,
AC03 generated-origin binding preserved as stale after contract changes, AC04
bounded read-only/immutable capture/attachment and AC05 selected scope/context,
ambiguous operations and external/malformed pointers map to
`tests/test_t013_attach_interface_contracts.py` (43 PASS) and actual K1/K2 captured
Kafka revisions `tests/test_t013_captured_kafka_contracts.py` (2 PASS). All45 own IDs
PASS in ONE combined descendant2df55 strict full2587PASS10exactoptionalSKIP2042.93s;
ALL2116 parent IDs in that XML are2106PASS10SKIP, not a standalone parent full.
Corrected current-composition focus444PASS0SKIP370.90s and pure59PASS3.03s retained.
AC06 [change85](changes/85_attachInterfaceContracts.md) explains actual capture,
payload-type UNKNOWN, stricter invalid-input helper limits and preserved failures.
T012 dependency merged; independent finalpair review/ready/merge separate.

## T030 — pure process-label packet (candidate)

| AC | Concrete public proof | Current result |
|---|---|---|
| AC01 | exact existing targets/origins/proofs, order/generation invariance, changed content/doc/ordered collapse hash | 153purePASS; all47T030 actualPASS in descendant2df55 |
| AC02 | tiny mandatory overflow, complete omissions, UTF8, exact adjacent char/token cost and hard-envelope failure | 153purePASS; all47T030 actualPASS in descendant2df55 |
| AC03 | no I/O/process/network/feature.prepare; raw label/config/proof/doc/error sentinel and ref-only provenance | 153purePASS; all47T030 actualPASS in descendant2df55 |
| AC04 | success/error deep equality; cyclic/shared/huge preflight before model copy; no last-artifact write | 153purePASS; all47T030 actualPASS in descendant2df55 |
| AC05 | captured structured conflicts, selection scope/context rejection, unsupported/unresolved/truncated preservation | 153purePASS; all47T030 actualPASS in descendant2df55 |
| AC06 | spec Rev2, Python API/capability docs, note90, descendant proof | exact final review/PR pending |

No model call, semantic approval, T031 apply or T034 CLI is supplied by this row.

T030 full support is ONE actual descendant2df55 run2587PASS10allowedSKIP, not a
standalone parent full. ALL1990parent IDs classified1980PASS10allowedSKIP; all47own
PASS. Original32AST/35globalbindings+byteprefix and whole testfile exact; see
[bounded proof](validation/t030-descendant-proof.json). GHCI optional/unverified.

Current main2a (Common/T012/T013 merged) requires all2116current-main parent
identities plus47T030 cases:2163total,2153PASS10sameallowedSKIP in actual2df.
OriginalT0301990 is also fully contained. This is an exact source/ID-union proof,
not a new parent collection/full/test execution. Original47own cases remain PASS.
## T046 — Offline delivery workflow

| Požadavek / acceptance | Implementace | Ověření / scénář |
|---|---|---|
| T046-R01 / AC01 | artifact_templates, template CLI, init | test_artifact_templates: defaults, custom content, hash, preserved edits, collision and symlink guards |
| T046-R02 / AC02–03 | testgen prepare/validate/apply/export | test_delivery: existing-function E2E, actual PASS then deliberate behaviour FAIL, framework/target ambiguity |
| T046-R05 / AC04 | schema_errors, JSON/CSV export | test_synthetic_data + delivery negative dataset, foreign-key and preflight tests |
| T046-R03 / AC05 | provenance journal, trace sync/show/check | delivery forward/backward traversal, requirement/test/data refs, staleness and missing actors |
| T046-R04 / AC06 | policy, decisions, workflow save gate | delivery optional gate, direct-save bypass rejection, review source binding and agent rejection |
| T046-R05 / AC07–08 | workflow v1/v2, CAS, atomic state | delivery ID preservation, journal tampering, writer conflict, invalid-input zero mutation and Git-only metadata process guard |

Výsledky skutečných běhů a limity prostředí jsou v change notes 56–61. Testovací
návrh má NOT_RUN; výsledek unittest E2E je oddělená validační evidence. Tato tabulka
nenahrazuje review ani chybějící pytest/compiler/GitHub CI běhy.

T046 revize 2 doplňuje protipříklady review: delayed creator + immutable history
(test_provenance), canonical protected code/data paths + FK missing-vs-null +
record/direct-save gate + all trace CAS routes (test_delivery) a recursive typed
enum equality (test_synthetic_data). Každý scénář před opravou reprodukoval chybu;
nové běhy nejsou zaměňovány s původními 198 testy.


T046 integrace 2026-11-05 nad main9eec41a: 52 cílených pytest PASS; dostupná celá sada 1152 PASS /1045 SKIP, bez failures. Skips nedokládají nepřipravené toolchainy. Přesné limity jsou v change61; GH CI je podle T045 revize 2 doplňující evidence. Nové exact-pair review není nahrazeno historickým review.

## T003-S07-W07 — explicit remote mapping draft

| AC | Current evidence | Pending |
|---|---|---|
| AC01 | Actual HTTP Java/Kafka K1/K2 mapping, explicit v1/v2 pairing, ambiguity and Kotlin HTTP UNKNOWN;334 unique source-specific cohort PASS | Final current-parent pair |
| AC02 | Strict optional manifest/capture version, existing workspace regressions; all1973 parent IDs covered in combined2df full | Exact refreshed composition review |
| AC03 | Actual/public realm/operation/hash/release/ambiguity/privacy/no-I/O/transport/budget negatives;334 cohort PASS | No runtime/availability proof claimed |
| AC04 | [contract](remote-contract-mapping.md), [note91](changes/91_planRemoteContractMapping.md); combined2df2587PASS/10approvedSKIP, W07-parent1963PASS/10SKIP | Final independent review |

The full ran on combined descendant2df55ff8, not standalone W07. Historical
failures and partial runs remain separately attributed in note91.

## T031 — read-only annotation validation (final review candidate)

| AC | Concrete public proof | Actual result |
|---|---|---|
| AC01 | Self-rehashed allowlist, stale current-process/docs/context/budgets rejection | PASS |
| AC02 | Czech group/outcome proposals, unchanged technical subtree and fingerprints | PASS |
| AC03 | All overlapping-field and captured documentary conflicts retained for review | PASS |
| AC04 | NoIO/immutability/error privacy/no partial proposals/bounded structures | PASS |
| AC05 | Forged refs/status/technical fields rejected; unsupported coverage unchanged | PASS |
| AC06 | SpecRev2/API/docs/note92 + bounded actual proof | Final exactpair review/PR pending |

ALL76owncases PASS in ONEactual descendant2df55 full2587PASS10allowedSKIP, not
standaloneT031. Original2066parentIDs2056PASS10SKIP. Currentmain5ffe2252 +own76
source/IDunion2328 gives2318PASS10sameSKIP fromthatXML; no new test/collection.
Whole module/testfile exactactual; T03032AST/35globals prefix+6disjointbindings.
See [bounded proof](validation/t031-descendant-proof.json). GHCI optional/unverified.

Explicit stack T030070. Its47tests and complete original module AST/byte prefix
are unchanged; full proof is pending, not inferred from these pure results.

## T032 — explicit local semantic review (final review candidate)

| AC | Concrete public evidence | Result |
|---|---|---|
| AC01 | Same operation/no rewrite; historical retry cannot rewind head | PASS |
| AC02 | Real processes+threads CAS; stale/different operation conflict | PASS |
| AC03 | Changed explicit baseline/capture revalidation; scope isolation | PASS |
| AC04 | Pre/postpublication failure/cancel; unchanged inputs and lastvalidJSON | PASS |
| AC05 | Documentary namespace; conflict blocks; safe error/bounds/unsupported paths | PASS |
| AC06 | Spec/API/docs/note94 + actual descendant proof | Final exactpairreview/PRpending |

All36owncases PASS in ONEactual2df55 full2587PASS10allowedSKIP; whole module/testfile
and currentT031 dependency exactactual. Original2102parent2092PASS10SKIP; current
2328main+36union2364=2354PASS10sameSKIP. Derived source/IDunion, not newexecution
orcollection. See [proof](validation/t032-descendant-proof.json). GHCIoptional/unverified.

Source `tests/test_t032_persist_process_review.py`:36PASS1.93s. Combined inherited
pure regression269PASS94SKIP8.74s; compiler cases SKIPPED without native execution.
The separately frozen T030/T031 full is not evidence of T032 full validation.

## T033 — read-only process catalog (final review candidate)

| AC | Concrete public evidence | Result |
|---|---|---|
| AC01 | Same label distinct trigger identity; explicit multiple triggers | PASS |
| AC02 | Candidate never approved; alias preserves every member review/label state | PASS |
| AC03 | Missing/stale/context trigger remains inactive historical, partial absence qualified | PASS |
| AC04 | No writes/network/process execution; immutable valid/invalid snapshots/store | PASS |
| AC05 | Scope/context/collision/alias/caps/privacy negatives; outcomes/owner/uncertainty retained | PASS |
| AC06 | SpecRev2/API/docs/note96 + actual proof | Finalexactpairreview/PRpending |

All37owncases XMLPASS in ONEactual2df55 full2587PASS10allowedSKIP; wholemodule/
testfile+5processdependencies exactactual. Original2139parent2129PASS10SKIP;
currentmain2364+37source/IDunion2401=2391PASS10sameSKIP. No new run/collection.
See [proof](validation/t033-descendant-proof.json). GHCIoptional/unverified.


## T014 — current-parent descendant-result transfer

- AC01–03: public hand-labelled HTTP/Kafka mapping, same URL/no mapping, wrong
  release/hash/pointer, ambiguous/incomplete candidates and original refs.
- AC04–05: input equality, changed capture/selection/graph/interface, no-I/O,
  credential IDs, hard bounds, source-proof polarity and UNKNOWN capture freshness.
- AC06: Root SOURCE_APPROVE09d plus accepted2df full2587PASS10allowedSKIP; owned
  source/tests exact, all24own cases XMLPASS. Current509+24own union2425 maps to
  2415PASS10sameSKIP on that accepted descendant; no new run. Exact-pair independent
  review/Root merge remain pending. See note93 and validation/t014-descendant-proof.json.

Hand-labelled protocol positives are not compiler/native acceptance proof.

## T016 — current-parent descendant-result transfer

- AC01: public HTTP origin interface/mapping/release/operation/edge expansions.
- AC02: Kafka publishes/consumes through realm/topic channels, distinct groups.
- AC03: graph enum noise changes input binding, not topology identities/expansions.
- AC04: pure denied I/O, input equality, capture file changes after remote phase,
  malformed/version/hash/selection and credential negative cases.
- AC05: separate resource polarity, UNKNOWN/truncated coverage, foreign scope,
  unresolved owner boundaries and independent upstream selection/baseline forms.
- AC06: Root SOURCE_APPROVE806 plus accepted2df source/test and all46own XMLPASS.
  Currentec6a1272425+46own union2471 is2461PASS10same optionalSKIP on the one
  accepted2587PASS10SKIP descendant; collection-only, no new full/build. Independent
  current exact-pair review pending. See note95/validation/t016-descendant-proof.json.

## T017 — current-parent descendant-result transfer

- AC01: shuffled star input/selector sets, directions, cycle and timestamp controls
  in `tests/test_t017_filter_topology_scope.py` prove stable selection and fingerprints.
- AC02: max-nodes=1, zero hops and upstream truncation preserve exact known omission
  IDs/counts/frontier and PARTIAL/UNKNOWN; metadata overflow rejects the result.
- AC03: middle-node and Kafka-channel removal never creates a shortcut.
- AC04: input equality, explicit no-I/O sentinels, invalid selectors, cycles/depth,
  credential references and Unicode identity controls.
- AC05: full cross-context tuples, original context selection/baseline, AMBIGUOUS,
  STALE and contradicting/unknown provenance buckets remain unchanged.
- AC06: note97 preserves historical149pure/source evidence. All33own cases PASS
  on accepted2df, source/tests exact. Current130720f2471+33own=2504 IDs maps
  2494PASS10same optionalSKIP, collection-only/no new full/build. Root is original
  author; architect plus another independent final-pair approval mandatory.
  See validation/t017-descendant-proof.json.

## T018 — current-parent descendant-result transfer

- AC01: exact summary/candidate/filter-origin inventories; missing graph/ref boundary.
- AC02: missing range null, canonical range tamper rejected without invented lines.
- AC03: actual temporary files match/edit/delete across two repos, original hash/
  fingerprint preserved; stale context does not become CURRENT after file match.
- AC04: input equality, source-status tamper, denied pure I/O/projectors/process/
  network, confined symlink/traversal/foreign refs, bounds and credential controls.
- AC05: original evidence buckets/type/freshness, UNKNOWN remote realm/group and
  filtered ambiguity/omitted alternatives preserved; no new availability proof.
- AC06: note98 retains historical RED/pure/source evidence. Owned source/tests
  exact299/accepted2df; all59own XMLPASS. Current4e4fcd6 base2504+59own=2563 IDs
  maps2553PASS10same optionalSKIP on the oneaccepted2587PASS10SKIP descendant;
  collection-only, no new actual/full/build. Current exact-pair independent review
  remains pending; see validation/t018-descendant-proof.json.

## T019 — current-parent exact descendant-result transfer

- AC01–AC02: public JSON interfaces/topology/explain; exact full filter envelope, selectors and fixed diagnostics.
- AC03: missing/corrupt original indexes fail before capture; temporary-file explicit capture leaves source/index bytes unchanged.
- AC04: invalid JSON, privacy, cancellation, pipe, conflict, bounded output, strict partial and source-status replay controls.
- AC05: legacy CLI smoke and documentation; coalesced 307 PASS / 10 actual deselected in 5.29s.
- Accepted2df own34 XMLPASS, owned architecture_cli/global5CLI lines/tests exactabad.
  Current1005b9f2563+34own union2597 is the EXACT acceptedfull ID set,2587PASS10same
  optionalSKIP; all302present runtime/test/fixture/CI files exact. Collection-only,
  no new actual/full/build/tool mutation. Independent current final-pair review
  remains pending; see validation/t019-descendant-proof.json.

## W07/T014 cold invocation correction (note108)

Runtime869ab/metadata91ca retains normalization/VERSION2 and adds the fresh-process
public T014 I/O audit regression. Pure25PASS is source-specific protocol evidence.
Continuation006 is terminal1176PASS/1typedWindowsSKIP, with source304 historical
1561PASS/9typedSKIP yielding source-corrected2747:2737PASS/10optionalSKIP.
This is not a fresh single full. All102 affected prior W07/T014 IDs were rerun.
The exact current-main publication subset2598 is2588PASS/10SKIP, with every ID's
actual source/origin/XML/phases retained. Runtime/test source is exact91ca;
main CLI three formatter bindings and main workflow remain main-owned instead of
renderer additions. External SVG15+4 proof is complete in the larger aggregate;
those149renderer IDs/features are outside this publication. Source/native/pins
and1364kindroots/94333entries are unchanged; old failures remain preserved.
Final architect+resume_t010 exact-pair reviews are PENDING. Root authored this fix
and acts only as execution/merge guard. See note108 and the per-ID terminal ledger.

## T020 — Markdown renderer, pre-staging source candidate

| AC | Concrete public check | Evidence status |
|---|---|---|
| AC01 | Golden decoded IDs/status/context, internal anchors and explicit generated/contract file capture | Historical compatibility176PASS6.59s; corrected renderer49PASS1.24s |
| AC02 | Real GFM AST hostile label/escaped ID tests, fixed headings/table shapes/internal links | Focused GREEN |
| AC03 | Empty scope retains UNKNOWN coverage reason and diagnostics | Focused GREEN |
| AC04 | Deep-input/sentinel equality, no renderer provider/I/O/process/network/store, CLI invalid/no-write/fingerprint | Expanded pure matrix GREEN |
| AC05 | Contradictory/stale evidence, contract revisions and Kafka realms/groups remain distinct; malformed/privacy/budget negatives | Focused GREEN |
| AC06 | Rev2/spec, note100, docs and dev parser lock | Source checkpoint review/full/upstream closure pending |


## T020 current-main publication transfer (2026-11-06)

Current parentfbb includes merged PR79–85; older checkpoint/review-pending entries
above are historical. T020 adds only interface Markdown: topology/explain stay
JSON-only, original286-line renderer and original49test source are preserved.
The source-corrected006 aggregate is2737PASS/10typedoptionalSKIP across2747IDs,
not a fresh single full. The T020 stage2647-ID subset is2637PASS/10typedSKIP.
Its49feature cases use48 assertion-equivalent aggregate cases and the original
unsupported topology-Markdown negative PASS on source446ddbe/metadataaa539.
The aggregate's same-ID topology-Markdown positive is T022 evidence, never the
T020 negative. Parser rejection route/entrypoint/helpers and original test body
are source-verified against that original execution; no new test was run here.
Current-main cold fix and all other APIs/CI jobs stay intact. Original249parent
capsules +three exactT020capsules=252; historical validation fields are unchanged.
Fresh scoped semantic CLI, source/global/ID proof and two-stage attribution are
recorded in /workspace/t020-publication-proof. Current T020 exact-pair independent
review/publication are pending; no T021/T022 code/capsules or wholeW09 claim.


### Current blocker — first-call renderer purity

Root's fresh ordinary CPython public-module invocation confirmed file-open I/O
inside `architecture_render._render`'s lazy `_safe_output` import (original
renderer SHAed93abfb9e4052ceef9a2aaf0b7ff2ecbed6be96db48a0948343aff97a00c8b7).
The original49 test result and2647 per-ID ledger remain source-attributed case
results, not closure of this newly uncovered first-call contract. Root RED receipt:
`/workspace/t020-cold-purity-proof/receipt.json`. The initial payload-preparation
missing parser path is separate from the corrected confirmed importlib-open RED.
This checkpoint is HOLD/REQUEST_CHANGES pending separately reviewed corrective
source/regression/affected-result transfer. No corrective code or new execution
was performed here; no final readiness or pure first-call support is claimed.


## Aktuální oddělený T020 checkpoint — 2026-11-06

Base je ověřený cold main `fbb0957`; pouze interface Markdown, nikoli Mermaid
ani topology Markdown. Původní 49 test bodies z aa539 zůstává beze změn; přidána
jedna přijatá first-call cold regrese. Schválená korekce109 extrahuje pouze původní
helpery do architecture_render_common a přesouvá existující importy do module scope
v rendereru/CLI/inspection; algoritmy, limity, veřejná exception a JSON zůstávají.
Historický HOLD výše je uzavřen korekcí, nikoli zpětným přepsáním starých důkazů.

Přijatý pokračovací běh007v2 na `41b9a454`: 152 PASS / 0 SKIP a 19 actual SVG.
Celková SOURCE_CORRECTED evidence je 2740 PASS + 10 typed optional SKIP / 2750;
nejde o nový jediný full běh. Oddělený T020 ledger má přesně 2648 IDs =
2638 PASS + 10 typed optional SKIP: 2598 parent + 50 T020. Původní unsupported
[topology] negative čerpá výhradně skutečný původní446/aa 49PASS receipt;
pozdější combined same-ID positive jej nedokládá. Ostatní47 původních případů
a specialized [explain]/path-error odpovídají přijatým cestám; nový cold případ
má exact41b9 AST. Source/global/per-ID proof je externě v
`/workspace/t020-corrected-publication-proof`. Native630 artefakty ani tools se
nemění; žádný nový test, collection, parser/SVG, preflight, build či full nebyl
pro tento isolated head spuštěn. Nezávislé finální review a publication PENDING.
T021 následně přidá Mermaid; T022 topology Markdown až ve vlastním odděleném PR.


## Aktuální stage ověření — 2026-11-06

Testovaný runtime/source checkpoint `fc6f58f997281e9dee871ae9ab61a90ddaea4578`:
jediná current-stage collect-only kontrola přesně 2648 unique IDs, bez module
skip/missing/extra; následný autorizovaný narrow běh **85 PASS / 0 SKIP, 14.05s**
(50 T020, 34 T019, jedna T014 first-call cold public regrese). Původní unsupported
topology-Markdown negative i explain/path-error nyní skutečně prošly na current
stage; původní446/aa receipt i pozdější combined positive historie zůstávají.
Před/po všech306 source/build/test inputs a čistý HEAD přesné; read-only parser
162regular-file/184total-member kind/hash/membership přesný proti accepted007v2. Cacheoff/PND1, mandatory
Markdown parser, maxfail1, vlastní tmp; žádný nový native/browser/SVG/build/full.

Aktuální per-ID SOURCE_CORRECTED union **2638 PASS + 10 typed optional SKIP /2648**
obsahuje85 skutečných current-stage řádků a2563 dříve přijatých source-qualified
řádků. Není to fresh2648 full. Raw XML, commands, collect a před/po guards i přesné
source-attribution řádky jsou v `/workspace/t020-corrected-stage-validation`;
receipt SHA256 `4256910e7b59ac67c396fa20751ed88235b4b2d7c779c1503bb95e41a1f72696`.
Finální metadata head je následník téhož testovaného runtime; nezávislé FINAL
review Root+resume10 před publikací čeká. GH CI neověřené/doplňující; žádný push,
PR ani merge nebyl proveden. Závislosti T013/T019 a cold main PR85 jsou sloučené;
T021/T022 nejsou součástí tohoto stage. AC01–05 dokládá původních49+novýcold
current-stage případ, CLI JSON/Markdown/fixed-error kontrakty dalších34T019;
AC06 čeká na finální review a samostatnou publikaci.

Finální integrační baseline 2026-11-05: `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d`, včetně nového remote contract mapping. Skutečný nový plný dostupný pytest běh: **1231 PASS /1055 SKIP**, 60 subtests PASS, bez selhání (42,98 s). Cílená sada T046/context/feature/Thymeleaf/remote mapping: **179 PASS /10 SKIP**, 51 subtests PASS (5,23 s). Toolchain SKIP nejsou PASS; worker/package data zůstávají identická s tímto main. Historické výsledky nad9eec zůstávají oddělenou evidencí. Nezávislé review a publikace se ověřují nad novými přesnými SHA.


T046 integrace 2026-11-06 nad `250e7c16250a97b9f8df5256b9894c8119dc64d9`: plná dostupná pytest sada **1577 PASS /1056 SKIP**, 60 subtests PASS, bez selhání (60,33 s). Cílená sada včetně architecture CLI: **229 PASS /10 SKIP**, 51 subtests PASS (16,01 s). Oba CLI dispatchery zůstávají aktivní. Skips nedokládají nepřipravené compiler/build/Windows toolchainy. Předčasný běh před dokončením snapshotu byl přerušen a nezapočítává se; uvedený výsledek pochází z následného dokončeného běhu. GitHub publikace/review/merge se ověřují odděleně.


### T046 — integrační evidence f115 (2026-11-06)

- T046-S01: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/56_addDeliveryReferences.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.
- T046-S02: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/57_addArtifactTemplates.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.
- T046-S03: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/58_addExistingFunctionTests.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.
- T046-S04: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/59_verifySyntheticTestData.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.
- T046-S05: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/60_enforceOptionalLocalApprovals.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.
- T046-S06: [konkrétní změny, dokumentační dopad a skutečné kontroly](changes/61_integrateDeliveryWorkflow.md). Při předání PR_OPEN; Python VERIFIED_IN_SCOPE, volitelné toolchainy SKIP/NOT_RUN.

## T049 — oddělení cílových agentů (2026-11-11)

[Scénáře AC01–AC12 a jejich ověření](tasks/49_separateTargetAgents.md) jsou PLANNED / NOT_RUN. Při implementaci přidej ke každému dodanému AC důkaz, SHA, verzi hostitele a skutečný výsledek.

## T003-S07-W03 — field a explicitní mapping flow

Dodání MERGED na `ec05a329fe2e51dbfe0eb47888bed037a251b8bf`, 2026-11-15
([PR104](https://github.com/p-rum/kgmaker/pull/104)), ověření omezené na
`field-mapping-1`, nikoli celé T003-AC07. Integrační běh nad `1f2acec0`: 166 PASS /
0 SKIP, 67.84 s; nezávisle 166 PASS / 0 SKIP, 68.33 s. PR105 zachovává jeho source
obsah, tuto sadu znovu neopakuje.
Přesné příkazy/výsledky: [change124](changes/124_fieldAndMappingFlow.md).

| Acceptance | Ověření | Konkrétní důkaz |
|---|---|---|
| T003-S07-W03-AC01 | VERIFIED_IN_SCOPE | `test_public_manual_and_actual_generated_mapper`, `test_source_provenance_and_generated_origin_are_captured`: skutečný Javac/JDK21 a MapStruct1.6.3, public fields i getter/identity/setter, source SHA/ranges |
| T003-S07-W03-AC02 | VERIFIED_IN_SCOPE | `test_legacy_schema_has_no_invented_compiler_mapping` v1/v2/v3, store roundtrip/offline scan, workspace kvalifikace |
| T003-S07-W03-AC03 | VERIFIED_IN_SCOPE | `test_unknown_business_transform_dispatch_recursion_and_aliases`, invalid actual compiler response, timeout/cancel orchestrace, source/version STALE, nulové implicitní procesy SOURCE_ONLY |
| T003-S07-W03-AC04 | PARTIAL | [Podporovaná matice](field-mapping.md), skutečná [fixture](../fixtures/field-mapping/README.md), lokální targeted regrese; full/GH CI NOT_RUN |

## T037 — invalidace odvozených pohledů (2026-11-15)

Delivery MERGED na `b1a8ba1f4234cd399de8319fcf5cde2c670dac26`
([PR103](https://github.com/p-rum/kgmaker/pull/103)); ověření PARTIAL v
dokumentovaném scope. HEAD `03aaf0d` má nezávislé APPROVE a 298 PASS / 0 SKIP,
21.57 s. [Zadání](tasks/T-037_invalidate-derived-views.md),
[API](view-cache.md), [change121](changes/121_invalidateDerivedViews.md).

| Acceptance | Ověření | Přímý test / limit |
|---|---|---|
| T037-AC01 | VERIFIED_IN_SCOPE | `test_dependency_mutations_force_rebuild_without_reusing_cached_approval`: service, contract, context, rule, annotation a workspace mapping changes způsobují miss; T032 review test doloží APPROVED→NEEDS_REVALIDATION. |
| T037-AC02 | VERIFIED_IN_SCOPE | `test_negative_lookup_new_provider_and_unrelated_edit_invalidate_conservatively`: přidaný dříve chybějící provider znovu spouští builder; celý snapshot je konzervativní invalidation boundary. |
| T037-AC03 | VERIFIED_IN_SCOPE | `test_mutation_refresh_matches_independent_full_rebuild` testuje create/edit/delete/rename proti nezávislému builderu, bez cache readback. |
| T037-AC04 | VERIFIED_IN_SCOPE | `test_invalid_inputs_and_builder_failure_leave_input_and_last_valid_artifact_unchanged`, corrupted cache, stale builder, mid-build dependency drift a symlink negatives zachovávají poslední validní artefakt. Oprava review navíc dokládá `test_cli_rejected_request_preserves_inputs_and_cache`, `test_cli_late_output_failure_never_publishes`, `test_cli_failed_atomic_publication_preserves_files_and_removes_temporary_paths`, input/source alias matice a `test_snapshot_wrapper_detects_original_input_mutations`; původní snapshot se kontroluje i při odložené publikaci. |
| T037-AC05 | VERIFIED_IN_SCOPE | Scope/context cache isolation, exact ViewDocument round-trip a test no approval/runtime evidence in cached topology; limity/truncation se kopírují beze změny v T016 view. |
| T037-AC06 | PARTIAL | README, architecture/API, CLI příklad, progress, acceptance row a [český change note](changes/121_invalidateDerivedViews.md) jsou aktualizované; první nezávislé review REQUEST_CHANGES bylo opraveno ve třech samostatně evidovaných krocích change121. PR103 je MERGED po nezávislém APPROVE integračního HEAD 03aaf0d; full suite a remote CI NOT_RUN. |

Původní checkpoint `43d7010` historicky uváděl 22/244 passed; jeho review přesto
odhalilo mezery AC04 a sémantické evidence. Po opravách obsahuje T037 modul 74
případů a stejná cílená view/provider/dependency sada má **296 passed in 10.96s**.
Po doplnění cleanup při přerušení zápisu prošel přímo dotčený T037 modul
**76 passed in 4.65s**; přesné příkazy, základní
dependency evidence a neprovedené kontroly viz change121. Není to full pytest,
actual runtime/toolchain ani úplná T004/produkční acceptance.

Nový integrační běh T037 po merge main `9f88d846`: **298 PASS / 0 SKIP,
11.07 s** v sedmi modulech uvedených v change121. Source identity vůči oběma
reviewovaným rodičům PASS; runtime/W06 sady se tímto výsledkem znovu nedokládají.

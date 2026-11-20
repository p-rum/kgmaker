# Ověřování compiler evidence při explicitní inspekci

Úkol [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md), incident
[#116](https://github.com/p-rum/kgmaker/issues/116). Zdrojová baseline
`465b121992aad50c2885acef0fd038531a31293a`; merge #114
`7c6a3dda821b55a4de6718f09504de4a861f47ae`. Aktuální cílový ref při ověření
`8f362471a8254ff9a0e44870c490a1dcb6b067b1`.

## Kroky 1 a 2 / T003-S10-W01-AC01, AC02, AC03

Spolu s kandidátem replay se v indexu ukládá i jeho digest. Vlastník
původního grafu mohl uložit nepodloženou hranu a validátor přijal strukturálně
konzistentní změnu se správně přepočteným digestem. Zdrojem pozorované chyby
byl [cache reader](../../src/kgmaker/extraction_cache.py). Merge provider
navíc dříve preferoval uložený záznam evidence při shodě ID.

## Kroky 3 a 4 / T003-S10-W01-AC01, AC02, AC03

Každá explicitní inspekce provede `worker-analysis`, projekci grafu a v JVM
framework augmentation. Před publikací stále kontroluje vstupy, timeout a zrušení.
Čerstvý důkaz vybraného kontextu má při shodě ID přednost. Formáty grafu v1–v3,
envelope v1 a existing scope/selection zůstávají kompatibilní.
[Přehled kontraktu](../stage-content-cache.md).

Příklad `kgmaker inspect code --root ./service --module core --source-set main`
hlásí pro standardní fáze `BYPASS/UNVERIFIED_REPLAY`. Opakovaný příkaz i se
stejnými vstupy znovu spustí práci. Pozdější samostatný krok může obnovit
výkon s nezávisle ověřitelnou provenance. Záznam dříve publikovaný pro jiný
kontext může vyžadovat novou explicitní inspekci tohoto kontextu.

- RED — `pytest -o pythonpath=/tmp/kgmaker-t047-oracle/src -p no:cacheprovider -q --tb=short tests/test_stage_content_cache.py tests/test_graph_provider.py -k 'rehashed or explicit_context_refresh_replaces'`
  nad původním Python modulem selhal ve všech čtyřech reprodukcích. Kontroly
  zahrnují worker coverage, compiler/graph, framework/graph a precedence evidence.
- PASS — JDK 21.0.13.1, skutečný Kotlin 2.1.10 K1 a K2 build pomocí
  `workers/jvm/build.py` nad připnutými lokálními deps. Připravený TypeScript 5.7.3.
- PASS — `KGMAKER_REQUIRE_WORKERS=1 python -m pytest -p no:cacheprovider -q tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py tests/test_argument_parameter_flow.py tests/test_graph_provider.py`,
  97 PASS, 0 SKIP. Součástí jsou fresh cold/warm, classpath/config, guardy store,
  zachování poslední validní generace a nulové spuštění workerů při offline refresh.
- `git diff --check` PASS. Publikované PR review a GH Actions NOT_RUN.

## Krok 5 / T003-S10-W01-AC04

Upřesněny [README](../../README.md), [compiler CLI](../compiler-inspection.md),
[matice](../production-analysis-progress.md) a [acceptance](../acceptance-inventory.md).
Vztah k registru, CLI argumenty, schema a init zůstávají kompatibilní.
T003-S10-W02 až W06, výkonový HIT a produkční availability nejsou doloženy
tímto během. Úplná sada a publikovaná dvojice SHA mají samostatné ověření.

## Revize po úplné sadě / T003-S10-W01-AC03 a AC04

Úplný běh `python -m pytest -p no:cacheprovider -q --tb=short` s JDK21 na
původním draft HEAD skončil **3127 PASS, 429 SKIP, 7 FAIL, 40 ERROR** za
1732.92 s. 42 případů použilo nefunkční `/snap/bin/kotlinc`, jedna
Mermaid fixture neměla připnutý parser a Gradle 4.4.1 nemohl otevřít lokální
socket. T025 nezávisle reprodukoval chybu nullable CFG refs, která má
samostatnou opravu v [#122](https://github.com/p-rum/kgmaker/pull/122).

Dva Spring K1/K2 případy ověřily očekávanou diagnostiku pro symbol z jiného
kontextu. Kontrola symbolu nyní vrací původní `Dangling/duplicate compiler symbol or context`
s `INVALID_PROTOCOL`. Ostatní metadata workeru mají vlastní diagnostiku.
Kontrola je pořád před projekcí a publikací. Opakovaný cílený běh s aktuálním
zdrojem potvrdil 97 PASS / 0 SKIP pro stack bez replay a oba actual Spring
context scénáře PASS. Baseline na uložené cache přeskočila změněnou worker
odpověď v osmi případech existujícího Spring testu a jeho negativní očekávání selhala.

Samostatný offline Gradle 8.13 exporter test byl po korekci prostředí PASS.
Běh s připnutým Kotlin 2.1.10 a parserem měl 55 PASS, 4 ERROR kvůli nepřipravené
dodatečné mixed Maven fixture. Tato čísla pokrývají opravné výběry; úplný nový
běh vyžaduje ověření na přesném integrovaném zdroji. GitHub Actions reportoval
failure s prázdnými kroky, provedení testů zůstává neověřené.

Zdrojový diff úplného běhu odpovídá původnímu GitHub HEAD
`db323d8729690bafabadd076b34c177f046e8e61`. Opravné výběry pro nové ověření

- `pytest -o pythonpath=/tmp/kgmaker-t047-oracle/src -p no:cacheprovider -q --tb=short tests/test_spring_registrations.py -k factory_invalid_context_and_timeout_preserve_store`
  — RED 8 FAIL na lokální baseline s replay. Stejný výběr bez přesměrování
  Python zdroje na baseline, s JDK21 a `JAVA_TOOL_OPTIONS="-XX:-UsePerfData -XX:ActiveProcessorCount=2"`
  — GREEN 8 PASS, 18 deselected. Souběžný pokus před omezením zátěže
  zaznamenal 4 PASS a 4 setup ERROR s neplatným JSON streamem workeru.
- `pytest -p no:cacheprovider -q --tb=short 'tests/test_exporter_distribution.py::test_installed_exporters_run_real_builds_outside_checkout[gradle]'`
  — 1 PASS s explicitním Gradle 8.13, JDK21 a lokální Gradle home mimo
  sandboxové omezení lokálních socketů. Test sám požaduje offline režim.
- `pytest -p no:cacheprovider -q --tb=short tests/test_default_body_mapping.py tests/test_dependency_dispatch.py tests/test_jvm_golden_corpus.py tests/test_unified_flow_views.py -k 'default_and_bridge_mapping or absent_sources_remain_bytecode_only or wrong_source_signature_never_maps_generated_body or nontrivial_bridge_body_stays_bytecode_only or foreign_default_impls_realm or test_scope_bytecode_never_claims_production_source or duplicate_class_bodies or same_realm_static_instance or static_facade_lookup or actual_inventory_and_unsupported_identity or inventory_rejects_missing_extra or actual_javac_public_formats_parser'`
  — 55 PASS, 4 ERROR mixed Maven, 143 deselected se skutečnými workery,
  Kotlin 2.1.10 a Mermaid 11.4.1. Před integrační regresí byla mixed fixture
  znovu zkompilována lokálně příkazem `mvn -o -DskipTests compile` (BUILD SUCCESS).

# Aktuální stav a zbývající práce


## T055 — Copilot skill pro migraci Excelu, 2026-11-25

Dodání MERGED v [#156](https://github.com/p-rum/kgmaker/pull/156) jako
`3a6b97fc9c44941e68bb390772a5eb13906bf1ff`. Ověření instalace a upgrade
skillu, lokální přípravy a Jira CSV zahrnuje skutečný Java 17 worker a
172 cílených PASS po review. Syntetický XLSM se načetl staticky bez
spuštění maker nebo IP spojení. Živý Copilot a import do Jira Cloud
zůstávají NOT_RUN.
[Zadání](tasks/55_automateExcelMigration.md) ·
[Návod](excel-migration.md#jeden-pokyn-pro-copilot) ·
[Doklady](changes/172_automateExcelMigration.md) · [Záznam sloučení a ověření](changes/174_reconcileMergedDelivery.md).

## T054 — analýza Excelu a Kotlin/JVM plán, 2026-11-25

Dodání MERGED v [#155](https://github.com/p-rum/kgmaker/pull/155)
jako `782ac6ac0287550084e9afadbd6182756fdd2730`. T054-S01–S02 mají
doložený statický rozsah se skutečnými XLSM, BIFF8 XLS a XLSX. Linux
wheel s JDK 17 a 137 cílených PASS patří k revizi po opravě vazeb názvů,
aliasů a limitů evidence. T054-S03–S04 zůstávají PARTIAL. Živý import do
Jira Cloud je NOT_RUN. Po sloučení prošel povinný Excel worker i wheel na
Windows v [přesném jobu #136](https://github.com/p-rum/kgmaker/actions/runs/45613808138/job/139203894219)
s nezměněnými Excel vstupy; jde o ověření dané fixture a distribuce.
[Cílové zadání](tasks/54_addExcelMigration.md) · [Návod](excel-migration.md) ·
[Evidence implementace](changes/171_addExcelMigration.md) · [Záznam sloučení a ověření](changes/174_reconcileMergedDelivery.md).

## T053 — správa instalace v cílovém projektu, 2026-11-24

Dodání MERGED v [#154](https://github.com/p-rum/kgmaker/pull/154)
jako `1e782a119e5ae54d22bfc8d7c22c565ed651815a`.
Doložený rozsah T053-S01–S04 / AC01–AC04 je VERIFIED_IN_SCOPE.
Původní samostatná PR větev: 129 PASS / 0 SKIP včetně instalovaného wheelu.
Review našlo ztracené vlastnictví legacy ignore při opakovaném init; oprava má
4 regresní RED → GREEN a 133 PASS / 0 SKIP na opravené PR větvi včetně wheelu,
viz doplnění change170.
Lokální integrační sada s připravenými T049-S08 fixture: 134 PASS / 0 SKIP. Init eviduje vlastnictví, `upgrade` aktualizuje
nezměněné templates a `uninstall` odstraňuje integraci i `.kgmaker/`.
Konflikty/dry-run/invalidní manifest a symlinky nezapisují; zachytitelná chyba
publikace obnoví původní soubory. Cizí soubory a ignore pravidla zůstávají.
Legacy rozpoznání má explicitní seznam otisků. Windows upgrade a uninstall,
živý reload hostitelů a crash atomicita jsou stále neověřené. T049-S01–S07
mají vlastní stav a ověření.
[Kontrakty a příklady](project-installation.md) ·
[Záznam kroků](changes/170_manageProjectInstallation.md) · [Záznam sloučení a ověření](changes/174_reconcileMergedDelivery.md).



## T052 — první běh dokončení 2026-11-19

Integrační baseline po ověřeném merge [#125](https://github.com/p-rum/kgmaker/pull/125)
je main `1532f1725f2cbe0d76685c273adc32c2e0d239e0`. T052 runtime zaznamenal
skutečný retry, dvojí nezávislé schválení a dokončený merge podle T045.
[Záznam workflow a evidence](changes/134_addCompletionOrchestrator.md).

T052-S02 / AC02 řeší obnovu dlouhého packetu pro T047-S01. Předání lze
zopakovat s explicitním rozpočtem; uložený profil i review packet zůstávají
stejné. Ověření opravy `VERIFIED_IN_SCOPE`, 99 zaměřených testů PASS / 0 SKIP.
Úplná sada NOT_RUN. Dodání opravy sleduje [#133](https://github.com/p-rum/kgmaker/pull/133).
[Regresní důkazy](changes/148_resumeCompletionPacketBudget.md).

Při zahájení běhu měl GitHub `main` ref `8f362471a8254ff9a0e44870c490a1dcb6b067b1`.
První lokální worktree používaly `465b121992aad50c2885acef0fd038531a31293a`,
tedy obsahu sloučené cache před přidáním `.github/workflows/pr-review.yml`.
Původní checkout a lokální změny T021 nebyly použity pro zápis.

[#127](https://github.com/p-rum/kgmaker/pull/127) sloučil na stejném páru revizí čtyři opravy compiler evidence. Úplná
lokální sada má 3644 PASS a jeden Windows SKIP. [výsledek integrace](changes/143_recordCompilerIntegrationMerge.md).

| Položka | Worktree nebo PR | Obnova a další krok |
|---|---|---|
| T052 | integrační zdroj `/tmp/kgmaker-t052-after-125`, runtime `/tmp/kgmaker-t052-completion`, [#120](https://github.com/p-rum/kgmaker/pull/120) | Ve skutečném runtime rootu načti `task:937d2fe76e4c93c0c8da6d1646ee72a9b5485516de6204536d6666639aa017f1` (review, iterace 1). Původní `task:058150b3297f150a629c14290f22e6cd269c757cbf5c20bb09720786fdb78189` tam zůstává BLOCKED po retry cap. [Záznam změny](changes/134_addCompletionOrchestrator.md). |
| T003-S10-W01 | `/tmp/kgmaker-cache-replay`, [#116](https://github.com/p-rum/kgmaker/issues/116), [#119](https://github.com/p-rum/kgmaker/pull/119) | `task:0353f35d68c7fae0847bb8ae1ac29a40205ba47986cddee556a10b1eac1e3798`. Head `4cad2ca2eb77d7f267d806fd0cc39aa7a9dcdcbb`, 97 PASS / 0 SKIP se skutečnými K1/K2/TS workery a 8 Spring fail-closed PASS. Selhání úplné sady před druhou revizí je evidováno v úloze. Bezpečnostní oprava je sloučena v [#127](https://github.com/p-rum/kgmaker/pull/127). W02/W06 mají vlastní acceptance a #116 zůstává otevřené pro ověření HIT. |
| T021 | [#123 MERGED](https://github.com/p-rum/kgmaker/pull/123), `61a554174b1c23257878fffae0e125f146223d79` | Runtime `/tmp/kgmaker-t021-17e9`, `task:ad6b0500b2aceac8040a8a695c43993827d9fa571f9a49108f563b16a49bef7b` je done/2. Úplná sada 3672 PASS a 1 Windows SKIP mimo T021. Nezávislé T045 ověřilo skutečný Mermaid a rodiče merge. [Doklad integrace](changes/146_recordTopologyMerge.md). |
| T047-S01 | [#121 MERGED](https://github.com/p-rum/kgmaker/pull/121), `b3bbba43304f499f96950ea4ecc2a2467919e616` | Přesný kandidát má 135 PASS, 0 SKIP a jeden očekávaný strict XFAIL pro T047-S02 se skutečnými K1/K2, TypeScriptem a offline Gradle. Výběr na sloučeném stromu má 7 PASS a stejný očekávaný XFAIL. T047-AC01 zůstává PARTIAL. [Doklad integrace](changes/161_recordMutationCorpusMerge.md). |
| T025 | Runtime `/tmp/kgmaker-t025-projection`, integrační zdroj `/tmp/kgmaker-t025-after-t052`, [#122](https://github.com/p-rum/kgmaker/pull/122) | V runtime rootu načti `task:8c0f8a08011df6992b001f26fc3df81ef9021a730e95d10097930b92c2faa101` (test, iterace 0). Přenos na main `8ff2529` má 113 PASS / 0 SKIP se skutečnými K1/K2. Sloučeno společně s W05 v [#127](https://github.com/p-rum/kgmaker/pull/127). |
| T046-S03 / #91 | [#125 MERGED](https://github.com/p-rum/kgmaker/pull/125) | 103 cílených PASS a ověřená T045 integrace `1532f172`. Runtime úloha je done. [Skutečný review doklad](https://github.com/p-rum/kgmaker/pull/125#issuecomment-7040630121). |
| T003-S07-W05 | [#126](https://github.com/p-rum/kgmaker/pull/126) | Vadný owner context vyvolal TypeError v baseline. Oprava a aktualizované fixture mají 240 PASS / 0 SKIP, [#127](https://github.com/p-rum/kgmaker/pull/127) prošel přesným T045 a byl sloučen. |

Otevřený [#4](https://github.com/p-rum/kgmaker/pull/4) je historický draft bez
unikátního patche. [#90](https://github.com/p-rum/kgmaker/issues/90) odkazuje na
již sloučený #42. První merge parent diff README zachoval dotčené sekce a nahradil jeden souhrn T046. První publikovanou změnou tohoto běhu byl původní draft #119. Při obnově čti worktree a task přes `kgmaker task show`, ověř
current refs přes GitHub connector, spusť nový plán a doplň výsledky.

## Post-merge integrace PR97 — 2026-11-15

W05 je MERGED v `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea`; skutečný první merge parent je `6eb755ec1d4e777abe8d34dea7bee9477c90692f`.
Nový čerstvý full nad tímto sloučeným main: **2318 PASS /481 SKIP /0 FAIL /0 ERROR**.
Původní branch full2264/481 jej nenahrazuje.
[Postup, oprava base ověření a limity](changes/119_reconcileJpqlDelivery.md).
T003/T004 i verification scope níže zůstávají částečné.

## Propojené workflows T051 — 2026-11-15

Baseline `6790b0e0a930089924c61c3f8a6b3aef1d44121c`,
[zadání](tasks/51_connectProjectWorkflows.md), [change118](changes/118_connectProjectWorkflows.md),
[uživatelský průchod](project-workflows.md). [PR #99](https://github.com/p-rum/kgmaker/pull/99) je MERGED do main jako `6eb755ec1d4e777abe8d34dea7bee9477c90692f`; závislost #98 je MERGED. Historická lokální evidence zůstává níže, aktuální integrace viz change119.

| Krok | Dodání | Ověření | Důkaz a omezení |
|---|---|---|---|
| T051-S01 | MERGED | VERIFIED_IN_SCOPE | Striktní JSON profily, builtins, read-only CLI; nulová mutace a ukázkový profil v cílených testech PASS |
| T051-S02 | MERGED | VERIFIED_IN_SCOPE | V3 snapshot/context/handoffs, v1/v2 regrese, stale test/review a plný CLI průchod PASS; evidence LOCAL_DECLARED |
| T051-S03 | MERGED | PARTIAL | 103 cílených testů PASS, čistý wheel smoke PASS, instrukce/docs; nové review po retargetu dle PR, živí hostitelé NOT_RUN; GH CI neověřené |

Pevné fáze, bez runneru/DAG/automatických trace vazeb. Fingerprint používá existující
source_inventory s jeho výlukami; viz příručka. T049 a produkční acceptance nejsou uzavřené.

Oprava zdrojové čerstvosti T051-S02 používané T052 je sloučena v [#151](https://github.com/p-rum/kgmaker/pull/151)
jako `b04d064a6147436adc751f5fffa4a219b8f8c16e`. Po #136 prošlo
208 cílených testů bez přeskočení. Skutečné XLSX, šifrované XLSX a legacy
XLS z fixture T054 ověřují shodu inventáře a indikátoru čerstvosti po
změně bajtů. Výsledek platí pro zdrojové otisky role packetu.
[Rozsah a důkazy](changes/167_useCanonicalPacketSourceSnapshot.md) ·
[Záznam sloučení](changes/174_reconcileMergedDelivery.md).


## Skilly v cílovém projektu T050 — 2026-11-15

Baseline `193c89b4d461047fd3330fd74892c5830ba8ac81`,
[zadání revize 1](tasks/50_addTargetProjectSkills.md),
[change117: přesné kontroly a omezení](changes/117_addTargetProjectSkills.md).

| Krok | Dodání | Ověření | Důkaz a omezení |
|---|---|---|---|
| T050-S01 | MERGED | VERIFIED_IN_SCOPE | Pět skillů + tři references, init preflight, parity a ochrana uživatelských souborů; čistý wheel smoke PASS. Hostitelská discovery NOT_RUN; neuzavírá T049. |
| T050-S02 | MERGED | PARTIAL | 83 cílených testů PASS, 5 skill validací PASS; příklady prošly skutečnými validátory. Plná sada má environmentální/toolchain chyby, živé hostitelské scénáře a GH CI NOT_RUN. |

[PR #98](https://github.com/p-rum/kgmaker/pull/98) byl sloučen do main jako
`31a69bcf5b72c5f1f3be4ed699cc6b5672bcdcde` dne 2026-11-15. Historické lokální
výsledky výše se nepovyšují na celou produkční ani hostitelskou podporu.
Příručka: [agent-skills.md](agent-skills.md). T050 nemění delivery součty T003,
T004, T046 nebo T047 níže. Lokální soubory nejsou důkaz merge ani živé podpory hostitele.

## Integrační ověření T048-S02 / T046 — 2026-11-12

S01–S06 jsou sloučené; S06 zachovává historii a integrovalo main
`6dffe5e39fb847e5552f38e67b957e4b51b20bed` jako merge
`9bcf91db1d1349241f7e1f7114f74c0331c25802`. Dostupná regrese S06:
**1635 PASS /1055 SKIP**, 76 subtests PASS; cíleně **309 PASS /10 SKIP**,
67 subtests PASS. [Přesné příkazy a omezení](changes/61_integrateDeliveryWorkflow.md).
Delivery S06 je MERGED, Python VERIFIED_IN_SCOPE; GH CI bez kroků a úplná
compiler/build/Windows matice zůstávají NOT_RUN/SKIP. Nejde o dokončení T003/T004/T047.


## Aktuální pracovní inventář T048-S01 — 2026-11-07

Baseline: `f115aa4a1c37683f3be9e4607111d51d9c1301c1`. Audit zdrojů, git historie a GitHub PR; změna [111](changes/111_reconcileDeliveryStatus.md).
Řádky níže jsou jediným aktuálním delivery inventářem. Následující historické
checkpointy zachovávají původní výsledky a nepředstavují čekající merge již
sloučených funkcí. SPECIFICATION je stav zadání a zůstává oddělený od dodání.

| Skupina | MERGED | PLANNED | PR_OPEN | Celkem |
|---|---:|---:|---:|---:|
| T003 work packages | 49 | 10 | 1 | 60 |
| T004 / T005–T044 | 29 | 11 | 0 | 40 |
| T046 etapy | 6 | 0 | 0 | 6 |
| T047 kroky | 1 | 11 | 1 | 13 |
| Celkem (včetně sdílených kontraktů T047) | 85 | 32 | 2 | 119 |

T003/T004 mají podle níže uvedených atomických řádků 21 položek v `PLANNED`
a jednu v `PR_OPEN`.
W09 a S09-W05 jsou `MERGED`. Součet vyjadřuje evidovaný stav dodání.
T047 není dalších 13 nezávislých
implementací; sloupec omezení určuje upstream vlastníky. `PARTIAL` znamená nalezený
kód/testy a historicky doložený subset; celý dnešní rozsah nebyl znovu spuštěn.
`NOT_RUN` nikdy nepřebírá PASS z popisu PR. T046-S01 až S06 jsou v `main`; jejich
řádky uvádějí přesné reviewované head a merge SHA. U plánovaných položek jsou
uvedeny existující body rozšíření, nikoli důkaz dodaného chování. SHA označuje
merge/integrační checkpoint, u nedodaných položek auditovanou baseline; nenahrazuje
testový receipt.

Po baseline T048 `250e7c1` byly kromě dokumentačních instrukcí sloučeny také
T046-S01 až S06 a přibylo zadání T049; jejich přesné SHA jsou v atomických řádcích.
T020 je MERGED v PR87. Výchozí formát topology a explain je JSON. T021 má upstream T003-S07-W09 v PR109 a je sloučené v #123. T031 a T032 jsou sloučené.
Oprava čtení normalizovaného kontextu T032 je od 2026-11-21 v main přes [#132](https://github.com/p-rum/kgmaker/pull/132).
[Doklad integrace](changes/152_recordNormalizedProcessReviewMerge.md). T034 procesní CLI zůstává PLANNED.

### Atomické položky

| ID / zadání | Dodání | Ověření | Evidence SHA | Zdroj / test | PR | Omezení / další krok |
|---|---|---|---|---|---|---|
| [T003-S03-W01](tasks/T003-S03-01-externalToolchainSelection.md) | MERGED | PARTIAL | `a39a24dde36ab104cf3d3f7dd07ef3a19f9d04cf` | [src/kgmaker/build_model.py](../src/kgmaker/build_model.py), [src/kgmaker/build_runner.py](../src/kgmaker/build_runner.py), [workers/build/maven/BuildExport.java](../workers/build/maven/BuildExport.java), [tests/test_build_runner.py](../tests/test_build_runner.py) | [# 9](https://github.com/p-rum/kgmaker/pull/9) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S03-W02](tasks/T003-S03-02-gradleCustomVariants.md) | MERGED | PARTIAL | `af5f70e767dedab80f7cb0c82926599022251965` | [workers/build/gradle/export.gradle](../workers/build/gradle/export.gradle), [src/kgmaker/build_model.py](../src/kgmaker/build_model.py), [src/kgmaker/classification.py](../src/kgmaker/classification.py), [tests/test_gradle_variants.py](../tests/test_gradle_variants.py) | [# 14](https://github.com/p-rum/kgmaker/pull/14) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S03-W03](tasks/T003-S03-03-gradleIncludedBuilds.md) | MERGED | PARTIAL | `a27885ea9e1b6614e782d97efe356af86a2b93da` | [workers/build/gradle/export.gradle](../workers/build/gradle/export.gradle), [src/kgmaker/build_model.py](../src/kgmaker/build_model.py), [src/kgmaker/build_runner.py](../src/kgmaker/build_runner.py), [tests/test_gradle_included.py](../tests/test_gradle_included.py) | [# 15](https://github.com/p-rum/kgmaker/pull/15) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S03-W04](tasks/T003-S03-04-kotlinCompilerOptions.md) | MERGED | PARTIAL | `3686eac6dea34441bfcff4df382753dd34d1ced7` | [src/kgmaker/build_model.py](../src/kgmaker/build_model.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [tests/test_kotlin_build_options.py](../tests/test_kotlin_build_options.py) | [# 16](https://github.com/p-rum/kgmaker/pull/16) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S03-W05](tasks/T003-S03-05-crossRepoArtifactMapping.md) | MERGED | PARTIAL | `f707d439765fcd22d202d425d639ba384af04e2b` | [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [src/kgmaker/build_model.py](../src/kgmaker/build_model.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [tests/test_cross_repo_artifacts.py](../tests/test_cross_repo_artifacts.py) | [# 17](https://github.com/p-rum/kgmaker/pull/17) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S04-W01](tasks/T003-S04-01-k2AnalysisApiBackend.md) | MERGED | PARTIAL | `eff0d3d5d7620b017fe42a65a54f672af8068667` | [src/kgmaker/worker_protocol.py](../src/kgmaker/worker_protocol.py), [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [tests/test_cross_repo_artifacts.py](../tests/test_cross_repo_artifacts.py), [tests/test_k2_backend.py](../tests/test_k2_backend.py) | [# 26](https://github.com/p-rum/kgmaker/pull/26) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S04-W02](tasks/T003-S04-02-defaultBodySourceMapping.md) | MERGED | PARTIAL | `33dc239a6d2eca2f42364a7b314aeb377e4b441a` | [src/kgmaker/callgraph.py](../src/kgmaker/callgraph.py), [tests/test_default_body_mapping.py](../tests/test_default_body_mapping.py) | [# 31](https://github.com/p-rum/kgmaker/pull/31) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S04-W03](tasks/T003-S04-03-coroutineSourceMapping.md) | MERGED | PARTIAL | `f2dad55c12c4fcf8af831cb3fff68e6ebbcf614f` | [src/kgmaker/control_flow.py](../src/kgmaker/control_flow.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [tests/test_coroutine_mapping.py](../tests/test_coroutine_mapping.py) | [# 37](https://github.com/p-rum/kgmaker/pull/37) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S04-W04](tasks/T003-S04-04-dependencyDispatchHierarchy.md) | MERGED | PARTIAL | `ec333966e657896382f310ef018835e3d696513e` | [src/kgmaker/callgraph.py](../src/kgmaker/callgraph.py), [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [tests/test_dependency_dispatch.py](../tests/test_dependency_dispatch.py) | [# 35](https://github.com/p-rum/kgmaker/pull/35) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S04-W05](tasks/T003-S04-05-jvmGoldenAcceptanceCorpus.md) | MERGED | PARTIAL | `02e2bbbceb0661f1c887020dbe47a61331d20698` | [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_jvm_golden_corpus.py](../tests/test_jvm_golden_corpus.py) | [# 52](https://github.com/p-rum/kgmaker/pull/52) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S05-W01](tasks/T003-S05-01-dynamicSpringImports.md) | MERGED | PARTIAL | `4113a7975451a8313321fd521252485c959908e3` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_spring_imports.py](../tests/test_spring_imports.py) | [# 30](https://github.com/p-rum/kgmaker/pull/30) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S05-W02](tasks/T003-S05-02-springRegistrarsFactories.md) | MERGED | PARTIAL | `c76f6dcfd38f0bfeed8c899535bcae5c5f3ccc8a` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_spring_imports.py](../tests/test_spring_imports.py) | [# 53](https://github.com/p-rum/kgmaker/pull/53) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S05-W03](tasks/T003-S05-03-springConditionMatrix.md) | MERGED | PARTIAL | `8b1eeceb28b71c122c2d48bf179e08cefa79c43c` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_spring_conditions.py](../tests/test_spring_conditions.py) | [# 34](https://github.com/p-rum/kgmaker/pull/34) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S05-W04](tasks/T003-S05-04-springProxyAsyncSemantics.md) | MERGED | VERIFIED_IN_SCOPE | merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [src/kgmaker/views.py](../src/kgmaker/views.py), [tests/test_spring_proxy_async.py](../tests/test_spring_proxy_async.py) | [# 95](https://github.com/p-rum/kgmaker/pull/95), [#127](https://github.com/p-rum/kgmaker/pull/127) | Exact-pair review finálního headu `44af09d36b69589fee882d017d22f07bdc2e3216` je čisté; historical actual-javac worker byl TOOLCHAIN_SKIP a runtime advice/scheduling zůstávají UNKNOWN. Kanonický `@Autowired` a negativní kontroly mají 15 PASS / 0 SKIP a samostatnou skutečnou kontrolu K1/K2. Dílčí oprava [#124](https://github.com/p-rum/kgmaker/pull/124) je součástí [společné integrace](changes/142_integrateCompilerEvidenceRepairs.md). Předchozí řádek evidoval `39eb46ba283e526d9748e80e2572f28b4f4348ed`. Přesné ověření viz [výsledek integrace](changes/143_recordCompilerIntegrationMerge.md). |
| [T003-S06-W01](tasks/T003-S06-01-kotlinJpaAccess.md) | MERGED | PARTIAL | `966948b533a7a9417dea370733f300f91fd2b61c` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [tests/test_k2_backend.py](../tests/test_k2_backend.py) | [# 32](https://github.com/p-rum/kgmaker/pull/32) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S06-W02](tasks/T003-S06-02-jpaInheritedAttributes.md) | MERGED | PARTIAL | `469e615b2766f78f27c11b85172d223b929cb031` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/domain.py](../src/kgmaker/domain.py), [tests/test_build_aware.py](../tests/test_build_aware.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py) | [# 39](https://github.com/p-rum/kgmaker/pull/39) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S06-W03](tasks/T003-S06-03-ormXmlOverrides.md) | MERGED | PARTIAL | `355e98fe2ab62fadbf4869eb4485cd3562173068` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/domain.py](../src/kgmaker/domain.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_orm_xml_overrides.py](../tests/test_orm_xml_overrides.py) | [# 50](https://github.com/p-rum/kgmaker/pull/50) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S06-W04](tasks/T003-S06-04-multiDatasourceRealms.md) | MERGED | PARTIAL | `9f6605db0258d1b27bf233e25c7737bf0b675f5b` | [src/kgmaker/domain.py](../src/kgmaker/domain.py), [src/kgmaker/schema_replay.py](../src/kgmaker/schema_replay.py), [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [tests/test_build_aware.py](../tests/test_build_aware.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py) | [# 62](https://github.com/p-rum/kgmaker/pull/62) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S06-W05](tasks/T003-S06-05-jpqlHqlGrammar.md) | MERGED | PARTIAL | `2bebab00c2ca368e3e5a6a4d7daa47fce2addcea` (head `ff31433eba0e180deb1df2b5f4aa8b76f3e690e0`) | [framework.py](../src/kgmaker/framework.py), [test_jpql_hql_grammar.py](../tests/test_jpql_hql_grammar.py), [change116](changes/116_parseExtendedJpqlHql.md), [post-merge change119](changes/119_reconcileJpqlDelivery.md) | [#97](https://github.com/p-rum/kgmaker/pull/97) | Bounded grammar a integrační opravy dodané. Původní branch full2264/481 a nové merged-main 2318 PASS /481 SKIP /0 FAIL /0 ERROR jsou oddělené receipty. Base-ověřovací chyba a dodatečný audit jsou transparentně v change119. W06/W07, další provider syntax a runtime SQL zůstávají PARTIAL/UNKNOWN. |
| [T003-S06-W06](tasks/T003-S06-06-namedQueryContainers.md) | MERGED | VERIFIED_IN_SCOPE | `9f88d8463b3c968592f0f1937736b752dfccee1d` | [framework](../src/kgmaker/framework.py), [named query decoder](../src/kgmaker/named_queries.py), [actual Javac fixture](../fixtures/named-queries/Model.java), [tests](../tests/test_named_query_containers.py), [change120](changes/120_namedQueryContainers.md) | [PR102](https://github.com/p-rum/kgmaker/pull/102) MERGED; source preserved in PR103 integration | Unique context-local annotation/XML catalog; repeatable containers, named/positional parameter checks, compiler projections, final XML native tables; SQL quoted spans/comments cannot invent table references, leading comments preserve UPDATE/DELETE intent; duplicates/missing/malformed remain unresolved. Integration with merged PR101: 205 targeted PASS / 0 SKIP (W06 117 + runtime 88), actual JDK21; provider/runtime and separate Kotlin corpus NOT_RUN. |
| [T003-S06-W07](tasks/T003-S06-07-criteriaSpecificationQuerydsl.md) | MERGED | VERIFIED_IN_SCOPE | `83999fb2e08c6d9d67449687c95b2217eee08b09` (approved `c57b57f`) | [criteria_queries](../src/kgmaker/criteria_queries.py), [actual tests](../tests/test_criteria_queries.py), [matrix](programmatic-queries.md), [change129](changes/129_criteriaSpecificationQuerydsl.md) | [PR111](https://github.com/p-rum/kgmaker/pull/111) | Bounded Java/Javac Criteria/Specification/QueryDSL equality a direct custom fragments; actual Jakarta3.1/SpringDataJPA3.4.2/QueryDSL5.1 APT. Dynamic/ambiguous/stale remains PARTIAL/UNKNOWN; Kotlin/provider/runtime outside scope. |
| [T003-S06-W08](tasks/T003-S06-08-schemaCompatibility.md) | MERGED | PARTIAL | `3bef611d0ed555e26e6663a0b243ce5a2bf1d428` | [src/kgmaker/schema_replay.py](../src/kgmaker/schema_replay.py), [src/kgmaker/domain.py](../src/kgmaker/domain.py), [src/kgmaker/availability.py](../src/kgmaker/availability.py), [tests/test_compiler_workers.py](../tests/test_compiler_workers.py), [tests/test_schema_compatibility.py](../tests/test_schema_compatibility.py) | [# 64](https://github.com/p-rum/kgmaker/pull/64) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S07-W01](tasks/T003-S07-01-argumentParameterFlow.md) | MERGED | PARTIAL | `1915ebf0be25cab4cb8b0836e2fce25b05c7b10f` | [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [tests/test_argument_parameter_flow.py](../tests/test_argument_parameter_flow.py), [tests/test_typescript_callback_limits.py](../tests/test_typescript_callback_limits.py) | [# 47](https://github.com/p-rum/kgmaker/pull/47) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S07-W02](tasks/T003-S07-02-returnConsumerFlow.md) | MERGED | PARTIAL | `deb3691c23de19064a9e9c0484cf6a62ab295592` | [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [tests/test_argument_parameter_flow.py](../tests/test_argument_parameter_flow.py), [tests/test_default_body_mapping.py](../tests/test_default_body_mapping.py) | [# 70](https://github.com/p-rum/kgmaker/pull/70) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S07-W03](tasks/T003-S07-03-fieldAndMappingFlow.md) | MERGED | PARTIAL | `ec05a329fe2e51dbfe0eb47888bed037a251b8bf` | [tests/test_field_mapping_flow.py](../tests/test_field_mapping_flow.py), actual Javac + MapStruct1.6.3 | [PR104](https://github.com/p-rum/kgmaker/pull/104) MERGED | Integrační běh 166 PASS / 0 SKIP, 67.84 s (163 W03 + 3 actual JVM integrační testy). Nezávisle zopakováno 166 PASS / 0 SKIP, 68.33 s. Omezený field-mapping-1 kontrakt a negativní matice; [change124](changes/124_fieldAndMappingFlow.md), [podpora](field-mapping.md). Celé S07 a produkční business ekvivalence nejsou uzavřené. |
| [T003-S07-W04](tasks/T003-S07-04-kafkaBindingIdentity.md) | MERGED | PARTIAL | `f6a6355192c9e2481c146e5214835c3d17172e5d` | [src/kgmaker/domain.py](../src/kgmaker/domain.py), [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [tests/test_kafka_code_bindings.py](../tests/test_kafka_code_bindings.py) | [# 69](https://github.com/p-rum/kgmaker/pull/69), [# 51](https://github.com/p-rum/kgmaker/pull/51) | Zaměřená kontrola kanonické reference a offline stárnutí na K1/K2 je v [change168](changes/168_assertQualifiedKafkaContext.md). Celá AC/toolchain matice zůstává neověřená. |
| [T003-S07-W05](tasks/T003-S07-05-kafkaRetryDlt.md) | MERGED | PARTIAL | merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [tests/test_kafka_retry_dlt.py](../tests/test_kafka_retry_dlt.py), [tests/test_mandatory_worker_ci.py](../tests/test_mandatory_worker_ci.py) | [#71](https://github.com/p-rum/kgmaker/pull/71), [#126](https://github.com/p-rum/kgmaker/pull/126), [#127](https://github.com/p-rum/kgmaker/pull/127) | Historické dodání #71. Na main se reprodukoval TypeError při neplatném `context_id`. Dílčí oprava #126 má 240 PASS / 0 SKIP a je součástí [společné integrace](changes/142_integrateCompilerEvidenceRepairs.md). Širší acceptance zůstává PARTIAL. Předchozí řádek evidoval `3e5ef0f0c56c406a5428e826120ca525774b373f`. Přesné ověření viz [výsledek integrace](changes/143_recordCompilerIntegrationMerge.md). |
| [T003-S07-W06](tasks/T003-S07-06-httpClientExecution.md) | MERGED | PARTIAL | `75d448ee7791cffb3dc9f4cceff5136402a8f5e0` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py), [tests/test_http_client_execution.py](../tests/test_http_client_execution.py), [tests/test_http_provider_privacy_integration.py](../tests/test_http_provider_privacy_integration.py) | [# 49](https://github.com/p-rum/kgmaker/pull/49) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S07-W07](tasks/T003-S07-07-crossServiceContractMapping.md) | MERGED | PARTIAL | `5ffe09952930a5a3e7a5d7b88a08560b7775ee9d` | [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [src/kgmaker/domain.py](../src/kgmaker/domain.py), [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py), [tests/test_cross_service_contract_mapping.py](../tests/test_cross_service_contract_mapping.py) | [# 76](https://github.com/p-rum/kgmaker/pull/76) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S07-W08](tasks/T003-S07-08-evidenceRanking.md) | MERGED | VERIFIED_IN_SCOPE | `8e7dff5b82597184662797c07a68e5ec460e9e0e` | [tests/test_evidence_ranking.py](../tests/test_evidence_ranking.py), actual Javac/JDK21 fixture | [PR106](https://github.com/p-rum/kgmaker/pull/106) | execution-2/impact-2, evidence contributions, lokalizované gaps/penalty, JSON/Markdown CLI; [change126](changes/126_evidenceRanking.md), [podpora](evidence-ranking.md). Celé S07 zůstává PARTIAL. |
| [T003-S07-W09](tasks/T003-S07-09-unifiedFlowViews.md) | MERGED | VERIFIED_IN_SCOPE | merge `cceb1109df6d88e4f46107f9f9ad12f5e563c0d3`; approved `999e60f` | [Unified flow capability](unified-flow-views.md), [change128 kroky12–14](changes/128_unifiedFlowViews.md) | [PR109](https://github.com/p-rum/kgmaker/pull/109) | Jednotný CFG model a tři formáty; caller/source proof guard, final429 + binding38 + T02859 PASS (překryv). Nezávislé review APPROVE a merge ověřeny; SOURCE_ONLY/legacy UNKNOWN, bounded async, full/GH CI NOT_RUN. |
| [T003-S08-W01](tasks/T003-S08-01-typescriptProjectReferences.md) | MERGED | PARTIAL | `1091330b67a7ff67db329ffbbb2eaba162313b3f` | [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [tests/test_typescript_project_references.py](../tests/test_typescript_project_references.py), [tests/test_worker_protocol.py](../tests/test_worker_protocol.py) | [# 28](https://github.com/p-rum/kgmaker/pull/28) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S08-W02](tasks/T003-S08-02-tsconfigPathsExclude.md) | MERGED | PARTIAL | `5430388a282f19f6c9637319c12a1731ae6d0674` | [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [tests/test_tsconfig_freshness.py](../tests/test_tsconfig_freshness.py) | [# 36](https://github.com/p-rum/kgmaker/pull/36) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S08-W03](tasks/T003-S08-03-typescriptCallbacksGenerics.md) | MERGED | PARTIAL | `3a7f76b00bb5136bbe5990546d9c8942a7f53f73` | [src/kgmaker/callgraph.py](../src/kgmaker/callgraph.py), [tests/test_typescript_callback_limits.py](../tests/test_typescript_callback_limits.py), [tests/test_typescript_callback_projects.py](../tests/test_typescript_callback_projects.py) | [# 46](https://github.com/p-rum/kgmaker/pull/46) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S08-W04](tasks/T003-S08-04-versionedUiEvents.md) | MERGED | PARTIAL | `081d69ca69d14b4d131cc305e4e5c873960e71a3` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py), [tests/test_tsconfig_freshness.py](../tests/test_tsconfig_freshness.py), [tests/test_ui_events.py](../tests/test_ui_events.py) | [# 61](https://github.com/p-rum/kgmaker/pull/61) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S08-W05](tasks/T003-S08-05-backendFrontendValueFlow.md) | MERGED | VERIFIED_IN_SCOPE | merge `7bb8b8d`; head `61f1d6c` | [frontend_flow.py](../src/kgmaker/frontend_flow.py), [actual fixture/tests](../tests/test_backend_frontend_value_flow.py), [capability](backend-frontend-value-flow.md) | [#107](https://github.com/p-rum/kgmaker/pull/107) | Actual Javac21/TS5.7.3/React18 compiler occurrence path through explicit contract hash/release/generation. Await/local-const scope only; reference alias mutation/escape invalidates the origin, and v1-connected facts require valid markers/endpoints. STALE cache entries reload the original explicit index, so exact restored dependency bytes can recover current proof without inspection. Review fixes are tracked against1550978 in change125. SOURCE_ONLY and unsupported callbacks remain PARTIAL/UNKNOWN, no runtime proof. [change125](changes/125_backendFrontendValueFlow.md) |
| [T003-S09-W01](tasks/T003-S09-01-xlsxAdvancedReferences.md) | MERGED | PARTIAL | `a39a24dde36ab104cf3d3f7dd07ef3a19f9d04cf` | [src/kgmaker/workbooks.py](../src/kgmaker/workbooks.py), [src/kgmaker/analysis_validation.py](../src/kgmaker/analysis_validation.py) | integrováno přes feat/impl; viz SHA | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S09-W02](tasks/T003-S09-02-binaryXlsDiagnostics.md) | MERGED | PARTIAL | `35033096e8a2ea5d74ae8d2195a7b27d22c7590a` | [src/kgmaker/workbooks.py](../src/kgmaker/workbooks.py), [src/kgmaker/data_check.py](../src/kgmaker/data_check.py), [tests/test_binary_xls.py](../tests/test_binary_xls.py) | [# 21](https://github.com/p-rum/kgmaker/pull/21) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S09-W03](tasks/T003-S09-03-templateDialectExpansion.md) | MERGED | PARTIAL | `2b0cf353c31f88c0c0226cf415585433843187f2` | [src/kgmaker/templates.py](../src/kgmaker/templates.py), [src/kgmaker/framework.py](../src/kgmaker/framework.py), [tests/test_templates.py](../tests/test_templates.py) | [# 38](https://github.com/p-rum/kgmaker/pull/38) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S09-W04](tasks/T003-S09-04-approvedMethodologyConflicts.md) | MERGED | PARTIAL | `aa9e64bbec0bfea4bf143824dcc3d8ddf5cd6533` | [src/kgmaker/availability.py](../src/kgmaker/availability.py), [src/kgmaker/feature.py](../src/kgmaker/feature.py), [src/kgmaker/analysis_report.py](../src/kgmaker/analysis_report.py), [tests/test_methodology_conflicts.py](../tests/test_methodology_conflicts.py) | [# 8](https://github.com/p-rum/kgmaker/pull/8) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S09-W05](tasks/T003-S09-05-completeAnalysisReport.md) | MERGED | VERIFIED_IN_SCOPE | `9c86d29fc267014e2bee4b197c7692f17a1cda93` (approved `edb5cff`) | [Report capability/CLI](complete-analysis-report.md), [actual fixture](../tests/test_complete_analysis_report_actual.py) | [PR112](https://github.com/p-rum/kgmaker/pull/112) | Independent overlapping facets, declared business/tool blockers, explicit delivery/acceptance/test links and pinned atomic publication. 73 integration PASS with actual Javac21/TS5.7.3/React; subsequent publication audit151 PASS / 2 DESELECTED + actual5 PASS / 0 SKIP; compiler BEFE artifact and SOURCE_ONLY template/PDF capability remain separate. Single-context feature selection, runtime/data UNKNOWN; [change131](changes/131_completeAnalysisReport.md). |
| [T003-S10-W01](tasks/T003-S10-01-stageContentCache.md) | MERGED | PARTIAL | merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` | [inspection](../src/kgmaker/inspection.py), [store](../src/kgmaker/store.py), [cache](../src/kgmaker/extraction_cache.py), [unit](../tests/test_stage_content_cache.py), [actual](../tests/test_stage_content_cache_actual.py) | [#114](https://github.com/p-rum/kgmaker/pull/114), [#119](https://github.com/p-rum/kgmaker/pull/119), [#127](https://github.com/p-rum/kgmaker/pull/127) | Historické dodání #114 a 102 PASS jsou v [change133](changes/133_stageContentCache.md). Regresi #116 reprodukuje základní revize. Dílčí oprava #119 má 97 PASS / 0 SKIP, používá živý výpočet evidence a je součástí [společné integrace](changes/142_integrateCompilerEvidenceRepairs.md). Dílčí oprava otisku a ochrany při změně launcheru je sloučena v [#149](https://github.com/p-rum/kgmaker/pull/149) jako `16f2ba8c4d109957edc295feea80db86da7093f1`. [Change164](changes/164_bindJavaLaunchInputs.md) pokrývá locale, `ct.sym` a odmítnutí změny vstupu se zachováním grafu na JDK 21/POSIX. W02/W06 mají vlastní acceptance. Výkonový HIT zůstává otevřený v #116. Předchozí řádek evidoval merge `7c6a3dda821b55a4de6718f09504de4a861f47ae`. Přesné ověření viz [výsledek integrace](changes/143_recordCompilerIntegrationMerge.md). |
| [T003-S10-W02](tasks/T003-S10-02-reverseDependencyIndexes.md) | MERGED | PARTIAL | merge `0c834c8b2c06ca80d76f1aaf09f6f49b968e8aa3` | [store](../src/kgmaker/store.py), [provider](../src/kgmaker/graph_provider.py), [feature](../src/kgmaker/feature.py), [fixture](../tests/test_reverse_dependency_index.py) | [#130](https://github.com/p-rum/kgmaker/pull/130) | Čtecí report pro doložené callery, Flyway, OpenAPI a použité citace feature. LF↔CRLF může označit i tranzitivní callery cíle s přesným bajtovým lokátorem. Report vynechá raw JVM kontext s neplatným uloženým otiskem a zachová ostatní doložené vazby. Oprava nad `1569d5d` má 164 PASS / 0 SKIP se skutečným Javac/K1/K2, včetně W06 a T032. Přenos po #156 má 124 PASS / 0 SKIP na JDK 21 s Mavenem a 2 585 PASS v úplné sadě CPython 3.13. Oprava T045 odmítá smíšené volby CLI, má 44 nativních PASS bez přeskočení a 2 586 PASS v úplné sadě. AC01 zůstává PARTIAL. Navazuje selektivní publikace do grafu a revizí, poté invalidace negativních lookupů W03. [Stav AC a hranice](acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy), [change145](changes/145_buildReverseDependencyIndexes.md) a [Sloučení a ověření](changes/174_reconcileMergedDelivery.md#t003-s10-w02-kroky-35-a-ac01ac04). |
| [T003-S10-W03](tasks/T003-S10-03-negativeLookupInvalidation.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/store.py](../src/kgmaker/store.py), [src/kgmaker/scanner.py](../src/kgmaker/scanner.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py) | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S10-W04](tasks/T003-S10-04-filesystemMutationEquivalence.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/scanner.py](../src/kgmaker/scanner.py), [src/kgmaker/semantic.py](../src/kgmaker/semantic.py), [src/kgmaker/store.py](../src/kgmaker/store.py) | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S10-W05](tasks/T003-S10-05-selectiveFeatureRevise.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/feature.py](../src/kgmaker/feature.py), [src/kgmaker/analysis_validation.py](../src/kgmaker/analysis_validation.py), [src/kgmaker/store.py](../src/kgmaker/store.py) | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S10-W06](tasks/T003-S10-06-cacheCorruptionConcurrency.md) | MERGED | VERIFIED_IN_SCOPE | [#129](https://github.com/p-rum/kgmaker/pull/129) `c067f9c3c7b3266842fc4f2230b4eaf65182e4df` | [src/kgmaker/store.py](../src/kgmaker/store.py), [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [src/kgmaker/build_runner.py](../src/kgmaker/build_runner.py) | — | Výhradní publikace a rollback Confluence, kontrola runtime generace a atomický build claim. Linux 3692 PASS / 1 SKIP se skutečnými workery, GH CI NEOVĚŘENO. Obnova po pádu a warm replay mají samostatný rozsah. [Doklad](changes/149_recordGraphPublicationMerge.md). |
| [T003-S11-W01](tasks/T003-S11-01-workerCleanInstall.md) | MERGED | PARTIAL | `3b7329284b376c83e20fe1a4ae3ea57a57131a90` | [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [tests/test_worker_install.py](../tests/test_worker_install.py) | [# 18](https://github.com/p-rum/kgmaker/pull/18) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S11-W02](tasks/T003-S11-02-buildExporterPackaging.md) | MERGED | PARTIAL | `e656b8ef4c174d3d60600037d7c0d78fc514e39d` | [src/kgmaker/build_runner.py](../src/kgmaker/build_runner.py), [tests/test_exporter_distribution.py](../tests/test_exporter_distribution.py) | [# 22](https://github.com/p-rum/kgmaker/pull/22) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S11-W03](tasks/T003-S11-03-windowsNoAdminInstall.md) | MERGED | PARTIAL | `a83dbab6263eb2fe225f0da51f2f2549c0ab162e` | [Windows harness](../tests/windows/no_admin_smoke.ps1), [testy](../tests/test_windows_install.py) | [# 24](https://github.com/p-rum/kgmaker/pull/24) | Původní core/Java/K1/TS Windows smoke 43 PASS / 2 SKIP. Po selhání na nepřipraveném K2 mimo rozsah prošel opravený `0329c5d` s omezeným Windows tokenem, 44 PASS / 1 SKIP / 1 DESELECTED. [Opravený job](https://github.com/p-rum/kgmaker/actions/runs/44930369173/job/136925458350), [Change155](changes/155_scopeWindowsWorkerSmoke.md). |
| [T003-S11-W04](tasks/T003-S11-04-mandatoryWorkerCi.md) | MERGED | PARTIAL | `e9027e9a14e048c891aec01ca5af812fc8cf46c7` | [tests/test_mandatory_worker_ci.py](../tests/test_mandatory_worker_ci.py) | [# 33](https://github.com/p-rum/kgmaker/pull/33) | Omezený kontrakt; úplná AC/toolchain matice nově NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S11-W05](tasks/T003-S11-05-benchmarkCorpus.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S11-W06](tasks/T003-S11-06-regressionBudgets.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S11-W07](tasks/T003-S11-07-fullEndToEndAcceptance.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S11-W08](tasks/T003-S11-08-releaseDocumentation.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S12-W01](tasks/T003-S12-01-liveConfluenceConnector.md) | MERGED | PARTIAL | `7b9a9eaecaf41c9c5bc5a6d1233cd82e2cf4f1e9` | [src/kgmaker/confluence.py](../src/kgmaker/confluence.py), [src/kgmaker/confluence_sync.py](../src/kgmaker/confluence_sync.py), [tests/test_confluence_configuration.py](../tests/test_confluence_configuration.py) | [# 25](https://github.com/p-rum/kgmaker/pull/25) | Pouze offline konfigurace; live adapter DEFERRED, live acceptance NOT_RUN. Ověřit původní AC a podporovanou matici. |
| [T003-S13-W01](tasks/T003-S13-01-runtimeTraceProducer.md) | MERGED | PARTIAL; JDK21/POSIX subset VERIFIED_IN_SCOPE | `d2507ef465c9b4844830520de68629a3b577c0d2`, `385943e48d2d2e60cec541f1f0db78beda83de22` | [tests/test_runtime_trace_producer.py](../tests/test_runtime_trace_producer.py), [JDK fixture](../tests/fixtures/runtime-trace/TraceApplication.java) | [PR101](https://github.com/p-rum/kgmaker/pull/101) MERGED · [#148](https://github.com/p-rum/kgmaker/pull/148) MERGED | Skutečný synchronní opt-in SDK capture call/factory/condition/map registration, strict v2, pre/postflight a POSIX cleanup. #148 dodalo veřejné předání deklarovaného SHA-256 z vybrané varianty BuildManifestu. Ověření W01 zůstává PARTIAL v rozsahu JDK21/POSIX. Okolní runtime prostředí, automatický Spring capture, Windows a dostupnost dat mají vlastní rozsah. Historický přenos PR102 zahrnul 88 runtime testů v sadě 205 PASS / 0 SKIP. [Ověření PR102](changes/120_namedQueryContainers.md) · [Kontrakt](runtime-trace.md) · [Change122](changes/122_runtimeTraceProducer.md) · [Change165](changes/165_forwardBuildConfiguration.md). |
| [T003-S13-W02](tasks/T003-S13-02-runtimeRtaImport.md) | MERGED | PARTIAL | merge `5809e84932b1910bfc3f17c72e2a2005283389b1` | [import](../src/kgmaker/runtime_evidence.py), [navigace](../src/kgmaker/callgraph.py), [fixture](../tests/test_runtime_trace_producer.py) | [#136](https://github.com/p-rum/kgmaker/pull/136) | Import uchovává doklady podle compiler kontextu a variant služby. V2 `call` a `dispatch` vyžadují volatelné symboly. Při změně vstupních objektů Python API se uloží jen ověřená konfigurace a pozorování. Statické cesty a cykly používají compiler call sites. #147 ověřuje zdroje, worker a u v2 bytecode při publikaci. #148 předává deklarovaný otisk. Receiver/type dispatch, přesná vazba na call site a širší T003-AC13 zůstávají otevřené. [Ověření #136](changes/151_preserveRuntimeObservationEvidence.md) · [Ověření #147](changes/163_revalidateRuntimeImportPublication.md) · [Záznam sloučení a ověření](changes/174_reconcileMergedDelivery.md). |
| [T003-S13-W03](tasks/T003-S13-03-runtimeValueFlow.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/runtime_evidence.py](../src/kgmaker/runtime_evidence.py), [src/kgmaker/availability.py](../src/kgmaker/availability.py), [src/kgmaker/dataflow.py](../src/kgmaker/dataflow.py) | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T003-S13-W04](tasks/T003-S13-04-runtimeAsyncReflection.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/runtime_evidence.py](../src/kgmaker/runtime_evidence.py), [src/kgmaker/flow.py](../src/kgmaker/flow.py) | — | Cílový kontrakt nedodán; existující moduly nejsou jeho acceptance. Implementovat dle závislostí původního zadání. |
| [T005](tasks/T-005_add-view-model.md) | MERGED | PARTIAL | `c0a10261c2ff1f83291125ec838bbaeea8723532` | [src/kgmaker/architecture_model.py](../src/kgmaker/architecture_model.py), [tests/test_t005_add_view_model.py](../tests/test_t005_add_view_model.py) | [#11](https://github.com/p-rum/kgmaker/pull/11) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T006](tasks/T-006_select-service-contexts.md) | MERGED | PARTIAL | `3c94ea8e91042cad1bfb516e76a9c110b04fc719` | [src/kgmaker/views.py](../src/kgmaker/views.py), [tests/test_t006_select_service_contexts.py](../tests/test_t006_select_service_contexts.py) | [#20](https://github.com/p-rum/kgmaker/pull/20) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T007](tasks/T-007_define-service-ownership.md) | MERGED | PARTIAL | `3a393e451b0d7b8f83de93f05f07d2307ba66ec3` | [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [tests/test_t007_define_service_ownership.py](../tests/test_t007_define_service_ownership.py) | [#23](https://github.com/p-rum/kgmaker/pull/23) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T008](tasks/T-008_project-service-inventory.md) | MERGED | PARTIAL | `ff26a6d74679fc38820c1f2fe711b1db20af2ca1` | [src/kgmaker/views.py](../src/kgmaker/views.py), [tests/test_t008_project_service_inventory.py](../tests/test_t008_project_service_inventory.py) | [#29](https://github.com/p-rum/kgmaker/pull/29) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T009](tasks/T-009_propagate-view-evidence.md) | MERGED | PARTIAL | `09d351d379b43c697451f93c8735a008204d8d9b` | [src/kgmaker/architecture_model.py](../src/kgmaker/architecture_model.py), [src/kgmaker/views.py](../src/kgmaker/views.py), [tests/test_t009_propagate_view_evidence.py](../tests/test_t009_propagate_view_evidence.py) | [#48](https://github.com/p-rum/kgmaker/pull/48) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T010](tasks/T-010_catalog-http-providers.md) | MERGED | PARTIAL | `c3825ee3341bdbbfc0f002a7eda161e5f437d85f` | [src/kgmaker/domain.py](../src/kgmaker/domain.py), [src/kgmaker/interfaces.py](../src/kgmaker/interfaces.py), [src/kgmaker/scanner.py](../src/kgmaker/scanner.py), [tests/test_t010_catalog_http_providers.py](../tests/test_t010_catalog_http_providers.py), [tests/test_t010_compiler_providers.py](../tests/test_t010_compiler_providers.py) | [#58](https://github.com/p-rum/kgmaker/pull/58) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T011](tasks/T-011_catalog-http-consumers.md) | MERGED | PARTIAL | `9eb4f2f88ff96159650fa57819f890db135d4568` | [src/kgmaker/interfaces.py](../src/kgmaker/interfaces.py), [tests/test_t011_catalog_http_consumers.py](../tests/test_t011_catalog_http_consumers.py) | [#63](https://github.com/p-rum/kgmaker/pull/63) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T012](tasks/T-012_catalog-kafka-interfaces.md) | MERGED | PARTIAL | `b0ef9e2ed93202154bf5bfb49aecd74d2b3dfdd6` | [src/kgmaker/interfaces.py](../src/kgmaker/interfaces.py), [src/kgmaker/workspace.py](../src/kgmaker/workspace.py), [tests/test_t012_catalog_kafka_interfaces.py](../tests/test_t012_catalog_kafka_interfaces.py) | [#73](https://github.com/p-rum/kgmaker/pull/73) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T013](tasks/T-013_attach-interface-contracts.md) | MERGED | PARTIAL | `2a387066ced5e4bcc8ab3d7c2bbdfbdfff2bb1ef` | [src/kgmaker/contract_inputs.py](../src/kgmaker/contract_inputs.py), [src/kgmaker/interfaces.py](../src/kgmaker/interfaces.py), [src/kgmaker/test_analysis.py](../src/kgmaker/test_analysis.py), [tests/test_t013_attach_interface_contracts.py](../tests/test_t013_attach_interface_contracts.py), [tests/test_t013_captured_kafka_contracts.py](../tests/test_t013_captured_kafka_contracts.py) | [#74](https://github.com/p-rum/kgmaker/pull/74) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T014](tasks/T-014_bind-remote-interfaces.md) | MERGED | PARTIAL | `ec6a127857cc47704316e6a1d5a088be9e4b16e7` | [src/kgmaker/remote_interfaces.py](../src/kgmaker/remote_interfaces.py), [tests/test_t014_bind_remote_interfaces.py](../tests/test_t014_bind_remote_interfaces.py) | [#80](https://github.com/p-rum/kgmaker/pull/80) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T015](tasks/T-015_project-data-resources.md) | MERGED | PARTIAL | `49c46b0bd165cf11e7b3eb0af04bf64fb93e23ce` | [src/kgmaker/data_resources.py](../src/kgmaker/data_resources.py), [tests/test_t015_project_data_resources.py](../tests/test_t015_project_data_resources.py) | [#55](https://github.com/p-rum/kgmaker/pull/55) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T016](tasks/T-016_aggregate-service-topology.md) | MERGED | PARTIAL | `130720f7714634430a2255486ce9c4c130003f2b` | [src/kgmaker/service_topology.py](../src/kgmaker/service_topology.py), [tests/test_t016_aggregate_service_topology.py](../tests/test_t016_aggregate_service_topology.py) | [#81](https://github.com/p-rum/kgmaker/pull/81) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T017](tasks/T-017_filter-topology-scope.md) | MERGED | PARTIAL | `4e4fcd65e94b855ac4aee2e76fa4a25084940da7` | [src/kgmaker/topology_filter.py](../src/kgmaker/topology_filter.py), [tests/test_t017_filter_topology_scope.py](../tests/test_t017_filter_topology_scope.py) | [#82](https://github.com/p-rum/kgmaker/pull/82) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T018](tasks/T-018_explain-view-elements.md) | MERGED | PARTIAL | `1005b9f950102d2d5fd0e74735bc0577c2e30c0b` | [src/kgmaker/view_explanation.py](../src/kgmaker/view_explanation.py), [tests/test_t018_explain_view_elements.py](../tests/test_t018_explain_view_elements.py) | [#83](https://github.com/p-rum/kgmaker/pull/83) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T019](tasks/T-019_add-architecture-json-cli.md) | MERGED | PARTIAL | `a60f02d2a36f0d826ea340541966028d818efd5d` | [src/kgmaker/architecture_cli.py](../src/kgmaker/architecture_cli.py), [src/kgmaker/cli.py](../src/kgmaker/cli.py), [tests/test_t019_add_architecture_json_cli.py](../tests/test_t019_add_architecture_json_cli.py) | [#84](https://github.com/p-rum/kgmaker/pull/84) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T020](tasks/T-020_render-interface-markdown.md) | MERGED | PARTIAL | `250e7c16250a97b9f8df5256b9894c8119dc64d9` | [src/kgmaker/architecture_cli.py](../src/kgmaker/architecture_cli.py), [src/kgmaker/architecture_render.py](../src/kgmaker/architecture_render.py), [src/kgmaker/architecture_render_common.py](../src/kgmaker/architecture_render_common.py), [tests/test_t020_render_interface_markdown.py](../tests/test_t020_render_interface_markdown.py) | [#87](https://github.com/p-rum/kgmaker/pull/87) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T021](tasks/T-021_render-topology-mermaid.md) | MERGED | VERIFIED_IN_SCOPE | head `c5c73a844f46ba9b458e4aa850a7d3ef3e78ed2b`; merge `61a554174b1c23257878fffae0e125f146223d79` | [Renderer](../src/kgmaker/architecture_render.py), [CLI](../src/kgmaker/architecture_cli.py), [test](../tests/test_t021_render_topology_mermaid.py) | [#123](https://github.com/p-rum/kgmaker/pull/123) | 194 cílených PASS / 0 SKIP s Mermaid 11.4.1, 3672 PASS a 1 mimo-scope Windows SKIP v úplné sadě. T045 schválilo přesný pár. [Doklad integrace](changes/146_recordTopologyMerge.md). T022 má splněnou závislost T021. |
| [T022](tasks/T-022_render-topology-markdown.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T023](tasks/T-023_define-business-process-model.md) | MERGED | PARTIAL | `b78d2e62148f225be7ba8c53c839f8b052ee269d` | [src/kgmaker/process_model.py](../src/kgmaker/process_model.py), [tests/test_t023_define_business_process_model.py](../tests/test_t023_define_business_process_model.py) | [#56](https://github.com/p-rum/kgmaker/pull/56) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T024](tasks/T-024_discover-process-triggers.md) | MERGED | PARTIAL | `c98ae1ea85934674eac743d60489b37b322f8fc9` | [src/kgmaker/process_triggers.py](../src/kgmaker/process_triggers.py), [tests/test_t024_discover_process_triggers.py](../tests/test_t024_discover_process_triggers.py) | [#59](https://github.com/p-rum/kgmaker/pull/59) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T025](tasks/T-025_build-local-process-path.md) | MERGED | PARTIAL | merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` | [src/kgmaker/control_flow.py](../src/kgmaker/control_flow.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [src/kgmaker/inspection.py](../src/kgmaker/inspection.py), [tests/test_t025_build_local_process_path.py](../tests/test_t025_build_local_process_path.py) | [#65](https://github.com/p-rum/kgmaker/pull/65), [#60](https://github.com/p-rum/kgmaker/pull/60), [#122](https://github.com/p-rum/kgmaker/pull/122), [#127](https://github.com/p-rum/kgmaker/pull/127) | Historický merge `32a3bca46d62f3715d1fb2d96dd6f0e92f941dc6`. Vadné optional CFG refs reprodukuje baseline. Dílčí oprava #122 má 113 PASS / 0 SKIP s JDK21 a K1/K2 a je součástí [společné integrace](changes/142_integrateCompilerEvidenceRepairs.md). Širší acceptance zůstává PARTIAL. Předchozí řádek evidoval `465b121992aad50c2885acef0fd038531a31293a`. Přesné ověření viz [výsledek integrace](changes/143_recordCompilerIntegrationMerge.md). |
| [T026](tasks/T-026_collapse-business-steps.md) | MERGED | PARTIAL | `9442114d169b84e6c9f98dd097faafd80eff0d48` | [src/kgmaker/business_process.py](../src/kgmaker/business_process.py), [tests/test_t026_collapse_business_steps.py](../tests/test_t026_collapse_business_steps.py) | [#66](https://github.com/p-rum/kgmaker/pull/66) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T027](tasks/T-027_cross-http-process-boundary.md) | MERGED | VERIFIED_IN_SCOPE | `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0` | [src/kgmaker/business_process.py](../src/kgmaker/business_process.py), [tests/test_t027_cross_http_process_boundary.py](../tests/test_t027_cross_http_process_boundary.py) | [PR105](https://github.com/p-rum/kgmaker/pull/105), independent APPROVE and verified two-parent merge | Historical integration 200 PASS / 0 SKIP, 10.76 s; independent review 200 PASS / 0 SKIP, 13.00 s. Source/semantic preservation verified. Status reconciled in change127; full suite remains NOT_RUN. |
| [T028](tasks/T-028_cross-async-process-boundary.md) | MERGED | VERIFIED_IN_SCOPE | `9f538634807957abe1004dde43450271b77f1bb5` | [business_process.py](../src/kgmaker/business_process.py), [test_t028_cross_async_process_boundary.py](../tests/test_t028_cross_async_process_boundary.py) | [PR108](https://github.com/p-rum/kgmaker/pull/108), [change127 steps 7–10](changes/127_crossAsyncProcessBoundary.md) | New context/projection/T025/T028 integration: 158 PASS / 0 SKIP, 28.09 s, actual JDK21/Javac/K1/K2 and 4 reviewer repros; both parent source/test trees preserved. Historical review-fix run 264 PASS / 0 SKIP. Independent APPROVE/merge and317 targeted PASS are recorded in [merge audit](https://github.com/p-rum/kgmaker/pull/108#issuecomment-6899650441); full suite NOT_RUN. |
| [T029](tasks/T-029_project-process-failures.md) | MERGED | VERIFIED_IN_SCOPE | merge `84f94d4462437fe1228f07d0ba8f51071224952e` | [test_t029_project_process_failures.py](../tests/test_t029_project_process_failures.py), actual Java/K1 positive and K2 UNKNOWN | [#110](https://github.com/p-rum/kgmaker/pull/110) | Pure failure projection, per-occurrence canonical Kafka entry and exact T014 membership tuple after the second PR110 review; current report-main integration 203 PASS / 0 SKIP (74.02 s), T014/T028/T029 + all 3 reviewer reproductions + report projection/publication; historical345 in step11; change130 steps9–12. Finally paths preserved, static retry/DLT, no remote rollback, PROPOSED compensation only. Full/actual Kafka3.2.0/runtime NOT_RUN. |
| [T030](tasks/T-030_prepare-process-label-packet.md) | MERGED | PARTIAL | `9eec41a403b4e6601fe3addac168bf39d37f31b6` | [src/kgmaker/process_semantics.py](../src/kgmaker/process_semantics.py), [tests/test_t030_prepare_process_label_packet.py](../tests/test_t030_prepare_process_label_packet.py) | [#75](https://github.com/p-rum/kgmaker/pull/75) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T031](tasks/T-031_validate-process-annotations.md) | MERGED | PARTIAL | `2c7b38ea2dc7b5ad08009eefa276c4dc41a5b1a9` | [src/kgmaker/process_semantics.py](../src/kgmaker/process_semantics.py), [tests/test_t031_validate_process_annotations.py](../tests/test_t031_validate_process_annotations.py) | [#77](https://github.com/p-rum/kgmaker/pull/77) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T032](tasks/T-032_persist-process-review.md) | MERGED | VERIFIED_IN_SCOPE | merge `4011825b15e4b65e1f57576a0986ca05b3cf810e` | [store](../src/kgmaker/process_store.py), [packet](../src/kgmaker/process_semantics.py), [testy](../tests/test_t032_persist_process_review.py) | [#78](https://github.com/p-rum/kgmaker/pull/78), [#132](https://github.com/p-rum/kgmaker/pull/132) | Výslovné POSIX review a oprava normalizovaného kontextu v main. 3698 PASS / 2 SKIP, všech 43 T032 případů PASS, 1 skutečný uložený kontext Javac 21/K1 PASS. Nezávislé T045 a serverový merge doložené. [Change152](changes/152_recordNormalizedProcessReviewMerge.md), [historický přenos](changes/147_replayNormalizedProcessContext.md). |
| [T033](tasks/T-033_catalog-business-processes.md) | MERGED | PARTIAL | `5095343a6796229bf40bf32d62404c709ddd51e5` | [src/kgmaker/process_catalog.py](../src/kgmaker/process_catalog.py), [tests/test_t033_catalog_business_processes.py](../tests/test_t033_catalog_business_processes.py) | [#79](https://github.com/p-rum/kgmaker/pull/79) | Pouze dokumentovaný subset; nová úplná acceptance NOT_RUN. Ověřit původní AC a zbývající limity. |
| [T034](tasks/T-034_add-process-cli.md) | PLANNED | NOT_RUN | `4011825b15e4b65e1f57576a0986ca05b3cf810e` | [T024](../src/kgmaker/process_triggers.py), [T025](../src/kgmaker/process_paths.py), [T033](../src/kgmaker/process_catalog.py) | — | Replay T032 je sloučený. První čtecí JSON rozsah může použít přesný trigger a explicitní ProcessView. Zápis čeká na kontrakt neměnné revize PROPOSED a přenos packetu, kandidáta a CAS tokenů. U širšího výběru kontextů je třeba ověřit vazbu ProcessView na T030. [Change152](changes/152_recordNormalizedProcessReviewMerge.md#zbývající-rozsah-t034). |
| [T035](tasks/T-035_render-business-process-mermaid.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T036](tasks/T-036_render-business-process-report.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T037](tasks/T-037_invalidate-derived-views.md) | MERGED | PARTIAL | `b1a8ba1f4234cd399de8319fcf5cde2c670dac26` | [view_cache.py](../src/kgmaker/view_cache.py), [graph_provider.py](../src/kgmaker/graph_provider.py), [test_t037_invalidate_derived_views.py](../tests/test_t037_invalidate_derived_views.py) | [PR103](https://github.com/p-rum/kgmaker/pull/103) MERGED | Explicitní single-view cache a broad invalidation: nová integrační sada 298 PASS / 0 SKIP, 11.07 s; zachování vstupů/cache při CLI chybách, původní snapshot guard a obnova původní sémantické evidence. Integrační HEAD 03aaf0d prošel nezávislým APPROVE a opakováním 298 PASS / 0 SKIP, 21.57 s; PR104 zachovává T037 helper a cache kontrakt. Full acceptance NOT_RUN. Viz [change121](changes/121_invalidateDerivedViews.md) a [API limity](view-cache.md). |
| [T038](tasks/T-038_publish-view-artifacts-atomically.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T039](tasks/T-039_diff-architecture-and-processes.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T040](tasks/T-040_add-agent-process-instructions.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T041](tasks/T-041_verify-architecture-acceptance.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T042](tasks/T-042_verify-process-acceptance.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T043](tasks/T-043_bound-view-performance.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T044](tasks/T-044_document-high-level-capabilities.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Nedodaný kontrakt; historický combined checkpoint není current dodávka. Implementovat po uvedených upstream závislostech. |
| [T046-S01](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | VERIFIED_IN_SCOPE | head `3083215800515e81425d4824c7db5cef0fe1ef10`; merge `25176ad8f63e3666a051dab9c9216f50adfd6ed3` | [src/kgmaker/provenance.py](../src/kgmaker/provenance.py), [src/kgmaker/workflow.py](../src/kgmaker/workflow.py), [tests/test_provenance.py](../tests/test_provenance.py) | [#41](https://github.com/p-rum/kgmaker/pull/41) | Exact-pair review schválilo append-only historii, monotónní CAS revizi a trace dostupnou před S03. Cíleně 83 passed + 7 subtests; full 1602 passed, 1055 skipped + 29 subtests; [záznam](changes/56_addDeliveryReferences.md). |
| [T046-S02](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | VERIFIED_IN_SCOPE | head `351a661641b8a8f619b389c20a7cf32641c23f5a`; merge `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10` | [src/kgmaker/artifact_templates.py](../src/kgmaker/artifact_templates.py), [tests/test_artifact_templates.py](../tests/test_artifact_templates.py) | [#42](https://github.com/p-rum/kgmaker/pull/42) | Exact-pair review schválilo kanonické exportní cesty a transakční instalaci. Cíleně 91 passed + 23 subtests; full 1610 passed, 1055 skipped + 45 subtests. [Záznam](changes/57_addArtifactTemplates.md). |
| [T046-S03](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | PARTIAL | head `1b7ce435c53a2dca0168997549f0dd587b331d6c`; merge `f000e3d5eb898031af15785bd1b80427c149ec4c` | [src/kgmaker/testgen.py](../src/kgmaker/testgen.py), [tests/test_delivery.py](../tests/test_delivery.py) | [#43](https://github.com/p-rum/kgmaker/pull/43) | Exact-pair review schválilo striktní CAS revizi, kanonický data_dir a úplný rollback. Cíleně 106 passed + 37 subtests; full 1625 passed, 1055 skipped + 59 subtests. [Záznam](changes/58_addExistingFunctionTests.md). Reprodukce na `465b1219` dne 2026-11-20 našla neověřované schema-valued additionalProperties. Oprava pro [#91](https://github.com/p-rum/kgmaker/issues/91) má 103 cílených PASS na opraveném zdroji. [Change140](changes/140_validateAdditionalDatasetFields.md). |
| [T046-S04](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | VERIFIED_IN_SCOPE | head `301bfb9f514c45176f119533303a5c1b1a435d05`; merge `306cb83105751a7848b9efb4ba8c801e551353df` | [tests/test_synthetic_data.py](../tests/test_synthetic_data.py), [tests/test_delivery.py](../tests/test_delivery.py) | [#44](https://github.com/p-rum/kgmaker/pull/44) | Exact-pair review schválilo CSV happy-path/kolizní rollback a maximum/maxLength acceptance. Cíleně 111 passed + 45 subtests; full 1630 passed, 1055 skipped + 67 subtests. [Záznam](changes/59_verifySyntheticTestData.md). Navazující T046-AC04 ověření variant typovaných dodatečných vlastností má 103 cílených PASS / 0 SKIP. [Change140](changes/140_validateAdditionalDatasetFields.md). |
| [T046-S05](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | VERIFIED_IN_SCOPE | head `bdedb6cc0e4f48a4e19357458a375fe3e04a72d9`; merge `6dffe5e39fb847e5552f38e67b957e4b51b20bed` | [src/kgmaker/workflow.py](../src/kgmaker/workflow.py), [tests/test_delivery.py](../tests/test_delivery.py) | [#45](https://github.com/p-rum/kgmaker/pull/45) | Exact-pair review po opravě statusů schválilo default-off approval gates. Cíleně 114 passed + 49 subtests; full 1633 passed, 1055 skipped + 71 subtests. [Záznam](changes/60_enforceOptionalLocalApprovals.md). |
| [T046-S06](tasks/46_addTemplatesTestsAndTraceability.md) | MERGED | VERIFIED_IN_SCOPE | head `65e6a3bbe7246ef7d3caac4d0f956cd6d3f81de5`; merge `9bcf91db1d1349241f7e1f7114f74c0331c25802` | [src/kgmaker/delivery_cli.py](../src/kgmaker/delivery_cli.py), [src/kgmaker/delivery_instructions.py](../src/kgmaker/delivery_instructions.py), [tests/test_delivery.py](../tests/test_delivery.py) | [#40](https://github.com/p-rum/kgmaker/pull/40) | Exact-pair review schválilo CLI/instrukce/CAS integraci. Cíleně 309 passed, 10 skipped + 67 subtests; full 1635 passed, 1055 skipped + 76 subtests. [Záznam](changes/61_integrateDeliveryWorkflow.md); [post-merge srovnání](changes/113_reconcileT046DeliverySummary.md). |
| [T047-S01](tasks/47_addReliableIncrementalContext.md) | MERGED | PARTIAL | `b3bbba43304f499f96950ea4ecc2a2467919e616` | [Oracle](../fixtures/incremental-integrity/oracle.json), [test](../tests/test_incremental_equivalence.py), [historie běhů](changes/137_prepareIncrementalMutationOracle.md) | [#121](https://github.com/p-rum/kgmaker/pull/121) | SOURCE_ONLY mezistavy, oddělené deklarace se stejným FQN a shodný graf po přesunu workspace, cold Kotlin změna těla, add, změna signatury a odstranění přesunutého cíle s nezměněným callerem, deklarativní Kafka match a Kotlin–TS flow s hash/release provenance. Cold JVM varianta pokrývá kladné `supplies_classpath` a dvě negativní změny. Inkrementální refresh a zbývající scénáře §7 jsou otevřené. Merge splňuje závislost dodání pro S02. [Doklad integrace](changes/161_recordMutationCorpusMerge.md). |
| [T047-S02](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/scanner.py](../src/kgmaker/scanner.py), [src/kgmaker/model.py](../src/kgmaker/model.py) | — | Upstream owner: T047-S02; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S03](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/model.py](../src/kgmaker/model.py), [src/kgmaker/store.py](../src/kgmaker/store.py) | — | Upstream owner: T003-S10-W02; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S04](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py), [src/kgmaker/inspection.py](../src/kgmaker/inspection.py) | — | Upstream owner: T003-S10-W03; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S05](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/store.py](../src/kgmaker/store.py), [src/kgmaker/graph_provider.py](../src/kgmaker/graph_provider.py) | — | Upstream owner: T003-S10-W06; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S06](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/scanner.py](../src/kgmaker/scanner.py), [src/kgmaker/semantic.py](../src/kgmaker/semantic.py) | — | Upstream owner: T003-S10-W04; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S07](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/framework.py](../src/kgmaker/framework.py), [src/kgmaker/spring_beans.py](../src/kgmaker/spring_beans.py) | — | Upstream owner: T047-S07; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S08](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/context.py](../src/kgmaker/context.py), [src/kgmaker/feature.py](../src/kgmaker/feature.py) | — | Upstream owner: T047-S08; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S09](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/contract_inputs.py](../src/kgmaker/contract_inputs.py), [src/kgmaker/interfaces.py](../src/kgmaker/interfaces.py) | — | Upstream owner: T047-S09 + T037; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S10](tasks/47_addReliableIncrementalContext.md) | MERGED | PARTIAL | `52af545bfc97396a0001432abc5d58ab7c3663af` | [capture](../src/kgmaker/verification.py), [runner](../src/kgmaker/build_runner.py), [journal](../src/kgmaker/provenance.py), [test](../tests/test_verification_records.py) | [#135](https://github.com/p-rum/kgmaker/pull/135) | Souborově vázaný doklad explicitního Maven/Gradle testu v jednom checkoutu. Ověřený head má 133 cílených PASS / 2 SKIP a merge má 27 PASS / 0 SKIP v sadě dokladů se skutečným Maven/Surefire. Workspace se dvěma checkouty vrací chybu před spuštěním buildu. Vícerepozitářový doklad, ověřitelné importy a širší ověřovací matice zůstávají otevřené. T047-S11 má samostatnou acceptance. [Change158](changes/158_recordFileBoundVerificationMerge.md). |
| [T047-S11](tasks/47_addReliableIncrementalContext.md) | MERGED | PARTIAL | `47807742a07c4a4fb92a590479fbfa0b558bf7fe` | [workflow](../src/kgmaker/workflow.py), [verification](../src/kgmaker/verification.py), [lineage](../src/kgmaker/provenance.py), [context](../src/kgmaker/context.py), [test](../tests/test_verification_records.py) | [#144](https://github.com/p-rum/kgmaker/pull/144) | Lokální volitelná brána `done` používá aktuální doklad jednoho explicitního běhu. Schválení T046 mají vlastní pravidla. Report odlišuje workflow od aktuálnosti evidence. Přesný head a sloučené main mají 179 PASS / 0 SKIP se skutečným Mavenem a Surefire. Mapování požadovaných testů, selektivní dopad, širší matice a projekce do paměti zůstávají otevřené. [Doklad integrace](changes/161_recordMutationCorpusMerge.md#t047-s11--t047-r11--t047-ac11-a-t048-s01--t048-ac01) · [Change159](changes/159_gateCompletionOnCurrentVerification.md). |
| [T047-S12](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | [src/kgmaker/cli.py](../src/kgmaker/cli.py), [src/kgmaker/feature_cli.py](../src/kgmaker/feature_cli.py) | — | Upstream owner: T047-S12; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |
| [T047-S13](tasks/47_addReliableIncrementalContext.md) | PLANNED | NOT_RUN | `f115aa4a1c37683f3be9e4607111d51d9c1301c1` | Implementace/test kontraktu nenalezen; viz zadání. | — | Upstream owner: T047-S13 + T003-S11; sdílené části se nepočítají znovu. Splnit explicitní Depends on a původní AC; nevytvářet paralelní infrastrukturu. |

### Historické PR checkpointy — 2026-11-07

GitHub GET dne 2026-11-07: T046 PR41/42/43/44/45/40 jsou ready (`draft=false`),
`mergeable=true`, `mergeable_state=unstable`. To není PASS CI ani approval.
Při změně main/parentu je nutné znovu ověřit pár a relevantní testy.

| PR | Base ref | Base SHA | Head SHA | Další krok |
|---|---|---|---|---|
| [#4](https://github.com/p-rum/kgmaker/pull/4) | `main` | `8ac80ca30f6f680539deb7fb3590519d3a5c1460` | `b11c86489a6ac2ffb89261ab0c7949d9d890374e` | Historický draft; nulový zbytkový patch, viz níže. |
| [#40](https://github.com/p-rum/kgmaker/pull/40) | `feat/t046-s05-local-approvals` | `4a60b6110fa41d9a53fdad639915e5495a785159` | `1b8b2f8d2cd09c5da95c919f84b96427a30299ad` | Nezávislé review a navazující retarget; bez automatického merge. |
| [#41](https://github.com/p-rum/kgmaker/pull/41) | `main` | `766c08fb47458220fb037c2ee278607247b721e1` | `3083215800515e81425d4824c7db5cef0fe1ef10` | MERGED jako `25176ad8f63e3666a051dab9c9216f50adfd6ed3` po nezávislém exact-pair review. |
| [#42](https://github.com/p-rum/kgmaker/pull/42) | `main` | `25176ad8f63e3666a051dab9c9216f50adfd6ed3` | `351a661641b8a8f619b389c20a7cf32641c23f5a` | MERGED jako `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10` po exact-pair review. |
| [#43](https://github.com/p-rum/kgmaker/pull/43) | `main` | `8aae58c0ca280c13ce19ccb6a7c4e3cd46005f10` | nový head po integračním commitu | Nové exact-pair review; merge až po schválení. |
| [#44](https://github.com/p-rum/kgmaker/pull/44) | `feat/t046-s03-testgen` | `792cf3ec302dab4b6f2ead816ab1911fe4b36022` | `cd5ee4847773b2d42e0281076394a77f56f18600` | Nezávislé review a navazující retarget; bez automatického merge. |
| [#45](https://github.com/p-rum/kgmaker/pull/45) | `feat/t046-s04-synthetic-data` | `cd5ee4847773b2d42e0281076394a77f56f18600` | `4a60b6110fa41d9a53fdad639915e5495a785159` | Nezávislé review a navazující retarget; bez automatického merge. |

### Větve bez PR a historický PR4

Všech 92 lokálně načtených remote refs (včetně origin/HEAD) bylo porovnáno s main. Větve bez otevřeného
PR jsou buď již obsažené v main, nebo `feat/compiler-workers` (head `f087725`).
Ta má jeden topologicky nesloučený merge commit, ale nulový patch proti společnému
předkovi. PR4 `feat/evidence-production-scope` má dva takové merge commity
(`f087725`, `b11c864`), rovněž nulový patch proti společnému předkovi.
`git diff main...origin/feat/evidence-production-scope` a stejná kontrola
`compiler-workers` vracejí prázdný diff. Nejde o prázdný rozdíl main proti celému
starému checkoutu: main obsahuje novější změny. Žádný původní patch PR4 nezůstává
k integraci; doporučení je samostatně uzavřít historický draft, zde nebyl změněn.
Ke dni historického auditu mělo všech šest T046 větví otevřená PR. Aktuální sloučení je zachyceno v atomických řádcích.

### Ověření tohoto auditu a pokračování

Repo checkout, task intake, source-only scan a cílená query byly provedeny.
Žádný worker/build/runtime/DB neběžel. Nové testy opisující dokumentaci nevznikly.
Přesné kontroly odkazů, 119 jedinečných řádků a git evidence jsou v change111.
Následuje T048-S02: zachovat existující T046 větve, ověřit jejich skutečné aktuální
kontrakty/testy a předat nezávislému review. T048 nepovoluje implementátorovi merge.
Po review a merge T003-S05-W04 pokračuje pořadí T048-S03 přes T003-S06-W05;
T047-S01 lze připravovat nezávisle podle původního zadání.

## Historické checkpointy — stav k jejich uvedeným SHA

Následující záznamy byly zachovány beze změny. Slova draft, candidate a pending
popisují tehdejší revizi; současné dodání určuje inventář výše.


## Předání dokončovacího programu — 2026-11-06

[T048](tasks/48_completeImplementationHandoff.md) koordinuje původní zadání nad
main `250e7c16250a97b9f8df5256b9894c8119dc64d9` po T020/PR #87. T003 má 37/60
balíčků se sloučenou prací (u S12-W01 pouze konfigurace, live DEFERRED); T004 má
24/40 dodaných úkolů: T005–T020, T023–T026, T030–T033. Zbývá 23 T003 balíčků a
16 T004 úkolů bez sloučené dodávky, otevřená integrace T046 a 13 kroků T047 se
sdílenými upstream kontrakty. Jde o delivery přehled, nikoli nové ověření acceptance.
T048-S01 má sjednotit jednotlivé aktuální stavy; starší řádky níže obsahují historické
checkpointy a místy již neaktuální draft/review status. Jejich testové výsledky
nejsou novým během nad touto baseline.

Každý další implementační krok povinně aktualizuje vlastní change note, dotčenou
aktuální dokumentaci a acceptance. Povinnost je v AGENTS i instalovaných host
instrukcích; chybějící nebo rozporná dokumentace blokuje dokončení kroku.


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

Lokální oprava klasifikace snapshotu pro Python 3.13 má 46 PASS / 0 SKIP
na Pythonu 3.12.14 i 3.13.5 se skutečným Javac/K1/K2. Smyčka odkazu se
zachytí jako `invalid`, chybějící cíl v projektu jako `missing`.
Hostovaný Python 3.13 na `d977f18` vykázal 2 421 PASS / 1 279 SKIP.
[Hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44930359814/job/136925433122),
[samostatný záznam opravy](changes/153_classifyLoopedJpaXmlInputs.md).
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

Aktualizace 2026-11-15: [change116](changes/116_parseExtendedJpqlHql.md)
dokládá explicitní přebuildování JARu/deskriptoru a 10 PASS instalovaných
exporter testů na Maven3.9.9/Gradle8.13/JDK21.0.13; historická evidence níže
se nepřepisuje a širší platform scope zůstává PARTIAL.

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

Automatický PR Review měl na #137 chybnou syntaxi vloženého Pythonu a
chybějící adaptér `pytest-cov`. Po nezávislém nálezu kandidát používá
SHA obou commitů z události PR, čte soubory z Git objektů headu a předává
coverage i stav testů jako data. Chybějící měření se zobrazí jako nedostupné.
Hostovaný běh `07c49d1` dokončil kroky review a zaznamenal selhání sběru
testů kvůli chybějícímu `jsonschema`. Kandidát doplňuje verzi `4.23.0` z
workflow Test. Hostovaný `11c5901` vykázal 2 371 PASS, 1 280 SKIP,
84 úspěšných subtestů a report 74 % pokrytí. Dodání je PR_OPEN a ověření
lokálního sběru, smoke i hostované opravy je VERIFIED_IN_SCOPE.
[#140](https://github.com/p-rum/kgmaker/pull/140),
[opravený job](https://github.com/p-rum/kgmaker/actions/runs/44932000190/job/136930443327),
[záznam a reprodukce](changes/154_fixPrReviewPythonAndCoverage.md).

| Oblast / etapa dokončení | Stav baseline | Implementováno a evidence | Zbývá |
|---|---|---|---|
| T003-S01 acceptance inventář | VERIFIED_IN_SCOPE | [řádkový inventář T001/T002](acceptance-inventory.md) uvádí stav, verzi, konkrétní test a běh; chybějící varianty jsou PARTIAL/NOT_IMPLEMENTED | Udržovat při každé změně scope/verze/běhu; implementační mezery řádků nejsou splněním jejich etap |
| T003-S02 lifecycle/provider | VERIFIED_IN_SCOPE | v1/v2/v3 store, provenance, atomický zápis; scan/hook/feature selektivně vyřadí stale compiler layer s důvodem/next command a zachovají ostatní; status/check/hook rozlišují source a compiler freshness bez spuštění procesu; module/profile contexts se akumulují; query/impact/feature/validate/report používají uložený explicitní scope/context a zachovávají společnou source/dataflow vrstvu; workspace schema v3 přenáší repo-qualified symbols/call sites/CFG/evidence/annotations; reálný `test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle` plus provider/workspace regrese | Rozšíření podporované matice patří do navazujících S03–S10; není tvrzena úplnost mimo zdokumentovaný scope |
| T003-S03 build a scope | PARTIAL | Maven reactor/EventSpy a content-bound `--java-home`; skutečný reactor/generated-source test. Gradle W02 validuje explicitní SourceSet scope a freshness, W03 exportuje snapshot-bound included builds s jednoznačným output realm a ordered classpath. W04 přenáší validované task/execution-level Kotlin compiler/language/API/JVM options, flags a plugin provenance do manifestu a context identity; `test_kotlin_build_options.py` ověřuje Maven 2.1.10, Gradle 8.13, selektivní invalidaci a fail-closed tamper. Workspace `release_mapping` v1 propojí validní regular-file BuildManifest output s regular-file fresh compiler classpath podle SHA-256; `test_cross_repo_artifacts.py` dokládá tento omezený scope; konflikt či adresář zůstávají PARTIAL. | Další Gradle variant API a úplná produkční matice; zachycená konfigurace nerozšiřuje K1 analyzér |
| T003-S04 JVM/Kotlin | PARTIAL | Opt-in K2 Analysis API 2.1.10 named-function call subset (`tests/test_k2_backend.py`, change35); JavacTask, K1 compatibility, ASM, 5 ground-truth direct calls with overloads/CFG; izolované testy ověřují konstruktor, primary-constructor property/init pořadí, file-facade `<clinit>`, oddělený object constructor realm, lambda caller, callable reference, source-defined operator v CFG, custom getter/setter method+CFG+ACCESSOR a extension/default/inline/suspend metadata; when/Elvis/short-circuit/try/finally/break/continue mají strukturovaný IR/CFG; `test_compiler_workers`, `test_control_flow` a JVM rendering; W02 dodává bounded Java/Kotlin DefaultImpls a bridge declaration mapping s přesným owner/name/descriptor, realm/ABI guard a bytecode-only diagnostics (`tests/test_default_body_mapping.py`); bounded compiler suspend/async boundaries a DebugMetadata continuation declaration mapping v `test_coroutine_mapping` | K2 širší source call/CFG matice a obecné coroutine state-machine CFG/runtime scheduling, další generated shapes, default-argument masks, statement-level LOC, širší corpus, úplná acceptance banka |
| T003-S05 Spring | PARTIAL | Spring rules v7 zachovávají context-bound `FRAMEWORK_DERIVED` bean/injection, qualifier/primary, ACTIVE/INACTIVE/UNKNOWN conditions, bounded imports/registrar/FactoryBean subset a v6 typed condition matici. W04 navíc odděluje advice declaration od bounded JDK/CGLIB `may_traverse_proxy`/`may_apply_advice`: vyžaduje externí compiler call, unikátní ACTIVE injection, specializovanou ACTIVE policy a interceptable metodu. Self-call je synchronní bypass; Async/Event/Reactive jsou declaration boundaries s execution NOT_OBSERVED. Přímá evidence je `tests/test_spring_proxy_async.py` a [change114](changes/114_modelSpringProxyAsyncSemantics.md). | Skutečný runtime proxy dispatch/advice, scheduling, event delivery, reactive subscription a AspectJ weaving zůstávají UNKNOWN; actual-javac W04 fixture je bez připraveného workeru SKIP. Širší selectors/registrars/factories, conditions a class/meta varianty zůstávají mimo bounded subset. |
| T003-S06 persistence | PARTIAL | Flyway replay plus JPA rules v8: Entity/Embeddable/MappedSuperclass, Java/Kotlin FIELD/PROPERTY identity, inheritance/XML/realm/schema projections, derived queries a compiler-owned JPQL/native `@Query`; W05 přidává bounded join/subquery/bulk DML/constructor/path grammar s lokalizovaným PARTIAL/UNKNOWN | Širší Criteria/Specification/QueryDSL/Kotlin patterny mimo [W07 bounded matici](programmatic-queries.md), širší provider/native grammar, implicit Kotlin target policy a úplná multi-datasource/provider matice |
| T003-S07 integrations/dataflow | PARTIAL | Literály, service mapping, lokální field edges; S07-W01 compiler-proven Javac/K1/TS argument→declared-parameter bindings s named/default/vararg proof (change52); bounded return→consumer proof s oddělenou caller/body identity a source guards (change66); S07-W04 bounded declared Kafka cluster/topic/contract SHA/release + profile/context precedence; privacy rules `kafka-binding-2` reject sensitive aliases/redact captured public properties; `tests/test_kafka_bindings.py`, fixture `fixtures/kafka-bindings`, [note54](changes/54_scopeKafkaBindingIdentity.md) | Omezené canonical listener/send a explicitní schema2 code/group join jsou sloučené v [#69](https://github.com/p-rum/kgmaker/pull/69). Celá matice revize2 zůstává PARTIAL. Runtime delivery/retry/DLT a obecné Kafka/HTTP datové cesty zůstávají UNKNOWN. |
| T003-S08 TS/UI | PARTIAL | Program/TypeChecker, overloads a React event binding | Multi-project/re-export, callback a BE–FE value flow acceptance |
| T003-S09 artifacts/report | PARTIAL | Feature lifecycle/report, offline HTML docs; bounded XLSX sheets/cells/named ranges/formula dependencies and hash-bound locators; literal Thymeleaf model bindings, static exact-arity fragment provenance, condition/unsupported diagnostics and explicit PDF boundary; `test_feature`, `test_data_check`, `test_workbooks`, `test_templates` | Širší template mapping, schválená metodika a plný scénář; formula/template evaluation zůstává non-goal |
| T003-S10 incremental | PARTIAL | Semantic diff, workspace cache, Flyway checkpoints | Selektivní compiler/feature invalidace a negativní lookup dependencies |
| T003-S11 release/acceptance | PARTIAL | Sedm CI jobů; worker/exporter clean install na Linuxu a skutečný Windows non-admin core/Java/K1/TS smoke (43 PASS / 2 scoped SKIP) | K2 Windows, Windows BUILD_EXECUTE, immutable publikace, celá acceptance a benchmark budgets |
| T003-S12 Confluence boundary | VERIFIED_IN_SCOPE / LIVE NOT_RUN | Adapter protocol, `FAKE_TEST_ONLY`, explicit pull, managed-section diff, hash+base-version approval, optimistic concurrency, TO_BE re-import and audit; `test_confluence_sync` covers FA-28–30/AC12 | Live connector requires a documented host/API/auth contract and remains separately NOT_RUN |
| T003-S13 runtime | PARTIAL / OPTIONAL | V1 import + strict v2 export/import; explicitní JDK21/POSIX synchronní producer s call/factory/condition/map capture a negativními testy. [change122](changes/122_runtimeTraceProducer.md), [kontrakt](runtime-trace.md). | Automatický Spring capture, Windows, RTA/value flow, async/reflective capture a deployment/data availability; celý milník neověřen |

Dílčí ověření T003-S02 / AC02 pokrývá Javac LF/CRLF. Nový JVM snapshot svazuje
přesný výběr compiler vstupů a bajty zdrojů s normalizovanou strukturální projekcí.
Ověřeny byly replay T025 local operations, Criteria filtr, rozvinutí source CFG, statické
deklarace Kafka retry/DLT a offline invalidace po změně konců řádků. W02 selektivní
invalidace má vlastní acceptance. [Doklad přesného rozsahu](changes/160_bindJvmSourceBytes.md).

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

Po dvou selháních DNS v hostovaném `compiler-workers` je pro 2.1.10 ověřeno
explicitní stažení osmi připnutých JARů z JetBrains Packages a Maven Central
a skutečný lokální build K2. Cílené kontroly mají 51 PASS / 0 SKIP.
Hostovaný `compiler-workers` na `7345f02` ověřil novou adresu stejnými
kontrolními součty a skutečným buildem, zaznamenal 1 441 PASS / 1 SKIP
a dokončil explicitní Maven plan/runner/export.
[Hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44934058014/job/136936734963),
[Change 156](changes/156_restorePinnedK2Download.md).

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

T009 používá explicitně povolený PARTIAL/UNKNOWN fallback a samo nevytváří
skóre, inferovanou polaritu ani rozhodnutí o konfliktu. T003-S07-W08 nyní
dodává samostatný [omezený ranking](evidence-ranking.md), viz
[change126](changes/126_evidenceRanking.md). Ověření a
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

## T012 — Kafka interface catalogue (verified bounded scope)

Pure `interfaces.project_kafka_interfaces` reuses canonical upstream code and
binding validation, T008 ownership/context and T009 evidence. Explicit workspace
checkouts/private captures are required. Groups/realms and original listener/send
IDs stay distinct; config-only, unknown brokers and regex remain unresolved.
Java listeners/send and Kotlin K1 listener are bounded static support; Kotlin K2
annotations UNKNOWN, delivery NOT_OBSERVED. Kafka rev2 and Common dependencies
merged; all105 own tests PASS in combined descendant2df55 strict full2587PASS /
10exactoptionalSKIP2042.93s,4897hashes/five member sets unchanged. All2071 parent
IDs classified2061PASS10SKIP in that one run, not a standalone full. Corrected
actual selection10PASS/0SKIP; current-parent coalesced444PASS/0SKIP. Final exactpair
review/ready/merge separate. [Capability](kafka-interfaces.md), [change81](changes/81_catalogKafkaInterfaces.md).
Oprava #145 ověřuje shodu T012 a T019 na skutečných Javac zdrojích s LF a CRLF.
Katalog porovnává bajtový otisk s kvalifikovaným workspace inventářem.
[Doklad a hranice opravy](changes/160_bindJvmSourceBytes.md).
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

## T027 — HTTP boundary across explicit service processes

The explicit `project_http_process_boundary` API composes the merged
T014 remote binding and T025 `ProcessView` contracts. It joins only the HTTP
consumer's exact `origin_call_site` to a local CFG callsite and the matching
remote candidate's target service/context/handler. T014 incompatible selectors,
ambiguous sets, missing target CFGs and unmatched callsites remain external;
existing local continuations are retained. HTTP request/response is recorded
separately from `TRANSPORT_BOUNDARY_ONLY` errors; no runtime, availability,
business outcome or T004 completion is claimed. See [capability](process-paths.md),
[acceptance rows](acceptance-inventory.md) and [change123](changes/123_crossHttpProcessBoundary.md).
First independent review returned REQUEST_CHANGES for crossed response/exception
paths, missing version/stale/provider guards and dropped target coverage. The
corrections retain only normal-response witnesses, leave server exceptions as
transport boundaries, validate selected scope and preserve imported diagnostics,
limits and truncation. Actual focused regression: **187 PASS / 0 SKIP, 11.05 s**
with prepared JDK21/Javac/K1/K2. After the final terminal-only/request-origin guards, **38 PASS /
0 SKIP, 0.54 s** covers 29 public T027 cases and all 9 reviewer reproductions.
Requests originate only from the matching call node, so expanded callee exception
exits cannot start a new remote request and reach a normal continuation.
PR105 merged at `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`; historical approved HEAD `82eef329` integrated merged PR101–104 main
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf` without functional changes. New targeted run:
**200 PASS / 0 SKIP, 10.76 s**, actual Javac/K1/K2; both source trees and semantic
histories preserved. Independent integration review passed 200 tests / 0 SKIP in
13.00 s and approved the exact merge tree. Delivery status reconciled in change127. Full
suite and HTTP runtime observation are NOT_RUN. Exact commands are in change123.

### T006/T008 revize2 — shared context-role boundary (review pending)

Bounded source separates exact canonical workspace-derived Kafka declarations
from service-owned source and compiler selection, preserving the original full
graph/proofs, legacy SOURCE_ONLY and strict foreign-path/scope/hash guards.
Unknown producer/version/identity is diagnostic; role validity does not require
current private compiler replay. Pure coalesced matrix: **294PASS/0SKIP**,9actual
cases explicitly deselected,15.04s,606 frozen inputs unchanged. Read-only replay
of the fresh actual current-parent Kafka capture passed T008/T010/T011/T015/T024
with2CURRENT real compiler contexts, full graph/input/store unchanged and no
new worker execution. Final exact-source independent review/full remain pending;
T016 is not implemented by this change. [Note84](changes/84_classifyWorkspaceContextRoles.md).
## T003-S07-W05 — Kafka retry/DLT historické ověření

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
Oprava #145 ověřuje shodné W08 výsledky po explicitní inspekci téhož Javac
zdroje s LF a CRLF. Flyway snapshot i dostupnost dat mají stejné výsledky.
[Doklad cíleného ověření](changes/160_bindJvmSourceBytes.md).

## T010 normalized variant correction (2026-11-03)

Actual JSON declarations /orders/{id} and /orders/{name} with one method caused
DUPLICATE_NODE_ID. Rule2 preserves one explicit ambiguous boundary and both
candidate/provenance sets; exact duplicates and YAML distinct locators retain
existing behavior. Public RED3FAIL1PASS1.88s; corrected pure/provider34PASS2.12s.
Actual compiler focus149PASS/0SKIP; strict full493:1605PASS/10SKIP1683.18s with2105 unchanged inputs. Return-parent e740 composition284PASS/0SKIP219.41s with2113 unchanged inputs. Final metadata-head review/merge remain separate; no execution or deployment claim. [change88](changes/88_preserveAmbiguousHttpProviders.md).


## T006/T008 revize 2 — verified shared context roles (2026-11-05)

Current main 3e5ef0f; shared producer identity, classifier and inventory boundary
retain the original full graph, strict source ownership and historical role versus
freshness distinction. Actual focus 217 PASS / 0 SKIP; combined descendant2df55ff
strict full 2587 PASS / 10 exact optional SKIP, 2042.93 s, 4897 unchanged hashes
and five unchanged artifact member sets. Every Common-parent ID is included:
1956 PASS / 10 optional SKIP from one descendant full, not a standalone run.
T006-AC07–08 / T008-AC07–09 verified in scope; no availability promotion.
See note84 for preserved setup failure/correction and final review limitations.


## T013 — explicit interface contract attachments (verified bounded scope)

Shared bounded declaration capture and immutable attachment preserve original IDs,
technical status, evidence buckets, role-separated operation/schema/revision
references and stale generated-client origin. Type IDs remain UNKNOWN without
upstream payload-reference proof; DTO names never prove compatibility. All45 own
tests PASS in ONEcombined2df55 strict full2587PASS10exactoptionalSKIP2042.93s;
ALL2116parentIDs=2106PASS10SKIP,4897hashes/five member sets unchanged. This is not a
standalone full. Current-parent focus444PASS/0SKIP; actual captured Kafka K1/K2
revision/type-reference cases passed. T012/Common dependencies merged, no native
extension, network/schema fetch or generator execution. Final exactpairreview and
merge separate. [API/limits](interface-contracts.md), [change85](changes/85_attachInterfaceContracts.md).

## T030 — process-label packet (final review candidate)

Pure Python API preserves bounded immutable process identity/evidence/context,
structured conflict and privacy/budget contracts; no model/compiler/file I/O or
apply. Source unchanged from reviewed070/6ae; current base main2a38706.
ONE actual combined descendant2df55 strict full2587PASS10allowedSKIP2042.93sJUnit,
4897hashes+5recursive inventories unchanged, Root+architect verified all2597 IDs.
T030 ALL1990parent IDs1980PASS10allowedSKIP; all47ownPASS. Original32AST/35globals
and module byteprefix +whole testfile preserved; addedT031 bindings do not shadow.
See note90 and validation/t030-descendant-proof.json. No standalone parent full or
new native build. Exact final base/head review and publication remain separate;
GHCI optional/unverified. T031+ is outside this PR; no runtime/business approval.

Current main2a (Common/T012/T013 merged) requires all2116current-main parent
identities plus47T030 cases:2163total,2153PASS10sameallowedSKIP in actual2df.
OriginalT0301990 is also fully contained. This is an exact source/ID-union proof,
not a new parent collection/full/test execution. Original47own cases remain PASS.
## T046 — Šablony, testovací návrhy a dohledatelnost

T046-S01–S06: implementováno v omezeném offline kontraktu popsaném v
[delivery workflow](delivery-workflow.md). Projektové šablony, konzervativní výběr
funkcionality/frameworku, host-agent proposals, citace, syntetické JSON/CSV data,
content-bound revize, export bez přepisu, explicitní obousměrné vazby a lokální
rozhodnutí jsou dostupné. Brány jsou volitelné, default off; review binding
používá skutečný source fingerprint. V1 se čte, implementace/review doplní v2 bez
změny ID. Tím se nemění stav ostatních T003/T004 acceptance.

Ověření: `tests/test_artifact_templates.py`, `tests/test_delivery.py` a
`tests/test_synthetic_data.py`; doplněné výsledky v change notes 56–61. Lokální
unittest E2E prokáže citlivost exportovaného testu na změnu chování. Pytest,
nezávislé review a GitHub CI nejsou tímto zápisem označeny za úspěšné. Širší
frameworky mají návrhový kontrakt, nikoli univerzálně ověřené execution adaptéry.
Očekávání z kódu není business oracle, syntetická data nejsou runtime proof a
LOCAL_DECLARED není autentizace. Freshness je konzervativní přes celý snapshot.

### T046 — opravy review z 2026-10-27

Šest nezávisle reprodukovaných nálezů je opraveno: create-or-load race, export
přes nekanonické cesty, JSON enum, chybějící FK target, implement gate přes
record/save a ignorovaná journal CAS volba. Regresní sady navíc chrání historii
a review bindings. Původní 198-testový výsledek není důkazem těchto oprav; nové
výsledky a přesné revidované SHA jsou doplněny v change notes 56–61 a v PR.
Merge zůstává podmíněný novým review a ostatními povinnými kontrolami pro nové revize; GH CI je podle T045 revize 2 doplňující evidence.

CI revizí T046 samostatně kontroluje i generované grafy každého inkrementu.
S01–S06 mají vlastní aktualizované semantic/GRAPH snapshoty; jejich správnost
není odvozena pouze z integračního S06.


T046-S01 až S06 jsou po exact-pair review sloučené. S06 integrovalo opravený
create/CAS, immutable-history, template/testgen/data a approval základ do CLI
a instalovaných instrukcí. Přesné aktuální výsledky jsou v atomickém řádku,
change notes 56–61 a post-merge change113.
## T003-S07-W07 — verified bounded source; dependency merge pending

See [remote mapping contract](remote-contract-mapping.md)
and [note91](changes/91_planRemoteContractMapping.md).
Explicit capture and pure resolution preserve service/context/contract/release
authority; HTTP and Kafka remain distinct declared boundaries, no JVM calls or
runtime/payload availability promotion. Source-specific cohort334 unique PASS;
combined descendant2df full2587PASS/10optionalSKIP includes all1973 W07-parent
cases (1963PASS/10SKIP). This full did not run standalone on W07. Current-parent refresh preserves exact tested source; dependency merges are complete, final independent review remains pending.

Pure `prepare_process_label_packet` preserves complete ProcessView target/ref
identity, actual content binding and captured evidence/uncertainty. Raw prose is
hash-omitted; document provenance is explicit ref-only and conflicts are supplied
review items, not NLP authority. Full serialized cost includes omissions/template
and a stable-width overflow flag. Tiny budgets keep validation IDs; invalid/hard
inputs fail without mutation or I/O. Unicode/code-path IDs are retained.
Corrected coalesced pure153PASS/0SKIP4.07s; required full and independent
exact-source review remain pending. T031/T032 apply/review and T034 CLI are not implemented here.

## T031 — read-only process annotations (final review candidate)

Pure API rederives the whole current T030 packet before accepting semantic-only
PROPOSED text/refs/groups; conflicting fields and structured documentary conflicts
remain PENDING/CONFLICT for review. No technical apply or approval. Currentmain
5ffe099 has merged T030/Common/T012/T013/W07 prerequisites.
Whole module/testfile exactactual2df55; originalT03032AST/35globals/byteprefix
preserved,6added bindings disjoint. All76ownXMLPASS in ONEcombined descendant
2587PASS10allowedSKIP2042.93s;4897hashes+5inventories unchanged. Original2066parent
cases2056PASS10SKIP; currentmain2252+76 source/IDunion2328=2318PASS10sameSKIP.
Not standalone parent full, new collection or test/build/fullrepeat. Main240episode
prefix and every old capture preserved. Exact finalreview/publication separate;
GHCI optional/unverified. See note92 and validation/t031-descendant-proof.json.

Pure same-module validation rederives the whole current T030 packet and accepts
only bounded semantic PROPOSED records. Invalid/stale/forged/unsafe inputs return
fixed-code REJECTED validation reports; valid input remains PENDING/CONFLICT with
all differing proposals and captured documentary review items. No approval/apply,
new outcomes, technical mutation, NLP comparison, runtime or physical freshness.
Explicit stack on T030070 retains all47T030tests and32original module AST nodes.
PublicRED6FAIL0.40s, currentcoalesced229PASS0SKIP6.22s (76new+153inherited). Required
full, independent exact source review and root publication remain pending.

## T032 — explicit local review (historical checkpoint, 2026-11-07)

Currentbase2c7b38 has mergedT030/T031 prerequisites. Separate bounded immutable
semantic envelope, POSIX cooperating process/thread CAS, exact operation identity,
baseline revalidation and honest postreplaceINDETERMINATE recovery. No technical
ProcessView/evidence mutation, document citation promotion or reviewer authentication.
APPROVE blocks both proposal/captured conflicts; REJECT publishes no new labels.
Whole store module/testfile/currentprocess_semantics exactactual2df55. All36own
XMLPASS in ONEcombined2587PASS10allowedSKIP2042.93s;4897hashes+five sets unchanged.
Original2102IDs2092PASS10SKIP; currentmain2328+36union2364=2354PASS10sameSKIP.
No standalone parent full or new test/build/fullrepeat. Main241episodeprefix/all
oldcaptures preserved. Final independentexactpairreview/Rootmerge pending; GHCI
optional/unverified. See note94 and validation/t032-descendant-proof.json.

Explicit stack on reviewed T031a359. Separate version1 envelope,128history/2MiB caps,
POSIX cooperating thread/process CAS, exact idempotent operation identity and current
explicit-baseline revalidation. APPROVE blocks captured and proposal conflicts;
REJECT publishes no new labels. Technical model/evidence remains unchanged.
Current feature36PASS1.93s; coalesced269PASS94SKIP8.74s (compiler SKIPs not PASS).
Independent source review and strict full NOT_RUN. No native build, CLI, external
publication, authenticated reviewer identity or hostile-root race guarantee.

## T033 — explicit process catalog (final review candidate)

Currentbase7e6c83 has mergedT030/T031/T032. Read-only explicit current/historical
ProcessViews+T024 inventory and direct validated T032 reads, stable process+scope
selection IDs, exact collisions/one-hop aliases preserving all original members/
revisions/triggers/review states. No label identity/approval borrowing/archive/
discovery/store writes. Partial absence NOT_IN_CURRENT_INVENTORY stays qualified.
Wholecatalog/test+5process dependencies exactactual2df55. All37ownXMLPASS in ONE
combined2587PASS10allowedSKIP2042.93s;4897hashes+5inventories unchanged. Original
2139parent2129PASS10SKIP; currentmain2364+37union2401=2391PASS10sameSKIP. No new
test/collection/build/fullrepeat. Main242episodeprefix/alloldcaptures preserved.
Finalexactpairreview/Rootmerge pending; GHCIoptional/unverified. See note96 and
validation/t033-descendant-proof.json. Runtime/data availability remain UNKNOWN.


## T014 — remote topology current-parent review candidate

Pure ViewDocument adapter on reviewed W07/T013 stack; retains every candidate,
unknown target and capture-time uncertainty. No resolver duplication, source I/O,
JVM/process edges or runtime/payload promotion. Public pure validation is recorded
in note93. Current509 retains merged Common/T012/T013/W07/process source. Owned
module/test bytes and all present runtime/test/worker/fixture files match accepted
2df55, except pending T019 CLI dispatch is correctly absent. Accepted descendant
full2587PASS10allowedSKIP covers all2425 current-parent IDs (2415PASS10SKIP);24own
PASS. No new actual/full/build. Final exact-pair review/merge remain pending;
see docs/validation/t014-descendant-proof.json.

## T016 — current-parent common-capture review candidate

One explicit snapshot closure composes T015/W07/T014 and verifies it again before
returning a handoff. Pure aggregation uses catalog services/resources and reversible
remote origin inventories, Kafka channels/groups, original proof buckets and UNKNOWN
remote runtime/freshness. Currentec6a127 retains merged T014/T015/Common/T012/T013/
W07v2 and process bodies/CI. Owned module/tests are exact accepted2df; all46own
cases XMLPASS. Collection-only2425main+46own union2471 maps2461PASS10same optional
SKIP on accepted2587PASS10SKIP full. No actual/full/build/tool mutation; independent
current-pair review remains pending. See note95 and validation/t016-descendant-proof.json.

## T017 — current-parent bounded filtering review candidate

Pure API over an existing T016 view: exact service focus, deterministic real-edge
hops and node budget, context/relation restriction and complete known omission
inventories. New frontier entries are metadata rather than graph nodes. No shortcut,
runtime/availability claim or ambiguity/freshness/evidence upgrade occurs. Public
absent-API RED2FAIL; corrective retained-expansion privacy RED1FAIL29PASS; final
33 own tests plus coalesced T016/T014/View/T009: 149 PASS in1.58s. No heavy queue,
native build or full at that historical source checkpoint. Current130720f preserves
merged T014/T016/Common/T012/T013/W07/process/CI. Owned source/tests exactaccepted2df;
all33own cases XMLPASS. Collection-only2471parent+33own=2504 maps2494PASS10sameSKIP
on the oneaccepted2587PASS10SKIP descendant. Root is author, not independent reviewer;
architect plus another independent final-pair review remain mandatory. No new full/
build/tool mutation. See [note97](changes/97_filterTopologyScope.md),
[proof](validation/t017-descendant-proof.json) and [API](topology-filter.md).

## T018 — current-parent snapshot explanation review candidate

Pure explanation rederives T016/T017 and expands exact original identities and
proof buckets. Original PUBLIC graph is required for canonical source locators;
missing graph/range is unavailable. Separate explicit confined source-status
capture checks current file hashes without replacing original snapshot fingerprints
or upgrading remote/context freshness. Public pure/file-backed tests are recorded
in note98. Current4e4fcd6 preserves T014/T016/T017/Common/T012/T013/W07/process/CI;
owned source/tests exact299/accepted2df, all59own XMLPASS. Collection-only2504parent
+59own=2563 IDs maps2553PASS10same optionalSKIP on the oneaccepted2587PASS10SKIP
full. No actual/full/build/tool mutation; current exact-pair independent review
remains pending. See validation/t018-descendant-proof.json.

## T019 — current-parent architecture JSON review candidate

Snapshot-only default wraps existing T014/T016/T017/T018 APIs without reselection.
Explicit capture-local preflights all original indexes before parser work, never
publishes indexes/caches; explicit check-source remains separate. Coalesced pure
CLI/dependency checks: 307 PASS, 10 actual cases deselected, 5.29s. No worker/native
build or full was run at that historical source checkpoint. Current1005b9f+34own
union exactly equals accepted2df2597 IDs:2587PASS10same optionalSKIP. ALL302present
runtime/test/worker/fixture/CI bodies match acceptedfull, including exact5-line CLI
registration/dispatch. No new actual/full/build/tool mutation. Current independent
final-pair review remains pending; T020/21not included. See note99,
[proof](validation/t019-descendant-proof.json) and [CLI contract](architecture-json-cli.md).

## W07/T014 — first-call purity correction (note108)

Root's import relocation preserves helper algorithm/VERSION2 and pure first-call
behavior (historical25T014PASS on869ab). Source91ca continuation006 is terminal:
1176PASS/1typedoptionalSKIP, XML575.90s/runner618.34s. The verified source-corrected
aggregate is2737PASS/10typedoptionalSKIP across2747IDs, combining1561PASS/9SKIP
on304 with current1177 and rerunning all102 explicitly affected cases. Never
label this a fresh single full or an original failed-attempt wholesale PASS.
Main-only cold publication2598 derives2588PASS/10SKIP with exact per-ID source,
origin XML, complete phases and typed skip policy. Its302source paths keep main
CLI/workflow and exclude renderer additions; common corrected source/test bytes
and helper globals are preserved. Actual SVG15+4 passed in the external aggregate,
which also verified1364kindroots/94333entries and80637fresh hashes unchanged.
Main248immutableepisodes plus one historical Rootcold capsule are retained. The
old capsule's unknown validation fields remain historical and unchanged. Runtime,
tests and native bytes were not changed or rerun for terminal metadata recording.
Architect and resume_t010 FINAL reviews on the new base/head remain PENDING;
Root is the original author and merge guard only. See note108/per-ID ledger.

## T020 — interface Markdown source candidate

Explicit stack T019 abad2e3; Rev2/root architecture approved before code. Pure
ViewDocument renderer and interfaces-only CLI format preserve IDs/context/evidence,
contract revisions, Kafka realm/group and generated/unclassified rows. Public
RED4FAIL1.08s → initial GREEN4; expanded safe/shape/parser/source-contract matrix
43PASS0.94s; T019 compatibility plus renderer77PASS4.37s; expanded pure closure
176PASS6.59s covers model/T010/T013 and the final namespace-collision regression.
Dev-only hash-pinned GFM parser isolated from shared venv/cache, table AST validated.
Native/heavy/full NOT_RUN; current source checkpoint awaits independent review
before staging. No whole T004, runtime, payload compatibility or deployment claim.

T020 current corrected renderer checkpoint446ddbe:49PASS1.24s, including explicit
validated content fingerprint checked against independent supplied-JSON SHA256.
Root independent SOURCE_APPROVE covers complete renderer/CLI/test source; final
metadata descendant preserves exact runtime/tests. Earlier176/48 are historical
source-attributed checks. Dependency/current-main/full/merge gates remain pending.


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

[T049](tasks/49_separateTargetAgents.md) · S01–S07 PLANNED · ověření NOT_RUN. Návrh pokrývá init, projektové profily, souhlas pro commit/push a migraci. Implementační evidence zatím chybí.

## T003-S07-W03 — field/mapping source evidence (2026-11-15)

Dodání MERGED ([PR104](https://github.com/p-rum/kgmaker/pull/104),
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf`), ověření PARTIAL v omezeném Javac/MapStruct scope.
Historický integrační běh 166 PASS / 0 SKIP, 67.84 s; nezávisle 166 PASS / 0 SKIP,
68.33 s. PR105 zachovává obsah W03 zdrojů a testů.
[Change124](changes/124_fieldAndMappingFlow.md) uvádí skutečné běhy a baseline;
[matice](field-mapping.md) odděluje direct field transfer od business/runtime
důkazu. Staré SOURCE_ONLY a graph/store v1/v2/v3 zůstávají čitelné.
Full suite odložena dle výslovného pokynu uživatele až na celý balík.

## T037 — invalidace odvozených pohledů (2026-11-15)

T037-S01–S05 jsou dodané v [PR103](https://github.com/p-rum/kgmaker/pull/103);
delivery MERGED na `b1a8ba1f4234cd399de8319fcf5cde2c670dac26`, ověření PARTIAL
v dokumentovaném scope. Integrační HEAD `03aaf0d` má nezávislé APPROVE a
298 PASS / 0 SKIP, 21.57 s; PR104 zachovává cache kontrakt a fingerprint helper.
Explicitní `view_cache.get_or_build_view` váže celý public workspace/graph,
contexts, rules, scope a context selection. Cache miss rebuildí celý view, takže
zachytí i přidané provider inventáře; není deklarována selektivita ani runtime
fresness. Cílená sada je v `tests/test_t037_invalidate_derived_views.py`;
konkrétní příkazy a výsledky jsou ve [change121](changes/121_invalidateDerivedViews.md).
README, architecture capability, CLI hranice, acceptance inventory a API příklad
odkazují na [T037 API dokumentaci](view-cache.md). Nezávislé review nad `43d7010`
vrátilo REQUEST_CHANGES: předčasná cache publikace, kopie místo původního snapshotu
a ztráta nesouvisejících semantic entries. Oprava odděluje prepare/publish, chrání
vstupní a source cesty, ověřuje skutečný původní snapshot a obnovuje původní vazby.
Cílená sada: **296 passed in 10.96s**; po finálním cleanup při přerušení zápisu
dotčený T037 modul **76 passed in 4.65s**, 0 failed/skipped. Jde o historické výsledky nad původní T037 dodávkou. Původní HEAD ed79c3b
prošel nezávislým APPROVE; nové integrační testy a kontrola zachování obou
semantic historií jsou v [change121](changes/121_invalidateDerivedViews.md).
Full pytest, remote PR CI a libovolné produkční workspace/toolchain acceptance
jsou NOT_RUN; T004 zůstává nedokončený.

## T028 — Potential Kafka process continuation

The pure `project_async_process_boundary` API composes source-backed T012 identities,
individual T014 memberships and supplied T025 CFGs. Derived publish/channel/subscription
steps retain partial order: consumer paths do not order each other and do not return
to publisher completion. Source call-site identity and target listener/service/context
are required; duplicates, conflicting selectors, stale evidence, missing consumers,
loops and expansion limits stay explicit. Static binding is not instance correlation;
all supported inputs leave that claim UNKNOWN with no correlation evidence refs.

Historical initial handoff `1732a3d` over `93c52d33`: **242 PASS / 0 SKIP,
136.07 s** across T028/T012/T014/T025/T027 with actual JDK21/Javac and prepared
K1/K2 worker configurations. Final bounded-input follow-up: 42 PASS / 0 SKIP,
20.18 s including actual pipeline; Kafka-only metadata follow-up: 66 PASS,
2 deselected, 1.21 s. That initial handoff's 43 T028 cases include the real public pipeline and
adversarial reachability checks. Full suite, application/Kafka runtime and GH CI are
NOT_RUN; no data or delivery availability claim follows from these static tests.
See [change127](changes/127_crossAsyncProcessBoundary.md) and
[API/capability examples](process-paths.md#potential-asynchronous-process-paths-t028).


T028 PR108 independent review found two AC05 blockers after the original handoff:
stale endpoint/binding proof authority and duplicate release selectors across
binding objects. Both are addressed in [change127 steps 7–8](changes/127_crossAsyncProcessBoundary.md).
Current targeted result: **264 PASS / 0 SKIP, 138.32 s**, including all four reviewer
reproductions and actual JDK21/Javac/K1/K2. Raw proofs survive unchanged, directly
or inside an explicit UNKNOWN reference-only envelope with gap diagnostics. The
envelope never authorizes expansion. Global membership conflicts retain every
boundary while different canonical endpoints/groups and explicitly compatible
versioned endpoints keep independent potential paths. New independent review of
the published fix remains required; original review is REQUEST_CHANGES, not APPROVE.


## T003-S07-W08 — vysvětlitelný ranking (2026-11-15)

Dodání MERGED ([PR106](https://github.com/p-rum/kgmaker/pull/106), main `8e7dff5b82597184662797c07a68e5ec460e9e0e`), ověření VERIFIED_IN_SCOPE nad integračním main
`93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`. [Change126](changes/126_evidenceRanking.md)
odděluje implementaci, opravu provenance projekce a skutečné cílené testy.
`execution-2`/`impact-2` zachovává původní klíče JSON a doplňuje contributions,
path a coverage/gaps. Každé skóre má reprodukovatelný rozklad; test/type/config
reference nezvyšují production execution, runtime vzorek neuzavírá statický dispatch.
Skutečný Javac/JDK21 test používá [fixture](../fixtures/evidence-ranking/README.md);
syntetické schema fixtures netvrdí compiler či runtime PASS. Full suite a GH CI
NOT_RUN dle uživatelského targeted-only pokynu. Nadřazené S07 zůstává PARTIAL;
W09 a S09-W05 nejsou tímto dodány.


### T003-S07-W08 — opravy nezávislého review PR106

Reviewed HEAD `e0bfd41b13fe0190e5608f88964a0eef36f274de` měl dva P1 nálezy:
STALE proof records se započítávaly přes aktuální context a METHOD_REFERENCE
mohla potlačit runtime-only gap. [Change126 kroky6–7](changes/126_evidenceRanking.md)
opravuje oba kontrakty i konzistenci cest. Historický pre-merge checkpoint PR_OPEN, tehdejší ověření
VERIFIED_IN_SCOPE: **96 PASS / 0 SKIP, 3.20 s**, včetně skutečného Javac,
veřejného CLI nad stale proofs a 10 compatibility variant invocation kindů. Dvě nezávislé reprodukce prošly; předchozí
REQUEST_CHANGES tehdy vyžadovalo nové nezávislé review; následné APPROVE a merge jsou doloženy níže. Historický72PASS
nebyl důkazem správnosti těchto případů. Full/GH CI nadále NOT_RUN.


### T003-S07-W08 — druhé review, authority a izolace variant

Reviewed HEAD `7169e88d97595694bf7591117c683716bb812218` opravil první dva P1,
ale nezávislé review doložilo další dva: SOURCE_ONLY/bare kontext mohl získat
execution weight ze silnějšího edge labelu a mixed-context hrana přitáhla druhou
compiler variantu. [Change126 kroky 9–10](changes/126_evidenceRanking.md) nyní
vyžaduje skutečný zachycený inspection tuple/source binding a vynechává celý
neizolovatelný claim s konkrétní boundary diagnostikou. Source provenance zůstává.
Nové cílené ověření: **173 PASS / 0 SKIP, 3.50 s**, navíc context selection/role
regrese **31 PASS / 1.23 s**; oba soubory nezávislých reprodukcí **4 PASS / 0.14 s**.
Actual Javac/public CLI zůstává pozitivním důkazem; schema model není native PASS.
Historický stav před merge byl PR_OPEN, verification VERIFIED_IN_SCOPE;
původní REQUEST_CHANGES následně uzavřelo nezávislé APPROVE nad HEAD `9117c801`.
PR106 je MERGED (8e7dff5b); Full/GH CI a celý S07 nadále neuzavřené.

## T003-S07-W09 — unified flow views (2026-11-15)

Dodání MERGED ([PR109](https://github.com/p-rum/kgmaker/pull/109)) v `cceb1109`; schválený HEAD `999e60f` a jeho source zachovány v T029 integraci (change130 krok8). Historické ověření níže zůstává oddělené od merge.
[Change128](changes/128_unifiedFlowViews.md) zaznamenává model a skutečné testy
odděleně. `flow-view-1` přidává společné pořadí z CFG, coverage/provenance a tři
formáty pro control-flow/process/integrations/data-flow. Relation view není CFG.
Source/legacy bez CFG je UNKNOWN, invalid input zůstává chyba; statická expanze
vyžaduje sdílenou W08 authority. Výstup `.kgmaker/flows/` je atomický a abort
zachovává poslední validní generaci. Předintegrační cílená matice349 PASS, následné
exact-proof regrese221 PASS, skutečný Javac21 a Mermaid11.4.1 parser ověřeny.
Native Kotlin/TS binding regrese nedokládají novou obecnou CFG podporu. Finální integrovaná sada293 PASS / 0 SKIP / 46.72 s zahrnuje T028, přímé
argument/return flow, actual BEFE relation view a cache/legacy regrese. Whole S07 a full/GH CI nejsou tímto prohlášeny za hotové.
R07 publication guard byl ověřen samostatně po tomto checkpointu: **84 PASS /
0 SKIP / 9.30 s**, vlastní W09 + provider + workbook regrese. Exact index bytes,
initial scanner inventory a source/legacy/binary late mutation nedovolí přepsat
last-valid výstup zastaralým reportem. Tento fix nebyl součástí historické293 sady.
Nezávislé [review PR109](https://github.com/p-rum/kgmaker/pull/109#issuecomment-6900427853)
nad028cb7c doložilo dva P1: foreign caller a stale caller CFG přesto expandovaly.
Opravy v [change128 kroky12–13](changes/128_unifiedFlowViews.md) kontrolují každého
root/nested CFG vlastníka a source occurrence před expanzí. Finální cílená sada
**429 PASS /0 SKIP /78.90 s** včetně actual Javac/K1/K2/TS/Mermaid; doplňující
actual binding/guard/repro sada **38 PASS /3.46 s**. Zachované
reference-only bindings nepřidávají call/return cestu. REQUEST_CHANGES vyžaduje
nové nezávislé review opraveného HEAD; dodání zůstává PR_OPEN.



### T028 / PR108 — integration of merged ranking/context projection

PR106 merged at `8e7dff5b82597184662797c07a68e5ec460e9e0e` after independent
APPROVE ([merge audit](https://github.com/p-rum/kgmaker/pull/106#issuecomment-6899380938)).
Its verified parents are `93c52d33` and `9117c801`, tree
`21b6e0fbfa4f7b863c5141361c86e1b96e7cce10`. PR108 integrates that actual main
into fixed T028 HEAD `284dc68`; its delivery at that historical handoff was PR_OPEN.
Independent review subsequently approved HEAD8f023bc6; PR108 is MERGED at9f538634
([audit](https://github.com/p-rum/kgmaker/pull/108#issuecomment-6899650441)). Source/test byte identity preserves both independently tested changes.
Only generated graph/semantic and appended progress/acceptance sections conflict;
all histories are retained. [Change127 step 10](changes/127_crossAsyncProcessBoundary.md)
records the new context/projection/T025/T028 targeted evidence separately from the
prior 264 PASS and the upstream ranking 173/31/4 PASS runs. Full suite NOT_RUN.

New PR108 integration run on both preserved parent trees: **158 PASS / 0 SKIP,
28.09 s**, covering T028/T025, T006/context roles, production scope/graph provider
and all four review108 repros. Actual JDK21/Javac/K1/K2 pipeline remains supported
with the stricter merged `views.project` isolation. No additional functional fix
or source conflict was needed; upstream ranking/scoring tests were not needlessly
repeated. Semantic union and generated graph audit are recorded in change127.

PR107 now integrates the actual PR108 main9f538634 while preserving both parents'
source/test contents. This is an integration only; W05 remains PR_OPEN and awaits
independent review. Scoped workspace/remote/process verification and semantic
preservation are recorded in [change125 step11](changes/125_backendFrontendValueFlow.md).

## T029 — Static failure projection (2026-11-15)

Historical pre-merge delivery PR_OPEN; verification VERIFIED_IN_SCOPE on actual main `9c86d29`. New integration: **203 PASS / 0 SKIP, 74.02 s**, T014/T028/T029 + three actual reviewer reproductions + report projection/publication (change130 step12). Source byte identity preserved. Historical integration on main `83999fb`: 345 PASS / 0 SKIP, 83.01 s (T014 + T025–T029 and all three actual reviewer reproductions); change130 step11. The former 301 PASS checkpoint predates the second membership correction.
[Change130](changes/130_projectProcessFailures.md) separates RED, actual fixture
repairs, implementation, final diagnostics fix and real test runs. The pure API
preserves all catch/finally CFG paths and only attaches validated static retry/DLT
policy boundaries at matching selected exceptional exits of canonical Kafka entries
or witnessed T028 consumer imports. An ordinary call of the same listener retains
an UNKNOWN boundary; annotation identity alone is insufficient. Java/K1 Spring Kafka
3.3.2 is positive; actual K2 Kafka annotation absence is an explicit UNKNOWN test.
Raw rejected proofs and relevant diagnostics/truncation survive. Local transaction
declarations do not establish remote rollback; compensation is only PROPOSED
semantic annotation. Public [API examples/limits](process-paths.md#static-failure-projection-t029).

Historical initial checks: 281 PASS / 0 SKIP, 44.31 s before the diagnostic
retention guard, then 60 T029 PASS / 0 SKIP, 13.02 s. Independent review on
`7dee1dd` passed 285 checks but found two actual invocation reproductions failing.
Historical first review-fix: 75 PASS / 0 SKIP, 36.24 s (73 public T029 + 2 actual Java reviewer reproductions), with history and limits in change130 step6. No flow.py/worker
change. Full suite and runtime NOT_RUN. Actual Kafka3.2.0 version matrix NOT_RUN
because its pinned JAR is unavailable; supported 3.3.2 capture is not a substitute.

T028 downstream membership preservation is an additive PR110 correction, documented
in [change130 steps9–11](changes/130_projectProcessFailures.md). Its tuple keeps
original IDs/raw proofs; endpoint evidence cannot replace a mapping declaration.
Existing T028 delivery remains MERGED; this correction is PR_OPEN and the current
verification is recorded separately from the historical 301 PASS above.

Second PR110 membership correction: **177 PASS / 0 SKIP, 71.60 s** in T014/T028/T029
and all three reviewer reproductions before the separate main83999fb integration;
see [change130 steps9–11](changes/130_projectProcessFailures.md).


## T003-S06-W07 — bounded programmatic query intent (2026-11-15)

Delivery MERGED ([PR111](https://github.com/p-rum/kgmaker/pull/111)) v `83999fb`, schválený HEAD `c57b57f`; verification VERIFIED_IN_SCOPE pro [Java/Javac
matici](programmatic-queries.md), nikoli celý S06. [Change129](changes/129_criteriaSpecificationQuerydsl.md)
odděluje initial RED, where replacement/clear fix, duplicate-qualified-entity
fail-closed, strict IR validation a opravy nezávislého review v krocích11–14.
Korekční targeted běh nad baaf573 (base main7bb8b8d):
**147 PASS /0SKIP /85.27s**, včetně45W07 a actual Jakarta3.1, SpringDataJPA3.4.2,
QueryDSL5.1 APT a rebuilt JDK21 workeru. `filters_by` vzniká jen ze spotřebovaného
predikátu; query text zůstává null a runtime/data availability UNKNOWN.
Full suite a GHCI NOT_RUN dle targeted-only zadání. K1/K2 programmatic Kotlin
corpus, další operátory/provider syntax a libovolný production corpus nejsou
tímto ověřeny. Historické134PASS,132PASS a127PASS/2setupERROR zůstávají oddělené.
Pozdější změny builderu nepřepisují executable snapshoty; opakované snapshoty jsou
UNKNOWN; QueryDSL attributes vyžadují final člen a Specification skutečný
compiler override. V1 intent replay odmítnut, explicitní reinspection vytváří v2.
Opravený HEAD `c57b57f` byl nezávisle schválen a sloučen; T029 integrace jeho source zachovává beze změny (change130 krok11).
Aktuální ordinary merge W09 maincceb do844c zachovává obě source varianty beze
změny. Nové kombinované cílené ověření: **397 PASS /0SKIP /95.57s** (W07, W09,
ORM/protocol, CFG/ranking/provider/workbook/binding); [change129 krok15](changes/129_criteriaSpecificationQuerydsl.md).
Předchozí147PASS zůstává samostatný pre-integration checkpoint.

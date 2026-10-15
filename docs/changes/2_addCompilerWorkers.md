# Compiler workery, CFG a explicitní Maven build

## Kontext

Datum předání inkrementu: 15. 10. 2026.

Branch `feat/compiler-workers`, stacked PR nad `feat/evidence-production-scope`
(draft PR #4), baseline `a81def9dbc74fff3a5619cd02244be7f215f91cc`. Historická
reference a aktuálně ověřený `main` jsou
`8ac80ca30f6f680539deb7fb3590519d3a5c1460`.

Číslo 2 bylo vybráno po kontrole pracovního stromu a aktuálního GitHub tree cílové
větve: obsahuje jediný dokument `1_addProductionScope.md`. Tree main byl ověřen
rekurzivně bez truncation; žádné docs/changes v něm nejsou. Před publikací se
kontrola opakuje. Číslo není číslem PR a mezery historických dokumentů se nemění.

## Problém a výsledné chování

Name-match nemohl doložit overload/caller ani CFG. Nové volitelné workery
používají JavacTask/Trees, Kotlin BindingContext/KotlinTypeMapper v K1 compatibility
a TypeScript Program/TypeChecker. Ručně označených pět direct mixed JVM call
expressions odpovídá přesně caller/owner/descriptor ground truth, včetně dvou
process overloadů a volání Java ↔ Kotlin. Toto nezaručuje runtime dispatch.

Explicitní compiler inspection má BUILD_IMPORT kontext LOCAL_COMPILER_INPUTS:
obsah je ověřen, ale žádný build/test úspěch se netvrdí. SOURCE_ONLY fallback
zůstává syntaktický scan. Python ověřuje protocol, source/classpath/config/worker hashe, context a foreign
keys a publikuje schema v3 přes existující atomický store. Worker stdout obsahuje
jeden JSON, stderr logy; timeout/cancellation a output limits nezanechají půl indexu.
Source CFG zachovává protilehlé větve, return/throw, finally, loop a await/resume.
Renderer nevytváří pořadí z call graphu a explicitně uvádí truncation/boundaries.

Projekt se vykonává pouze samostatným build-plan/build-run. Plán je obsahově
svázaný s úplným inventářem včetně dirty/untracked, argv, executable/exporter,
prostředím a policy LOCAL_TRUSTED. Kopie projektu není bezpečnostní sandbox.
Build-run používá nové output roots, zachová log a oddělí BUILD status od XML test
statusu. Effective Maven export vzniká z skutečného MavenProject/session; import
ověřuje artefakty, ale supplied export neoznačuje za autentický host observation.
Gradle exporter používá source sets, nikoli regex Kotlin DSL; ještě nebyl integračně
ověřen v této session. Python baseline funguje bez JDK/Node, implicitní execution
se do původních příkazů nepřidává.

## Milníky a acceptance

Celý P0–P9 je **PARTIAL**. Žádný milník se neprohlašuje za úplný PASS.
[Gap/progress](../production-analysis-progress.md) obsahuje celé zbývající zadání.

- P0/P3, JV-01: reálné direct source calls přesně 5/5, nulové false resolved edges
  na ručně anotované malé fixture. CFG overload větve nemají path B→C ani C→B.
- P3/JV-02: oddělená bytecode reprezentace a application-only CHA; completeness
  zůstává false. Úplná CHA/classpath acceptance matrix není dokončena.
- P7/TS-01–02: dva skutečné TS overload signatures a React intrinsic onClick
  FRAMEWORK_DERIVED binding. Multi-project/re-export a backend mapping fixtures chybí.
- FLOW-01–04: strukturální testy protilehlých větví, arguments-before-call,
  return/throw přes finally, break cleanup, await boundary, escapování a unsupported
  resource close. Kompletní skutečná when/Elvis/suspend/exception/async matice chybí.
- BL-02–05 podmnožina: stale plan se nespouští, starý target/build se nekopíruje,
  failed build nemůže importovat fresh output, XML rozlišuje NOT_RUN/ZERO_TESTS/
  SKIPPED/FAILED; worker timeout/cancel jsou skutečné procesní testy. Maven skutečný
  build/test/import/inspection prošel; reactor, BOM/toolchain/variant fixture chybí.
- EV/BC: zachovaný v1/v2 kontrakt, v3 foreign keys a LLM annotations validátor,
  atomický store, source/config freshness a nezměněná availability regrese.
  Kompletní semantic cache/hook/context acceptance není hotová.

## CLI a kompatibilita

Přibyly `project build-plan`, `project build-run`, `project build-import`,
`inspect code/frontend`, `callgraph callers/callees/path`, `entrypoints`,
`flow render`, compiler-aware `graph rank/view` a `coverage report`.
CLI používá root/scope/context; více compiler kontextů vyžaduje explicitní volbu.
Absent/stale/unsupported index není prázdný úspěšný výsledek. Exit codes jsou
0 report, 2 invalid input, 3 execution/stale failure, 4 strict partial coverage.

V3 přidává symbols/call_sites/cfgs/analysis_annotations. V1/v2 se stále čtou,
legacy confidence se nepovyšuje. Testy, typové reference a dokumentace stále
nepřispívají k execution centrality. Flyway replay/workspace/availability zůstává
v původní implementaci. JSON je primární; Mermaid/Markdown pochází z CFG.
[Schéma](../schemas/graph-v3.schema.json) a [podrobná matice](../compiler-inspection.md).

## Přesně spuštěné kontroly

Toolchain: Python 3.12.14 / pytest 8.3.4 / jsonschema 4.23.0,
Temurin 21.0.6+7, Kotlin compiler 2.1.10, Maven 3.9.9, Node 24.19.0,
TypeScript 5.7.3, React 18.3.1, @types/react 18.3.18, Mermaid 11.4.1 / jsdom 26.0.0.
Lokální aktivace: `source /workspace/toolchains/activate.sh`.

```bash
python workers/jvm/build.py --kotlin-home /workspace/toolchains/kotlin/kotlinc \
  --maven-repository /workspace/toolchains/maven-repository --java-home "$JAVA_HOME"
python workers/build/build.py --maven-home /workspace/toolchains/maven/apache-maven-3.9.9 \
  --java-home "$JAVA_HOME"
mvn -o -B -ntp -f fixtures/build-inspection/maven/pom.xml test
KGMAKER_REQUIRE_WORKERS=1 pytest -q
kgmaker project build-plan --root fixtures/build-inspection/maven --phase test \
  --offline --output /workspace/toolchains/verification/kgmaker-build-plan.json
kgmaker project build-run --plan /workspace/toolchains/verification/kgmaker-build-plan.json
kgmaker project build-import --root fixtures/build-inspection/maven \
  --manifest fixtures/build-inspection/maven/.kgmaker/build-runs/fccb10455f3d416b9a20f9b02a5e8e9a/manifest.json
kgmaker inspect code --root fixtures/build-inspection/maven \
  --build-id fccb10455f3d416b9a20f9b02a5e8e9a --context root:main
python tests/rendering/generate.py --output /workspace/toolchains/verification/actual-render
node tests/rendering/validate.mjs /workspace/toolchains/verification/actual-render/flow.mmd \
  /workspace/toolchains/verification/actual-render/flow.json
```

Výsledky: oba trusty builders SUCCESS; Maven fixture skutečný JUnit 1/1 PASS.
Explicitní Maven runner SUCCESS (33.116 s; závěrečný běh 04a2d9b113654591b6bed2f1b11b314f), tests PASSED, executed/passed 1,
failed/skipped 0; production/test classpath 98/141 položek, compiler release 21.
Import a navazující code inspection vytvořily validní JSON. Závěrečný přebuild workeru SUCCESS; `KGMAKER_REQUIRE_WORKERS=1 pytest -q`
prošlo 140 testy za 57.39 s. `kgmaker scan`, `kgmaker semantic update --base
a81def9dbc74fff3a5619cd02244be7f215f91cc` a `kgmaker check` PASS; graph docs
odpovídají 118 souborům, 848 uzlům a 2320 vztahům. Semantic update pouze připravil
packet, žádná nedoložená semantic patch se neaplikovala.
Mermaid parser skutečného TS CFG: 6 vertices, 5 edges, endpointy shodné s CFG.
`python tests/rendering/generate.py --language jvm --output
/workspace/toolchains/verification/actual-jvm-render` a navazující
`node tests/rendering/validate.mjs /workspace/toolchains/verification/actual-jvm-render/flow.mmd
/workspace/toolchains/verification/actual-jvm-render/flow.json` PASS: 10 vertices,
12 edges, přesně shodné endpoints pro skutečnou compiler if větev.

Dva skutečné JVM worker launches (bez analyzer cache) měly 21.902 s a 12.548 s,
peak child RSS 277376 KiB, JSON 20483 bytes, stejný normalizovaný SHA-256
`7377ed9594a00e7fa5eb04e0943100e21cdfe249c61349096031e7698ecb1c47`.
Měření běželo současně s regresí, takže není izolovaný výkonový benchmark ani
zamčený regression budget. Obě analýzy našly/analyzovaly 2 soubory, 5 metod a
5 calls; 5 resolved / 5 found, 0 unresolved. Výsledek se nezobecňuje na bankovní projekt.

Při průběžné regresi změna package-lock během frontend analysis správně vyvolala
STALE; souběžný rebuild worker distribuce vedl k worker failure. Po dokončení
instalace/regenerace byla regrese opakována. Tyto průběžné neúspěchy nejsou PASS.

## Nespuštěné nebo neúspěšné kontroly a omezení

Nový Gradle workflow byl spuštěn v default sandboxu a vrací FAILED, tests NOT_RUN,
žádné outputs. Gradle selhal před projektem: `FileLockContentionHandler` / `Could
not determine a usable wildcard IP for this machine`. Žádost o command network
režim byla přerušena před spuštěním; žádné automatické schválení ani rejection
se netvrdí. Exportér tak není doložen build testem. Nové CI jobs Python, compiler/
actual Maven build, Gradle a rendering jsou připraveny, jejich remote výsledek
v této změně ještě není znám.

Nové negativní testy dále ověřují relativní classpath vůči root, pravdivé XML test
počty i ve fázi test-compile, validní PARTIAL import neúspěšného buildu bez modelu,
změnu kopírovaných vstupů během execution (MIXED_BUILD_INPUTS, bez fresh outputs),
redakci citlivých headers/URL/property defaults a compiler lookup nejkonkrétnější
interface default metody přes superclass hierarchy. Nepokryté Kotlin property
bodies/default argument evaluation a Java initializers mají diagnostiku a hranici.
Bytecode CFG evidence odkazuje na ASM a hashe artefaktů, source CFG na compiler AST.

Zbývá širší Maven/Gradle reactor/variant/toolchain/generated matrix, K2/Analysis API,
Kotlin default/inline/suspend/operators/accessors, plný def-use, dependency CHA,
Spring wiring/conditions/proxy, Hibernate/JPA entity/query model, Kafka/REST
framework adaptéry, BE/FE service/contract/value-flow, plné ranking dimenze,
Markdown/Mermaid integrační view, hook/feature/cache přenos všech kontextů,
celá mandatory acceptance suite a měření/regression budgets. Povinnosti se tím
nestávají volitelné. P10 zůstává samostatná neimplementovaná volitelná etapa.

## Ověřitelný příklad

Po explicitním buildu fixture a workerů:
`KGMAKER_REQUIRE_WORKERS=1 pytest -q tests/test_compiler_workers.py` ověřuje
nezávislý ground truth z `fixtures/build-inspection/ground-truth.json`, skutečné
compiler declared targets a CFG neexistenci sekvence protilehlých overloadů.
Nenalezená statická cesta při neúplném pokrytí má UNKNOWN, ne důkaz neexistence.

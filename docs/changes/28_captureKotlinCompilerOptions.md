# Zachycení Kotlin compiler options v build manifestu

- Change note: 28; číslo 11 je již použito v otevřeném PR #11 na `main`.

## Problém

Build manifest zachovával Java release, ale zahazoval efektivní Kotlin konfiguraci.
Změna language/API/JVM targetu, flags nebo compiler pluginu proto nebyla samostatně
vysvětlitelná v provenance a context identity.

## Skutečné změny

- Maven EventSpy zachytí efektivní konfiguraci úspěšného Kotlin `compile` a
  `test-compile` mojo.
- Gradle exporter čte finalizované `compilerOptions` příslušného Kotlin tasku a
  content-bound identity compiler pluginů.
- Manifest validuje versioned Kotlin options fail-closed; malformed nebo unresolved
  hodnota se nepublikuje.
- Compiler context zahrnuje options do selection identity. Offline freshness kontrola
  odmítne pozměněné options bez spuštění buildu nebo workeru.
- Staré manifesty bez Kotlin sekce zůstávají čitelné. Zachycená konfigurace se
  nepovyšuje na tvrzení podpory dané language verze současným K1 frontendem.

## Vazba na zadání a acceptance

- `T003-S03-W04`
- `T003-S03-W04-AC01` až `T003-S03-W04-AC04`
- nadřazené `T003-AC03` a průřezové `T003-R01`, `T003-R04`, `T003-R05`,
  `T003-R07` až `T003-R10`

## Kompatibilita a příklad

`compiler_options` zůstává kompatibilní objekt. Nová volitelná sekce
`compiler_options.kotlin` má `schema_version: 1`, explicitní capture status a
normalizované hodnoty. Například změna `-Xjsr305=warn` na `-Xjsr305=strict`
vytvoří jinou identity pouze pro dotčený module/source-set context.

## Provedené kontroly

- `python3 -m pytest -q tests/test_kotlin_build_options.py -k 'not real_gradle'`
  — 11 passed.
- explicitní Gradle 8.13 fixture s Kotlin Gradle pluginem 2.2.20 — 1 passed;
  provedla dva skutečné compile běhy a ověřila čerstvý `Options.class`.
- skutečný offline Maven 3.8.7/Kotlin 2.1.10 běh je součástí zaměřené sady;
  provedl dva compile běhy a ověřil čerstvý `Options.class` i inspection inputs.
- `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1
  python3 -m pytest -q` — 211 passed, 1 skipped;
  skip je výhradně explicitně oddělená Gradle fixture vyžadující host JVM IPC,
  která prošla předchozím samostatným hostitelským během.
- `python3 -m json.tool docs/schemas/build-manifest-v1.schema.json` a
  `git diff --check` — prošly.

- scoped semantic update/apply/validate, capture implementační paměti a následný
  `kgmaker scan` — prošly nad baseline po T003-S03-W01; zachovaly nesouvisející
  semantic vztahy.

## Zbývající práce

Tento work package neimplementuje K2 Analysis API, další Gradle variant API
ani cross-repo artefakty. Dříve sloučené W02/W03 poskytují vlastní SourceSet
scope a included builds; jejich rozsah zůstává oddělený. Compiler plugin classpath je v manifestu
content-bound hashem; úplná interpretace chování libovolného pluginu zůstává mimo scope.

## Revize po nezávislém CR

CR nalezlo dva nedoložené Maven stavy. Pokud Kotlin Mojo vrátí nepřeložený
default `${kotlin.compiler.languageVersion}` nebo obdobnou základní option,
export ji nyní vynechá, označí zachycení `PARTIAL` a přidá konkrétní
diagnostiku také do contextu. Úspěšný build tím nezíská falešné úplné
compiler options; manifest běžného projektu s implicitním defaultem zůstává
validní.

Maven EventSpy načítá resolved plugin descriptor classpath včetně compiler
plugin dependencies a ukládá pro každý soubor souřadnice, absolutní cestu a
SHA-256. Import nebo offline validace při výměně JAR selže s
`STALE_KOTLIN_PLUGIN` před zápisem store. Test provádí skutečné offline Maven
compile s `kotlin-maven-allopen` 1.9.25 a kontroluje jeho výskyt v zachycené
classpath; samostatná negativní fixture mění obsah JAR a ověřuje nulovou
mutaci. Maven exporter byl sestaven příkazem
`python3 workers/build/build.py --maven-home /usr/share/maven
--java-home /usr/lib/jvm/java-21-openjdk-amd64`.

Zaměřené dvě regrese prošly 2 PASS. Následná úplná sada s povinnými
JVM/TypeScript workery, skutečným Maven/Gradle 8.13 a JDK21/22 měla
**213 PASS, 0 SKIP** za 60,75 s.
`python3 -m json.tool docs/schemas/build-manifest-v1.schema.json` a
`git diff --check` prošly. `kgmaker semantic update --base 3155b49`
označil dříve doložený koncept README a čtyři jeho vazby; packet-bound patch
je zachoval, `semantic apply` i `semantic validate` prošly bez domyšlených
nových vztahů.

## Integrace po sloučení W02/W03 a T045

Gradle exporter zachovává W03 composite fragmenty, ordered classpath a output
realm a zároveň přidává W04 task-level Kotlin compiler options. Stavová matice
popisuje oba již dodané rozsahy. Obsahové sloučení sémantiky zachovalo všech 32
historických epizod; `semantic validate`, `scan` a `kgmaker check` prošly.
`tests/test_kotlin_build_options.py tests/test_gradle_included.py
tests/test_gradle_variants.py` se skutečným Maven/Gradle toolchainem: **34 PASS**.
První full běh měl 220 PASS a 14 setup ERROR kvůli nesestavené Maven fixture;
po explicitním `mvn -q -o -DskipTests package` ve fixture opakovaný strict běh
se skutečnými workery, Gradlem 8.13 a JDK21/22: **234 PASS, 0 SKIP za 70,73 s**.
Dočasné symlinky testovacích workerů a React typings byly odstraněny.

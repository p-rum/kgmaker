# Bounded deklarace dynamických Spring importů

Datum: 2026-10-26. Task [T003-S05-W01](../tasks/T003-S05-01-dynamicSpringImports.md),
AC01–AC04, nadřazené T003-S05/AC05. Baseline a splněná K2 závislost:
`eff0d3d5d7620b017fe42a65a54f672af8068667` (merge PR26). Izolovaná větev
`feat/t003-s05-01-dynamic-spring-imports`. Číslo změny42 bylo potvrzeno parent
orchestrací po kontrole alokací; tento task nepřebírá registrar/factory rozsah.

## Problém a skutečné změny

Původní detekce zkracovala přímé supertypes na simple name. Zděděný skutečný
selector se stal obyčejným ACTIVE beanem, zatímco `fake.ImportSelector` dostal
falešnou dynamic boundary. Ani literal selector result se nepropojil. Přímý
read-only skutečný Javac probe a failing acceptance to doložily; po přidání
worker facts, před framework implementací: **8 FAIL, 2 PASS** na obou distribucích.

Nový worker helper `SelectorFacts` emituje pouze compiler declaration facts:
bounded exact/transitive hierarchy a jediný literal String[] return známé
selector metody s přesným API descriptorem. Žádný selector se nevolá, třída se
nenačítá/initializuje a obecné return payloads se neukládají. Děděný owner metody
je konkrétní symbol. Limit hierarchy/targets je128 a literal FQN512 znaků.

`spring_imports.py` validuje aditivní schema1 facts a framework v4 používá
existující model/context/evidence/condition/reachability vrstvy. Přidává
`spring_import_selector`, `uses_import_selector`, `selects_import` a
`may_select_import`; statický import má `imports_configuration`. Configuration
view je zachovává. Unknown/complex body, custom filter/group, chybějící nebo
nested processor target, neúplná hierarchie a překročený limit zůstávají UNKNOWN.
Registrary se dál neinterpretují. Selector nedostane běžný bean status jen kvůli
@Import a fake FQN interface se za selector nevydává.

Skutečné Spring API default members zároveň odhalily původní `_string_arg` chybu:
`proxyBeanMethods` se mylně stal názvem configuration beanu. Parser nyní
nezaměňuje unrelated named member za positional value; skutečné default
Configuration/Bean anotace ponechají název deklarace.

## Reprodukovatelné vstupy a kompatibilita

Worker protocol zůstává1, graph/store čtou v1/v2/v3. Nová pole class hierarchy,
selector contract a literal return mají samostatné schema1; chybějící legacy pole
nepromují selector result, nevalidní nová fakta se odmítnou před store publication.
Rule version `annotation-source-v4` a hash distribuce jsou součástí nového
context fingerprintu. Evidence zůstává FRAMEWORK_DERIVED, source method/hash a
context-bound; compiler-call confidence ani data availability se nemění.

Nový Spring rule version platí pouze pro JVM. Dva čisté context testy porovnávají
celé ordinary TypeScript/React metadata, ID a selection key se snapshoty skutečné
baseline `eff0d3d`; **2 PASS v 0.31 s**. Dřívější přepsání React rule metadata v
`inspection.context` zůstává zachováno kvůli kompatibilitě a patří do následného
T003-S08 posouzení. Tato změna nezavádí TypeScript context migration.

Tests používají skutečné externí Spring6.2.2 API JARy, nikoli vlastní Spring
stubs. `fixtures/spring-imports/pom.xml` pinne šest Spring dependencies a Maven
resources3.3.1/compiler3.13.0. CI je explicitně připraví Maven compile příkazem
před mandatory testy. `dependencies.lock.json` nese jejich coordinates, SHA-256,
worker protocol1 a skutečný `META-INF/license.txt` Apache-2.0 entry. Test před
inspekcí ověří bytes/license; chybějící/změněné APIs jsou FAIL pod
KGMAKER_REQUIRE_WORKERS nebo KGMAKER_REQUIRE_SPRING_IMPORTS. Test fixture ani core
nic nestahuje. Spring JARy nejsou součástí distribuovaného worker wheelu.
Checksums jsou identity obsahu, nikoli nový důkaz publisher authenticity/sítě.

## Provedené kontroly

- Projektový kgmaker skill, status bez počátečního machine indexu, scan/query,
  přijatý read-only architecture brief, source/test inspekce, memory recall a
  durable analyze/plan artifacts: provedeny. K2 závislost je skutečně na baseline.
- Obě vlastní JVM distribuce byly explicitně znovu sestaveny offline přes
  `workers/jvm/build.py` se skutečnými Kotlin2.1.10/AnalysisAPI2.1.10, JDK21.0.6+7,
  Jackson2.18.2 a pinned locky. Python3.12.14, Linux.
- `JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=... mvn -B -ntp -o -Dmaven.repo.local=/workspace/tools/m2 -f fixtures/spring-imports/pom.xml compile`:
  **BUILD SUCCESS, 6.397 s**, skutečný Java interface zkompilovaný proti Spring API.
- První rozšířený actual suite: **69 PASS / 2 FAIL**; opraven expected rule version
  v existujícím AC05 a připravené React fixture dependency zkopírované z již
  buildnutého lokálního K2 checkoutu bez package manageru. TS kontrola poté PASS;
  finální samotný AC05: **1 PASS v 77.00 s**. Nejde o vynechání toolchain guardu.
- Rozšíření PATH o Maven aktivovalo také dříve nepřipravené optional build tests:
  full běh měl **401 PASS, 6 SKIP, 2 FAIL v 457.45 s**. Jednorázový opakovaný
  diagnostic těchto dvou testů měl **2 FAIL v 58.39 s**: reactor fixture žádá
  resources plugin3.3.1 přes nedostupnou síť/missing host cache a offline Kotlin
  all-open fixture postrádá plugin1.9.25. Tyto chyby se nevydávají za PASS;
  zdroj ani testy se kvůli nim nemění. Finální full používá standardní PATH bez
  optional Maven/Gradle a explicitně připravené Spring APIs z výše uvedeného
  offline Maven příkazu. Povinné worker/API guards zůstávají zapnuté.

Finální full/focused kontroly a semantic/memory/scan/check evidence jsou doplněny
před předáním; žádný local či CI test se nevydává za Spring application runtime.

## Příklad a zbývající scope

`kgmaker inspect code --root project --manifest /approved/build-manifest.json
--context BUILD_CONTEXT_ID --kotlin-backend k2 --worker-home /approved/workers`
vrátí literal selector jako FRAMEWORK_DERIVED deklaraci; chybějící scan/profile
scope či custom Group zachová UNKNOWN. Scan/feature/data-check nic nesestavují
ani nespouštějí. Static bean selection není AVAILABLE ani CONFIRMED_MISSING.

Nepodporováno: Kotlin selector annotation metadata bez compiler factů, složitá
těla, field/concatenation/evaluation, binární metoda bez source literal factu,
vnořené selectors, custom filtering/group execution, ordering/runtime registrace,
registrars/factories a produkční availability. S05/AC05 ani celý T003 nejsou hotové.
Implementace zůstává lokální; parent zajistí nezávislé review a publikaci.

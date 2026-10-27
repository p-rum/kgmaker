# Bounded Spring registrar a FactoryBean deklarace

Datum: 2026-10-26. Task [T003-S05-W02](../tasks/T003-S05-02-springRegistrarsFactories.md),
AC01–AC04; nadřazené S05/AC05 zůstává PARTIAL. Číslo47 bylo rezervováno parentem.
Závislost W01 je skutečně merged v `4113a7975451a8313321fd521252485c959908e3`.
Před finální validací integrován skutečný main
`33dc239a6d2eca2f42364a7b314aeb377e4b441a`, včetně inventory, mandatory CI a
source/bytecode mapping. Nejde o dokončení obecného Spring runtime.

## Problém a skutečné změny

Actual Javac/Spring6.2.2 probe nad oběma distribucemi ukázal chybějící literal
registrace a záměnu FactoryBean objektu s produktem. `FactoryBean<Product>` měl
v běžných bean types dokonce `Product>`, bez produktové provenance/boundary.
Regresní suite před implementací: **6 FAIL, 4 PASS v32.10 s**, oba backendy.

`RegistrationFacts.java` přidává pouze compiler declaration facts:

- Přesná/transitivní `ImportBeanDefinitionRegistrar` identita, effective owner
  veřejné dvouparametrové metody a informace o custom tříparametrovém overloadu.
- Nejvýše128 přímých expression statements skutečného
  `BeanDefinitionRegistry.registerBeanDefinition` na přesném registry parametru,
  literal bean name do512 znaků a přesný `RootBeanDefinition(Type.class)`.
  Conditional/control flow, alias/helper, jiný receiver/constructor či překročený
  limit je explicitně UNSUPPORTED. Fake registry stejného method name neprojde.
- Přesná `FactoryBean` hierarchie včetně generic substitution, effective source
  metody getObject/getObjectType a jediný literal zero-argument constructor/class
  return. Generický typ a oba return typy se musí přesně shodovat; source target
  musí být indexovaný. Těla, konstruktory ani class initializers se neprovádějí.

`spring_beans.py` validuje schema1 facts, jejich shape a selected context.
Framework reuse stávající `spring_bean`, condition/reachability, evidence a
injection/store vrstvy; přidává `spring_registrar`, `uses_bean_registrar`,
`registers_bean` a `produces_bean`. Configuration view tyto vazby zachovává.
Registrar bean condition dědí od importující konfigurace; RootBeanDefinition
zde samo nevyhodnocuje target @Profile. Unknown custom condition či overload
nevyrobí ACTIVE product. Factory objekt `&name` a produkt `name` jsou odlišné
deklarace. Abstract factory objekt/produkt zůstává UNKNOWN. Kompilátorově
rozlišený Spring FactoryBean injection nesmí vybrat stejnojmenný fake interface.

## Kontrakty, bezpečné hranice a kompatibilita

Worker protocol zůstává1; aditivní fields `bean_registrar`, `bean_registrations`,
`factory_bean`, `factory_bean_return`, `factory_producer`, `factory_return` mají vlastní schema1.
Legacy fakta a graph/store v1/v2/v3 zůstávají čitelné; bez nového důkazu se literal
registrace/produkt nepromuje. Invalidní facts, strict error a timeout ponechávají
poslední validní generaci. Cross-context symbol odmítne už společný model validator.

Nový Spring rule version je `annotation-source-v5` pouze pro JVM. TypeScript a
React metadata/key zůstávají současnému main byte-identické; pre-existing React
metadata overwrite se tímto taskem nemění. Evidence je FRAMEWORK_DERIVED,
obsahově/source-symbol/context-bound; nevzniká execution ani runtime/data proof.
Audit statického registered beanu zůstává UNKNOWN, žádný CONFIRMED_MISSING.

Reálná fixture používá stávajících šest SHA/license-bound Spring6.2.2 API JARů
z `fixtures/spring-imports/pom.xml` a locku. Žádná nová dependency ani implicitní
instalace/fetch nevzniká. Mandatory CI bootstrap z W01 zůstává a compiler job
navíc spouští `tests/test_spring_registrations.py`; missing API/worker je FAIL
pod mandatory flags. Spring JARy nejsou redistribuované v worker wheelu.

Nepodporováno: obecné BeanDefinition builders/properties/suppliers, runtime
post-processors, custom registrars/factory evaluace, Kotlin registration facts,
XML a Spring/Boot factories metadata discovery. `spring.factories` a Boot
`.imports` se nepovyšují na beans; jejich budoucí čtení musí nejprve zavést
source-set-bound freshness. Nejde o aktuální podporu těchto formátů.

## Provedené kontroly a průběh

- Projektový kgmaker skill, status/scan/query, přijatý read-only architecture
  brief, ověření normativních dependencies a memory recall: provedeny. Durable
  analyze/plan/implementation packet je zapsaný.
- První skutečné integrované JVM/TS-context případy: **12 PASS v18.90 s**.
- Rozšířená actual sada: **40 PASS, 2 FAIL v88.08 s**. Dvě chyby byly očekáváním
  AnalysisError v testu cross-context symbolu; společný model správně odmítl symbol
  dříve přes ValueError. Test nyní ověřuje tento existující kontrakt i nulový zápis.
- K1/K2 byly explicitně rebuildnuté s vlastními source facts, JDK21.0.6+7,
  Kotlin2.1.10/AnalysisAPI2.1.10 a Jackson2.18.2, pinned/offline vstupy.
  Po integraci main33dc se znovu sestavují i s jeho mapping additions.
- Další focused actual suite: **53 PASS v169.03 s**; následující nezávislé review
  kandidáta363e75 našlo dva skutečné P1 gaps. Anonymous factory producer mohl
  převzít base getter proof a `other.Product` mohl vybrat stejnojmenný app.Product.
  Review repros používaly skutečné Javac/Spring APIs bez execution.
- Oprava přidává `factory_producer` source fact: jen jediný literal no-argument
  constructor bez anonymous těla určí skutečnou implementaci a její effective
  getter metody. Custom/anonymous producent zachová UNKNOWN a evidence cituje
  producer i všechny použité getter symbols/hash/context. Qualified compiler
  field type kontroluje assignability registrace/produktu; známý foreign typ se
  odmítne, neúplná/generic proof zůstává UNKNOWN. Neshoda FactoryBean generic
  contractu ani fake interface nevyrobí resolved injection. Opakovaný import stejné
  deklarace agreguje conditions; name collision s Primary zůstává UNKNOWN.
- První starý full byl ještě pouze ve frontě locku, byl bezpečně zrušen před
  spuštěním pytest child, nikoli vydáván za provedený test. Po rebuild obou workerů
  review-fix actual suite: **57 PASS v109.01 s**, povinné K1/K2/Spring APIs,
  včetně nové producer/qualified namespace regresní fixture a TS contextů.

- Strict full po prvních dvou review opravách, source `fe125e0`: **558 PASS, 10 SKIP v662.92 s**. Povinné
  K1/K2 a pinned Spring APIs skutečně běžely. Deset skips je volitelný Maven/
  Gradle/included-build/variant/plugin/installed exporter a skutečný Windows gate;
  nevydávají se za PASS. Proces skončil0, JUnit a log lokálně zachovány.
- Explicitně rebuilt K1 worker SHA256
  `8158a0bb49ec531001950334d5d8fd4be6a16a7e236edd652a44a70588033cbb`,
  K2 `426a73aa04b8ad8748b22cf7bed847e385b0c1f5293669a1316369d93241660e`.
  JARy jsou lokální ignorované artefakty, žádná nová redistribuce.

Přesný final full příkaz (PATH dědí managed Node, Maven/Gradle nejsou exponované):

```bash
export JAVA_HOME=/workspace/tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:/workspace/tools/kotlinc/bin:$PATH"
/workspace/kgmaker-venv/bin/python /workspace/kgmaker-test-prerequisites.py /workspace/spring-factories
flock /workspace/kgmaker-heavy-tests.lock env KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_WORKERS_HOME=/workspace/spring-factories/workers \
  PYTHONPATH=/workspace/spring-factories/src /workspace/kgmaker-venv/bin/python \
  -m pytest -q -rs --tb=short --basetemp=/tmp/kgmaker-registrars-review-full \
  --junitxml=/tmp/kgmaker-registrars-review-full.xml
```

Scoped semantic update/apply/validate, memory capture, scan/check a diff check
jsou součástí předání; sémantická fakta mimo scope a historie main zůstávají zachované. Žádný skutečný runtime PASS se
neodvozuje z fixture nebo přítomnosti compileru. GitHub Actions billing/quota
je externí překážka nového CI; lokální validace ji nenahrazuje. Publikace má být
Draft a merge/CI retry zůstává pozastaven dle výslovného uživatelského pokynu.

## Použití

```bash
kgmaker inspect code --root project --manifest /approved/build-manifest.json \
  --context BUILD_CONTEXT_ID --kotlin-backend k2 --worker-home /approved/workers
kgmaker query --root project --context ANALYSIS_CONTEXT_ID registeredProduct
```

Nutný je explicitní Spring/API classpath a profile/scan scope; bez důkazu jsou
conditions UNKNOWN. Scan/hook/query/feature/data-check nic implicitně nesestaví,
neinstaluje ani nespustí. Bean ACTIVE zde označuje statickou condition deklarace,
nikoli instanci, úspěšný custom constructor nebo dostupná produkční data.


## Následné namespace review a finální ověření

Nezávislé actual review našlo factory-object sibling: field `fake.FactoryBean`
s qualifierem `&literalFactory` mohl převzít skutečný Spring object podle simple
name. Source `f6719909` přidal qualified object assignability; exact official
Spring FactoryBean generic path zůstal zachovaný. Reviewer ověřil původní repro
bez injects/may edges a předchozí anonymous/producer opravy zůstaly správné.

První nový focused příkaz měl chybný název `test_spring_context_keys.py` místo
`test_spring_imports_context.py`: žádné testy se nespustily, nebyl to PASS. Guard
zabránil navazujícímu full a pouze jeho dosud queued proces byl bezpečně zrušen.
Správný focused pak vykázal **57 PASS, 2 FAIL v125.85s**: nová fixture měla dvě
annotated fields na jednom řádku a dosavadní bounded textual injection projection
první field nevytvořila (StopIteration, nikoli namespace false-positive).
Fixture `ec32256` používá samostatné deklarace; runtime zůstal byte-identický.
Následně **59 PASS v125.31s** a strict **558 PASS, 10 SKIP v491.33s**.

Tento stávající injection subset nepokrývá více anotovaných deklarací na jednom
řádku ani obecnou Java formatting/FQN grammar; fixture používá imported simple
types a samostatné declaration lines. Compiler-qualified field/hierarchy proof
se používá pro nové registrar/product/object candidates. Netvrdí se podpora
libovolného Java source formátu.

Finální self-check nezávisle reprodukovaný reviewerem odhalil ještě slabou UNKNOWN
may-edge pro `@Bean literalProducer` → fake.FactoryBean: method protocol má
return_type a původní object metadata ignorovala validovaný factory_producer.type.
Nešlo o falešný resolved/ACTIVE injection. `cd0f9f8` nyní používá jen přesný
component owner nebo schema/index/contract-validovaný literal producer type;
custom method implementations zůstávají UNKNOWN. Actual negative pro method
factory a pozitivní method factory implementující obě rozhraní ověřují obě strany.
Worker source/JARy se touto Python opravou nemění. Nezávislý původní method probe
nyní nemá žádné edges; anonymous product je UNKNOWN a literalProducer ACTIVE.

Finální actual focused nad `cd0f9f8`: **59 PASS v133.44s**. Poté pod stejným
shared lockem strict full: **558 PASS, 10 SKIP v437.81s**, exit0; JUnit/log
`/tmp/kgmaker-registrars-object-full.xml` a `.log`. Full se spustil pouze po
returncode0 focused; oba reálné backendy/pinned Spring APIs byly mandatory.
Volitelné skips jsou stejné Maven/Gradle/Windows gates uvedené výše, nikoli PASS.
Předchozí passing logy jsou zachované jako `*-before-method.log`; failure excerpt
z tool transcriptu je označen jako excerpt, ne jako původní přepsaný log.

```bash
# Stejný explicitní JAVA_HOME/PATH, workers home, PYTHONPATH a mandatory flags
# jako v předchozím full příkazu; Maven/Gradle nejsou na PATH.
python -m pytest -q --tb=short tests/test_spring_registrations.py \
  tests/test_spring_imports.py tests/test_spring_imports_context.py \
  tests/test_worker_protocol.py
python -m pytest -q -rs --tb=short \
  --basetemp=/tmp/kgmaker-registrars-object-full \
  --junitxml=/tmp/kgmaker-registrars-object-full.xml
```

Finální scoped semantic apply/validate/scan/check a diff check PASS; core facts
mimo scope a105 immutable main episodes zachovány, implementační paměť captured.
Durable task končí v review, nikoli self-approved/done. Publikační connector
odmítl Draft PR automatickým posouzením: chybí explicitní repository-egress
souhlas pro private p-rum/kgmaker. Read-only app check ověřil repository1394670937,
admin/push práva a přesný origin; žádný CLI/alternativní bypass ani retry/merge
neproběhl. Dřívější push kandidáta d6a61b3 uspěl, aktuální finální source je lokální.


## Integrace schváleného kandidáta s main09d (2026-10-27)

Root publikoval původní schválený source `7859e165` jako DraftPR53; dřívější
publikační/billing block výše popisuje historický stav. Billing byl obnoven.
Nyní je lokálně integrován přesný main
`09d351d379b43c697451f93c8735a008204d8d9b`: PR48/T009, rootem ověřených7 CI
checks v run40483160106 a jsonschema4.23.0 v unit/Windows test preparation.
Číslo47 a původní omezený work package zůstávají stejné.

Main nemění Java worker source ani Factory runtime. Osm feature runtime/test
souborů je blob-identických `7859e165`; jediný sdílený views.py má přesně
stejný Factory added/removed patch jako před integrací a současně všechny
nové T009 evidence/schema změny. Pinned worker/API vstupy se nemění, žádný
implicitní rebuild/fetch. Nová jsonschema test dependency je v aktuálním
sdíleném venv4.23.0; všech7 CI gate definitions a mandatory Spring suite zůstaly.

Merge řeší jen generated graph a semantic artifact konflikty. Sémantická unie
zachovává všech115 main episodes jako immutable prefix a obě jedinečné Factory
episodes beze změny; core7 concepts/18edges je unie včetně T009. Citace README
jsou na skutečných semantic prepare/update bullets167/169, architecture ownership/
inventory156/164 a Javac STATIC proof113. Graph se regeneruje CLI, nikoli ručně.

První integration focus (T005/T006/T008/T009 schema/service views, mandatory CI a
Windows preparation): **90 PASS, 1 native-Windows SKIP v2.46s**. Actual Factory/
imports/protocol/context compatibility se ověřuje samostatně pod shared lock;
queued nebo running stav se nevydává za PASS. Starý **558PASS/10SKIP** zůstává
feature proof pro byte-identický Factory runtime; whole local full se kvůli
čistému merge neopakuje. Nový přesný integration head musí po root publication
projít fresh všech7 remote checks; CI na předchozím main není proof nového páru.
Autor nevykonává push, CI retry ani merge PR.

Integration actual focus dokončen: **59 PASS v122.12s**, exit0, genuine K1/K2 a
pinned Spring6.2.2 API classpath byly mandatory. Testy zahrnují Factory namespace/
producer bounds, registry podmínky, legacy/protocol/store negatives a TS context
identity. Persistent preflight/log/XML/basetemp jsou v
`/workspace/validation/spring-factory-integration-09d/`; žádný souběžný full,
implicitní worker build ani source mutation. Celkem dvě relevantní sady:
**149 PASS a1 native-Windows SKIP**; nejde o nově provedený whole local full.

```bash
# Děděný PATH zachovává managed Node; explicitní JDK21+Kotlin prefix.
export JAVA_HOME=/workspace/tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:/workspace/tools/kotlinc/bin:$PATH"
flock /workspace/kgmaker-heavy-tests.lock env KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_WORKERS_HOME=/workspace/spring-factories/workers \
  PYTHONPATH=/workspace/spring-factories/src /workspace/kgmaker-venv/bin/python \
  -m pytest -q -rs --tb=short tests/test_spring_registrations.py \
  tests/test_spring_imports.py tests/test_spring_imports_context.py \
  tests/test_worker_protocol.py \
  --basetemp=/workspace/validation/spring-factory-integration-09d/actual-temp \
  --junitxml=/workspace/validation/spring-factory-integration-09d/actual.xml
```

Finální scoped semantic update/apply/validate, CLI scan/check a diff check PASS;
žádné nové semantic business facts ani přepsání zachovaných epizod se nevymýšlí.
Původní dvě Factory implementační epizody už nesou validated source proof;
čistá integrace je durable orchestrator artifact, nikoli nový implementation
scope. Finální commit je lokální merge aktuálního main, bez publikace autorem.


## Refresh po merge PR36 (2026-10-27)

Následný přesný main je `5430388a282f19f6c9637319c12a1731ae6d0674` po PR36.
Přidává dříve schválený scoped TypeScript input-discovery guard/helper a CI test;
Java/Factory runtime ani testy se nemění. CI konflikt zachovává oba mandatory
seznamy (`test_tsconfig_freshness.py` i `test_spring_registrations.py`) a všechny
předchozí7gates. Pyproject ponechává TS snapshot helper jako hash-bound resource.

Sémantická unie nyní má main118 immutable episodes jako přesný prefix + stejné
2Factory episodes =120; core8/21 je unie. Source mapping heading je skutečně589,
README semantic bullets167/169, architecture156/164, vlastní Javac STATIC113.
Runtime/test blobs zůstávají `7859e165`; žádný worker rebuild/install nebo nové
business facts. Relevantní view/schema/mandatory-CI/Windows preparation sada:
**90 PASS, 1 native-Windows SKIP v2.46s** v předchozí09d integraci; aktuální543
výsledky jsou doplněny samostatně po dokončení. Source compatibility ověří oba
JVM backendy plus relevantní nový TS guard. Whole local full se neopakuje;
old558/10 je nadále feature proof a current remote7CI zajišťuje root po publikaci.

Aktuální543 scoped proof: view/T006/T008/T009/schema/mandatory-CI/Windows
preparation **90 PASS, 1 native-Windows SKIP v1.44s**; genuine K1/K2 Factory
producer/namespace/registrar + context/protocol a nové TS guard negatives
**38 PASS v49.64s**, exit0. Persistent preflight/log/XML/basetemp jsou v
`/workspace/validation/spring-factory-integration-543/`. Součet je128 PASS
a1 explicitní platform SKIP; nejde o nový full. Frozen feature proof558/10
zůstává platný pro nezměněné Factory/JVM blobs. Finální semantic validate,
CLI scan/check a git diff check jsou ověřeny před lokálním merge commitem;
remote7CI musí být fresh pro nový přesný head po publikaci rootem.

## Refresh po merge PR46 (2026-10-27)

Aktuální main `3a7f76b00bb5136bbe5990546d9c8942a7f53f73` obsahuje samostatně
schválené TypeScript callback/generic hranice. Integrace zachovává jejich runtime,
fixtures a tři testové moduly přesně jako main; Factory/JVM runtime a8 chráněných
feature/test blobs zůstávají byte-identické `7859e165`. Mandatory compiler CI
zachovává callback testy i Spring registrations, všech7gate a Windows přípravu.

Current main121 immutable episodes zůstává přesným prefixem +2 původní nezměněné
Factory episodes =123; core9concepts/26relationships je doložená unie. Default body
source mapping cituje skutečný nadpis602 v integrovaném capability dokumentu;
README semantic bullets167/169 a Javac STATIC113 zůstávají přesné. Grafy jsou
regenerovány CLI, nikoli ručně. Starší actual38/59 a full558/10 jsou historický
feature/source-compatibility proof; nový čistý merge je znovu nespouští.
Relevantní pure integrační výsledek a semantic/check/diff jsou zaznamenány níže;
root po nezávislém review publikuje a vyžádá fresh7remoteCI pro přesný nový head.

Aktuální3a7 čistá integrační sada: **103 PASS, 1 native-Windows SKIP v2.20s**,
exit0; T005/T006/T008/T009, mandatory CI, Windows preparation, Spring TS-context
identity a worker protocol. `node --check workers/typescript/worker.cjs` PASS.
Persistent log/XML: `/workspace/validation/spring-factory-integration-3a7/`.
Žádný actual JVM/full repeat, worker rebuild, instalace, push či author self-merge.
Finální scoped semantic update/apply/validate, CLI scan/check a diff check PASS;
staré feature důkazy jsou výslovně odlišeny od tohoto čistého integration run.

## Integrace sloučeného T015

Aktuální parent je main `49c46b0bd165cf11e7b3eb0af04bf64fb93e23ce` (merged
PR55). Factory/JVM source a původní registration testy zůstávají byte-identické
reviewovanému `7859e16`; T015 projector, testy a pinned API fixture jsou přesně
z main. CI zachovává explicitní API bootstrap i všechny main compiler testy a
přidává registrars/factories modul. Sdílený configuration view nadále přidává
pouze tři původní registration relation kinds.

Čisté integrační kontroly T005/T008/T009/T015/mandatory: **124 PASS**, dva již
samostatně doložené actual T015 případy byly úmyslně deselected, **3.44s**;
XML `/workspace/factory-main49-pure.xml`. Původní actual38 a full558/10 se pro
nezměněné feature source neopakují. Nový head/base vyžaduje čerstvé remote CI.
Main prefix127 immutable episodes i dva původní Factory captures zůstávají
beze změny; generated grafy obnovuje pouze CLI.

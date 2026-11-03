# Compiler inspection a explicitní build workflow

Tato stránka popisuje implementaci PR #5, nikoli dokončení T002/T003 ani úplný
model Spring aplikace. Historické P aliasy jsou mapované v [registru](tasks/README.md). Python scan/build/hook/feature prepare
nadále nevyžadují JDK/Node a nespouštějí projekt, npm, databázi ani migrace.

`kgmaker status` vykazuje freshness source grafu a uložených compiler kontextů
odděleně. I když scan již publikoval aktuální source graf se stale compiler markerem,
status vrátí 2 a vytiskne přesný `inspect code`/`inspect frontend` příkaz. `check`
používá stejný stale gate. Tyto offline kontroly nespouštějí worker ani projektový
proces. Workspace JSON status navíc vrací oddělené `source_graph_current`,
`compiler_contexts_current` a repo-qualified `stale_compiler_contexts`.

## Ověřená matice a technologická volba

| Komponenta | Verze | Skutečně ověřený rozsah |
|---|---|---|
| Python | 3.12.14, pytest 8.3.4 | Regrese a bounded worker transport |
| JDK / javac | Temurin 21.0.6+7 | JavacTask/Trees, overload a mixed Java/Kotlin |
| Kotlin compiler | 2.1.10 distribuce, K1 frontend v language 1.9 compatibility; Gradle export ověřen i s pluginem 2.2.20 | BindingContext, KotlinTypeMapper, overload, constructors, lambda callers, callable references, source-defined operators, extension/default/inline/suspend metadata a volání do Java; build konfigurace zůstává oddělená provenance |
| Kotlin K2 (opt-in) | Standalone Analysis API / FIR 2.1.10, backend `k2-analysis-api-2.1.10-v1` | Mixed Java/Kotlin named-function calls, compiler PSI light-method JVM descriptors, explicit unresolved/ambiguous boundaries; source CFG/property/lambda semantics remain PARTIAL |
| Bytecode | ASM přibalené v Kotlin 2.1.10 | Deskriptory, invokes, základní CFG, ordered selected-classpath CHA (open world) |
| Maven | 3.9.9 | EventSpy effective session export v2, parent/BOM, effective dependencies, profily, generated roots, toolchain, ordered classpath, explicitní test build |
| Gradle | 8.12.1 a lokálně 8.13 | Skutečný source-set export/test build PASS v GitHub Actions run 38703831737; lokální explicitní Gradle 8.13 build ověřuje Kotlin task options a čerstvý class output |
| TypeScript / Node | 5.7.3 / 24.19.0 | Program/TypeChecker, call signatures, overloads, React JSX event binding |
| React typings | React 18.3.1, @types/react 18.3.18 | Intrinsic JSX onClick v malé fixture |

Výchozí backend zůstává explicitně omezený `k1-compat-1`. Opt-in K2 používá skutečnou
Standalone Analysis API/FIR 2.1.10; nejde o přejmenování BindingContext backendu.
Podporovaná K2 matice není tvrzením úplné podpory Kotlin language 2.1. Java release request je explicitní,
Maven import přenáší získaný release. V integrační fixture byl ověřen pouze release 21.
Kotlin options v manifestu nesou vlastní schema/status a vstupují do content-bound
identity compiler kontextu. Změna flagu proto zneplatní dotčený kontext, ale
nezmění ostatní module/source-set kontexty. Zachycený language/API target ani plugin
není tvrzením, že jej současný K1 frontend umí analyzovat.
Maven export zapisuje resolved plugin classpath jako soubory s SHA-256; import
nebo offline kontrola odmítne změněný JAR před publikací. Maven default
`${kotlin.compiler.*}` bez určené hodnoty se nezapisuje jako compiler option:
context má `PARTIAL` a konkrétní diagnostiku. Pro explicitní ověření použij
`kgmaker project build-plan --root . --build-system maven --offline --output /tmp/kotlin-plan.json`,
pak `kgmaker project build-run --plan /tmp/kotlin-plan.json` a
`kgmaker project build-import --root . --manifest /path/from/build-run/manifest.json`.
TypeScript worker v3 (project references od v2) podporuje solution-style project references uvnitř zvoleného
repo rootu. `kgmaker inspect frontend --root /repo --tsconfig tsconfig.json`
rekurzivně načte nejvýše 128 configů, vytvoří skutečné Program/TypeChecker pro
projekty a použije compiler source redirects bez `emit`, `tsc -b` či instalace.
`context.project.project_graph` v1 uchovává repo/config identity, reference,
root files, effective options a source/reference content fingerprints, které se
propagují po reference hranách. Symboly nesou `project_id`; stejnojmenné funkce
v různých projektech se nesloučí. Starý single-project vstup zachovává tvar IDs;
graph/store v1/v2/v3 a worker protocol v1 se nemění.
Identita a deklarovaný typ source targetu pocházejí vždy z AST/TypeCheckeru jeho
vlastnícího projektu, i když má consumer jiné compiler options. Call-site
signature zůstává pohledem consumeru. Reference s nastavením
`disableSourceOfProjectReferenceRedirect: true` jsou v tomto source-only
inspection kontraktu odmítnuty diagnostikou `TS_PROJECT_REFERENCE_REDIRECT_DISABLED`
před publikací; emitted declaration se nevydává za aktuální source target.
Python porovnává úplné preflight/analyze mapy compiler input path → SHA-256,
nejen obsah souborů známých před spuštěním. Nový či odebraný dependency vstup
vrací STALE před publikací grafu. Konstrukce a provider replay sdílejí jeden
selection-key helper: Kotlin backend/version patří pouze do JVM klíčů.
Původní frontend klíče, staré záznamy bez klíče i dočasné TS klíče s dvěma
irelevantními Kotlin None poli se při reinspection sloučí do jednoho slotu;
neznámé opaque klíče a odlišné K1/K2 varianty se nepřejmenovávají.

`tests/test_typescript_project_references.py` ověřuje dva konkrétní přeshraniční
targety i při neexistujících/stale `.d.ts` výstupech, transitive input freshness
bez worker procesu a chybějící/cyklickou/outside-root reference či nejednoznačné
vlastnictví zdroje. Invalidní reference graph selže s cestou configu před zápisem
store; nezvyšuje neúplný výsledek na COMPLETE. Celý T003-S08 zůstává PARTIAL:
rozšířená paths/exclude acceptance, generics/callbacks a BE–FE value flow jsou
samostatná zadání. Více repo rootů a diskový incremental compilation cache
nejsou tímto kontraktem implementovány.

Zvolený bytecode engine je přibalené ASM, nikoli SootUp. Pilot nepotřebuje jeho
whole-program režim: deskriptory a instrukce zůstávají oddělené od source grafu,
CHA kandidáti jsou konzervativní a jejich úplnost je vždy false. JAR závislosti
jsou kontrolovány pomocí `workers/jvm/dependencies.lock.json`. Kotlin compiler
je Apache-2.0 s notices distribuce; ASM je BSD-3-Clause, Jackson Apache-2.0,
TypeScript Apache-2.0. Offline builder kopíruje Kotlin distribution licenses.
Kotlin ZIP byl obsahově připnut, jeho publisher checksum nebyl v pilotu ověřen;
obsahová kontrola není důkaz autenticity.

## Reprodukovatelné explicitní kroky

### Selected tsconfig freshness (T003-S08-W02)

Worker3 přidává `project.input_discovery` v1 a context marker
`typescript-input-discovery-1`. TypeScript sám respektuje extends/baseUrl/paths/
include/exclude; Python replayuje zachycené content hashes, existence/realpath
pozorování a directory membership. Root/project package metadata a lockfiles
jsou obsahově svázané. Změna nepoužitého sibling configu nebo excluded-unused
obsahu nestaluje selected context; relevantní input či dříve missing dependency
ano. Negativní/mixed snapshot nepublikuje graf, offline status/hook nespustí Node.
Legacy snapshot, TS selector sloty a JVM politika zůstávají beze změny.
Discovery membership je konzervativní a má explicitní limity; nejde o persistent
incremental compilation cache. [Freshness guide](typescript-freshness.md) a
[note45](changes/45_scopeTypeScriptConfigFreshness.md) uvádějí přesnou matici.

### Bounded TypeScript callbacks (T003-S08-W03)

Worker4 keeps compiler-selected generic/overload signatures and canonical owner
parameter IDs through barrel aliases. Named and inline callback arguments bind to
local higher-order parameters. Parameter invocations and unions use incomplete
`dispatch_candidates`; mutable/any values never promote an arbitrary initializer
or signature to a concrete target. Ambient declared callable contracts remain
compiler evidence, separate from runtime implementation proof. Protocol1/model
schemas are unchanged; existing candidate navigation is reused.
[Callback guide](typescript-callbacks.md) documents limits, non-goals and CLI examples;
[note53](changes/53_resolveBoundedTypeScriptCallbacks.md) records exact local proof,
remaining full validation and blocked CI. This does not complete all of T003-S08.

### Windows user-space ověření (T003-S11-W03)

Transport používá omezené souběžné čtení pipe bez POSIX selectorů. Explicitní
buildery používají nativní JDK `.exe`, platformní classpath separator a přímý Java
compiler entrypoint místo `.bat` launcheru. JVM inspection vyžaduje plný JDK21+;
JRE-only a známý starší JDK končí `TOOLCHAIN_UNAVAILABLE` před procesem.
SOURCE_ONLY tyto runtimy nepotřebuje a nic neinstaluje/buildí.

Skutečný Windows restricted-user smoke ověřil core, Java, existující K1 Kotlin
subset a TypeScript v cestách s mezerami: run40351407076/job121672139333,
43 PASS / 2 scoped SKIP, 50.23s (Windows Server2025/Python3.12.10/JDK21.0.6).
K2 Windows se netvrdí; SKIP zahrnuje jeho nepřipravený artefakt a POSIX-only test. [Windows guide](windows-install.md) uvádí prerequisite kontrakt a
[change note40](changes/40_supportWindowsUserInstall.md) přesné provedené kontroly.
Windows `project build-plan/build-run` vrací explicitní `UNSUPPORTED_PLATFORM`
před procesem či zápisem run/store; pro ověřené lokální artefakty zůstává BUILD_IMPORT.

### Distribuce build exporteru

T003-S11-W02 přidává `build/exporters.json` (schema/protocol 1) a `build/LICENSE`
do resource package. Záznam obsahuje relativní cestu, SHA-256, očekávané exporter
ID (`maven-session-2` / `gradle-composite-1`) a cestu licence. JAR obsahuje pouze
projektový EventSpy; Maven/Gradle/JDK ani jejich závislosti se nedistribuují.
Checksum zajišťuje vazbu obsahu, nikoli autenticitu vydavatele.

`project build-plan` ověří dostupný descriptor a adapter bez spuštění procesu.
Nový plán aditivně nese `exporter_contract`, který váže také descriptor a licenci;
`build-run` odmítne změnu před vytvořením execution directory. Očekávané schema a
exporter ID kontroluje před publikací BuildManifestu. Chyba nepublikuje silnější
evidence a nemění graph store. Starý plán nebo explicitní legacy workers home bez
descriptoru zachovává původní content-bound režim; nejde o nově ověřenou distribuci.

```bash
# Explicitní příprava trusted artefaktu a descriptoru před sestavením wheelu:
python workers/build/build.py --maven-home /path/to/apache-maven-3.9.9 --java-home /path/to/jdk21
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/kgmaker-dist .
# V čistém cílovém venv mimo checkout; nástroje musí být připravené na PATH:
python -m pip install --no-index --no-deps /tmp/kgmaker-dist/kgmaker-0.1.0-py3-none-any.whl
kgmaker project build-plan --root /path/to/maven-or-gradle-project --phase compile --output /tmp/plan.json
kgmaker project build-run --plan /tmp/plan.json
```

`tests/test_exporter_distribution.py` skutečně sestaví sdist/wheel, instaluje jej
offline mimo checkout a provede Maven i Gradle export; negativní varianty ověří
hash/protocol mismatch bez mutace posledního grafu. Build aplikace se spouští
výhradně explicitním `build-run`, ne během instalace, scan, hook nebo feature.
Windows, immutable publikace a úplná release/benchmark matice zůstávají otevřené.

### Instalace mimo checkout

Od T003-S11-W01 obsahuje wheel balíček `kgmaker_workers`. Jeho adresář má stejný
layout jako `workers/` v checkoutu. Resolver používá v pořadí explicitní
`--worker-home`, `KGMAKER_WORKERS_HOME`, instalovaný balíček a při přímém běhu ze
zdrojů checkout. Explicitní chybějící či neúplný adresář nikdy nenahradí jiným
workerem. Missing runtime/artifact a nejednoznačný versioned JVM JAR vracejí
`TOOLCHAIN_UNAVAILABLE`; poslední index se nepřepíše.

Core wheel obsahuje skripty, lockfiles a zdroje trusted builderů. JDK/Node,
Maven/Kotlin ani npm samotné nejsou součástí wheelu. Runtime JARs s knihovnami a
TypeScript 5.7.3 se zabalí pouze tehdy, když je release builder předem explicitně
připraví níže uvedenými příkazy. Stejné artefakty jsou zahrnuty i do sdist.
Po přípravě použijte čistý build adresář, aby starý `build/lib` nezanesl do wheelu
odstraněné soubory; sestavení ani instalace nespouštějí npm či compiler builder.

```bash
# V čisté kopii zdrojů; nejprve explicitně připravte volitelné workery níže.
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/kgmaker-dist .
# Cílový venv mimo checkout:
python -m pip install --no-index --no-deps /tmp/kgmaker-dist/kgmaker-0.1.0-py3-none-any.whl
kgmaker scan --root /path/to/project
kgmaker inspect frontend --root /path/to/project
# Alternativa s vlastní kompletní distribucí, bez fallbacku:
KGMAKER_WORKERS_HOME=/opt/trusted/workers kgmaker inspect code --root /path/to/project
kgmaker inspect frontend --root /path/to/project --worker-home /opt/trusted/workers
```

Linux acceptance v `tests/test_worker_install.py` skutečně sestaví wheel,
nainstaluje jej offline do čistého venv, odstraní vstupy a analyzuje Java i
TypeScript mimo checkout. Samostatná source-only varianta ověřuje sdist → wheel
bez runtime artefaktů a scan bez JDK/Node nebo child procesů. Windows transport,
immutable publication a úplná release matice zůstávají samostatnou prací.

Závislosti workerů se instalují samostatně, nikdy při scan nebo hooku:

```bash
python workers/jvm/build.py --kotlin-home /path/to/kotlinc \
  --maven-repository /path/to/maven-repository --java-home /path/to/jdk21
python workers/build/build.py --maven-home /path/to/apache-maven-3.9.9 \
  --java-home /path/to/jdk21
npm ci --ignore-scripts --prefix workers/typescript
npm ci --ignore-scripts --prefix fixtures/build-inspection/frontend
```

JVM builder požaduje Jackson 2.18.2 a přesné dependency hashes. Maven `pom.xml`
workeru je alternativní distribuční popis; jeho Maven package zde nebyl ověřen.
Ověřeným buildem workeru je uvedený offline Python builder. Worker rebuild
neprovádějte současně s inspection: distribuce není zatím publikována pomocí
immutable versioned directories. Změna distribuce během analysis je odmítnuta.

```bash
kgmaker project build-plan --root fixtures/build-inspection/maven \
  --phase test --offline --java-home /path/to/jdk21 \
  --output /tmp/kgmaker-plan.json
kgmaker project build-run --plan /tmp/kgmaker-plan.json
kgmaker project build-import --root fixtures/build-inspection/maven \
  --manifest /absolute/path/from/build-run/manifest.json
kgmaker inspect code --root fixtures/build-inspection/maven \
  --build-id BUILD_ID --context root:main
kgmaker inspect frontend --root fixtures/build-inspection/frontend --ui-framework react
kgmaker coverage report --root fixtures/build-inspection/frontend --format json
kgmaker callgraph callees --root fixtures/build-inspection/frontend --symbol SYMBOL_ID
kgmaker flow render --root fixtures/build-inspection/frontend \
  --entry SYMBOL_ID --view control-flow --format mermaid
kgmaker project inspect --root fixtures/build-inspection/maven --format json
kgmaker entrypoints --root fixtures/build-inspection/maven --format json
kgmaker runtime import --root fixtures/build-inspection/maven --manifest runtime-manifest.json
```

BuildPlan obsahuje přesné argv, executable/exporter checksum, úplný inventář
včetně dirty/untracked souborů, hash povoleného prostředí, timeout a policy
`LOCAL_TRUSTED`. Ta dovoluje vykonání důvěryhodného projektového kódu podle
hostitelské policy; kopie do `.kgmaker/build-runs/ID/snapshot` není sandbox.
Žádný shell řetězec se nesestavuje. Dřívější target/build nejsou kopírovány.
Plán je jednorázový, změna obsahu nebo povoleného prostředí jej zneplatní.
Volitelné `--java-home` vybírá externí JDK explicitně. BuildPlan obsahově váže
kanonický home, `java` a `javac`; build dostane přesné `JAVA_HOME` a jeho `bin`
má přednost v `PATH`. Exporter musí ohlásit tentýž Java home. Chybějící nebo
změněný JDK je `TOOLCHAIN_UNAVAILABLE`/`STALE_PLAN` před buildem, odlišný runtime
JDK je `EXPLICIT_TOOLCHAIN_MISMATCH` bez čerstvých outputs. Bez přepínače zůstává
kompatibilní host-default chování starších plánů.
Gradle vyžaduje hostitelský režim s možností JVM socket/IPC; bez něj build
vrací FAILED a zachová log, bez čerstvých outputs.

Maven adaptér čte reálný `MavenProject` v execution session, nikoli pouze pom.xml.
Export `maven-session-2` přenáší effective parent, resolved dependencies,
dependency management, importované BOM z parent chain, aktivní i injected profily,
compiler release, generated source roots a Java/Maven toolchain. Tyto položky se
validují a jejich hash je součástí výběru compiler kontextu. Reálná Maven fixture
ověřuje, že profil a BOM změní manifest a že aktuální reactor output má přednost
před starým JAR v repository.

Gradle exporter čte skutečné `SourceSetContainer`; Kotlin DSL se neparsuje regexem
a export označuje roots pod `build/generated`. Pokud source set obsahuje Kotlin compile
task, exporter čte jeho finalizované `compilerOptions`: compiler/language/API/JVM
verzi, relevantní booleany, opt-ins a free args. Pluginy jsou content-bound SHA-256
identity a `-P` volby z compiler argumentů; nedostupné hodnoty zůstávají `PARTIAL`
s diagnostikou. Maven EventSpy stejným způsobem zachytí effective konfiguraci
úspěšného `compile`/`test-compile` mojo. Obsah vytvořený annotation processorem
se přijímá jen z explicitního úspěšného buildu: zůstává pod konkrétním build runem,
manifest ukládá SHA-256, execution ID a snapshot hash a jakákoli následná změna
import zneplatní. Reálná fixture provede následnou JVM inspection a ověřuje
`origin=generated`; scan ani běžná inspection processor nespouštějí. Gradle
custom varianty/included builds a
cross-repo artefakty vyžadují další fixture. Tyto mezery drží T003-S03 v PARTIAL.

Test result rozlišuje NOT_RUN, ZERO_TESTS, SKIPPED, PASSED, FAILED a počty z
čerstvých Surefire/Gradle XML reportů. Chybějící report neznamená TEST_PASS.
BUILD_IMPORT ověřuje obsah, ale supplied export má trust UNVERIFIED. Build
success ani call path nemění availability verdict.

## JSON, resolution, CFG a omezení

Graph v3 je kompatibilní rozšíření v2 o symbols, call_sites, cfgs a oddělené
analysis_annotations. V1/v2 se stále čtou; historické calls se nepovyšují na
SYMBOL_RESOLVED. [JSON schema](schemas/graph-v3.schema.json) doplňuje runtime
foreign-key validátor před atomickým zápisem. LLM annotations nemohou vložit
technické fields, neexistující evidence ani cílové ID.

Workers mluví protocol v1, handshake uvádí compiler/capabilities. Stdout obsahuje
jediný JSON, logy patří stderr. Transport používá bounded vstup 16 MiB, výstup
64 MiB, stderr 256 KiB, timeout a cancel-file. Duplicitní JSON keys a nefinite
hodnoty se odmítají. Javac má `-proc:none` a `-implicit:none`; analysis nespouští
annotation processors ani inicializaci projektových tříd.

Explicitní compiler inspection vytváří BUILD_IMPORT kontext lokálně načtených
compiler vstupů (LOCAL_COMPILER_INPUTS), s CONTENT_VERIFIED obsahem. Není to
BUILD_EXECUTE ani tvrzení BUILD_PASS/TEST_PASS; SOURCE_ONLY fallback zůstává
syntaktický scan. Při skutečném manifest importu je původ dodaného exportu zvlášť
UNVERIFIED.

`project inspect` čte Maven reactor deklarace bez spuštění Maven a vrací
`SOURCE_ONLY_DECLARED_MODEL`; profily, BOM mediation a effective classpath
zůstávají nevyřešené do explicitního build exportu. Po JVM inspection se nad
compiler symboly provádí deterministická frameworková projekce. Spring
stereotype/`@Bean`, injection podle typu s `@Qualifier`/`@Primary`, profile
boundary, HTTP/listener/scheduler entrypoint, advice a self-invocation proxy
boundary jsou `FRAMEWORK_DERIVED`. Spring pravidla v6 vyhodnocují dodané profiles,
properties a available-class scope jako ACTIVE/INACTIVE/UNKNOWN. Jen unikátní ACTIVE
bean dostane `injects_bean`; UNKNOWN/ambiguous kandidáti mají `may_inject_bean` a
diagnostiku. Custom Condition se nespouští. Meta-stereotype chain se rozvíjí pouze
přes compiler annotation-type symboly s bounded hloubkou; cizí shodné krátké jméno
není Spring anotace. `spring_component_packages` dává package/subpackage scan scope
a je součástí context fingerprintu. List/Set/Collection/Iterable a Map<String,T>
injection přenáší všechny ACTIVE členy; Optional používá unikátní výběr a
ObjectProvider/Provider je konzervativní lazy kandidát. Statický `@Import`
rozšiřuje dosažitelný konfigurační graf i mimo component scan; stav podmínek
konfigurace se skládá se stavem její `@Bean` metody. Obyčejná importovaná třída
je bean. ImportSelector/DeferredImportSelector používají níže popsaný bounded
compiler subset; registrar se neprovádí a hlásí explicitní boundary.
`@Bean` mimo compiler-resolved `@Configuration` je odmítnut. JPA
`@Entity`/`@Table`/`@Column`, Spring Data
repository/query a přesné názvy tabulek/sloupců se vážou na source-only schema
nodes, pokud jsou ve stejném snapshotu. Chybějící aktivní profil, naming
strategy, dynamic query, custom registrar, proxy execution nebo deployment/data
availability zůstávají diagnostikou či UNKNOWN.

JPA pravidla `annotation-source-v4` používají compiler identity pro oddělené
entity, embeddable a mapped-superclass deklarace. Umístění `@Id`/`@EmbeddedId`
volí FIELD nebo PROPERTY access; embedded atributy a explicitní override mají
vlastní uzly. Asociace nesou cílovou entitu a roli OWNING/INVERSE, přičemž
`mappedBy` se váže na konkrétní protistranu. JoinColumn/JoinTable se nemíchá se
scalar `@Column` a neověřený target či `mappedBy` zůstává diagnostikou.
Při explicitním `--kotlin-backend k2` se pro constructor properties zachová
K2 annotation identity a use-site target. `@field:Id`/`@field:EmbeddedId`
vybere FIELD a `@get:Id` vybere PROPERTY; `@Access` má přednost, ale jeho
nesoulad s identity targetem je diagnostikován a nevytvoří silnější atribut.
Kotlin `@Id` bez explicitního FIELD/GET targetu zůstává nejednoznačný. Embedded
Kotlin ID reuseuje stávající entity/embeddable uzly a nevyžaduje nový graph typ.
Compiler values zachovají nested `@AttributeOverride` column a class literals;
nevyřešená explicitní table/column/override hodnota zůstává UNKNOWN a nevytváří
náhradní fyzické jméno. Testovací JPA API deklaruje skutečné FIELD/METHOD cíle,
takže implicitní FIELD default i dual-use-site nejednoznačnost odpovídají API.
Kotlin embeddable member annotations se filtrují podle Jakarta/Javax identity.
Bez vlastního embeddable `@Access` se column metadata zachová jen pro
jednoznačné FIELD inheritance; PROPERTY, mixed nebo neznámý container access
zůstává UNKNOWN bez fyzického defaultu. JPA annotation identity se omezuje na
známé názvy přímo v `jakarta.persistence`/`javax.persistence`; odpovídající
subpackage se nepovažuje za compiler-resolved JPA API.
Mapped-superclass atributy dostanou deklarující `orm_attribute` a zvláštní
effective projekci pro každou ověřenou entitu. `declaring_owner` a
`effective_owner` jsou exact compiler class identities; `inherits_attribute`
váže projection na zdrojový uzel. Zděděné FIELD/PROPERTY access určuje ID v celé
mapped-superclass hierarchii. K2 property annotations a Java field/getter facts
zůstávají v jejich skutečném use-site/access scope. Entity-level
`@AttributeOverride` přebije mapped-superclass hodnotu podle nejbližší deklarace;
stejně pojmenované fieldy ani unresolved override nevytvoří vybraný column edge.
Při entity inheritance se SINGLE_TABLE/JOINED projekce váže na root table a
TABLE_PER_CLASS na konkrétní entity table. Tento výsledek je statická projekce,
ne deployment/schema compatibility proof; nevyřešený access, type identity,
inheritance strategy nebo class override zůstává UNKNOWN.
Spring Data repository model se vybírá z compiler-resolved generic supertype a
přesného entity owneru. Entity atributy se indexují podle canonical owner
identity, nikoli podle prostého class name; derived predicate zůstane unresolved,
když compiler facts neprokáží jediného ownera.
Explicit JPQL uses the declared `@Entity(name)` (or its default class name) and
requires exactly one compiler-owned entity; the repository domain type never
substitutes for an ambiguous query entity. Compiler return type identity likewise
selects an exact entity/projection node. A source-level simple return name is
accepted only when the JVM method descriptor proves its canonical owner; a
missing qualified owner, erased generic type variable, or duplicate simple name
without that proof remains unresolved.
Derived query parser pokrývá podporované find/read/get/query/search/stream/count/
exists/delete/remove prefixy, Top/First/Distinct, běžné operátory, And/Or a
OrderBy. Property path se musí vyřešit proti přímému, embedded nebo association
atributu; teprve pak vznikne `filters_by`/`orders_by`. Query nese `query_reads`
nebo statický `query_deletes` intent, nikdy tvrzení o provedeném SQL či commitu.
Explicitní `@Query` je vlastněno přesným compiler method symbolem. JPQL řeší
entitu, alias paths, parametry a return entity/projection; native SQL váže pouze
explicitní názvy tabulek v aktuální ORM projekci a při kolizi zůstává ambiguous.
Statické JPA named queries mají oddělenou definici a repository reference; SpEL,
`${...}` a jiné dynamické části se nerozvíjejí.

Source CFG vzniká deterministicky z compiler AST IR. Zachovává podmínky,
protilehlé větve, return/throw, loops, finally abrupt continuations a await/resume.
Kotlin frontend navíc zachovává when bez fallthrough, Elvis, safe-call,
short-circuit, konstruktory, lambda caller identity a compiler-resolved uživatelské
operátory; operator call site je součástí odpovídajícího CFG bloku. Callable
reference zůstává referencí a není vydávána za provedené volání. Custom property
getter/setter mají přesný method symbol, vlastní CFG a čtení/zápis odkazuje na
`ACCESSOR` call site; backing-field `field` nevytváří rekurzivní accessor hranu.
Property initializers a `init` bloky běžné třídy se řadí podle zdroje do přesného
primary-constructor method/CFG a jejich calls používají constructor caller. Top-level
properties mají samostatný file-facade `<clinit>()V`; object/companion property a
`init` bloky používají constructor daného objektu, takže se realms neslučují.
Exceptional edges jsou konzervativní, nikoli řešení exception/path feasibility.
Try-with-resources close, neznámé konstrukce a scheduling mají explicitní boundary.
Interprocedural process view používá tyto CFG; recursion, neúplný dispatch,
limity hloubky/počtu uzlů a nerozlišené cíle zůstávají hranicí, nikoli jistou sekvencí.

Běžné source-only name-match hrany zůstávají v legacy části grafu jako kandidáti.
Compiler call sites jsou samostatné, cíle používají vlastníka a descriptor/signaturu.
Application-only CHA není úplný dependency dispatch; bytecode instruction_index
není bytecode offset. Kotlin inline/suspend/default argument metadata jsou zachována,
jejich compiler-generated bodies a coroutine state machine se však nevydávají za
source CFG. Framework proxy, generated default/coroutine bodies a plný def-use ještě
nejsou pokryty.
Source mapping bez debug metadata nevymýšlí řádky.

Spring conditions/custom registrars, rozšířený Hibernate model a query grammar,
Kafka cluster/retry/DLT, Feign/WebClient/RestClient, service mapping a BE/FE
value-flow nejsou tímto inkrementem dokončeny. Stávající Flyway/workspace/
availability implementace zůstává zachovaná. Data/integration view zatím poskytuje
JSON, nikoli dokončený framework Markdown/Mermaid renderer. Runtime import je
samostatný důkaz konkrétního běhu; nepřítomnost pozorování nic nevyvrací.


## Integrace s běžným workflow

Build context může explicitně nést `database_id`, `schema_stream_id`,
`persistence_unit` a `naming_strategy`. ORM binding filtruje podle databázového a
stream realm; shodné tabulky v několika realms zůstávají ambiguous. Bez explicitního
`@Table` se fyzická tabulka neodvozuje univerzálním camelCase→snake_case pravidlem.
Skutečný reactor test `test_mv02_real_reactor_output_precedes_stale_repository_jar`
ověřuje čerstvý sibling output proti starému JAR ve file repository.

`scan`, `hook-context` a single-root `feature.current_graph` nyní používají
`graph_provider.retain_compiler_layer`. Ověří zdroje (včetně nových souborů),
konfiguraci, classpath a worker distribuci a zachovají compiler symboly, call sites,
CFG a evidence. Žádný worker/build se při tom nespustí. Stale vstup odstraní pouze
fakta dotčeného compiler kontextu; kontext zůstane s `freshness=STALE`, důvodem a
přesným příkazem `inspect code` / `inspect frontend`. Ostatní čerstvé kontexty
zůstávají použitelné a hook předá stale diagnostiku v bootstrapu.

Nová inspection začne ze scan baseline a před atomickým zápisem sloučí nový
module/profile selection s ostatními validními kontexty. Worker symbol IDs obsahují
context ID, takže varianty nesplynou; stejný selection se při opakování nahradí.
Workspace snapshot zachová compiler collections v graph schema v3 a kvalifikuje
jejich symbol, context, evidence, call-site i CFG identity repository namespace.
Jednotný výběr contextu používají query, impact, feature i report. Reálný
`test_ac02_real_end_to_end_context_profile_and_classpath_lifecycle` ověřuje celý
veřejný sled, dvě profilové varianty, packet revision a classpath invalidaci.
Contextová projekce zachovává společné source/dataflow hrany a filtruje pouze
konkurenční compiler vrstvy. T003-S02/AC02 je VERIFIED_IN_SCOPE pro výše uvedenou
matici; rozšíření build/framework/jazykových variant patří do S03–S10.

Explicitní `--java-home` vybírá launcher JDK (reálná Maven matice JDK21+22). Samostatný fork/toolchain compiler pluginu tento kontrakt nedokazuje; odlišný exportovaný Java home runner odmítne. Fixture dvou skutečných JDK přijímá `KGMAKER_TEST_OTHER_JAVA_HOME`; bez druhého JDK hlásí SKIP.
## T003-S03-W02: explicit custom source sets

Gradle exporter `gradle-source-sets-2` reads `SourceSetContainer` rather than
inferring variants from build-script text. Exact built-ins `main`, `test`,
`testFixtures` map to production/test/test_fixture. Projects may explicitly supply
`ext.kgmakerSourceSetScopes = [integration: 'test', tooling: 'development']`
in Groovy (`extra["kgmakerSourceSetScopes"] = mapOf("integration" to "test")`
in Kotlin DSL). Allowed values are production/test/test_fixture/development/unknown.
Custom names without a declaration remain unknown with UNMAPPED_GRADLE_SOURCE_SET;
invalid declarations yield unknown with INVALID_GRADLE_SOURCE_SET_SCOPE. No
substring heuristic grants test or production scope. Per-context `scope_origin`
records GRADLE_CONVENTION / EXPLICIT_MAPPING / UNKNOWN; source-set IDs retain
project identity. Existing manifests without this additive field remain accepted;
graph/store v1/v2/v3 and worker transport do not change. Generated sources retain
existing execution/hash binding. This does not add Android/KMP variant APIs.

Explicit workflow (after reviewing the content-bound build plan):

```bash
kgmaker project build-plan --root . --build-system gradle --executable /path/to/gradle --offline --output /tmp/gradle-plan.json
kgmaker project build-run --plan /tmp/gradle-plan.json
kgmaker project build-import --root . --manifest /path/from/build-run/manifest.json
kgmaker inspect code --root . --build-id BUILD_ID --context :integration --scope test
```

Real Gradle 8.13 fixture in `tests/test_gradle_variants.py` covers main/test,
generated Java, custom mapped integration and unknown contest under src/main;
negative tests cover conflicting memberships and invalid provenance without mutation.

### Review fixes: source-set freshness and convention provenance

New JVM contexts with a supplied source-set model use
`source_snapshot_version=selected-source-set-1`. Capture, pre-publication checks
and offline replay share the same helper: selected module/set membership (including
`:generated`), configuration directly in root/module ancestor directories, Gradle
configuration under those directories, and explicit build/settings scripts. Selected
resources remain inputs; sibling source sets/resources are excluded even with an
identical scope. Configuration additions/removals and selected source additions are
compared by content inventory. Legacy contexts without the marker retain their
original scope-wide freshness gate until reinspection; no silent narrowing occurs.

A supplied GRADLE_CONVENTION now requires exactly main→production, test→test or
testFixtures→test_fixture. Custom sets must use EXPLICIT_MAPPING or UNKNOWN.
Manifests lacking scope_origin remain accepted as legacy, without inventing a
conventional origin. Negative imports validate before changing the store.
`tests/test_gradle_variants.py` covers offline scan/hook/current_graph without
subprocesses, shared/selected config invalidation, forged convention rejection,
byte-for-byte preservation and valid/legacy provenance.

## T003-S03-W03: Gradle composite identity

`gradle-composite-1` coordinates explicit `kgmakerExport` tasks in included builds
inside the captured snapshot. Each build writes a separate fragment; the root
merges completed fragments. Included repository IDs derive deterministically from
the build-root-relative path, not project names. Context IDs include that identity;
modules with the same name in separate builds remain distinct. `build_root` is an
optional manifest field; imports reject ambiguous repo/build-root ownership.
Existing manifests without it and graph/store v1/v2/v3 remain readable.

The existing ordered `classpath` and `realm` carry dependency evidence. Gradle's
resolved project substitution selects current included outputs over stale external
artifacts with the same coordinates. The runner preserves Gradle order, records
content hashes and retains the included repo identity. Jar ownership comes from
actual Gradle archive tasks; conflicting output ownership yields
AMBIGUOUS_BUILD_OUTPUT_REALM without choosing either repo.
Při importu je `classpath.realm` uznáno jen při jediném stejně hashovaném,
execution-bound outputu odpovídajícího producenta. Samotný Jar task model
neprokazuje existenci výstupu; chybějící nebo kolidující producer realm je
odmítnut před publikací manifestu.

```bash
kgmaker project build-plan --root . --build-system gradle --offline --output /tmp/composite-plan.json
kgmaker project build-run --plan /tmp/composite-plan.json
kgmaker project build-import --root . --manifest /path/from/build-run/manifest.json
kgmaker inspect code --root . --build-id BUILD_ID --context INCLUDED_CONTEXT_ID --scope production
```

`tests/test_gradle_included.py` uses actual Gradle8.13 with duplicate lib modules,
a stale local Maven jar and an independent external file dependency. It verifies
substitution, exact classpath order, separate repo IDs and included inspection
inputs; negative tests verify ambiguous realm ownership and no-mutation import
failure. Included roots outside the captured tree emit UNBOUND_INCLUDED_BUILD;
missing fragments emit INCLUDED_BUILD_EXPORT_UNAVAILABLE. Such scope is PARTIAL,
never evidence of complete source coverage. Non-Java model aggregators retain
UNSUPPORTED_GRADLE_VARIANT diagnostics. No implicit process is added to offline
analysis commands.

## T003-S04-W01 — explicitní K2 Analysis API

Samostatný backend `k2-analysis-api-2.1.10-v1` používá FIR `analyze` a
`resolveToCall` ze skutečné Standalone Analysis API. JVM identity vycházejí
z jednoznačné compiler light-method signatury, nikoli z textového odhadu typu.
Java zůstává JavacTask/Trees. Worker protocol v1 a graph v1/v2/v3 se nemění;
backend/verze a SHA-256 distribuce vstupují do context identity a evidence.
K1 a K2 mají oddělené selection keys a target adresáře. Offline refresh zachová
čerstvý K2 kontext a jeho stale diagnostika nabízí opět `--kotlin-backend k2`.

Explicitní příprava pro release builder/developera (nic z toho nevolá instalace
ani `scan`/`inspect`):

```bash
python workers/jvm/fetch_k2.py --output /tmp/kgmaker-k2-api
python workers/jvm/build.py --backend k2 --analysis-api-home /tmp/kgmaker-k2-api \
  --kotlin-home /opt/kotlinc-2.1.10 --maven-repository /opt/trusted-m2 \
  --java-home /opt/jdk-21
kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10 \
  --worker-home /opt/kgmaker/workers \
  --classpath /opt/kgmaker/workers/jvm/target-k2/lib/kotlin-stdlib.jar
```

`fetch_k2.py` je oddělený explicitní síťový příkaz. Stahuje sedm JetBrains
Analysis API JARů 2.1.10 a Caffeine 2.9.3 z pevných repository URL a ověřuje
SHA-256 z `dependencies-k2.lock.json` před publikací; builder pracuje offline
a ověřuje všechny připnuté compiler/API/Jackson vstupy. Neplatné bytes
nepřepíší platný soubor. JDK ani compiler se automaticky nestahují. Volitelný
`target-k2` se balí pouze po explicitní přípravě; core wheel zůstává bez runtime.

Podporovaná konfigurace je compiler 2.1.10, language/API 2.1 a JVM target 21.
Importovaná jiná compiler/language/API/JVM verze nebo flags/plugins/opt-ins
se odmítnou před spuštěním workeru. Tím se neignoruje zachycená konfigurace
T003-S03-W04. Chybějící K2 distribuce nevyvolá fallback na K1.

Mixed fixture, dvě obsahově shodná spuštění, přesné caller/target JVM identity,
missing/ambiguous call, oddělení test scope, backend/version evidence,
strict no-publication, offline refresh a instalace mimo checkout jsou v
`tests/test_k2_backend.py` a `tests/test_worker_install.py`.

K2 nyní dodává omezená Kotlin type/property annotation fakta pro JPA use-site
projection a bounded Spring conditions, ale nedodává obecný source CFG, constructor ABI, runtime Spring activation, property/operator/reference/initializer call sites ani local/lambda
execution. Omezené default-body source mapping popisuje W02 a bounded coroutine
source/async boundaries W03 níže. Širší default-body coverage a obecné coroutine
state-machine CFG/runtime scheduling zůstávají mimo podporovanou matici.
Tyto hranice mají diagnostiky a stav PARTIAL;
nepodporovaná či nejednoznačná signatura nemá resolved target. Výchozí K1
compatibility cesta zachovává svou dřívější podporu. T003-S04 zůstává PARTIAL;
konkrétní běhy a AC mapování uvádí [change note35](changes/35_addK2AnalysisBackend.md).

V tomto omezeném JPA subsetu K2 zachovává compiler-resolved annotation identity,
use-site placement a konstantní či vnořené hodnoty. Explicitní nevyřešený
`@Table`, `@Column`, override nebo access nevytvoří náhradní fyzické mapování;
neznámý annotation subpackage není Jakarta/Javax JPA evidence. FIELD/PROPERTY
výběr vyžaduje doložený identity target nebo `@Access`, včetně ověření přístupu
pro embedded atributy.

## T003-S04-W04 — Ordered dependency dispatch

Javac a K1/K2 2.1.10 předávají u podporovaných virtuálních/interface call expressions
compiler-proven erased receiver. ASM používá stejný hierarchy index pro bytecode
`invokevirtual`/`invokeinterface`. Metadata selected JARů a adresářů se čtou bez
class loadingu, inicializace, buildů či aplikace. První classpath entry pro daný
binary class name vyhrává; pozdější kopie se nesjednocují. Explicitní artifact realm
zůstává zachovaný, bez mapování se používá stávající SHA-256 dependency realm.

`declared_target` je compiler/JVM declaration; `dispatch_candidates` jsou oddělené
`DISPATCH_CANDIDATE` důkazy. `dispatch_algorithm=CHA_ORDERED_SELECTED_CLASSPATH`,
`dispatch_classpath` a `dispatch_completeness_reason` jsou součástí provenance.
Candidate class musí být subtype compiler-erased receiveru **i** owneru skutečného
`declared_target`. Source type-variable/intersection receiver je konzervativně
unsupported: úplné upper bounds se zde nereprezentují, proto se kandidáti nevydají
a declared target i konkrétní compiler diagnostic zůstanou zachované.
Defining owner zděděného implementation body sám tyto dva vztahy splňovat nemusí.
Cache klíč obsahuje receiver, declared contract, method name a descriptor.
`dispatch_complete` zůstává false kvůli otevřenému runtime světu. Výsledek není
runtime observation, call-path feasibility ani dostupnost dat. Reference a
invokedynamic creation nejsou provedení; static/private/final/super targety
nedostávají virtuální enrichment.

Index má limity 10000 classes, 100000 archive/filesystem entries, 16 MiB/class a
128 MiB souhrnně čtených class bytes; hierarchy lookup nejvýše 256 visited types. Chybějící parent, corrupt archive/class,
shadow, duplicate entry či truncation mají lokalizovanou diagnostiku. Multi-release
JAR candidate enumeration je explicitně unsupported; physical declared lookup
používá bounded runtime-effective JarFile metadata včetně version-only classes,
aby je nenahradila pozdější plain kopie. Chybějící hierarchy nepřidává domnělou
implementaci. Package-private override access zůstává konzervativní hranicí.
K2 property/operator/local/lambda semantics zůstávají v dosavadním PARTIAL subsetu.
K2 source owner bez type-hierarchy proof nepřebírá subtype vazby ze staré compiled kopie.
Source overlay a physical hierarchy mají oddělené lookup/cache. Skutečné JDK
platform resources mají parent-first přednost a toolchain realm; metadata
`module-info.class` nejsou candidate classes. Compiler-proven `jvm_static`
kontradikce source/physical canonical vrací `SOURCE_BINARY_ABI_CONFLICT`, unresolved
site/PARTIAL a generated body bez nekompatibilního source locator/mapping.
Před physical canonical bindingem se ověřuje také úplný realm tuple
repo_id/module/source_set/scope: mismatch dává `SOURCE_BINARY_REALM_CONFLICT`,
source declaration zůstává zachovaná.

Příklad: po explicitním získání a importu content-bound ordered classpath spusť
`kgmaker inspect code --root project --kotlin-backend k2 --kotlin-version 2.1.10`;
`kgmaker callgraph callees --help` popisuje přepnutí dispatch kandidátů při navigaci.
Fixture `tests/test_dependency_dispatch.py` skutečně sestaví JDK21 API/base JAR a
dva implementation JARy v odlišných realms. Protocol v1 ani graph/store v1/v2/v3
se nemění; nová provenance pole jsou aditivní a staré vstupy zůstávají čitelné.
## T003-S05-W01 — bounded Spring import selectors

`annotation-source-v4` zachovává statický `@Import` a rozlišuje běžný importovaný
typ od přesných `org.springframework.context.annotation.ImportSelector` a
`DeferredImportSelector` v compiler-resolved transitivní hierarchii. Stejné krátké
jméno v cizím package není selector. Zdrojové Java compiler facts používají obě
JVM distribuce K1/K2; nejde o rozšíření nepodporovaných Kotlin annotation metadata.

| Vstup | Výsledek v tomto scope |
|---|---|
| Přesná selector identita a jediný `return new String[]{"app.Configuration"};` | `spring_import_selector`, `uses_import_selector`, `selects_import`; deklarovaná konfigurace pokračuje existujícím condition/reachability modelem |
| Zdrojový zděděný selector / default DeferredImportSelector | Stejná bounded literal cesta, konkrétní owner metody; deferred phase je metadata, nikoli provedený ordering |
| Custom exclusion filter nebo deferred Group | UNKNOWN; známé literal targets mají pouze `may_select_import` a UNKNOWN condition |
| Neznámé/komplexní tělo, chybějící metoda/target, vnořený selector target, neúplná hierarchie nebo legacy fakta | Explicitní `SPRING_DYNAMIC_IMPORT_BOUNDARY`; žádný odhadnutý ACTIVE selector bean |
| Registrar/factory, Spring context nebo runtime registrace | Nespouští se; další samostatné work packages |

Hierarchy i literal target array mají limit 128 položek; literal FQN nejvýše
512 znaků. Nekonstantní výrazy, field reads, concatenation, `Class.getName()` ani
jiné volání se nevyhodnocují. Libovolné return strings se nepublikují jako data.
Selector třída se nepovažuje za běžný bean jen proto, že je v `@Import`.
Evidence je `FRAMEWORK_DERIVED` se source method ID/hash, selected context a rule
version; nejde o `SYMBOL_RESOLVED` invocation ani runtime/data availability proof.
Statická selection proto nikdy sama nezpůsobí AVAILABLE nebo CONFIRMED_MISSING.

Graph/store v1/v2/v3 a worker protocol v1 zůstávají čitelné. Aditivní symbol fields
`type_hierarchy`, `import_selector` a `static_import_return` mají vlastní schema1;
legacy worker bez nich zůstává pro selector selection UNKNOWN. Chybná nová facts
se odmítnou před publikací. Rule v4 i obsah distribuce jsou ve fingerprintu nového
inspection contextu; scan/feature/audit žádný worker ani selector nespustí.
Nové Spring v4 metadata platí pouze pro JVM; TypeScript/React metadata a selection
key se touto změnou nemigrují. Dva čisté regresní testy v
`tests/test_spring_imports_context.py` porovnávají celé context hodnoty s baseline.

```bash
kgmaker inspect code --root project --manifest /approved/build-manifest.json \
  --context BUILD_CONTEXT_ID --kotlin-backend k2 --worker-home /approved/workers
kgmaker query --root project --context ANALYSIS_CONTEXT_ID app.DirectSelector
```

Classpath musí obsahovat skutečná schválená Spring API; profiles/properties a
component packages musí mít dodaný scope, jinak jejich stav zůstává UNKNOWN.
Pro reprodukovatelné testování se explicitně spouští
`mvn -B -ntp -f fixtures/spring-imports/pom.xml compile`. Fixture pinne Spring6.2.2,
Maven resources3.3.1/compiler3.13.0 a SHA-256/license entries šesti API JARů.
Core ani test fixture nic implicitně nestahují. Mandatory CI vyžaduje skutečné API
a oba skutečné JVM workery; chybějící vstup je FAIL, ne PASS. Viz
[change note42](changes/42_resolveBoundedSpringImports.md).

## Required CI prerequisites (T003-S11-W04)

`compiler-workers` explicitly prepares pinned JDK21, Kotlin2.1.10, K1/K2
workers, TypeScript5.7.3, the mixed Maven fixture and Spring6.2.2 API inputs.
`KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1` and
`KGMAKER_REQUIRE_SPRING_IMPORTS=1` turn missing prerequisites into failures.
The exporter job separately sets `KGMAKER_REQUIRE_EXPORTERS=1` and runs actual
Maven/Gradle exports from an installed wheel. These flags belong to the test
matrix; they do not authorize implicit builds in product commands.

Run `python -m pytest -q tests/test_mandatory_worker_ci.py` to exercise the
existing setup gates against absent K1, TS, K2, JDK and mixed-build inputs,
with each flag unset, zero and one. The 15 negative cases assert the actual
FAIL/SKIP exception contract, no subprocess, no worker-home creation and
preservation of the last valid graph bytes. They acknowledge earlier
prerequisites only to reach the selected missing input; positive execution
remains the separate actual compiler/installed-exporter fixture suite.
Spring API absence/corruption and exporter absence retain their existing
negative tests. Local source-only suites may SKIP actual integrations; a
second-JDK exploration is explicitly outside the required one-JDK matrix.
Graph/store/protocol formats and runtime worker discovery are unchanged.

## Default body source mapping

T003-S04-W02 adds declaration mappings on the existing explicit bytecode path:

```bash
kgmaker inspect code --root project --build-id BUILD_ID --context CONTEXT_ID
# Import a validated execution-bound build manifest before selecting bytecode roots.
# No compilation is triggered by scan, graph queries or source-only inspection.
```

Bytecode method IDs and generated call-site identities remain separate from source
methods. Generated methods use their actual artifact realm scope and keep direct
`path`/`range` empty; even an otherwise identical test-scope artifact cannot claim
a production source declaration. `source_mapping_ids`, `source_mapping_reason`, `source_mapping_path` and
`source_mapping_range` describe the enclosing **declaration**, never an exact source
call expression. `maps_to_source` facts retain source hash/range, selected context and
bytecode artifact hashes. Every generated call site has a localized `BYTECODE_ONLY_CALL_SITE` diagnostic:
its declaration mapping does not prove a call-expression position.
Generated instruction `path`/`range` remain absent;
`source_line`/`SourceFile` are raw debug attributes, not inferred locators.

The verified matrix uses JDK 21.0.6, Kotlin 2.1.10 and both explicit K1/K2 workers:
Java interface default bodies and Kotlin `-Xjvm-default=all` use an exact declared
owner/name/descriptor. Kotlin `-Xjvm-default=disable` DefaultImpls requires Kotlin
Metadata (synthetic class + interface), a unique InnerClasses outer interface, an
exact static receiver type, the same repository/module/source-set/scope realm and an actually declared interface signature matching
the source symbol. The suffix alone proves nothing. Generic Java bridges require
both ACC_BRIDGE/ACC_SYNTHETIC, a straight-line load/cast/single same-owner delegate/
return body, no handlers and an actual nonsynthetic target declaration. Value and
void returns are covered. Duplicate class owners never yield source mappings.
Other generated shapes, absent or mismatched source
signatures stay bytecode-only with localized `BYTECODE_ONLY_SOURCE_MAPPING`.
No-debug fixtures remove only debug attributes from actual compiler output;
source declaration locations remain available through compiler attribution.

This is an additive worker-v1 payload extension; graph v1/v2/v3 readers and existing
IDs/store format remain unchanged. It does not map statement-level lines, default
argument masks, coroutine state machines, arbitrary bridges/dependency bodies or
prove runtime dispatch/availability. Source-only mode has no new process path.


Direct source mappings additionally require a compiler-proven `jvm_static` flag
matching the physical method. Javac, K1 descriptor/codegen API and K2 light methods
provide this flag; absence means UNKNOWN, not an inferred method-name convention.
Bridge delegates must remain instance-compatible. DefaultImpls retains its explicit
static-helper/interface-instance signature transform. Stale source static/instance
changes never yield a source mapping even inside an identical repository realm.

## Coroutine source boundaries (T003-S04-W03)

The explicit JVM inspection preserves compiler-proven suspend call sites and
recognized `kotlinx.coroutines.launch`/`async` boundaries. K1 source CFG retains
calls with resume/failure boundaries; scheduling remains UNKNOWN. K2 preserves
source boundaries even when dependency JVM signatures remain unresolved, and
continues to report unavailable source CFG explicitly.

```bash
kgmaker inspect code --root project --build-id BUILD_ID --context CONTEXT_ID
# Source/compiler inspection does not execute coroutine code or a scheduler.
```

Named ContinuationImpl `invokeSuspend` declarations can map through bounded
Kotlin/DebugMetadata, enclosing-method signature, delegate and exact realm proof.
Metadata suspension lines never become source call-expression locations.
Generated state-machine instructions retain BYTECODE_ONLY locators and generated
identities; missing/malformed metadata, foreign realm or absent source remains
unmapped. Suspend lambdas, arbitrary state machines and runtime async ordering
remain outside this mapping contract. Store/protocol formats remain readable;
metadata is additive and worker content identities invalidate older cached facts.

## Hand-labelled JVM acceptance corpus

T003-S04-W05 adds a versioned test inventory for T002-CG-01–05. It reuses the
existing mixed five-call golden and actual ordered dependency fixture, with
explicit Java owner/overload/reference/lambda/recursion/reflection and Kotlin
extension/default/inline/suspend/Java-call supplements. Original inline source
fixtures are shared files with byte-identical contents.

```bash
PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  python -m pytest -q tests/test_jvm_golden_corpus.py
```

Source-call RESOLVED/UNRESOLVED counts and exact caller/target/range identities
are compared separately from unsupported model/CFG diagnostic identities. K2
SOURCE CFG remains unavailable; K1 default-argument CFG and collapsed Java
expression order retain explicit boundaries. Source-level inline callable
attribution does not prove a physical public facade invocation. Reflection APIs
may resolve while their runtime targets stay unknown; method references remain
non-executing, and opposite branches never become a sequence.

The corpus and its mutation checks reject missing/extra/retargeted/stronger
observations. Store/protocol formats remain unchanged; source/class/store bytes
and offline retention use the existing model/provider pipeline. The prerequisite
stack is explicitly documented in change62; this is bounded static acceptance,
not a complete JVM program, runtime scheduling or availability proof.

## T003-S05-W02 — registrar a FactoryBean declaration facts

Spring `annotation-source-v5` přidává bounded Java/Javac compiler facts pro
`ImportBeanDefinitionRegistrar` a `FactoryBean<T>`; metadata sdílejí oba JVM
backends. Není to Kotlin metadata rozšíření, execution ani Spring bootstrap.

| Podporovaný vstup | Výsledek |
|---|---|
| Exact/transitive registrar a2-parameter API method, přímé `registry.registerBeanDefinition("name", new RootBeanDefinition(Type.class))` statements | `spring_registrar`/`registers_bean`, source symbol/hash/context evidence; bean condition z importující konfigurace |
| Custom3-parameter overload, branches/alias/helper/fake receiver, více než128 statements, chybějící/nepodporovaný target | Explicitní UNKNOWN boundary; žádný odhadnutý ACTIVE bean |
| Concrete indexed FactoryBean<T>, sole zero-argument `return new T()` a `return T.class`, typy souhlasí | Samostatný `&name` factory object a `name` product, `produces_bean`, static condition z bean declaration |
| Raw/inherited unresolved/custom/mismatched factory body, abstract factory, @Bean bez prokázané konkrétní literal implementation | UNKNOWN product; žádné volání getObject/getObjectType, žádný falešný product availability |

Product type je kompilátorový typ včetně inherited generic substitution; fake
FactoryBean nebo Registry stejného simple name nepředstavují Spring API. Literal
bean name je nejvýše512 znaků, registry body128 statements. Aditivní symbol fields
`bean_registrar`, `bean_registrations`, `factory_bean`, `factory_bean_return` a
`factory_return` mají schema1; worker protocol1 a graph/store v1/v2/v3 zůstávají
čitelné. Aditivní `factory_producer` fact určuje skutečný literal constructor
vrácený @Bean metodou; anonymous/complex producer nepřebírá proof base class.
Producer i getter method hashes jsou součástí evidence. Factory object type je
přesný component owner nebo validovaná skutečná literal producer implementation;
custom method object assignability zůstává UNKNOWN. Nové product/registrar
selection používá compiler-qualified field assignability a známé supertypes;
foreign short-name shoda není resolved injection. Chybějící legacy evidence
nepromuje registrace. Invalid facts/context
se odmítnou před store publikací. Rule v5 je JVM-only a vstupuje do context
fingerprintu, TypeScript/React selection key se nemění. Evidence zůstává
FRAMEWORK_DERIVED, nezvyšuje compiler-call confidence ani availability.

```bash
kgmaker inspect code --root project --manifest /approved/build-manifest.json \
  --context BUILD_CONTEXT_ID --kotlin-backend k2 --worker-home /approved/workers
kgmaker query --root project --context ANALYSIS_CONTEXT_ID registeredProduct
```

Skutečné Spring6.2.2 API se explicitně připravuje existujícím pinned fixture POM;
SHA/license lock a mandatory CI guard z W01 zůstávají. Fixture nic nestahuje a
source/app code se nespouští. XML, BeanDefinition builders/properties/suppliers,
post-processors a Spring/Boot factories metadata nejsou tímto scope interpretovány.
Viz [change note47](changes/47_declareSpringRegistrations.md) pro testy a aktuální
externě blokované Actions; lokální zelené testy nenahrazují nové CI ani review.


S05-W02 injection fixture používá imported simple field types a samostatné
annotated declaration lines. Existující bounded textual injection projection
nepokrývá více deklarací na jednom řádku ani obecnou lowercase-leading FQN
source grammar. Nové qualified hierarchy guards jsou compiler-backed v tomto
podporovaném subsetu; nejde o nový úplný Java annotation parser.
## Data resource projection (T015)

The public pure Python API consumes an already captured workspace:

```python
from pathlib import Path
from kgmaker.workspace import load_workspace, snapshot_workspace
from kgmaker.data_resources import project_data_resources

manifest = Path("workspace.json")
workspace = load_workspace(manifest)
_, coverage, _, graph, _ = snapshot_workspace(manifest)
view = project_data_resources(workspace, graph, source_coverage=coverage,
                              scope="production")
print(view.to_json())
```

Capture is separate from projection; the latter reads only explicit local source
snapshots and never starts a process or connects to a database. It reuses T008
service ownership and selected contexts, including `selected_contexts` pins.

- Two explicit database/stream realms with an `orders` table stay two resources.
  Table IDs are references, not database identities; JDBC URLs and class names do
  not identify a resource.
- Existing `query_reads`, `query_writes`, and `query_deletes` project as scoped
  `reads`, `writes`, and `deletes` only with matching explicit context/target realms,
  exact evidence references, selected service ownership and current source hashes. Both endpoint files must have the selected scope and matching hashes in that same context snapshot; a shared migration resource cannot mask a foreign ORM target.
  Missing optional per-fact SHA uses only the validated selected-context source
  hash, recorded as `VALIDATED_CONTEXT_SOURCE`; supplied stale hashes are rejected.
  Entity targets may compose exactly one existing `maps_to_table` edge with its
  own matching context/scope/realm/evidence. Both original composite edge identities
  survive; ambiguous mappings produce no access. Mapping and migration declarations
  alone establish only dependencies.
- `coverage.schemas` inventories/configuration must match the workspace declaration,
  graph table inventory, realm IDs and actual local hashes. Stale or malformed
  snapshots fail without mutation. Unmapped default Flyway database IDs remain
  unresolved; a default is accepted only when explicitly declared as a datasource.
- Flyway resources carry `derivation=["MIGRATION_DERIVED"]`, while evidence keeps
  its original T009 kind. Deployment and data availability remain `UNKNOWN`.
  An ORM node tag alone supplies no new FRAMEWORK_DERIVED proof. Unknown polarity
  is not promoted; explicit conflicts retain both buckets and AMBIGUOUS status.
- Known foreign test scopes are excluded. Unknown file scope is not converted to
  production because its repository belongs to a production service.

`tests/test_t015_project_data_resources.py` exercises actual offline SQL replay and
workspace capture plus independently supplied bounded upstream edge contracts.
An additional K1/K2 fixture captures real Javac-backed Spring Data native read/write
and JPQL entity facts with hash-locked published APIs before pure projection.
It does not claim a new compiler/ORM adapter or complete S06/W08 support. Coverage
is PARTIAL (or UNKNOWN with no resource inventory); multi-datasource adapters,
physical naming/schema compatibility, live databases and data population remain
outside this projection. Graph/store v1/v2/v3 and CLI behavior are unchanged.

## T003-S05-W03 — typed condition matrix

The JVM v6 evaluator preserves compiler member types alongside legacy annotation
display strings. `@Profile` accepts a nonempty string array (OR); expressions
support `!`, `&`, `|`, parentheses, at most256 tokens/64 nesting levels. Mixed
`&`/`|` require parentheses, as in Spring. Explicit empty active profiles use
Spring's ordinary `default` profile; custom default-profile configuration is
outside this subset. Missing or malformed active-profile snapshots are UNKNOWN.

`ConditionalOnProperty` accepts agreeing `value`/`name` aliases, an optional
trimmed dot-delimited prefix, all property names (AND), a string `havingValue`
and a genuine boolean `matchIfMissing`. Context property values must be literal
strings: default matching accepts any string except case-insensitive false,
including empty/other text. Case comparison supports ASCII and exact literal
equality; unsupported non-ASCII case equivalence remains UNKNOWN rather than
using Python's expanding casefold. Unresolved placeholders, collections and
malformed members remain UNKNOWN.

`ConditionalOnClass` requires all explicit `value` class literals and `name`
strings to occur in `spring_available_classes`; `ConditionalOnMissingClass`
requires all to be absent. An explicit empty inventory means absent; omitted
inventory means UNKNOWN. Matching uses complete identities without simple-name
inference. Unresolved compiler class literals stay UNKNOWN in both directions.
This inventory is a declared selected-context snapshot, not a runtime probe.
Custom/unsupported Boot conditions stay UNKNOWN and are never executed.

Class, method, imported-configuration and component-scan reachability remain in
the existing framework projection. INACTIVE dominates UNKNOWN across conditions;
UNKNOWN dominates ACTIVE. A second raw-profile injection filter is removed, so
proven negated/OR profiles retain their computed state. Evidence stays
FRAMEWORK_DERIVED and retains source/compiler/context provenance; no bean runs.

An explicit Python API example (the existing inspection CLI is unchanged):

```python
from pathlib import Path
from kgmaker.inspection import inspect_jvm
result = inspect_jvm(Path("app"), classpath=["/prepared/api.jar"], publish=False,
    build_context={"spring_profiles": ["qa"],
        "spring_properties": {"feature.enabled": "true"},
        "spring_available_classes": ["java.lang.String"],
        "spring_component_packages": ["example"]})
```

Context IDs bind the input snapshot; offline validation detects tampering and
requires reinspection for older Spring rule versions. Graph v1/v2/v3 remains
readable; old framework facts are not silently promoted to current rules.
Explicit variant-specific `project.input_files` and captured classpath hashes
are checked per context, without narrowing shared build/source inputs. A change
to one variant's external config/JAR leaves another untouched context fresh and
the stored graph unchanged. No configuration loader, installation or build is
implicit in the evaluator or offline freshness path.

Actual API inputs: `fixtures/spring-conditions`, Spring6.2.2/Boot3.4.2, pinned
hashes/licenses; preparation is an explicit Maven command. Required CI uses
`KGMAKER_REQUIRE_SPRING_CONDITIONS=1` and runs the real K1/K2 fixture. Local
missing tools/APIs are SKIP unless required. See
[change note50](changes/50_expandSpringConditions.md) for final test results and
remaining unsupported cases; this does not complete all of T003-S05.

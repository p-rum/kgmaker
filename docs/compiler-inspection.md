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
| Bytecode | ASM přibalené v Kotlin 2.1.10 | Deskriptory, invokes, základní CFG, application-only CHA |
| Maven | 3.9.9 | EventSpy effective session export v2, parent/BOM, effective dependencies, profily, generated roots, toolchain, ordered classpath, explicitní test build |
| Gradle | 8.12.1 a lokálně 8.13 | Skutečný source-set export/test build PASS v GitHub Actions run 38703831737; lokální explicitní Gradle 8.13 build ověřuje Kotlin task options a čerstvý class output |
| TypeScript / Node | 5.7.3 / 24.19.0 | Program/TypeChecker, call signatures, overloads, React JSX event binding |
| React typings | React 18.3.1, @types/react 18.3.18 | Intrinsic JSX onClick v malé fixture |

Kotlin Analysis API/K2 zatím není implementována; podpora compiler distribuce 2.1.10
není tvrzením úplné podpory Kotlin language 2.1. Java release request je explicitní,
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
TypeScript worker v2 podporuje solution-style project references uvnitř zvoleného
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
boundary jsou `FRAMEWORK_DERIVED`. Spring pravidla v3 vyhodnocují dodané profiles,
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
je bean, ale ImportSelector/registrar se neprovádí a hlásí explicitní boundary.
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

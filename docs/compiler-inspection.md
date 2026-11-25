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
Checksum zajišťuje vazbu obsahu, nikoli autenticitu vydavatele. Při přípravě wheelu musí aktuální trusted JAR a descriptor pocházet ze stejného explicitního běhu `workers/build/build.py`; starý lokální JAR nelze kombinovat s novým descriptor-em. Lokální oprava prostředí a hash refresh pro Maven3.9.9 /Gradle8.13 /JDK21.0.13 jsou doloženy v [change116](changes/116_parseExtendedJpqlHql.md).

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

BuildManifest v1 přijímá volitelný `contexts[].config_fingerprint` jako SHA-256
deklarované netajné konfigurace, přesně 64 malých hexadecimálních znaků.
`inspect code` převezme hodnotu pouze ze zvolené varianty a uloží ji do jejího
compiler kontextu vedle `manifest_hash` a původu exportu. Manifesty bez pole lze
nadále importovat a použít k inspekci. Runtime v2 používá uloženou hodnotu pro
kontrolu před spuštěním. [Příklad](runtime-trace.md#spuštění).

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
Vybraný `persistence-unit` z `META-INF/persistence.xml` určuje mapping files v
deklarovaném pořadí; bez explicitního seznamu se hledá `META-INF/orm.xml`.
Podporovaný ORM XML subset používá přesné compiler-resolved class identity,
tabulku a scalar ID/basic/version sloupce. XML mapping má přednost před
annotations a `metadata-complete` skutečně potlačí annotation-only bindings.
Hrany a uzly nesou cestu a SHA-256 mappingu, persistence unit a pořadí zdroje.
Neznámý namespace/verze, neúplný nebo nepodporovaný construct, nevyřešená
class/attribute reference a nebezpečný nebo root-escaping XML soubor zůstávají
UNKNOWN bez odvození fyzického názvu z annotation fallbacku. Parser odmítá
DOCTYPE/external entities a nic nestahuje ani nespouští; graph schema zůstává v3.

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
Explicitní `@Query` je vlastněno přesným compiler method symbolem. JPA rules
`annotation-source-v9-named-query-containers` tokenizují omezený statický JPQL/HQL
subset: root a association join aliasy, subquery roots, bulk `UPDATE`/`DELETE`,
`select new` s přesným compiler-owned DTO a clause-specific path expressions.
Vznikají oddělené `query_reads`/`query_writes`/`query_deletes`, `joins_by`,
`projects_attribute`, `filters_by`, `orders_by`, `groups_by` a
`updates_attribute`; implicitní association traversal přidá read pouze pro
jediný přesný entity owner. Hibernate `join ... with` je podporovaný bounded
provider extension. `lateral`, set/window operace, `treat`, collection-index
funkce a direct entity join mimo association grammar jsou PARTIAL s přesným
query offset/line/column locatorem. Bounded parser konzumuje celé klauzule a
výrazy; porovnání, AND/OR/NOT, EXISTS, IN (seznam/poddotaz), BETWEEN, LIKE
(s volitelným ESCAPE), IS [NOT] NULL a základní aritmetika mají oddělenou
predikátovou a skalární syntaxi. Alias lookup je case-insensitive; každý
poddotaz má vlastní scope a lexical parent, běžné závorky zachovají scope.
Sourozenecké poddotazy mohou znovu použít alias, vnější alias lze korelovat,
vnitřní alias nesmí uniknout ven. Malformed input, neúplné klauzule,
neočekávané tokeny a nerozvázané aliasy jsou UNKNOWN bez read/write/path hran.
Podporované funkce jsou count/sum/avg/min/max, lower/upper/length/abs/sqrt,
mod, concat, substring, coalesce a nullif s kontrolou arity. Další funkce
jsou PARTIAL s locatorem; CASE, enum konstanty, select-result aliasy,
collection operators a složitější provider gramatika nejsou garantované.
DML poddotaz s GROUP/ORDER BY zůstává mimo tento omezený scope.
[Opravy po review a testy](changes/116_parseExtendedJpqlHql.md). Native SQL nadále váže pouze
explicitní názvy tabulek v aktuální ORM projekci a při kolizi zůstává ambiguous.
Statické JPA named queries mají oddělenou definici a repository reference; SpEL,
`${...}` a jiné dynamické části se nerozvíjejí.

### Named query containers (T003-S06-W06)

Named-query kontrakt zavedený v `annotation-source-v9-named-query-containers`
zachovává schema grafu 3; aktuální JPA rule je `annotation-source-v10-programmatic-queries`
a W07 doplňuje optional typed IR. Jednotlivé `@NamedQuery`/`@NamedNativeQuery`,
opakované anotace a `@NamedQueries`/`@NamedNativeQueries` používají jeden katalog
v právě vybraném compiler kontextu a persistence unit. Javac nested annotation
mirrors a strukturované compiler hodnoty mají stejnou normalizaci. JPA identity
musí být z `jakarta.persistence` nebo `javax.persistence`. Katalog nepřebírá
deklarace z jiného kontextu; `exclude-unlisted-classes` a `metadata-complete`
potlačí příslušné annotation definice. XML podporuje deklarace v kořeni mappingu
i přímo v entity/mapped-superclass; jejich provenance obsahuje hash mappingu a
persistence descriptoru. Chybné nebo duplicitní jméno se nikdy znovu nezařadí
jako jednoznačné jen proto, že po něm následuje další platná deklarace.

`@Query(name="Order.byStatus")` vytvoří `uses_named_query` pouze pro jedinou
úplnou definici. Tělo prochází stejnou omezenou JPQL/HQL analýzou jako přímé
`@Query`; vlastník anotace není automaticky čtená entita. Metadata `parameters`,
`positional_parameters`, `method_parameters` a `unbound_parameters` dokládají
statickou kontrolu názvů compiler parametrů nebo pozic `?1`, `?2`, …; literály a
komentáře se za parametry nepovažují. Alias přes Spring `@Param` se zde
nevyhodnocuje, odlišný název zůstává nevyřešený. Konstruktorová projekce,
repository návratový typ a native `resultClass`/XML `result-class` vyžadují
přesný compiler typ. SQL result-set mapping má lokalizovanou diagnostiku a
PARTIAL, bez předstírání provider interpretace. Native názvy tabulek se hledají
v konečné ORM projekci po XML overrides; nerozlišené jméno je UNKNOWN.
Společná lexikální vrstva named i přímých native queries maskuje standardní
SQL quoted spans (včetně zdvojených uvozovek) a `--`/`/* ... */` komentáře.
Text `from orders` uvnitř literálu/komentáře není table reference. První skutečný
statement keyword za komentáři rozlišuje SELECT/UPDATE/INSERT/DELETE; například
`/* audit */ update orders set status='x'` vytváří statický write intent.
Quoted token na začátku dotazu nemůže zpřístupnit pozdější klíčové slovo jako
začátek statementu. Neuzavřený literál/komentář, dialect-dependent quoting,
nepodporovaný první token a dotaz bez podporované unquoted table reference
vrací `NATIVE_QUERY_STRUCTURE_UNRESOLVED`, `validated=false` a UNKNOWN bez
read/write/delete hran. Týká se to i scalar-only SELECT; nejde o SQL grammar
validator. Plná syntaxe, dialect-specific string escapes a quoted table names
nejsou tímto lexikálním kontraktem interpretovány.

Například po explicitní inspekci projektu s uvedenou deklarací:

```bash
kgmaker inspect jvm --root app
kgmaker query --root app --scope production Order.byStatus
```

Vybraný persistence unit se přebírá ze stejného build/context kontraktu jako
ostatní ORM mapping; nový přepínač ani paralelní store nevzniká. `scan` a `hook`
nevolají worker. Starší v1/v2/v3 grafy zůstávají čitelné; stará framework rule
vyžaduje čerstvou explicitní inspekci, nikoliv automatické povýšení evidence.
Skutečná Javac 21 fixture je `fixtures/named-queries/Model.java` a `orm.xml`;
`tests/test_named_query_containers.py` kontroluje veřejný graf, realm izolaci,
chyby a neměnnost store. API stubs jsou compiler fixture, nikoli běžící JPA
provider. Samostatný actual Kotlin container corpus, EntityManager dynamická
volání, implicitní repository naming convention a runtime dostupnost nejsou
ověřeny tímto balíkem. [Přesné výsledky a kompatibilita](changes/120_namedQueryContainers.md).

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
availability implementace zůstává zachovaná. Data/integration view poskytuje
JSON/Markdown/Mermaid ze společného modelu jako RELATIONSHIP_ONLY; netvrdí CFG
execution pořadí. Viz [W09 kontrakt](unified-flow-views.md). Runtime import je
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

The `selected-source-set-1` JVM snapshot introduced source-set membership for a
supplied project model. Capture, pre-publication checks and offline replay share
the same helper for selected module/set membership (including
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

`fetch_k2.py` je explicitní síťový příkaz. Stahuje sedm Analysis API JARů 2.1.10
z [JetBrains Packages](https://packages.jetbrains.team/maven/p/kt/kotlin-ide-plugin-dependencies) a Caffeine 2.9.3 z Maven Central.
Před zápisem ověří SHA-256 z `dependencies-k2.lock.json` a limit 32 MiB na
stažený JAR. Vadná data ponechají původní soubor. Offline builder ověřuje
compiler/API/Jackson a používá již připravený JDK a compiler. Volitelný `target-k2`
se balí po explicitní přípravě. Core wheel zůstává bez runtime. [Change 156](changes/156_restorePinnedK2Download.md).

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

## Argument to parameter bindings

T003-S07-W01 uses the existing canonical method and parameter IDs plus call-site
argument value occurrences. Worker protocol v1 and graph/store v1/v2/v3 are
unchanged; `argument_mapping_version=1` is additive. Formal IDs use the existing
`METHOD_ID:parameter:INDEX` convention, independently from parameter names.

| Compiler | Supported static binding proof | Explicit boundary |
|---|---|---|
| Javac/JDK21 | Attributed overloads, ordinary method/constructor arguments, vararg element/array binding; generic methods use instantiated executable formal types | Erroneous/unresolved calls; generic constructor vararg packing without instantiated formal; unavailable expression locator |
| K1/Kotlin2.1.10 | Successful resolved call argument map, named order, omitted defaults, vararg elements and spread aggregates | Implicit operator/accessor bindings outside ordinary call expressions and unsupported argument locators |
| K2/Kotlin2.1.10 | Java part uses Javac binding | Kotlin call bindings remain UNKNOWN with `K2_ARGUMENT_BINDINGS_UNAVAILABLE`; no K1 fallback or guessed positions |
| TypeScript5.7.3 | Resolved signature/overload, positional arguments, rest elements/spread aggregate, omitted explicit initializer | Compiler-error recovery signatures; spread before fixed formals without tuple proof; unresolved callbacks/any |
| ASM | Declared target/candidates preserved | Operand-stack argument values are not inferred: `NO_SOURCE_ARGUMENT_BINDING_PROOF` |

`DIRECT` binds a source expression **result** to a declared formal; it does not
claim that the expression is an identity transformation or that implicit language
conversions never occur. `VARARG_ELEMENT`, `VARARG_ARRAY` and `VARARG_SPREAD`
retain packing semantics without inventing array contents or evaluation order.
Omitted defaults have `DEFAULT_VALUE_NOT_EVALUATED` and no invented value edge.
Callable references are `NOT_EXECUTION` and do not receive invocation arguments.

The `argument_to_parameter` proof carries original call-site ID, argument/formal
indices, context, declared-contract binding kind and transformation. It never
binds a dispatch candidate implementation as an observed callee. The process JSON
preserves original binding proofs even when dispatch prevents body expansion;
`argument_binding_status` distinguishes PROVEN, UNKNOWN and legacy unavailable
proof. Availability remains UNKNOWN and execution NOT_OBSERVED.

Explicit examples after content-bound inspection:

```bash
kgmaker inspect code --root project --kotlin-backend k1 --kotlin-version 2.1.10
kgmaker flow render --root project --entry METHOD_ID --view process --format json
kgmaker impact --root project --entity ARGUMENT_ID --include-data-flow --format json
```

Use the existing explicit `--context`/`--scope` selection when variants exist.
Directional impact traverses only versioned proven argument edges; legacy and
candidate edges do not gain new strong paths. Its existing v1 path shape remains
unchanged and supplemental `argument_parameter_bindings` retains typed provenance.
Workspace federation qualifies argument/formal/call-site/context references;
malformed or ambiguous bindings fail before replacing the last valid generation.
No scan/hook/projection starts workers, builds or application code implicitly.

### T003-S08-W04: bounded versioned React event evidence

`--ui-framework react` uses `react-jsx-events-4`, pinned React18.3.1 and
@types/react18.3.18 (official index.d.ts SHA256 recorded in change69). The compiler
must select that external declaration's DOMAttributes or pinned input/select/textarea event member. Evidence keeps
package versions/hashes, declaration/forwarder ranges and `execution=NOT_OBSERVED`.
The existing protocol1 `handles_event` fact and graph/store model are reused.

Supported: onClick/onChange/onSubmit on intrinsic tags; a checkout function with
one props parameter and sole intrinsic JSX return forwarding the same official
prop. Arbitrary wrappers, spreads, mutable/ambiguous callbacks, redirected fake
React modules, unknown versions and missing packages are explicit unresolved
boundaries. Existing S08-W03 callback candidates remain open-world. No JSX/React JS
or application executes. This rule does not prove a click, scheduling or availability.

Adapter package/declaration inputs use the existing TypeScript discovery closure,
are compared between preflight/analyze and revalidated offline. UI context and
selector bind the adapter snapshot; old UI rules require reinspection. Non-UI and
legacy context construction keep their existing identity. The helper is included
in worker distribution hashes and wheel; incomplete marked distributions fail
before starting a worker. No package installation or network is implicit.

The JSX renderer is part of that proof: classic React factory lookup must resolve
the lexical value to the official React namespace/createElement, including actual
import aliases; a locally shadowed object annotated as typeof React is insufficient.
Automatic default react-jsx/react-jsxdev modes require the pinned external runtime
declaration. Custom importSource/per-file JSX directives remain UNKNOWN. Uppercase
component names and checkout-added custom IntrinsicElements cannot bypass wrapper
proof just because their props reuse React's event types.

The supported renderer-control whitelist is explicit: classic default or an actual
official createElement import alias via jsxFactory; automatic default react-jsx/
react-jsxdev with pinned runtime declaration. Explicit reactNamespace,
jsxFragmentFactory, jsxImportSource and per-file JSX pragmas are UNKNOWN, including
empty controls rather than truthy fallback. The official event declaration families
are DOMAttributes plus Input/Select/TextareaHTMLAttributes for onChange; onSubmit
on form is covered too. Same-named checkout declarations do not qualify. Full
historical frozen v3 validation:727 PASS/10 SKIP, all66 UI cases; focused binding,
factory and event-control matrix36 PASS. Change69 preserves the earlier v2 and
pre-fix results, interrupted runs and current remote status.

UI binding proof excludes ordinary member callable references and their aliases.
Lexical function/const bindings use a compiler-symbol syntactic write catalog
(assignments, compound/unary targets and destructuring/loop targets), with direct
or ambiguous eval and duplicate binding diagnostics as UNKNOWN boundaries.
Classic renderer namespace/createElement declarations must pass the same write
check. This bounded catalog does not infer heap identity or runtime execution.
Direct imported handlers/wrappers require explicit ESM compiler modes in caller and owner,
and the exact exported value declaration; CommonJS, interop and re-export aliases stay UNKNOWN.
Whole React namespace values escaping through aliases/casts/containers cannot prove an immutable
renderer. Handler/wrapper materialization also requires canonical selected classified scope.
Previous v1/v2/v3 UI captures require reinspection; offline freshness validation
preserves the saved cache/store.

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

Both JVM and TypeScript captures include the optional `return_flow_rule_version`
field. For unchanged capture inputs this updates the full context ID while the
logical selection key and other legacy fields remain unchanged. Historical
contexts remain readable without newly certified return-body evidence.

Example after explicit compiler inspection: `kgmaker flow render --help` describes
the existing process rendering commands; their JSON call blocks include
`return_consumer_bindings`, and data-flow JSON includes the same supplemental proof.
Actual coverage is in `tests/test_return_consumer_flow.py`; broader production
interprocedural flow and complete S07 remain pending.

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

## T003-S05-W04 — proxy, weaving a async boundaries

Spring rules `annotation-source-v9-proxy-provenance` zachovávají graph/store schéma
v1/v2/v3 a přidávají pouze framework nodes/edges a metadata. Deklarace
`spring_advice` má vždy `DECLARATION_ONLY`, `execution=NOT_OBSERVED` a
`availability=UNKNOWN`; samotná `@Transactional`, `@Async`, cache nebo method
security anotace nikdy nedokládá aplikaci advice.

Pozitivní proxy-eligible cesta vyžaduje současně compiler-resolved externí call,
compiler FIELD receiver binding shodný s jedinou explicitně anotovanou
`@Autowired`/`@Inject`/`@Resource` ACTIVE injection do ACTIVE Spring beanu,
explicitní ACTIVE policy
(`EnableTransactionManagement`, `EnableAsync`, `EnableCaching` nebo
`EnableMethodSecurity`) a podporovanou interceptable deklaraci. JDK dynamic cesta
vyžaduje přesně určený injected compiler interface a public metodu. CGLIB cesta
vyžaduje konkrétní injected non-final bean a public/protected non-final,
non-private, non-static class metodu. Výstup je záměrně jen
`may_traverse_proxy` → `may_apply_advice`; runtime dispatch ani advice execution
se z něj nestává. `EnableAspectJAutoProxy` se eviduje jako obecná policy, ale
neaktivuje specializované Transaction/Async/Cache/Security advice.

`AdviceMode.ASPECTJ` bez compiler/load-time weaving artefaktu má status UNKNOWN a
diagnostiku `SPRING_WEAVING_UNVERIFIED`; nevytvoří pozitivní proxy path. Nejednoznačná
injection, prosté nebo ručně inicializované pole, local/new receiver, konfliktní
policy, neinterceptable metoda a chybějící receiver proof
končí `spring_proxy_boundary`/`proxy_resolution_unknown`. Same-owner call používá
`bypasses_proxy`, `continuation=SYNCHRONOUS`; self-call na `@Async` tedy netvrdí
naplánování tasku.

`@Async`, `@EventListener` a přesný `Mono`/`Flux`/`Publisher` return na Spring
beanu mají samostatné declaration boundaries. Process view se na Async targetu
zastaví s `continuation=SEPARATE` jen přes doložený `may_traverse_proxy` a
`crosses_async_boundary`; self-invocation s `bypasses_proxy` rozvine synchronně
jen při compiler receiver kind `THIS`/`SUPER`. Stejný method owner přes parametr,
jinou instanci nebo pole bez proxy evidence zůstává UNKNOWN.
Coroutine/reactive target zůstává samostatnou boundary s `continuation=SEPARATE`,
`execution=NOT_OBSERVED`; event listener neprodukuje přímou call edge a default
caller-thread delivery není vydávána za pozorovaný běh. Configuration view umí
nové policy/path/boundary vztahy zobrazit, execution ranking je nepovyšuje.

Přímá matice je `tests/test_spring_proxy_async.py`: JDK/CGLIB, self-invocation,
Async, EventListener, reactive declaration, AspectJ bez weaving proof,
ambiguous injection a flow boundary. Dva actual-javac parametry jsou povinné jen
v připraveném worker prostředí (`KGMAKER_REQUIRE_WORKERS=1`); lokálně chybějící
worker je explicitní SKIP, nikdy PASS. Žádný scan/hook/view nespouští worker,
build, Spring context, task executor, event publisher ani reactive subscription.

```bash
kgmaker inspect code --root app --manifest build-manifest.json --format json
kgmaker graph view --root app --view configuration --scope production --format json
```

`graph view` je nad uloženým explicitním contextem read-only; varianty vyžadují
existující `--context` výběr stejně jako ostatní compiler-backed pohledy.

## Explicit persistence realms (T003-S06-W04, verified bounded subset)

Current physical schema binding requires an explicit database_id/schema_stream_id
pair in the compiler selection and replay configuration. Optional
persistence_schema/flyway_target context selectors are shape validated and hashed;
a declared table schema or one supported replay schema may supply an unambiguous
schema, while multiple choices remain UNKNOWN. W03 still owns persistence-unit
selection and XML input replay. A globally unique table name cannot fill a
missing realm. Legacy contexts remain readable but require reinspection under
JPA rule annotation-source-v6-persistence-realms.

An explicit workspace repo.flyway replay joins already captured fresh compiler
facts locally before workspace qualification, without running a worker or build.
Source-only @Table/@Column fields no longer create strong persisted_in or schema
mismatch claims without compiler-owned realm proof. Migration-derived schema,
framework interpretation and runtime/deployed data availability remain separate.
Physical binding supports non-renamed replay table/column identities. A valid
Replay rename retains its creation ID, so the current strict current-name/ID guard
returns UNKNOWN after rename; it never guesses from previous/display names.
S06-W08 owns the creation-identity metadata/parser-cache follow-up, not this PR.
See change note74 for actual validation and remaining acceptance; no complete
production/provider/schema-lifecycle support is claimed.



## T003-S07-W04 — declared Kafka binding identity

Optional workspace `kafka_bindings` schema1 reuses repositories, services
(`transport: kafka`), service_ownership and graph/store v1/v2/v3. The executable
example is `fixtures/kafka-bindings/workspace.json`; no broker API is called.
`clusters` declares unique logical IDs only. Each bounded binding declares its
repo/service/module/source_set/scope, optional selected context ID, direction,
active profiles, ordered config_files (path/profile expression), binder-alias to
cluster map, and contract repo/path/release plus payload label. Unknown fields,
duplicate identities, invalid ownership, out-of-root/symlink/hidden/sensitive or
>1MB artifacts fail before source processing/publication. There is no new approval
flow: labels are explicit declarations, never runtime observations.

Supported configuration is literal UTF-8 `.properties` (at most10000 lines),
Cloud Stream `spring.cloud.stream.bindings.<binding>.destination` and `.binder`,
and bounded whole-property `${key}` references (depth16, cycles unresolved). An
explicit empty active-profile list uses Spring `default`; an absent list is UNKNOWN. Base
files precede profile files; explicit profile expressions reuse S05-W03 grammar.
Captured properties of exactly one fresh matching JVM context take precedence.
Multiple contexts require an explicit compatible context ID. Source-only scope
requires conventional root/main or root/test resource paths; nonstandard layouts
need matching compiler source-set membership. Unsupported/duplicate properties,
missing files/profiles, partial placeholders/SpEL, YAML, multi-destination topics,
missing release/payload, stale context or invalid JSON contract stay UNKNOWN.
Configuration and contract files are content-hashed and checked again before
cache publication; selected compiler snapshots are validated without execution.

`kafka_binding` metadata records declared service realm, logical cluster, topic,
contract SHA, release/payload, input hashes and exact selected context. Resolved
static configuration produces FRAMEWORK_DERIVED `produces`/`consumes` and
`kafka_binding_match` only for identical workspace cluster/topic/contract SHA/
release/scope. JSON contract bytes identify an artifact; no schema compatibility
or payload class mapping is inferred. `code_binding=UNPROVEN` and
`delivery=NOT_OBSERVED` remain explicit. Raw properties, broker endpoints and
credentials are never copied into new nodes/evidence. There is no implicit
Kafka/AdminClient, network, build, package installation, registry or application
execution. Existing Git baseline reads are unchanged.

Legacy pattern topic nodes stay separate SYNTAX_CANDIDATE hints. Literal prefixes
of concatenated/placeholder expressions no longer create guessed topics;
`kafka_binding_boundary` records UNKNOWN. No source hint is promoted by matching a
declared configuration label. Retry/DLT, binder auto-discovery, environment/default
placeholder expansion, arbitrary YAML, Avro/protobuf/remote schema registries,
serialization compatibility and runtime delivery are outside this bounded scope.

Evidence: `tests/test_kafka_bindings.py` uses actual local repository/properties/
JSON fixtures, two clusters with the same topic, profile/context precedence,
dynamic/invalid/ambiguous cases, exact hash invalidation, source/store/cache
atomicity, secret exclusion and no-process offline checks. Actual K1/K2 contexts
verify property provenance and stale-source refusal; no Kafka toolchain is needed.
See change note54 for exact commands/results.


### Kafka property privacy (`kafka-binding-2`)

Every destination/binder lookup checks its property key before fetching the
value, including all whole-property alias hops within the existing16-step/cycle
budget. Key matching ignores separators/case and covers password/passwd, secret,
credential, authorization, API key, token, username, JAAS and bootstrap-server
families, consistent with existing configuration/inspection redaction. Sensitive
references yield generic TOPIC_UNRESOLVED/CLUSTER_UNRESOLVED, UNKNOWN and no match;
diagnostics never contain the referenced value. Benign topic/binder aliases retain
their supported literal behavior.

With `kafka_bindings` enabled, context selection/freshness checks consume the
original captured context. Only the subsequent public workspace projection
deep-copies and redacts captured `spring_properties` values using `<redacted>`
and existing inspection sanitization. This also protects a captured Spring
property map attached to another language without changing its selection key or
framework metadata. Other workspaces preserve their prior serialization.

`spring_properties_projection` explicitly records `redacted: true`, SHA256 of
the original property map and `original_context_id`. Existing selection key,
condition-input hash, source hashes and original identity remain content-bound
to the private input. The redacted property map is a display projection and
cannot validate/replay those original inputs. The persisted compiler index and
in-memory input cache remain unchanged; validation still uses the original
context, and no worker is launched to repair or sanitize it. Derived identity and
workspace cache version change to `kafka-binding-2`; graph/store schemas remain
v1/v2/v3-readable.

Public fixture regressions cover direct/transitive application and captured
properties, binder-alias privacy, benign references, complete graph/coverage
absence of the synthetic secret, source/index/cache immutability, original
context validation and unchanged non-JVM selection identity. See note54 for the
independently reproduced prior defect and current validation evidence.


Redacted public contexts remain selectable by T006 with an explicit repository
checkout. `workspace.validate_projected_context` reads the existing private
graph store, requires exactly one matching original context, and compares the
entire rederived qualified/redacted projection (including repository alias) to
the supplied context. It recomputes the raw selector and uses the existing
validator on the original input for condition/source/classpath/worker freshness.
The marker/hash alone establishes no authority. Missing store/root, duplicate or
forged identity/marker/body/hash, and changed original bytes fail closed. Only
the unchanged public redacted context continues through selection; private
properties are never returned or substituted into the public graph/cache.
Unprojected context validation retains its previous path.
## T003-S09-W03 — statické Thymeleaf fragmenty

`thymeleaf-bindings-2` zachovává dosavadní literal model-key/template-return vazby a
přidává pouze statické `th:fragment`, `th:replace` a `th:insert`. Cíl musí být
jedinečný ve stejném source scope a počet argumentů se musí přesně shodovat s
parametry deklarace. Literal `${model.path}` se vede přes scoped parametr fragmentu;
stejně pojmenované proměnné mimo fragment se proto nesloučí. Nejednoznačné,
dynamické a špatně aritní odkazy mají lokalizovanou diagnostiku bez resolved
include edge. Podmínky jsou PARTIAL a nepodporované výrazy UNKNOWN; nic se
nevyhodnocuje ani nevykonává. `th:each`, `th:with` a jejich `data-th-*` aliasy
zavádějí lokální jména, která tato verze nemodeluje; obsah těchto scope ani
vnořené fragmentové argumenty se nevážou na globální model a dostávají UNKNOWN
diagnostiku. Hrany zůstávají SOURCE_ONLY `SYNTAX_CANDIDATE`.

To nedokazuje Spring MVC handler resolution, renderovaný výstup ani runtime
availability. Jiné template dialecty, podmínková logika a PDF rendering nejsou
implementovány; explicitní PDF service zůstává externí boundary. Viz
[change note55](changes/55_expandThymeleafFragments.md) a
[acceptance inventory](acceptance-inventory.md#t003-s09-w03--thymeleaf-fragment-provenance).

## HTTP client intent

T003-S07-W06 reuses graph/store schema3 and existing compiler IR. The JVM protocol
adds optional `typed-java-literals-bindings-v1` facts; old workers/indexes and
schema1/2 graphs remain readable with HTTP coverage UNKNOWN. Fresh captures bind
HTTP rule/config fingerprints; replay validates them without running a worker.
Rule `http-client-execution-2` invalidates prior version1 HTTP proof as STALE;
explicit reinspection is required, with no implicit process/store mutation.
No source label, callee spelling alone, confidence score or runtime availability
is used to resolve a request. No client is instantiated and no request is sent.

| Supported proof | Result | Actual fixture/test |
| --- | --- | --- |
| Java WebClient cold `retrieve`/`bodyToMono`/`bodyToFlux`/`exchangeToMono` | Definition; closed unused local publisher UNSUBSCRIBED_WITHIN_SCOPE | Spring6.2.2/Reactor3.7.2; `test_cold_request_and_same_origin_block_are_separate` K1/K2 |
| Exact same publisher Mono block/blockOptional/subscribe/toFuture; Flux blockFirst/blockLast/subscribe | STATIC_TRIGGER or CONDITIONAL_STATIC_TRIGGER, runtime NOT_OBSERVED | `test_same_request_spec_does_not_mix_distinct_publishers`, branch boundary |
| RestClient retrieve versus body/toEntity/toBodilessEntity/exchange | retrieve DEFINITION_ONLY; imperative terminal STATIC_TRIGGER | `test_imperative_retrieve_is_not_a_terminal` |
| Source Feign interface abstract annotated method and attributed call | DECLARATION_ONLY / FEIGN_INVOCATION_INTENT; proxy registration UNKNOWN | OpenFeign4.2.0; `test_feign_declaration_only_and_abstract_invocation_intent` |
| Literal URI; simple `@Value`/PropertyResolver/Feign placeholder + explicit matching properties/profile/source SHA | Separate method/base/path and config provenance | `test_bound_property_source_provenance_and_plain_literal_placeholder` |
| Escaped, stored, returned, captured, unknown helper/operator/merged origin | UNKNOWN, no invented terminal | escape/capture/reference/branch tests |
| Kotlin K1/K2 missing required typed binding IR | HTTP_TYPED_IR_UNAVAILABLE / UNKNOWN | `test_kotlin_unavailable_bindings_are_explicit_unknown` |
| Throw/ternary operands; loop updates and try resources | Escapes UNKNOWN; loop/try control boundaries UNKNOWN with no invented terminal order | `test_abrupt_conditional_loop_and_resource_operands_do_not_claim_unused` K1/K2 |
| URI callback/extra-argument overload | URI/base/path UNKNOWN even if same-origin terminal intent exists | `test_uri_callback_cannot_keep_original_literal_route` K1/K2 |
| Feign nonempty client path prefix | Separate client_path/method_path; composed route UNKNOWN, no guessed concatenation | `test_feign_client_prefix_is_not_an_exact_unprefixed_route` |
| Unsupported/escaped/whitespace properties syntax | Selected file cannot establish exact config value provenance | `test_unsupported_properties_override_cannot_prove_first_literal` |

Custom clients/operators, cross-method publisher flow, dynamic URI construction,
multiple/unknown routes, YAML/SpEL/default/nested placeholders and proxy registration
are outside this matrix. Explicit Java method references/lambda capture never
activate an HTTP request. Unrelated Mono terminals do not activate another origin.
All runtime execution/availability remain NOT_OBSERVED/UNKNOWN. Fresh scans/captures redact URI userinfo,
query values and fragments before graph/context persistence, including SOURCE_ONLY
signatures, documentation summaries and heading identities. Privacy also covers
unsupported URI schemes and scheme-relative authorities; HTTP recognition stays
limited to HTTP/HTTPS, so redaction never makes an unsupported URI executable. Opaque
input hashes preserve freshness without retaining credentials. Configuration
mapping requires a selected `application.properties` or explicit active profile
file containing only the supported literal property syntax, matching property and SHA.
Unsupported meaningful lines, escaped/continuation syntax or unreadable/oversized
selected files invalidate that file's property provenance rather than hiding an
overriding definition. Loop/try boundaries visit resources/updates/operands but
remain UNKNOWN, including a break that makes the loop update unreachable. Explicit values without source provenance
remain unknown. Workspace identities/source locators are repo-qualified, URI path
strings stay paths, and no cross-service endpoint match is invented.

Explicit API preparation (never triggered by scan/inspection):

```sh
mvn -B -ntp -f fixtures/http-client-execution/pom.xml compile
kgmaker inspect jvm --help
kgmaker flow render --view integrations --entry '<canonical-method-id>' --format json
```

Use the existing inspection classpath options for the pinned API JARs listed in
`fixtures/http-client-execution/dependencies.lock.json` (JAR/POM SHA and license).
The actual API tests require the Maven cache and own worker home; mandatory CI
prepares these APIs and runs `tests/test_http_client_execution.py`.

### W08 bounded schema compatibility

An already explicitly inspected compiler context can be compared with the same
realm/target's offline replay using
`kgmaker schema compatibility --root /path/to/repo --config flyway.json --database money --stream main --target 1 --context CONTEXT_ID`.
See [schema compatibility scope](schema-compatibility.md). W04 dependency PR62 is merged and current main is integrated; it does not run an inspection/build or DB implicitly. Missing,
stale, legacy or unsupported proof is UNKNOWN, not compatible by omission.
Schema COMPATIBLE is separate from populated data and deployment evidence.
### Explicit Kafka code declarations (`kafka-code-1`, revision2 draft)

Explicit JVM inspection can attach canonical listener declarations from captured
method annotations: Java in either worker backend and Kotlin K1. An explicit
nonempty groupId is required. Topics are exact case-sensitive literals or captured
whole-property references; topicPattern remains a regex candidate without topic
expansion. Kotlin K2 omits method annotations in its current source model and
remains UNKNOWN. Listener activation and execution are not observed.

Java producer declarations require the dependency-owned KafkaTemplate or
KafkaOperations `send(String,Object)` callsite, compiler-proven argument mapping,
and a direct ASCII string literal topic. Both backends share this Javac support.
Named constants, escaped literals, Kotlin bodies, wrappers, NewTopic,
ProducerRecord and other overloads do not provide positive producer proof.

Workspace schema2 optionally adds the following exact `code_ref` shape to a
binding (schema1 remains supported):

```json
{"kind":"listener","id":"<original compiler method ID>","context_id":"<captured context ID>","source_file":"src/main/java/demo/Listener.java","sha256":"<64 lowercase hex characters>"}
```

Producer references use `kind: "send"` and the original compiler callsite ID.
Selectors are checked against private current compiler capture, canonical source,
realm, scope, ownership, original source SHA and exact topic agreement. Consumers
also require exact agreement with the explicit `.group` configuration property.
Only this bounded join can yield `code_binding: VERIFIED_STATIC` and a
`kafka_subscription`; configuration alone remains UNPROVEN. Logical identities and
capture revisions are separate, and original IDs survive workspace qualification.
Public context privacy and freshness checks remain mandatory. This is static
provenance, without delivery, broker, activation or data availability evidence.

### T003-S07-W05 — bounded retry/DLT policy

An explicit context projection excludes a policy node with a non-null,
non-string owner identity. The original proof is still available to report an UNKNOWN boundary
for the caller. [Regression evidence](changes/141_handleInvalidKafkaPolicyContext.md).

`kafka-retry-1` reuses captured Kafka listener and compiler annotation proof.
Java/K1 explicit literal policy and exact3.3.2 API provenance are the bounded
positive path; unsupported3.2.0, custom handler, expressions, source shadows and
ambiguous DLT associations remain UNKNOWN. Flow policy boundaries are separate
from executable CFG transitions. See [contract](kafka-retry-dlt.md) and
[truthful run history](changes/87_captureKafkaRetryDlt.md). The current-parent coalesced run passed470cases without SKIP; the required full
is NOT_RUN pending the final frozen integration gate. Independent source+focus closure is
recorded, but final ready review is pending; Kotlin K2 annotation gaps remain.

## Remote service/contract declarations (W07 draft)

See [remote mapping contract](remote-contract-mapping.md)
and [note91](changes/91_planRemoteContractMapping.md).
Explicit capture and pure resolution preserve service/context/contract/release
authority; HTTP and Kafka remain distinct declared boundaries, no JVM calls or
runtime/payload availability promotion. Source-specific334PASS; combined2df parent1963PASS/10optionalSKIP. Dependency merges are complete; final exact-pair review remains pending.

## Backend response values in frontend consumers

Explicit frontend inspection now captures optional `value_flow_version=1`
occurrences/facts for the bounded await/JSON/destructuring path. The opt-in
pinned React adapter additionally binds state writes to concrete JSX consumers.
The complete prerequisites, workspace generation metadata, CLI example and
SOURCE_ONLY behavior are in [backend→frontend value flow](backend-frontend-value-flow.md)
and [change125](changes/125_backendFrontendValueFlow.md). Existing worker-response
v1 and graph/store v1/v2/v3 remain readable. Legacy facts disconnected from frontend
value occurrences remain compatible. A fact touching a frontend occurrence must
carry the supported v1 marker and validated endpoints; removing a marker, role or
version cannot bypass validation or replace the last-valid graph. Alias-group
mutation/escape invalidation is conservative across the source, including
`Readonly<T>` references; independent primitive copies remain separate. The packaged `frontend_values.cjs` helper is content-bound in the worker
distribution and required when its package marker is present.

## Field read/write and explicit mapper bindings

T003-S07-W03 adds `field-mapping-1` on existing validated Javac return IR, with
no protocol/store schema change. Direct fields, straight-line static/private/final
helpers and actual captured MapStruct Java source produce source-backed
`reads_value`/`writes_value` occurrences and `maps_to` declaration dependencies.
Business transforms, open dispatch, recursion and ambiguous local definitions
remain UNKNOWN. Runtime/data availability is never promoted.
The [supported matrix and CLI example](field-mapping.md),
[actual manual/generated fixture](../fixtures/field-mapping/README.md) and
[change124](changes/124_fieldAndMappingFlow.md) describe the bounded verification.


### Programmatic query intent (T003-S06-W07)

Explicitní JVM inspection používá bounded Java/Javac Criteria `select(root)` +
`where(equal(root.get("attribute"), value))`, přímo typovanou Specification a
QueryDSL `selectFrom(root).where(root.field.eq(value)).fetch()`. Skutečný dependency
původ API, class/generic identity, source binding a QueryDSL member factory
jsou povinné. Žádný SQL text se nesyntetizuje. Pouze spotřebovaný predicate
vytvoří `filters_by`; unused selector/projection-only jej nevytvoří. Criteria
where reset/clear a QueryDSL accumulation jsou odlišené. Custom fragment je
potenciální deklarovaná kompozice, nikoli Spring runtime dispatch.
Executable Criteria snapshot vzniká při `EntityManager.createQuery`; pozdější
změny builderu jej nepřepisují. Opakované snapshoty jsou oddělené UNKNOWN intent.
QueryDSL attribute evidence vyžaduje final source field; mutable/reassigned člen
ji nedostane. Direct Specification implementation musí mít Javac `Elements.overrides`
důkaz pro dependency `toPredicate` a matching descriptor; overload ani chybějící
contract tuto autoritu nezíská. Saved intent používá `programmatic-query-2`;
v1 replay je odmítnut a vyžaduje explicitní reinspection, schema grafu se nemění.

[Úplná ověřená matice a CLI příklad](programmatic-queries.md) ·
[actual Javac/APT fixture](../fixtures/criteria-queries/README.md) ·
[change129, výsledky a omezení](changes/129_criteriaSpecificationQuerydsl.md).
Graph/store v1/v2/v3 i staré workery bez additive fields zůstávají čitelné.
Scan/hook nikdy nespouští worker, APT, package installation, DB ani aplikaci;
source/context/classpath freshness zůstává oddělená od runtime dostupnosti.

## Unified flow presentation (T003-S07-W09)

All four `flow render` views support JSON/Markdown/Mermaid through the same report.
CFG presentation order preserves branches and async/loop boundaries; relation
views do not establish execution order. Missing CFG is UNKNOWN, with strict exit4.
See [public contract](unified-flow-views.md) and [change128](changes/128_unifiedFlowViews.md)
for context/proof guards, atomic output and exact bounded native verification.


## Obsahová cache inspekčních stupňů (T003-S10-W01)

Explicitní JVM/TS inspekce vrací `cache.stages` s důvodem BYPASS.
Každá fáze používá aktuální výpočet a znovu ověří zdroj/worker před publikací.
Grafová fáze vrací svůj validovaný objekt a otisk launcheru čte soubory
průběžně při každé kontrole.
Otisk spuštění Java zahrnuje `lib/ct.sym`, který Javac používá pro starší
`--java-release`, a na POSIX přesné hodnoty `LANG`, `LC_ALL` a `LC_CTYPE`.
Při výběru přes `bin/java` jako symbolický odkaz vychází otisk z cílové
binárky a platformních souborů jejího JDK.
Relativní položku `PATH` ukotví KGMAKER při výběru launcheru a worker
použije stejnou cestu i po přechodu do adresáře analyzovaného projektu.
Chybějící vstup otisku ponechá případný živý výsledek v režimu
`BYPASS/INCOMPLETE_INPUT_CLOSURE`. Změna zachyceného otisku během běhu
vyvolá `STALE` před dokončením publikace.
Graph/store v1/v2/v3 a interní envelope v1 zůstávají čitelné.
A competing graph publication or intervening generation yields `STALE`
and exit 3. The next explicit inspection can read the newly committed graph
without mixing contexts from stale candidates. A runtime import with an explicit
schema 3 object compares its persisted content to the authoritative stored graph
and rejects a mismatch as `STALE`. An explicit graph remains a valid seed when
there is no store. A Confluence-enabled scan keeps the report and validation index
in the graph publication rollback scope.
[Detaily, příklady a hranice souběhu](stage-content-cache.md),
[ověření #116](changes/135_bindCachedCompilerEvidence.md),
[regrese locale a platformních symbolů](changes/164_bindJavaLaunchInputs.md),
[ověření nákladů živé inspekce](changes/177_reduceLiveInspectionOverhead.md).

Runtime import ověří obálku před publikací. Pod zámkem store hlídá
očekávanou generaci a import před každým nahrazením výstupu znovu kontroluje
zdroje a distribuci workeru z vybraného kontextu. U v2 opakuje i validaci
zachycených vstupů compiler kontextu včetně classpath a bytecode. Zjištěná
změna zastaví publikaci a store obnoví již nahrazené výstupy.
[Regrese runtime importu](changes/163_revalidateRuntimeImportPublication.md).

## Klasifikace vstupů ORM XML

Snapshot `jpa_xml_inputs` zachycuje chybějící soubor i symbolický odkaz na
chybějící cíl uvnitř projektu jako `missing` s rozlišenou cestou. Smyčku
odkazů, chybu rozlišení nebo cíl mimo projekt zachytí jako `invalid`.
Stejná pravidla platí pro Python 3.12 a 3.13. Změna uložené klasifikace
označí odpovídající compiler kontext jako `STALE` při kontrole čerstvosti.
[Ověřovací matice](changes/153_classifyLoopedJpaXmlInputs.md).

```bash
kgmaker inspect code --root ./service --scope production --format json
kgmaker status --root ./service
```

Výsledek inspekce obsahuje jednotlivé záznamy v `context.jpa_xml_inputs.inputs`.

## Explicitní lokální build

Při plánované fázi `test` lze požádat o navázání výsledku na existující task v
kořeni Git checkoutu. Přidejte `--record-verification TASK_ID` k `project build-run`.
Funkce používá jeho existující snapshot a reporty Maven/Gradle. Vypočtený výsledek
a freshness se čtou pomocí `trace show`.
[Příklad a omezení dokladu](delivery-workflow.md#dokumentace-skutečného-testovacího-běhu).

## JVM source byte fingerprints

Fresh JVM inspection uses `source_snapshot_version=selected-source-set-raw-1`.
The scanner captures raw and normalized hashes from the same bounded UTF-8 read.
`source_files` holds selected raw SHA-256 fingerprints. A checkout's `graph.files`
represents normalized scanner text. `normalized_source_files` carries the
structural hash for scanned paths where the two digests differ. The workspace
graph uses raw file inventory hashes. It qualifies both source maps and the
compiler inputs with the owning repository. The `jvm-raw-1:` capture ID binds
the snapshot version, canonical compiler input list, raw hashes and their sparse
normalized projection to the pre-augmentation inspection digest. Offline replay
checks that identity, the current inputs and the selected persistence XML inventory.
Legacy JVM snapshots and the separate TypeScript input-discovery protocol remain
readable.

An LF/CRLF-only edit makes the affected JVM context stale. To refresh it, run
`kgmaker inspect code --root ./service --module app --source-set main`. The
verified Javac fixtures cover return and void bodies, abstract declarations,
T025 local operation replay, a Criteria filter, source CFG call expansion,
W08 JPA schema compatibility, the T012 Kafka catalogue and static retry/DLT
declarations on CRLF input.
Kotlin workers currently report PSI coordinates over normalized text. Explicit
JVM inspection rejects a selected Kotlin file whose line endings change those
coordinates. Offline replay applies the same guard to the captured compiler
input list. Kotlin files excluded from that list can remain in the source-set
inventory for freshness checks.
[Exact verification and scope](changes/160_bindJvmSourceBytes.md).

## Pozorované hrany a statické cesty

`callgraph callers` a `callees` zobrazí doložené importované hrany jako
`RUNTIME_OBSERVED`. `callgraph path` a statické cykly používají compiler
call sites. V2 pozorování `call` a `dispatch` vyžadují volatelné symboly
obou konců ve vybraném compiler kontextu. Import ověří jeho čerstvost také
při publikaci grafu. Původ dokladů opakovaného importu uvádí
[kontrakt runtime importu](runtime-trace.md#opakovaný-import-a-navigace).

```bash
kgmaker callgraph callers --root PROJECT --context CONTEXT_ID --symbol TARGET_ID
kgmaker callgraph path --root PROJECT --context CONTEXT_ID --from CALLER_ID --to TARGET_ID
```

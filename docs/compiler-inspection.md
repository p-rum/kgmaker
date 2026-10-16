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
| Kotlin compiler | 2.1.10 distribuce, K1 frontend v language 1.9 compatibility | BindingContext, KotlinTypeMapper, overload, constructors, lambda callers, callable references, source-defined operators, extension/default/inline/suspend metadata a volání do Java |
| Bytecode | ASM přibalené v Kotlin 2.1.10 | Deskriptory, invokes, základní CFG, application-only CHA |
| Maven | 3.9.9 | EventSpy effective session export v2, parent/BOM, effective dependencies, profily, generated roots, toolchain, ordered classpath, explicitní test build |
| Gradle | 8.12.1 | Skutečný source-set export/test build PASS v GitHub Actions run 38703831737; lokálně blokované socket/IPC |
| TypeScript / Node | 5.7.3 / 24.19.0 | Program/TypeChecker, call signatures, overloads, React JSX event binding |
| React typings | React 18.3.1, @types/react 18.3.18 | Intrinsic JSX onClick v malé fixture |

Kotlin Analysis API/K2 zatím není implementována; podpora compiler distribuce 2.1.10
není tvrzením úplné podpory Kotlin language 2.1. Java release request je explicitní,
Maven import přenáší získaný release. V integrační fixture byl ověřen pouze release 21.
TypeScript projektové reference předává worker kompilátoru; úplná acceptance fixture
s více projekty a re-exporty ještě chybí.

Zvolený bytecode engine je přibalené ASM, nikoli SootUp. Pilot nepotřebuje jeho
whole-program režim: deskriptory a instrukce zůstávají oddělené od source grafu,
CHA kandidáti jsou konzervativní a jejich úplnost je vždy false. JAR závislosti
jsou kontrolovány pomocí `workers/jvm/dependencies.lock.json`. Kotlin compiler
je Apache-2.0 s notices distribuce; ASM je BSD-3-Clause, Jackson Apache-2.0,
TypeScript Apache-2.0. Offline builder kopíruje Kotlin distribution licenses.
Kotlin ZIP byl obsahově připnut, jeho publisher checksum nebyl v pilotu ověřen;
obsahová kontrola není důkaz autenticity.

## Reprodukovatelné explicitní kroky

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
  --phase test --offline --output /tmp/kgmaker-plan.json
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
a export označuje roots pod `build/generated`. Obsah vytvořený annotation processorem
se přijímá jen z explicitního úspěšného buildu: zůstává pod konkrétním build runem,
manifest ukládá SHA-256, execution ID a snapshot hash a jakákoli následná změna
import zneplatní. Reálná fixture provede následnou JVM inspection a ověřuje
`origin=generated`; scan ani běžná inspection processor nespouštějí. Externí Maven
toolchain selection, Gradle custom varianty/included builds, Kotlin options a
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

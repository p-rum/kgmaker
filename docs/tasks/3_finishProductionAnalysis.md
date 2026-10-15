# T003 — Dokončení integrované produkční analýzy KGMAKER

- Task ID: `T003`
- Revision: 1
- Datum: 2026-10-15
- Stav: SPECIFICATION; níže uvedené kroky nejsou deklarací hotové implementace.
- Baseline: main `8ac80ca30f6f680539deb7fb3590519d3a5c1460`; PR #4 `a81def9dbc74fff3a5619cd02244be7f215f91cc`; navazující PR #5 `6b5aea13c150a75858973dd2e08debf802ff29ed`.
- Depends on: [T001](1_featureAnalysis.md), [T002](2_buildAwareInspection.md), obsah PR #4 a #5.
- Supersedes: pořadí implementace a nejednotné aktivní značení milníků. Neruší požadavky T001/T002 ani historické dokumenty změn.
- Autorita současného stavu: [stavová matice](../production-analysis-progress.md). Pravidla: [AGENTS.md](../../AGENTS.md), [registr](README.md).

## Cíl a rozsah

Dodej integrovaný nástroj, který pro Kotlin/Java Spring Boot backend, PostgreSQL/Flyway,
Kafka/HTTP a TypeScript frontend poskytuje doloženou strukturu, call/data paths,
konzervativní framework vazby, vysvětlitelný impact a použitelné podklady pro analytického
či implementačního agenta. Nestačí samostatně spustit worker: jeho kontext musí používat
query, impact, feature, workspace, hook i report bez ztráty důkazní síly a freshness.

Priorita uživatelského přínosu: lifecycle → build/Kotlin → Spring → persistence →
integrační dataflow. Frontend, XLSX, metodika, incremental a distribuce zůstávají
povinné položky statického/analytického cíle. Confluence boundary dle T001 se dodává
odděleně a není nahrazena slibem budoucího připojení. Runtime import je samostatná
volitelná etapa a neblokuje dokončení statického jádra.

Non-goals: model API/MCP, povinná graph DB, online procházení repozitářů bez explicitního
workspace, automatické migrace, runtime capture při scan/hook, finanční důkazní engine,
slib úplného runtime dispatch z čisté statické analýzy, nahrazení neznámých údajů odhadem.
Příklad finančního/platebního toku je fixture, nikoli natvrdo zabudovaná doména produktu.

## Výchozí fakta ověřená v kódu

- `feature.current_graph()` staví syntaktický/semantic/Flyway graf; nepřebírá compiler index.
- `cli.scan()` a `cli.hook_context()` ukládají nově vytvořený syntaktický graf do stejného store jako inspection. Nová inspection začíná také ze scan baseline; není dokončený správce více nezávislých compiler kontextů.
- `inspection.py`, `worker_protocol.py`, `callgraph.py`, `control_flow.py`, `flow.py` obsahují funkční compiler pipeline pro omezenou matici; nepřepisuj ji od nuly.
- `KotlinFrontend.kt` používá BindingContext a language/API 1.9 při distribuci compileru 2.1.10. To není podpora K2 language 2.x.
- `build_runner.py` vykonává explicitní plán; Maven EventSpy a Gradle SourceSet export nejsou pouhé regexy nad build soubory.
- `availability.py`, `schema_replay.py`, `workspace.py` jsou existující implementace s omezeným podporovaným rozsahem, nikoli prázdné stuby.
- Registry kompatibility, framework adaptéry, XLSX a selektivní invalidace nejsou kompletní. Dependency-free Python core zůstává oddělený od JDK/Node workerů.

## Závazné průřezové požadavky

| ID | Požadavek |
|---|---|
| T003-R01 | Jedna identita entity a jedna evidence/store infrastruktura; zachovat repo/module/source-set/variant kontext a explicitní source↔bytecode mapping. |
| T003-R02 | Oddělit SYNTAX_CANDIDATE, SYMBOL_RESOLVED, DISPATCH_CANDIDATE, FRAMEWORK_DERIVED a RUNTIME_OBSERVED; typové reference nejsou volání. |
| T003-R03 | Konfigurace a testy nesmějí zkreslit produkční execution ranking. Enum může mít skutečné metody, jeho reference samy nejsou execution význam. |
| T003-R04 | Freshness zahrnuje obsah zdrojů, dirty/untracked vstupy, classpath a pořadí, dependencies, compiler/worker verze, config/profiles, toolchain a workspace mapping. |
| T003-R05 | SOURCE_ONLY funguje bez JDK/Node; žádný implicitní build/download/npm script/test/DB/DDL při scan, query, hook, feature nebo data-check. |
| T003-R06 | Build PASS, test PASS, statická dosažitelnost a AVAILABLE jsou nezávislé stavy. Agent nesmí vyrábět compiler fakta či approvals svou confidence. |
| T003-R07 | Zápis je atomický; timeout/cancel/invalid input/stale snapshot ponechá poslední validní generaci a explicitní diagnostiku. |
| T003-R08 | Neúplný dispatch/parser/config/coverage vede k PARTIAL/UNKNOWN s konkrétní hranicí; prázdný výsledek není důkaz absence. |
| T003-R09 | Zachovat staré single-root/semantic/feature CLI a čtení grafů v1/v2/v3; migrační změna má test i sémantiku starých ID. |
| T003-R10 | Každý PR obsahuje řádně číslovaný český dokument změn, aktualizované aktuální docs a skutečnou test evidence. |

## T003-S01 — Sjednocený acceptance inventář a compatibility matrix

Závislosti: žádné; před implementací znovu ověř remote heads a relevantní instrukce.
Vstupy: T001/T002, `docs/production-analysis-progress.md`, `tests/`, `fixtures/`, CI workflow.

1. Používej číslování registru; nevytvářej další P/M/A řadu. Přenes všechna lokální acceptance ID T001/T002 do dohledatelné matice: požadavek, scope, stav, test path/test name, fixture, verze, důkaz běhu, gap, cílová etapa.
2. Stavy: NOT_STARTED, PARTIAL, VERIFIED_IN_SCOPE, BLOCKED. VERIFIED_IN_SCOPE vyžaduje konkrétní fixture/matici, ne jen existující funkci nebo zelené obecné CI.
3. Původní P aliasy mapuj dle registru, ale nevymýšlej jejich chybějící původní text. Nové acceptance tohoto dokumentu jsou samostatné závazné scénáře.
4. Pinuj a ověř podporované JDK/Kotlin/Maven/Gradle/TS/React/Spring/Hibernate kombinace. Rozšíření verze bez testu není automaticky podporované.

**T003-AC01:** Každý požadavek T001/T002 má záznam; žádný nezmizel při normalizaci. Matice rozlišuje testované, netestované a záměrně unsupported varianty a uvádí jejich další krok.

## T003-S02 — Jednotný provider a lifecycle grafu

Závislosti: S01. Moduly: `inspection.py`, `model.py`, `store.py`, `feature.py`, `workspace.py`,
`cli.py`, `project_cli.py`, `inspection_cli.py`, `semantic.py`, `analysis_validation.py`.

1. Zaveď společný provider aktuálního grafu nad existujícím store, nikoli druhý nezávislý katalog. Může vracet projekci syntaktické vrstvy, compiler kontextů a sémantiky, ale všechny entity/evidence musí mít jednoznačnou identitu.
2. Zaveď atomickou generaci a index kontextů. Aktualizace jednoho module/source-set nesmí smazat ostatní platné kontexty. Stejný source symbol v různých variantách neslučuj bez identity kontextu.
3. Scan/hook smí obnovit syntaktickou vrstvu a označit závislé compiler kontexty stale; nesmí je tiše přepsat ani znovu spustit kompilaci. Uživateli vrať důvod a explicitní další příkaz.
4. Zaveď jednotný výběr scope/context pro query/impact/feature/workspace/report. Více možných kontextů vyžaduje explicitní volbu nebo PARTIAL s popisem; žádný výběr „poslední vyhrává“.
5. Feature packet a validator převezmou context fingerprint a evidence IDs. Impact validuje skutečný směrovaný vztah i nejméně jistý článek. Semantic anotace nemohou vytvořit compiler facts.
6. Aktualizuj `status`, `check`, hook a agent routing: source-only check nesmí deklarovat aktuálnost compiler vrstvy. Přenes realm a provenance přes multirepo namespace.

**T003-AC02:** Reálná fixture `inspect → scan → hook-context → query/impact → feature prepare/validate/report` zachová čerstvé call sites/CFG; změna classpath JAR, profilu nebo zdroje je zneplatní. Druhá inspection modulu B zachová A; selhání B nesmaže A. Ve všech offline cestách procesní sentinel prokáže nulové spuštění buildu. Pokrývá T002-S06, T002-WS-01, T002-BC-01 a T001-FA-31.

## T003-S03 — Reprodukovatelný build, source sets a scope

Závislosti: S02. Moduly: `build_model.py`, `build_runner.py`, `classification.py`, Maven/Gradle exportéry.

1. Dokonči effective model pro parent/BOM, profily/properties, ordered classpath, reactor dependencies, generated roots, compiler options a toolchains. Gradle varianty/included builds musí být podporované nebo explicitně diagnostikované; regex Kotlin DSL není náhrada.
2. Zachovej oddělení build tool orchestrace od source analysis. Nepovoluj annotation processors při pouhé inspekci; generovaný kód pochází z explicitního buildu/importu.
3. Mapuj produkční/test/generated/dependency origin podle skutečných source sets, zachovej konflikty overrides a build modelu. Unknown scope nesmí tiše spadnout do production.
4. Ověř snapshot před/po execution, nepřenášej starý target/build. Build result a XML test summary rozlišují compile-only, NOT_RUN, ZERO_TESTS, SKIPPED, FAILED a PASSED.
5. Cross-repo artefakt mapuj podle konkrétního obsahu/manifestu, ne jen GAV či názvu třídy. Zdokumentuj LOCAL_TRUSTED policy: kopie projektu není bezpečnostní sandbox.

**T003-AC03:** Skutečný multi-module Maven projekt s neaktuálním JAR v local repo použije aktuální reactor output; profil/BOM změní manifest; failed module nepublikuje čerstvý bytecode. Gradle fixture ověří main/test/generated a vlastní source set. Přidání 500 testů/dokumentů nezmění produkční projekci/ranking. Pokrývá T002-MV-01–05 a EX-01; timeout/cancel nezanechá platné incomplete artefakty.

## T003-S04 — Kotlin/JVM resolution a CFG

Závislosti: S03. Moduly: `workers/jvm`, protocol, inspection, callgraph, control_flow.

1. Dolož technologickou volbu K2/Analysis API na mixed Java/Kotlin fixture a podporované matici; K1 kompatibilitu ponech jen jako explicitně omezený backend, dokud ji nenahradíš.
2. Zachovej přesné owner/descriptors, caller, source range a call-site identity; přidej constructors, references/lambdas, extension/operator/accessor, default arguments, inline/suspend a initializers. Nepodporované konstrukce musí mít lokalizovanou diagnostiku.
3. Odděl declared target a konzervativní dispatch kandidáty; zahrň dependency hierarchy a důvody neúplnosti. Reflexe/classloading nejsou resolved podle jména.
4. Ověř source/bytecode mapping včetně chybějících debug dat a generovaných členů. Neslučuj bytecode instructions se source expressions bez doloženého mappingu.
5. Rozšiř CFG o when/Elvis, short-circuit, try/catch/finally, break/continue, return/throw, coroutine/async hranice. CFG není důkaz proveditelnosti každé cesty.

**T003-AC04:** Ručně anotované golden call sites a větve pokrývají T002-CG-01–05; protilehlé větve nikdy nejsou vykreslené jako následná sekvence. Počty resolved/unresolved/unsupported odpovídají inventáři, žádné falešné resolved hrany v anotovaném corpus. Výsledky uvádějí verze a scope, ne extrapolaci přesnosti na celý bankovní projekt.

## T003-S05 — Spring Boot symbolový adaptér

Závislosti: S04. Rozšiř worker facts a Python framework inference nad společným modelem.

1. Rozliš FQN a meta-anotace, component scan, imports, Configuration/Bean; podporované injection formy včetně kolekcí/providerů.
2. Resolve Qualifier/Primary a Profile/Conditional proti konkrétním properties/classpath. U neznámé property nebo custom registrar/factory ponech alternativy a boundary.
3. Odděl object call, bean selection a proxy/advice. Modeluj self-invocation a podporované proxy/weaving režimy; samotné Transactional/Async/Cacheable/security anotace nejsou vykonané advice.
4. Entry points: HTTP handlers, Kafka/listeners, scheduled/event handlers a runners. Asynchronní hrana nesmí být synchronní pokračování.
5. Verzi pravidel a frameworku vlož do evidence a invalidace. Žádný automatický Spring bootstrap/Actuator.

**T003-AC05:** Fixture se dvěma beany, dvěma profily, qualifier/primary, neznámou condition a self-invocation prokáže rozdílné výsledky. Běžná uživatelská anotace stejného krátkého jména se nezmění na Spring bean. T002-SP-01–03.

## T003-S06 — Persistence a query model

Závislosti: S05. Moduly: JVM facts, `domain.py`, `schema_replay.py`, `flyway.py`, feature/availability.

1. Java/Kotlin javax/jakarta dle dependencies; field/property access, Id/EmbeddedId, embedded/overrides, associations, owning/inverse side, inheritance a priorita XML overrides.
2. Entity → persistent attribute → logical/physical table/column s datasource/persistence unit/schema/Flyway stream/target identitou. Žádné univerzální camelCase→snake_case pravidlo pro custom naming.
3. Repository method → entity/projection/query; derived queries parsuj proti entity modelu. Odděl JPQL/HQL a native SQL, named queries, parametry a návratové projection typy.
4. Criteria/Specifications/QueryDSL/custom fragmenty zpracuj v podporovaných vzorech; dynamické zbytky jsou PARTIAL. Nevytvářej smyšlené source tělo runtime-generated repository.
5. Ověř nullability, typ, precision/scale, keys a relations proti vybranému Flyway cíli. `save()` je persistence intent, ne potvrzený INSERT/commit.

**T003-AC06:** Java i Kotlin fixtures s embedded ID, property access, dvěma datasource se stejným názvem tabulky, rename/drop a custom naming; žádné tiché sloučení ani deployment claim. Query read/write edges odkazují na správné objekty nebo explicitní unresolved. T002-HB-01–04 a T001-S06.

## T003-S07 — Integrační a datové cesty, ranking a diagramy

Závislosti: S06. Moduly: `dataflow.py`, `domain.py`, `test_analysis.py`, `views.py`, `flow.py`, feature validators.

1. Argument→parameter, return→consumer, field reads/writes a explicitní mappingy musí mít metodu, context, source a směrovou sémantiku. Rozliš potřebnou transformaci a neznámou business ekvivalenci.
2. Kafka: producer/consumer binding, topic z podporované konfigurace, cluster/service identity, payload; retry/DLT a subscription boundaries podle ověřené framework verze.
3. HTTP: Feign/WebClient/RestClient a podporované klientské vzory; rozliš definici requestu a execution/subscription. Dynamic URL/auth/context neodhaduj.
4. Propoj služby pouze přes explicitní service/contract/release mapping. Neoznač vzdálený HTTP/Kafka přechod jako lokální JVM call.
5. Rozšiř execution/impact rank o entry relevance, doložené cesty a side effects s vysvětlením. Typové reference, testy a konfigurace zůstávají oddělené; metody enumů se nezahazují.
6. Markdown/Mermaid/JSON pohledy generuj z téhož modelu, s scope, provenance, async/unresolved a truncation. Pořadí pochází z CFG, ne seřazeného call graphu.

**T003-AC07:** Controller→service→repository→DB a producer→topic→consumer fixtures poskytují validované call/data paths. Stejný topic na jiném clusteru se nesloučí; nevykonaný reactive request není execution. Build PASS + statická cesta bez požadovaného důkazu nechá availability UNKNOWN (T002-EV-02). Přidání číselníků/reference hubů nezvýší execution význam samo o sobě.

## T003-S08 — TypeScript a backend/frontend kontrakt

Závislosti: S02/S03; pro kompletní BE–FE cestu S07. Moduly: `workers/typescript`, inspection, workspace/test_analysis/dataflow.

1. Dokonči project references, tsconfig options/paths/exclude, re-exports, generics/overloads a callback resolution s přesnými unresolved důvody.
2. Versioned UI adaptér rozšíří doložené event→handler vazby, nikoli libovolné jmenné propojení komponent. Generovaný klient zůstává derivátem svého kontraktu.
3. Propoj HTTP response fields přes mapping/destructuring/state do podporovaného UI použití; service/version/prefix mapping je explicitní. Stejná URL v jiném service realm není shoda.
4. Zachovej explicitní test overlay a oddělení produkce; statický test není runtime PASS.

**T003-AC08:** Multi-project fixture s re-exportem a backend/frontend/test checkouty: změna backendového pole ukáže správné UI použití a testy, rozporný kontrakt nebo chybějící repo vytvoří coverage gap. Změna tsconfig či lockfile zneplatní dotčený kontext. T001-FA-08 a T001-S07.

## T003-S09 — Artefakty, metodika a analytický výstup

Závislosti: S07/S08 pro úplný cross-layer scénář. Moduly: nové offline workbook/template adaptéry, confluence, evidence validation/report.

1. XLSX čti přes zipfile/XML s limity entries, expanded bytes a XML velikosti. Sheets/named ranges/formula dependencies a cached values jsou oddělené; nic nevyhodnocuj, nespouštěj makra ani externí odkazy.
2. Shared/INDIRECT/external/unsupported binární XLS mají diagnostiku. Evidence používá ověřitelný workbook/sheet/cell locator a hash.
3. Podporovaný HTML template dialect propojí backendové naplnění placeholderů; PDF service je external boundary.
4. Rozliš aktuální implementační fakt a schválený požadavek/metodiku. Rozpor IMPLEMENTATION_VS_APPROVED_REQUIREMENT není automaticky chyba dokumentu; zachovej approval/provenance.
5. Report obsahuje Required/Existing/Missing/Derived/External/Unresolved odvozené z nezávislých availability/acquisition/usability dimenzí, konkrétní delivery requirements, otázky, změny, acceptance a test plan.

**T003-AC09:** T001-FA-20–23 a FA-08 mají skutečné fixtures s platnými i falešnými lokátory; unsupported data nejsou „chybějící v bance“. Kompletní report pokryje podporovanou cestu BE→UI/template→PDF boundary a odliší business blocker od omezení nástroje.

## T003-S10 — Skutečný incremental a selektivní revise

Závislosti: S02, stabilní adaptéry S04–S09. Moduly: scanner/inspection/provider, semantic/feature/workspace/schema caches.

1. Content-addressed cache po module/source-set/variant a extrakčním stupni; zahrň parser/worker/rule verze, compiler options, ordered classpath, config a workspace release mapping.
2. Reverse dependency indexes pro kladnou evidenci, schema/contract vazby a negativní lookupy. Nově přidaný soubor může zneplatnit NOT_FOUND_IN_SCOPE i bez změny původních zdrojů.
3. Add/change/delete/rename a kolize ID musí vést ke canonical stejnému grafu jako full scan. Změna veřejné signatury invaliduje callers; změna interního těla invaliduje relevantní paths.
4. Revise odpovědi přepočítá závislé závěry, zachová validní nezávislé závěry a historii. Nepřenášej staré approval na jiný význam/hash.
5. Cache corruption je miss, nikoli evidence. Atomická publikace immutable worker distribucí odstraní závod přestavby workeru proti analýze.

**T003-AC10:** T001-FA-13–16/24: nesouvisející změna nevyžaduje celou novou sémantickou analýzu, relevantní změna ano; nový zdroj invaliduje negativní lookup. Full/incremental jsou shodné po normalizaci neidentitních metadat. Dva souběžné worker/snapshot běhy nepublikují mixed context.

## T003-S11 — Release, packaging, benchmark a společná acceptance

Závislosti: S02–S10; S12 se vykazuje zvlášť, S13 není statický release gate.

1. Zabal volitelné workery a exportéry tak, aby fungovaly z čisté instalace mimo checkout. Zachovej KGMAKER_WORKERS_HOME/explicit home a SOURCE_ONLY bez JDK/Node. Jasné prerequisite/install/licence/hash instructions pro podporované OS včetně cílových Windows bez admin práv.
2. CI odděl Python core, skutečné workers, Maven/Gradle/framework fixtures a rendering. Povinný worker job musí chybějící worker odmítnout, ne potichu skipnout.
3. Benchmark: reprezentativní ručně anotovaný corpus, cold/warm čas, peak memory, velikost indexu a resolution/unsupported pokrytí. Změř opakování, popiš hardware/versions a nastav regression budgets z dat. Žádná nepodložená úspora tokenů nebo procento přesnosti.
4. Jeden end-to-end scénář: explicitní build/import→inspection→offline refresh→feature/data audit→report→source change→targeted invalidation. Obsahuje pozitivní i negativní scénáře a všechny povinné legacy acceptance.
5. README, architecture, capability docs, CLI help, registry a progress musí být konzistentní. Každá VERIFIED položka odkazuje na skutečný test/log artefakt a matrix scope.

**T003-AC11:** Čistý instalační smoke test v podporované matici, všechny povinné acceptance doložené, mimo matici jasný unsupported fallback. Model/CLI migrace bez falešného zvýšení evidence. Výkonový limit má změřený základ; nulová nevyřešená povinná mezera potřebná k tvrzenému scope.

## T003-S12 — Confluence synchronizační boundary

Závislosti: stabilní feature/evidence model, pro schválenou metodiku S09.
Implementuj T001-S05: adapter interface, fake adapter, pull/prepare-publish, přesný
payload diff, approval navázané na hash a page version, optimistic concurrency,
TO_BE izolaci a re-import vlastního návrhu bez povýšení na implementaci.
Reálný konektor je samostatně doložená integrace konkrétního hosta/API; případný
chybějící přístup je BLOCKED pro živou integraci, ne důvod vynechat offline boundary.
Žádný automatický publish při scan/hook/feature. Publish vyžaduje explicitní pokyn.

**T003-AC12:** T001-FA-28–30: změna stránky či payloadu po approval zabrání zápisu;
fake adapter test není označen za živou synchronizaci. Lokální HTML workflow funguje bez adaptéru.

## T003-S13 — Volitelný runtime import

Závislosti: S02/S05/S07. Implementuj T002-S07 až odděleně od statického dokončení.
Přijímej sanitizované traces/beans/conditions/mappings s build/config/service/version
fingerprintem a scope. Observed edge platí jen pro daný běh; nepřítomnost v trace
neprokazuje nemožnost vykonání. Actuator bean export není method trace. Žádná
automatická instrumentace/startup, který by mohl spustit migrace či externí komunikaci.

**T003-AC13:** Stale trace nebo jiný artefakt/config je odmítnut/oddělen; async hranice
zůstávají. Runtime call observation bez hodnotového důkazu nezmění availability.
S13 se ve statickém DoD vykáže NOT_STARTED/OPTIONAL bez zkreslení ostatních stavů.

## Rozdělení dodávky a pracovní postup

- Nejdříve přečti AGENTS/registry, aktuální kód/testy a open PR heads. PR #4→#5 tvoří stack; pokračuj z jejich obsahu, nepřepisuj je a nemerguj bez pokynu.
- S01 může být dokumentační PR. S02 musí předcházet tvrzení, že agent využívá compiler graf. Další etapy mohou mít více malých PR; číslo etapy neurčuje číslo PR ani change note.
- Před úpravou kontraktu popiš migration a failing acceptance. Přidávej smysluplné testy chování, ne testy kopírující implementaci.
- Zachovej existující produkční graf, Flyway/workspace/proof engine; rozšiř sdílené rozhraní. Nepřidávej tiché fallbacky zaměňující zdrojový pattern za přesný důkaz.
- V implementačním PR vždy odkazuj na T003-Sxx/ACxx a relevantní T001/T002 testy. Každý PR má nový `docs/changes/<N>_<shortPrName>.md` dle AGENTS.
- Aktualizuj status pouze na základě provedených kontrol. Zachovej blokery, logy a podporovanou matici; neodstraň požadavky, které jsou obtížné.

## Definition of Done a předání

Statické/analytické jádro je hotové teprve po doložení T003-AC01–11 a povinných
scénářů T001-S01–04/S06–07 a T002-S01–06 ve zveřejněné podporované matici.
Úplný rozsah T001 navíc obsahuje boundary T003-S12; stav živé integrace se vykazuje
samostatně. Runtime T003-S13 je volitelný. Žádná etapa nesmí být nazvána COMPLETE,
pokud má povinné části pouze jako prompt, stub, mocked success nebo neurčený follow-up.

Předání obsahuje PR + change note, tabulku etap/acceptance, přesné příkazy a skutečné
výsledky, podporované verze, konkrétní příklad reportu a nevyřešené hranice. Zdokumentuj
co umí agent po integraci automaticky a kde musí ověřit zdroj nebo požádat o business
rozhodnutí. Přesný syntaktický graf není sám o sobě kompletní implementační agent.

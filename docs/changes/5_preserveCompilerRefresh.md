# Zachování compiler důkazů při offline refreshi

Datum: 2026-10-15. Baseline: `d9a89fe` a existující rozpracovaný tree.
Vazby: T003-S02/AC02, T003-R05/R07/R09. S02 je ověřeno pouze v publikované
matici; dokument netvrdí dokončení navazujících produkčních etap.

## Problém a změny

Scan/hook přepisovaly compiler index. Nový `graph_provider.py` sdílí validaci
snapshotu s compiler CLI a zachovává compiler symboly, hrany, call sites, CFG a
evidence v single-root scan/hook/feature projekci. Validuje zdroje včetně nových
souborů, classifier konfiguraci, project inputs, classpath a worker distribuci.
Dotčený stale kontext ztratí compiler fakta a zůstane jako explicitní marker s
důvodem a next command; ostatní module/profile kontexty zůstávají použitelné.
Proces compileru ani buildu se při refreshi nespouští. Workspace schema v3 navíc
přenáší compiler kolekce s repo-qualified symbol/context/evidence/CFG identitami.

## Kompatibilita a příklad

Store zůstává stejný, legacy source-only grafy se obnovují původním způsobem.
Nové compiler důkazy nevznikají z heuristických hran ani semantic confidence.
Příklad: `inspect code --classpath ...`, následně `scan`, `hook-context` a
single-root `feature prepare` zachovají čerstvé compiler výsledky. Po změně
compiler vstupu výstup uvede konkrétní nový příkaz explicitní inspection.

## Ověření

Navazující běh 2026-10-16: **195 passed in 38.41 s** (`python3 -m pytest -q`).
Nové kontroly pokrývají skutečný Maven reactor proti starému JAR, TS re-export a
lockfile invalidaci, ORM realm/naming boundary a schválenou metodiku s decision
provenance. Query/impact podporují `--context`, packets obsahují context fingerprint
a graph evidence IDs; workspace cache zahrnuje compiler index. Opravena byla také
regrese `docs`, který opět vykresluje uložený snapshot. T003-S03/S06/S08/S09 jsou
nadále PARTIAL. Navazuje na T003-S01/S02 a jejich dílčí acceptance.

- `python3 -m pytest -q`: **184 passed**, 15.93 s; lokální Python 3.12.
- `python3 -m pytest -q tests/test_compiler_workers.py tests/test_graph_provider.py tests/test_build_aware.py`:
  **17 passed**, 10.16 s; skutečný JVM worker a existující build fixture,
  zachované call sites/CFG přes scan a hook, procesní sentinel v offline cestě.
- `python3 -m pytest -q tests/test_graph_provider.py tests/test_workspace.py tests/test_inspection_contract.py`:
  **24 passed**, 1.63 s; selective stale a workspace compiler schema v3.
- `mvn -q -DskipTests package` ve `workers/jvm`: PASS.

## Neprovedené kontroly a zbývající práce

T003-AC02 je ověřeno v publikované JVM/Python matici. Query, impact a feature lifecycle
používají stejnou explicitní volbu scope/context; packet ji zachová pro validate,
apply, status a report a nejednoznačnou variantu odmítne. Skutečný worker test provádí
celý end-to-end sled s profilem, classpath a packet invalidací. Module/profile kontexty se akumulují podle selection
key; worker identity obsahuje context a neplatný modul B nemaže A. Řádkový
acceptance inventář T001/T002 je v `docs/acceptance-inventory.md`; viditelně uvádí
PARTIAL a NOT_IMPLEMENTED mezery ostatních etap T003.

Lokální číslo změny 5 je volné v tree a známých refs. Kontrola otevřených PR
nebyla provedena: `gh` není nainstalováno. Číslo před publikací znovu ověřit;
PR zatím nebyl publikován a nic nebylo mergováno.

## Offline XLSX, Thymeleaf a Confluence boundary

Navazující změny pokrývají části T003-S09/AC09 a T003-S12/AC12:

- `workbooks.py` bezpečně čte bounded `.xlsx` ZIP/XML, vytváří sheets, cells,
  named ranges a statické formula dependencies. Cached value je oddělená a má
  freshness `UNKNOWN`; vzorce se nevyhodnocují. `.xls`, shared formula, INDIRECT,
  external link, traversal a překročení limitu mají explicitní diagnostiku.
- Feature/data-check přijímá hashově svázaný `workbook_cell` locator a při
  validaci znovu ověří sheet, cell, formula a cached value. Falešná hodnota je
  odmítnuta.
- `templates.py` v podporovaném Thymeleaf subsetu propojuje literal MVC model key,
  vrácenou šablonu a `${variable.path}`. Explicitní PDF renderer zůstává external
  boundary.
- `confluence_sync.py` definuje adapter interface a `FAKE_TEST_ONLY`: explicitní
  pull, managed-section diff, payload/base-version approval, optimistic concurrency,
  TO_BE re-import a audit bez obsahu. Živý konektor není tvrzen ani implementován.
- `semantic.apply_semantic_layer` již nemutuje vstupní graph. Tím je opravena
  duplicita, která blokovala `memory capture` po sloučení semantic konceptů.

Nové kontroly: `tests/test_workbooks.py`, `tests/test_templates.py` a
`tests/test_confluence_sync.py`. T003-S09 zůstává PARTIAL kvůli širším template
variantám, schválené metodice a plnému scénáři. Offline S12/AC12 je ověřeno ve
fake scope; live připojení je samostatně NOT_RUN bez doloženého host/API kontraktu.

Navazující `semantic apply` + `semantic validate`: PASS, znovu doložené 3 koncepty
a 7 vztahů. `memory capture --base HEAD --validation pytest189=passed`: PASS,
epizoda `a15d9564159267ab…`. `scan` + `check`: PASS, 151 souborů, 1306 uzlů,
3566 vztahů po projekci epizody. `git diff --check`: PASS.
`semantic.apply_semantic_layer` už nemutuje structural graph a regresní
`tests/test_memory.py` pokrývá původní duplicate-node selhání.

Focused feature/provider/workspace kontrola po sjednocení context selection:
**49 passed in 6.13 s**. Nový packet ukládá `graph_selection`, report ji zobrazuje,
staré packet schema bez tohoto pole zůstává čitelné a pozdější command nemůže
podstrčit jiný scope/context.

`status` nyní vykazuje source graph a compiler context odděleně. Pokud scan již
publikoval aktuální syntaktický graf se stale compiler markerem, status vrátí 2,
uvede konkrétní module/source-set/scope a přesný další inspection příkaz. `check`
zachovává stejný fail-closed gate. Regresní test obě cesty obaluje procesním
sentinelem; žádný worker ani build se nespustí. Init templates a existující
`.github/agents` instrukce byly sjednoceny se skutečným preserve/mark-stale chováním.
Workspace status poskytuje stejnou informaci strojově ve třech oddělených polích:
`source_graph_current`, `compiler_contexts_current` a `stale_compiler_contexts`.
Repo-qualified regresní scénář povoluje pouze read-only Git baseline příkazy a
odmítne případné spuštění projektu nebo workeru.

Explicitní compiler projekce nyní zachová společné source-only a dataflow hrany;
filtruje pouze fakta konkurenčních compiler kontextů. Bez této opravy by contextově
vybraný impact skončil bez cest. Reálný AC02 test ověřuje nenulovou směrovanou
impact cestu a celý veřejný feature report. Focused běh relevantní matice:
**68 passed in 20.07 s**.

## Maven effective model v2

Exportér `maven-session-2` nově zapisuje effective parent, resolved dependencies,
dependency management, importované BOM z parent chain, aktivní i inherited profily,
compiler release, generated source roots a konkrétní Java/Maven toolchain. Manifest
validator tato pole kontroluje; `dependency_model_hash`, toolchain, generated roots
a celý manifest vstupují do identity compiler kontextu. Gradle export doplňuje
generated roots a Java home. Reálná MV-02 fixture ověřuje BOM řízenou verzi reactor
dependency, profilovou změnu generated root a přednost čerstvého reactor outputu
před stale repository JAR.

Build runner nově přemapuje processor output do neměnného run snapshotu a zapisuje
pro každý generated source SHA-256, execution ID a snapshot hash. Validator odmítne
chybějící, cizí nebo dodatečně změněný generated vstup. Project model jej vede jako
samostatné generated membership a JVM worker přenáší `origin=generated` do symbolu.
Reálná fixture skutečně spustí vlastní annotation processor a následnou JVM inspection.

Zaměřený běh `tests/test_build_runner.py tests/test_build_aware.py
tests/test_graph_provider.py tests/test_compiler_workers.py tests/test_production_scope.py`:
**46 passed in 21.97 s**. T003-S03 zůstává PARTIAL: chybí externí toolchain selection,
Gradle custom/included varianty, Kotlin options a cross-repo artefakty.

## Kotlin operator a konstrukční matice

K1 compatibility frontend nyní převádí compiler-resolved uživatelský binární
operator na samostatný `OPERATOR` call site s přesným owner/descriptorem. IR zachová
receiver a argument a CFG odkazuje na totožné call-site ID. Nová izolovaná fixture
současně dokládá sekundární constructor call, callable reference bez tvrzení runtime
invocation, samostatného lambda caller, inline/default/suspend metadata a operator
v CFG. Zaměřený worker/CFG/build běh: **30 passed in 24.90 s**.

T003-S04 zůstává PARTIAL kvůli K2/Analysis API, generated default/coroutine body
mappingu, širšímu ručně anotovanému corpus a dependency dispatch.

Custom Kotlin getter/setter už nejsou neurčená property-body hranice. Frontend jim
přiřazuje přesný compiler descriptor, vlastní method symbol a source CFG; read/write
výraz vytváří `ACCESSOR` call site a assignment jej řadí po vyhodnocení hodnoty.
Speciální backing-field `field` nevytváří rekurzivní volání. Property initializers
a `init` bloky běžné třídy se nyní ve zdrojovém pořadí přiřadí primary constructoru;
jejich calls mají constructor caller a shodné IDs v jeho CFG. Top-level properties
používají file-facade `<clinit>()V`, zatímco object/companion inicializace zůstává
v constructor realm objektu. Samostatný test prokazuje, že se call sites ani CFG
mezi těmito realms nesloučí. JVM/CFG regrese po změně: **21 passed in 22.52 s**.

## Spring condition a bean-selection matice

Spring rules `annotation-source-v3` dávají každému beanu condition stav
ACTIVE/INACTIVE/UNKNOWN podle dodaných profiles, properties a available classes.
Podporované jsou Profile, ConditionalOnProperty a ConditionalOnClass; custom
Conditional zůstává UNKNOWN a nikdy se nespouští. Pouze jediný ACTIVE kandidát
vytvoří `injects_bean`; ambiguity či UNKNOWN používá `may_inject_bean`.

Reálná compiler fixture ověřuje dva profily, Qualifier, Primary, property i custom
condition, self-invocation proxy boundary a ochranu proti cizí anotaci stejného
krátkého jména. Opravila také dvě původní false-positive cesty: compiler symbol s
prázdným seznamem anotací už nepoužije textový look-behind a injection qualifier
se čte jen z bezprostředního annotation segmentu. Zaměřený framework/compiler/
provider/feature běh: **51 passed in 29.56 s**. T003-AC05 je VERIFIED_IN_SCOPE pro
tuto matici; celý S05 zůstává PARTIAL s hranicemi uvedenými v progress dokumentu.

Navazující rozšíření rozvíjí Spring meta-stereotype pouze přes compiler symbol
annotation typu, s limitem osmi kroků a detekcí cyklu. Explicitní
`spring_component_packages` určuje package/subpackage scan scope a vstupuje do
context identity; bean mimo scope je INACTIVE, chybějící scope je UNKNOWN. Fixture
ověřuje `@DomainService → @Service`, odmítnutí `fake.Service` i bean mimo `app`.
Zaměřený běh po rozšíření: **51 passed in 26.06 s**.

Po doplnění collection/map/optional/provider injection proběhl stejný zaměřený
běh znovu: **51 passed in 24.96 s**. Celá sada následně prošla jako **195 passed
in 40.19 s**.

Injection parser nyní zachovává generic target pro List/Set/Collection/Iterable,
Map<String,T>, Optional a ObjectProvider/Provider. Collection/map edges dokazují
každý ACTIVE člen; Optional používá stejný unikátní výběr jako scalar a provider
zůstává lazy `may_inject_bean`. AC05 fixture ověřuje každou formu a nezaměňuje
wrapper za bean typ.

Spring rules v3 následně přidávají statický konfigurační graf. `@Import` může
aktivovat konfiguraci nebo obyčejnou třídu mimo component scan, class condition
se přenáší na její `@Bean` metody a `@Bean` mimo `@Configuration` je odmítnut s
diagnostikou. ImportSelector/registrar zůstává explicitní neprovedená boundary.
AC05 fixture ověřuje aktivní i neaktivní imported configuration, její bean,
přímý import obyčejné třídy a false-positive factory metodu.
Zaměřený compiler/provider/feature běh po rules v3: **51 passed in 26.43 s**;
celá sada: **195 passed in 40.23 s**.

## JPA embedded identity a association role

JPA rules `annotation-source-v4` už nevytvářejí tabulku pro `@Embeddable`.
Compiler field symboly tvoří embedded atributy, `@EmbeddedId` se váže na jejich
typ a `@AttributeOverride` na konkrétní atribut i explicitní column. Umístění
identity rozlišuje FIELD a PROPERTY access. Many/One asociace nesou cílovou
entitu a OWNING/INVERSE roli; `mappedBy` vytváří `inverse_of`. Vztahový atribut
bez `@Column` už nevytvoří falešný scalar column. Reálný javac fixture a samostatný
kontraktní graph fixture pokrývají stejné invariants.
Zaměřený běh po JPA změně: **53 passed in 28.25 s**; úplná sada:
**197 passed in 43.89 s**.

JPA v4 navíc validuje Spring Data derived query proti vytvořenému entity modelu.
Fixture kombinuje Top, And, nested `customer.id`, embedded `id.tenant`, OrderBy,
delete intent a neexistující property. Jen vyřešené paths vytvářejí
`filters_by`/`orders_by`; query používá `query_reads` nebo `query_deletes` a
neznámá property zůstává `SPRING_DATA_DERIVED_PROPERTY_UNRESOLVED`.
Po rozšíření query modelu prošel zaměřený běh jako **53 passed in 28.46 s** a
celá sada jako **197 passed in 47.13 s**.

Explicitní `@Query` se nyní čte z compiler method symbolu. JPQL fixture váže
`Order` a `customer.id`, native SQL přesný `orders` ORM table, návratový
`OrderView` jako projection a named parametry proti method parametrům. JPA
`@NamedQuery` má samostatnou definici a `@Query(name=...)` používá
`uses_named_query`; dynamické výrazy a chybějící parametr zůstávají diagnostikou.
Po JPA v4 prošel zaměřený běh jako **53 passed in 28.60 s** a celá sada jako
**197 passed in 45.14 s**.

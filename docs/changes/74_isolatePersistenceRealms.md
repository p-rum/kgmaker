# Oddělené persistence realms a explicitní Flyway target

T003-S06-W04, kroky1–5, AC01–AC04; baseline355e98fe2ab62fadbf4869eb4485cd3562173068.
Závislosti W01/W02/W03 jsou merged, S03W05 content-bound cross-repo kontrakty
byly znovu ověřeny18PASS. Toto je rozpracovaný bounded subset, nikoli dokončení S06.

## Problém a změna

Workspace zaměňoval samotný stream_id za identitu databáze/streamu a odmítal dvě
různé DB se streamem main. Replay uzly neměly strukturovaný realm a schema
mapping mohl vybrat globálně jediné jméno bez prokázané datasource. Attach schema
navíc nahrazoval všechny SQL uzly se stejnou migration cestou a přesměrovával
field edges podle suffixu názvu.

Nová explicitní identita je dvojice(database_id,stream_id). Replay uzly nesou
původní dvojici, schema, target, config fingerprint a explicitní provenance.
DB/stream ID komponenty jsou percent-escaped, včetně procenta; běžné dosavadní
entity IDs zůstávají stejné. Migration/operation IDs jsou realm-qualified, aby
stejný SQL soubor pro dvě DB nevytvořil jedinou operaci. Parser/cache verze se
mění; staré uložené grafy se nepřepisují a zůstávají čitelné.

Nová fyzická vazba vyžaduje oba explicitní DB/stream klíče v konfiguraci i
selected compiler kontextu. Porovnává strukturovanou dvojici, typ objektu a jeho
kanonické ID, nikoli prefix/suffix ani náhodnou globální unikátnost. Volitelné
persistence_schema/flyway_target jsou validované context/build-manifest selektory
zahrnuté do selection hash/identity. Více schemas bez explicitní deklarace nebo
selektoru se nehádá. Persistence-unit výběr používá W03 XML input capture.

Explicitní workspace repo.flyway nejdříve provede offline replay. Teprve pak
znovu projektuje již čerstvé compiler fakty nad vybranými schemas, lokálně před
workspace kvalifikací. Nevolá worker, build, instalaci, migraci, aplikaci ani DB.
Přepočítává pouze FRAMEWORK layer daného kontextu; compiler SOURCE/IR/SYMBOL,
SQL replay, jiné kontexty a realms zachovává. T015 u nových realm-aware facts
vyžaduje přesný replay binding a konfiguraci, nikoli pouze stejné DB jméno.

## Kompatibilita a použití

Graph/store schema v1/v2/v3 se nemění. Starý context s dřívější JPA rule verzí
je čitelný jako historický, pro aktuální fyzickou vazbu vyžaduje reinspection.
Dřívější source-only @Table/@Column regex nevytváří nové silné persisted_in
hrany ani schema type/nullability tvrzení bez realm proof; hlásí UNKNOWN.
Zdvojená přesná DB/stream dvojice je neplatná před replay/cache mutací, stejné
stream jméno pod dvěma DB je podporováno. Chybějící/částečná/kontradiktorní volba
nevybírá fyzickou vazbu. MIGRATION_DERIVED není deployment/populated-data proof.

Příklad existujícího Python API: inspect_jvm(..., build_context={
'database_id':'orders-one','schema_stream_id':'main','persistence_schema':'public',
'flyway_target':'1'}), poté snapshot_workspace(manifest). Manifest repo.flyway
obsahuje explicitní database_id,stream_id,locations a target pro každý realm.
CLI nad již explicitně importovaným build manifestem používá stávající
kgmaker inspect jvm --root app --build-id BUILD_ID; nové automatické CLI discovery
ani nové přepínače se nezavádějí.

## Skutečné ověření a zbývající práce

Po opravě příliš širokého testového zákazu procesů (read-only Git je povolen)
real RED:3FAIL1PASS pro dvě DB se stejným streamem, chybějící strukturovanou
provenance a source-only global unique mapping. Minimum poté6PASS. Broader pure
Flyway/workspace/build-aware/T015 sada84PASS9actual-deselected5.98s. První příkaz
uvedl neexistující test_build_model.py a nespustil testy; nahrazen existujícími
moduly. Legacy assertions jsou změněné podle explicitního nového kontraktu.

Actual K1/K2 compiler→replay joins, dvě context identity nad stejnou entitou,
idempotence/reprojection/cache a negativní/tampered varianty jsou připravené,
ale ještě nebyly provedeny. Early root source review a skutečné focused kontroly
předcházejí jednomu novému frozen full; tento dokument žádný jejich PASS netvrdí.
Semantic/memory/scan a finální publikace/review jsou další kroky. Žádný merge
implementační agent neprovádí; GH CI je volitelné dle T045, lokální acceptance a
skutečný vyžadovaný toolchain zůstávají povinné.


## Early current-main source checkpoint

Merged HTTP parent75d448ee7791cffb3dc9f4cceff5136402a8f5e0 zachovává oba
JPA selection a HTTP input guards. Samostatný regresní RED našel, že obecné
smazání FRAMEWORK_DERIVED edges by odstranilo HTTP producer ve stejném kontextu.
Oprava identifikuje pouze vlastní Spring/JPA provenance přes framework_rules;
HTTP proof/edge/node zůstávají zachované. Tento scénář je GREEN. Exact-context
symbol subset, orphan owned-node cleanup a scoped diagnostics umožňují bezpečný
idempotentní přepočet nad dvěma kontexty. Pure sada82PASS9deselected5.80s;
aktuální minimum7PASS22actual-deselected0.23s. Actual fixture nově ověřuje i
T015 selected-realm access a osm partial/foreign/malformed proof variant pro
oba backendy. Ještě nebyla spuštěna; full není queued.


## Seskupená identity/provenance oprava před actual během

Vlastní původní unstarted flock byl ukončen sezero children, bez startu testu
(exit143; `/workspace/s06-w04-initial-cancelled-queue.json`). Oprava přidává
content-consistency proof_hash bezpečného realm recordu, nikoli autentizaci.
Node.name musí odpovídat strukturovanému SQL objektu; samotný shodný display
text ale nestačí. Binding používá schema_object komponenty a existující SQL
identifier/quote normalizaci. Compiler annotation JSON string constants se
dekódují se zachováním SQL quote markerů, nevzniká nový SQL/query parser.
Skutečný offline replay `"a.b".c` a `a."b.c"` má stejný display a dvě různé
identity; pure regression prošel. Actual fixture stejnou kolizi zkouší i přes
compiler-declared JPA schema/table hodnoty. Deset partial/foreign/malformed
variant včetně target hash a display-name tamper doplňuje oba backendy.
Pure targeted sada nyní83PASS31actual-deselected5.18s. Nový společný actual
batch čeká na jeden nový freeze; full stále není queued.


## Skutečný multicontext RED a seskupená oprava

První actual frozen batch skončil **6 PASS, 1 FAIL v8.23s**, exit1,
unchanged=true. Receipt/log/XML/source manifest jsou zachované jako
`/workspace/s06-w04-context-lookup-red*`. Dva správné physical bindings měly jen
jednu native-query hranu: starý repository lookup podle cesty/jména vybral
foreign compiler node. Tři existující class/method lookups nyní omezují výběr
na selected symbol IDs. Sedm ORM/XML attribute/unknown/metadata-complete/inheritance
lookupů navíc vyžaduje generated context_id, aby stejný canonical owner ve dvou
PU nesdílel attributes. Root tyto přesné guardy schválil jako representation
isolation, nikoli nový resolver. Offline replay původních skutečných K1 facts
po opravě zachová dvě native-query hrany; nové compiler spuštění tím není tvrzeno.

Připravený grouped actual případ kopíruje původní source/API fixture do vlastní
izolované repository, přidá dva persistence units a dvě mapping files. Stejná
entity class se váže na(public,orders) v DBone a(a.b,c) v DBtwo podle selected PU;
kontroluje XML provenance, foreign-context attributes a chybějící PU nad
skutečnými compiler facts i replay schemas bez mutace posledního validního store.
Tento centrální 2PU physical join zatím není PASS; následuje source-delta review
a jeden společný focused batch. Full zůstává nequeued.


První grouped actual běh skončil **8 PASS, 1 FAIL v9.65s**, exit1,
unchanged=true; `/workspace/s06-w04-selector-red-*` zachovává receipt. Testový
T015 selector omylem použil(repo,module,source_set), místo veřejného kontraktu
(service_id,repo_id,module). Opraven pouze tuple('orders','app','app'); replay
týchž skutečných K1 facts s opraveným T015 testem prošel bez worker spuštění.
Runtime se nemění, grouped compiler matrix se zopakuje s tímto testovým fixem.


Corrected společný batch: **182 PASS, 1 setup ERROR v227.54s**, exit1,
unchanged=true, `/workspace/s06-w04-corrected-focus.{log,xml}` a status/source
receipts. Všechny vlastní actual K1/K2 případy včetně 2PU physical join a
malformed negatives, T015, XML, Factory a conditions/cache prošly. Sibling
TypeScript prerequisite v Javac AC06 class setup chybělo v novém worktree;
nejde o celý PASS. Po exact source/lock shodě byly explicitně offline zkopírovány
TS a frontend node_modules včetně všech library SHA, bez install/network/build.
Receipt `/workspace/s06-w04-node-provenance.json`. Dosud unstarted remaining
AC06/HTTP flock byl ukončenzerochildren a bude sloučen s current-parent closure;
nevzniká duplicitní 182-test rerun.


## Current-parent closure preparation

Current parent ef3ab4050289aafd557caa5414c594698da006ea obsahuje Arg/UI,
Thymeleaf/T025 a Kafka51. Žádný JVM source delta W04 se nezavádí. Java/Kotlin
2bf6cbde/24461c43 distribuce z actual Arg donoru byla ověřena proti source/build/
lock receipt a přesnému30-JAR setu; TS/frontend source/lock a library SHA rovněž
souhlasí (`/workspace/s06-w04-current-worker-provenance.json`). Kafka workspace
properties projection a _qualified_evidence se zachovaly spolu s vlastní realm
reaugmentation. Cache key zahrnuje aktuální schema parser i HTTP a Kafka verzi.
New persistence_schema/flyway_target se zahrnují jen do JVM selection payload;
3JVM digesty zůstaly shodné a2TS varianty odpovídají přesné parent funkci.
Focused identity regression prošel. Chybějící realm se diagnostikuje pouze
pro skutečné entity, nikoli pro nesouvisející HTTP/Spring kontext bez JPA.
Zbývající AC06/HTTP a relevantní current-parent W04 případy jsou sloučeny
do jednoho closure batch; předchozích182 PASS se bezdůvodně neopakuje.


Current-parent closure je GREEN: **13 PASS, 0 SKIP v65.03s**, exit0,
unchanged=true,mismatches=[]; `/workspace/s06-w04-current-closure.xml` a status
receipt. Zahrnuje zbývající Javac AC06/HTTP cold+terminal cases a relevantní
current Arg W04/JPA/T015 positive/idempotence/2PU případy. Vlastní Maven fixture
byla explicitně čerstvě sestavena OFFLINE compile: BUILD SUCCESS8.632s; source
a oba class-file SHA jsou v `/workspace/s06-w04-fixture-build-proof.json`.
Následující read-only prerequisite preflight prošel; neprováděl build/instalaci.
283 tracked source/JAR hashů zůstalo přes closure stejných.

Compiler CI příkaz přidává skutečné XML a persistence-realm moduly s existující
explicitní API/worker přípravou; GitHub CI tím není povinným merge gate.
Schema/physical binding je podporovaný bounded důkaz; deployment, populated
DB, provider naming/runtime compatibility a širší XML query-access projection
bez dostatečné existující ownership evidence nadále zůstávají UNKNOWN.
Jeden repository-wide frozen full nyní čeká na finální root source closure;
předchozí partial runs nejsou vydávány za celý PASS.

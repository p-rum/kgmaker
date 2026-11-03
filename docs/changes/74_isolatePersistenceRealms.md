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

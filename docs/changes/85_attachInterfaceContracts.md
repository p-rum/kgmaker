# Připojení explicitních verzovaných integračních kontraktů

T013-S01–S05 a AC01–AC06, explicitní draft stack currentmain32a3bca + reviewed
T0127de7f6e; dependency T012 není tímto dokumentem prohlášena za merged/ready.
Izolovaný /workspace/interface-contracts, branch feat/t013-attach-interface-contracts.
Root schválil architektonický brief /workspace/t013-architecture-brief.md.

## Skutečná implementace a kompatibilita

Existující interfaces.py rozšiřují capture_interface_contracts a immutable
attach_interface_contracts. Sdílený bounded contract_inputs helper používá také
stávající test_analysis čtení OpenAPI/generation metadata a origin validator;
nevzniká druhý parser/registry/store. Raw SHA, explicitní revize/release, operation/
schema pointers a role mají vlastní revision fingerprint. Původní interface IDs,
logical IDs, technický stav a evidence buckets se nepřepisují; kompatibilita payloadu
zůstává UNKNOWN. DTO názvy ani return types se nejoinují na schéma.

Generated-client deklarace vyžaduje skutečné explicitní soubory, metadata source
contract tuple a generated-file membership/hash. Změněný contract SHA zachová
client ID a původní origin tuple, ale binding je STALE, i když legacy graph linker
stale generated node vypustí. SOURCE_ONLY source occurrence může doložit pouze
file deklaraci při module/compiler UNKNOWN; není to generator execution receipt.
Původní T011 main interfaces prefix i celý T0127de append jsou v baseline zachovány
byteově. Jeden chybný sdílený return při merge byl zachycen exactness kontrolou a
opraven composition commitem bb19eea před feature kódem/testy.

Čtou se jen explicitní confined bounded files; před/po capture/projection se
kontrolují hashes. Žádný scan/inspect/build/generator/network/schema-fetch/latest
index query/cache-write v attachment funkci. Zápis nového persistent formátu není
součástí API; migrace není potřeba. Unknown in-memory capture version fail-closed.

## Dosavadní skutečná evidence

Durable taskcaa94ab7c045224f542e459d54657431bd6988b43151140bdd6071abf4ef964f:
memory recall, bounded analyze/plan/implementation packet, root architecture closure.
Skutečný public RED nad reálnými OpenAPI/generated TS/metadata soubory a původním
provider catalogem: **1FAIL0.39s** na missing capture API. První pure positive/
stale/offline matrix následně **7PASS0.50s**, source-guard varianta **7PASS0.73s**.
Rozšířená pure T013 + workspace regresní sada **34PASS2.06s** před finálním
before/after guardem; finální pure skupina **35PASS3.23s** včetně during-attachment replacement guardu;
actual Kafka revision matrix PENDING.
Nejde o full PASS, compiler execution ani runtime transport důkaz.

Konkrétní fixture: dvě OpenAPI info.version při stejné method/route; same-name
backend/frontend Order bez kompatibility; valid generated metadata a stejně dlouhá
změna v1→v2; změna contract/source/metadata mezi capture a projekcí; forged capture,
external refs, ambiguous operations, foreign scope/source/context, missing/symlink/
oversize file a preserved last valid artifact při mutation během projekce.

V ambiguity negative byl nalezen upstream T010 DUPLICATE_NODE_ID pro POST
/orders/{id} a /orders/{name}. Root jej sleduje samostatným corrective scope;
T013 jej skrytě neopravuje ani neoslabuje pozitivní test. T013 odmítne ambiguous
nový contract na původním skutečném katalogu a zachová IDs/diagnostiku.

Příklad a hranice: [interface contracts](../interface-contracts.md). Native compiler
se zde nerozšiřuje. Actual Kafka fixture a finální source closure/focus/full/review
jsou PENDING; readiness až po T012 merge/current integration. GH CI je volitelné
podle výslovného uživatelského pravidla, ostatní gates nadále povinné.

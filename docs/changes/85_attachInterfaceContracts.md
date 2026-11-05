# Připojení explicitních verzovaných integračních kontraktů

T013-S01–S05 a AC01–AC06, explicitní draft stack currentmain32a3bca + reviewed
T0127de7f6e (historická baseline); aktuální merged dependency a evidence jsou uvedeny na konci.
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


## Nezávislý type-reference nález a oprava

Architect/root reprodukoval P1 nad5e935bd: method-not-a-type Node a symbol s
contradictory scope/path prošel původním existence-only type guardem. Tento source
není finálně schválený. Oprava odděluje canonical TYPE Node/symbol/source/hash/
selected context/declaration proof od chybějícího upstream payload-reference proof.
Současné versioned HTTP/Kafka facts žádný payload-type-ID producer nemají; supplied
request/response/message_type_id se proto nepřenese jako důkaz, ale zůstane None
s TYPE_REFERENCE_UNKNOWN. Explicitní contract operation/file/schema a generated
origin positive se zachovávají samostatně. Nepřidává se vymyšlený proof envelope.
Tamper matrix pokrývá method/fake-type/scope/path/context/metadata/missingproof pro
všechna3 pole; actual canonicalclass-without-payloadproof negative je připraven.

Provider pravidlo http-providers-2-ambiguous-variants je rozpoznané; AMBIGUOUS node
nebo incident edge se nepovýší na BOUND ani při jedné odpovídající operation.
Původní kandidáti/reasons/technický status se zachovávají. Unknown catalogue version
fail-closed. Finální type-corrected T013+workspace sada **59PASS3.03s**; source closure a
actual canonical-class/Kafka matrix stále PENDING. Starý35PASS receipt zůstává.


## Finální current-main, skutečné kompilátory a společný strict full (2026-11-05)

Common i T012 jsou merged; finální base je
`b0ef9e2ed93202154bf5bfb49aecd74d2b3dfdd6` (main po PR73).
Runtime/test/native source se vůči source-reviewed `9698828` nemění. Celý
interfaces module, contract_inputs, test_analysis i oba vlastní testové soubory
jsou byte-exact s actual společným potomkem
`2df55ff8d15d790808f6a81072144eeb408a05b8`. T012 prefix/constants/imports/globals
zůstávají zachované, žádná appended binding je nepřepisuje. Current main
workspace qualifier i Common role guards zůstávají zachovány.

P1 oprava type-reference byla nezávisle schválena na `df70c888`; původní source
s existence-only guardem není důkazem finálního chování. Skutečné K1/K2 Kafka
capture/contract revision případy i canonical-class-without-payload-proof negative
prošly. Historická matice **136 PASS / 1 setup ERROR** sdílela opravený T012
fixture-context výběr; oba vlastní actual Kafka případy v ní již PASS. Následný
corrected remainder **171 PASS / 0 SKIP, 85.94 s** a current-composition
**444 PASS / 0 SKIP, 370.90 s**, 2074 hashů beze změny, zůstávají oddělené receipts.

Jeden společný strict full běžel na `2df55ff`: **2587 PASS / 10 přesně povolených
optional SKIP, 2042.93 s**; všech 2597 výsledků, 4897 vstupních hashů a pět úplných
inventářů artefaktových adresářů beze změny. Všech 2116 ID tohoto rodiče je v témže
XML: **2106 PASS / 10 optional SKIP**. Vlastní testové moduly mají **45 PASS**
(43 pure/public + 2 skutečné K1/K2 captured fixtures). Nejde o samostatný full této
větve. Původní společný pokus **78 PASS / 2 SKIP / 1 FAIL, 2516 NOT_RUN** je zachován:
transfer fixture classpath postrádal JavaBridge.class a Kotlin module metadata.
Po explicitní SHA-ověřené obnově přesných donor souborů a **2 PASS** obou původních
golden/branch testů byl nový celý full autorizován. Runtime/assertion nebyly
oslabeny a native build nebyl opakován. Původní raw null-site není tvrzen jako
zachycený; corrected raw setup má 5/5 resolved calls.

Sdílený capture helper zachovává ověřené bounded UTF-8 JSON/list-origin pozitivní
případy starého test_analysis. Duplicate keys, oversized/changing files, non-object
metadata a chybné generation tuples nyní zůstávají fail-closed; není tvrzena
univerzální byte-ekvivalence původního permissive parseru. Staré test IDs jsou ve
společném fullu zachovány a nové malformed/immutability negativy tento rozsah
pokrývají. Nepřidává se resolver, persistent formát ani inferred type/schema join.

AC01–AC06 jsou ověřeny v dokumentovaném rozsahu. Payload compatibility a type-ID
reference bez explicitního upstream producer zůstávají UNKNOWN; ambiguous provider
Rule2 se nepovýší na BOUND ani při jedné matching operation. Data/runtime/deployment,
generator execution a schema compatibility nejsou dokázány. Finální nezávislé
base/head review, ready a merge jsou samostatné; GH CI není prohlášeno za PASS.

# Katalog Kafka producerů a consumerů

T012-S01–S05, AC01–AC06; explicitní draft stack nad Kafka W04 revize2
8afabe7c5056b9ec45e04f1f8fcf3470d18f4c98, nikoli schema1 samotné.
Root schválil architektonickou rekognoskaci /workspace/t012-architecture-brief.md.
Historický vývoj níže je oddělen od finální evidence na konci; finální independent review/merge zůstávají samostatné.

## Problém a zamýšlený rozsah

Čistá katalogová projekce má použít existující versioned Kafka code/binding/
subscription fakta, sdílený ViewDocument/interfaces, T008 ownership/context a
T009 evidence buckets. Producer/consumer záznamy zachovají original call/listener
IDs; consumer groups a broker realms zůstanou oddělené. Regex subscription bude
candidate bez topic expansion. Config-only a neznámý broker zůstávají UNKNOWN;
NewTopic/ProducerRecord se nepovýší na publikování ani delivery.

Podpora parenta: Java listener oba JVM backends, Kotlin K1 listener; Kotlin K2
annotation model UNKNOWN. Java canonical send(String,Object) pouze s přímým
ASCII literal topicem. Runtime/delivery NOT_OBSERVED, activation/data/deployment
UNKNOWN. Žádný parser/resolver/store ani implicitní proces, transport či broker.

## Dosavadní skutečné kroky

Izolovaný checkout /workspace/kafka-interfaces s vlastním durable workflow a
memory recall. Před vlastní kopií byly porovnány27 tracked worker source/build/
lock inputs a30 JAR/lib hashů proti skutečnému Arg build receipt63d3dbb;
doplněno102 SHA-ověřených license souborů. Parent Kafka worktree/artefakty se
nemění. Explicitní actual K1 RED po compiler/public snapshotu skončil1FAIL6.22s na
chybějícím public API; log/XML jsou zachovány v /workspace/t012-validation.
Následný K1 captured replay prošel14 public/negative kontrol a5 virtual tuple
negatives; config-only/unknown-realm pure test1PASS0.29s. Fresh actual matrix pending.

Implementace, konkrétní acceptance výsledky, finální dokumentace, full a nezávislé
review jsou zatím PENDING. Ready/merge až po schváleném Kafka parent merge a
aktuální integraci. GH CI je podle uživatele volitelné; ostatní gates platí.


Implementace revaliduje public kvalifikované facts proti explicitnímu privátnímu
saved graphu přes existující validate_code_fact; binding/subscription pouze
porovnává s read-only parent build_links replay. Je vyžadován dostupný workspace
s private capture, nikoli portable graph-only provoz. Žádná implicitní inspection,
cache write či rebinding k posledním nevybraným faktům. T008 inventory nyní dostává celý původní plný graph. Schválená společná
T006/T008 role classification rozpozná canonical workspace-derived identity;
role validity sama neautorizuje current Kafka link. Aktivní binding/code proof,
public whole-Node equality a unselected identity tamper kontroly zůstávají oddělené
od historical freshness. Konkrétní forged kind/path/context negatives tuto
hranici kontrolují; žádná kopie s vymazanými Kafka kontexty se nepoužívá. Unresolved deklarace bez původního proof mají pouze view-level
UNKNOWN/polarityUNKNOWN record, nikoli compiler či code proof.


## Finální current-main a ověřený rozsah (2026-11-05)

Závislosti Kafka rev2 i společná role boundary jsou merged. Finální base je
`4b0b07ce6e0ddd9d9f71c04f05ca4cbcb00ab49f` (main po Common PR72).
Current-main refresh nemění runtime/test vůči source-reviewed a skutečně
validovanému katalogu. Vlastní `project_kafka_interfaces`, imports/constants a
celý module prefix jsou AST-exact s jedním společným actual potomkem
`2df55ff8d15d790808f6a81072144eeb408a05b8`; parent HTTP provider/consumer APIs a
shared workspace qualification zůstávají zachovány. Všech 105 vlastních testů je
v jeho XML PASS, včetně actual K1/K2 selection/group/realm a malformed/Node guards.

První actual matrix 91 PASS / 1 FAIL odhalila chybný předpoklad input tuple:
producer ukládá čtyři explicitní config/contract/code inputs, manifest hash je
samostatný. Po bounded opravě a opravě testového výběru kontextu (historický
5 PASS / 1 setup ERROR zachován) prošla corrected actual selection matice
**10 PASS / 0 SKIP, 36.89 s**. Společná current-parent actual/pure matice T012/T013
prošla **444 PASS / 0 SKIP, 370.90 s**, 2074 hashů beze změny.

Jeden nový strict full na společném potomku `2df55ff`: **2587 PASS / 10 přesně
povolených optional SKIP, 2042.93 s**, všech 2597 výsledků, 4897 vstupních hashů
a pět úplných member inventářů beze změny. Všech 2071 ID tohoto rodiče je v témže
XML: **2061 PASS / 10 optional SKIP**. Nejde o samostatný full této větve.
První společný full selhal na neúplně přenesené Maven fixture classpath
(78 PASS / 2 SKIP / 1 FAIL, 2516 NOT_RUN); log/XML a vstupy zůstaly zachovány.
Po ověřeném doplnění přesných donor souborů a 2 PASS nezměněných původních testů
byl nový celý full autorizován. Native worker build nebyl opakován, assertion ani
runtime se kvůli setup chybě neměnily.

AC01–AC06 jsou ověřeny v dokumentovaném bounded upstream rozsahu; Kotlin K2
annotation UNKNOWN a config-only/regex/absent-private-proof limity zůstávají.
Delivery/activation/runtime availability nebyly pozorovány. Finální independent
base/head review a ready/merge jsou samostatné; GH CI tímto není prohlášeno PASS.

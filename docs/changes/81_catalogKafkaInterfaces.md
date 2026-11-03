# Katalog Kafka producerů a consumerů

T012-S01–S05, AC01–AC06; explicitní draft stack nad Kafka W04 revize2
8afabe7c5056b9ec45e04f1f8fcf3470d18f4c98, nikoli schema1 samotné.
Root schválil architektonickou rekognoskaci /workspace/t012-architecture-brief.md.
Tento rozpracovaný dokument neprohlašuje acceptance ani review za dokončené.

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
cache write či rebinding k posledním nevybraným faktům. T008 inventory dostává
nemutující kopii bez pouze přesně VALIDATED canonical workspace Kafka nodes,
incident edges a SOURCE_ONLY/WORKSPACE_DECLARATION contexts; původní plný graph
zůstává pro Kafka validaci. Konkrétní forged kind/path/context negatives tuto
výjimku kontrolují. Unresolved deklarace bez původního proof mají pouze view-level
UNKNOWN/polarityUNKNOWN record, nikoli compiler či code proof.

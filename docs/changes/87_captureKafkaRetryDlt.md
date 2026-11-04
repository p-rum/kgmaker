# T003-S07-W05 — bounded Kafka retry/DLT deklarace (draft)

## Problém a scope

W04 canonical listener/send neobsahoval retry/DLT policy hranice. Tato změna
reuse kafka_code compiler proof guardy, graph/evidence/workspace a flow; nepřidává
store, resolver, native producer ani implicitní build/app/broker. Explicitní
parent `19b0594795ac1f9167916178907b77bb0f070f51` zůstává draft závislost.

Přidán `kafka-retry-1`: exact supported Spring Kafka3.3.2 JAR+resource SHA,
Java/K1 literal attempts/suffix deklarace a jednoznačný same-owner DltHandler.
Původní IDs zůstávají. Python compiler materializer zachovává annotation/realm
witness i pro RetryableTopic/DltHandler; žádný JVM rebuild nebyl potřebný.

Flow odděluje framework policy od CFG execution. DECLARED znamená statickou
policy, execution/delivery NOT_OBSERVED a activation/runtime/data/schedule/
destinations UNKNOWN. Nepodporované API má jen SYNTAX_CANDIDATE/UNKNOWN;
custom handler, expressions, ambiguity a unsupported configurace nevytvářejí
jistou DLT cestu. Version+ordered-classpath hash brání přijetí staré generace.

## Reprodukce a dosavadní skutečné kontroly

- Actual Java/K1 RED:2FAIL6.15s, raw capture uložen před assertion chybějící policy;
  všech396source/test/worker/fixture vstupů beze změny. Nešlo o setup failure.
- Initial implementation FIFO actual6PASS21.74s,397vstupů beze změny; supported,
  custom handler a skutečný official3.2.0. Historický výsledek před guard opravami,
  nikoli finální acceptance.
- Nezávislý review doložil publicGraph P1: selfhashed policy + foreign syntax DLT
  edge bez proof se reportovala DECLARED. Oprava ověřuje celý relevant edge set,
  kanonické source/handler tuples a jejich vlastní compiler proofs. Unknown row
  nevrací falešný foreign target. API duplicity jsou konzervativně odmítnuté.
- Cheap public-snapshot replay matice:60PASS0.60s, následně68PASS0.77s a82PASS1.08s;
  jde o čisté replay nad skutečnými captured compiler facts, ne nový compiler běh.
  Zachovány všechny předchozí receipts/log/XML v `/workspace/kafka-retry-validation`.
- Nová souhrnná actual matice, full suite a finální independent review: NOT_RUN.
  GH CI NOT_RUN (volitelné dle T045 revize2); nejde o lokální PASS.

Official older3.2.0 API JAR/POM byly explicitně staženy přes inherited proxy/TLS
jen do nových Maven cache paths; SHA/license lock v `fixtures/kafka-retry-dlt`.
Nejde o package installation. Whole JAR hash je nutný:3.2.0 a3.3.2 mají stejné
RetryableTopic/DltHandler/KafkaListener class bytes. Žádné síťové auto-fetch při testu.

## Acceptance a kompatibilita

AC01: actual Java/K1 positive, dva groups, custom/error/unsupported API a async
boundaries; nové final cases pending. AC02: legacy graphs bez policy se čtou,
version fail-closed, v1/v2/v3 schema beze změny. AC03: exact public compiler/W04/
DLT/edge/proof/scope/hash a coherent-metadata tamper matrix, input immutability,
offline no-process/network. AC04: README/capability/acceptance/progress uvádějí
přesný bounded scope a historické/pending kontroly; žádné dokončení celého S07.

Zbývá final source closure, actual grouped focus, jedna frozen FIFO full sada,
sémantika/memory/scan/check a reviewed publication rootem. Autor tuto větev
nereviewuje ani nemerguje. Nestartovala se žádná aplikace ani broker.

## Udržitelnost připravené actual matice

Stávající compiler-workers job dostává pouze explicitní API-only3.2.0 fixture
POM s vyloučenými transitive dependencies a nový W05 test modul. Nevzniká nový
gate, instalace aplikace ani CI retry. Behaviorální mandatory-worker guard
ověřuje optional SKIP/required FAIL při chybějícím pinovaném API před compilerem.
Runtime source z checkpoint7c1b zůstává byte-exact; CI nebylo spuštěno.

## Koherentní malformed input před actual startem

Po CI-only checkpointf279 nalezen veřejný Graph input bez KafkaListener annotation,
se vzájemně přepočítanými Node/symbol/annotation/proof/policy hash: Graph validace
prošla, policy reader ale vyvolal IndexError. Oprava vyžaduje právě jednu skutečnou
listener annotation i při čistém replay a chybějící tuple lokalizuje jako UNKNOWN.
Vlastní čekající flock33797 byl ověřen bez potomka/pytest/logu a zrušen před startem;
nejde o provedený ani přerušený pytest. Nová koherentní public-snapshot regrese
pokrývá oba captured backend jazyky. Native workery zůstávají beze změny.

## Skupinový primitive-shape audit před opravným compiler během

Před novou actual frontou ověřeno20public Graph mutací (deset policy polí ×
list/dict): pouze origin_id list/dict odhalily TypeError v nechráněné membership
operaci. Oprava typuje selected method IDs a pouze pro UNKNOWN používá existující
selected retry edge jako locator. Neověřená edge nikdy neautorizuje DECLARED ani
nevybírá vítěze; zachovají se všechny relevantní neznámé alternativy. Neplatný
policy kind/metadata rovněž nezmizí. Žádná nová actual fronta ještě nebyla spuštěna.

Rozšířená čistá matice172PASS1.70s. První běh skončil58PASS1FAIL0.70s kvůli
příliš přísné nové assertion: původní legální reasons=[] zůstalo stejnou hodnotou,
nikoli korupcí. Opraven test, aby beze změny požadoval totožný validní výstup;
nejde o další product failure. Oba log/XML zůstaly zachované. Current actual/full
jsou stále NOT_RUN; předchozí schválení zdroje neznamená self-review této úpravy.

## Proof integrity před scope/context projekcí veřejného flow

Čistý public-flow audit odhalil pořadí filtrů: direct policy guard vracel UNKNOWN,
ale flow.process scope projekce odstranila foreign test-scope edge a znovu
reportovala DECLARED. Stejnou předprojekci prováděl CLI indexed. Oprava uchovává
celý explicitní graph pro policy proof replay, zatímco CFG dále omezuje stejný
scope a přesný context selector. Pouze CLI flow/process předává validovaný
selector interně; ostatní navigační příkazy se nemění. Nevzniká nový resolver,
store ani veřejný flag. Neplatná relevantní policy dává PARTIAL/UNKNOWN s
lokalizovanou diagnostikou; strict CLI vrací4. Unrelated policy zůstává platná.

Aktuální čistá captured matice178PASS0.74s včetně direct flow, CLI selector a
strict JSON cesty; nejde o compiler běh. Opravená actual fronta ještě nezačala.

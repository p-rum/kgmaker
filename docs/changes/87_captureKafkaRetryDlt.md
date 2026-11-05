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

## Canonical producer envelope, nikoli samotný self-hash

Normativní audit doložil, že přepočítaný policy logical alias/extra field/execution
nebo změněná W04 base metadata scope/owner/logical/revision mohla zůstat DECLARED.
Report nepřebíral falešné OBSERVED hodnoty, ale tuple nebyl přesný. Reader nyní
vyžaduje známá policy v1 pole a pevné static-status hodnoty, logickou identitu
od skutečného W04 listeneru, přesnou W04 base identitu/source/realm i uloženou
logical/revision. Neřeší znovu skupiny podle názvů či private properties a nevytváří
resolver. Legacy graph1/2 zůstává čitelný jako UNKNOWN policy, ne current proof.

Čistá captured/CLI/control matice215PASS0.91s. Actual12 a full stále NOT_RUN.
Zdroj je připraven k novému nezávislému closure; žádný autorův APPROVE se nevydává.

## Ověřený focused checkpoint a aktuální main — 2026-11-04

Nezávislý source reviewer resume_return schválil exact43a646f pro jeden opravený
coalesced focus. Běh skutečně proběhl FIFO s --maxfail=1: **361PASS/0SKIP102.17s**,
exit0. Zahrnuje všech12current actual Java/K1 případů (dvě explicit groups v
oddělených owner classes, supported3.3.2, custom handler, official3.2.0, source
shadow, ambiguous DLT a expressions), public-snapshot tamper/CLI/flow a existující
Kafka/trigger/control/mandatory regrese. HEAD před/po43a646f a všech1610source,
native/TS distribution, fixture/API/Python/JDK/Kotlin vstupů beze změny.
Receipts: `/workspace/kafka-retry-validation/guarded-focus-{pre,post,result}.json`
a `guarded-focus.log/xml`. Žádný native rebuild, app ani broker.

Mainf6a6355 (merged Kafka69 + prerequisite-only67) integrován do vlastní větve
v28f748c. Runtime/workers/fixtures/W05test/mandatoryguard/workflow jsou byte-exact
proti43a646f; pouze upstream prerequisite testy a metadata se změnily. Jejich
čistá regrese43PASS0.18s. Parent221implementation episodes zůstávají neměnný prefix.
Reviewer ověřil361JUnitIDs/0fail/error/skip a exact1610pre/post; schválil jeden
budoucí strict full po capacity gate a fresh final freeze, nikoli fullPASS/ready.

**Full NOT_RUN / BLOCKED:** preflight ověřil2.53GB free proti5368709120bytes
(5GiB). Žádná full fronta/pytest nezačala; nevydává se to za přerušený či zelený
full. Explicitní receipt `full-capacity-preflight.json` má tests0. Lokální focus
nenahrazuje povinný full. GH CI NOT_RUN, bez retry/externího zápisu. Draft není
ready ani dokončení celého W05/S07; zbývá připravený frozen full po uvolnění místa
a finální nezávislé review/publikace rootem.


## Current Return parent a nový coalesced focus — 2026-11-05

Po uvolnění kapacity původní full zůstal childless ve FIFO frontě. Před
jakoukoli preflight/test marker byl pouze vlastní čekající flock83895 zastaven,
ověřen bez potomků a ukončen. Receipt obsolete-queue-cancel-20261105.json má
tests0; tento full nebyl spuštěn ani přerušen jako pytest. Historická disková
blokace výše platila v daný čas, není současným výsledkem celého full.

Current main deb3691 (Return) integrován v463f662. Conflict union zachoval
Return block/component/evidence qualifiers a retry origin/compiler refs;
LocalOps→Return pořadí a full-graph policy validation před CFG scope/context
projekcí zůstaly. Workflow obsahuje return i retry modul. All27tracked worker
sources byly byte-exact proti explicitnímu Return donorovi4a4eaef;132JVM
JAR/lib/license souborů zkopírováno s donor pre/post a destination SHA, bez buildu.
Receipt current-return-donor-copy.json. Parent224episodes zůstaly neměnný prefix,
předchozí vlastní episode zachován; nová memory může přidat další vlastní historii.

Root nezávisle source-composition APPROVE exact463f662/base deb3691 pro JEDEN
current-parent focus. FIFO běh skutečně **470PASS/0SKIP186.44s** (runner187.34s),
exit0, XML0fail/0error, všech12actual Java/K1 scenarios. Zahrnuje Retry/Return/
Kafka/code/binding/trigger/CFG/protocol/mandatory matrix;1620source/distribution/
fixture/API/toolchain pre/post hashes beze změny, po běhu znovu ověřeny aktuální.
Receipts integrated-focus-{pre,post,result}.json, integrated-focus.log/xml
a12integrated-captures JSON. Runtime/native source checkpoint463f662 je pro
následující docs/semantic/memory finalization neměnný.

**Required full NOT_RUN**: po green focus čeká finální current-parent/source
closure a nový5GiB acquisition preflight + fresh all-input freeze. Žádný nový
full nebyl zařazen; předchozí361green zůstává historickým43a důkazem. GH CI
NOT_RUN, bez retry, externího zápisu, publication nebo merge. Není ready.

## Provider ambiguity parent před jediným full — 2026-11-05

Current main c193748 integrován před full. Proti841e8b4 mění runtime pouze cizí
schválený interfaces.py rule2 a jeho nový provider test; vlastní retry/flow/CLI/
inspection/workspace/native soubory zůstávají byte-exact470focus checkpointu.
Main226episodes je neměnný prefix +obě vlastníhistorické episodes=228. Žádný build.
Malý pure provider test:4PASS0.70s. První invocation omylem uvedla neexistující
název test_t010_provider_ambiguity.py:0tests/exit4; skutečný soubor je
 test_http_provider_ambiguity.py, opravený command/proof je uložen odděleně.
Required full zůstává NOT_RUN do nezávislého composition closure a fresh5GiB
preflight/freeze; žádný další470focus ani compiler matrix se neopakuje kvůli
nesouvisející pure provider změně.

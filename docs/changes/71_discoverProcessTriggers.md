# Inventář doložených spouštěčů T024

T024-S01–S05, AC01–AC06; závislosti T008/T023 jsou skutečně v main.
Původní stack30ce0cd/PR56 je integrován s merged main
`b78d2e62148f225be7ba8c53c839f8b052ee269d`.

## Problém a skutečné změny

Chyběl oddělený inventář trigger candidates nad existujícími framework fakty.
Čistý `process_triggers.discover_process_triggers` reuse T008 workspace/service
selection a T005/T009 ViewDocument/evidence. HTTP, Kafka a scheduler deklarace
mají entry symbol, owner, context, scope, original IDs a přesně svázanou source,
edge/proof tuple. Graph symbol se porovnává s canonical Node authority pouze
v identity/provenance polích; nesrovnává se obecná nested metadata.

Missing/ambiguous/unsupported CFG zachová kandidáta s explicitní body gap.
Neexistuje resolver procesu z názvu, parser anotací, CFG expansion, nový store,
network/worker execution ani nový CLI. API-only fixture pinne Spring6.2.2/Kafka3.3.2
JAR/POM/license hashes. CI explicitně připravuje tuto fixture před actual testy;
projekce/test preflight sama nic nefetchuje.

## Skutečné ověření a hranice

- RED chybějící module zaznamenán před implementací. Pure initial24/35/39 PASS
  jsou mezivýsledky, nikoli finální full.
- První actualK1/K2:2FAIL v21.23s kvůli draft požadavku na nesprávné context
  states a chybějící matching stdlib. Oprava přijímá pouze T006 current supported
  states BUILD_IMPORT/SYMBOL_RESOLVED a explicitně přidává stdlib vlastního workeru.
- Druhý actual grouped:2FAIL v16.85s odhalil skutečné hranice: K1 expression body
  má unlocated synthetic return; K2 nemá authoritative symbol annotations ani
  SOURCE CFG. Jeho starý framework fallback může připsat anotace pozdější ordinary
  metodě. Tyto hints se neakceptují a žádná upstream oprava není skryta v T024.
- Finální bounded module: **41 PASS v41.91s**, včetně skutečného K1/K2 capture,
  offline projection a canonical symbol/name/owner/descriptor/hash/scope/range,
  edge source/line/proof tuple a malformed CFG negatives. Log/XML:
  `/workspace/validation/t024/bounded-closure.log`, `bounded-closure.xml`.
- K1 genuine capture doloží HTTP/Kafka/scheduler typy, production/test hranici a
  žádnou source mutaci. HTTP candidate zůstává při UNAVAILABLE expression body;
  ostatní dvě mají doložený SOURCE CFG. K2 je skutečný negativní UNKNOWN případ,
  nikoli SKIP nebo tvrzení podpory. Async a název metody nejsou trigger proof.
- AC01/02: public distinct-type/owner test + actual K1 fixture. AC03/05: unsupported
  scheduler/K2, no CFG, stale/canonical/foreign evidence případy. AC04: input/store
  byte identity a subprocess/network zákaz, structured error pro malformed input.
  AC06: capability, README, acceptance/progress a tento note; full a release pending.

Current-main T024/T023/T008/T009/T015 focus je **199 PASS v47.71s**, včetně
actual K1/K2 T024 a T015, bez skips. Root early source closure APPROVE; required
full bude spuštěn právě jednou pod sdíleným flockem s --maxfail=1, nikoli předem
vykázán jako PASS. Semantic update/apply/validate a CLI scan/check PASS.
Původní worker receipt `artifact-provenance.json` platí pouze pro starý Ec source;
nový receipt `jpa-main-artifact-provenance.json` porovnává všech14 JVM tracked
source/build/lock files a identity obou JARů se skutečným build receipt
`/workspace/combined-jvm-main-ec/verified-results.json` pro sourcebdbe4ca.
K1e44e3dac a K2e2553425 artifacts se výslovně kopírují z own s06-jpa checkoutu,
nikoli ze stale process-model cache. Žádný nový build/fetch/install.
GH CI je dle T045 volitelné; jeho stav není vydáván za PASS.

## Kompatibilita a příklad

Viz [veřejné API](../process-triggers.md): explicitní workspace snapshot předává
`discover_process_triggers(workspace, graph, source_coverage=coverage)`.
Vrací shared process-kind ViewDocument s trigger nodes a bez process edges.
Graph/schema/store v1/v2/v3 a T023 zůstávají kompatibilní, migrace není potřeba.
Registration/execution/data availability jsou UNKNOWN, output nejvýše PARTIAL.
T025+ path projection, CLI/render/review/export ani celý T003/T004 nejsou dodány.

## Required frozen full (2026-11-03)

Checkpoint `3b24cc66ed70c269e43830181e7f50523c245b92` strict full je GREEN:
**812 PASS,10 optional SKIP v713.46s**, exit0. XML822 tests/0errors/0failures/
10skipped,713.440s. Mandatory WORKERS/K2/SPRING a vlastní worker/source home
byly zapnuté. Všech206 zmrazených source/test/fixture/JAR hashů zůstalo shodných.
Log/XML/status/manifest jsou `/workspace/validation/t024/full.log`, `full.xml`,
`full-status.json`, `full-frozen.json`. Skript `run-full.sh` bere jediný flock,
runner `run-full.py` ověřuje hashe před i po běhu a používá --maxfail=1.

10 SKIP jsou existující optional Maven/exporter/Gradle/Kotlin2.2.20 cache, druhý
JDK a native non-admin Windows gates; actual T024 K1/K2 nejsou přeskočené.
Jediná root-autorizovaná relokace vlastní neodstartované queue14138 byla ověřena
bez childů, ukončena exit143 a nahrazena jedinou queue2517; žádný běžící validní
full ani cizí proces se nerušil. Audit `queue-relocation.json`.

Durable test artifact673c1ef1d8955ccb44863cac628c9268e4e977b2feafbc37837c3f0f1dac3c1d
přesunul task do REVIEW. Current-main integrace, finální SHA-pair review a ready/
merge zatím neproběhly; Draft PR59 není automaticky schválen tímto full výsledkem.

## Current-parent integration after full

Integrated main `8b1eeceb28b71c122c2d48bf179e08cefa79c43c` includes merged
W02 inherited JPA, T010 HTTP, Factory registrations and typed condition rulesv6.
Own T024 runtime/tests/API fixture bytes remain exact full-tested3b24cc6.
Only workflow/docs/generated metadata conflicted; all parent API preparation and
test commands are retained together with T024. No worker/runtime conflict edit.

15 tracked JVM source/build/lock files match actual built Factory source0044123;
K1 JAR9b95d55d and K2d881ff22 plus all declared libraries match actual buildlogs
and successful28-case worker XML at `/workspace/factory-mainJpa-validation/`.
Explicit copy receipt `/workspace/validation/t024/current-main-worker-receipt.json`.

Current-parent pure inventory/query/model/conditions replay:231PASS11deselected
v4.31s; three source-only pure cases with actual in their name were subsequently
run explicitly:3PASS0.27s (pure-extra.xml). Actual T024 official K1/K2 fixture2PASS36.53s,
39unrelated deselected, no skips. All221 current integration input hashes stayed
unchanged. No second full or new build/install/fetch was run.

Main172 immutable episodes form the unchanged prefix plus the single validated
T024 capture. Final independent current-pair review, ready and merge remain pending.

Scoped semantic update/apply/validate and CLI scan/check PASS. The parent already
held the correct scanner function ID261; union initially retained obsolete child
ID251 as an extra edge. Validation rejected it and a duplicated attempted rebind;
neither invalid patch was applied. The final scoped patch omits only that obsolete
child duplicate, preserving the existing main261 relationship. All14 parent
concepts/47 edges remain byte-equivalent; final core15/48,172episode prefix+1=173.

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

Po review budou zaznamenány current-main integration, required full, semantic a
memory. Full zatím NEPROVEDEN a nefrontován; nejprve root early source closure.
Původní worker receipt `artifact-provenance.json` platí pouze pro starý Ec source;
po JPA main integraci se nesmí tvrdit aktuální toolchain proof bez nové provenance.
GH CI je dle T045 volitelné; jeho stav není vydáván za PASS.

## Kompatibilita a příklad

Viz [veřejné API](../process-triggers.md): explicitní workspace snapshot předává
`discover_process_triggers(workspace, graph, source_coverage=coverage)`.
Vrací shared process-kind ViewDocument s trigger nodes a bez process edges.
Graph/schema/store v1/v2/v3 a T023 zůstávají kompatibilní, migrace není potřeba.
Registration/execution/data availability jsou UNKNOWN, output nejvýše PARTIAL.
T025+ path projection, CLI/render/review/export ani celý T003/T004 nejsou dodány.

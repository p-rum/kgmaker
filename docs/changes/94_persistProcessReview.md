# T032 — explicitní lokální review a historie procesů

## Problém a rozsah

T031 validuje návrhy bez publikování. T032 přidá samostatný semantic review envelope,
explicitní APPROVE/REJECT a bounded immutable historii s POSIX cooperating-writer CAS.
Technický ProcessView, evidence a dokumentové citation domains se nesměšují.
T032-S01–S05, AC01–AC06; specifikace Rev2, explicitní stack T031 a359.

## Historický plán a počáteční kontroly

Při založení šlo pouze o plán/specifikaci, nikoli implementační PASS. Před alokací
ověřeny všechny lokální worktrees/main, registr a file lists všech7 otevřených PR:
maximum93 (T014), žádná94; koordinace integrate8 potvrzena2026-11-05.
Tehdejší T030/T031full byl samostatně zmrazen; další skutečné výsledky jsou níže.

## Implementovaný kontrakt a skutečné kontroly

Nový `process_store.py` používá T031 rederivation, oddělené dokumentové bindings,
verzovaný bounded envelope, immutable hash-chain, POSIX flock+thread lock a jeden
atomic replace. Explicitní lokální APPROVE blokuje CONFLICT, REJECT nemění dřívější
aktivní approval. Operation identity/CAS brání lost updates a retry rewrites.
NEEDS_REVALIDATION při změně explicitních podkladů nezmění historii. Viz
`../process-review-store.md` pro přesný Python příklad a privacy/platform limity.

Před implementací public RED6FAIL0.50s (chybějící API). Po implementaci36PASS1.93s;
meziběhy26PASS2FAIL (test fixture/source-ref order),35PASS1FAIL (test fixture ID key)
zachovány v durable logech; opraveny test fixtures, nikoli uvolněn kontrakt.
Coalesced feature+T030/T031+model/collapse/feature/provider/protocol269PASS94SKIP8.74s.
Skutečné multiprocessing i threading CAS testy měly jeden commit a jeden konflikt.
T032-AC01–05 viz acceptance inventory. Tehdejší full/review/publication byly NOT_RUN.
Žádný native build, T034 CLI, technické apply, autentizace nebo power-loss slib.

## Finální current-main a actual descendant proof

Base main `2c7b38ea2dc7b5ad08009eefa276c4dc41a5b1a9` obsahuje merged T030/T031
a Common/T012/T013/W07. Celý process_store.py a T032testfile jsou byte-exact
actual `2df55ff8d15d790808f6a81072144eeb408a05b8` i původnímureviewedf2e962e.
Currentprocess_semantics.py se nemění a je také whole-fileexactactual.

ONEcombined strict full na2df:2587PASS10přesněpovolených optionalSKIP,2042.93sJUnit;
2597výsledků,4897hashů a5recursive memberinventories beze změny, Root+architect
nezávisle ověřili. Není to standaloneT032full. Všech36vlastních cases je XMLPASS,
včetně skutečného process/thread CAS, cancellation a postreplaceINDETERMINATE.
Originální2102parentIDs2092PASS10SKIP; aktuální2328main+36own dává2364source/IDunion,
všech2354PASS10stejnýchSKIP v témžeactual2df. Union není nový test/collection/run.

[Bounded proof/statusy/SHA](../validation/t032-descendant-proof.json). Main241
episodeprefix a všechny staré captureobjekty zachovány. Žádný nový nativebuild,
test/fullrepeat, technické apply či autentizace; GHCI optional/neověřeno. Finální
independent exactpairreview/Rootready/merge samostatně pending. Windows writes
zůstávají UNSUPPORTED,128history/2MiB hardfailbezprune; postreplacefailure není
nepravdivý rollback. Původní RED a chybové/setup/capacityreceipts se nepřepisují.

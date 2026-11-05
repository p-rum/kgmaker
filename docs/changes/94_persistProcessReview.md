# T032 — explicitní lokální review a historie procesů

## Problém a rozsah

T031 validuje návrhy bez publikování. T032 přidá samostatný semantic review envelope,
explicitní APPROVE/REJECT a bounded immutable historii s POSIX cooperating-writer CAS.
Technický ProcessView, evidence a dokumentové citation domains se nesměšují.
T032-S01–S05, AC01–AC06; specifikace Rev2, explicitní stack T031 a359.

## Stav a kontroly

Pouze plán/specifikace; implementace ani PASS zatím nejsou doloženy. Před alokací
ověřeny všechny lokální worktrees/main, registr a file lists všech7 otevřených PR:
maximum93 (T014), žádná94; koordinace integrate8 potvrzena2026-11-05.
Budoucí konkrétní testy/výsledky, kompatibilita a příklad budou doplněny po běhu.
Full T030/T031 je nezávisle zmrazen; T032 nemá build/full/PR/merge autorizaci.

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
T032-AC01–05 viz acceptance inventory. Full, nezávislé review a publication NOT_RUN.
Žádný native build, T034 CLI, technické apply, autentizace nebo power-loss slib.

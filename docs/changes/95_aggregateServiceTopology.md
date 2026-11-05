# T016 — bounded service/resource/channel topology

Root approved brief a explicitní T01409/W075b39 stack, main3bef integrován před
capture. Revize2 stanovuje jedinou explicitní capture fázi a pure aggregate přes
stejné upstream objekty. Nezávislý architect preferoval konkrétní B handoff.
Note95 přidělen po ALLworktree/main/registry (max94), openPR filelist kontrole a
potvrzení resume_return: T032 používá94,95nerezervuje.

T016-S01–05/AC01–06 implementace a publicRED zatím PENDING. Žádný nový native
build/heavyqueue. T013/W07/T014 actual/full, current-main closure, independent
source review a requiredfull zůstávají NOT_RUN/PENDING; žádná readiness deklarace.

## Implementační source checkpoint

Nový service_topology.py má explicit capture_topology_inputs a pure
aggregate_service_topology, bez změny T014/T015/W07/native producentů.
Integrován main3bef jako8d98ce2 před capture, zachován main227episode prefix
plus všechny child objects (230total); generated graphs obnoveny CLI scan.
Inherited stale semantic citations jsou přiznané a final scoped repair/memory
čeká na current dependency integration, nejde o hotové metadata/readiness.

PublicRED2FAIL0.84s: nová API absent. První pure22PASS0.37s; realpubliccommon
capture positive23PASS0.90s používá skutečný workspace/contract/source fixture
a existing snapshot/projectors, žádný compiler/build. Testy dalších source/
schema/manifest změn po remote fázi skutečně zapisují jen svoje dočasné fixtures
a capture je odmítá. Hand-labelled compatibility fixtures nejsou compiler proof.

Coalescedpure170PASS10actualDESELECTED2.24s; finální scope-hardening checkpoint
**172PASS0SKIP10actualDESELECTED0.97s**, pure-checkpoint.xml. T01424case/W07pure/View/T009 jsou
zahrnuté. Per-resource polarity se nepřevádí na remote proof, UNKNOWN a upstream
truncation se nezvedá, foreign scope se nepřepisuje.

Root vyžaduje final current T013b2e0477/T012613bef integration až po ukončení
jejich validního frozen full. Source checkpoint je přípravný, nikoli final full
freeze. ALLparent collected-ID/runtime/test/native/superset ledger se musí na
finálním descendantSHA znovu ověřit. Žádný heavy/actual/full/native job se zde
nespustil; W07 actual capture replay počká na jeho terminal receipt/source review.

## Root source review feedback — explicit coverage equality

Root REQUEST_CHANGES nad262640f prokázal P2: validní hash format sám neověřoval
rovnost input_binding.coverage_fingerprint a remote_selection.source_coverage_fingerprint,
ačkoli oba vznikají digestem téhož coverage objektu. Recomputed outer/shared
hashes mohly zachovat vnitřní rozpor. Nešlo o autentizaci koherentně cizího vstupu.

Public RED **1FAIL1PASS37DESELECTED0.19s** přesně zopakoval rozdílné explicitní
coverage hashes. Hand-labelled specimen nyní používá actual W07 coverageNone hash;
mock capture používající schemas={} váže právě tento objekt i ve W07 handoffu.
Guard se neoslabuje: capture i pure consumer vyžadují exact equality před projekcí.
Coalesced correction **174PASS10actualDESELECTED1.58s**; následný nový explicitní
capture-before-projector regression spolu s oběma coverage cases **3PASS37DESELECTED**
(coverage-capture-green.xml). Žádný native/heavy/full run. Root independent
re-review nad opraveným SHA zůstává samostatný gate.

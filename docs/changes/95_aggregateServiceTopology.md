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

## Root actual upstream owner contract feedback

Root REQUEST_CHANGES P1 nadf05: T012 Kafka emit používá plain service owner_id,
ale catalog service IDs mají prefix service:. Původní qualified hand-labelled
fixtures chybu zakrývaly a canonical Kafka skončila bez channelu jako ownerUNKNOWN.
Public realistický plain-owner RED **1FAIL1PASS44DESELECTED0.31s**, HTTP qualified
control zůstal green. Upstream API se nemění.

Oprava bere source/target release před owner kontrolou. Catalog ID vzniká jen
z explicitního selected release.service_id; origin endpoint musí mít přesně
release.interface_id a owner přesně plain service_id nebo jeho catalog ID.
Cizí/částečně podobná/prefixová či opačná service nezíská fallback; žádné parsing
ID/label/name inference. Public plain Kafka pozitivní, qualified HTTP kontrola
a4foreign owner negatives jsou zahrnuté. Coalesced **181PASS0SKIP10actualDESELECTED
1.36s**, plain-owner-green.xml. Saved actual W07 capture replay počká na opravený
upstream terminal/source receipt; tento pure běh se za něj nevydává.
Root independent re-review a finaldependency/current-main/full dál pending.

## Currentec6a127 parent a accepted-descendant evidence

T016806ccf1 source approved Root po obou coverage/plain-owner opravách. Refresh
na verified main ec6a127857cc47704316e6a1d5a088be9e4b16e7 zachovává T014/T015/
Common/T012/T013/W07v2/process moduly a current CI. Vlastní service_topology.py
a test jsou byte-exact accepted2df55ff8d15d790808f6a81072144eeb408a05b8.
Accepted ONEfull:2587PASS10allowedSKIP, XML2042.878s/runner2048.01s;4897 hashes
a recursive member sets unchanged. Všech46own cases XMLPASS. Historické pending
source-only stavy výše se netvrdí jako aktuální acceptance.

Collection-only currentmain2425+46own=2471 ID, všechny v acceptedfull;
2461PASS10stejných optionalSKIP. Žádný nový actual/full/build ani cache/tool mutation.
Všech296 present src/test/worker/fixture/CI souborů porovnáno:295exact2df a jen
currentMain cli.py bez budoucího T0195line dispatch, správně zachovaný. 27native
worker a9preparedfixture source hashes exact původní Return079; není freshbuildclaim.

Main244episode prefix +allold230child objects zachovány;1owncapture=245. Currentmain
semantic fact keys zachovány.1starý doložený Common role concept+4facts se zachová
s aktuální doc298citací;3obsolete workspace/JPA codeIDs jsou již zastoupené správně
rebound currentmain edges, nevytvářejí se stalealiases. Scoped semantic apply/validate,
memory a scan/check CLI regenerují graph. Finální nezávislé currentbase/head review
a Root merge zůstává gate. GHCIbilling/cascade optional/unverified, nePASS.
Viz docs/validation/t016-descendant-proof.json. T020/21 nejsou v acceptedfull.

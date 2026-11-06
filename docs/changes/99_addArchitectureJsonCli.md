# T019 — read-only architecture JSON CLI

## Problém a změny

Chyběl veřejný JSON adaptér pro existující pohledy. T019-S01–S05 / AC01–AC05
přidává snapshot-only interfaces/topology/explain, verzovaný interface bundle1,
přesný T017 envelope, selector assertions a oddělený T018 source-status handoff.
Opt-in capture-local nejprve kontroluje všechny původní indexy a nepublikuje cache.
Bez worker/build/model/runtime operací; legacy CLI zachováno. Revize2 a schválený
brief předcházely implementaci na explicitním T018299 stacku. Note99 po kontrole
registru/main/ALLworktrees/openPR a koordinaci T03396/T01797/T01898.

## Skutečné kontroly

Public absent-CLI RED: 3 FAIL. Po implementaci initial-green 2 PASS / 1 FAIL:
test fixture přiřazovala seřazené role pozičně; opravena podle publikované role,
bez oslabení runtime guardu. Rozšířený pure běh 27 PASS. Předběžný focus
306 PASS / 11 DESELECTED obsahoval jeden omylem vyřazený pure test kvůli názvu
actual_selection; přejmenován a zahrnut do konečného běhu. Konečný coalesced
source-focus: **307 PASS, 0 SKIP, 10 actual DESELECTED, 5.29s**; XML/log pod
/workspace/t019-validation/source-focus.*. Subprocess jsou pouze CLI harnessy;
temporary-file source/parser capture není compiler/application run.

## Příklad a zbývající práce

`kgmaker architecture topology --capture-snapshot topology-inputs.json --strict`
vrátí celý envelope a exit4 pro validní partial. JSON stdout, fixed diagnostics
stderr; neplatné vstupy2, explicit conflict3, cancel130, broken pipe141.
Viz [kontrakt](../architecture-json-cli.md). Závislosti/current-main composition,
actual saved-capture replay, ALL-ID/native closure, semantic/memory finalizace,
nezávislé source/final review a required descendant full zůstávají PENDING.
Žádný vlastní heavy/native/full queue ani tvrzení o full PASS na tomto SHA.

## Current1005b9f final integration a accepted-descendant proof

Root původní nezávislé SOURCE_APPROVE přesného abad2e30c1a1e422392585e6073995568b82a564
se týká stejného architecture_cli.py +5CLI registration/dispatch lines +34testů.
Refresh na main1005b9f950102d2d5fd0e74735bc0577c2e30c0b zachovává T014/T016/T017/
T018/Common/T012/T013/W07/process a current CI. Vlastní source/tests +celý global
cli.py jsou byte-exact accepted2df55ff8d15d790808f6a81072144eeb408a05b8.

Collection-only2563mergedparent+34own=2597 přesných ID; set je PŘESNĚ CELÝ accepted
full set, bez missing/extra,2587PASS10stejných optionalSKIP. Accepted ONEfull XML
2042.878s/runner2048.01s,4897hashes+recursive member sets unchanged; všech34own
XMLPASS. Není to nový fullrun na tomto head. Všech302present src/test/worker/fixture/
CI files exact2df, nyní BEZ cli.py výjimky. 27worker a9preparedfixture source inputs
exactReturn079; žádný freshbuildclaim.

Main247immutableepisode prefix+all230oldchild objects zachovány,+1scopedcapture=248.
Mainsemanticfactkeys zachovány; freshscopedsemantic/memory/scan/check přes CLI.
Current exactbase/head nezávislé review a Root merge nadále gate. GHCIbilling/
cascade optional/unverified, nePASS. Žádný actual/full/build/tool/cache mutation;
W03active56807/globaltoolsfrozen nedotčeny. T020/T021/T022 se sem nepřidávají;
jejich jointstaging/full je samostatný. Viz docs/validation/t019-descendant-proof.json.

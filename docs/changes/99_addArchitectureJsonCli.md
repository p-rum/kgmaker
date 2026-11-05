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

# T017 — Omezený výběr již sestavené topologie

## Problém a plánovaný kontrakt

Velká topologie potřebuje deterministický focus, směr, hops a node budget s úplným
seznamem odříznutých vazeb. Odstranění prostředního uzlu nesmí vytvořit novou vazbu
a vynechání alternativy nesmí změnit AMBIGUOUS na RESOLVED.

T017 revize 2 a nezávislý architektonický brief byly připraveny před kódem.
Explicitní pracovní base je source-approved T016 `f05b13b`; jeho vlastní dependency,
current-main a full acceptance zůstávají povinné. Číslo 97 bylo přiděleno po kontrole
66 worktrees, main, registru a všech 7 otevřených PR; 93/95 patří T014/T016,
94/96 T032/T033. Identita procesů ani názvy existujících funkcí se nepřejmenovávají.

## Stav a skutečné kontroly

- Public absent-API RED: 2 FAIL, 0.09s. První dvě behavior kontroly po implementaci PASS.
- Rozšířená sada zachytila privacy chybu: retained origin-interface credential ID
  nebylo odmítnuto (1 FAIL /29 PASS,0.31s). Oprava validuje expansion inventory
  všech vstupních claimů, nikoli pouze vynechaných. Původní neúspěšné XML zůstává.
- Finální vlastní sada má 33 cases; společně T017/T016/T014/View/T009 **149 PASS**
  za1.58s, 0 SKIP/FAIL/ERROR. Cykly, star/channel, scope/context, provenance,
  metadata bounds, Unicode, immutability a no-I/O mají veřejné behavioral testy.
- Baseline scan proběhl přes CLI; zděděné stale semantic citations jsou výslovně
  hlášené a budou opraveny scoped semantic update, bez ručních úprav GRAPH.
- Memory recall a durable analyze/plan proběhly před implementací. Žádný worker, build, instalace,
  full ani GH CI nebyly tímto úkolem spuštěny.
- T017-AC01–06 jsou namapované v acceptance inventory; API/příklad je v
  `docs/topology-filter.md` a README. Source checkpoint není final acceptance T004.

## Kompatibilita a zbývající práce

Rozhraní je aditivní čistá projekce existujícího ViewDocument; graph/store
v1/v2/v3 a upstream IDs se nemění. Technické důkazy a runtime/data availability
zůstávají oddělené. Zbývá doložený required full,
finální dependency/main integrace, semantic/memory a nezávislé review aktuálního SHA.

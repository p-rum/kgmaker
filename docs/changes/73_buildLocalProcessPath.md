# Lokální technický průběh od doloženého triggeru

T025-S01–S05, AC01–AC06. Větev feat/t025-build-local-process-path, explicit stack
nad Draft PR59, přesný head `3b24cc66ed70c269e43830181e7f50523c245b92`.
T024 zatím není merged; T025 nesmí předběhnout jeho validation/review/merge.
S04 se reuse pouze v již skutečně ověřeném Javac/K1 SOURCE CFG subsetu; pending
coroutine PR37 není prohlášen za merged ani podmínkou nové nepodložené podpory.

## Problém a skutečné změny

`flow.process` kopíroval celý root CFG před budget kontrolou, která platila pouze
pro callees. Překročený root nyní dostane jednu explicitní node-limit boundary.
Není nový CFG builder ani nebezpečné spojení vybraných protilehlých větví.

Nový čistý `process_paths.build_local_process` reuse T024 trigger inventory,
existující flow.process traversal a T023 typed ProcessView. Kontroluje vybranou
canonical declaration/endpoint, context/scope/source hash a originální trigger
edge/proof. Source CFG musí mít shodný method/context/source witness. Obě vazby
caller→site declares_call i site→declared target resolves_to vyžadují odpovídající
edge/proof/current context/hash/range. Neřeší se nový dispatch či heap resolver.

Trigger má explicitní caller-selected process_id/revision; nevzniká business
identita z názvu metody. Branch/exception/return/loop/original IDs a call-site
boundaries zůstávají zachovány. Chybějící body se neodhaduje. Async annotation
hint a suspend call jsou unsupported boundaries, ne tvrzení runtime scheduling.

Current compiler call-site Node obsahuje invocation kind v canonical labelu,
ale nemá nezávislé receiver/dispatch-complete metadata. Takové virtual/interface
calls zůstávají boundary i při změně příznaku v site table. Private-static/top-level
actual positive paths expandují. T025 neprohlašuje opravu upstream receiver proof.

## Ověření a acceptance

- Architecture brief nezávisle ověřil root; durable task
  `task:f182777423915d588b431f809fcbdf59c72c59ae98ba18886cad8f8f08d5de36`
  má analyze/plan před kódem a bounded role packets; memory recall skutečně proběhl.
- RED: nový public module chyběl, collection ModuleNotFoundError; log
  `/workspace/validation/t025/red.log`. První pure implementace14PASS/1FAIL
  měla ve fixture nesprávně očekávané condition labels; zachovány skutečné labels.
- První skutečný Javac fixture selhal po5.12s: adapter chybně očekával relation
  invokes, skutečný graph má declares_call. Captured provider replay doložil
  proof-unavailable boundaries; opravila se vazba v adapteru i fixture, nikoli
  rozšíření recursion assertion. Následný combined25PASS18.71s zahrnul actualJavac/K1.
- Zesílený actual/pure/CFG focus:41PASS9.43s. Actual ověřuje expanded
  entry/left/right/nested methods, returns_to a nulovou left↔right cestu;
  mutated target→other real method, complete/receiver/invocation flags se nepromují.
- Po source-file scope a primitive-shape guardech pure/T023/CFG focus:
  **112 PASS,2 actual deselected v2.16s**, bez skips. Finální actual a celý full
  budou zapsány až po dokončení; full se nefrontuje před root source closure.
- AC01: `test_ac01_diamond_never_joins_opposite_branches` +actual fixture.
  AC02: call boundaries +actual mutations; AC03: root overflow a budget1/2/3.
  AC04/05: exact proof/scope/hash/CFG/site negatives, inputs/store bytes,
  legacyv1/v2 remain readable and cannot acquire compiler proof.
- Vlastní trusted workers jsou kopie po porovnání25 tracked worker source/lock
  souborů s frozen T024. Receipt `/workspace/validation/t025/artifact-provenance.json`
  odkazuje na skutečné build source/JAR identity; žádný nový build/fetch/install.
  Pinned API-only T024 fixture je reuse, CI explicitní preparation zachována.

## Kompatibilita, příklad a zbývající práce

Viz [API](../process-paths.md). `build_local_process(graph, trigger_inventory,
trigger_id, process_id="process:explicit", max_nodes=200)` vrací T023 ProcessView.
Žádný nový CLI/render/apply/store; graph/store v1/v2/v3 decoding se nemění.
Existing flow process report má stále schema1, oversized root vrací PARTIAL
s explicitní boundary/truncated. Žádná migrace není potřeba.

Projection validuje dodané content-bound vztahy, ne physical checkout freshness,
a neautentizuje JSON claims. Current provider input zůstává odpovědností calleru.
Technical status nejvýše PARTIAL, trigger→body association UNKNOWN, žádná observed
execution/data availability/business equivalence. Semantic overlay je prázdný.
T026+ grouping, cross-service/business/report/catalog/CLI nejsou dodány.

Semantic/memory refresh, required full, final exact-pair review a publikace zatím
pending. GH CI je dle T045 volitelné, jiné povinné kontroly tím nahrazeny nejsou.

## Early source-closure checkpoint

Finální bounded pre-review focus vlastního T025 modulu + existující CFG testy:
**45 PASS v12.51s**, včetně actualJavac/K1 a všech nových scope/proof/legacy
negativních případů. XML/log `/workspace/validation/t025/pre-review.xml`,
`pre-review.log`. Semantic/memory a full zůstávají pending; tohle není ready PR.

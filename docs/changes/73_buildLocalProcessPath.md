# Lokální technický průběh od doloženého triggeru

T025-S01–S05, AC01–AC06. Větev feat/t025-build-local-process-path, explicit stack
nad Draft PR59, přesný head `3b24cc66ed70c269e43830181e7f50523c245b92`.
Při zahájení byl T024 pending; nyní je PR59 merged a je převzat v current parentu.
T025 nepředběhl jeho validation/review/merge.
S04 se reuse pouze v již skutečně ověřeném Javac/K1 SOURCE CFG subsetu; coroutine PR37 je nyní součástí current parentu; scheduling/runtime podpory se
tím nedeklarují.

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

## Nezávislé root review: dvě opravené skupiny nálezů

Před full root našel traceability chybu: expanded returns_to/exception edges
neměly čitelnou original call-site vazbu. flow.process nyní taguje call, returns_to
a exception hranice call_site i original ID; typed adapter uchovává tuto vazbu
v attributes/original_ids a přidává pouze skutečně admitted declares_call a
resolves_to proof provenance, se zachováním kind/polarity. Public i actual Javac/K1
fixture mají dvě různá místa volající stejný callee; roundtrip ověřuje každou
call/return/exception vazbu a její dvě původní proof IDs zvlášť.

Root dále reprodukoval P1: pro nepodchycený callee mohly chybějící hash hodnoty
porovnáním None==None vytvořit CURRENT syntax body. Nový shared source-checksum
guard vyžaduje skutečnou membership v graph.files i selected context.source_files,
platný lower-hex64 nonempty hash a totožný symbol/proof hash, také pro site caller.
Callee CFG musí vlastnit canonical method/function/constructor a source file scope.
Missing/None/malformed/uppercase hash nevytváří body a input bytes se nemění.

Skupinový RED: **4 FAIL,1 PASS** v0.48s (`root-review-red.log`), potom pure
T025/T023/CFG **117 PASS,2 actual deselected v1.69s**. Finální corrected vlastní
module + CFG focus: **50 PASS v14.36s**, bez skips, včetně actual Javac/K1 a
obou nových regresních skupin. XML/log `review-corrected.xml`/`.log` v persistent
`/workspace/validation/t025`. Předchozí45/41/25 výsledky jsou historické checkpoints.
Full zatím nebyl spuštěn ani queued; vyžaduje nové root source closure.

## Known-invalid full a oprava finally clone identity

Další read-only public a genuine Javac fixture odhalily stejnou lexikální
cleanup call-site ve třech strukturálních finally continuations (return/throw).
Traversal prefix pouze podle site ID sdílel jediný callee subtree a vytvořil
DUPLICATE_EDGE_ID v jinak validním ProcessView. Root výslovně autorizoval
ukončení pouze tohoto nyní known-invalid full; nešlo o neúspěšný pytest test
ani dokončený full PASS.

SIGINT dostal jen vlastní pytest100647; jeho java worker108978 se vyčistil a
celý známý subtree byl ověřen jako ukončený před source editací. Partial výsledek:
**186 PASS,2 SKIP v367.54s**, exit2 KeyboardInterrupt; XML188tests/0errors/0failures/
2skipped. Všech212 source/prerequisite hashů i HEAD39044a1 zůstalo shodných.
Log/XML/status/manifest/start/preflight byly uchovány jako
`/workspace/validation/t025/interrupted-finally-39044a1-*`; procesní audit
`interrupted-finally-processes.json`. Žádný cizí proces/queue se nerušil.

Localized fix rozlišuje callee clone pomocí původního site ID a strukturálního
caller CFG block ID. Nezavádí nový CFG builder nebo novou source identitu;
původní site/AST/method IDs se zachovávají, odvozené process clone IDs se opravují.
Expanded call/return/exception edges navíc uchovají caller_block a origin reference.
Public i actual Javac/K1 finally fixture ověřují samostatné callee entry IDs,
exact normal/exception continuation, unikátní edge IDs, roundtrip a node limits.

Nový RED měl1FAIL (valid finally input), corrected pureT023/CFG118PASS2actualdeselected
v5.91s; vlastní module+CFG actual focus **51PASS v21.35s**, bez skips.
`finally-red.log`, `finally-pure.xml`, `finally-corrected.xml` jsou persistent.
Nový current-parent source checkpoint musí projít root closure před corrected full.

## Current-parent před corrected full

Před corrected full je integrován main355e98fe2ab62fadbf4869eb4485cd3562173068
(T024 merged, corpus, XMLcapturev2/JPA rulesv5 a conditionsv6, reviewed coroutine
SOURCE CFGv2). T025 flow/adapter/test source je přesně opravenýe85c225; žádný
ručně řešený runtime konflikt. Source CFG musí odpovídat aktuálnímu imported
VERSION; starší unsupported body zůstane opaque, schema v1/v2/v3 decoding se nemění.

15 JVM source/build/lock hashes a všechny kopírované libraries odpovídají skutečnému
Coro/Factory build receipt a actual48 XML; K1 SHA714e2523/K2ad8cab7a. Explicit copy
receipt `/workspace/validation/t025/current-parent-worker-receipt.json`. No newbuild
install/fetch. První current-parent focus před test body ERRORoval kvůli ENOSPC;
nešlo o correctnessFAIL. Odstraněny pouze moje dokončené disposable full-temp
adresáře, logs/XML/status/source manifests a skutečný finallyrepro zachovány.
Current parent focus je nyní **120PASS v8.02s**, bez skips, včetně actualJavac/K1
finally/two-site/diamond/recursion/budget a T023/CFG/context fixtures; XMLcurrent355.xml.

Všechny parent facts se zachovávají, unie přidává pouze vlastní nový concept a
vazbu T025 oproti explicitnímu stack baseline. Parent187 immutable episodes jsou
beze změny; vlastní validated implementation capture bude přidána po full.
Root musí uzavřít tento nový source checkpoint před corrected full.

## Current HTTP parent před freeze

Final composition nyní používá main75d448ee7791cffb3dc9f4cceff5136402a8f5e0
(merged HTTP execution intent PR49). Flow runtime se spojil automaticky: zachovává
T025 rootbudget, async/coroutine/unknown-site guards i finally prefix(site,callerblock)
a všechny call/return/exception origin/proof fields. Parent přidává pouze HTTP
request inventory sidecar omezený na expanded_methods a jeho markdown output;
žádný reason/prefix konflikt se ručně nepřepisoval. Inspection typed optional IR
validation, URI privacy, HTTPcontext/cache tokens a publikace byly převzaty přesně
z parenta, bez vlastní změny nebo druhého parseru.

Všech15 tracked JVM source/build/lock souborů +2 JARy a declared libraries
odpovídají skutečným HTTP fresh buildlogům, frozen manifestu a successful153
actual XML +3 current-parent cases. K1 SHA50cf8376/K22eb240a5; explicit copy receipt
`/workspace/validation/t025/http-parent-worker-receipt.json`. Žádný nový build.

Jediný combined current-parent focus: **127PASS v40.01s**, bez skips; zahrnuje
vlastní actualJavac/K1 finally/clone/diamond/two-site/budget, T023/CFG, skutečný
HTTP Feign process-inventory boundary a cold/subscribed distinction, provider
privacy/legacy regressions. XML/log `/workspace/validation/t025/http-parent.xml`
a `.log`. Input source/test/worker tree zůstal po běhu beze změny.

Parent191 immutable episodes jsou beze změny, vlastní semantic delta je jen
jeden nový concept a jedna source-bound vazba. Corrected full se nesmí spustit
před root final source closure tohoto current-parent checkpointu.

## Dokončený corrected full a UI parent

Root source closure schválila exact5668659403cdfdea9e8f5d4e8865f3310d16c676/base75.
Jeden corrected strict full dokončen: **1104 PASS,10 optional SKIP,1273.70s,exit0**.
XML `/workspace/validation/t025/full.xml` obsahuje1114tests/0errors/0failures.
`full-status.json` potvrzuje unchanged246 frozen inputs i exactHEAD; nezávislé
post-run porovnání prošlo. Starší interrupted186/2/exit2 zůstává historicky neúspěšný
full gate a není započítán jako PASS. Dokončený vlastní disposable full-temp byl
odstraněn až po ověření proof; log/XML/manifests a repro zůstávají zachovány.

Následná kompozice main081d69ca69d14b4d131cc305e4e5c873960e71a3 přebírá UI event
versioning. Vlastní flow.py/process_paths.py a T025 test jsou byte-exact full566;
JVM sources/build/locks se tím nemění. Bounded pure parent focus **130 PASS,
2 actual deselected,2.12s**, XML `/workspace/validation/t025/ui-parent-pure.xml`.
Nový full se kvůli tomuto parentu neopakuje. Parent195 immutable episodes jsou
zachovány; konečný review/merge zůstává samostatný exact-pair gate.

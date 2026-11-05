# 91 — Plán explicitního cross-service contract/release mappingu

Datum 2026-11-05. T003-S07-W07 revize2, AC01–04. Předimplementační checkpoint.

## Problém a skutečná změna

Workspace artifact release_mapping nedokládá API/deployment kompatibilitu. URL,
schema title ani DTO name nesmí spojit služby. Tato změna je pouze specifikace a
registr: oddělený remote_mapping v1, explicitní bounded capture a pure resolver nad
existujícími upstream interface/contract/proof vstupy. Runtime/API a testy nejsou
implementované.

Isolated branch feat/t003-s07-07-cross-service-contract-mapping má explicitní base
T013 f43c9e08096887ca216df4a4d1ebceee1ca0e98e, včetně T012 8f76e5e/common a65c195.
Upstream source approval pro focus není full/merge readiness. T014 je downstream.

Revize2 navrhuje strict service/interface/context/scope/contract/release records,
exact default a explicitní směrovou compatibility pair. HTTP declaration/execution/
request-response se nemění na Kafka publish/subscribe ani runtime/delivery proof.
Payload zůstává UNKNOWN. Artifact release_mapping a Graph1/2/3 jsou beze změny;
žádný nový store/context/discovery/model. Např. dvě služby se stejným GET /orders
zůstanou unresolved bez explicitní authority; jiný SHA není kompatibilní jen podle
stejného version labelu. Více oprávněných targets zachová candidate set.

## Provedené a neprovedené kontroly

- Read-only architect source/graph/query recon main deb3691 a T012/T013.
- Registry/main/worktree poznámky: 87,88,89 existují, 90 rezervováno T030; 91 nebylo
  obsazeno. Connector open-PR search vrátil prázdnou množinu, nikoli záruku budoucí
  absence kolize; před publikací je povinná nová kontrola.
- Nový worktree neměl private graph: status/recall nejprve no readable graph.
  Default scan obnovil index a recall; scan hlásí inherited stale README semantic
  evidence a 5 vztahů. Žádné immutable fakta ani generated grafy se neupravují ručně.
  Scoped semantic oprava bude součástí následné implementace, ne zdejšího plánu.
- Durable workflow analyze/plan, konkrétní proposed schema/API a RED matice.
- Public pure acceptance RED: 1 FAIL / 0.46s po validním T013 contract attachment setup,
  chybějící W07 API; nejde o setup ERROR. Actual capture RED je připraven a NOT_RUN.
- Runtime implementace, actual RED, focused/full, native build, remote publikace,
  model API a merge: **NOT_RUN**. Tento checkpoint není completion ani ready.

Zbývá review plánu, skutečné public/actual failing acceptance, implementace,
nezávislé source review, focus/full a final docs/semantic/memory. Nic zde nezvyšuje
availability ani prokázaný jazykový/backend rozsah.


## První runtime source checkpoint (před actual matrix)

Root schválil refined capture schema/plan. Ověřené FIFO actual RED na4c7bc98:
**2 očekávané FAIL,3DESELECTED10.30s**, runner11.02s; obě real Kafka/HTTP setup
proběhla a uložila public graph před missingAPI assertion.1374pre/post hashů
beze změny, žádný ERROR/native build. Receipts /workspace/remote-contract-proof/
actual-red.{log,xml},actual-red-receipt.json a actual-captures/{kafka,http}.json.

Přidán remote_mapping.py a jediný aditivní manifest loader hook + dataflow pure
API wrapper. Capture provádí upstream I/O/replay, resolver výhradně porovnává
explicitní in-memory canonical handoff. Summary vynechá raw schema payloady a váže
původní capture hash; canonical source validace zůstávají upstream. HTTP client
expectation je explicitní deklarace, ne odvozený payload type. Známý method/path
se nesmí přepsat očekáváním. Žádný T013/common/native source změněn.

První pure run26PASS1FAIL0.30s odhalil chybu nového testu: test předpokládal
index0 canonical docs jako provider, ale stabilně se řadí consumer před provider.
Opraven test na explicitní node selector; žádná runtime chyba maskována.
Následující combined86PASS/4DESELECTED4.41s; current101PASS/8actualDESELECTED5.69s
(T013/workspace+W07 pure). Hand-labelled trusted protocol handoff testuje matching
pravidla, není důkazem compiler producerů či autentizace libovolného JSON.

Aktuální actual positive HTTP/Kafka a negative matrix jsou připravené, NOT_RUN
před nezávislou source closure. Kotlin HTTP upstream typed proof je UNKNOWN a
actual test to musí zachovat. Full NOT_RUN, žádný nový native build/remote write.

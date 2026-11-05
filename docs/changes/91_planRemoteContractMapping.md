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
- Runtime implementace, actual RED, focused/full, native build, remote publikace,
  model API a merge: **NOT_RUN**. Tento checkpoint není completion ani ready.

Zbývá review plánu, skutečné public/actual failing acceptance, implementace,
nezávislé source review, focus/full a final docs/semantic/memory. Nic zde nezvyšuje
availability ani prokázaný jazykový/backend rozsah.

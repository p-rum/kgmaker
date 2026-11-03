# T026 — Bezztrátové seskupení doložených lokálních operací

T026-S01–S05 / AC01–AC06. Explicitní draft stack nad PR65,
`feat/t025-certify-local-operations`, exact `a6170c18c53333946dc6bb694e797170227a90fc`.
Readiness vyžaduje schválený a merged prerequisite; tento dokument jej nenahrazuje.

Nové čisté API `business_process.collapse_business_steps` a
`expand_business_steps` používá ProcessView/ViewDocument a již vložené T025
certifikáty. Slučuje maximální acyklické sousední řetězce min2 ověřených lokálních
operací stejného method/owner/scope/context. Zachovává úplné ordered origin nodes,
internal edges, vnější paralelní hrany, provenance, entry/exit/outcome i nepoužitý
exceptional_exit. Finally klony se nerozpoznávají podle samotného rozsahu.
Rozhodnutí, calls, side effects, field writes, loops a UNKNOWN hranice zůstávají
viditelné; stejné DTO či label nemá důkazní sílu.

Agregovaný action zůstává UNRESOLVED s původní syntaktickou adjacency i compiler
operation evidence; process zůstává PARTIAL. CURRENT je převzatý stav vstupních
podkladů, nikoli nová fyzická kontrola checkoutu. Nevzniká nový CFG, cert issuer,
resolver, store, CLI ani business semantic approval.

Provedeno před implementací: actual Javac workspace→T024→T025 pozitivní případ
vytvořil šest skutečných certified operací a skončil RED1FAIL4.78s kvůli chybějícímu
T026 modulu. Po implementaci actual K1/K2 GREEN2PASS10.20s. První širší matice
82PASS9.76s před finálními doplněnými testy. První pokus bez Maven cache selector
byl TOOLCHAIN_UNAVAILABLE setup ERROR; není vydáván za product RED ani PASS.
Finální focused/full a nezávislá source closure zatím PENDING.

AC01 testuje skutečnou pipeline, ordered roundtrip, paralelní external records,
finally clones a unused exit; AC02 disconnected DTO a diamond; AC03 actual unsafe
body a boundary/loop matrix; AC04 immutable inputs a no-subprocess/network guards;
AC05 provenance/confidence a scope/context/source/hash/CFG tamper; AC06 tento
note + README/capability/status/acceptance. Konkrétní názvy jsou v
`tests/test_t026_collapse_business_steps.py`.

Kompatibilita: aditivní verzovaný group metadata v attributes, staré ProcessView
bez něj expanduje identicky. Rozbalení obnovuje kanonický dokument včetně pořadí;
žádná změna graph v1/v2/v3, existujícího graph view nebo flow render. Čisté funkce
neprovádějí I/O ani aplikaci, nemění vstup či poslední artefakt. Velikost/vnoření
podkladu je ohraničena; neznámý či tampered group fail-closed. Runtime NOT_RUN,
HTTP/DB/model NOT_RUN. Celé T003/T004 ani business ekvivalence nejsou dokončeny.

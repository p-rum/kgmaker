# První mutační workspace a ruční oracle T047-S01

Zadání [T047](../tasks/47_addReliableIncrementalContext.md), krok T047-S01 /
T047-AC01. Lokální výchozí SHA `465b121992aad50c2885acef0fd038531a31293a`.
Dodání IN_PROGRESS, ověření PARTIAL.

## T047-S01 / T047-AC01 — reprodukční corpus

Dřívější testy workspace, Kafka a Flyway pokrývaly jednotlivé vstupy. Nová
[fixture](../../fixtures/incremental-integrity/workspace_fixture.py) je skládá do
dvou repozitářů s Kotlin API, samostatným callerem, dvěma overloady a nezávislým
Kotlin modulem. Frontend obsahuje TypeScript klienta, komponentu a explicitní
API kontrakt. Kafka témata, release mapping a Flyway stream mají oddělené
zdrojové záznamy. Zdrojové soubory fixture se sestaví v izolovaném pytest workspace.

[Ruční oracle](../../fixtures/incremental-integrity/oracle.json) kontroluje
pozitivní cestu DTO → endpoint, očekávané overloady a hranici do frontendu bez
compiler evidence. Kafka deklarace mají bez prokázaného členství modulů UNKNOWN.
Explicitní release map vrací PARTIAL s `RELEASE_MANIFEST_UNAVAILABLE`.
Flyway evidence je migration-derived. Test nic nenavozuje v běžící databázi.

Devět mutací ověřuje komentář, změnu těla, přidání symbolu, přesun a smazání
souboru, změnu verze kontraktu, Kafka topic, Flyway skript a změnu tsconfig.
Každá vrací hash výsledného souborového stromu a přesné cesty změny. Reset
obnoví stejné bytes, opakovaný běh má stejné výsledky. Test oracle odmítá
duplicitní overload. Současné source ID se po posunu deklarace mění, kontrola
T047-S02 je proto explicitně strict XFAIL.

Příklad ověření `python -m pytest -p no:cacheprovider -q --tb=short tests/test_incremental_equivalence.py tests/test_workspace.py tests/test_kafka_bindings.py`
— 100 PASS, 2 SKIP, 1 XFAIL. Původní první běh 99 PASS, 2 SKIP, 1 XFAIL
a 1 FAIL odhalil předpoklad pozitivní Kafka hrany bez scope proof. Oracle byl
opraven podle existujícího capability kontraktu.
`git diff --check` PASS. Skutečný compiler, Windows, úplná mutační matice,
inkrementální ekvivalence a publikované PR review NOT_RUN.

Aktualizovány [README](../../README.md), [dokumentace fixture](../../fixtures/incremental-integrity/README.md),
[acceptance](../acceptance-inventory.md) a [stav](../production-analysis-progress.md).
Veřejné CLI, graf, worker formáty a init nemají změnu. Zbývá doložit zbývající
varianty a provést review. T047-S02 až S06 na tuto scoped fixture navazují.

# Sloučení korpusu T047-S01 a brány T047-S11

## T047-S01 / T047-R01 / T047-AC01 a T048-S01 / T048-AC01

Výchozí `main` je `b3bbba43304f499f96950ea4ecc2a2467919e616`.
Stavová matice v tomto stromu stále uváděla #121 jako otevřené PR. GitHub
potvrdil `merged=true` dne 2026-11-21 ve 22:54:01 UTC. První rodič merge
je `34591e2f45814838dd8b21390cdc43c84530f648`, druhý
`f85269aeedeb849bb503d4273ad1d82a9dbc3a07`. Sloučený strom
`61211b7dd68414dadea322c1b7364c66207cb3e6` se shoduje s ověřeným
stromem kandidáta. [PR #121](https://github.com/p-rum/kgmaker/pull/121) · [Merge commit](https://github.com/p-rum/kgmaker/commit/b3bbba43304f499f96950ea4ecc2a2467919e616)

Stavová matice a acceptance inventář evidují T047-S01 jako `MERGED`
s ověřením `PARTIAL`. Sloučený korpus umožňuje reset a deterministické
opakování mutací proti ručnímu oracle. Offline cold testy ověřují
vybrané vazby v K1/K2, kontrakt typovaného klienta a scénáře s přesným
JVM release artefaktem. Příkaz `python -m pytest -q tests/test_incremental_equivalence.py`
spouští dosavadní sadu fixture. Stávající README a příručka fixture
nadále popisují tento příkaz i potřebný toolchain. Veřejné CLI, API,
schémata, inicializace a registr zadání mají stejný kontrakt.
[Stavová matice](../production-analysis-progress.md) · [Acceptance](../acceptance-inventory.md) · [Příručka fixture](../../fixtures/incremental-integrity/README.md) · [README](../../README.md#incremental-integrity-fixtures)

## Ověření kandidáta a merge

- **Přesný head, JDK 21, Kotlin K1/K2, TypeScript a offline Gradle 8.13.**
  Výběr `test_incremental_equivalence.py`, `test_workspace.py`,
  `test_kafka_bindings.py` a `test_cross_repo_artifacts.py` má 135 PASS,
  0 SKIP a jeden očekávaný strict XFAIL pro T047-S02. JUnit SHA-256
  `7cc32cad877193943929f9d09298bde57eae749982ff9fdc6ca2d8e8a02cd899`.
  Vstupní i výstupní manifest nástrojů má SHA-256
  `9b3fb3b5aa0983192c2aa8342bc44afec6d49e1228e9299ca7eed378bed37c0e`.
- **Přesný head, Python 3.13.18.** Úplný standardní výběr má 2 451 PASS,
  1 294 SKIP a stejný očekávaný strict XFAIL. JUnit SHA-256
  `0dd6e642c709a7df8daf9744ae34fd119e216c14d4a7afdb6681d55bb82255f0`.
  Oba běhy skončily s návratovým kódem 0. Manifest sledovaných souborů
  má před a po obou bězích stejný SHA-256
  `9ae0fc7bf795061833a87e12a368d6458ea56bec28a2ae97ef7cec7e7a8a4f3f`.
  Přípravný přesný výběr před doplněním worker JARů skončil na chybě
  dostupnosti toolchainu. [Historické běhy a příkazy](137_prepareIncrementalMutationOracle.md)
- **Nezávislé review.** Correctness a steelman schválily společný T052 packet
  `1d5e05faa16729be27a75e31a50a49fde985968d98daef78d2fb53de53d079d9`.
  T045 schválil přesný pár v rozsahu reprodukčního korpusu. GitHub odmítl
  formální schválení z účtu autora s HTTP 422. Verdikt je doložen
  komentářem. [T045 záznam](https://github.com/p-rum/kgmaker/pull/121#issuecomment-7070498926)
- **GitHub Actions NEOVĚŘENO.** U osmi jobů pro přesný head chybělo
  přiřazení runneru i záznam kroků. Oba vzorkované logy
  vrátily HTTP 404. [Test](https://github.com/p-rum/kgmaker/actions/runs/44958479371) · [PR Review](https://github.com/p-rum/kgmaker/actions/runs/44958479278)
- **Sloučený strom.** Výběr ze `tests/test_incremental_equivalence.py`
  filtroval `changed_kotlin_body or mutation_replay or source_only or malformed_oracle or comment_does_not_change_logical_identity`.
  Se skutečnými K1/K2 bylo 7 PASS, 0 SKIP, 11 DESELECTED a jeden očekávaný
  strict XFAIL. JUnit `post121-s01.xml` má SHA-256
  `8c14f91d5443060ff1716de4cf0eb1239cb9d4de1becfed36b56c641efa0eb78`.
  Manifest sledovaných souborů má stejný SHA-256 jako obě sady přesného
  headu.

T047-AC01 zůstává PARTIAL. Stabilní logické klíče mají vlastní acceptance
T047-S02. Body-dependent inkrementální refresh, scénáře Windows a úplná
matice §7 zůstávají otevřené.

## Kontroly části S01 na stromu před sloučením #144

- PASS — `PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short tests/test_completion.py tests/test_t032_persist_process_review.py`.
  50 PASS a 0 SKIP.
- PASS — `kgmaker completion plan --jobs 3` načetl 119 položek, z toho
  86 MERGED a 33 PLANNED. Pro S01 vrátil MERGED / PARTIAL a akci
  `verify`. Pro S02 vrátil PLANNED / NOT_RUN a akci `implement` bez
  blokace. Deklarovaná závislost S02 na S01 zůstává v plánu. Stav S11
  je na této revizi PLANNED / NOT_RUN a T032 je MERGED / VERIFIED_IN_SCOPE.
- Úplná testovací sada pro samotný dokumentační krok je NOT_RUN.

## T047-S11 / T047-R11 / T047-AC11 a T048-S01 / T048-AC01

Výchozí `main` pro tuto část je `47807742a07c4a4fb92a590479fbfa0b558bf7fe`.
Stavová matice v tomto stromu stále uváděla T047-S11 jako IN_PROGRESS.
GitHub potvrdil `merged=true` dne 2026-11-21 ve 23:10:34 UTC. První rodič
je `b3bbba43304f499f96950ea4ecc2a2467919e616` a druhý
`a808cef6f509036df92cd3646cccdefe2b946641`. Sloučený strom
`4cef9cf82919ce931eb1c698a7bbc66a43576fb3` se shoduje s ověřeným stromem
kandidáta. [PR #144](https://github.com/p-rum/kgmaker/pull/144) · [Merge commit](https://github.com/p-rum/kgmaker/commit/47807742a07c4a4fb92a590479fbfa0b558bf7fe)

Stavová matice a acceptance inventář evidují S11 jako MERGED s ověřením
PARTIAL. Pravidlo se zapíná příkazem
`kgmaker trace policy --verification-before-done on --expected-revision REVISION`.
Brána vychází z nejnovějšího dokladu aktuální iterace, který pochází ze
skutečného explicitního běhu v jednom lokálním checkoutu. Po dokončení
úlohy další editace změní aktuálnost dokladu a zachová stav `done`.
Dosavadní výchozí režim s vypnutou bránou, čtení dokladů v1, schválení T046,
CLI, API, schémata, inicializace a registr zadání mají v dokumentační
změně stejný kontrakt. [Stavová matice](../production-analysis-progress.md) · [Acceptance](../acceptance-inventory.md#t047-s11--aktuální-lokální-ověření-před-dokončením) · [Příručka](../delivery-workflow.md#aktuální-ověření-před-dokončením-t047-s11) · [README](../../README.md)

### Ověření kandidáta a merge #144

- **Přesný head a sloučený strom.** Osm testovacích souborů z Change159 má
  v každém běhu samostatně 179 PASS, 0 SKIP, 0 FAIL a 0 ERROR se skutečným
  Maven 3.9.9, Surefire 3.5.2 a Temurin JDK 21.0.6+7. SHA-256 JUnit
  přesného headu je `7154fd2f1dbe96387ccc69faa0953e10e9e45a39758333cce48466e67d0dfaca`.
  SHA-256 JUnit ze sloučeného main je
  `410c77d9acaef0d765f771fb288c8dbf24c76a953ce6e617e2c84aa81461fef0`.
  [Příkaz osmisouborového výběru](159_gateCompletionOnCurrentVerification.md#provedené-kontroly)
- **Přesný head, Python 3.13.18.** Úplný standardní výběr má 2 466 PASS,
  1 294 SKIP a jeden očekávaný strict XFAIL pro T047-S02. JUnit SHA-256 je
  `aafa7321909d679ba2b2d220a9749d4ca64c6ebc38a43b82d396d10d4c2ef158`.
  Manifest sledovaných cest má před a po všech třech bězích stejný SHA-256
  `cf6aba5b5206554e05c6d93ceb8291535e2f6f1250fcb1d962feb6d1d445f583`.
- **Přesný head, skutečný offline Gradle 8.13 a JUnit 4.13.2.** Kouřový test
  zaznamenal PASS, skutečný FAIL a nový PASS. Brána po editaci odmítla
  dokončení až do nového aktuálního dokladu a po následné editaci trace
  zobrazil historické `done` s `STALE`. SHA-256 souhrnu je
  `3e2fe51163919c244bfe63f640b6a813d6ead9f8b65045642825790e2232e39b`.
  Samostatný výběr se skutečným Gradle dokladem vynutil `STALE_RUN`
  při editaci zdroje během čtení XML, posunu HEAD při závěrečném výpočtu
  inventáře i změně bajtů vázaného XML. Všech šest odmítnutí v
  `advance_task` a `save_task` zachovalo stejné bajty tasku a journalu.
  SHA-256 souhrnu je `6a0cd88f1ca0c604cfaef934e4bc7cc0ed33050f8c0d6a88af77033b7cc8ff53`.
- **Nezávislé review.** Correctness a steelman schválily společný T052 packet
  `813cfd44d31612396c5172da7496ce67728652b995aa2366c46096d22b7a688c`.
  T045 schválil přesný pár pro volitelnou lokální bránu. [T045 záznam](https://github.com/p-rum/kgmaker/pull/144#issuecomment-7070689840)
- **GitHub Actions NEOVĚŘENO.** Oba běhy přesného headu skončily se stavem
  `failure`. Dostupné záznamy osmi jobů nemají údaje o přiřazeném runneru
  ani evidované kroky. [Test](https://github.com/p-rum/kgmaker/actions/runs/44959889022) · [PR Review](https://github.com/p-rum/kgmaker/actions/runs/44959889016)

T047-AC11 zůstává PARTIAL. Mapování jednotlivých požadovaných testů,
selektivní dopad, širší produkční matice a samostatná projekce do paměti
mají vlastní zbývající rozsah. T047-S12 má nadále samostatné závislosti
na S06, S08 a S09.

## Kontroly společné aktualizace dokumentace

- PASS — `PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short tests/test_completion.py tests/test_t032_persist_process_review.py`.
  50 PASS a 0 SKIP.
- PASS — `kgmaker completion plan --jobs 3` načetl 119 položek, z toho
  87 MERGED a 32 PLANNED. T047-S01 i S11 mají MERGED / PARTIAL a akci
  `verify`. T047-S02 má PLANNED / NOT_RUN a akci `implement` bez blokace.
  Závislost S12 na sloučeném S11 je splněná. Zbývající blokace S12 jsou
  S06, S08 a S09 ve stavu PLANNED / NOT_RUN. T032 má MERGED / VERIFIED_IN_SCOPE.
- PASS — odkazy, kontrolní součty dokladů a shoda produkčních a testovacích
  souborů s přesným sloučeným main.
- Úplná testovací sada pro samotnou společnou dokumentační změnu je NOT_RUN.

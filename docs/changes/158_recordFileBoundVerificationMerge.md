# Doložený merge souborově vázaného ověření T047-S10

## T047-S10 / T047-R10 / T047-AC10 a T048-S01 / T048-AC01

Stavová matice evidovala #135 jako otevřené PR. GitHub zaznamenal merge do
`main` dne 2026-11-21 ve 21:41:22 UTC, `merged=true` a merge SHA
`52af545bfc97396a0001432abc5d58ab7c3663af`. Skutečný první rodič je
`e155cbdc7e5d708920d7632df7bd1ee792d8ebc8`, druhý
`1d7b659a7f04029c740c0209a75a10562412dba9`. Tree
`b765680f96b23fdaa887e4901d9fbbba80e52592` odpovídá ověřenému kandidátu.
[PR #135](https://github.com/p-rum/kgmaker/pull/135) · [Merge commit](https://github.com/p-rum/kgmaker/commit/52af545bfc97396a0001432abc5d58ab7c3663af)

Stavová matice a acceptance inventář evidují S10 jako `MERGED` s ověřením
`PARTIAL`. Implementace váže doklad skutečného testu na existující task,
explicitní build plán, soubory a reporty jednoho Git checkoutu. Příkaz
`kgmaker project build-run --plan /tmp/plan.json --record-verification TASK_ID`
navazuje testovací doklad na dosavadní journal. `kgmaker trace show REF`
oddělí výsledek od jeho aktuálnosti. Tento dokumentační krok používá stávající
veřejný kontrakt, formáty a příklady. Formát BuildPlan v1, BuildManifest v1
a journal v1 lze dál používat bez migrace.
[Stavová matice](../production-analysis-progress.md) · [Acceptance](../acceptance-inventory.md) · [Příručka a příklad](../delivery-workflow.md#dokumentace-skutečného-testovacího-běhu) · [README](../../README.md#doklad-skutečného-testovacího-běhu-t047-s10)

## Ověření kandidáta a merge

- **Přesný head, Python 3.13.18:** úplný standardní výběr měl 2 446 PASS,
  1 281 SKIP, 0 FAIL a 0 ERROR. JUnit SHA-256
  `34fd87a81daecf033f1132fbd9b662f9ec359db87ade1def5afee703d85c6437`.
- **Přesný head, Maven 3.9.9 a JDK 21.0.6:** cílený výběr měl 133 PASS
  a 2 SKIP. Dva starší testy vyžadují exporter přímo pod checkoutem nebo
  dvě JDK na pevných cestách. Skutečný Surefire 3.5.2 ověřil PASS s `CURRENT`,
  následný `STALE` po editaci při stejném HEAD a FAIL s `CURRENT` z nového
  běhu. Test workspace se dvěma checkouty ověřil odmítnutí před spuštěním
  procesu a zápisem do žurnálu. JUnit SHA-256
  `ad8587d3918f2b2e0b7c1ac07e5c6fa45ad278ecf9d4cfd2d12ee5b461a3ac42`.
- **Přesný head, T032 a plánovač:** 50 PASS a 0 SKIP. JUnit SHA-256
  `52f003f8a0f0e92c748c9f99aaf406b125337735fabe4e9ecc7fe49271b49c57`.
  Vstupní i výstupní manifesty obou běhů s úplným a Maven výběrem mají
  stejný SHA-256 `08d763b400c843a420a34f5c6a932df741b413c84ad8a42d273a4adcb1c905d4`.
  [Příkazy a historie dílčích běhů](150_captureBoundVerification.md)
- **Review a merge:** nezávislé role correctness a steelman schválily tentýž
  T052 packet. T045 schválil přesný pár v rozsahu jednoho checkoutu. GitHub
  odmítl formální schválení z účtu autora s HTTP 422. Verdikt nezávislého
  review je doložen komentářem. [T045 záznam](https://github.com/p-rum/kgmaker/pull/135#issuecomment-7069641783)
- **GitHub Actions `NEOVĚŘENO`:** joby Test a PR Review neměly při kontrole
  přiřazené runnery ani evidované kroky. Vzorkované logy včetně cíleného
  opakování Pythonu 3.13 vrátily HTTP 404. Dostupná data nepotvrzují příčinu.
  [Test](https://github.com/p-rum/kgmaker/actions/runs/44952133817) · [PR Review](https://github.com/p-rum/kgmaker/actions/runs/44952133850)
- **Sloučený `main`:** `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --tb=short tests/test_verification_records.py`
  se skutečným Mavenem a Surefire má 27 PASS / 0 SKIP. JUnit SHA-256
  `d5f27612448dca6c4ea6d42a9a2051565cf29f8aa8a7d4901a16e10fede70fd4`.

T047-AC10 zůstává `PARTIAL`. Vícerepozitářové spuštění, ověřitelné
importované doklady a širší ověřovací matice mají samostatný rozsah. T047-S11
zůstává `PLANNED / NOT_RUN` s vlastní acceptance pro freshness a brány
dokončení.

## Kontroly dokumentačního kroku

- PASS — `PYTHONPATH=src python -m pytest -p no:cacheprovider --assert=plain -q --tb=short tests/test_completion.py tests/test_t032_persist_process_review.py`.
  50 PASS / 0 SKIP.
- PASS — `kgmaker completion plan --jobs 3` potvrzuje pro S10
  `MERGED / PARTIAL` a akci `verify`, pro S11 `PLANNED / NOT_RUN`
  a pro T032 `MERGED / VERIFIED_IN_SCOPE`. Souhrn 119 atomických řádků
  odpovídá matici se stavy 85 `MERGED`, 33 `PLANNED` a 1 `PR_OPEN`.
- Úplná testovací sada pro samotný dokumentační krok je `NOT_RUN`.

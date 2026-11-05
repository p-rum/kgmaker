# T003-S07-W05 — Kafka retry, DLT a subscription hranice

- Work package ID: `T003-S07-W05`
- Milník: `T003-S07`
- Revision: 2
- Datum: 2026-11-03
- Stav: SPECIFICATION; tento soubor popisuje cílové chování, nikoli hotovou implementaci.
- Baseline: pracovní větev nad `8ac80ca30f6f680539deb7fb3590519d3a5c1460`; před zahájením ověř aktuální cílovou větev a otevřené PR.
- Závislosti: T003-S07-W04; průřezové požadavky `T003-R01–R10`.
- Nadřazená acceptance: `T003-AC07`.

## Cíl

Modelovat retry/DLT a subscription boundary podle ověřené framework verze.

## Rozsah a konkrétní kontrakty

- Primární místa změny: `src/kgmaker/framework.py, src/kgmaker/flow.py`.
- Reuse existující model/store/provider/workspace/evidence vrstvy; nevytvářej paralelní katalog ani odlišnou identitu entity.
- Zachovej SOURCE_ONLY, nulové implicitní spouštění buildů, instalací, migrací a aplikace a atomickou publikaci poslední validní generace.
- Výsledek s neúplnou evidencí musí být PARTIAL/UNKNOWN s konkrétním důvodem; confidence nesmí nahrazovat chybějící důkaz.
- Veřejnou změnu současně promítni do README, capability dokumentace, CLI příkladů a stavové/acceptance matice.

## Implementační kroky

1. Před kódem ověř současný kontrakt ve zdroji, testech a knowledge graphu; zapiš přesnou podporovanou matici a failing acceptance.
2. Rozšiř stávající datový model a versioned protocol pouze o pole nutná pro tento work package; popiš migraci a kompatibilitu v1/v2/v3.
3. Implementuj pozitivní cestu, lokalizovanou diagnostiku a nulovou mutaci při invalidním vstupu, timeoutu nebo zrušení.
4. Přidej produkčně věrnou fixture a negativní/ambiguous variantu: Spring Kafka version matrix s retryable topic a custom error handler.
5. Aktualizuj acceptance inventář, `docs/production-analysis-progress.md` a nový český `docs/changes/<N>_<shortName>.md` skutečnými výsledky.

## Požadavky na testování

- Test musí ověřit: Spring Kafka version matrix s retryable topic a custom error handler.
- Spusť nejmenší relevantní testy, potom celý `python3 -m pytest -q`; worker/build task navíc spustí příslušný skutečný toolchain test.
- Ověř `git diff --check`, nulové implicitní procesy v offline cestách a nulovou mutaci store při chybě.
- Chybějící povinný toolchain je FAIL/BLOCKED/SKIP dle matice, nikdy PASS. Do change note napiš přesné příkazy, výsledky a neprovedené kontroly.

## Akceptační kritéria

- **T003-S07-W05-AC01:** Asynchronní/retry hrany jsou označené; unsupported konfigurace nevytvoří jistou execution cestu.
- **T003-S07-W05-AC02:** Staré podporované vstupy a graph/store schema zůstávají čitelné nebo mají výslovně otestovanou migraci.
- **T003-S07-W05-AC03:** Negativní a nejednoznačný případ nevytvoří silnější evidence ani dostupnost, než dovolují vstupy.
- **T003-S07-W05-AC04:** Stavová matice odkazuje na konkrétní test/fixture/verzi a nepovýší celý milník nad skutečně ověřený scope.

## Větev, PR a Definition of Done

- Implementuj výhradně v samostatné větvi, doporučeně `feat/t003-s07-05-kafka-retry-dlt`; do stejné větve nepřidávej jiný work package.
- Na konci vytvoř samostatný pull request do aktuálně určené cílové větve. PR musí odkázat na tento soubor, `T003-S07`, nadřazenou acceptance a nový change note; bez explicitního pokynu jej nemerguj.
- Hotovo znamená implementovaný omezený kontrakt, zelené požadované kontroly, aktualizované docs, validní sémantický patch/scan podle projektových instrukcí a zdokumentované zbývající hranice.


## Revize 2 — explicitní bounded framework-policy deklarace

Implementační draft parent je Kafka revize2 `19b0594795ac1f9167916178907b77bb0f070f51`;
ready/merge až po schválení závislosti W04 a integraci aktuálního main.
Podporovaná pozitivní matice: skutečný Java a K1 method listener nad vybraným
oficiálním Spring Kafka3.3.2 annotation resource a hashem, explicitní literal
RetryableTopic attempts/retryTopicSuffix/dltTopicSuffix a jednoznačný DltHandler
ve stejném compiler owner/context/scope. Nested annotations/defaults se nepředpokládají:
nejprve se ověří actual capture, unsupported shapes dostanou UNKNOWN reason.
Spring Kafka3.2.0 je skutečný odlišný API vstup pro nepodporovanou version matrix,
ne metadata přeznačeného3.3.2. K2 annotation capture zůstává explicitně UNKNOWN.

Deklarovaná policy má FRAMEWORK_DERIVED evidence a označenou async hranici,
execution/delivery NOT_OBSERVED, activation/runtime/data availability UNKNOWN.
Nesmí vzniknout synchronní call nebo konkrétní runtime retry destination z názvu.
Custom errorHandler/containerFactory/template, SpEL, dynamické hodnoty,
ambiguous DLT handlers a source-shadowed/unknown API zůstávají viditelně UNKNOWN.
Původní listener IDs a W04 fakta se zachovávají; vlastní rule/cache verze je aditivní.
Reuse kafka_code canonical compiler proof guards, model/evidence/workspace a flow;
žádný nový store/resolver, implicitní build, app ani broker.

AC01 vyžaduje actual Java/K1 explicit retry/DLT positive + customhandler negative
+ skutečnou3.3.2/3.2.0 API matrix. AC02 legacy inputs bez nové verze nezískají policy,
unknown verze fail closed. AC03 source/context/scope/owner/annotation/proof/API hash
mutace, dva groups a unsupported values nesmějí povýšit evidence; nulová mutace
checkout/store a offline no-process/no-network. AC04 capability matrix uvede přesný
backend/API/rule a zbývající UNKNOWN. Nejprve bounded RED/capture, poté source
freeze+focused a jedna FIFO full sada s pre/post input receipts a nezávislým review.

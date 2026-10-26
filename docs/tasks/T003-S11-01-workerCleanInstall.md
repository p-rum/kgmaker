# T003-S11-W01 — Worker distribuce mimo checkout

- Work package ID: `T003-S11-W01`
- Milník: `T003-S11`
- Revision: 2
- Datum: 2026-10-16
- Stav: SPECIFICATION; tento soubor popisuje cílové chování, nikoli hotovou implementaci.
- Baseline: pracovní větev nad `8ac80ca30f6f680539deb7fb3590519d3a5c1460`; před zahájením ověř aktuální cílovou větev a otevřené PR.
- Závislosti: existující verzovaný JVM/TypeScript worker protocol a již podporované worker artefakty v baseline; průřezové požadavky `T003-R01–R10`. Úplná release acceptance T003-S11 nadále vyžaduje T003-S04-W05 a T003-S08-W03.
- Nadřazená acceptance: `T003-AC11`.

## Cíl

Zabalit JVM/TypeScript workers pro čistou instalaci a explicitní workers home.

### Odůvodnění revize 2 (2026-10-26)

Původní pořadí vázalo samotnou distribuci také na budoucí golden corpus
T003-S04-W05 a callback/generic resolution T003-S08-W03. Resolver a balení
používají současný worker protocol a nepřidávají sémantické schopnosti těchto
úkolů. Tento work package proto může samostatně distribuovat již podporovaný
rozsah. AC01–AC04 se nemění a musí být ověřena skutečnou instalací obou workerů.
Nejde o splnění ani zrušení uvedených budoucích úkolů: jejich specifikace,
podporovaná matice a celkové acceptance/release gates T003 zůstávají v platnosti.
T003-S11 i T003-AC11 zůstávají PARTIAL až do úplného ověření plánu.

## Rozsah a konkrétní kontrakty

- Primární místa změny: `packaging config, src/kgmaker/inspection.py, workers`.
- Reuse existující model/store/provider/workspace/evidence vrstvy; nevytvářej paralelní katalog ani odlišnou identitu entity.
- Zachovej SOURCE_ONLY, nulové implicitní spouštění buildů, instalací, migrací a aplikace a atomickou publikaci poslední validní generace.
- Výsledek s neúplnou evidencí musí být PARTIAL/UNKNOWN s konkrétním důvodem; confidence nesmí nahrazovat chybějící důkaz.
- Veřejnou změnu současně promítni do README, capability dokumentace, CLI příkladů a stavové/acceptance matice.

## Implementační kroky

1. Před kódem ověř současný kontrakt ve zdroji, testech a knowledge graphu; zapiš přesnou podporovanou matici a failing acceptance.
2. Rozšiř stávající datový model a versioned protocol pouze o pole nutná pro tento work package; popiš migraci a kompatibilitu v1/v2/v3.
3. Implementuj pozitivní cestu, lokalizovanou diagnostiku a nulovou mutaci při invalidním vstupu, timeoutu nebo zrušení.
4. Přidej produkčně věrnou fixture a negativní/ambiguous variantu: clean venv/wheel smoke test mimo checkout se SOURCE_ONLY variantou.
5. Aktualizuj acceptance inventář, `docs/production-analysis-progress.md` a nový český `docs/changes/<N>_<shortName>.md` skutečnými výsledky.

## Požadavky na testování

- Test musí ověřit: clean venv/wheel smoke test mimo checkout se SOURCE_ONLY variantou.
- Spusť nejmenší relevantní testy, potom celý `python3 -m pytest -q`; worker/build task navíc spustí příslušný skutečný toolchain test.
- Ověř `git diff --check`, nulové implicitní procesy v offline cestách a nulovou mutaci store při chybě.
- Chybějící povinný toolchain je FAIL/BLOCKED/SKIP dle matice, nikdy PASS. Do change note napiš přesné příkazy, výsledky a neprovedené kontroly.

## Akceptační kritéria

- **T003-S11-W01-AC01:** Worker se najde deterministicky; SOURCE_ONLY nepotřebuje JDK/Node; chybění je jasná diagnostika.
- **T003-S11-W01-AC02:** Staré podporované vstupy a graph/store schema zůstávají čitelné nebo mají výslovně otestovanou migraci.
- **T003-S11-W01-AC03:** Negativní a nejednoznačný případ nevytvoří silnější evidence ani dostupnost, než dovolují vstupy.
- **T003-S11-W01-AC04:** Stavová matice odkazuje na konkrétní test/fixture/verzi a nepovýší celý milník nad skutečně ověřený scope.

## Větev, PR a Definition of Done

- Implementuj výhradně v samostatné větvi, doporučeně `feat/t003-s11-01-worker-clean-install`; do stejné větve nepřidávej jiný work package.
- Na konci vytvoř samostatný pull request do aktuálně určené cílové větve. PR musí odkázat na tento soubor, `T003-S11`, nadřazenou acceptance a nový change note; bez explicitního pokynu jej nemerguj.
- Hotovo znamená implementovaný omezený kontrakt, zelené požadované kontroly, aktualizované docs, validní sémantický patch/scan podle projektových instrukcí a zdokumentované zbývající hranice.

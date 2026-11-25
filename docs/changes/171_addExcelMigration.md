# T054 — Analýza sešitů a export migračních úloh

Datum 2026-11-25. Výchozí SHA všech kroků `1e782a119e5ae54d22bfc8d7c22c565ed651815a`.
[Zadání T054](../tasks/54_addExcelMigration.md) · [CLI, kontrakty a příklady](../excel-migration.md) · [Stavová matice](../production-analysis-progress.md) · [Akceptační inventář](../acceptance-inventory.md)

## T054-S01 / T054-AC01–AC02

Stávající scanner umí omezené XLSX a diagnostiku binárního XLS. Samostatný worker v `workers/excel` čte BIFF8, OOXML a zdrojové VBA. `kgmaker.excel` váže manifest a lokátory na konkrétní bajty vstupů, propojuje podporované odkazy a ponechává dynamické konstrukce jako diagnostiku.

**PASS** Skutečné XLSM, BIFF8 XLS, dva propojené sešity, události a ovládací prvek, zápisy a přepočtové vazby, názvy, skryté listy, neplatný formát, šifrování, limity a nedostupná závislost v `tests/test_excel_migration.py`. `strace -f -e trace=execve,execveat,connect` nad dvousešitovou fixture zachytil dva spuštěné Excel workery a nula IP spojení. Zdroje zůstaly se stejným SHA-256. **NOT_RUN** Excel runtime parita a obsluha nepodporovaných VBA konstrukcí.

## T054-S02 / T054-AC03

Lokální packet a kandidát obsahují návrh Kotlin/JVM, dohledatelné podklady, akceptaci, testy a graf pořadí úloh. Validátor odmítá chybějící pokrytí, neznámou citaci, cykly a staré zdroje. Export Markdown a JSON používá atomickou publikaci a pravidla kolizí vstupů s výstupem.

**PASS** End-to-end s ručně vyplněným kandidátem podle vygenerované šablony, řízeným zveřejněním zdrojového kontextu a zachováním dřívějšího exportu při změně souboru. **NOT_RUN** Živá interaktivní relace Copilot a funkční parita přepsaného Kotlin programu.

## T054-S03 / T054-AC04

`jira-task` zavádí výchozí šablonu Jira Cloud a projektová pole s typem, povinností a povolenými hodnotami. CSV export generuje Epic, Task, importní ID, Parent, odchozí Blocks a text s akceptací i citacemi. Výpis příkazu uvádí mapování pro průvodce.

**PASS** Lokální kontrola UTF-8, escapování, víceřádkového popisu, hierarchie, více závislostí, vícenásobných a vlastních polí a chybové validace. **NOT_RUN** Import do konkrétního Jira Cloud projektu, který vyžaduje ověření správcem projektu.

## T054-S04 / T054-AC05

`pyproject.toml` přidává Excel modul a podmíněně přibaluje sestavený worker. Samostatná CI matice má Linux a Windows, JDK 17 a instalaci wheelu. Stávající formáty grafu a úložiště nevyžadují migraci. Cílové init šablony nemají novou závislost, modul se spouští výhradně explicitním příkazem.

- **PASS** `mvn -o -B -ntp -f workers/excel/pom.xml package` s Temurin 17.0.17, Maven 3.9.12 a připravenou repozitoří Mavenu. `python workers/excel/verify_distribution.py` potvrdil 16 runtime JARů.
- **PASS** `KGMAKER_REQUIRE_EXCEL_WORKER=1 KGMAKER_REQUIRE_EXCEL_WHEEL=1 python -m pytest -q tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py tests/test_feature.py tests/test_scanner.py tests/test_worker_protocol.py` s Java 17 na Linuxu. Celkem 131 PASS, včetně offline instalace wheelu mimo checkout.
- **PASS** `python -m pytest -q -rs` po editable instalaci. Celkem 2 561 PASS, 1 317 SKIP a 1 XFAIL. SKIP zahrnuje nepřipravené ostatní toolchainy a samostatný opt-in wheel test, který proběhl v cílené sadě.
- **FAIL** `kgmaker check` nad izolovanou kopií vývojového repozitáře se starým semantic snapshotem hlásí změněné otisky `README.md` a `src/kgmaker/cli.py`. Vlastní graf vývojového repozitáře je předmětem samostatného [PR #153](https://github.com/p-rum/kgmaker/pull/153).
- **PASS** `git diff --check`.
- **NOT_RUN** Lokální Windows a testovací Jira Cloud. Stav vzdálené CI se posuzuje nad hashem PR.

Ukázka výstupu z testovací faktury sleduje `Workbook_Open` → `RecalculateInvoice` → `Sheet1!A1` → `Sheet1!B1`. Externí čtení sazby `Rates!B2` je dohledatelné přes druhý soubor. Samostatná portová úloha v CSV blokuje migraci výpočtu.

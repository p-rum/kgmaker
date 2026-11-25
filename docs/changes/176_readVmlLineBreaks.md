# Čtení párové značky zlomu řádku ve VML

Datum 2026-11-25. Výchozí `main` `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`.
[T054-S01 / T054-AC01 a T054-AC02](../tasks/54_addExcelMigration.md) · [Návod](../excel-migration.md#podporovaný-rozsah) · [Akceptační inventář](../acceptance-inventory.md).

Apache POI 6.0.0 při čtení VML nahrazuje samostatný řetězec `<br>` za `<br/>`. Z platného `<br></br>` tím vznikne `<br/></br>` a načtení XLSM selže s `EXCEL_PARSE_FAILED`. Syntetický sešit s VML tlačítkem chybu reprodukoval a zachoval původní bajty. Produkční sešit nebyl součástí ověření.

`ExcelWorker.java` poskytuje POI bezpečný ZIP zdroj otevřený pouze pro čtení. Párovou značku normalizuje pouze v proudu deklarovaných VML částí, s rozlišením značek od komentářů, CDATA a instrukcí zpracování. XLSM se nepřepisuje a nástroj neprodukuje znormalizovaný soubor. `tests/test_excel_migration.py` ověřuje vazbu skutečného VML tlačítka na VBA, varianty `<br></br>` a `<br/>`, bajtovou shodu sešitu a původní SHA-256 v inventáři.

Stejný vstup lze předat přímo pomocí `kgmaker excel analyze --manifest app.json --out inventory.json` nebo `kgmaker excel migrate prepare --workbook Fakturace.xlsm --out-dir migrace`. Stávající inventáře mají stejný formát. Ve zdrojovém checkoutu sestav aktualizovaný worker. Makra se analyzují staticky.

Před opravou regresní test s `<br></br>` skončil `FAIL`, varianta `<br/>` prošla. Po opravě prošly obě varianty. `mvn -o -B -ntp -f workers/excel/pom.xml package` použil JDK 17 a lokální Maven cache. `python workers/excel/verify_distribution.py` potvrdil 16 runtime závislostí.

Cílený `pytest` nad `test_excel_migration.py`, `test_workbooks.py`, `test_xlsx_references.py`, `test_binary_xls.py`, `test_skills.py` a `test_installation.py` s `KGMAKER_REQUIRE_EXCEL_WORKER=1` a `KGMAKER_REQUIRE_EXCEL_WHEEL=1` má 174 PASS. Plný `pytest -q` s `KGMAKER_REQUIRE_MARKDOWN_PARSER=1` má 2 582 PASS, 1 323 SKIP a 1 XFAIL. `strace -f -e trace=execve,execveat,connect` při `excel migrate prepare` zaznamenal dva statické Java workery, žádná IP spojení a shodné SHA-256 obou vstupů. `git diff --check` prošel. Živý Copilot a produkční XLSM mají stav NOT_RUN.

První [GitHub Test run](https://github.com/p-rum/kgmaker/actions/runs/45660572649) skončil `failure` bez kroků v Excel jobu a bez dostupného logu (`BlobNotFound`). Ověření na GitHub runneru tím není doložené.

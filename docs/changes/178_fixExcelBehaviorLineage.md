# Opravy statického toku Excelu po review

Datum 2026-11-25. Základní SHA `a1cb9e0c6edacc50c89b57c9a96ac18f544b4447`.
[Zadání T056](../tasks/56_extractExcelBehavior.md) · [Návod](../excel-migration.md#funkce-a-tok-dat-v-sešitu) · [Acceptance](../acceptance-inventory.md).

## T056-S02 / T056-AC02

Review našlo tři nepřesnosti v odvozených cestách. Rozsah zápisu query tabulky a čtení vzorce se nyní propojí podle překryvu adres i bez důkazu `cell`; rozbalení oblastí zůstává omezené. Známá nepřepisující VBA intrinsic volání, například `Format`, zachovávají argumentové definice. Přiřazení po uzavření větve přepíše starší definice, zatímco přiřazení uvnitř větví zůstávají alternativami.

Změněné soubory: `src/kgmaker/excel/behavior.py`, `src/kgmaker/excel/extraction.py` a `tests/test_excel_migration.py`. Inventář, CLI, exporty i jejich schémata zůstávají kompatibilní. Uživatelský návod a stav T056 byly zpřesněny; README zůstává beze změny, protože oprava nemění příkazy ani formát. Zadání a registr T056 se nemění.

### Kontroly

- **PASS** — `/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_excel_migration.py -k 'query_destination_connects or vba_function_lineage or vba_non_mutating_intrinsic'`: 3 passed.
- **PASS** — `/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_excel_migration.py`: 19 passed.
- **PASS** — `/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_excel_migration.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py`: 81 passed.
- **SKIP** — 14 worker/wheel testů: 13 vyžaduje Java 17+ a Excel worker, jeden explicitní smoke instalovaného wheelu. Worker ani wheel zde nejsou dostupné.
- **PASS** — `git diff --check`.
- **PASS** — `./kgmaker scan --root . --no-docs` obnovil strojový index; scan také upozornil na čtyři zastaralé sémantické vazby a zastaralé důkazy v README. Tyto nesouvisející vztahy nejsou součástí opravy.
- **SKIP** — `ruff check ...`; Ruff není v prostředí dostupný a projekt nemá nastavený povinný lint příkaz.
- **NOT_RUN** — Java worker/wheel a hostovaná CI; oprava těchto tří případů nevyžadovala změnu workeru.

Statická inference nad syntetickými doklady zůstává omezená; neběží sešit, VBA ani externí zdroj. Další ověření produkčního sešitu a živého Copilotu zůstává NOT_RUN.

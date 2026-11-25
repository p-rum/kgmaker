# T055 — Jeden pokyn pro migraci Excelu

Datum 2026-11-25. Baseline `782ac6ac0287550084e9afadbd6182756fdd2730`.
[Zadání T055](../tasks/55_automateExcelMigration.md) · [Návod](../excel-migration.md#jeden-pokyn-pro-copilot) · [Akceptační inventář](../acceptance-inventory.md) · [Stavová matice](../production-analysis-progress.md)

## T055-S01 / T055-AC01 — Příprava přímo ze sešitů

Ruční tvorbu manifestu nahrazuje `excel migrate prepare` v `src/kgmaker/excel/migration.py`. Zdrojový výběr a kontrola čerstvosti používají společnou logiku v `source.py` a `inventory.py`. Přímý výběr váže jen výslovně předané sešity a přesně odpovídající jedinečné názvy. Pro explicitní identity zůstává podporovaný `--manifest`. Kompletní subjekty v `subjects.jsonl` pomáhají pokrýt i větší inventář se zkráceným packetem. Výchozí packet vynechává zdroj maker, vzorce a hodnoty. Schémata z T054 se nemigrují.

**PASS** Testy přímého výběru s XLSM a závislým XLSX, nejednoznačných názvů, úplného seznamu pokrytí a výchozího skrytí zdrojového obsahu. Výběr neskenuje okolní soubory.

## T055-S02 / T055-AC02 — Validace a export balíku

`excel migrate export` používá validátor plánu a Jira renderer z T054. Vytváří společný adresář s Markdown, CSV a mapováním. Před publikací i po zápisu ověřuje otisky explicitně předaných zdrojů. Při kolizi chrání předchozí export. Kandidát zůstává čitelným lokálním JSON souborem. Vytvoření úloh provádí uživatel v Jira importéru.

**PASS** Testy skutečného CLI s kandidátem pokrývají vlastní Jira pole, výstupy Markdown a CSV, neplatný návrh, změněný sešit i ochranu předchozího exportu. **NOT_RUN** Živý import Jira Cloud.

## T055-S03 / T055-AC03 — Copilot skill a zákaz maker

Nový `kgmaker-excel-migration` je v distribuovaném `skills.py` a spravované kopii `.agents/skills/kgmaker-excel-migration/SKILL.md`. Skill si sám připraví data, napíše validovatelný kandidát a exportuje oba výstupy. Pokyny výslovně zakazují makra, interpretry VBA, tabulkové aplikace, COM, přepočet a následování externích odkazů. Stávající instalace získá skill přes `kgmaker upgrade`. Přímé příkazy a příklad použití jsou v README a návodech k Excelu a skillům.

**PASS** Parita souborů, nový `init` a upgrade ze starší instalace. `strace -f -e trace=execve,execveat,connect` nad syntetickým XLSM a závislostí s `--include-source` doložil dva Java analyzátory, žádný tabulkový editor a nula IP spojení. **NOT_RUN** Živá relace Copilotu a Windows.

Příklad použití v Copilotu. „Použij $kgmaker-excel-migration pro Fakturace.xlsm se závislostí Sazby.xlsx. Vytvoř Kotlin plán a Jira CSV do migrace/. Makra nikdy nespouštěj.“

Cílené ověření použilo Java 17, instalovaný Linux wheel a příkaz `python -m pytest -q tests/test_excel_migration.py tests/test_skills.py tests/test_installation.py tests/test_workbooks.py tests/test_xlsx_references.py tests/test_binary_xls.py` s `KGMAKER_REQUIRE_EXCEL_WORKER=1` a `KGMAKER_REQUIRE_EXCEL_WHEEL=1`.
Výsledek cílené sady je 168 PASS. Plná sada `python -m pytest -q -rs` má 2 571 PASS, 1 317 SKIP a 1 XFAIL. `git diff --check` prošel.

## Předání T055-S01–S03 k review

Aktuální `main` `5809e84932b1910bfc3f17c72e2a2005283389b1` byl integrován bez konfliktů. Ověřený integrační commit `13559f6a55f89785b4e142bf6b6aab10b8ab6da6` zachovává rozsah AC01–AC03. Cílená sada ze záznamu výše znovu prošla se skutečným Java 17 workerem a instalovaným Linux wheelem, 168 PASS. `python workers/excel/verify_distribution.py` ověřil 16 runtime závislostí. `git diff --check origin/main...HEAD` prošel. Živý Copilot, Windows a Jira import zůstávají NOT_RUN.

## Opravy review T055-S02 a T055-S03

Výchozí HEAD `8904bde87b38c0771b2e91e3189e30e3b02f6207`. Kontrola odhalila, že příklad umožňoval předat celé `--include-source` po povolení dílčího obsahu a že výměna cesty mohla po chybě přesměrovat úklid na cizí soubor.

- **T055-S02 / AC02.** Publikace ověřuje identitu vytvořených souborů i adresáře a při výměně cesty hlásí chybu. Úklid při chybě zachovává cizí náhrady a přemístěné výstupy.
- **T055-S03 / AC03.** Distribuovaný skill i spravovaná kopie výslovně uvádějí všechny části rozšířeného packetu. Částečný souhlas ponechává redigovaný režim. Ukázkový pokyn používá výchozí redigovaný režim.

**PASS** Čtyři regresní scénáře úklidu, kontrola instrukcí a parity instalace a cílená sada z T055-S03 nad opravenými zdroji. Celkem 172 PASS s Java 17 a instalovaným Linux wheelem. `git diff --check` prošel. **NOT_RUN** Živý Copilot, Windows a Jira import.

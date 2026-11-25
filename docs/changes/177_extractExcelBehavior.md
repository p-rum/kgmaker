# Funkce a toky dat v Excelu před plánem migrace

Datum 2026-11-25. `main` `0c834c8b2c06ca80d76f1aaf09f6f49b968e8aa3`. [Zadání T056](../tasks/56_extractExcelBehavior.md) · [Návod](../excel-migration.md#funkce-a-tok-dat-v-sešitu) · [Acceptance](../acceptance-inventory.md).

## T056-S01 / T056-AC01

Inventář dosud evidoval některé odkazy na buňky a procedury, ale integrace často skončily obecným hlášením. `ExcelWorker.java` čte deklarovaná připojení a vazby query tabulek ve vztazích OOXML. `excel/extraction.py` a `excel/inventory.py` přidávají zdrojové položky pro `WEBSERVICE`, externí sešity a deklarace připojení. Podporované zápisy VBA evidují operátory, volání, HTTP požadavky a čtení odpovědi, možné lokální definice a zápisy s dohledatelnou polohou. Worker `excel-poi-6.0.0-3` používá stejný protokol. Dřívější inventář z workeru `-2` zůstává čitelný. Pro nové doklady je potřeba přegenerovat inventář s aktualizovaným workerem.

## T056-S02 / T056-AC02

`excel/behavior.py` uvádí přímo pozorované deklarace a příkazy, citace a odvozené cesty ke kandidátům na výstupy. `IFERROR` popisuje podmínku pro náhradní výsledek. VBA s větvením nabízí dohledatelné předchozí alternativy, výběr za běhu má stav neověřeno. Zobrazené buňky mohou sloužit i jako mezivýsledky nebo externí vstupy. Rozsáhlé oblasti zůstávají také jako citované adresy. Nevyhodnocuje se Excel, VBA, externí odpověď ani dynamicky poskládaný zdroj.

## T056-S03 / T056-AC03

`excel migrate prepare` zveřejní `behavior.md` společně s inventářem a packetem. `excel behavior --inventory migrace/inventory.json --book main --sheet Vysledky` vypíše výpočty listu a jejich dohledatelné cesty i přes jiné listy. Bez `--include-source` se neuvádějí přesné výrazy, hodnoty, VBA text, adresy zdrojů ani přesné formátovací řetězce. Distribuovaný skill i jeho spravovaný vzor vedou od konkrétního chování k akceptaci a Jira úlohám. Schéma plánu, mapování a import CSV fungují podle stávajícího kontraktu.

## Ověření

- S01 a S02. Regrese `test_currency_behavior_reports_three_sources_across_fifteen_sheets` používá skutečný Java worker, 15 listů, přes 200 vazeb a tři neprovozní zdroje. Ověřuje tři cesty do `Display!A1`, query tabulku se zdrojem v OOXML a zobrazení `IFERROR` i při výběru listu. VBA regrese dokládá HTTP deklaraci, čtení odpovědi, výpočet, zápis, možná přiřazení před `MsgBox` a nevyřešený dynamický cíl.
- S03. `mvn -o -B -ntp -f workers/excel/pom.xml package` s JDK 17 a lokální Maven cache prošel. `python workers/excel/verify_distribution.py` ověřil 16 závislostí. Cílený `pytest` pro Excel, skilly, instalaci, workbooks, reference a binární XLS s `KGMAKER_REQUIRE_EXCEL_WORKER=1` a `KGMAKER_REQUIRE_EXCEL_WHEEL=1` má **174 PASS**. Ověřuje instalovaný Linux wheel, redakci, zachování XLSX a čitelnost inventáře `-2`.
- `KGMAKER_REQUIRE_MARKDOWN_PARSER=1 python -m pytest -q` má **2 599 PASS**, **1 334 SKIP** a **1 XFAIL**. `git diff --check` prošel.
- `strace -f -e trace=execve,execveat,connect` nad syntetickým kurzovním sešitem a dvěma existujícími fixture ověřil tři statické workery, žádné IP spojení a shodné SHA-256 vstupů. Produkční sešit, skutečný Copilot, Windows a Jira Cloud import mají stav NOT_RUN.

## Integrace s `main` a opravy review

Výchozí HEAD `9cabfde497deaf9ef97b1cb08a5eaa349b32a070`. Opravy jsou ověřované s `main` `61cd97d90d7a342396da79e7c3c7401c3df2560e` včetně změn T052. Integrace proběhla bez konfliktů.

- **T056-S01 / AC01 a T056-S02 / AC02.** Cesta k hodnotě vzorce sleduje doložená přiřazení návratové hodnoty VBA. Aktivní definice v přímé větvi vyřadí dříve přepsané přiřazení. Podmíněné definice mohou zůstat alternativami. Samostatná operace HTTP při volání funkce se neposouvá na cestu hodnoty vzorce. Pokud neprůhledné volání může přepsat předanou proměnnou, detekce ruší dřívější vazbu hodnoty, HTTP klienta a odvozené URL.
- **T056-S02 / AC02.** Statický průchod od VBA čtení končí u citované buňky nebo oblasti. Část o limitech uvádí neověřené pořadí zápisů a přepočtu. Výpis přestane připisovat dřívějšímu výsledku pozdější zápis do zdrojové buňky. Vzorcové a OOXML vazby se dál zobrazují.
- **T056-S03 / AC03.** Filtrovaný výpis listu zobrazuje doloženou událost `Worksheet_Change` z dokumentového modulu. Formát inventáře a exportů zůstává kompatibilní.

Po sestavení čistého výstupu workeru pomocí `mvn -o -B -ntp -f workers/excel/pom.xml package` na Java 17 potvrdil `python workers/excel/verify_distribution.py` 16 závislostí. Cílený `pytest` nad `test_excel_migration.py`, `test_skills.py`, `test_installation.py`, `test_workbooks.py`, `test_xlsx_references.py`, `test_binary_xls.py` a `test_completion.py` s povinným Excel workerem a wheelem má **190 PASS / 0 SKIP**. Plná sada s povinným Markdown parserem má **2 608 PASS / 1 334 SKIP / 1 XFAIL**. `git diff --check` prošel. Nové statické trasování `excel migrate prepare` opět ověřilo tři workery bez IP spojení a shodné vstupní SHA-256.

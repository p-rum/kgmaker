# Funkce a toky dat v Excelu před plánem migrace

Datum 2026-11-25. `main` `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`. [Zadání T056](../tasks/56_extractExcelBehavior.md) · [Návod](../excel-migration.md#funkce-a-tok-dat-v-sešitu) · [Acceptance](../acceptance-inventory.md).

## T056-S01 / T056-AC01

Inventář dosud evidoval některé odkazy na buňky a procedury, ale integrace často skončily obecným hlášením. `ExcelWorker.java` čte deklarovaná připojení a vazby query tabulek ve vztazích OOXML. `excel/extraction.py` a `excel/inventory.py` přidávají zdrojové položky pro `WEBSERVICE`, externí sešity a deklarace připojení. Podporované zápisy VBA evidují operátory, volání, HTTP požadavky a čtení odpovědi, možné lokální definice a zápisy s dohledatelnou polohou. Worker `excel-poi-6.0.0-3` používá stejný protokol. Dřívější inventář z workeru `-2` zůstává čitelný. Pro nové doklady je potřeba přegenerovat inventář s aktualizovaným workerem.

## T056-S02 / T056-AC02

`excel/behavior.py` uvádí přímo pozorované deklarace a příkazy, citace a odvozené cesty ke kandidátům na výstupy. `IFERROR` popisuje podmínku pro náhradní výsledek. VBA s větvením nabízí dohledatelné předchozí alternativy, výběr za běhu má stav neověřeno. Zobrazené buňky mohou sloužit i jako mezivýsledky nebo externí vstupy. Rozsáhlé oblasti zůstávají také jako citované adresy. Nevyhodnocuje se Excel, VBA, externí odpověď ani dynamicky poskládaný zdroj.

## T056-S03 / T056-AC03

`excel migrate prepare` zveřejní `behavior.md` společně s inventářem a packetem. `excel behavior --inventory migrace/inventory.json --book main --sheet Vysledky` vypíše výpočty listu a jejich dohledatelné cesty i přes jiné listy. Bez `--include-source` se neuvádějí přesné výrazy, hodnoty, VBA text, adresy zdrojů ani přesné formátovací řetězce. Distribuovaný skill i jeho spravovaný vzor vedou od konkrétního chování k akceptaci a Jira úlohám. Schéma plánu, mapování a import CSV fungují podle stávajícího kontraktu.

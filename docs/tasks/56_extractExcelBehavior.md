# T056 — Popis funkcí a toků dat v Excelu

- **Task ID** T056
- **Revision** 1
- **Datum** 2026-11-25
- **Stav** SPECIFICATION
- **Baseline** `main` `3a6b97fc9c44941e68bb390772a5eb13906bf1ff`
- **Závislosti** T054 statický inventář a T055 příprava migračního balíku. Oprava VML z PR #159 umožňuje načíst také dříve odmítnuté XLSM s párovým `<br></br>`.

## Rozsah a požadavky

- **T056-R01** Z inventáře popsat konkrétní zdroje dat, vstupní události, vzorce a VBA kroky, vazby mezi listy a kandidátní zobrazené výstupy. Každá položka má identifikátor důkazu a dohledatelnou polohu. Mezi rozpoznané zdroje patří `WEBSERVICE`, reference na jiný sešit, deklarovaná připojení a běžné explicitní VBA HTTP požadavky. Vzorce a lokální VBA tok zůstávají statické.
- **T056-R02** Uvést rozdíl mezi konkrétním zápisem v sešitu, odvozeným tokem a zjištěnou nejasností. Evidovat možné alternativní definice a větvení. Výstup má fungovat ve větším sešitu a zobrazit upstream cesty i při výběru konkrétního listu.
- **T056-R03** `prepare` dodá `behavior.md` před tvorbou Jira úloh. CLI umí report sestavit z existujícího inventáře. Přesné zdrojové výrazy, hodnoty, VBA text a identity odkazů se přidávají výslovnou volbou `--include-source`. Worker provádí pouze statické čtení; žádné požadavky, přepočty, otevírání sešitu v tabulkové aplikaci ani makra se neprovádějí.

## Kroky a akceptace

| Krok | Závislost | Akceptace |
|---|---|---|
| T056-S01 | T054 | **T056-AC01** Výstup obsahuje tři doložené zdroje syntetického 15listého sešitu včetně XLSX query table. Všechny tři lze sledovat přes mezilistové odkazy do výstupu. Podporovaný VBA HTTP požadavek má vazbu na čtení odpovědi, výpočet a výstup. |
| T056-S02 | T056-S01 | **T056-AC02** Citace ukazují buňku, modul a řádek. Report popíše `IFERROR` a více možných přiřazení s podmínkami a hranicemi statické inference. Nejasná metadata ani běh sešitu se nepovažují za potvrzené výsledky. |
| T056-S03 | T056-S02, T055 | **T056-AC03** Lokální `prepare` a `behavior --sheet` vytvoří report, zdrojové údaje jsou ve výchozím režimu redigované. Inventář, Jira šablona a export se nadále validují. Distribuovaný Copilot skill z reportu odvozuje konkrétní úlohy a příslušné testy. |

## Kontrakty, hranice ověření a dokončení

`kgmaker.excel` rozšíří položky stávajícího inventáře o deklarované zdroje a
operace. Formát plánu, Jira CSV a dosavadní inventáře zůstávají kompatibilní.
Přesné výsledky, úplný tok ve VBA s dynamickými objekty nebo mezi procedurami,
návrháře formulářů, výsledky Power Query a skutečný import Jira jsou samostatné
ověření. Dokončení tohoto rozsahu vyžaduje syntetický vícezdrojový test nad
skutečným workerem, regresní testy CLI a instalace, doklady o redakci a český
záznam výsledků. [Uživatelský návod](../excel-migration.md#funkce-a-tok-dat-v-sešitu)

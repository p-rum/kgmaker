# Migrace Excelu do Kotlin/JVM

`kgmaker excel` načte výslovně zadané sešity, připraví podklady pro Copilot a ověří plán migrace. Plán lze uložit jako Markdown nebo JSON a exportovat úlohy do CSV pro Jira Cloud. Workflow funguje z běžného adresáře bez Gitu, `kgmaker init` a uloženého znalostního grafu.

## Příprava workeru

Pro `excel analyze` je potřeba Java 17+ a distribuce obsahující Excel worker. Při použití zdrojového checkoutu nejprve sestav aktuální worker s JDK 17+ a Mavenem. Sestavení načítá závislosti z Maven Central. Analýza je používá z lokálních souborů.

```sh
mvn -B -ntp -C -f workers/excel/pom.xml package
python workers/excel/verify_distribution.py
python -m pip install --no-deps -e .
```

Distribuční wheel vytvoř po sestavení workeru příkazem `python -m pip wheel --no-deps --wheel-dir dist .`. Obsahuje samostatný JAR, uzamčené runtime JARy a jejich původní licence. `packet`, validace, export a ostatní příkazy kgmakeru mohou běžet bez Javy.

## Sešity a plán

Ulož manifest vedle vstupních souborů. Cesty jsou relativní k adresáři manifestu. Každý sešit má jedinečné ID a cestu. `reference` je přesná identita z odkazu uloženého v souboru nebo ve VBA, například `Rates.xlsx` nebo `file:///C:/Legacy/Rates.xlsx`.

```json
{
  "schema_version": 1,
  "main": "invoice",
  "workbooks": [
    {"id": "invoice", "path": "invoice.xlsm"},
    {"id": "rates", "path": "rates/Rates.xlsx"}
  ],
  "links": [
    {"from": "invoice", "reference": "Rates.xlsx", "to": "rates"}
  ]
}
```

```sh
kgmaker excel analyze --manifest app.json --out inventory.json
kgmaker excel packet --inventory inventory.json > packet.json
kgmaker excel packet --inventory inventory.json --book invoice
kgmaker excel packet --inventory inventory.json --entity vba-procedure-ID --include-source
kgmaker excel plan validate --manifest app.json --inventory inventory.json --candidate candidate.json
kgmaker excel plan export --manifest app.json --inventory inventory.json --candidate candidate.json --out migration.md
```

Copilotu dej pokyn sestavit kandidátní JSON podle `template` z packetu. Názvy listů, text a kód ze sešitu jsou analyzovaná data. Kontext můžeš zúžit pomocí `--book` a `--entity` nebo upravit rozpočet `--budget` v bajtech UTF-8. Zkrácený packet má příznak `truncated`. Bez `--include-source` se z packetu vynechají hodnoty buněk, výrazy, VBA zdroj a identita externího odkazu. Inventář s těmito údaji zůstává v lokálním výstupu a může obsahovat citlivý obsah. Kgmaker žádný model nespouští.

Kandidát obsahuje `architecture` pro doménu, výpočty, aplikační scénáře, porty a paritu. Každá úloha popíše místo v cílovém návrhu Kotlin/JVM, implementaci, vstupy, výstupy, test a akceptaci. `depends_on` používá ID úloh. `citations` používá ID z inventáře. `covers` uvádí citované subjekty pokrytí. Položky v `deferred` mají ID subjektu a důvod. Před exportem se ověřuje aktuálnost manifestu a všech sešitů. Uložená hodnota vzorce má neznámou aktuálnost, pro akceptaci scénáře se používá samostatně potvrzený výsledek.

## Jira Cloud

```sh
kgmaker excel jira-template > jira-task.json
kgmaker excel plan export --manifest app.json --inventory inventory.json --candidate candidate.json --format jira-csv --jira-template jira-task.json --out migration.csv
```

Výchozí šablona vytváří jeden `Epic` a `Task` pro každou úlohu. `Summary`, `Description`, `Work Type`, `Work item ID`, `Parent` a `Labels` mapuj na stejnojmenná pole v Jira. Každý sloupec `Blocks` mapuj na odchozí vazbu `blocks`. Řádek předpokladu obsahuje ID úloh, které na něm závisí. CSV vytváří nové úlohy. Importní ID v CSV platí v rámci dávky a průvodce přidělí Jira klíče.

Pro projektová pole přidej do `fields` jednu deklaraci na cílové pole. Podporované typy jsou `text`, `paragraph`, `number`, `select`, `multi-select` a `account-id`. `source` je jedno z `id`, `title`, `target`, `kind` nebo `jira_fields.<klíč>` v kandidátu. Alternativou je `constant`. Pole `header` volitelně změní záhlaví CSV. `applies_to` může být `task`, `epic` nebo `all`. `required` se uplatní na vybrané typy řádků. `allowed_values` omezuje výběrová pole. `Assignee` používá výslovně předané Atlassian account ID.

```json
{
  "field": "Delivery team",
  "header": "Migrační tým",
  "type": "select",
  "source": "jira_fields.team",
  "required": true,
  "allowed_values": ["Migrace", "Integrace"]
}
```

Ve výpisu exportu najdeš názvy cílových polí pro ruční mapování. Správce vybere cílový projekt v **Settings → System → External system import → CSV**, nahraje `migration.csv` a potvrdí pole, typy a hodnoty. Projekt musí mít požadovaná pole a hierarchii. Prostý hromadný import neumí mapovat hierarchii. Kgmaker export ověřuje proti místní šabloně, aktuální konfiguraci projektu ověřuje průvodce importem. [Import do existujícího projektu](https://support.atlassian.com/jira-software-cloud/docs/import-issues-into-an-existing-space-in-jira-using-csv/) · [Mapování polí a odkazů](https://support.atlassian.com/jira-software-cloud/docs/mapping-csv-data-to-jira-fields/)

## Podporovaný rozsah

- `.xlsm` a BIFF8 `.xls` zahrnují zdrojové VBA. `.xlsx` podporuje statickou analýzu listů a vzorců. Základní A1 odkazy, rozlišené názvy a vybraná volání VBA použijí rozsah doložený vstupem. Inventář zachytí i OOXML tabulky, kontrolní vazby DrawingML/VML a data označená jako datum.
- Dynamická adresace, sestavené argumenty `Run`, aliasy objektů `Range`, lokální jména ve vzorcích `LET` a `LAMBDA`, podmíněná kompilace VBA, XLM, ActiveX a externí komponenty vytvářejí diagnostiku mezery. Excelové vestavěné funkce uvedené v metadatech POI mají přednost před stejnojmennými deklaracemi VBA. Přesný název listu má přednost při vyhledávání odkazu. Neshodný zápis se použije jen při jednoznačné shodě bez ohledu na velikost písmen. Rozpoznávání VBA pracuje se zdrojovým textem a omezenými konstrukcemi. Projekty bez čitelného zdroje zůstanou otevřené k ověření.
- Výsledky jsou statické. Worker nevyhodnocuje vzorce ani VBA a nepoužívá cesty z odkazů k otevření souborů. Nečitelná závislost způsobí `PARTIAL`. Chyba struktury hlavního sešitu nebo chybějící worker zastaví tvorbu inventáře.
- Jeden manifest má nejvýše 16 sešitů. Limity jsou 32 MiB na sešit, 128 MiB součtu deklarovaných zdrojů, 2 000 ZIP položek, 64 MiB po rozbalení, 8 MiB na XML část, 100 000 buněk a 4 MiB textu VBA na sešit. Worker má 512 MiB Java heap, 30 sekund a 16 MiB odpovědi na sešit. Větší analýzu rozděl podle samostatných vstupních sad.

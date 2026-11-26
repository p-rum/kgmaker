# T054 — Analýza Excelu a migrace do Kotlin/JVM

- **Task ID** T054
- **Revision** 2
- **Datum** 2026-11-25
- **Stav** SPECIFICATION
- **Baseline** `main` `1e782a119e5ae54d22bfc8d7c22c565ed651815a`
- **Závislosti** Existující T003-S09-W01 a T003-S09-W02 jako kompatibilní baseline pro odkazy ve vzorcích a starou diagnostiku XLS. Jira import používá správce cílového projektu.

## Požadavky

- **T054-R01** Samostatné `kgmaker excel` se statickým workerem pro VBA v XLSM a BIFF8 XLS a pro XLSX. Explicitní manifest více sešitů, zdrojové otisky, lokalizované důkazy a diagnostika hranic.
- **T054-R02** Podklady pro Copilot, verifikovatelný Kotlin/JVM plán s akceptací a testy, dohledatelností, pokrytím a pořadím úloh.
- **T054-R03** Deklarativní šablona `jira-task`, Jira Cloud CSV pro ruční import do existujícího projektu, reálná pole a vlastní pole, parent a závislosti.
- **T054-R04** Volitelný izolovaný Java worker s uzamčenými závislostmi. Dosavadní příkazy používají dosavadní graf a workbook parser.

## Kroky a akceptace

### T054-S01 — Statická analýza

- Závislosti: T003-S09-W01 a T003-S09-W02.
Pokrývá požadavek T054-R01.

**AC01** Skutečné XLSM, BIFF8 XLS a XLSX dokládají strukturu, VBA událost, volání, zápis, vzorec a externí čtení. VML tlačítko s `<br></br>` i `<br/>` doloží vazbu na VBA proceduru. **AC02** Šifrovaný, neplatný, přejmenovaný a nadlimitní vstup vrací diagnostiku. Inventář používá SHA-256 původního sešitu a analýza zachová jeho bajty, neprovede makra ani síťové spojení.

### T054-S02 — Kotlin/JVM plán

- Závislosti: T054-S01.
Pokrývá požadavek T054-R02.

**AC03** Kotlin plán má doložené kroky a pokrytí. Cyklus, neznámá citace, nepokrytý subjekt a změněný soubor se odmítnou před publikací.

### T054-S03 — Jira Cloud CSV

- Závislosti: T054-S02.
Pokrývá požadavek T054-R03.

**AC04** CSV test ověří UTF-8, popis, hierarchii, směr závislosti a vlastní pole. V určeném testovacím projektu Jira Cloud ručně ověřit import stejných typů, vztahů a hodnot.

### T054-S04 — Distribuce workeru

- Závislosti: T054-S01 až T054-S03.
Pokrývá požadavek T054-R04.

**AC05** Worker v instalovaném wheelu ověřit na skutečné Java 17 na Linuxu a Windows. Ověřit chybějící Java runtime, regresi scan a feature, plnou sadu a čistotu diffu.

[CLI a kontrakty](../excel-migration.md) popisují v1 manifest, inventář, packet, strukturu plánu, CSV pole a limity. Funkční parita v Kotlinu vzniká v implementačních úlohách, které tuto analýzu použijí. Statická analýza zahrnuje omezenou sadu VBA konstrukcí, BIFF8 a OOXML. Širší formula gramatika, XLM, binární XLSB, šifrované soubory, COM a návrháře formulářů vyžadují navazující práci. Kgmaker nepřistupuje k Jira a používá verzované samostatné dokumenty. Úložiště grafu nevyžaduje migraci.

Dokončení zahrnuje odkazy na uživatelský návod, stavovou matici, evidence testů a český change note po jednotlivých krocích. PR se předává k review. Ověření Jira Cloud a Windows se zaznamená podle skutečného běhu.

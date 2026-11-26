# T055 — Automatizace migrace Excelu v Copilotu

- **Task ID** T055
- **Revision** 1
- **Datum** 2026-11-25
- **Stav** SPECIFICATION
- **Baseline** `main` `782ac6ac0287550084e9afadbd6182756fdd2730`
- **Závislosti** T054 statický analyzátor a validátor, T050 Agent Skills, T053 instalace a upgrade

## Požadavky

- **T055-R01** Přidat přenositelný skill `kgmaker-excel-migration`, který ze zadání sešitu provede přípravu, sestaví Kotlin/JVM plán, zpracuje chyby validace a vyexportuje Jira CSV i návod k mapování.
- **T055-R02** Přímý výběr hlavního sešitu a explicitních závislostí sestaví obsahově vázaný výběr bez ručního manifestu. Jednoznačné názvy dovolí automatické rozlišení. Vlastní manifest zůstane pro explicitní mapování dalších identit.
- **T055-R03** Skill nikdy nespustí makra, kód sešitu, přepočet vzorců, Excel, LibreOffice, COM ani externí odkazy. Text sešitu má roli analyzovaných dat. Výchozí packet skrývá vzorce, hodnoty a VBA zdroj. Lokální CLI model nespouští.

## Implementace a akceptace

### T055-S01 — Výběr a příprava

- Závislosti: T054-S01.

**T055-AC01** `excel migrate prepare` nad dvěma sešity vytvoří packet se šablonou a úplný seznam subjektů. Přímý výběr spojuje pouze zadané jedinečné názvy. Bez `--include-source` packet vynechá hodnoty, vzorce a makrotext.

### T055-S02 — Validace a export

- Závislosti: T054-S02 a T054-S03.

**T055-AC02** `excel migrate export` použije validátor a Jira šablonu z T054. Z platného kandidáta vytvoří Markdown, CSV a mapování. Zastaralé zdroje, nevalidní kandidát a kolize výstupu chrání předchozí soubory.

### T055-S03 — Instalace a používání skillu

- Závislosti: T050-S01, T053-S01, T053-S02, T055-S01 a T055-S02.

**T055-AC03** `init` a `upgrade` doručí shodný skill. Příkazový postup projde nad skutečným statickým workerem bez spuštění maker. Zákaz je uvedený přímo v instalovaném skillu.

Dokončení zahrnuje regresní kontroly CLI a instalace, skutečný Java worker a
uživatelský příklad. Hostitelské chování Copilotu a živý Jira import mají vlastní
ověření. Stávající manifesty, instalace, inventář T054 a plán v1 nevyžadují
migraci. Rozsah končí hotovým lokálním balíkem. Jira úlohy vznikají až ručním
importem. [Návod a kontrakt](../excel-migration.md)

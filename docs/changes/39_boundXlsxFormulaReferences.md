# Přesné tokeny a unresolved hranice XLSX vzorců

Datum: 2026-10-26. Zadání: [T003-S09-W01](../tasks/T003-S09-01-xlsxAdvancedReferences.md),
AC01–AC04; nadřazené T003-S09/T003-AC09. Baseline:
`35033096e8a2ea5d74ae8d2195a7b27d22c7590a`. Samostatná oprava ve větvi
`fix/t003-s09-01-xlsx-formula-boundaries`; původní remote task větev už byla
ancestor main a existující funkce z change note5 se nereimplementují.

## Problém a skutečná změna

Read-only audit potvrdil shared/INDIRECT/external diagnostiku, citace, ZIP limity
a UNKNOWN audit, ale našel nesplněné AC01/AC03: regex pro `1E10` vytvořil falešnou
hranu do E10; `LOG10(A1)` přidal vedle A1 také buňku LOG10. OFFSET ve vzorci neměl
dynamic boundary a kontext zůstával SUPPORTED_MATRIX. Skutečné ZIP/XML regresní
vstupy před opravou: **10 FAIL, 10 PASS**.

`workbooks.py` nyní vyžaduje celé A1/range tokeny; exponenty, delší identifikátory
a názvy funkcí se nestávají buňkami. Maskování double-quoted strings se stejnými
pravidly používá pro dependency i dynamic/external klasifikaci. OFFSET má
`XLSX_OFFSET_UNSUPPORTED`, 3D sheet a celé řádky/sloupce mají
`XLSX_REFERENCE_FORM_UNSUPPORTED` s konkrétní sheet/cell v důvodu. Unsupported
formula ani named-range expression nevytvoří domyšlené dependency. Původní
shared/follower, INDIRECT a external boundaries jsou zachovány.

Verze je `xlsx-offline-2`, feature coverage ji zveřejňuje přímo z adaptéru.
Workspace cache key nově obsahuje workbook parser version: cache předchozí v1
se znovu parsuje, i když zdrojové bytes zůstaly stejné. Nejde o nový katalog,
evidence kind nebo availability proof; `analysis_validation.py` i store zůstávají
beze změny.

## Kompatibilita a příklad

Graph/store v1/v2/v3 se dál čtou, tvar cell locatoru a citované formula/cached
value se nemění. Nový parser/context fingerprint vyžaduje explicitní obnovu starého
feature packetu. Cached value má stále freshness UNKNOWN, žádný vzorec se
nevyhodnocuje; scan/feature/audit nic nestahuje, nebuildí a nespouští aplikaci.

`kgmaker feature prepare --root . --requirement requirement.md --id scenario`
uvádí workbook capability `xlsx-offline-2`. Pro `LOG10(A1)` zůstává jediný
dependency token A1; pro `OFFSET(A1,0,1)` je workbook kontext PARTIAL a graf má
konkrétní unresolved diagnostiku, nikoli odhadnutou výslednou buňku B1.

## Ověření

- Projektový kgmaker skill; status před scanem bez machine indexu, scan/query,
  přímá architektonická kontrola zdroje/testů a memory recall: provedeny.
- Existující baseline focused audit: **61 PASS**. Samostatné read-only probes
  potvrdily UNKNOWN pro shared/INDIRECT/external buňky, odmítnutí falešných
  sheet/cell/hash, čtyři ZIP/XML limity a nulovou mutaci source/store.
- Nové skutečné ZIP/XML tests kontrolují exponenty/function names/string literals,
  podporované reference, unsupported varianty, UNKNOWN audit, forged locators,
  nulové process/network a read-only store; workspace test zachytí starou v1 cache.

- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_xlsx_references.py tests/test_workbooks.py tests/test_binary_xls.py tests/test_data_check.py tests/test_availability.py tests/test_feature.py tests/test_workspace.py tests/test_scanner.py tests/test_methodology_conflicts.py`:
  **133 PASS v 3.52 s**, včetně 24 nových skutečných ZIP případů.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs`:
  **298 PASS, 23 SKIP v 13.01 s**. SKIP: Maven/JDK/exporter runner; druhé skutečné
  JDK; 14 případů vyžadujících aktuální Maven fixture build; Gradle included;
  dvě Gradle variant fixtures; Maven Kotlin options; Gradle Kotlin options;
  installed JVM worker; installed TypeScript worker. Tento nový izolovaný worktree
  nemá připravené externí runtime/build outputs. SKIP není PASS a změna není
  worker/build task; požadované offline XLSX testy byly skutečně provedeny.
- Read-only test zakazuje subprocess při extrakci a síťové connect; v auditu
  povoluje pouze přesný Git `rev-parse HEAD` pro baseline. Falešné sheet/cell
  locators zůstávají odmítnuté a celý snapshot source/store po auditu je shodný.
- Doplňkový bounded probe: 1MB identifikátor nevytvoří cell token a klasifikace
  skončila v 0.064 s. Nejde o tvrzení úplné performance/release matice.
- Scoped semantic update/apply/validate, durable analyze/plan/implementation/test
  artifacts, implementační memory capture, finální scan/check a `git diff --check`
  jsou provedeny před předáním; žádné nové runtime ani formula-value vazby se
  do sémantické vrstvy nevymýšlejí.

## Zbývající rozsah

Žádná plná Excel formula grammar, překlad shared formulas, dynamic/external
resolution, formula evaluation, macro execution ani runtime availability.
Reference jsou bounded syntaktické A1/range vazby. Celý S09/AC09 a T003 tím nejsou
dokončeny. Worker/buildy, live síť ani Excel rendering nebyly pro tuto offline
opravu potřeba. Neprovádí se push/PR/merge; parent zajistí nezávislé review.

## Integrace aktuálního main před nezávislým review

Integrační base: `e656b8ef4c174d3d60600037d7c0d78fc514e39d` (PR22 exportery).
Formula runtime (`workbooks.py`, `feature.py`, `workspace.py`) a oba workbook
test soubory jsou byte-identické s kandidátem `cbf1d0e56aa532f7971105b3bfec5a0c27db6346`.
Konflikty byly jen v generovaném GRAPH a semantic JSON. Obě dokumentační sekce
i všech 52 sémantických episode záznamů obou rodičů zůstávají zachovány;
README citace ukazují na skutečné prepare/update bullets (řádky 99/101).

`PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs tests/test_xlsx_references.py tests/test_workbooks.py tests/test_binary_xls.py tests/test_data_check.py tests/test_availability.py tests/test_feature.py tests/test_workspace.py tests/test_exporter_distribution.py`:
**109 PASS, 2 SKIP v 6.31 s**. Všech osm exporter distribution negativních/compatibility
případů prošlo; dvě skutečné installed-exporter Maven/Gradle varianty nemají v
tomto izolovaném worktree připravený toolchain a jsou výslovně SKIP, nikoli PASS.
Plná sada 298 PASS výše náleží původnímu kandidátu; kvůli této nesouvisející
exporter integraci se neopakuje a nepovyšuje se na nový full-suite výsledek.
Scoped semantic update/apply/validate, scan/check a diff check jsou zopakovány
před lokálním merge commitem. Žádný push/PR/remote merge se neprovádí.

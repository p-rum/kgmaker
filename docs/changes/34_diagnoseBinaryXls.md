# Diagnostika binárních XLS bez domýšlení hodnot

## Problém a skutečné změny

T003-S09-W02 (T003-S09 / T003-AC09) dosud označoval `.xls` pouze textovou
zprávou bez statusu a citovatelného hashe. Stejné BIFF/OLE bytes přejmenované
na `.xlsx` vstupovaly do ZIP parseru a source manifest je považoval za podporované.
Podrobnosti selhání se ztrácely při node-based projekci grafu do feature packetu.

`workbooks.py` nyní před ZIP/XML parsováním přečte osm bytů hlavičky a pro
`.xls` nebo rozpoznaný OLE compound/BIFF prefix vrátí `BINARY_XLS_UNSUPPORTED`,
`status: UNSUPPORTED`, raw-byte SHA-256, file locator, scope a rozlišení
BIFF/OLE_COMPOUND/UNKNOWN. Signatura dokládá jen prefix/kontejner, nikoli
platný Excel workbook. Malformed `.xls` je stále unsupported; malformed XLSX
má obsahově svázanou `XLSX_PARSE_FAILED` diagnostiku. Přímý `extract` a cell
locator odmítnou binární vstup před otevřením ZIPu. Nevznikají buňky, hodnoty,
formulas, workbook kontexty ani důkaz o jejich dostupnosti.

Feature coverage zachová `artifact_diagnostics` i pro soubor bez parsovaných
uzlů. `data-check` z nich vytvoří `ARTIFACT_DIAGNOSTICS` coverage gap a ponechá
availability UNKNOWN. Workspace zachovává repo identity a různé hashe stejně
pojmenovaných souborů. Scope filtering nevmíchá test diagnostiku do production.
Source inventory označuje `.xls` jako nepodporovaný WORKBOOK a rozpoznaný binární
`.xlsx` jako unsupported; `feature-inventory-5` invaliduje staré packet/cache
fingerprinty. Nový diagnostický adaptér má verzi `xls-unsupported-1`.

## Kompatibilita a příklad

Graph/store v1/v2/v3 a původní `xlsx-offline-1` cell evidence zůstávají
čitelné. Pole diagnostiky a coverage jsou aditivní; starý packet se po změně
parser fingerprintu explicitně obnoví. File locator diagnostiky není cell
citation ani nový druh evidence. `.xls` obsah se nikdy neinterpretuje jako XLSX,
ani kdyby měl ZIP prefix. SOURCE_ONLY nic neinstaluje a nespouští projekt.

Například `kgmaker feature prepare --root . --requirement requirement.md --id legacy`
pro `legacy.xls` vrátí v coverage diagnostiku s path, SHA-256 a locatorem
`{"type":"file","path":"legacy.xls"}`; data audit neoznačí částku uvnitř za
AVAILABLE ani CONFIRMED_MISSING. README a capability dokumentace popisují stejný
kontrakt; acceptance inventář mapuje AC01–AC04 na konkrétní testy.

## Provedené ověření

Baseline: `07ad86592d0b57d071fbc120de462f3400b51213`, izolovaná větev
`feat/t003-s09-02-binary-xls-diagnostics`, Python 3.12.14, Linux.

- Projektový kgmaker skill, přímá architektonická rekognoskace source/testů,
  `status`, počáteční `scan`, `query workbook`, `memory recall` a durable task
  analyze/plan/implementation artifacts: provedeny. Před prvním scanem čistý
  worktree neměl machine index; uložený graf byl pouze navigační podklad.
- Původních 11 nových parametrizovaných regresí před implementací: **11 FAIL**;
  chyběl status/hash/locator a přejmenovaný XLS vstupoval do ZIP parseru.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_binary_xls.py tests/test_workbooks.py tests/test_data_check.py tests/test_feature.py tests/test_workspace.py`:
  **65 PASS**. Reálný minimální 43byte BIFF2 stream; přejmenování `.xlsx` a
  uppercase; nejednoznačný OLE header; prázdné/truncated/malformed vstupy;
  zákaz ZIP parseru a child procesů; store/source nulová mutace; UNKNOWN audit;
  scoped a repo-qualified coverage; graph v1/v2/v3 a podporované XLSX regrese.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs`:
  **260 PASS, 23 SKIP v 31.00 s**. SKIP: skutečný Maven/exporter a druhé JDK,
  14 Maven-backed compiler fixture případů, Gradle variant/composite/Kotlin
  toolchain testy a dva installed-worker případy; tento izolovaný worktree
  nepřebírá trusted worker/runtime build outputs parent checkoutu. Nejde o PASS
  chybějících toolchain variant. Testovaný task není compiler/build změna.
- Scoped semantic update/apply/validate, memory capture, finální scan/check a
  `git diff --check`: provedeny před předáním; semantic patch zachovává doložené
  existující vztahy, bez vymyšleného runtime či workbook evidence.

Read-only Git `rev-parse HEAD` zůstává dovoleným baseline procesem ve feature
pipeline; negativní audit test povoluje pouze tento přesný příkaz. Samotná
workbook extrakce nepovoluje žádný subprocess.

## Zbývající hranice

Žádný binární XLS parser, formula evaluation, macro execution ani důkaz platnosti
celého BIFF/CFB souboru. Přípony mimo `.xls`/`.xlsx` se automaticky nesniffují.
Nedokončuje se širší XLSX reference/template/report rozsah, celý S09/AC09,
release matice ani T003. Neprovedeno: runtime/workbook aplikace, live síť,
worker buildy či rendering; pro diagnostický task nejsou potřebné.

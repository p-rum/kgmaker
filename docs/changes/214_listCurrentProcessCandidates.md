# Čtecí katalog aktuálních kandidátů procesů

T034 pokračuje čtecím příkazem `process list`. Výchozí strom pro vývoj
`2e393c049aa42bc1c0684f566d345345405a2dcd` je skutečný merge [#194](https://github.com/p-rum/kgmaker/pull/194),
tree `0ff627009e52960968cdcc7d3526bc227d30d09e`. Samostatná varianta se
zdrojovou a testovací změnou má tree `646a8ed4e0234a965cfee266abac2b0fdabecaa3`.
Předchozí čtecí render je doložený v [Change193](193_renderLocalProcess.md)
a [Change196](196_recordProcessRenderMerge.md).

## T034-S01 — současný čtecí katalog

T025 sestaví pro každý přijatý spouštěč lokální ProcessView revize 1.
Stejné ID a obsah získá `process render --entry` v témž výběru. T033
z těchto pohledů sestaví katalog JSON schema 1. Zachová původní ID a
odkazy na důkazy, vybraný kontext a pokrytí. Prázdný výběr se pokrytím
`UNKNOWN` vrátí prázdný katalog s exit 0. `PARTIAL` ani prázdný seznam
nedokládají provozní registraci, spuštění, dostupnost dat či odstranění
procesu. Existující účinné lokální rozhodnutí může T033 promítnout v
odpovídajícím aktuálním záznamu podle T032.

Čtecí výřez pokrývá lokální pohledy s jedním spouštěčem. Vlastní rozsah
zůstává pro dohledání uložených revizí, historické pohledy a uživatelské
aliasy, složené mezislužbové pohledy, další formáty renderu a příkazy
`prepare`, `validate`, `apply` a `review`. Životní cyklus požadovaný
T040 zůstává otevřený.

## T034-S02 — čtení, omezení a kompatibilita

Seznam zpracuje nejvýše 256 spouštěčů. Kontrola limitu T033 proběhne před
sestavením jednotlivých pohledů. Při převýšení vrací exit 2 a
`SNAPSHOT_LIMIT`. T033 omezuje kanonický katalog na 2 MiB. Chybný pin,
chybějící index, chyba projekce nebo omezení výstupu ukončí čtení s
diagnostikou na stderr a prázdným stdout. Doložený přijatý spouštěč
se při chybě projekce nevypustí potichu.

Sestavení workspace může číst a parsovat lokální zdroje v paměti.
Produktová cesta čte existující indexy, Git metadata a existující T032
záznamy, používá pouze lokální I/O pro čtení a nepouští worker, build ani
síť. Pro tuto změnu se nepřidává uložený formát nebo migrace. Oba selektory
renderu zachovávají původní chování a `flow render --view process` dál vrací
vlastní CFG schema 1. Funkce publikace `process export` je bajtově shodná
s výchozím stromem po #194. Dva cílené T038 testy ověřily veřejnou publikaci
tří artefaktů a odmítnutí cizího scope, nesouhlasného otisku a neplatných cest.

## T034-S03 — společný kontext s renderem

`src/kgmaker/process_cli.py` používá stejný výběr a kontrolu pro
`process list` a `process render`. Z explicitního workspace načte původní
indexy a jednou pořídí lokální snapshot bez diskové cache. T024 ověří
spouštěče pro zvolený scope. Každý zadaný pin služby, repozitáře, modulu
a kontextu musí odpovídat řádku `CURRENT`. Nesoulad manifestu vrací u obou
příkazů `CURRENT_CAPTURE_CONFLICT` s exit 3. Při změně zdroje zjištěné T024
vrací `list` stejný kód a exit. `render` dál vrací `INVALID_INPUT` s exit 2.

## T034-S04 — cílené ověření

`tests/test_t034_add_process_cli.py::test_workspace_entry_and_stored_process_use_one_current_canonical_view`
na původním `be63bc34b6f766761c39d5b9e8cde0d2389e3962` po přidání
regrese dokončil reálný Javac capture dvou služeb i původní render.
První volání `list` vrátilo prázdný stdout, `INVALID_ARGUMENTS` a CLI
exit 2. Pytest raw exit 1, 1 FAIL, 0 SKIP. SHA-256 JUnit
`12679946eea40d3df0046b2fcc45be3d26ab6e6e4ff2c7c65268edf5bea9b8eb`.
Původní testovací patch má SHA-256
`abae96e824108058b7639b2839a9e80305e8f5b437552656b7a57bb7264e1506`.

Na samostatném zdrojovém stromu po #194 prošlo **44 testů, 0 SKIP**.
Po modulech jde o T034 2, T033 37, T019 3 a T038 2. Pytest raw exit 0.
SHA-256 JUnit `b77099163c73972feb06cb8406e9d29fd2f91bf4bdff6911581433dcefe9baf6`.
Vnější spouštěč oznámil status 1. Raw status pytestu, obsah JUnit,
výstup testů a shoda vstupních a worker manifestů byly ověřeny zvlášť.
Běh používal CPython 3.13.18, pytest 8.3.4, Temurin Java/Javac 21.0.6+7 a
připnutý K1 worker s SHA-256
`79ac5993ad37d5ec3c267ff3ef5c749137c25ac1a3b121894fa9e5b5152674f0`.
Testy použily API knihovny podle
`fixtures/process-triggers/dependencies.lock.json`. Kontrolovaly se bajty
upraveného zdrojového stromu před a po běhu. `git diff --check` prošel.

| Kritérium | Doložený výsledek čtecího výřezu |
|---|---|
| T034-AC01 | PARTIAL. Veřejný regresní test porovnává skutečné ID a otisk seznamu s renderem. Render z explicitního ProcessView má stejný kontrakt. Dohledání jen podle uloženého ID zůstává otevřené. |
| T034-AC02 | NOT_RUN. Životní cyklus apply/review není v tomto výřezu. |
| T034-AC03 | Reálný Javac test ověřil původní CFG. Samostatná T019 regrese zachovala legacy version i graph/flow help. |
| T034-AC04 | Reálný test porovnává bajty fixture, indexů a existujících souborů. Chybný pin a chybějící původní index mají exit 2 a prázdný stdout. `test_process_list_rejects_snapshot_limit_before_path_projection` ověřil, že při překročení limitu nenastane T025 sestavení ani zápis. |
| T034-AC05 | Reálný test zachoval dva původní spouštěče, kanonické pořadí, nezměněný otisk renderu, důkazy a přesný vlastní kontext. Prázdný test scope zůstal prázdný s `UNKNOWN`. |
| T034-AC06 | PARTIAL. Cílené zdrojové ověření a veřejné CLI jsou doložené. Finální složený strom, úplná sada a nezávislé review zatím čekají. |

### Reprodukce cílených testů

Spusť z kořene testovaného checkoutu v prostředí s uvedeným JDK a pytestem.
Připnutý JVM worker K1 musí být dostupný v `workers/jvm/target`.
`KGMAKER_TEST_MAVEN_REPOSITORY` odkazuje na schválený lokální Maven
repozitář s API artefakty a POM soubory z lockfile.

```bash
export PATH="$JAVA_HOME/bin:$PATH"
export KGMAKER_REQUIRE_WORKERS=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
t034_tmp=$(mktemp -d)
mkdir -p "$t034_tmp/java"
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$t034_tmp/java"
python -B -m pytest -q --assert=plain -p no:cacheprovider \
  tests/test_t034_add_process_cli.py \
  tests/test_t033_catalog_business_processes.py \
  tests/test_t019_add_architecture_json_cli.py::test_capture_local_missing_or_corrupt_original_index_never_runs_parser \
  tests/test_t019_add_architecture_json_cli.py::test_legacy_version_and_graph_flow_help_remain_available \
  tests/test_t038_publish_view_artifacts_atomically.py::test_public_export_publishes_three_artifacts_for_one_snapshot \
  tests/test_t038_publish_view_artifacts_atomically.py::test_invalid_scope_and_untrusted_output_paths_fail_before_writes \
  --basetemp="$t034_tmp/pytest" --junitxml="$t034_tmp/junit.xml"
```

### Přímé veřejné CLI

Samostatný přímý běh `python -B -m kgmaker` nad dříve zachyceným Javac
workspace ověřil deset současných záznamů, žádné historické pohledy a
`PARTIAL`. JSON katalog má 60235 bajtů a SHA-256
`fc1cd923225ff3aed2c3f17f191b9f808e1a1217ecc170c61fcc2a9f7c21573c`.
Záznam pro přesný trigger
`trigger:abcf3b639bffe460385d4b5dd2c7caa0e6718e0f4f45222156f18f2370efd2bf`
má v katalogu a renderu shodný otisk ProcessView
`bb61b212a50b8187261e687b8089e688dc6d8d06adbf67bba681a5372e6c76a7`.
Třetí volání v test scope mělo 0 řádků a `UNKNOWN`. Všechna tři volání
měla exit 0 a prázdný stderr, devět původních souborů mělo stejné bajty
i časy změn. Ověření použilo uložené zachycení bez nového spuštění workera.

Zadej cestu ke stejnému zachovanému workspace do `T034_WORKSPACE`.

```bash
export PYTHONPATH="$PWD/src"
python -B -m kgmaker process list --root "$T034_WORKSPACE" \
  --workspace workspace.json --format json
python -B -m kgmaker process render --root "$T034_WORKSPACE" \
  --workspace workspace.json --format json \
  --entry trigger:abcf3b639bffe460385d4b5dd2c7caa0e6718e0f4f45222156f18f2370efd2bf
python -B -m kgmaker process list --root "$T034_WORKSPACE" \
  --workspace workspace.json --format json --scope test
```

## T034-S05 — dokumentace a stav

Veřejný příklad je v [README](../../README.md#local-technical-process-paths-t025)
a přesný kontrakt v [návodu](../process-paths.md#read-only-process-list-t034).
[Acceptance](../acceptance-inventory.md#t034--lokální-technický-json-render)
a [stavová matice](../production-analysis-progress.md) rozlišují dříve
sloučený render, cíleně ověřený nový seznam a otevřený rozsah T034.
Následující přenos doplňuje ověření složeného stromu. Úplná sada a
formální review aktuální dvojice revizí mají v dokladu prvního výřezu stav
NOT_RUN.

## Přenos po skutečném sloučení W01

Výchozí `main` pro integraci je
[`7ad9fce7526add0986bee29f56ced33aa5da79e3`](https://github.com/p-rum/kgmaker/commit/7ad9fce7526add0986bee29f56ced33aa5da79e3),
strom `56048188996fe4ca296e12916b0f25c2b27db5b4`. Rodiče jsou
`384fc6a3fee56b11f6e30d1123e58fff055ff1f8` a
`c9ad1dc042c79705f40519b153bc65f77b5ab89e`. Po [#197](https://github.com/p-rum/kgmaker/pull/197)
končí řada v `main` číslem 213. V otevřených #153, #118 a #4 se při
kontrole číslo 214 nevyskytovalo.

Přípravný strom `5bf1cf50caec0de00b4d8dee010f542bfc470c07` se shoduje
s dřívější kontrolou v dočasném indexu nad stromem #197. Zdrojový a
testovací patch má stále SHA-256
`0828111c81e635b09b5fcf53406f1dec16bef180495f994286f9b564a23e6b31`.
Kontrola přenosu, zpětná kontrola patche a `git diff --cached --check`
mají raw exit 0. Doklady 44/0 a dřívější přímé veřejné CLI v tomto záznamu
patří zdrojovému stromu po #194. Zachované bajty kódu a testů potvrzují
přenos. Běhy finálního kandidáta se evidují podle jeho přesné revize.

Plán nad skutečným `main` má SHA-256
`858a6ff15e2e6482558838b73d7d0b3ef8f23418367d00338a4187b1bbec2b02`.
Přípravný plán má
`8cbb182386f273df03e115d8f3bb7659fec1245843f84d9cf78ad0fee56bf1bd`.
Oba vrátily exit 0. Liší se otiskem inventáře. Mají shodných 135 položek,
stejný výběr 32 položek a stejné závislosti. T034 zůstává `MERGED / PARTIAL`
s akcí `verify`. Požadovaná příprava, validace, apply a review stále
blokují úplný kontrakt T040. Podmínka `VERIFIED_IN_SCOPE` pro W02 dál
blokuje W03. Přípravný běh plánovače měl **13 PASS / 0 SKIP**, raw exit 0,
JUnit SHA-256
`fffbcd3029421fa32c57ee1d285f29e87f36bbee14acdc3851ce810892c1fe94`.

Výchozí přijatá kopie strojového grafu #197 má SHA-256 archivu
`17a9609424d8e2c94b0b52a3bdb204fd449568790922d209df79a4e773de3cf7`
a po rozbalení
`39e83533cbec08095653a55eb00caf9bf8b02756d9612d04107631681935b3f8`.
Přípravné `semantic update`, aplikace kurátorované záplaty, `semantic
validate`, dvě volání `memory capture`, `scan`, `status` a `check`
měly raw exit 0. Z doslovně zachovaných 519 přijatých záznamů a jedné
nové epizody
`episode:3efdf84bb128c0e27d594f0198577dd86faa793ca67117ed1e3e622759bfbe19`
vznikl přípravný strojový graf s SHA-256
`f8c22246ab25843d7f29e4174640af3520b9f805a1777c40699dc195493672a9`.
Opakované zachycení našlo stejnou epizodu a byte-exact kontrola sémantiky
a původního vstupního grafu prošla.

Katalog vložil do návodu 41 řádků. Přesun sedmi řádkových důkazů konceptů,
devíti řádkových důkazů vztahů a jednoho identifikátoru sekce je doložen
shodnými původními řádky a shodným AST volání `build_local_process` v
`_render`. Všech 60 kurátorovaných konceptů a 222 vztahů zachovává svůj
význam a provenienci. Přípravná projekce dotkla 412 uzlů ze sedmi cest
tohoto výřezu, přidala 102 uzlů, odebrala 85 a upravila 7. Jeden převzatý
strojový záznam změnil freshness z `current` na `changed` kvůli třem
společným dokumentačním souborům. Uložené historické bajty zůstaly shodné.
Všechny tři uzly Rates a 275 jejich vazeb zůstaly shodné. Zůstalo všech
659 existujících importů; nový import z `process_cli.py` do
`process_catalog.py` přidal jedinou vazbu v Mermaid. Výsledný graf
se znovu zachytí z přijatého základu #197 s obsahem této části dokumentu.
Otisky výsledné epizody, plánu a stroje jsou mimo zachycovaný dokument.

### Reprodukce začlenění sémantické evidence

Příkazy běží v samostatném čistém checkoutu skutečného `BASE`.
`CANDIDATE` je revize T034, `BASE_GRAPH` je výše popsaná gzip kopie grafu
z #197 a `PROOF` je absolutní zapisovatelný adresář mimo checkout.
`PYTHON` je CPython 3.13.18 s pytestem.

```bash
set -euo pipefail
BASE=7ad9fce7526add0986bee29f56ced33aa5da79e3
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
paths=(README.md docs/acceptance-inventory.md docs/changes/214_listCurrentProcessCandidates.md
  docs/process-paths.md docs/production-analysis-progress.md
  src/kgmaker/process_cli.py tests/test_t034_add_process_cli.py)
git diff --binary --full-index "$BASE" "$CANDIDATE" -- "${paths[@]}" > "$PROOF/ordinary.patch"
printf '%s  %s\n' 17a9609424d8e2c94b0b52a3bdb204fd449568790922d209df79a4e773de3cf7 "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' 39e83533cbec08095653a55eb00caf9bf8b02756d9612d04107631681935b3f8 .kgmaker/graph.json | sha256sum -c
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/before-plan.json"
git apply --index --check --whitespace=error-all "$PROOF/ordinary.patch"
git apply --index --whitespace=error-all "$PROOF/ordinary.patch"
git diff --cached --check "$BASE"
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan.json"
"$PYTHON" -B -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$PYTHON" -B -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" -B - "$BASE" "${paths[@]}" <<'PATCH'
import ast, json, subprocess, sys
from pathlib import Path

base, *paths = sys.argv[1:]
packet = json.loads(Path('.kgmaker/semantic-update.json').read_bytes())
assert packet['base_commit'] == base
assert {row['path'] for row in packet['changed_files']} == set(paths)
docs, cli = 'docs/process-paths.md', 'src/kgmaker/process_cli.py'

def before(path):
    return subprocess.check_output(['git', 'show', f'{base}:{path}'], text=True)

def render_call(source):
    root = next(row for row in ast.parse(source).body if getattr(row, 'name', '') == '_render')
    return next(row for row in ast.walk(root) if isinstance(row, ast.Call)
                and getattr(row.func, 'id', '') == 'build_local_process')

old, new = before(docs).splitlines(), Path(docs).read_text().splitlines()
assert new[:37] == old[:37] and new[78:] == old[37:]
assert old[549] == new[590] and old[549].startswith('## Static failure projection (T029)')
a, b = render_call(before(cli)), render_call(Path(cli).read_text())
assert (a.lineno, b.lineno) == (97, 143) and ast.dump(a) == ast.dump(b)
old_section = 'section:docs/process-paths.md:Static failure projection (T029)::550'
new_section = old_section.removesuffix('550') + '591'
patch = {'schema_version': 1, 'update_id': packet['update_id']}
for kind in ('nodes', 'edges'):
    patch[kind] = packet[f'affected_semantic_{kind}']
    for row in patch[kind]:
        path, line = row['source_file'], row['source_line']
        if path == docs and line >= 38:
            assert old[line - 1] == new[line + 40]
            row['source_line'] = line + 41
        elif path == cli:
            assert line == a.lineno
            row['source_line'] = b.lineno
        for field in ('source', 'target'):
            if row.get(field) == old_section:
                row[field] = new_section
assert (len(patch['nodes']), len(patch['edges'])) == (9, 23)
Path('.kgmaker/semantic-patch.json').write_text(json.dumps(patch, ensure_ascii=False, indent=2) + '\n')
PATCH
"$PYTHON" -B -m kgmaker semantic apply --root "$PWD"
"$PYTHON" -B -m kgmaker semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed
  --validation exact-focus=unknown --validation exact-native=unknown --validation standard=unknown)
"$PYTHON" -B -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first-capture.sha256"
"$PYTHON" -B -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first-capture.sha256"
"$PYTHON" -B -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -B -m kgmaker scan --root "$PWD"
"$PYTHON" -B -m kgmaker status --root "$PWD"
"$PYTHON" -B -m kgmaker check --root "$PWD"
git diff "$BASE" -- .kgmaker/GRAPH.mmd
```

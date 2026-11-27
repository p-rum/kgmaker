# Záznam sloučení atomického exportu technického pohledu procesu T038

Datum 2026-11-27. Výchozí `main` `2e393c049aa42bc1c0684f566d345345405a2dcd`,
strom `0ff627009e52960968cdcc7d3526bc227d30d09e`.
[T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md) ·
[T038-S05 / T038-AC06](../tasks/T-038_publish-view-artifacts-atomically.md) ·
[Stav dodání](../production-analysis-progress.md).

## Záznam skutečného sloučení

[#194](https://github.com/p-rum/kgmaker/pull/194) byl sloučen do `main`
27. listopadu 2026 ve 14:13:51 UTC jako
[`2e393c049aa42bc1c0684f566d345345405a2dcd`](https://github.com/p-rum/kgmaker/commit/2e393c049aa42bc1c0684f566d345345405a2dcd).
Rodiče jsou v pořadí `be63bc34b6f766761c39d5b9e8cde0d2389e3962` a
`c5360666c391a03ed45d878a1037676a899a9111`. Strom merge je shodný se
schváleným headem. Nezávislá revize T045 ověřila přesnou dvojici SHA a uzavřela
připomínky k předání potvrzeného manifestu a opakovanému použití stavu.
Doklad o sloučení má SHA-256
`3297e0306996721619cf3845e8e37f0e8d4bc0a4d8c6e56192bdb62f7ae12b9e`.
[Záznam T045](https://github.com/p-rum/kgmaker/pull/194#issuecomment-7220500538).

- Na skutečném merge měly T038 a regrese T036 **39 PASS / 0 SKIP**, raw exit 0.
  Běh na Linuxu použil CPython 3.13.18, markdown-it-py 3.0.0, Mermaid 11.4.1
  a jsdom 26.0.0. SHA-256 JUnit
  `530a7811916903b6d2dcd9cdf5f2d02d58d2ab16a44bde8321537dcc0729071f`.
- Samostatný příkaz `kgmaker process export` na merge měl raw exit 0.
  Stdout odpovídal uloženému manifestu, všechny tři soubory měly očekávaný
  SHA-256 a bajty vstupu zůstaly shodné. `semantic validate` a `completion plan`
  měly raw exit 0. Testy plánovače měly **13 PASS / 0 SKIP**, raw exit 0. SHA-256
  jejich JUnit je `b54bef011486df6e0cfc5e64d84a602822c209ca0f149f60bf6b5c1c2cee346a`.
  Otisky zdrojů a závislostí se před a po kontrolách shodovaly. Souhrnný doklad
  má SHA-256 `6ae37292f2090977b950bf94a946aabd1b889275dc906a261adff7a002ddbb0a`.
- Úplná standardní sada na schváleném headu měla **2 733 PASS / 1 409 SKIP /
  1 očekávaný XFAIL**, raw exit 0. SHA-256 JUnit
  `b9a1bd39fcebd0e6dfe31d7d641a01a9ecb41f046ac71811281b925de731e288`.
  Úplná sada přímo na merge má stav NOT_RUN.

Kanonický řádek T038 má stav `MERGED / PARTIAL`.
[T038-AC02](../acceptance-inventory.md#t038--atomická-publikace-dodaného-processview)
dokládá zachování dřívější generace a chování po potvrzené výměně v technickém
exportu na Linuxu. Při zachyceném přerušení při předání do CLI má uložený manifest
stále platné odkazy a příkaz vrátí `EXPORT_RECEIPT_INTERRUPTED` s exit 1.
Architektonický export a širší acceptance zůstávají v T038, T041 a T042.
[Použití příkazu](../process-paths.md#atomic-process-export-t038) ·
[Implementace a fault injection](210_publishProcessViewAtomically.md).

## Zopakování kontrol

V čistém archivu výše uvedeného merge označuje `PROOF` existující zapisovatelný
adresář mimo checkout. `PYTHON` a `KGMAKER` jsou binárky v témž místním prostředí.
Lokální závislosti pro nativní vykreslení odpovídají lockfile v `tests/rendering`.

```bash
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 "$PYTHON" -m pytest -q -p no:cacheprovider --tb=short \
  --basetemp "$PROOF/focused-tmp" --junitxml "$PROOF/focused.xml" \
  tests/test_t038_publish_view_artifacts_atomically.py \
  tests/test_t036_render_business_process_report.py
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" completion plan --root "$PWD" --jobs 32 > "$PROOF/plan.json"
mkdir "$PROOF/cli"
cp fixtures/process-model/checkout.json "$PROOF/cli/process.json"
"$PYTHON" -m kgmaker.cli process export --root "$PROOF/cli" \
  --snapshot process.json --output reports/process > "$PROOF/manifest.json"
cmp "$PROOF/manifest.json" "$PROOF/cli/reports/process/manifest.json"
cmp fixtures/process-model/checkout.json "$PROOF/cli/process.json"
```

## Dopad na plán

V izolovaném archivu `2e393c0` měly oba běhy `completion plan --jobs 32`
raw exit 0 a 135 položek. SHA-256 plánů před úpravou a po ní jsou
`0d5203a4785cc7cf699f64956de6e0b69f0d56b79ad6fe7eef1fe6c34f4f5326`
a `809ffb684bf8e8e3ec70424363c26b36b78a1900bce7a430873390f9e2176ce3`.
Příkaz plánovače a jeho testy používají výběr uvedený výše.
Přípravné testy plánovače měly 13 PASS / 0 SKIP, raw exit 0, JUnit SHA-256
`e4c608b2f8d500a4691eeaa71968918de568299dc8fe6de9aeddb6dd216aeac6`.

T038 přechází z akce `resume` na `verify`. Podle stavů dodání plán vybírá
T039 na třetí a T041 na páté místo z 32. Ověřovací položky T038 a W02 jsou
v tomto běhu mimo výběr. Podmínka `VERIFIED_IN_SCOPE` pro W02 dál blokuje W03.

- Čisté porovnání T039-S01–03 může pracovat se dvěma explicitními snapshoty
  s ověřeným kontextem a obsahem. [Zadání T039](../tasks/T-039_diff-architecture-and-processes.md).
- T041-S02 vyžaduje skutečnou extrakci, katalog, topologii, explain a export.
  T041-AC04 ověřuje zachování posledního uloženého artefaktu při chybě. Ve
  sloučeném stromu `architecture --help` uvádí `interfaces`, `topology` a
  `explain`. `architecture export --help` vrací `INVALID_ARGUMENTS` s raw
  exit 2. Publikaci tří artefaktů používá příkaz pro technický ProcessView.
  Úplná akceptace T041 proto čeká na atomický architektonický export T038.
  [Zadání T041](../tasks/T-041_verify-architecture-acceptance.md) ·
  [Architektonické CLI](../../src/kgmaker/architecture_cli.py) ·
  [Procesní CLI](../../src/kgmaker/process_cli.py).
- T040 zůstává `PLANNED / NOT_RUN`. T042 na něm dál čeká a musí ověřit
  přípravu, validaci, apply, review a render v jednom scénáři.
  [Zadání T042](../tasks/T-042_verify-process-acceptance.md).

Sémantické zachycení, opakování kontrol po přenosu na pozdější základ a nezávislé
review tohoto záznamu v přípravné kopii mají stav NOT_RUN.

## Přenos po sloučení #195

Výchozím bodem přenosu je skutečný merge
[`ec73b9cb0406c5331086ef668a798e1ad8c84c1d`](https://github.com/p-rum/kgmaker/commit/ec73b9cb0406c5331086ef668a798e1ad8c84c1d)
se stromem `1ccb54f590cb394bfc5ecb1f4709fdad87df1764`. Jeho rodiče jsou
`2e393c049aa42bc1c0684f566d345345405a2dcd` a
`0afc9ea5b7de3d7600fb4b423a731727ce81d6f2`. V tomto stromu je poslední
change note 211. V době ověření neměly otevřené PR #153, #118 ani #4 kolizi
s číslem 212. Záplata z izolovaného archivu uvedeného výše má SHA-256
`f0d78e2e294ec76286e4592446075dd351ef4807d3cf2e51fad7471d8a7b4dc0`.
Kontrola záplaty, aplikace do indexu a kontrola whitespace měly raw exit 0.
Přenos zasáhl dva inventáře a tento záznam. CLI procesního a architektonického
pohledu zůstalo bajtově shodné s #194.

Příkazy `semantic validate`, `check` a `memory recall` nad přijatým grafem #195
měly raw exit 0. Plán před přenosem má SHA-256
`6e169002d36d911d64f305ecb4a8746c0209cd75a88b266544dfcc93f3331c6a`
a shoduje se s přímým plánem po merge #195. Plán po přenosu má SHA-256
`8f9ddbaeb0933337c560af07b9b3c8c4a88a1e0d6dd808828fb43e3aba8f9670`.
Oba měly raw exit 0, 135 položek a výběr o 32 položkách. Změnily se záznamy
T038, T039, T041 a T042. Výsledky a zbývající podmínky odpovídají výše
uvedenému popisu. Plánovač před přenosem měl **13 PASS / 0 SKIP**, raw exit 0,
JUnit SHA-256 `28188f203e82b5568bd2795097dbb3ab166667e7894f66511e848e81c828238b`.
Na přípravném stromu po přenosu měl **13 PASS / 0 SKIP**, raw exit 0, JUnit
SHA-256 `2e5e858e418516e6a9e950f22fd13fa3b56fc43c717aad16c7b5655cc6e7f824`.

Přípravný strom dokumentů `fa43f07c7e82373ee7fb6d3c7b5317fbe1d5b1e3` prošel
`semantic update`, aplikací prázdné kurátorované záplaty, dvěma voláními
`memory capture`, `semantic validate`, `scan`, `status` a `check` s raw exit 0.
Výsledný přípravný strom `544aa29766042f6316540d7523e8ea0c7c2d0a47` zachoval
60 kurátorovaných konceptů, 222 vztahů a všech 517 přijatých epizod doslova.
Zachytil jedinou přípravnou epizodu
`episode:2d6f39ca2b7635b85b694c959f141eb9bcafdcba3e84ae75103c53845187ef03`.
Druhé zachycení našlo tutéž epizodu a zachovalo bajty sémantiky i vstupního grafu.
Strojový graf přípravného stromu má SHA-256
`0a9701cc51212e4469b01a22ce32b01ea0be8a3394705dd77bce55fd54643f74`.

V přípravném grafu má všech 227 dotčených uzlů původ v jedné ze tří cest.
Přibylo pět uzlů dokumentace, žádný uzel se neodebral ani nezměnil. Projekce
epizody #195 přešla z `current` na `changed` kvůli dvěma společným inventářům.
Mermaid a všech 659 importů zůstaly shodné. Tři uzly Rates a jejich 275 vazeb se
nezměnily. Finální zachycení vychází opět z přijatého grafu #195 a zahrnuje
bajty této části záznamu. Otisky finální epizody a grafu jsou v dokladu mimo
zachycované soubory. Úplná standardní sada má pro tento dokumentační krok
stav NOT_RUN. Review finálního kandidáta je samostatný krok.

### Reprodukce přenosu a zachycení grafu

`CANDIDATE` je finální revize T048 a `BASE_GRAPH` je přijatá kopie
`candidate-graph.json.gz` z ověření #195. `PROOF` je absolutní zapisovatelný
adresář mimo checkout. `PYTHON` je CPython 3.13.18 s pytestem. Příkazy se
spouštějí z čisté oddělené větve na `BASE`.

```bash
set -euo pipefail
BASE=ec73b9cb0406c5331086ef668a798e1ad8c84c1d
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
git diff --binary --full-index "$BASE" "$CANDIDATE" -- docs/acceptance-inventory.md \
  docs/changes/212_recordProcessExportMerge.md docs/production-analysis-progress.md \
  > "$PROOF/t048.patch"
printf '%s  %s\n' c400eaf66cea38b66d63ce03fc4a6fd4dd43a777e9d55d3138c699961868dfbc "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' d2c282afecc2cf1146c09b3a2524403455cc2953bae71196941f9ed158d9e78e .kgmaker/graph.json | sha256sum -c
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -m kgmaker check --root "$PWD"
"$PYTHON" -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-before.json"
git apply --index --check --whitespace=error "$PROOF/t048.patch"
git apply --index --whitespace=error "$PROOF/t048.patch"
git diff --cached --check "$BASE"
"$PYTHON" -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-after.json"
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$PYTHON" -m kgmaker.cli architecture --help > "$PROOF/architecture-help.txt"
raw=0
"$PYTHON" -m kgmaker.cli architecture export --help \
  > "$PROOF/architecture-export.out" 2> "$PROOF/architecture-export.err" || raw=$?
test "$raw" = 2
test ! -s "$PROOF/architecture-export.out"
grep -F INVALID_ARGUMENTS "$PROOF/architecture-export.err"
"$PYTHON" -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

base = sys.argv[1]
update = json.loads(Path('.kgmaker/semantic-update.json').read_bytes())
assert update['base_commit'] == base
paths = {'docs/acceptance-inventory.md', 'docs/changes/212_recordProcessExportMerge.md',
         'docs/production-analysis-progress.md'}
assert {row['path'] for row in update['changed_files']} == paths
assert update['affected_semantic_nodes'] == update['affected_semantic_edges'] == []
patch = {'schema_version': 1, 'update_id': update['update_id'], 'nodes': [], 'edges': []}
Path('.kgmaker/semantic-patch.json').write_text(json.dumps(patch, indent=2, ensure_ascii=False) + '\n')
PATCH
"$PYTHON" -m kgmaker semantic apply --root "$PWD"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation planner=passed
  --validation source-diff=passed --validation architecture-cli-diagnostic=passed
  --validation semantic-before-capture=passed --validation standard=unknown)
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first-capture.sha256"
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first-capture.sha256"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -m kgmaker scan --root "$PWD"
"$PYTHON" -m kgmaker status --root "$PWD"
"$PYTHON" -m kgmaker check --root "$PWD"
git diff --exit-code "$BASE" -- .kgmaker/GRAPH.mmd
```

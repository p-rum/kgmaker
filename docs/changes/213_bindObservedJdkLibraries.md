# Otisk tří dalších standardních knihoven Linux JDK

27. listopadu 2026. [T003-S10-W01](../tasks/T003-S10-01-stageContentCache.md),
kroky 1–5, W01-AC01–AC04 a T003-AC10. Přípravné měření je svázané s
`main` `2e393c049aa42bc1c0684f566d345345405a2dcd`, stromem
`0ff627009e52960968cdcc7d3526bc227d30d09e` a úkolem T052
`task:534be4b4d634004750d751644d7da8a815b61e7e940062bbd0ab5bbe82c721bf`.

## Krok 1 — zjištění na původním kódu

Na Linuxu s Temurin JDK 21.0.6+7 proběhla živá inspekce příkladu
`Math.abs` s výchozí sadou symbolů Java 21 a vypnutou publikací.
Diagnostika glibc `LD_DEBUG=files` zaznamenala ve dvou Java procesech
inicializaci `lib/libjava.so`, `lib/libjimage.so` a `lib/libzip.so` v
použitém JDK. Ve výchozí mapě `launch.files` chyběly všechny tři položky.
Loader zaznamenal i jiné knihovny. Oprava pokrývá uvedené tři další
doložené cesty standardního JDK. Běh vrátil `JAVAC_ATTRIBUTED_SYMBOL`
pro `java.lang.Math.abs(I)I`, tři `BYPASS/UNVERIFIED_REPLAY` a exit 0.
SHA-256 JSON `375cb6477f67793e12783a98a8fdd8ea6ab206d8591dad122da32ad78f252e36`.
SHA-256 výřezu loaderu `be631e55b6e9dbc1c0087d71119d1fbf1bc4454fc7d1482dedfba36df6e94007`.

Na původním produkčním kódu po přenesení testů byl cílený výsledek
**13 FAIL / 9 PASS / 0 SKIP**, raw exit 1. Případy selhaly pro úplnost
průběžně čtené mapy, samotné otisky všech tří knihoven, šest variant
nedostupných bajtů a tři změny po analýze. Produkční soubor se shodoval
s výchozí revizí. Pokus `kgmaker memory recall` skončil kódem 2,
protože přípravná pracovní kopie neměla čitelný lokální index.
Rekognoskace použila zdroj, testy a dosavadní záznamy
[locale a platformních symbolů](164_bindJavaLaunchInputs.md),
[nativních vstupů](180_bindLinuxJdkNativeInputs.md) a
[prostředí launcheru](198_bindLinuxLauncherEnvironment.md).

## Krok 2 — rozšíření stávajícího otisku a kompatibilita

[extraction_cache.py](../../src/kgmaker/extraction_cache.py) přidává
`lib/libjava.so`, `lib/libjimage.so` a `lib/libzip.so` do seznamu
souborů standardního Linux JDK. Cesty se odvozují od skutečného
launcheru stejně jako u `lib/libjli.so` a `lib/server/libjvm.so`.
Stávající průběžné čtení váže SHA-256 obsahu i těchto tří souborů.
Graph/store v1–v3 a interní cache envelope v1 zůstávají čitelné.
Úplný přípravný cache unit soubor zahrnuje regresi starších grafů,
nelinuxovou větev a dosavadní výběr launcheru. Syntaxe příkazů a
instalované instrukce se používají ve stávající podobě.

## Krok 3 — nedostupné bajty a ochrana publikace

Změna využívá stávající `InspectionStages.guard` a pravidla
publikace. Při chybějícím nebo nečitelném souboru má případný platný
živý výsledek `BYPASS/INCOMPLETE_INPUT_CLOSURE` bez metadat
extraction cache. Pokud se zachycený otisk změní po analýze,
inspekce vrátí `STALE` a zachová bajty poslední platné generace.
Syntetické testy používají stávající náhradní transport. Samostatně
změní a obnoví bajty každé knihovny, odeberou soubor nebo simulují
`PermissionError`. Testy sledují výsledek i bajty uložených výstupů.
Stabilní živá JVM inspekce nadále vykazuje
`BYPASS/UNVERIFIED_REPLAY`. [Použití a hranice](../stage-content-cache.md#použití)

## Krok 4 — přípravná ověření

Přípravný strom produkčního souboru a dvou testů
`63b2d48d196977798d69683d8e0d5c2a36a88e77` má SHA-256 patche
`c527ed07d735bfbe5e4f7994c128af872ae8402c030f2223984dca83246a0038`.
Běžely CPython 3.12.14 a Linux x86_64. Souhrnný přípravný doklad má
SHA-256 `88799153c77ea97b75eb42548a607700025a7d4d2a4a69db640bafb4d9b208b2`.

| Kontrola | Výsledek | SHA-256 JUnit |
|---|---|---|
| Vybrané regrese na původních produkčních bajtech | 13 FAIL / 9 PASS / 0 SKIP, raw 1 | `d3b0cb4d24df900eaf6d8e1e759d3c2e6a82b12f0d90d40cebd8bc691d99d450` |
| První běh celého cache unit souboru po opravě | 86 PASS / 1 FAIL / 0 SKIP, raw 1 při zakládání dočasného adresáře (`ENOSPC`) | `104f73189c34935c3be85e77380a2a926c9ae55c3d1de33a4db3950e2e222e3e` |
| Opakování celého cache unit souboru se shodným kódem | 87 PASS / 0 SKIP, raw 0 | `1663283afd7649c1ca59dd9362a587dd324065d1089c6228ccdf1587e38a182e` |
| Jeden vybraný případ se skutečným JVM workerem | 1 PASS / 0 SKIP, raw pytest 0 | `a21378b0a3764b3c87bcb77e71dd272dca7c5f8e4634a83a5a97c4679503e660` |

Pro zopakování RED použijte dva testovací soubory změny na původní
produkční revizi. GREEN používá opravený soubor i oba testy.
Zvolte `proof_dir` jako nový adresář pro výstupy a `python_bin` jako
cestu k CPythonu 3.12.14 s pytest.

```bash
PYTHONDONTWRITEBYTECODE=1 "$python_bin" -B -m pytest -q \
  -p no:cacheprovider --tb=line --junitxml="$proof_dir/red-unit.junit.xml" \
  --basetemp="$proof_dir/red-unit-tmp" \
  tests/test_stage_content_cache.py::test_launch_capture_hashes_without_materializing_platform_files \
  tests/test_stage_content_cache.py::test_java_launch_capture_binds_linux_native_library \
  tests/test_stage_content_cache.py::test_unavailable_java_launch_input_allows_live_inspection_without_cache \
  tests/test_stage_content_cache.py::test_java_native_library_change_after_analysis_preserves_generation

PYTHONDONTWRITEBYTECODE=1 "$python_bin" -B -m pytest -q \
  -p no:cacheprovider --tb=short --junitxml="$proof_dir/green-unit-retry.junit.xml" \
  --basetemp="$proof_dir/green-unit-retry-tmp" tests/test_stage_content_cache.py
```

První GREEN použil stejný příkaz s názvy `green-unit.junit.xml` a
`green-unit-tmp`. Pro nativní výběr nastavte `jdk_root` na Temurin
21.0.6+7 a vystavte v `workers/jvm/target` připravenou distribuci
workeru s přilehlými závislostmi. Ověřený JAR měl SHA-256
`021584a2c6b14626d8af4a6907aed1837dc7c8ee51da1d9ad56c3326b87e0e3b`.
V přípravné pracovní kopii se použil dočasný odkaz na tuto distribuci.
Po běhu byl odstraněn.

```bash
env -u LD_DEBUG -u LD_DEBUG_OUTPUT -u LD_LIBRARY_PATH -u JAVA_TOOL_OPTIONS \
  -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
  PATH="$jdk_root/bin:$PATH" JAVA_HOME="$jdk_root" \
  KGMAKER_REQUIRE_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 \
  "$python_bin" -B -m pytest -q -p no:cacheprovider --tb=short \
  --junitxml="$proof_dir/green-native.junit.xml" --basetemp="$proof_dir/green-native-tmp" \
  'tests/test_stage_content_cache_actual.py::test_actual_jvm_locale_drift_preserves_published_generation[after-analyze]'

git diff --cached --check
git diff --check
```

Nativní test použil `--java-release 17`, potvrdil atribuci volání
`Math.abs`, tři živé fáze `BYPASS/UNVERIFIED_REPLAY` a přesné SHA-256
v uloženém klíči `worker-analysis`. Druhá inspekce v témže testu změnila locale po
analýze a doložil `STALE` s bajtově shodnou předchozí generací.
Skutečné nativní knihovny po celý běh zůstaly bajtově shodné. Obě kopie
připnutého manifestu mají SHA-256
`faeb08a0c6ae69b86c8c26371bcc5f7ebb24ebb5662804f7eb64679dfed1119f`.
Obalový shell nahlásil kód 1. Samostatný záznam návratového kódu
pytest uvádí 0, JUnit uvádí PASS a samostatné porovnání manifestů
skončilo kódem 0. Obě kontroly diffu skončily kódem 0.

## Krok 5 — příklad použití a zbývající ověření

Na Linuxu se standardním rozložením JDK spusťte stávající explicitní
inspekci `kgmaker inspect code --root ./service`. Případný rozdíl
zachyceného otisku zjištěný během inspekce vede ke `STALE`.
[Příklady](../stage-content-cache.md#použití) ·
[Compiler inspekce](../compiler-inspection.md#obsahová-cache-inspekčních-stupňů-t003-s10-w01) ·
[README](../../README.md#obsahová-cache-explicitní-inspekce-t003-s10-w01) ·
[Acceptance](../acceptance-inventory.md#t003-s10-w01--obsahová-cache-explicitních-inspekčních-stupňů) ·
[Stavová matice](../production-analysis-progress.md)

Na přípravném stromu mají úplná sada, hostované CI a nativní test
na jiném OS stav `NOT_RUN`. W01-AC01 zůstává `PARTIAL`.
Úplné vymezení dynamických vstupů a nezávislá evidence původu
persistentního výsledku zůstávají otevřené. [#116](https://github.com/p-rum/kgmaker/issues/116)

## Přenos po sloučení #196

Výchozí `main` při přenosu je skutečný merge [#196](https://github.com/p-rum/kgmaker/pull/196)
`384fc6a3fee56b11f6e30d1123e58fff055ff1f8`, strom
`ae82d73ab85c06641a00fc40eae6e40b964208c1`, s rodiči
`ec73b9cb0406c5331086ef668a798e1ad8c84c1d` a
`1ed2d9883e0fdae0b07b4c1cee0b85ad1fc1858d`. Poslední záznam v tomto
stromu měl číslo 212. Otevřené PR #153, #118 a #4 neměly při kontrole
kolizi s tímto záznamem. Původní tři ověřené produkční a testovací soubory
převzaté z přípravného stromu mají shodné bajty a shodný patch.
Aplikace zdrojového i dokumentačního patche do indexu, kontroly jejich
aplikovatelnosti a `git diff --cached --check` skončily s raw exit 0.

Nad převzatým grafem #196 skončily `semantic validate`, `check` a
`memory recall` s raw exit 0. Před a po aplikaci měl
`completion plan --jobs 32` raw exit 0, 135 položek a shodný výběr i pořadí
32 položek. Změnily se digest dokumentu W01 a digest inventáře.
Ve W01 zůstává `MERGED / PARTIAL` s akcí `verify`. W03 nadále čeká na
`VERIFIED_IN_SCOPE` u W02-AC01. SHA-256 plánu před přenosem je
`8f9ddbaeb0933337c560af07b9b3c8c4a88a1e0d6dd808828fb43e3aba8f9670`, po přenosu `858a6ff15e2e6482558838b73d7d0b3ef8f23418367d00338a4187b1bbec2b02`.
V testech plánovače prošlo **13 PASS / 0 SKIP**, raw exit 0, JUnit
SHA-256 `ae3a18722cf3871b5f6037014cd86a6d91bbab7b67c77f7b269b9b8d954c7b6a`.

Před doplněním tohoto oddílu prošel přípravný strom
`7533148b574c91dcd8f085b5c2d0b1ac18f9d41c` příkazy `semantic update`, `semantic apply`,
`semantic validate` před zachycením, dvěma voláními `memory capture`,
`semantic validate` po zachycení, `scan`, `status`, `check` a
kontrolou diffu. Každý skončil s raw exit 0. Při aktualizaci přezkoumal
packet 15 existujících konceptů a 80 vztahů. Změnila se dvě umístění.
Nadpis selektivního dopadu v návodu cache se posunul z řádku 152 na 154.
Regrese prostředí launcheru zůstala stejným testem a posunula se
z řádku 310 na 318. Její existující vztah aktualizoval řádek zdroje a strukturální
ID testu. Všechny kurátorované skutečnosti, 60 konceptů a 222 vztahů,
zůstaly zachované.

Přípravný výsledek má strom `fd08e0ab3d3de22efa95e3537d5574b77b226b38`, strojový graf SHA-256
`f3eede55a4a659c8739ba96b75845fcccf68f7a782c4a663eafd22c5b777ed0f` a jednu novou epizodu `episode:a774aacfb02430781ce8cc509719e1f3b68fc1a9a66468d298573244d98469b8`.
Všech 518 přijatých epizod zůstalo doslova zachováno. Druhé zachycení
našlo stejnou epizodu a ponechalo bajty sémantiky a vstupního grafu
shodné. Zachovalo se 659 importů, tři uzly tabulky Rates s jejich
275 vazbami i Mermaid a soubor s kurátorovanými poznámkami.
Grafový rozdíl má 218 přidaných, 210 odebraných a
1 změněných uzlů. Všech 678 dotčených uzlů patří
přenášeným cestám. Finální zachycení znovu vychází z přijatého grafu
#196 a zahrnuje bajty tohoto oddílu. Jeho otisky jsou v dokladu mimo
zachycované soubory. Přesný cílený, nativní a standardní běh nad
publikovaným HEAD a nezávislé review jsou samostatné kontroly. V
přípravném ověření tohoto přenosu mají stav `NOT_RUN`.

### Reprodukce přenosu a zachycení

`CANDIDATE` označuje finální kandidátskou revizi W01. `BASE_GRAPH` je
přijatý archiv grafu #196. `PROOF` je zapisovatelný adresář mimo checkout,
`PYTHON` je CPython 3.13.18 s pytestem. Příkazy se spouštějí z čisté
oddělené větve na `BASE`. Přípravná měření nad CPython 3.12.14 jsou
vypsána zvlášť výše.

```bash
set -euo pipefail
BASE=384fc6a3fee56b11f6e30d1123e58fff055ff1f8
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
paths=(README.md docs/acceptance-inventory.md docs/changes/213_bindObservedJdkLibraries.md
  docs/compiler-inspection.md docs/production-analysis-progress.md docs/stage-content-cache.md
  docs/tasks/T003-S10-01-stageContentCache.md src/kgmaker/extraction_cache.py
  tests/test_stage_content_cache.py tests/test_stage_content_cache_actual.py)
git diff --binary --full-index "$BASE" "$CANDIDATE" -- "${paths[@]}" > "$PROOF/w01.patch"
printf '%s  %s\n' b672357af6684f2bdc74e8bb28949f4c6400b094138b1140c33d8908619660c9 "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' 696c9f761a32c9d9fd6785a040de76216ee93770b396871b4fb01ab2f21cd54b .kgmaker/graph.json | sha256sum -c
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -m kgmaker check --root "$PWD"
"$PYTHON" -m kgmaker memory recall 'T003-S10-W01 Linux JDK launcher freshness new libjava libjimage libzip' --root "$PWD"
"$PYTHON" -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-before.json"
git apply --index --check --whitespace=error "$PROOF/w01.patch"
git apply --index --whitespace=error "$PROOF/w01.patch"
git diff --cached --check "$BASE"
"$PYTHON" -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-after.json"
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$PYTHON" -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

base = sys.argv[1]
update = json.loads(Path('.kgmaker/semantic-update.json').read_bytes())
assert update['base_commit'] == base
paths = {
    'README.md',
    'docs/acceptance-inventory.md',
    'docs/changes/213_bindObservedJdkLibraries.md',
    'docs/compiler-inspection.md',
    'docs/production-analysis-progress.md',
    'docs/stage-content-cache.md',
    'docs/tasks/T003-S10-01-stageContentCache.md',
    'src/kgmaker/extraction_cache.py',
    'tests/test_stage_content_cache.py',
    'tests/test_stage_content_cache_actual.py',
}
assert {row['path'] for row in update['changed_files']} == paths
docs = 'docs/stage-content-cache.md'
unit = 'tests/test_stage_content_cache.py'
heading_id = 'concept:docs/stage-content-cache.md:evidence_only_dependency_impact'
function = 'test_linux_library_search_path_drift_preserves_generation'
old_id = f'function:{unit}:{function}::310'
new_id = f'function:{unit}:{function}::318'
assert len(update['affected_semantic_nodes']) == 15
assert len(update['affected_semantic_edges']) == 80
patch = {'schema_version': 1, 'update_id': update['update_id']}
for section in ('nodes', 'edges'):
    patch[section] = update[f'affected_semantic_{section}']
heading, = [row for row in patch['nodes'] if row['id'] == heading_id]
edge, = [row for row in patch['edges'] if row['source'] == old_id]
assert (heading['source_file'], heading['source_line']) == (docs, 152)
assert (edge['source_file'], edge['source_line']) == (unit, 310)
heading['source_line'] = 154
edge['source_line'] = 318
edge['source'] = new_id
Path('.kgmaker/semantic-patch.json').write_text(json.dumps(patch, indent=2, ensure_ascii=False) + '\n')
PATCH
"$PYTHON" -m kgmaker semantic apply --root "$PWD"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed
  --validation exact-focus=unknown --validation exact-native=unknown --validation standard=unknown)
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first-capture.sha256"
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first-capture.sha256"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -m kgmaker scan --root "$PWD"
"$PYTHON" -m kgmaker status --root "$PWD"
"$PYTHON" -m kgmaker check --root "$PWD"
git diff --exit-code "$BASE" -- .kgmaker/GRAPH.mmd .kgmaker/NOTES.md
git add -- .kgmaker/GRAPH.md .kgmaker/semantic.json
git diff --cached --check "$BASE"
```

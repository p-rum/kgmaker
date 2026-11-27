# Porovnání dodaných snímků procesu

Výchozí `main` pro vývoj je
`384fc6a3fee56b11f6e30d1123e58fff055ff1f8`, strom
`ae82d73ab85c06641a00fc40eae6e40b964208c1`. Plán po sloučení #196 vybral
T039 jako třetí z 32 položek. Závislosti T037 a T038 mají stav
`MERGED / PARTIAL`. [Zadání T039](../tasks/T-039_diff-architecture-and-processes.md) ·
[Společný kontrakt T004](../tasks/4_addHighLevelProjectViews.md) ·
[Předání po #196](212_recordProcessExportMerge.md).

## T039-S01 — porovnání záznamů podle jejich ID

`kgmaker.view_diff.diff_process_views(before, after)` porovná dva výslovně
dodané typované `ProcessView` schématu 1. Páruje uzly, orientované výskyty hran
a záznamy důkazů podle jejich přesných ID. Přeuspořádání kanonických seznamů,
řádků výběru T025 nebo změna času generování nevytvoří rozdíl příslušných
záznamů. Otisky a revize v polích `before` a `after` identifikují dodané snímky.

## T039-S02 — samostatné druhy změn a pokrytí

Změna popisku kroku je `presentation`. Změna vztahu hrany je `topology`.
Každý paralelní výskyt si zachovává vlastní ID, směr a odkazy na původní důkazy.
Změny `resolution`, `freshness` a `evidence` zachovávají hodnoty z obou
snímků. `supplied_annotations` nese dodaný text a stav review jako metadata.
Ověření účinného T032 rozhodnutí zůstává otevřené.

`added` a `removed` popisují změnu přítomnosti záznamu v porovnatelných
úplných výřezech. Při neúplném, zkráceném nebo odlišně omezeném pokrytí
dostane chybějící záznam `not_observed_before` či `not_observed_after`
podle strany, kde chybí.
Obě vazby si nesou vlastní pokrytí, diagnostiky, limity, vybraný kontext
a ID nevyřešených záznamů. `truncated_node_ids` a `truncated_edge_ids`
nesou místní zkrácení z výslovného `attributes.truncated = true`, i když
celkové pokrytí uvádí `COMPLETE_WITHIN_SELECTED_SCOPE`. Výskyt zkrácení
na jednom ze snímků kvalifikuje všechny rozdíly přítomnosti. Zachycené
omezení neobsahuje seznam ID vynechaných záznamů. Změnu příznaku ukazuje
`changes.coverage`, zatímco struktura uzlů a hran má vlastní změny.

## T039-S03 — kontrola srovnatelnosti a kompatibilita

Párování vyžaduje stejné ID procesu, scope, verzi pravidel, vybraná ID kontextu
a shodný rozpoznaný výběr zachycení. Výběr může být přímá mapa služby na ID
kontextu nebo strukturovaný výběr T025 s přesnou vazbou aktuálních řádků.
Porovnání řadí známé seznamy diagnostických záznamů vybraného kontextu.
Shoda vyžaduje stejný obsah včetně násobnosti. Výstup obsahuje původní
záznamy a pořadí obou snímků.
Samotný výběrový klíč varianty nestačí k propojení různých zachycení.
Při neshodě nebo neprůkazném výběru vrátí API `INCOMPARABLE`, kódy důvodu
a prázdné `changes`. Otisky a revize se uchovávají jako vazba na vstup.

Porovnání je čisté Python API pro existující dokumenty `ProcessView`. Při
překročení sdíleného rozpočtu výjimka `ViewValidationError` nese
`PROCESS_DIFF_LIMIT` a stranu vstupu. Výsledek má vlastní kopie vnořených
záznamů. Tímto krokem nevzniká uložené schéma, takže migrace odpadá.
[Python příklad a rozsah](../process-paths.md#compare-supplied-process-views-t039).

## T039-S04 — lokální výsledky

První běh 12 nových testů před přidáním `view_diff.py` měl 12 FAIL,
0 SKIP, raw exit 1 kvůli chybějícímu modulu. SHA-256 logu
`9a48f3d325c0d106f3102e21196b46040926fc75f4ce8002c48154541e2a2d7f`.
Přípravný běh měl 10 PASS a 2 FAIL, raw exit 1. Test přeřazení znovu
použil vnořený kontejner snímku a test diagnostiky čekal seznam místo
n-tice. Oprava oddělila kopie a přidala kontrolu výsledku po jeho úpravě.
SHA-256 přípravného logu
`ebcaf204d624e654f24e8b7b67849df51b773330f1121bd20e82396084dab4e`.

Po opravách prošlo na dvou zdrojových a testovacích souborech na uvedeném
vývojovém základu **83 testů, 0 SKIP**, raw exit 0. T039 má 14 PASS
a čisté modelové regrese T023 mají 69 PASS. Běh použil CPython 3.13.18
a pytest 8.3.4. SHA-256 JUnit
`45922ec260669ac6f522deea0352d72e9a62eec5ec3ddb4816fe2803312c7104`.
Bajty obou souborů váže doklad pod SHA-256
`3726dc7368b5ab1491afae315344a9e5fb17cd52930c3e4c499310bcaa325b08`.
Příprava ověřila reverzní aplikovatelnost patch souboru s kontrolou bílých
znaků, raw exit 0. U finálního integrovaného stromu zůstává tato kontrola
předmětem vlastního běhu.

Z kořene checkoutu s oběma změněnými soubory spusť v uvedeném Python
prostředí cílenou sadu. `PROOF` je existující zapisovatelný adresář mimo
checkout.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider \
  tests/test_t039_diff_architecture_and_processes.py \
  tests/test_t023_define_business_process_model.py \
  --junitxml="$PROOF/source-green-final.xml"
```

Samostatná kontrola načetla původní zachycený Javac workspace již používaný
pro T034. Veřejný `process render` skončil raw exit 0 a vydal ProcessView
s otiskem `bb61b212a50b8187261e687b8089e688dc6d8d06adbf67bba681a5372e6c76a7`.
Přeřazení vstupu dalo `COMPARABLE` s prázdnými změnami a zachovalo
`PARTIAL`. Kontrolní platný dokument s dalším aktuálním kontextem mimo
deklarovaný výběr procesu dal `INCOMPARABLE` s prázdnými změnami.
Devět souborů workspace mělo shodné SHA-256 a časy změn. Samotné porovnání
proběhlo s blokovaným otevřením souborů, socketů a procesů. Šlo o čtení
uloženého zachycení. SHA-256 výstupu kontroly
`0433fc2c45f2d8f5db205b5af255a62dbea84dd7a79a27226b69f789adf8998e`.

| AC | Konkrétní cílený důkaz a rozsah |
|---|---|
| T039-AC01 | `test_reorder_and_generation_metadata_have_no_deltas`, `test_t025_selection_row_order_is_irrelevant_and_recapture_requires_exact_proof` a `test_selected_context_diagnostic_order_and_duplicate_evidence` ověřily prázdný rozdíl po změně pořadí. |
| T039-AC02 | `test_label_and_supplied_review_are_independent_of_parallel_edge_removal` a `test_same_edge_id_technical_relation_change_keeps_directed_identity` odlišily popisek, odebraný výskyt a změnu vztahu procesní hrany. Architektonické integrační vazby a kontrakty zůstávají otevřené. |
| T039-AC03 | `test_incompatible_pair_never_invents_changed_records`, `test_t025_selection_row_order_is_irrelevant_and_recapture_requires_exact_proof`, `test_capture_fingerprint_and_result_binding_stay_detached` a `test_opaque_selection_cannot_prove_comparability_even_when_equal` odmítly nesrovnatelné dvojice s prázdným rozdílem. Architektonické release párování zbývá. |
| T039-AC04 | `test_invalid_and_over_limit_inputs_cannot_mutate_any_supplied_data` a `test_capture_fingerprint_and_result_binding_stay_detached` ověřily shodu vstupů, původního artefaktu a oddělení výsledných dat. |
| T039-AC05 | `test_unresolved_and_stale_are_separate_and_retain_proof_and_limits`, `test_changed_projection_limits_make_new_absence_uncertain`, `test_projection_gap_is_symmetric_and_complete_addition_remains_genuine` a `test_local_truncation_qualifies_absence_and_preserves_coverage` ověřily důkazy, nevyřešené hranice a kvalifikovanou absenci při celkovém či místním zkrácení. |
| T039-AC06 | `PARTIAL`. Cílený běh vývoje a doklad zachovaného Javac vstupu jsou doloženy výše. |

### T052 retry 1 — obousměrná absence a pořadí diagnostik

Nezávislá kontrola na přesné předchozí dvojici souborů reprodukovala dvě
chyby. Zakrytý `pay-card` v dřívějším zkráceném výřezu se později označil
`added`. Převrácení 111 diagnostik vybraného kontextu skutečného Javac snímku
dalo `INCOMPARABLE`. Kontrola dřívějšího stavu měla 2 FAIL a raw exit 1.
SHA-256 výstupu `808de7abf2db452887184cd7f96c8b11ea205ef20152a041b6f052f773676244`.
T052 zaznamenal neúspěšné nezávislé testování a vrátil úkol k implementaci.

Stejná nezávislá kontrola po opravě prošla oběma případy, raw exit 0.
`pay-card` dostal v obou směrech příslušné `not_observed_*`. Jinak shodný
snapshot s přeřazenými diagnostikami je `COMPARABLE` s prázdnými změnami.
Oba testované vstupy mají shodné bajty před a po testu. SHA-256 výstupu
`5526453630d105f8ac1cece6b5ba10575d509dce83ea3dc0e84a1e37b1e6c901`.
Zachovaný Javac snapshot má SHA-256 vstupního JSON
`0bf7fb88a5d8b450e76d61f6260a7daf14ef7e7103fc27196db1063c20ea275a`.

Po přidání tří cílených případů měla sada T039 na předchozím zdroji
15 PASS a 2 FAIL, raw exit 1. Shodné úplné výřezy správně zachovaly `added`
a `removed` už v tomto běhu. SHA-256 JUnit
`1e31cae7c563fd9321894778f7958a82d1a21ce544ee23a57aa2dbd4d1dcc33c`.
Opravená vývojová dvojice má **86 PASS / 0 SKIP**, raw exit 0. Jde o
17 testů T039 a 69 regresí T023. SHA-256 JUnit
`911c03b9114aaf64cb6368dd6d49af11e57f4a960e7ef35b5abfb91767b6e873`.
Zopakované čtení zachovaného Javac workspace skončilo raw exit 0 se
stejným výstupem kontroly jako před opravou. Doklad pro opravenou dvojici
má SHA-256 `950369cb72666619eeb32d8ce98bf827a68a90a8c5bf1036220e7541091445d5`.

Pro ověření opraveného zdroje použij stejný Python a existující `PROOF`.

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -B -m pytest -q -p no:cacheprovider \
  tests/test_t039_diff_architecture_and_processes.py \
  tests/test_t023_define_business_process_model.py \
  --junitxml="$PROOF/t039-retry1-focused-green.xml"
```

### T052 retry 2 — místní zkrácení uzlů a hran

Další nezávislá kontrola reprodukovala dvě chyby na přesné dvojici po
první opravě. Místně zkrácený krok `card` nebo hrana `start` ještě dovolily
označit chybějící `pay-card` jako `added` nebo `removed` při obrácení vstupů,
pokud celkové pokrytí zůstalo `COMPLETE_WITHIN_SELECTED_SCOPE`. Kontrolní
dvojice bez zkrácení prošla. Běh měl 1 PASS, 2 FAIL a raw exit 1. SHA-256
výstupu `f60610b702ee26acb0a1a7559b63c7e3c89554dcda460abb03168890d3fadddd`.

T052 vrátil úkol k implementaci podruhé. Oprava zachovává místní zkrácení
v obou vazbách, zobrazuje jeho změnu v přehledu pokrytí a kvalifikuje
chybějící výskyt v obou směrech. Stejná nezávislá reprodukce má 3 PASS,
raw exit 0 a shodné vstupy. SHA-256 výstupu
`dcf0c308d3c858216e34b50d7b03559321c81a0938a46b3e3d4e58e84cc8ec3a`.
Původní kontrola pořadí diagnostik a celkové absence má dál 2 PASS,
raw exit 0 a stejný SHA-256 jako po první opravě.

Cílený regresní test obou markerů měl před opravou 17 PASS a 2 FAIL
v celé sadě T039, raw exit 1. SHA-256 JUnit
`50066b9f31700c44cba43090984931faa68524a8713c6c7aa7474986e473f802`.
Na nové vývojové dvojici prošlo **88 testů, 0 SKIP**, raw exit 0.
Jde o 19 T039 a 69 čistých T023. SHA-256 JUnit
`2948dc6f105f01c75ba13f6398064d65fb51bb81e45965ea44ac8f7adc98ceb2`.
Opakované čtení zachovaného Javac workspace má raw exit 0 a shodný doklad
jako první běh. Reprodukci cílené sady proveď příkazem výše s cestou
`$PROOF/t039-retry2-focused-green.xml`. SHA-256 dokladu o zdroji
`23d029a71e6fc9171a0c55315bed42a8fa6b315413dfd411528b8373b0a1c00d`.

## T039-S05 — návody a zbývající rozsah

[README](../../README.md#local-technical-process-paths-t025) a
[návod](../process-paths.md#compare-supplied-process-views-t039) odkazují
na dostupné Python API. Stav `PARTIAL` je veden v [přehledu dodání](../production-analysis-progress.md)
a v [acceptance inventáři](../acceptance-inventory.md#t039--porovnání-dodaných-processview).
Otevřené zůstává srovnání architektonických kontraktů a release, napojení
CLI a ověření účinného T032 rozhodnutí pro porovnávané popisky.
Úplná standardní sada, finální integrační kontroly a formální nezávislé
review přesného kandidáta mají v tomto dokladu stav `NOT_RUN`.

## Přenos po sloučení #198

Základ pro integraci je skutečný merge
[`e63a82176623af8f6cd768868c282ac272749a6d`](https://github.com/p-rum/kgmaker/commit/e63a82176623af8f6cd768868c282ac272749a6d)
ze dne 2026-11-27 16:22:12 UTC. Rodiče jsou v pořadí
`7ad9fce7526add0986bee29f56ced33aa5da79e3` a
`902e0afede217fae7d75d7428f4ef7f585f2a9e8`. Strom
`baf5f1269478db19d591a97d75391d2342caa159` se shoduje se schváleným
druhým rodičem #198. [Doložený výřez T034](214_listCurrentProcessCandidates.md).

Přenesená dvojice má stejné bloby jako vývojový retry 2
`e347e424abed91223cc312f5d63e9c4dda9f0288` a
`57d8dfece745269cde78e9407a4c57bc687f4beb`. Nezávislá zdrojová kontrola
na dřívějším vývojovém základu zopakovala pět případů s raw exit 0 a
výstupem shodným po bajtech. SHA-256 jejího dokladu
`4e208b340b22b3c8881e71573503438549a9f2e8bf2db4a2ae8b621a68239052`.

Před zachycením měly přípravné kontroly v pracovním stromu
**32 PASS / 0 SKIP**, raw exit 0. Šlo o 19 T039 a 13 plánovacích
testů. SHA-256 JUnit
`daf87049405dbfd801ddc815d069cd793826e81056e9d0a8d279663f2737f70a`.
Příkaz je reprodukovatelný z kořene připraveného stromu.

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest --assert=plain -q \
  -p no:cacheprovider tests/test_t039_diff_architecture_and_processes.py \
  tests/test_completion.py --basetemp "$PROOF/light-pytest" \
  --junitxml "$PROOF/light.xml"
```

Plán na skutečném základu má SHA-256
`8cbb182386f273df03e115d8f3bb7659fec1245843f84d9cf78ad0fee56bf1bd`.
Po nahrazení jediného řádku T039 má SHA-256
`956a46d928446c82097282b14d8452e1147bb6b71dc16bcf75dc93f2d0a7855d`.
Oba běhy měly raw exit 0 a 135 položek. T039 je `IN_PROGRESS / PARTIAL`
s akcí `resume` a postupuje z třetí na druhou příčku. Ve výběru zůstává
stejných 32 položek a ostatní mají stejné vzájemné pořadí. T044 nadále
čeká na T039 s upraveným textem blokace. W03 dál vyžaduje u W02
`VERIFIED_IN_SCOPE`. Žádná další položka plánu se nezměnila.

Přijatý archiv strojového grafu #198 má SHA-256
`5819ee55b8f1ffe084d657686ddd04224701b4e049ad5190732c7c5b9287b4e9`,
rozbalené bajty podle dokladu o přijetí
`7e26c3ae411b05b0b6cf8ccc478f621b3f5b5c7820ac07a52dc1e12dca2d03a7`.
Verzovaná sémantika základu má 520 přijatých epizod. Poslední je
`episode:af8959c192baef8aaa187e9dcfed1499723676574e926aef0c4af575c6363d97`
ze skutečně přijaté verze #198.

## Přípravná kompozice sémantiky

Přípravná kompozice z přijatého základu měla raw exit 0 pro plán, 13
plánovacích testů, semantic update/apply/validate, dvě volání memory
capture, scan, status a check. Opakované zachycení identické změny
zachovalo bajty sémantiky a předběžného strojového vstupu. SHA-256
JUnit plánovače je
`b9773b87c0386f7a9e8da4a6ddac54d9f9f9544cd086f859c420285efcabef08`.

Kurátorovaný patch obsahoval 9 konceptů a 22 vztahů. U pěti konceptů
a šesti vztahů se posunul původní řádkový důkaz na stejný řádek textu
v nové pozici. Identifikátor sekce T029 přešel z řádku 591 na 641.
Všech 60 konceptů a 222 vztahů zachovalo význam a vazby. Zachovalo se
520 doslovně převzatých epizod včetně přijaté #198. Strojový graf
uchoval tři uzly Rates a jejich 275 vztahů. Nový soubor
`view_diff.py` přidal čtyři lokální importy, které jsou vidět v Mermaid.

První čtení vnějšího ověřovače skončilo raw exit 1, protože jeho parser
podporoval pouze obdélníkové uzly Mermaid a narazil na zděděný uzel
Kafka. Opravený ověřovač přečetl stejné bajty s raw exit 0. Výstupy
kompozice i ověřovaný strom zůstaly po tuto dobu beze změny.

Předběžná epizoda je
`episode:f98241fec172f518f237bf5d2fe2bb41af4227b915a97444aa9946992d17900f`.
Otisk předběžného strojového grafu je
`448fe406322d06676874c24d41a0c8f4aae173cfab394265f0baa2fbd3d3b18f`.
Výsledný graf znovu vzniká z ověřeného přijatého základu s tímto
zněním Change215. Jeho finální otisk a doklad skutečného kandidáta
mají samostatné uložení.

### Opakování kompozice

`BASE_GRAPH` označuje přijatý komprimovaný strojový graf po #198.
`PROOF` je zapisovatelný adresář mimo checkout a `CANDIDATE` je přesný
commit se sedmi běžnými změněnými soubory. V příkladu je `PYTHON`
binárka ze stejného místního prostředí jako v cílených testech.

```bash
set -euo pipefail
BASE=e63a82176623af8f6cd768868c282ac272749a6d
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
paths=(README.md docs/acceptance-inventory.md docs/changes/215_compareCapturedProcessViews.md
  docs/process-paths.md docs/production-analysis-progress.md
  src/kgmaker/view_diff.py tests/test_t039_diff_architecture_and_processes.py)
git diff --binary --full-index "$BASE" "$CANDIDATE" -- "${paths[@]}" > "$PROOF/ordinary.patch"
printf '%s  %s\n' 5819ee55b8f1ffe084d657686ddd04224701b4e049ad5190732c7c5b9287b4e9 "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' 7e26c3ae411b05b0b6cf8ccc478f621b3f5b5c7820ac07a52dc1e12dca2d03a7 .kgmaker/graph.json | sha256sum -c
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/before-plan.json"
git apply --index --check --whitespace=error-all "$PROOF/ordinary.patch"
git apply --index --whitespace=error-all "$PROOF/ordinary.patch"
git diff --cached --check "$BASE"
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan.json"
"$PYTHON" -B -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner" --junitxml "$PROOF/planner.xml"
"$PYTHON" -B -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" -B - "$BASE" .kgmaker/semantic-update.json .kgmaker/semantic-patch.json <<'CURATED'
import json, subprocess, sys
from pathlib import Path

base, update_file, patch_file = sys.argv[1:]

def original(path):
    return subprocess.check_output(['git', 'show', f'{base}:{path}']).decode().splitlines()

docs = 'docs/process-paths.md'
old, new = original(docs), Path(docs).read_text().splitlines()
assert old[:266] == new[:266] and old[266:] == new[316:]
assert old[590] == new[640] and old[590].startswith('## Static failure projection (T029)')
old_section = 'section:docs/process-paths.md:Static failure projection (T029)::591'
new_section = old_section.removesuffix('591') + '641'

update = json.loads(Path(update_file).read_bytes())
paths = {'README.md', 'docs/acceptance-inventory.md', 'docs/changes/215_compareCapturedProcessViews.md',
         docs, 'docs/production-analysis-progress.md', 'src/kgmaker/view_diff.py',
         'tests/test_t039_diff_architecture_and_processes.py'}
assert update['base_commit'] == base
assert {row['path'] for row in update['changed_files']} == paths
patch = {'schema_version': 1, 'update_id': update['update_id']}
readme_old, readme_new = original('README.md'), Path('README.md').read_text().splitlines()
for kind in ('nodes', 'edges'):
    patch[kind] = update[f'affected_semantic_{kind}']
    for row in patch[kind]:
        path, line = row['source_file'], row['source_line']
        if path == docs:
            position = line if line < 267 else line + 50
            assert old[line-1] == new[position-1]
            row['source_line'] = position
        elif path == 'README.md':
            assert readme_old[line-1] == readme_new[line-1]
        else:
            assert path not in paths
        for field in ('source', 'target'):
            if row.get(field) == old_section:
                row[field] = new_section
assert (len(patch['nodes']), len(patch['edges'])) == (9, 22)
Path(patch_file).write_text(json.dumps(patch, ensure_ascii=False, indent=2)+'\n')
CURATED
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

Po přesném zachycení následují cílené testy kandidáta a samostatná
úplná sada. Stav T039 zůstává `PARTIAL`.

## Doplnění po nezávislém ověření #199

T045 na veřejném kandidátovi
[`0a2ea9bb749e72ba532dbddbaaf1630a8cf96ed9`](https://github.com/p-rum/kgmaker/commit/0a2ea9bb749e72ba532dbddbaaf1630a8cf96ed9)
reprodukoval další případ T039-AC01. Přeházení `candidate_owner_ids`
v nejednoznačném řádku bez přiřazeného kontextu dalo `INCOMPARABLE` v obou
směrech. Ten samý řádek má podle T025 kandidáty z množiny známých vlastníků.
Zdrojový `views.py` sestaví kandidáty z množiny a `process_paths.py` zachová
tento řádek jako doklad v procesním snímku. Původní replay měl raw exit 1.
SHA-256 jeho JSON
`f3f9a0357a087fc4fa0185f37594686fd8413e88e611ca8cf6a1953f3fc7789d`.

Navazující úkol T052 upravil pouze kopii těchto seznamů pro porovnání.
Výstup zachovává původní pořadí každého snímku. Změna člena nebo četnosti
záznamů stále mění vazbu. Výběrový klíč, ID kontextu a otisk zachycení
zůstávají v porovnání. Test
`test_candidate_owner_order_is_irrelevant_but_membership_is_bound` ověřuje
oba směry, odlišné členství, opakovaný záznam a shodu bajtů vstupu.

Na původním zdroji měl cílený běh 19 PASS a 1 FAIL, raw exit 1.
SHA-256 jeho JUnit
`ea70c6e94ce54b78fb6bf4c0946d2af112a22ef7a5ce69f4dd93676eb7e732b1`.
Opravený pracovní strom má **102 PASS / 0 SKIP**, raw exit 0, z toho
20 T039, 69 T023 a 13 plánovacích testů. SHA-256 JUnit
`d81413daea3be362f532fef1d8d98cdc6c566948b44ccc1a7919640eadfc2d87`.
Výše uvedené přímé volání pytestu pokryje tento běh po doplnění souboru
`tests/test_t023_define_business_process_model.py`.

Nezměněný T045 probe na soukromém stromu přesné dvojice zdroje a testu
`b7f8b2f6387408ef9fbff04b59d773619c412b59` měl raw exit 0 a ověřil nulový
rozdíl v obou směrech. Shoda členství s odlišným pořadím je `COMPARABLE`.
Testovaná změna člena zůstala `INCOMPARABLE`. SHA-256 JSON
`308b66be638962683fa1f15ab137d3dcde290da08743b16435c0dab0b4821d71`.
Obě předchozí nezávislé kontroly s pěti případy stále mají raw exit 0
a stejné výstupy.

Kompozice navazujícího kandidáta používá uvedený čistý replay nad
skutečným základem #198. Opravující snapshot zachovává 520 přijatých
epizod a vytváří jednu vlastní epizodu z konečných běžných změn.
Doklad původního kandidáta #199 zůstává uložený samostatně. Jeho standardní
sada měla raw exit 1 se šesti chybami přípravy `ensurepip` ve společné
fixture instalovaných workerů. SHA-256 tehdejšího JUnit
`fee6d30a1d4e90a5f975ff5fdc0ad780a1f4f6ea1a72db8be897c415861b3dfc`.
Doklady přesného opravujícího kandidáta následují na jeho vlastním SHA.

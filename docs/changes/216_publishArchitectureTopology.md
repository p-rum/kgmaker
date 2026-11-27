# Atomický export zachycené architektonické topologie

27. listopadu 2026. [T038](../tasks/T-038_publish-view-artifacts-atomically.md),
kroky S01–S05 a kritéria AC01–AC06. Přípravný základ
`384fc6a3fee56b11f6e30d1123e58fff055ff1f8`, strom
`ae82d73ab85c06641a00fc40eae6e40b964208c1`.
Úkol T052 `task:3a9ab683c2971981fe5603462e97a7656e8db737e4cb52f253991616694e9c4d`.

## S01 — chybějící cesta a dodaný vstup

Ve výchozím stromu veřejné `architecture topology` ze stejného zachyceného
T016 vstupu úspěšně vrátilo JSON, Markdown i Mermaid. Zachovalo vztah HTTP
`service:checkout → service:orders`, pokrytí `PARTIAL` a u výběru jednoho
uzlu dohledatelnou hranici vynechání. V Mermaid byla shodná filtrovací obálka
JSON a Markdown obsahoval stejný diagram bajt po bajtu. Stejný vstup předaný do
`architecture export` vrátil `INVALID_ARGUMENTS`, raw exit 2 a prázdný stdout.
Vstup zůstal shodný a výstupní adresář nevznikl. Přípravný JSON doklad
má SHA-256 `23c6258a3eaa83ea3aa9851d1db4d9815c74445d66ae81c390fbff702b3a94b3`.

[Architektonické CLI](../../src/kgmaker/architecture_cli.py) přidává
`architecture export --capture-snapshot ... --output ...` nad jedním
explicitním T016 capture. Používá stávající validaci a agregaci T016, filtry
T017 a [renderery](../../src/kgmaker/architecture_render.py) T021/T022.
JSON obsahuje celou filtrovací obálku. Markdown vkládá stejný diagram
Mermaid a uvádí vybrané kontexty, důkazy a vynechané hranice. Otisk
`view_fingerprint` je shodný s `architecture topology --expected-fingerprint`
pro tentýž vstup a filtry. `--scope` ověřuje zachycený scope a
`--filter-contexts` omezuje zobrazení v daném zachycení.

## S02 — omezené cesty a společná generační publikace

[Společný CLI adaptér](../../src/kgmaker/_view_export_cli.py) používá
stávající [publikaci](../../src/kgmaker/view_store.py) ze sloučeného
[procesního exportu #194](https://github.com/p-rum/kgmaker/pull/194).
Jediný potvrzený manifest verze 1 s `view_kind: topology` ukazuje na
`view.json`, `view.md` a `view.mmd` v jedné neměnné generační složce.
Každá položka nese SHA-256 konkrétních bajtů. Čtenář načte všechny formáty
podle jednoho manifestu a dřívější generace zůstane dostupná.

Cíl je samostatný adresář pod kořenem koordinátora. Traversal, symlinky
a nepřípustné cesty se odmítnou před výměnou. Existující manifest jiného
druhu se odmítne jako `INVALID_EXPORT_MANIFEST`. Aktuální měření je z Linuxu
s požadovanými operacemi POSIX. Graph/store i workspace formáty a manifest
procesního exportu zůstávají kompatibilní. Doménová validace a čtecí
příkazy dál používají dosavadní modely.

## S03 — zachování vstupu a poslední platné generace

Výměna manifestu používá stávající compare-and-swap. Ověřuje stav vstupu
před přepnutím a kontroluje kooperativní časový limit i značku zrušení.
Dva zápisy se stejným původním manifestem mají právě jeden úspěch.
Shodný aktivní export vrátí stejný manifest. Selhání druhého rendereru,
nesouhlas scope či fingerprintu, zjištěná změna vstupu, zrušení nebo
timeout před potvrzením zachovají předchozí výstup.
Typické diagnostiky jsou `EXPECTED_FINGERPRINT_MISMATCH` a
`EXPORT_INPUT_CHANGED` s kódem 3, `CANCELLED` s kódem 130 a
`EXPORT_TIMEOUT` s kódem 1.

Po potvrzené výměně je uložený manifest směrodatný. Přerušení výpisu
potvrzení může hlásit `EXPORT_RECEIPT_INTERRUPTED` s kódem 1 i při
platném uloženém manifestu. Dosavadní procesní zkoušky tohoto předání
používají přemístěné testovací body ve společném adaptéru. Ostatní očekávání
procesních zkoušek zůstala v přípravném diffu shodná. Rozdíl
`process_cli.py` se při třícestném náhledu s rozpracovaným T034 sloučil
s raw exit 0. Náhled ověřil složení zdrojových změn.

## S04 — provedené přípravné kontroly

Ověřený přípravný strom `146abf2e63c34910d8dc8a0b4fb4d091af357b99`,
SHA-256 zdrojového patche
`eac38c237cd76994160a1a01726438221d94ccff2b07cfe5b2491a06c9df52ff`.
Souhrnný doklad `implementation-source.receipt.json` má SHA-256
`3486a9a57658c8378bdc63fe0f8541c6b1c6f11bf50a8fa83f309b038ede512b`.

| Běh | Výsledek | SHA-256 JUnit |
|---|---|---|
| RED na výchozích produkčních bajtech | 8 FAIL / 0 SKIP, raw 1. Příkaz chyběl ve všech osmi případech. | `ef423d84c73225862431da3670cb15126029fdea92e3b1a387247f5d54ba5e0e` |
| První cílený běh | 111 PASS / 1 FAIL / 1 SKIP, raw 1. Jeden procesní test používal staré umístění objektu publikace. Původní T034 fixture přeskočila kvůli nedostupnému připnutému Maven artefaktu. | `c752371ae8a1c31107d7eed3017d3cf578a94a6b4ac8a7ca37dde4d873f00367` |
| Opakovaný cílený běh | 113 PASS / 0 SKIP, raw 0 po opravě umístění testu a připojení již připravených závislostí. | `c47cf8957059c56a7a27710e4d1d70998c3ec1e2220ad2c45ce352cde350a436` |

Přípravný běh na CPython 3.13.18 použil Node 24.22.3, Mermaid 11.4.1,
jsdom 26.0.0, markdown-it-py 3.0.0 a pro původní T034 test připnutý
Temurin 21.0.6+7 s JVM workerem a API z připnutého Maven repozitáře.
Manifesty připravených souborů před a po běhu mají shodný SHA-256
`72124d8382b9ab1a8ac0845fbc445ea7446ebbe887745b566640f191cc1d2693`.
Z 113 kontrol je 11 nových architektonických, 27 původních procesních,
34 T019, 28 T021, 12 T022 a jedna původní T034. Kontroly staged diffu,
reverzní aplikovatelnosti patche a zdrojové shody mají raw exit 0.
Pokus `kgmaker memory recall` skončil kódem 2 kvůli chybějícímu strojovému
grafu v odděleném přípravném worktree.

| Kritérium | Konkrétní kontrola v architektonickém výřezu |
|---|---|
| AC01 | `test_public_export_matches_three_read_formats_and_retains_generations` ověřuje hash a bajty všech formátů, shodu s čtecími příkazy, opakování i dostupnost starší generace. |
| AC02 | `test_rejected_or_interrupted_export_preserves_previous_generation` pokrývá selhání druhého rendereru, pozdní zrušení a timeout. |
| AC03 | `test_topology_writers_cannot_commit_from_the_same_manifest` prokazuje právě jeden commit. `test_confinement_and_foreign_kind_are_rejected_without_changes` ověřuje cestu mimo kořen, symlink a cizí manifest. |
| AC04 | Stejné negativní případy kontrolují shodu poslední generace i vstupu s výjimkou záměrné mutace vstupu v testu pozdní změny. |
| AC05 | `test_parser_and_renderer_accept_exported_artifacts` parsuje publikovaný Markdown a Mermaid a ověřuje skutečné vykreslení SVG se dvěma vrcholy a jednou hranou. Veřejné porovnání zachovává `PARTIAL`, skutečný filtr a vynechanou hranici. |
| AC06 | Přípravný zdrojový rozsah a přesná ověření jsou doloženy tímto záznamem. Úplné ověření a review publikované revize jsou samostatné. |

Pro lokální reprodukci RED přenes původní `implementation-red-test.patch`
(SHA-256 `b25089a46f628d390a1f1db4b75676a55646849be0c15866dd411a243a976ff6`)
do oddělené kopie výchozí revize. Druhý příkaz použij na přípravném opraveném
stromu s dostupným `tests/rendering/node_modules` podle lockfile a s
připraveným K1 workerem v `workers/jvm/target`. `PYTHON`, `JDK` a `MAVEN`
jsou absolutní cesty k připnutým nástrojům. `PROOF` je zapisovatelný
adresář mimo checkout.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  "$PYTHON" -B -m pytest -q -p no:cacheprovider --tb=line \
  --junitxml="$PROOF/implementation-red.xml" --basetemp="$PROOF/implementation-red-tmp" \
  tests/test_t038_publish_architecture_export.py::test_public_export_matches_three_read_formats_and_retains_generations \
  tests/test_t038_publish_architecture_export.py::test_rejected_or_interrupted_export_preserves_previous_generation

env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
  PATH="$JDK/bin:$PATH" JAVA_HOME="$JDK" JAVA_TOOL_OPTIONS=-XX:-UsePerfData \
  KGMAKER_TEST_MAVEN_REPOSITORY="$MAVEN" KGMAKER_REQUIRE_WORKERS=1 \
  KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  "$PYTHON" -B -m pytest -q -p no:cacheprovider --tb=short \
  --junitxml="$PROOF/implementation-green-retry.xml" --basetemp="$PROOF/implementation-green-retry-tmp" \
  tests/test_t038_publish_architecture_export.py tests/test_t038_publish_view_artifacts_atomically.py \
  tests/test_t019_add_architecture_json_cli.py tests/test_t021_render_topology_mermaid.py \
  tests/test_t022_render_topology_markdown.py tests/test_t034_add_process_cli.py
```

První cílený běh měl stejných šest testovacích souborů a volby pytest.
Použil výstupy `implementation-green.xml`, `implementation-green-tmp`
a připnutý parser, ještě bez připojení konkrétního JVM workeru a jeho Maven
závislostí. Samostatný veřejný smoke má raw Python exit 0 a vnější
obal nástroje uvedl 1. Nezávislý cílený pytest běh potvrdil stejnou
publikační smlouvu a jeho obal i pytest skončily kódem 0.

### S04 — oprava přenositelnosti testu v iteraci 1

Nezávislá kontrola nad zdrojovým stromem
`146abf2e63c34910d8dc8a0b4fb4d091af357b99` simulovala nepřítomný Markdown
parser. Import na úrovni modulu přeskočil celý testovací soubor a výběr
tří čistých kontrol skončil raw 5. Se skutečným Markdown parserem a
prázdným `PATH` nativní test skončil raw 1 s `FileNotFoundError` při
spuštění Node. T052 vrátil opravu do implementace
(`artifact:f811c13145fe9ab501558dc3a10df38212fcec74af119fa5530a22ca1474c7e3`).

Test nyní importuje parser až v jediné nativní zkoušce. Node ověřuje
explicitním vyhledáním. Stejný skript s nepřítomným Markdown parserem
vrátil **3 PASS**, raw exit 0. S nepřítomným Node přeskočil jediný nativní
případ, raw exit 0. Samostatná kontrola chybějícího volitelného Markdown
parseru přeskočila právě nativní zkoušku. S
`KGMAKER_REQUIRE_MARKDOWN_PARSER=1` skončila tatáž zkouška očekávaně
raw exit 1 s diagnostikou o chybějícím povinném parseru.

Bajtově stejný skript obou běhů má SHA-256
`6e2bd818b97adb7e80a9c0ed8b8586cf2eba95822d844a0e7a6d57ffb95a0e10`.
Souhrn nepřítomného Markdownu a Node po opravě má SHA-256
`2c8fc5dd5a6ddbe7d1ee026ddd087d78be0783b50b36942cb6291a02577731f4`.
Změněný architektonický testovací soubor s dostupnými připnutými parsery
má **11 PASS / 0 SKIP**, raw pytest exit 0, JUnit SHA-256
`72fa90305ba7e90dd9f06d779c58d6735febfde00dd00db073c799019ba9d15c`.
Vnější nástroj u tří spuštění vykázal kód 1. Samostatné záznamy výsledků
obou ověřovacích skriptů a pytest obsahují raw 0 a byly zkontrolovány
samostatným příkazem s kódem 0.

Přípravný strom po opravě je `f739b998836ede5bc453551a655b0689694650bc`.
SHA-256 samotné opravy je
`e1db43e0f18a448ca3f440e71862803b96b4126e172f8a4651dbdcc8e1cb7e8b`.
Produkční soubory i stávající procesní testy zůstaly bajtově stejné.
Opakování výběru ze všech šesti souborů na tomto přípravném stromu má
stav `NOT_RUN`. Výše uvedených 113 PASS patří předchozímu stromu.

```bash
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$PROOF/portability-probe.py"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B "$PROOF/markdown-native-paths.py"
KGMAKER_REQUIRE_MARKDOWN_PARSER=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  "$PYTHON" -B -m pytest -q -p no:cacheprovider --tb=short \
  --junitxml="$PROOF/native.xml" --basetemp="$PROOF/native-tmp" \
  tests/test_t038_publish_architecture_export.py
```

## S05 — veřejný příklad a rozsah ověření

Následující příklad vytvoří známý vstup T016 ze stejné existující testovací
fixture a pak zavolá skutečné veřejné CLI. Cesta vstupu je explicitní.
Očekávaný SHA-256 zachycení je
`25084140c34df5d66e3872545f772637a55ee76ab79118b2b092be9efdb5335e`.
Na výchozím stromu vrátí stejný export raw 2. Pro každý běh použij čerstvý
adresář `PROOF/fixture`.

```bash
mkdir -p "$PROOF/fixture"
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B - "$PROOF/fixture/topology-inputs.json" <<'PY'
from pathlib import Path
import json
import sys

from test_t016_aggregate_service_topology import labelled_handoff

Path(sys.argv[1]).write_text(json.dumps(labelled_handoff(), ensure_ascii=False) + "\n")
PY
sha256sum "$PROOF/fixture/topology-inputs.json"
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -B -m kgmaker architecture export \
  --root "$PROOF/fixture" --capture-snapshot topology-inputs.json \
  --output reports/topology > "$PROOF/manifest.json"
cmp "$PROOF/manifest.json" "$PROOF/fixture/reports/topology/manifest.json"
```

Přípravný rozsah zahrnuje zachycenou topologii a technický ProcessView.
T041 vyžaduje vlastní průchod se skutečnou extrakcí, workerem, více
repozitáři, explain a uloženým exportem. Na tomto přípravném stromu mají
úplná standardní sada, hostované GitHub Actions, nativní publikace na
jiném OS, finální grafový transfer a formální review stav `NOT_RUN`.
[Použití](../architecture-json-cli.md#atomic-topology-export-t038) ·
[Acceptance](../acceptance-inventory.md#t038--atomická-publikace-dodaného-processview) ·
[Stav](../production-analysis-progress.md) ·
[Zadání T041](../tasks/T-041_verify-architecture-acceptance.md)

## Přenos po sloučení #199

Základem přenosu je [sloučení #199](https://github.com/p-rum/kgmaker/pull/199)
`e7391ea58bb4d6e519a1886c309710752d8472e4`, strom
`31a22963555e154b642f5030b85e2a98ab6bf663`. Jeho rodiče jsou
`e63a82176623af8f6cd768868c282ac272749a6d` a
`e065c8317ad4cc693a18245924e1e8e6fd029173`. Poslední change note v
základu má číslo 215. Při kontrole GitHubu neměly otevřené PR #153, #118
ani #4 kolizi s číslem 216.

Záplata přípravného zdroje a dokumentace má SHA-256
`ba0f35dbe605512e5805f58d1832a7c9ff30875e725ce4f94f8ccb1376c89b04`.
Kontrola a aplikace do indexu na skutečném základu měly raw exit 0 a
vytvořily přípravný strom `3dd817865deda650db7d3c632a7302845c08dfb8`.
Pět zdrojových a testovacích souborů se shoduje s opraveným zdrojovým
stromem. `process_cli.py` zachovává implementace T034 `_list` a `_render`
i rozpoznání příkazů. Část `_export` se shoduje s opraveným zdrojovým
stromem. Soubor T039, jeho testy, příklady a záznam změny zůstaly bajtově
shodné. [Dosavadní T034](214_listCurrentProcessCandidates.md) ·
[Dosavadní T039](215_compareCapturedProcessViews.md)

Nad přijatým grafem #199 prošly `semantic validate`, `check` a
`memory recall` s raw exit 0. `completion plan --jobs 32` před a po
přenosu skončil raw exit 0 a zachoval všech 135 položek a jejich stejný
výběr o 32 pozicích. Změnil se digest stavového inventáře. T038 zůstává
`MERGED / PARTIAL`, T041 `NOT_RUN` a W03 čeká na
`VERIFIED_IN_SCOPE` u W02-AC01. Předběžný plán má SHA-256
`956a46d928446c82097282b14d8452e1147bb6b71dc16bcf75dc93f2d0a7855d`, plán po přenosu `e38849a88cdc0b7ffc50618caa7c71b5772cbbe48031569765c1fe7ba5407649`.
Testy plánovače mají **13 PASS / 0 SKIP**, raw exit 0, JUnit SHA-256
`eb99690f8fdeb6f972ea1fcc05de8630d167498251dad0a82d5e0f5aa6196746`.

Před doplněním tohoto oddílu skončily příkazy `semantic update`,
`semantic apply`, obě sémantické validace, obě volání `memory capture`,
`scan`, `status`, `check` a kontroly diffu s raw exit 0. Packet
označil dva kurátorované koncepty a 18 vztahů. U sedmi existujících
vztahů byly ověřeny posuny locátorů citace na totožný text. Dva
strukturální identifikátory architektonického CLI odpovídají aktuálním
identifikátorům scanneru. Zachovalo se všech 60 kurátorovaných konceptů a
222 vztahů.

Přípravný výsledek má strom `941548cf6a185e2b173ca8d85781b3f7b9ba7a11`, strojový graf SHA-256
`8d8853749e2bd8fdc8bc72bf575b81b1d3f7d2b702a155e3b6da66078129cd9e` a jednu novou epizodu `episode:ce33a6687cb7c7ca5e46f05274a4173953793c0d70c1827da6d84dee26087d6d`.
Všech 521 přijatých epizod zůstalo doslova shodných. Opakované zachycení
našlo tutéž epizodu a ponechalo bajty sémantiky i vstupního grafu shodné.
Zůstaly zachované tři uzly Rates a všech 275 souvisejících vazeb.
Zachovalo se 665 existujících importů. Přibylo
9 ověřených lokálních importů a Mermaid zobrazil nový
společný CLI adaptér a 5 jeho souvisejících hran.
Přípravný rozdíl má 121 přidaných, 88 odebraných a
0 změněných strukturních uzlů. Všech 514 dotčených uzlů
souvisí s přenášenými cestami. Finální zachycení znovu vychází
z přijatého grafu #199 a zahrnuje i bajty tohoto oddílu. Otisk finální
epizody a grafu je uložen mimo zachycované soubory.

Přesný cílený, nativní a úplný standardní běh publikovaného kandidáta
a nezávislé review mají v přípravném ověření stav `NOT_RUN`.
Technický ProcessView a zachycený architektonický pohled tvoří dva
ověřené přípravné výřezy T038. [T041](../tasks/T-041_verify-architecture-acceptance.md)
vede vlastní produkčně věrnou fixture a průchod přes skutečný worker,
katalog, topologii, explain i uložený export.

### Reprodukce přenosu a sémantické validace

`CANDIDATE` označuje finální revizi T038, `BASE_GRAPH` přijatý archiv #199,
`PROOF` zapisovatelný adresář mimo checkout a `PYTHON` CPython 3.13.18
s pytestem. Spusť z čisté oddělené větve na `BASE`.

```bash
set -euo pipefail
BASE=e7391ea58bb4d6e519a1886c309710752d8472e4
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
paths=(README.md docs/acceptance-inventory.md docs/architecture-json-cli.md
  docs/changes/216_publishArchitectureTopology.md docs/production-analysis-progress.md
  src/kgmaker/_view_export_cli.py src/kgmaker/architecture_cli.py src/kgmaker/architecture_render.py
  src/kgmaker/process_cli.py tests/test_t038_publish_architecture_export.py
  tests/test_t038_publish_view_artifacts_atomically.py)
git diff --binary --full-index "$BASE" "$CANDIDATE" -- "${paths[@]}" > "$PROOF/t038.patch"
printf '%s  %s\n' 4b361040f80bafe27a971016e36d758f55a006723ff327e20a20c1c4a455a925 "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' 70d1adddb617d99109ab361a26cfa5ca8cd014bc3606733233badf1ba7340d4c .kgmaker/graph.json | sha256sum -c
"$PYTHON" -B -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -B -m kgmaker check --root "$PWD"
"$PYTHON" -B -m kgmaker memory recall 'T038 explicit architecture topology export atomic manifest' --root "$PWD"
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-before.json"
git apply --index --check --whitespace=error-all "$PROOF/t038.patch"
git apply --index --whitespace=error-all "$PROOF/t038.patch"
git diff --cached --check "$BASE"
"$PYTHON" -B -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan-after.json"
"$PYTHON" -B -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml "$PROOF/planner.xml"
"$PYTHON" -B -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" -B - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

base = sys.argv[1]
update = json.loads(Path('.kgmaker/semantic-update.json').read_bytes())
assert update['base_commit'] == base
paths = {
    'README.md',
    'docs/acceptance-inventory.md',
    'docs/architecture-json-cli.md',
    'docs/changes/216_publishArchitectureTopology.md',
    'docs/production-analysis-progress.md',
    'src/kgmaker/_view_export_cli.py',
    'src/kgmaker/architecture_cli.py',
    'src/kgmaker/architecture_render.py',
    'src/kgmaker/process_cli.py',
    'tests/test_t038_publish_architecture_export.py',
    'tests/test_t038_publish_view_artifacts_atomically.py',
}
assert {row['path'] for row in update['changed_files']} == paths
assert [len(update[f'affected_semantic_{kind}']) for kind in ('nodes', 'edges')] == [2, 18]
architecture = 'src/kgmaker/architecture_cli.py'
process = 'src/kgmaker/process_cli.py'
lines = {architecture: {155: 171, 308: 350, 321: 365, 327: 371, 333: 377},
         process: {143: 139}}
identities = {
    f'function:{architecture}:run::306': f'function:{architecture}:run::348',
    f'function:{architecture}:_preflight::153': f'function:{architecture}:_preflight::169',
}
patch = {'schema_version': 1, 'update_id': update['update_id']}
for kind in ('nodes', 'edges'):
    patch[kind] = update[f'affected_semantic_{kind}']
    for row in patch[kind]:
        line = row['source_line']
        row['source_line'] = lines.get(row['source_file'], {}).get(line, line)
        for endpoint in ('source', 'target'):
            if row.get(endpoint) in identities:
                row[endpoint] = identities[row[endpoint]]
Path('.kgmaker/semantic-patch.json').write_text(json.dumps(patch, indent=2, ensure_ascii=False) + '\n')
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
git diff --exit-code "$BASE" -- .kgmaker/NOTES.md
git add -- .kgmaker/GRAPH.md .kgmaker/GRAPH.mmd .kgmaker/semantic.json
git diff --cached --check "$BASE"
```

# Přítomnost hodnoty s doprovodným záznamem volání

27. listopadu 2026. [T003-S13-W03](../tasks/T003-S13-03-runtimeValueFlow.md),
kroky 1–5, AC01–AC04, nadřazená T003-AC13 a dokumentační T048-AC09.
Původní zdrojový základ je `f7015b61473a0700d979157eeba271c480c21cb8`.
Validační doklady níže patří původnímu zdroji. Výřez i celý work package
mají při místním předání stav `IN_PROGRESS / PARTIAL`.

## Krok 1 a AC01 — reprodukce

Explicitně spuštěná Java fixture zapíše běžné `call`, jeden hodnotový
vzorek a další `call`. Původní validátor v4 odmítne platný vzorek kvůli
počtu faktů. Případ
`test_actual_java_value_presence_affects_only_matching_live_data_check[same-line]`
na nezměněném produktu a nové fixture skončil `RUNTIME_VALUE_FACT`,
1 FAIL, 0 SKIP a raw exit 1. JUnit SHA-256
`cf047e9275316d05f8737f40af92f15984de0c95e51b0ed59b7922fa9b41b342`.
Pro zopakování použijte historický commit z veřejné historie a fixture
s testem z právě stažené revize kandidáta. `S13_REPO` a `S13_EVIDENCE`
jsou absolutní cesty k repozitáři a zapisovatelnému adresáři. `S13_REVISION`
určuje stažený commit kandidáta, `S13_PYTHON` Python s pytest,
`JAVA_HOME` JDK 21 a `KGMAKER_WORKERS_HOME` připnutý worker popsaný
v kroku 4. Zdroj validátoru zůstane v izolovaném archivu historického commitu.

```bash
set -euo pipefail
red_dir=$(mktemp -d "$S13_EVIDENCE/w03-red.XXXXXX")
mkdir "$red_dir/source" "$red_dir/java-tmp"
historical_base=f7015b61473a0700d979157eeba271c480c21cb8
candidate=$(git -C "$S13_REPO" rev-parse --verify "$S13_REVISION^{commit}")
fixture=tests/fixtures/runtime-trace/ValuePresenceApplication.java
value_test=tests/test_runtime_value_presence.py
test "$(git -C "$S13_REPO" rev-parse "$candidate:$fixture")" = \
  2dfca05d57fcea7238af1c4c12409bbb58d7c98b
test "$(git -C "$S13_REPO" rev-parse "$candidate:$value_test")" = \
  4707f7cbf266d0aaaa47ff83754c804e87cabfe5
git -C "$S13_REPO" archive "$historical_base" | tar -x -C "$red_dir/source"
git -C "$S13_REPO" archive "$candidate" "$fixture" "$value_test" | tar -x -C "$red_dir/source"
cd "$red_dir/source"
git -C "$S13_REPO" show "$historical_base:src/kgmaker/runtime_evidence.py" | \
  cmp - src/kgmaker/runtime_evidence.py
export JAVA_HOME KGMAKER_WORKERS_HOME
export PATH="$JAVA_HOME/bin:$PATH"
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData TMPDIR="$red_dir/java-tmp"
export KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
code=0
env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
  "$S13_PYTHON" -m pytest -q --assert=plain -p no:cacheprovider \
  --basetemp "$red_dir/pytest" --junitxml "$red_dir/red.xml" \
  'tests/test_runtime_value_presence.py::test_actual_java_value_presence_affects_only_matching_live_data_check[same-line]' \
  > "$red_dir/red.log" 2>&1 || code=$?
printf '%s\n' "$code" > "$red_dir/red.exit"
test "$code" -eq 1
grep -F 'RUNTIME_VALUE_FACT' "$red_dir/red.log"
```

## Krok 2 a AC02 — kompatibilita formátu

`src/kgmaker/runtime_evidence.py` podporuje v RuntimeManifest v4 jeden
`value_presence` a běžné `call` v existujícím uzavřeném poli `facts`.
Stav zůstává `PARTIAL / INSTRUMENTED_SCOPE_ONLY`. Pole a verze manifestu,
původní samostatný v4, podpora v1–v3, SDK, parametry CLI i graph/store v3
zachovávají dosavadní kontrakt. Původní čtečka v4 kombinovaný tvar odmítne.
Po návratu ke staršímu programu použijte původní samostatné exporty.
Novější exporty lze ponechat k pozdějšímu čtení současnou verzí.

## Krok 3 a AC01/03 — hodnotový import a živé čtení

Doprovodná volání si v exportu zachovají pořadí. Používají stávající
uzavřený tvar `call` a validaci obou volatelných symbolů v zachyceném
compiler kontextu. Import odvodí jediný hodnotový záznam a stejné formáty
grafového dokladu. Doprovodné facts zůstanou v exportu a statické cesty i
runtime vazby volání a dispatch se řídí dosavadními doklady. Čerstvý
`PRESENT` z přesného Java `String` přiřazení s účinným schváleným
mapováním může živému `data-check` doložit `PARTIAL/UNASSESSED` pro
jeden běh. `ABSENT`, call-only a prošlý důkaz ponechají `UNKNOWN`.

## Krok 4 a AC01–AC03 — nativní a regresní kontroly

[`ValuePresenceApplication.java`](../../tests/fixtures/runtime-trace/ValuePresenceApplication.java)
a [test](../../tests/test_runtime_value_presence.py) ověřují skutečné
Javac varianty hooku na stejném a následujícím řádku, pořadí záznamů,
uložené `value_evidence_ids` a výsledek živého čtení. Odmítají chybějící
nebo druhý vzorek, jiné typy faktů, cizí symboly, neplatný výsledek volání,
pole navíc a zastaralý zdroj. Negativní případy zachovají poslední export i
grafové výstupy. Offline import v testu zakáže spouštění podprocesů.
Regrese ověřují dřívější v1 a v2 import, opt-in v2 capture a obě v3
varianty skutečného synchronního dispatch.

Opravený zdrojový strom `1064e59bd97347aefeffd76b7c0f614f3196db2e`
skončil 16 PASS, 0 SKIP, 0 FAIL a raw exit 0. JUnit SHA-256
`995054ca9fa0150ab2214cb4d622f77447497f45dbe985735776fefe7dd340f6`.
Shodný manifest 950 souborů před a po má SHA-256
`395b7b29524bd8b9923839a9fc41d3aa16cfbd6975c6d234917249ddfabe3907`.
Použity byly CPython 3.12.14, skutečný Temurin JDK 21.0.6+7 a 15 ověřených
položek distribuce workeru a JDK.

Reprodukční příkaz pro stejný výběr testů používá izolovaný Git archiv.
`S13_REPO` a `S13_EVIDENCE` jsou absolutní cesty k repozitáři a
existujícímu adresáři pro výstupy. Pro běžné ověření použijte
`S13_REVISION` z právě staženého commitu kandidáta. Původní lokální strom
výše slouží k identifikaci historického důkazu.
`S13_PYTHON` je Python s pytest,
`JAVA_HOME` je JDK a `KGMAKER_WORKERS_HOME` je kořen distribuce workerů
s `jvm/target`. U jiného připraveného toolchainu zaznamenejte jeho
verze a hash zvlášť.

```bash
set -euo pipefail
run_dir=$(mktemp -d "$S13_EVIDENCE/w03-native.XXXXXX")
mkdir "$run_dir/source" "$run_dir/java-tmp"
revision=$(git -C "$S13_REPO" rev-parse --verify "$S13_REVISION^{commit}")
git -C "$S13_REPO" archive "$revision" | tar -x -C "$run_dir/source"
git -C "$S13_REPO" ls-tree -rz --name-only "$revision" > "$run_dir/tracked.z"
git -C "$S13_REPO" show -s --format='%H %T %P' "$revision" > "$run_dir/revisions.log"
cd "$run_dir/source"
export JAVA_HOME KGMAKER_WORKERS_HOME
export PATH="$JAVA_HOME/bin:$PATH"
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData TMPDIR="$run_dir/java-tmp"
export KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1
"$S13_PYTHON" --version
"$JAVA_HOME/bin/javac" --version
"$JAVA_HOME/bin/java" --version

pin_manifest() {
  (cd "$KGMAKER_WORKERS_HOME" && export LC_ALL=C &&
    sha256sum jvm/target/kgmaker-jvm-worker.jar jvm/target/lib/*.jar)
  (cd "$JAVA_HOME" && sha256sum bin/java bin/javac lib/server/libjvm.so lib/libjli.so)
}

pin_manifest > "$run_dir/pins-before.sha256"
printf '%s  %s\n' ad54d197e4ebadb93ea6065eee090f4f37d9f3666600fabce0fcf6292268dc6d \
  "$run_dir/pins-before.sha256" | sha256sum -c
xargs -0 sha256sum < "$run_dir/tracked.z" > "$run_dir/before.sha256"
code=0
env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS -u CLASSPATH \
  "$S13_PYTHON" -m pytest -q --assert=plain -p no:cacheprovider \
  --basetemp "$run_dir/pytest" --junitxml "$run_dir/native.xml" \
  tests/test_runtime_value_presence.py \
  tests/test_runtime_trace_producer.py::test_runtime_import_retains_same_edge_observations_and_v2_variant_identity \
  tests/test_runtime_trace_producer.py::test_actual_jdk21_capture_is_opt_in_and_records_only_executed_branch \
  'tests/test_runtime_trace_producer.py::test_jdk21_interface_dispatch_binds_concrete_receiver_and_call_site[alpha]' \
  'tests/test_runtime_trace_producer.py::test_jdk21_interface_dispatch_binds_concrete_receiver_and_call_site[beta]' \
  > "$run_dir/native.log" 2>&1 || code=$?
printf '%s\n' "$code" > "$run_dir/native.exit"
xargs -0 sha256sum < "$run_dir/tracked.z" > "$run_dir/after.sha256"
pin_manifest > "$run_dir/pins-after.sha256"
cmp "$run_dir/before.sha256" "$run_dir/after.sha256"
cmp "$run_dir/pins-before.sha256" "$run_dir/pins-after.sha256"
test "$code" -eq 0
"$S13_PYTHON" - "$run_dir/native.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET

cases = ET.parse(sys.argv[1]).findall(".//testcase")
assert len(cases) == 16
assert all(c.find(k) is None for c in cases for k in ("error", "failure", "skipped"))
PY
sha256sum "$run_dir/native.xml" "$run_dir/before.sha256" "$run_dir/pins-before.sha256"
```

### Úplná standardní sada

Pro stejný commit použijte nový izolovaný archiv. `S13_STD_PYTHON` je
CPython 3.13.18 s testovacími závislostmi. `JAVA_HOME` označuje JDK 21,
`S13_RUNTIME_LAUNCHER_BIN` adresář místních launcherů pro build fixture,
`S13_GRADLE_BIN` adresář bin distribuce Gradle 8.13 a `GRADLE_USER_HOME`
jeho připravenou místní cache. Gradle potřebuje místní loopback. Výběr
nativních testů a jejich povinné workery se ověřují samostatným během výše.

```bash
set -euo pipefail
std_dir=$(mktemp -d "$S13_EVIDENCE/w03-standard.XXXXXX")
mkdir "$std_dir/source" "$std_dir/java-tmp"
revision=$(git -C "$S13_REPO" rev-parse --verify "$S13_REVISION^{commit}")
git -C "$S13_REPO" archive "$revision" | tar -x -C "$std_dir/source"
git -C "$S13_REPO" ls-tree -rz --name-only "$revision" > "$std_dir/tracked.z"
git -C "$S13_REPO" show -s --format='%H %T %P' "$revision" > "$std_dir/revisions.log"
cd "$std_dir/source"
xargs -0 sha256sum < "$std_dir/tracked.z" > "$std_dir/before.sha256"
export JAVA_HOME GRADLE_USER_HOME
export PATH="$S13_RUNTIME_LAUNCHER_BIN:$S13_GRADLE_BIN:$JAVA_HOME/bin:$PATH"
export JAVA_TOOL_OPTIONS=-XX:-UsePerfData TMPDIR="$std_dir/java-tmp" PYTHONPATH="$PWD/src"
unset KGMAKER_REQUIRE_WORKERS KGMAKER_REQUIRE_K2 KGMAKER_WORKERS_HOME
"$S13_STD_PYTHON" --version > "$std_dir/python.log"
code=0
"$S13_STD_PYTHON" -m pytest -q -p no:cacheprovider -o tmp_path_retention_policy=failed \
  --basetemp "$std_dir/pytest" --junitxml "$std_dir/standard.xml" \
  > "$std_dir/standard.log" 2>&1 || code=$?
printf '%s\n' "$code" > "$std_dir/standard.exit"
xargs -0 sha256sum < "$std_dir/tracked.z" > "$std_dir/after.sha256"
cmp "$std_dir/before.sha256" "$std_dir/after.sha256"
test "$code" -eq 0
sha256sum "$std_dir/standard.xml" "$std_dir/before.sha256"
```

## Krok 5 a AC04 — dokumentace a další ověření

[README](../../README.md), [runtime capture a import](../runtime-trace.md#přítomnost-hodnoty-po-přímém-přiřazení-v-javě),
[živá kontrola](../feature-analysis.md#runtime-presence-in-data-check),
[acceptance](../acceptance-inventory.md#t003-s13-w03--přítomnost-hodnoty-po-přímém-přiřazení)
a [stavová matice](../production-analysis-progress.md) popisují omezený
rozsah. Identita, revize specifikace a závislosti zadání se nemění.
Instanční pole, další typy a vícekrokové toky, Windows, async a reflexe
mají vlastní ověření. Změna nedokládá úplnou dostupnost ani použitelnost.

Při původní přípravě na `f7015b6` měly grafové kontroly přenosu, přesný
nativní běh a úplná sada na tehdy budoucí revizi, review, Windows i GitHub
Actions stav `NOT_RUN`. Následující část zaznamenává kontroly skutečného
přenosu po #190. Historické zdrojové výsledky platí pro výše uvedené stromy.

## Přenos na skutečný main po #190

Základ přenosu je sloučený [#190](https://github.com/p-rum/kgmaker/pull/190)
na `71ace79093f853c385566dd90c25e0178cec8fca`, strom
`17b6856043015d916616b32b06d50a4fe13f4fe5`. Přenesly se bajtově shodné
`src/kgmaker/runtime_evidence.py`, fixture a test z původního zdrojového
stromu. Přenos používá původní patch se SHA-256
`5da9778e8ef4f0d1a3dc15c4b5026f13074dd50206abe7a28baa0b962b115893`.
Pro tyto tři cesty byly výchozí bloby mezi `f7015b6` a `71ace79` shodné.
Po `git merge --ff-only 71ace79093f853c385566dd90c25e0178cec8fca` a
`git apply --index --whitespace=error` má samotný přenos zdroje strom
`e2747730d5d61ee5ec865abd4684c2f65925811c`, shodný s ověřením v
dočasném Git indexu. Kontroly diffu a totožnosti všech tří blobů prošly.

Kandidát odvozuje graf ze strojového grafu skutečně sloučeného základu s
512 přijatými epizodami. Následující příkazy patří do kořene checkoutu.
Sémantický patch omezuje revizi na dotčený packet. Zachovává dosavadní
koncepty a vazby, bez nových kurátorovaných tvrzení. Opakování capture
kontroluje, že stejný rozsah druhou epizodu nevytvoří.

```bash
base=71ace79093f853c385566dd90c25e0178cec8fca
git diff --cached --check "$base"
PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider \
  --basetemp "$S13_EVIDENCE/planner-tmp" \
  --junitxml "$S13_EVIDENCE/planner.xml" tests/test_completion.py
kgmaker completion plan --jobs 32 --root "$PWD"
kgmaker semantic update --base "$base" --root "$PWD"
# Z připraveného packetu zachovat dotčené existující uzly a vazby.
kgmaker semantic apply --root "$PWD"
kgmaker semantic validate --root "$PWD"
capture=(memory capture --base "$base"
  --validation exact-head-native=unknown --validation standard=unknown
  --validation planner=passed --validation source-diff=passed
  --validation semantic-before-capture=passed)
kgmaker "${capture[@]}" --root "$PWD"
kgmaker "${capture[@]}" --root "$PWD"
kgmaker semantic validate --root "$PWD"
kgmaker scan --root "$PWD"
kgmaker status --root "$PWD"
kgmaker check --root "$PWD"
```

Návrh návodu před předáním doplnil přesný standardní běh, ověřené dva
testové bloby pro reprodukci RED z veřejných revizí a ověření příkazů.
Oproti původnímu integračnímu návrhu se změnila dokumentace. Základ,
fixture, test a produktový zdroj mají stejné původní bloby.

### Výsledky přenosu pro T003-S13-W03 a AC04

Běh 27. listopadu ověřil staged strom
`fc7586dba9be4eab37f1e75bb571d551114b284f`, později commit
`955f613e07ecb4ff4fe1654c6e0180ad6f9d8606` nad základem `71ace79`.

- `git diff --cached --check` měl PASS a raw exit 0. Ověřeny byly také
  tři shodné zdrojové bloby.
- `tests/test_completion.py` mělo 13 PASS, 0 SKIP, 0 FAIL a raw exit 0.
  SHA-256 JUnit `b99c6d6f4b773d9f3a3336e86f0a8bf7bf9bdf02c10283122b57cfaae67a8aed`.
  Příkaz `completion plan --jobs 32` skončil raw exit 0. Zachoval
  všech 135 položek, pořadí 32 položek k práci a požadavek
  `VERIFIED_IN_SCOPE` pro T003-S10-W02 před T003-S10-W03.
- `semantic update` měl raw exit 0 pro devět vlastních cest. Kontrola
  sémantického patche, `semantic apply` a oba příkazy `semantic validate`
  měly raw exit 0. Zachovaly se hodnoty všech 60 kurátorovaných konceptů
  a 222 vazeb.
- První a opakovaný `memory capture` měly raw exit 0. Všech 512 přijatých
  epizod zůstalo bajtově shodných. Přibyla jedna epizoda omezená na devět
  vlastních cest. Při opakování se nezměnil sémantický artefakt ani graf.
- `scan`, `status` a `check` měly každý raw exit 0. Strojový graf
  zachoval všechny tři uzly `Rates.xlsx`. `.kgmaker/GRAPH.mmd` zůstal
  bajtově shodný se základem.

Tyto výsledky platí pro uvedený strom přenosu. Pro následnou revizi s
doplněným záznamem mají přesný nativní běh, úplná standardní sada,
nezávislé review a GitHub Actions při přípravě záznamu stav `NOT_RUN`.

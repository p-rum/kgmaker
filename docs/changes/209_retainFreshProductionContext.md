# Zachování nezávislého produkčního JVM kontextu

27. listopadu 2026. [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
kroky 1–5, W02-AC01 až AC04 a T003-AC10. Kód navazuje na dvojici
produkční obnovy a nezávislé testovací kontroly z
[#189](https://github.com/p-rum/kgmaker/pull/189). Přípravná nativní
reprodukce začala na `0e0c49120281e73ae131777e6f342f39407644e6`.
Zdrojový přenos po #190 používá `71ace79093f853c385566dd90c25e0178cec8fca`
a zdrojový strom `f5e65819c9a6f796a8408bb9a27db68952da3457`.
Základ tohoto dokumentačního přenosu je `d759fa907aa7b17e08bc3c8db42cd3194b42f2dc`.

## Krok 1 — reprodukce (W02-AC01)

Tři moduly mají samostatné source sety v jednom explicitním modelu.
Změna signatury v testovacím modulu označí v čtecím reportu výhradně
doloženého volajícího z dřívějšího kontextu. Suchá inspekce skutečným
Javacem rozřeší nový cíl v jiném testovacím modulu. Původní publikace
přijme nezávislý aktuální testovací kontrolní modul. Při stejně
ověřeném produkčním kontrolním modulu vrátí `STALE` před první výměnou
souboru. Bajty store a revize CAS zůstanou stejné.

Finální regrese nad původním kódem měla **1 FAIL, 0 SKIP**, raw 1,
JUnit SHA-256
`5c610124ed92fbdf769d717f9f969aafdd91536a884426710638a45b7fc10f8b`.
První širší výchozí běh měl 1 FAIL, 1 PASS, 0 SKIP, raw 1, JUnit SHA-256
`3a2ce779b41b3b60e7e53610f85973fa911e5e009010550cc2c36065431a69b7`.
V obou bězích zrcadlový případ selhal před výměnou prvního výstupu.
Oddělená kontrola odmítla už při prvním běhu skutečně změněný
produkční kontext.

## Krok 2 — kompatibilita (W02-AC02)

Používá se stávající raw JVM snapshot a validace původních dokladů.
Formáty vstupů, graph/store v1–v3, report JSON v1 a existující CAS mají
stejné schéma. `kgmaker impact --evidence-only` zůstává čtecí.
Zadání a jeho registr už pokrývají selektivní invalidaci pod W02,
proto nevyžadují novou identitu, revizi ani změnu závislosti.

## Krok 3 — izolovaná publikace (W02-AC01, W02-AC03)

`src/kgmaker/graph_provider.py` doplňuje opačnou možnost zachování
scope. Při obnově a vyřazení dvou testovacích kontextů může zachovat
nezávislou obsahově ověřenou produkční vrstvu. Obnovený a vyřazený
kontext mají stejný scope. Kontrolní kontext má vlastní modul,
výhradní zdroje a důkazy oddělené od vyřazované i původní a nové
vybrané vrstvy. Model source sets a distribuce workeru musejí
souhlasit. Každá classpath se zvlášť omezuje na obsahově ověřené
knihovny společné distribuce. `inspect_jvm` dál ověřuje veškeré
zachované vstupy i uvnitř původního CAS.

U samostatné editace má vyřazený kontext dosavadní obecný důvod
`STALE_INDEX: source/config inputs changed; inspect again`. Konkrétní
dříve doložená cesta a ID kontextu jsou v čtecím reportu. Diagnostika
smazání a kombinované editace se smazáním dál uvádí dotčené cesty.
`tests/test_reverse_dependency_index.py` pracuje se společnou nativní
fixture pro obě historické produkční varianty a novou testovací
variantu. Ověřuje nový cíl, odstranění staré vrstvy a přesnou shodu
zachovaného kontextu. Pozdní LF→CRLF změna kontrolního souboru obnoví
uložené bajty a revizi CAS. Změna produkčního kontrolního kontextu
před publikací vrátí `STALE` a zachová poslední generaci.

## Krok 4 — přesné příkazy a skutečné výsledky (W02-AC01–AC03)

Historické běhy použily čistý archiv vstupu
`0e0c49120281e73ae131777e6f342f39407644e6` se `src`, `pyproject.toml`
a `tests/test_reverse_dependency_index.py`. RED dostal finální testy.
GREEN dostal stejný test i změnu `graph_provider.py`. Pro reprodukci
lze použít obsah těchto dvou souborů z revize se zde popsaným patchem.
`CANDIDATE` určuje tuto Git revizi, `SCRATCH` a `EVIDENCE` jsou
absolutní zapisovatelné adresáře mimo repozitář. `PYTHON` určuje CPython 3.13.18
s pytestem, `JAVA_HOME` Temurin 21.0.6+7 a `KGMAKER_WORKERS_HOME`
adresář připravených workerů. JVM worker `jvm/target/kgmaker-jvm-worker.jar`
má SHA-256 `021584a2c6b14626d8af4a6907aed1837dc7c8ee51da1d9ad56c3326b87e0e3b`.
JDK a pracovní adresář musejí podporovat skutečný místní Javac.

```bash
set -euo pipefail
base=0e0c49120281e73ae131777e6f342f39407644e6
test_file=tests/test_reverse_dependency_index.py
product_file=src/kgmaker/graph_provider.py
for phase in red green; do
  mkdir -p "$SCRATCH/$phase/source" "$SCRATCH/$phase/java-tmp"
  git archive "$base" src pyproject.toml "$test_file" | tar -x -C "$SCRATCH/$phase/source"
  git show "$CANDIDATE:$test_file" > "$SCRATCH/$phase/source/$test_file"
done
git show "$CANDIDATE:$product_file" > "$SCRATCH/green/source/$product_file"
mkdir -p "$EVIDENCE"
printf '%s  %s\n' 021584a2c6b14626d8af4a6907aed1837dc7c8ee51da1d9ad56c3326b87e0e3b \
  "$KGMAKER_WORKERS_HOME/jvm/target/kgmaker-jvm-worker.jar" | sha256sum -c
```

Z archivu se spustily stejné přepínače pytestu a níže uvedené
selektory. Testy mají shodný SHA-256
`33f63048329220dc1ccd33b8ec557852b571ee64480f4c9b2db59d78bdd37505`.
Manifesty před a po každém běhu souhlasily. Mezi RED a GREEN se
ze zaznamenaných vstupů lišil výhradně `graph_provider.py`.

```bash
set -euo pipefail
run_native() (
  phase=$1
  expected=$2
  shift 2
  cd "$SCRATCH/$phase/source" || exit 2
  export JAVA_HOME KGMAKER_WORKERS_HOME
  export PATH="$JAVA_HOME/bin:$PATH" KGMAKER_REQUIRE_WORKERS=1
  export JAVA_TOOL_OPTIONS=-XX:-UsePerfData PYTHONDONTWRITEBYTECODE=1
  export PYTHONPATH="$PWD/src" TMPDIR="$SCRATCH/$phase/java-tmp"
  inputs=(src/kgmaker/{inspection,graph_provider,model,store}.py
          "$test_file" "$KGMAKER_WORKERS_HOME/jvm/target/kgmaker-jvm-worker.jar")
  sha256sum "${inputs[@]}" > "$EVIDENCE/$phase-input-before.sha256"
  if "$PYTHON" -m pytest -q --tb=short -p no:cacheprovider \
    --basetemp "$SCRATCH/$phase/pytest" --junitxml "$EVIDENCE/$phase.xml" \
    "$@" > "$EVIDENCE/$phase.log" 2>&1; then
    raw=0
  else
    raw=$?
  fi
  printf '%s\n' "$raw" > "$EVIDENCE/$phase.exit"
  sha256sum "${inputs[@]}" > "$EVIDENCE/$phase-input-after.sha256"
  cmp "$EVIDENCE/$phase-input-before.sha256" "$EVIDENCE/$phase-input-after.sha256" &&
    test "$raw" = "$expected"
)

mirror="$test_file::test_actual_javac_preserves_fresh_production_control_during_test_peer_retirement"
drift="$test_file::test_actual_javac_rejects_drifting_production_control_during_test_peer_retirement"
production="$test_file::test_actual_javac_preserves_fresh_control_during_production_peer_retirement"
run_native red 1 "$mirror"
"$PYTHON" - "$EVIDENCE/red.xml" <<'CHECK'
import sys
from xml.etree.ElementTree import parse

case, = list(parse(sys.argv[1]).iter("testcase"))
assert case.get("name") == "test_actual_javac_preserves_fresh_production_control_during_test_peer_retirement"
failure = case.find("failure")
assert failure is not None and "replaced == [diagram]" in (failure.text or "")
assert "STALE and [] ==" in (failure.get("message") or "")
assert case.find("error") is None and case.find("skipped") is None
CHECK
run_native green 0 "$mirror" "$drift" "$production"
"$PYTHON" - "$EVIDENCE/green.xml" <<'CHECK'
import sys
from xml.etree.ElementTree import parse

green = list(parse(sys.argv[1]).iter("testcase"))
assert len(green) == 4
assert all(case.find(tag) is None for case in green for tag in ("failure", "error", "skipped"))
CHECK
```

Kontrola JUnit odděluje očekávaný RED od setup chyby a vyžaduje čtyři
nativní výsledky bez přeskočení. Historický kandidát po opravě asertace dosáhl **4 PASS, 0 SKIP, 0 FAIL**,
raw 0, JUnit SHA-256
`45a736f6c87e953498823f5856eac336fadb4f26be13a1dc5bf661fbfbb013a9`.
Prošly obě dosavadní produkční varianty, testovací obnova při zachování
produkční vrstvy i odmítnutí skutečně změněné produkční vrstvy.

Předchozí běh se změněným zdrojem měl 3 FAIL, 1 PASS, 0 SKIP, raw 1,
JUnit SHA-256
`609560178991ab5f49916b96d03fd46b154cafce918657a8ce909d8544dc63a0`.
Stejný příkaz `run_native green` se stejnými výběry nejprve zkoušel
meziverzi společné asertace. Tři pozitivní případy se dostaly k publikaci
a selhaly na nesprávném požadavku na konkrétní cestu v obecném důvodu
samostatné editace. Finální test ověřuje konkrétní cestu a původní
kontext v čtecím reportu a zavedený důvod samostatné editace ve store.

Přenesení zdroje na main po #190 ověřilo
`git apply --check --index "$PATCH"`, `git apply --index "$PATCH"`
a `git diff --cached --check` s návratovým kódem 0. `PATCH` měl SHA-256
`6c304b221661434e2b4ad1f625d4c863db748f54d8a01e008dafa254c14d0bfe`.
Rozdíl vůči tomuto základu obsahoval pouze uvedený produktový soubor a testy.

## Krok 5 — příkazy pro integračního kandidáta (W02-AC01–AC04)

Tento postup patří k přesnému commitu `CANDIDATE`. Nativní a standardní
sada používají dva samostatné archivy. `EVIDENCE` je absolutní
zapisovatelný adresář mimo checkout. `PYTHON_NATIVE` je CPython 3.12.14
s pytestem a xdist, `PYTHON_STANDARD` je CPython 3.13.18 s pytestem.
`JAVA_HOME` odpovídá Temurinu 21.0.6+7. `PINNED_WORKERS` určuje připravené
`workers` s JVM `target` a `target-k2`. `TYPESCRIPT_NODE_MODULES`
určuje připravené Node závislosti TypeScript workeru. Binárky Node a Maven
jsou v `PATH`. `MAVEN_REPO` označuje lokální repozitář Maven pro testy.
`RUNTIME_LAUNCHER_BIN` a `NATIVE_LAUNCHER_BIN` jsou cesty k místním
spouštěčům nástrojů. Standardní běh používá Gradle 8.13 z `GRADLE_BIN`
a uložené závislosti z `GRADLE_USER_HOME`. Gradle používá lokální loopback.

```bash
set -euo pipefail
reverse=tests/test_reverse_dependency_index.py
native_cases=(
  test_actual_javac_preserves_fresh_production_control_during_test_peer_retirement
  test_actual_javac_rejects_drifting_production_control_during_test_peer_retirement
  test_actual_javac_preserves_fresh_control_during_production_peer_retirement
  test_actual_javac_rejects_unqualified_test_control_during_peer_retirement
  test_actual_jvm_isolated_stale_peer_publication_and_guards
  test_actual_jvm_overlapping_stale_peer_still_aborts
  test_actual_jvm_retirement_of_deleted_owned_peer_input
  test_actual_jvm_retirement_after_mixed_owned_peer_changes
  test_actual_jvm_overlapping_deleted_peer_input_still_aborts
  test_actual_jvm_stale_peer_requires_unambiguous_runtime_proof_owner
  test_actual_jvm_stale_peer_checks_cfg_and_typed_proof_references
  test_actual_jvm_uncaptured_eol_drift_during_peer_publication
  test_actual_javac_signature_change_reaches_transitive_callers_without_workers
  test_replayed_schema_and_openapi_citation_invalidate_only_proven_dependents
  test_legacy_and_unproven_name_matches_never_gain_positive_evidence
)
native_targets=()
for case_name in "${native_cases[@]}"; do
  native_targets+=("$reverse::$case_name")
done
native_targets+=(tests/test_graph_provider.py tests/test_completion.py)

worker_manifest() {
  sha256sum -c <<'PINS'
021584a2c6b14626d8af4a6907aed1837dc7c8ee51da1d9ad56c3326b87e0e3b  workers/jvm/target/kgmaker-jvm-worker.jar
e2ab706954b70a5341e0d57bdb0189949f94eee5ae81ce235c38f4da18aea196  workers/jvm/target-k2/kgmaker-jvm-worker.jar
0fba5508ecbe50cd00a45f132a76582fb22a4ec55769fd3d794fd0e026f9fb67  workers/typescript/node_modules/typescript/lib/typescript.js
PINS
}

run_exact() (
  mode=$1
  proof="$EVIDENCE/$mode"
  mkdir -p "$proof"
  mkdir "$proof/source" "$proof/java-tmp"
  git archive "$CANDIDATE" | tar -x -C "$proof/source"
  git ls-tree -rz --name-only "$CANDIDATE" > "$proof/tracked.z"
  git show -s --format='%H %T %P' "$CANDIDATE" > "$proof/revisions.log"
  cd "$proof/source"
  export JAVA_HOME JAVA_TOOL_OPTIONS=-XX:-UsePerfData
  export TMPDIR="$proof/java-tmp" PYTHONPATH="$PWD/src"
  args=(-q -p no:cacheprovider -o tmp_path_retention_policy=failed
        --basetemp "$proof/pytest" --junitxml "$proof/$mode.xml")
  if test "$mode" = native; then
    for target in target target-k2; do
      ln -s "$PINNED_WORKERS/jvm/$target" "workers/jvm/$target"
    done
    ln -s "$TYPESCRIPT_NODE_MODULES" workers/typescript/node_modules
    worker_manifest > "$proof/workers-before.log"
    export PATH="$RUNTIME_LAUNCHER_BIN:$NATIVE_LAUNCHER_BIN:$JAVA_HOME/bin:$PATH"
    export KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1
    export KGMAKER_TEST_MAVEN_REPOSITORY="$MAVEN_REPO"
    export KGMAKER_WORKERS_HOME="$PWD/workers" PYTHONDONTWRITEBYTECODE=1
    java -version > "$proof/java.log" 2>&1
    mvn -v > "$proof/maven.log" 2>&1
    node -v > "$proof/node.log" 2>&1
    python_cmd=(env -u _JAVA_OPTIONS -u JDK_JAVA_OPTIONS -u NODE_OPTIONS
                -u CLASSPATH "$PYTHON_NATIVE")
    args+=(-n 2 "${native_targets[@]}")
  else
    export PATH="$RUNTIME_LAUNCHER_BIN:$GRADLE_BIN:$JAVA_HOME/bin:$PATH"
    export GRADLE_USER_HOME
    unset KGMAKER_REQUIRE_WORKERS KGMAKER_REQUIRE_K2 KGMAKER_WORKERS_HOME
    python_cmd=("$PYTHON_STANDARD")
  fi
  "${python_cmd[@]}" --version > "$proof/python.log"
  xargs -0 sha256sum < "$proof/tracked.z" > "$proof/before.sha256"
  if "${python_cmd[@]}" -m pytest "${args[@]}" > "$proof/$mode.log" 2>&1; then
    raw=0
  else
    raw=$?
  fi
  printf '%s\n' "$raw" > "$proof/$mode.exit"
  xargs -0 sha256sum < "$proof/tracked.z" > "$proof/after.sha256"
  cmp "$proof/before.sha256" "$proof/after.sha256"
  if test "$mode" = native; then
    worker_manifest > "$proof/workers-after.log"
    cmp "$proof/workers-before.log" "$proof/workers-after.log"
  fi
  test "$raw" = 0
)
run_exact native
"$PYTHON_NATIVE" - "$EVIDENCE/native/native.xml" <<'CHECK'
import sys
from xml.etree.ElementTree import parse

cases = list(parse(sys.argv[1]).iter("testcase"))
assert len(cases) == 52
assert all(case.find(tag) is None for case in cases for tag in ("failure", "error", "skipped"))
CHECK
run_exact standard
```

Na přípravném zdrojovém stromu se zatím pouze načetlo uvedených 52
testů bez jejich spuštění. Výsledky přípravného běhu se skutečným Javacem
z předchozího kroku patří k oddělenému předchozímu archivu.

## Krok 5 — dokumentace a zbývající ověření (W02-AC04)

Pro předem zachycené izolované moduly použijte před další inspekcí
`kgmaker impact --evidence-only --format json edited/src/test/java/Api.java`.
Příklad API uvádí konkrétní testovací source set a zachovaný
produkční modul. [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02) ·
[Návod k API](../compiler-inspection.md#obnova-izolovaného-jvm-kontextu) ·
[Čtecí report CLI](../stage-content-cache.md#selektivní-dopad-změn) ·
[Acceptance](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy) ·
[Stavová matice](../production-analysis-progress.md).

Ve chvíli dokumentační přípravy mají testy se skutečnými K1/K2 workery,
úplná standardní sada, kontroly grafu, nezávislé review a hostované CI
tohoto výsledného integračního kandidáta stav `NOT_RUN`.
Dosavadní W02-AC01 a souhrnný W02 zůstávají `PARTIAL`. Selektivní
revize feature, sdílené vrstvy, build manifesty a širší compiler matice
mají samostatné kontrakty. W03 dál
vyžaduje `VERIFIED_IN_SCOPE` pro W02.

## Krok 6 — přenos a skutečné kontroly po #192 (W02-AC01–AC04)

Po skutečném sloučení [#192](https://github.com/p-rum/kgmaker/pull/192)
použil přenos výchozí `main` `d759fa907aa7b17e08bc3c8db42cd3194b42f2dc`
a jeho strom `eda3ab15a0a932eb64f355c50cfcdb92ef167d3f`. Oddělená čistá
větev přijala tento základ příkazem `git merge --ff-only "$BASE"`
s raw 0. Znovu se aplikovala ověřená produktová a testovací záplata
a dokumentace se přenesla proti skutečnému stavu W02 v inventáři.
Změnil se pouze rozsah osmi souborů této opravy. Produkt i testy mají
stejné bajty jako přípravný nativní GREEN. `git apply --check --index`
a `git diff --cached --check "$BASE"` měly raw 0.

Na přijatém strojovém grafu #192 měly `semantic validate` a `check`
raw 0. Upravený plán eviduje u W02 navíc skutečně sloučené #189.
Dalších 134 položek a pořadí všech 32 kandidátů zůstalo shodných.
T036 je `MERGED / PARTIAL`. T038 a T040 jsou připravené, T042 čeká
na oba a S10-W03 dál vyžaduje `VERIFIED_IN_SCOPE` pro W02.
Přípravný plánovač měl **13 PASS, 0 SKIP**, raw 0, JUnit SHA-256
`916a360b3e2058f2c8045e764baac2fbe4dcfa80ada3d750d96ae310c159cafb`.

První lokální pokus o omezenou sémantickou aktualizaci opravil pouze
řádkové lokátory. Validátor ještě před zápisem odmítl neznámá ID
původních deklarací s raw 1. Opravená aktualizace zachovala 60
kurátorovaných konceptů, 222 vazeb a 514 přijatých epizod. Posunula
sedm zdrojových lokátorů a svázala čtyři původní ID funkcí s jejich
novou polohou. Porovnání syntaxe Pythonu potvrdilo stejné deklarace
bez změny jejich těla.

Na přípravném zdrojovém stromu `160abee612c4bcc37b0bd9be58d4b0bb9885f4d1`
měly `semantic update`, `semantic apply`, `semantic validate`,
oba příkazy `memory capture`, `scan`, `status` a `check` raw 0.
První záznam vytvořil epizodu `episode:979411713f72fae4ad03744d1a771e47d16ed38b9b6f40e143da27a7b911350f`.
Opakování vrátilo stejnou epizodu a zachovalo bajty sémantiky
i vstupního grafu. Strojový graf přípravného stromu
`98d6a1b6a1a8aaa0066819108b315892c2eb4006` má SHA-256
`90622c1329f5c562539bfef889f1f41004ccdca4a3517db1ee7b9b36d50cda15`. Zachovaly se všechny tři uzly Rates, importy
a Mermaid diagram. Grafový rozdíl má 163 přidaných, 152 odstraněných
a jeden změněný uzel. Všech 594 dotčených uzlů patří osmi souborům W02.

Přípravný graf a doklady se archivovaly před začleněním tohoto záznamu
do Change209. Finální záznam vzniká znovu z přijatého grafu #192 a zahrne
otisk tohoto textu. Přípravná epizoda zůstává v odděleném dokladu.

### Zopakování kontroly přesného výřezu

`CANDIDATE` je SHA přeneseného commitu W02. `BASE` je uvedené SHA #192,
`PROOF` absolutní zapisovatelný adresář a `KGMAKER` s `PYTHON` místní
binárky stejného prostředí. `BASE_GRAPH` ukazuje na místní kopii
archivu `candidate-graph.json.gz` z přijatého ověření #192.
Při prvním přenosu se použily dříve uložené dvě záplaty. Tento příkaz
odvodí společnou záplatu osmi souborů z přesného kandidáta a základu.

```bash
set -euo pipefail
git diff --binary "$BASE" "$CANDIDATE" -- README.md \
  docs/acceptance-inventory.md docs/changes/209_retainFreshProductionContext.md \
  docs/compiler-inspection.md docs/production-analysis-progress.md docs/stage-content-cache.md \
  src/kgmaker/graph_provider.py tests/test_reverse_dependency_index.py > "$PROOF/w02.patch"
```

Z kořene čisté oddělené pracovní větve s `HEAD` na `BASE` nejprve
ověřte archiv a načtěte přijatý strojový graf. Samostatný replay
`kgmaker scan --no-docs --root "$PWD"` v kopii z `git archive "$BASE"`
skončil s raw 0 a vytvořil jiný strojový otisk
`86e149ec2495009ea9635909f9988b936098831e517bbcae1f930ae446958522`. Přesný záznam epizody používá
ověřený archiv `BASE_GRAPH`.

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1
printf '%s  %s\n' f37945243444fcf08f0b1b9a987e353cdc8f3fd4d79f3d709b296784a9736eaa \
  "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' e82a7db5eedb6666da7dd3e814fe9061547a0a9865a049052fafb2bf511c290d \
  .kgmaker/graph.json | sha256sum -c
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" check --root "$PWD"
git apply --check --index --whitespace=error "$PROOF/w02.patch"
git apply --index --whitespace=error "$PROOF/w02.patch"
git diff --cached --check "$BASE"
"$KGMAKER" completion plan --root "$PWD" --jobs 32
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml="$PROOF/planner.xml"
"$KGMAKER" semantic update --base "$BASE" --root "$PWD"
"$PYTHON" - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

update = json.loads(Path(".kgmaker/semantic-update.json").read_bytes())
assert update["base_commit"] == sys.argv[1]
assert len(update["changed_files"]) == 8
provider = "src/kgmaker/graph_provider.py"
tests = "tests/test_reverse_dependency_index.py"
lines = {
    provider: {752: 753, 759: 760, 919: 920, 930: 931, 935: 936},
    tests: {798: 823, 880: 905},
}
declarations = (
    (provider, "_reverse_dependency_index", 734, 735),
    (provider, "dependency_impact", 917, 918),
    (tests, "test_actual_javac_line_ending_change_rechecks_proven_caller", 708, 733),
    (tests, "test_actual_javac_malformed_capture_digest_is_ignored_in_public_impact", 830, 855),
)
ids = {f"function:{path}:{name}::{old}": f"function:{path}:{name}::{new}"
       for path, name, old, new in declarations}
patch = {"schema_version": 1, "update_id": update["update_id"]}
for section in ("nodes", "edges"):
    patch[section] = update[f"affected_semantic_{section}"]
    for row in patch[section]:
        line = row["source_line"]
        row["source_line"] = lines.get(row["source_file"], {}).get(line, line)
        for endpoint in ("source", "target"):
            if row.get(endpoint) in ids:
                row[endpoint] = ids[row[endpoint]]
Path(".kgmaker/semantic-patch.json").write_text(json.dumps(patch, indent=2, ensure_ascii=False) + "\n")
PATCH
"$KGMAKER" semantic apply --root "$PWD"
"$KGMAKER" semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation exact-head-native=unknown
  --validation standard=unknown --validation planner=passed
  --validation source-diff=passed --validation semantic-before-capture=passed)
"$KGMAKER" "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first-capture.sha256"
"$KGMAKER" "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first-capture.sha256"
"$KGMAKER" semantic validate --root "$PWD"
"$KGMAKER" scan --root "$PWD"
"$KGMAKER" status --root "$PWD"
"$KGMAKER" check --root "$PWD"
```

Při zaznamenání tohoto kroku čekají přesná nativní sada, standardní
sada, nezávislé review a hostované CI finálního commitu.

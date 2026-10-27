# Selected TypeScript config freshness s filesystem discovery

Datum:2026-10-26. Task [T003-S08-W02](../tasks/T003-S08-02-tsconfigPathsExclude.md),
AC01–AC04, nadřazené T003-AC08. Baseline main
`1091330b67a7ff67db329ffbbb2eaba162313b3f`; závislost W01 je skutečně merged PR28.
Worktree `/workspace/tsconfig-freshness`, samostatná větev
`feat/t003-s08-02-tsconfig-paths-exclude`. Note45 byla rezervována orchestrátorem.
Celý T003-S08 a callback/generic rozsah W03 se tímto neprohlašují za dokončené.

## Skutečný problém a failing acceptance

Přímá graph/query/source rekognoskace a skutečný TypeScript5.7.3 prokázaly, že
resolution `extends`/`paths`/`include`/`exclude` už funguje. Imported excluded file
se správně zpracoval. Chyba byla ve freshness: broad Python source_snapshot
zahrnoval nepoužitý tsconfig B i excluded-unused source a staloval selected A.
Současně positive input_files neobsahovaly neúspěšný alias lookup: vytvoření
nové dependency mimo root ponechalo původní partial context falešně fresh.

Před source úpravami byly Python/CJS a tři nové acceptance případy zmrazeny do
`/workspace/scratch/tsconfig-w02-baseline-1091330` (pinned TS knihovna je read-only
symlink). Pod sdíleným `flock /workspace/kgmaker-heavy-tests.lock`:
**3 FAIL**,7.11s. První implementace stejné případy: **3 PASS**,9.49s.
Scratch baseline zabránila tomu, aby čekání na cizí heavy suite kontaminovalo
red důkaz mezitím editovaným kódem. Žádný heavy test neběžel mimo zámek.

## Implementace a kontrakt

Existing TypeScript config parser/Program/TypeChecker se nepřepisují. Bounded
compiler host zachycuje positive files, negative existence, realpaths, directory
membership a root/project lockfiles. `ts.matchFiles` provádí skutečné TS matching;
Python pouze replayuje filesystem evidence. Nový worker3 a versioned
input_discovery1/source_snapshot marker nahrazují broad guard jen pro nový TS
context. Legacy fallback, původní selector sloty, v1/v2/v3 a JVM zůstávají.
Preflight/analysis a prepublish ověřují stejnou captured closure; malformed,
unknown nebo změněná evidence nepublikuje nový graf. Helper je explicitní wheel
resource a součást distribution hash. Private analysis output se nepovažuje za
compiler source. Přesný kontrakt a konzervativní directory omezení:
[TypeScript freshness guide](../typescript-freshness.md).

Příprava toolchainu byla explicitní: pinned TS node_modules a genuine K1/K2
artefakty převzaty z vlastního W01 worktree po porovnání všech JVM/K2 sources;
nejde o implicitní build/install při offline operacích. Managed Node24.19.0,
TypeScript5.7.3, JDK21.0.6+7; PYTHONPATH a worker-home vždy vlastní checkout.

## Průběžná validace

- První rozšířená sada `tests/test_tsconfig_freshness.py`, W01 reference matice
  a provider: **46 PASS**,142.90s, heavy lock. Další adversarial/resource/
  lifecycle případy a finální full validation následují před dokončením.
- Skutečné imported-excluded resolution, A/B izolace přes offline provider,
  include membership, alias selector replacement, šest lockfile formátů,
  mixed preflight/analysis a malformed capture jsou testované cesty.
- Local completion/full suite/semantic evidence se doplní podle skutečných
  výsledků; tento průběžný záznam není potvrzením PR acceptance.

Další locked snapshot/resource/installed-wheel sada: **41 PASS**,183.94s.
Zahrnuje cross-request discovery-only změnu, povolenou nesouvisející změnu během
inspection, legacy fallback, graph loader v1/v2/v3 a hash-bound helper.
Po explicitním package markeru pro chybějící helper: shape/prerequisite negative
sada **15 PASS / 18 DESELECTED**,0.12s, XML `/tmp/tsconfig-w02-shape.xml`.
Final protected focus a full zůstávají před přijetím povinné.

## Frozen source a main integrace před protected focus

Lokální source checkpoint `6b0f17e` byl integrován s main
`ff26a6d74679fc38820c1f2fe711b1db20af2ca1` (Spring imports a service inventory).
Jediný textový konflikt byl CI seznam testů: zachovány všechny TS freshness,
W01, Spring/K2 i Windows mandatory gates. TS CJS/helper, Python snapshot modul
a test bytes byly před/po integraci porovnány a zůstaly shodné. Shared context
převzal main JVM-only Spring rule version a zachoval staré TS selector metadata;
`test_spring_imports_context.py`: **2 PASS**,0.13s.

Před actual testy byly explicitně převzaty matching genuine Spring-aware K1/K2
artefakty a fixture output z parent checkoutu; JVM/K2 sources, builder a oba
pinned lockfiles byly před kopírováním byte porovnány. Během testů se workery
nebuildí ani nepřepisují. Final focus má persistent log/XML
`/tmp/tsconfig-w02-final-focused.log` a `.xml` a je serializován heavy flockem;
čekání na jiný legitimní full run není vykazováno jako PASS.

## Finální source-protected focus a aktuální integrace

Final focused suite: **70 PASS**,193.26s; persistent log
`/tmp/tsconfig-w02-final-focused.log`, JUnit XML stejného stemu. Příkaz pod
heavy flockem spustil `tests/test_tsconfig_freshness.py`,
`tests/test_typescript_project_references.py`, `tests/test_graph_provider.py`,
`tests/test_worker_install.py` a `tests/test_spring_imports_context.py` s vlastním
PYTHONPATH/worker-home, JDK21 a mandatory workers/K2/Spring flags.

Následně integrován actual main `33dc239a6d2eca2f42364a7b314aeb377e4b441a`
(mandatory CI a JVM default/bridge source mapping). TS worker/helper/snapshot/tests
byly SHA256 porovnány proti frozen source a jsou byte-identické. CI konflikt
zachoval union mandatory CI, default-body, W01/W02, Spring/K2 a Windows gates.
Před jediným source-final full během byly explicitně připraveny matching K1/K2
artefakty po byte porovnání JVM/K2 sources, builderu a obou lockfiles; žádný build
neprobíhá během validace ani offline commandu. Full log/XML:
`/tmp/tsconfig-w02-full.log`, `/tmp/tsconfig-w02-full.xml`; výsledek dosud PENDING.

GitHub Actions billing/quota nyní brání novému CI běhu. Uživatel povolil pokračovat
lokálním proof/review a další práci ve stacked větvi; chybějící CI se tím nenahrazuje
a merge acceptance se netvrdí. Žádné opakované CI retry ani bypass nejsou provedeny.

První full pokus byl přerušen po **207 PASS /7 SKIP /50 setup ERROR**,49.68s:
chyběly explicitní Maven/Spring fixture outputs a pinned Kotlin na PATH pro novou
main default-body matici. Nejde o PASS ani runtime regresní závěr. Log/XML byly
zachovány jako `/tmp/tsconfig-w02-prerequisite-interrupted-full.*`. Před novým
během byly fixture sources byte porovnány s vlastními skutečně zbuilděnými
checkouty a jejich output explicitně zkopírován. PATH doplněn o
`/workspace/tools/kotlinc/bin` (Kotlin2.1.10); mandatory flags nebyly zeslabeny.

## Konečný lokální source-final výsledek

**567 PASS /10 SKIP**,787.45s, persistent `/tmp/tsconfig-w02-full.log` a
`/tmp/tsconfig-w02-full.xml`. Kód odpovídá reviewed Draft PR36 head d416e2a nad
main33dc; worker/helper/snapshot/test frozen SHA256 zůstaly shodné. Full byl jediný
dokončený source-final běh po explicitní přípravě všech missing fixtures. Příkaz:

```sh
flock /workspace/kgmaker-heavy-tests.lock env \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_WORKERS_HOME=/workspace/tsconfig-freshness/workers \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q -rs \
  --junitxml=/tmp/tsconfig-w02-full.xml
```

Před tímto final během byl druhý prerequisite-only pokus přerušen:
**1 FAIL /130 PASS /2 SKIP**,128.90s. React fixture neměla pinned @types/react,
proto chyběl handles_event (TypeScript overload proof už PASS). Zachovaný
`/tmp/tsconfig-w02-react-prerequisite-interrupted-full.log/.xml`; frontend package
a lock/source byly byte porovnány a odpovídající genuine node_modules explicitně
zkopírovány. Read-only `/workspace/kgmaker-test-prerequisites.py` poté PASS, bez
instalace či buildu. Žádná runtime oprava nebyla potřebná; full následně prošel.

Deset SKIP je výslovně mimo připravenou lokální matici: Maven/exporter runner1,
druhé skutečné JDK+Maven1, installed Maven/Gradle exporters2, Gradle included/variant
fixtures3, Kotlin build Maven exporter1 a Gradle8.13/Kotlin2.2.20 cache1, actual
non-admin Windows1. Missing toolchain není vykázán jako PASS. Lokální TS/W01/K2 a
Spring worker prerequisite gates zůstaly mandatory a prošly. Windows dříve
merged proof ani samostatné build exporter acceptance se tímto znovu netvrdí.

GitHub Actions billing/quota stále blokuje nové CI. Draft PR36 a nezávislé root
source+actual18PASS19.07s review nejsou náhradou required CI; merge/durable task
DONE zůstávají pending. Celý S08 a callbacks W03 nejsou touto W02 změnou dokončeny.

## Integrace schváleného T009 main (2026-10-27)

Větev byla integrována s main09d351d379b43c697451f93c8735a008204d8d9b po mergePR48. Všechny vlastní worker/runtime/guard zdroje jsou byte-identické schválenému8e839374302da7150ee75987203196e96703fb84; integrace přidává již ověřený view model/evidence a CI jsonschema dependency. Relevantní T005/T009/T006/T008/mandatory-CI sada **87 PASS, 1.19 s**; vlastní skutečná TS freshness sada **33 PASS, 242.84 s**, s REQUIRE_WORKERS=1 bez SKIP. Původní whole567/10 zůstává feature proof; další lokální whole se pro čistou integraci bez změny runtime neopakuje. Aktuální remote CI musí projít nad novým HEAD a base09d351d. Billing blokace byla po uživatelském upgradu odstraněna; žádný bypass kontrol.

Sémantický merge zachovává115 epizod nového main jako přesný immutable prefix a dvě unikátní starší TS epizody beze změny, celkem117 před capture integrace. Osm konceptů/21 vztahů je union obou ověřených větví; aktualizována pouze skutečná posunutá compiler-documentation citace. Generovaný graf obnovuje CLI.

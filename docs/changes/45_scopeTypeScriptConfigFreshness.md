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

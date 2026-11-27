# Dopad změny na závislé vstupy aplikované analýzy

27. listopadu 2026. [T003-S10-W02](../tasks/T003-S10-02-reverseDependencyIndexes.md),
kroky 1–5, W02-AC01 až AC04 a T003-AC10. Přípravný základ
`be63bc34b6f766761c39d5b9e8cde0d2389e3962` obsahuje [#193](https://github.com/p-rum/kgmaker/pull/193).
Opravu po zapracování nálezu k výkonu a regresní testy ověřil pracovní
strom `df2bef6c06a284d8323c09551d26ebe3d3a7a95f`. Od základu se liší
v `feature.py`, `graph_provider.py` a `test_reverse_dependency_index.py`.
Identita integračního kandidáta má vlastní záznam ověření níže.

## Krok 1 — reprodukce (W02-AC01)

Připravená a aplikovaná revize 1 přímo cituje operaci `getBalance` v
`openapi.json` u vstupu `balance`. Vstupy `label` a `style` na něj
odkazují přes `dependency_ids`, `summary` používá oba a `page` používá
`summary`. Vstup `health` cituje samostatný kontrakt. Po změně na
`fetchBalance` vznikne packet revize 2 a dosavadní aplikovaný záznam
zůstane svázaný s původním packetem a receipt revize 1. Čtecí report
na výchozím kódu označil deklaraci `RECHECK` a `balance` jako `STALE`.
Chyběly čtyři navazující vstupy.

Původní veřejný výstup z menší fixture se stejnou vazbou `label` →
`balance` měl návratový kód 0 a SHA-256
`5a3689daf3085b6ad7252e6640f19d5c77b0755ba2f9512bbe9f100fbb905e3a`.
Po opravě přibyl právě `label` se stavem `STALE` a důvodem z revize 1.
Všechny původní řádky a ostatní pole zůstaly shodné. Nový výstup měl
návratový kód 0 a SHA-256
`778b35802814fbf6eaca3d44ce90b6e1c89701bc3bf7bb5688e492808229dc41`.
Manifest souborů store před a po příkazu byl shodný.

## Krok 2 — kompatibilita (W02-AC02)

Formát JSON v1, identita analýzy, packetu, aplikované revize a citace se
zachovávají. Přímé důvody mají dosavadní pole. Důvod přenesený přes závislost
přidává volitelná pole `dependency_id` pro bezprostřední vstup a
`source_conclusion_id` pro vstup s původní citací. `conclusion_id` nadále
označuje dotčený vstup. Změna nevyžaduje migraci grafů v1–v3 ani souborů
aplikované feature. Zadání a registr zachovávají stávající ID a závislosti.

## Krok 3 — čtení doložených závislostí (W02-AC01, W02-AC03)

`src/kgmaker/feature.py` používá původní kontrolu aplikačního potvrzení,
otisku kandidáta a původního packetu. `src/kgmaker/graph_provider.py`
porovná přímé citace s jedním pozorováním bajtového otisku každé zadané
cesty. Teprve po zjištěné změně nebo odstranění vstupu se vyhodnotí
explicitní `dependency_ids` ve stejné lokální aplikované revizi.
Nezměněné bajty nevyvolají průchod závislostmi. Vyhodnocení nepřidává
další čtení změněné cesty. Compiler, Flyway a OpenAPI deklarace používají
dosavadní postup.

Sdílený potomek má jeden záznam v `affected`. Pro stejnou cestu a stejný
původní bajtový otisk zachová nejvýše jeden doložený přenesený důvod na
každého bezprostředního předchůdce. Při pokračování k dalšímu vstupu má
přednost přímá citace předchůdce pro danou dvojici. Jinak rozhoduje
stabilní pořadí ID původních citací a bezprostředních vazeb. Všechny
přímo doložené důvody ve výstupu zůstávají. Každý přenesený důvod uvádí
původní citaci a oba otisky souboru.

Neplatný tvar vazby, duplicitní nebo cizí odkaz či cyklus při zjištěné změně
vynechá přenesené důvody dotčené revize. Report zachová přímé ověřené citace a uvede
`FEATURE_INPUT_DEPENDENCIES_UNAVAILABLE` s ID analýzy a revizí. Při
nesouhlasu kandidáta, receipt nebo packetu se vynechají citace té analýzy
s diagnostikou `FEATURE_REVISION_UNAVAILABLE`. Citace ostatních analýz
mají vlastní ověření. Nečitelný uložený graf dál ukončí celý příkaz s kódem
1 bez výstupu JSON. Regresní testy v `tests/test_reverse_dependency_index.py`
ověřují jeden průchod pro čtení otisku, nulový průchod vazbami při stejných
bajtech, sdílenou hranu s více citacemi, neplatné vazby a poškozený receipt
vedle platné druhé analýzy.

```bash
kgmaker impact --root ./service --evidence-only --format json openapi.json
```

Jde o čtecí výsledek s `coverage: PARTIAL`. Stav `STALE` v reportu určuje
závěr k revalidaci. Obsah grafu, aplikační potvrzení, historie feature, její
schválení a revize CAS se příkazem nemění. Příkaz nespouští workery ani
build. Deklarovaná závislost sama nedokládá dostupnost dat.

## Krok 4 — příkazy a přípravné výsledky (W02-AC01–AC03)

Použitý nástroj byl CPython 3.13.18 s pytestem 8.3.4. Selektory pokrývají
offline fixture. `CANDIDATE` určuje Git commit obsahující tento patch,
`SCRATCH` nový absolutní zapisovatelný adresář mimo checkout, `EVIDENCE`
absolutní adresář výstupů a `PYTHON` cestu k Pythonu s pytestem. Příkazy
spusťte ze zdrojového repozitáře s oběma Git objekty. Základ zůstává stejný
pro oba archivy a testový soubor pochází v obou případech z `CANDIDATE`.
V GREEN se navíc převezmou `feature.py` a `graph_provider.py`. Tím je
funkční RED opakovatelný s veřejným testovým souborem z kandidáta.

```bash
set -euo pipefail
base=be63bc34b6f766761c39d5b9e8cde0d2389e3962
test_file=tests/test_reverse_dependency_index.py
product_files=(src/kgmaker/feature.py src/kgmaker/graph_provider.py)
feature_tests=(tests/test_feature.py tests/test_complete_analysis_report.py tests/test_graph_provider.py)
mkdir -p "$SCRATCH" "$EVIDENCE"
for phase in red green; do
  mkdir "$SCRATCH/$phase"
  git archive "$base" src pyproject.toml "$test_file" "${feature_tests[@]}" \
    | tar -x -C "$SCRATCH/$phase"
  git show "$CANDIDATE:$test_file" > "$SCRATCH/$phase/$test_file"
done
for product_file in "${product_files[@]}"; do
  git show "$CANDIDATE:$product_file" > "$SCRATCH/green/$product_file"
done
cmp "$SCRATCH/red/$test_file" "$SCRATCH/green/$test_file"

run_impact_tests() (
  label=$1
  archive=$2
  expected=$3
  shift 3
  cd "$SCRATCH/$archive"
  export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  export PYTHONPATH="$PWD/src"
  sha256sum "${product_files[@]}" "$test_file" > "$EVIDENCE/$label.before.sha256"
  if "$PYTHON" -m pytest -q -p no:cacheprovider "$@" \
    --junitxml="$EVIDENCE/$label.xml" --basetemp="$EVIDENCE/$label-pytest" \
    > "$EVIDENCE/$label.log" 2>&1; then
    raw=0
  else
    raw=$?
  fi
  printf '%s\n' "$raw" > "$EVIDENCE/$label.exit"
  sha256sum "${product_files[@]}" "$test_file" > "$EVIDENCE/$label.after.sha256"
  cmp "$EVIDENCE/$label.before.sha256" "$EVIDENCE/$label.after.sha256"
  test "$raw" = "$expected"
)

run_impact_tests red red 1 "$test_file" \
  -k 'openapi_impact and not does_not_expand_unchanged_input and not coalesces_input_citations'
run_impact_tests green green 0 "$test_file" \
  -k 'openapi or applied_feature or feature_record or schema_dependency'
run_impact_tests feature green 0 "${feature_tests[@]}"
"$PYTHON" - "$EVIDENCE" <<'CHECK'
from pathlib import Path
import sys
from xml.etree.ElementTree import parse

evidence = Path(sys.argv[1])
for label, count, failed in [('red', 6, 6), ('green', 19, 0), ('feature', 60, 0)]:
    cases = list(parse(evidence / f'{label}.xml').iter('testcase'))
    assert len(cases) == count
    assert sum(case.find('failure') is not None for case in cases) == failed
    assert all(case.find('error') is None and case.find('skipped') is None for case in cases)
    if label == 'red':
        for case in cases:
            expected = ('FEATURE_INPUT_DEPENDENCIES_UNAVAILABLE' if 'malformed' in case.get('name', '')
                        else ':input:label')
            assert expected in (case.find('failure').get('message') or '')
CHECK
```

Funkční RED v čistém archivu základu, RED k výkonu a GREEN používají
tentýž test s otiskem
`4e4a85d067933db75cc6deb9fab805118dc9176a4c20c5c7b5b2823ccae0ba5f`.
Opravený `feature.py` má SHA-256
`fe3c90119dfd94a05c24666ad6f30f35a0c500890a59e87abd6a761818c0bde8`
a `graph_provider.py`
`8a8eb5db3cdb7ea70189d5b80faf820bc444c710a9a043de6216e02e91664278`.
Manifesty před a po se shodovaly. Cílené testy ověřily stejné bajty grafu
i historie, stejnou revizi CAS a žádný subprocess při čtení dopadu.

RED k výkonu použil produktové soubory ze staršího přípravného stromu
`69d4c7a13c8c6ae614aec8e24b44045e7edf0c75` a shodný finální test.
Selektor byl `-k 'does_not_expand_unchanged_input or coalesces_input_citations'`.
První kontrola zachytila průchod závislostmi u nezměněného vstupu, druhá
nadbytečné důvody pro stejnou cestu a stejný původní otisk. Obě příčiny
se v opraveném stromu ověřily jako součást GREEN. Veřejný výstup menšího
příkladu z kroku 1 měl po opravě výkonu shodný SHA-256.

| Běh | Skutečný výsledek | Kód pytestu | SHA-256 JUnit |
|---|---|---:|---|
| Funkční RED se základním kódem | 6 FAIL, 0 SKIP, 63 DESELECTED | 1 | `12c6eb4d61d42f95c6cb7c5085b3411ba8e341aa507a70f10bb31cc4ca2d7761` |
| RED k výkonu před opravou | 2 FAIL, 0 SKIP, 67 DESELECTED | 1 | `45e1d19b2593fc41d6cad5d3a881e30548f9624a8beb43781f33842f7cd8c911` |
| GREEN, OpenAPI, aplikované feature a schéma | 19 PASS, 0 SKIP, 50 DESELECTED | 0 | `a7023768d95ce2e33d288556eabd4c032962568247ad0ae76388e7b7d2766fea` |
| Regrese feature, reportu a graph provideru | 60 PASS, 0 SKIP | 0 | `65b0c1f8364321cf198e8b778143d1292c919e57397abe9ef8b3d55e546d7f4e` |

`git diff --cached --check` prošel. Přípravný pokus o `kgmaker memory
recall` skončil kódem 2 s hlášením `no readable graph found; run kgmaker
scan first`. Ověření recall je v tomto řezu `NOT_RUN`. Nativní a úplná
standardní sada jsou pro tento přípravný strom `NOT_RUN`.

## Krok 5 — dokumentace a integrační ověření (W02-AC04)

Příklady příkazu a formát důvodů jsou v [README](../../README.md#selektivní-dopad-změněných-souborů-t003-s10-w02)
a [popisu CLI](../stage-content-cache.md#selektivní-dopad-změn). Stav pokrytí
je v [akceptačním inventáři](../acceptance-inventory.md#t003-s10-w02--reverse-dependency-indexy)
a [matici dodání](../production-analysis-progress.md). Dokumentace modelu
feature už definuje `dependency_ids` a jeho kontrakt zůstává stejný.

Integrační běh, formální nezávislé review a ověření na `main` jsou pro
tento záznam zatím otevřené. Po integraci patří k důkazu přesné base a head
SHA, strom kandidáta, příkazy, skutečné výsledky a JUnit ze stejného stromu.
Po sloučení se ověří výsledný commit, přenos změny a aktuální stav plánovače.
W02-AC01 zůstává `PARTIAL` a W03 čeká na ověřený selektivní zápis. Obnova
grafu, přepočet aplikované revize a negativní lookupy mají vlastní kroky.

## Krok 6 — přenos na základ po #194 (W02-AC01–AC04)

Přenos má základ `2e393c049aa42bc1c0684f566d345345405a2dcd`, strom
`0ff627009e52960968cdcc7d3526bc227d30d09e` a pořadí rodičů
`be63bc34b6f766761c39d5b9e8cde0d2389e3962`,
`c5360666c391a03ed45d878a1037676a899a9111`.
Přenesly se ověřené bajty tří souborů z kroku 4 a pět dokumentačních cest.
Po přidání této části je v dokumentaci zachycen přípravný běh před změnou
jejího obsahu. Ten měl strom osmi cest
`8f72a5db94ed40cbaf7e3ac1f6f9f34a635797dd`, celý připravený strom
`0d19fff670688b17e87e05505b77bb521a48a904` a epizodu
`episode:fa2f74db3b8596c4f9261c40384ad550b74e49bb7f3937a57e43571337600255`.
Strojový graf přípravného běhu měl SHA-256
`d50c115a392f4a67b8621bf317aa26e639a519445c5243aca9958806e1aa70d2`.

Kontroly `completion plan`, `semantic update`, `semantic apply`,
`semantic validate`, dvě volání `memory capture`, `scan`, `status`,
`check` a kontrola diffu měly v přípravném běhu návratový kód 0.
Paměť nad přijatým grafem bylo možné vyhledat s návratovým kódem 0.
Druhé zachycení našlo tutéž epizodu a zachovalo její bajty. Následný
`scan` potvrdil 160 přidaných, 144 odebraných a 0 změněných uzlů v osmi zdrojových cestách.
Všech 516 přijatých epizod se zachovalo doslova. Projekce epizody #194
ve strojovém grafu změnila pouze `freshness` z `current` na `changed`,
protože obě změny upravují README a oba inventáře. Zůstalo také všech
60 kurátorovaných konceptů a 222 vztahů. Jediná změna kurátorovaného
vztahu přivázala původní volání na nové ID deklarace
`applied_dependency_citations` (`::462` → `::519`). AST původního
volání na řádku 936 a těla ověřujícího kandidáta, receipt, packet
a přímé citace se shodují. Bajty Mermaid i jeho normalizované uzly
a hrany jsou shodné. Tři uzly `Rates.xlsx` a 275
hran s nimi spojených zůstaly shodné.

Přípravný běh plánovače měl **13 PASS, 0 SKIP**, raw 0, JUnit SHA-256
`41391cdcbbeb5d68d7c210cbb18ebe6e5508cc35857cf48f5b7dcdd80bcf6aa7`.
Plán zachoval všech 135 položek a výběr
32 kandidátů ve stejném pořadí. W02 je
`MERGED/PARTIAL` pro dříve dodaný rozsah. W03 má dál bránu
`VERIFIED_IN_SCOPE` a ve výběru chybí. [Issue #116](https://github.com/p-rum/kgmaker/issues/116)
zůstává otevřené pro persistentní ověření cache. Přenos eviduje čtecí
rozsah této změny samostatně.

Po doplnění tohoto kroku se finální epizoda zachytí znovu z přijatého
grafu #194. Použije stejných 516 doslovných epizod a aktuální bajty osmi
souborů. Přípravná epizoda patří výhradně k výše uvedenému výřezu.
Úplná sada, formální review a ověření přesného veřejného headu mají
samostatné výsledky.

### Reprodukce přenosu a grafu

`BASE` je revize #194 uvedená výše a `CANDIDATE` je commit tohoto
přeneseného kandidáta. `PROOF` je absolutní zapisovatelný adresář mimo
checkout, `PYTHON` určuje CPython 3.13.18 s pytestem. Použijte čistou
oddělenou větev s `HEAD` na `BASE`. `BASE_GRAPH` je přijatý archiv grafu
`candidate-graph.json.gz` z ověření #194. Jeho SHA-256 je
`2f03213a58afa06402238e5698aee61e2438cae3cd4a1403af47404caa6d4d07`.
Obsah po rozbalení má SHA-256
`bd83cc889beda73f2929bf313fc97b9b0410ceb8df44a113d751b93067099a7c`.
Čistý replay ze samotných zdrojů `git archive "$BASE"` bez přijatého
archivu zavolal `scan --no-docs` s raw 0 a vytvořil samostatný
otisk `f00d1a21ed39141abc31f573eb46429047de1064bfb73f2281899e84db22a3fa`.
Přesná reprodukce epizody vychází z přijatého archivu.

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "$BASE"
test -z "$(git status --porcelain)"
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
mkdir -p "$PROOF"
git diff --binary --full-index "$BASE" "$CANDIDATE" -- README.md \
  docs/acceptance-inventory.md docs/changes/211_followAppliedInputDependencies.md \
  docs/production-analysis-progress.md docs/stage-content-cache.md \
  src/kgmaker/feature.py src/kgmaker/graph_provider.py tests/test_reverse_dependency_index.py \
  > "$PROOF/w02.patch"
printf '%s  %s\n' 2f03213a58afa06402238e5698aee61e2438cae3cd4a1403af47404caa6d4d07 "$BASE_GRAPH" | sha256sum -c
gzip -dc "$BASE_GRAPH" > .kgmaker/graph.json
printf '%s  %s\n' bd83cc889beda73f2929bf313fc97b9b0410ceb8df44a113d751b93067099a7c .kgmaker/graph.json | sha256sum -c
git apply --check --index --whitespace=error "$PROOF/w02.patch"
git apply --index --whitespace=error "$PROOF/w02.patch"
git diff --cached --check "$BASE"
"$PYTHON" -m kgmaker completion plan --root "$PWD" --jobs 32 > "$PROOF/plan.json"
"$PYTHON" -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py \
  --basetemp "$PROOF/planner-tmp" --junitxml="$PROOF/planner.xml"
"$PYTHON" -m kgmaker semantic update --base "$BASE" --root "$PWD"
"$PYTHON" - "$BASE" <<'PATCH'
import json
from pathlib import Path
import sys

update = json.loads(Path('.kgmaker/semantic-update.json').read_bytes())
assert update['base_commit'] == sys.argv[1]
assert len(update['changed_files']) == 8
old = 'function:src/kgmaker/feature.py:applied_dependency_citations::462'
new = 'function:src/kgmaker/feature.py:applied_dependency_citations::519'
patch = {'schema_version': 1, 'update_id': update['update_id'],
         'nodes': update['affected_semantic_nodes'], 'edges': update['affected_semantic_edges']}
assert (len(patch['nodes']), len(patch['edges'])) == (3, 22)
edge, = (row for row in patch['edges'] if row['target'] == old)
assert (edge['source_file'], edge['source_line']) == ('src/kgmaker/graph_provider.py', 936)
assert not any(row['source'] == old for row in patch['edges'])
edge['target'] = new
Path('.kgmaker/semantic-patch.json').write_text(json.dumps(patch, indent=2, ensure_ascii=False) + '\n')
PATCH
"$PYTHON" -m kgmaker semantic apply --root "$PWD"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
capture=(memory capture --base "$BASE" --validation exact-head-standard=unknown
  --validation planner=passed --validation source-diff=passed --validation semantic-before-capture=passed)
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum .kgmaker/semantic.json .kgmaker/graph.json > "$PROOF/first.sha256"
"$PYTHON" -m kgmaker "${capture[@]}" --root "$PWD"
sha256sum -c "$PROOF/first.sha256"
"$PYTHON" -m kgmaker semantic validate --root "$PWD"
"$PYTHON" -m kgmaker scan --root "$PWD"
"$PYTHON" -m kgmaker status --root "$PWD"
"$PYTHON" -m kgmaker check --root "$PWD"
git diff --exit-code "$BASE" -- .kgmaker/GRAPH.mmd
```

Přípravný výřez lze zopakovat stejným postupem, pokud se po aplikaci
osmi cest odebere tento krok 6 včetně prázdného řádku těsně před jeho
nadpisem a přidá se pouze upravený Change211 do indexu před vytvořením
sémantického packetu. Výsledný strom osmi cest lze porovnat s uvedeným
přípravným otiskem.

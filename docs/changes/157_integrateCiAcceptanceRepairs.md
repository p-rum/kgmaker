# Společné ověření oprav Pythonu, Windows, PR Review a K2

Výchozí `main` je `4011825b15e4b65e1f57576a0986ca05b3cf810e`, Git tree
`d8021d4f2eefe3b1576c75ed66e7f71d642fbd`. Uživatel povolil společnou
integraci oprav, jejichž oddělené větve přebírají selhání ze stejného
výchozího stavu. T052-S02 až S04 a T045-R01 až R04 vážou společné
ověření a review na aktuální base/head.

| Dílčí PR | Přesný head | Převzaté zdrojové soubory | Záznam |
| --- | --- | --- | --- |
| [#138](https://github.com/p-rum/kgmaker/pull/138) | `d977f1823baa85f091a3baa6ca8d3239e148d585` | `src/kgmaker/inspection.py`, `tests/test_orm_xml_overrides.py` | [Change153](153_classifyLoopedJpaXmlInputs.md) |
| [#139](https://github.com/p-rum/kgmaker/pull/139) | `0329c5d2e9ed900be3122f729fc03648f1e0c80a` | `tests/windows/no_admin_smoke.ps1` | [Change155](155_scopeWindowsWorkerSmoke.md) |
| [#140](https://github.com/p-rum/kgmaker/pull/140) | `11c59015675774013fdd8cd9055292a11b045079` | `.github/workflows/pr-review.yml` | [Change154](154_fixPrReviewPythonAndCoverage.md) |
| [#141](https://github.com/p-rum/kgmaker/pull/141) | `7345f02586ce3e7ddbf53f4d5b900d912c48fdd8` | `workers/jvm/fetch_k2.py` | [Change156](156_restorePinnedK2Download.md) |

Pět uvedených souborů a všechny čtyři záznamy změn jsou převzaty po
bajtech. Každý záznam zachovává stav a důkazy k datu svého vzniku.

## T003-S06-W03 kroky 1–5, AC01–AC04 a T003-AC06

Python 3.13 při nestriktním rozlišení symlinků klasifikoval cyklus jako
`missing`. Capture nyní označí cyklus jako `invalid` a chybějící cíl uvnitř
projektu jako `missing`. Stávající snapshot a formát graph/store v3
umožňují čtení starších kontextů. Porovnání opraví jejich stav při změně
klasifikace na `STALE`. Ověření zahrnuje test XML snapshotu i celou
`tests/test_graph_provider.py` s reálnými Javac/K1/K2 vstupy. Dílčí běhy
mají 46 PASS / 0 SKIP na Pythonu 3.12.14 i 3.13.5 a hostovaný Python 3.13
na `d977f18` má 2 421 PASS / 1 279 SKIP. Podrobnosti a příklad
`kgmaker inspect code --root ./service --scope production --format json`
uvádí příručka compiler inspection. [Příručka](../compiler-inspection.md#klasifikace-vstupů-orm-xml),
[hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44930359814/job/136925433122).

## T003-S11-W03 kroky 4–5, AC01 a AC04

Windows smoke připravuje core, Java, K1 Kotlin a TypeScript pod omezeným
tokenem. Výběr vyřazuje přesným `--deselect` jediný K2 wheel test, jehož
preflight dříve selhal na nepřipravené distribuci. Skutečný Windows běh
na `0329c5d` potvrdil administrátorské členství `False` a 44 PASS / 1 SKIP /
1 DESELECTED. Linux job `compiler-workers` spouští povinný test K2 se svou
distribucí. Ověření Windows K2 a Windows `BUILD_EXECUTE` mají samostatný
rozsah. [Windows příručka](../windows-install.md),
[hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44930369173/job/136925458350).

## T045-S03, AC02 a AC04

PR Review používá `pytest-cov`, předává stav testovacího kroku a čte
neměnná Git data z přesné dvojice event base/head. Report rozlišuje
naměřených 0 % od chybějícího měření. Po hostovaném nálezu při sběru
instaluje `jsonschema==4.23.0`, stejnou verzi jako workflow Test.
Skutečný běh na `11c5901` má 2 371 PASS, 1 280 SKIP, 84 úspěšných
subtestů a report 74 % pokrytí. Devět lokálních kontrol pokrývá syntaxi,
formátování stavu a pokrytí, Git event data a propagaci návratového kódu.
Nezávislé T045 review má vlastní evidence a verdikt.
[README](../../README.md#development),
[hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44932000190/job/136930443327).

## T003-S04-W01 AC03–AC04 a T003-AC04

Explicitní `python workers/jvm/fetch_k2.py --output "$K2"` získá sedm
JARů 2.1.10 z JetBrains Packages a Caffeine 2.9.3 z Maven Central. Používá
dosavadní připnuté SHA-256, kontrolu velikosti před publikací a atomic
replace. Lokální K1/K2 build a dvě striktní testovací sady mají 51 PASS /
0 SKIP. Hostovaný `compiler-workers` na `7345f02` připravil osm artefaktů,
sestavil K2, vykázal 1 441 PASS / 1 SKIP a dokončil explicitní Maven
plan/runner/export. Odběr jiných compiler verzí má samostatné ověření.
[Příkazy](../compiler-inspection.md#t003-s04-w01--explicitní-k2-analysis-api),
[hostovaný job](https://github.com/p-rum/kgmaker/actions/runs/44934058014/job/136936734963).

## Společný kandidát, T052-AC02 až AC04 a T045-AC03

`git diff --cached --check` a shoda blobů ověřují zdroj a doklady čtyř
větví. Stavová matice a acceptance inventář uchovávají rozsah jednotlivých
výsledků. Registr zadání a instalované instrukce mají stejný kontrakt.
[Stavová matice](../production-analysis-progress.md),
[acceptance inventář](../acceptance-inventory.md).

Před integrací měla samostatná lokální kompozice pět stejných zdrojových
souborů. Celý výchozí výběr `python -m pytest -p no:cacheprovider -q
--tb=short` na Pythonu 3.13.18 měl 2 420 PASS / 1 280 SKIP a shodný
manifest sledovaných souborů před a po testu. Toto ověření platí pro
lokální kompozici.

Nezávislá předběžná kontrola sestaveného zdroje `269642193643d2c0a190bf8d74c652f2281e1224`
ověřila osm SHA-256 připnutých vstupů z čistého K2 stažení, skutečný K2
build, devět kontrol PR Review a syntaxi PowerShellu. Pět souborů mělo
shodnou SHA-256 před a po běhu. Skutečné workery K1, K2 a TypeScript s JDK
21.0.6 daly **106 PASS / 0 SKIP / 0 FAIL** za 115,63 s. JUnit SHA-256 je
`259f6d547d54325edc3af68c4af3e5dec1533ff689437d8fdbcf8f5c31035926`.

```bash
JAVA_TOOL_OPTIONS=-XX:-UsePerfData KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 \
  PYTHONPATH=src python -m pytest -n 3 --dist loadfile -p no:cacheprovider \
  -q --tb=short -ra tests/test_orm_xml_overrides.py tests/test_k2_backend.py \
  tests/test_mandatory_worker_ci.py tests/test_worker_install.py tests/test_worker_protocol.py
```

Výsledky finálního kandidáta, nezávislá rozhodnutí a nový hostovaný běh patří
k předání společného PR. Skutečný Windows restricted-user běh je samostatná
platformní kontrola.

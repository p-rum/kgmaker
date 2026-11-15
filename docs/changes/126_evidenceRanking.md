# Vysvětlitelný ranking nad doloženými hranami

Task **T003-S07-W08**, nadřazený krok **T003-S07**, acceptance
**T003-S07-W08-AC01 až AC04**, cílový kontrakt:
[zadání](../tasks/T003-S07-08-evidenceRanking.md). Tento PR nedokončuje celé S07,
W09 ani S09-W05. Dodání PR_OPEN ([PR106](https://github.com/p-rum/kgmaker/pull/106)), ověření VERIFIED_IN_SCOPE.

## Krok 1 — rekognoskace a failing acceptance

T003-S07-W08, implementační krok 1, AC01/AC03. Výchozí SHA
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf`. Přečteny projektové instrukce,
registr, stavová matice, profil a skill kgmaker-context. Zdrojová kontrola
`views.rank`, `callgraph.adjacency`, `analysis_report` a `project_cli` doložila
chybějící penalty, chybějící incoming witnesses a chybný runtime
`dispatch_complete=True`. Existující graph Markdown posloužil jen k navigaci.

Nový checkout neměl `.kgmaker/graph.json`: `kgmaker status`, `query` a
`memory recall 'execution ranking'` nevrátily čitelný index. Pre-task memory je
**NOT_RUN / missing index**, nikoli zpětně vytvořená historická evidence.
Architektonická kontrola proběhla přímo ve zdroji; rodič ji zkontroloval.
Workflow task `task:0270348a1fc7a13a28caefe36005ce8f8f1c9bac16d096c379c6a467a28ac235`
vznikl před kódem; jeho audit/plan artefakty byly zapsány retrospektivně a tuto
okolnost výslovně uvádějí. Nejde o předstíranou předchozí graph paměť.

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_evidence_ranking.py`
na původním rankeru: **FAIL očekávaný RED, 10 failed / 1 passed, 0.13 s**.
Testy pokryly konkrétní nový kontrakt a chybějící veřejný Markdown report.
Kompatibilita/omezení: bez změny runtime/worker schémat, žádné application buildy.

## Krok 2 — ranking a veřejný report

T003-S07-W08, implementační kroky 2–4, AC01/AC02/AC03. Výchozí SHA
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf`.
Dotčené soubory: `src/kgmaker/views.py`, `callgraph.py`, `analysis_report.py`,
`project_cli.py`, `tests/test_evidence_ranking.py`, `tests/test_production_scope.py`,
`fixtures/evidence-ranking/`.

`execution-2`/`impact-2` zachovávají stávající klíče JSON a doplňují contributions,
path, lokalizované coverage/gaps a aplikovanou penalty. Každý nenulový term má
konkrétní edge/site/context/evidence nebo vstupní entry. Příchozí i odchozí hrany
jsou dohledatelné, stejné proof tuples nepřidávají váhu opakovaným ingestem ani
změnou confidence. TYPE/config/legacy name-match relations nezvyšují execution;
test→production hrana ho nezvýší ani v all scope. Side-effect váha respektuje
existující source-owned hranu; nevymýšlí dokončení operace.

Score je součet breakdown a má nulu jako spodní mez. Penalty mají pevný
zdokumentovaný vzorec; identické site gaps se deduplikují, různé důvody zůstávají.
Neúplný dispatch, unresolved/ambiguous call, stale/unknown context, chybějící
coverage a relevantní provider diagnostiky mají konkrétní důvod a provenance.
Runtime observation neuzavírá static dispatch, nezávislá current static
completeness zůstává. `callgraph.adjacency` proto u samotného runtime záznamu
vrací false a `RUNTIME_SAMPLE_NOT_STATIC_DISPATCH`.

Veřejná integrace: default JSON i nový `graph rank --format markdown` používají
stejný payload. `--explain` je zachováno; vysvětlení je vždy součástí obou formátů.
`--strict` odmítá PARTIAL i UNKNOWN s exit4. Feature report `render_report`
se nemění; nový renderer je veřejný přes existující rank command.

Kompatibilita: graph/store v1/v2/v3 a worker protocol v1 beze změny, bez migrace.
Nové verze profilu výslovně signalizují změnu metriky. Neplatná stará ručně
sestavená v2 fixture v `test_production_scope` dostala povinné skutečné
context/evidence reference; její původní assertions zůstaly. Neplatné reference
jsou odmítnuty před scope filtrem, read-only operace nemění graph/store ani při
chybě/timeout výjimce. Konkrétní command/result souhrn je níže.

## Krok 3 — skutečný Javac a oprava provenance projekce

T003-S07-W08, implementační kroky 3–4, AC01/AC02/AC03. Výchozí SHA
`ec05a329fe2e51dbfe0eb47888bed037a251b8bf`; začleněný finální main
`93c52d338ea273175b9c0ed5a7a5477ae6bf2de0` (PR105, fast-forward).
Dotčené soubory: `views.py`, `tests/test_evidence_ranking.py`,
`tests/test_graph_provider.py` a fixture.

Skutečný worker/Javac21 odhalil dvě chyby: stejný incomplete-dispatch gap byl
započten přes target i path, a `indexed → project(context_id) → rank` ztrácel
SOURCE_ONLY context records, které potřebovaly ponechané structural edges.
První native běh **FAIL 1 / 16 PASS**, následná veřejná CLI kontrola **FAIL 1 /
16 PASS**. Oprava site deduplikace a zachování skutečně referencovaných contexts
vedla k validnímu projected roundtrip. Změna není výběr další compiler varianty.
Feature `graph_selection` beze změny; `analysis_contexts` nově pravdivě obsahuje
vybraný compiler context a potřebnou SOURCE_ONLY provenance. Její starý exact
assertion byl rozšířen o roundtrip a izolaci; nepřejmenovávají se runtime IDs.
První integrační běh tohoto assertion byl **FAIL 1 / 38 PASS**, opraveno.

Fixture používá skutečné Java enum method/type refs, production/test soubory,
configuration a method-reference construction, interface dispatch a úmyslně
chybějící `MissingClient`. Po jedné explicitní inspection oba CLI formáty běží
s blokovaným `subprocess.run`, stejné bytes graph store zůstanou zachované.
Framework side effects a runtime/ambiguous scénáře jsou validované modelové
fixture, nikoli dodatečná tvrzení o podpoře extraktorů nebo runtime PASS.

## Krok 4 — dokumentace, semantic a předání

T003-S07-W08, implementační krok 5, AC04. Výchozí SHA
`93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`.
Aktualizované plochy: README, [capability/CLI](../evidence-ranking.md),
[production scope](../production-scope.md), [architecture](../architecture.md),
[stavová matice](../production-analysis-progress.md),
[acceptance inventář](../acceptance-inventory.md), fixture README a tento záznam.
Registr zadání **bez dopadu**: nemění se ID, revize, závislosti ani odkazy zadání.
Instalované host instrukce a Python templates **bez dopadu**: rank nemění init
nebo instrukční kontrakt. Feature API/availability **bez dopadu**: nový ranking
není důkaz pozitivní dostupnosti a nezasahuje do feature candidate schématu.

Semantic maintenance zachová všech 45 konceptů, 144 vztahů a 299 epizod main93c.
Reanchor se provádí pouze pro ověřené původní source hashes a stejné citation
lines; nové vazby odkazují na aktuální rank/report/test zdroj. Generované grafy
vznikají příkazem, nikoli ručním editem. Reanchor zachoval původní identitu
a význam. Nový koncept + 3 source-backed vazby; po memory capture celkem
46 konceptů / 147 vztahů / 300 epizod. Původních 45/144/299 beze ztrát.

## Provedené kontroly

Příkazy byly spuštěny v `/tmp/kgmaker-evidence-ranking`. Native prostředí:
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`, jeho `bin` první v `PATH`,
`KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers`,
`KGMAKER_REQUIRE_WORKERS=1`, `PYTHONPATH=src`.
Worker vrací compiler `javac-21.0.13.0.3/kotlin-2.1.10-k1`; ranking fixture je
Java, nikoli nová K1/K2 acceptance. Existence toolchainu se nepočítá jako PASS.

- `/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_evidence_ranking.py tests/test_production_scope.py tests/test_graph_provider.py tests/test_build_aware.py tests/test_inspection_contract.py tests/test_feature.py`:
  finální integrační běh po main93c a duplicate/confidence testu
  **PASS 72 / 0 SKIP, 3.02 s**. Předchozí checkpoint **PASS 71 / 0 SKIP, 3.18 s**.
- Dřívější stejná sada před posledními scope/variant testy **PASS 69 / 0 SKIP,
  3.20 s**; historický checkpoint, nikoli náhrada finální kontroly.
- Full suite `python3 -m pytest -q`: **NOT_RUN**, výslovný uživatelský pokyn
  targeted-only až do dokončení celého balíku.
- GH CI: **NOT_RUN**, lokální testy se nevydávají za GH CI PASS.
- K1/K2/TS specializovaná native ranking matice: **NOT_RUN**, nebyla změněna
  compiler implementace/protocol a tento PR ji neclaimuje.
- Java application, Maven/Gradle build, DB, migrace, package install: **NOT_RUN**;
  úkol je offline ranking s explicitním compiler fixture testem.

- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic update --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`, source-reviewed patch, `semantic apply`, `semantic validate`: **PASS**. První scan ještě hlásil stale citations, po reanchor finální validate/scan bez tohoto varování.
- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory capture --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0 --validation targeted-72=passed --validation full=skipped`: **PASS**, episode `f1863cabb184382a4fca82b54366f9655b94b4da1e1d32930d6e75c56f6a8463`.
- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker scan` a `kgmaker check`: **PASS**, generated docs odpovídají aktuálním zdrojům.
- `python3 /tmp/ranking-preservation.py`: **PASS**, všechny 45/144/299 původní koncepty/vztahy/epizody main93c zachované; pouze source-range/ID reanchor.
- `git diff --check`: **PASS**.

## Příklad a zbývající práce

`kgmaker graph rank --profile execution --entry "$SYMBOL_ID" --format markdown`
zobrazí u enum metody konkrétní declared path a incomplete-dispatch důvod,
u enum typu nulový execution term. `--profile impact` odděleně uvede typové
reference. Skóre nic nemění na UNKNOWN runtime dostupnosti.

Zbývá nezávislé review/případné opravy, širší unified flow/report práce v jejich
samostatných zadáních a pozdější celobalíková acceptance. Celé S07 není hotové.


## Krok 5 — publikace a synchronizace stavu

T003-S07-W08, implementační krok 5 / dokumentační předání, AC04.
Výchozí implementační HEAD `61481bdb9c9252fd057fcc6dff4275d9381f125c`,
base main `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`.
Publikován samostatný ready PR106; tento krok opravuje stav na PR_OPEN a doplňuje
URL v tomto záznamu, production matrix a acceptance inventory. README/capability/
CLI **bez dalšího dopadu**: tento krok nemění příkaz ani algoritmus dodaný krokem2.

Workflow test-artifact poprvé odmítl delší než 200znakový command field; žádný
artefakt nevznikl. Stejných šest souborů bylo poté spuštěno s kratším skutečným
Bash brace-expansion příkazem ve výše uvedeném native prostředí:
`/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_{evidence_ranking,production_scope,graph_provider,build_aware,inspection_contract,feature}.py`:
**PASS 72 / 0 SKIP, 2.97 s**. Validovaný test-artifact byl uložen a workflow
přešlo do review; nezávislé review není nahrazeno vlastním schválením.

Kontroly tohoto docs-only kroku: `kgmaker semantic validate`, `kgmaker scan`,
`kgmaker check`, `python3 /tmp/ranking-preservation.py` a `git diff --check`
**PASS**. Opakování pytest po samotné změně stavu/URL **NOT_RUN — bez změny kódu**.
Nadále zbývá nezávislé review; implementační agent PR nemergoval.


## Krok 6 — review P1: freshness konkrétních proof records

T003-S07-W08, oprava implementačních kroků2–4, nadřazený T003-S07,
AC01/AC02/AC03/AC04. Výchozí reviewed SHA
`e0bfd41b13fe0190e5608f88964a0eef36f274de`, integrační base93c beze změny.
[Nezávislý REQUEST_CHANGES](https://github.com/p-rum/kgmaker/pull/106#issuecomment-6898922692)
doložil, že current context překryl explicitní STALE v graph.evidence: entry
mělo score16 a COMPLETE bez gaps. Formální GitHub self-review bylo serverem
odmítnuto422, reviewer vložil transparentní technický REQUEST_CHANGES comment.

Změny: `views.rank` indexuje proof records a posuzuje jejich vlastní freshness,
včetně refs celého call site. STALE proof nemá execution/impact/side-effect ani
path příspěvek. `STALE_EVIDENCE` uvádí přesný proof ID; explicitní unknown stav
vytváří `EVIDENCE_FRESHNESS_UNKNOWN` a nemůže doložit completeness. Stejné proof
mezery se deduplikují, jiné příčiny zůstávají samostatné. Vstup/store zůstávají
beze změny. Testy jsou v `tests/test_evidence_ranking.py`; actual Javac test nyní
ověřuje i veřejný CLI read-only průchod nad stale proof records při validním
compiler contextu.

Kompatibilita: legacy v2/v3 evidence bez pole freshness používá původní
context-bound interpretaci. Explicitní freshness má přednost. Graph/worker
schema, profile IDs execution-2/impact-2 a CLI parametry se nemění. Pole gaps se
rozšířilo o dva popsané důvody, confidence se nepovyšuje. README, capability,
production matrix a acceptance inventory aktualizovány; production-scope a
architecture **bez dalšího dopadu** — už odkazují na aktualizovaný kontrakt.
Registr/host templates **bez dopadu** — žádná změna identity nebo init instrukcí.

## Krok 7 — review P1: statická completeness pouze z přijaté call path

T003-S07-W08, oprava implementačních kroků2–4, nadřazený T003-S07,
AC01/AC02/AC03/AC04. Stejný výchozí reviewed SHA `e0bfd41b13fe0190e5608f88964a0eef36f274de`.
Původní `complete_pairs` četlo samotné metadata METHOD_REFERENCE a tím potlačilo
RUNTIME_SAMPLE_ONLY, ačkoli scoring samotnou referenci správně nepovažoval za call.

Změny: sdílené `views.is_execution_callsite` používají `callgraph.adjacency`,
rank traversal a completeness. Známé executable kindy a legacy omitted kind
zůstávají podporované; explicitní neznámé kindy, METHOD_REFERENCE a INVOKEDYNAMIC
se nepovažují za execution. Complete pair vyžaduje aktuální kontext/proofs a
již přijaté statické caller→site→target hrany. Samotná metadata, unresolved site,
stale/unknown proof, chybějící hrana ani scope/config hranice nestačí. Skutečná
nezávislá current static completeness se zachovává. Runtime-only a proof-freshness
mezery se přenesou do potomků právě té path, která příslušnou hranu používá;
nezahrnují nesouvisející cesty. Tento navazující source nález byl také opraven a
má vlastní regresní test.

Dotčené soubory: `src/kgmaker/views.py`, `src/kgmaker/callgraph.py`,
`tests/test_evidence_ranking.py`, README, evidence-ranking capability,
production matrix, acceptance inventory, tento záznam a generovaná semantic/graph
maintenance. Kompatibilita: graph/worker schemata a výstupní keys zachované;
explicitní unsupported invocation se nyní konzervativně nepromuje.
Žádná změna sousedních BEFE/T028 modulů ani spouštění projektu.

### Kontroly obou review oprav

Native prostředí shodné s krokem2 (`JAVA_HOME` JDK21, `KGMAKER_WORKERS_HOME`
prepared distribution, `KGMAKER_REQUIRE_WORKERS=1`, `PYTHONPATH=src`).

- `PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 /tmp/kgmaker-test-venv/bin/python -B -m pytest -q -p no:cacheprovider --tb=line /tmp/pr106_review_repros.py`:
  před opravou **FAIL 2 / 0.09 s**, po opravě **PASS 2 / 0.08 s**.
- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_evidence_ranking.py -k 'stale_proof_records or non_execution_site or only_admitted'`:
  před opravou **FAIL13,20deselected / 0.20s**, po opravě **PASS13,20deselected / 0.08s**.
- `/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_{evidence_ranking,production_scope,graph_provider,build_aware,inspection_contract,feature}.py`:
  po obou opravách včetně navazující path regrese **PASS86 / 0SKIP, 3.21s**.
  Skutečný Javac/JDK21 a public CLI stale proofs jsou součástí tohoto běhu.
- Full suite/GH CI **NOT_RUN**, targeted-only pokyn zůstává. K1/K2/TS nové native
  acceptance **NOT_RUN**; nebyl změněn worker/protocol ani rozšířena compiler matice.
- `kgmaker semantic update --base e0bfd41b13fe0190e5608f88964a0eef36f274de`, reviewed source reanchor patch, `semantic apply`, `semantic validate`, `scan`, `check`: **PASS**.
- `python3 /tmp/ranking-review-preservation.py` a `python3 /tmp/ranking-preservation.py`: **PASS**; zachovány všechny koncepty/vztahy/epizody reviewed e0 (46/147/300) i main93c (45/144/299), nyní46/149/302.
- `git diff --check`: **PASS**.

Zbývá nové nezávislé review nového HEAD. Předchozí review není přejmenováno na
APPROVE a implementační agent nemerguje.


## Krok 8 — zachování dříve podporovaných invocation kindů

T003-S07-W08, navazující source review opravy kroku7, AC01/AC02/AC03/AC04,
výchozí publikovaný SHA `e0bfd41b13fe0190e5608f88964a0eef36f274de`.
Při kontrole všech producentů v `workers/jvm` a `workers/typescript` bylo zjištěno,
že K1 produkuje také OPERATOR a ACCESSOR. Sdílený eligibility helper zachovává
oba spolu s ostatními existujícími kindy; explicitní unsupported druhy jsou
nadále konzervativně vyloučené. Žádný worker nebyl upraven.
`test_supported_compiler_invocation_kinds_retain_static_evidence` ověřuje všech
9 emitovaných kindů a legacy omitted kind v ranking i callgraph. Jde o modelový
compatibility test, nikoli nové tvrzení o nativní Kotlin/TS acceptance.
Dotčeno `views.py`, `tests/test_evidence_ranking.py` a capability text; ostatní
veřejné příkazy/schema **bez dalšího dopadu**. Důkaz producentů: K1
`KotlinFrontend.kt` uvádí OPERATOR/ACCESSOR, K2 CALL/CONSTRUCTOR, Java a bytecode
STATIC/VIRTUAL/INTERFACE/SPECIAL/CONSTRUCTOR, TypeScript CALL/CONSTRUCTOR.

Stejný přesný šestisouborový příkaz z kroku7 s JDK21 prostředím:
**PASS96 / 0SKIP, 3.20s**. Nezávislé `/tmp/pr106_review_repros.py` opět
**PASS2 / 0.08s**. Checkpoint86PASS3.21s je historický před touto dodatečnou
compatibility regresí. Full/GH CI a další native matice NOT_RUN jako výše.

Semantic po opravách: scoped update nad reviewed e0bfd, ověřené unchanged
source citations reanchor, dva nové source-backed test vztahy, bez odstranění
historie; finální validate/scan/check/diff a preservation jsou součástí publikace.


Finální maintenance kroků6–8: **PASS** semantic apply/validate/scan/check,
`git diff --check` a preservation vůči main93c i reviewed e0. Nově2 test vazby,
2 implementační epizody (první zaznamenává checkpoint86, druhá finální96).
`kgmaker memory capture --base e0bfd41b13fe0190e5608f88964a0eef36f274de --validation targeted-96=passed --validation review-repros-2=passed --validation full=skipped`
zapsal episode `1fa8e1391c8bb7fcc0b155dc143e7067708d49cecde955e65de4037f918580e7`.
Celkem46 konceptů /149 vztahů /302 epizod; obě předchozí historie zachované.
Po doplnění výsledků do dokumentace pytest znovu **NOT_RUN — bez další změny kódu**.

# Vysvětlitelný ranking nad doloženými hranami

Task **T003-S07-W08**, nadřazený krok **T003-S07**, acceptance
**T003-S07-W08-AC01 až AC04**, cílový kontrakt:
[zadání](../tasks/T003-S07-08-evidenceRanking.md). Tento PR nedokončuje celé S07,
W09 ani S09-W05. Dodání IN_PROGRESS, ověření VERIFIED_IN_SCOPE.

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

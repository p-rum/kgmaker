# 131 — Úplný analytický report v doloženém rozsahu

Task `T003-S09-W05`, nadřazené `T003-S09` / `T003-AC09`, průřezové `T003-R01–R10`.
Výchozí SHA `cceb1109df6d88e4f46107f9f9ad12f5e563c0d3`, datum 2026-11-15.
Dodání PR_OPEN ([PR112](https://github.com/p-rum/kgmaker/pull/112)); ověření VERIFIED_IN_SCOPE; report zůstává PARTIAL v popsaných hranicích. Specifikace je cílový kontrakt.

## Krok 1 — rekognoskace před implementací (Step 1, AC01–04)

Přečteny AGENTS, copilot, registry/profil/zadání, aktuální kgmaker-context a
kgmaker-semantic. Ověřena ancestry W09 (`999e60f`, merge `cceb1109`), BEFE
(`61f1d6c`, merge `7bb8b8d`) a všech čtyř S09 předchůdců. Source audit:
`analysis_report.py`, `analysis_validation.py`, `feature_cli.py`, `feature.py`,
`availability.py`, `templates.py`, `workbooks.py` a jejich veřejné fixture testy.
XLSX je `xlsx-offline-3`, binární XLS `xls-unsupported-1`, template
`thymeleaf-bindings-2`; změny 39/55/9 zůstávají skutečnými hranicemi podpory.

Fresh checkout původně neměl machine index: status/query/recall NOT_AVAILABLE.
Po ověření absence compiler indexu proběhl výslovně autorizovaný pre-change
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker scan`: PASS,
609 files / 7028 nodes / 48034 relationships. Následné query/recall PASS;
nejde o zpětně vytvořenou historickou memory. `workflow list`, `workflow check`
PASS; task `5341a2362882659c71d0b0a46f49d28427b7587bb89220c81f113c3ec454897c`
má pravdivý architect analysis/plan. První task help bez PYTHONPATH FAIL
(`No module named kgmaker`), správný příkaz s PYTHONPATH PASS.

Failing acceptance před kódem: report nezobrazuje nezávislé acquisition/usability
ani šest překrývajících se dimenzí, chybí návaznost požadavek → vstup/rozhodnutí/
změna/acceptance/test a explicitní typ otázky. Statická deklarace nesmí být
AVAILABLE; NOT_FOUND_IN_SCOPE není CONFIRMED_MISSING. BEFE compiler tok a
SOURCE_ONLY template/PDF větev se nesmí spojit odhadem.

Kompatibilita: FeatureAnalysis envelope v1 a graph/store v1/v2/v3 se nemění;
nová report projection bude aditivní a otázka bez typu UNCLASSIFIED.
Plánované cílené kontroly: report/feature/data-check/availability, skutečný
Javac21 + TS5.7.3/React fixture, template/workbook/methodology, atomický late abort.
Full suite NOT_RUN na výslovný pokyn uživatele. Zdrojové resolvery/workery mimo scope.

## Krok 2 — projekce a aditivní otázky (Step 2–3, AC01–03)

Baseline `cceb1109`. `report_projection.py` je čistý pohled nad stávajícími
FeatureAnalysis IDs, nikoli druhý katalog nebo schema store. `analysis_report.py`
promítá překrývající se Required/Existing/Missing/Derived/External/Unresolved,
původ/usability/scope, explicitní delivery/acceptance/test vazby a trace gaps.
`analysis_validation.py` přijímá pouze optional `blocker_kind` BUSINESS/TOOL/
UNCLASSIFIED; absence zachovává legacy UNCLASSIFIED, neznámý typ je chyba.
Existing potřebuje EXTRACTED citaci shodného source inventory ID/path/repo/hash;
AMBIGUOUS/INFERRED nebo business dokumentace jej nevytvoří. Missing vyžaduje
aktuální validované CONFIRMED_MISSING; NOT_FOUND_IN_SCOPE zůstává unresolved.
Stale evidence nevytváří aktuální pozitivní facet. Delivery/test je deklarovaný
plán, execution NOT_RUN; processing completion zůstává kompatibilní.

RED: `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py`
před implementací 12 FAIL (chybějící projekce/typ/guard). Po opravách a přidání
scoped absence/ambiguous/legacy testů stejný příkaz 20 PASS / 0 SKIP, 1.57 s.
Jeden mezikrok měl 2 FAIL kvůli neexistujícímu testovému file ID; fixture nyní bere
skutečné node IDs z packet inventory, ne obcházení validace. `git diff --check` PASS.

## Krok 3 — atomická publikace svázaná se vstupy (Step 3, AC02–03)

Baseline `cceb1109`. Se souhlasem koordinátora jen report callsite
`feature_cli.py` a úzký `report_publication.py`: aditivní JSON report_projection,
přesné bytes current/historical packet/analysis/receipt/requirement, původní
read-only snapshot a kontrola před existing atomic_write replacement. Změna
už zastaralého vstupu se detekuje porovnáním obsahu, nikoli jen STALE hlášek.
Expiry dodané observation se kontroluje znovu před publikací. Neprobíhá prepare,
inspect/build/install/network/DB. Ostatní lifecycle ani context selector se nemění.

Mezikrok 4 PASS / 8 FAIL odhalil vlastní output tempfile v coverage.exclusions.
Oprava ignoruje pouze exclusion entries rezervovaného generated report prefixu;
zdroje, kontexty, manifest ani evidence se nefiltrují. Následně
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py tests/test_feature.py tests/test_feature_fixture.py tests/test_data_check.py`
45 PASS / 0 SKIP, 3.53 s. Regrese zahrnují late source/packet/analysis/receipt
change, již STALE zdroj, timeout/KeyboardInterrupt po vytvoření temp souboru,
expiry i neměnnost původních stores. Feature envelope a receipts bez migrace.

## Krok 4 — skutečná cross-layer fixture a hranice (Step 4, AC01–04)

Baseline `cceb1109`. `tests/test_complete_analysis_report_actual.py` reuse
existující explicitní `capture_workspace`: Javac21 DTO + TS5.7.3/React18 frontend
+ test repo, skutečné publikované compiler grafy. Připravené JVM workers a npm deps
jsou pouze použity, shared worker se nepřestavuje. Ve stejném workspace je
SOURCE_ONLY report controller/literal template/external PDF boundary a binární
XLS tool gap. Public `snapshot_workspace` + `dataflow.impact_paths` vytváří
explicitně uložený source/context/hash-bound BEFE artifact; report cituje přesný
hash a JSON pointer. Každý skutečný BEFE route má konkrétní origin/target IDs,
evidence/context IDs a SYMBOL_RESOLVED/FRAMEWORK_DERIVED hrany.

Source audit/RED fixture odhalil dva skutečné upstream limity: feature.prepare
vybírá právě jeden compiler context, a template relace nejsou v impact traversal
FORWARD. Nejsou obcházeny. Report má lokální validovanou FE request/JSON→JSX path,
samostatně citovaný multi-context BEFE artifact a INFERRED/SOURCE_ONLY
capability_match template/PDF s přesnými entities/citacemi. Žádný join ani nová
impact_path přes tyto hranice. TOOL otázka to výslovně vysvětluje; BUSINESS otázka
řeší měnovou jednotku/policy. FOREIGN path odmítnuta; všechny dostupnosti UNKNOWN.
První dvě spuštění fixture: 2 FAIL / 2 FAIL (chybný testový qualified path,
respektive nepodporovaná template traversal); oprava používá source_key a skutečný
kontrakt, ne nový resolver. Pak 2 PASS / 0 SKIP, 12.79 s.

Příkaz s rozšířenými late workspace/context/artifact kontrolami:
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src:tests /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py tests/test_complete_analysis_report_actual.py`
22 PASS / 0 SKIP, 29.28 s. Git-only process guard a zakázaná socket API ověřují
public apply/report po explicitní fixture přípravě; uložené compiler/sources bytes
zůstávají stejné. Obnovování testem mutovaných bytes je ve finally.

Cílená regresní matice před poslední úzkou expiry kontrolou:
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py tests/test_feature.py tests/test_feature_fixture.py tests/test_data_check.py tests/test_availability.py tests/test_templates.py tests/test_workbooks.py tests/test_binary_xls.py tests/test_methodology_conflicts.py tests/test_workspace.py tests/test_unified_flow_views.py -k 'not actual and not mermaid'`
215 PASS / 0 SKIP / 2 DESELECTED, 8.90 s. Není to full suite; actual report fixture
je provedena zvlášť. Kotlin/K1/K2/Mermaid NOT_RUN (nezměněné vrstvy); live PDF,
application/runtime/data NOT_RUN a netvrzeno. GH CI zatím NOT_RUN.

Dokumentace současně: README CLI příklad, docs/feature-analysis.md,
docs/complete-analysis-report.md, progress a acceptance inventory. Registry bez
dopadu (identity/revize/dependencies stejné); installed instructions/templates
bez dopadu (žádná jejich změna). Aktuální delivery rows W09/BEFE opraveny podle
skutečných merged cceb/7bb, historické test výsledky zachovány. Zbývá integrace
aktuálního main, semantic preservation/regeneration a PR/review.


## Krok 5 — integrace aktuálního main (Step 5, AC02–04)

Baseline rodiče `3fbc570` a main `83999fb2e08c6d9d67449687c95b2217eee08b09`
(PR111). Běžný merge, jediný konflikt append sekcí acceptance inventory; oba
obsahy zachovány. Main framework/inspection/criteria/JavaFrontend a jejich testy
jsou byte-identické s main; vlastní report source/test soubory s autorským rodičem.
Sémantika main má 50 concepts / 170 edges / 319 episodes; vlastní předchozí fakta
a historie se nesmí ztratit, následuje doložený reanchor.

Aktuální actual JAR použit read-only z `/tmp/kgmaker-criteria-queries/workers/jvm/target`,
SHA-256 `651468ee0743057ead245e57c2d36cc1b20633655853079a25f33d3bc05cc3fb`,
source shodný s main83999fb. Žádný shared rebuild. Dočasný symlink poté odstraněn.
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src:tests /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py tests/test_complete_analysis_report_actual.py tests/test_feature.py tests/test_workspace.py tests/test_data_check.py`
**73 PASS / 0 SKIP / 34.73 s**. Zahrnuje všech 25 vlastních report/actual/legacy
kontrol a skutečný Javac21/TS5.7.3/React setup po integraci. Širší 215-case sada se
bez důvodu neopakuje; je samostatný předintegrační checkpoint, ne current whole-suite.
Full/Kotlin/K1/K2/Mermaid/GH CI NOT_RUN.

`git diff --check --cached` PASS; source identity ověřena proti oběma rodičům.
README/capability/CLI/progress/acceptance jsou současně sladěny se skutečným
jednokontextovým feature scope a oddělenými evidence vrstvami. Žádné nové modely,
resolver, implicitní worker či migrace.


## Krok 6 — před-review publication audit (Step 3, AC02–03)

Baseline `7a8ac8b6efa4601b940276d1cd6daefc0f193f00`. Parent audit správně
identifikoval zbývající adresáře po late abort do nové vnořené cesty. Jeho první
symlink hypotéza byla následně odvolána: existující safe_path už komponenty
odmítá před resolve a veřejný `test_output_symlink_cannot_overwrite_source`
prošel; není deklarována nová symlink oprava ani přidán duplicitní test.

Skutečný veřejný hardlink alias byl přijat a ztratil link identitu po report
replacement (zdroj se nepřepsal). `report_output_path` nyní reuse `_safe_cache_target`
odmítá multlink/unsafe cíl v rezervovaném podstromu. Report-only `publish_report`
reuse atomic_write a W09 cleanup pravidlo: odstraní jen vlastní nové prázdné
parents, při BaseException včetně KeyboardInterrupt; cizí/concurrent obsah
zachová. Shared atomic API beze změny. `ReportGuard.read` předává přesné zachycené
bytes stávajícímu strict read_json parseru a vyžaduje shodu validated loader
payloadu, takže změněný mezilehlý payload nemůže převzít původní snapshot.

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py -k 'nested or hardlink or another_loaded'`
RED **4 FAIL / 1 PASS / 20 DESELECTED**, poté GREEN **5 PASS / 20 DESELECTED**,
0.35 s. Zahrnuje neměnnost files i directory inventory a zachování concurrent
obsahu. `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report.py tests/test_feature.py tests/test_unified_flow_views.py -k 'not actual and not mermaid'`
**151 PASS / 0 SKIP / 2 DESELECTED**, 4.42 s. Dvě vyloučené položky jsou
actual-Javac/Mermaid kontroly W09, nikoli PASS nebo SKIP. `git diff --check` PASS.
Starších73 integračních PASS je checkpoint před touto opravou. Actual report
fixture se provádí znovu samostatně; full suite stále NOT_RUN.

README, feature capability/CLI a complete-report dokumentace současně popisují
pinned bytes a own-parent cleanup; progress/acceptance odkazují na tento krok.
Instalované instructions/templates, task registry, resolver a výběr kontextu
bez dopadu. Zachován v1 report projection, v1 analysis i graph/store v1/v2/v3.

Oprava kroku6 byla navíc ověřena aktuálním skutečným worker setupem:
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src:tests /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_complete_analysis_report_actual.py`
**5 PASS / 0 SKIP / 26.31 s**; temporary JAR symlink odstraněn. Jde o samostatný
post-fix výsledek, nikoli součet s předchozími73 nebo215 testy.

## Krok 7 — sémantika, historie a předání (Step 5, AC02–04)

Baseline `83999fb` a vlastní integrační `7a8ac8b`. Znovu ověřena rezervace změny131:
main max129, otevřené PR110/change130 a historické draft4; žádná kolize. Autorský
push a draft [PR112](https://github.com/p-rum/kgmaker/pull/112) míří výhradně na
původní private `p-rum/kgmaker`, repoID1394670937; no force, žádný implementer merge.

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic update --base 83999fb2e08c6d9d67449687c95b2217eee08b09`,
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/report-reanchor.py`,
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic apply`,
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic validate`: PASS.
Patch zachovává všechny ovlivněné fakta, bez removals. Reanchor přijímá původní
obsah jen při přesné shodě jeho uloženého SHA-256 s ověřeným rodičem, mapuje pouze
nezměněné řádky a odmítá nejednoznačné entity IDs. Přidán jeden zdrojově doložený
report concept a tři vazby implements/uses/validates, žádná runtime inference.

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/report-preservation.py`: PASS
pro původní cceb (49/167/315), main83999fb (50/170/319) i autorský3fbc (49/167/315).
Původní facts (kromě doložených locatorů) i všechny přesné episode objekty jsou
zachovány. Po patchi **51 concepts /173 relationships /319 historical episodes**.
`kgmaker scan` obnovil GRAPH.md/GRAPH.mmd příkazem, nikoli ručním editováním.

První memory capture s nepodporovaným `full-suite=not_run` FAIL, žádná epizoda
nevznikla. Opravený skutečný příkaz
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory capture --base 83999fb2e08c6d9d67449687c95b2217eee08b09 --validation scoped-report-integration=passed --validation actual-javac-typescript=passed --validation full-suite=unknown`
PASS, epizoda `952e34647e09b2b2fe3910718961885cf100f00492ee1759d8dd5c3a1a5044c6`,
průběžný stav51/173/320. Jde o CURRENT capture po doloženém scanu aktuálních zdrojů,
nikoli o předstíraný pre-task graph delta. `unknown` je povolený memory status;
v této dokumentaci zůstává full suite výslovně NOT_RUN dle uživatele. Závěrečné
documentation reconciliation zachová tuto epizodu jako historii a používá stejný
capture/scan workflow pro current generaci. Žádná epizoda se nepřepisuje.

Aktuální veřejný rozsah a příklady jsou v README, docs/feature-analysis.md a
[complete-analysis-report.md](../complete-analysis-report.md); příklady v capability
nahrazují samostatný examples soubor (žádné nové CLI API). Progress i acceptance
odlišují PR_OPEN/VERIFIED_IN_SCOPE od report PARTIAL/UNKNOWN. Registry a instalované
instructions/templates bez dopadu. GitHub CI bez provedených job steps není PASS;
nezávislé review aktuálního HEAD a následný merge patří code_review agentovi.

`kgmaker check` spuštěný bez následného scanu po první memory capture: FAIL
(stale generated graph, žádná kódová/testová chyba). Závěrečný scan/check je
opakován po dokumentačním a memory reconciliation; generované soubory se nikdy
neopravují ručně. Self-review tím nenahrazuje nezávislé PR review.

Závěrečný checkpoint: scan/check **PASS**, 621 files /7198 nodes /49852 relationships;
preservation **PASS**,51/173/321 (319 původních + dvě skutečné capture epizody).
Workflow má doložené implementation/test artifacts a stav review bez vlastní
APPROVE. Aktuální main před ready znovu fetch ověřen jako83999fb. Po tomto přesném
záznamu následuje poslední current capture/scan; historické epizody zůstávají beze změny.

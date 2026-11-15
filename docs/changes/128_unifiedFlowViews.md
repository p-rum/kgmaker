# T003-S07-W09 — jednotné flow pohledy

Výchozí main `8e7dff5b82597184662797c07a68e5ec460e9e0e`, tree
`21b6e0fbfa4f7b863c5141361c86e1b96e7cce10`. W08 dependency byla nezávisle
APPROVE a merged v PR106. Samostatná větev `feat/t003-s07-09-unified-flow-views`.
Dodání IN_PROGRESS; ověření VERIFIED_IN_SCOPE po níže uvedené finální integraci. Nadřazené T003-S07/T003-AC07 se tímto
neprohlašuje za dokončené. Uživatelský pokyn omezuje běhy na cílené testy;
full pytest je NOT_RUN i přes historický text specifikace/profilu.

## Krok 1 — rekognoskace a RED acceptance

T003-S07-W09 krok1, AC01–AC04, baseline výše. Přečteny AGENTS, copilot,
registry, specifikace, profil a kgmaker-context/architect instrukce. Ve fresh
checkoutu `status`, `query 'flow control CFG'`, `memory recall 'unified flow CFG render'`
ohlásily chybějící graph.json: žádná pre-task compiler paměť nebyla dostupná.
Tracked GRAPH/NOTES a přímý source audit našly `flow.control_flow/process`,
oddělené render pořadí, JSON-only integrations/data-flow a nezajištěnou authority
při interprocedurální expanzi. Deliberate následný `scan` vytvořil navigační
SOURCE_ONLY index; následný query/recall nejsou vydávány za pre-task paměť.

`workflow list/check`, `task add --workflow existing-feature` a analysis/plan
artifacts byly zapsány před kódem; runtime task
`task:cb0a2afca9210f2b464b71992b291989761d1fdd7282733a4ef128059ec28ae9`.
Samostatný agent slot nebyl použit; požadovaná read-only architektická kontrola
proběhla přímo. Zdrojový audit nevykonal projekt ani worker.

`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_unified_flow_views.py`:
**FAIL 7 / 0.07 s**, chybějící `flow.build_report`. Golden fixture kombinuje
branch alternatives, loop-back, async resume/exception a unresolved boundary.
Model má explicitní model-only producer tuple; native důkaz je oddělený Javac.

## Krok 2 — společný model a authority hranice

T003-S07-W09 kroky2–3, AC01–AC03, stejný baseline. `flow.py` zachovává entity,
CFG a process IDs i legacy schema_version1; `flow_report.py` finalizuje jeden
report s flow_model_version=flow-view-1, coverage/gaps, provenance a CFG-derived
adjacency presentation order. Žádný total order paralelních větví nevzniká.
Source CFG je syntaktická evidence; procesní expanze navíc vyžaduje current
caller→site→target proof a callee CFG proof. `views.py` sdílí původní W08 authority
/freshness helpery, aby se pravidla nerozcházela. Source-only/legacy nemá novou
execution autoritu. Chybějící CFG vrací UNKNOWN; invalid snapshot zůstává chyba.

Všechny formáty používají stejné uzly/hrany/gaps. Mermaid metadata comments
uchovají přesné IDs, evidence i diagnostics; Markdown obsahuje tentýž diagram a
textovou provenance/coverage. Integrations/data-flow používá RELATIONSHIP_ONLY,
zachovává legacy nodes/edges a netvrdí CFG pořadí. Limits počítají také explicitní
boundary uzly; příliš malý rozpočet vrací opaque root s původními endpoint IDs.

Kompatibilita: graph/store v1/v2/v3 se nemění; v1 nemá scope klasifikaci a čte se
s explicitním `--scope all`. Raw flow API i CLI používají stejnou validaci.
V3 Python objekty odporující reader schema již nejsou přijaty jen proto, že
neprošly readerem. Žádná změna compiler worker/protocol ani sousedního work package.

## Krok 3 — veřejné CLI a atomický výstup

T003-S07-W09 krok3, AC01–AC03, stejný baseline. Výslovně koordinovaný ownership:
flow-only registrace/index výběr/dispatch v `inspection_cli.py`;
`analysis_model.atomic_write` aditivní keyword-only before_replace callback po
fsync, uvnitř dosavadního try/finally. Ostatní callers beze změny.

`flow render` zachovává stdout a format default mermaid. Nové `--output` přijímá
pouze `.kgmaker/flows/`, `--timeout` je kladný konečný cooperative deadline,
`--cancel-file` externí lokální marker. Reuse safe_path a safe cache target guard
odmítá symlink/hardlink, store/source/input alias; před replace se znovu kontroluje.
Text se validuje a sestaví před publikací. Flow cesta sleduje pouze vlastní nové
parent dirs a po abortu odstraní pouze stále prázdné; souběžný obsah zachová.

Fault injection pokrývá timeout/cancel/KeyboardInterrupt/OSError po zápisu temp,
last-valid bytes, cleanup temp i nových parent directories. Žádné implicitní
subprocessy/network při renderu. Invalid args/input ponechá output/store beze změny.
Strict PARTIAL/UNKNOWN vrací 4 ve všech třech formátech; invalid vstup 2, stale
provider 3. Validní částečný report lze vědomě publikovat a má explicitní status.

## Krok 4 — cílené regrese a skutečné toolchainy

T003-S07-W09 krok4, AC01–AC04, stejný baseline. Vlastní tests/golden/unified-flow,
fixture `fixtures/unified-flow`, skutečný parser
`tests/rendering/validate_unified.mjs` (Mermaid11.4.1/jsdom26), actual Javac21
inspection + public CLI. Native fixture obsahuje if/else, loop, statický callee
s návratem a nevyřešený cíl. Není tvrzen obecný Kotlin/TS CFG scope nebo runtime běh.

Historické checkpointy:

- Vlastní schema testy **PASS 21 / 0.09 s**; parser **PASS 8 vertices / 9 edges**.
- W08/control-flow/schema checkpoint **PASS 136 / 1 actual deselected / 0.41 s**.
- První pětimodulová regrese: **FAIL 44 / PASS 94 / ERROR 53 / 16.23 s**.
  Převažovaly explicitní test HOME override bez připravených local worker targets
  /TS node_modules; nešlo o PASS toolchainu. Následná konkrétní klasifikace níže.
- T025 izolovaně: **FAIL 5 / PASS 35 / SKIP 2 / 1.14 s**. Čtyři pozitivní
  schema topology testy měly legacy mode=SYMBOL_RESOLVED bez inspection authority;
  root budget navíc ztrácel context/proof provenance (opraveno v produkčním kódu).
  Lokální T025 setup nyní má explicitní model-only producer tuple nad původními
  source hashes/proofs; nový negativ zachovává původní bare authority bez expanze.
- Dvě spring modelové fixtures měly schema-invalid role=framework a chybějící
  context/proofs. Opraveny na validní model-only tuple, actual testy beze změny.
- Po těchto opravách vlastní/T025/Spring sada **PASS 79 / 0 SKIP / 9.97 s**,
  včetně skutečných JVM fixture. První W09 public output pokus správně odmítl
  stale index po uložení parser artefaktů do zdrojového rootu; test nyní ukládá
  generované reporty do `.kgmaker/flows/`, neobchází freshness.
- Argument/return sada **FAIL 4 / PASS 126 / 68.04 s**: tři environment failures
  chybějící TS dependencies v zvoleném externím workers home; čtvrtý byl skutečná
  renderer regrese ztracené Markdown return/consumer sekce. Sekce obnovena.
  Finální prostředí používá místní workers home s prepared JVM/TS symlinky.

Finální matice a source-backed semantic preservation budou doplněny po skutečném
běhu, nikoli nahrazeny checkpointy. Full/GH CI NOT_RUN. Zbývá review a publikace.

## Dokumentační plochy

README, capability/CLI `docs/unified-flow-views.md`, compiler inspection rozcestník,
production matrix a acceptance inventory odkazují na tento záznam. Registr/task
identity bez dopadu: existující W09 revision1 se nemění. Init/templates bez dopadu:
žádné instalované instrukce ani jejich generátor se nemění. Historická change notes
zůstávají zachována. Žádná předchozí zelená fixture nedokládá libovolný produkční CFG.

Aktuální předintegrační kontroly (2026-11-15):

- `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_WORKERS_HOME=/tmp/kgmaker-unified-flow-views/workers KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_argument_parameter_flow.py tests/test_return_consumer_flow.py tests/test_unified_flow_views.py tests/test_t025_build_local_process_path.py tests/test_spring_proxy_async.py tests/test_control_flow.py tests/test_evidence_ranking.py tests/test_graph_provider.py`:
  **PASS 349 / 0 SKIP / 86.59 s**. Prepared local JVM target/target-k2 odkazují na
  `/tmp/kgmaker-pr97-reconciled/workers/jvm/`; TS a rendering node_modules na již
  připravené pinned dependencies sdíleného rootu (root bez mutace).
- Po dodatečném exact site-proof provenance a stale callee-CFG negativu:
  stejná sada bez argument/return modulů **PASS 221 / 0 SKIP / 10.95 s**.
- `node tests/rendering/validate_unified.mjs tests/golden/unified-flow/branch.mmd tests/golden/unified-flow/branch.json`:
  **PASS 8 vertices / 9 edges**, deep equality všech metadata/node/edge fields.
  Mermaid title navíc viditelně označuje status/truncation a async nodes scheduling
  UNKNOWN; nejde jen o neviditelné metadata komentáře.

Lokální symlinky nejsou součástí commitu a po závěrečných testech se uklidí.

Při doplnění Mermaid title první parser běh **FAIL**: DOMPurify v Node/jsdom
vyžadovalo globální `Element`. Test harness nyní výslovně sdílí `dom.window.Element`;
opakovaný skutečný parser **PASS 8 vertices / 9 edges**. Renderer text se tím
neobešel ani nevynechal z validace.


## Krok 5 — integrace T028 a finální acceptance

T003-S07-W09 krok5, AC01–AC04. Implementační checkpoint
`7c3834c` vznikl nad původním main8e7; následně `git fetch origin main` ověřil
`9f538634807957abe1004dde43450271b77f1bb5` (T028 merge, tree990f9de7).
`git merge --no-edit origin/main` vyžadoval pouze spojení append sekcí v acceptance
inventory a production progress; obě historie ponechány. Merge commit
`7e79c80ffa449852e553158053edcf47395a7bbb`, tree740b7eac. Žádný T028 source kód
ani jeho fixtures nebyly měněny. Semantic baseline main47/154/307 převzat celý.

Integrační příkaz (prostředí přesně jako předchozí 349 sada):

`/tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_unified_flow_views.py tests/test_t025_build_local_process_path.py tests/test_spring_proxy_async.py tests/test_control_flow.py tests/test_evidence_ranking.py tests/test_graph_provider.py tests/test_t028_cross_async_process_boundary.py`

**PASS 280 / 0 SKIP / 34.70 s**. Samostatné poslední přímé flow binding testy
`tests/test_argument_parameter_flow.py::test_graph_evidence_roundtrip_and_process_preserve_call_binding`
a `tests/test_return_consumer_flow.py::test_process_and_impact_report_static_return_consumer_provenance`:
**PASS 2 / 1.42 s**.

Závěrečný source audit navíc našel CFG call blok s nulovou/nejednoznačnou occurrence:
nový AMBIGUOUS_CALL_BLOCK přiznává mezeru bez domýšlení expanze. Neplatná library
representation je explicitní chyba, nikoli UNKNOWN prázdný úspěch. Doplňkové
3 negativy jsou ve vlastním test modulu. Finální příkaz je integrační sedmimodulová
sada výše plus oba přesně jmenované binding testy: **PASS 285 / 0 SKIP / 32.38 s**.
To je aktuální source verification; historické checkpointy se nesčítají.

Kompatibilita a dokumentační plochy odpovídají capability. Remaining: nezávislé
review a publikace; full/GH CI NOT_RUN, širší runtime/CFG a celý S07 neuzavřeny.

## Krok 6 — source-backed semantic a předání

T003-S07-W09 krok5, AC04, baseline9f538634. `semantic update --base
9f538634807957abe1004dde43450271b77f1bb5` vytváří aktuální packet; nový patch má
jediný source-backed koncept a5 vztahů implementuje/validuje. Historické source
hashes a nezměněné citation lines se ověřily před reanchor. Nové multiline
`build_report` není samostatný scanner node, proto vztah používá existující file ID
a přesnou def citation, nikoli vymyšlenou identitu.

První helper pokus odmítl chybějící function ID, `semantic apply` **FAIL** bez
patch souboru a validate správně ohlásilo dosud stale citace; žádná historie nebyla
změněna. Nový current packet a file-ID patch prošel. Druhý reanchor při doplnění
negativů správně odmítl záměnu staré a nové citation baseline; následně mapuje
historická fakta proti přesnému main9f a již přidaná fakta proti ověřenému committed
source hash HEAD7e79. Ověřený script `/tmp/unified-flow-reanchor.py` nezahazuje žádný
node/edge/episode. Výsledky finálního apply/validate/scan/check/preservation níže.

Poslední source fix kroku5 se dotkl `src/kgmaker/flow.py`,
`src/kgmaker/flow_report.py`, `tests/test_unified_flow_views.py`; původní baseline
byl integrační `7e79c80`. Capability i fixture README popisují stejné limity.
Workflow test-artifact validator odmítl příkaz delší než200 znaků (**FAIL**, bez
zápisu artefaktu). Přesný dlouhý příkaz je zachován výše; korektní workflow artifact
zaznamenává skutečně provedené `tail -20 /tmp/unified-flow-final-matrix.log` jako
kontrolu execution logu, nikoli alternativní test command. Task přešel do review.

První `memory capture` **FAIL** bezpečně odmítl local prepared JVM symlink mimo
checkout. Všechny čtyři dočasné JVM/TS/Mermaid symlinky byly odstraněny bez zásahu
do jejich cílů; opakování capture je samostatně ověřené níže.

Finální maintenance **PASS**:

- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic apply`
  a `semantic validate`: 48 konceptů /159 vztahů, žádná odstranění.
- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory capture --base 9f538634807957abe1004dde43450271b77f1bb5 --validation integrated-285=passed --validation earlier-targeted-349=passed --validation full=skipped`:
  episode `9b089887abbfa58a0b4015cffbaa34545432410a3c8f51d3472111bbaddc7476`.
- `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker scan` a `check`:
  grafy generované příkazem, aktuální.
- `python3 /tmp/unified-flow-preservation.py`: všechny main9f koncepty, vztahy
  (s ověřeným posunem citací) a immutable epizody zachovány **47/154/307 →48/159/308**.
- `git diff --check`: PASS. Main/open PR kolize před publikací: max change127,
  otevřené107/change125 a historický draft4; rezervace128 platí.

Po doplnění výsledků, fixture README a PR odkazu pouze dokumentační scan/check/diff;
pytest bez další source změny znovu NOT_RUN. Nezávislé review musí ověřit nový HEAD;
implementační agent tento PR nemerguje.

## Krok 7 — závěrečný runnable/scope audit

T003-S07-W09 kroky3–4, AC01/AC03, baseline integrační `7e79c80` plus výše
zaznamenané W09 opravy. Přímý source audit našel rozdíl mezi W08 rank a flow:
platný context/proof tuple sám neověřoval executable role caller/site/callee a
jejich stejný scope. `views.is_execution_entity` nyní sdílí původní W08 runnable
pravidlo; rank pouze deleguje identickou podmínku, flow před expanzí kontroluje
všechny3 endpointy a scope. Config/type/cross-test reference proto nevyrobí
interprocedurální path ani při formálně validním silném edge labelu.

Dotčeno `views.py`, `flow.py`, vlastní negativy v `test_unified_flow_views.py` a
T025 pozitivní schema setup/helper (explicitní executable_code u method/site
modelu; původní bare authority negativ beze změny). Reálné worker outputs a
schema/version se nemění. Capability již popisovala tuto hranici a její tvrzení
nyní pokrývají další3 explicitní testy, včetně scope=all.

Přesně finální285 příkaz kroku5 (stejných7 modulů a2 binding testy, stejné native
prostředí) po doplnění těchto případů: **PASS 288 / 0 SKIP / 32.30 s**.
Předchozí285 je historický checkpoint. Nový current semantic packet, ověřené
reanchor a samostatná implementační epizoda následovaly po této source opravě;
starší epizoda9b089887 zůstává immutable historií.

Maintenance po kroku7: current `semantic apply/validate/scan/check` a preservation
**PASS**, 48/159/309; druhá immutable epizoda
`92067b6faf40783a425fe4ca29a2344a20dec528617b43695e5fc7aae24db794`.
Příkaz capture: `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory capture --base 9f538634807957abe1004dde43450271b77f1bb5 --validation integrated-288=passed --validation full=skipped`.
Následuje ještě povinná kumulativní integrace mezitím sloučeného BEFE PR107.

## Krok 8 — poslední integrace BEFE a relation-mode věrnost

T003-S07-W09 krok5, AC01–AC04. Výchozí W09 commit
`50712f03e19d20f194b7393936b6e89150b888db` (48/159/309) a nový skutečný main
`7bb8b8d389c461c684197704203a99dcb2b83724` (48/157/310; PR107).
`git fetch origin main && git merge --no-edit origin/main` provedl source merge
bez konfliktů. Konflikty byly pouze v semantic.json a generovaných GRAPH souborech.
Sémantické ID/relations byly sjednoceny při zachování obou parents; všechny immutable
episodes z obou parents zůstaly. Generated GRAPH byl obnoven pouze `kgmaker scan`.
Merge commit `b3796053e059ac6c1ccd1ebc8da832be08b8de85`, součet49/162/312 před
finální integrační epizodou. BEFE helper/validation/cache source nebyl upravován.

Při integraci vyšlo najevo, že dosavadní data-flow whitelist neobsahoval existující
FORWARD/REVERSE relation sets z `dataflow.py`, včetně FE value vztahů. Koordinovaná
oprava ve `views.project` tyto sets pouze reuse, zachovává stored orientaci a
W08 compiler-context isolation před filtrem. Nejde o nový resolver ani převod
reference na CFG execution. `flow_report` stále uvádí RELATIONSHIP_ONLY,
NOT_OBSERVED/UNKNOWN. Nový actual single-context FE test reuse W05 compiler capture
(Javac21/TS5.7.3/React18), zachová cestu HTTP_RESPONSE→JSX_CONSUMER v existujících
FE vztazích a porovná skutečný Mermaid parse s reportem. Mixed-context BE→FE bridge
se tím nezpřístupňuje výběrem druhého compiler contextu.

První integrační test **FAIL1 / PASS291 / 48.38 s**: nový test chybně očekával
`passes_value` v samotné frontend fixture. Source producer tento druh emituje pro
ordinary argument consumer; zde state setter emituje `writes_value`. Cesta
HTTP_RESPONSE→JSX i exact evidence byly přítomné. Assertion byla opravena na
skutečný producer kontrakt; upstream pozitivní workspace/test-argument regression
zůstává samostatně zapnutá a neoslabuje se. Žádná změna workeru kvůli testu.

Finální příkaz je přesný 288 příkaz kroku7 plus:
`tests/test_backend_frontend_value_flow.py::test_ac01_actual_backend_field_has_exact_ui_and_test_paths`,
`tests/test_backend_frontend_value_flow.py::test_ac02_source_only_and_legacy_versions_never_gain_compiler_flow`,
`tests/test_backend_frontend_value_flow.py::test_ac03_cached_context_revalidates_external_package_inputs`.
Lokální prepared prostředí navíc obsahuje dočasný symlink
`fixtures/build-inspection/frontend/node_modules` na pinned React fixture ve
sdíleném rootu; po kontrole se odstraní spolu s předchozími čtyřmi symlinky.

Další opakování matrice mělo **FAIL1 / PASS291 / 48.98 s**. JVM handshake správně
odmítl INVALID_PROTOCOL: host JVM na stdout vypsala warning perfdata lock kolize
`/tmp/hsperfdata_petra/618`, a potom JSON. Protocol parser nebyl oslaben ani nebyl
smazán sdílený soubor. Pouze pro test command přidáno
`JAVA_TOOL_OPTIONS=-XX:-UsePerfData`; tento flag mění host performance bookkeeping,
nikoli compiler worker kontrakt. Po opravě prostředí a doplnění mixed-context
relation renderer negativu: přesný příkaz kroku8 s tímto env flagem
**PASS293 / 0 SKIP / 46.72 s**. Single-context FE cesta i všechny tři formáty
prošly actual capture/parser; mixed compiler claim je ve všech formátech vynechán
s COMPILER_CONTEXT_BOUNDARY_UNKNOWN, bez cizího context/evidence objektu.

Závěrečný docs/script compatibility audit odstranil nepravdivou aktuální větu
„Data/integration view zatím poskytuje JSON“ v compiler-inspection.md. Existující
`tests/rendering/validate.mjs` je sladěn se skutečným modelem: budget/truncation
nemintuje extra vizuální uzel mimo CFG, status je viditelný v title; jsdom poskytuje
Element i pro title sanitizer. Příkazy
`node tests/rendering/validate.mjs tests/golden/unified-flow/branch.mmd tests/golden/unified-flow/branch.json`
a `node tests/rendering/validate.mjs /tmp/unified-flow-truncated.mmd /tmp/unified-flow-truncated.json`
**PASS 8/9 a2/1 vertices/edges**. Truncated payload vznikl příkazem
`flow.build_report(model_graph(),'method',max_nodes=3)` + `flow.render`, nikoli
ruční editací. Po tomto docs/test-harness doplnění žádný další production source
change; pytest bez nové příčiny neopakován.


## Krok 9 — R07 snapshot před atomickou publikací

T003-S07-W09 kroky3–5, AC02–AC04, T003-R07. Výchozí SHA
`b3796053e059ac6c1ccd1ebc8da832be08b8de85`, již integrovaný main7bb.
Předchozí293 PASS je checkpoint kroku8, nikoli důkaz této nové opravy.
Source audit našel chybějící late freshness guard: po načtení indexu mohl renderer
publikovat starý report, pokud se index/source změnil před os.replace.

`inspection_cli.indexed` pouze pro flow --output parsuje přesné jednou načtené
index bytes; `PublicationSnapshot` v flow_report.py je porovnává při startu i
před replace. Proto se nový fingerprint nemůže přiřadit ke starému graphu.
Reuse scanner `_candidate_files`/`_safe_source`/`_file_digest` zachovává bounded
normalized-text graph.files kontrakt a navíc hlídá raw bytes během pokusu.
Initial readable inventory se musí rovnat indexovanému; přidaný soubor mezi
indexed a guardem vyvolá STALE. SOURCE_ONLY LOCAL_SOURCE classifier fingerprint
se ověřuje stávajícím Classifier; legacy nepřibývá compiler autorita. Compiler
snapshot se ověřuje existujícím validate_compiler_snapshot bez worker/network.
Callback před replace znovu kontroluje i output aliases, deadline a cancel.
Stdout a jiné atomic_write callers zůstávají beze změny.

Dvě konkrétní připomínky root source auditu byly vyřešeny před předáním:
initial-only kontrola jednotlivých graph.files mohla převzít nově přidaný soubor,
a binární workbook by chybně selhal na UTF8 kontraktu. `workbooks.py` proto po
schválení ownership pouze extrahuje **nezměněný** candidates výraz a jeho sort/
exclusions do `workbook_paths(root)`; producer i guard jej reuse. Žádná změna
parseru. Indexed XLS/XLSX používá `workbook_hash` streaming raw checksum, nový/
smazaný workbook mění zachycený inventář. Neindexovaný workbook nevytváří flow
proof. Test zakazuje workbook extract během renderu. Vlastní smíšený source +
actual XLSX (stávající write_xlsx fixture) a unsupported XLS validně publikují
UNKNOWN, změny/add/delete po fsync zachovávají last-valid bytes/temp cleanup.

Ve `tests/test_unified_flow_views.py` přibyly také veřejné v1/v2/v3 SOURCE_ONLY
source/index/addition/classification mutation negativy pro existující i původně
neexistující output parents. Test obnoví pouze injektovanou externí změnu a
porovná celý filesystem před/po: žádný publikací vytvořený file/directory
nezůstane. Explicitní indexed→capture race test pokrývá starý graph + nové index,
source, added-source či classification. Actual Javac test znovu doložil late
source/index odmítnutí po temp fsync, se zákazem implicitního process/network.

Průběžný nejmenší příkaz `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_unified_flow_views.py -k 'publication or atomic or abort'`
**PASS28 /27 deselected /0.62 s**. Následné vlastní W09+provider checkpointy
**PASS65 /8.81 s**, **PASS73 /8.87 s** byly před konečným
workbook doplněním; nejsou vydávány za jeho důkaz. Finální přesný příkaz:

```sh
JAVA_TOOL_OPTIONS=-XX:-UsePerfData JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_WORKERS_HOME=/tmp/kgmaker-unified-flow-views/workers KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_unified_flow_views.py tests/test_graph_provider.py tests/test_workbooks.py
```

**PASS84 /0 SKIP /9.30 s**, log `/tmp/unified-flow-publication-final.log`.
Skutečný Javac21/TS5.7.3 a Mermaid11.4.1 parser proběhly; modelové schema testy
zůstávají oddělené. `git diff --check` PASS. Původní293 ani full se neopakují bez
nové příčiny; full a GH CI NOT_RUN. README/capability/progress/acceptance a tento
záznam upraveny ve stejném kroku. CLI příklad používá stávající --output; nová
STALE chyba má exit3. Spec/registry bez dopadu: identita, revize, závislosti a
cílové AC se nemění. Instalované instrukce/templates bez dopadu.

Limity: deadline je cooperative a finální validation nezamyká externí writery.
Last-valid ochrana platí pro zjištěný invalid/stale snapshot, timeout/cancel/
interrupt; cizí concurrent obsah se nemaže. Žádná nová obecná CFG/async runtime
podpora, žádný S07 milestone completion. Následuje source-backed semantic
maintenance a samostatný PR k nezávislému review.


## Krok 10 — finální kumulativní semantic a předání

T003-S07-W09 krok5, AC02/AC04; baseline main
`7bb8b8d389c461c684197704203a99dcb2b83724`, implementační výchozí HEAD b3796053.
Po source freeze kroku9 byly revidovány aktuální source kotvy, včetně callbacku
publikace a nových veřejných source/binary negativů. Příkazy:

```sh
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker scan
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic update --base 7bb8b8d389c461c684197704203a99dcb2b83724
python3 /tmp/unified-flow-7bb-reanchor.py
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic apply
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker semantic validate
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker memory capture --base 7bb8b8d389c461c684197704203a99dcb2b83724 --validation publication-84=passed --validation integrated-293-checkpoint=passed --validation full=skipped
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker scan
PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m kgmaker check
python3 /tmp/unified-flow-7bb-preservation.py
python3 /tmp/unified-flow-ours-preservation.py
git diff --check
```

Vše **PASS**. Patch obsahuje pouze aktuálně doložené změny/reanchor, žádné
remove_nodes/remove_edges. Tracked semantic výsledek **49 konceptů /165 vztahů /
314 immutable episodes**, tedy main48/157/310 celý zachován a navíc vlastní
W09 historie. Preservation porovnává obě historie (main7bb a W09 commit50712f0),
normalizuje jen posunuté line suffix IDs a ověřuje staré zdrojové citace proti
baseline bajtům. Všech313 epizod před posledním capture je deep-equal zachováno.
Krok8 epizoda `1f872f6b81d68006c40725343df8a582a0e2222dae0de8c53f7ab442644d6f4f`;
krok9 epizoda `7e75efa7f012bf79b05d13324c1b93c53d9393109b99c7d54d311a8145ed83c7`.
Generated graph vznikl pouze příkazem (608 files /7016 nodes /48983 relationships
před posledním docs-only záznamem). Semantic validate expanded view362 concepts /
33741 relationships není počet tracked author-semantic záznamů.

Prepared JVM/K2/TS/React/Mermaid symlinky byly odstraněny; shared targety se
neměnily. Read-only `git ls-remote origin refs/heads/main` znovu potvrdil main7bb.
GitHub search otevřených PR vrátil pouze historický draft4; change128 bez kolize,
registry dependency W08 merged. Další registry identity/revision změna nenastává.
Pokus `kgmaker task advance <task> implement` **FAIL**: iteration2/max3
(zero-based) již nepovoluje další návrat z review. Následné record/advance
pokusy byly odmítnuty beze změny historie (artifact z /tmp je navíc mimo root).
Limity tasku ani staré artefakty se nepřepisují. Finální skutečné evidence jsou
append-only orchestration handoff artefaktem ve stávající review fázi;
nejde o independent APPROVE ani fingované implement/test phase. Přesný pytest
command a výsledek jsou v kroku9; durable task zůstává review.
Následný pouze dokumentační PR odkaz vyžaduje scan/check/diff, nikoli znovu pytest.
Independent review zbývá; implementer nemerguje. Full/GH CI NOT_RUN.

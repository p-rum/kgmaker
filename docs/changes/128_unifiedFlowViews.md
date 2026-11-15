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

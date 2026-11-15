# T003-S07-W09 — jednotné flow pohledy

Výchozí main `8e7dff5b82597184662797c07a68e5ec460e9e0e`, tree
`21b6e0fbfa4f7b863c5141361c86e1b96e7cce10`. W08 dependency byla nezávisle
APPROVE a merged v PR106. Samostatná větev `feat/t003-s07-09-unified-flow-views`.
Dodání IN_PROGRESS; ověření dosud PARTIAL. Nadřazené T003-S07/T003-AC07 se tímto
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

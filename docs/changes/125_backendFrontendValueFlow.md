# T003-S08-W05 — compiler doložený backend→frontend tok

Datum: 2026-11-15. Výchozí SHA všech níže uvedených kroků:
`d2507ef465c9b4844830520de68629a3b577c0d2`. Větev:
`feat/t003-s08-05-backend-frontend-value-flow`. Cílový main poPR105 byl začleněn samostatně; jeho SHA a integrační ověření
jsou uvedeny níže.
Task `T003-S08-W05`, nadřazená `T003-AC08`; dodání IN_PROGRESS,
ověření VERIFIED_IN_SCOPE pro omezenou matici. S08 jako celek zůstává PARTIAL.

## Krok 1 — rekognoskace a audit rozpracované změny

**Task/Step/AC:** T003-S08-W05 krok 1, AC01/AC03. Problém: jediný `fetch` v souboru
původně propojoval i nesouvisející JSON/promise/state/assertion podle stejného
názvu pole. Pouhé označení INFERRED ani obecná přítomnost compiler evidence
nedokládají takovou datovou cestu.

Přečteny AGENTS, copilot instructions, registr, zadání, profil, architekt a
`kgmaker-context`. `status`, `query` a `memory recall` zde skončily **FAIL**:
nový izolovaný checkout neměl čitelný `.kgmaker/graph.json`. Tracked GRAPH/NOTES
a historie semantic.json zůstaly zachovány; následoval přímý source/test audit
`workspace.current_graph`, `federated_links`, return/local-operation kontraktů,
TS symbolů, provenance a existujících worker fixture. Chybějící pre-task paměť
se zpětně nevyrábí. Runtime workflow má lokální task
`task:9cd0e3eba58339b3aff2f75a8342729385c8b1bd42aaec2d4182b40c61cca3aa`;
analysis/plan záznamy výslovně uvádějí chybějící graf.

Historické předané regex testy (19/28/3 PASS s worker SKIP) nejsou acceptance
nové implementace; byly nahrazeny skutečnou fixture. Pozitivní veřejný test před
novou implementací nedokázal najít požadovanou compiler cestu (**FAIL/RED**).

## Krok 2 — aditivní compiler occurrences, validace a distribuce

**Task/Step/AC:** T003-S08-W05 krok 2, AC01/AC02/AC03.
Změny: `workers/typescript/frontend_values.cjs`, `worker.cjs`, `package.json`,
`src/kgmaker/inspection.py`, `src/kgmaker/frontend_flow.py`, `pyproject.toml`,
`tests/test_tsconfig_freshness.py`.

TS TypeChecker doloží standardní DOM fetch/json, lokální binding IDs a oddělené
výskyty hodnot s hashem, rozsahem a kontextem. Podporované jsou await, const,
property/destructuring rename a explicitní object mapping. React state vyžaduje
pinned React18.3.1/@types18.3.18 declaration, skutečný symbol useState a přesný
setter argument; jméno setteru nehraje roli. Více zápisů, alias/escape, mutace,
callback/branch/loop/try a custom JSX nedostávají neprokázanou cestu. Samostatné
state properties mají samostatné identity. Test consumer je konkrétní resolved
call argument, nikoli heuristika názvu expect/assert.

Optional `value_flow_version=1` facts/symbols reuse graph value_occurrence; staré
v1/v2/v3 a worker-response-v1 zůstávají čitelné. Validator odmítá jiný hash,
rozsah mimo deklaraci, kontext/verzi a neplatnou React provenance před publikací.
Nový helper je součástí wheel/sdist, distribution hash a package marker fail-closed
kontroly. Instalované host instrukce ani Python init templates se nemění: **bez
dopadu**, nevznikl nový host command ani přepis uživatelského souboru.

Historické cílené kontroly před posledním hardeningem:

- **PASS** `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_backend_frontend_value_flow.py` — 16 passed/25.50s.
- **PASS** stejný environment + `python -m pytest -q tests/test_backend_frontend_value_flow.py tests/test_worker_install.py::InstalledWorkerTests::test_packaged_typescript_analyzes_outside_checkout -x` — 21 passed/57.87s (20 W05 a skutečný clean sdist→wheel→venv TS smoke mimo checkout).
- Jeden průběžný běh skončil **FAIL/STALE** po17 PASS, protože v době běhu byl upraven worker helper; ochrana distribuce správně odmítla smíšený snapshot. Tento běh není finální test evidence a níže jej nahrazuje opakování na stabilních zdrojích.

## Krok 3 — workspace bridge, impact a odstranění false positives

**Task/Step/AC:** T003-S08-W05 krok 3, AC01/AC02/AC03.
Změny: `frontend_flow.py`, `workspace.py`, `dataflow.py`, `test_analysis.py`.

Read-only snapshot reuseuje current_graph/retain_compiler_layer, contract
capture a generation_origin. K bridge je třeba přesný aktuální backend field
symbol a source hash, jednoznačná service/method/path, metadata cílená na
consumer a aktuální contract/generated hash i release. Generování zůstává
LOCAL_DECLARED, payload compatibility/availability UNKNOWN a runtime NOT_OBSERVED.
Nejde o nový remote katalog ani automatický W07 binding. Backend field→contract
→konkrétní field projection se spojuje s compiler request→JSON ancestry;
navazující mapping/state/UI/test mají konkrétní IDs a evidence. Impact přidává
`frontend_value_bindings` vedle existujícího return/argument kontraktu.

Staré syntax UI/test nodes se stále inventarizují. Odstraněny jsou name-only
`displayed_in`/`asserts_field` zkratky. `test_fa46_47_identity_and_cross_repo_impact`
proto ověřuje zachovaný inventář a contract candidate, současně **neexistenci**
nepodložené cesty a konkrétní COMPILER_EVIDENCE_UNAVAILABLE gap. Je to záměrná
oprava veřejného false-positive chování; SOURCE_ONLY je PARTIAL/UNKNOWN.

**PASS** stabilní cílená regrese před závěrečným hardeningem:
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_workspace.py tests/test_dataflow.py tests/test_inspection_contract.py tests/test_tsconfig_freshness.py -x`
— 60 passed/43.68s. Před opraveným očekáváním byl původní SOURCE_ONLY test RED,
protože očekával právě odstraněný false positive.

## Krok 4 — skutečná acceptance fixture a hranice

**Task/Step/AC:** T003-S08-W05 krok 4, AC01/AC02/AC03.
`tests/test_backend_frontend_value_flow.py` připravuje tři skutečné lokální Git
checkouty. Explicitně publikuje Javac21 backend a TS5.7.3 frontend/test index;
React18.3.1/@types18.3.18 jsou připravené dependency, nikoli stub useState.
Konkrétní request/JSON/destructure/state/UI a test argument cesta se ověřuje
po IDs/hranách/evidence, včetně impact. Negativy pokrývají změnu pole/source,
contract/generated hash, release, missing checkout, ambiguous service,
nesouvisející JSON/promise/state/assertion, shadowing, multiple writes a missing
await. Invalid worker hash/range/context/version zachová byte-identical store.
Snapshot smí spustit jen explicitní Git baseline čtení; worker/network/app procesy
jsou v testu zakázány, soubory všech repo se nesmějí změnit.

Kotlin, obecné Promise callbacky, Axios/Playwright, libovolné React verze,
interprocedurální/heap/branch merging ani runtime execution nejsou ověřené.
Podporovaná deklarace generation provenance není generator execution receipt.
Full suite je **NOT_RUN** podle výslovného uživatelského omezení pouze na cílené
testy do dokončení celého balíku. GH CI zatím **NOT_RUN**.

## Krok 5 — dokumentace, integrace a předání

**Task/Step/AC:** T003-S08-W05 krok 5, AC04.
Aktualizovány `README.md`, `docs/backend-frontend-value-flow.md` (API, metadata,
CLI, compatibility/limity), `docs/compiler-inspection.md`,
`docs/flyway-workspace-proofs.md`, `docs/production-analysis-progress.md` a
`docs/acceptance-inventory.md`. CLI parametry porovnány s `inspect code --help`
a `impact --help` (**PASS**). Registry/spec jsou **bez dopadu**: nezměněna
identita, revize, dependency ani odkaz existujícího W05; SPECIFICATION zůstává cíl.

Závěrečné kontroly a integrace jsou uvedeny níže. Nezávislé review a merge
provádí pověřený reviewer; implementer nemerguje.

### Krok 3/4 — závěrečný hardening generation a cache

Stejný baseline a AC01/AC03. Před integrací prošla stabilní cílená matice
`tests/test_backend_frontend_value_flow.py tests/test_workspace.py tests/test_dataflow.py tests/test_ui_events.py tests/test_inspection_contract.py tests/test_tsconfig_freshness.py`
se stejným JDK21/REQUIRE_WORKERS/PYTHONPATH environmentem: **165 PASS /0 SKIP,
197.83s**. Následný source audit doplnil nutnou vazbu compiler field declaration
na konkrétní hashovaný generated soubor a opakované ověření kontextu i při
workspace cache hitu (dependency node_modules není běžný source inventory).
Dotčeno: worker helper, frontend_flow, workspace a vlastní negativní testy.
Lokální stejnojmenný TS typ ani změněná React dependency nesmí obejít bridge.
Scope API zůstává aditivní; tato oprava nepřidává automatické inspection/build.
Finální dotčené testy po této opravě jsou uvedeny v integračním záznamu níže.

### Krok 2 — izolace request identity ve worker protocolu

Stejný baseline, AC03. Read-only parent review upozornilo na chybějící ochranu
pro vadný worker fact mezi dvěma jinak validními request chains. Validator nyní
vyžaduje shodu celého request metadata, source/target/fact path+hash, fact range
rovný target occurrence, zachování field identity a příslušné target role.
Přidány skutečné dvourequestové injekční případy cross-request/fact-range/fact-file
a byte-identical ochrana uložené generace. **PASS** JDK21/REQUIRE_WORKERS/PYTHONPATH
environment + `python -m pytest -q tests/test_backend_frontend_value_flow.py -k 'invalid_worker or actual_backend' -x`: **8 passed /19 deselected,39.29s**.
Finální veřejný test a negativy generation/cache před tím prošly s workspace/dataflow
regresí: **48 PASS /0 SKIP,54.94s**. Zdrojový audit také přidal localized gap pro
nečitelný/nepodporovaný OpenAPI capture místo neřízené práce s jeho tvarem.

### Krok 5 — integrace main po PR105

Integrační baseline `93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`, vlastní implementace
`502d2f9`, merge `0e85411`. Zachovány W03 field_mapping_bindings, kvalifikace
field-mapping symbolů i navazující capability dokumentace; konflikty byly jen
v dataflow capability seznamu, workspace qualifieru a konci compiler dokumentace.
**PASS** finální integrační JDK21/REQUIRE_WORKERS/PYTHONPATH environment +
`python -m pytest -q tests/test_backend_frontend_value_flow.py tests/test_workspace.py tests/test_dataflow.py tests/test_field_mapping_flow.py tests/test_t027_cross_http_process_boundary.py tests/test_inspection_contract.py -x`
— **95 passed /0 skipped,73.53s**.

Následná W01 regrese našla **FAIL**: obecný `if` bez response hodnoty dostal
nový frontend coverage gap a změnil COMPLETE na PARTIAL. Oprava lokalizuje tuto
diagnostiku jen na prostředí s přítomnými response hodnotami; běžné funkce bez
value toku status nemění. Dotčený worker helper, AC02/AC03, stejná integrační
baseline. Cílený opakovaný výsledek je uveden níže.

### Závěrečná ověřená matice

Všechny příkazy spuštěny v izolovaném checkoutu s
`JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64`, jeho `bin` na PATH,
`KGMAKER_REQUIRE_WORKERS=1`, `PYTHONPATH=src` a Pythonem
`/tmp/kgmaker-test-venv/bin/python` (3.12.0). Toolchain: OpenJDK21.0.13.0.3,
Node24.22.1, TypeScript5.7.3, React18.3.1, @types/react18.3.18.

- **PASS** `python -m pytest -q tests/test_tsconfig_freshness.py::test_snapshot_helper_is_hash_bound_to_distribution tests/test_worker_install.py::InstalledWorkerTests::test_packaged_typescript_analyzes_outside_checkout tests/test_typescript_project_references.py tests/test_typescript_callbacks.py tests/test_backend_frontend_value_flow.py -x` — **55 passed /0 skipped,132.81s** po opravě nepříslušného control-flow gapu.
- Dodatečný AC03 guard: reuse existujícího `dynamicScopeFiles` odmítá dynamic-eval soubory; protocol v1 fact musí zachovat očekávaný evidence kind a přesný React adapter target occurrence. Dotčeno: worker.cjs, frontend_flow.py a vlastní negativy; baseline0e85411.
- **PASS** `python -m pytest -q tests/test_backend_frontend_value_flow.py tests/test_worker_install.py::InstalledWorkerTests::test_packaged_typescript_analyzes_outside_checkout -x` — **31 passed /0 skipped,94.06s** na finálním kódu (30 W05 a clean installed TS).
- **PASS** `git diff --check` po integraci a source opravách.
- **NOT_RUN** celý test suite (výslovný targeted-only pokyn), Kotlin K1/K2 W05 matice, runtime aplikace/HTTP/UI test execution, obecné Promise/heap/control-flow podpory a GH CI.

### Sémantická evidence a zachování historie

Scoped `semantic update --base 93c52d338ea273175b9c0ed5a7a5477ae6bf2de0` +
`semantic apply` + `semantic validate` proběhly **PASS**. Reanchor ověřil původní
hashe zdrojů a mapoval jen nezměněné citované řádky; nejednoznačné IDs či změněné
citace jsou fail-closed. Přidán jediný doložený W05 concept a tři implementační/
validační vazby. **PASS preservation** obou rodičů: původní baseline42concepts/
135edges/286episodes a main45/144/299. Aktuální stav před capture:46/147/299,
žádné odstranění historických faktů nebo epizod.

Původní pre-task graph.json chyběl. Implementační paměť byla proto zachycena až
nad explicitním postintegration maintenance checkpointem; nedokládá historický
pre-task graph delta. Capture episode `0475787e39d03ca0507f0a3ca91e8366435a40ec50c12d6fff233749a61b928e`
(**PASS**) zachoval299 historických epizod a přidal jednu (celkem300).
`semantic validate`, generovaný `scan` a `status` jsou **PASS**; source graph
je current. Finální refresh po aktualizaci publikačních metadat zachová tyto kotvy.
Publikační stav: implementace dokončena v omezeném scope; samostatný PR se
předává reviewerovi, celý S08 zůstává PARTIAL.

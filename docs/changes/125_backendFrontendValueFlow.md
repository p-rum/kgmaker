# T003-S08-W05 — compiler doložený backend→frontend tok

Datum: 2026-11-15. Výchozí SHA všech níže uvedených kroků:
`d2507ef465c9b4844830520de68629a3b577c0d2`. Větev:
`feat/t003-s08-05-backend-frontend-value-flow`. Cílový main poPR105 byl začleněn samostatně; jeho SHA a integrační ověření
jsou uvedeny níže.
Task `T003-S08-W05`, nadřazená `T003-AC08`; dodání PR_OPEN,
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

### Publikace PR a finální metadata

[PR107](https://github.com/p-rum/kgmaker/pull/107), code commit
`96856d44f8681116f929a548a1b07e7bf9d5369b`, base main
`93c52d338ea273175b9c0ed5a7a5477ae6bf2de0`. Závěrečný docs commit mění pouze
publikační stav/odkazy a generované graph/semantic hash kotvy; kód zůstává přesně
ve stavu posledních31 PASS. Dodání PR_OPEN, ověření VERIFIED_IN_SCOPE.
Nezávislé review je další gate a merge provádí pouze pověřený reviewer.

Po aktualizaci metadat je znovu proveden aktuální semantic update/apply/validate
a generovaný scan; preservují se46concepts/147edges/300episodes, včetně všech
parent facts. Registry je beze změny, číslo125 nekolizní s main (max124) i
parent rezervací sousedních úloh. Původní root checkout nebyl upraven.

### Krok 6 — review P1: objektové aliasy a únik reference

Baseline `15509781f955a9c4b73cf78fd2bf4a3c8c1c8bec`, Task T003-S08-W05,
kroky 1/3/4/5, AC01/AC03/AC04. Nezávislé
[REQUEST_CHANGES](https://github.com/p-rum/kgmaker/pull/107#issuecomment-6899067284)
reprodukovalo zápis `const alias=data; alias.decline=7` a předání
`overwrite(alias)`: původní audit zneplatnil jen spelling aliasu, zatímco původní
`data` dál vytvářelo falešnou HTTP_RESPONSE→ARGUMENT cestu. **FAIL baseline**:
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/befe-review-repro.py`
(kopie nezávislého `/tmp/review107_probes.py` pouze s cestou vlastní fixture)
vypsal obě cesty `True`, bez TS errors; stejně prošla vadná publikace z kroku7.

`workers/typescript/frontend_values.cjs` nyní používá skupiny compiler bindingů
pro reference a jejich řetězce. Mutace, únik do neznámého call/receiveru, kontejneru
nebo návratu zneplatní celý původ. Podporované transparentní obaly/přetypování
nemohou odpojit skutečnou referenci. Shorthand mapping respektuje stejné guardy.
Podmíněné aliasy a nepodporované heap návraty se konzervativně odmítají.
Typ `Readonly<T>`, readonly parametr ani `const` neprokazují bezpečný escape.
Skutečně samostatné primitivní kopie se do reference skupiny nepřipojují.
Audit je flow-insensitive: může odmítnout i dřívější čtení před pozdější mutací;
neslibuje heap/control-flow ani runtime ekvivalenci.

`tests/test_backend_frontend_value_flow.py` přidává actual TS případy pro zápis,
compound/increment/delete, aliasové řetězce, wrapped/Readonly/cast escape,
kontejnery, conditional alias, receiver a návrat reference. Pozitivy ověřují
čtené aliasy bez escape, nezávislé scalar kopie i nesouvisející objekt. Veřejný
BE/FE/test snapshot odmítá cestu po mutaci/escape a zachová přesnou cestu druhého
nezměněného repo; žádný implicitní proces/síť ani mutace snapshot vstupů.

Kompatibilita: schéma ani API se nemění; nově se odstraní nesound paths pro
mutované/uniklé referenční hodnoty, s `VALUE_FLOW_CONSUMER_UNPROVEN` a UNKNOWN
availability. Staré již zachycené compiler kontexty jsou změnou distribution
hash STALE a potřebují explicitní inspection. Bez automatické instalace/rebuild.
Výsledky finální cílené matice jsou níže. První vývojový běh měl **55 PASS/1 FAIL**
(157.66s): vývoj helperu probíhal během běhu. Opakovaný stabilní běh měl **64 PASS/1 FAIL**
(181.57s) a odhalil skutečnou příčinu: sdílená module fixture po předchozím testu
změněné dependency záměrně ponechala konzervativní STALE cache entry; nový pozitivní
kontrolní consumer tedy už nebyl přítomen. Nové veřejné alias testy nyní vytvářejí
vlastní BE/FE/test checkouty s explicitními čerstvými compiler captures. Nemění
se očekávání consumeru ani invalidace cache. Oba vývojové FAIL zůstávají uvedeny;
finální stabilní běh je níže.

### Krok 7 — review P1: fail-closed volitelný protokol

Stejný baseline, Task T003-S08-W05, kroky 2/3/4/5, AC02/AC03/AC04.
`src/kgmaker/frontend_flow.py` dříve přeskočil libovolný fact bez
`value_flow_version`. Cross-request hranu šlo protlačit přes legacy větev pouhým
smazáním markeru. **FAIL baseline** nezávislého repro: `published True`,
`cross_request_path True`.

Validator rozpoznává frontend claims podle markeru, occurrence kind/identity a
role/request metadat. Každý fact dotýkající se takového occurrence musí mít
podporovanou celočíselnou verzi1 a dva validní v1 endpointy; symboly a facts se
validují odděleně. Chybějící marker, neznámá verze, smíšený legacy endpoint nebo
odstraněná role neumožní obejít request/path/hash/range/evidence kontroly.
`tests/test_backend_frontend_value_flow.py` injektuje tyto poruchy do skutečné
worker response a pro veřejné `inspect_frontend(publish=True)` kontroluje
`INVALID_PROTOCOL` a byte-identical původní `.kgmaker` store. Opravdu stará,
od v1 occurrences odpojená facts zůstávají publikovatelná; samostatná legacy
fixture to ověřuje. Graph/store v1/v2/v3 zůstává čitelný, bez migrace či změny
veřejných parametrů. Runtime/payload důkaz stále UNKNOWN.

### Krok 8 — dokumentace a kontrola review oprav

Stejný baseline, Task T003-S08-W05 krok5, AC04. README, capability
`docs/backend-frontend-value-flow.md` (včetně CLI příkladu),
`docs/compiler-inspection.md`, `docs/production-analysis-progress.md` a
`docs/acceptance-inventory.md` vysvětlují alias guard, konzervativní scope,
fail-closed marker a skutečnou legacy kompatibilitu. Registry/spec mají stejnou
identitu/revizi/závislosti, tedy bez dopadu. Instalované agent instructions a
Python templates se nemění, tedy bez dopadu; distribuovaný worker helper zůstává
ve stejném package manifestu a v content-bound kontrole. Cílený clean install
ověřuje právě aktuální zabalený helper mimo checkout. Celý milník zůstává PARTIAL.

### Krok 9 — obnova compiler evidence po vrácení dependency

Baseline opět1550978, Task T003-S08-W05 kroky3/4/5, AC01/AC03/AC04.
Parent review izolace fixture potvrdilo produktovou chybu: workspace cache
ukládala už snížený STALE graf pod source/index klíčem, který nezahrnuje vyloučený
node_modules obsah. Následné čtení tento STALE kontext přeskočilo a ani po obnovení
přesných dependency bytes nevrátilo původní doloženou cestu. Nešlo o mutaci store
ani falešné zvýšení evidence, ale o chybnou obnovu platných důkazů.

`src/kgmaker/workspace.py` nyní při STALE compiler cache entry znovu čte původní
explicitní index přes existující `current_graph` obsahovou validaci. Žádný index
se automaticky neobnovuje/spouští; stále neplatné podklady zůstanou STALE. Přesné
obnovení původních bytes může vrátit jen původní validovaný důkaz. Veřejný test
`test_ac03_cached_context_revalidates_external_package_inputs` provádí v jednom
workspace validní cestu → změnu React dependency → STALE → opakované STALE čtení
→ obnovení bytes → přesně shodnou původní cestu/edge evidence. Každý snapshot
zakazuje jiné subprocess než git a síť, porovnává všechny vstupní bytes a navíc
explicitně zachová `.kgmaker/graph.json` byte-identical. Izolované alias fixture
nenahrazují tuto regresi stejného vstupu.

**FAIL před opravou / PASS po opravě**, se stejným JDK21/REQUIRE_WORKERS/PYTHONPATH
environmentem a Pythonem uvedeným výše:
`python -m pytest -q tests/test_backend_frontend_value_flow.py -k cached_context -x`
— nejprve1 FAIL/66 deselected7.08s, potom1 PASS/66 deselected7.11s.
README, capability/CLI a progress/acceptance nyní výslovně popisují obnovu
z původního indexu; schema/API a instalované templates beze změny.

### Ověření review oprav před integrací PR106

Se stejným výše uvedeným explicitním toolchain environmentem:

- **PASS** `python -m pytest -q tests/test_backend_frontend_value_flow.py -k 'workspace_never or genuine_legacy' -x` —3 PASS/64 deselected19.57s po izolaci nových alias fixture.
- **PASS** `python -m pytest -q tests/test_backend_frontend_value_flow.py tests/test_workspace.py tests/test_dataflow.py tests/test_ui_events.py tests/test_inspection_contract.py tests/test_tsconfig_freshness.py tests/test_typescript_project_references.py tests/test_typescript_callbacks.py tests/test_worker_install.py::InstalledWorkerTests::test_packaged_typescript_analyzes_outside_checkout -x` —235 PASS/0 SKIP406.78s; včetně67 W05 případů, skutečného toolchainu a aktuálního helperu zabaleného/instalovaného mimo checkout. Běh před samostatnou cache recovery opravou, která má RED/GREEN důkaz výše a integrační regresi níže.
- **PASS** `node --check workers/typescript/frontend_values.cjs`, `git diff --check`.
- **NOT_RUN** full suite, runtime aplikace/UI, Kotlin W05 matice; uživatel výslovně požaduje pouze cílené testy. Aktuální GH CI se netvrdí jako PASS.

### Krok 10 — integrace main po PR106 a zachování sémantické historie

Baseline integračního rodiče `8e7dff5b82597184662797c07a68e5ec460e9e0e`, vlastní
review opravy `6389c8d`, původní review1550978; Task T003-S08-W05 kroky1/5,
AC01–AC04. Ranking PR106 se přebírá beze změny: `analysis_report.py`,
`callgraph.py`, `project_cli.py`, `views.py`, `test_evidence_ranking.py` jsou
byte-identical s novým main. README/progress/acceptance se spojily automaticky;
konflikty se týkaly jen sémantického artefaktu a generovaných pohledů.

Historické epizody z obou rodičů se spojily podle ID a shodného payloadu.
`semantic update --base 8e7dff5b82597184662797c07a68e5ec460e9e0e`, aktuální patch,
`semantic apply` a `semantic validate` jsou **PASS**. Patch reanchoruje pouze
nezměněné citované řádky přes SequenceMatcher po ověření původního hash obsahu
ze správného rodiče; změněné citace/nejednoznačné entity jsou fail-closed.
Zachovává původní W05 concept a jeho tři vazby vedle všech ranking/main faktů.
Žádné ruční úpravy generovaného grafu, žádné odstranění nesouvisející evidence.

**PASS** `PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/befe-review-preservation.py`:
původníbaseline42/135/286, main93c52 45/144/299, review1550978 46/147/300 a
main8e7dff5 46/151/303 zachovány; aktuálně47 concepts/154 edges/304 episodes.
Kontrola porovnává historické IDs/typy/confidence, celé immutable epizody a pro
oba aktuální rodiče celé facts kromě přeukotveného řádku/strukturálního locatoru.
Starší baseline již v main upravila summary T037 architektury; není to tato oprava
ani odstranění faktu. Generované pohledy obnovuje závěrečný `kgmaker scan`.

**PASS finální integrační matice** se stejným JDK21/REQUIRE_WORKERS/PYTHONPATH:
`python -m pytest -q tests/test_backend_frontend_value_flow.py tests/test_workspace.py tests/test_dataflow.py tests/test_evidence_ranking.py tests/test_graph_provider.py tests/test_t027_cross_http_process_boundary.py tests/test_field_mapping_flow.py -x`
— **265 passed /0 skipped205.44s**. Obsahuje všech67 aktuálních W05 testů včetně
cache RED/GREEN regrese i společné ranking/projection/workspace/flow kontroly.
Předchozí235PASS dokládá stejný finální TS helper v čisté instalaci; po něm se
měnil jen workspace cache recovery a integrace main, ověřené touto sadou.

**PASS původní nezávislé repro po opravě**:
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/befe-review-repro-assert.py`
spouští původní reviewer skript s cestou vlastní fixture, kontroluje obě
`path False`/`ts_errors []` a odmítnutí neoznačené cross-request publikace přes
WorkerError. Byte-identical zachování existujícího store dokazují veřejné
protokolové testy, nikoli tento samostatný repro.

Existující lokální pre-fix graph byl obsahově ověřen proti1550978 pro dotčený
worker/validator/workspace/test; tentokrát je tedy k dispozici skutečný pre-change
checkpoint. `memory capture --base 15509781f955a9c4b73cf78fd2bf4a3c8c1c8bec
--validation alias-protocol-and-install235=passed --validation integrated265=passed
--validation cache-recovery=passed --validation full-suite=unknown` je **PASS**:
episode `6637bfb0acf8c6dbbde6cf3fd60332212699b9595aad65e487db65c2202ade9b`.
První pokus byl bezpečně odmítnut kvůli dočasnému externímu JVM target symlinku;
po odstranění testovacího symlinku proběhl capture bez změny historických epizod.
Aktuální počet47/154/305; původních304 epizod z obou rodičů zůstává beze změny.

Závěrečné `semantic update/apply/validate`, generovaný `scan`, `status` a
`git diff --check` jsou **PASS**; graph current, žádné konfliktní značky.
Před dokončením generování diff check správně hlásil konflikty generated views;
vyřešil je příkaz scan, nikoli ruční editace. Po tomto publikačním záznamu se
znovu obnovují pouze aktuální hash kotvy a generované pohledy stejnými příkazy.
Full a aktuální GH test execution zůstávají **NOT_RUN**; nezávislé re-review
nad novým HEAD/base je další povinný krok. Implementer nemerguje do main.

### Krok 11 — integrace schváleného PR108 bez změny W05 implementace

Vlastní baseline `340a1d722811aa612bfdac8428e6923a206e25e3`, nový actual main
`9f538634807957abe1004dde43450271b77f1bb5`, rodiče main
`8e7dff5b82597184662797c07a68e5ec460e9e0e` a
`8f023bc65396f1f7feec757f78effd8a0d9c33fd`, tree
`990f9de74320da19466b8400cdb6224e3975e072`. Task T003-S08-W05 kroky1/5,
AC01–AC04; návaznost na T028/T014 pouze v procesu/remote handoff a workspace.
[Nezávislý merge audit PR108](https://github.com/p-rum/kgmaker/pull/108#issuecomment-6899650441)
uzavřel jeho dva P1 a doložil317 targeted PASS. To je upstream evidence, ne nový
běh této integrace.

Zdrojový průnik: T028 přidává `project_async_process_boundary` do
`business_process.py`; `remote_interfaces.py` přenáší explicitní Kafka
origin/subscription identitu a validuje její příslušnost k original IDs.
HTTP extra attributes tím nejsou přebírány. W05 používá workspace a stávající
contract/field evidence. Merge neměl funkční konflikt: **PASS byte identity**
W05 `frontend_flow.py`, `workspace.py`, `frontend_values.cjs` a vlastních testů
vůči340a1d7, a T028 `business_process.py`, `remote_interfaces.py` a vlastních testů
vůči9f538634. Worker helpery nebyly během paralelního reviewer běhu změněny.

README se spojilo automaticky. Progress/acceptance nyní správně uvádějí PR108
MERGED, W05 PR_OPEN a rozlišují historické PASS od nového scoped běhu. Nové
CLI parametry, API/protocol změny ani instalované instrukce/templates se
nezavádějí — capability a CLI příklady tedy bez dalšího dopadu. Task identity,
revize a dependencies se nemění, registry bez dopadu. Jediné konflikty byly
sémantický artefakt a generovaný GRAPH.md; oba se obnovují doloženým union,
aktuálním packetem/patch a generátorem, nikoli ruční editací grafu.

Sémantický union zachovává immutable epizody obou rodičů: main47concepts/
154edges/307episodes, vlastní47/154/305, společný stav před capture48/157/309.
Každá citace se reanchoruje podle svého vlastníka, po ověření jeho source hash;
nezměněné řádky přes SequenceMatcher, nejednoznačné ID nebo změněná citace fail-closed.
Žádná nová business tvrzení ani odstranění nesouvisející historie.

Cílený příkaz po této integraci (nikoli opakování235/265):

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 PATH=/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_WORKERS_HOME=/tmp/kgmaker-pr97-reconciled/workers PYTHONPATH=src:tests /tmp/kgmaker-test-venv/bin/python -m pytest -q tests/test_t028_cross_async_process_boundary.py tests/test_t014_bind_remote_interfaces.py tests/test_cross_service_contract_mapping.py tests/test_workspace.py tests/test_backend_frontend_value_flow.py::test_ac01_actual_backend_field_has_exact_ui_and_test_paths tests/test_backend_frontend_value_flow.py::test_ac03_cached_context_revalidates_external_package_inputs tests/test_backend_frontend_value_flow.py::test_ac03_workspace_never_bridges_aliased_mutable_payload -x
```

**PASS193 /0 SKIP95.11s**: T028/T014/remote handoff a workspace plus konkrétní
BE→FE/test cesta, stejný vstup cache recovery a aliasovaná payload hranice.
Skutečný JDK21/Javac/K1/K2 a TS5.7.3/React18; žádná implicitní inspection ve
snapshot cestách. Celé235/265, full suite ani nový clean install se neopakovaly:
W05 code/distribution se nezměnily. **PASS source/test/distribution identity**:
všech12 dotčených souborů W05 vůči340a1d7 a všechny3 source/test soubory PR108
vůči9f538634 jsou byte-identical. Upstream317 PASS a nezávislé review PR107
265+144 PASS jsou historické oddělené výsledky, nikoli nové běhy integrace.

[Review PR107 nad340a1d7](https://github.com/p-rum/kgmaker/pull/107#pullrequestreview-5912329170)
uzavřelo oba P1 i cache recovery bez nového nálezu; nové head/base vyžaduje nové
integrační review. **PASS** aktuální semantic update/apply/validate a
`PYTHONPATH=src /tmp/kgmaker-test-venv/bin/python /tmp/befe-main108-preservation.py`:
oba rodiče i předchozí baseline zachovány, včetně celých immutable epizod a
facts kromě doložených přepočtených locatorů. Full/runtime/GH test execution
zůstávají NOT_RUN; implementer nemerguje do main.

**PASS** `memory capture --base 340a1d722811aa612bfdac8428e6923a206e25e3
--validation integration193=passed --validation source-identity=passed
--validation semantic-preservation=passed --validation full-suite=unknown`:
aktuální integrační epizoda
`ad6e5e6e06c7f34f6a08970eddbb38ecdfec23ba7f8d555c4f75c28de36350db`, celkem
48 konceptů/157 vztahů/310 epizod. Pre-integration graph byl skutečně přítomen a
current nad340a1d7; nevyrábí se zpětná pre-task evidence. Dočasné target/target-k2
symlinky byly před capture odstraněny.

**PASS** generovaný `kgmaker scan`, `kgmaker status`, opakovaná preservation a
`git diff --check`: graf current, všechny původní epizody/facts zachovány a žádné
conflict markery. Tento poslední audit mění pouze dokumentační hash; následný
aktuální semantic update/apply/validate a scan obnovují hash kotvy stejnými
příkazy. Nový head/base se předává pověřenému reviewerovi, bez merge implementerem.

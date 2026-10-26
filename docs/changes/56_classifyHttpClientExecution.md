# HTTP request definition versus static execution intent

T003-S07-W06, AC01–AC04; implementační plán, nikoli dokončení S07/T003.
Explicitní combined base `c7beaec95951267796c0c21baa6079fafe5fe124` má rodiče
PR35 `89e50cf4cf8edbebc4f9d08879656698c75ebd50` a PR34
`78d7968ea7408adea3ec9ce783769bb799522470`. Feature patří pouze do samostatné
větve feat/t003-s07-06-http-client-execution; target je oddělený prereq stack.

Před feature kódem byl ověřen independent architecture brief a actual RED se
skutečnými Spring6.2.2/Reactor3.7.2 API: 5 compiler-attributed calls,
0 cold request definitions; očekávané selhání assertion. Javac neměl chyby a
neproběhlo žádné HTTP volání ani spuštění aplikace. Reused K1 source je identický
ověřenému PR35; combined K2 a ostatní prereq proof jsou zaznamenané v change44.

Cíl je oddělit definition, typed same-origin terminal a runtime availability.
WebClient publisher je cold; retrieve/bodyToMono/exchangeToMono nejsou trigger.
Pouze doložený same-origin Reactor terminal znamená statický execution intent,
nikoli skutečný runtime request či dostupná data. RestClient retrieve samo nestačí;
Feign default/static/custom methods nejsou proxy HTTP proof. Escaped/returned/
stored/passed publisher a neověřený helper/operator zůstane UNKNOWN.

Nová projection bude pure nad stávajícím modelem/IR/evidence. Java literal/local
binding fakta budou aditivní, ne odhad z masked labels. Config key/file hash/profile
provenance musí být explicitní; URI credentials nesmí skončit v identities,
metadata, contexte ani persistent source-only reference. Nepodporovaný proof se
nevymýšlí. K1/K2 Kotlin bez potřebných IR facts zůstane konkrétní UNKNOWN.

Skutečné změny, kompatibilita, pinned API/license fixture, přesné test commands a
výsledky budou doplněny podle dodaného kódu a provedených kontrol. Zatím nejsou
pro HTTP feature tvrzené nové PASS výsledky. Remote CI billing zůstává pozastavené;
žádný Draft merge bez povinných zelených gates není autorizovaný.

## Dodaný lokální kontrakt a kompatibilita

Implementace používá stávající Node/Edge/evidence/graph/store3; nepřidává parallel
catalog ani value propagation do jiné služby. JavaFrontend poskytuje aditivní
compiler literal a source-location binding ID, explicitní capture/reference proof;
K1 i K2 distribuce sdílejí stejný Javac frontend. Staré workery bez těchto optional
facts, staré compiler kontexty a graph/store1/2/3 zůstávají čitelné; HTTP coverage
bez nové rule version je UNKNOWN. Malformed nové IR facts se odmítnou před zápisem.

Pure `http_execution` projection rozlišuje definition/closed unused publisher,
static/conditional terminal a Feign invocation intent. Každý publisher má vlastní
origin, takže terminal jiného publisheru ze stejného request spec jej neaktivuje.
Return/store/pass/capture/unknown operators a unsupported switch nevymýšlejí
execution. Neznámá URI reconfiguration nezachová předchozí konkrétní route.
Kotlin K1/K2 bez potřebných binding facts vydá HTTP_TYPED_IR_UNAVAILABLE/UNKNOWN.
Read inventory se promítá do integrations/data-flow JSON a process JSON/Markdown;
workspace kvalifikuje IDs a source locators, nikoli URI route string.

URI userinfo/query/fragment se redaktují před persistencí včetně explicitního
kontextu a staré SOURCE_ONLY reference. Opaque hash zachovává freshness. Config
mapping vyžaduje explicitní matching properties/profile/source SHA; plain string
placeholder, YAML/SpEL/default/nested placeholder či hodnoty bez provenance zůstávají
UNKNOWN. `runtime_execution=NOT_OBSERVED`, `runtime_availability=UNKNOWN` vždy.

Fixture explicitně připravuje API Spring6.2.2, Reactor3.7.2 a OpenFeign4.2.0,
nikoli application/client. Lock obsahuje SHA skutečných JARů a publikovaných POMů
plus jejich license name; JARy se nevendorizují. Povinný Linux compiler CI job
explicitně kompiluje API fixture a zahrnuje HTTP test module. Remote gate nebyl
spuštěn kvůli již potvrzenému Actions billing blockeru; nic nebylo mergováno.

## Lokální kontroly (source frozen, full pending)

Env: `PYTHONPATH=/workspace/http-execution/src`,
`KGMAKER_WORKERS_HOME=/workspace/http-execution/workers`,
`KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2`,
`KGMAKER_REQUIRE_WORKERS=1`, `KGMAKER_REQUIRE_K2=1`, JDK21.0.6/Kotlin2.1.10,
Python `/workspace/kgmaker-venv/bin/python`. K1/K2 build sekvenčně a focused/full
pod `flock /workspace/kgmaker-heavy-tests.lock`, runner `/tmp/http-final-validate.py`.

- Před implementací actual RED: `tests/test_http_client_execution.py` původní2
  parametrizované případy **2 FAIL13.60s**, chyběly cold definitions; žádný Javac
  error ani HTTP/app execution. Rozšířené průběžné kontroly zachytily missing
  Kotlin boundary diagnostic a přísný validator odmítající legitimní null binding;
  obě chyby opraveny před finálním runem. Jeden nový URI test původně volal
  metodu na chybném API návratovém typu; opravena fixture, nikoli obcházen compiler error.
- `python workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7` **PASS14.07s**.
- Totéž `--backend k2 --analysis-api-home /workspace/tools/k2-verified` **PASS12.36s**.
- `python -m pytest -q tests/test_http_client_execution.py tests/test_worker_protocol.py tests/test_control_flow.py tests/test_dataflow.py tests/test_workspace.py tests/test_mandatory_worker_ci.py --maxfail=1` **85 PASS40.22s**; tehdejších26 HTTP případy včetně skutečných K1/K2 API a negative/legacy/privacy/store.
- K1 runtime SHA256 `14eddbf8f31011c22a144e67552706268daa3138ca71993fd638d70a556f026b`;
  K2 `3c84080730333731611f42dbacd91a1bf3f75b863f045de715be73fc3828a0b3`.
- `python -m compileall -q src/kgmaker`, `git diff --check` **PASS**.
- Bounded semantic update/apply/validate/CLI scan: **PASS**, původních7 concepts/25
  relations zachováno, přidán1 HTTP concept/4 doložené relations; scanner ownership
  target275 a Javac staticness citation112 aktualizovány. Všech119 původních memory
  episodes zatím byte-identických; feature capture proběhne po final full.

Full aktuálního frozen source běží, proto zatím není pro něj tvrzen PASS. Přesný
výsledek, memory capture a final CLI check budou doplněny po dokončení. Remote
mandatory CI, skutečné HTTP/runtime response a celý S07/T003 nejsou ověřené.

První whole-suite run byl vědomě přerušen po **1 FAIL / 330 PASS / 7 SKIP,
449.35s** (`/tmp/http-interrupted-full.log/.xml`). Starý
`test_sensitive_headers_urls_and_property_defaults_are_redacted` vyžadoval
ponechat `safe=1` query; nový HTTP privacy kontrakt záměrně odstraňuje celý URI
s userinfo/query/fragment včetně hodnot, jejichž citlivost nelze staticky ověřit.
Expectation tohoto testu byla aktualizována na `<redacted-uri>` a nepřítomnost
query. Produktový source ani oba worker runtimes se nezměnily. Následuje contract+
HTTP/relevant focused a nový celý run `/tmp/http-retry-full.log/.xml`, nikoli
povýšení přerušeného runu na PASS. Testovací runner typo před retry neodstartoval
žádné testy; opraven před spuštěním skutečného retry.

Retry contract+HTTP/relevant focused: **86 PASS41.96s**, bez změny workerů či
produktového source. Whole retry však zaplnil oddělený `/tmp` tmpfs4.9GiB;
pytest skončil exit1/392.15s, sessionfinish/JUnit write hlásí Errno28 a XML má
0 bytes. Tento run není validní evidence PASS ani spolehlivý per-test count.
`df` doložil `/workspace`23GiB free versus `/tmp`32KiB free. Jen vlastní již
ukončené pytest-545/547 artefakty byly přesunuty do `/workspace` a zachovány;
žádné cizí pracovní stromy ani source se neměnily.

Další final run používá `/workspace/http-validation-final/run.py`,
`TMPDIR=/workspace/http-validation-final/tmp`, explicitní pytest basetemp a
persistent log/XML na `/workspace/http-validation-final/full.log`/`full.xml`.
Read-only prerequisite preflight **PASS0.04s**, skutečný K1 cold/terminal smoke
**1 PASS2.63s** (runner2.84s), obě runtime SHA jsou nadále stejné. Fresh full
běží pod týmovým flock; finální výsledek bude zaznamenán bez přejmenování
předchozích přerušených/ENOSPC runů na PASS.

Při závěrečném source privacy auditu byl actual SOURCE_ONLY scan s Kotlin default
URL reprodukován jako leak v raw Node.signature (sourcePass/sourceQuery byly
přítomné). Předchozí full byl proto zastaven jako **159 PASS / 2 SKIP196.37s**,
nikoli PASS celé sady. Následný úzký fix aplikuje stejnou privacy transformaci na
persistované scanner signatures/doc summaries a Markdown heading name/ID, včetně
quoted relative URI defaults; nejde o odvozování HTTP významu ze source labels.
Nový scan/save/load/generated-docs regression zakazuje Popen a s contract testem
**2 PASS0.07s**. JVM source i runtime SHA zůstaly stejné. Final runner je nyní
`/workspace/http-privacy-final/run.py`, source manifest109 files a persistent
focused/full log/XML jsou ve stejném adresáři; temp storage je výhradně spacious
workspace. Nový read-only prerequisite preflight **PASS0.06s**.

Finální focused po SOURCE_ONLY privacy fixu: `tests/test_scanner.py`, `test_inspection_contract.py`, `test_http_client_execution.py`, protocol/control-flow/dataflow/workspace/mandatory-CI **108 PASS43.53s**, včetně všech27 HTTP případů. Whole aktuálního source běží; předchozí výsledky zůstávají historické.

Read-side acceptance kontrola našla a actual testem potvrdila další úzkou mezeru:
Feign definition patří abstraktní deklaraci, ale process filter hledal jen tuto
`metadata.caller`, takže consumer process nezobrazil prokázaný call-site intent.
Přidaný assertion v původní skutečné Feign fixture **RED1 FAIL3.10s**. Inventory
nyní vybírá také podle caller originů terminal call-sites; unused declaration se
nepřidává jako execution. **GREEN1 PASS2.16s**. Předchozí source full byl zastaven
**184 PASS / 2 SKIP311.54s** před úpravou, nikoli vydáván za konečný PASS.

Aktuální final runner/log/XML/manifest jsou `/workspace/http-final-proof/`,
`run.py`/`full.log`/`full.xml`/`source-manifest.json`; read-only prerequisite
preflight **PASS0.05s**. Worker zdroje a SHA jsou stále identické, změnil se jen
pure read-side filter a jeho actual regression. Scoped semantic preserve8/29 a
119 immutable episodes byl znovu validován; scanner target258, HTTP prepare78,
HTTP augment548, workspace ownership275 a Javac citation112 odpovídají source.
Zde ještě není tvrzený full PASS; po dokončení následuje přesný výsledek a capture.

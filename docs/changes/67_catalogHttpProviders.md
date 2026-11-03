# Katalog deklarovaných HTTP providerů v explicitním service realm

Datum: 2026-10-27. Task [T010](../tasks/T-010_catalog-http-providers.md), AC01–AC06.
Větev `feat/t010-catalog-http-providers`, worktree `/workspace/t010`, výchozí
source checkpoint `cbf17b1d57719c05c4e918851647c375811e8b07` z explicitní dependency
Draft PR48 (T009). T009 source je nezávisle reviewed; parent mezitím sloučil finální T009 po opravě
explicitních testových jsonschema prerequisites v obnoveném CI. Stabilní merged
main bude převzat po tomto validním full běhu, nikoli při něm. Původní GitHub
Actions billing/quota blokace skončila po uživatelově upgradu; nové T010 CI
jsou nyní dle orchestrátora znovu billing-blocked; žádný remote PASS se nehlásí. Note67 rezervoval orchestrátor.

## Rekognoskace a skutečný problém

Převzat a ve zdrojích/graph/query ověřen architect brief: T008 explicit ownership
selection, T005/T009 ViewDocument a evidence agregace se znovu použijí. Domain API
node ID globálně lowercasuje route a sdílí ji napříč deklaracemi. Proto samotný
api_endpoint není dostatečný provider identity ani důkaz originální route.
Přidána aditivní bounded registration metadata k existujícím API uzlům; jejich
legacy identity se nepřejmenovávají. Zachovány samostatné source path/SHA/line,
method/class route components a opaque registration/contract variant fingerprints.
Nekopírují se annotation/config bodies, credentials ani URL query/userinfo.

Nový `interfaces.project_http_providers` je čistá projekce nad explicitním
workspace/provider snapshotem. Service realm, HTTP method a case-preserving route
určují logical operation; registration a contract variant identity zůstávají oddělené.
OpenAPI declaration nepřechází na implementation/deployment/runtime proof.
Heuristický Spring/Ktor zůstává syntax/SOURCE_ONLY; typed compiler class/method
mirrors se mohou skládat pouze s přesným owner/context důkazem. Neznámý prefix,
placeholder, scope/context či ownership se nedopočítává.

## Skutečné průběžné testy před dokončením

- Před runtime editací actual workspace/metadata acceptance: **6 FAIL**,0.41s,
  `/tmp/t010-baseline-red.log/.xml`. Case/variant údaje se ztrácely a API projekce
  neexistovalo. První source-only cesta: **6 PASS**,1.10s.
- Structured metadata/hash/edge binding a URI/query negatives: nejprve
  **7 FAIL /2 PASS**,0.77s; po opravách **15 PASS**,1.14s. Opaque fingerprints
  rozlišují sanitizované varianty, aniž nesou původní secret/query text.
- Scanner/scope/T008/T009 regrese: **75 PASS**,1.15s,
  `/tmp/t010-source-regression.log/.xml`.
- Po refaktoru společné emit cesty a typed guards: **15 PASS**,2.70s,
  `/tmp/t010-typed-guards-green.log/.xml`.
- Actual JVM/Spring6.2.2 compiler případ byl připraven před compiler projection
  implementací. Pinované API jars jsou z explicitní cache, vlastní trusted K1
  artifact až po byte porovnání JVM sources/builderu/locků; žádný download,
  implicitní build ani instalace. Live compiler **1 PASS**,4.20s.
- Autoritativní actual RED je izolovaná kopie
  `/workspace/scratch/t010-compiler-baseline`: cwd/PYTHONPATH/tests i fyzické
  worker/API classpath soubory patří této immutable kopii bez compiler projection.
  Runner ověřil module path, nepřítomnost compiler helperu a Manifest Class-Path;
 141 souborů má totožný before/after SHA manifest. **1 FAIL**,3.32s,
  `/tmp/t010-compiler-isolated-red.log/.xml`, manifests
  `/tmp/t010-frozen-baseline-before.json` a `...-after.json`.
  Kvůli pořadí heavy fronty běžel tento RED až po live GREEN, ale immutable
  baseline source/tests byly zkopírovány a zahashovány před compiler editací.
  Starší frozen-Python/live-worker RED ani chybný runner preflight nejsou náhradou
  tohoto plně izolovaného důkazu.
- Unrelated-source identity regression nejprve skutečně FAIL, po opravě stabilní
  logical/variant IDs. Rozšířená source/workspace sada **22 PASS**,1.61s,
  `/tmp/t010-expanded-source.log/.xml`. Dvě služby v jednom repo sdílí upstream
  endpoint node, ale mají dva logical interface IDs; oddělené contract revisions
  nepřecházejí na handler binding.
- Runtime-boundary fixture je pouze negativní model (nikoli execution): existující
  edge/evidence kind nebo metadata tag bez lifecycle bindingu nesmí povýšit
  source evidence. Před explicitním diagnostickým fallbackem **1 FAIL /1 PASS**,
 0.39s; po opravě final focused **25 PASS**,17.63s,
  `/tmp/t010-final-focused.log/.xml`. Obsahuje actual compiler class/method
  composition RESOLVED/CURRENT a foreign/dangling context reject bez mutace.
- Mandatory compiler CI nyní explicitně připravuje nový Maven API fixture
  (Spring6.2.2 včetně spring-web) a spouští oba T010 test files s
  `KGMAKER_REQUIRE_HTTP_PROVIDERS=1`. Nepřipravený worker/jar v této cestě FAIL,
  nikoli SKIP; SHA mismatch je assertion chyba, nikoli optional prerequisite.
  Cache default je portable `~/.m2/repository`; lokálně explicitně tools/m2.
  Rozšířená T010 + mandatory-worker-CI sada **40 PASS**,8.04s,
  `/tmp/t010-ci-focused.log/.xml`. Původní queued full byl ukončen před spuštěním
  testovacího child a znovu zařazen po této test/CI opravě; runtime bytes stejné.
- Source review odhalilo fail-open no-local-class-mapping větev: chybějící
  superclass metadata byla brána jako prázdná známá hierarchie. Public projection
  test odvozený ze skutečného compiler graphu nejprve **1 FAIL**,12.26s,
  `/tmp/t010-partial-hierarchy-red.log/.xml`. Po odstranění implicitního `[]`
  je missing/null/object/nonstring i explicitní cizí superclass prefix UNKNOWN;
  explicitní root `java.lang.Object` připouští prázdný prefix. Přímý typed class
  mapping zůstává podporován. Projection ani při těchto chybách nic nemutuje.
  Nejnovější T010/mandatory-CI focused **40 PASS**,19.29s,
  `/tmp/t010-hierarchy-focused.log/.xml`; předchozí40PASS je intermediate source.
  Vlastní stále čekající full byl zrušen bez spuštěného pytest child a znovu
  zařazen až po této opravě a novém source SHA manifestu. Žádný validní aktivní
  run nebyl měněn; další runtime source je frozen.
- Historický full před owner/binding opravou doběhl **590 PASS /10 SKIP**,
 381.34s. `/tmp/t010-pre-owner-full.log/.xml` a source SHA manifest jsou zachovány.
  Tento výsledek není finální source acceptance: source review poté potvrdilo
  None==None owner spojení, neověřený method path a další partial tuple/proof mezery.
- Kompletní actual-derived binding RED **1 FAIL**,22.53s,
  `/tmp/t010-complete-binding-red.log/.xml`. Oprava ověřuje canonical symbol a
  veřejný Node přes id/kind/name/signature/path/scope/line/SHA/context, přesný
  neprázdný owner method/class, endpoint/edge/proof source/target/relation/context/
  file/line/rules a případný proof SHA. Chybějící či rozporné class proof dává
  UNKNOWN, nikoli složenou route; nested lokální Node.metadata nenahrazují
  canonical Graph.symbols. Empty prefix bez místního mappingu vyžaduje konzistentní
  kompletní `type_hierarchy` a explicitní root superclass. Známé endpoint method/
  path nesmí odporovat compiler variantám. Actual positive root/default path,
  multipath a multimethod varianty zůstávají podporované. Rozšířený actual test
  **1 PASS**,53.28s, `/tmp/t010-boundary-audit-green.log/.xml`.
- Skutečné CRLF Kotlin/Java/OpenAPI JSON/YAML vstupy nejprve **4 FAIL**,0.59s,
  `/tmp/t010-crlf-red.log/.xml`: scannerův normalizovaný text hash nebyl raw byte
  SHA workspace snapshotu. Nový bounded capture čte jednou nejvýše limit+1 byte,
  zachová dosavadní universal-newline text i legacy normalized graph hashes/IDs,
  raw SHA předá explicitně jen novým HTTP recordům. Snapshot recheck porovnává
  text i raw SHA; LF↔CRLF race je odmítnuta a poslední uložený graph zůstane stejný.
  Původní meaningful mixed-source test nyní patchuje skutečný capture seam.
  Workspace cache používá aditivní HTTP capture version ve stávajícím parser key,
  takže starý normalized/missing metadata cache není skrytě znovu použit. Žádný
  hash se nedoplňuje zpětně z graphu, žádný source IO není přidán do projekce.
  Source/scanner/scope/workspace/cache sada **79 PASS**,8.89s,
  `/tmp/t010-capture-cache-focused.log/.xml`.
- Další AC05 skutečný probe odhalil pořadí kontrol: unselected STALE capture
  s historickým source SHA zastavil validní explicitně zvolený CURRENT context.
  Vlastní full byl bezpečně ukončen SIGINT a child/flock ověřeny jako ukončené
  před editací; **257 PASS /7 SKIP**,315.30s je jen interrupted partial, uložený
  `/tmp/t010-pre-selection-partial.log/.xml`, nikoli full PASS.
  Public actual-derived selection regression nejprve **1 FAIL**,61.38s,
  `/tmp/t010-selection-red.log/.xml`, poté **1 PASS**,55.66s,
  `/tmp/t010-selection-green.log/.xml`. T008 selected/requested context ID filter
  nyní předchází čtení silných per-context bindingů. Nezvolené STALE/CURRENT sibling
  captures zachovají proof refs/diagnostics; bez explicitní volby zůstane ambiguity
  UNKNOWN. Explicitně zvolený hash mismatch se stále odmítne fail-closed.
- Mandatory same-line overload probe následně odhalil skutečné duplicate view ID:
  actual Javac methods `same()`/`same(int)` a druhá class metoda na stejném řádku
  sdílely původní route/mapping/line fingerprint. RED **1 FAIL**,6.78s,
  `/tmp/t010-overload-red.log/.xml`. Vlastní known-invalid full byl ukončen před
  editací; child/flock ověřen ukončen, partial **148 PASS /2 SKIP**,410.64s
  zachován `/tmp/t010-pre-overload-partial.log/.xml`, není full PASS.
  Canonical owner/name/descriptor nyní rozlišují registration varianty; descriptor
  shape se pouze validuje, nic se neparsuje na jiný symbol ani nepřepisuje.
  Chybějící/malformed signature zůstává UNKNOWN diagnostic s původními refs.
- Root review skutečně ověřilo i posun řádků ve stejném controlleru: RED **1 FAIL**,
 67.34s, `/tmp/t010-line-shift-red.log/.xml`. Canonical compiler declaration
  identity nyní neobsahuje source path/line ani snapshot handler/context IDs.
  Path/line/hash/context jsou provenance; source-only či unknown-owner expressions
  bez canonical declaration identity ponechávají přiznaný locator boundary.
- Kompletní actual grouped matrix **1 PASS**,59.71s,
  `/tmp/t010-complete-identity-green.log/.xml`: tři same-line handlers mají různé
  varianty/jeden logical operation; class+method prefix/array a multimethod varianty;
  inherited/custom prefix UNKNOWN a explicit local override;81kombinací omezeno
  na64 s viditelným truncation; všechny tuple/metadata/selected-sibling negatives.
  Skutečná reinspekce obou repo po přidání unrelated source i po comment prefixu
  zachová všechny compiler logical/variant IDs včetně dynamic/truncated případů,
  zatímco snapshot handler IDs se mění a source_line provenance roste o2.
  Přesun controller souboru uvnitř explicitně vlastněného modulu rovněž zachová
  IDs a aktualizuje source provenance. Žádný aplikační runtime nebyl spuštěn.
- Final combined focused (stejná145case sada) **145 PASS**,87.81s na renewed frozen
 10file manifestu `/tmp/t010-binding-source-frozen.json`, log/XML
  `/tmp/t010-pre-full-focused.*`. Předchozí145PASS54.43s je pre-line-shift
  intermediate; current-source closure potvrzena root i independent architect review nad totožným10file manifestem.
- Plánovaný fresh final full: `flock /workspace/kgmaker-heavy-tests.lock env
  PYTHONPATH=/workspace/t010/src JAVA_HOME=/workspace/tools/jdk-21.0.6+7
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH
  KGMAKER_WORKERS_HOME=/workspace/t010/workers
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 KGMAKER_REQUIRE_WORKERS=1
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 KGMAKER_REQUIRE_HTTP_PROVIDERS=1
  /workspace/kgmaker-venv/bin/python -m pytest -q -rs
  --junitxml=/tmp/t010-final-full.xml`. Current-source strict full **596 PASS /10 SKIP**,479.68s, exit0,
  `/tmp/t010-final-full.log/.xml`. Všechny10 frozen source/test/CI/fixture hashes
  jsou before/after totožné (`/tmp/t010-final-source-before.json`/`...-after.json`).
  Mandatory WORKERS/K2/SPRING_IMPORTS/HTTP_PROVIDERS=1 brání toolchain skip v této
  podporované matici;10SKIP je výhradně volitelný Maven/Gradle exporter/second-JDK/
  Kotlin2.2.20 cache a native Windows gate mimo T010. Staré590/10 ani partial257/7
  a148/2 nejsou náhradou tohoto výsledku. Prepared prerequisites PASS;
  žádný implicitní build/download/install. Nové Actions jsou dle orchestrátora znovu
  billing-blocked; žádné CI retry/bypass ani tvrzení remote PASS.

## Integrace skutečného main po source proof

Po full596/10 byl vytvořen lokální checkpoint3e9b6fb a sloučen skutečný main
`ec333966e657896382f310ef018835e3d696513e` (PR35 plus již merged T009/TS/T015).
Všech7 vlastních runtime/test souborů je byte-identical s tímto validovaným
checkpointem. Konflikty zachovaly oba dokumentační bloky, všechny povinné CI testy,
obě HTTP/data API fixture přípravy i Windows/jsonschema gates. Main immutable
134episode prefix a vlastní původní episode jsou beze změn; current facts union
11concept/28edge s aktuálními README/architecture/scanner citations.

Main přinesl jiný trusted JVM worker source. Před lokální kopii připravených K1/K2
artifactů z `/workspace/dependency-dispatch` HEAD10ad319 bylo porovnáno všech14
tracked JVM source/builder/lock souborů s integrovaným checkoutem; jar SHA po kopii
jsou totožné s donor artifacty. Doklad `/tmp/t010-integrated-worker-copy.json`,
prepared prerequisite preflight PASS. Nejde o implicitní install/build ani použití
starého workeru z editable parent resources.

Relevant integration suite **199 PASS**,167.32s, bez SKIP:
`/tmp/t010-integrated-focused.log/.xml`. Zahrnuje celý T010 actual grouped matrix,
source/context/ownership/snapshot/cache/scanner/T009/T015 a critical actual TS owner,
redirect, negative lookup, extends a callback tests. Použit vlastní PYTHONPATH a
worker home, JDK21, mandatory compiler flags. Neopakoval se celý full jen kvůli
nezávislé main integraci bez změny vlastního runtime;596/10 je přesně standalone
frozen source proof a199 je current-main integration proof, nikoli tvrzení nového
celého merged full. Scoped semantic/validated memory a command-generated graph
budou součástí finálního local merge commitu. Exact Git-pair review zůstává povinné; GH CI je podle následného výslovného
pokynu uživatele volitelné při splnění všech ostatních kontrol. Actions stav se
uvádí pravdivě, žádné retry/bypass ani falešné CI PASS.

## AC → konkrétní test

- AC01: `test_ac01_same_post_route_in_two_real_services_stays_separate`,
  `test_two_services_in_same_repository_do_not_share_global_endpoint_identity`.
- AC02: `test_ac02_openapi_contract_only_never_becomes_implemented`,
  `test_contract_revisions_stay_separate_without_automatic_handler_binding`.
- AC03: `test_ac03_dynamic_class_prefix_remains_unknown_without_fake_url`, actual
  `test_actual_spring_class_method_mirrors_preserve_handlers_and_route_case`.
- AC04: `test_invalid_registration_is_structured_and_preserves_all_inputs`,
  `test_ac04_05_pure_projection_preserves_inputs_and_excludes_test_routes`.
- AC05: explicit-test-scope, foreign-context, missing-ownership, legacy-metadata,
  consumer-only a runtime-named/unbound-edge tests ve stejném veřejném test file.
- AC06: README library example, architecture guide, acceptance/status matrix,
  tento český note; strict full596/10 lokálně PASS; main integration199 PASS; finální exact Git-pair review/remote CI zůstávají PENDING.

## Hranice a zbývající práce

Coverage zůstává PARTIAL/UNKNOWN. Projekce neumí bindovat imported runtime record
na přesný HTTP registration variant/lifecycle: zachová source/target/context a
original evidence IDs v `HTTP_RUNTIME_BINDING_UNKNOWN`, bez event payloadů nebo
odvozeného route joinu. Nezavádí importer ani nové runtime schema. Runtime,
deployment i data availability zůstávají UNKNOWN; reálný aplikační runtime test
NOT_RUN. Compiler fixture je statický compiler důkaz, nikoli spuštění aplikace.
Framework/source varianty zůstávají oddělené, API contract s handlerem se automaticky
nespojuje. Custom/inherited annotation resolution a úplná OpenAPI YAML grammar
nejsou podporovány; neznámý prefix/placeholder se nedopočítává.

Veřejný příklad: `from kgmaker.interfaces import project_http_providers`;
`document = project_http_providers(workspace, graph, scope="production",
source_coverage=coverage)` nad explicitním `snapshot_workspace`/`load_workspace`.
Žádný nový CLI příkaz. Graph v1/v2/v3 loader i legacy IDs zůstávají, metadata v1
jsou aditivní; starý sloučený endpoint bez metadat je diagnosticky UNKNOWN.

Strict full596/10 PASS na frozen source. Scoped semantic update/apply/validate
PASS: původní aktuální8concept/19edge facts jsou zachovány včetně1doloženého HTTP
concept/implements edge, scanner function ID a README citations rebind podle
skutečného graphu/textu. Immutable112episode base prefix beze změny; nový validated
implementation episode `episode:d9c4a36a2276f7012c7f08a8a4182603c7450d4e4f581daa0d6a73b2e73e25d4`.
Command-generated scan/check i diff-check PASS (326files/3125nodes/21422relations).
Main integration199 PASS; finální exact Git-pair review/CI dosud PENDING. T003-S07-W08 ranking není dokončen a projekce jej neimplementuje.
HTTP consumers, remote bindings, nový store/resolver, architektura CLI/diagram
rendering a T004 jako celek nejsou scope tohoto PR.

## Obnovení prostředí a zachování auditní hranice

Po restartu prostředí 2026-11-03 zůstaly zdroje i rozpracovaná integrace na disku.
Dočasné `/tmp/t010-*` logy, XML a kopírovací receipt již nejsou dostupné. Výsledky
596/10 a199/0 výše jsou historické skutečné běhy zaznamenané před restartem;
nejde o nově přečtené či znovu provedené běhy. Všech sedm vlastních runtime/test
souborů zůstává byte-identických checkpointu3e9b6fb. Nový read-only resume audit
ověřuje semantic validate, scan/check a diff-check. Nezávislý reviewer rozhodne
o dostatečnosti zachované evidence; ztráta dočasných logů se nezatajuje.
GH CI je dle nového výslovného pokynu uživatele nepovinné při splnění ostatních
kontrol; lokální acceptance/toolchain ani review se tím nenahrazují.

## Integrace revize merge pravidel

Před publikací byl integrován policy-only main
`54a3e01c7bcb1295973655d72b58a14e6a5d597d`. Vlastní runtime/test zdroje zůstávají
byte-identické checkpointu3e9b6fb; není důvod opakovat full kvůli dokumentům a
agent profilu. Nový main immutable episode prefix je zachován přesně, child
episodes připojeny beze změn. GH CI zůstává pozorovaná doplňující evidence;
lokální acceptance, toolchain a nezávislé exact-pair review jsou povinné.

## Integrace compiler JPA parenta

Před finálním review byl integrován main
`966948b533a7a9417dea370733f300f91fd2b61c` obsahující JPA PR32. Vlastní sedm
T010 runtime/test souborů se nemění. Všech14 tracked JVM source/builder/lock
souborů je totožných se skutečně sestaveným JPA checkoutem7819193. Kopie K1/K2
a pinned libraries ověřila původní build receipt, hash každého dependency a JAR
(e44e3dac / e2553425); persistent doklad `/workspace/t010-jpa-worker-copy.json`.
Nejde o pouhou shodu nově mergnutého source s neprokázaným starým JAR. Další
integrační actual fixture rozhodne reviewer; historický full se nepřepisuje.

## Integrace explicitního process modelu

Current main b78d2e62148f225be7ba8c53c839f8b052ee269d přidává nezávislý čistý
T023 model. Je převzat beze změny; HTTP runtime/tests zůstávají3e9. Před finálním
review následuje jediný bounded actual HTTP/JPA/dispatch focus a pure process
regrese. Nejde o nový full suite ani rozšíření scope HTTP projekce.

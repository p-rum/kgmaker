# Return výraz a call-result do consumer použití

T003-S07-W02 AC01–AC04, explicitní stack na PR47
`e1487098632cd90892be3760f30676560e15d062`. Implementační plán, nikoli hotový S07.
Před implementací source/graph/native recon ověřil stávající W01 value argument
nodes a žádné typed return-consumer facts. Java/K1/TS mají return/assign/call IR,
ale chybí binding/projection identities. K2 Kotlin nemá source CFG a zůstane UNKNOWN.

Reuse model/store/context/evidence a graph1/2/3, optional typed IR/protocol metadata;
žádný parallel catalog, source-label inference ani runtime value observations.
Actual branching/nullable/chained/destructure RED, skutečné toolchain positives
plus ambiguity/ref/void/opaque/recursive negatives, focused/full, scoped semantic,
memory a přesné výsledky budou doplněny podle skutečně dodaného kódu. Note66 je
rezervována rootem; žádné CI retries, merge nebo externí publikace autorem.

## Dodaná implementace a dosavadní ověření

Optional `return-consumer-ir-v1` používá skutečné Javac/K1/TS typy, declaration
bindings a source ranges; existující model/value nodes a versioned `returns_to`
evidence propojují assignment, argument, receiver a deklarovaný návrat. Branch
alternativy, nullable safe-chain a jednotlivé zápisy zůstávají oddělené. K1 generated
data-class components a přímé TS tuple/object literal bodies mají projection proof;
custom component/opaque dispatch, recursive/async/callable/void/any/unsupported CFG
zůstávají UNKNOWN. K2 Kotlin bez source CFG nevymýšlí bindings.

Process JSON/Markdown, data-flow a impact přenášejí static proof; workspace kvalifikuje
identity. Legacy graph/store1/2/3 se čtou, explicitně stará verze pravidel je STALE
offline. Invalidní IR se odmítá před publikací a bez změny store. Nevzniká runtime
value ani execution observation; aplikace, síť a instalace se nespouštějí.

Skutečná RED sada: 4 FAIL za 28.40s před implementací. Aktuální vlastní toolchain
build: K1 PASS22.14s, K2 PASS13.52s; sequential build logs v
`/workspace/return-consumer-proof`. Nový modul: 25 PASS50.15s; průběžná integrace
67 PASS63.94s a protocol/control/mandatory-CI35 PASS2.01s. Plná aktuální sada je
zařazena pod sdíleným flock; výsledek bude doplněn, dosud není tvrzen PASS.

Příklad: po explicitní inspekci `kgmaker flow render --root . --entry '<method-id>'
--view process --format json` vrací call blocks s `return_consumer_bindings`.
Fixture `fixtures/return-consumer` a `tests/test_return_consumer_flow.py` dokládají
AC01–04 v této omezené matici. S07/T003 jako celek nejsou dokončeny; remote CI je
pozastaveno kvůli billing limitu a autor neprovádí publish/merge.

## Review: mutable TypeScript body boundary

Review nad064da2b odhalilo mylný original-body join u mutable TS static/soft-private
method. Vlastní full byl cíleně přerušen:239 PASS2 SKIP403.86s, NENÍ final PASS.
Dvě skutečné member regression byly RED; třetí původní top-level test odhalil
nepodporovaný top-level IR a byl opraven na skutečné function-body callsite.
Nová sada static/soft-private/lexical-reassignment negatives a nezměněný lexical/
ECMAScript #private positive:5 PASS20.51s před přidáním explicitního reason fieldu.
TS body joins nyní ignorují JVM static/private modifiers; ordinary members jsou
OPEN, lexical function se zjištěným compiler-bound assignment target také. Bez heap
resolveru; typed caller result/consumer contract zůstává oddělený.

Stejná kontrola prokázala namespace export function jako mutable property přes
`alias:any`;7f1b345 focus byl před dalším full přerušen54 PASS45.09s. Namespace
function není lexical proof a lexical join navíc vyžaduje compiler-AST identifier
callsite. Finální grouped TS sada6 PASS12.93s: member/namespace/reassignment
negatives a lexical/#private positives, bez spuštění analyzované aplikace.

Review9f357e6 dále prokázalo ForOf/ForIn initializer writes včetně destructuring.
Sada3 RED/4 PASS52.00s; guard nyní pokrývá assignment/compound/unary i oba loop
initializer targets podle compiler bindings. Top-level script functions jsou global
object members, tedy UNKNOWN; pouze source module/block lexical jsou kandidáti
closed proof. Finální grouped TS10 PASS44.62s. Předchozí9f full byl přerušen po
konkrétním nálezu266.95s (pytest SIGINT interruption), nikoli final PASS.

## Grouped protocol/source-proof repair před finálním full

Shorthand assignment targets nyní používají veřejné TypeChecker
`getShorthandAssignmentValueSymbol`; plain/loop/default shorthand byly3 RED,
renamed property již PASS, grouped14 actual TS PASS69.31s. Compiler-bound direct
builtin eval či ambiguous eval identity zneplatní lexical body join v celém souboru;
string se nečte/nevyhodnocuje, skutečný const local arrow eval je odlišen.
Builtin identity používá skutečný lib.es5.d.ts locator; targeted3 PASS7.10s.

Actual captured-response replay prokázal12 RED/2 PASS2.56s: non-call return locator
nebyl svázán s captured snapshot/owner, některé container enums způsobily TypeError.
Oprava váže source proof na metodu/context/path/SHA a enclosing IR range, validuje
binding declaration ownership a canonical local/parameter identity. UNKNOWN future
IR kind zůstane boundary; list/dict kind/status/nullability/reference jsou
INVALID_PROTOCOL bez změny posledního validního store. Nyní28 actual-response
replay cases PASS7.90s (27 tamper +future-string). Interval index omezuje opakované
hledání enclosing method. Uncaptured TS dependency/global declaration binding se
nevydává za source binding proof; typed caller expression zůstává zachována.
K1 expression-body wrapper dostává skutečný compiler body locator; rebuild čeká
sdílený lock, aktuální whole-module/final-full zatím NENÍ tvrzen PASS.

Ancestor protocol fixes PR47 `f92c83e` a `ee14ea8` jsou převzaty jako `1537c10`
a `ae5fa2b`: strict argument enums/callsite references, owner a canonical occurrence
index. Finální full čeká jejich aktualizovaný parent s current-main integrací;
předchozí155 PASS109.35s focus je historický source9f, nikoli finální current proof.

Vlastní K1/K2 rebuild s real expression-body locator nyní PASS33.00s/PASS35.32s.
Finální pre-parent nový modul70 PASS248.52s, bez skip. Skutečná compatibility
regrese odhalila tsconfig program zahrnující test source mimo production snapshot:
1 RED7.15s. Worker pro takový body neposílá optional typed proof version, zachová
původní compiler graph a explicitní RETURN_SOURCE_NOT_CAPTURED; production caller
má typed result, nikoli foreign body join. Forged locator ve version1 proof se stále
striktně odmítá. Nejde o uvolnění snapshot validace.

Combined argument parent `417e2aa` obsahuje current-main49c46b a TSversion5 callback/
freshness kontrakty; jeho integrace a společný fokus/full jsou zatím PENDING.

## Combined TS5 source closure a primitive fields

CommonJS import přes mutable export property byl skutečně RED1/6.48s. Identifier
není automaticky lexical function binding: nyní se vyžaduje exact compiler
FunctionDeclaration symbol, nikoli import/alias/candidate. Skutečný #private member
má vlastní marker; typed caller result zůstává PROVEN, body identity je UNKNOWN.
Range line/column containers byly2 RED8.12s; nyní jsou primitive/positive/ordered,
včetně direct-proof flags a všech call/source/target reference containers před
hash lookup. VOID callsite source span se také kontroluje. Poslední cílené
scope/import/#private/lexical positives3 PASS25.84s.

Při parent integraci bylo nutné respektovat skutečný model: TS5 capture zahrnuje
celý compiler program a inferred source-set deklaruje jeho roots production i přes
folder convention (conflict zůstává viditelný). Skutečně nevybraný scope proto test
vyjadřuje explicitním classification.json override; existující config se byte-for-
byte zachová. Return projection používá classified Node.scope, nikoli jméno složky
nebo raw worker.scope. Alias import node a declaration target zůstávají oddělené.
Parent full733 PASS10 SKIP je ověřený, current return combined focus/full teprve následuje.

Bounded root review před full odhalilo malformed child collections: v1 block
statements=None/{} či [None] projde filtered traversal a následně havaruje. Známé
child nodes/collections, catch/case bodies a call references jsou nyní striktně
shape-checked před projekcí; nullable finally=None zůstává validní, legacy bez
return_flow_version se nemění. Actual captured-response replay53 PASS10.65s,
včetně14 nových child-container mutations a future-string UNKNOWN boundary.
Žádný další whole run nebyl spuštěn; combined focus-only před root closure následuje.

## Obnovení a skutečný společný argument/return fokus

Po obnovení prostředí odpovídalo všech127 zmrazených source hashů i oba JARy
manifestu6f4ec. Focus-only dokončil **124 PASS, 1 FAIL za91.67s**: starší actual
argument fixture předávala do version1 replay pouze context ID, nikoli captured
source_files. Produkční inspekce snapshot předává; strict return proof guard se
nemění. Test-only captured_context nyní počítá SHA256 ze skutečných fixture bytes
a canonical relative paths; synthetic legacy cases zůstávají nezměněné.

Původně selhávající round-trip nyní **1 PASS za2.20s**. Celé actual argument a
return moduly mají **128 PASS za106.89s**, bez skip, s mandatory vlastními K1/K2
workers. Log/XML jsou persistentní `fixture-context-focus.*` v
`/workspace/return-consumer-proof`. Root nezávisle schválil runtime closure i
17řádkový testový diff. Jeden strict full s --maxfail=1 je autorizován až po tomto
GREEN; jeho výsledek zatím není tvrzen PASS. Nový corrective durable task
`181b317334c7051df72f974d483085db741842ccfb022a947db1c0729ca7d24d` navazuje na
vyčerpaný historický retry budget707659; limity ani runtime guards se neuvolňují.

## Seskupená kontrola replay kontextů

Strict full nad4acbd77 skončil **158 PASS, 2 SKIP, 1 FAIL za87.87s**, exit1;
všech517 zmrazených vstupů zůstalo shodných. XML161 tests/1failure/0errors/2skips,
log, výsledky i manifest jsou zachované jako `failed-4acbd77-full-*`.
Nejde o finální full PASS. Selhal actual default-body graph roundtrip s dalším
historickým context ID bez source_files; production snapshot guard se neuvolňuje.

Následný rg+AST audit všech18 přímých proof calls v6 test modules našel právě tento
poslední actual caller. Ostatní graph-provider/workspace/Gradle vstupy jsou
syntetické s production context helperem; skutečný return replay zachovává
captured payload context. Legacy/malformed ID-only negatives zůstávají stejné.
Default-body fixture nyní předává SHA256 skutečných Bridge.java/Defaults.kt/Modern.kt
bytes, tedy přesně tří vstupů explicitní worker request. Oprava mění pouze test.

Celá grouped matrix default-body, arguments, return, graph-provider, workspace a
Gradle variants je GREEN: **203 PASS, 2 SKIP za280.13s**, exit0;
XML205 tests/0failure/0errors/2skips. Oba skips jsou explicitně optional Gradle8.13
gates bez KGMAKER_TEST_GRADLE; žádný actual default-body/K1/K2 případ nebyl přeskočen.
`grouped-context-focus.log/xml` a `grouped-context-callers.json` jsou persistentní
v `/workspace/return-consumer-proof`. Proti517file manifestu se změnila pouze
opravená test_default_body_mapping.py. Před jediným dalším strict full následuje
nezávislé review checkpointu a integrace aktualizované argument dependency/main;
nový full zatím není tvrzen PASS.

## Jednorázová integrace aktuální argument dependency/main

Po skutečném merge PR47 je current parent
`1915ebf0be25cab4cb8b0836e2fce25b05c7b10f`. Převzatý main obsahuje společně
argument mapping, HTTP typed literal/binding IR, Spring/ORM XML, coroutine,
React rule4 a Thymeleaf změny. Return proof guards a obě opravy captured test
kontextů z7385390 zůstávají beze změny; dřívější203/2 focus není vydáván za
validaci nové kompozice.

Java IR zachovává současně main binding/binding_ref/literal/captured_bindings
pro HTTP a additive return value_info/value_binding/body metadata. Own field
binding zachovává také canonical enum_constant/type metadata, aby nepřepsal
parent enum proof. Context/freshness, HTTP a return validators jsou samostatné;
workspace/CLI/process zachovávají oba inventáře i jejich původní refs.
Root nezávisle přečetl Java i Python resolved diff a source closure schválil.
Python compileall, TypeScript syntax a čistota diffu prošly. Následují oba
čerstvé vlastní worker buildy a společný actual focus. Ani nové buildy/focus,
ani jediný následný strict full zatím nejsou tvrzeny PASS.

Nová skutečná integrační fixture `test_actual_java_ir_preserves_both_binding_consumers`
pro oba backends současně kontroluje LOCAL_VARIABLE identity v obou IR kontraktech,
compiler literal/value_info, lambda capture, canonical enum_constant a zachovaný
DECLARED_BODY_RETURN proof. Fixture se pouze kompiluje; analyzovaná aplikace se
nespouští. Před čerstvým buildem/focus není tento nový test uváděn jako PASS.

## Skutečné čerstvé buildy a aktuální T025/Kafka parent

Na e1f81777 oba vlastní buildy skutečně uspěly: K1 za14.33s a K2 za13.07s.
Společná actual matrix má **295 PASS, 2 optional Gradle SKIP za365.39s**, exit0;
XML297/0failure/0errors/2skips, všech575 source a30 post-build JAR hashů při
běhu shodných. Obě nové dual-IR/backend integrační fixture prošly. Persistentní
source/built-jars/results/focus log/XML jsou v
`/workspace/return-consumer-current-validation`. JAR K1 má SHA47b4e624d14f1711d2f13445eedf96d45c26e04335ea9ad7d59b52486aa7e5f3,
K2 b7157bd9b120b846eeb30a00f2ba1d974a052499f30257736cfb6fcfc98ec813.

Před jediným finálním full byl absorbován main
`ef3ab4050289aafd557caa5414c594698da006ea` s T025 a deklarovaným Kafka W04.
Mezi1915 aef3 není žádný worker source delta; všech27 tracked worker/build
vstupů a všech30 skutečně postavených JAR/lib hashů zůstává přesně shodných.
Nový build se proto neopakuje; všech575 původních source hashů po parent změně
za shodné prohlášeno není. Flow ponechává T025 root/type/async/site/body guards,
caller-block clone prefix a argument i return sidecar. Workspace ponechává
Kafka redacted contexts/diagnostics i return reference qualification.
Relevantní current-parent focus a jediný strict full následují; jejich výsledek
zatím není tvrzen PASS. T025 certifikace lokálních operací je jiná budoucí větev.

## Hand-labelled golden return hranice

Finální-parent focus nad ef205 skutečně prošel **159 PASS, 0 SKIP za22.07s**.
Následný strict full skončil **419 PASS, 7 SKIP, 1 FAIL za719.36s**, exit1;
všech589 source,30 post-build JAR a4 ignored prerequisite hashů zůstalo shodných.
Log/XML/results/source receipts jsou zachované v
`/workspace/return-consumer-current-validation/final-parent/failed-ef205/`.
Nejde o full PASS. Golden inventory poprvé nečekalo nové správné return UNKNOWN
hranice na Work.kt6 absent(4) a Work.kt9 ambiguous pick(null).

Před dalším během byl ručně přečten celý golden source a všech5 scénářů pro oba
backends proti return v1 kontraktu. Přidány jsou pouze dvě přesné K1 unsupported
řádky pro tyto dvě source identity. K2 nemá Kotlin source return IR; Java ERROR,
constructor/callable a suspend ASYNC bodies se nepovyšují na DECLARED return join.
Ostatní mixed/Java/features/dispatch očekávání zůstávají nezměněná. Přesný
unsupported Counter, multiplicity, call inventory, počty a target assertions se
nemění; žádná diagnostická kategorie se nefiltruje a runtime guards se neuvolňují.
`golden-source-audit.md` v persistent validation adresáři obsahuje ruční matici
zdůvodnění před actual během. README corpus vysvětluje stejnou omezenou změnu.

Vyčerpaný corrective task181 je BLOCKED pouze z důvodu workflow retry budgetu;
explicitní nový golden corrective task navazuje bez změny limitů. Celý golden+
return/protocol focus následuje před nezávislým review a jediným corrected full;
žádný z těchto nových běhů zatím není uváděn jako PASS.

## Obnovení a přesná TypeScript context kompatibilita

Golden corrected full aa79 je skutečně dokončený, nikoli přerušený:
**820 PASS, 9 SKIP, 1 FAIL za1023.60s**, exit1; všech589 source,30 post-build JAR
a4 ignored prerequisite hashů při běhu zůstalo shodných. XML830 tests/1failure/
0errors/9skips a log/results/manifests zůstávají v `golden-corrected/`. Po ověření
ukončeného běhu a nulových /proc cwd/fd uživatelů byly smazány pouze disposable
pytest projekty; audit je `disposable-temp-cleanup-audit.json`. Source/JAR/M2 ani
aktuální fronty se nemažou. Žádný failed full není uváděn jako PASS.

Selhal Spring-only exact TS context specimen: nová nezávislá return extension
úmyslně přidává return_flow_rule_version a tím mění full context ID. Seskupený audit
všech exact-context assertions našel pouze tento historický whole-context fixture,
s variantami ordinary a React. V1 soubor zůstává byte-identický. Nový reviewed
`typescript-contexts-return-v1.json` obsahuje pouze výslovně očekávané pole
return-consumer-1 a kanonicky odvozená ID; všechny ostatní hodnoty a selection_key
jsou přesně původní. Očekávání není převzaté z actual output. Stávající dva testy
se přesměrovávají na nový fixture a nadále porovnávají celý dictionary; nic se
neignoruje a runtime guards se neuvolňují.

Nejmenší context/inspection-contract/protocol sada je **14 PASS za2.04s**.
Capability docs a fixture README popisují aditivní context extension a původní
historický fixture. Následuje společný context/freshness/return/protocol focus,
nezávislé review a jediný corrected full; nové běhy zatím nejsou tvrzeny PASS.

Navazující full nad `a67418a` skutečně skončil **822 PASS, 9 SKIP,
1 FAIL za896.91s**, nikoli PASS. Všechny590source/30JAR/4ignored-fixture
hashes zůstaly stejné; log/XML/manifests jsou zachované. Selhal původní registrar
test: nová return `valueBinding()` při čtení parametru znovu registrovala jeho
metodu, čímž `State.method()` přepsal dříve ověřené `bean_registrations`.
Minimální oprava používá existující čisté `State.methodIdentity()` se stejným
owner/name/descriptor/location tuple; binding IDs a compiler/registrar guards
se nemění. Regression nad skutečnou worker response ověřuje původní registrar
facts, factory facts i return receiver parameter ID. Nové oba native buildy a
společný Registrar/Factory/Conditions/Imports/Return/Arg/HTTP/protocol focus
teprve následují; další full zatím není autorizován. Workflow feedback legálně
přešel na implement iteration2/3, bez změny limitů.

Full na aktuálním parentu `630538de` skončil **1260 PASS,9 SKIP,1 FAIL
za1151.79s**.601source/30JAR/1493tool-fixture vstupů zůstalo shodných.
Selhal historický T024 předpoklad, že K1 expression-body return nemá source
locator. Zachovaný skutečný CFG ukazuje úplný SOURCE return blok nad přesným
`"static"` výrazem, line7, source SHA a compiler range; W02 producent nyní
přenáší `loc(it)` i na tento return. Historický raw worker response uložen nebyl,
což se nezaměňuje za existující CFG důkaz. Test-only oprava zachytí raw response
uvnitř stejných existujících inspekcí, ověří K1 body/context/scope/source/range
plus joined CFG proof tuple, a očekává HTTP body AVAILABLE pouze jako
SYNTAX_CANDIDATE. K2 zůstává bez Kotlin SOURCE body a bez triggerů. Všechny
původní tamper/scope/store kontroly zůstávají. Runtime/native se nemění.

Root schválil tento přesný test-only diff. Retry budget původního corrective
tasku zůstává vyčerpaný/BLOCKED; samostatný explicitní scoped task
`574934f1…` navazuje bez změny limitů. Nový coalesced focus teprve následuje,
další full není tvrzen PASS. Původní log/XML/manifests a malý failed T024
specimen jsou zachované; pouze dokončené disposable pytest projekty byly
s auditem odstraněny a uvolnily přibližně1.5GiB.

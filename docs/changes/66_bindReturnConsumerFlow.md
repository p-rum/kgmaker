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

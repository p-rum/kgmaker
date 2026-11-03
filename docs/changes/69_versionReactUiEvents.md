# Verzovaný bounded React JSX event adaptér

Task T003-S08-W04, AC01–AC04. Explicitní prerequisite stack je schválený lokální
PR46 head `1e21140fb261b3446f473b53b04ca9c7c4d1c754` (S08-W03, se svými W01/W02
závislostmi); není vydáván za merged main. Samostatná větev
`feat/t003-s08-04-versioned-ui-events`, žádný sousední work package.

## Problém a skutečný rozsah

Původní handles_event hledal substring @types/react v cestě a měl hardcoded rule
react-18.3.1 bez skutečné package/declaration provenance. React context pravidlo
navíc přepisoval legacy generic framework map. Nový adaptér `react-jsx-events-3`
reuse TypeChecker, handles_event fact, protocol1 a graph/schema1/2/3; nevytváří
paralelní UI model ani runtime/click/data availability proof.

Jediná aktuálně podporovaná matice: React18.3.1, @types/react18.3.18, TypeScript5.7.3.
Compiler musí vybrat external-library `node_modules/@types/react/index.d.ts`,
package name musí přesně souhlasit a celý declaration SHA256 je
`b89c2ddec6bd955e8721d41e24ca667de06882338d88b183c2cdc1f41f4c5a34`.
Odpovídající runtime package metadata se pouze čtou, nikdy neimportuje React JS.
Je to doložená deklarace známého balíku, nikoli attestace obecného supply chainu.
Jiné verze, změněná deklarace, lokální redirected fake nebo chybějící balíky mají
UNKNOWN diagnostic, bez nové handles_event hrany. Nic se neinstaluje automaticky.

Podporované eventy: onClick/onChange/onSubmit. Intrinsic prop musí být skutečný
compiler member oficiálního DOMAttributes nebo pinned Input/Select/TextareaHTMLAttributes. Jediný bounded wrapper tvar je checkout
function declaration s jedním props parametrem a jediným return JSX intrinsic,
který předává přesně stejný oficiální prop jako props.onClick/onChange/onSubmit.
Spready, další statements/returns, libovolné wrapper resolvery a podobná jména
nejsou důkaz. Callback musí být jediný complete source callable dle existující
callbackProof; mutable/conditional/open-world bindings se nesmí povýšit na
jedinečný handler. Existující S08-W03 candidate call-site význam se nemění.

## Evidence, freshness a kompatibilita

Evidence uvádí rule, skutečné runtime/types verze a package SHA, declaration SHA,
compiler declaration range a případný forwarding source range/hash. Execution je
NOT_OBSERVED. Package/declaration lookupy používají stávající input_snapshot
observations a input_files: preflight/analyze porovnává obě closure i ui_adapters.
UI snapshot i rule jsou v novém React context/selection identity. Offline provider
rehashuje captured inputs; staré React adapter contexts vyžadují novou explicitní
inspekci. Legacy/non-UI context konstrukce zachovává přesnou starou identitu.

Worker helper je součástí opt-in package marker, wheel a distribution SHA snapshotu;
neúplná nová distribuce selže před procesem. Protokol a graph/store formát zůstávají
stejné, evidence metadata jsou aditivní. Žádný source checkout se nepřepisuje;
publish=False a offline scan nemění last-valid store. Zápis inspekce zůstává pouze
původní explicitní publish kontrakt.

## Ověření a zbývající práce

- Actual TSX RED před změnou: **1 FAIL /6.88s**, verified wrapper handler chyběl.
- První adapter focus **4 PASS /41.78s** (před rozšířením negatives).
- Interim širší run **25 PASS, 2 FAIL /126.73s** není finální proof: vlastní worker
  byl během běhu změněn a správně selhal distribution hash; druhý failure odhalil
  dočasnou legacy React context identity změnu. Oprava se omezuje na nové skutečné
  adapter-bearing contexts. Oba původní výsledky zůstávají přiznané.
- Po této opravě legacy context/protocol/mandatory-CI **28 PASS /2.64s**.
- Finální frozen actual focus, strict full a semantic/scan/check budou doplněny
  skutečným výsledkem, nikoli odhadem. Required toolchain missing znamená FAIL;
  optional fixture bez připravených závislostí znamená explicitní SKIP.
- Remote CI/billing/merge jsou pozastavené uživatelem; žádný retry/merge se netvrdí.

Příklad (předem explicitně připravené pinned balíky):
`kgmaker inspect frontend --root /repo --ui-framework react`.
Obecné React versions, HOC/class/memo wrappers, arbitrary prop transforms, dynamic
callback execution a celý T003-S08 zůstávají nedodané/UNKNOWN; statická vazba není
skutečný uživatelský klik ani runtime pořadí.

## Zpřesnění compiler tag/factory proof před finálním během

První frozen širší focus prošel **53 PASS /126.60s**, ale nezávislý actual audit
následně našel false positive mimo tehdejší negatives. Lokální queued full byl
ukončen ještě před startem pytest child: **0 executed**, žádný full PASS.
- Augmentované JSX.IntrinsicElements pro uppercase Fancy i lowercase custom tag
  vytvořily nesprávnou vazbu na swallowing wrapper: actual RED **2 FAIL /11.98s**.
  TypeScript intrinsic lexical kind a skutečná pinned IntrinsicElements tag
  deklarace se nyní kontrolují společně; uppercase/member tags jdou wrapper cestou.
- Custom jsxFactory, checkout React.createElement shadow, per-file @jsx a custom
  jsxImportSource reprodukovaly false positives: actual RED **4 FAIL /16.26s**.
- Následující focus byl zastaven jako known-invalid po11 dots bez summary; žádný
  výsledek PASS se z něj neodvozuje. Další mezikrok byl zastaven po10 dots, protože
  actual typed-shadow probe (`as unknown as typeof R`) prokázal, že samotný
  oficiální member type není důkaz factory receiver value.

Classic JSX nyní vyžaduje lexical compiler symbol pro skutečný oficiální React
namespace/createElement (import alias povolen), nikoli checkout object se stejným
typem. Automatic react-jsx/react-jsxdev vyžaduje default react/jsx-runtime nebo
react/jsx-dev-runtime, skutečný compiler-selected external module a přesný hash
jeho pinned declaration. Custom importSource a per-file JSX directives zůstávají
UNKNOWN. Renderer config/snapshot a jeho input hashes jsou součástí stejné
existující preflight closure/context identity. Žádný renderer se nespouští.

Nový frozen actual UI renderer focus: **20 PASS /91.37s**. Následný širší frozen
callback/project/limits/legacy/protocol/mandatory-CI focus: **63 PASS /160.72s**.
Před queue full ještě actual stará PR46 distribuce prokázala, že uměla vrátit
handles_event bez ui_adapters snapshotu. Nové opt-in React inspect proto explicitně
odmítne chybějící versioned preflight kontrakt; non-UI legacy worker a staré uložené
graph formáty zůstávají čitelné. Samostatný regression hlídá source/last-valid-store
při této chybě a neúplný marked helper selže ještě před spuštěním procesu.

## Full fixture guard a oprava přípravy distribuce

Final UI contract focus: **6 PASS, 29 DESELECTED /20.21s**. Připravený strict full
pak našel starou test fixture `test_snapshot_helper_is_hash_bound_to_distribution`,
která kopírovala nový marked worker bez jeho UI helperu. Guard správně odmítl
neúplnou distribuci ještě před zamýšlenou mutací input_snapshot helperu. Nejde o
runtime regression; reprodukce samostatného testu byla **1 FAIL /0.16s**.

Na pokyn orchestrátora byl ukončen pouze vlastní známý invalidní full pomocí
SIGINT. Pytest uložil JUnit a konečný částečný výsledek **494 PASS, 9 SKIP,
1 FAIL /508.08s**, KeyboardInterrupt; není vydáván za whole PASS. Artefakty jsou
`/workspace/ui-events-interrupted-fixture-full.log` a `.xml`. Před opravou byly
všechny vlastní procesy ukončeny; žádný cizí validní běh se nerušil.

Fixture nyní kopíruje kompletní nový worker a stejný test parametrizovaně ověřuje
hash-bound invalidaci input_snapshot i ui_events helperu. Produkční source/worker
bytes z checkpointu0171107 zůstaly beze změny. Actual repair focus:
**5 PASS, 51 DESELECTED /15.24s** (oba helper hashes, neúplné distribuce, chybějící
versioned UI kontrakt a last-valid store). Nový připravený frozen full čeká pod
shared heavy lockem; finální výsledek bude doplněn skutečným logem/XML.


## Konečná kompletní matice a strict full

Actual TS5.7.3 `reactNamespace=Fake` audit prokázal další factory false positive:
compiler emituje Fake.createElement, nikoli React; žádná aplikace neběžela.
Vlastní známý invalidní full byl ukončen před úpravou source: **464 PASS, 9 SKIP
/436.73s**, KeyboardInterrupt, bez whole PASS. Log/XML zůstávají v
`/workspace/ui-events-interrupted-namespace-full.*`. Grouped RED pro namespace,
explicit fragment a empty renderer controls: **4 FAIL /19.91s**.

Finální whitelist rozlišuje undefined od prázdné hodnoty. Podporuje classic
React default a skutečné official createElement import aliases přes jsxFactory;
automatic default react-jsx/react-jsxdev vyžaduje pinned runtime declaration.
Jakýkoli explicitní reactNamespace, jsxFragmentFactory, jsxImportSource a per-file
jsx/jsxfrag/jsxruntime/jsximportsource pragma je mimo tento bounded subset UNKNOWN.
Preserve/react-native ani malformed factory values nevyrábějí pozitivní UI edge.
Public TS5.7 declarations neposkytují factory accessor; produkt nepoužívá privátní
getJsxNamespace ani emit/transpile. Jednorázový transpileModule audit byl pouze
validační, nikoli produktová cesta či spuštění aplikace.

Audit všech tří inzerovaných eventů odhalil, že onChange na input/select/textarea
má specializovanou oficiální deklaraci mimo DOMAttributes: RED **3 FAIL, 2 PASS
/20.29s**. Vlastní incomplete full skončil před změnou **144 PASS, 2 SKIP /157.79s**,
KeyboardInterrupt, nikoli whole PASS (`/workspace/ui-events-interrupted-controls-full.*`).
Allowlist nyní obsahuje pouze čtyři známé pinned React interface families:
DOMAttributes, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes;
stále platí přesný declaration hash, official intrinsic tag a factory value proof.
Stejnojmenné checkout interface samo nedostane framework binding.

Kompletní frozen advertised matrix: **43 PASS, 32 DESELECTED /237.28s**
(`/workspace/ui-events-complete-matrix.log` a `.xml`). Obsahuje onClick, všechny
specializované onChange controls, form onSubmit, direct/verified wrapper positives,
všech pět renderer controls a čtyři pragma forms, official aliases/automatic modes,
critical fake/shadow/type/mutable/ambiguous/spread/version negatives a oba helper
hash guards. Pure pre-process metadata guard používá tool-lookup stub a netvrdí
skutečný compiler/toolchain PASS.

Následný jediný full na stejných frozen source/test bytes: **624 PASS, 10 SKIP
/762.95s**, JUnit634 cases,0 failures,0 errors; všech41 UI cases skutečně proběhlo.
Preflight ověřil vlastní worker distributions, reálný Maven/React fixture a pinned
Spring API bez buildu/installu. Explicitní own PYTHONPATH/workers, JDK21/Kotlin PATH,
required Workers/K2/Spring flags, workspace TMPDIR a shared heavy lock jsou stejné
jako v příkazech předaných orchestrátorovi. Persistent artifacts:
`/workspace/ui-events-full.log`, `/workspace/ui-events-full.xml`.
Deset SKIP je optional tool/exporter matrix a skutečný Windows gate; missing
mandatory tools nejsou PASS. Předchozí neúplné/failing běhy nejsou přepsány.

Po upgradu uživatele root obnovil GitHub Actions; historická billing pause již není
aktuální blocker. Tento lokální candidate nemá vlastní nové CI výsledky ani merge;
publikaci, aktuální dependency/base integraci a nezávislé review řídí root.
Scoped semantic update zachovává existující facts/history, mění pouze doložené
source anchors a zachytí nový validation episode. Nadřazený T003-S08 zůstává PARTIAL.


## Dodatečná hranice mutable binding (před finálním přijetím)

Nezávislý audit po předchozím full našel přepsanou function-declaration wrapper
binding a mutable method handler, které neprávem přebíraly původní source proof.
Výsledek **624 PASS /10 SKIP** výše je proto historický před touto opravou.
UI nyní samostatně ověřuje compiler-bound lexical binding; obecný callbackProof
pro non-UI source calls zůstává beze změny. Ordinary member handlers a jejich
const aliases nemají silný handles_event proof. Jediný per-checker syntaktický
write catalog používá veřejné TypeChecker symboly, včetně
getShorthandAssignmentValueSymbol pro object shorthand/default destructuring;
zahrnuje assignments/compound/unary/loop targets a initialized function redeclaration.
Nejde o heap resolver ani pozorování spuštění callbacku. Direct/ambiguous eval
znamená UNKNOWN pro lexical proof v daném source file; nečte ani nespouští string.
Definite const local callable pojmenovaná eval je od builtin boundary odlišena.
Duplicate/redeclared binding diagnostics TS2300/2451 na declaration-name span
brání vybrání jedné z nekompatibilních compiler symbol declarations.

Pravidlo v3 zneplatňuje uložené v1/v2 UI generations a frontend preflight odmítne
snapshot staršího pravidla. Původní snapshot/cache/store se nepřepisuje; freshness
kontrola zůstává offline. Main callback parent je explicitně integrován z
3a7f76b00bb5136bbe5990546d9c8942a7f53f73, bez změny jeho non-UI callback resolveru.

První actual mutability focus: **11 PASS /27.55s**. Kompletní běh před upravením
staré diagnostic assertion skončil **51 PASS, 1 FAIL /291.02s**; jediný FAIL byl
nový MUTABLE_UI_HANDLER reason mimo původní testový allowlist, bez false edge.
Následující vlastní focus byl bezpečně přerušen před úpravou catalogu:
**30 DESELECTED /10.90s**, žádný dokončený test ani whole PASS. Další focus odhalil
initialized var collision: **26 PASS, 1 FAIL, 30 DESELECTED /149.10s**. Compiler
pro tuto collision vydal dvě TS2300; fix využívá tyto skutečné compiler diagnostics,
nikoli textový name resolver. Následný opravený focus: **27 PASS, 30 DESELECTED
/124.52s** (`/workspace/ui-events-binding-27pass.xml`). Rozšířený write/cache focus skončil **35 PASS, 30 DESELECTED /164.77s**
(`/workspace/ui-events-binding-35pass.log` a `.xml`).


## Finální v3 přijetí mutable-binding opravy (2026-10-27)

Nezávislé review doplnilo stejný write/dynamic audit také na renderer namespace a
createElement declarations. Skutečný valid TypeScript s explicitním přepsáním
React.createElement měl nula TS diagnostics, ale původně vytvořil false event:
RED **1 FAIL, 65 DESELECTED /3.85s** (`/workspace/ui-events-factory-write-red.*`).
Po opravě běžel frozen focus **36 PASS, 30 DESELECTED /266.43s**. Původní odhad41
byl dvojí započtení form-control případů již zahrnutých přes verified_wrapper;
JUnit prokazuje skutečné input/select/textarea onChange, form onSubmit, onClick,
oficiální factory modes a všechny nové binding/renderer/cache negativy.
Artefakty: `/workspace/ui-events-final-binding-acceptance.log` a `.xml`.

Main49c46b0bd165cf11e7b3eb0af04bf64fb93e23ce je explicitně integrován v lokálním
source commit96df82a7f063b3b542d92768756219d0a637ad5e. Mandatory compiler job
zachovává původní i T015 a UI testy. Tři nezávisle reviewované source/test SHA se
při integraci nezměnily; vlastní worker distributions nebyly přestavovány ani
měněny. Jedna still-queued flock instance byla ukončena před pytest kvůli chybějícímu
explicitnímu test Maven repository exportu: exit143, žádný child/log/test/PASS.
Opravený runner teprve poté získal shared lock. Přesný příkaz je zachován v
`/workspace/ui-events-mutability-full.sh`:

```bash
flock /workspace/kgmaker-heavy-tests.lock env \
  JAVA_HOME=/workspace/tools/jdk-21.0.6+7 \
  PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/kotlinc/bin:$PATH \
  PYTHONPATH=/workspace/ui-events/src \
  KGMAKER_WORKERS_HOME=/workspace/ui-events/workers \
  KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/tools/m2 \
  KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_SPRING_IMPORTS=1 \
  TMPDIR=/workspace/ui-events-validation-tmp \
  /workspace/kgmaker-venv/bin/python -m pytest -q \
  --junitxml=/workspace/ui-events-mutability-full.xml
```

Jediný finální required full: **727 PASS, 10 SKIP /791.26s**, exit0. JUnit737
cases má zero failures/errors a všech66 UI cases skutečně proběhlo. Deset SKIP
zůstává optional tool/exporter/Windows matrix; missing mandatory setup není PASS.
`/workspace/ui-events-mutability-full.log`, `.xml` a `.exit` zachovávají výsledek.
Preflight ověřil core compiler/API/fixture vstupy, navíc přesné JPA JAR/POM/parent
license SHA z nově integrované T015 fixture; nebyl spuštěn build ani install.
Po full sedělo všech201 položek source/test/fixture/config/worker manifestu
`/workspace/ui-events-mutability-full-frozen.json`. Během validního běhu nebyl
změněn runtime/helper/test. Předchozí624/10 ani žádný RED/partial nejsou vydávány
za aktuální v3 proof. Exact Git-pair review, publikaci a vzdálené CI řídí root;
tento autor nic nepublikoval ani nemergoval. Nadřazený S08 zůstává PARTIAL.

## V4: opaque module/namespace a canonical scope guards

Root actual valid-TypeScript repro našlo dvě false positive cesty: CommonJS import
s přepsáním exportu přes any alias a React namespace alias s přepsáním factory.
V4 vyžaduje explicitní ESM compiler mode calleru i vlastníka, přímý compiler export
s přesným valueDeclaration; CJS/interop/re-export chain zůstává UNKNOWN. Celý React
namespace přes alias/cast/container představuje escape boundary, bez heap resolveru.
Materializer navíc vyžaduje canonical classified scope handleru i wrapperu;
explicitně test-classified declarations neprojdou production UI proof.

Nová actual opaque/scope matrix: **23 PASS,60 deselected v148.92s**. Kompletní
v4 UI/distribution matrix: **117 PASS,0 SKIP v522.58s**. Source checkpoint
`8f660affdbe14909ef57028063550d7688bb2b25`, čtyři opaque SHA root review APPROVE.
Jediný corrected strict full: **785 PASS,10 SKIP v891.07s**, exit0; XML795 tests,
nula errors/failures. Všech230 source/test/fixture/config/JAR hashů před/po souhlasí.
Persistent `/workspace/ui-events-v4-full.log`, `.xml`, `.exit`, `-frozen.json` a
`-receipt.json`. Dřívější43 complete matrix je pre-v4 historický proof, nikoli
finální v4 test. Žádná aplikace, React JS nebo browser nebyl spuštěn.

Po ověření full integrován main `c76f6dcfd38f0bfeed8c899535bcae5c5f3ccc8a`
(s Kotlin JPA/W02, HTTP katalogem, process model a Factory hooks). Čtyři vlastní
opaque source/test SHA zůstaly přesně nezměněné, runtime merge byl bez konfliktů.
Všech15 JVM source/builder/lock souborů je přesně source donor spring-factories,
jehož vlastní fresh build a actual28 byly doložené před merge PR53. K1/K2 JARy
převzaty až po porovnání všech10/18 library SHA; worker receipt je v
`/workspace/ui-events-current-parent-worker-receipt.json`. Nejde o staré JARy
odvozené pouze z názvu source větve. Aktuální parent focused integrace ještě čeká;
nový full se pro nezměněný vlastní v4 runtime neopakuje. GH CI je volitelné dle
výslovného T045 revize2; ostatní acceptance/toolchain a nezávislé review povinné.

## Current-parent compose HTTP/Spring/XML/coroutine

Předchozí focused integrace nad `78d35c7` není kompletní PASS: **168 PASS,1 setup
ERROR v368.52s**, XML169/1error/0fail. Chyba nastala v InstalledWorkerTests.setUpClass
při Python3.12 ensurepip subprocess; původní stderr není v tracebacku zachovaný.
Izolovaný následný explicitní offline ensurepip diagnostic uspěl; původní příčina
není domýšlena. Všech213 tehdejších source/JAR hashů před refresh souhlasilo.
Log/XML/receipt jsou zachované v `/workspace/ui-events-current-parent-focus.*`.

Nový parent `75d448ee7791cffb3dc9f4cceff5136402a8f5e0` přidává coroutine,
Spring conditionsv6, ORM XMLv2, T024/golden a HTTP/privacy guards. Root přečetl a
výslovně schválil kompozici tří konfliktů: UI adapter selection vedle HTTP rule
filteru; React snapshot gate vedle JVM-only Spring condition a HTTP proof gates;
JVM HTTP prepare/conditionhash a aktuální JPA rule zachované, React rule4 override
pouze pro TS React s adapters. Canonical source/target/wrapper scope guards
zůstávají přesně stejné. Inspection jako celek má kvůli parent additions jiné SHA;
zbývající tři opaque helper/worker/test SHA jsou přesně z validovaného785/10 full.

Aktuální HTTP donor má15 přesných JVM source/build/lock souborů a dva JARy shodné
s jeho skutečnou153 PASS0SKIP320.65s + XML-parent3 PASS39.72s evidencí. K1/K2
50cf8376/2eb240a5 byly převzaty až po ověření10/18 library SHA; receipt
`/workspace/ui-events-http-parent-worker-receipt.json` uchovává celý closure.
Zůstaly zachované raw source snapshot, XML cachev2, conditionv6 i HTTP privacy
kontroly. Před retry byly odstraněny pouze dokončené vlastní pytest temp trees
(5.3GiB) a diagnostic venv; logy/XML/manifesty/receipts nebyly odstraněny. Nový
current focused batch včetně distribution musí opravdu proběhnout; není nahrazen
starými168 PASS ani isolated diagnostic. Full se pouze kvůli parent neopakuje.

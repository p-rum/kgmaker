# Verzovaný bounded React JSX event adaptér

Task T003-S08-W04, AC01–AC04. Explicitní prerequisite stack je schválený lokální
PR46 head `1e21140fb261b3446f473b53b04ca9c7c4d1c754` (S08-W03, se svými W01/W02
závislostmi); není vydáván za merged main. Samostatná větev
`feat/t003-s08-04-versioned-ui-events`, žádný sousední work package.

## Problém a skutečný rozsah

Původní handles_event hledal substring @types/react v cestě a měl hardcoded rule
react-18.3.1 bez skutečné package/declaration provenance. React context pravidlo
navíc přepisoval legacy generic framework map. Nový adaptér `react-jsx-events-2`
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
compiler member oficiálního DOMAttributes. Jediný bounded wrapper tvar je checkout
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

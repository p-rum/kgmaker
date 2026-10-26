# Omezené TypeScript callback targety přes generic API a barrel exports

Datum: 2026-10-26. Task [T003-S08-W03](../tasks/T003-S08-03-typescriptCallbacksGenerics.md),
AC01–AC04, nadřazené T003-AC08. Výchozí commit `d416e2aa7208f3f3bf385d567c4ad8dce31a5cee`:
explicitní stacked dependency [Draft PR36](https://github.com/p-rum/kgmaker/pull/36)
pro W02; W01 již merged. W02 a tato práce dosud nemají merge acceptance;
GitHub Actions billing/quota blokuje nové CI, bez bypassu. Uživatel výslovně
povolil pokračovat ve stacked větvi. Větev
`feat/t003-s08-03-typescript-callbacks-generics`, worktree `/workspace/ts-callbacks`.
Note53 rezervována orchestrátorem; žádné cizí zadání ani note se nepřepisují.

## Rekognoskace a konkrétní mezera

Graph/query, memory recall, task/source/test kontrola: TypeScript již rozlišuje
re-export aliases a concrete overload signatures. Worker obecně používá
`getResolvedSignature().getDeclaration()` jako declared target. Syntetická union
signature tak může vypadat jako jednoznačný target; function-type declaration
callback parametru naopak není konkrétní implementace callbacku. Existující
argument-to-parameter extrakce používá symbol na argument expression, takže
přímé inline arrows opomíjí. `callgraph` a graph model již odlišují declared
od `dispatch_candidates`; nový paralelní katalog není potřeba.

Produkčně věrná fixture `fixtures/typescript-callbacks` obsahuje generic higher-order
API přes dvojitý barrel alias, dvě overload signatures, named a inline callback,
const alias, union callback a any. První skutečná acceptance sada je připravena
před runtime změnami a čeká na heavy lock. Výsledek není dosud vydáván za FAIL/PASS.
Plán: jednoznačné direct/const callables resolverem doložit; callback argument
bindings reprezentovat canonical IDs a open-world param invocation pouze jako
incomplete candidates. Jeden pozorovaný caller není důkaz jediného runtime targetu.

## Hranice a validace

Zachovat owner Program/TypeChecker, scoped freshness, identity, protocol1,
graph/store v1/v2/v3, SOURCE_ONLY a nulové implicitní procesy/mutaci store.
Persistent compiler cache, framework UI/BE–FE flow ani celý T003-S08 nejsou scope.
Přesné skutečné red/green, regresní/full výsledky a omezení budou doplněny podle
provedených kontrol; současný průběžný záznam není dokončení work package.

## Skutečný první proof

Po výslovném upřesnění orchestrátora: heavy FULL/JVM buildy zůstávají pod sdíleným
flockem; malé focused Node/pure Python kontroly mohou běžet souběžně. Zrušeno
pouze vlastní čekající baseline flock PID326147 a spuštěn actual TS baseline:
**6 FAIL /1 PASS**,4.89s, `/tmp/ts-callbacks-baseline.log` a XML. Generic barrel,
selected overloads a direct alias již PASS; konkrétní callback mezery skutečně FAIL.
První worker-only oprava stejnou sadu: **7 PASS**,5.17s. Žádná W02 runtime změna
ani zásah do její běžící/čekající full proof nebyly provedeny.

Při kompatibilitní kontrole přidán ambient `StringConstructor` contract případ:
**1 FAIL /7 DESELECTED**,5.44s, `/tmp/ts-callbacks-contract-red.*`. Oprava odlišuje
compiler-proven ambient call signatures od falešného initializer body targetu;
ambient contract není tvrzení konkrétní runtime implementace. Širší focused
regrese nyní běží; výsledek doplníme podle skutečnosti.

Source-final expanded callback/owner/limit/atomic sada: **13 PASS**,62.45s,
`/tmp/ts-callbacks-expanded.log` a XML. Předchozí callback+W01+provider regresní
sada: **34 PASS**,280.34s. Doplňující strictNullChecks/project/repo owner proof
před bound úpravou: **2 PASS**,66.24s; source-final13 obsahuje obě varianty znovu.

Bound audit nejprve skutečně reprodukoval dvě nežádoucí whole-worker failures
na65 callbacks; třetí red assertion zaměňovala WorkerError numeric exit code za
status (validator už správně odmítal unknown candidate), assertion opravena na
`status == INVALID_PROTOCOL`. Nyní library callbacks nespotřebují local binding
budget, source invocation nad64 bindings vrátí PARTIAL s64 candidates a explicitním
`CALLBACK_TARGET_LIMIT`; nic netvrdí complete dispatch. Unknown callback ID zachová
byte-identický poslední validní store. Worker4 zůstává protocol1; callgraph/model
se nemění, protože existující candidate evidence kontrakt prokazatelně stačí.

Další konkrétní negative proof: conditional callback argument se dvěma known
function branches byl nesprávně označen jako dva resolved argument bindings.
Actual red **1 FAIL /3 DESELECTED**,6.29s (`/tmp/ts-callbacks-union-binding-red.*`);
one-line evidence oprava a protected sada **14 PASS**,78.88s. Další actual red
**1 FAIL /4 DESELECTED**,5.66s (`/tmp/ts-callbacks-expression-limit-red.*`) prokázal
chybějící přenos expression candidate limitu do parameter-invocation reason;
bounded PARTIAL limit evidence se nyní přenáší i z jediného complex argumentu.
Final source/test SHA256 freeze: `/tmp/ts-callbacks-source-final-freeze.json`;
final15-case focus a full jsou spuštěny/queued s persistent log/XML a bez dalšího
runtime přepisování. Prerequisite preflight po explicitní přípravě PASS; full
mandatory workers/K2/Spring flags zůstávají1, JDK21/Kotlin2.1.10 jsou explicitně na PATH.

Final protected source/test matice: **15 PASS**,61.69s,
`/tmp/ts-callbacks-final-focused.log` a XML. Zahrnuje actual owner Program strict
a non-strict consumer, dvě repo realms, overload→body parameter binding,65
library/local/complex-expression callbacks, conditional candidate fact strength
a actual corrupted candidate zachovávající store. Source/test freeze nyní odpovídá
tomuto přesnému workeru a15-case matici. Heavy full byl znovu queued po opravách
bez runtime přepisování; `/tmp/ts-callbacks-full.log/.xml`, výsledek PENDING.
W02 dependency mezitím local source-final full dokončila567PASS10SKIP787.45s;
required CI/merge PR36 stále pending kvůli billing/quota, není obejito.

## Stacked integrace a scoped semantic evidence

Převzat metadata-only W02 final commit8e83937 (full567PASS10SKIP); všechny current
worker/test SHA256 po merge7e8cfaa zůstaly shodné s final15PASS. W02 acceptance
a vlastní W03 candidate sekce jsou zachovány společně. Scoped semantic update
base8e83937 vytvořil nový packet; patch použil jeho přesné update_id/contexty,
reanchored compiler documentation citation a doložený callback concept.
`semantic apply` a `semantic validate` PASS: **8 concepts /23 static edges**.
W02 **107 episodes** jsou exact immutable prefix, následované jedním vlastním
implementation capture s actual15/regression34=passed, full/CI=unknown.
Generované graph views jsou obnoveny příkazem, ne ručně. Full zůstává PENDING;
žádná automatická instalace/build ani CI retry/bypass nebyly přidány.

## Přesná hranice overload navigation

Actual compiler/read-only probe nad stejnou fixture vybral qualified function
`src/handlers.ts` /kind function /name asText (nikoli barrel alias). Generic run
→asText vrací `STATIC_PATH` s DECLARED_TARGET a DISPATCH_CANDIDATE kroky;
overloadedCallback→asText vrací `UNKNOWN`: selected overload signature a její
implementation body jsou oddělené graph identity bez nově doplněného bridge.
AC01 vyžaduje resolved canonical signature targety a nepovýšené callback ambiguity;
nepožaduje nový signature→body path kontrakt. Toto je výslovně PARTIAL/unsupported
navigation hranice, nikoli důvod vymýšlet dispatch alias či přepisovat selected
signature. Skutečný implementation-parameter binding proof je testován odděleně.
Žádný runtime kód ani full freeze kvůli tomuto dokumentovanému omezení neměněn.

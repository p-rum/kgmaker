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

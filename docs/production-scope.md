# Production scope a evidence v2

Tato stránka popisuje offline klasifikaci a pohledy dostupné od PR #4.
Na navazující větvi PR #5 existují také explicitní compiler workery, build exportéry
a CFG v omezené matici; viz [compiler inspection](compiler-inspection.md).
Úplné dokončení řeší [T003](tasks/3_finishProductionAnalysis.md). Přehled požadavků a stav milníků je v
[progress dokumentu](production-analysis-progress.md).

## Použití

```bash
kgmaker project inspect --root . --format json
kgmaker project classify --root . --explain --format json
kgmaker scan --root .
kgmaker query process --root . --scope production
kgmaker graph view --root . --scope production --view calls --format json
kgmaker graph rank --root . --profile execution --explain
kgmaker coverage report --root . --format json
kgmaker graph migrate --root .
```

Offline `project inspect/classify` pracují se zdroji/modely bez spuštění buildu.
`graph view/rank` a `coverage report` mohou využít validní compiler index;
bez něj poskytují syntaktický pohled. Samy compiler/build nespouštějí. Freshness reportu
rozlišuje `MISSING_INDEX`, `STALE` a `FRESH`; `analysis_source` výslovně označuje
aktuální in-memory výsledek. `graph migrate` jako jediný nový příkaz zapisuje
uložený index; migrace nečte nový compiler model a scope zůstává unknown.

Výsledek SOURCE_ONLY má `status: PARTIAL`. Úspěšné vytvoření částečného reportu
vrací exit 0, neplatný vstup 2, nesplněná strict coverage 4. Detekce mixed snapshotu
vrací 3. Offline klasifikační příkazy nic nevykonávají; explicitní build/inspect workflow má samostatnou execution a stale diagnostiku.
Stará `build`/`scan`/`feature`/hook workflow nespouštějí Maven, Gradle, npm,
aplikaci, migrace ani DB spojení.

## Nezávislé osy a overrides

Soubor a zdrojový symbol nesou `scope`, `role`, `origin`, `build_membership` a
`classification_evidence`. Konvence `src/main`, `src`, `app`, `pages`, `lib`
jsou production fallback; `test`, `tests`, `integrationTest`, colocated `.test.`/
`.spec.` a `test_` jsou test fallback. Fixtures mají samostatný scope.
Soubory bez doloženého pravidla zůstávají unknown. Role rozlišuje executable
code, konfiguraci, migraci, kontrakt, dokumentaci a resource. Kotlin soubor
s `@Bean` metodou zůstává executable code; YAML property není execution krok.
Fallback nemá úplnou znalost framework anotací nebo symbolových DTO rolí.

Explicitní overrides v `.kgmaker/classification.json` používají verzovaný JSON:

```json
{
  "schema_version": 1,
  "overrides": [
    {"path":"custom/backend","scope":"production","reason":"Project-owned application root"},
    {"path":"custom/client","scope":"production","origin":"generated","reason":"Generated application API client"}
  ]
}
```

Path je přesný soubor nebo prefix adresáře. Pravidla se vyhodnocují v zadaném
pořadí; pozdější explicitní pravidlo přepisuje uvedené osy. Každé má povinný
důvod. Symlinky a cesty mimo root jsou odmítnuté.

`project classify --model source-sets.json` přijímá explicitně dodaný model:

```json
{
  "source_sets": [
    {"module":"api","id":"main","scope":"production","roots":["custom/backend"]},
    {"module":"api","id":"integrationTest","scope":"test","roots":["custom/it"]},
    {"module":"client","id":"main","scope":"production","roots":["custom/client"],"generated":true}
  ]
}
```

Pole `files` umožňuje uvést přesné vstupy. Jeden soubor může mít více memberships;
rozpor scopes je viditelný a bez výběru varianty dává unknown. Model má trust
`SUPPLIED_MODEL_UNVERIFIED`: není ověřeným exportem skutečného buildu nebo TS
Program. Neprokazuje effective classpath, profily, compiler verzi ani úplnost
tsconfig exclude. Podezřelý test v production source setu zůstává ve skutečně
zadaném production pohledu s `BUILD_SCOPE_CONFLICT`; override/build rozpor
se zachová jako `OVERRIDE_BUILD_CONFLICT`. Strict konflikt odmítne.

## Projekce, ranking a kompatibilita

Scanner odděluje scope před name-match indexem, persistence/dataflow extrakcí a
slučováním sdílených doménových uzlů. Produkční import nemůže vybrat testovací
soubor. Testovací index v tomto inkrementu neřeší test-to-production call targets;
test overlay zatím není samostatné CLI. Sdílené doménové uzly neprodukčních
scope mají scope-qualified IDs. Path-owned dataflow IDs zůstávají stejné.

Výchozí query, architecture Markdown/Mermaid a hook používají production.
Neznámé soubory se nepovažují za production. `query --scope all` a `graph view
--scope all` zpřístupní inventory. Python renderer umí explicitní `scope="all"`.
Diagram je architektura, nikoli control-flow nebo pořadí vykonání.

Profily `execution-2` a `impact-2` mají stabilní ID tie-break, score breakdown,
konkrétní contributions/path a lokalizované penalty za neúplnost.
`kgmaker graph rank --profile impact --format markdown` vykreslí stejnou evidenci
jako výchozí JSON. Podrobný kontrakt a omezení: [evidence ranking](evidence-ranking.md),
[change126](changes/126_evidenceRanking.md).
Execution profile používá explicitní call-site/dispatch rodiny; legacy `calls`,
typové reference, konstanty, contains, testy a dokumentace mají nulový execution
příspěvek. Side effects a shared type references jsou samostatné dimenze. Enum
ani DTO nejsou automaticky schované; enum metoda v doložené cestě může být
viditelná. SOURCE_ONLY zatím takovou compiler cestu nedokládá.

Schema v2 přidává contexts, diagnostics, evidence inventory, klasifikaci a
nezávislý `evidence_kind`. Každá scanner hrana má evidence ID, scope context,
zdrojový hash a dostupnou lokaci. Syntaktické nálezy zůstávají SYNTAX_CANDIDATE,
bez ohledu na staré confidence score. V1 reader nepřebírá tvrzení o scope.
`graph migrate` zachová jednoznačné legacy IDs a old→new map, scope unknown,
trust LEGACY_UNKNOWN a freshness UNKNOWN; duplicitní IDs odmítne.

Serializer před atomickým zápisem validuje ID, evidence reference, klasifikaci
a typ důkazu. Snapshot se ověří před publikací. Změna classification config
invaliduje context, feature fingerprint a workspace cache. Semantic update
packet nese contexts a po jejich změně se starý patch odmítne. Agent annotations
stále nedodávají resolved calls nebo availability. Feature v1 path proof formát
a jeho availability kontrakt se zachovávají.


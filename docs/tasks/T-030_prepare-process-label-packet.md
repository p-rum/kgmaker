# T030 — Packet pro business pojmenování agentem

- Task ID: `T030`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T024](T-024_discover-process-triggers.md); [T026](T-026_collapse-business-steps.md).
- Větev: `feat/t030-prepare-process-label-packet`
- PR title: `feat(t030): prepare process label packet`
- Primární moduly: `nový process_semantics.py`, `analysis_model.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Packet pro business pojmenování agentem. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T030-S01:** Připrav bounded packet s existujícími process/step IDs, evidence summary, baseline hash a allowed annotation schema.
2. **T030-S02:** Vytvářej candidate template bez volání model API; rozpočet v tokenech/znacích a omitted části uveď v packetu.
3. **T030-S03:** Dokumentaci používej jako citovaný podklad pro význam, nikoli autoritu pro technické hrany.
4. **T030-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T030-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T030-AC01:** Packet stejného snapshotu má stabilní hash a jen existující target IDs.
- **T030-AC02:** Překročení budgetu je explicitní a neodstraní identity potřebné k validaci.
- **T030-AC03:** Příprava nespustí model, build ani semantic apply a nepřenese secrets/raw credentials.
- **T030-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T030-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T030-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Bounded packet; doc/code conflict; unsupported language; token budget; secret sentinel.**

- Navržený cílový soubor: `tests/test_t030_prepare_process_label_packet.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T030-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t030-prepare-process-label-packet`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T030, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T030** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize 2 — čistý veřejný kontrakt a bezpečné rozpočty

`prepare_process_label_packet(process, *, documents=(), conflicts=(),
token_budget=8000, char_budget=32000)` vrací pouze `{packet, candidate_template}`.
Vstup je existující ProcessView nebo jeho JSON document; nic se nenačítá ani
neukládá. ProcessView je ověřen až po kontrole cyklů, hloubky, počtu položek a
celkové velikosti, před kopií/JSON. Invalidní vstup vrací řízenou výjimku bez
obsahu vstupu. Native/compiler, feature.prepare, apply a CLI jsou mimo T030.

Mandatory envelope zachovává process/revision, definici/technical/content
fingerprints, původní baseline, přesný scope/context selection, úplné sorted
allowed target IDs (process + kroky + transitions) a source/evidence refs,
entry/exit/outcomes, minimální typed topology a původní evidence/status/coverage.
Content hash se váže na skutečný canonical ProcessView bez generation timestamp,
nikoli jen supplied baseline. Ordered collapse expansion se neřadí a neexportuje;
je součástí původního content fingerprintu. Existující význam/approval se nepřebírá.

Žádné raw labels, descriptions, conditions, source/config/annotation/proof prose
ani dokumentový text se neexportují. Omitted records nesou existující bezpečné
ref, pevný důvod a hash původního obsahu; cizí klíče/prose nejsou chybové zprávy.
Required identity/context selection zachovává bounded Unicode IDs i mezery a
punctuation ve skutečných source-path/code IDs. Odmítá řídicí/formatovací znaky,
rozpoznatelné credential či URI payloady a credential config keys ve selection. Nevyhovující mandatory ID se odmítne, nikdy nepřejmenuje.
Tato syntax není autentizace neprůhledného producentova ID; systém neklasifikuje
libovolný alfanumerický token jako secret. Prose/payload se proto neexportuje vůbec.

Explicit captured document má `ref`, `format` (HTML/MARKDOWN/TEXT/STRUCTURED),
`content_hash` (SHA256), `scope`, `context_ids`, `selection_provenance` (bezpečné
ref struktury) a optional `content`. Dodaný content musí mít přesný hash; bez
content je hash výslovně SUPPLIED_NOT_REVERIFIED. Žádný discovery/Confluence I/O.
Document refs/hash/scope/context bindings jsou mandatory; safe format/provenance
summary je optional a vstupuje v deterministickém pořadí celý nebo se vynechá.
Conflicts jsou pouze explicitní `{document_ref,target_id,source_refs,status}`,
status CONFLICT/UNKNOWN; refs musí patřit témuž výběru. Zůstávají review items,
nikoli NLP/technical authority. Bez těchto tvrzení comparison=NOT_EVALUATED.

Estimator je `ceil(UTF8_bytes(canonical({packet,candidate_template}))/4)` a
char cost počet Unicode znaků stejné finální serializace. Zahrnuje schema,
fixed-size packet hash, candidate template, omissions i samotné cost fields;
číselné délky se dopočítají konečným stabilním fixed pointem. Výslovné započítané
status_padding drží stejnou serializovanou šířku false/null i true/reason, takže
samotný overflow flag nemůže oscilovat na přesné hranici. Mandatory a actual
cost jsou odlišné. Bool/non-int/out-of-range budget je chyba. Soft overflow
mandatory identity/coverage je explicitní a nic z identity nezmizí. Optional doc
summaries jsou celé přijaty nebo mají úplný BUDGET omission. Hard input/packet
limit se nepřekračuje ani kvůli mandatory datům: řízená chyba, žádný artefakt.

Candidate template má prázdné annotations, packet hash a allowed schema odvozené
z process_model.ANNOTATION_FIELDS; proposed fields jsou pouze existující target,
label/description/source_refs/grouping_proposal, fixed PROPOSED, žádný technický
edge, condition, availability, nový outcome ani approval authority. Template není
aplikovaný ProcessView ani implementace validátoru T031. Pozitivní/negativní
matice zahrne collapsed input, pořadí/timestamp, hash změny, maličký i exact
budget, UTF8, cykly/shared/depth/huge input, secret sentinels, mixed scope,
unsupported/truncated input a zero-I/O/immutability/error cases.


Context selection podporuje existující service→context ID list, explicitní
service-selection row a inventory `{services:{service:{scope,status,contexts}}}`.
Identity fields a pořadí zůstávají, kompletní původní selection má vlastní hash;
coverage/diagnostics payload v selection se nahradí binding hashem a omission
záznamem, nikoli raw prose. Neznámý selection shape je řízená chyba.
Document selection_provenance má pouze povinné capture_id/source_ref a optional
context_ids; source_ref patří známému technickému ref nebo tomuto captured doc,
context_ids odpovídají doc výběru. Unknown note/config fields se neexportují.
Original compiler evidence refs se zachovají odděleně od annotation source-ref
allowlistu podle ProcessView; samotná existence odkazu není nový annotation target.

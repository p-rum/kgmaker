# T020 — Markdown katalog integračních rozhraní

- Task ID: `T020`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline: explicitní schválený draft stack nad T019 `abad2e30c1a1e422392585e6073995568b82a564`; ready/merge čeká na T019 a jeho prerequisites.
- Depends on: [T013](T-013_attach-interface-contracts.md); [T019](T-019_add-architecture-json-cli.md).
- Větev: `feat/t020-render-interface-markdown`
- PR title: `feat(t020): render interface markdown`
- Primární moduly: `nový architecture_render.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Markdown katalog integračních rozhraní. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T020-S01:** Renderuj katalog z ViewDocument: poskytovaná/používaná rozhraní, kontrakty, vlastníci a unresolved seznam.
2. **T020-S02:** Každý řádek obsahuje stabilní ID a odkaz do evidence sekce; neztrácej diagnostics při prázdném výsledku.
3. **T020-S03:** Escapuj Markdown pipes, backticks a nové řádky; řaď dle service/direction/protocol/ID.
4. **T020-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T020-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T020-AC01:** Všechny interface IDs z JSON jsou dohledatelné v Markdownu a nezmění status.
- **T020-AC02:** Nestandardní label neporuší tabulku ani nevloží další Markdown blok.
- **T020-AC03:** Prázdný katalog obsahuje scope a coverage důvod, nikoli tvrzení o absenci integrací.
- **T020-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T020-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T020-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Golden katalog; adversarial labels; unresolved; empty scope.**

- Navržený cílový soubor: `tests/test_t020_render_interface_markdown.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T020-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t020-render-interface-markdown`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T020, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T020** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize2 — schválený konkrétní renderer/CLI kontrakt

Tato revize zaznamenává Root APPROVE architektonického briefu a explicitního stacku,
neprohlašuje implementaci nebo finální upstream validation. Veřejná čistá funkce
`architecture_render.render_interface_markdown(document)` přijímá jediný přesný
`interfaces` ViewDocument nebo jeho schema1 JSON mapping a vrací celý Markdown
řetězec. Nečte zdroje ani soubory, nevolá provider/projector/scan/model/network/DB,
nevytváří nové identity nebo autoritativní store. Bounded shape/occurrence/depth/
scalar checks předcházejí modelové normalizaci, deepcopy a serializaci.

CLI přidává `--format markdown` pouze k T019 `architecture interfaces`. JSON je
nadále default; topology/explain/flow se nemění. Zpracuje tentýž upstream validated
snapshot a původní fingerprint, nikoli další capture nebo selection. T019 explicit
capture hranice, safe errors, strict/exit/cancel/BrokenPipe a nulová store mutace
platí beze změny. Render string je připraven před prvním stdout zápisem; export
nebo output file není součástí T020. Nesoulad expected fingerprint zůstává exit3,
validní partial0, strict incomplete4; invalid/schema/unsupported format2.

Fixní headings/tabulky obsahují scope/context/baseline/rules/coverage, poskytovaná
rozhraní, použitá rozhraní, povinnou generated/unclassified sekci se všemi ID,
contract bindings, unresolved, evidence/origins a diagnostics/limits. Řazení je
service/direction/protocol/ID s explicitním UNKNOWN, deterministicky i při různém
pořadí vstupů. Owner se neodhaduje z názvu ani neparsuje z ID. Logical interface ID,
contract revision fingerprint, release/context a Kafka realm/group zůstávají
odlišné. Cold HTTP definition není execution; regex topic není exact topic; stale
contract nezmizí, DTO jméno není compatibility. Evidence kind, polarity buckets,
resolution/freshness/coverage a runtime/data/deployment stav se nepovyšují.

Každý řádek uvádí původní ID a odkazuje na vygenerovaný interní SHA256 anchor
v evidence sekci. Chybějící evidence má explicitní UNKNOWN sekci. Cizí paths/URLs
nejsou automatické odkazy; T018 topology explain není interface resolver. Žádný
raw attribute/schema/prose dump: pouze bounded známá public scalar/ref pole,
případná opaque pole zůstávají explicitně mimo display kontrakt. Diagnostics a
coverage důvody včetně prázdného katalogu se neztratí. Render limit odmítne vstup
před outputem, nevrací potichu zkrácenou COMPLETE tabulku.

Použije se existující T019 public privacy guard; unsafe identity se odmítá fixní
bezpečnou chybou, nikdy nepřejmenuje. Escaped text v cells nesmí tvořit další
řádky/bloky/HTML/linky/images/fences; pipes/backticks/backslashes/HTML a Unicode
line separators mají konkrétní bezpečné inline kódování. Původní ID se ověřuje
z dekódovaného skutečného Markdown AST, nikoli jen substringem escapovaného textu.

Povinná testovací závislost je dev-only `markdown-it-py==3.0.0` a `mdurl==0.1.2`,
published wheel SHA256 v `tests/requirements-markdown.txt`. Parser má výslovně
enabled table rule. Příprava je explicitní mimo renderer/shared frozen inputs;
žádná runtime dependency/installace. T020 testy ověřují AST table/heading/link
strukturu i hand-labelled expected ID/status/refs. Real upstream source/contract
captures jsou oddělené od jasně označených model/protocol fixtures.

Veřejné RED před rendererem: golden provided/consumer+generated IDs/statusy,
adversarial label parsed AST, empty diagnostics/coverage a nepodporovaný formát
na actual CLI snapshot cestě. Následují unresolved/stale/buckets, realm/group/
context/revision identity, malformed/huge/cyclic/shared inputs, fixed privacy errors
na valid/invalid cestě a byte-identical input/store sentinel. Relevant pure upstream
regressions a CLI JSON default zůstávají zachovány. Před stagingem vyžadováno
nezávislé exact-source review; native/build/heavy/full zde zatím NOT_RUN a není
kvůli samotnému rendereru autorizováno.

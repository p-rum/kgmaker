# T014 — Projekce ověřených vzdálených bindingů

- Task ID: `T014`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T013](T-013_attach-interface-contracts.md); `T003-S07-W07` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí).
- Větev: `feat/t014-bind-remote-interfaces`
- PR title: `feat(t014): bind remote interfaces`
- Primární moduly: `workspace.py`, `nový interfaces.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Projekce ověřených vzdálených bindingů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T014-S01:** Konzumuj T003-S07-W07 service/contract/release mapping a promítni jej do vzdálených hran.
2. **T014-S02:** Rozliš HTTP request/response od async publish/subscribe; vzdálenou hranu nikdy netypuj jako JVM call.
3. **T014-S03:** Při více kompatibilních kandidátech uchovej kandidátní množinu, při chybějícím mappingu zachovej unresolved target.
4. **T014-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T014-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T014-AC01:** Stejná URL v nesouvisejících services nevytvoří potvrzené propojení.
- **T014-AC02:** Neodpovídající release/contract nevytvoří confirmed remote transition.
- **T014-AC03:** HTTP a Kafka přechody mají původní binding evidence a odlišnou sémantiku.
- **T014-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T014-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T014-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Duplicitní URL; incompatible release; dva target candidates; validní mapping.**

- Navržený cílový soubor: `tests/test_t014_bind_remote_interfaces.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T014-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t014-bind-remote-interfaces`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T014, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T014** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize 2 — explicitní W07 stack a čistá projekce

Výslovně schválený stack je W07 `5b39ec4` nad T013 `f43c9e0`.
T013/W07 actual/full a current-main integration zůstávají readiness gates;
source approval ani existence upstream API je nenahrazuje. Root schválil
architecture brief `/workspace/t014-architecture-brief.md` před implementací.

`project_remote_interfaces(workspace, graph, interfaces, *, captured,
scope='production', selected_contexts=None) -> ViewDocument` je pure API.
Volá existující W07 resolve_remote_mappings se stejným explicitním capture,
grafem, interfaces a výběrem. Nepřijímá caller report jako novou autoritu,
nevytváří druhý resolver, nevolá capture/upstream projectors/source I/O,
compiler/model/store/apply. Převádí static declared bindings na topology view.

Původní endpoint variant/service/evidence IDs zůstávají. Nové binding/boundary
IDs jsou namespaced obsahové identity workspace/source-release/rule; candidate
edge rozlišuje mapping, target variant/release, transport a context tuple.
HTTP remote request/response declaration a Kafka async publish/subscribe mají
odlišné relations, nikdy calls/dispatch/CFG. Původní endpoint proofs nezískají
silnější význam: nové remote declaration provenance je SOURCE_ONLY,
polarity UNKNOWN, bez runtime/payload/delivery proof. Ordinary HTTP client má
jen manifest EXPECTATION; provider contract BOUND_DECLARATION zůstává oddělený.

Celá kandidátní množina, unresolved_mapping_ids/reasons a scope/context se
zachová. AMBIGUOUS se nerozhodne, částečná kandidátní množina není unikátní
RESOLVED. Unmapped source i unresolved source selector mají explicitní boundary;
absence endpointu v partial catalog není negativní existence proof.
Capture-time freshness W07 není CURRENT: derived view objekty mají UNKNOWN,
metadata CAPTURE_TIME_ONLY a captured fingerprints. Endpoint freshness zůstává
původní. Overall coverage PARTIAL/UNKNOWN, runtime/delivery NOT_OBSERVED,
payload/deployment/availability UNKNOWN; unsupported KotlinHTTP zůstává UNKNOWN.

Input bounds před kopiemi/model validation; unsafe credential/control/URI IDs,
cykly/depth/shared/fanout a malformed inputs mají fixed nonsecret diagnostics.
Žádné raw source/config/schema/proof prose ani credential exporty. Hard limit
selže před publikací celé view; žádná tichá truncation či zvolený vítěz.
Deep input equality platí pro success i error, API nic neukládá.

Public RED a hand-labelled pure matrix ověří duplicate URL, explicit/missing/
incompatible pair, HTTP/Kafka semantics, ambiguity+incomplete candidates,
foreign/stale/tampered capture, no-I/O, privacy, bounds, immutability a původní
proof polarity. Actual W07 capture lze read-only reprojektovat jen se shodnou
source/native/selection provenance; není to nový compiler run. Nový native build
není potřeba pouze kvůli T014. Heavy actual/full až po nezávislém source review;
full případně na descendantu potřebuje ALL parent collected IDs superset,
byte/AST/global preservation a original native/artifact/broad hash receipts.
README/capability/acceptance/progress a note93 uvedou přesné skutečné důkazy,
nikoli tvrzení full/ready před jejich dokončením. T014 neimplementuje T027 ani
process continuation/živé remote volání.

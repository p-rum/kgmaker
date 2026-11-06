# T006 — Výběr kontextů pro více služeb

- Task ID: `T006`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-03
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T005](T-005_add-view-model.md); `T003-S02` (upstream; ověř konkrétní podporovaný kontrakt a acceptance, samotná existence zadání nestačí).
- Větev: `feat/t006-select-service-contexts`
- PR title: `feat(t006): select service contexts`
- Primární moduly: `graph_provider.py`, `views.py`, `workspace.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Výběr kontextů pro více služeb. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T006-S01:** Přidej explicitní context_selection mapování service/repo/module → context ID a fingerprint.
2. **T006-S02:** Ověř scope, freshness a kompatibilitu deklarovaného release/environment mappingu. U více variant vyžaduj volbu, neber první kontext.
3. **T006-S03:** SOURCE_ONLY dovol jen s označeným pokrytím; nevyvozuj kompatibilitu deploymentu z názvu profilu.
4. **T006-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T006-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T006-AC01:** Dvě služby mohou použít dva různé čerstvé kontexty bez promíchání modulových variant.
- **T006-AC02:** Nejednoznačný nebo stale kontext vrátí konkrétní diagnostiku a dostupné volby/next command.
- **T006-AC03:** Výběr ani jeho chyba nespustí compiler/build a nezmění uložený graph.
- **T006-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T006-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T006-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Dvě služby a dva profily; chybějící selection; stale classpath; SOURCE_ONLY.**

- Navržený cílový soubor: `tests/test_t006_select_service_contexts.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T006-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t006-select-service-contexts`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T006, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T006** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

## Revize 2 — role kontextu před výběrem (T006-S06–S08)

Výslovný stack baseline `8afabe7c5056b9ec45e04f1f8fcf3470d18f4c98`, navazující na
Kafka rev2; tato revize je SPECIFICATION, nikoli tvrzení hotové opravy. Sdílený
klasifikátor rozlišuje skutečný source/compiler kontext od kanonického
producer-owned workspace-derived kontextu před ownership a compiler selection.
Samotný prefix ID, SOURCE_ONLY ani přítomnost analyzer_version není authority.

- **T006-S06:** Reuse přesného producer kontraktu (známá verze, explicitní
  manifest binding, repo/module/source_set/scope, captured input identity, digest
  kontextu a původní selected compiler realm). Role validity není current source
  freshness; historický nevybraný derived kontext nesmí vyžadovat private compiler
  replay ani build jen pro určení role.
- **T006-S07:** Derived/unknown role není kandidát compiler výběru. Explicitní
  selector na derived nebo malformed/unknown claim vrací řízenou diagnostiku
  nebo strukturovanou selection chybu; nikdy source ownership fallback.
  Obyčejný legacy SOURCE_ONLY bez nového markeru zachovává dosavadní coverage.
- **T006-S08:** Zachovat celý původní graph/context/node/edge/proof snapshot,
  T006 freshness/variant a T007 foreign-path/hash/scope kontroly; čistá projekce
  nezapisuje ani nespouští worker/build.
- **T006-AC07:** Ve veřejném mixed Kafka snapshotu zůstane vybrán skutečný
  source/compiler kontext; derived declaration nemůže být compiler pin.
- **T006-AC08:** Unknown/malformed derived verze/realm/hash/identity má konkrétní
  diagnostiku bez mutace vstupů/store; genuine foreign source zůstává odmítnut.

Ověřit společně T006/T008, config-only/mixed/legacy SOURCE_ONLY, explicitní i cizí
selectory a relevantní katalogy T010/T011/T015/T016. Žádný nový catalog/store,
resolver, parser, worker contract nebo runtime availability proof.

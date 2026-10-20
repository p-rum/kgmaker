# T043 — Limity výkonu a velikosti

- Task ID: `T043`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 1
- Datum: 2026-10-20
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T017](T-017_filter-topology-scope.md); [T025](T-025_build-local-process-path.md); [T037](T-037_invalidate-derived-views.md).
- Větev: `feat/t043-bound-view-performance`
- PR title: `feat(t043): bound view performance`
- Primární moduly: `tests/benchmarks`, `architecture.py`, `business_process.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Limity výkonu a velikosti. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T043-S01:** Přidej reprodukovatelný generátor 100 services/10000 bindings a lokální CFG s cykly; zaznamenej runtime/hardware/Python.
2. **T043-S02:** Garantuj max-nodes/max-hops/max-depth a bounded diagnostics ještě před renderem; nenásob cesty neomezeným rozvíjením.
3. **T043-S03:** Změř cold/warm běh a peak memory; publikuj baseline a relativní regresní gate s tolerancí 25 % na stejném runneru, bez slibu univerzální latence.
4. **T043-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T043-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T043-AC01:** Výstup nikdy nepřekročí dokumentovaný budget vyjma explicitně omezených boundary summaries.
- **T043-AC02:** Zdvojnásobení jednoduchého lineárního vstupu nevytvoří exponenciální počet kroků.
- **T043-AC03:** Benchmark report obsahuje parametry a měření; překročení gate není skryto změnou fixture.
- **T043-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T043-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T043-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Synthetic scale; dense cycle; huge root CFG; bounded truncation; cold/warm comparison.**

- Navržený cílový soubor: `tests/test_t043_bound_view_performance.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T043-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t043-bound-view-performance`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T043, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T043** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

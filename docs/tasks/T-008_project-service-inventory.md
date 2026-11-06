# T008 — Inventář služeb a externích systémů

- Task ID: `T008`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-03
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T006](T-006_select-service-contexts.md); [T007](T-007_define-service-ownership.md).
- Větev: `feat/t008-project-service-inventory`
- PR title: `feat(t008): project service inventory`
- Primární moduly: `nový architecture.py`, `workspace.py`, `views.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Inventář služeb a externích systémů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T008-S01:** Sestav čistou projekci ServiceView z ověřeného ownership a provider snapshotu.
2. **T008-S02:** Přenášej repo-qualified IDs, scope, context a provenance; nezahrnuj testovací služby do production.
3. **T008-S03:** Externí systém bez checkoutu zachovej s explicitní deklarací a UNKNOWN interní implementací; konfiguraci použij jako důkaz, ne jako service node.
4. **T008-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T008-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T008-AC01:** Production inventář neobsahuje test fixture službu ani náhodný @Service bean.
- **T008-AC02:** Chybějící externí checkout nesmaže deklarovaný systém ani nevytvoří interní endpointy.
- **T008-AC03:** Stejný snapshot dává stabilní service IDs i po přejmenování zobrazovaného labelu.
- **T008-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T008-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T008-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Interní/externí systém; test scope; změna labelu; nedostupný repo.**

- Navržený cílový soubor: `tests/test_t008_project_service_inventory.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T008-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t008-project-service-inventory`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T008, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T008** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

## Revize 2 — workspace-derived declaration není service source (T008-S06–S08)

Výslovný stack baseline `8afabe7c5056b9ec45e04f1f8fcf3470d18f4c98`; současná
revize je SPECIFICATION. Skutečný mixed Kafka snapshot obsahuje cross-repo
contract soubor v derived context.source_files a dosavadní source ownership walk
končí foreign-qualified-path chybou. T007 strict foreign-source pravidlo zůstává.

- **T008-S06:** Před ownership použít společnou T006/T008 role klasifikaci
  opřenou o přesný existující producer-owned derived kontrakt, nikoli prefix
  či samotný SOURCE_ONLY. Původní source/compiler kontexty se nemění.
- **T008-S07:** Kanonické derived declarations zůstanou v plném graphu/proofs
  pro další katalogy, ale nejsou owned service source ani compiler kandidáti.
  Unknown/malformed explicitní claim má lokalizovanou diagnostiku, ne fallback.
  Klasifikace nevyžaduje private compiler replay; validity role je oddělená od
  current freshness historických nevybraných captured inputs.
- **T008-S08:** Zachovat source coverage a obyčejný legacy SOURCE_ONLY,
  repo-qualified ownership/scope/hash kontroly, explicitní pin pravidla a nulovou
  mutaci full graphu, workspace a posledního validního artefaktu při chybě.
- **T008-AC07:** Veřejný full mixed/config-only Kafka snapshot projde inventory
  bez foreign-path chyby a bez promotion derived inputů na source/compiler proof.
- **T008-AC08:** Legacy SOURCE_ONLY a production/test roots zachovají dosavadní
  PARTIAL/UNKNOWN i stabilní service IDs; skutečný foreign source zůstane odmítnut.
- **T008-AC09:** Prefix/mode-only, neznámá verze/role, malformed identity, manifest
  binding, repo/module/scope, captured hash/path a foreign selector mají konkrétní
  fail-closed výsledek bez mutace vstupů, cache nebo store.

Regrese zahrnuje T006/T008 a katalogy T010/T011/T015/T016 nad původním full
graphem; bounded actual captured mixed snapshot je oddělen od hand-built fixture
a config-only testů. Žádný nový compiler build, parser ani availability promotion.

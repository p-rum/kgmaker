# T033 — Katalog identifikovaných procesů

- Task ID: `T033`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T024](T-024_discover-process-triggers.md); [T032](T-032_persist-process-review.md).
- Větev: `feat/t033-catalog-business-processes`
- PR title: `feat(t033): catalog business processes`
- Primární moduly: `nový business_process.py`, `process_store.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Revize 2 — explicitní read-only katalog

Baseline je výslovně schválený stack T032 `4fea8eea83395599da4fc994079676856ac87b0c`
(source3652 APPROVE, full/dependency/current-main dosud PENDING). Architektura
`/workspace/t033-architecture-brief.md` přijata koordinátorem2026-11-05.

Nový `process_catalog.py` rozšiřuje existující model/T024/T032 projekcí; již existující
`business_process.py` je T026 collapse a zůstane byte-exact. Veřejné API:
`catalog_business_processes(root, trigger_inventory, *, current_processes=(),
historical_processes=(), review_inputs=(), aliases=())`. Jde o explicitní read-only
adapter: žádný build/discovery/network/model/graph scan ani zápis. Čte pouze T032
store pro explicitně dodané snapshots přes `read_process_reviews`, ne callerem
podvržený APPROVED bundle. Root je již existující schválený adresář. Pevné chyby
`ProcessCatalogError` neobsahují raw input/path/exception chain.

Vstupy: aktuální validovaný T024 ViewDocument (exact kind/rule, selected scope),
explicitní validované aktuální a historické ProcessViews. Chybějící historický
ProcessView nelze rekonstruovat z T032 semantic metadata. Žádný nový archive/index.
Právě jeden explicitní current snapshot pro process_id+scope; canonical byte-exact
(normalizované modelové) duplikáty se deduplikují, kolize obsahu/revision odmítají.
Historical snapshots mají explicitní revision/content/technical hashes; stejná
identity+revision s rozdílným obsahem je chyba i napříč current/history. Kontext/scope
se nesmí přimíchat. Jiné revision stejné identity jsou samostatné immutable záznamy.

`review_inputs` je bounded list záznamů exact `process_id`, `documents`, `conflicts`;
nejvýše jeden pro dodanou identitu. Bez záznamu prázdné explicitní captures. Žádné
skryté načtení dokumentů; changed captures znamenají T032 NEEDS_REVALIDATION.
Výstup zachová per-member T032 effective status, current/historical designation,
originální proces/trigger/outcome/owner IDs, revisions/fingerprints, static technical
coverage/status/limits a evidence refs. U historického snapshotu se žádné aktivní
labels ani available path nepublikují; původní rozhodnutí/hashes zůstanou čitelné.
Candidate není APPROVED; reviewed může být technicky PARTIAL/UNKNOWN.

Trigger se připojuje pouze exact ID v supplied T024 inventory a same scope/context.
Absence se jmenuje NOT_IN_CURRENT_INVENTORY a kvalifikuje se inventory coverage;
není univerzální důkaz odstranění, protože discovery je PARTIAL. Chybějící trigger
má inactive-in-current-selection historical záznam, nikoli dostupnou cestu. Některé
chybějící refs zachovají per-trigger status a partial agregaci. Current presence
není proof registration/execution/runtime/data availability; ty zůstávají UNKNOWN.
Nevzniká implicitní T025 expansion nebo name/symbol fallback.

Stable `selection_id` váže exact canonical process_id+scope a nezávisí na label,
owner/revision/order. Canonical original IDs jsou vždy také ve výstupu. Dva různé
triggery/procesy se stejným label/helper zůstávají samostatné. Explicit `aliases`
obsahuje pouze one-hop `{alias_process_id, canonical_process_id}` pro existující
supplied identity ve stejném scope a exact context selection+context IDs. Canonical
target je supplied; unknown/self/chains/cycles/multiple winners odmítají. Alias group
ponechá VŠECHNY původní členy/revisions/triggers a review states; nikdy nepřenese
approved label nebo availability z jednoho člena na jiného, nemá group-level active
labels/availability ani libovolného payload winnera. Bez aliasu žádný fuzzy merge.

Formát1 limity před copy: T030 bounded plain-input guard; nejvýše256 supplied
snapshots (current+history před dedup),256 alias/review-input rows, T024 nejvýše4096
trigger nodes; maximálně2MiB finálního canonical JSON, hard fail bez tichého truncation.
Raw technické label/doc/proof/config prose se neexportují. Zobrazené semantic texty
jen přes validované T032 current APPROVE; IDs se zachovají Unicode/path-space,
známé credentials/control se odmítají genericky se stejnými privacy limity jako T030.
Technická fakta/source IDs nejsou prohlášena runtime observation nebo auth.

## Cíl a hranice samostatné dodávky

Katalog identifikovaných procesů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T033-S01:** Seznam procesů obsahuje trigger, owner, semantic review, technical coverage, outcomes a revision.
2. **T033-S02:** Deduplikuj jen podle explicitní identity/alias; podobné labely nebo shared helper nesloučí dvě operace.
3. **T033-S03:** Rozliš candidate, reviewed a historical/stale proces; poskytni stabilní selection ID pro render.
4. **T033-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T033-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T033-AC01:** Dva procesy s totožným názvem a rozdílným triggerem zůstanou samostatné.
- **T033-AC02:** Candidate není prezentován jako schválený business proces.
- **T033-AC03:** Smazaný trigger zachová historický záznam, ale není aktivní dostupnou cestou.
- **T033-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T033-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T033-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Duplicitní label; více triggerů; alias; odstraněný endpoint; stale revision.**

- Navržený cílový soubor: `tests/test_t033_catalog_business_processes.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T033-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t033-catalog-business-processes`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T033, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T033** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

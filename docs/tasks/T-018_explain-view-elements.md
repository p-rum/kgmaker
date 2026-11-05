# T018 — Dohledání zdrojů high-level objektů

- Task ID: `T018`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T009](T-009_propagate-view-evidence.md); [T016](T-016_aggregate-service-topology.md).
- Větev: `feat/t018-explain-view-elements`
- PR title: `feat(t018): explain view elements`
- Primární moduly: `nový architecture.py`, `graph_provider.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Dohledání zdrojů high-level objektů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T018-S01:** Implementuj explain(view_id, element_id) přes original_ids a evidence_refs až na repo/path/range/hash.
2. **T018-S02:** Přidej seznam kontextů, aggregation rule version a důvody UNKNOWN/PARTIAL.
3. **T018-S03:** Přístup je read-only; stale nebo nedostupný zdroj se označí, neotvírej externí systémy a nevydávej jiný snapshot za původní.
4. **T018-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T018-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T018-AC01:** Každá neprázdná agregovaná hrana má dohledatelné podkladové IDs nebo explicitní unavailable boundary.
- **T018-AC02:** Chybějící source range nevede k vymyšlenému číslu řádku.
- **T018-AC03:** Explain na stale snapshotu zachová původní fingerprint a upozorní na neaktuálnost.
- **T018-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T018-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T018-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Multi-repo provenance; smazaný soubor; unknown element; agregovaná hrana.**

- Navržený cílový soubor: `tests/test_t018_explain_view_elements.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T018-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t018-explain-view-elements`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T018, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T018** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize 2 — explicitní snapshot explanation a confined source status

Root schválil `/workspace/t018-architecture-brief.md` a zvolil implementaci
optional explicit source-status capture pro skutečné deleted/stale AC.
Výslovný stack T017f22a698 (T016806/T01409), T009/T016 a optional T017filtering;
final current T012/T013/W07 integration/actual/full zůstává dependencygate.
Žádná readiness ani nový compiler/runtime proof z této revize neplyne.

`explain_view_element(view, element_id, *, captured, graph=None,
filtering=None, source_status=None) -> report` je pure. Reuse pure T016 aggregate
pro přesnou rederivaci origin topology; optional T017 celý filtering envelope
se přes jeho canonical criteria rederivuje původní filter API a musí přesně
odpovídat view+filtering. View ID i element ID patří tomuto snapshotu, nikdy
fallback novějšího graphu/LATEST. Unknown element má UNKNOWN_ELEMENT bez
hledání stejného jména jinde. Frontier není rendered element a nemá implicitní
nový technický target.

Přes origin interface/mapping/release/input-edge/binding inventories a evidence_refs
expanduj přesné immutable IDs. Původní SUPPORTING/CONTRADICTING/UNKNOWN partitions,
evidence kind/freshness, scope/context tuple, realm/group a aggregation/filter
versions zůstávají. Omitted candidates, incomplete/truncated boundaries ani
conflicts se nesmějí stát unikátním/current/observed proof. Raw source/config/
SQL/schema/proof text se neexportuje, jen safe refs/typedmetadata/hash omission.

Optional PUBLIC KnowledgeGraph musí přesně odpovídat captured.input_binding.graph_fingerprint.
Sanitizované topology payload hashes nemají zpětně path/range: bez původního grafu
nebo podpory exact canonical locator contract je explicit SOURCE_LOCATOR_UNAVAILABLE.
Nečti private stores ani současný graph pro opravu chybějících originů. Přímý
compiler locator musí mít exact canonical node+symbol/site, selected context,
scope, repo/path a graph.files==context.source_files==captured SHA. Graph1/2/legacy
bez této vazby zůstávají ref-onlyUNKNOWN. Source-only declaration není novýcompilerproof.
Chybějící range/start/end/column zůstává null, nevymýšlej line1/end z jiné informace.

`capture_explanation_source_status(workspace, graph, *, captured, reference_ids)`
je oddělená explicitní I/O fáze. Každé requested reference ID se nejdříve odvodí
z bound public graphu/selected context/source hash; caller neposílá volné path/range.
Loaded declared workspace/rawmanifest a fingerprint musí odpovídat capture,
repo musí patřit deklarovaným roots. Teprve potom bounded confined reads přes
shared safe_path; symlink/traversal/absolute/foreign refs odmítnout bez echo.
Žádné externí URL/model/build/worker/sourceexcerpt. Capture vrací jen původní
locator inventory/hash a current hash/status, bound na original graph/capture.

Pure explanation bez source-status má NOT_CHECKED, nikdy CURRENT. Status capture
CONTENT_MATCH platí jen pro přesně přečtený soubor, nepovýší stale compilercontext
ani remote mapping UNKNOWN/CAPTURE_TIME_ONLY. SOURCE_STALE obsahuje captured a
currenthash odděleně; SOURCE_MISSING/UNAVAILABLE neznamená codeabsence/žádnýservice.
Původní view/graph/baseline/content fingerprints zůstávají původní. Invalidní
inputs/failure nic nemění a source-status se nepublikuje automaticky.

Strict version/schema, cycle/depth/shared/per-occurrence/string/fanout limits
před copies/JSON a hard reportinventory limit; žádná tichá truncation reference
chain. Fixednonsecret diagnostics, unsafe credential/control/userinfo requiredIDs
odmítnout, nikoli přejmenovat. ValidUnicode/pathspaces se zachovají. Optional
source adapter načte jen bezpečné deklarované soubory, nikdy application/network/DB.

Public RED před API: multi-repo aggregateedge expansion, missingrange, unknown
ID, unsupported/missinggraph, actualfile match/change/delete a originalfingerprint.
Negatives poisonedgraph/filter/view/source-status, foreignpath/repo/context/
realm, stalecompiler/proofbuckets, symlinks/traversal, bounds/secret/noI/O pure
část + deepinput/sentinel equality. Source-backed captures jsou read-onlyreprojection,
ne nový compiler run. Relevantní T016/T017/T014/W07/View/T009 pure potom independent
source closure; heavy/full až Rootapproval, případný descendantfull jen s ALLparent
collected IDs a exactruntime/global/test/native/receipt proof.

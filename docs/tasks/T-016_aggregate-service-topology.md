# T016 — Agregace topologie služeb

- Task ID: `T016`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T014](T-014_bind-remote-interfaces.md); [T015](T-015_project-data-resources.md).
- Větev: `feat/t016-aggregate-service-topology`
- PR title: `feat(t016): aggregate service topology`
- Primární moduly: `nový architecture.py`, `views.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Agregace topologie služeb. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T016-S01:** Agreguj interface bindings na service/resource/channel úroveň podle relation a realm.
2. **T016-S02:** Více HTTP volání lze sloučit do souhrnné hrany se seznamem origin interface IDs; neslučuj různé protokoly a směry.
3. **T016-S03:** Kafka modeluj přes channel, aby více consumerů nepůsobilo jako jediné synchronní volání; nezahrnuj DTO/enum centralitu.
4. **T016-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T016-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T016-AC01:** Souhrnná hrana se rozbalí na přesnou množinu původních rozhraní.
- **T016-AC02:** Publish/consume hrany nejsou zobrazeny jako přímé synchronní service call.
- **T016-AC03:** Přidání hojně používaného enumu nezmění servisní topologii.
- **T016-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T016-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T016-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Fan-out; paralelní HTTP/Kafka; několik endpointů; enum noise.**

- Navržený cílový soubor: `tests/test_t016_aggregate_service_topology.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T016-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t016-aggregate-service-topology`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T016, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T016** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize 2 — jeden explicitní capture a pure aggregate

Root schválil brief `/workspace/t016-architecture-brief.md` včetně nezávislého
architect návrhu B. Explicitní stack T01409d1a93/W075b39 a ověřený main3bef
(T015/W08) je integrován před capture. Dependency actual/full/final review nejsou
nahrazeny source approval. Produktové upstream API se kvůli T016 nemění.

`capture_topology_inputs(manifest, *, scope='production', selected_contexts=None)`
je jediná I/O fáze. load_workspace + snapshot_workspace(persist_cache=False)
zachytí jeden workspace/graph/source_coverage closure. T015, W07 capture a T014
obdrží přesně stejné objekty a výběr. W07 canonical_interfaces a captured object
jdou přímo do T014. Poté load/snapshot closure znovu ověří manifest/source/schema/
graph/coverage; nestabilní čtení selže, neopravuji původní hash. Žádný inspect/build,
DB/model ani publikace souboru. Existující migration replay není runtime proof.

Versioned handoff váže workspace ID/raw manifest SHA, společný input binding
(declarativní workspace, graph, complete coverage, requested selectors/scope),
actual inventory context_selection, W07 capture ID/selection a oddělené původní
T014/T015 baseline/content fingerprints plus canonical dokumenty. T014 selection
musí přesně odpovídat W07.capture.selection; všechny tři W07 canonical interfaces
musí mít stejné actual inventory selection a T015 musí odpovídat právě jemu.
Nesrovnávají se neekvivalentní baseline/selection formáty. Envelope digest je
consistency handoff, nikoli autentizace libovolného koherentního replacementJSON.

`aggregate_service_topology(captured) -> ViewDocument` je pure, bez load/projector/
snapshot/private proof/FS/network/process/model. Bounds před kopiemi/JSON/modely;
strict version/schema, safe IDs, exact complete input document fingerprints a
scope/selection/baseline bindings. Optional očekávaný input ID není live freshness.
Malformed input má fixed nonsecret diagnostics, všechny inputs zůstávají stejné.

ViewDocument topology agreguje jen existující services/resources a typedremote
claims, ne DTO/enum/type centralitu. HTTP summary key zahrnuje service pair,
relation/direction, scope/context a contract/release boundary; expansion zachová
přesné origin interface/mapping/release/input-edge IDs. Kafka channel ID váže
workspace+explicit broker realm+exact topic, publish a consume jsou oddělené,
consumer groups a origin inventories zůstávají oddělené. Unknownrealm/pattern se
neslévá s reálným channel. Missing/ambiguous ownership či mapping zůstává boundary,
ne name/URL fallback; AMBIGUOUS/incomplete/truncated se nesmí stát unikátníRESOLVED.

Původní evidence/buckets/scope/context jsou oddělené od mappingdeclarations;
SOURCE_ONLY nevytváří SYMBOL_RESOLVED/runtime proof. Remote UNKNOWNfreshness a
CAPTURE_TIME_ONLY zůstávají; runtime/deployment/payload/delivery UNKNOWN či
NOT_OBSERVED. Celková coverage nepřesáhne upstream. Safe typed summaries/refs,
žádné raw SQL/schema/config/proof prose. Credential/userinfo requiredID se odmítne,
nenahradí; Unicode/pathspaces zůstávají. Hard bound selže před vrácením view,
než aby skryl kandidáty nebo prohlásil neúplný výběr za unikátní.

Public RED a pure matrix: reversible HTTP expansion, Kafka fanout/groups/realms,
paralleltransport, enum noise bez identity/expansiondelta (inputhash se smí změnit),
missing/ambiguous/contradicting/stale boundaries; crossworkspace/selection/baseline/
viewtamper, unknownversion/unsafeIDs/depth/cycle/shared, noI/O pureaggregate a
input/storeimmutatibility. Capture actualpublicnegative zahrne manifest/source/
schema změnu mezi fázemi, rozdílnévalidníupstreambaselines positive. Actual W07
savedcaptures se jenreprojektují po vlastnísource review a jejich dokončení;
nejde o novýnative run. Heavy/full až po Root source closure. Naturaldescendantfull
potřebuje ALLparenttestIDs a exactruntime/test/global/native/receipts closure.

Shared input_binding.coverage_fingerprint musí být přesně stejný jako
W07 remote_selection.source_coverage_fingerprint: oba jsou digest téhož objektu,
nejde o porovnání různých baseline formátů. Capture odmítá rozdíl před T014
projekcí a pure consumer před agregací, i po recomputed outer/shared hash.

Endpoint owner není univerzálně catalog ID: canonical T012 Kafka má plain
service_id, HTTP catalog form. Pro obě formy použij pouze explicitní selected
release.service_id -> přesný catalog service ID a exact endpoint.interface_id/
owner equality; cizí owner se neparsuje ani nehádá podle jména.

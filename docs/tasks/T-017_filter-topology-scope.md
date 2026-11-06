# T017 — Filtrování a omezení velikosti topologie

- Task ID: `T017`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T016](T-016_aggregate-service-topology.md).
- Větev: `feat/t017-filter-topology-scope`
- PR title: `feat(t017): filter topology scope`
- Primární moduly: `views.py`, `nový architecture.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Revize 2 upřesňuje čistý kontrakt nad explicitní pracovní závislostí T016
`f05b13b87b2b3255c4a67fde7e5279223cef4144`. Source review T016 není dokončením
jeho dependency/full gate. T017 zůstává samostatná větev a PR; před ready musí
převzít finální schválené dependency a aktuální main. Implementační místo je nový
`src/kgmaker/topology_filter.py`, který reuseuje `ViewDocument` a T016; nevytváří
další store, resolver ani katalog.

Filtrování a omezení velikosti topologie. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T017-S01:** Přidej focus service, směr incoming/outgoing/both, max-hops a max-nodes nad již sestavenou topologií.
2. **T017-S02:** Deterministicky vybírej okolí a pro odříznuté vazby vytvářej boundary objects s omitted IDs/counts.
3. **T017-S03:** Prázdný filtr, neexistující service a node budget rozliš; nespojuj přes vynechané uzly novou fiktivní hranou.
4. **T017-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T017-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T017-AC01:** Stejný focus a budget vytvoří stejný výběr bez ohledu na pořadí vstupu.
- **T017-AC02:** Oříznutí je viditelné v datech i coverage a nikdy nehlásí úplnost.
- **T017-AC03:** Odstranění prostředního uzlu nevytvoří novou přímou vazbu jeho sousedů.
- **T017-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T017-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T017-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Hvězdicová topologie; cyklus; nulový/neplatný budget; unknown focus.**

- Navržený cílový soubor: `tests/test_t017_filter_topology_scope.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T017-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t017-filter-topology-scope`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T017, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T017** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

## Přesný kontrakt revize 2 před implementací

`filter_topology(topology, *, focus_service=None, direction='both', max_hops=None,
max_nodes=200, relations=None, scope=None, context_ids=None)` přijímá již sestavený
T016 `ViewDocument` nebo jeho JSON dokument. Vrací `{schema_version, rules_version,
document, filtering}`. Funkce nečte soubory ani zdroje, nespouští capture, projektory,
procesy, model, síť ani store. Jde o důvěryhodný lokální snapshot; hash neověřuje
autenticitu libovolně nahrazeného vstupu ani fyzickou freshness checkoutu.

Focus je přesné ID existujícího uzlu `service`; `None` znamená bez focus omezení,
prázdný řetězec je chyba, neznámé platné ID vrací prázdný `UNKNOWN_FOCUS` výsledek.
Směr je incoming/outgoing/both. Hops počítají skutečné hrany, tedy Kafka
service→channel→service jsou dva hops. Nula hops je platná; node budget musí být
celé číslo alespoň 1, bool/float/záporná hodnota jsou chyby. Nezaměňuj neznámý focus,
prázdnou množinu relations a kapacitní ořez.

`relations=None` zachová všechny zachycené relation; explicitní prázdný seznam
nezachová žádnou. Scope může pouze potvrdit scope snapshotu; jiný je řízená chyba.
Kontextový filtr pouze omezuje původní celé context tuples; nikdy je nezkracuje
ani nepředstírá nový T006 výběr. Neprokázaný prázdný tuple není wildcard.
Původní `context_selection` a baseline zůstanou zachované, filtr se zapíše odděleně.

Deterministický BFS volí uzly podle vzdálenosti a ID, nikoli pořadí vstupu nebo
centrality. Bez focus se použije kanonické pořadí ID. Zachovají se jen původní
způsobilé hrany s oběma ponechanými endpointy; nevznikne shortcut přes vynechaný uzel.
Resolution, freshness, evidence a jejich polarity se nezlepší odebráním alternativ.

`max_nodes` počítá všechny skutečně vrácené uzly včetně existujících boundaries.
Nové cutoff boundaries jsou pouze `filtering.frontier` metadata a nezvětšují graph.
Metadata obsahují přesná vynechaná node/edge IDs, důvody, referenční original
interface/mapping/release IDs a oddělené unikátní počty. Zachované summary edges
ponechají celý původní expansion inventory. Detached exclusions se nespojí s focus.
Žádné vynechání nehlásí COMPLETE; upstream truncation a nejistota se zachovají.

Před normalizací se kontrolují cykly, hloubka a per-occurrence počet/velikost vstupu;
sdílené acyklické hodnoty se započítají opakovaně. Samostatný hard limit úplného
výstupního metadata inventáře při překročení odmítne výsledek, nikdy nezamlčí IDs.
Chyby mají pevné kódy bez vstupních tajných hodnot. Unicode a mezery v platných
immutable IDs se zachovají; rozpoznané credential/userinfo identity se odmítnou.
Technický vstup, zdrojový checkout i poslední artefakt zůstanou beze změny.

Po public RED následuje star/cycle/channel fixture, shuffled-input determinismus,
incoming/outgoing/both, budget=1/0/bool, hops=0, unknown focus, prázdné relations,
foreign scope/context tuples, žádné shortcut, ambiguity po ořezu, přesné omissions,
provenance/polarity a upstream truncation, privacy/bounds a zákaz I/O. Required full
může dodat jen doložený descendant s úplným parent collected-ID supersetem a přesnou
source/native/test closure; collection či pure sada nejsou full PASS. GH CI je
doplňující podle uživatelské merge politiky v AGENTS, nikoli náhrada lokálních gate.

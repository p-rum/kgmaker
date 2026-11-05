# T031 — Validace agentových návrhů

- Task ID: `T031`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T023](T-023_define-business-process-model.md); [T030](T-030_prepare-process-label-packet.md).
- Větev: `feat/t031-validate-process-annotations`
- PR title: `feat(t031): validate process annotations`
- Primární moduly: `nový process_semantics.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Cíl a hranice samostatné dodávky

Validace agentových návrhů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T031-S01:** Validuj labels, descriptions, grouping proposals a business outcomes vůči packet hash, target IDs a evidence refs.
2. **T031-S02:** Technické edges/conditions/availability nesmí agent měnit; odmítni dodatečná technická pole.
3. **T031-S03:** Proposal může zůstat PENDING nebo CONFLICT; validace je read-only a stale packet je rejected.
4. **T031-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T031-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T031-AC01:** Vymyšlený step ID a jiný packet hash jsou odmítnuty bez zápisu.
- **T031-AC02:** Přejmenování business kroku zachová všechny technické vlastnosti.
- **T031-AC03:** Rozpor dokumentace s kódem zůstane review item, nikoli přepsaná implementace.
- **T031-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T031-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T031-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Forged target; stale packet; extra technical fields; valid Czech labels; contradiction.**

- Navržený cílový soubor: `tests/test_t031_validate_process_annotations.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T031-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t031-validate-process-annotations`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T031, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T031** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.


## Revize 2 — explicitní T030 stack a řízené validační reporty

Baseline tohoto samostatného stacku je T030 `070e709` nad main `deb3691`.
T030 source je schválen pro validaci, required full zatím nepřebírá tvrzení PASS.
API se připojí na konec stejného process_semantics.py; původní T030 functions,
imports/constants a všech47testů zůstane byte/AST exact. Žádný nový worker/build.

`validate_process_annotations(process, packet, candidate, *, documents=(),
conflicts=()) -> report` je čistá funkce bez I/O/provider/Git/model/apply/store.
Normální invalidní data (včetně cyklu/oversize/unsafeID, malformed process/docs,
stale/forgedpacket, unknownfield nebo špatného návrhu) vrací report
`valid=False, validation_status=REJECTED, annotations=[]` s pevnými nonsecret
code diagnostics; nevyhazují input-bearing exception. Neočekávané programové
chyby mimo podporovanou validaci se nemaskují jako business výsledek.
Valid proposal má `valid=True, validation_status=VALID`, ale semantic review
zůstává PENDING/CONFLICT a každá normalizovaná anotace pouze PROPOSED. Žádný
report není approval, změněný ProcessView ani publikovaný návrh.

Před kopií/JSON se použijí existující per-occurrence/depth/text/JSON bounds nad
všemi explicitními vstupy. Rebuild úplného očekávaného T030 packetu z aktuálního
process/docs/conflicts používá ověřené původní packet budgets; musí souhlasit
celý canonical packet, version/rule/hash/schema/allowed IDs/coverage/input binding.
Samotný caller self-hash nestačí. Připouští se pouze packet schema1 a T030rule1;
žádná tichá migrace. Dodané current inputs nejsou fyzicky fresh/autentizované
proti útočníkovi, který může nahradit všechny vstupy; jde o content consistency.

Candidate top-level má přesně template keys schema_version(int1),packet_hash,
annotations(list). Max256anotací; unique nonempty safe IDs nesmějí kolidovat
s technical/process targets. Records smějí pouze rederived annotation_schema
fields a fixed PROPOSED. Label max512Unicode znaků, description max4096,
neprázdné; známé credential/URI/control payloady se odmítnou bez echo. Description
smí běžný newline/tab, nikoli jiné controls. Arbitrary unlabeled secret nelze
univerzálně rozpoznat; semantic prose není technická ani approval authority.

source_refs jsou unique existing allowed refs (i explicit doc refs), grouping
unique nonempty existing step IDs, nikoli transitions/proof/source IDs. Prázdné
citace jsou strukturálně přípustné stejně jako v process_model, ale zůstávají
explicitní PENDING review item. Vyžaduje se label/description/grouping. Existing
outcomes lze pojmenovat pouze přes jejich existující target_id; žádný nový
outcome/node/edge/condition/availability/context/scope/confidence field.

Normalizace řadí anotace podle ID a reference/group members jako množiny; text
nemění. Různé hodnoty stejného label/description/grouping pole u stejného targetu
se zachovají všechny a vytvářejí strukturální CONFLICT review item, nikdy first/
last winner. Komplementární pole se nedeklarují jako NLP contradiction. Duplicate
annotation IDs jsou rejected i při stejném obsahu. Grouping je návrh, nikoli T026
SESE certifikát či změna topology/order.

Captured doc/code CONFLICT/UNKNOWN z rederived packetu zůstává ve review_items,
comparison vždy NOT_EVALUATED; neprovádí se NLP ani inference NO_CONFLICT.
Report obsahuje pouze ověřený packet binding/current technical hashes/status/
uncertainty, normalized PROPOSED annotations a pevné diagnostics/review items.
Při chybném bindingu není untrusted packet hash reflektován; při následné chybě
candidate může report uvést pouze již ověřený current binding. Všechny inputs,
source ProcessView a technical subtree/fingerprint zůstávají beze změny.
T032 review/apply a T034 CLI jsou samostatně pending.

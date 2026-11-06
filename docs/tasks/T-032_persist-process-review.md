# T032 — Schválení a revizní historie procesů

- Task ID: `T032`
- Parent: [T004 — High-level zobrazení projektu](4_addHighLevelProjectViews.md)
- Revision: 2
- Datum: 2026-11-05
- Stav: SPECIFICATION — cílové chování, žádná implementace se tímto dokumentem neprohlašuje za hotovou.
- Baseline návrhu: `c39f8adf2e3004d201960a18575bc7659808ae94` na `main`; před implementací ověř aktuální HEAD a související otevřené PR.
- Depends on: [T031](T-031_validate-process-annotations.md).
- Větev: `feat/t032-persist-process-review`
- PR title: `feat(t032): persist process review`
- Primární moduly: `nový process_store.py`, `process_semantics.py`. Názvy nových modulů jsou návrh; při existujícím ekvivalentu jej rozšiř a odůvodni umístění v PR.

## Revize 2 — závazný bounded kontrakt

Implementační baseline je explicitně schválený stack T031
`a3590aaca15a8caa53fb73671ce57f6970e2c6af` / T030 `3ae82b4` / main `c193748`.
Upstream full je samostatný probíhající důkaz, nikoli hotová závislost.
Architektura: `/workspace/t032-architecture-brief.md`, přijata koordinátorem.

Veřejné API nového `kgmaker.process_store`:

- `prepare_process_review(process, packet, candidate, *, documents=(), conflicts=())`
  je čisté. Znovu volá T031 nad aktuálními explicitními vstupy; invalidní návrh
  vyvolá `ProcessReviewError` s pevným kódem bez hodnot/cest vstupu. Vrací verzi1,
  normalizované návrhy (seřazené podle ID), payload hash, úplný baseline binding,
  baseline hash, oddělené dokumentové bindings, technické nejistoty a review status.
- `persist_process_review(root, process, packet, candidate, *, action, reviewer,
  operation_id, expected_head, expected_payload_hash, expected_baseline_hash,
  documents=(), conflicts=(), cancelled=None)` explicitně zapíše rozhodnutí
  `APPROVE` nebo `REJECT`. `expected_head=None` znamená prázdnou historii.
  Tokeny musí přesně souhlasit s novou lokální rederivací; operace není automaticky
  rebased. Identifikátory zachovává přesně, známé credential formy odmítá genericky.
  Reviewer je lokální deklarace, nikoli autentizovaná nebo technická evidence.
- `read_process_reviews(root, process, *, documents=(), conflicts=())` vrací historii,
  head a oddělené aktivní schválené návrhy; aktuální baseline přepočítá s uloženými
  validovanými budgets. Při změně je effective status `NEEDS_REVALIDATION`, historie
  původního APPROVE se nemění a aktivní návrhy se nepřenášejí do nové baseline.
  Neexistující store vrací explicitní EMPTY. Poškozený/neschválený formát hard fail.

APPROVE blokuje jak T031 field CONFLICT, tak captured doc/code CONFLICT; není
acknowledgement bypass. REJECT smí zaznamenat strukturálně validní konfliktní návrh,
ale nepublikuje nové aktivní labels a nevymaže starší schválenou revizi. Prázdný
návrh je odmítnut (`EMPTY_PROPOSAL`). Každé nové rozhodnutí vytvoří monotónní
semantic revision; `ProcessDefinition.revision`, technický ProcessView a graph
zůstávají beze změny. Dokumentové citace jsou vlastní namespace bindings, nikdy
falešná technical provenance nebo nové `known_sources`.

Jeden verzovaný JSON envelope pod `.kgmaker/process-reviews/<hash>.json` obsahuje
úplnou immutable historii, hash chain a head; hash názvu váže exact process ID+scope.
Žádný samostatně publikovaný receipt/head/history. Limity formátu1: nejvýše128
rozhodnutí a 2MiB serializovaného envelope; před čtením/copy/serializací bounded
vstupy, překročení hard fail bez pruning. Uložený JSON odmítá duplicate keys,
nonfinite čísla, neznámá pole, neplatné typy/hash chain a symlinky.

Podpora zápisu je POSIX stdlib `fcntl.flock` plus společný thread lock pro všechny
spolupracující volající. Windows vrací řízené UNSUPPORTED, dokud není skutečně
ověřen. Lock pokrývá read/CAS/write/fsync/replace. Persistent lock inode se nemaže;
inicializace lock infrastruktury není semantic publication. Podpora není obranou
proti hostile same-privilege změnám adresářů/symlinků během operace. Předem známé
symlinky/confinement chyby jsou odmítnuty. Nepoužívá subprocess/network/model/Git.

Linearizační bod je jediný atomic replace sibling temp. Před replace cancellation
nebo chyba zachová poslední JSON a uklidí temp. Po replace je výsledek COMMITTED
nebo INDETERMINATE (např. directory fsync selže); nikdy nepravdivý rollback.
Operation ID umožní recovery. Stejný operation ID + přesné akční/payload/baseline/
reviewer/predecessor binding vrací původní receipt bez zápisu/změny mtime; po novějším
head explicitně `is_current=false`. Jiný obsah stejného operation ID je konflikt.
Atomic visibility a CAS nejsou slib power-loss durability libovolného filesystemu.

Explicitní snapshots nejsou důkaz fyzické freshness nezávisle mutujícího checkoutu.
Bounded immutable historie nenahrazuje graph catalog, autentizaci ani archivaci.
T034 CLI, export/apply do technického modelu a implicitní discovery jsou non-goals.

## Cíl a hranice samostatné dodávky

Schválení a revizní historie procesů. Výstupem tohoto úkolu je jediný otestovatelný kontrakt popsaný níže. Lze jej sloučit samostatně po splnění deklarovaných závislostí; není nutné dokončit celý T004. Závislosti neimplementuj skrytě v tomto PR. Při chybějícím upstream kontraktu zapiš BLOCKED a odkaz na konkrétní chybějící AC; fallback je povolen pouze jako přiznaný PARTIAL/UNKNOWN, pokud splní všechna zdejší kritéria.

## Podrobný rozsah a implementační kroky

1. **T032-S01:** Ukládej immutable semantic revisions a explicitní approve/reject rozhodnutí svázaná s payload hash a baseline.
2. **T032-S02:** Použij atomický zápis/CAS; při novější revizi odmítni přepsání stale base.
3. **T032-S03:** Schválení je záznam rozhodnutí lokálního uživatele/hosta, nikoli kryptografický důkaz identity ani technické evidence.
4. **T032-S04:** Přidej níže uvedené pozitivní i negativní testy na veřejném kontraktu. Zachovej konkrétní reprodukční vstupy; test nesmí pouze porovnávat hodnotu se stejnou implementační funkcí.
5. **T032-S05:** Aktualizuj dotčené CLI/capability příklady, stavovou a acceptance matici a český change note skutečnými výsledky. Připrav samostatný PR.

## Vstupy, výstupy a invariants

Vstupy jsou content-bound graph/provider/workspace snapshoty nebo explicitní dokumenty uvedené v krocích. Výstup musí zachovat vybraný scope a kontext, logical IDs a provenance. Platí společné schéma a stavové definice T004; nepřidávej vlastní význam pro COMPLETE, UNKNOWN ani RUNTIME_OBSERVED. Čisté projekce a renderery nevykonávají procesy ani I/O mimo čtení explicitních podkladů. Zápis je přípustný jen v úkolech s výslovným apply/review/export/cache kontraktem a s atomickým publikováním.

Non-goals: implementace dalších úkolů T004, nový graph store nebo resolver paralelní k T003, live discovery infrastruktury, automatické schvalování business významu, implicitní build/test aplikace a důkaz dostupnosti dat z pouhé statické cesty.

## Acceptance criteria

- **T032-AC01:** Opakované apply stejného payloadu je idempotentní.
- **T032-AC02:** Dva soupeřící zápisy nepřepíší novější revizi ani nerozbijí JSON.
- **T032-AC03:** Změna podkladů označí approval jako vyžadující revalidation; historie zůstane čitelná.
- **T032-AC04:** Invalidní vstup a chyba v podporované cestě nezmění zdrojový checkout ani poslední validní uložený artefakt. U čisté funkce test porovná vstup před/po; u zapisující funkce také filesystem/store před/po.
- **T032-AC05:** Výsledek nezvýší druh evidence, nepřimíchá jiný scope/kontext a přizná všechny relevantní unresolved/truncated hranice. Ověř negativním testem z níže uvedené matice.
- **T032-AC06:** PR obsahuje implementaci, konkrétní testy, výsledky běhů, dokumentaci a nový český change note; nedodané části jsou explicitně uvedeny. Žádná assertion „hotovo“ pouze na základě existence souboru nebo mocku.

## Povinné testy a způsob ověření

Specifická testovací matice: **Approve/reject; CAS conflict; cancelled write; idempotence; changed baseline.**

- Navržený cílový soubor: `tests/test_t032_persist_process_review.py`; pokud je vhodnější rozšířit existující test, uveď jeho přesný název a mapování AC v PR.
- Nejprve test pro každý T032-AC01–03 a negativní případ, poté regresní testy dotčených modulů. Každé AC má v change note konkrétní test, nikoli jen „suite green“.
- Spusť `python3 -m pytest -q` a `git diff --check`. Pro compiler/framework změny navíc skutečný podporovaný worker fixture; pro Mermaid skutečný parser/render job, nikoli jen substring assertion.
- V offline cestě ověř žádné neautorizované subprocess/network/DB/model API volání. Read-only Git pro baseline je povolen podle existujícího workspace kontraktu; není povolen implicitní worker/build.
- Reálný runtime observation test je oddělený od statické fixture. Chybějící toolchain uváděj SKIP/BLOCKED s důvodem, nikdy PASS. Pokud povinný gate nelze provést, PR může být pouze draft a nesmí být označen ready.
- Dokumentační příklady musí odpovídat implementovaným argumentům. Nepřidávej test, který pouze opisuje text tohoto zadání.

## Kompatibilita, migrace a omezení

Zachovej čtení graph v1/v2/v3, původní IDs, existující `graph view` a `flow render` chování. Nové serializované pole je aditivní nebo má explicitní verzi a test migrace; nepřepisuj cizí manifesty. Stará nebo neznámá evidence se nepromění na čerstvou. Pokud úkol nový persistent formát nevytváří, migrace je „není potřeba“ s uvedením ověřeného kontraktu. Neúplný parser/framework rozsah je součástí coverage, ne důvod k domýšlení faktů.

## Větev, samostatný PR a Definition of Done

1. Přečti AGENTS, registr a T004; proveď rekognoskaci source/testů dle kgmaker-architect. Zaznamenej HEAD a skutečné upstream dependency commits. Použij projektový task/memory workflow, pokud je v checkoutu dostupný.
2. Z aktuálního `main` vytvoř izolovaný worktree a větev `feat/t032-persist-process-review`. Pokud dependency PR ještě není merged, počkej; stacked PR je přípustný jen s výslovně uvedeným base/dependency PR a pozdějším retargetem. Nemíchej jiné úkoly do stejné větve.
3. Po implementaci a kontrolách přidej `docs/changes/<N>_<lowerCamelCase>.md`; N je max+1 přes main i otevřené PR. Odkazuj T032, jeho AC, skutečné změny, kompatibilitu, příkazy/výsledky a NOT_RUN kontroly.
4. Podle projektových pravidel aktualizuj memory/semantic vrstvu pouze doloženými změnami; generované grafy obnov příkazem. Nevytvářej smyšlený semantic patch. Zaznamenej případný blocker.
5. Commitni a pushni tuto větev, otevři **jeden samostatný PR pro T032** do aktuálního main (nebo deklarované dependency base). Použij výše uvedený PR title. Body obsahuje problém, řešení, odkazy na zadání/change note, tabulku AC → test → výsledek, dependencies a zbývající omezení.
6. Ověř remote PR diff a povinné CI. DoD = všechna AC splněna v deklarovaném scope, reviewovatelný PR s doloženými výsledky, žádné cizí změny. PR **nemerguj** bez explicitního pokynu. V závěru předej URL PR; pouhý lokální commit nestačí.

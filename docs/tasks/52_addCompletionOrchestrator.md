# T052 — Completion Orchestrator

- Task ID: T052
- Revision: 1
- Datum: 2026-11-19
- Stav: SPECIFICATION
- Baseline: GitHub main `8f362471a8254ff9a0e44870c490a1dcb6b067b1`.
- Zdroj požadavku: zadání KGMAKER Completion Orchestrator z 2026-11-19.
- Závislosti: T048 pro inventář, T051 a T046 pro úlohy a doklady, T045 revize 2
  pro nezávislé PR review a bezpečný merge.

## Rozsah

Dokončovat evidovaný backlog KGMAKERu po nejmenších ověřitelných krocích.
Koordinátor používá jediný task registr, inventář, graf, role a trace journal.
Hostitel dispatchuje agenty a provozuje jejich worktree. Příkaz plánování je
lokální a deterministický. Mimo rozsah patří migrace task store, vlastní
modelový klient, automatické povyšování compiler/runtime evidence a obcházení
Git oprávnění nebo serverových pravidel.

## Požadavky, kroky a acceptance

| Krok | Požadavek a kontrakt | Acceptance a ověření |
|---|---|---|
| T052-S01 | T052-R01. `kgmaker completion plan` odvodí prioritní výběr a dependency graph ze stávajících atomických řádků a zadání. Výstup odděluje delivery a verification a obsahuje identitu vstupů. | T052-AC01. Test priorit, nejvýše N kandidátů, chybných vstupů bez zápisu, cyklů aktivní práce, selhání závislostí a skutečného inventáře. |
| T052-S02 | T052-R02. Host skill volí specializované agenty, nezávislé položky běží v oddělených worktree a každý handoff používá T051 packet a artefakt. Uložené task ID obnovuje stav a retry vrací přesné nálezy. | T052-AC02. Reálné worktree a task ID, zaznamenaný test, nezávislé review, alespoň jeden retry a ověřená obnova. Sekvenční varianta na hostiteli bez paralelních slotů. |
| T052-S03 | T052-R03. Správnost a steelman hodnotí dva různí aktéři mimo implementaci proti stejné revizi. T045 ověřuje lokální důkazy, závislosti, ready/mergeable a aktuální base/head, respektuje branch protection a po merge ověřuje cílovou větev. | T052-AC03. Doložit odmítnuté vlastní nebo stale review a blokaci změněného páru, chybějících testů či otevřeného nálezu. Ověřit autorizovanou integraci skutečné schválené změny. |
| T052-S04 | T052-R04. Koordinátor udržuje T048 inventář a obnovitelný checkpoint, spustí aktuální backlog od compiler cache a inkrementální integrity. | T052-AC04. Inventář reprodukovatelně odráží zdroj, PR a skutečné výsledky. Checkpoint drží stavy a další krok po přerušení. Alespoň první položka projde celým cyklem nebo je konkrétně zablokovaná. |

## Migrace a Definition of Done

Stávající task IDs, workflow artefakty, formát stage cache, graph store a init
zůstávají kompatibilní. Plán využívá strukturované řádky aktuální matice a
rozpoznané deklarace v původních specifikacích. Nejasné předpoklady a aktuálnost
důkazů ověřuje host. Lokální actor label má důvěru LOCAL_DECLARED. GitHub Actions
jsou doplňující důkaz podle T045 revize 2.

DoD vyžaduje zaměřené testy, nezávislé review, lokální kontrolu skutečné matice,
ověření obnovy, audit prvního běhu a [provozní návod](../completion-orchestrator.md).
Zdrojové, toolchainové a GitHub výsledky se evidují podle skutečnosti. Stav dodání
a zbývající ověření jsou v [inventáři](../production-analysis-progress.md).

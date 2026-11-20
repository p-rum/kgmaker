# Completion Orchestrator

T052 koordinuje dokončování repozitáře KGMAKER. Lokální příkaz plánování čte
[existující stavový inventář](production-analysis-progress.md) a jeho odkazy
do [registru zadání](tasks/README.md). Pro vykonání plánu používá podporovaný
hostitel [repozitářový skill](../.agents/skills/kgmaker-completion/SKILL.md) a
[stávající workflow](delivery-workflow.md).

```bash
kgmaker completion plan --root /repo/kgmaker --jobs 3
kgmaker task list --root /path/to/item-worktree
kgmaker task show "$KGMAKER_TASK_ID" --root /path/to/item-worktree
kgmaker completion handoff "$KGMAKER_TASK_ID" --root /path/to/item-worktree
kgmaker completion handoff "$KGMAKER_TASK_ID" --root /path/to/item-worktree --apply
```

`--jobs` je 1 až 32 a výchozí hodnota je 1. Výstup JSON obsahuje
`inventory_fingerprint`, položky `items` podle ID a nejvýše zadaný
počet kandidátů `dispatch`. Každá položka obsahuje odkaz a hash zadání,
dodání, ověření, priority, příslušné PR, deklarované závislosti, vlastníka,
navrženou akci a blokery. Oddělené podmíněné závislosti patří k širším variantám, které host vyhodnotí z původního zadání. Historické evidence SHA jsou součást inventáře.
Chybný inventář nebo cyklus aktivní práce končí návratovým kódem 2. Souhrnný milník T003 se rozvine na jeho evidované work packages. Samostatný offline kontrakt vyžaduje ověření zdroje. Neznámé
deklarované závislosti vyžadují posouzení zdroje. Historické výsledky platí pro zdokumentovanou revizi.
Známý FAIL má přednost a blokuje přímé i nepřímé závislé položky. Plán je read-only a funguje bez sítě, grafu a Actions.

`completion handoff` je určený pro profilované úlohy. Bez `--apply` čte stav a
vrací náhled. S `--apply` uloží nejvýše jeden přechod a standardní packet pro
vrácenou roli. Po selhání testu nebo `REQUEST_CHANGES` vrátí `feedback` s původními
nálezy do implementace, pokud platí source fingerprint a zbývá další iterace.
Při souběžné změně úlohy nebo zdroje je potřeba načíst aktuální stav. Příkaz
nevykonává validační příkazy a schválenou úlohu ponechá pro explicitní T045
rozhodnutí. Při tvrdém ukončení během držení zámku je nutné ověřit jeho vlastníka
před obnovením zápisu.

Před dispatchí ověř aktuální refs, acceptance předchůdců, zdroj, stav PR a
překryv zapisovaných cest. Hostitel použije samostatný worktree a stávající
workflow s omezenou kapacitou skutečných agentů. Test a review patří konkrétní
revizi. Skill vede hostitele ke dvěma odděleným review a k předání nevyřešených
nálezů přes existující retry. Skutečné GitHub schválení a merge vykonává role
`code_review` podle [T045](tasks/45_addCodeReviewAgent.md).

Po přerušení vyhledej worktree a v něm existující task ID. Před pokračováním
načti jeho stav, přepočítej plán pro aktuální inventář a ověř zdrojovou revizi.
Po integraci aktualizuj existující stavové dokumenty skutečnými výsledky.
[První běh a neověřené kroky](changes/134_addCompletionOrchestrator.md).

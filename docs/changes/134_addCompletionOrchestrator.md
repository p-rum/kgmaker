# T052 — lokální plánovač dokončení a první běh backlogu

Zadání [T052 revize 1](../tasks/52_addCompletionOrchestrator.md) vychází z požadavku
z 2026-11-19. Lokální baseline `465b121992aad50c2885acef0fd038531a31293a`,
ověřený GitHub main `8f362471a8254ff9a0e44870c490a1dcb6b067b1`. Porovnání přes
GitHub našlo jediný rozdílný soubor baseline, nový PR review workflow.
Stav lokálně IN_PROGRESS. Ověření PARTIAL.

## T052-S01 / T052-AC01 — plán a závislosti

Dřívější inventář sloužil čtenáři a postup výběru musel ověřovat každý
koordinátor. [Plánovač](../../src/kgmaker/completion.py) čte jeho atomické
řádky a seznamy závislostí v zadání, rozlišuje dodání od ověření, opravám dává
přednost a omezuje návrh souběžné práce na kapacitu hostitele. Sdílené kroky
odkazují na vlastníka. Neznámá přímá závislost drží položku mimo výběr. Cykly
brání plánování aktivní práce. Historické reference sloučených položek zůstávají
v úplném výpisu. JSON obsahuje fingerprint inventáře a zadání pro ověření vstupu.

`kgmaker completion plan --jobs 4` je read-only a nevyžaduje graf ani GitHub.
Ostatní CLI příkazy a uložená workflow data používají dosavadní formát.

## T052-S02 / T052-AC02 — práce hostitele a obnova

[Repozitářový skill](../../.agents/skills/kgmaker-completion/SKILL.md) používá
stávající task, role, CAS a graph packet. Worktree oddělují implementace. Při návratu
se načte původní workflow ID. Retry předává uložené nálezy a testovací reprodukce.
Příkaz completion handoff vrací další roli ze stavu uložené úlohy, s --apply
uloží nejvýše jeden přechod a vydá výchozí packet. Zastaralý test zůstane ve fázi
test, zastaralý předpoklad testu ve fázi review vyžaduje nový cyklus přes
implementaci a test. Přechod a výsledek testu používají přesnou CAS revizi a
ověřenou vazbu ke zdroji až do zápisu pod zámkem. Při obnovení implementace se
znovu ověřuje případná revokace předchozího lidského schválení.
Lokální běh vytvořil úlohy pro T052, W01 a T047-S01 a uložil stav k obnově.
V produkčním použití závisí výběr a identita specialisty na hostiteli. Plánovač
delegaci ani spuštění příkazů neprovádí.

## T052-S03 / T052-AC03 — nezávislé review a integrace

Skill vyžaduje oddělené correctness a steelman review, skutečné testy a čerstvý
source fingerprint. Existující role code_review uplatňuje pravidla T045 při
integraci. Místní workflow verdikt nepředstavuje schválení na GitHubu ani merge.
Oddělené correctness a steelman review našly chyby v grafu závislostí a vazbě packetu. Opravy prošly lokálním re-review. Publikované T045 review, retry v reálném PR a merge zůstávají NOT_RUN. Stávající formát artefaktů neslibuje autentizaci lokálního aktéra.

## T052-S04 / T052-AC04 — inventář a pokračování

[Stavová matice](../production-analysis-progress.md) potvrzuje sloučení T029 a W01.
W01 zůstává MERGED/FAIL kvůli otevřenému P1, T021 má nedokončenou opravu.
První výběr před záznamem dodatečného nálezu CFG vrátil W01, T021, T047-S01
a T003-S13-W02. [Dokumentace CLI a postupu](../completion-orchestrator.md),
[README](../../README.md), [registr](../tasks/README.md) a [acceptance](../acceptance-inventory.md)
popisují stejný kontrakt.

## Kontroly

- `python -m pytest -p no:cacheprovider -q tests/test_completion_handoff.py tests/test_completion.py tests/test_workflow.py tests/test_workflow_profiles.py tests/test_delivery.py tests/test_provenance.py tests/test_context_roles.py`
  — 117 PASS v Pythonu 3.12 po poslední opravě z review.
- `python -m kgmaker completion plan --jobs 4` — PASS na 119 položkách.
- `python -m pytest -p no:cacheprovider -q` — FAIL, 2326 PASS, 1230 SKIP,
  21 FAIL a 27 ERROR. Mezi příčinami nepřipravený JVM toolchain a build exporter.
  Dva selhávající zdrojové scénáře reprodukovány na čisté baseline, CFG projekce
  při hodnotě null a inicializace cache s testovacím argv bez skutečného executable.
- `git diff --check` — PASS při zaměřené kontrole. Skutečná produkční JVM/TS/Windows
  matice zůstává neověřená a GitHub CI NOT_RUN.

Checkpoint v [inventuračním dokumentu](../production-analysis-progress.md)
obsahuje worktree, runtime ID, otevřené PR a další krok. Žádná dosavadní evidence
neoznačuje celý backlog za dokončený.

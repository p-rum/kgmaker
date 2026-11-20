# T052 — lokální plánovač dokončení a první běh backlogu

Zadání [T052 revize 2](../tasks/52_addCompletionOrchestrator.md) vychází z požadavku
z 2026-11-19. Lokální baseline `465b121992aad50c2885acef0fd038531a31293a`,
ověřený GitHub main `8f362471a8254ff9a0e44870c490a1dcb6b067b1`. Porovnání přes
GitHub našlo jediný rozdílný soubor baseline, nový PR review workflow.
Dodání PR_OPEN ([#120](https://github.com/p-rum/kgmaker/pull/120)). Ověření PARTIAL.

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
Oddělené correctness a steelman review našly chyby v grafu závislostí a vazbě packetu.
Opravy prošly lokálním re-review. Revize 2 přidává
[`completion attribute`](../../src/kgmaker/completion_review.py). Příkaz používá
existující artefakt a T046 `submitted` událost. Formát úlohy, journalu, role
packetů a běžný `task record` jsou kompatibilní. Koordinátor vyžaduje pro
`awaiting_pr_review` dva aktuální připsané výsledky mimo implementaci. Aktuální
otevřený major/blocker, REQUEST_CHANGES a BLOCK mají přednost.
Příklad `kgmaker completion attribute TASK_ID ARTIFACT_ID --actor HOST_AGENT_ID`
používá identitu LOCAL_DECLARED. Publikované T045 review a merge jsou NOT_RUN.
Nezávislé review našlo dvě chyby v první implementaci atribuce. Workflow
uložil nález `artifact:38d9a2c31fcfd908757fcc63207d37d202b9c1f2e94310aba9940e39459ca133`
a vrátil shodný feedback v novém procesu po přechodu do iterace 2. Oprava omezuje
blokaci i retry na platná připsaná review. Při atribuci ověřuje hash uloženého
packet ID i přesnou source binding. Běžný T051 příjem starších packetů zachovává
kompatibilitu. Obě hranice kryjí nové regresní testy.

### T052-S03 / T052-AC02 a AC03 — obnovení společného packetu a všech nálezů

První publikovaný HEAD #120 `51ed1141befbd4f34f91a5c6cec77dff002530d2`.
Steelman reprodukoval ztrátu druhého nálezu a přepsání společného packetu při
obnovení. Skutečný připsaný výsledek
`artifact:c5cd8001045b8f3c41cb52d19d866aea2ae3f45741af2277ae2be98807d0c98d`
vyčerpal retry cap původní úlohy. Původní úloha zůstala evidována BLOCKED.
[`completion handoff`](../../src/kgmaker/completion_handoff.py) nově posílá
všechny platné nálezy v `reviews.feedback` a zachovává jeden kompatibilní
`feedback` pro stávající primární CAS důkaz. Obnovení stejné fáze znovu použije
platný společný packet. Poškozený packet před přechodem blokuje bez zápisu.
Zaměřené případy jsou v [testech](../../tests/test_completion_handoff.py).
Navazující skutečná correctness kontrola reprodukovala přepsání výsledku po
ztrátě JSON packetu a souběh připsaného BLOCK těsně před retry. Nález
`artifact:59aed238b7d14b5a44a48cbbb06618637c011ba4832ea39962656c4fef7e689f`
přešel do iterace 1 navazující úlohy. Atribuce i vyhodnocení hlídají stejné
packet ID obou review. Po ztrátě packetu po prvním rozhodnutí musí host obnovit
původní soubor nebo zahájit novou iteraci. Zápis retry ověřuje i revizi journalu
pod existujícím zámkem v [workflow](../../src/kgmaker/workflow.py).
GitHub review a merge jsou NOT_RUN.

## T052-S04 / T052-AC04 — inventář a pokračování

[Stavová matice](../production-analysis-progress.md) potvrzuje sloučení T029 a W01.
W01 zůstává MERGED/FAIL kvůli otevřenému P1, T021 má nedokončenou opravu.
První výběr před záznamem dodatečného nálezu CFG vrátil W01, T021, T047-S01
a T003-S13-W02. [Dokumentace CLI a postupu](../completion-orchestrator.md),
[README](../../README.md), [registr](../tasks/README.md) a [acceptance](../acceptance-inventory.md)
popisují stejný kontrakt.

### T052-S03/S04 / T052-AC02–AC04 — ověřená integrace prvního follow-up

T052 zpracoval skutečný retry opravy T046-S03/S04 a při opakovaném načtení
zachoval nález na stejném task ID. Dvě nezávislá review pak schválila stejný
packet. Úloha `task:91472f36fd41997e71b5739345417f392add792bf467a51dc5730665a8fc1c62`
dosáhla `awaiting_pr_review` a po ověřené integraci `done`.
[Projektový reviewer T045](https://github.com/p-rum/kgmaker/pull/125#issuecomment-7040630121)
nezávisle ověřil 103 PASS, připravené PR, statický graf a obě SHA. GitHub
odmítl formální self-review s HTTP 422, proto je explicitní přesný verdikt
v komentáři. Merge použil očekávaný head `17739888492d56ee813aed3d1c0b203ff6e8420f`.
[Sloučený #125](https://github.com/p-rum/kgmaker/pull/125) má merge commit
`1532f1725f2cbe0d76685c273adc32c2e0d239e0` se skutečnými rodiči
`8f362471a8254ff9a0e44870c490a1dcb6b067b1` a `17739888492d56ee813aed3d1c0b203ff6e8420f`.
Ověřený cílový tree `3f840cd64bcfad9ed049aa274f1b46f76b16ea3a` je
nová integrační baseline tohoto PR. Běh hostitele prokázal skutečné delegování,
obnovu a integraci tohoto rozsahu. W01 stále čeká na úplný integrační důkaz.

## Kontroly

- `python -m pytest -p no:cacheprovider -q tests/test_completion_handoff.py tests/test_completion.py tests/test_workflow.py tests/test_workflow_profiles.py tests/test_delivery.py tests/test_provenance.py tests/test_context_roles.py`
  — 129 PASS v Pythonu 3.12 po opravách z correctness a steelman review.
  Původní #120 průchod měl 117 PASS.
- Stejná zaměřená sada na zdrojově přesném main po #125 a integrovaném T052
  — 134 PASS / 0 SKIP. Obsahuje dalších pět T046 regresí. `git diff --check`
  ověřuje integrované zdroje i dokumentaci.
- `kgmaker semantic apply`, `semantic validate`, `scan`, `status` a `check`
  — PASS na stejném integrovaném T052 checkoutu. Předchozí #125 vrstva je zachována.
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

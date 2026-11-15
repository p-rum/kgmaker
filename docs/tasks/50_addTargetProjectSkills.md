# T050 — Skilly KGMakeru v cílovém projektu

- Task ID: **T050**; Revision: **1**
- Datum: **2026-11-15**; stav dokumentu: **SPECIFICATION** (cílové chování).
- Baseline: `main` @ `193c89b4d461047fd3330fd74892c5830ba8ac81`.
- Depends on: existující `init`, semantic/feature/data-check CLI a dodané T046
  testgen kontrakty. Související [T049](49_separateTargetAgents.md) zůstává
  samostatným nedokončeným programem; T050 neuzavírá jeho acceptance.
- Větev: `feat/t050-target-project-skills`.

## Rozsah a kontrakty

Cílový projekt dostane pomocí `kgmaker init` samostatné Agent Skills pro kontext,
sémantické vztahy, analýzu požadavku, audit dat a návrh testů. Instrukce používají
existující nástrojové kontrakty, neslibují runtime důkazy ze statických dat a
nepřenášejí vývojovou governance KGMakeru. Automatické objevení závisí na hostiteli;
ruční otevření `SKILL.md` musí fungovat i bez registrace nebo delegace agentů.

Non-goals: změna dosavadních Copilot/Junie rolí, profilový průvodce, migrace dle
T049, technické omezení hostitelského shellu, automatický build, instalace závislostí,
commit/push/merge, nové modelové API či změna graph/store/packet schématu.

| ID | Požadavek |
|---|---|
| T050-R01 | `src/kgmaker/skills.py` obsahuje explicitní seznam instalovaných cest a Python templates; nové resources fungují i v instalovaném wheelu. |
| T050-R02 | Pět stručných skillů má rozlišující name/description, funkční relativní references a konkrétní příkazy odpovídající současnému CLI. Samostatně respektují pravidla cíle a rozsah oprávnění. |
| T050-R03 | `init` instaluje skilly do `.agents/skills/`, běžné opakování zachová existující obsah. Neplatná/symlinková nová cílová cesta se odmítne před jakýmkoli zápisem init. `scan` není instalátor. |
| T050-R04 | Spravované kopie v tomto repozitáři odpovídají templates; starý uživatelsky smazaný `.agents/skills/kgmaker` se neobnovuje. Dokumentace odděluje dodání od ověření. |

## Kroky, acceptance a ověření

| Krok | Výstup | Acceptance |
|---|---|---|
| T050-S01 | Templates a návody pro pět samostatných workflow, spravované kopie, CLI init integrace s preflightem; README a návod. | T050-AC01, AC02, AC03 |
| T050-S02 | Regrese ochrany souborů a parity, kontrola wheelu mimo checkout, validace skillů; change note, matice a acceptance inventář. | T050-AC01 až AC05 |

- **T050-AC01:** init v prázdném cíli vytvoří celý explicitní seznam skillů a
  references; bajty odpovídají templates. Wheel bez zdrojového checkoutu dodá totéž.
- **T050-AC02:** opakovaný init má stejný obsah a mtime; uživatelské skill soubory,
  cizí skills a instrukce přežijí. Existující explicitní `--force` může obnovit
  deklarované templates; nikdy se nezapíná automaticky.
- **T050-AC03:** symlink v kterémkoli novém výstupu nebo jeho rodiči, soubor místo
  adresáře či adresář místo souboru vrací nenulový stav a nulovou mutaci cíle i
  externího cíle. Stejně při `--force`. Nové skilly nevznikají při `scan`.
- **T050-AC04:** `skill-creator/scripts/quick_validate.py` projde nad pěti skilly;
  každá reference je dodaná. Příkazy se porovnají se skutečným parserem. Ukázkové
  context/semantic/feature/data-check/testgen workflow se ověří v lokální fixture.
  Samotný formátový test není důkaz chování hostitelského modelu.
- **T050-AC05:** každý krok má český záznam s baseline, soubory, kompatibilitou,
  skutečnými kontrolami a limity. README, capability/CLI návod, matice a inventář
  odkazují na změnu; nedostupní hostitelé mají NOT_RUN.

## Migrace, DoD a zbývající omezení

Python `init(root, force=False)` a CLI zůstávají kompatibilní. Žádná migrace dat.
Existující upravené soubory nejsou při běžném init aktualizovány; uživatel porovná
nové templates s vlastními úpravami. Před předáním projdou relevantní regrese,
validace skillů, wheel smoke a `git diff --check`; každé neprovedené ověření se uvede.
ID alokováno po kontrole registru, main tree a otevřených PR #4/#97 (change116
rezervuje PR #97, tato dodávka používá change117); před publikací kontrolu zopakuj.

Bez ověření konkrétního hostitele nelze tvrdit automatickou discovery ani kvalitu
modelových odpovědí. Instrukce nejsou technický sandbox. Nový preflight neřeší
atomický rollback ostatních historických výstupů init ani souběžné změny cest;
kompletní instalátor/migrace patří T049. Implementace starých profilů zůstává
beze změny včetně jejich známých mezí izolace.

# T051 — Propojené projektové workflows

- Task ID: T051; Revision: 1; datum: 2026-11-15; stav: SPECIFICATION.
- Baseline: `6790b0e0a930089924c61c3f8a6b3aef1d44121c`.
- Závislosti: existující task/context/store, T046 delivery a T050 skills.
  T049 hostitelské profily a vynucování oprávnění zůstávají samostatným cílem.
- Číslování: lokální registr, main a otevřené PR #4/#97; maximum T050,
  change117 (PR #97 rezervuje change116). Nová čísla T051/change118.

## Rozsah a návrh

Propojit analýzu, návrh, implementaci, testy a review přes stávající runtime task.
Verzovatelná `.kgmaker/workflows.json` konfiguruje datové profily; každý nový
profilovaný task nese neměnný snapshot a jeho hash se účastní identity tasku.
Výchozí profily `greenfield`, `existing-feature`, `bugfix` používají stejnou
posloupnost intake → analyze → plan → implement → test → review → done.
Samostatné read-only analýzy dál používají feature/data-check, testování existujícího
kódu testgen. Není nutné předstírat implementaci pro dokončení takového auditu.

Non-goals: libovolný DAG, automatický runner/LLM, build, instalace závislostí,
DB, runtime availability, automatické schválení, Git operace nebo nový katalog.
Konfigurace neuděluje oprávnění. Artefakty jsou lokální deklarovaná evidence.

## Kontrakty a kroky

| Požadavek / krok | Dodávka | Acceptance |
|---|---|---|
| T051-R01 / T051-S01 | `workflow_profiles.py`: striktní v1 JSON, builtins, vlastní profily s explicitním extends, default, role instructions, label/command validace, limity; read-only CLI list/show/check | T051-AC01: chyby verze/polí/duplicit/typů/cest bez mutace; konfigurace nic nespouští |
| T051-R02 / T051-S02 | `workflow.py`, `context.py`, `cli.py`: `task add --workflow`, snapshot ve v3, role packet, obsahové vazby a artefaktové gates | T051-AC02: stabilní v1/v2 ID a chování; v3 izolované identity a immutable snapshot; změna konfigurace nemění rozpracovaný task |
| T051-R03 / T051-S02 | Forward gates vyžadují dokončený artefakt příslušné role; test potřebuje passed povinné label/command; done aktuální test/review bez otevřeného major/blocker | T051-AC03: žádné přeskočení gates přes save_task, stale evidence/SKIP/unknown bez PASS, retry/stop funkční |
| T051-R04 / T051-S03 | Instructions/templates, spravované kopie, příklady a uživatelský průchod novým i existujícím projektem | T051-AC04: init parity a ochrana úprav; CLI příklady ověřené v lokálních fixtures |
| T051-R05 / T051-S03 | Stavová matice, acceptance a change note po krocích | T051-AC05: relevantní regrese a skutečné limity, oddělené dodání a ověření |

## Ověření a migrace

Použít pytest nad novými profile tests a existujícími workflow, delivery, init,
skills a provenance tests. Negativní scénáře porovnají obsah před/po chybě.
Packet nesmí zahodit workflow instrukce kvůli budgetu: při nedostatku místa chyba
před zápisem. Konfigurace leží mimo ignorovaný runtime `.kgmaker/workflow/`.
Staré tasky zůstávají v1/v2; bez konfigurace a bez --workflow zachovat legacy API.
Profilované tasky jsou v3 a starší verze nástroje je nepřečte; downgrade není podporován.

DoD: kontrakty, aktuální příručka, testy a záznam každého kroku souhlasí.
Zbývající omezení: skutečné hostitelské chování, compiler/toolchain produkční matice,
automatická orchestrace a T049 se tímto nedokládají. Před publikací znovu ověřit ID.

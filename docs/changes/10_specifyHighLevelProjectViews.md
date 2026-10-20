# Specifikace high-level zobrazení projektu

- Datum: 2026-10-20
- Baseline: main `c39f8adf2e3004d201960a18575bc7659808ae94`
- Task: T004; atomické implementační úkoly T005–T044.
- Typ: pouze dokumentace; žádná implementace ani runtime capability.

## Problém

Integrační projekce a technický process CFG nejsou katalog služeb a business procesů.
Analýzu bylo potřeba převést na kompletní zadání s malými samostatně mergeovatelnými
úkoly, testy, acceptance a jednoznačným branch/PR postupem.

## Skutečné změny

- Hlavní specifikace T004: modely, evidence, multi-context selection, HTTP/Kafka/DB,
  business review, CLI kontrakt, atomic export, invalidace, kompatibilita a non-goals.
- 40 samostatných souborů T005–T044, každý s konkrétními kroky, šesti acceptance,
  testovací maticí, dependencies, přesnou větví, PR title a DoD.
- Registr, README a stavový dokument odkazují na plán jako SPECIFICATION.
- AGENTS a Copilot pravidla výslovně dokumentují uživatelem požadovaný formát
  `T-<NNN>_<kebab-case-slug>.md` pro tento balík. Historické soubory beze změn.
- Evidence a význam procesu jsou oddělené; business approval nepovyšuje technický důkaz.

## Číslování a kompatibilita

Main obsahoval T001–T003 a change notes 1–7. Kontrola otevřených PR #4 a #8
nezjistila nové hlavní Task ID; PR #8 má change note 9. Proto T004 a T005–T044,
change note 10 (mezera 8 se nerecykluje). Před publikací byly main HEAD a oba PR head
znovu porovnány a nezměnily se. IDs nejsou GitHub PR numbers.

Pravidla pro tento balík mají přednost před starými naming odstavci v templates;
templates se neinstalují ani nemění. Graph/store schema, CLI a source kód se nemění.
Žádná migrace uživatelských dat není potřeba.

## Provedené kontroly

- Read-only GitHub API: main baseline, registr, AGENTS/Copilot pravidla, oba otevřené
  PR trees, uložený navigační graph/notes a rekognoskace z předchozí analýzy.
- JavaScript validace připravených dokumentů: 40 task files, 240 podřízených AC,
  explicitní branch/PR požadavky; žádná chybějící AC.
- Dependency validace: každý interní předchůdce existuje a má nižší ID; bez cyklů.
- Relativní Markdown odkazy ověřeny proti baseline tree a připraveným souborům.
- Kontrola uzavřených code fences, trailing whitespace a závěrečného newline.
- Po publikaci se ověří remote changed-file manifest a PR base/head.

## Neprovedené kontroly

Pytest, compiler workers, build, Mermaid runtime render, kgmaker scan/query,
semantic update/apply a git diff --check nebyly v dokumentační API cestě spuštěny.
Kontrola whitespace proběhla nad přesným textem souborů v JavaScriptu.
Generované graph soubory nebyly ručně upraveny. Žádný sémantický patch nebyl
vymyšlen; nevznikla nová runtime evidence. Dokumentační změna nevyžaduje nové
testy opisující text specifikace.

## Příklad a zbývající práce

Agent převezme `T-021_render-topology-mermaid.md`, ověří dependencies,
založí `feat/t021-render-topology-mermaid`, splní jeho AC/testy a odešle
samostatný PR. Nemá realizovat celý T004 v jedné větvi.

Veškerá implementace T005–T044 zbývá. T004-AC01–AC10 i všechna podřízená AC
jsou cílová kritéria, ne PASS. Případné potřebné upstream work packages T003
musí dodat vlastní PR. Tento dokumentační PR se bez pokynu nemerguje.

# Obnovení registru naplánovaných high-level úkolů

## Problém a skutečná změna

Merge `0c0902896c4803be7e7c1246aa0ba5da45f8ebe2` odstranil z registru
`docs/tasks/README.md` řádek T004 a sekci všech čtyřiceti úkolů T005–T044,
ačkoli jejich specifikace a projektové agent profily zůstaly v repozitáři.
Registr proto neobsahoval všechny již přidělené identity.

Obnovena je přesná sekce a řádek z rodiče `e625014`; aktuální řádky T003 a
T045 i registr šedesáti T003 work packages jsou zachovány. Oprava souvisí
s T004-AC10 a registračními pravidly AGENTS.md. Nemění acceptance úkolů,
jejich stav SPECIFICATION, runtime, schémata ani instrukce profilů.

## Ověření

Na izolované větvi `fix/restore-planned-task-registry` nad `0c09028`:

- Jednorázová kontrola Pythonem (`pathlib`, `re`, `tomllib`, `subprocess`):
  **PASS** — 45 jedinečných hlavních Task ID T001–T045, 113 platných
  relativních odkazů registru, 101 syntakticky platných profilů s jedinečnými
  názvy, právě jeden profil pro každé ze 40 zadání T005–T044 a acyklický
  jejich dependency graf. Obnovená sekce je přesně shodná s `e625014`;
  existující řádky T003/T045 jsou zachovány.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker scan --no-docs`:
  **PASS s diagnostikou** — 267 souborů, 2119 deklarací/sekcí. Pouze lokální
  ignorovaný machine index; generované Markdown/Mermaid soubory se nemění.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker memory recall registry task T004 --limit 2`:
  **PASS** po scanu; nalezen registr a nadřazené zadání. Před scanem nebyl
  v čistém checkoutu čitelný machine index.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker check`:
  **BLOCKED** — existující sémantická vrstva hlásí stale evidence v `README.md`
  a čtyři vazby na odstraněné nebo stale uzly. Tato oprava nemění README,
  sémantický soubor ani zdrojové uzly; nesouvisející vazby nebyly přepisovány.
- `git diff --check`: **PASS**.

Pytest, worker buildy a rendering: **NOT_RUN**, protože jde výhradně o
obnovu dokumentačního registru. Nevzniká nová implementovaná capability ani
důkaz dokončení T003/T004. Nové sémantické vazby nejsou potřeba a nebyly
vymyšleny; soubory generovaného grafu nejsou ručně upraveny.

## Příklad a zbývající práce

Čtenář registru znovu najde například T005 s odkazem na
`T-005_add-view-model.md` a T044 s jeho release gate závislostmi. Skutečnou
implementaci, testy a sloučení jednotlivých úkolů nadále dokládají jejich
samostatná PR. Stale sémantická baseline vyžaduje samostatnou doloženou opravu.

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
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker scan`:
  **PASS** po sémantické obnově — 268 souborů, 2124 deklarací/sekcí.
  Generovaný GRAPH.md je obnoven příkazem, bez ručních úprav.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker memory recall registry task T004 --limit 2`:
  **PASS** po scanu; nalezen registr a nadřazené zadání. Před scanem nebyl
  v čistém checkoutu čitelný machine index.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker semantic update --base HEAD~1`,
  prázdný patch pro přesný update packet, `semantic apply` a `semantic validate`:
  **PASS** — 40 concepts, 10199 relationships. Obnoveny jsou obsahové
  fingerprinty souborů včetně stale README z baseline; původní pole nodes,
  edges a episodes zůstávají přesně zachována. Žádné vazby nejsou přidány.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker check`:
  **PASS** — 268 souborů, 2392 uzlů, 14916 vztahů. První scan a validace
  před obnovou korektně hlásily stale README evidence; finální kontroly prošly.
- `git diff --check`: **PASS**.

Pytest, worker buildy a rendering: **NOT_RUN**, protože jde výhradně o
obnovu dokumentačního registru. Nevzniká nová implementovaná capability ani
důkaz dokončení T003/T004. Nové sémantické vazby nejsou potřeba a nebyly
vymyšleny; soubory generovaného grafu nejsou ručně upraveny.

## Příklad a zbývající práce

Čtenář registru znovu najde například T005 s odkazem na
`T-005_add-view-model.md` a T044 s jeho release gate závislostmi. Skutečnou
implementaci, testy a sloučení jednotlivých úkolů nadále dokládají jejich
samostatná PR. Tato dokumentační oprava je nepovažuje za implementované.

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

Na izolované větvi `fix/restore-planned-task-registry`, původně nad `0c09028`,
integrované s `main` `3b7329284b376c83e20fe1a4ae3ea57a57131a90` (PR #11 a #18):

- Jednorázová kontrola Pythonem (`pathlib`, `re`, `tomllib`, `subprocess`):
  **PASS** — 45 jedinečných hlavních Task ID T001–T045, 113 platných
  relativních odkazů registru, 101 syntakticky platných profilů s jedinečnými
  názvy, právě jeden profil pro každé ze 40 zadání T005–T044 a acyklický
  jejich dependency graf. Obnovená sekce je přesně shodná s `e625014`;
  existující řádky T003/T045 jsou zachovány.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker scan`:
  **PASS** po sémantické obnově — finální integrovaný snapshot (počty níže).
  Generovaný GRAPH.md je obnoven příkazem, bez ručních úprav.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker memory recall registry task T004 --limit 2`:
  **PASS** po scanu; nalezen registr a nadřazené zadání. Před scanem nebyl
  v čistém checkoutu čitelný machine index.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker semantic update --base 3b7329284b376c83e20fe1a4ae3ea57a57131a90`,
  prázdný patch pro přesný update packet, `semantic apply` a `semantic validate`:
  **PASS** — obsahové fingerprinty jsou obnoveny vůči aktuálnímu main; jeho
  pole nodes, edges a episodes zůstávají přesně zachována. Žádné vazby
  nejsou přidány; nové historie PR #11/#18 nejsou přepsány starým snapshotem.
- `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m kgmaker check`:
  **PASS** — finální kontroly integrovaného snapshotu prošly. První scan
  původní baseline před obnovou korektně hlásil stale README evidence.
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

## Oprava souvisejícího integračního stavu

Řádek T005-AC06 v acceptance inventáři již po sloučení PR #11 nesprávně
uváděl IN_PROGRESS. Je opraven na PASS s odkazem na existující finální
ověření v change note 11; tato oprava registračního stavu nepřidává runtime
capability ani netvrdí dokončení ostatních úkolů T004.

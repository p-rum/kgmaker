# Rozpad zbývající implementace T003

- Change note: 6
- Datum: 2026-10-16; audit úplnosti 2026-10-17
- Související zadání: T003-S03–S13, T003-AC03–AC13
- Stav: dokumentační předání; nedeklaruje implementaci nových work packages.

## Problém

Po dokončení omezeného JPA v4 podúkolu zůstával zbytek produkční analýzy popsán
jen jako široké milníky. Takové celky nebylo možné bezpečně přidělovat do
samostatných větví a reviewovat jako malé pull requesty.

## Skutečné změny

- Aktuální stav JPA v4 a poslední doložený plný test run jsou zapsány ve stavové matici.
- Zbývající scope T003-S03–S13 je rozdělen do 60 samostatných work packages.
- Každý soubor obsahuje cíl, kontrakty, kroky, testovací požadavky, negativní případ,
  akceptační kritéria, kompatibilitu, Definition of Done a povinnou vlastní větev/PR.
- Registr vysvětluje identitu `T003-Sxx-Wyy` a odlišuje ji od hlavních T001–T003.
- Registr obsahuje matici pokrytí všech mezer T003-S03–S13; S01/S02 jsou
  výslovně uvedené jako již ověřený společný základ bez nového implementačního tasku.
- Každý work package uvádí konkrétní předchozí Work Package ID nebo výslovně
  říká, že po T003-S02 nemá další taskovou závislost.
- Volitelný runtime S13 a live Confluence S12 zůstávají výslovně oddělené od
  dokončení statického jádra.

## Kompatibilita a migrační dopad

Jde o dokumentační změnu. Nemění CLI, store schema, worker protocol ani runtime
chování. Historické Task ID, acceptance ID, analysis IDs a packet revisions zůstávají
beze změny.

## Provedené kontroly

- Kontrola kolizí názvů v `docs/tasks` a `docs/changes`.
- Kontrola úplnosti registru proti vytvořeným souborům.
- Audit konkrétních závislostí a matice pokrytí: **60/60 work packages**.
- Strukturní audit názvů, ID, sekcí, test requirements, acceptance, větví,
  PR požadavků, registru a dependencies: **60 souborů, 60 ID, 60 větví, 0 chyb**.
- Kontrola lokálních Markdown odkazů: **63 souborů, 0 rozbitých odkazů**.
- `python3 -m pytest -q` po dokončení dokumentace: **197 passed in 35.24 s**.
- Sémantická aktualizace dle workflow, finální scan a `git diff --check` jsou
  součástí závěrečného předání.

## Neprovedené kontroly

Nové implementační testy nebyly přidány ani spuštěny, protože work packages jsou
specifikace budoucích změn. Live Confluence integrace zůstává NOT_RUN bez konkrétního
host/API/auth kontraktu.

## Příklad použití

Implementátor vybere například `T003-S07-W06`, založí doporučenou samostatnou
větev, implementuje pouze HTTP request/execution scope, doloží uvedené pozitivní
i negativní fixture a vytvoří samostatný PR s vlastním novým change note.

## Zbývající práce

Implementovat work packages jednotlivě v jejich explicitním pořadí závislostí.
Milník ani acceptance se nesmí označit COMPLETE jen proto, že existuje jeho
specifikace.

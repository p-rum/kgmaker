# Projektoví implementační agenti pro atomické work packages T003

- Change note: 7
- Datum: 2026-10-17
- Související zadání: `T003-S03-W01` až `T003-S13-W04`
- Související acceptance: všechna kritéria `<WorkPackageID>-AC01` až `-AC04`
  zůstávají otevřená; tato změna pouze připravuje implementační agenty.
- Stav: projektová konfigurace a dokumentace; neimplementuje žádný work package.

## Problém

Šedesát atomických zadání mělo detailní rozsah, testovací požadavky, větev a PR,
ale nemělo odpovídající projektové Codex agenty. Koordinátor proto nemohl vybrat
jednoznačný profil svázaný s jediným work package a požadovaným modelem.

## Skutečné změny

- V `.codex/agents` vzniklo 60 samostatných TOML profilů v poměru 1:1 k
  work packages `T003-S03-W01` až `T003-S13-W04`.
- Každý profil má unikátní `name`, přesnou cestu k zadání, doporučenou větev,
  `model = "gpt-5.6-luna"` a `model_reasoning_effort = "medium"`.
- Instrukce každého agenta omezují implementaci na jediný work package a vyžadují
  kontrolu závislostí, architektonickou rekognoskaci, izolovaný worktree,
  acceptance testy, celý test suite, dokumentaci, sémantický workflow, commit,
  push a samostatný pull request bez automatického merge.
- `.codex/agents/README.md` obsahuje použití a úplný registr 60 profilů včetně
  vazby na zadání a doporučenou větev.
- Hlavní README, registr zadání a stavová matice popisují přidané profily a
  výslovně zachovávají stav všech work packages jako `SPECIFICATION`.

## Kompatibilita a migrační dopad

Změna nemění Python API, CLI, store schema, worker protocol ani runtime chování
kgmakeru. Profily jsou projektová konfigurace tohoto repozitáře a příkaz
`kgmaker init` je neinstaluje do uživatelských projektů. Existující Copilot agenti
v `.github/agents` zůstávají beze změny.

## Provedené kontroly

- Strukturní audit: **60 zadání, 60 TOML profilů, 60 unikátních jmen, 0 chyb**;
  pro každý profil ověřil model, effort, Task ID, cestu zadání, doporučenou větev,
  požadavek na testy, PR a zákaz merge.
- Parsování všech profilů standardním Python `tomllib`: **PASS**.
- `codex debug models --bundled`: přesně jeden záznam `gpt-5.6-luna`.
- `codex debug prompt-input 'Ověření registru projektových agentů.'`: **exit 0**;
  projektová konfigurace se načetla bez chyby definice agenta.
- Kontrola lokálních Markdown odkazů v dotčených registrech: **4 soubory,
  0 rozbitých odkazů**.
- `python3 -m pytest -q`: **197 passed in 35.12 s**.
- `kgmaker semantic update --base 61ac562`: **3 změněné indexované cesty,
  152 kontextových uzlů**; scoped patch zachoval 1 dotčený koncept a 4 vztahy.
- `kgmaker semantic validate`: **23 konceptů, 10143 vztahů, PASS**.
- `kgmaker scan`: **212 souborů, 1629 deklarací/sekcí, 14207 vztahů**.
- `kgmaker memory capture --base 61ac562 ...`: vytvořena ověřená implementační
  epizoda se stejnými validačními výsledky.
- Závěrečný `kgmaker scan` po capture a change note a následný
  `kgmaker status`: **graph current**.
- `git diff --check`: **PASS**.

## Neprovedené kontroly

- Agenti nebyli spuštěni proti svým work packages a nevzniklo 60 implementačních
  větví ani PR; tato změna vytváří jejich profily, nikoli jejich implementace.
- Žádné acceptance kritérium jednotlivého work package nebylo touto změnou
  povýšeno na PASS.
- Kontrola kolize change note proti otevřeným GitHub PR nebyla dostupná bez
  přístupu k privátnímu remote; lokální i dostupné remote větve obsahovaly jako
  nejvyšší publikovaný dokument `6_splitRemainingImplementation.md`.
- Volání `codex --strict-config debug prompt-input` nelze použít, protože Codex
  CLI 0.160.1 nepodporuje `--strict-config` pro podcommand `debug`; běžný parserový
  průchod `codex debug prompt-input` prošel.

## Příklad použití

Koordinátor může zadat:

```text
Implementuj T003-S03-W01 pomocí agenta t003_s03_w01_external_toolchain_selection.
```

Vybraný agent ověří závislosti, pracuje pouze ve větvi
`feat/t003-s03-01-external-toolchain-selection` v izolovaném worktree a na konci
vytvoří samostatný pull request odkazující na zadání a nový change note.

## Zbývající práce

Spouštět agenty jednotlivě podle explicitních závislostí v zadáních. Každý agent
musí dodat skutečnou implementaci, testy a samostatný PR; existence profilu není
důkazem dokončení work package ani nadřazeného milníku.

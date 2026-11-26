# Záznam sloučení výběru kontextu lokálního procesu

Datum 2026-11-26. [T048-S01 / T048-AC01](../tasks/48_completeImplementationHandoff.md#3-první-krok-t048-s01--sjednotit-stav-a-vytvořit-pracovní-seznam),
[T025](../tasks/T-025_build-local-process-path.md),
[T030](../tasks/T-030_prepare-process-label-packet.md).

## T048-S01 / T048-AC01

Kanonický řádek T025 po sloučení stále označoval #174 jako draft. GitHub
potvrdil sloučení do `main` v 19:25:20 UTC. Výchozí commit dokumentační
změny je `cb9848520b056518d028ceb8010ec6a6f9a43a2f`, strom
`833ec83af3495311aafabb25a0f5de87181d1c62`. Rodiče jsou
`346536495db749a6a1d79f89b388b55f9db3da83` a schválený head
`7e36de47dce06c44157c1080cc1a304af0e47239`. Matice uvádí nový merge, zachovává
dřívější merge `7a89e2868791eb7a061572de7527172e3b1ceb6a` i původní seznam PR.
[Sloučený #174](https://github.com/p-rum/kgmaker/pull/174) · [Stavová matice](../production-analysis-progress.md).

Nezávislé T045 vydalo `APPROVE` pro uvedený base, head a strom. Výsledek je
zaznamenaný komentářem. GitHub API odmítlo formální schválení účtem autora
kódem 422. V době merge běžely dva hostované `Test` běhy na headu a jeden na
`main`. Doklad o sloučení má SHA-256
`76c08c796135298a2f09af25feaf333a7e30e13d10452a7a3efd1210d8729aec`.
[Přesný verdikt T045](https://github.com/p-rum/kgmaker/pull/174#issuecomment-7201558053).

## T025-AC04/05/09 a vazba na T030-AC01/04/05

Sloučený `main` má samostatný cílený běh s Temurin JDK 21.0.6+7. Prošlo
19 testů za 16,89 s, 0 SKIP, 0 FAIL a 0 ERROR, raw exit 0. Běh ověřil
lokální proces v Javacu a Kotlin K1, skutečný výběr ze dvou repozitářů,
odmítnutí nepodporované obálky T030, starší grafy v1/v2 a plánovač.
Manifest 923 souborů a identita workerů před a po běhu souhlasí. SHA-256
JUnit `4e533abaae73b25e0fde3e3804d36972c1fb3a739ec61be336f059dddf0def2c`.
SHA-256 shodných manifestů
`4c966b422af0c9e4450ce5a08615a65a773feb0c7c9c6e6ebf1425ba084c8ee9`.
[Testy](../../tests/test_t025_build_local_process_path.py) · [Acceptance](../acceptance-inventory.md#t025--local-technical-process-path).

Před sloučením proběhla na headu `7e36de47` standardní sada s výsledkem
2625 PASS, 1382 SKIP, 1 očekávaný XFAIL a raw exit 0. To je samostatný
historický doklad, SHA-256 JUnit
`939a3327c79f6f612707541d3860b9969a8dc90611fb00abde75d2e8d22c55be`.
[Implementace a její původní kontroly](190_bindLocalProcessContext.md).

T025 a T030 mají dodání MERGED a ověření PARTIAL. T034 zůstává PLANNED /
NOT_RUN. Pro použití lokálního výběru platí stávající příklady v příručce API
a README. [Výběr kontextu](../process-paths.md) · [Příprava packetu](../process-label-packets.md)
· [README](../../README.md#local-technical-process-paths-t025).

## Ověření aktualizace inventáře

```sh
kgmaker completion plan --root "$PWD" --jobs 32
python -m pytest --assert=plain -q -p no:cacheprovider tests/test_completion.py
```

- PASS — plán má 135 položek, 106 MERGED a 29 PLANNED. Změnil se jen
  doklad v řádku T025. Ostatních 134 položek a všech 32 pozic pro delegování
  je shodných. SHA-256 výsledného plánu
  `041fd9091026f8cbaa7e1aeaa46b682cf44579124bd6b5afa73a67f9f5c48351`.
- PASS — 13 testů plánovače, 0 SKIP. SHA-256 JUnit
  `dae2f4dc6ba6188311db97a4b15973e063fd5d54bb5872b2ff8e4b47df08db1e`.

Doklady se ověřují také přes `semantic update`, `semantic apply`,
`semantic validate`, `memory capture`, `scan`, `status`, `check` a
`git diff --cached --check`. Nová úplná sada a nezávislé review této
dokumentační revize mají stav NOT_RUN.

# Výběr kontextu lokálního procesu pro T030

Datum 2026-11-26. Výchozí `main` `538d61d80ba991cbff5413973d92e7c6ec79e2aa`,
strom `132d262d3d0aad67c31fccacc7443d4b18e3a8c3`.
[T025](../tasks/T-025_build-local-process-path.md) · [T030](../tasks/T-030_prepare-process-label-packet.md).

## T025-S01 a T025-AC04, AC05, AC09

T025 sestavoval `ProcessView` pro přesně jeden trigger, ale do něj přebíral
celý výběr inventáře T024. Když měl workspace dva aktuální compiler kontexty,
T030 v pohledu našel vybraný kontext druhé služby mimo `definition.context_ids`
a ukončil přípravu packetu s `SELECTION_CONTEXT_MISMATCH`.

`build_local_process` použije ověřený aktuální compiler kontext triggeru
shodně v definici i technickém pohledu. Ponechá odpovídající řádky služeb a
jejich řádky o pokrytí bez vybraného kontextu. Baseline se dál váže k celému
vstupnímu inventáři, původnímu grafu, triggeru a limitům. Zachová scope,
topologii, zdrojové důkazy i stav PARTIAL. [Implementace](../../src/kgmaker/process_paths.py)
· [Kontrakt T025 a příklad použití](../process-paths.md).

## T025-S04 a T030-AC01, AC04, AC05

Test `test_actual_local_process_carries_only_its_selected_context_to_label_packet`
vytvoří dva fyzické repozitáře a pro každý výslovně spustí Javac 21 s JVM
workerem. T024 vybere jejich aktuální kontexty, T025 sestaví proces služby
orders a T030 připraví packet. Test zároveň zakáže procesy a síť během
projekce a porovná vstupní graf, inventář a soubory. Dřívější formát lze
načíst jako `ProcessView`. Dokud obsahuje cizí vybraný kontext, T030 jej
nadále odmítá. Výběr starého doloženého jednoslužbového pohledu kontroluje
existující Javac/K1 test. [Regrese](../../tests/test_t025_build_local_process_path.py)
· [Kontrakt T030](../process-label-packets.md).

- RED — před změnou zdroje selhal jediný nový nativní test s kódem 1 a
  `SELECTION_CONTEXT_MISMATCH`. SHA-256 JUnit
  `5008ae1789fc9ff2519babfda631702dc1c4eaf4c5abfb4a38f39f7541d72522`.
- PASS — porovnání původního a opraveného kódu nad stejnými uloženými
  compiler vstupy zachovalo devět vstupních souborů, baseline, identitu
  triggeru, topologii a provenance. Změnil se výběr a odvozený otisk definice.
  T030 připravil validní packet. SHA-256 srovnání
  `c71001141ce0d96bdd06f80fb7a13811c45e1a55ba34721bf8281736f4a425fa`.
- PASS — 439 cílených testů na prvním připraveném stromu
  `df951b63bc7094248b984a52a0b21a45d2c3730e`, 0 SKIP, 0 FAIL a 0 ERROR za 165,16 s.
  Temurin JDK 21.0.6+7 provedl novou Javac regresi a stávající testy
  lokálního a navazujícího procesu se skutečnými JVM workery. SHA-256 JUnit
  `f81dbddef56fec1593725630272352bc0d3e6da777cccf7bbedf0242229f8ae0`.

### Kompatibilita obálky výběru

T025-S01/S04 a T030-AC01/04/05. Kontrola prvního připraveného stromu našla
nechtěné odstranění neznámého pole v obálce `context_selection`. T030 tak
přijal dříve odmítnutý vstup. T025 nyní mění pouze větev `services` a ponechá
ostatní pole pro validaci. `test_local_process_preserves_selection_envelope_for_strict_label_packet`
ověřuje validní kontrolní vstup, zachovanou obálku v obou částech a odmítnutí
`UNSUPPORTED_SELECTION_SHAPE`, beze změny grafu, vstupu a posledního souboru.

- RED — rozšířený test na prvním připraveném stromu nevyvolal očekávanou chybu.
  SHA-256 JUnit `baf488e422caece2a9288eace71f4024615f41fff7e548a9cf6befd73af0e6a5`.
- PASS — po doplnění kontroly proběhly znovu T025, T030–T032 a T052. Prošlo
  224 testů, 0 SKIP, 0 FAIL a 0 ERROR za 27,87 s, včetně Javac 21 pro dvě služby
  a původní Javac/K1 cesty. SHA-256 JUnit
  `e591123119a23159168d8885d3294699c82125fc9850305ed4eb1f9337062e2c`.
  Opakování se stejnými compiler vstupy vrátilo bajtově shodný platný výstup.

## T025-S05 a T025-AC06

[README](../../README.md), [matice dodání](../production-analysis-progress.md)
a [acceptance](../acceptance-inventory.md) evidují dílčí opravu. Stav a pořadí
všech 135 položek T052 a 32 pozic dispatch zůstaly shodné. SHA-256 plánu
`dc55bf06ff89d49bf9164898bc1e2d047dba8fce2d831441e2183e58e404bb5f`.
T025 a T030 zůstávají MERGED / PARTIAL.
Čtecí `process` CLI, zápis neměnné revize PROPOSED a širší procesní kompozice
patří do vlastního rozsahu. Revize modelu a perzistence se nemění.

```sh
export JAVA_HOME=/workspace/kgmaker-tools/jdk-21.0.6+7
export PATH="$JAVA_HOME/bin:$PATH"
export KGMAKER_WORKERS_HOME=/workspace/kgmaker-tools/worker-dist KGMAKER_REQUIRE_WORKERS=1
export KGMAKER_TEST_MAVEN_REPOSITORY=/workspace/kgmaker-tools/maven-repository
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData
python -m pytest --assert=plain -q -p no:cacheprovider --tb=short \
  tests/test_t025_build_local_process_path.py \
  tests/test_t027_cross_http_process_boundary.py tests/test_t028_cross_async_process_boundary.py \
  tests/test_t029_project_process_failures.py tests/test_t030_prepare_process_label_packet.py \
  tests/test_t031_validate_process_annotations.py tests/test_t032_persist_process_review.py \
  tests/test_t033_catalog_business_processes.py tests/test_completion.py
kgmaker completion plan --jobs 32
```

Ověření navazuje příkazy `semantic update`, `semantic apply`, `semantic validate`,
`memory capture`, `scan`, `status`, `check` a `git diff --cached --check`.

Úplná sada, Windows, GitHub Actions a nezávislé review této revize mají stav
NOT_RUN.

# Předání deklarované konfigurace z BuildManifestu do runtime

[T003-S13-W01](../tasks/T003-S13-01-runtimeTraceProducer.md), kroky 2–5,
T003-S13-W01-AC01–AC04. Výchozí `main`
`0dbe9a754f06cf67f5fe40db0aaa31944497fe19`.

## Krok 2 — kontrakt BuildManifestu v1

Původní build import přijal `contexts[].config_fingerprint` jako neznámou položku
a compiler inspekce ji nepřenesla. Veřejný `runtime produce` pak odmítl i
platnou hodnotu vybrané varianty ještě před spuštěním aplikace.

`build_model.validate_manifest` validuje nepovinný digest v každé položce
`contexts[]`. Přijímá přesně 64 malých hexadecimálních znaků SHA-256 netajné
deklarované konfigurace. Chyba popisuje formát pole bez vložení odmítnuté
hodnoty. BuildManifesty v1 bez pole se dál importují a fungují pro inspekci.
Schémata BuildManifestu, grafu a RuntimeManifestu zůstávají kompatibilní.

## Krok 3 — předání existujícím compiler a runtime cestám

`build_model.inspection_inputs` předá digest z jediné varianty vybrané podle
ID kontextu a scope. Compiler kontext dál váže celý `manifest_hash` a uložený
původ importu `SUPPLIED_EXPORT_UNVERIFIED`. V2 producer před spuštěním ověří
shodu deklarovaných hodnot. Přenos používá existující schéma RuntimeManifestu
a stejný importní postup pro v1 a v2. Změna se týká explicitně deklarované
konfigurace. Maven exporter dál zachycuje parametry buildu. Instrumentace
ověřuje pouze vykonané synchronní callbacky. Úplná identita prostředí,
Windows a receiver/type RTA mají vlastní rozsah.

## Krok 4 — reprodukce a ověření

- RED na `0dbe9a7` s novými kontraktovými testy má 11 FAIL a 0 SKIP.
  Chybí přenos platného pole a validátor přijímá všech deset chybných variant.
  JUnit `runtime-build-config-red.xml`, SHA-256
  `d9dbab4df7ee22fa280c6aae698ba7e4b838766f85af52eb90640edfe35e7036`.
- Skutečný Maven 3.9.9 a JDK 21.0.6+7 před opravou zpracovaly fixture
  veřejnými příkazy a zapsaly compiler kontext bez zadaného pole.
  Nový end-to-end test má RED 1 FAIL, 0 SKIP a 106,76 s, přímo na
  `configured_context["config_fingerprint"]`. JUnit
  `runtime-build-config-actual-red.xml`, SHA-256
  `1dc5c24279c2c2728f44687cf88f9e7fe8f7348f0b6d9ec9692061ae3c39a2b0`.
- Kvalifikace má 179 PASS, 2 SKIP, 0 FAIL za 185,10 s. Nový veřejný test
  provedl skutečný offline Maven build, compiler inspekci a JDK 21 capture
  čtyř druhů instrumentovaných faktů. Digest v2 odpovídá uloženému kontextu
  a jeho zdrojům. Chybějící a cizí digest se odmítly před spuštěním.
  Vadné pole se odmítlo při importu i při inspekci přímo z manifestu.
  Všechny odmítnuté kroky zachovaly bajty grafu, dříve importovaného
  manifestu a runtime artefaktu. Dva starší Maven testy vyžadující exporter
  umístěný v checkoutu nebo volbu dvou JDK skončily SKIP. JUnit
  `runtime-build-config-qualification-final.xml`, SHA-256
  `8535998617bdd831498d4e4720ee4dfe9cffacc9a8b568453dd4cba0a1e97b1c`.
  Shodné manifesty zdroje, testů, fixture, nástrojů a workerů mají SHA-256
  `39ac9a99cb6d1de21df084c7859917081175c9d951b77a689eba8c81a57803ab`.
- Úplná standardní sada na CPythonu 3.13.18 má 2477 PASS, 1295 SKIP
  a jeden očekávaný strict XFAIL pro původní SOURCE_ONLY ID v T047-S02.
  Běh trval 356,41 s a skončil kódem 0. JUnit
  `runtime-build-config-standard-final.xml`, SHA-256
  `3eab9c4dbbcb09514d23ecef8b181a2645f60d8d2339e3d6ff59107c19c636be`.
  Shodné manifesty testovaných vstupů mají SHA-256
  `fd41f56b6e86410581ed4e8a928835da97aa6691c3d9b28bfda0a747c4e3993e`.

Kvalifikace s Mavenem 3.9.9, JDK 21.0.6+7 a připravenými workery proběhla
v tomto prostředí.

```bash
kg_tools=/workspace/kgmaker-tools
export JAVA_HOME="$kg_tools/jdk-21.0.6+7"
export PATH="/workspace/kgmaker-evidence/runtime-build-config-tools:$JAVA_HOME/bin:$kg_tools/kotlinc/bin:$PATH"
export KGMAKER_WORKERS_HOME="$kg_tools/worker-dist"
export KGMAKER_REQUIRE_WORKERS=1 KGMAKER_REQUIRE_K2=1
export PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 JAVA_TOOL_OPTIONS=-XX:-UsePerfData
python -m pytest -n 3 -p no:cacheprovider -q --tb=short -ra \
  tests/test_runtime_trace_producer.py tests/test_build_runner.py tests/test_build_aware.py \
  tests/test_graph_provider.py tests/test_graph_publication_concurrency.py \
  tests/test_stage_content_cache.py
```

Standardní běh použil `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1` a CPython
3.13.18 s `python -m pytest -p no:cacheprovider -q --tb=short`.

## Krok 5 — veřejné použití a stav

V manifestu k importu deklarujte digest například v položce `root:main`.
Při inspekci vyberte `--context root:main`. Pro capture použijte hash z
vráceného compiler kontextu jako `--config-fingerprint`.
[CLI a příklad manifestu](../runtime-trace.md#spuštění),
[compiler kontrakt](../compiler-inspection.md), [README](../../README.md),
[stav dodání](../production-analysis-progress.md), [acceptance](../acceptance-inventory.md).

Graf ověřují `kgmaker semantic update --base 0dbe9a7`, `kgmaker semantic apply`,
`kgmaker semantic validate`, `kgmaker memory capture --base 0dbe9a7`,
`kgmaker scan`, `kgmaker status`, `kgmaker check` a `git diff --cached --check`.
GitHub Actions, Windows a nezávislé review mají stav NOT_RUN. Celý T003-S13
zůstává PARTIAL.

## Začlenění aktuálního main s #147

Prvním rodičem je `6b6d8e6287c61c52d45f4b1717e8ff767f0fd58b`, druhým
`2db5c4931bfd832908158900b2823b6c122bc3a7` se sloučeným #147.
Předání konfigurace W01 a kontroly publikace importu W02 si zachovaly původní
zdrojové změny i těla testů. Stavová matice zachovává oba dílčí rozsahy. [Doklad W02](163_revalidateRuntimeImportPublication.md).

Na společném stromu se skutečným Mavenem 3.9.9 a JDK 21.0.6+7 prošly čtyři
testy bez přeskočení za 60,50 s. Ověřily veřejný v2 capture se zvoleným
digestem, jednu plnou validaci payloadu, kontrolu v1 workeru a rollback
při změně bytecode skutečného v2 capture. JUnit `runtime-build-config-forward.xml`
má SHA-256 `44e0c08918b3db4c8066c52d177881d3cc9b5b46e76bdaeebb4574f0a7efd1a9`.
Shodné manifesty před a po tomto běhu mají SHA-256
`afe1a3feb660ed03b0bf55b7ac5f42dea583497aa6879b0006da50a506057c04`.
Manifest změn obou rodičů má SHA-256
`6605fd503a565add69fbd3ba6e8aa3705df1a96681a87d9035b6bf40fcba7ccb`.

```bash
python -m pytest -n 2 -p no:cacheprovider -q --tb=short -ra \
  tests/test_runtime_trace_producer.py::test_actual_maven_public_runtime_uses_selected_build_configuration \
  tests/test_runtime_trace_producer.py::test_runtime_import_validates_payload_once_and_rechecks_inputs_per_publication_step \
  tests/test_runtime_trace_producer.py::test_v1_cli_rechecks_worker_before_graph \
  tests/test_runtime_trace_producer.py::test_real_jdk21_v2_cli_rechecks_bytecode_before_graph
```

Úplná sada uvedená výše patří prvnímu rodiči. Pro společný strom čeká úplný
běh a nezávislé review.

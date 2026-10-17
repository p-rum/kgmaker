# Explicitní výběr externího JDK

- Change note: 10
- Datum: 2026-10-17
- Související zadání: T003-S03-W01, T003-S03, T003-AC03, T002-MV-01
- Stav: implementováno v samostatné větvi; T003-S03 zůstává PARTIAL.

## Problém

Build exporter uměl zpětně uvést JVM, ale BuildPlan neumožňoval vybrat konkrétní
externí JDK. Maven nebo Gradle proto mohl být spuštěn jiným Java home, než který
uživatel zamýšlel, a plán neměl content-bound důkaz vybraných JDK binárek.

## Skutečné změny

- `project build-plan` přijímá `--java-home`.
- Plán obsahuje kanonický Java home, SHA-256 `java` a `javac`, selection fingerprint
  a omezený `JAVA_HOME` override; všechny položky kryje stávající `plan_hash`.
- BuildRun před mutací ověří vybrané binárky, nastaví `JAVA_HOME` a vloží JDK `bin`
  na začátek `PATH`.
- Export z jiného Java home přejde do `TOOLCHAIN_UNAVAILABLE`, přidá
  `EXPLICIT_TOOLCHAIN_MISMATCH` a žádný context nedostane čerstvý output.
- BuildManifest validuje selection fingerprint, aktuální hashe vybraných binárek (`STALE_TOOLCHAIN`) a při úspěchu shodu s toolchainem
  každého exportovaného contextu.

## Kompatibilita a migrace

Pole `environment_overrides` a `toolchain_selection` jsou v build-plan-v1 i
build-manifest-v1 volitelná. Starší plány a importované manifesty bez explicitní
volby zůstávají čitelné a používají dosavadní host-default chování. Store ani graph
schema se nemění.

## Testy a výsledky

- Nová regrese omezeného environment allowlistu nejprve FAILED (1 failed), po
  opravě vynucení `JAVA_HOME` PASS. Explicitní override je nyní použit i když
  uživatel dovolí pouze `PATH`.
- `KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 python3 -m pytest -q tests/test_build_runner.py`
  — 13 passed in 6.15 s.
- Stejný environment a `python3 -m pytest -q` — 200 passed in 37.78 s.
- Skutečná fixture `test_external_toolchain_two_real_jdks` provádí offline Maven
  compile/test-compile skutečných zdrojů přes JDK 22.0.1 a systémové JDK21.
  Manifesty obsahují odlišné skutečné verze, home a fingerprints.
- `git diff --check`, semantic update/apply/validate/scan a memory capture —
  PASS; semantic validate: 22 concepts, 9391 relationships.

## Neprovedené kontroly a hranice

Gradle skutečný běh dvou JDK nebyl proveden; společný runner zajišťuje explicitní
launcher selection a odmítne export odlišného home. Maven compiler-plugin fork
nebo pluginem vybraný JDK nejsou touto launcher volbou dokázány. Stávající exporter
je zkompilován pro Java21; pokus přes instalované JDK17 skončil FAILED s class-file
version 65/61 bez čerstvých artefaktů. Podporovaná reálná matice je Maven/JDK21+22.
Starší JDK vyžaduje kompatibilně sestavenou trusted distribuci exporteru.
Gradle custom varianty a included builds patří do dalších work packages.

## Příklad

```bash
kgmaker project build-plan --root . --build-system maven \
  --java-home /opt/jdk-21 --output /tmp/kgmaker-plan.json
kgmaker project build-run --plan /tmp/kgmaker-plan.json
```

## Zbývající práce

T003-S03-W02 až W05: Gradle custom varianty, included builds, Kotlin compiler
options a obsahové mapování cross-repo artefaktů.

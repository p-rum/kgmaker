# Obsahové mapování cross-repo artefaktů

## Problém

Workspace uměl kvalifikovat repository identity, ale volitelný `release_mapping`
nevalidoval ani nepoužíval. Stejný GAV, název JARu nebo class name tak neměl
bezpečný kontrakt pro propojení producer outputu s consumer classpath.

## Skutečné změny

- Workspace manifest validuje versioned `release_mapping` v1 s explicitním
  producer BuildManifestem, producer/consumer contextem a SHA-256 outputu.
- Build vrstva vybere právě jeden úspěšný execution-bound output; provider
  offline ověří fresh compiler snapshot a právě jeden classpath artefakt se
  stejným obsahem.
- Silné mapování přijímá pouze běžné soubory. Directory output/classpath je
  `PARTIAL`, protože stávající JVM directory hash pokrývá `.class`, ne všechny
  resource bytes; symlink je rovněž odmítnut.
- Finální pre-publication snapshot opakuje kontrolu typu i hashe producentova
  outputu a consumer classpath. Same-byte záměna souboru za symlink mezi
  resolution a publikací proto skončí chybou bez změny store/cache.
- Ověřený pár vytvoří repo-qualified `workspace_release_output` a
  `workspace_classpath_artifact` s hranou `supplies_classpath`.
- Chybějící, stale, rozdílný nebo duplicitní obsah zůstane `PARTIAL` s
  lokalizovanou `RELEASE_*` diagnostikou a bez silné hrany.
- Absence `release_mapping` zachovává starý workspace vstup. Graph/store schémata
  v1/v2/v3 zůstávají čitelná; invalidní nový kontrakt nezmění poslední store.

## Vazba na zadání a acceptance

- `T003-S03-W05`
- `T003-S03-W05-AC01` až `T003-S03-W05-AC04`
- nadřazené `T003-AC03` a průřezové `T003-R01` až `T003-R10`

## Kompatibilita a příklad

Producenti mohou mít shodné `example:shared:1.0` i
`example/Shared.class`. Pokud mají odlišné JAR bytes, mapování jednoho z nich
nevytvoří hranu k consumer classpath obsahujícímu druhý. Identitou je deklarovaný
hash běžného souboru v aktuálně validním BuildManifestu a compiler contextu.

## Provedené kontroly

- `PYTHONPATH=src python3 -m pytest -q tests/test_cross_repo_artifacts.py`
  — 8 passed, včetně directory/resource mismatch, přímé consumer-directory
  hranice a same-byte file-to-symlink race regrese.
- `python3 -m pytest -q tests/test_cross_repo_artifacts.py tests/test_workspace.py tests/test_build_runner.py tests/test_graph_provider.py`
  — 41 passed, 2 skipped; skips byly následně pokryty explicitním host během.
- `KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 python3 -m pytest -q -rs tests/test_build_runner.py`
  — 13 passed, včetně skutečného Maven exporteru a JDK21/JDK22.
- `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1 python3 -m pytest -q`
  — původní commit 205 passed, bez skipů; finální běh po CR opravě je uveden níže.
- `PYTHONPATH=src KGMAKER_REQUIRE_WORKERS=1
  KGMAKER_TEST_OTHER_JAVA_HOME=/home/petra/.jdks/openjdk-22.0.1
  python3 -m pytest -q` po obou opravách code-review findingů — 208 passed,
  bez skipů, 42,32 s.

- Po integraci nad aktuální `feat/impl` (`f03b27f`, strom `77045b27`)
  prošlo `PYTHONPATH=src python3 -m pytest -q tests/test_cross_repo_artifacts.py tests/test_workspace.py tests/test_graph_provider.py tests/test_build_runner.py`
  s výsledkem 45 PASS a 2 SKIP bez toolchain prostředí. Plný přísný běh
  `KGMAKER_REQUIRE_WORKERS=1 KGMAKER_TEST_GRADLE=<Gradle 8.13> KGMAKER_TEST_OTHER_JAVA_HOME=<JDK 22> PYTHONPATH=src python3 -m pytest -q -rs`
  s připraveným Maven exporterem a JVM/TypeScript/React fixtures prošel
  **242 PASS, 0 SKIP v 99,72 s**. První sandboxovaný pokus měl 237 PASS
  a 5 selhání kvůli blokované native Gradle knihovně a chybějícím React typům
  v izolovaném worktree; všech pět testů po doplnění prostředí prošlo.
- Integrovaná sémantika zachovala všech 36 dosavadních epizod před závěrečným
  memory capture; `kgmaker semantic validate`, `kgmaker scan`, `kgmaker check`
  a `git diff --check` prošly.
- Scoped semantic update/apply/validate zachoval nesouvisející vztahy; memory
  capture vytvořil content-bound implementační episode a následný `kgmaker scan`
  obnovil strojový i lidský graf.
- `python3 -m py_compile` pro změněné Python moduly/test a `git diff --check`
  — prošly.

## Neprovedené kontroly

Runtime deployment nebyl spuštěn ani pozorován; není součástí tohoto work package.

## Zbývající práce

Mapování neodvozuje release kompatibilitu z GAV/názvu a nevytváří JVM method-call
hrany přes repozitáře. Included builds, custom Gradle varianty, K2 dispatch a
runtime deployment patří do samostatných work packages.

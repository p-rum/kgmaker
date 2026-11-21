# Obnovení stažení připnutých závislostí Kotlin K2

T003-S04-W01 / T003-S04-W01-AC03–AC04, nadřazené T003-AC04.
Výchozí `main` je `4011825b15e4b65e1f57576a0986ca05b3cf810e`.

## Oprava

Ve dvou bězích `compiler-workers` na [#140](https://github.com/p-rum/kgmaker/pull/140/checks)
21. 11. 2026 prošel build Maven fixtures a K1 workeru. Explicitní stažení
K2 v `workers/jvm/fetch_k2.py` skončilo chybou DNS `[Errno -3] Temporary
failure in name resolution` v jobech `136930443545` a `136931951358`.
Build K2 a testovací sada mají v těchto bězích stav přeskočeno.

`workers/jvm/fetch_k2.py` používá pro Kotlin 2.1.10
[repozitář Kotlin v JetBrains Packages](https://packages.jetbrains.team/maven/p/kt/kotlin-ide-plugin-dependencies).
[Přesměrovač Kotlinu](https://redirector.kotlinlang.org/maven/kotlin-ide-plugin-dependencies)
potvrdil adresu pro připnutý JAR `low-level-api-fir-for-ide-2.1.10.jar`
odpovědí HTTP 307. Pokus s repozitářem `ij/intellij-dependencies` pro
novější API skončil po pěti připnutých JAR souborech chybou HTTP 404.
[JetBrains KT-78662](https://youtrack.jetbrains.com/projects/KT/issues/KT-78662/Analysis-API-2.2.0-artifacts-not-published).

Stahuje se stále sedm JARů JetBrains z jednoho repozitáře a Caffeine 2.9.3
z Maven Central. Zápis staženého JARu vyžaduje shodný SHA-256 z původního
locku a velikost nejvýše 32 MiB. Builder pracuje offline. CI vyvolává
dosavadní explicitní příkaz. KGMAKER CLI, instalace, inspection, graph
schema a task registry používají dosavadní kontrakty. Návod a evidence jsou
v [README](../../README.md), [compiler inspection](../compiler-inspection.md#t003-s04-w01--explicitní-k2-analysis-api),
[stavové matici](../production-analysis-progress.md) a [acceptance inventáři](../acceptance-inventory.md).

## Ověření v Cloud Environmentu

- RED — původní skript z výchozího SHA s původním lockem a prázdným
  `--output` skončil na `Tunnel connection failed: 403 Forbidden` a nezapsal
  žádný soubor. GitHub zaznamenal výše uvedenou chybu DNS.
- PASS — `python workers/jvm/fetch_k2.py --output "$K2"` v novém prázdném
  adresáři stáhl přesně osm souborů. Nezávislá kontrola změřila velikosti
  všech osmi JARů a porovnala všech osm SHA-256 s původním lockem.
  SHA-256 protokolu kontroly `3e738edf8b919dfa1db71c20cf210927ccf140f92aa746949d8d395e3730b477`.
- PASS — skutečný build K2 s JDK 21.0.6, Kotlinem 2.1.10 a připraveným Maven
  repozitářem pro Jackson 2.18.2. Build K1 nad stejným compilerem a JDK
  prošel také. Git po buildech potvrdil bajtovou shodu obou locků.

  ```bash
  python workers/jvm/build.py --backend k2 --analysis-api-home "$K2" \
    --kotlin-home "$KOTLIN_HOME" --maven-repository "$MAVEN_REPOSITORY" \
    --java-home "$JAVA_HOME"
  python workers/jvm/build.py --kotlin-home "$KOTLIN_HOME" \
    --maven-repository "$MAVEN_REPOSITORY" --java-home "$JAVA_HOME"
  ```

  SHA-256 JARu K2 `588c9ddbef69917c91e1f0f755229a6fc488605e8dbaeca63a3308f95baabaf2`.
- PASS — 51 testů za 92,76 s, bez chyb a přeskočení. 33 testů ověřilo
  K2 včetně skutečné mixed fixture, neplatného staženého obsahu a offline
  refresh. Zbývajících 18 ověřilo rozhodnutí FAIL/SKIP při chybějících
  předpokladech `compiler-workers`.

  ```bash
  KGMAKER_REQUIRE_K2=1 KGMAKER_REQUIRE_WORKERS=1 PYTHONPATH=src python -m pytest \
    -p no:cacheprovider -q --tb=short -ra tests/test_k2_backend.py \
    tests/test_mandatory_worker_ci.py
  ```

  SHA-256 JUnit `78c0d283d3bffd6fa9a531077aca0681ec104c45513e2939a1ea338e8265d597`.
- NOT_RUN — úplná sada projektu a GitHub Actions pro změněnou adresu.
  Další compiler verze, Windows a zbývající části T003-AC04 čekají na ověření.

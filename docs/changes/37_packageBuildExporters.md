# Distribuce Maven/Gradle exporterů s ověřením obsahu

Datum: 2026-10-26. Zadání: [T003-S11-W02](../tasks/T003-S11-02-buildExporterPackaging.md),
AC01–AC04, nadřazené T003-AC11. Baseline integrace:
`aa9e64bbec0bfea4bf143824dcc3d8ddf5cd6533`; závislosti T003-S03-W03/W04
jsou již v main. T003-S11 zůstává PARTIAL.

## Problém a skutečná změna

W01 již přenášelo adapter soubory do wheelu, ale chyběl distribuční hash/protocol
kontrakt, licence a skutečný build exporter acceptance mimo checkout.
`workers/build/exporters.json` nyní popisuje protocol/schema1, SHA-256 adapterů,
očekávané export ID a licenci Apache2.0. Maven builder explicitně vytvoří JAR
včetně aktualizovaného descriptoru; aktualizuje také hash Gradle scriptu. Žádný
builder se nespouští implicitně při instalaci nebo analytických příkazech.
JAR obsahuje vlastní EventSpy, nikoli Maven/Gradle/JDK runtime nebo knihovny.

`build_runner.create_plan` ověřuje hash a dostupnost licence před spuštěním
procesu. Aditivní `exporter_contract` váže descriptor a licenci do plan hash;
změna mezi plan/run je odmítnuta před vytvořením execution directory. Default
packaged resources vyžadují descriptor; jeho odstranění nemá legacy fallback.
`run_plan` kontroluje schema/exporter ID výstupu před publikací manifestu.
Graph/store se na chybě nemění a chybný export nevytvoří compiler evidence.
Checksums vážou obsah, nejsou podpisem ani autentizací dodavatele.

Explicitní legacy workers home bez descriptoru i staré plány zůstávají v původním
content-bound režimu. Přítomný descriptor je závazný, nikdy se neignoruje při
hash/protocol chybě. Graph/BuildManifest v1 a graph v1/v2/v3 zůstávají beze změny;
BuildPlan v1 získává pouze volitelné pole se schématem. Existující workflow/store
ani availability katalog nejsou nahrazeny.

Rekognoskace: project skill kgmaker, status (chyběl lokální JSON index),
scan/GRAPH/NOTES/query, memory recall, zdroj build_runner/build_model/inspection,
worker build skripty a existující testy. Samostatný durable task vznikl pomocí
`kgmaker task add`; scoped semantic/memory workflow zachovává upstream historii.

## Ověření a mapování AC

- AC01: `test_installed_exporters_run_real_builds_outside_checkout[maven|gradle]`
  skutečně vytvoří sdist → offline wheel → čistý venv a spustí oba adaptery z
  instalovaných resources mimo checkout. Java source se skutečně zkompiluje;
  manifest projde původním `validate_manifest`, obsahuje produkční output a graph
  soubor zůstane byte-identický. Maven build je explicitní (může stáhnout pluginy),
  Gradle fixture běží offline; instalace samotná nevyžaduje síť.
- AC01/03: tři nejprve FAIL reprodukce pro adapter hash, protocol a změněný
  descriptor; po opravě procházejí před procesem a před run directory mutací.
- AC02: `test_explicit_legacy_home_preserves_existing_plan_contract` a existující
  `tests/test_build_runner.py`; žádná migrace graph/store.
- AC03: output protocol mismatch explicitního testovacího child procesu nevytvoří
  manifest a zachová graf. Chybějící packaged descriptor nevolí legacy cestu.
- AC04: README, capability docs, BuildPlan schema a obě stavové matice uvádějí
  přesný omezený scope, nikoli dokončení celého T003.

Skutečné verze: Python3.12.14, pytest8.3.4, Temurin21.0.6+7, Maven3.9.9,
Gradle8.13 (ověřený distribuční SHA-256), setuptools84.2.1, wheel0.48.0.
Build exporter byl explicitně sestaven offline existujícím Python builderem.
První pokus skutečného testu: 4 PASS/2 FAIL — Maven compiler3.10.1 neměl úplnou
lokální dependency cache a Gradle nemohl zapisovat do výchozího native cache.
Podporovaný compiler3.13.0 a explicitní writable GRADLE_USER_HOME tyto požadavky
prostředí vyřešily; assertion nebyla odstraněna ani nahrazena mockem.

Cílené skutečné oba exportery: původně 6 PASS v46.08s; navazující finální sada
zahrnuje navíc missing-descriptor a legacy kompatibilitu.
První strict plná sada před konečnou integrací/metadatovou úpravou:
267 PASS/9 SKIP v170.63s; nejde o finální ověření nového main.
Finální výsledky jsou doplněny po posledním běhu níže.

## Použití a zbývající práce

```bash
python workers/build/build.py --maven-home /opt/apache-maven-3.9.9 --java-home /opt/jdk21
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/kgmaker-dist .
# V samostatném venv mimo checkout:
python -m pip install --no-index --no-deps /tmp/kgmaker-dist/kgmaker-0.1.0-py3-none-any.whl
kgmaker project build-plan --root /path/to/project --phase compile --output /tmp/plan.json
kgmaker project build-run --plan /tmp/plan.json
```

CI Gradle job explicitně připraví Maven exporter a vyžaduje skutečné oba
installed-wheel testy (`KGMAKER_REQUIRE_EXPORTERS=1`); tento změněný vzdálený CI
zde ještě není proveden. Windows, immutable atomická distribuce workerů,
autentizovaná release publikace a úplná benchmark/acceptance banka zůstávají
samostatné work packages. SOURCE_ONLY nadále nevyžaduje žádný JDK/Node/build.

## Finální ověření integrovaného worktree

- `KGMAKER_REQUIRE_EXPORTERS=1 JAVA_HOME=/workspace/tools/jdk-21.0.6+7 GRADLE_USER_HOME=/workspace/tools/gradle-cache MAVEN_OPTS=-Dmaven.repo.local=/workspace/tools/m2 PATH=/workspace/tools/jdk-21.0.6+7/bin:/workspace/tools/apache-maven-3.9.9/bin:/workspace/tools/gradle-8.13/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_exporter_distribution.py`: **8 PASS** v30.47s; oba skutečné installed exporters, nikoli mocky.
- `JAVA_HOME=/workspace/tools/jdk-21.0.6+7 KGMAKER_REQUIRE_WORKERS=1 GRADLE_USER_HOME=/workspace/tools/gradle-cache MAVEN_OPTS=-Dmaven.repo.local=/workspace/tools/m2 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`: **280 PASS / 9 SKIP** v121.34s nad main po PR8. Skutečné compiler workery mají připravené artefakty a prošly; sedm ostatních SKIP odpovídá Maven/Gradle/second-JDK prostředí a dva installed-exporter testy nemají v tomto plném běhu Maven/Gradle na PATH. Tyto dva testy byly povinně provedeny v cíleném běhu výše.
- JSON Schema Draft2020 self-check, scoped semantic update/apply/validate, implementační memory capture, scan/check a `git diff --check`: PASS.
- Vzdálené CI a Windows: NOT_RUN. Durable task předán do fáze review; toto vlastní implementační ověření nenahrazuje nezávislé PR review.

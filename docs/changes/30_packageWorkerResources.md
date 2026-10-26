# Distribuce workerů v instalovaném balíčku

Datum: 2026-10-26. Baseline: `0c0902896c4803be7e7c1246aa0ba5da45f8ebe2`.
Zadání: [T003-S11-W01](../tasks/T003-S11-01-workerCleanInstall.md),
AC01–AC04, nadřazené T003-AC11; T003-S11 zůstává PARTIAL.

## Problém a skutečná změna

Worker resolver předpokládal adresář checkoutu, který v běžném wheelu nebyl.
`pyproject.toml` nyní balí explicitní worker resources jako `kgmaker_workers`:
skripty/lockfiles, zdroje builderů a pouze předem připravené volitelné runtime
artefakty. Stejné soubory projdou sdist → wheel. Instalace nic nestahuje,
nekompiluje a nespouští npm. Licence Kotlinu a TypeScriptu se přenášejí s jejich
připravenými distribucemi.

`inspection.worker_home` volí explicitní parametr, environment, instalované
resources a nakonec checkout. Neplatná explicitní volba nemá fallback.
Chybějící či nejednoznačné artefakty vracejí TOOLCHAIN_UNAVAILABLE před zápisem
grafu. SOURCE_ONLY nepotřebuje Node/JDK. Veřejný CLI a graph/store/protocol
v1/v2/v3 se nemění. Unsupported worker language již není implicitně TypeScript.

Rekognoskace použila status (bez lokálního indexu), následný scan/query worker,
GRAPH/NOTES, memory recall a ověření `inspection.py`, `build_runner.py`, transportu,
packaging konfigurace a existujících testů. Nepřidává paralelní store ani důkazy.

## Ověření

- `KGMAKER_REQUIRE_WORKERS=1 python3 -m pytest -q tests/test_worker_install.py`:
  7 PASS. Dva skutečné sdist/wheel buildy a offline čisté venv mimo checkout;
  core bez runtimů/procesů, JVM/TS analýza z instalace, precedence, ambiguity a
  zachování posledního grafu při chybě. Python 3.12, setuptools 84.2.1,
  TypeScript 5.7.3, Node 24, Temurin 21.0.6, Kotlin 2.1.10.
- CI a vývojový příkaz explicitně instalují setuptools 84.2.1 a wheel 0.48.0.
  První CI na Pythonu 3.13 odhalilo chybějící globální setuptools po isolated
  editable buildu; nový běh má Python 3.11/3.12/3.13 a rendering PASS.
- Instalační + worker transport sada před posledním rozšířením sdist kontroly:
  11 PASS, 0 SKIP.
- Skutečná Maven 3.9.9 fixture: BUILD SUCCESS, JUnit 1 PASS, 0 SKIP.
- `KGMAKER_REQUIRE_WORKERS=1 python3 -m pytest -q`: **244 PASS / 5 SKIP**
  za 138.44 s; Gradle/druhé JDK nejsou připraveny. Oba workery jsou skutečné,
  ne mocky. Finální `git diff --check`, semantic apply/validate, scan/check PASS.
- Počáteční běh: 221 PASS / 21 SKIP bez připravených toolchainů. První strict
  běh: 242 PASS / 5 SKIP / 2 FAIL kvůli Maven proxy/cache; reactor po konfiguraci
  prostředí PASS, chybějící offline all-open 1.9.25 dependency byla explicitně
  připravena skutečným buildem. Nejde o opravu nebo obejití assertion.

## Použití a hranice

`kgmaker inspect frontend --root /path/to/project --worker-home /opt/trusted/workers`
použije výhradně zvolenou distribuci. Bez přepínače instalace používá vlastní
resources. Release builder připraví workery explicitně a sestaví wheel z čistých
zdrojů; uživatel může instalovat i core bez binárních artefaktů.

Windows transport, immutable publication, úplné benchmark/acceptance pokrytí,
distribuce JDK/Node a zbývající T003/T004 features nejsou touto změnou dokončeny.
Gradle a druhý JDK zde nebyly připraveny; jejich skutečné testy zůstávají SKIP.

## Integrační ověření 2026-10-26

Revize 2 zadání opravuje závislost samotného balení: existující worker protocol
nevyužívá budoucí golden corpus ani callback/generic resolution. Beze změny
AC01–AC04 umožňuje distribuovat současný podporovaný rozsah; T003-S04-W05,
T003-S08-W03 i celkové release gates zůstávají povinné a nedokončené.
Technickou nezávislost ověřilo samostatné code review resolveru a protokolu.

Znovu byly explicitně připraveny Maven 3.9.9, Kotlin 2.1.10 a Jackson 2.18.2
(shoda distribučních/lockfile checksumů), Temurin 21.0.6+7 a TypeScript 5.7.3.
Skutečný Maven fixture build: BUILD SUCCESS, JUnit 1 PASS/0 SKIP.
`KGMAKER_REQUIRE_WORKERS=1` s tímto JDK a
`/workspace/kgmaker-venv/bin/python -m pytest -q`: **242 PASS / 7 SKIP**
za 103.12 s, včetně skutečných instalací sdist → wheel mimo checkout.
Maven nebyl na testovacím PATH, Gradle a druhý JDK nebyly připraveny;
příslušných sedm testů je explicitně SKIP. Před přípravou úplného JDK selhal
instalační test na systémovém JRE a před skutečným Maven buildem strict sada
hlásila 14 setup errors; tyto pokusy nejsou vydávány za PASS.
Semantic apply/validate a check PASS; navazující integrace do aktuálního main
vyžaduje nové review přesné base/head dvojice a zelené CI.

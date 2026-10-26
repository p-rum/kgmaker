# Windows user-space instalace a portable worker transport — kandidát

Datum: 2026-10-26. Zadání:
[T003-S11-W03](../tasks/T003-S11-03-windowsNoAdminInstall.md), AC01–AC04,
nadřazené T003-AC11. Baseline `e656b8ef4c174d3d60600037d7c0d78fc514e39d`.
Závislosti W01/W02 jsou sloučeny (PR18/22). **Windows CI zatím NOT_RUN**;
tento dokument neprohlašuje Windows acceptance ani celý release za hotové.

## Problém a skutečná změna

Původní transport registroval anonymní stdin/stdout/stderr pipe do selectors a
volal `os.set_blocking`, což není přenositelné na Windows socket-only selectors.
Před implementací veřejný transport test s nedostupným pipe selectorem FAIL
(`OSError: pipes are not sockets`). Nyní concurrent stdin/stdout/stderr obsluhují
I/O threads s omezenou queue (osm bloků), stejným response/stderr limitem,
deadline a cancellation. Ukončení procesu odblokuje writer/readery; po chybě se
join/close provede před návratem. Windows EINVAL při předčasném zavření stdin se
stejně jako BrokenPipe přenechá následné validaci stdout/exit-code, místo falešné
náhrady protocol chyby. Protocol1 a striktní JSON validace zůstávají stejné.

Explicitní worker builder používá JDK native executables včetně `.exe`,
`os.pathsep` a přímý Java entrypoint již existujícího Kotlin2.1.10 compileru,
nikoli `.bat`/shell launcher. Tím se nemění K1 analyzační backend. Maven exporter
builder také vybírá JDK exe; descriptor/packaging W02 se nemění. JVM inspection
před procesem odmítne JRE bez sousedního javac a známý JDK<21 s konkrétním
TOOLCHAIN_UNAVAILABLE; SOURCE_ONLY zůstává bez runtimů.

Windows BUILD_EXECUTE nebyl ověřen a dosavadní POSIX process-group/batch launcher
cesta se netváří jako podporovaná: build-plan/run na Windows nyní vrací
UNSUPPORTED_PLATFORM s BUILD_IMPORT next step před procesem nebo mutací run/store.
Nejde o přidání Windows Maven/Gradle execution podpory ani o nový graph store.

## Skutečný Windows CI gate (dosud nespouštěn)

Nový `windows-user-install` job používá windows-latest/Python3.12/Temurin21.0.6/
Node24.19.0. `runas /trustlevel:0x20000` spustí skutečný Windows SAFER normal-user
token; PowerShell a Python nezávisle kontrolují, že administrator membership je
false. Elevated běh nemůže projít jako PASS. Setup actions dodají původní pinned
runtimy, ale kopie JDK/Node, venv, explicitní worker buildy a installed smoke
běží až pod omezeným tokenem v uživatelském profilu. Source, runtimy, caches,
venvs i Kotlin project mají cesty s mezerami.

Maven3.9.9 a Kotlin2.1.10 archivy mají checksum; Jackson2.18.2 se ověřuje proti
committed dependency lockfile v builderu. Maven/Kotlin/JDK/Node nejsou implicitně
instalovány produkčními analytickými příkazy. Script explicitně připraví artefakty
před dvěma sdist → offline wheel → čistými venv instalacemi. Core no-tools scan,
Java, stávající K1 Kotlin a TS source calls ověřují původní store/protocol;
K2 Windows není tvrzeno. Chybějící povinný runtime zde vyvolá FAIL, ne SKIP.
Výstup/return marker a transcript jsou reviewovatelný CI artefakt.

## Provedené lokální kontroly

- Projektový skill kgmaker, status (lokální JSON index chyběl), scan/GRAPH/NOTES,
  query, memory recall a přímá rekognoskace transportu, builderů, resolveru,
  packaging a testů. Závislosti jsou ověřeny v baseline main; durable task
  vznikl pomocí `kgmaker task add`.
- `python3 workers/jvm/build.py --kotlin-home /workspace/tools/kotlinc --maven-repository /workspace/tools/m2 --java-home /workspace/tools/jdk-21.0.6+7`:
  SUCCESS, skutečný offline build novým přímým Java launcherem a ověřené hashes.
- `python3 workers/build/build.py --maven-home /workspace/tools/apache-maven-3.9.9 --java-home /workspace/tools/jdk-21.0.6+7`:
  SUCCESS, skutečný offline exporter build.
- `KGMAKER_REQUIRE_WORKERS=1 JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH KGMAKER_WORKERS_HOME=/workspace/windows-install/workers PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_worker_protocol.py tests/test_worker_install.py tests/test_windows_install.py`:
  původní portable/installed sada **16 PASS / 1 SKIP**, 22.31s. Jediný SKIP je
  skutečný Windows gate, nikoli chybějící Java/Kotlin/TS worker. Wheel install
  i project paths obsahují mezery; žádný worker není mock.
- Po explicitních JRE/JDK17 a early-stdin-close regresích:
  `PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_worker_protocol.py tests/test_windows_install.py`:
  **11 PASS / 1 SKIP**, 0.53s, Linux. Pokrývá cancel blokovaného writeru,
  souběžný large stdin/stderr, output limit, strict JSON, unsupported platform a
  procesně prázdnou prerequisite diagnostiku.
- Finální strict celá sada:
  `KGMAKER_REQUIRE_WORKERS=1 JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH KGMAKER_WORKERS_HOME=/workspace/windows-install/workers PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q`:
  **306 PASS / 10 SKIP**, 75.58s. Devět SKIP odpovídá nedostupnému Maven/Gradle/
  second-JDK výběru a dvěma exporter variantám bez executable na PATH; dřívější W02 acceptance se
  tím nepřepisuje. Desátý SKIP je skutečný Windows gate. Compiler workery byly
  připraveny v tomto checkoutu; fixture Maven outputs byly výslovně převzaty z
  dříve úspěšného genuine buildu, nejde o nový Maven projekt build v tomto tasku.
- Workflow YAML parse PASS; portable PowerShell7.4.6 parser na Linuxu zkontroloval
  oba PS skripty bez syntaktické chyby. Distribuční SHA256 parseru byl ověřen.
  Tento parser **není** Windows běh.
- Scoped semantic update/apply/validate, memory capture, command-generated
  scan/check a diff check: PASS. Historické semantic vztahy nejsou nahrazeny;
  nevymýšlí se nový runtime ani availability důkaz.

## AC a kompatibilita

- AC01: skutečný Windows restricted-user smoke je připravený, dosud NOT_RUN.
  Lokální Linux worker/core smoke PASS není jeho náhrada.
- AC02: protocol1, graph/store v1/v2/v3 a worker home precedence beze změny;
  existující loader/compiler/install regrese prošly na Linuxu.
- AC03: příslušné transport/no-tools/prerequisite testy ověřují žádné implicitní
  procesy ani přepsání posledního grafu. Windows BUILD_EXECUTE je fail-closed;
  žádný static/build výsledek nezískává runtime data availability.
- AC04: README, Windows/capability guide i acceptance/progress matrix explicitně
  rozlišují provedený Linux běh od čekajícího Windows CI výsledku.

Uživatelské příklady a prerequisite cesty jsou v [Windows guide](../windows-install.md).
Windows gate musí proběhnout na publikovaném exact HEAD před konečným přijetím
W03; kandidát proto patří do draft PR. Zbývá skutečný Windows výsledek.
Immutable publikace, obecná production matice, benchmarky,
Windows build execution a K2 Windows scope se tímto taskem neprohlašují za hotové.

## Oprava review P1: zděděné pipes po ukončení workeru

Nezávislé review odhalilo, že exit přímého workeru neznamená EOF jeho pipes:
živý potomek je může stále držet. Původní `_terminate` přeskočil POSIX killpg
po exit parentu a buffered close čekal na reader lock až do exit potomka.
Nová skutečná regrese na původním kandidátu `4f07f21` selhala pro timeout i
cancel: **5.17s / 5.28s**, místo požadovaného návratu pod 3s.

POSIX nyní ukončuje vlastní process group i po exit leaderu. Raw nonblocking
pipe I/O průběžně kontroluje stop event; cleanup nespoléhá na EOF ani na
uvolnění buffered read locku. Windows spustí worker suspended, před spuštěním
jeho kódu ho připojí do Job Object s KILL_ON_JOB_CLOSE a obnoví hlavní thread
přes dokumentované Toolhelp/OpenThread/ResumeThread API. Job drží potomky i po
exit leaderu a zavírá se před join readerů. Není použit shell, taskkill ani
admin právo; odmítnuté přiřazení je explicitní TOOLCHAIN_UNAVAILABLE.

Regrese ověřuje elapsed bound pro timeout i cancel po prokázaném exit parentu,
reap přímého procesu, uzavřené streams, žádný transport thread, nezměněný graph
sentinel a na Linuxu nezvýšený počet FD i ukončeného potomka. Zachovává se input,
response i stderr bound. `tests/test_worker_protocol.py`: **9 PASS**, 1.84s;
transport + Windows prerequisite sada: **12 PASS / 1 SKIP**, 1.91s (Linux).
Job Object a nový regression test jsou součástí skutečného Windows CI gate;
Linux PASS nepředstavuje důkaz jeho Windows chování.

Integrace zachovává main `7b9a9eaecaf41c9c5bc5a6d1233cd82e2cf4f1e9`, T006/T007,
Confluence konfiguraci i úplnou immutable historii. Semantic merge zachovává
čtyři ověřené concepts a osm vztahů včetně obnovených semantic.py vazeb;
README evidence se znovu váže na skutečné řádky výsledného souboru.

Po integraci main a cleanup opravě strict own-worker celá Linux sada:
**356 PASS / 10 SKIP**, 101.74s. Příkaz je shodný s výše uvedeným strict
příkazem; Windows gate zůstává mezi SKIP. Poslední zpřesnění FD/descendant
assertions prošlo samostatně v devíti transport testech (1.84s).

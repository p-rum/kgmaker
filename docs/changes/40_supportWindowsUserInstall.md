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

## Skutečný Windows CI gate (původní kandidát před opravou harnessu)

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

## Skutečný Windows CI: selhání launcheru a oprava

Run `40343225493`, job `121643195548` na Windows Server2025 skončil FAILED
před smoke: `runas /trustlevel` vrátil nonzero, nevznikl transcript ani result.
Původní harness nevypsal číselný exit code ani runas diagnostiku; přesná příčina
proto z tohoto logu není doložitelná. Tento výsledek není Windows acceptance.

Harness nyní používá dokumentované `CreateRestrictedToken` a
`CreateProcessAsUserW` místo konzolového runas. Vlastní primary token má
DISABLE_MAX_PRIVILEGE a Administrators SID deny-only; žádný elevated fallback.
Child se spustí suspended, připojí k Job Object, pak pokračuje. Launcher
čeká na skutečný exit (nejvýše15min), vlastní celý strom a zavírá token/process/
thread handles i při setup chybě. Win32 API errors, PID a číselný exit code
jdou do `restricted-launcher.log`; transcript a result pocházejí ze smoke.
PowerShell i skutečný Python smoke stále nezávisle vyžadují false admin
membership a paths with spaces. Chybějící result nebo failed launcher je FAIL.
Windows zůstává PENDING do nového skutečného CI běhu.

Lokálně po opravě harnessu: Python compile a workflow YAML parse PASS; oba
PowerShell skripty projdou parserem PowerShell7.4.6 na Linuxu (syntax only).
Transport/prerequisite regrese **12 PASS / 1 Windows SKIP**. Přímý pokus
spustit restricted launcher na Linuxu správně vrací exit1 s explicitním
`requires actual Windows`; nejde o emulovaný Windows PASS. Produkční transport
se od strict356PASS baseline nemění, proto se drahý celý suite neopakuje.

## Doplňující review: vlastnictví inicializace a asynchronní kill

Nezávislý reviewer potvrdil další dvě cleanup mezery: chyba při POSIX
`os.set_blocking` před exchange guardem zanechala sleeping child; KeyboardInterrupt
při Windows attach/resume obcházel OSError-only guard. Request nyní vlastní celý
launch, attach, deadline i exchange pod BaseException guardem s idempotentním
abort. Nonblocking setup probíhá uvnitř exchange try před startem threadů;
job konstruktor zavírá již vytvořený handle i při BaseException. Zachovává se
původní KeyboardInterrupt a původní TOOLCHAIN_UNAVAILABLE mapování OSError
z launch/attach. Nové regrese kontrolují skutečný POSIX sleeping child po
injected setup error a cleanup simulovaného Windows attach interruptu. Simulace
je pouze fault-injection test vlastnictví, nikoli Windows acceptance.

Kontrola potomka v `/proc` nyní čeká nejvýše1s na jeho ukončení: SIGKILL je
asynchronní, takže okamžitý stav R nebyl důkaz úniku. Původní elapsed bound,
FD/thread/stream a graph invariants zůstávají. Cílená sada po opravě:
**14 PASS / 1 Windows SKIP**, 1.77s.

Reviewer dále zachytil selhání attach ještě před přiřazením do jobu: prázdný
job nezabije suspended child. `_terminate` proto ve finally vždy samostatně
kill/wait přímého child, je-li živý, i po chybě tree termination. Testovací
nepřiřazený process nyní odmítne wait, pokud před ním nepřišel direct kill;
ověřují se OSError i KeyboardInterrupt před přiřazením. Po této úpravě
cílená sada znovu **14 PASS / 1 SKIP**, 1.77s. Předchozí celá sada s init
guardy měla **358 PASS / 10 SKIP**, 106.03s; finální strict own-worker celá sada po direct-kill
pojistce má **358 PASS / 10 SKIP**, 81.61s. Windows acceptance zůstává PENDING.

## Skutečný Windows CI: startup před PowerShell skriptem

Kandidát `fe540a1`, run `40345519027`, job `121651274359`: restricted token
vznikl, PID8140 se přiřadil/resumoval, ale child skončil **3221225794 /
0xC0000142 (STATUS_DLL_INIT_FAILED)** ještě před PowerShell transcriptem/result.
Transport smoke se vůbec neprovedl. Tento FAILED výsledek zůstává evidován.

Dokumentovaný požadavek CreateProcessAsUserW je plný access tokenového useru
k window station i desktopu. Původní NULL lpDesktop dědil objekty service runneru,
jejichž admin-only přístup může po Administrators deny-only zaniknout. To je
hypotéza odpovídající startup failure, nikoli prokázaná příčina tohoto logu.
Oprava připraví izolovanou noninteractive window station a desktop s explicitní
protected DACL pouze pro tentýž user SID a SYSTEM; přesné station\\desktop předá
v STARTUPINFO. Parent svou station po vytvoření desktopu ihned obnoví, handles
si ponechá do ukončení child. Nemění se shared desktop ACL, disabled privileges,
Administrators deny-only ani nezávislé PowerShell/Python non-admin kontroly.
Launcher navíc tiskne hex child exit code a vrací normalizovaný status0/1.

Native startup musí znovu ověřit skutečný Windows CI. Lokálně pouze Python
compile a transport/prerequisite **14 PASS / 1 Windows SKIP**; žádný Linux
výsledek se neoznačuje jako Windows PASS. Produkční transport zůstává beze změny.
K2 main integrace ještě následuje odděleně; K2 Windows podpora není tímto tvrzena.

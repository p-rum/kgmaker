# Windows user-space instalace a portable worker transport — VERIFIED_IN_SCOPE

Datum: 2026-10-26. Zadání:
[T003-S11-W03](../tasks/T003-S11-03-windowsNoAdminInstall.md), AC01–AC04,
nadřazené T003-AC11. Baseline `e656b8ef4c174d3d60600037d7c0d78fc514e39d`.
Závislosti W01/W02 jsou sloučeny (PR18/22). **Skutečný Windows gate PASS** na
`d311231ed4e199ee0c19d9d5037ccfcdcdce199b`, run40351407076/job121672139333:
43 PASS / 2 scoped SKIP, 50.23s. Review/merge ještě následují; celý release
T003-S11/T003-AC11 zůstává PARTIAL. Starší odstavce níže jsou chronologická
evidence původních kandidátů; finální skutečný výsledek je na konci poznámky.

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

- AC01: skutečný Windows restricted-user smoke nyní PASS (run40351407076);
  core a deklarované Java/K1/TS workery prošly. K2 Windows zůstává neověřené.
- AC02: protocol1, graph/store v1/v2/v3 a worker home precedence beze změny;
  existující loader/compiler/install regrese prošly na Linuxu i ve Windows smoke.
- AC03: příslušné transport/no-tools/prerequisite testy ověřují žádné implicitní
  procesy ani přepsání posledního grafu, nyní také na skutečném Windows. Windows BUILD_EXECUTE je fail-closed;
  žádný static/build výsledek nezískává runtime data availability.
- AC04: README, Windows/capability guide i acceptance/progress matrix explicitně
  rozlišují provedený Linux i Windows běh a dosud neověřené K2 Windows.

Uživatelské příklady a prerequisite cesty jsou v [Windows guide](../windows-install.md).
Windows gate proběhl na publikovaném exact HEAD d311231; metadata kandidát
stále vyžaduje zelené checks a nezávislé review před přijetím PR24.
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

## Integrace K2 main před dalším Windows během

Main `eff0d3d5d7620b017fe42a65a54f672af8068667` je integrován bez změny
cleanup vlastnictví nebo private desktop launcheru. Inspection zachovává full
JDK21 prerequisite a zároveň explicitní K1/K2 JAR selection; oba installed
Kotlin testy (K1 v cestě s mezerami i K2 mimo checkout) zůstávají. Builder
kombinuje backend/source/lock/manifest folding z K2 s native exe, os.pathsep a
přímým Java compiler entrypointem z W03. Povinný K2 Linux CI i Windows gate
zůstávají zachovány.

Jedna K2 no-fallback negativní fixture původně mockovala java bez skutečného
JDK layoutu; nová prerequisite ji správně zastavila dříve. Fixture nyní připraví
explicitní fake java/javac soubory a nadále zakazuje každý subprocess, takže
znovu ověřuje skutečnou missing-K2-distribution větev (ne implicitní fallback).
Immutable historie obou větví i čtyři semantic concepts/osm vztahů se zachovají;
README evidence se znovu ověří proti výsledným řádkům.

Integrační kontroly: transport/prerequisite/K2 sada **33 PASS / 12 SKIP**, 1.91s
(11 SKIP jsou nepřipravený vlastní K2 artefakt, jeden skutečný Windows gate;
mandatory K2 CI není změněn). Skutečný offline build integrovaného K1 workeru
pomocí přímého Java launcheru SUCCESS; SHA256 JAR
`44c872c438297ca748d6ef88072ff88cacf36edb80a54ae05b64abc87dc3f203`.
Ověření byte obsahu potvrzuje, že transport, Job Object i PrivateDesktop
launcher jsou shodné s již reviewovaným startup kandidátem `6101113`.
Celý suite358 se kvůli této integraci neopakuje; povinný native gate se spustí
na novém candidate. K2 Linux implementace má vlastní main acceptance důkazy.

Po genuine buildu integrovaného workeru proběhly actual installed-wheel/core/
Java/K1 Kotlin/TypeScript smoke testy v cestách s mezerami:
`KGMAKER_REQUIRE_WORKERS=1 JAVA_HOME=/workspace/tools/jdk-21.0.6+7 PATH=/workspace/tools/jdk-21.0.6+7/bin:$PATH KGMAKER_WORKERS_HOME=/workspace/windows-install/workers PYTHONPATH=src /workspace/kgmaker-venv/bin/python -m pytest -q tests/test_worker_install.py -k 'not packaged_k2'`:
**8 PASS / 1 DESELECTED**, 45.10s. K2 installed test je zde explicitně oddělen;
nejde o důkaz K2 Windows. Semantic validate, scan/check a diff check PASS.

## Native startup diagnostika místo další neověřené opravy

Skutečný kandidát `9033d14`, run `40347960136`, job `121659870361`, opět skončil
FAILED před smoke: private desktop vznikl, PID4768 skončil 0xC0000142.
Předchozí desktop-ACL hypotéza tento běh neopravila. Windows acceptance zůstává
BLOCKED; transport assertions se ještě na Windows neprovedly.

Nový diagnostický kandidát před smoke provede omezenou matici skutečných
`cmd.exe`, pinned Python a PowerShell procesů. Původní restricted token se
porovnává na inherited/private desktopu s vlastním Job Object/bez něj. Další
oddělené diagnostické varianty porovnají explicitní process/thread object ACL,
TokenDefaultDacl a obě ACL změny dohromady; všechny grantují pouze stejný user
SID a SYSTEM, ponechávají maximum privileges disabled a Administrators deny-only.
Source a restricted default DACL se tisknou jako SDDL spolu s explicitním user
SDDL; logují se i dostupné UI restrictions parent jobu. Tím se rozlišuje default
ACL tokenu od ACL počátečních process/thread objektů, které může vytvořit
administrativní caller. ACL varianta není přijata jako oprava bez native důkazu.

Každý proces má 5s startup limit a maximálně1s direct cleanup wait, vlastní
process/thread handles a případný job se zavřou. JSON výstup obsahuje PID,
wait result, decimal/hex exit code, cleanup wait a případný skutečný Python/
PowerShell non-admin marker; Python má i marker dosažení user kódu před ctypes.
Výsledky a Application Error/WER záznamy pro cmd/Python/PowerShell se uploadují
společně s launcher logem. Toto je diagnostika, nikoli acceptance substitute.
Skutečný smoke nadále používá původní restricted token a žádná experimentální
varianta se do něj automaticky nepromítá. Není elevated fallback.

Lokálně: Python compile, YAML a PowerShell syntax parse PASS; transport/
prerequisite **14 PASS / 1 Windows SKIP**. Produkční source se nemění; další
skutečný native běh teprve dodá příčinnou evidenci.

## Native důkaz příčiny a přijetí minimální ACL opravy

Run `40350225577`, job `121667944961`, dodal skutečný kontrolovaný důkaz:
všechny původní-token i explicit-process/thread-ACL probes (cmd, Python,
PowerShell, oba desktopy i Job/no-Job) skončily 0xC0000142. Varianty s explicitním
**TokenDefaultDacl pro tentýž user SID a SYSTEM** všechny skončily EXIT0;
Python i PowerShell nezávisle zapsaly `is_admin=false`, včetně vlastního Job
Object a private desktopu. Varianta obou ACL změn také uspěla. Původní source/
restricted DACL obsahovala BA, SYSTEM a logon SID; explicitní own-user default
ACL jako jediná změna umožnila inicializaci. Původní acceptance smoke použil
nezměněný token a selhal očekávaně; tento run není full Windows acceptance.

Acceptance nyní používá přesně tuto native ověřenou restricted-token variantu
s own-user+SYSTEM default DACL. DISABLE_MAX_PRIVILEGE, Administrators deny-only,
Job vlastnictví i nezávislé non-admin kontroly zůstávají stejné. Není elevated
fallback; selhání přípravy default ACL je explicitní FAIL. Private desktop se
zatím ponechává pro izolaci, ale není příčinou opravy (native matice to vyvrátila).
Diagnostická matice a její přesné výsledky zůstávají dostupné jako regrese.
Plná skutečná Windows instalace/build/installed smoke se teprve musí provést
na novém kandidátu; dílčí native EXIT0 není za tuto acceptance vydáván.

## Finální skutečná Windows acceptance — 2026-10-26

Exact runtime/harness head: `d311231ed4e199ee0c19d9d5037ccfcdcdce199b`, base
`eff0d3d5d7620b017fe42a65a54f672af8068667`; Actions checkout byl skutečný merge
`380e04f` této dvojice. [Run40351407076](https://github.com/p-rum/kgmaker/actions/runs/40351407076)
má všech sedm jobů SUCCESS. [Windows job121672139333](https://github.com/p-rum/kgmaker/actions/runs/40351407076/job/121672139333)
prošel; [artifact12664820415](https://github.com/p-rum/kgmaker/actions/runs/40351407076/artifacts/12664820415)
obsahuje restricted launcher log, PowerShell transcript, native diagnostiku,
non-admin marker JSON a result.json. Filtrované skutečné logs byly načteny přes
GitHub job-log API, neodvozují se z Linuxu.

Ověřená matice: Windows Server2025, Windows PowerShell **5.1.26100.33648**,
CPython **3.12.10**, Temurin **21.0.6+7.0.LTS**, Kotlin compiler **2.1.10**
(K1 compatibility backend), Jackson2.18.2, Node **24.19.0**, npm11.17.0,
TypeScript **5.7.3**, Maven distribution **3.9.9**, pytest8.3.4,
setuptools84.2.1 a wheel0.48.0. Maven/Kotlin archivy a compiler dependencies
byly ověřeny stejnými committed checksum/lock kontrakty jako v CI skriptu.

Přesná spuštěná acceptance cesta (proměnné odpovídají workflow/scriptu):

```powershell
$space = Join-Path $env:USERPROFILE 'KGMAKER user space'
$source = Join-Path $space 'source checkout'
& $python (Join-Path $source 'tests/windows/restricted_launcher.py') --root $space -- $powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $source 'tests/windows/no_admin_smoke.ps1') -Python $python -WorkRoot $space
# Následuje již v restricted child, nikoli v administrativním bootstrapu:
& $developerPython workers/jvm/build.py --kotlin-home (Join-Path $space 'kotlinc') --maven-repository (Join-Path $space 'maven repository') --java-home (Join-Path $space 'java runtime')
& $developerPython workers/build/build.py --maven-home (Join-Path $space 'apache-maven-3.9.9') --java-home (Join-Path $space 'java runtime')
$env:KGMAKER_REQUIRE_WORKERS = '1'
$env:KGMAKER_REQUIRE_WINDOWS_SMOKE = '1'
$env:KGMAKER_WORKERS_HOME = Join-Path $source 'workers'
$env:PYTHONPATH = Join-Path $source 'src'
& $developerPython -m pytest -q tests/test_worker_protocol.py tests/test_worker_install.py tests/test_windows_install.py tests/test_t005_add_view_model.py
```

Child s explicitním own-user+SYSTEM TokenDefaultDacl ponechal disabled privileges
a Administrators deny-only. Native Python i PowerShell probes zapsaly
`is_admin=false`; transcript má `Restricted token administrator membership: False`.
Restricted smoke PID4120 skončil **exit0 / 0x00000000**, launcher **exit0**.
Tvrzení není založeno na názvu účtu runneradmin: testuje skutečné členství tokenu.

Všechny source/runtime/cache/venv/worker a instalované project cesty obsahovaly
mezery pod `C:\Users\runneradmin\KGMAKER user space`. JDK/Node byly zkopírovány
do user-local cest; venv/package instalace i explicitní workery vznikly až v
restricted child. JVM build SUCCESS (Windows JAR SHA256
`4e4598b7e5646a0d0d260e0785544c828dbe02ad5459a78fe0629f7baa911d44`), trusted
Maven exporter offline build SUCCESS a npm pinned TypeScript příprava prošly.
Exporter build není důkaz Windows BUILD_EXECUTE inspected projektů.

Pytest: **43 PASS / 2 SKIP**, **50.23s**:

- Protocol sada: skutečné Windows pipes, large stdin/stderr, strict JSON/output
  limit, timeout/cancel včetně již ukončeného parentu s inherited pipes, bounded
  elapsed time, žádné transport threads ani otevřené streams, graph sentinel.
- Instalace: sdist → offline wheel → čisté venv mimo checkout; core SOURCE_ONLY
  bez JDK/Node/child procesů; skutečné Java/K1 Kotlin/TypeScript calls, precedence,
  missing/ambiguous distribution a zachování posledního validního grafu.
- Native Windows non-admin/path-space gate, explicitní JRE/JDK17 prerequisite a
  unsupported BUILD_EXECUTE bez procesu nebo mutace run/store.
- T005 view/model a legacy graph/store v1/v2/v3 kompatibilita.
- Přesně dva SKIP: POSIX-only `test_nonblocking_setup_failure_reaps_child_and_closes_pipes`
  a `test_packaged_k2_analyzes_outside_checkout` bez připraveného K2 artefaktu.
  Žádný povinný deklarovaný Windows worker ani non-admin gate nebyl přeskočen.

AC01–AC04 jsou VERIFIED_IN_SCOPE pro tuto Windows matici. K2 Windows,
Windows BUILD_EXECUTE, immutable release publication, celá production/benchmark
matice a nadřazený T003-S11/T003-AC11 zůstávají otevřené/PARTIAL.
Tento commit mění pouze dokumentaci/semantic metadata, runtime/harness byte
obsah zůstává shodný s d311231. Durable task přechází do review, nikoli done;
nový exact metadata HEAD vyžaduje vlastní sedm zelených CI jobů, review a merge.

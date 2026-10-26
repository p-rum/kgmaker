# Windows instalace do uživatelských adresářů

Stav T003-S11-W03: implementační kandidát, skutečné Windows CI dosud NOT_RUN.
Linux regresní testy nejsou důkazem běhu na Windows. Úplný release T003-S11
zůstává PARTIAL; přesné lokální výsledky uvádí
[change note40](changes/40_supportWindowsUserInstall.md).

## Prerequisites a podporovaná matice kandidáta

- Python3.12 s `venv`/`ensurepip`, instalovaný pro aktuálního uživatele; žádná
  machine-wide instalace ani aktivace PowerShell venv skriptem není potřeba.
- Core scan/save/load funguje bez JDK/Node. Volitelné chybějící worker artefakty
  nepřepnou explicitní distribuci na jinou a nezmění poslední graph store.
- Java/Kotlin inspection vyžaduje plný JDK21+ (`java` a `javac` ve stejném JDK),
  ověřovaný runtime je Temurin21.0.6+7. JRE-only a známý JDK<21 jsou explicitně
  odmítnuty jako TOOLCHAIN_UNAVAILABLE před worker procesem.
- TypeScript inspection používá Node24.19.0 a předem připravený TypeScript5.7.3.
  Node/JDK lze rozbalit do vlastního uživatelského adresáře a změnit PATH pouze
  v aktuálním procesu. Wheel musí být od trusted release builderu s příslušnými
  resources, nebo lze explicitně zvolit vlastní kompletní `--worker-home`.
- Smoke pokrývá Java source call, stávající K1 Kotlin compatibility subset a TS
  source call. K2/Analysis API na Windows není tímto testem ověřeno.
- Windows BUILD_EXECUTE (`project build-plan/build-run`) zatím není podporovaný;
  vrací jasnou diagnostiku před procesem nebo mutací run/store. BUILD_IMPORT
  vyžaduje již ověřené lokální artefakty a stávající content-bound manifest.

## Instalace bez elevace

Následující příklad předpokládá již připravený uživatelský Python a trusted wheel;
instalace sama nestahuje ani nebuildí volitelné workery.

```powershell
$python = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python312/python.exe'
$venv = Join-Path $env:LOCALAPPDATA 'KGMAKER tools/clean venv'
& $python -m venv $venv
$venvPython = Join-Path $venv 'Scripts/python.exe'
$wheel = Join-Path $env:USERPROFILE 'Downloads/kgmaker-0.1.0-py3-none-any.whl'
$project = Join-Path $env:USERPROFILE 'Projects/My Project'
$frontend = Join-Path $env:USERPROFILE 'Projects/My Frontend'
& $venvPython -m pip install --no-index --no-deps $wheel
& $venvPython -m kgmaker scan --root $project
# Pouze pro explicitní inspection s připravenými runtime ZIP distribucemi:
$env:JAVA_HOME = Join-Path $env:LOCALAPPDATA 'KGMAKER tools/jdk 21'
$env:PATH = "$env:JAVA_HOME\bin;$(Join-Path $env:LOCALAPPDATA 'KGMAKER tools/node 24');$env:PATH"
& $venvPython -m kgmaker inspect code --root $project
& $venvPython -m kgmaker inspect frontend --root $frontend
```

Není nutné aktivovat `.ps1` nebo spouštět `.bat`: instalace a CLI používají přímo
Python exe, worker transport Java/Node exe. Source/config ani data-check workflow
nespouštějí project build, package installation, migrace nebo aplikaci.

## Skutečný Windows gate

Job `windows-user-install` na `windows-latest` spouští
`tests/windows/no_admin_smoke.ps1` pomocí vlastního restricted primary tokenu
(`CreateRestrictedToken` s vypnutými privilegii a Administrators deny-only,
`CreateProcessAsUserW`; launcher nepotřebuje interaktivní runas konzoli).
Restricted token má výslovný TokenDefaultDacl pro vlastní user SID a SYSTEM;
native matice prokázala, že bez něj původní admin-derived default bránil DLL
inicializaci. Privilegia zůstávají vypnutá, Administrators deny-only.
Child dostane explicitní private noninteractive window station/desktop s DACL
pro vlastní user SID a SYSTEM; ACL sdíleného runner desktopu se nemění. PowerShell i Python smoke samostatně ověřují, že
proces nemá administrator membership; elevated proces nemůže projít jako PASS.
CI bootstrap poskytne pinned runtimy z tool cache, ale explicitní příprava
workerů, venv/wheel instalace a smoke proběhnou až pod omezeným tokenem.

Source checkout, JDK, Node, caches a čisté venv jsou pod uživatelským profilem a
obsahují mezery. Worker builder ověřuje dependency lockfile; Maven/Kotlin archivy
mají distribuční checksum. Instalované sdist/wheel testy běží mimo checkout,
včetně SOURCE_ONLY s nulovými child procesy a zachování posledního grafu na chybě.
Transport gate ověřuje timeout, cancellation, output limits, současný large
stdin/stderr a cleanup blokovaného writeru. Žádný chybějící povinný runtime se v
tomto jobu nepřeskakuje.

Výsledek se publikuje až po skutečném běhu: lokální PowerShell parser a Linux
transport testy nepovyšují Windows acceptance na PASS. Podrobnosti jsou v
[T003-S11-W03](tasks/T003-S11-03-windowsNoAdminInstall.md).

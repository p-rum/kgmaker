param([Parameter(Mandatory = $true)][string]$Python,
      [Parameter(Mandatory = $true)][string]$WorkRoot)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$resultPath = Join-Path $WorkRoot 'result.json'
$logPath = Join-Path $WorkRoot 'restricted-smoke.log'
$code = 1
$isAdmin = $true
$message = ''
$transcriptStarted = $false

function Invoke-Tool([string]$Executable, [string[]]$ToolArguments) {
    & $Executable @ToolArguments
    if ($LASTEXITCODE -ne 0) { throw "Explicit tool failed: $Executable (exit $LASTEXITCODE)" }
}

function Get-VerifiedArchive([string]$Uri, [string]$Destination, [string]$Algorithm, [string]$Expected) {
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination
    $actual = (Get-FileHash -LiteralPath $Destination -Algorithm $Algorithm).Hash
    if ($actual -ne $Expected) { throw "Distribution checksum mismatch: $Destination" }
}

try {
    Start-Transcript -Path $logPath
    $transcriptStarted = $true
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) { throw 'Smoke must execute under a non-admin restricted token' }
    Write-Output "Restricted token administrator membership: $isAdmin"
    if (-not $WorkRoot.Contains(' ')) { throw 'Smoke root must include spaces' }
    $source = Join-Path $WorkRoot 'source checkout'
    Set-Location -LiteralPath $source
    $env:TEMP = Join-Path $WorkRoot 'temporary files'
    $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null

    # All runtimes, caches, venvs and explicit build outputs remain user-local.
    $javaSource = $env:JAVA_HOME
    $nodeSource = Split-Path (Get-Command node.exe).Source
    $javaDirectory = Join-Path $WorkRoot 'java runtime'
    $nodeDirectory = Join-Path $WorkRoot 'node runtime'
    Copy-Item -LiteralPath $javaSource -Destination $javaDirectory -Recurse
    Copy-Item -LiteralPath $nodeSource -Destination $nodeDirectory -Recurse
    $env:JAVA_HOME = $javaDirectory
    $env:PATH = "$javaDirectory\bin;$nodeDirectory;$env:PATH"
    $developerVenv = Join-Path $WorkRoot 'developer venv'
    Invoke-Tool $Python @('-m', 'venv', $developerVenv)
    $developerPython = Join-Path $developerVenv 'Scripts/python.exe'
    Invoke-Tool $developerPython @('-m', 'pip', 'install', 'pytest==8.3.4', 'jsonschema==4.23.0', 'setuptools==84.2.1', 'wheel==0.48.0')
    Invoke-Tool $developerPython @('-m', 'pip', 'install', '--no-build-isolation', '--no-deps', '-e', $source)

    $mavenArchive = Join-Path $WorkRoot 'maven.tar.gz'
    Get-VerifiedArchive 'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.tar.gz' $mavenArchive 'SHA512' 'a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b'
    Invoke-Tool (Get-Command tar.exe).Source @('-xzf', $mavenArchive, '-C', $WorkRoot)
    $kotlinArchive = Join-Path $WorkRoot 'kotlin.zip'
    Get-VerifiedArchive 'https://github.com/JetBrains/kotlin/releases/download/v2.1.10/kotlin-compiler-2.1.10.zip' $kotlinArchive 'SHA256' 'c6e9e2636889828e19c8811d5ab890862538c89dc2a3101956dfee3c2a8ba6b1'
    Expand-Archive -LiteralPath $kotlinArchive -DestinationPath $WorkRoot
    $repository = Join-Path $WorkRoot 'maven repository'
    foreach ($artifact in @('jackson-databind', 'jackson-core', 'jackson-annotations')) {
        $directory = Join-Path $repository "com/fasterxml/jackson/core/$artifact/2.18.2"
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri "https://repo.maven.apache.org/maven2/com/fasterxml/jackson/core/$artifact/2.18.2/$artifact-2.18.2.jar" -OutFile (Join-Path $directory "$artifact-2.18.2.jar")
    }
    # Builder verifies every dependency against the committed lockfile. No .bat
    # launcher or shell quoting is needed for Kotlin or the Java build tools.
    Invoke-Tool $developerPython @('workers/jvm/build.py', '--kotlin-home', (Join-Path $WorkRoot 'kotlinc'), '--maven-repository', $repository, '--java-home', $javaDirectory)
    Invoke-Tool $developerPython @('workers/build/build.py', '--maven-home', (Join-Path $WorkRoot 'apache-maven-3.9.9'), '--java-home', $javaDirectory)
    Invoke-Tool (Join-Path $nodeDirectory 'node.exe') @((Join-Path $nodeDirectory 'node_modules/npm/bin/npm-cli.js'), 'ci', '--ignore-scripts', '--prefix', 'workers/typescript')
    $env:KGMAKER_REQUIRE_WORKERS = '1'
    $env:KGMAKER_REQUIRE_WINDOWS_SMOKE = '1'
    $env:KGMAKER_WORKERS_HOME = Join-Path $source 'workers'
    $env:PYTHONPATH = Join-Path $source 'src'
    # W03 builds the K1 distribution. The compiler-workers job owns mandatory K2.
    Invoke-Tool $developerPython @('-m', 'pytest', '-q',
        '--deselect=tests/test_worker_install.py::InstalledWorkerTests::test_packaged_k2_analyzes_outside_checkout',
        'tests/test_worker_protocol.py', 'tests/test_worker_install.py',
        'tests/test_windows_install.py', 'tests/test_t005_add_view_model.py')
    $code = 0
    $message = 'Actual Windows restricted-user core / Java / K1 Kotlin / TypeScript smoke passed'
} catch {
    $message = $_.Exception.Message
    Write-Output $message
} finally {
    if ($transcriptStarted) { Stop-Transcript }
    $result = @{ exit_code = $code; is_admin = $isAdmin; message = $message }
    $temporaryResult = $resultPath + '.tmp'
    [IO.File]::WriteAllText($temporaryResult, ($result | ConvertTo-Json))
    Move-Item -LiteralPath $temporaryResult -Destination $resultPath -Force
}
exit $code

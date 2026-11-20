$ErrorActionPreference = 'Stop'

Write-Host '[EGM] Searching for Python 3.10+...'
$python = $null
$prefix = @()
if ($env:EGM_PYTHON) {
    Write-Host "[EGM] Using EGM_PYTHON: $env:EGM_PYTHON"
    $command = Get-Command $env:EGM_PYTHON -ErrorAction SilentlyContinue
    if (-not $command) {
        throw 'EGM_PYTHON must point to Python 3.10+.'
    }
    $python = $command.Source
} else {
    foreach ($name in @('py', 'python', 'python3')) {
        Write-Host "[EGM] Looking for '$name'..."
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $command -or $command.Source -match '\\Microsoft\\WindowsApps\\python3?\.exe$') {
            Write-Host "[EGM] '$name' is unavailable or points to a Windows Store alias."
            continue
        }
        $candidatePrefix = @()
        if ($name -eq 'py') {
            $candidatePrefix = @('-3')
        }
        Write-Host "[EGM] Checking Python version: $($command.Source)"
        & $command.Source @candidatePrefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
        if ($LASTEXITCODE -eq 0) {
            $python = $command.Source
            $prefix = $candidatePrefix
            break
        }
        Write-Host "[EGM] '$name' did not provide a compatible Python."
    }
}

if ($env:EGM_PYTHON) {
    Write-Host "[EGM] Checking Python version: $python"
    & $python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
    if ($LASTEXITCODE -ne 0) {
        throw 'EGM_PYTHON must point to Python 3.10+.'
    }
}

if ($python) {
    Write-Host "[EGM] Compatible Python selected: $python"
}

$previousPythonPath = $env:PYTHONPATH
$previousSecurityProtocol = [Net.ServicePointManager]::SecurityProtocol
$portableDirectory = $null
$moduleArguments = @('-m', 'egm_copilot')
$installerExit = 1
try {
    if (-not $python) {
        $version = '3.14.10'
        $architecture = $env:PROCESSOR_ARCHITEW6432
        if (-not $architecture) {
            $architecture = $env:PROCESSOR_ARCHITECTURE
        }
        $platform = switch ($architecture) {
            'AMD64' { 'amd64' }
            'ARM64' { 'arm64' }
            'x86' { 'win32' }
            default { throw "Unsupported Windows architecture: $architecture" }
        }
        # SHA-256 values published at https://www.python.org/downloads/release/python-31410/
        $hashes = @{
            amd64 = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
            arm64 = 'bbe116bb1248820359cbf25127ac5c7794ea161869d83686cfbc9a45203ff836'
            win32 = '11a28e8c00a6d8f56b0a6164d52546133a9ed015a5b33e04536917e4fd6e306c'
        }
        $portableDirectory = Join-Path ([IO.Path]::GetTempPath()) ('egm-python-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $portableDirectory | Out-Null
        $archive = Join-Path $portableDirectory 'python.zip'
        $runtime = Join-Path $portableDirectory 'runtime'
        $url = "https://www.python.org/ftp/python/$version/python-$version-embed-$platform.zip"
        Write-Host "[EGM] No compatible Python found. Downloading portable Python $version ($platform) from python.org..."
        [Net.ServicePointManager]::SecurityProtocol = $previousSecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive
        Write-Host '[EGM] Verifying portable Python archive (SHA-256)...'
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $hashes[$platform]) {
            throw 'Portable Python archive SHA-256 verification failed.'
        }
        Write-Host '[EGM] SHA-256 verified. Extracting portable Python...'
        Expand-Archive -LiteralPath $archive -DestinationPath $runtime
        $python = Join-Path $runtime 'python.exe'
        Write-Host "[EGM] Portable Python ready: $python"
        # The embeddable distribution ignores PYTHONPATH; add only this repository explicitly.
        $moduleArguments = @(
            '-c',
            "import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('egm_copilot', run_name='__main__')",
            $PSScriptRoot
        )
    }
    $env:PYTHONPATH = $PSScriptRoot
    if ($previousPythonPath) {
        $env:PYTHONPATH += [IO.Path]::PathSeparator + $previousPythonPath
    }
    Write-Host '[EGM] Installing EGM...'
    & $python @prefix @moduleArguments install @args
    $installerExit = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
    [Net.ServicePointManager]::SecurityProtocol = $previousSecurityProtocol
    if ($portableDirectory) {
        Write-Host '[EGM] Removing temporary portable Python files...'
        Remove-Item -LiteralPath $portableDirectory -Recurse -Force
    }
}
if ($installerExit -eq 0) {
    Write-Host '[EGM] Installation completed.'
} else {
    Write-Host "[EGM] Installation failed (exit code $installerExit)."
}
exit $installerExit
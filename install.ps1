$ErrorActionPreference = 'Stop'

$python = $null
$prefix = @()
if ($env:EGM_PYTHON) {
    $python = Get-Command $env:EGM_PYTHON -ErrorAction SilentlyContinue
} else {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($python) {
        $prefix = @('-3')
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            $python = Get-Command python3 -ErrorAction SilentlyContinue
        }
    }
}

if (-not $python) {
    throw 'Python 3.10+ is required. Install it or set EGM_PYTHON.'
}

& $python.Source @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) {
    throw 'Python 3.10+ is required.'
}

$previousPythonPath = $env:PYTHONPATH
$installerExit = 1
try {
    $env:PYTHONPATH = $PSScriptRoot
    if ($previousPythonPath) {
        $env:PYTHONPATH += [IO.Path]::PathSeparator + $previousPythonPath
    }
    & $python.Source @prefix -m egm_copilot install @args
    $installerExit = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
exit $installerExit
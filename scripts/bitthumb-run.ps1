$ErrorActionPreference = "Stop"

function Get-PythonSpec {
    $candidates = @(
        @('py', '-3.12'),
        @('py', '-3.11'),
        @('py', '-3'),
        @('python3'),
        @('python')
    )

    foreach ($candidate in $candidates) {
        $command = $candidate[0]
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            continue
        }

        $args = @()
        if ($candidate.Length -gt 1) {
            $args = $candidate[1..($candidate.Length - 1)]
        }

        try {
            & $command @args '-c' 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null > $null
        }
        catch {
            continue
        }

        if ($LASTEXITCODE -eq 0) {
            return @{ Command = $command; Args = $args }
        }
    }

    return $null
}

$pythonSpec = Get-PythonSpec
if (-not $pythonSpec) {
    throw "Python 3.11 이상이 필요합니다. Microsoft Store, winget 또는 https://www.python.org/downloads/ 에서 설치 후 다시 시도하세요."
}

function Invoke-SelectedPython {
    param([string[]]$Arguments)
    & $pythonSpec.Command @($pythonSpec.Args + $Arguments)
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv-bitthumb"

if (Test-Path $venvPath) {
    $existingPython = Join-Path $venvPath "Scripts/python.exe"
    $needsRebuild = $false
    if (-not (Test-Path $existingPython)) {
        $needsRebuild = $true
    }
    else {
        & $existingPython '-c' 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -ne 0) {
            $needsRebuild = $true
        }
    }

    if ($needsRebuild) {
        Remove-Item -Recurse -Force $venvPath
    }
}

if (-not (Test-Path $venvPath)) {
    Invoke-SelectedPython @('-m', 'venv', $venvPath)
}

$venvPython = Join-Path $venvPath "Scripts/python.exe"

& $venvPython -m pip install --upgrade --disable-pip-version-check pip setuptools wheel > $null
& $venvPython -m pip install --disable-pip-version-check $projectRoot

$cliPath = Join-Path $venvPath "Scripts/bitthumb-cli.exe"

if (-not (Test-Path $cliPath)) {
    throw "bitthumb-cli가 설치되지 않았습니다."
}

& $cliPath @args

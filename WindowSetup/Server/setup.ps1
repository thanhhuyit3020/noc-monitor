param([switch]$LanAccess)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path
Set-Location $repoRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher (py.exe) not found. Install Python 3.13 x64 and run this command again."
}

& py -3.13 --version
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.13 x64 is required. Install it, then run this command again."
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $python) {
    $pythonVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne "3.13") {
        throw "Existing .venv must use Python 3.13. Replace it and run setup.ps1 again."
    }
} else {
    & py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv." }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }

& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Could not install requirements.txt." }

& $python -m noc.auth_cli bootstrap
if ($LASTEXITCODE -ne 0) { throw "Could not configure the Global Admin account." }

$installScript = Join-Path $PSScriptRoot "install_autostart.ps1"
if ($LanAccess) { & $installScript -LanAccess }
else { & $installScript }

param([switch]$LanAccess)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Python environment not found. Run setup.ps1 first." }

$dataDir = Join-Path $repoRoot "data"
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$env:NOC_HOST = if ($LanAccess) { "0.0.0.0" } else { "127.0.0.1" }
$env:NOC_PORT = "6969"

$server = Start-Process -FilePath $python -ArgumentList "run_server.py" -WorkingDirectory $repoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput (Join-Path $dataDir "noc-server.out.log") -RedirectStandardError (Join-Path $dataDir "noc-server.err.log")
if ($server.ExitCode -ne 0) { throw "NOC Monitor exited with code $($server.ExitCode). Check data\noc-server.err.log." }
exit $server.ExitCode

$ErrorActionPreference = "Stop"

$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot "agent.json") -Raw | ConvertFrom-Json
$env:NOC_PUSH_URL = $config.push_url
$env:NOC_AGENT_TOKEN = $config.token
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python (Join-Path $PSScriptRoot "run_agent.py") --interval 15
exit $LASTEXITCODE

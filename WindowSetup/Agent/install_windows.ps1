$ErrorActionPreference = "Stop"

$admin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell window."
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.10+ for all users first." }
$pythonVersion = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or [version]$pythonVersion -lt [version]"3.10") { throw "Python 3.10+ is required." }

$pushUrl = Read-Host "NOC agent push URL (for example http://192.168.1.10:6969/api/agent/push)"
$uri = $null
if (-not [Uri]::TryCreate($pushUrl, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -notin @("http", "https") -or $uri.AbsolutePath.TrimEnd("/") -ne "/api/agent/push") {
    throw "Enter an HTTP(S) URL ending in /api/agent/push."
}
$secureToken = Read-Host "Agent token from the NOC host configuration" -AsSecureString
$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr) }
if ([string]::IsNullOrWhiteSpace($token)) { throw "Agent token cannot be empty." }

$installDir = Join-Path $env:ProgramData "NOC-Agent"
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
$agentSource = $PSScriptRoot
if (-not (Test-Path (Join-Path $agentSource "run_agent.py"))) {
    $agentSource = (Resolve-Path (Join-Path $PSScriptRoot "..\..\agent")).Path
}
$runnerSource = Join-Path $PSScriptRoot "start_agent.ps1"
if (-not (Test-Path $runnerSource)) {
    $runnerSource = Join-Path $agentSource "start_agent.ps1"
}
foreach ($file in @("run_agent.py", "requirements.txt")) {
    $source = Join-Path $agentSource $file
    if (-not (Test-Path $source)) { throw "Agent source file not found: $source" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $installDir $file) -Force
}
if (-not (Test-Path $runnerSource)) { throw "Agent runner not found: $runnerSource" }
Copy-Item -LiteralPath $runnerSource -Destination (Join-Path $installDir "start_agent.ps1") -Force
& icacls.exe $installDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict permissions on $installDir." }

$configPath = Join-Path $installDir "agent.json"
@{ push_url = $uri.AbsoluteUri; token = $token } | ConvertTo-Json -Compress | Set-Content -LiteralPath $configPath -Encoding UTF8
$token = $null
& py -3 -m venv (Join-Path $installDir ".venv")
if ($LASTEXITCODE -ne 0) { throw "Could not create the agent virtual environment." }
$python = Join-Path $installDir ".venv\Scripts\python.exe"
& $python -m pip install -r (Join-Path $installDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install agent requirements." }

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$env:NOC_PUSH_URL = $config.push_url
$env:NOC_AGENT_TOKEN = $config.token
try { & $python (Join-Path $installDir "run_agent.py") --once }
finally { Remove-Item Env:NOC_PUSH_URL, Env:NOC_AGENT_TOKEN -ErrorAction SilentlyContinue }
if ($LASTEXITCODE -ne 0) { throw "Agent test push failed; check the NOC URL, token, and firewall." }

$taskName = "NOC Monitor Agent"
$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$runner = Join-Path $installDir "start_agent.ps1"
$action = New-ScheduledTaskAction -Execute $powershell -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" -WorkingDirectory $installDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Pushes host metrics to NOC Monitor." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "NOC Agent installed as a startup task. Check host status on the NOC dashboard."

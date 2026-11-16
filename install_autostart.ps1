param([switch]$LanAccess)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "NOC Monitor"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$ownedPids = @()
foreach ($listenerPid in (Get-NetTCPConnection -LocalPort 6969 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid" -ErrorAction SilentlyContinue
    if ($process.ExecutablePath -ieq $python -and $process.CommandLine -match "run_server\.py") {
        $ownedPids += $listenerPid
    } else {
        throw "TCP port 6969 is already used by PID $listenerPid. Stop that process before installing NOC Monitor."
    }
}
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask -and $existingTask.State -eq "Running") {
    Stop-ScheduledTask -TaskName $taskName
}
foreach ($listenerPid in $ownedPids) { Stop-Process -Id $listenerPid -Force -ErrorAction SilentlyContinue }
for ($attempt = 0; $attempt -lt 15 -and (Get-NetTCPConnection -LocalPort 6969 -State Listen -ErrorAction SilentlyContinue); $attempt++) {
    Start-Sleep -Seconds 1
}
if (Get-NetTCPConnection -LocalPort 6969 -State Listen -ErrorAction SilentlyContinue) {
    throw "TCP port 6969 did not become available. Stop the old server and retry."
}
$startScript = Join-Path $repoRoot "start_server.ps1"
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$lanArgument = if ($LanAccess) { " -LanAccess" } else { "" }
$arguments = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`"$lanArgument"
$action = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") -Argument $arguments -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Runs NOC Monitor on port 6969 after sign-in." -Force -ErrorAction Stop | Out-Null

Start-ScheduledTask -TaskName $taskName

$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:6969/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $healthy) { throw "NOC Monitor did not become healthy. Check data\noc-server.err.log." }

Write-Host "NOC Monitor is running at http://127.0.0.1:6969/"
if ($LanAccess) { Write-Host "LAN access is enabled. Restrict inbound TCP 6969 to trusted networks in Windows Firewall." }
Write-Host "First run: .\.venv\Scripts\python.exe -m noc.auth_cli bootstrap"
Write-Host "Sign-in: http://127.0.0.1:6969/login"
Write-Host "It will start at sign-in. Task: $taskName"

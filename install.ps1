# Install the arrangement watcher as a Windows scheduled task that starts at
# login, runs hidden (no console window), and has no time limit.
#
#   powershell -ExecutionPolicy Bypass -File install.ps1 [output_file]
#
# Default output file: %USERPROFILE%\ProPresenter Stage Text\arrangement.txt
param(
    [string]$OutFile = (Join-Path $env:USERPROFILE "ProPresenter Stage Text\arrangement.txt")
)
$ErrorActionPreference = "Stop"

$TaskName = "ProPresenter Stage Arrangement"
$Script = Join-Path $PSScriptRoot "arrangement_watch.py"

# pythonw.exe runs Python without a console window. Fall back to the py launcher.
$Exe = $null
$ExeArgs = @()
$pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
$pyw = Get-Command pyw.exe -ErrorAction SilentlyContinue
if ($pythonw) {
    $Exe = $pythonw.Source
} elseif ($pyw) {
    $Exe = $pyw.Source
    $ExeArgs = @("-3")
} else {
    Write-Error "Python not found. Install it from https://www.python.org/downloads/ (check 'Add python.exe to PATH'), then run this again."
}

New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null
if (-not (Test-Path $OutFile)) { New-Item -ItemType File -Path $OutFile | Out-Null }

$argLine = (($ExeArgs + @("`"$Script`"", "`"$OutFile`"")) -join " ")
$action = New-ScheduledTaskAction -Execute $Exe -Argument $argLine -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Windows stops scheduled tasks after 3 days by default; zero means no limit.
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Writes the live ProPresenter arrangement to $OutFile" | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "Installed. Writing to: $OutFile"
Write-Host "Log: $(Join-Path (Split-Path $OutFile) 'arrangement-watch.log')"

# Stop the arrangement watcher and remove its scheduled task.
$TaskName = "ProPresenter Stage Arrangement"
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Uninstalled."

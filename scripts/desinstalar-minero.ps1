# Quita la tarea TNB-Minero del Programador de tareas.
#   powershell -ExecutionPolicy Bypass -File scripts\desinstalar-minero.ps1

$ErrorActionPreference = "Stop"
$TaskName = "TNB-Minero"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "No había tarea '$TaskName'."
    exit 0
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Tarea '$TaskName' eliminada."

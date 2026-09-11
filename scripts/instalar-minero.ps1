# Instala el minero 24/7 en el Programador de tareas de Windows.
# El bucle python mine_loop.py sobrevive un reinicio; el sleep del PC
# SIGUE pausando el SO (el task no despierta el equipo).
#
#   powershell -ExecutionPolicy Bypass -File scripts\instalar-minero.ps1
#
# Quitar: scripts\desinstalar-minero.ps1

$ErrorActionPreference = "Stop"
$Fw = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Fw ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
$TaskName = "TNB-Minero"
$Arg = "mine_loop.py"
Write-Host "Framework: $Fw"
Write-Host "Python:    $Python"

$action = New-ScheduledTaskAction -Execute $Python -Argument $Arg -WorkingDirectory $Fw
$logon = New-ScheduledTaskTrigger -AtLogOn
$repeat = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon, $repeat) `
    -Settings $settings -Description "The NewsBreakers mine_loop.py (RSS/API cada ~30 min). El sleep del PC pausa la minería; el task sobrevive al reinicio." | Out-Null

Write-Host "Tarea '$TaskName' registrada."
Write-Host "  - Al iniciar sesión"
Write-Host "  - Repetición cada 30 minutos (si el equipo está despierto)"
Write-Host "Importante: suspender/hibernar Windows detiene el minero hasta que el PC despierte."
Write-Host "Comprobar: Get-ScheduledTask -TaskName $TaskName"

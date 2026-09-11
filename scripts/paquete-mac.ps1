# Empaqueta tnb.db + miniaturas para AirDrop / USB al Mac.
# Uso (API y minero parados un momento):
#   powershell -ExecutionPolicy Bypass -File scripts\paquete-mac.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\paquete-mac.ps1 -Dest $env:USERPROFILE\Desktop\tnb-datos-mac.zip

param(
    [string]$Dest = ""
)

$ErrorActionPreference = "Stop"
$Fw = Split-Path -Parent $PSScriptRoot
$Db = Join-Path $Fw "data\processed\tnb.db"
$Imgs = Join-Path $Fw "storage\images"
if (-not $Dest) {
    $Dest = Join-Path $env:USERPROFILE "Desktop\tnb-datos-mac.zip"
}

if (-not (Test-Path $Db)) {
    Write-Error "No existe $Db — no hay corpus que enviar."
}

$stage = Join-Path $env:TEMP ("tnb-paquete-mac-" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Force -Path (Join-Path $stage "data\processed"), (Join-Path $stage "storage\images") | Out-Null
Copy-Item $Db (Join-Path $stage "data\processed\tnb.db")
if (Test-Path $Imgs) {
    Copy-Item (Join-Path $Imgs "*") (Join-Path $stage "storage\images") -Recurse -ErrorAction SilentlyContinue
}

if (Test-Path $Dest) { Remove-Item $Dest -Force }
Compress-Archive -Path (Join-Path $stage "data"), (Join-Path $stage "storage") -DestinationPath $Dest -Force
Remove-Item $stage -Recurse -Force

$mb = [math]::Round((Get-Item $Dest).Length / 1MB, 2)
Write-Host "Listo: $Dest ($mb MB)"
Write-Host "AirDrop / USB al Mac. En el clone:"
Write-Host "  mac/detener.command"
Write-Host "  unzip y deja tnb.db en data/processed/"
Write-Host "Luego git pull (el repo ya trae el snapshot) o Instalar-y-abrir.command"

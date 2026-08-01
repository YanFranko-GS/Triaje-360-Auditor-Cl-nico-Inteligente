# Alternativa: powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\stop_demo.ps1"
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$pidFile = Join-Path $PSScriptRoot ".demo\streamlit.pid"
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "No hay un proceso de demostracion registrado."
    exit 0
}
$demoPid = [int](Get-Content -Raw -LiteralPath $pidFile)
$process = Get-Process -Id $demoPid -ErrorAction SilentlyContinue
if ($process) {
    $appScript = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "app.py")).Path
    $details = Get-CimInstance Win32_Process -Filter "ProcessId=$demoPid" -ErrorAction SilentlyContinue
    if (-not $details -or $details.CommandLine -notlike "*$appScript*" -or $details.CommandLine -notlike "*streamlit*") {
        throw "El PID registrado no corresponde al Streamlit de este proyecto; no se detuvo ningun proceso."
    }
    Stop-Process -Id $demoPid
    Wait-Process -Id $demoPid -ErrorAction SilentlyContinue
    Write-Host "Proceso de demostracion $demoPid detenido."
} else {
    Write-Host "El proceso registrado ya no esta activo."
}
Remove-Item -LiteralPath $pidFile -Force

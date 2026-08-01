# Alternativa: powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_windows.ps1"
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) { throw "No existe .venv. Ejecute primero .\setup_windows.ps1" }
if (-not (Test-Path -LiteralPath ".env")) { Copy-Item -LiteralPath ".env.example" -Destination ".env" }

$modelReady = $false
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    try {
        $models = (& ollama list) -join "`n"
        $modelReady = $models -match [regex]::Escape("gemma4:e2b")
    } catch { Write-Warning "Ollama no respondio; se activara el respaldo determinista." }
}
if (-not $modelReady) { Write-Warning "gemma4:e2b no esta disponible. Para instalarlo: ollama pull gemma4:e2b" }

$demoDir = Join-Path $PSScriptRoot ".demo"
New-Item -ItemType Directory -Path $demoDir -Force | Out-Null
$pidFile = Join-Path $demoDir "streamlit.pid"
$stdoutLog = Join-Path $demoDir "streamlit.stdout.log"
$stderrLog = Join-Path $demoDir "streamlit.stderr.log"
$appScript = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "app.py")).Path
if (Test-Path -LiteralPath $pidFile) {
    $existingPid = [int](Get-Content -Raw -LiteralPath $pidFile)
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        Write-Host "TRIaje 360 ya se esta ejecutando en http://localhost:8501 (PID $existingPid)"
        exit 0
    }
}
$process = Start-Process -FilePath $venvPython -ArgumentList @("-m","streamlit","run",$appScript,"--server.address","127.0.0.1","--server.port","8501","--server.headless","true") -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -WindowStyle Hidden -PassThru
$serverPid = $null
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $connection = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($connection) {
        $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.CommandLine -like "*$appScript*" -and $candidate.CommandLine -like "*streamlit*") {
            $serverPid = [int]$candidate.ProcessId
            break
        }
    }
    Start-Sleep -Milliseconds 500
}
if (-not $serverPid) { throw "Streamlit no inició con un PID validable. Revise $stderrLog" }
Set-Content -LiteralPath $pidFile -Value $serverPid
Write-Host "TRIaje 360 iniciado en http://localhost:8501 (PID $serverPid)"
Write-Host "Use .\stop_demo.ps1 para detener solamente este proceso."

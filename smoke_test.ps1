# Alternativa: powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\smoke_test.ps1"
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python no esta disponible." }
if (-not (Test-Path -LiteralPath $venvPython)) { throw "Falta .venv; ejecute setup_windows.ps1." }
if (-not (Test-Path -LiteralPath ".env")) { throw "Falta .env." }
& $venvPython -c "import streamlit, requests, pydantic, dotenv; from database import initialize; initialize(); print('DEPENDENCIAS Y SQLITE: OK')"
if ($LASTEXITCODE -ne 0) { throw "Fallo la comprobacion de dependencias y SQLite." }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Ollama no esta instalado." }
$tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
$names = @($tags.models | ForEach-Object { $_.name })
Write-Host "MODELOS OLLAMA: $($names -join ', ')"
if ($names -notcontains "gemma4:e2b") { throw "Falta gemma4:e2b. Ejecute: ollama pull gemma4:e2b" }

$requestBody = @{
    model="gemma4:e2b"
    stream=$false
    think=$false
    keep_alive="2m"
    prompt="Responde unicamente: GEMMA 4 OPERATIVO"
    options=@{temperature=0; num_predict=32; num_ctx=4096; num_gpu=0}
} | ConvertTo-Json -Depth 5
$inference = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -ContentType "application/json" -Body $requestBody -TimeoutSec 180
if ($inference.model -ne "gemma4:e2b") { throw "Ollama identifico un modelo diferente: $($inference.model)" }
if (-not $inference.response) { throw "La inferencia de Gemma devolvio una respuesta vacia." }
Write-Host "GEMMA REAL: OK (model=gemma4:e2b, response=$($inference.response.Trim()))"

& $venvPython -c "from services.ollama_client import fallback_analysis; assert fallback_analysis('me falta el aire').protocol_id == 'respiratory_alert'; print('RESPALDO DETERMINISTA: OK')"
if ($LASTEXITCODE -ne 0) { throw "Fallo la comprobacion del respaldo determinista." }
& $venvPython -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Pytest fallo; el smoke test no puede continuar como aprobado." }

& (Join-Path $PSScriptRoot "run_windows.ps1")
$responded = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8501/_stcore/health" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200 -and $response.Content -match "ok") { $responded = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $responded) { throw "Streamlit no respondio por HTTP. Revise .demo\streamlit.stderr.log" }
Write-Host "STREAMLIT HTTP: OK (200) - http://localhost:8501"
Write-Host "SMOKE TEST COMPLETADO"

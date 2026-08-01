# Alternativa: powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\setup_windows.ps1"
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$launcher = Get-Command py -ErrorAction SilentlyContinue
$pythonCommand = $null
$pythonArgs = @()
$explicitPython = $env:TRIAJE_PYTHON
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if ($explicitPython -and (Test-Path -LiteralPath $explicitPython)) {
    $pythonCommand = Get-Item -LiteralPath $explicitPython
} elseif (Test-Path -LiteralPath $bundledPython) {
    $pythonCommand = Get-Item -LiteralPath $bundledPython
    Write-Host "Usando Python compatible detectado en el runtime local de Codex."
} elseif ($launcher) {
    $availableVersions = (& $launcher.Source -0p) -join "`n"
    if ($availableVersions -match "-V:3\.12") {
        $pythonCommand = $launcher
        $pythonArgs = @("-3.12")
    } elseif ($availableVersions -match "-V:3\.11") {
        $pythonCommand = $launcher
        $pythonArgs = @("-3.11")
    }
    if (-not $pythonCommand) {
        $pythonCommand = $launcher
        Write-Warning "Python 3.11/3.12 no esta disponible; se usara la version predeterminada del launcher."
    }
} elseif (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) { throw "Python no esta instalado o no esta en PATH." }
$pythonExecutable = $pythonCommand.Source
if (-not $pythonExecutable) { $pythonExecutable = $pythonCommand.FullName }

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & $pythonExecutable @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
}
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Creado .env desde .env.example"
}

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warning "Ollama no esta instalado. La aplicacion funcionara con el respaldo determinista."
} else {
    try {
        $models = (& ollama list) -join "`n"
        if ($models -notmatch [regex]::Escape("gemma4:e2b")) {
            Write-Host "Descargando exclusivamente gemma4:e2b mediante Ollama..."
            & ollama pull gemma4:e2b
            if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar gemma4:e2b." }
            $models = (& ollama list) -join "`n"
            if ($models -notmatch [regex]::Escape("gemma4:e2b")) { throw "La descarga termino pero gemma4:e2b no aparece en ollama list." }
            Write-Host "Modelo gemma4:e2b instalado."
        } else {
            Write-Host "Modelo gemma4:e2b detectado."
        }
    } catch {
        Write-Warning "Ollama esta instalado pero no respondio: $($_.Exception.Message)"
    }
}

& $venvPython -c "from database import initialize; initialize(); print('SQLite inicializado')"
& $venvPython -m pytest -q
Write-Host "Instalacion terminada. Ejecute .\run_windows.ps1"

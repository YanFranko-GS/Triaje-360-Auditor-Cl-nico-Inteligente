# KutanLab: TRIaje 360 — Auditor Clínico Inteligente

![Estado](https://img.shields.io/badge/estado-prototipo%20educativo-0284c7)

> Captura principal: pendiente de incorporar desde una ejecución local validada, sin datos personales.

Prototipo web funcional para **Build with Gemma — GDG Lima**. Apoya la admisión ficticia y la auditoría concurrente de completitud documental. Gemma 4 E2B se ejecuta localmente mediante Ollama, estructura el relato y propone uno de dos protocolos demostrativos autorizados; Python valida la salida, genera el checklist y controla el cierre. La integración real fue validada el 31 de julio de 2026.

> Uso exclusivamente educativo. No utiliza información real, no diagnostica, no prescribe, no recomienda medicamentos, no determina negligencia, no sustituye el juicio profesional ni reemplaza protocolos institucionales.

## Problema y solución

Los registros incompletos dificultan una revisión clínica concurrente. TRIaje 360 combina un resumen estructurado con reglas cerradas para que las acciones documentales pendientes sean visibles y el cierre quede bloqueado hasta registrarlas. Toda decisión final sigue perteneciendo al profesional autorizado.

## Arquitectura

```text
Navegador → Streamlit → engine.py
                         ├─ Ollama REST → gemma4:e2b → Pydantic
                         ├─ respaldo determinista
                         ├─ catálogo cerrado de protocolos
                         └─ SQLite (consulta, respuesta, checklist, acciones y auditoría)
```

La presentación está separada en `ui/components.py`, `ui/theme.py` y `ui/styles.css`. El encabezado, las tarjetas de estado, las etapas y los estados clínicos son componentes locales sin JavaScript ni recursos visuales externos. `app.py` conserva la orquestación del flujo.

Gemma nunca controla el cierre. `database.attempt_close` consulta el checklist persistido y registra cada intento. Consulte [ARCHITECTURE.md](ARCHITECTURE.md).

## Papel de Gemma 4

Gemma recibe únicamente el relato y antecedentes ficticios, y devuelve JSON con `summary`, `risk_flags`, `protocol_id`, `reason` y `disclaimer`. La salida se acepta solo si Ollama responde, identifica el modelo configurado y Pydantic valida todos los campos. En caso contrario se registra `model_used=false` y se activa el respaldo.

La prueba real del caso demostrativo produjo `model_used=true`, `model_name=gemma4:e2b`, `protocol_id=respiratory_alert`, banderas para revisión y prioridad naranja. En la MX330 de 2 GB, la carga CUDA automática falló; las solicitudes del proyecto fuerzan CPU sin cambiar la configuración global de Ollama. Consulte [docs/gemma4_real_validation.md](docs/gemma4_real_validation.md).

## Ejecución con doble clic

Requisitos: Windows 11, Python 3.11/3.12 y Ollama. No requiere permisos de administrador ni abrir PowerShell.

1. Descomprima el proyecto.
2. Haga doble clic en `INICIAR_TRIAJE360.bat`.
3. Elija **Instalar o reparar** la primera vez.
4. Elija **Probar toda la instalación**.
5. Elija **Iniciar aplicación**.
6. Abra [http://localhost:8501](http://localhost:8501) si el navegador no se abre automáticamente.
7. Elija **Detener aplicación** al terminar.

Los BAT usan rutas relativas a su propia ubicación, ejecutan `.venv\Scripts\python.exe` directamente y escriben evidencia en `logs`. No activan visualmente el entorno virtual y no cambian ninguna política del sistema.

Si Windows muestra «la ejecución de scripts está deshabilitada en este sistema», use los BAT: no dependen de ejecutar manualmente un `.ps1`. Como alternativa de emergencia, el bypass permitido se limita al proceso actual:

```bat
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\smoke_test.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_windows.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\stop_demo.ps1"
```

No use `Set-ExecutionPolicy`; no es necesario para este proyecto.

## Configuración

`00_INSTALAR_O_REPARAR.bat` copia `.env.example` a `.env` únicamente si falta. Variables:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_PREDICT=320
OLLAMA_NUM_GPU=0
OLLAMA_KEEP_ALIVE=2m
DATABASE_PATH=data/triaje360.db
```

`.env` y la base local están excluidos de Git.

## Caso de demostración

- DNI: `76543210`.
- Paciente ficticia: mujer, 58 años; hipertensión, diabetes tipo 2, alergia a AINEs y última visita simulada.
- Relato: `Tengo dolor en la espalda al respirar y me falta el aire desde ayer.`
- Resultado esperado: `respiratory_alert`, prioridad documental naranja, banderas, cuatro acciones obligatorias y cierre bloqueado hasta completarlas.

El guion está en [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Pruebas y smoke test

```bat
01_PROBAR_TODO.bat
.venv\Scripts\python.exe -m pytest -q
```

El smoke test comprueba Python, entorno, dependencias, `.env`, SQLite, Ollama, modelos, inferencia breve cuando Gemma está instalado, respaldo, pytest y `/_stcore/health` de Streamlit.

La suite incluye una prueba de integración real. Solo se omite cuando Ollama o `gemma4:e2b` no están disponibles; con la instalación validada debe ejecutarse y aprobar.

## Modo de respaldo

Se activa ante desconexión, modelo ausente, timeout, respuesta vacía, JSON inválido, protocolo desconocido o error HTTP. Usa términos respiratorios cerrados para elegir `respiratory_alert`; de lo contrario usa `general_review`. La interfaz y SQLite conservan la causa exacta y nunca afirman que Gemma participó.

## Privacidad, seguridad y limitaciones

No ingrese datos personales reales. El MVP no incorpora autenticación, cifrado, integración con historia clínica, voz real ni protocolos institucionales. SQLite es local. Consulte [docs/safety_and_limitations.md](docs/safety_and_limitations.md).

## Estructura

```text
app.py                 Interfaz Streamlit
engine.py              Orquestación Gemma/respaldo
config.py              Configuración .env
schemas.py             Validación Pydantic
database.py            SQLite y bloqueo determinista
protocols.py           Catálogo y reglas
services/ollama_client.py
data/protocols.json
tests/                  Pruebas automatizadas
docs/                   Documentación técnica y seguridad
scripts/windows_launcher.py  Control Windows, health y PID seguro
00_*.bat a 03_*.bat     Instalación, prueba, inicio y detención
INICIAR_TRIAJE360.bat   Menú recomendado para doble clic
*_windows.ps1           Alternativas con Bypass solo por proceso
```

## Equipo

KutanLab: Daniel Ríos, Yan Franco Gonzales Segura y Jhon Gesell Villanueva Portella.

## Flujo Git para colaboradores

```bash
git clone https://github.com/YanFranko-GS/Triaje-360-Auditor-Cl-nico-Inteligente.git
cd Triaje-360-Auditor-Cl-nico-Inteligente
git switch develop
git pull --ff-only origin develop
git switch -c feature/nombre-descriptivo
# realizar cambios y pruebas
git add <archivos>
git commit -m "feat: descripción breve"
git push -u origin feature/nombre-descriptivo
```

Abra un Pull Request hacia `develop`. No haga push directo ni fusione sin revisión del responsable del repositorio. Consulte [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

Código del prototipo bajo Apache License 2.0. Consulte [LICENSE](LICENSE).

# Rebuilding and improving TRIaje 360 with an AI agent

[English](#english) | [Español](#español)

This guide is for humans supervising Codex or another coding agent. `AGENTS.md` is the canonical operating contract for the agent; this document explains how to stage the work and verify its evidence.

## English

### 1. Open the repository

Clone the repository, open `<PROJECT_ROOT>` as the agent's workspace, and make sure the agent can run PowerShell, Python 3.12, Git, and localhost requests. Install and start Ollama yourself if it is not already available. Do not give the agent real clinical data or production credentials.

### 2. Initial prompt

> Read AGENTS.md and README.md. Inspect the repository, create an isolated Python environment, verify Ollama and Gemma 4, initialize synthetic data, run the complete test suite and smoke test, start the application and report evidence before making improvements. Do not modify main or develop directly.

### 3. Recommended stages

1. **Repository audit:** status, branches, remotes, recent commits, dependency files, ignored artifacts.
2. **Architecture discovery:** entry point, role navigation, data services, AI/ASR adapters, schemas, RAG, tests.
3. **Isolated setup:** create `.venv`, install pinned requirements, copy `.env.example` to untracked `.env`.
4. **Synthetic initialization:** run account and data seeds twice to confirm idempotency.
5. **AI validation:** verify exact `gemma4:e2b` identity, perform real non-empty inference, and test deterministic fallback.
6. **Automated validation:** run full pytest and `01_PROBAR_TODO.bat`.
7. **Visual validation:** start Streamlit, check health, and exercise patient, triage, physician, supervisor, and admin roles.
8. **Change design:** state assumptions, safety impact, tests, and acceptance criteria before implementation.
9. **Implementation:** make focused changes without weakening confirmation, provenance, permissions, or fallback.
10. **Release evidence:** rerun tests, smoke, health, visual checks, secret scan, and Git diff checks.

### 4. Files the agent must read

- `AGENTS.md` and `README.md`
- `docs/architecture-overview.md`
- `docs/safety_and_limitations.md`
- `docs/source_governance.md` and `docs/source_register.csv` for RAG changes
- `app.py`, `ui/navigation.py`, and the affected UI page
- affected service modules and Pydantic schemas
- tests covering the requested behavior
- `.env.example`, `requirements*.txt`, and Windows launchers for setup changes

### 5. How to detect invented results

Ask for command, exit code, test count, duration, and a short output excerpt. Independently run:

```powershell
git status --short
.\.venv\Scripts\python.exe -m pytest -q
.\01_PROBAR_TODO.bat
Invoke-WebRequest http://127.0.0.1:8501/_stcore/health -UseBasicParsing
git diff --check
```

Check that the reported model name is exactly `gemma4:e2b`, not merely a configured string; the smoke output must show a real response. Review `git diff --cached` and `git ls-files` to ensure no `.env`, databases, logs, WAV files, models, or personal paths were added. Open screenshots and verify they show a functioning real UI with synthetic data and no visible password. A badge, mockup, or previous log is not execution evidence.

### 6. Safe improvement prompts

Use bounded prompts with observable acceptance criteria, for example:

> Improve the missing-field follow-up without changing clinical priority rules. Preserve one-question-at-a-time behavior, patient confirmation, deterministic fallback, and audit events. Add tests for ordinary and immediate-review narratives, run the full suite, and report the exact evidence.

For clinical logic, request domain review as a separate requirement; never ask the agent to invent thresholds or imply regulatory approval.

## Español

### 1. Abrir el repositorio

Clona el repositorio, abre `<PROJECT_ROOT>` como espacio del agente y confirma que puede ejecutar PowerShell, Python 3.12, Git y solicitudes a localhost. Instala e inicia Ollama por separado si hace falta. No entregues información clínica real ni credenciales productivas.

### 2. Prompt inicial

> Lee AGENTS.md y README.md. Inspecciona el repositorio, crea un entorno Python aislado, verifica Ollama y Gemma 4, inicializa datos sintéticos, ejecuta la suite completa y el smoke test, inicia la aplicación y reporta evidencia antes de realizar mejoras. No modifiques main ni develop directamente.

### 3. Etapas recomendadas

1. **Auditoría:** estado, ramas, remotos, commits, dependencias y artefactos ignorados.
2. **Arquitectura:** entrada, roles, datos, adaptadores IA/ASR, esquemas, RAG y pruebas.
3. **Entorno aislado:** `.venv`, requisitos fijados y `.env` local no rastreado.
4. **Inicialización sintética:** ejecutar dos veces las semillas para comprobar idempotencia.
5. **Validación IA:** confirmar identidad exacta, inferencia real no vacía y respaldo determinista.
6. **Automatización:** ejecutar pytest completo y `01_PROBAR_TODO.bat`.
7. **Validación visual:** iniciar Streamlit, comprobar salud y recorrer todos los roles.
8. **Diseño del cambio:** declarar supuestos, impacto de seguridad, pruebas y aceptación.
9. **Implementación:** no debilitar confirmación, procedencia, permisos ni respaldo.
10. **Evidencia final:** repetir pruebas, smoke, HTTP, visual, secretos y diff.

### 4. Archivos que debe leer

- `AGENTS.md`, `README.md` y `docs/architecture-overview.md`
- `docs/safety_and_limitations.md`
- `docs/source_governance.md` y `docs/source_register.csv` si cambia RAG
- `app.py`, `ui/navigation.py` y la vista afectada
- servicios, esquemas Pydantic y pruebas relacionadas
- `.env.example`, `requirements*.txt` y lanzadores si cambia instalación

### 5. Cómo comprobar que no inventó resultados

Exige comando, código de salida, cantidad de pruebas, duración y fragmento de salida. Ejecuta tú mismo los comandos de verificación del apartado inglés. Comprueba que Gemma fue identificado por Ollama, que HTTP devuelve 200, que las capturas son reales y que Git no rastrea `.env`, bases, logs, audios, modelos ni rutas personales. Un README o un badge no demuestra ejecución.

### 6. Supervisión clínica

Toda modificación de lógica clínica necesita una fuente aplicable, configuración versionada, pruebas y validación profesional. El agente puede implementar y verificar software; no puede certificar seguridad clínica, crear una norma oficial ni reemplazar el criterio humano.

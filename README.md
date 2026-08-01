# TRIaje 360

## Plataforma inteligente de admisión, triaje y continuidad clínica

TRIaje 360 integra acceso por roles, registro dinámico de pacientes, admisión por voz o texto, conversación guiada, memoria clínica estructurada, triaje supervisado, historia longitudinal, analítica descriptiva y recuperación documental trazable. KutanLab desarrolla la experiencia y Gemma 4 actúa como modelo principal local mediante Ollama.

La plataforma organiza información y señala faltantes. No diagnostica, prescribe ni sustituye decisiones del personal sanitario.

## Capacidades

- Registro transaccional de pacientes sintéticos con validación de DNI, fecha, contacto, consentimiento y duplicados.
- Acceso diferenciado para pacientes, enfermería, médicos, supervisión y administración.
- Captura de voz con Vosk local o texto editable, sin persistencia de audio por defecto.
- Extracción Pydantic con `gemma4:e2b` y respaldo determinista explícito.
- `ClinicalCompletenessVerifier` con reglas y una segunda inferencia secuencial independiente.
- Memoria longitudinal relacional: alergias, medicamentos, atenciones, signos, diagnósticos y recetas registrados por profesionales.
- Sistema configurable de prioridad de cinco niveles basado en ESI para validación profesional.
- RAG con fuente, institución, año, población, URL, fragmento y limitaciones.
- Portal de historia del paciente, panel médico con analítica descriptiva y catálogo administrativo del esquema.
- Auditoría de accesos, cambios, decisiones, ejecuciones de modelos y recuperaciones RAG.

## Arquitectura

```text
Paciente / profesional
        │
        ▼
Streamlit ── autenticación y permisos
        │
        ├── Audio PCM 16 kHz ── Vosk local ── texto confirmado
        ├── Gemma 4 E2B ── extracción JSON Pydantic
        ├── reglas deterministas ── completitud y contradicciones
        ├── Gemma 4 E2B ── verificación independiente secuencial
        ├── RAG gobernado ── citas y limitaciones
        └── SQLite ── memoria longitudinal y auditoría
```

`PRIMARY_MODEL` y `REVIEW_MODEL` pueden configurarse por separado. Las solicitudes se realizan de forma secuencial para no mantener dos modelos grandes cargados a la vez. `OLLAMA_KEEP_ALIVE` conserva el modelo durante el recorrido.

## Inicio en Windows

Requisitos: Windows 11, Python 3.11/3.12 y Ollama con `gemma4:e2b`.

1. Ejecute `INICIAR_TRIAJE360.bat`.
2. Seleccione **Instalar o reparar**.
3. Seleccione **Probar toda la instalación**.
4. Seleccione **Iniciar aplicación**.
5. Abra [http://localhost:8501](http://localhost:8501).

Alternativa:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run_windows.ps1"
```

## Configuración

Copie `.env.example` a `.env` y ajuste solamente valores locales:

```dotenv
OLLAMA_MODEL=gemma4:e2b
PRIMARY_MODEL=gemma4:e2b
REVIEW_MODEL=gemma4:e2b
OLLAMA_KEEP_ALIVE=2m
STORE_DEMO_AUDIO=false
ASR_PROVIDER=vosk
ASR_MODEL_PATH=.demo/asr_models/vosk-model-small-es-0.42
```

No se versionan `.env`, bases SQLite, audios, modelos, logs, PID ni entornos virtuales.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\01_PROBAR_TODO.bat
```

El smoke test comprueba dependencias, migraciones, Gemma real, fallback, pruebas y salud HTTP de Streamlit.

## Documentación

- [Acceso y pruebas](docs/ACCESS_AND_TESTING.md)
- [Guía de conversación](docs/PATIENT_CONVERSATION_GUIDE.md)
- [Revisión del estándar peruano](docs/peru_triage_standard_review.md)
- [Esquema relacional](docs/database_schema.md)
- [SQL exportado](docs/database_schema.sql)
- [Relaciones Mermaid](docs/database_relationships.mmd)
- [Flujo de voz](docs/voice_workflow.md)
- [Seguridad y limitaciones](docs/safety_and_limitations.md)

## Límites regulatorios y operativos

TRIaje 360 no afirma aprobación de MINSA, integración con SIS o EsSalud, certificación como dispositivo médico ni aptitud para producción clínica real. Los nombres de aseguramiento son campos de registro, no integraciones externas. SQLite y las cuentas incluidas están orientados a validación local con información sintética; una implantación real requiere gobierno institucional, identidad robusta, cifrado, respaldo, interoperabilidad, evaluación clínica, ciberseguridad y autorización regulatoria.

Código bajo Apache License 2.0.

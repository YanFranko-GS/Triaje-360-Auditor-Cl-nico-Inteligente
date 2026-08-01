# Línea base antes de RAG y flujo multivista

Fecha de validación: 2026-08-01.

Rama de origen: `feature/integracion-gemma4-ui-clinica` (`bc51491c6645240b32e720d8b951d87be576e051`).

## Resultado verificable

- Python: 3.12.13 en `.venv` local.
- Pytest previo: `40 passed in 86.15s`.
- Pytest dentro del smoke test: `40 passed in 21.95s`.
- Ollama: 0.32.4 en `127.0.0.1:11434`.
- Modelo: `gemma4:e2b`, inferencia real en CPU (`num_gpu=0`).
- Precalentamiento: respuesta `GEMMA 4 OPERATIVO` en 4.03 s.
- Integración real: `1 passed in 20.57s`.
- Fallback determinista: operativo para relato respiratorio.
- SQLite: inicialización aprobada.
- Streamlit: `/_stcore/health` respondió HTTP 200.
- Ciclo de proceso: PID 7012 validado y detenido; el puerto 8501 quedó liberado.

La línea base no diagnostica, prescribe ni utiliza datos personales reales. Este documento sirve para comparar regresiones durante la iteración RAG.

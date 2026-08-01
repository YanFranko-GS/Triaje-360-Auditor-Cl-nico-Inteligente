# Informe de validación RAG

Fecha: 2026-08-01. Alcance: demostración local con datos ficticios.

## Resultado

- Registro de 9 fuentes revisadas; 2 aprobadas para fragmentos breves y 7 excluidas.
- 4 fragmentos ingeridos de forma idempotente con metadatos, población, URL y hash SHA-256.
- Recuperación FTS5 reproducible para el relato respiratorio: resultados de OMS Basic Emergency Care e IETSI/EsSalud.
- Filtro adulto excluye material pediátrico; fuentes no aprobadas, sustituidas o sin vigencia no ingresan.
- Prompt injection y contenido `script` se rechazan antes de almacenar.
- El validador impide citas que no hayan sido recuperadas en la misma ejecución.
- La interfaz diferencia evidencia recuperada, citas usadas y ausencia de evidencia; no presenta métricas como exactitud clínica.

## Pruebas automatizadas

`tests/test_rag_safety.py` cubre aprobación, vigencia, población, inyección, metadatos, citas y trazabilidad. `tests/test_clinical_workflow.py` verifica persistencia, cola, triaje, cierre independiente del LLM y reset acotado.

## Interpretación

El resultado demuestra trazabilidad técnica y degradación segura, no eficacia clínica. La relevancia, cobertura, actualización y utilidad asistencial requieren evaluación independiente con profesionales y documentos autorizados por cada institución.

## Evidencia de ejecución final

- Caso sintético `76543210` recorrido en navegador: `AWAITING_TRIAGE → AWAITING_PHYSICIAN → CLOSED`.
- Inferencia real: `model_used=true`, `model_name=gemma4:e2b`, CPU, 51.73 s, Pydantic aprobado y 4 fragmentos recuperados de 2 fuentes.
- Actividad indeterminada y cinco etapas visibles durante la espera; fallback y ausencia de evidencia diferenciados.
- Layout sin desbordamiento horizontal a 1366×768 y 1920×1080; logos KutanLab/Gemma visibles sin recorte.
- Suite final: 61 pruebas aprobadas. Smoke test: exit 0, Streamlit `/_stcore/health` HTTP 200.

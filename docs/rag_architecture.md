# Arquitectura RAG trazable

El RAG del prototipo es local, léxico y deliberadamente pequeño. `rag/ingest.py` lee el registro de fuentes y sólo ingiere fragmentos preaprobados; guarda texto, metadatos, hash SHA-256 y una copia FTS5 en SQLite. No descarga documentos durante la ejecución ni redistribuye PDFs.

```text
source_register.csv + approved_chunks.json
                 │ validación de licencia, vigencia y población
                 ▼
         rag_documents / rag_chunks / FTS5
                 │ consulta léxica, máximo 6 resultados
                 ▼
      filtro de elegibilidad y población ──► citas visibles
                 │
                 ▼
       Gemma 4 + esquema Pydantic estricto
                 │
                 ▼
       reglas Python + auditoría SQLite
```

## Fronteras de confianza

- Los fragmentos recuperados son **datos no confiables**, no instrucciones. El prompt obliga a ignorar órdenes contenidas en documentos.
- `rag/safety.py` rechaza contenido activo, intentos de prompt injection, fuentes no aprobadas, desactualizadas, sustituidas o de población incompatible.
- Gemma sólo puede citar identificadores incluidos en la recuperación de esa ejecución. Una cita desconocida invalida el análisis.
- Las métricas son de trazabilidad (documentos recuperados, citados y cobertura), no de exactitud clínica.
- La ausencia de evidencia se muestra explícitamente y no se rellena con conocimiento inventado.

## Límites

FTS5 es una base reproducible para la demo, no un buscador clínico validado. No hay reranking semántico, evaluación de relevancia clínica ni garantía de cobertura. Antes de uso real se requieren corpus con licencia, gobierno institucional, versionado de umbrales, evaluación profesional y controles de privacidad.

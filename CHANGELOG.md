# Changelog

## 0.3.0 - 2026-08-01

- Navegación multivista por seis perfiles clínicos/administrativos demostrativos.
- Base sintética relacional con 2 instituciones, 10 pacientes y 20 atenciones históricas; seed/reset idempotentes.
- RAG local FTS5 con gobierno de fuentes, filtros de vigencia/población, hashes y citas verificadas.
- Esquema Gemma ampliado, máquina de estados visible, actividad indeterminada, duración, CPU y fallback explícito.
- Portal del paciente, cola de triaje, panel médico y auditoría con cierre independiente del LLM.
- Identidad visual local de KutanLab y Gemma con fallback tipográfico de TRIaje 360.
- Pruebas de flujos, seguridad RAG, branding y contrato visual; documentación de despliegue y fuentes.

## 0.2.0 - 2026-08-01

- Integración del MVP funcional en el repositorio colaborativo.
- Rediseño completo de la interfaz clínica Streamlit.
- Encabezado estable, panel inicial informativo, estado del sistema y flujo de cuatro etapas.
- Componentes y estilos separados bajo `ui/`.
- Pruebas de contrato visual, portabilidad y seguridad del CSS.
- Documentación de instalación, demostración y contribución desde `develop`.

## 1.0.0 — 2026-07-31

- Interfaz web responsiva de admisión y panel clínico.
- Integración verificable con Ollama y `gemma4:e2b`.
- Esquema Pydantic estricto y respaldo determinista.
- Motor de protocolos, checklist y bloqueo de cierre.
- Trazabilidad SQLite en ocho tablas de negocio.
- Scripts de instalación, ejecución, detención y smoke test para Windows.
- Suite automatizada y documentación de demo, arquitectura y seguridad.

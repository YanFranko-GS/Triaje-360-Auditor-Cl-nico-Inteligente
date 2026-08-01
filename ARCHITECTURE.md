# Arquitectura

## Capa de presentación

- `app.py`: composición del flujo Streamlit y estado de sesión.
- `ui/components.py`: encabezado, estado, etapas, ficha ficticia, panel inicial y avisos de motor.
- `ui/theme.py`: carga del tema local.
- `ui/styles.css`: diseño institucional adaptable, con espaciado superior seguro y sin posicionamiento fijo.

La capa visual consume los resultados de `engine.py`; no selecciona protocolos ni habilita cierres por sí misma.

## Decisiones

La aplicación es un monolito modular de Streamlit, adecuado para una demostración local con 12 GB de RAM. No requiere servicios propios adicionales: Ollama es opcional y SQLite se crea de forma idempotente.

## Flujo

1. `app.py` recupera el paciente ficticio y remite relato y antecedentes a `engine.process_case`.
2. `services/ollama_client.py` consulta `/api/tags`, exige `gemma4:e2b` y llama `/api/chat` con temperatura 0.1, límite de 300 tokens y timeout configurable.
3. `schemas.GemmaAnalysis` rechaza campos adicionales, textos extensos, descargo ausente o `protocol_id` desconocido.
4. Ante cualquier error, el motor cerrado crea una respuesta segura y registra la causa.
5. `protocols.py` carga solo `respiratory_alert` y `general_review`.
6. `database.py` crea la consulta, respuesta, checklist y evento de auditoría dentro de una transacción.
7. Cada acción registrada se valida determinísticamente. `attempt_close` es la única puerta de cierre y persiste tanto bloqueos como cierres permitidos.

## Componentes y límites de confianza

- **Gemma 4:** texto no confiable hasta pasar Pydantic; no decide el cierre.
- **Catálogo JSON:** identificadores autorizados y campos requeridos revisables.
- **Motor Python:** fuente de verdad para completitud, avance y cierre.
- **SQLite:** trazabilidad local; no está preparada para datos reales ni acceso multiusuario.
- **Streamlit:** presentación y captura del registro; no implementa autenticación.

## Datos persistidos

Ocho tablas de negocio: `patients`, `medical_history`, `consultations`, `model_responses`, `checklist_items`, `actions`, `closures` y `audits`. Las claves foráneas están activas y la inicialización puede repetirse.

## Identidad, voz y conversación

`auth_service.py` separa hashes, autenticación, sesiones y eventos de login de la presentación. `ui/auth.py` sólo captura datos; `app.py` aplica permisos antes de construir navegación. La navegación programática usa `requested_page`, que se consume antes de instanciar `st.radio(key="nav_page")`.

`audio_pipeline.py` valida y acondiciona WAV sin persistirlo. `services/local_asr.py` carga Vosk únicamente cuando existe paquete y ruta local. `intake_service.py` entrega a Gemma texto confirmado, valida la extracción con `IntakeExtraction` y degrada a extracción determinista explícita. `workflow_store.py` conserva metadatos, transcripción, turnos, campos y confirmaciones.

## Arquitectura multivista y RAG

`app.py` compone configuración, migraciones, perfil y navegación. `ui/pages.py` implementa las vistas por rol y `ui/ai_status.py` la máquina visual `OFFLINE → STARTING → READY → WARMING_UP → ANALYZING → VALIDATING → COMPLETED`, con estados explícitos de `FALLBACK` y `ERROR`.

`clinical_db.py` mantiene el dominio demostrativo separado mediante tablas `demo_*`. El portal crea `AWAITING_TRIAGE`; el profesional registra signos y decisión para avanzar a `AWAITING_PHYSICIAN`; el médico documenta y cierra sólo cuando las reglas configuradas lo permiten. El LLM no cambia estados por sí mismo.

El subsistema `rag/` valida gobierno y contenido, ingiere fragmentos aprobados en FTS5, filtra por población y entrega citas permitidas a Gemma. La salida ampliada distingue datos estructurados, información faltante, preguntas de revisión y evidencia. Las citas desconocidas invalidan el resultado. Véase [docs/rag_architecture.md](docs/rag_architecture.md).

## Degradación segura

Ollama desconectado, modelo ausente, timeout, HTTP inválido, salida vacía, JSON defectuoso o validación fallida convergen en el mismo respaldo determinista. `model_used` solo vale 1 después de recibir, identificar y validar la respuesta real.

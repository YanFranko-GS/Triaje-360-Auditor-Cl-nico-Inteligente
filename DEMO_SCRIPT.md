# Guion de presentación de TRIaje 360

## Preparación

1. Ejecute `01_PROBAR_TODO.bat` y confirme pruebas, Gemma y HTTP 200.
2. Inicie la aplicación y abra `http://localhost:8501`.
3. Mantenga Ollama activo con `gemma4:e2b`.

## Recorrido principal

1. Presente **TRIaje 360 — Plataforma inteligente de admisión, triaje y continuidad clínica** y las marcas KutanLab y Gemma.
2. Ingrese con `76543210` / `1999-01-01`. Muestre que el sistema recupera identidad e historia confirmada.
3. En **Nueva atención**, autorice la captura, grabe o escriba: “Tengo dolor en el pecho desde esta mañana”. Revise la transcripción editable.
4. Pulse **Continuar**. Explique la extracción principal y la verificación independiente secuencial. Responda una pregunta por turno; use **No sé** para mostrar un `NULL` con motivo.
5. Revise campos, origen y confirmación. Pulse **Enviar a triaje** y abra **Estado de atención**.
6. Ingrese como `nurse.demo` / `Clinica360-N1!`. Abra la cola, revise relato, memoria, completitud, contradicciones y evidencia RAG.
7. Registre signos vitales. Muestre la prioridad configurable, modifíquela o acéptela y deje trazabilidad profesional.
8. Ingrese como `attending.demo` / `Clinica360-M1!`. Recorra resumen, historia, signos, triaje, fuentes, pendientes, registro profesional, analítica y auditoría.
9. Ingrese como `admin.demo` / `Clinica360-A1!`. Abra **Estructura de datos** y muestre tablas, columnas, registros, claves foráneas y migraciones sin secretos.

## Casos alternativos

- Respiratorio: “Tengo dificultad para respirar desde hace una hora”.
- Dolor abdominal: “Tengo dolor abdominal desde ayer y está empeorando”.
- Cefalea: “Presento cefalea gradual desde hace dos horas”.
- Lesión: “Me lesioné el tobillo esta mañana; dolor 5 de 10”.
- Sin dolor: “Tengo tos desde hace tres días, sin dolor”.
- Paciente nuevo: use **Registrar nuevo paciente**, un DNI sintético de ocho dígitos no registrado y luego acceda con su fecha de nacimiento.

## Mensajes obligatorios

- Gemma estructura y verifica; no diagnostica ni prescribe.
- El segundo proceso reduce omisiones, pero no garantiza exactitud clínica.
- La prioridad es una propuesta configurable que el profesional acepta, modifica, escala o reevalúa.
- ESI no se presenta como norma nacional peruana.
- RAG ofrece contexto documentado y trazable, no decisiones clínicas.
- Entorno de validación con información sintética. No sustituye el juicio clínico.

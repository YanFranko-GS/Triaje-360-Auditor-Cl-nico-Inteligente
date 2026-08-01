# KutanLab: TRIaje 360 — Auditor Clínico Inteligente

## Problema

Durante la atención, la documentación incompleta puede dificultar la continuidad y la revisión concurrente. En contextos con recursos limitados, una herramienta local y resiliente puede ayudar a visibilizar campos pendientes sin convertir a la IA en decisora clínica.

## Solución

TRIaje 360 es una aplicación web educativa con dos módulos: admisión ficticia y panel de auditoría de completitud. El paciente simulado aporta DNI y relato; Gemma 4 lo transforma en un resumen estructurado, banderas para revisión profesional, protocolo demostrativo y motivo breve. Un motor Python independiente valida, crea el checklist y bloquea el cierre mientras falten acciones.

## Arquitectura e integración con Gemma 4

Streamlit ofrece la interfaz, Ollama ejecuta localmente `gemma4:e2b`, Pydantic valida la respuesta, Python aplica protocolos cerrados y SQLite conserva trazabilidad. Antes de inferir, el cliente verifica `/api/tags` y el modelo exacto. La llamada usa temperatura baja, salida JSON, tokens limitados y timeout.

`model_used=true` solo se guarda cuando Ollama respondió, identificó `gemma4:e2b`, entregó contenido y el JSON superó el esquema estricto. Gemma no puede crear protocolos ni cerrar consultas. Si falla la conexión, falta el modelo, vence el timeout o la salida es inválida, reglas cerradas mantienen la demostración y registran la causa.

## Funcionalidad

El caso principal usa el DNI ficticio `76543210`, con antecedentes simulados, y el relato “Tengo dolor en la espalda al respirar y me falta el aire desde ayer”. Se espera `respiratory_alert`, prioridad documental naranja, banderas y cuatro acciones. La barra muestra avance; el cierre solo se habilita con 4/4. Respuestas, acciones, bloqueos y cierre quedan en SQLite.

## Innovación

La innovación no es delegar decisiones clínicas, sino separar claramente dos responsabilidades: el modelo estructura lenguaje y el motor determinista gobierna el flujo. Esta frontera facilita auditoría, demostración offline y explicación honesta sobre cuándo participó Gemma.

## Impacto social y ODS

El proyecto se alinea con **ODS 3** al explorar apoyo seguro al registro clínico; **ODS 9** mediante IA local y arquitectura resiliente; y **ODS 10** al priorizar ejecución en hardware accesible y conectividad limitada. Su impacto real requeriría cocreación con profesionales, validación clínica y evaluación regulatoria.

## Limitaciones y trabajo futuro

Es un MVP con datos y protocolos ficticios. No incluye autenticación, cifrado, interoperabilidad, voz real, validación clínica ni despliegue multiusuario. El siguiente trabajo debe incluir revisión ética, pruebas con usuarios autorizados, análisis de sesgos, seguridad, consentimiento, estándares de interoperabilidad y protocolos aprobados por cada institución.

## Evidencia técnica

El repositorio contiene suite pytest, `smoke_test.ps1`, verificación HTTP de Streamlit, inicialización SQLite idempotente, comprobación real de Ollama/modelos, inferencia mínima cuando Gemma está disponible y prueba explícita del respaldo. La interfaz expone modelo, `model_used`, JSON validado y eventos persistidos.

## Evolución: plataforma clínica demostrativa trazable

La segunda iteración convierte el panel lineal en un recorrido por roles: captura del paciente, cola de triaje, revisión médica, administración del dataset sintético y auditoría. La base reproduce relaciones entre instituciones, perfiles, antecedentes, atenciones, signos vitales, decisiones, ejecuciones de modelo y fuentes, sin almacenar personas reales.

Se añadió RAG local con SQLite FTS5. Sólo se indexan fragmentos breves con licencia/estado revisados; el modelo recibe documentos como datos no confiables, sólo puede citar los identificadores recuperados y no inventa evidencia cuando no hay resultados. La demo presenta trazabilidad, no una afirmación de exactitud clínica.

Gemma sigue siendo verificable: estados visibles, tiempo real, modelo exacto, CPU, documentos recuperados, validación Pydantic, fallback y `model_used`. El profesional conserva aceptar, modificar, escalar o solicitar reevaluación, y las reglas Python gobiernan estados y cierre.

## Equipo

KutanLab: Daniel Ríos; Yan Franco Gonzales Segura; Jhon Gesell Villanueva Portella.

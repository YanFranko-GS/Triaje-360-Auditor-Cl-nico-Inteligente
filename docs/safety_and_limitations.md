# Seguridad y limitaciones

TRIaje 360 es una demostración educativa con pacientes y protocolos ficticios. No diagnostica, prescribe, recomienda medicamentos, determina negligencia ni sustituye el juicio profesional. No afirma usar protocolos oficiales y no reemplaza los institucionales.

## Controles implementados

- Lista cerrada de dos protocolos demostrativos.
- Salida de Gemma con Pydantic, límites de longitud y campos extra prohibidos.
- Descargo obligatorio y ausencia de razonamiento interno.
- Cierre controlado únicamente por reglas Python.
- Respaldo determinista y registro explícito de fallos.
- Reinicio limitado a registros marcados como demo.

## Controles añadidos en la demo multivista

- Perfiles y consentimiento son simulados y están etiquetados como no aptos para producción.
- Ollama se limita a `127.0.0.1`; el acceso LAN está desactivado por defecto.
- El RAG sólo ingiere fuentes aprobadas, vigentes y de población compatible; rechaza instrucciones y contenido activo dentro de documentos.
- Las citas del modelo deben pertenecer a la recuperación actual. “Documentos recuperados” y cobertura son trazabilidad, no exactitud clínica.
- No existen umbrales universales atribuidos a MINSA/EsSalud; la escala de cinco niveles está rotulada como demostrativa.
- Cierre, transiciones y reset dependen de reglas Python acotadas, no del LLM.

La nueva base sí incluye roles, consentimiento y auditoría **demostrativos**, pero no autenticación, autorización ni consentimiento legal reales. Todo identificador y episodio incluido es sintético.

## Fuera del alcance

No hay autenticación, roles, cifrado de base, consentimiento, interoperabilidad clínica, alta disponibilidad, reconocimiento de voz, validación clínica, monitoreo de sesgos ni certificación regulatoria. No debe desplegarse con información real sin una evaluación integral de privacidad, seguridad, regulación y factores humanos.

# Seguridad y limitaciones

TRIaje 360 es una demostración educativa con pacientes y protocolos ficticios. No diagnostica, prescribe, recomienda medicamentos, determina negligencia ni sustituye el juicio profesional. No afirma usar protocolos oficiales y no reemplaza los institucionales.

## Controles implementados

- Lista cerrada de dos protocolos demostrativos.
- Salida de Gemma con Pydantic, límites de longitud y campos extra prohibidos.
- Descargo obligatorio y ausencia de razonamiento interno.
- Cierre controlado únicamente por reglas Python.
- Respaldo determinista y registro explícito de fallos.
- Reinicio limitado a registros marcados como demo.

## Fuera del alcance

No hay autenticación, roles, cifrado de base, consentimiento, interoperabilidad clínica, alta disponibilidad, reconocimiento de voz, validación clínica, monitoreo de sesgos ni certificación regulatoria. No debe desplegarse con información real sin una evaluación integral de privacidad, seguridad, regulación y factores humanos.

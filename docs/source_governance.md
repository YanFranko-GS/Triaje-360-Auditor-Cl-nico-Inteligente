# Gobierno de fuentes

La fuente de verdad es `docs/source_register.csv`. Cada fila conserva título, entidad, URL, fecha, población, jurisdicción, licencia o términos, vigencia, estado de sustitución, aprobación y notas. La ingestión se limita a filas con `approved=true` y a fragmentos breves, parafraseados y con hash.

## Fuentes aprobadas para la demo

- `WHO_BEC_2018`: página pública del curso Basic Emergency Care de OMS; población mixta y advertencia explícita al usarla en contexto adulto.
- `ESSALUD_RRI_2019`: reporte de respuesta rápida sobre sistemas de triaje del repositorio IETSI/EsSalud, marcado como acceso abierto.

La aprobación significa únicamente “apta para esta demostración documental”; no significa que sea un protocolo clínico local, vigente para todos los establecimientos ni validado para decisión asistencial.

## Fuentes registradas pero no ingeridas

Normas MINSA/SAMU, catálogos hospitalarios y guías pediátricas se conservan como evidencia de revisión, pero quedan fuera por licencia no clara, antigüedad, sustitución, población incompatible o falta de verificación. Una URL de OPS respondió HTTP 403 y no se aprobó. No se descargaron ni versionaron PDFs de terceros.

## Incorporación futura

1. Verificar autoridad, URL canónica, fecha, vigencia, población, jurisdicción y términos de redistribución.
2. Obtener aprobación institucional y registrar responsable/fecha.
3. Extraer sólo el mínimo necesario; desactivar contenido activo y revisar prompt injection.
4. Calcular hash, agregar pruebas de población/citas y ejecutar el informe de validación RAG.
5. Marcar la fuente anterior como sustituida antes de activar una revisión nueva.

# Flujos por rol

Los perfiles son demostrativos; no constituyen autenticación de producción.

| Rol | Vista y responsabilidad demo |
|---|---|
| `PATIENT` | Registra consentimiento ficticio, motivo, relato, duración y dolor; recibe sólo estado de envío y señales de solicitar personal. |
| `TRIAGE_NURSE` | Revisa cola, antecedentes, signos vitales, evidencia recuperada y registra aceptación, modificación, escalamiento o reevaluación. |
| `TRIAGE_DOCTOR` | Mismo flujo de triaje con perfil médico configurable por establecimiento. |
| `ATTENDING_PHYSICIAN` | Revisa cronología, faltantes, banderas, evidencia/citas y documenta su decisión. |
| `SUPERVISOR` | Accede a revisión médica, datos ficticios y auditoría. |
| `ADMIN` | Puede recorrer todas las vistas, sembrar/restablecer datos demo y revisar fuentes. |

Estados principales: `AWAITING_TRIAGE → AWAITING_PHYSICIAN → CLOSED`. La clasificación usa una escala **demostrativa** de cinco niveles sin afirmar umbrales universales. El cierre documental depende de campos configurados y decisiones profesionales persistidas, nunca de Gemma.

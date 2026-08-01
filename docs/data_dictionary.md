# Diccionario de datos

| Tabla | Propósito | Campos principales |
|---|---|---|
| `patients` | Identidad exclusivamente ficticia | `dni`, `name`, `age`, `sex`, `is_demo` |
| `medical_history` | Antecedentes simulados | `patient_dni`, `category`, `detail`, `event_date` |
| `consultations` | Cabecera y estado | `symptoms`, `protocol_id`, `priority`, `model_used`, `status`, `block_reason` |
| `model_responses` | Evidencia de análisis | `model_name`, `validated`, `response_json`, `error_detail` |
| `checklist_items` | Obligaciones del protocolo | `action_id`, `action_type`, `value_json`, `completed` |
| `actions` | Historial inmutable de registros | `action_id`, `value_json`, `completed`, `actor`, `created_at` |
| `closures` | Intentos permitidos o bloqueados | `permitted`, `reason`, `actor`, `created_at` |
| `audits` | Eventos técnicos | `event_type`, `details_json`, `created_at` |

Las fechas se almacenan en ISO 8601 UTC. Los JSON preservan Unicode. `model_used=1` significa respuesta real, modelo identificado y esquema validado.

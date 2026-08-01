# Esquema relacional de TRIaje 360

La migración final es idempotente, activa `PRAGMA foreign_keys=ON` y amplía el esquema heredado sin eliminar registros. La memoria clínica no depende del historial libre del modelo.

| Dominio | Tablas principales |
|---|---|
| Identidad y acceso | `patients`, `patient_identifiers`, `users`, `roles`, `user_roles`, `sessions` |
| Organización | `institutions`, `facilities` |
| Atención | `encounters`, `symptoms`, `pain_assessments`, `vital_signs`, `triage_assessments` |
| Memoria longitudinal | `allergies`, `medications`, `prescriptions`, `diagnoses`, `procedures`, `laboratory_results`, `imaging_results`, `clinical_notes` |
| Conversación | `conversation_turns`, `field_extractions`, `field_confirmations` |
| IA y evidencia | `model_runs`, `rag_retrievals` |
| Trazabilidad | `audit_events` |

Las tablas `demo_*` permanecen como capa de compatibilidad para la rama anterior. Los nuevos registros se reflejan en la capa longitudinal. Los valores nulos de conversación requieren un estado y motivo en `field_confirmations`; una ausencia inferida no se considera confirmada.

## Exportación e inspección

```powershell
.\.venv\Scripts\python.exe scripts\export_schema.py
.\.venv\Scripts\python.exe scripts\inspect_database.py
.\.venv\Scripts\python.exe scripts\inspect_database.py --json
```

- [DDL completo](database_schema.sql)
- [Diagrama Mermaid](database_relationships.mmd)

La vista **Estructura de datos** está restringida a `ADMIN` y filtra columnas relacionadas con contraseñas, hashes, sales, secretos y tokens.

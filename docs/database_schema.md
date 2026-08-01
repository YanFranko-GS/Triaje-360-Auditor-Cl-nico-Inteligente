# Esquema de base de datos demostrativa

Las tablas nuevas usan prefijo `demo_` para convivir con el MVP anterior y permitir un reset acotado.

| Grupo | Tablas |
|---|---|
| Organización y acceso | `demo_institutions`, `demo_facilities`, `demo_roles`, `demo_users`, `demo_user_roles` |
| Paciente | `demo_patients`, `demo_allergies`, `demo_patient_allergies`, `demo_medications`, `demo_patient_medications` |
| Atención | `demo_encounters`, `demo_vital_signs`, `demo_triage_assessments`, `demo_clinical_notes`, `demo_requested_considerations` |
| IA y evidencia | `rag_documents`, `rag_chunks`, `rag_chunks_fts`, `demo_rag_retrievals`, `demo_model_runs` |
| Trazabilidad | `demo_audit_events` |

La migración y el seed son idempotentes, activan claves foráneas e índices y crean 2 instituciones, 6 perfiles profesionales/administrativos, 10 pacientes sintéticos y 20 atenciones históricas. El identificador `76543210` está marcado como ficticio. `reset_demo_data()` elimina únicamente filas `demo_*`, vuelve a sembrarlas y preserva tablas externas y del flujo heredado.

SQLite es adecuado para una demo local de un usuario. No ofrece las garantías de concurrencia, cifrado, control de acceso ni operación requeridas por una historia clínica real.

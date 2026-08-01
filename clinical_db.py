from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import load_settings


DEMO_PREFIX = "DEMO_"
ROLES = ("PATIENT", "TRIAGE_NURSE", "TRIAGE_DOCTOR", "ATTENDING_PHYSICIAN", "SUPERVISOR", "ADMIN")


class ClosingConnection(sqlite3.Connection):
    """Conexión que confirma/revierte y libera el archivo al salir del contexto."""

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path or load_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def migrate_demo_schema(db_path: Path | str | None = None) -> None:
    with connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS demo_institutions(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, country TEXT NOT NULL,
                source TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_facilities(
                id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES demo_institutions(id),
                name TEXT NOT NULL, triage_role TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_roles(id TEXT PRIMARY KEY, label TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS demo_users(
                id TEXT PRIMARY KEY, display_name TEXT NOT NULL, demo_profile INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_user_roles(
                user_id TEXT NOT NULL REFERENCES demo_users(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL REFERENCES demo_roles(id), PRIMARY KEY(user_id,role_id)
            );
            CREATE TABLE IF NOT EXISTS demo_patients(
                id TEXT PRIMARY KEY, synthetic_identifier TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
                age INTEGER NOT NULL, registered_sex TEXT NOT NULL, insurer TEXT NOT NULL,
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), source TEXT NOT NULL,
                status TEXT NOT NULL, created_by TEXT, updated_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_allergies(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS demo_patient_allergies(
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                allergy_id TEXT NOT NULL REFERENCES demo_allergies(id), source TEXT NOT NULL,
                PRIMARY KEY(patient_id,allergy_id)
            );
            CREATE TABLE IF NOT EXISTS demo_medications(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS demo_patient_medications(
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                medication_id TEXT NOT NULL REFERENCES demo_medications(id), status TEXT NOT NULL,
                source TEXT NOT NULL, PRIMARY KEY(patient_id,medication_id)
            );
            CREATE TABLE IF NOT EXISTS demo_encounters(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL REFERENCES demo_patients(id),
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), status TEXT NOT NULL,
                chief_complaint TEXT NOT NULL, narrative TEXT NOT NULL, duration TEXT,
                pain_present INTEGER NOT NULL DEFAULT 0, pain_score INTEGER, pain_location TEXT,
                onset TEXT, evolution TEXT, accompanying_symptoms_json TEXT NOT NULL DEFAULT '[]',
                consent_demo INTEGER NOT NULL DEFAULT 0, mobility TEXT, companion TEXT,
                pregnancy_possible TEXT, source TEXT NOT NULL, created_by TEXT, updated_by TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_vital_signs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                systolic INTEGER, diastolic INTEGER, heart_rate INTEGER, respiratory_rate INTEGER,
                temperature REAL, oxygen_saturation INTEGER, glucose INTEGER, consciousness_scale TEXT,
                weight REAL, height REAL, pain_score INTEGER, population TEXT NOT NULL,
                source TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_triage_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                proposed_level TEXT NOT NULL, confirmed_level TEXT, decision TEXT NOT NULL,
                justification TEXT, reevaluation_requested INTEGER NOT NULL DEFAULT 0,
                scale_name TEXT NOT NULL, source TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_clinical_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                section TEXT NOT NULL, note TEXT NOT NULL, source TEXT NOT NULL,
                created_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_requested_considerations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES demo_encounters(id) ON DELETE CASCADE,
                statement TEXT NOT NULL, source_ids_json TEXT NOT NULL, applicability TEXT NOT NULL,
                professional_decision TEXT NOT NULL, justification TEXT, created_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_rag_retrievals(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                source_id TEXT NOT NULL, chunk_id TEXT NOT NULL, score REAL NOT NULL,
                retrieval_reason TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_model_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                provider TEXT NOT NULL, model_name TEXT NOT NULL, state TEXT NOT NULL,
                model_used INTEGER NOT NULL, fallback_reason TEXT, duration_seconds REAL,
                validated INTEGER NOT NULL, result_json TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_audit_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL, details_json TEXT NOT NULL, actor_id TEXT,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_password_credentials(
                user_id TEXT PRIMARY KEY REFERENCES demo_users(id) ON DELETE CASCADE,
                username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
                algorithm TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_patient_access(
                user_id TEXT PRIMARY KEY REFERENCES demo_users(id) ON DELETE CASCADE,
                patient_id TEXT NOT NULL REFERENCES demo_patients(id) ON DELETE CASCADE,
                birth_date TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_sessions(
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES demo_users(id), role_id TEXT NOT NULL,
                facility_id TEXT, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS demo_login_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username_fingerprint TEXT,
                role_id TEXT, success INTEGER NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_audio_sessions(
                id TEXT PRIMARY KEY, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL, noise_profile TEXT NOT NULL, consent INTEGER NOT NULL,
                store_audio INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS demo_audio_segments(
                id TEXT PRIMARY KEY, audio_session_id TEXT NOT NULL REFERENCES demo_audio_sessions(id) ON DELETE CASCADE,
                sequence_no INTEGER NOT NULL, mime_type TEXT NOT NULL, duration_seconds REAL NOT NULL,
                sample_rate INTEGER NOT NULL, audio_sha256 TEXT NOT NULL, signal_status TEXT NOT NULL,
                stored_path TEXT, created_at TEXT NOT NULL, UNIQUE(audio_session_id,sequence_no)
            );
            CREATE TABLE IF NOT EXISTS demo_transcriptions(
                id TEXT PRIMARY KEY, audio_segment_id TEXT REFERENCES demo_audio_segments(id) ON DELETE SET NULL,
                encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                provider TEXT NOT NULL, text TEXT NOT NULL, confidence REAL, confirmed INTEGER NOT NULL DEFAULT 0,
                edited_text TEXT, created_at TEXT NOT NULL, confirmed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS demo_conversation_turns(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                turn_no INTEGER NOT NULL, speaker TEXT NOT NULL, question TEXT, response TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_field_extractions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES demo_encounters(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL, value_json TEXT, source TEXT NOT NULL,
                confidence_status TEXT NOT NULL, requires_confirmation INTEGER NOT NULL,
                model_run_id INTEGER REFERENCES demo_model_runs(id), created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_field_confirmations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, extraction_id INTEGER NOT NULL REFERENCES demo_field_extractions(id) ON DELETE CASCADE,
                confirmed_value_json TEXT, status TEXT NOT NULL, confirmed_by TEXT NOT NULL,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_workflow_requirements(
                facility_id TEXT NOT NULL REFERENCES demo_facilities(id), population TEXT NOT NULL,
                stage TEXT NOT NULL, field_name TEXT NOT NULL, required INTEGER NOT NULL,
                version TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(facility_id,population,stage,field_name)
            );
            CREATE INDEX IF NOT EXISTS idx_demo_encounters_status ON demo_encounters(status,created_at);
            CREATE INDEX IF NOT EXISTS idx_demo_vitals_encounter ON demo_vital_signs(encounter_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_demo_audit_encounter ON demo_audit_events(encounter_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_demo_sessions_user ON demo_sessions(user_id,ended_at);
            CREATE INDEX IF NOT EXISTS idx_demo_login_created ON demo_login_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_demo_turns_encounter ON demo_conversation_turns(encounter_id,turn_no);
            """
        )


def _audit(connection: sqlite3.Connection, event_type: str, details: dict[str, Any], *, encounter_id: int | None = None, actor_id: str | None = None) -> None:
    connection.execute(
        "INSERT INTO demo_audit_events(encounter_id,event_type,details_json,actor_id,source,created_at) VALUES(?,?,?,?,?,?)",
        (encounter_id, event_type, json.dumps(details, ensure_ascii=False), actor_id, "demo_application", utc_now()),
    )


def seed_demo_data(db_path: Path | str | None = None) -> dict[str, int]:
    migrate_demo_schema(db_path)
    now = utc_now()
    with connect(db_path) as connection:
        initial_seed = connection.execute("SELECT COUNT(*) FROM demo_patients").fetchone()[0] == 0
        institutions = (
            ("DEMO_MINSA", "Red clínica Andina", "validation-network", "Perú"),
            ("DEMO_ESSALUD", "Red clínica Costa", "validation-network", "Perú"),
        )
        for item in institutions:
            connection.execute(
                "INSERT OR IGNORE INTO demo_institutions VALUES(?,?,?,?,?,?,?,?)",
                (*item, "seed_demo", "active", now, now),
            )
        facilities = (
            ("DEMO_FAC_A", "DEMO_MINSA", "Centro Andino", "TRIAGE_NURSE"),
            ("DEMO_FAC_B", "DEMO_ESSALUD", "Policlínico Costa", "TRIAGE_DOCTOR"),
        )
        for item in facilities:
            connection.execute(
                "INSERT OR IGNORE INTO demo_facilities VALUES(?,?,?,?,?,?,?,?)",
                (*item, "seed_demo", "active", now, now),
            )
        for facility_id in ("DEMO_FAC_A", "DEMO_FAC_B"):
            for field_name in ("chief_complaint", "narrative", "consent_demo"):
                connection.execute(
                    "INSERT OR IGNORE INTO demo_workflow_requirements VALUES(?,?,?,?,?,?,?)",
                    (facility_id, "adult", "admission", field_name, 1, "demo-2026.08", now),
                )
        for role in ROLES:
            connection.execute("INSERT OR IGNORE INTO demo_roles VALUES(?,?)", (role, role.replace("_", " ").title()))
        users = (
            ("DEMO_PATIENT", "Paciente 01", "PATIENT"),
            ("DEMO_NURSE_1", "Profesional de triaje A", "TRIAGE_NURSE"),
            ("DEMO_TRIAGE_MD", "Profesional de triaje B", "TRIAGE_DOCTOR"),
            ("DEMO_ATTENDING_1", "Médico tratante A", "ATTENDING_PHYSICIAN"),
            ("DEMO_ATTENDING_2", "Médico tratante B", "ATTENDING_PHYSICIAN"),
            ("DEMO_SUPERVISOR", "Supervisor local", "SUPERVISOR"),
            ("DEMO_ADMIN", "Administrador local", "ADMIN"),
        )
        for user_id, name, role in users:
            connection.execute("INSERT OR IGNORE INTO demo_users VALUES(?,?,?,?,?,?)", (user_id, name, 1, "active", now, now))
            connection.execute("INSERT OR IGNORE INTO demo_user_roles VALUES(?,?)", (user_id, role))
        patients = []
        for number in range(1, 11):
            identifier = "76543210" if number == 1 else f"SYN-{number:06d}"
            patients.append(
                (
                    f"DEMO_PAT_{number:02d}", identifier, f"Paciente {number:02d}", 22 + number * 4,
                    "Mujer" if number % 2 else "Hombre", "MINSA" if number % 2 else "EsSalud",
                    "DEMO_FAC_A" if number % 2 else "DEMO_FAC_B", "seed_demo", "active",
                    "DEMO_ADMIN", "DEMO_ADMIN", now, now,
                )
            )
        connection.executemany("INSERT OR IGNORE INTO demo_patients VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", patients)
        for user_id, name, _role in users:
            connection.execute("UPDATE demo_users SET display_name=?,updated_at=? WHERE id=?", (name, now, user_id))
        for number in range(1, 11):
            connection.execute("UPDATE demo_patients SET display_name=?,updated_at=? WHERE id=?", (f"Paciente {number:02d}", now, f"DEMO_PAT_{number:02d}"))
        connection.execute("UPDATE demo_institutions SET name='Red clínica Andina',updated_at=? WHERE id='DEMO_MINSA'", (now,))
        connection.execute("UPDATE demo_institutions SET name='Red clínica Costa',updated_at=? WHERE id='DEMO_ESSALUD'", (now,))
        connection.execute("UPDATE demo_facilities SET name='Centro Andino',updated_at=? WHERE id='DEMO_FAC_A'", (now,))
        connection.execute("UPDATE demo_facilities SET name='Policlínico Costa',updated_at=? WHERE id='DEMO_FAC_B'", (now,))
        # Stable eight-digit synthetic identifiers for additional end-to-end patient access.
        connection.execute("UPDATE demo_patients SET synthetic_identifier='87654321' WHERE id='DEMO_PAT_02'")
        connection.execute("UPDATE demo_patients SET synthetic_identifier='11223344' WHERE id='DEMO_PAT_03'")
        allergies = (("ALG_AINE", "AINEs"), ("ALG_PEN", "Penicilina"), ("ALG_NONE", "Sin alergias declaradas"))
        medications = (("MED_A", "Medicamento histórico A"), ("MED_B", "Medicamento histórico B"), ("MED_NONE", "Sin medicación habitual declarada"))
        connection.executemany("INSERT OR IGNORE INTO demo_allergies VALUES(?,?)", allergies)
        connection.executemany("INSERT OR IGNORE INTO demo_medications VALUES(?,?)", medications)
        for number in range(1, 11):
            patient_id = f"DEMO_PAT_{number:02d}"
            allergy_id = "ALG_AINE" if number == 1 else "ALG_NONE"
            medication_id = "MED_A" if number % 3 == 0 else "MED_NONE"
            connection.execute("INSERT OR IGNORE INTO demo_patient_allergies VALUES(?,?,?)", (patient_id, allergy_id, "seed_demo"))
            connection.execute("INSERT OR IGNORE INTO demo_patient_medications VALUES(?,?,?,?)", (patient_id, medication_id, "historical", "seed_demo"))
        count = connection.execute("SELECT COUNT(*) FROM demo_encounters WHERE source='seed_demo'").fetchone()[0]
        if count < 20:
            for number in range(1, 21):
                created = (datetime.now(timezone.utc) - timedelta(days=number * 7)).isoformat(timespec="seconds")
                connection.execute(
                    """INSERT INTO demo_encounters(patient_id,facility_id,status,chief_complaint,narrative,duration,
                       pain_present,pain_score,pain_location,onset,evolution,accompanying_symptoms_json,consent_demo,
                       mobility,companion,pregnancy_possible,source,created_by,updated_by,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"DEMO_PAT_{((number - 1) % 10) + 1:02d}", "DEMO_FAC_A" if number % 2 else "DEMO_FAC_B",
                        "CLOSED", "Atención histórica ficticia", "Registro sintético sin instrucciones terapéuticas.",
                        "1 día", 0, 0, "", "gradual", "estable", "[]", 1, "independiente", "sin acompañante",
                        "no aplica", "seed_demo", "DEMO_ADMIN", "DEMO_ADMIN", created, created,
                    ),
                )
                encounter_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
                connection.execute(
                    """INSERT INTO demo_vital_signs(encounter_id,systolic,diastolic,heart_rate,respiratory_rate,
                       temperature,oxygen_saturation,glucose,consciousness_scale,weight,height,pain_score,population,
                       source,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (encounter_id, 110 + number % 10, 70 + number % 5, 70 + number, 16 + number % 4, 36.5, 97, None, "Alerta", 60.0, 1.65, 0, "adult", "seed_demo", "DEMO_NURSE_1", created),
                )
                _audit(connection, "seed_encounter_closed", {"synthetic": True}, encounter_id=encounter_id, actor_id="DEMO_ADMIN")
        if initial_seed:
            _audit(connection, "demo_seed_completed", {"patients": 10, "historical_encounters": 20}, actor_id="DEMO_ADMIN")
        return {
            "patients": connection.execute("SELECT COUNT(*) FROM demo_patients").fetchone()[0],
            "professional_users": connection.execute("SELECT COUNT(*) FROM demo_users WHERE id!='DEMO_PATIENT'").fetchone()[0],
            "institutions": connection.execute("SELECT COUNT(*) FROM demo_institutions").fetchone()[0],
            "encounters": connection.execute("SELECT COUNT(*) FROM demo_encounters").fetchone()[0],
        }


def reset_demo_data(db_path: Path | str | None = None) -> dict[str, int]:
    migrate_demo_schema(db_path)
    with connect(db_path) as connection:
        for table in (
            "demo_field_confirmations", "demo_field_extractions", "demo_conversation_turns",
            "demo_transcriptions", "demo_audio_segments", "demo_audio_sessions", "demo_sessions",
            "demo_login_events", "demo_password_credentials", "demo_patient_access", "demo_workflow_requirements",
            "demo_requested_considerations", "demo_clinical_notes", "demo_model_runs", "demo_rag_retrievals",
            "demo_triage_assessments", "demo_vital_signs", "demo_audit_events", "demo_encounters",
            "demo_patient_medications", "demo_patient_allergies", "demo_medications", "demo_allergies",
            "demo_patients", "demo_user_roles", "demo_users", "demo_roles", "demo_facilities", "demo_institutions",
        ):
            connection.execute(f"DELETE FROM {table}")
    return seed_demo_data(db_path)


def demo_profiles(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """SELECT u.id,u.display_name,r.id AS role FROM demo_users u
               JOIN demo_user_roles ur ON ur.user_id=u.id JOIN demo_roles r ON r.id=ur.role_id
               ORDER BY u.id"""
        ).fetchall()
    return [dict(row) for row in rows]


def patient_by_identifier(identifier: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        patient = connection.execute("SELECT * FROM demo_patients WHERE synthetic_identifier=?", (identifier,)).fetchone()
        if not patient:
            return None
        allergies = connection.execute(
            """SELECT a.name FROM demo_allergies a JOIN demo_patient_allergies pa ON pa.allergy_id=a.id
               WHERE pa.patient_id=?""", (patient["id"],),
        ).fetchall()
        medications = connection.execute(
            """SELECT m.name FROM demo_medications m JOIN demo_patient_medications pm ON pm.medication_id=m.id
               WHERE pm.patient_id=?""", (patient["id"],),
        ).fetchall()
        previous = connection.execute(
            "SELECT id,status,chief_complaint,created_at FROM demo_encounters WHERE patient_id=? ORDER BY created_at DESC LIMIT 5",
            (patient["id"],),
        ).fetchall()
    result = dict(patient)
    result["allergies"] = [row["name"] for row in allergies]
    result["medications"] = [row["name"] for row in medications]
    result["previous_encounters"] = [dict(row) for row in previous]
    return result


def patient_by_id(patient_id: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        row = connection.execute("SELECT synthetic_identifier FROM demo_patients WHERE id=?", (patient_id,)).fetchone()
    return patient_by_identifier(row["synthetic_identifier"], db_path) if row else None


def patient_tracking(patient_id: str, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """SELECT id,status,chief_complaint,created_at,updated_at FROM demo_encounters
               WHERE patient_id=? AND source!='seed_demo' ORDER BY created_at DESC LIMIT 10""",
            (patient_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_attention_selection(
    encounter_id: int, actor_id: str, role: str, db_path: Path | str | None = None
) -> None:
    with connect(db_path) as connection:
        _audit(connection, "attention_selected", {"role": role}, encounter_id=encounter_id, actor_id=actor_id)


def validate_patient_payload(payload: dict[str, Any]) -> None:
    if not payload.get("consent_demo"):
        raise ValueError("Debe aceptar el consentimiento demostrativo.")
    if not str(payload.get("chief_complaint", "")).strip() or not str(payload.get("narrative", "")).strip():
        raise ValueError("El motivo y el relato son obligatorios.")
    if payload.get("pain_present") and payload.get("pain_score") is None:
        raise ValueError("La escala de dolor 0–10 es obligatoria cuando existe dolor.")
    score = payload.get("pain_score")
    if score is not None and not 0 <= int(score) <= 10:
        raise ValueError("La escala de dolor debe estar entre 0 y 10.")


def create_patient_encounter(payload: dict[str, Any], actor_id: str = "DEMO_PATIENT", db_path: Path | str | None = None) -> int:
    validate_patient_payload(payload)
    patient = patient_by_identifier(str(payload["identifier"]), db_path)
    if not patient:
        raise ValueError("Identificador sintético no encontrado.")
    now = utc_now()
    with connect(db_path) as connection:
        cursor = connection.execute(
            """INSERT INTO demo_encounters(patient_id,facility_id,status,chief_complaint,narrative,duration,
               pain_present,pain_score,pain_location,onset,evolution,accompanying_symptoms_json,consent_demo,
               mobility,companion,pregnancy_possible,source,created_by,updated_by,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                patient["id"], patient["facility_id"], "AWAITING_TRIAGE", payload["chief_complaint"].strip(),
                payload["narrative"].strip(), payload.get("duration", ""), int(bool(payload.get("pain_present"))),
                payload.get("pain_score"), payload.get("pain_location", ""), payload.get("onset", ""),
                payload.get("evolution", ""), json.dumps(payload.get("accompanying_symptoms", []), ensure_ascii=False),
                1, payload.get("mobility", ""), payload.get("companion", ""), payload.get("pregnancy_possible", "no aplica"),
                "patient_demo_portal", actor_id, actor_id, now, now,
            ),
        )
        encounter_id = int(cursor.lastrowid)
        _audit(connection, "patient_submission", {"status": "AWAITING_TRIAGE"}, encounter_id=encounter_id, actor_id=actor_id)
    return encounter_id


def triage_queue(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """SELECT e.id,e.status,e.chief_complaint,e.created_at,p.display_name,p.synthetic_identifier,p.age,
                      CAST((julianday('now')-julianday(e.created_at))*1440 AS INTEGER) AS wait_minutes
               FROM demo_encounters e JOIN demo_patients p ON p.id=e.patient_id
               WHERE e.status IN ('AWAITING_TRIAGE','AWAITING_PHYSICIAN') ORDER BY e.created_at"""
        ).fetchall()
    return [dict(row) for row in rows]


def encounter_context(encounter_id: int, db_path: Path | str | None = None) -> dict[str, Any] | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """SELECT e.*,p.synthetic_identifier,p.display_name,p.age,p.registered_sex,p.insurer,f.name AS facility_name,
                      f.triage_role FROM demo_encounters e JOIN demo_patients p ON p.id=e.patient_id
                      JOIN demo_facilities f ON f.id=e.facility_id WHERE e.id=?""", (encounter_id,),
        ).fetchone()
        if not row:
            return None
        patient = patient_by_identifier(row["synthetic_identifier"], db_path)
        vitals = connection.execute("SELECT * FROM demo_vital_signs WHERE encounter_id=? ORDER BY id DESC LIMIT 1", (encounter_id,)).fetchone()
        triage = connection.execute("SELECT * FROM demo_triage_assessments WHERE encounter_id=? ORDER BY id DESC LIMIT 1", (encounter_id,)).fetchone()
        retrievals = connection.execute("SELECT * FROM demo_rag_retrievals WHERE encounter_id=? ORDER BY id", (encounter_id,)).fetchall()
        models = connection.execute("SELECT * FROM demo_model_runs WHERE encounter_id=? ORDER BY id DESC LIMIT 1", (encounter_id,)).fetchone()
    result = dict(row)
    result["patient"] = patient
    result["vitals"] = dict(vitals) if vitals else None
    result["triage"] = dict(triage) if triage else None
    result["retrievals"] = [dict(item) for item in retrievals]
    result["model_run"] = dict(models) if models else None
    return result


def save_triage(
    encounter_id: int, vitals: dict[str, Any], assessment: dict[str, Any], actor_id: str,
    db_path: Path | str | None = None,
) -> None:
    now = utc_now()
    with connect(db_path) as connection:
        connection.execute(
            """INSERT INTO demo_vital_signs(encounter_id,systolic,diastolic,heart_rate,respiratory_rate,
               temperature,oxygen_saturation,glucose,consciousness_scale,weight,height,pain_score,population,
               source,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                encounter_id, vitals.get("systolic"), vitals.get("diastolic"), vitals.get("heart_rate"),
                vitals.get("respiratory_rate"), vitals.get("temperature"), vitals.get("oxygen_saturation"),
                vitals.get("glucose"), vitals.get("consciousness_scale"), vitals.get("weight"), vitals.get("height"),
                vitals.get("pain_score"), vitals.get("population", "adult"), "professional_demo", actor_id, now,
            ),
        )
        connection.execute(
            """INSERT INTO demo_triage_assessments(encounter_id,proposed_level,confirmed_level,decision,justification,
               reevaluation_requested,scale_name,source,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                encounter_id, assessment["proposed_level"], assessment.get("confirmed_level"), assessment["decision"],
                assessment.get("justification", ""), int(bool(assessment.get("reevaluation_requested"))),
                assessment.get("scale_name", "Sistema de prioridad de cinco niveles configurable"), "professional_demo", actor_id, now,
            ),
        )
        connection.execute("UPDATE demo_encounters SET status='AWAITING_PHYSICIAN',updated_by=?,updated_at=? WHERE id=?", (actor_id, now, encounter_id))
        _audit(connection, "triage_recorded", assessment, encounter_id=encounter_id, actor_id=actor_id)
    from longitudinal_db import mirror_triage
    mirror_triage(encounter_id, vitals, assessment, actor_id, db_path)


def save_rag_and_model_run(
    encounter_id: int, retrievals: list[dict[str, Any]], run: dict[str, Any], db_path: Path | str | None = None,
) -> None:
    now = utc_now()
    with connect(db_path) as connection:
        connection.execute("DELETE FROM demo_rag_retrievals WHERE encounter_id=?", (encounter_id,))
        for item in retrievals:
            connection.execute(
                """INSERT INTO demo_rag_retrievals(encounter_id,source_id,chunk_id,score,retrieval_reason,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (encounter_id, item["source_id"], item["chunk_id"], item["score"], item["retrieval_reason"], now),
            )
        connection.execute(
            """INSERT INTO demo_model_runs(encounter_id,provider,model_name,state,model_used,fallback_reason,
               duration_seconds,validated,result_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                encounter_id, run["provider"], run["model_name"], run["state"], int(run["model_used"]),
                run.get("fallback_reason"), run.get("duration_seconds"), int(run.get("validated", False)),
                json.dumps(run.get("result", {}), ensure_ascii=False), now,
            ),
        )
        _audit(connection, "rag_model_completed", {"sources": [item["source_id"] for item in retrievals], "state": run["state"]}, encounter_id=encounter_id)


def audit_feed(limit: int = 100, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        rows = connection.execute("SELECT * FROM demo_audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def save_clinical_note(
    encounter_id: int, note: str, actor_id: str, section: str = "medical_review",
    db_path: Path | str | None = None,
) -> None:
    if not note.strip():
        raise ValueError("La nota profesional no puede estar vacía.")
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO demo_clinical_notes(encounter_id,section,note,source,created_by,created_at) VALUES(?,?,?,?,?,?)",
            (encounter_id, section, note.strip(), "professional_demo", actor_id, utc_now()),
        )
        _audit(connection, "clinical_note_recorded", {"section": section}, encounter_id=encounter_id, actor_id=actor_id)


def documentary_closure_status(encounter_id: int, db_path: Path | str | None = None) -> tuple[list[str], bool]:
    with connect(db_path) as connection:
        checks = {
            "Signos vitales documentados": connection.execute("SELECT 1 FROM demo_vital_signs WHERE encounter_id=?", (encounter_id,)).fetchone(),
            "Decisión de triaje registrada": connection.execute("SELECT 1 FROM demo_triage_assessments WHERE encounter_id=?", (encounter_id,)).fetchone(),
            "Nota profesional registrada": connection.execute("SELECT 1 FROM demo_clinical_notes WHERE encounter_id=?", (encounter_id,)).fetchone(),
        }
    missing = [label for label, present in checks.items() if not present]
    return missing, not missing


def close_demo_encounter(encounter_id: int, actor_id: str, db_path: Path | str | None = None) -> tuple[bool, str]:
    missing, permitted = documentary_closure_status(encounter_id, db_path)
    with connect(db_path) as connection:
        if permitted:
            connection.execute(
                "UPDATE demo_encounters SET status='CLOSED',updated_by=?,updated_at=? WHERE id=?",
                (actor_id, utc_now(), encounter_id),
            )
            reason = "Cierre documental registrado."
        else:
            reason = "Faltan campos institucionales: " + ", ".join(missing)
        _audit(connection, "documentary_closure_attempt", {"permitted": permitted, "reason": reason}, encounter_id=encounter_id, actor_id=actor_id)
    return permitted, reason


def demo_statistics(db_path: Path | str | None = None) -> dict[str, int]:
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        return {
            "patients": connection.execute("SELECT COUNT(*) FROM demo_patients").fetchone()[0],
            "users": connection.execute("SELECT COUNT(*) FROM demo_users").fetchone()[0],
            "encounters": connection.execute("SELECT COUNT(*) FROM demo_encounters").fetchone()[0],
            "awaiting_triage": connection.execute("SELECT COUNT(*) FROM demo_encounters WHERE status='AWAITING_TRIAGE'").fetchone()[0],
            "awaiting_physician": connection.execute("SELECT COUNT(*) FROM demo_encounters WHERE status='AWAITING_PHYSICIAN'").fetchone()[0],
            "audit_events": connection.execute("SELECT COUNT(*) FROM demo_audit_events").fetchone()[0],
        }

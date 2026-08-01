from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from clinical_db import connect, seed_demo_data, utc_now


INSURANCE_TYPES = ("SIS", "EsSalud", "Privado", "Otro")
REGISTERED_SEX_VALUES = ("Femenino", "Masculino", "Intersexual", "No especificado")


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _add_column(connection: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def migrate_longitudinal_schema(db_path: Path | str | None = None) -> None:
    """Create the final relational layer without invalidating legacy demonstration data."""
    seed_demo_data(db_path)
    with connect(db_path) as connection:
        # `patients` belongs to the first MVP schema. Extend it in place so old flows remain valid.
        connection.execute(
            """CREATE TABLE IF NOT EXISTS patients(
                dni TEXT PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL CHECK(age >= 0),
                sex TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 1
            )"""
        )
        for definition in (
            "given_names TEXT", "family_names TEXT", "birth_date TEXT", "phone TEXT",
            "email TEXT", "address TEXT", "emergency_contact TEXT", "insurance_type TEXT",
            "facility_id TEXT", "consent_at TEXT", "created_at TEXT", "updated_at TEXT",
        ):
            _add_column(connection, "patients", definition)
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS patient_identifiers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                identifier_type TEXT NOT NULL,
                identifier_value TEXT NOT NULL UNIQUE,
                synthetic INTEGER NOT NULL CHECK(synthetic=1),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS roles(
                id TEXT PRIMARY KEY, label TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS institutions(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, institution_type TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS facilities(
                id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id),
                name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY, username TEXT UNIQUE, display_name TEXT NOT NULL,
                password_hash TEXT, active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_roles(
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id TEXT NOT NULL REFERENCES roles(id),
                facility_id TEXT REFERENCES facilities(id),
                PRIMARY KEY(user_id,role_id,facility_id)
            );
            CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                role_id TEXT NOT NULL REFERENCES roles(id), facility_id TEXT REFERENCES facilities(id),
                started_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS encounters(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni),
                facility_id TEXT REFERENCES facilities(id), legacy_encounter_id INTEGER UNIQUE,
                status TEXT NOT NULL, chief_complaint TEXT NOT NULL, narrative TEXT NOT NULL,
                started_at TEXT NOT NULL, ended_at TEXT, created_by TEXT, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS symptoms(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                name TEXT NOT NULL, onset TEXT, duration TEXT, evolution TEXT, location TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pain_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                present INTEGER, score INTEGER CHECK(score BETWEEN 0 AND 10), location TEXT,
                source TEXT NOT NULL, confirmed_by TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vital_signs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
                systolic INTEGER, diastolic INTEGER, heart_rate INTEGER, respiratory_rate INTEGER,
                temperature REAL, oxygen_saturation INTEGER, glucose INTEGER, consciousness TEXT,
                weight REAL, height REAL, pain_score INTEGER CHECK(pain_score BETWEEN 0 AND 10),
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS allergies(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                substance TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL,
                confirmed_by TEXT, confirmed_at TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS medications(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                name TEXT NOT NULL, dose TEXT, frequency TEXT, status TEXT NOT NULL,
                source TEXT NOT NULL, confirmed_by TEXT, confirmed_at TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS prescriptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni),
                encounter_id INTEGER REFERENCES encounters(id), medication_name TEXT NOT NULL,
                instructions TEXT, prescribed_by TEXT NOT NULL, prescribed_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS diagnoses(
                id INTEGER PRIMARY KEY AUTOINCREMENT, patient_dni TEXT NOT NULL REFERENCES patients(dni),
                encounter_id INTEGER REFERENCES encounters(id), description TEXT NOT NULL, code TEXT,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS procedures(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                description TEXT NOT NULL, recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS laboratory_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                test_name TEXT NOT NULL, result TEXT NOT NULL, unit TEXT, reference_text TEXT,
                recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS imaging_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                study_name TEXT NOT NULL, result TEXT NOT NULL, recorded_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clinical_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                section TEXT NOT NULL, note TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 1,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS triage_assessments(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER NOT NULL REFERENCES encounters(id),
                proposed_level INTEGER CHECK(proposed_level BETWEEN 1 AND 5),
                confirmed_level INTEGER CHECK(confirmed_level BETWEEN 1 AND 5),
                scale_name TEXT NOT NULL, decision TEXT NOT NULL, justification TEXT,
                reevaluation_requested INTEGER NOT NULL DEFAULT 0,
                recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversation_turns(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT NOT NULL REFERENCES patients(dni), turn_no INTEGER NOT NULL,
                speaker TEXT NOT NULL, question TEXT, response TEXT, resolution_reason TEXT,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS field_extractions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT NOT NULL REFERENCES patients(dni), field_name TEXT NOT NULL,
                value_json TEXT, source TEXT NOT NULL, confidence_status TEXT NOT NULL,
                requires_confirmation INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS field_confirmations(
                id INTEGER PRIMARY KEY AUTOINCREMENT, extraction_id INTEGER NOT NULL REFERENCES field_extractions(id) ON DELETE CASCADE,
                value_json TEXT, status TEXT NOT NULL, reason TEXT, confirmed_by TEXT NOT NULL, confirmed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                stage TEXT NOT NULL, provider TEXT NOT NULL, model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL, validated INTEGER NOT NULL, duration_seconds REAL,
                result_json TEXT, error_detail TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rag_retrievals(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                source_id TEXT NOT NULL, institution TEXT NOT NULL, year TEXT NOT NULL, population TEXT NOT NULL,
                url TEXT NOT NULL, fragment TEXT NOT NULL, limitations TEXT NOT NULL,
                score REAL NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, encounter_id INTEGER REFERENCES encounters(id),
                patient_dni TEXT REFERENCES patients(dni), event_type TEXT NOT NULL,
                actor_id TEXT, details_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_patient_identifiers_value ON patient_identifiers(identifier_value);
            CREATE INDEX IF NOT EXISTS idx_encounters_patient_date ON encounters(patient_dni,started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_vitals_encounter_date ON vital_signs(encounter_id,recorded_at DESC);
            CREATE INDEX IF NOT EXISTS idx_diagnoses_patient_date ON diagnoses(patient_dni,recorded_at DESC);
            CREATE INDEX IF NOT EXISTS idx_prescriptions_patient_date ON prescriptions(patient_dni,prescribed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_patient_date ON audit_events(patient_dni,created_at DESC);
            """
        )
        now = utc_now()
        for role in ("PATIENT", "TRIAGE_NURSE", "TRIAGE_DOCTOR", "ATTENDING_PHYSICIAN", "SUPERVISOR", "ADMIN"):
            connection.execute("INSERT OR IGNORE INTO roles VALUES(?,?,?)", (role, role.replace("_", " ").title(), now))
        connection.execute("INSERT OR IGNORE INTO institutions VALUES('KUTAN_HEALTH','Red clínica sintética Kutan','validation',?,?)", (now, now))
        for facility_id, name in (("DEMO_FAC_A", "Centro Andino"), ("DEMO_FAC_B", "Policlínico Costa")):
            connection.execute("INSERT OR IGNORE INTO facilities VALUES(?,?,?,1,?,?)", (facility_id, "KUTAN_HEALTH", name, now, now))
        connection.execute(
            "INSERT OR IGNORE INTO patients(dni,name,age,sex,is_demo) VALUES('76543210','Ana Torres',27,'Femenino',1)"
        )
        for dni, name, age, sex, birth_date, facility_id in (
            ("87654321", "Paciente 02", 30, "Masculino", "1990-02-02", "DEMO_FAC_B"),
            ("11223344", "Paciente 03", 34, "Femenino", "1985-03-03", "DEMO_FAC_A"),
        ):
            connection.execute("INSERT OR IGNORE INTO patients(dni,name,age,sex,is_demo) VALUES(?,?,?,?,1)", (dni, name, age, sex))
            connection.execute("UPDATE patients SET birth_date=COALESCE(birth_date,?), insurance_type=COALESCE(insurance_type,'Otro'), facility_id=COALESCE(facility_id,?), consent_at=COALESCE(consent_at,?), created_at=COALESCE(created_at,?), updated_at=COALESCE(updated_at,?) WHERE dni=?", (birth_date, facility_id, now, now, now, dni))
            connection.execute("INSERT OR IGNORE INTO patient_identifiers(patient_dni,identifier_type,identifier_value,synthetic,created_at) VALUES(?,?,?,1,?)", (dni, "DNI", dni, now))
        connection.execute(
            """UPDATE patients SET given_names=COALESCE(given_names,'Ana'), family_names=COALESCE(family_names,'Torres'),
               birth_date=COALESCE(birth_date,'1999-01-01'), insurance_type=COALESCE(insurance_type,'SIS'),
               facility_id=COALESCE(facility_id,'DEMO_FAC_A'), consent_at=COALESCE(consent_at,?),
               created_at=COALESCE(created_at,?), updated_at=COALESCE(updated_at,?) WHERE dni='76543210'""",
            (now, now, now),
        )
        connection.execute(
            "INSERT OR IGNORE INTO patient_identifiers(patient_dni,identifier_type,identifier_value,synthetic,created_at) VALUES('76543210','DNI','76543210',1,?)",
            (now,),
        )
        _seed_longitudinal_history(connection, now)


def _seed_longitudinal_history(connection: sqlite3.Connection, now: str) -> None:
    if connection.execute("SELECT 1 FROM encounters WHERE patient_dni='76543210'").fetchone():
        return
    for month, complaint, facility in (("2026-02-10", "Control general", "DEMO_FAC_A"), ("2026-05-15", "Seguimiento ambulatorio", "DEMO_FAC_B")):
        cursor = connection.execute(
            "INSERT INTO encounters(patient_dni,facility_id,status,chief_complaint,narrative,started_at,ended_at,created_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("76543210", facility, "CLOSED", complaint, "Registro clínico sintético confirmado.", month + "T10:00:00+00:00", month + "T11:00:00+00:00", "DEMO_ATTENDING_1", now),
        )
        encounter_id = int(cursor.lastrowid)
        connection.execute("INSERT INTO diagnoses(patient_dni,encounter_id,description,code,recorded_by,recorded_at,status) VALUES(?,?,?,?,?,?,?)", ("76543210", encounter_id, "Diagnóstico registrado por profesional", None, "DEMO_ATTENDING_1", month + "T10:40:00+00:00", "confirmed"))
        connection.execute("INSERT INTO prescriptions(patient_dni,encounter_id,medication_name,instructions,prescribed_by,prescribed_at,status) VALUES(?,?,?,?,?,?,?)", ("76543210", encounter_id, "Medicamento registrado", "Según registro profesional", "DEMO_ATTENDING_1", month + "T10:45:00+00:00", "completed"))
        connection.execute("INSERT INTO vital_signs(encounter_id,systolic,diastolic,heart_rate,respiratory_rate,temperature,oxygen_saturation,glucose,consciousness,weight,height,pain_score,recorded_by,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (encounter_id, 118, 76, 74, 17, 36.6, 98, None, "Alerta", 64.0, 1.64, 2, "DEMO_NURSE_1", month + "T10:15:00+00:00"))


def validate_registration(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {key: str(value).strip() if value is not None else "" for key, value in payload.items()}
    if not re.fullmatch(r"\d{8}", cleaned.get("dni", "")):
        raise ValueError("El DNI sintético debe contener exactamente 8 dígitos.")
    for field, label in (("given_names", "nombres"), ("family_names", "apellidos"), ("birth_date", "fecha de nacimiento"), ("registered_sex", "sexo registrado"), ("phone", "teléfono"), ("emergency_contact", "contacto de emergencia"), ("insurance_type", "aseguramiento"), ("facility_id", "establecimiento")):
        if not cleaned.get(field):
            raise ValueError(f"El campo {label} es obligatorio.")
    try:
        born = date.fromisoformat(cleaned["birth_date"])
    except ValueError as exc:
        raise ValueError("La fecha de nacimiento no es válida.") from exc
    if born >= date.today() or born.year < 1900:
        raise ValueError("La fecha de nacimiento debe ser anterior a hoy.")
    if cleaned["registered_sex"] not in REGISTERED_SEX_VALUES:
        raise ValueError("El sexo registrado no pertenece al catálogo permitido.")
    if cleaned["insurance_type"] not in INSURANCE_TYPES:
        raise ValueError("El aseguramiento no pertenece al catálogo permitido.")
    if not re.fullmatch(r"[+\d][\d\s-]{6,19}", cleaned["phone"]):
        raise ValueError("El teléfono no tiene un formato válido.")
    if cleaned.get("email") and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned["email"]):
        raise ValueError("El correo no tiene un formato válido.")
    if payload.get("consent") is not True:
        raise ValueError("Debe confirmar el consentimiento para crear el registro.")
    cleaned["consent"] = True
    cleaned["age"] = date.today().year - born.year - ((date.today().month, date.today().day) < (born.month, born.day))
    return cleaned


def register_patient(payload: dict[str, Any], db_path: Path | str | None = None) -> dict[str, Any]:
    migrate_longitudinal_schema(db_path)
    data = validate_registration(payload)
    now = utc_now()
    patient_id = "PAT_" + hashlib.sha256(data["dni"].encode()).hexdigest()[:12].upper()
    user_id = "USR_" + hashlib.sha256((data["dni"] + "patient").encode()).hexdigest()[:12].upper()
    with connect(db_path) as connection:
        if connection.execute("SELECT 1 FROM patient_identifiers WHERE identifier_value=?", (data["dni"],)).fetchone():
            raise ValueError("El DNI sintético ya está registrado.")
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO patients(dni,name,age,sex,is_demo,given_names,family_names,birth_date,phone,email,address,
                   emergency_contact,insurance_type,facility_id,consent_at,created_at,updated_at)
                   VALUES(?,?,?,?,1,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (data["dni"], f"{data['given_names']} {data['family_names']}", data["age"], data["registered_sex"], data["given_names"], data["family_names"], data["birth_date"], data["phone"], data.get("email") or None, data.get("address") or None, data["emergency_contact"], data["insurance_type"], data["facility_id"], now, now, now),
            )
            connection.execute("INSERT INTO patient_identifiers(patient_dni,identifier_type,identifier_value,synthetic,created_at) VALUES(?,?,?,?,?)", (data["dni"], "DNI", data["dni"], 1, now))
            connection.execute("INSERT INTO users(id,username,display_name,active,created_at,updated_at) VALUES(?,?,?,1,?,?)", (user_id, None, f"{data['given_names']} {data['family_names']}", now, now))
            connection.execute("INSERT INTO user_roles VALUES(?,?,?)", (user_id, "PATIENT", data["facility_id"]))
            # Compatibility shadow used by the existing authenticated UI.
            connection.execute("INSERT INTO demo_users VALUES(?,?,1,'active',?,?)", (user_id, f"{data['given_names']} {data['family_names']}", now, now))
            connection.execute("INSERT INTO demo_user_roles VALUES(?,?)", (user_id, "PATIENT"))
            connection.execute("INSERT INTO demo_patients VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (patient_id, data["dni"], f"{data['given_names']} {data['family_names']}", data["age"], data["registered_sex"], data["insurance_type"], data["facility_id"], "patient_registration", "active", user_id, user_id, now, now))
            connection.execute("INSERT INTO demo_patient_access VALUES(?,?,?,?)", (user_id, patient_id, data["birth_date"], now))
            for value in _split_list(payload.get("allergies")):
                connection.execute("INSERT INTO allergies(patient_dni,substance,status,source,confirmed_by,confirmed_at,created_at) VALUES(?,?,?,?,?,?,?)", (data["dni"], value, "active", "patient_registration", user_id, now, now))
            for value in _split_list(payload.get("medications")):
                connection.execute("INSERT INTO medications(patient_dni,name,status,source,confirmed_by,confirmed_at,created_at) VALUES(?,?,?,?,?,?,?)", (data["dni"], value, "active", "patient_registration", user_id, now, now))
            if str(payload.get("history", "")).strip():
                connection.execute("INSERT INTO audit_events(patient_dni,event_type,actor_id,details_json,created_at) VALUES(?,?,?,?,?)", (data["dni"], "history_registered", user_id, json.dumps({"confirmed_note": str(payload["history"]).strip()}, ensure_ascii=False), now))
            connection.execute("INSERT INTO audit_events(patient_dni,event_type,actor_id,details_json,created_at) VALUES(?,?,?,?,?)", (data["dni"], "patient_registered", user_id, json.dumps({"synthetic": True, "facility_id": data["facility_id"]}), now))
        except sqlite3.IntegrityError as exc:
            raise ValueError("No se pudo crear el registro; revise que el DNI no esté duplicado.") from exc
    return patient_summary(data["dni"], db_path) or {}


def _split_list(value: Any) -> list[str]:
    return [item.strip() for item in re.split(r"[,;\n]", str(value or "")) if item.strip()]


def patient_summary(dni: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    migrate_longitudinal_schema(db_path)
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM patients WHERE dni=?", (dni.strip(),)).fetchone()
    return dict(row) if row else None


def patient_longitudinal_record(dni: str, db_path: Path | str | None = None, facility_id: str | None = None, date_from: str | None = None, date_to: str | None = None) -> dict[str, Any]:
    migrate_longitudinal_schema(db_path)
    clauses, params = ["e.patient_dni=?"], [dni]
    if facility_id:
        clauses.append("e.facility_id=?"); params.append(facility_id)
    if date_from:
        clauses.append("date(e.started_at)>=date(?)"); params.append(date_from)
    if date_to:
        clauses.append("date(e.started_at)<=date(?)"); params.append(date_to)
    with connect(db_path) as connection:
        encounters = [dict(row) for row in connection.execute(f"SELECT e.*,f.name facility_name FROM encounters e LEFT JOIN facilities f ON f.id=e.facility_id WHERE {' AND '.join(clauses)} ORDER BY e.started_at DESC", params)]
        diagnoses = [dict(row) for row in connection.execute("SELECT * FROM diagnoses WHERE patient_dni=? ORDER BY recorded_at DESC", (dni,))]
        prescriptions = [dict(row) for row in connection.execute("SELECT * FROM prescriptions WHERE patient_dni=? ORDER BY prescribed_at DESC", (dni,))]
        allergies = [dict(row) for row in connection.execute("SELECT * FROM allergies WHERE patient_dni=? ORDER BY created_at DESC", (dni,))]
        medications = [dict(row) for row in connection.execute("SELECT * FROM medications WHERE patient_dni=? ORDER BY created_at DESC", (dni,))]
        vitals = [dict(row) for row in connection.execute("SELECT v.*,e.started_at,e.facility_id FROM vital_signs v JOIN encounters e ON e.id=v.encounter_id WHERE e.patient_dni=? ORDER BY v.recorded_at", (dni,))]
    return {"encounters": encounters, "diagnoses": diagnoses, "prescriptions": prescriptions, "allergies": allergies, "medications": medications, "vitals": vitals}


def descriptive_statistics(dni: str, db_path: Path | str | None = None) -> dict[str, list[dict[str, Any]]]:
    record = patient_longitudinal_record(dni, db_path)
    monthly: dict[str, int] = {}
    complaints: dict[str, int] = {}
    facilities: dict[str, int] = {}
    for item in record["encounters"]:
        month = item["started_at"][:7]
        monthly[month] = monthly.get(month, 0) + 1
        complaints[item["chief_complaint"]] = complaints.get(item["chief_complaint"], 0) + 1
        facility = item.get("facility_name") or item.get("facility_id") or "Sin establecimiento"
        facilities[facility] = facilities.get(facility, 0) + 1
    return {
        "monthly": [{"mes": key, "atenciones": value} for key, value in sorted(monthly.items())],
        "complaints": [{"motivo": key, "atenciones": value} for key, value in sorted(complaints.items(), key=lambda item: -item[1])],
        "facilities": [{"establecimiento": key, "atenciones": value} for key, value in facilities.items()],
        "vitals": record["vitals"],
    }


def mirror_intake_encounter(
    legacy_encounter_id: int, dni: str, facility_id: str, extraction: Any,
    narrative: str, actor_id: str, verification: dict[str, Any],
    resolutions: dict[str, str] | None = None, db_path: Path | str | None = None,
) -> int:
    """Persist confirmed longitudinal memory after the patient explicitly submits intake."""
    migrate_longitudinal_schema(db_path)
    now = utc_now()
    resolutions = resolutions or {}
    with connect(db_path) as connection:
        existing = connection.execute("SELECT id FROM encounters WHERE legacy_encounter_id=?", (legacy_encounter_id,)).fetchone()
        if existing:
            return int(existing["id"])
        cursor = connection.execute(
            """INSERT INTO encounters(patient_dni,facility_id,legacy_encounter_id,status,chief_complaint,narrative,
               started_at,created_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (dni, facility_id, legacy_encounter_id, "AWAITING_TRIAGE", str(extraction.chief_complaint.value or narrative)[:240], narrative, now, actor_id, now),
        )
        encounter_id = int(cursor.lastrowid)
        connection.execute(
            """INSERT INTO symptoms(encounter_id,name,onset,duration,evolution,location,source,confirmed_by,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (encounter_id, str(extraction.chief_complaint.value or narrative)[:240], extraction.onset.value, extraction.duration.value, extraction.evolution.value, extraction.location.value, extraction.chief_complaint.source, actor_id, now),
        )
        connection.execute(
            "INSERT INTO pain_assessments(encounter_id,present,score,location,source,confirmed_by,created_at) VALUES(?,?,?,?,?,?,?)",
            (encounter_id, int(bool(extraction.pain_present.value)) if extraction.pain_present.value is not None else None, extraction.pain_score.value, extraction.location.value, extraction.pain_present.source, actor_id, now),
        )
        for field_name in extraction.model_fields:
            if field_name == "missing_fields":
                continue
            field = getattr(extraction, field_name)
            value = field.value
            extraction_cursor = connection.execute(
                """INSERT INTO field_extractions(encounter_id,patient_dni,field_name,value_json,source,confidence_status,
                   requires_confirmation,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (encounter_id, dni, field_name, json.dumps(value, ensure_ascii=False) if value is not None else None, field.source, field.confidence_status, int(field.requires_confirmation), now),
            )
            if not field.requires_confirmation or field_name in resolutions:
                status = "confirmed" if value is not None else "null_with_reason"
                connection.execute(
                    "INSERT INTO field_confirmations(extraction_id,value_json,status,reason,confirmed_by,confirmed_at) VALUES(?,?,?,?,?,?)",
                    (int(extraction_cursor.lastrowid), json.dumps(value, ensure_ascii=False) if value is not None else None, status, resolutions.get(field_name), actor_id, now),
                )
        connection.execute(
            """INSERT INTO model_runs(encounter_id,stage,provider,model_name,model_used,validated,duration_seconds,
               result_json,error_detail,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (encounter_id, "verification", "ollama" if verification.get("verification_model") != "deterministic-rules-v1" else "deterministic", verification.get("verification_model", "unknown"), int(verification.get("verification_model") != "deterministic-rules-v1"), int(bool(verification.get("validated"))), verification.get("duration_seconds"), json.dumps(verification, ensure_ascii=False), verification.get("error_detail"), now),
        )
        connection.execute(
            "INSERT INTO audit_events(encounter_id,patient_dni,event_type,actor_id,details_json,created_at) VALUES(?,?,?,?,?,?)",
            (encounter_id, dni, "intake_submitted", actor_id, json.dumps({"legacy_encounter_id": legacy_encounter_id, "verification": verification.get("verification_model")}, ensure_ascii=False), now),
        )
    return encounter_id


def mirror_triage(
    legacy_encounter_id: int, vitals: dict[str, Any], assessment: dict[str, Any], actor_id: str,
    db_path: Path | str | None = None,
) -> None:
    migrate_longitudinal_schema(db_path)
    now = utc_now()
    with connect(db_path) as connection:
        encounter = connection.execute("SELECT id FROM encounters WHERE legacy_encounter_id=?", (legacy_encounter_id,)).fetchone()
        if not encounter:
            return
        encounter_id = int(encounter["id"])
        connection.execute(
            """INSERT INTO vital_signs(encounter_id,systolic,diastolic,heart_rate,respiratory_rate,temperature,
               oxygen_saturation,glucose,consciousness,weight,height,pain_score,recorded_by,recorded_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (encounter_id, vitals.get("systolic"), vitals.get("diastolic"), vitals.get("heart_rate"), vitals.get("respiratory_rate"), vitals.get("temperature"), vitals.get("oxygen_saturation"), vitals.get("glucose"), vitals.get("consciousness_scale"), vitals.get("weight"), vitals.get("height"), vitals.get("pain_score"), actor_id, now),
        )
        proposed = int(str(assessment.get("proposed_level", "5")).replace("Nivel ", "").split()[0])
        confirmed = int(str(assessment.get("confirmed_level", "5")).replace("Nivel ", "").split()[0])
        connection.execute(
            """INSERT INTO triage_assessments(encounter_id,proposed_level,confirmed_level,scale_name,decision,
               justification,reevaluation_requested,recorded_by,recorded_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (encounter_id, proposed, confirmed, assessment.get("scale_name", "Prioridad configurable de cinco niveles"), assessment["decision"], assessment.get("justification"), int(bool(assessment.get("reevaluation_requested"))), actor_id, now),
        )
        connection.execute("UPDATE encounters SET status='AWAITING_PHYSICIAN',updated_at=? WHERE id=?", (now, encounter_id))
        connection.execute("INSERT INTO audit_events(encounter_id,event_type,actor_id,details_json,created_at) VALUES(?,?,?,?,?)", (encounter_id, "triage_recorded", actor_id, json.dumps(assessment, ensure_ascii=False), now))


def record_professional_entry(
    legacy_encounter_id: int, actor_id: str, *, note: str, diagnosis: str = "",
    medication: str = "", instructions: str = "", db_path: Path | str | None = None,
) -> None:
    migrate_longitudinal_schema(db_path)
    now = utc_now()
    with connect(db_path) as connection:
        encounter = connection.execute("SELECT id,patient_dni FROM encounters WHERE legacy_encounter_id=?", (legacy_encounter_id,)).fetchone()
        if not encounter:
            return
        encounter_id, dni = int(encounter["id"]), encounter["patient_dni"]
        connection.execute("INSERT INTO clinical_notes(encounter_id,section,note,confirmed,recorded_by,recorded_at) VALUES(?,?,?,?,?,?)", (encounter_id, "professional_record", note.strip(), 1, actor_id, now))
        if diagnosis.strip():
            connection.execute("INSERT INTO diagnoses(patient_dni,encounter_id,description,recorded_by,recorded_at,status) VALUES(?,?,?,?,?,?)", (dni, encounter_id, diagnosis.strip(), actor_id, now, "confirmed"))
        if medication.strip():
            connection.execute("INSERT INTO prescriptions(patient_dni,encounter_id,medication_name,instructions,prescribed_by,prescribed_at,status) VALUES(?,?,?,?,?,?,?)", (dni, encounter_id, medication.strip(), instructions.strip() or None, actor_id, now, "active"))
        connection.execute("INSERT INTO audit_events(encounter_id,patient_dni,event_type,actor_id,details_json,created_at) VALUES(?,?,?,?,?,?)", (encounter_id, dni, "professional_entry_recorded", actor_id, json.dumps({"diagnosis_recorded": bool(diagnosis.strip()), "prescription_recorded": bool(medication.strip())}), now))


def schema_catalog(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    migrate_longitudinal_schema(db_path)
    with connect(db_path) as connection:
        tables = [row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        catalog = []
        for table in tables:
            columns = [dict(row) for row in connection.execute(f"PRAGMA table_info({table})")]
            foreign_keys = [dict(row) for row in connection.execute(f"PRAGMA foreign_key_list({table})")]
            count = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            catalog.append({"table": table, "columns": columns, "foreign_keys": foreign_keys, "row_count": count})
        return catalog

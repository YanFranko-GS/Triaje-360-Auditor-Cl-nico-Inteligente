from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import load_settings
from protocols import is_action_complete

DEMO_DNI = "76543210"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path or load_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: Path | str | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                dni TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK(age >= 0),
                sex TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS medical_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_dni TEXT NOT NULL REFERENCES patients(dni) ON DELETE CASCADE,
                category TEXT NOT NULL,
                detail TEXT NOT NULL,
                event_date TEXT,
                is_demo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                protocol_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'blocked',
                block_reason TEXT,
                created_at TEXT NOT NULL,
                closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS model_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                model_name TEXT NOT NULL,
                model_used INTEGER NOT NULL,
                validated INTEGER NOT NULL,
                response_json TEXT NOT NULL,
                error_detail TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                action_id TEXT NOT NULL,
                label TEXT NOT NULL,
                action_type TEXT NOT NULL,
                constraints_json TEXT NOT NULL DEFAULT '{}',
                value_json TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(consultation_id, action_id)
            );
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                action_id TEXT NOT NULL,
                value_json TEXT NOT NULL,
                completed INTEGER NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS closures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
                permitted INTEGER NOT NULL,
                reason TEXT NOT NULL,
                actor TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER REFERENCES consultations(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        _seed_demo(conn)


def _seed_demo(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO patients(dni, name, age, sex, is_demo) VALUES (?, ?, ?, ?, 1)",
        (DEMO_DNI, "Paciente ficticia de demostración", 58, "Mujer"),
    )
    histories = [
        ("antecedente", "Hipertensión arterial", None),
        ("antecedente", "Diabetes tipo 2", None),
        ("alergia", "Alergia a AINEs", None),
        ("última visita simulada", "Control ambulatorio ficticio", "2026-05-15"),
    ]
    for category, detail, event_date in histories:
        conn.execute(
            """INSERT INTO medical_history(patient_dni, category, detail, event_date, is_demo)
               SELECT ?, ?, ?, ?, 1 WHERE NOT EXISTS (
                 SELECT 1 FROM medical_history WHERE patient_dni=? AND category=? AND detail=?
               )""",
            (DEMO_DNI, category, detail, event_date, DEMO_DNI, category, detail),
        )


def reset_demo_data(db_path: Path | str | None = None) -> None:
    """Reinicia exclusivamente registros marcados como demostrativos."""
    with connect(db_path) as conn:
        conn.execute("DELETE FROM patients WHERE is_demo = 1")
        _seed_demo(conn)
        conn.execute(
            "INSERT INTO audits(consultation_id,event_type,details_json,created_at) VALUES(NULL,?,?,?)",
            ("demo_data_reset", json.dumps({"scope": "demo_only"}), utc_now()),
        )


def get_patient(dni: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        patient = conn.execute("SELECT * FROM patients WHERE dni = ?", (dni,)).fetchone()
        if patient is None:
            return None
        history = conn.execute(
            "SELECT category, detail, event_date FROM medical_history WHERE patient_dni=? ORDER BY id", (dni,)
        ).fetchall()
    result = dict(patient)
    result["history"] = [dict(item) for item in history]
    return result


def create_consultation(
    *, dni: str, symptoms: str, analysis: dict[str, Any], protocol: dict[str, Any],
    model_name: str, model_used: bool, error_detail: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    now = utc_now()
    reason = f"Faltan {len(protocol['required_actions'])} acciones obligatorias."
    with connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO consultations(dni,symptoms,protocol_id,priority,model_name,model_used,status,block_reason,created_at)
               VALUES(?,?,?,?,?,?,'blocked',?,?)""",
            (dni, symptoms, analysis["protocol_id"], protocol["priority"], model_name, int(model_used), reason, now),
        )
        consultation_id = int(cursor.lastrowid)
        conn.execute(
            """INSERT INTO model_responses(consultation_id,model_name,model_used,validated,response_json,error_detail,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (consultation_id, model_name, int(model_used), 1, json.dumps(analysis, ensure_ascii=False), error_detail, now),
        )
        for action in protocol["required_actions"]:
            constraints = {key: action[key] for key in ("min", "max") if key in action}
            conn.execute(
                """INSERT INTO checklist_items(consultation_id,action_id,label,action_type,constraints_json)
                   VALUES(?,?,?,?,?)""",
                (consultation_id, action["id"], action["label"], action["type"], json.dumps(constraints)),
            )
        _audit(conn, consultation_id, "analysis_completed", {
            "model_used": model_used, "model_name": model_name,
            "protocol_id": analysis["protocol_id"], "fallback_reason": error_detail,
        })
    return consultation_id


def record_action(
    consultation_id: int, action: dict[str, Any], value: Any, actor: str = "profesional_demo",
    db_path: Path | str | None = None,
) -> bool:
    completed = is_action_complete(action, value)
    value_json = json.dumps(value, ensure_ascii=False)
    with connect(db_path) as conn:
        conn.execute(
            """UPDATE checklist_items SET value_json=?, completed=?
               WHERE consultation_id=? AND action_id=?""",
            (value_json, int(completed), consultation_id, action["id"]),
        )
        conn.execute(
            """INSERT INTO actions(consultation_id,action_id,value_json,completed,actor,created_at)
               VALUES(?,?,?,?,?,?)""",
            (consultation_id, action["id"], value_json, int(completed), actor, utc_now()),
        )
        completed_count, total = _progress(conn, consultation_id)
        reason = None if completed_count == total else f"Faltan {total - completed_count} acciones obligatorias."
        conn.execute("UPDATE consultations SET block_reason=? WHERE id=?", (reason, consultation_id))
        _audit(conn, consultation_id, "action_recorded", {"action_id": action["id"], "completed": completed, "actor": actor})
    return completed


def get_progress(consultation_id: int, db_path: Path | str | None = None) -> tuple[int, int, bool]:
    with connect(db_path) as conn:
        completed, total = _progress(conn, consultation_id)
    return completed, total, total > 0 and completed == total


def _progress(conn: sqlite3.Connection, consultation_id: int) -> tuple[int, int]:
    row = conn.execute(
        "SELECT COALESCE(SUM(completed),0) AS completed, COUNT(*) AS total FROM checklist_items WHERE consultation_id=?",
        (consultation_id,),
    ).fetchone()
    return int(row["completed"]), int(row["total"])


def attempt_close(
    consultation_id: int, actor: str = "profesional_demo", db_path: Path | str | None = None,
) -> tuple[bool, str]:
    with connect(db_path) as conn:
        completed, total = _progress(conn, consultation_id)
        permitted = total > 0 and completed == total
        reason = "Checklist completo; cierre habilitado por el motor determinista." if permitted else f"Cierre bloqueado: faltan {total - completed} acciones obligatorias."
        conn.execute(
            "INSERT INTO closures(consultation_id,permitted,reason,actor,created_at) VALUES(?,?,?,?,?)",
            (consultation_id, int(permitted), reason, actor, utc_now()),
        )
        if permitted:
            conn.execute(
                "UPDATE consultations SET status='closed', block_reason=NULL, closed_at=? WHERE id=?",
                (utc_now(), consultation_id),
            )
        else:
            conn.execute("UPDATE consultations SET status='blocked', block_reason=? WHERE id=?", (reason, consultation_id))
        _audit(conn, consultation_id, "closure_attempt", {"permitted": permitted, "reason": reason, "actor": actor})
    return permitted, reason


def get_trace(consultation_id: int, db_path: Path | str | None = None) -> dict[str, Any]:
    with connect(db_path) as conn:
        consultation = conn.execute("SELECT * FROM consultations WHERE id=?", (consultation_id,)).fetchone()
        response = conn.execute("SELECT * FROM model_responses WHERE consultation_id=? ORDER BY id DESC LIMIT 1", (consultation_id,)).fetchone()
        events = conn.execute("SELECT event_type,details_json,created_at FROM audits WHERE consultation_id=? ORDER BY id", (consultation_id,)).fetchall()
    return {
        "consultation": dict(consultation) if consultation else None,
        "model_response": dict(response) if response else None,
        "events": [{**dict(row), "details": json.loads(row["details_json"])} for row in events],
    }


def _audit(conn: sqlite3.Connection, consultation_id: int | None, event_type: str, details: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO audits(consultation_id,event_type,details_json,created_at) VALUES(?,?,?,?)",
        (consultation_id, event_type, json.dumps(details, ensure_ascii=False), utc_now()),
    )

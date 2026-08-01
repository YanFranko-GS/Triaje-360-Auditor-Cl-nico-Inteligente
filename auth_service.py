from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from pathlib import Path

from clinical_db import connect, migrate_demo_schema, seed_demo_data, utc_now


DEMO_ACCOUNT_PASSWORDS = {
    "nurse.demo": ("DEMO_NURSE_1", "Clinica360-N1!", "DEMO_FAC_A"),
    "triage.doctor": ("DEMO_TRIAGE_MD", "Clinica360-TD!", "DEMO_FAC_B"),
    "attending.demo": ("DEMO_ATTENDING_1", "Clinica360-M1!", "DEMO_FAC_A"),
    "supervisor.demo": ("DEMO_SUPERVISOR", "Clinica360-S1!", "DEMO_FAC_A"),
    "admin.demo": ("DEMO_ADMIN", "Clinica360-A1!", "DEMO_FAC_A"),
}


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    display_name: str
    role: str
    session_id: str
    facility_id: str | None = None
    patient_id: str | None = None


def _password_hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32).hex()


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode("utf-8")).hexdigest()[:16]


def seed_demo_accounts(db_path: Path | str | None = None) -> int:
    seed_demo_data(db_path)
    now = utc_now()
    with connect(db_path) as connection:
        for username, (user_id, password, _facility) in DEMO_ACCOUNT_PASSWORDS.items():
            exists = connection.execute(
                "SELECT 1 FROM demo_password_credentials WHERE user_id=?", (user_id,)
            ).fetchone()
            if not exists:
                salt = secrets.token_bytes(16)
                connection.execute(
                    """INSERT INTO demo_password_credentials
                       (user_id,username,password_hash,salt,algorithm,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (user_id, username, _password_hash(password, salt), salt.hex(), "scrypt-n16384-r8-p1", now, now),
                )
        connection.execute(
            """INSERT OR IGNORE INTO demo_patient_access(user_id,patient_id,birth_date,created_at)
               VALUES('DEMO_PATIENT','DEMO_PAT_01','1999-01-01',?)""",
            (now,),
        )
        return connection.execute("SELECT COUNT(*) FROM demo_password_credentials").fetchone()[0]


def _start_session(connection: object, user_id: str, role: str, facility_id: str | None) -> str:
    session_id = secrets.token_urlsafe(24)
    now = utc_now()
    connection.execute(
        "INSERT INTO demo_sessions VALUES(?,?,?,?,?,?,NULL)",
        (session_id, user_id, role, facility_id, now, now),
    )
    return session_id


def authenticate_professional(
    username: str, password: str, facility_id: str, db_path: Path | str | None = None
) -> AuthPrincipal | None:
    seed_demo_accounts(db_path)
    normalized = username.strip().casefold()
    with connect(db_path) as connection:
        row = connection.execute(
            """SELECT c.*,u.display_name,r.role_id FROM demo_password_credentials c
               JOIN demo_users u ON u.id=c.user_id JOIN demo_user_roles r ON r.user_id=u.id
               WHERE c.username=? AND u.status='active'""",
            (normalized,),
        ).fetchone()
        password_valid = bool(row) and hmac.compare_digest(
            _password_hash(password, bytes.fromhex(row["salt"])), row["password_hash"]
        )
        expected_facility = DEMO_ACCOUNT_PASSWORDS.get(normalized, (None, None, None))[2]
        facility_valid = bool(row) and (facility_id == expected_facility or row["role_id"] in {"ADMIN", "SUPERVISOR"})
        success = bool(password_valid and facility_valid)
        user_id = row["user_id"] if row else None
        role = row["role_id"] if row else None
        connection.execute(
            "INSERT INTO demo_login_events(user_id,username_fingerprint,role_id,success,reason,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, _fingerprint(normalized), role, int(success), "success" if success else "invalid_credentials", utc_now()),
        )
        if not success:
            return None
        session_id = _start_session(connection, user_id, role, facility_id)
        return AuthPrincipal(user_id, row["display_name"], role, session_id, facility_id=facility_id)


def authenticate_patient(
    synthetic_identifier: str, birth_date: str, db_path: Path | str | None = None
) -> AuthPrincipal | None:
    seed_demo_accounts(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            """SELECT pa.user_id,pa.patient_id,pa.birth_date,p.display_name,p.facility_id
               FROM demo_patient_access pa JOIN demo_patients p ON p.id=pa.patient_id
               WHERE p.synthetic_identifier=?""",
            (synthetic_identifier.strip(),),
        ).fetchone()
        success = bool(row) and hmac.compare_digest(row["birth_date"], birth_date.strip())
        connection.execute(
            "INSERT INTO demo_login_events(user_id,username_fingerprint,role_id,success,reason,created_at) VALUES(?,?,?,?,?,?)",
            (
                row["user_id"] if row else None, _fingerprint(synthetic_identifier), "PATIENT", int(success),
                "success" if success else "invalid_patient_validation", utc_now(),
            ),
        )
        if not success:
            return None
        session_id = _start_session(connection, row["user_id"], "PATIENT", row["facility_id"])
        return AuthPrincipal(
            row["user_id"], row["display_name"], "PATIENT", session_id,
            facility_id=row["facility_id"], patient_id=row["patient_id"],
        )


def logout(principal: AuthPrincipal, db_path: Path | str | None = None) -> None:
    with connect(db_path) as connection:
        now = utc_now()
        connection.execute("UPDATE demo_sessions SET ended_at=?,last_seen_at=? WHERE id=?", (now, now, principal.session_id))
        connection.execute(
            "INSERT INTO demo_login_events(user_id,username_fingerprint,role_id,success,reason,created_at) VALUES(?,?,?,?,?,?)",
            (principal.user_id, None, principal.role, 1, "logout", now),
        )


def record_attention_change(principal: AuthPrincipal, encounter_id: int, db_path: Path | str | None = None) -> None:
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO demo_audit_events(encounter_id,event_type,details_json,actor_id,source,created_at) VALUES(?,?,?,?,?,?)",
            (encounter_id, "attention_selected", '{"role":"' + principal.role + '"}', principal.user_id, "authenticated_session", utc_now()),
        )

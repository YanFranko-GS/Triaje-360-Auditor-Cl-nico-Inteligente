from __future__ import annotations

from pathlib import Path

import pytest

from clinical_db import (
    close_demo_encounter,
    create_patient_encounter,
    demo_profiles,
    demo_statistics,
    documentary_closure_status,
    encounter_context,
    migrate_demo_schema,
    patient_by_identifier,
    reset_demo_data,
    save_clinical_note,
    save_triage,
    seed_demo_data,
    triage_queue,
    validate_patient_payload,
)


@pytest.fixture
def demo_db(tmp_path: Path) -> Path:
    path = tmp_path / "clinical-demo.sqlite"
    seed_demo_data(path)
    return path


def _payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "identifier": "76543210",
        "consent_demo": True,
        "chief_complaint": "Relato ficticio",
        "narrative": "Dolor al respirar desde ayer, caso sintético.",
        "pain_present": True,
        "pain_score": 6,
    }
    payload.update(updates)
    return payload


def test_migrations_and_seed_are_idempotent(demo_db: Path) -> None:
    first = seed_demo_data(demo_db)
    migrate_demo_schema(demo_db)
    second = seed_demo_data(demo_db)
    assert first == second == {"patients": 10, "professional_users": 6, "institutions": 2, "encounters": 20}


def test_demo_roles_cover_the_workflow(demo_db: Path) -> None:
    roles = {profile["role"] for profile in demo_profiles(demo_db)}
    assert {"PATIENT", "TRIAGE_NURSE", "TRIAGE_DOCTOR", "ATTENDING_PHYSICIAN", "SUPERVISOR", "ADMIN"} <= roles


def test_seeded_patient_is_explicitly_synthetic(demo_db: Path) -> None:
    patient = patient_by_identifier("76543210", demo_db)
    assert patient and patient["id"].startswith("DEMO_")
    assert "sintético" in patient["display_name"].casefold()


def test_pain_score_is_required_when_pain_exists() -> None:
    with pytest.raises(ValueError, match="dolor"):
        validate_patient_payload(_payload(pain_score=None))


def test_patient_submission_enters_triage_queue(demo_db: Path) -> None:
    encounter_id = create_patient_encounter(_payload(), db_path=demo_db)
    queued = {item["id"]: item for item in triage_queue(demo_db)}
    assert queued[encounter_id]["status"] == "AWAITING_TRIAGE"


def test_triage_records_vitals_and_professional_decision(demo_db: Path) -> None:
    encounter_id = create_patient_encounter(_payload(), db_path=demo_db)
    save_triage(
        encounter_id,
        {"systolic": 120, "diastolic": 80, "heart_rate": 78, "respiratory_rate": 18, "temperature": 36.7, "oxygen_saturation": 98, "pain_score": 6, "population": "adult"},
        {"proposed_level": "Pendiente de revisión profesional", "confirmed_level": "Nivel 3", "decision": "aceptar", "justification": "Caso demo"},
        "DEMO_NURSE_1",
        demo_db,
    )
    context = encounter_context(encounter_id, demo_db)
    assert context and context["status"] == "AWAITING_PHYSICIAN"
    assert context["vitals"]["oxygen_saturation"] == 98
    assert context["triage"]["scale_name"] == "Escala demostrativa de prioridad de 5 niveles"


def test_closure_depends_only_on_configured_documentary_fields(demo_db: Path) -> None:
    encounter_id = create_patient_encounter(_payload(), db_path=demo_db)
    assert documentary_closure_status(encounter_id, demo_db)[1] is False
    save_triage(
        encounter_id, {"population": "adult"},
        {"proposed_level": "Pendiente", "confirmed_level": "Nivel 3", "decision": "aceptar"},
        "DEMO_NURSE_1", demo_db,
    )
    save_clinical_note(encounter_id, "Nota profesional ficticia.", "DEMO_ATTENDING_1", db_path=demo_db)
    assert documentary_closure_status(encounter_id, demo_db)[1] is True
    permitted, _ = close_demo_encounter(encounter_id, "DEMO_ATTENDING_1", demo_db)
    assert permitted
    assert encounter_context(encounter_id, demo_db)["status"] == "CLOSED"


def test_reset_preserves_non_demo_tables(demo_db: Path) -> None:
    import sqlite3

    with sqlite3.connect(demo_db) as connection:
        connection.execute("CREATE TABLE external_marker(value TEXT)")
        connection.execute("INSERT INTO external_marker VALUES('preserve')")
    reset_demo_data(demo_db)
    with sqlite3.connect(demo_db) as connection:
        assert connection.execute("SELECT value FROM external_marker").fetchone()[0] == "preserve"
    assert demo_statistics(demo_db)["patients"] == 10

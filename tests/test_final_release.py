from __future__ import annotations

from pathlib import Path

import pytest

from clinical_verifier import ClinicalCompletenessVerifier
from config import load_settings
from intake_service import confirm_field, fallback_extract_intake, resolve_field_as_null
from longitudinal_db import (
    descriptive_statistics,
    migrate_longitudinal_schema,
    patient_longitudinal_record,
    register_patient,
    schema_catalog,
)
from scripts.export_schema import export_schema
from triage_service import SCALE_NAME, propose_priority
from ui.navigation import allowed_pages_for


def _registration(dni: str = "12345678") -> dict[str, object]:
    return {
        "dni": dni, "given_names": "Lucía", "family_names": "Ramos",
        "birth_date": "1992-05-12", "registered_sex": "Femenino",
        "phone": "+51 900 000 001", "email": "lucia@example.test",
        "address": "Dirección sintética", "emergency_contact": "Contacto 999 000 000",
        "insurance_type": "SIS", "facility_id": "DEMO_FAC_A",
        "allergies": "Penicilina", "medications": "Medicamento habitual",
        "history": "Antecedente confirmado", "consent": True,
    }


def test_dynamic_patient_registration_and_duplicate_guard(tmp_path: Path) -> None:
    db = tmp_path / "registration.sqlite"
    patient = register_patient(_registration(), db)
    assert patient["dni"] == "12345678"
    assert patient["birth_date"] == "1992-05-12"
    with pytest.raises(ValueError, match="ya está registrado"):
        register_patient(_registration(), db)


@pytest.mark.parametrize("field,value", [("dni", "ABC"), ("phone", "1"), ("email", "bad")])
def test_registration_validates_formats(tmp_path: Path, field: str, value: str) -> None:
    payload = _registration("23456789")
    payload[field] = value
    with pytest.raises(ValueError):
        register_patient(payload, tmp_path / f"{field}.sqlite")


@pytest.mark.parametrize(
    "narrative",
    [
        "Tengo dolor abdominal desde ayer y está empeorando.",
        "Presento cefalea gradual desde hace dos horas.",
        "Me lesioné el tobillo esta mañana y tengo dolor 5 de 10.",
        "Tengo tos sin dolor desde hace tres días.",
    ],
)
def test_intake_accepts_general_complaints(narrative: str) -> None:
    extraction = fallback_extract_intake(narrative)
    assert extraction.chief_complaint.value
    assert extraction.chief_complaint.value == narrative


def test_explicit_null_resolution_is_not_an_unasked_absence() -> None:
    extraction = fallback_extract_intake("Tengo mareo")
    resolved = resolve_field_as_null(extraction, "allergies")
    assert resolved.allergies.value is None
    assert resolved.allergies.requires_confirmation is False
    assert resolved.allergies.confidence_status == "confirmed"
    assert "allergies" not in resolved.missing_fields


def test_second_stage_detects_contradiction_without_ollama() -> None:
    extraction = fallback_extract_intake("No tengo dolor")
    extraction = confirm_field(extraction, "pain_present", False, "patient_text")
    extraction = confirm_field(extraction, "pain_score", 8, "patient_text")
    result = ClinicalCompletenessVerifier().verify(extraction, "No tengo dolor", use_model=False)
    assert result.model_used is False
    assert result.result.validated is True
    assert result.result.contradictions
    assert result.result.complete is False


def test_verifier_normalizes_single_string_review_signal() -> None:
    extraction = fallback_extract_intake("Tengo dificultad respiratoria")
    extraction.immediate_review_signals.value = "Manifestación declarada para revisión"
    result = ClinicalCompletenessVerifier().verify(extraction, "Tengo dificultad respiratoria", use_model=False)
    assert result.result.requires_professional_review == ["Manifestación declarada para revisión"]


def test_config_exposes_sequential_primary_and_review_models(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("PRIMARY_MODEL=gemma4:e2b\nREVIEW_MODEL=review-local:latest\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.primary_model == "gemma4:e2b"
    assert settings.review_model == "review-local:latest"


def test_configurable_triage_uses_multiple_factors() -> None:
    proposal = propose_priority(
        {"oxygen_saturation": 88, "systolic": 85, "pain_score": 0, "consciousness_scale": "Alerta", "population": "adult"},
        {"narrative": "Consulta sin dolor", "evolution": "estable"},
    )
    assert proposal.level == 1
    assert len(proposal.reasons) >= 2
    assert "basado en ESI" in SCALE_NAME


def test_relational_schema_and_foreign_keys(tmp_path: Path) -> None:
    db = tmp_path / "schema.sqlite"
    migrate_longitudinal_schema(db)
    catalog = {item["table"]: item for item in schema_catalog(db)}
    required = {
        "patients", "patient_identifiers", "users", "roles", "sessions", "institutions", "facilities",
        "encounters", "symptoms", "pain_assessments", "vital_signs", "allergies", "medications",
        "prescriptions", "diagnoses", "procedures", "laboratory_results", "imaging_results",
        "clinical_notes", "triage_assessments", "conversation_turns", "field_extractions",
        "field_confirmations", "model_runs", "rag_retrievals", "audit_events",
    }
    assert required <= catalog.keys()
    assert catalog["encounters"]["foreign_keys"]
    assert catalog["field_confirmations"]["foreign_keys"]


def test_longitudinal_history_prescriptions_diagnoses_and_statistics(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    migrate_longitudinal_schema(db)
    history = patient_longitudinal_record("76543210", db)
    stats = descriptive_statistics("76543210", db)
    assert history["encounters"]
    assert history["diagnoses"]
    assert history["prescriptions"]
    assert stats["monthly"] and stats["vitals"]


def test_schema_export_generates_sql_and_mermaid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "export.sqlite"))
    sql_path, mermaid_path = export_schema(tmp_path / "docs")
    assert "CREATE TABLE encounters" in sql_path.read_text(encoding="utf-8")
    assert "erDiagram" in mermaid_path.read_text(encoding="utf-8")
    assert "patients ||--o{ encounters" in mermaid_path.read_text(encoding="utf-8")


def test_permissions_and_patient_safety_copy() -> None:
    assert "Estructura de datos" in allowed_pages_for("ADMIN")
    assert "Estructura de datos" not in allowed_pages_for("SUPERVISOR")
    assert "Historia clínica" in allowed_pages_for("PATIENT")
    patient_ui = (Path(__file__).parents[1] / "ui" / "patient_portal.py").read_text(encoding="utf-8")
    assert "no emite diagnósticos ni tratamientos" in patient_ui
    assert "Enviar a triaje" in patient_ui
    assert "prescribir" not in patient_ui.casefold()


def test_responsive_styles_have_mobile_breakpoints_and_no_wide_fixed_layout() -> None:
    styles = (Path(__file__).parents[1] / "ui" / "styles.css").read_text(encoding="utf-8")
    assert "@media (max-width: 900px)" in styles
    assert "@media (max-width: 560px)" in styles
    assert "overflow-x" in styles


def test_official_source_review_does_not_claim_national_esi_standard() -> None:
    review = (Path(__file__).parents[1] / "docs" / "peru_triage_standard_review.md")
    assert review.exists()
    text = review.read_text(encoding="utf-8")
    assert "Normativa ESI del Perú" not in text
    assert "evidencia oficial suficiente" in text

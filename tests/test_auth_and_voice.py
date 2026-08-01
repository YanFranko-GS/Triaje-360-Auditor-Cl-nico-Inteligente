from __future__ import annotations

import io
import math
import struct
import wave
from pathlib import Path

import pytest

from audio_pipeline import NoiseProfile, process_wav, sanitize_transcription
from auth_service import authenticate_patient, authenticate_professional, logout, seed_demo_accounts
from clinical_db import connect, migrate_demo_schema
from intake_service import confirm_field, fallback_extract_intake, next_followup_question
from scripts.check_gemma_audio_support import RESULT_SUPPORTED, check_audio_support
from services.local_asr import asr_status
from ui.navigation import allowed_pages_for, request_logout
from ui.ai_status import AIState
from workflow_store import add_audio_segment, create_audio_session


def wav_bytes(seconds: float = 1.0, amplitude: float = 0.25) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b"".join(
            struct.pack("<h", int(amplitude * 32767 * math.sin(2 * math.pi * 440 * i / 16000)))
            for i in range(int(seconds * 16000))
        ))
    return output.getvalue()


def test_professional_login_uses_hash_and_session(tmp_path: Path) -> None:
    db = tmp_path / "auth.db"
    seed_demo_accounts(db)
    principal = authenticate_professional("admin.demo", "Clinica360-A1!", "DEMO_FAC_A", db)
    assert principal and principal.role == "ADMIN"
    with connect(db) as connection:
        credential = connection.execute("SELECT * FROM demo_password_credentials WHERE username='admin.demo'").fetchone()
        session = connection.execute("SELECT ended_at FROM demo_sessions WHERE id=?", (principal.session_id,)).fetchone()
    assert credential["password_hash"] != "Clinica360-A1!" and credential["algorithm"].startswith("scrypt")
    assert session["ended_at"] is None


def test_failed_login_is_recorded_without_password(tmp_path: Path) -> None:
    db = tmp_path / "auth.db"
    assert authenticate_professional("admin.demo", "incorrecta", "DEMO_FAC_A", db) is None
    with connect(db) as connection:
        event = connection.execute("SELECT * FROM demo_login_events ORDER BY id DESC LIMIT 1").fetchone()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(demo_login_events)")}
    assert not event["success"] and event["reason"] == "invalid_credentials"
    assert "password" not in columns


def test_patient_login_is_scoped_to_one_synthetic_patient(tmp_path: Path) -> None:
    principal = authenticate_patient("76543210", "1999-01-01", tmp_path / "patient.db")
    assert principal and principal.role == "PATIENT" and principal.patient_id == "DEMO_PAT_01"
    assert authenticate_patient("76543210", "2000-01-01", tmp_path / "patient.db") is None


def test_logout_closes_session_and_callback_does_not_touch_navigation(tmp_path: Path) -> None:
    db = tmp_path / "logout.db"
    principal = authenticate_professional("nurse.demo", "Clinica360-N1!", "DEMO_FAC_A", db)
    assert principal
    logout(principal, db)
    with connect(db) as connection:
        assert connection.execute("SELECT ended_at FROM demo_sessions WHERE id=?", (principal.session_id,)).fetchone()[0]
    state = {"nav_page": "Inicio"}
    request_logout(state)
    assert state == {"nav_page": "Inicio", "logout_requested": True}


@pytest.mark.parametrize("role,allowed,forbidden", [
    ("PATIENT", "Portal del paciente", "Auditoría"),
    ("TRIAGE_NURSE", "Estación de triaje", "Panel médico"),
    ("ATTENDING_PHYSICIAN", "Panel médico", "Datos ficticios"),
    ("SUPERVISOR", "Auditoría", "Portal del paciente"),
])
def test_role_permissions(role: str, allowed: str, forbidden: str) -> None:
    pages = allowed_pages_for(role)
    assert allowed in pages and forbidden not in pages


def test_audio_preprocessing_outputs_mono_16khz_and_real_metrics() -> None:
    processed = process_wav(wav_bytes(), "audio/wav", NoiseProfile.CLINIC)
    assert processed.sample_rate == 16000 and processed.duration_seconds > 0
    assert 0 < processed.rms_level <= processed.peak_level <= 1
    assert len(processed.audio_sha256) == 64


def test_high_noise_profile_requests_shorter_segments() -> None:
    assert process_wav(wav_bytes(), "audio/wav", NoiseProfile.HIGH_NOISE).suggested_segment_seconds == 12


@pytest.mark.parametrize("content,mime,error", [
    (b"", "audio/wav", "vacío"),
    (b"not-wave", "audio/wav", "WAV válido"),
    (b"not-wave", "audio/mpeg", "MIME"),
])
def test_audio_rejects_empty_invalid_and_bad_mime(content: bytes, mime: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        process_wav(content, mime)


def test_audio_rejects_excess_duration_and_silence() -> None:
    with pytest.raises(ValueError, match="máximo"):
        process_wav(wav_bytes(31), "audio/wav")
    with pytest.raises(ValueError, match="señal"):
        process_wav(wav_bytes(1, amplitude=0), "audio/wav")


def test_audio_metadata_is_stored_without_audio_blob(tmp_path: Path) -> None:
    db = tmp_path / "audio.db"
    seed_demo_accounts(db)
    session_id = create_audio_session("DEMO_PATIENT", "CLINIC", True, db_path=db)
    add_audio_segment(session_id, process_wav(wav_bytes(), "audio/wav"), db_path=db)
    with connect(db) as connection:
        row = connection.execute("SELECT stored_path,audio_sha256 FROM demo_audio_segments").fetchone()
    assert row["stored_path"] is None and len(row["audio_sha256"]) == 64


def test_transcription_sanitization_blocks_active_content() -> None:
    assert sanitize_transcription("  dolor desde ayer  ") == "dolor desde ayer"
    with pytest.raises(ValueError, match="no permitido"):
        sanitize_transcription("<script>alert(1)</script>")


def test_local_asr_fails_safe_when_package_or_model_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("services.local_asr.importlib.util.find_spec", lambda _name: None)
    status = asr_status(None)
    assert not status.available and status.provider == "local_asr" and status.confidence is None


def test_direct_gemma_audio_requires_content_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __init__(self, payload: dict, status: int = 200):
            self.payload, self.status_code, self.ok, self.text = payload, status, status == 200, ""
        def json(self) -> dict:
            return self.payload
    monkeypatch.setattr("scripts.check_gemma_audio_support.requests.get", lambda *_a, **_k: Response({"version": "0.32.4"}))
    def fake_post(url: str, **_kwargs: object) -> Response:
        return Response({"capabilities": ["completion", "audio"]}) if url.endswith("/api/show") else Response({"message": {"content": "TONO"}})
    monkeypatch.setattr("scripts.check_gemma_audio_support.requests.post", fake_post)
    assert check_audio_support("http://127.0.0.1:11434", "gemma4:e2b")["result"] == RESULT_SUPPORTED


def test_structured_extraction_marks_missing_and_never_confirms_inference() -> None:
    extraction = fallback_extract_intake("Tengo dolor y me falta el aire desde ayer")
    assert extraction.chief_complaint.confidence_status == "inferred_for_review"
    assert extraction.duration.requires_confirmation
    assert extraction.immediate_review_signals.value


def test_followup_is_one_at_a_time_and_stops_for_immediate_flag() -> None:
    ordinary = fallback_extract_intake("Tengo malestar")
    question = next_followup_question(ordinary, set())
    assert question and question[0] in ordinary.missing_fields
    critical = fallback_extract_intake("No puedo respirar")
    assert next_followup_question(critical, set()) is None


def test_field_confirmation_updates_source_and_pain_validation() -> None:
    extraction = fallback_extract_intake("Tengo dolor")
    updated = confirm_field(extraction, "pain_score", 7, "patient_text")
    assert updated.pain_score.value == 7 and updated.pain_score.confidence_status == "confirmed"


def test_voice_migrations_are_repeatable(tmp_path: Path) -> None:
    db = tmp_path / "migration.db"
    migrate_demo_schema(db)
    migrate_demo_schema(db)
    with connect(db) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name in ("demo_sessions", "demo_audio_segments", "demo_transcriptions", "demo_conversation_turns", "demo_field_extractions"):
        assert name in names


def test_ui_keeps_manual_input_and_editable_transcription() -> None:
    source = (Path(__file__).parents[1] / "ui" / "audio_capture.py").read_text(encoding="utf-8")
    assert "st.audio_input" in source and "Transcripción editable" in source and "Información adicional escrita" in source
    assert "confidence" not in source.casefold() or "transcription_confidence" in source


def test_visible_ai_state_machine_covers_voice_and_followup() -> None:
    for state in ("LISTENING", "PROCESSING_AUDIO", "TRANSCRIBING", "RETRIEVING", "ASKING_FOLLOWUP"):
        assert AIState(state).value == state

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import requests

import engine
from config import Settings, load_settings
from database import (
    attempt_close, create_consultation, get_patient, get_progress, get_trace,
    initialize, record_action,
)
from protocols import completion_status, select_protocol
from schemas import GemmaAnalysis
from services.ollama_client import (
    OllamaError, _extract_json, analyze_case, check_ollama, fallback_analysis, validate_analysis,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    initialize(path)
    return path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings("http://localhost:11434", "gemma4:e2b", 2, tmp_path / "settings.db")


@pytest.fixture
def valid_payload() -> dict:
    return {
        "summary": "Relato con falta de aire desde ayer.",
        "risk_flags": ["Manifestación respiratoria para revisión profesional."],
        "protocol_id": "respiratory_alert",
        "reason": "El relato menciona falta de aire.",
        "disclaimer": "No constituye diagnóstico ni indicación médica.",
    }


def test_sqlite_initialization_is_idempotent(db_path: Path):
    initialize(db_path)
    initialize(db_path)
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"patients", "medical_history", "consultations", "audits", "model_responses", "checklist_items", "actions", "closures"} <= tables


def test_demo_patient_lookup(db_path: Path):
    patient = get_patient("76543210", db_path)
    assert patient and patient["age"] == 58
    assert "Alergia a AINEs" in {item["detail"] for item in patient["history"]}


def test_unknown_dni(db_path: Path):
    assert get_patient("00000000", db_path) is None


def test_selects_respiratory_protocol():
    protocol_id, protocol = select_protocol("Tengo dolor al respirar y falta de aire")
    assert protocol_id == "respiratory_alert"
    assert protocol["priority"] == "Naranja"


def test_selects_general_protocol():
    assert select_protocol("Molestia leve en la rodilla")[0] == "general_review"


def test_valid_model_output(valid_payload: dict):
    assert validate_analysis(valid_payload).protocol_id == "respiratory_alert"


def test_unknown_protocol_is_rejected(valid_payload: dict):
    valid_payload["protocol_id"] = "invented_protocol"
    with pytest.raises(OllamaError):
        validate_analysis(valid_payload)


def test_malformed_json_is_rejected():
    with pytest.raises(OllamaError):
        _extract_json("```json {mal formado} ```")


def test_empty_response_is_rejected():
    with pytest.raises(OllamaError, match="vacía"):
        _extract_json("  ")


def test_ollama_timeout(monkeypatch: pytest.MonkeyPatch, settings: Settings):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"models": [{"name": "gemma4:e2b"}]}
    monkeypatch.setattr(requests, "get", lambda *a, **k: Response())
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout("timeout")))
    with pytest.raises(OllamaError, match="tiempo límite"):
        analyze_case("falta de aire", [], settings)


def test_ollama_disconnected(monkeypatch: pytest.MonkeyPatch, settings: Settings):
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("offline")))
    status = check_ollama(settings)
    assert not status.reachable and not status.model_available


def test_fallback_activation(monkeypatch: pytest.MonkeyPatch, db_path: Path, settings: Settings):
    monkeypatch.setattr(engine, "analyze_case", lambda *a, **k: (_ for _ in ()).throw(OllamaError("offline")))
    run = engine.process_case(dni="76543210", symptoms="Me falta el aire", history=[], settings=settings, db_path=db_path)
    assert not run.model_used
    assert run.model_name == "deterministic-fallback"
    assert run.analysis.protocol_id == "respiratory_alert"
    assert run.fallback_reason == "offline"


def _consultation(db_path: Path, valid_payload: dict) -> tuple[int, dict]:
    analysis = GemmaAnalysis.model_validate(valid_payload)
    _, protocol = select_protocol("falta de aire", analysis.protocol_id)
    consultation_id = create_consultation(
        dni="76543210", symptoms="falta de aire", analysis=analysis.model_dump(), protocol=protocol,
        model_name="deterministic-fallback", model_used=False, error_detail="test", db_path=db_path,
    )
    return consultation_id, protocol


def test_incomplete_actions_block_closure(db_path: Path, valid_payload: dict):
    consultation_id, protocol = _consultation(db_path, valid_payload)
    record_action(consultation_id, protocol["required_actions"][0], True, db_path=db_path)
    permitted, reason = attempt_close(consultation_id, db_path=db_path)
    assert not permitted and "faltan" in reason.casefold()


def test_complete_checklist_enables_closure(db_path: Path, valid_payload: dict):
    consultation_id, protocol = _consultation(db_path, valid_payload)
    values = {"history_review": True, "lung_exam": "Evaluación registrada", "oxygen_saturation": 97, "referral_decision": "Decisión documentada"}
    for action in protocol["required_actions"]:
        record_action(consultation_id, action, values[action["id"]], db_path=db_path)
    assert get_progress(consultation_id, db_path) == (4, 4, True)
    assert attempt_close(consultation_id, db_path=db_path)[0]


def test_audit_is_recorded(db_path: Path, valid_payload: dict):
    consultation_id, _ = _consultation(db_path, valid_payload)
    trace = get_trace(consultation_id, db_path)
    assert trace["model_response"]["model_used"] == 0
    assert trace["events"][0]["event_type"] == "analysis_completed"


def test_configuration_loads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = tmp_path / ".env"
    env.write_text("OLLAMA_BASE_URL=http://example.test:11434\nOLLAMA_MODEL=gemma4:e2b\nOLLAMA_TIMEOUT_SECONDS=9\n", encoding="utf-8")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    loaded = load_settings(env)
    assert loaded.ollama_base_url == "http://example.test:11434" and loaded.ollama_timeout_seconds == 9


def test_app_source_compiles():
    app = Path(__file__).resolve().parents[1] / "app.py"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(app)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_app_does_not_render_streamlit_delta_generator_on_close():
    app = Path(__file__).resolve().parents[1] / "app.py"
    source = app.read_text(encoding="utf-8")
    assert "st.success(reason) if permitted else st.error(reason)" not in source


def test_fallback_general_and_completion_rules():
    analysis = fallback_analysis("Molestia general desde ayer")
    assert analysis.protocol_id == "general_review"
    _, protocol = select_protocol("Molestia general")
    assert completion_status(protocol, {"history_review": True, "physical_exam": "Registrado", "plan": "Documentado"}) == (3, 3, True)

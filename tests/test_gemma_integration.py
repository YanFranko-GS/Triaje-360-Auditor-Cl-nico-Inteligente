from __future__ import annotations

import pytest

from config import load_settings
from database import attempt_close, connect, get_patient, get_progress, get_trace, initialize, record_action
from engine import process_case
from services.ollama_client import check_ollama


@pytest.mark.integration
def test_real_gemma_demo_case_is_persisted_and_closed_by_rules(tmp_path):
    settings = load_settings()
    status = check_ollama(settings)
    if not status.reachable or not status.model_available:
        pytest.skip(f"Integración local no disponible: {status.detail}")

    db_path = tmp_path / "real_demo.db"
    initialize(db_path)
    patient = get_patient("76543210", db_path)
    assert patient is not None
    run = process_case(
        dni="76543210",
        symptoms="Tengo dolor en la espalda al respirar y me falta el aire desde ayer.",
        history=patient["history"],
        settings=settings,
        db_path=db_path,
    )
    assert run.model_used is True
    assert run.model_name == "gemma4:e2b"
    assert run.fallback_reason is None
    assert run.analysis.protocol_id == "respiratory_alert"
    assert run.protocol["priority"] == "Naranja"
    assert len(run.protocol["required_actions"]) == 4
    assert attempt_close(run.consultation_id, db_path=db_path)[0] is False
    values = {
        "history_review": True,
        "lung_exam": "Evaluación ficticia registrada",
        "oxygen_saturation": 97,
        "referral_decision": "Decisión ficticia documentada",
    }
    for action in run.protocol["required_actions"]:
        assert record_action(run.consultation_id, action, values[action["id"]], db_path=db_path)
    assert get_progress(run.consultation_id, db_path) == (4, 4, True)
    assert attempt_close(run.consultation_id, db_path=db_path)[0] is True
    trace = get_trace(run.consultation_id, db_path)
    consultation = trace["consultation"]
    model_response = trace["model_response"]
    assert consultation["status"] == "closed"
    assert consultation["model_used"] == 1
    assert model_response["model_name"] == "gemma4:e2b"
    assert model_response["error_detail"] is None

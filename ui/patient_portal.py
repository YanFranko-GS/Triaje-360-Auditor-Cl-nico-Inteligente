from __future__ import annotations

import streamlit as st

from audio_pipeline import NoiseProfile, process_wav, sanitize_transcription
from auth_service import AuthPrincipal
from clinical_db import create_patient_encounter, patient_by_id, patient_by_identifier, patient_tracking, save_rag_and_model_run
from clinical_verifier import ClinicalCompletenessVerifier
from config import Settings
from intake_service import confirm_field, extract_intake, next_followup_question, resolve_field_as_null
from longitudinal_db import mirror_intake_encounter, patient_longitudinal_record
from services.local_asr import transcribe_wav
from ui.ai_activity import render_assistant_status
from ui.ai_status import AIState, get_runtime_status, make_status, set_runtime_status
from ui.audio_capture import render_audio_capture
from workflow_store import save_conversation_turn, save_field_extractions, save_transcription


FIELD_LABELS = {
    "chief_complaint": "Motivo principal", "onset": "Inicio", "duration": "Duración",
    "evolution": "Evolución", "location": "Localización", "pain_present": "Dolor presente",
    "pain_score": "Dolor 0–10", "accompanying_symptoms": "Síntomas acompañantes",
    "allergies": "Alergias", "usual_medications": "Medicamentos habituales",
    "relevant_history": "Antecedentes", "immediate_review_signals": "Señales para revisión inmediata",
}


def _value(extraction: object, name: str, default: object = "") -> object:
    field = getattr(extraction, name)
    return field.value if field.value is not None else default


def _apply_structured_memory(extraction: object, dni: str) -> object:
    record = patient_longitudinal_record(dni)
    if not extraction.allergies.value and record["allergies"]:
        extraction = confirm_field(extraction, "allergies", [item["substance"] for item in record["allergies"] if item["status"] == "active"], "history")
    if not extraction.usual_medications.value and record["medications"]:
        extraction = confirm_field(extraction, "usual_medications", [item["name"] for item in record["medications"] if item["status"] == "active"], "history")
    return extraction


def render_patient_portal(settings: Settings, principal: AuthPrincipal) -> None:
    patient = patient_by_id(principal.patient_id or "") if principal.patient_id else None
    if not patient:
        st.error("La cuenta no tiene un paciente asociado.")
        return
    st.markdown('<div class="section-kicker">Admisión digital</div>', unsafe_allow_html=True)
    st.title("Nueva atención")
    st.caption(f"{patient['display_name']} · {patient['age']} años")
    render_assistant_status(get_runtime_status(settings.primary_model), "PATIENT")
    st.info("Si necesita atención inmediata, avise al personal presente. Este portal no emite diagnósticos ni tratamientos.")
    consent = st.checkbox("Autorizo la captura y organización temporal de mi información", key="patient_intake_consent")
    if not consent:
        st.warning("Confirme el consentimiento para comenzar.")
        return
    st.markdown("## Cuéntenos qué siente")
    intake_text = render_audio_capture(settings, principal.user_id)
    if st.button("Continuar", key="organize_patient_intake", type="primary", disabled=not (intake_text.text and intake_text.confirmed), use_container_width=True):
        set_runtime_status(make_status(AIState.ANALYZING, settings.primary_model, last_result="Completando información"))
        with st.spinner("Completando información"):
            run = extract_intake(intake_text.text, "patient_audio" if intake_text.provider != "manual_text" else "patient_text", settings)
            run = run.__class__(_apply_structured_memory(run.extraction, patient["synthetic_identifier"]), run.model_used, run.model_name, run.fallback_reason, run.duration_seconds)
        set_runtime_status(make_status(AIState.VALIDATING, settings.review_model, last_result="Verificando coherencia y completitud"))
        with st.spinner("Verificando información"):
            verification = ClinicalCompletenessVerifier(settings).verify(run.extraction, intake_text.text)
        st.session_state.intake_run = run
        st.session_state.verification_run = verification
        st.session_state.intake_original_text = intake_text.text
        st.session_state.asked_fields = set()
        st.session_state.field_resolutions = {}
        st.session_state.followup_turn = 0
        set_runtime_status(make_status(AIState.READY, settings.primary_model, last_result="Listo para revisar"))
        st.rerun()
    run = st.session_state.get("intake_run")
    if not run:
        return
    extraction = run.extraction
    verification = st.session_state.get("verification_run")
    if extraction.immediate_review_signals.value:
        st.error("Se requiere valoración prioritaria.")
        st.caption("La información fue recibida y debe ser confirmada por personal sanitario.")
    else:
        next_question = next_followup_question(extraction, st.session_state.get("asked_fields", set()))
        if next_question:
            field_name, question = next_question
            st.markdown("### Conversación guiada")
            st.chat_message("assistant").write(question)
            voice_answer = st.audio_input("Responder por voz (opcional)", key=f"followup_audio_{field_name}")
            if voice_answer and st.button("Transcribir respuesta", key=f"transcribe_followup_{field_name}"):
                try:
                    processed = process_wav(voice_answer.getvalue(), voice_answer.type or "audio/wav", NoiseProfile.CLINIC, settings.max_audio_seconds)
                    asr = transcribe_wav(processed.wav_bytes, settings.asr_model_path)
                    if asr.available and asr.text:
                        st.session_state[f"followup_voice_text_{field_name}"] = sanitize_transcription(asr.text)
                        st.rerun()
                    st.warning(asr.detail)
                except ValueError as exc:
                    st.error(str(exc))
            response = st.text_input("Su respuesta", value=st.session_state.get(f"followup_voice_text_{field_name}", ""), key=f"followup_response_{field_name}")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("Confirmar", key=f"confirm_{field_name}", disabled=not response.strip()):
                _complete_followup(run, extraction, field_name, question, response.strip(), principal, None)
            if c2.button("No sé", key=f"unknown_{field_name}"):
                _complete_followup(run, extraction, field_name, question, "No sé", principal, "unknown")
            if c3.button("No aplica", key=f"na_{field_name}"):
                _complete_followup(run, extraction, field_name, question, "No aplica", principal, "not_applicable")
            if c4.button("Omitir", key=f"skip_{field_name}"):
                _complete_followup(run, extraction, field_name, question, "Prefiere no responder", principal, "declined")
    _render_review(extraction, verification)
    if st.button("Editar relato", key="edit_patient_intake"):
        for key in ("intake_run", "verification_run", "asked_fields", "field_resolutions"):
            st.session_state.pop(key, None)
        st.rerun()
    force_send = st.checkbox("Solicito enviar la información disponible ahora", key="force_patient_submit")
    next_pending = next_followup_question(extraction, st.session_state.get("asked_fields", set()))
    has_contradictions = bool(verification and verification.result.contradictions)
    can_send = bool(extraction.immediate_review_signals.value) or ((next_pending is None and not has_contradictions) or force_send)
    if st.button("Enviar a triaje", key="submit_patient_intake", type="primary", disabled=not can_send, use_container_width=True):
        _submit_intake(settings, principal, patient, intake_text, run, extraction, verification)


def _complete_followup(run: object, extraction: object, field_name: str, question: str, response: str, principal: AuthPrincipal, resolution: str | None) -> None:
    updated = resolve_field_as_null(extraction, field_name) if resolution else confirm_field(extraction, field_name, response, "patient_text")
    st.session_state.intake_run = run.__class__(updated, run.model_used, run.model_name, run.fallback_reason, run.duration_seconds)
    st.session_state.verification_run = ClinicalCompletenessVerifier().verify(
        updated, st.session_state.get("intake_original_text", ""), use_model=False
    )
    st.session_state.asked_fields.add(field_name)
    st.session_state.followup_turn += 1
    if resolution:
        st.session_state.field_resolutions[field_name] = resolution
    save_conversation_turn(None, st.session_state.followup_turn, "patient", question, response, "patient_text", principal.user_id)
    st.rerun()


def _render_review(extraction: object, verification: object) -> None:
    st.markdown("### Revise la información antes de enviarla")
    completed, pending = [], []
    for name, label in FIELD_LABELS.items():
        field = getattr(extraction, name)
        row = {"Campo": label, "Valor": field.value, "Origen": field.source, "Confirmación": "Confirmado" if not field.requires_confirmation else "Por confirmar"}
        (pending if field.value in (None, "", []) and field.requires_confirmation else completed).append(row)
    st.markdown("#### Campos completados")
    st.dataframe(completed, use_container_width=True, hide_index=True)
    if pending:
        st.markdown("#### Campos pendientes")
        st.dataframe(pending, use_container_width=True, hide_index=True)
    if verification:
        if verification.result.contradictions:
            for item in verification.result.contradictions:
                st.warning(item)
        st.caption(f"Completitud verificada por {verification.result.verification_model}")


def _submit_intake(settings: Settings, principal: AuthPrincipal, patient: dict, intake_text: object, run: object, extraction: object, verification: object) -> None:
    payload = {
        "identifier": patient["synthetic_identifier"], "consent_demo": True,
        "chief_complaint": str(_value(extraction, "chief_complaint", st.session_state.get("intake_original_text", ""))),
        "narrative": st.session_state.get("intake_original_text", ""), "duration": str(_value(extraction, "duration", "")),
        "onset": str(_value(extraction, "onset", "")), "evolution": str(_value(extraction, "evolution", "")),
        "pain_present": bool(_value(extraction, "pain_present", False)), "pain_score": _value(extraction, "pain_score", None),
        "pain_location": str(_value(extraction, "location", "")), "accompanying_symptoms": _value(extraction, "accompanying_symptoms", []),
    }
    try:
        encounter_id = create_patient_encounter(payload, principal.user_id)
        save_field_extractions(encounter_id, extraction)
        save_transcription(intake_text.provider, payload["narrative"], encounter_id=encounter_id, confirmed=True)
        save_rag_and_model_run(encounter_id, [], {"provider": "ollama" if run.model_used else "deterministic-intake-fallback", "model_name": run.model_name, "state": "COMPLETED" if run.model_used else "FALLBACK", "model_used": run.model_used, "fallback_reason": run.fallback_reason, "duration_seconds": run.duration_seconds, "validated": run.model_used, "result": extraction.model_dump()})
        verification_payload = verification.result.model_dump() if verification else {"verification_model": "not-run", "validated": False}
        if verification:
            verification_payload.update({"duration_seconds": verification.duration_seconds, "error_detail": verification.error_detail})
        mirror_intake_encounter(encounter_id, patient["synthetic_identifier"], patient["facility_id"], extraction, payload["narrative"], principal.user_id, verification_payload, st.session_state.get("field_resolutions"))
        st.session_state.last_patient_encounter = encounter_id
        st.success("Información recibida. El personal de triaje confirmará la prioridad.")
    except ValueError as exc:
        st.error(str(exc))


def render_patient_tracking(principal: AuthPrincipal) -> None:
    st.title("Estado de atención")
    labels = {"AWAITING_TRIAGE": "Información recibida", "IN_TRIAGE": "En triaje", "AWAITING_PHYSICIAN": "En valoración profesional", "CLOSED": "Atención documentada"}
    records = patient_tracking(principal.patient_id or "")
    if not records:
        st.info("Aún no hay atenciones enviadas desde este acceso.")
        return
    for record in records:
        st.markdown(f'<article class="tracking-card"><b>Atención {record["id"]}</b><span>{labels.get(record["status"], "En espera")}</span><small>{record["created_at"]}</small></article>', unsafe_allow_html=True)

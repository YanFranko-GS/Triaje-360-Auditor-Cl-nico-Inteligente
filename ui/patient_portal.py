from __future__ import annotations

import streamlit as st

from auth_service import AuthPrincipal
from clinical_db import create_patient_encounter, patient_by_id, patient_by_identifier, patient_tracking, save_rag_and_model_run
from config import Settings
from intake_service import confirm_field, extract_intake, next_followup_question
from ui.ai_activity import render_assistant_status
from ui.ai_status import get_runtime_status
from ui.audio_capture import render_audio_capture
from workflow_store import save_conversation_turn, save_field_extractions, save_transcription


def _value(extraction: object, name: str, default: object = "") -> object:
    field = getattr(extraction, name)
    return field.value if field.value is not None else default


def render_patient_portal(settings: Settings, principal: AuthPrincipal) -> None:
    patient = patient_by_id(principal.patient_id or "") if principal.patient_id else patient_by_identifier("76543210")
    if not patient:
        st.error("La cuenta no tiene un paciente sintético asociado.")
        return
    st.markdown('<div class="section-kicker">Admisión digital</div>', unsafe_allow_html=True)
    st.title("Nueva atención")
    st.caption(f"{patient['display_name']} · acceso restringido a su información sintética")
    render_assistant_status(get_runtime_status(settings.ollama_model), "PATIENT")
    st.info("Si necesita atención inmediata, avise al personal presente. Este portal no emite diagnóstico ni tratamiento.")
    consent = st.checkbox("Acepto la captura y organización temporal de información sintética", key="patient_intake_consent")
    if not consent:
        st.warning("Confirme el consentimiento de validación para comenzar.")
        return
    intake_text = render_audio_capture(settings, principal.user_id)
    if st.button(
        "Organizar información", key="organize_patient_intake", type="primary",
        disabled=not (intake_text.text and intake_text.confirmed), use_container_width=True,
    ):
        with st.spinner("Organizando la información"):
            st.session_state.intake_run = extract_intake(
                intake_text.text, "patient_audio" if intake_text.provider != "manual_text" else "patient_text", settings
            )
            st.session_state.intake_original_text = intake_text.text
            st.session_state.asked_fields = set()
            st.session_state.followup_turn = 0
        st.rerun()
    run = st.session_state.get("intake_run")
    if not run:
        return
    extraction = run.extraction
    if extraction.immediate_review_signals.value:
        st.error("Se requiere valoración inmediata del personal.")
        st.caption("El cuestionario se detuvo; no espere a completar todos los campos.")
    else:
        next_question = next_followup_question(extraction, st.session_state.get("asked_fields", set()))
        if next_question:
            field_name, question = next_question
            st.markdown("### Completemos un dato")
            st.write(question)
            response = st.text_input("Respuesta", key=f"followup_response_{field_name}")
            voice_answer = st.audio_input("Responder por voz (opcional)", key=f"followup_audio_{field_name}")
            if voice_answer:
                st.caption("La respuesta de voz requiere ASR local; siempre puede escribir o indicar “no sé”.")
            c1, c2, c3 = st.columns(3)
            if c1.button("Confirmar", key=f"confirm_followup_{field_name}", disabled=not response.strip()):
                extraction = confirm_field(extraction, field_name, response.strip(), "patient_text")
                st.session_state.intake_run = run.__class__(
                    extraction, run.model_used, run.model_name, run.fallback_reason, run.duration_seconds
                )
                st.session_state.asked_fields.add(field_name)
                st.session_state.followup_turn += 1
                save_conversation_turn(None, st.session_state.followup_turn, "patient", question, response.strip(), "patient_text", principal.user_id)
                st.rerun()
            if c2.button("No sé", key=f"unknown_followup_{field_name}"):
                st.session_state.asked_fields.add(field_name)
                st.session_state.followup_turn += 1
                save_conversation_turn(None, st.session_state.followup_turn, "patient", question, "no sé", "patient_text", principal.user_id)
                st.rerun()
            if c3.button("Omitir", key=f"skip_followup_{field_name}"):
                st.session_state.asked_fields.add(field_name)
                st.rerun()
    st.markdown("### Revise el resumen")
    st.write(_value(extraction, "chief_complaint", st.session_state.get("intake_original_text", "")))
    summary = {
        "Inicio": _value(extraction, "onset", "Pendiente"),
        "Duración": _value(extraction, "duration", "Pendiente"),
        "Evolución": _value(extraction, "evolution", "Pendiente"),
        "Dolor": _value(extraction, "pain_score", "Pendiente") if _value(extraction, "pain_present", False) else "No declarado",
    }
    st.json(summary)
    if st.button("Enviar al personal de triaje", key="submit_patient_intake", type="primary", use_container_width=True):
        payload = {
            "identifier": patient["synthetic_identifier"], "consent_demo": True,
            "chief_complaint": str(_value(extraction, "chief_complaint", "Motivo por confirmar")),
            "narrative": st.session_state.get("intake_original_text", ""),
            "duration": str(_value(extraction, "duration", "")), "onset": str(_value(extraction, "onset", "")),
            "evolution": str(_value(extraction, "evolution", "")),
            "pain_present": bool(_value(extraction, "pain_present", False)),
            "pain_score": _value(extraction, "pain_score", None), "pain_location": str(_value(extraction, "location", "")),
            "accompanying_symptoms": _value(extraction, "accompanying_symptoms", []),
        }
        try:
            encounter_id = create_patient_encounter(payload, principal.user_id)
            save_field_extractions(encounter_id, extraction)
            save_transcription(intake_text.provider, payload["narrative"], encounter_id=encounter_id, confirmed=True)
            save_rag_and_model_run(
                encounter_id, [],
                {
                    "provider": "ollama" if run.model_used else "deterministic-intake-fallback",
                    "model_name": run.model_name, "state": "COMPLETED" if run.model_used else "FALLBACK",
                    "model_used": run.model_used, "fallback_reason": run.fallback_reason,
                    "duration_seconds": run.duration_seconds, "validated": run.model_used,
                    "result": extraction.model_dump(),
                },
            )
            st.session_state.last_patient_encounter = encounter_id
            st.success("Información enviada al personal de triaje.")
        except ValueError as exc:
            st.error(str(exc))


def render_patient_tracking(principal: AuthPrincipal) -> None:
    st.title("Seguimiento de atención")
    labels = {
        "AWAITING_TRIAGE": "Recibido · pendiente de triaje",
        "IN_TRIAGE": "En triaje",
        "AWAITING_PHYSICIAN": "Derivado a atención",
        "CLOSED": "Atención documentada",
    }
    records = patient_tracking(principal.patient_id or "")
    if not records:
        st.info("Aún no hay atenciones enviadas desde este acceso.")
        return
    for record in records:
        st.markdown(
            f'<article class="tracking-card"><b>Atención {record["id"]}</b><span>{labels.get(record["status"], "Pendiente")}</span><small>{record["created_at"]}</small></article>',
            unsafe_allow_html=True,
        )

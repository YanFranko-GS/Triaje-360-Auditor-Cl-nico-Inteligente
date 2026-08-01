from __future__ import annotations

import streamlit as st

from ui.ai_status import AIRuntimeStatus, AIState, render_ai_status, render_inference_activity


PATIENT_MESSAGES = {
    AIState.READY: "Listo para escuchar",
    AIState.LISTENING: "Escuchando",
    AIState.PROCESSING_AUDIO: "Procesando el audio",
    AIState.TRANSCRIBING: "Organizando la información",
    AIState.ANALYZING: "Organizando la información",
    AIState.ASKING_FOLLOWUP: "Necesitamos completar algunos datos",
    AIState.COMPLETED: "Información enviada al personal de triaje",
    AIState.FALLBACK: "Puede continuar escribiendo la información",
    AIState.ERROR: "Asistente temporalmente no disponible",
}


def render_assistant_status(status: AIRuntimeStatus, role: str) -> None:
    if role == "PATIENT":
        message = PATIENT_MESSAGES.get(status.state, "Preparando el asistente")
        st.markdown(f'<div class="patient-ai-state" aria-live="polite">{message}</div>', unsafe_allow_html=True)
        return
    st.markdown("#### Asistente clínico")
    render_ai_status(status)


def render_processing(stage: int, elapsed_seconds: float) -> None:
    render_inference_activity(stage, elapsed_seconds)
    st.button("Cancelar", key=f"cancel_safe_{stage}", disabled=stage >= 3, help="Disponible sólo antes de iniciar la inferencia.")

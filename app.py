from __future__ import annotations

from typing import Any

import streamlit as st

from config import load_settings
from database import (
    attempt_close,
    get_patient,
    get_progress,
    get_trace,
    initialize,
    record_action,
    reset_demo_data,
)
from engine import AnalysisRun, process_case
from services.ollama_client import check_ollama
from ui.components import (
    render_disclaimer,
    render_empty_clinical_panel,
    render_engine_banner,
    render_header,
    render_patient_card,
    render_progress_steps,
    render_system_status,
)
from ui.theme import load_styles


st.set_page_config(
    page_title="TRIaje 360 | KutanLab",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

settings = load_settings()
initialize()
load_styles()

if "run" not in st.session_state:
    st.session_state.run = None
if "patient_snapshot" not in st.session_state:
    st.session_state.patient_snapshot = None

status = check_ollama(settings)
run: AnalysisRun | None = st.session_state.run

render_header(
    ollama_ready=status.reachable,
    model_ready=status.model_available,
    model_name=settings.ollama_model,
)
render_system_status(
    reachable=status.reachable,
    model_available=status.model_available,
    model_name=settings.ollama_model,
)

active_step = 1
if run is not None:
    completed, total, can_close = get_progress(run.consultation_id)
    active_step = 4 if can_close else 3
render_progress_steps(active_step)

with st.sidebar:
    st.title("TRIaje 360")
    st.caption("Auditor clínico documental · KutanLab")
    st.markdown("**Arquitectura**")
    st.write("Streamlit → Gemma 4/Ollama → Pydantic → reglas cerradas → SQLite")
    st.markdown("**Modelo configurado**")
    st.code(settings.ollama_model)
    st.markdown("**Caso demostrativo**")
    st.write("DNI 76543210 · relato respiratorio ficticio")
    st.markdown("**Limitaciones**")
    st.write("Sin diagnóstico, prescripción, voz real, autenticación ni historia clínica real.")
    if st.button("Reiniciar sesión demostrativa", use_container_width=True):
        reset_demo_data()
        st.session_state.run = None
        st.session_state.patient_snapshot = None
        st.rerun()
    st.divider()
    st.caption("Daniel Ríos · Yan Franco Gonzales Segura · Jhon Gesell Villanueva Portella")

left, right = st.columns([0.92, 1.5], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<div class="section-kicker">01 · Admisión</div>', unsafe_allow_html=True)
        st.subheader("Admisión del paciente")
        st.caption("Caso exclusivamente ficticio para la demostración educativa.")

        dni = st.text_input(
            "DNI ficticio",
            value="76543210",
            max_chars=8,
            help="No ingrese identificadores ni datos de pacientes reales.",
        )
        patient = get_patient(dni.strip())
        if patient:
            render_patient_card(patient)
        else:
            st.info("DNI ficticio no encontrado. El relato puede analizarse sin antecedentes.")

        symptoms = st.text_area(
            "Relato o dictado transcrito",
            value="Tengo dolor en la espalda al respirar y me falta el aire desde ayer.",
            height=145,
            help="Ejemplo: describa desde cuándo ocurre, ubicación y señales relevantes. La voz real no forma parte del MVP.",
        )
        st.caption("Ejemplo respiratorio cargado. También puede probar un relato general ficticio.")
        use_ollama = st.toggle("Intentar análisis con Gemma 4", value=True)

        if status.reachable and status.model_available:
            st.success(f"Listo para inferencia real con {settings.ollama_model} en CPU.")
        elif status.reachable:
            st.warning(f"Ollama responde, pero falta {settings.ollama_model}. Se aplicará respaldo determinista.")
        else:
            st.warning("Ollama no está disponible. Se aplicará respaldo determinista y quedará registrada la causa.")

        if st.button("Analizar caso con Gemma 4", type="primary", use_container_width=True):
            if not symptoms.strip():
                st.error("Ingrese un relato antes de analizar.")
            else:
                with st.spinner("Gemma 4 está estructurando el relato..."):
                    new_run = process_case(
                        dni=dni.strip(),
                        symptoms=symptoms.strip(),
                        history=patient["history"] if patient else [],
                        use_ollama=use_ollama,
                        settings=settings,
                    )
                st.session_state.run = new_run
                st.session_state.patient_snapshot = patient
                st.rerun()

        render_disclaimer()

with right:
    with st.container(border=True):
        st.markdown('<div class="section-kicker">02 · Auditoría</div>', unsafe_allow_html=True)
        st.subheader("Auditoría clínica documental")
        st.caption("Gemma estructura; Pydantic valida; las reglas deterministas controlan el cierre.")

        if run is None:
            render_empty_clinical_panel()
        else:
            analysis = run.analysis
            protocol = run.protocol
            snapshot = st.session_state.patient_snapshot

            render_engine_banner(
                model_used=run.model_used,
                model_name=run.model_name,
                fallback_reason=run.fallback_reason,
            )
            if snapshot:
                render_patient_card(snapshot)

            priority_col, source_col, protocol_col = st.columns(3)
            priority_col.metric("Prioridad documental", protocol["priority"])
            source_col.metric("Motor utilizado", "Gemma 4 real" if run.model_used else "Respaldo")
            protocol_col.metric("Protocolo", analysis.protocol_id)

            st.markdown("#### Resumen estructurado")
            st.write(analysis.summary)
            st.markdown(f"#### Protocolo demostrativo: {protocol['name']}")
            st.caption(f"Motivo de activación: {analysis.reason}")

            if analysis.risk_flags:
                st.markdown("**Banderas para revisión profesional**")
                for flag in analysis.risk_flags:
                    st.markdown(f'<div class="flag">⚑ {flag}</div>', unsafe_allow_html=True)
            st.info(analysis.disclaimer)

            st.markdown("#### Checklist obligatorio")
            values: dict[str, Any] = {}
            with st.form(f"checklist_{run.consultation_id}"):
                for action in protocol["required_actions"]:
                    if action["type"] == "checkbox":
                        values[action["id"]] = st.checkbox(
                            action["label"], key=f"{run.consultation_id}_{action['id']}"
                        )
                    elif action["type"] == "number":
                        values[action["id"]] = st.number_input(
                            action["label"],
                            min_value=action.get("min"),
                            max_value=action.get("max"),
                            value=None,
                            step=1,
                            key=f"{run.consultation_id}_{action['id']}",
                        )
                    else:
                        values[action["id"]] = st.text_area(
                            action["label"], height=75, key=f"{run.consultation_id}_{action['id']}"
                        )
                submitted = st.form_submit_button("Registrar acciones", use_container_width=True)

            if submitted:
                for action in protocol["required_actions"]:
                    record_action(run.consultation_id, action, values[action["id"]])
                st.success("Acciones registradas con trazabilidad.")

            completed, total, can_close = get_progress(run.consultation_id)
            st.progress(completed / total if total else 0.0)
            st.caption(f"{completed} de {total} acciones completadas · {total - completed} pendientes")
            if not can_close:
                st.error("Cierre bloqueado por el motor determinista hasta completar todas las acciones.")
            else:
                st.success("Checklist completo. El cierre documental está habilitado.")

            if st.button(
                "Finalizar consulta y guardar",
                disabled=not can_close,
                type="primary",
                use_container_width=True,
            ):
                permitted, reason = attempt_close(run.consultation_id)
                if permitted:
                    st.success(reason)
                else:
                    st.error(reason)

            with st.expander("Trazabilidad técnica"):
                st.json(
                    {
                        "consultation_id": run.consultation_id,
                        "model_configured": settings.ollama_model,
                        "model_name": run.model_name,
                        "model_used": run.model_used,
                        "fallback_reason": run.fallback_reason,
                        "validated_json": analysis.model_dump(),
                        "database_trace": get_trace(run.consultation_id),
                    }
                )

st.markdown(
    '<div class="footer-note">TRIaje 360 · Prototipo educativo de KutanLab · Toda decisión corresponde a un profesional autorizado.</div>',
    unsafe_allow_html=True,
)

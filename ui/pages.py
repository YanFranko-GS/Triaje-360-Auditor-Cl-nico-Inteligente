from __future__ import annotations

import json
import time
from typing import Any

import streamlit as st

from clinical_db import (
    audit_feed,
    close_demo_encounter,
    create_patient_encounter,
    demo_statistics,
    documentary_closure_status,
    encounter_context,
    patient_by_identifier,
    reset_demo_data,
    save_clinical_note,
    save_rag_and_model_run,
    save_triage,
    seed_demo_data,
    triage_queue,
)
from config import Settings
from engine import AnalysisRun, process_case
from rag.citations import citation_payload, traceability_metrics
from rag.ingest import ingest_approved_sources, load_source_register
from rag.retriever import LexicalRetriever
from services.ai_provider import probe_provider, provider_status
from services.ollama_client import OllamaError
from ui.ai_status import AIState, get_runtime_status, make_status, render_ai_status, render_inference_activity, set_runtime_status
from ui.components import render_disclaimer, render_patient_card, render_system_status


PAGE_ROLES = {
    "Portal del paciente": {"PATIENT", "ADMIN"},
    "Estación de triaje": {"TRIAGE_NURSE", "TRIAGE_DOCTOR", "SUPERVISOR", "ADMIN"},
    "Panel médico": {"ATTENDING_PHYSICIAN", "SUPERVISOR", "ADMIN"},
    "Datos ficticios": {"ADMIN", "SUPERVISOR"},
    "Auditoría": {"SUPERVISOR", "ADMIN"},
}


def _role_allowed(page: str, role: str) -> bool:
    allowed = PAGE_ROLES.get(page)
    if not allowed or role in allowed:
        return True
    st.warning(f"La vista {page} requiere uno de estos perfiles demo: {', '.join(sorted(allowed))}.")
    st.caption("Autenticación demostrativa; no apta para producción.")
    return False


def _page_heading(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="section-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<h2 class="page-title">{title}</h2>', unsafe_allow_html=True)
    st.caption(subtitle)


def render_home(settings: Settings, profile: dict[str, str]) -> None:
    _page_heading("Inicio", "Plataforma demostrativa de atención documental", "Paciente → Triaje → Médico → Auditoría documental")
    status = provider_status(settings)
    render_system_status(reachable=status.reachable, model_available=status.model_available, model_name=settings.ollama_model)
    render_ai_status(get_runtime_status(settings.ollama_model))

    stats = demo_statistics()
    rag_count = ingest_approved_sources()
    cols = st.columns(4)
    cols[0].metric("RAG aprobado", f"{rag_count} chunks")
    cols[1].metric("Pacientes sintéticos", stats["patients"])
    cols[2].metric("Atenciones demo", stats["encounters"])
    cols[3].metric("Perfil activo", profile["role"])

    st.markdown(
        """
        <section class="workflow-grid" aria-label="Flujo de atención demostrativo">
          <div class="workflow-card"><b>1 · Paciente</b><span>Registra datos ficticios y síntomas; no recibe diagnóstico.</span></div>
          <div class="workflow-card"><b>2 · Triaje</b><span>Profesional documenta signos y revisa evidencia aplicable.</span></div>
          <div class="workflow-card"><b>3 · Médico</b><span>Revisa cronología, faltantes, fuentes y decisiones.</span></div>
          <div class="workflow-card"><b>4 · Auditoría</b><span>Conserva cambios, fuentes, aceptación y cierre documental.</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="safety-banner"><b>Prototipo educativo.</b> No diagnostica, prescribe, ordena pruebas ni sustituye al profesional. Use sólo datos ficticios.</div>', unsafe_allow_html=True)
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Caso reproducible")
        st.write("Identificador sintético `76543210` · relato respiratorio ficticio · escala de dolor declarada por el paciente.")
        if st.button("Iniciar recorrido", type="primary", use_container_width=True):
            st.session_state.nav_page = "Portal del paciente"
            st.rerun()
    with right:
        st.subheader("Comprobación técnica")
        if st.button("Comprobar Gemma 4", use_container_width=True):
            set_runtime_status(make_status(AIState.WARMING_UP, settings.ollama_model, last_result="Ejecutando inferencia mínima..."))
            try:
                result = probe_provider(settings)
                state = AIState.READY if result.responded else AIState.ERROR
                set_runtime_status(
                    make_status(
                        state, result.model_name, duration_seconds=result.duration_seconds,
                        last_result=result.detail, pydantic_validated=False,
                    )
                )
            except OllamaError as exc:
                set_runtime_status(make_status(AIState.ERROR, settings.ollama_model, last_result=str(exc)))
            st.rerun()


def render_patient_portal(settings: Settings, profile: dict[str, str]) -> None:
    if not _role_allowed("Portal del paciente", profile["role"]):
        return
    _page_heading("Vista 1", "Portal del paciente", "Captura inicial ficticia; clasificación orientativa pendiente de validación profesional.")
    st.markdown('<div class="safety-banner">Si el relato contiene una señal configurada como crítica: <b>solicite valoración inmediata del personal</b>. La aplicación no aconseja esperar ni automedicarse.</div>', unsafe_allow_html=True)

    identifier = st.text_input("DNI o identificador sintético", value="76543210", max_chars=12)
    patient = patient_by_identifier(identifier.strip()) if identifier.strip() else None
    if patient:
        render_patient_card(
            {
                "name": patient["display_name"], "dni": patient["synthetic_identifier"],
                "sex": patient["registered_sex"], "age": patient["age"],
                "history": [{"detail": item} for item in patient["allergies"] + patient["medications"]],
            }
        )
        st.caption(f"Asegurador ficticio: {patient['insurer']} · establecimiento: {patient['facility_id']}")
    else:
        st.info("Use un identificador sintético sembrado; no ingrese datos personales reales.")

    with st.form("patient_intake"):
        consent = st.checkbox("Acepto el consentimiento demostrativo y confirmo que usaré datos ficticios")
        chief = st.text_input("Motivo de consulta")
        narrative = st.text_area("Relato o dictado transcrito", height=120)
        duration = st.text_input("Duración de síntomas", placeholder="Ejemplo ficticio: desde ayer")
        pain_present = st.checkbox("Existe dolor")
        pain_score = st.number_input(
            "Escala de dolor declarada (0–10)", min_value=0, max_value=10, value=None,
            help="0 = sin dolor. 10 = peor dolor imaginable declarado por el paciente. No determina por sí sola la urgencia.",
        )
        pain_location = st.text_input("Localización del dolor")
        col1, col2 = st.columns(2)
        onset = col1.selectbox("Inicio", ("", "súbito", "gradual"))
        evolution = col2.selectbox("Evolución", ("", "mejora", "estable", "empeora"))
        accompanying = st.multiselect(
            "Síntomas acompañantes declarados",
            ("Falta de aire", "Mareo", "Náuseas", "Tos", "Fiebre declarada", "Otro"),
        )
        mobility = st.selectbox("Movilidad", ("independiente", "con apoyo", "camilla", "no declarado"))
        companion = st.text_input("Acompañante ficticio", value="sin acompañante")
        pregnancy = st.selectbox("Embarazo posible cuando aplique", ("no aplica", "no declarado", "sí declarado", "no declarado como posible"))
        submitted = st.form_submit_button("Enviar para valoración de triaje", type="primary", use_container_width=True)
    if submitted:
        try:
            encounter_id = create_patient_encounter(
                {
                    "identifier": identifier.strip(), "consent_demo": consent, "chief_complaint": chief,
                    "narrative": narrative, "duration": duration, "pain_present": pain_present,
                    "pain_score": pain_score, "pain_location": pain_location, "onset": onset,
                    "evolution": evolution, "accompanying_symptoms": accompanying, "mobility": mobility,
                    "companion": companion, "pregnancy_possible": pregnancy,
                },
                actor_id=profile["id"],
            )
            st.session_state.selected_encounter = encounter_id
            st.success(f"Atención {encounter_id} creada con estado AWAITING_TRIAGE.")
            if any(term in narrative.casefold() for term in ("falta de aire", "no puedo respirar", "dolor al respirar")):
                st.error("Solicite valoración inmediata del personal.")
        except ValueError as exc:
            st.error(str(exc))
    render_disclaimer()


def _select_queue_encounter(status_filter: str | None = None) -> tuple[int | None, dict[str, Any] | None]:
    queue = triage_queue()
    if status_filter:
        queue = [item for item in queue if item["status"] == status_filter]
    if not queue:
        st.info("No existen atenciones ficticias pendientes para esta vista.")
        return None, None
    labels = {item["id"]: f"#{item['id']} · {item['display_name']} · {item['status']} · espera simulada {max(item['wait_minutes'], 0)} min" for item in queue}
    default = st.session_state.get("selected_encounter")
    ids = list(labels)
    index = ids.index(default) if default in ids else 0
    encounter_id = st.selectbox("Cola ficticia", ids, index=index, format_func=lambda item: labels[item])
    st.session_state.selected_encounter = encounter_id
    return encounter_id, encounter_context(encounter_id)


def _render_evidence(results: list[Any]) -> None:
    if not results:
        st.info("No se encontró evidencia aplicable en la base configurada.")
        return
    for result in results:
        item = citation_payload(result)
        st.markdown(
            f"""
            <article class="evidence-card">
              <b>{item['source_id']} · {item['title']}</b>
              <div class="evidence-card__meta">{item['institution']} · {item['year']} · población {item['population']} · {item['section']} · página {item['page']}</div>
              <p>{item['fragment']}</p>
              <p><b>Aplicabilidad:</b> {item['applicability']}</p>
              <p><b>Limitaciones:</b> {item['limitations']}</p>
              <div class="evidence-card__meta">Recuperación: {item['retrieval_reason']}</div>
            </article>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"[Abrir fuente oficial]({item['url']})")


def render_triage_station(settings: Settings, profile: dict[str, str]) -> None:
    if not _role_allowed("Estación de triaje", profile["role"]):
        return
    _page_heading("Vista 2", "Estación del personal de triaje", "Rol configurable por establecimiento; no se atribuye una regla universal a MINSA o EsSalud.")
    encounter_id, context = _select_queue_encounter("AWAITING_TRIAGE")
    if not encounter_id or not context:
        return
    patient = context["patient"]
    left, right = st.columns([1.05, 1.4], gap="large")
    with left:
        st.subheader("Datos disponibles")
        st.write(f"**{patient['display_name']}** · {patient['age']} años · {patient['registered_sex']}")
        st.write(f"**Motivo:** {context['chief_complaint']}")
        st.write(context["narrative"])
        st.write(f"**Dolor declarado:** {context['pain_score'] if context['pain_present'] else 'No declarado'}")
        st.write("**Alergias:** " + ", ".join(patient["allergies"]))
        st.write("**Medicación histórica:** " + ", ".join(patient["medications"]))
        st.caption("Fuente: portal demo, seed sintético y antecedentes estructurados; no forman parte del corpus RAG.")
    with right:
        runtime = get_runtime_status(settings.ollama_model)
        render_ai_status(runtime)
        if st.button("Analizar caso con Gemma 4 y RAG", type="primary", use_container_width=True):
            started = time.monotonic()
            activity = st.empty()
            with activity.container():
                render_inference_activity(1, 0.0)
            retriever = LexicalRetriever(limit=4)
            results = retriever.retrieve(context["narrative"] + " triaje emergencia evaluación respiración", population="adult")
            with activity.container():
                render_inference_activity(2, time.monotonic() - started)
            citations = [citation_payload(item) for item in results]
            with activity.container():
                render_inference_activity(3, time.monotonic() - started)
            set_runtime_status(make_status(AIState.ANALYZING, settings.ollama_model, last_result="Gemma está procesando evidencia aprobada.", documents_retrieved=len(results)))
            history = [{"category": "antecedente", "detail": item} for item in patient["allergies"] + patient["medications"]]
            with st.spinner("Gemma 4 está estructurando el relato y consultando la evidencia…"):
                run = process_case(
                    dni=patient["synthetic_identifier"], symptoms=context["narrative"], history=history,
                    settings=settings, retrieved_chunks=citations, role=profile["role"], population="adult",
                )
            with activity.container():
                render_inference_activity(5, time.monotonic() - started)
            duration = time.monotonic() - started
            state = AIState.COMPLETED if run.model_used else AIState.FALLBACK
            message = "Gemma 4 respondió correctamente." if run.model_used else f"Fallback activado: {run.fallback_reason}"
            set_runtime_status(
                make_status(
                    state, run.model_name, duration_seconds=duration, last_result=message,
                    fallback_used=not run.model_used, documents_retrieved=len(results), pydantic_validated=run.model_used,
                )
            )
            save_rag_and_model_run(
                encounter_id,
                [{"source_id": item.chunk.source_id, "chunk_id": item.chunk.chunk_id, "score": item.score, "retrieval_reason": item.retrieval_reason} for item in results],
                {
                    "provider": settings.ai_provider, "model_name": run.model_name, "state": state.value,
                    "model_used": run.model_used, "fallback_reason": run.fallback_reason,
                    "duration_seconds": duration, "validated": run.model_used, "result": run.analysis.model_dump(),
                },
            )
            st.session_state.last_analysis = run
            st.session_state.last_analysis_encounter = encounter_id
            st.session_state.last_rag_results = results
            activity.empty()
            st.rerun()

        run: AnalysisRun | None = st.session_state.get("last_analysis") if st.session_state.get("last_analysis_encounter") == encounter_id else None
        if run:
            render_ai_status(get_runtime_status(settings.ollama_model))
            st.markdown("#### Resultado pendiente de revisión profesional")
            st.write(run.analysis.summary)
            st.caption(f"model_used={str(run.model_used).lower()} · model_name={run.model_name} · protocolo demostrativo={run.analysis.protocol_id}")
            if run.fallback_reason:
                st.warning(run.fallback_reason)
            _render_evidence(st.session_state.get("last_rag_results", []))

    st.divider()
    st.subheader("Signos vitales y decisión profesional")
    st.caption("No se aplican rangos universales. Registre valores y población; los umbrales deben venir de configuración versionada.")
    with st.form(f"triage_{encounter_id}"):
        c1, c2, c3 = st.columns(3)
        systolic = c1.number_input("Presión sistólica", min_value=0, value=None)
        diastolic = c2.number_input("Presión diastólica", min_value=0, value=None)
        heart_rate = c3.number_input("Frecuencia cardiaca", min_value=0, value=None)
        respiratory_rate = c1.number_input("Frecuencia respiratoria", min_value=0, value=None)
        temperature = c2.number_input("Temperatura", min_value=0.0, value=None, step=0.1)
        oxygen = c3.number_input("Saturación de oxígeno", min_value=0, max_value=100, value=None)
        glucose = c1.number_input("Glucosa capilar, si corresponde", min_value=0, value=None)
        consciousness = c2.selectbox("Escala de conciencia configurada", ("No registrada", "Alerta", "Responde a voz", "Responde a dolor", "Sin respuesta"))
        weight = c3.number_input("Peso", min_value=0.0, value=None)
        height = c1.number_input("Talla", min_value=0.0, value=None)
        pain = c2.number_input("Dolor 0–10", min_value=0, max_value=10, value=context["pain_score"])
        population = c3.selectbox("Población", ("adult", "pediatric", "obstetric", "other"))
        proposed = st.text_input("Categoría propuesta para revisión", value="Pendiente de revisión profesional", disabled=True)
        confirmed = st.selectbox("Escala demostrativa de prioridad de 5 niveles", ("Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4", "Nivel 5"))
        decision = st.radio("Decisión profesional", ("aceptar", "modificar", "escalar", "solicitar reevaluación"), horizontal=True)
        justification = st.text_area("Justificación u observación profesional")
        triage_submit = st.form_submit_button("Registrar triaje profesional", type="primary", use_container_width=True)
    if triage_submit:
        if decision != "aceptar" and not justification.strip():
            st.error("La modificación, escalamiento o reevaluación requiere justificación.")
        else:
            save_triage(
                encounter_id,
                {
                    "systolic": systolic, "diastolic": diastolic, "heart_rate": heart_rate,
                    "respiratory_rate": respiratory_rate, "temperature": temperature,
                    "oxygen_saturation": oxygen, "glucose": glucose, "consciousness_scale": consciousness,
                    "weight": weight, "height": height, "pain_score": pain, "population": population,
                },
                {
                    "proposed_level": proposed, "confirmed_level": confirmed, "decision": decision,
                    "justification": justification, "reevaluation_requested": decision == "solicitar reevaluación",
                },
                actor_id=profile["id"],
            )
            st.success("Triaje registrado con trazabilidad; atención pendiente del médico tratante.")


def render_physician_panel(settings: Settings, profile: dict[str, str]) -> None:
    if not _role_allowed("Panel médico", profile["role"]):
        return
    _page_heading("Vista 3", "Panel del médico tratante", "Revisión documental; las decisiones clínicas corresponden exclusivamente al profesional autorizado.")
    encounter_id, context = _select_queue_encounter("AWAITING_PHYSICIAN")
    if not encounter_id or not context:
        return
    patient = context["patient"]
    st.subheader("A. Datos disponibles")
    st.write(f"**{patient['display_name']}** · {patient['age']} años · {patient['registered_sex']} · {patient['insurer']}")
    st.write(f"**Relato:** {context['narrative']}")
    st.json({"alergias": patient["allergies"], "medicacion_historica": patient["medications"], "signos_vitales": context["vitals"], "triaje": context["triage"]})

    missing = []
    if not context["vitals"]:
        missing.append("signos vitales")
    if not context["triage"]:
        missing.append("decisión profesional de triaje")
    if not context.get("duration"):
        missing.append("duración de síntomas")
    st.subheader("B. Datos faltantes")
    st.write(", ".join(missing) if missing else "No se detectaron faltantes configurados en esta etapa.")

    st.subheader("C. Banderas para revisión")
    run = st.session_state.get("last_analysis") if st.session_state.get("last_analysis_encounter") == encounter_id else None
    if run and run.analysis.risk_flags:
        for flag in run.analysis.risk_flags:
            st.warning(flag)
    else:
        st.info("Sin banderas persistidas en la sesión actual; revise el relato y la trazabilidad.")

    st.subheader("D. Evidencia recuperada")
    results = LexicalRetriever(limit=4).retrieve(context["narrative"] + " triaje emergencia evaluación respiración", population="adult")
    _render_evidence(results)
    cited = {result.chunk.source_id for result in results}
    st.json(traceability_metrics(results, cited))

    st.subheader("E. Elementos documentados en fuentes para consideración profesional")
    st.write("La fuente consultada menciona considerar una evaluación inicial estructurada bajo sus condiciones y población. No se emiten órdenes, pruebas ni procedimientos.")
    st.info("Consulte el protocolo institucional y actúe según su competencia.")

    st.subheader("F. Decisiones del profesional")
    with st.form(f"medical_note_{encounter_id}"):
        note = st.text_area("Nota de revisión o decisión profesional", height=120)
        decision = st.selectbox("Tratamiento del elemento documental", ("aceptado para documentación", "no corresponde", "requiere evaluación adicional"))
        justification = st.text_input("Justificación cuando no corresponde o requiere evaluación")
        note_submit = st.form_submit_button("Guardar decisión profesional", use_container_width=True)
    if note_submit:
        if decision != "aceptado para documentación" and not justification.strip():
            st.error("Esta decisión requiere justificación.")
        else:
            save_clinical_note(encounter_id, f"{decision}: {note}. Justificación: {justification}", profile["id"])
            st.success("Decisión profesional registrada.")

    st.subheader("G. Checklist documental")
    missing_fields, can_close = documentary_closure_status(encounter_id)
    if can_close:
        st.success("Campos institucionales configurados completos.")
    else:
        for field in missing_fields:
            st.error(f"Pendiente: {field}")
    if st.button("Cerrar registro demostrativo", disabled=not can_close, type="primary"):
        permitted, reason = close_demo_encounter(encounter_id, profile["id"])
        st.success(reason) if permitted else st.error(reason)

    st.subheader("H. Auditoría")
    events = [item for item in audit_feed(100) if item["encounter_id"] == encounter_id]
    st.dataframe(events, use_container_width=True, hide_index=True)


def render_demo_admin(profile: dict[str, str]) -> None:
    if not _role_allowed("Datos ficticios", profile["role"]):
        return
    _page_heading("Administración", "Datos ficticios", "Migraciones idempotentes y reset limitado al prefijo demo.")
    stats = demo_statistics()
    cols = st.columns(len(stats))
    for column, (label, value) in zip(cols, stats.items()):
        column.metric(label.replace("_", " ").title(), value)
    st.caption("Autenticación demostrativa; no apta para producción. No existen contraseñas en texto plano.")
    if st.button("Sembrar o reparar datos demo"):
        st.success(str(seed_demo_data()))
    if st.button("Reiniciar únicamente datos demo", type="secondary"):
        st.success(str(reset_demo_data()))

    st.subheader("Gobernanza de fuentes")
    register = load_source_register()
    rows = [source.model_dump() for source in register.values()]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_audit(profile: dict[str, str]) -> None:
    if not _role_allowed("Auditoría", profile["role"]):
        return
    _page_heading("Trazabilidad", "Auditoría documental", "Eventos de datos demo, recuperación RAG, ejecución de modelo y decisiones profesionales.")
    rows = audit_feed(200)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    with st.expander("Detalles JSON del evento más reciente"):
        if rows:
            st.json(json.loads(rows[0]["details_json"]))


def render_page(page: str, settings: Settings, profile: dict[str, str]) -> None:
    if page == "Inicio":
        render_home(settings, profile)
    elif page == "Portal del paciente":
        render_patient_portal(settings, profile)
    elif page == "Estación de triaje":
        render_triage_station(settings, profile)
    elif page == "Panel médico":
        render_physician_panel(settings, profile)
    elif page == "Datos ficticios":
        render_demo_admin(profile)
    else:
        render_audit(profile)

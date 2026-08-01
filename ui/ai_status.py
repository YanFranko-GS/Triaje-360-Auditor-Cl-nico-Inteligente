from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from html import escape

import streamlit as st


class AIState(StrEnum):
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    READY = "READY"
    WARMING_UP = "WARMING_UP"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FALLBACK = "FALLBACK"
    ERROR = "ERROR"


LABELS = {
    AIState.OFFLINE: "Sin conexión",
    AIState.STARTING: "Iniciando",
    AIState.READY: "Disponible",
    AIState.WARMING_UP: "Precalentando",
    AIState.ANALYZING: "Analizando",
    AIState.VALIDATING: "Validando JSON",
    AIState.COMPLETED: "Respuesta recibida",
    AIState.FALLBACK: "Fallback activado",
    AIState.ERROR: "Error de conexión",
}


@dataclass
class AIRuntimeStatus:
    state: AIState
    model_name: str
    cpu_mode: bool = True
    duration_seconds: float | None = None
    last_result: str = "Análisis pendiente"
    fallback_used: bool = False
    checked_at: str = ""
    documents_retrieved: int = 0
    pydantic_validated: bool = False

    def to_session(self) -> dict[str, object]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


def make_status(state: AIState, model_name: str, **changes: object) -> AIRuntimeStatus:
    return AIRuntimeStatus(state=state, model_name=model_name, checked_at=datetime.now().isoformat(timespec="seconds"), **changes)


def set_runtime_status(status: AIRuntimeStatus) -> None:
    st.session_state.ai_runtime_status = status.to_session()


def get_runtime_status(model_name: str) -> AIRuntimeStatus:
    raw = st.session_state.get("ai_runtime_status")
    if not raw:
        return make_status(AIState.STARTING, model_name)
    return AIRuntimeStatus(**{**raw, "state": AIState(raw["state"])})


def render_ai_status(status: AIRuntimeStatus) -> None:
    state_class = status.state.value.casefold()
    duration = "—" if status.duration_seconds is None else f"{status.duration_seconds:.2f} s"
    validation = "Aprobada" if status.pydantic_validated else "Pendiente"
    st.markdown(
        f"""
        <section class="ai-runtime ai-runtime--{state_class}" aria-live="polite" aria-label="Estado de Gemma 4">
          <div class="ai-runtime__headline"><span class="ai-runtime__dot"></span><b>{escape(LABELS[status.state])}</b></div>
          <div class="ai-runtime__grid">
            <span>Modelo <b>{escape(status.model_name)}</b></span><span>Modo <b>CPU</b></span>
            <span>Duración <b>{duration}</b></span><span>Documentos <b>{status.documents_retrieved}</b></span>
            <span>Validación Pydantic <b>{validation}</b></span><span>Comprobación <b>{escape(status.checked_at or 'pendiente')}</b></span>
          </div>
          <div class="ai-runtime__result">{escape(status.last_result)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_inference_activity(stage: int, elapsed_seconds: float = 0.0) -> None:
    stages = (
        "Preparando contexto",
        "Consultando RAG",
        "Generando salida estructurada",
        "Validando JSON",
        "Aplicando reglas deterministas",
    )
    items = "".join(
        f'<li class="{"active" if index == stage else "done" if index < stage else ""}">{index}. {escape(label)}</li>'
        for index, label in enumerate(stages, 1)
    )
    st.markdown(
        f"""
        <section class="ai-activity" aria-live="polite">
          <div class="ai-activity__bar"><span></span></div>
          <b>Gemma 4 está estructurando el relato y consultando la evidencia…</b>
          <p>Tiempo transcurrido: {elapsed_seconds:.1f} s · progreso por etapas, no porcentaje clínico.</p>
          <ol>{items}</ol>
        </section>
        """,
        unsafe_allow_html=True,
    )

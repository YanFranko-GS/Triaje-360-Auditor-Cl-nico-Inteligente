"""Componentes HTML pequeños y accesibles para TRIaje 360."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st


def _safe(value: Any) -> str:
    return escape(str(value))


ROOT = Path(__file__).resolve().parents[1]


def _image_data(path: Path) -> str | None:
    if not path.is_file():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_brand_header() -> None:
    kutan = _image_data(ROOT / "logos" / "Nosotros_KutanLAB.png")
    gemma = _image_data(ROOT / "logos" / "GEMA.png")
    left = f'<img src="{kutan}" alt="Logo KutanLab">' if kutan else '<span class="brand-fallback">KutanLab</span>'
    right = f'<img src="{gemma}" alt="Isotipo Gemma 4">' if gemma else '<span class="brand-fallback">Gemma 4</span>'
    st.markdown(
        f"""
        <header class="brand-header">
          <div class="brand-header__logo">{left}</div>
          <div class="brand-header__copy">
            <h1>TRIaje <span>360</span> — Auditor Clínico Inteligente</h1>
            <p>Apoyo a la completitud documental y recuperación de evidencia clínica</p>
            <span class="pill pill--warn">Prototipo educativo — datos ficticios</span>
          </div>
          <div class="brand-header__powered"><small>Powered by Gemma 4</small>{right}</div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_header(*, ollama_ready: bool, model_ready: bool, model_name: str) -> None:
    ollama_class = "ok" if ollama_ready else "off"
    model_class = "ok" if model_ready else "warn"
    ollama_text = "Ollama conectado" if ollama_ready else "Ollama sin conexión"
    model_text = f"{model_name} disponible" if model_ready else f"{model_name} pendiente"
    st.markdown(
        f"""
        <header class="hero" aria-label="Encabezado de TRIaje 360">
          <div class="hero__identity">
            <div class="hero__mark" aria-hidden="true">🩺</div>
            <div>
              <h1 class="hero__brand">TRIaje <span>360</span></h1>
              <p class="hero__title">Auditor Clínico Inteligente</p>
              <p class="hero__subtitle">Auditoría concurrente de completitud documental con Gemma 4</p>
            </div>
          </div>
          <div class="hero__meta">
            <span class="pill pill--info">KutanLab</span>
            <span class="pill pill--warn">Prototipo educativo</span>
            <span class="pill pill--{ollama_class}">{ollama_text}</span>
            <span class="pill pill--{model_class}">{_safe(model_text)}</span>
            <span class="pill pill--info">CPU · GPU 0</span>
          </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_system_status(*, reachable: bool, model_available: bool, model_name: str) -> None:
    ollama_value = "Conectado" if reachable else "Sin conexión"
    ollama_dot = "" if reachable else " status-dot--off"
    model_value = model_name if model_available else f"{model_name} no detectado"
    model_dot = "" if model_available else " status-dot--warn"
    st.markdown(
        f"""
        <section class="status-grid" aria-label="Estado del sistema">
          <div class="status-card"><div class="status-card__label">Estado de Ollama</div><div class="status-card__value"><span class="status-dot{ollama_dot}"></span>{_safe(ollama_value)}</div></div>
          <div class="status-card"><div class="status-card__label">Modelo activo</div><div class="status-card__value"><span class="status-dot{model_dot}"></span>{_safe(model_value)}</div></div>
          <div class="status-card"><div class="status-card__label">Motor de seguridad</div><div class="status-card__value"><span class="status-dot"></span>Pydantic + reglas</div></div>
          <div class="status-card"><div class="status-card__label">Base de datos</div><div class="status-card__value"><span class="status-dot"></span>SQLite local</div></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_progress_steps(active: int) -> None:
    labels = ("Admisión", "Análisis con Gemma", "Verificación", "Cierre documental")
    parts = []
    for number, label in enumerate(labels, 1):
        state = "done" if number < active else "active" if number == active else "pending"
        parts.append(
            f'<div class="step step--{state}"><span class="step__number">{number}</span><span>{label}</span></div>'
        )
    st.markdown(f'<nav class="steps" aria-label="Etapas del flujo">{"".join(parts)}</nav>', unsafe_allow_html=True)


def render_patient_card(patient: dict[str, Any]) -> None:
    history = patient.get("history", [])
    tags = "".join(f'<span class="history-tag">{_safe(item["detail"])}</span>' for item in history)
    st.markdown(
        f"""
        <section class="patient-card" aria-label="Ficha del paciente ficticio">
          <div class="patient-name">{_safe(patient['name'])}</div>
          <div class="patient-meta">DNI ficticio {_safe(patient['dni'])} · {_safe(patient['sex'])} · {_safe(patient['age'])} años</div>
          <div class="history-tags">{tags}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_empty_clinical_panel() -> None:
    st.markdown(
        """
        <section class="empty-state" aria-label="Auditoría pendiente">
          <div class="empty-state__icon" aria-hidden="true">📋</div>
          <h3>Esperando análisis del caso</h3>
          <p>Complete la admisión ficticia. Aquí aparecerán la prioridad documental, las banderas de revisión y el protocolo demostrativo.</p>
          <div class="empty-steps">
            <div class="empty-step"><b>1 · Registrar</b>Ingrese el relato transcrito.</div>
            <div class="empty-step"><b>2 · Estructurar</b>Gemma 4 genera JSON validado.</div>
            <div class="empty-step"><b>3 · Verificar</b>Complete el checklist obligatorio.</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_engine_banner(*, model_used: bool, model_name: str, fallback_reason: str | None) -> None:
    if model_used:
        st.markdown(
            f'<div class="engine-banner engine-banner--real">● Gemma real confirmado · {_safe(model_name)} respondió y su JSON fue validado.</div>',
            unsafe_allow_html=True,
        )
    else:
        reason = fallback_reason or "Análisis determinista solicitado"
        st.markdown(
            f'<div class="engine-banner engine-banner--fallback">● Respaldo determinista activo · {_safe(reason)}</div>',
            unsafe_allow_html=True,
        )


def render_disclaimer() -> None:
    st.markdown(
        '<aside class="notice"><b>Uso educativo.</b> Este sistema no diagnostica, no prescribe y no sustituye el juicio profesional ni los protocolos institucionales. Use únicamente datos ficticios.</aside>',
        unsafe_allow_html=True,
    )

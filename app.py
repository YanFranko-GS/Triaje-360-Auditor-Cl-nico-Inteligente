from __future__ import annotations

import streamlit as st

from clinical_db import demo_profiles, migrate_demo_schema, seed_demo_data
from config import load_settings
from database import initialize
from rag.ingest import ingest_approved_sources
from services.ai_provider import provider_status
from ui.ai_status import AIState, make_status, set_runtime_status
from ui.components import render_brand_header
from ui.pages import render_page
from ui.theme import load_styles


PAGES = ("Inicio", "Portal del paciente", "Estación de triaje", "Panel médico", "Datos ficticios", "Auditoría")

st.set_page_config(
    page_title="TRIaje 360 | KutanLab",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

settings = load_settings()
initialize()
migrate_demo_schema()
seed_demo_data()
ingest_approved_sources()
load_styles()

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Inicio"
if "ai_runtime_status" not in st.session_state:
    status = provider_status(settings)
    initial_state = AIState.READY if status.model_available else AIState.OFFLINE if not status.reachable else AIState.ERROR
    set_runtime_status(make_status(initial_state, settings.ollama_model, last_result=status.detail))

profiles = demo_profiles()
profile_labels = {item["id"]: f"{item['display_name']} · {item['role']}" for item in profiles}

with st.sidebar:
    st.title("TRIaje 360")
    st.caption("Autenticación demostrativa; no apta para producción")
    selected_profile = st.selectbox("Perfil demo", list(profile_labels), format_func=lambda key: profile_labels[key])
    profile = next(item for item in profiles if item["id"] == selected_profile)
    page = st.radio("Navegación", PAGES, key="nav_page")
    st.divider()
    st.caption("Ollama permanece en 127.0.0.1. Acceso LAN desactivado por defecto.")
    st.caption("KutanLab · Daniel Ríos · Yan Franco Gonzales Segura · Jhon Gesell Villanueva Portella")

render_brand_header()
render_page(page, settings, profile)

st.divider()
st.caption("TRIaje 360 · Prototipo educativo con datos ficticios · No constituye diagnóstico, prescripción ni indicación médica.")

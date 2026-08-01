from __future__ import annotations

import streamlit as st

from auth_service import AuthPrincipal, logout, seed_demo_accounts
from clinical_db import migrate_demo_schema, seed_demo_data
from config import load_settings
from database import initialize
from rag.ingest import ingest_approved_sources
from services.ai_provider import provider_status
from ui.ai_status import AIState, make_status, set_runtime_status
from ui.auth import render_login
from ui.layout import render_application_header, render_footer
from ui.navigation import allowed_pages_for, apply_requested_navigation, request_logout
from ui.pages import render_audit, render_demo_admin, render_home
from ui.patient_portal import render_patient_portal, render_patient_tracking
from ui.physician_workspace import render_physician_workspace
from ui.theme import load_styles
from ui.triage_workspace import render_triage_workspace


st.set_page_config(
    page_title="TRIaje 360 | KutanLab",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": "TRIaje 360 · entorno de validación"},
)

settings = load_settings()
initialize()
migrate_demo_schema()
seed_demo_data()
seed_demo_accounts()
ingest_approved_sources()
load_styles()

if "ai_runtime_status" not in st.session_state:
    status = provider_status(settings)
    initial_state = AIState.READY if status.model_available else AIState.OFFLINE if not status.reachable else AIState.ERROR
    set_runtime_status(make_status(initial_state, settings.ollama_model, last_result=status.detail))

principal: AuthPrincipal | None = st.session_state.get("auth_principal")
if st.session_state.pop("logout_requested", False) and principal:
    logout(principal)
    for key in tuple(st.session_state):
        if key not in {"ai_runtime_status"}:
            st.session_state.pop(key, None)
    principal = None

if principal is None:
    st.markdown("<style>section[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)
    render_login()
    st.stop()

allowed_pages = allowed_pages_for(principal.role)
default_page = "Portal del paciente" if principal.role == "PATIENT" else "Inicio"
apply_requested_navigation(st.session_state, allowed_pages=allowed_pages, default=default_page)

with st.sidebar:
    st.markdown("## TRIaje 360")
    st.caption(principal.display_name)
    st.caption(principal.role.replace("_", " ").title())
    page = st.radio("Navegación", allowed_pages, key="nav_page")
    st.divider()
    st.button(
        "Cerrar sesión", key="logout_button", use_container_width=True,
        on_click=request_logout, args=(st.session_state,),
    )
    st.caption("Acceso local · información sintética")

render_application_header(principal)
profile = {"id": principal.user_id, "display_name": principal.display_name, "role": principal.role}

if page == "Inicio":
    render_home(settings, profile)
elif page == "Portal del paciente":
    render_patient_portal(settings, principal)
elif page == "Seguimiento":
    render_patient_tracking(principal)
elif page == "Estación de triaje":
    render_triage_workspace(settings, profile)
elif page == "Panel médico":
    render_physician_workspace(settings, profile)
elif page == "Datos ficticios":
    render_demo_admin(profile)
elif page == "Auditoría":
    render_audit(profile)

render_footer()

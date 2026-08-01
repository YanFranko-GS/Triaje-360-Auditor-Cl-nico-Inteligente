from __future__ import annotations

from datetime import date

import streamlit as st

from auth_service import AuthPrincipal, authenticate_patient, authenticate_professional
from ui.components import render_brand_header


FACILITIES = {
    "DEMO_FAC_A": "Centro de validación Andino",
    "DEMO_FAC_B": "Policlínico de validación Costa",
}


def render_login() -> AuthPrincipal | None:
    render_brand_header(login=True)
    st.markdown(
        """
        <section class="login-intro">
          <div class="section-kicker">Acceso seguro</div>
          <h1>Asistencia inteligente para admisión y completitud clínica</h1>
          <p>Captura estructurada, triaje supervisado y trazabilidad documental.</p>
          <span>Entorno de validación — datos sintéticos</span>
        </section>
        """,
        unsafe_allow_html=True,
    )
    patient_tab, staff_tab = st.tabs(("Acceso paciente", "Acceso personal sanitario"))
    with patient_tab:
        with st.form("patient_login_form"):
            identifier = st.text_input("Identificador sintético", max_chars=16, autocomplete="off")
            birth_date = st.date_input(
                "Segundo dato de validación", value=date(1999, 1, 1), min_value=date(1920, 1, 1), max_value=date.today()
            )
            submitted = st.form_submit_button("Ingresar al portal", type="primary", use_container_width=True)
        if submitted:
            principal = authenticate_patient(identifier, birth_date.isoformat())
            if principal:
                st.session_state.auth_principal = principal
                st.session_state.requested_page = "Portal del paciente"
                st.rerun()
            st.error("No se pudo validar el acceso con los datos sintéticos proporcionados.")
    with staff_tab:
        with st.form("staff_login_form"):
            username = st.text_input("Usuario", autocomplete="username")
            password = st.text_input("Contraseña", type="password", autocomplete="current-password")
            facility = st.selectbox("Establecimiento", tuple(FACILITIES), format_func=FACILITIES.get)
            submitted = st.form_submit_button("Ingresar al espacio clínico", type="primary", use_container_width=True)
        if submitted:
            principal = authenticate_professional(username, password, facility)
            if principal:
                st.session_state.auth_principal = principal
                st.session_state.requested_page = "Inicio"
                st.rerun()
            st.error("Credenciales o establecimiento no válidos.")
    st.caption("Acceso de validación con información sintética. No utilice credenciales ni datos personales reales.")
    return None

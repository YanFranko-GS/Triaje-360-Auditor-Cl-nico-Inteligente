from __future__ import annotations

from datetime import date

import streamlit as st

from auth_service import AuthPrincipal, authenticate_patient, authenticate_professional
from clinical_db import patient_by_identifier
from longitudinal_db import INSURANCE_TYPES, REGISTERED_SEX_VALUES, register_patient
from ui.components import render_brand_header


FACILITIES = {"DEMO_FAC_A": "Centro Andino", "DEMO_FAC_B": "Policlínico Costa"}


def render_login() -> AuthPrincipal | None:
    render_brand_header(login=True)
    st.markdown(
        """
        <section class="login-intro">
          <div class="section-kicker">Acceso seguro</div>
          <h1>Plataforma inteligente de admisión, triaje y continuidad clínica</h1>
          <p>Captura estructurada, triaje supervisado y trazabilidad documental.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    patient_tab, registration_tab, staff_tab = st.tabs(
        ("Paciente existente", "Registrar nuevo paciente", "Personal sanitario")
    )
    with patient_tab:
        _render_existing_patient_login()
    with registration_tab:
        _render_patient_registration()
    with staff_tab:
        _render_professional_login()
    st.caption("Entorno de validación con información sintética. No sustituye el juicio clínico.")
    return None


def _render_existing_patient_login() -> None:
    pending_identifier = st.session_state.get("pending_patient_identifier")
    if not pending_identifier:
        with st.form("patient_lookup_form"):
            identifier = st.text_input("DNI sintético", max_chars=8, autocomplete="off", placeholder="8 dígitos")
            lookup = st.form_submit_button("Continuar", type="primary", use_container_width=True)
        if lookup:
            patient = patient_by_identifier(identifier.strip())
            if patient:
                st.session_state.pending_patient_identifier = identifier.strip()
                st.rerun()
            st.error("No se encontró un paciente con ese DNI sintético.")
        return
    patient = patient_by_identifier(pending_identifier)
    if not patient:
        st.session_state.pop("pending_patient_identifier", None)
        st.error("El registro ya no está disponible.")
        return
    st.success(f"Identidad recuperada: {patient['display_name']} · {patient['age']} años")
    with st.form("patient_login_form"):
        birth_date = st.date_input(
            "Confirme su fecha de nacimiento", value=date(1999, 1, 1),
            min_value=date(1920, 1, 1), max_value=date.today(),
        )
        submitted = st.form_submit_button("Ingresar al portal", type="primary", use_container_width=True)
    if submitted:
        principal = authenticate_patient(pending_identifier, birth_date.isoformat())
        if principal:
            st.session_state.pop("pending_patient_identifier", None)
            st.session_state.auth_principal = principal
            st.session_state.requested_page = "Portal del paciente"
            st.rerun()
        st.error("No se pudo confirmar el acceso.")
    if st.button("Usar otro DNI", use_container_width=True):
        st.session_state.pop("pending_patient_identifier", None)
        st.rerun()


def _render_patient_registration() -> None:
    st.caption("Use exclusivamente identidades sintéticas creadas para este entorno.")
    with st.form("new_patient_registration"):
        c1, c2 = st.columns(2)
        dni = c1.text_input("DNI sintético *", max_chars=8)
        birth_date = c2.date_input("Fecha de nacimiento *", value=date(1990, 1, 1), min_value=date(1900, 1, 1), max_value=date.today())
        given_names = c1.text_input("Nombres *")
        family_names = c2.text_input("Apellidos *")
        registered_sex = c1.selectbox("Sexo registrado *", REGISTERED_SEX_VALUES)
        phone = c2.text_input("Teléfono *")
        email = c1.text_input("Correo opcional")
        address = c2.text_input("Dirección opcional")
        emergency_contact = st.text_input("Contacto de emergencia *")
        insurance_type = c1.selectbox("Aseguramiento *", INSURANCE_TYPES)
        facility_id = c2.selectbox("Establecimiento *", tuple(FACILITIES), format_func=FACILITIES.get)
        allergies = st.text_area("Alergias conocidas", placeholder="Separe varios elementos con comas")
        medications = st.text_area("Medicamentos habituales", placeholder="Separe varios elementos con comas")
        history = st.text_area("Antecedentes relevantes")
        consent = st.checkbox("Confirmo el consentimiento para crear este registro sintético *")
        create = st.form_submit_button("Crear registro seguro", type="primary", use_container_width=True)
    if create:
        try:
            created = register_patient({
                "dni": dni, "given_names": given_names, "family_names": family_names,
                "birth_date": birth_date.isoformat(), "registered_sex": registered_sex,
                "phone": phone, "email": email, "address": address,
                "emergency_contact": emergency_contact, "insurance_type": insurance_type,
                "facility_id": facility_id, "allergies": allergies, "medications": medications,
                "history": history, "consent": consent,
            })
            st.success(f"Registro creado para {created['name']}. Ya puede ingresar como paciente existente.")
        except ValueError as exc:
            st.error(str(exc))


def _render_professional_login() -> None:
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

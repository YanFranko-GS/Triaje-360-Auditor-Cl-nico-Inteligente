from __future__ import annotations

import streamlit as st

from auth_service import AuthPrincipal
from ui.components import render_brand_header


def render_application_header(principal: AuthPrincipal) -> None:
    render_brand_header(login=False)
    st.markdown(
        f'<div class="session-strip"><span>{principal.display_name}</span><span>{principal.role}</span><span>Acceso seguro</span></div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        '<footer class="clinical-footer">Entorno de validación con información sintética. No sustituye el juicio clínico.</footer>',
        unsafe_allow_html=True,
    )

from __future__ import annotations

import streamlit as st

from auth_service import AuthPrincipal
from ui.components import render_brand_header


def render_application_header(principal: AuthPrincipal) -> None:
    render_brand_header(login=False)
    st.markdown(
        f'<div class="session-strip"><span>{principal.display_name}</span><span>{principal.role}</span><span>Entorno de validación — datos sintéticos</span></div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        '<footer class="clinical-footer">TRIaje 360 · Validación con datos sintéticos · Las decisiones corresponden al personal autorizado.</footer>',
        unsafe_allow_html=True,
    )

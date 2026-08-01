"""Tema institucional y portable para la interfaz Streamlit."""

from pathlib import Path

import streamlit as st


STYLES_PATH = Path(__file__).with_name("styles.css")


def load_styles() -> None:
    """Carga los estilos locales sin JavaScript ni recursos externos."""
    st.markdown(f"<style>{STYLES_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

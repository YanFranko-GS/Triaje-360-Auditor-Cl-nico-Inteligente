from __future__ import annotations

from pathlib import Path

from ui.navigation import apply_requested_navigation, request_navigation


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")
PAGES_SOURCE = (ROOT / "ui" / "pages.py").read_text(encoding="utf-8")


def test_requested_navigation_is_applied_before_widget_creation() -> None:
    state = {"nav_page": "Inicio"}
    request_navigation(state, "Portal del paciente")
    assert state == {"nav_page": "Inicio", "requested_page": "Portal del paciente"}

    apply_requested_navigation(state, allowed_pages=("Inicio", "Portal del paciente"))
    assert state == {"nav_page": "Portal del paciente"}


def test_start_tour_never_mutates_nav_widget_key_after_instantiation() -> None:
    assert 'st.session_state.nav_page = "Portal del paciente"' not in PAGES_SOURCE
    assert 'st.session_state["nav_page"] = "Portal del paciente"' not in PAGES_SOURCE
    assert "apply_requested_navigation" in APP_SOURCE
    assert APP_SOURCE.index("apply_requested_navigation") < APP_SOURCE.index('st.radio("Navegación"')


def test_invalid_browser_history_target_falls_back_safely() -> None:
    state = {"nav_page": "Inicio", "requested_page": "Ruta inexistente"}
    apply_requested_navigation(state, allowed_pages=("Inicio", "Portal del paciente"))
    assert state == {"nav_page": "Inicio"}

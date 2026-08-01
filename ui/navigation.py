from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from typing import Any


ROLE_PAGES = {
    "PATIENT": ("Portal del paciente", "Seguimiento"),
    "TRIAGE_NURSE": ("Inicio", "Estación de triaje"),
    "TRIAGE_DOCTOR": ("Inicio", "Estación de triaje"),
    "ATTENDING_PHYSICIAN": ("Inicio", "Panel médico"),
    "SUPERVISOR": ("Inicio", "Panel médico", "Auditoría"),
    "ADMIN": ("Inicio", "Portal del paciente", "Estación de triaje", "Panel médico", "Datos ficticios", "Auditoría"),
}


def request_navigation(state: MutableMapping[str, Any], target: str) -> None:
    """Queue navigation without mutating a key owned by an instantiated widget."""
    state["requested_page"] = target


def apply_requested_navigation(
    state: MutableMapping[str, Any], *, allowed_pages: Sequence[str], default: str = "Inicio"
) -> str:
    """Apply a queued target before the navigation widget is constructed."""
    allowed = tuple(allowed_pages)
    if not allowed:
        raise ValueError("allowed_pages no puede estar vacío")
    fallback = default if default in allowed else allowed[0]
    requested = state.pop("requested_page", None)
    current = state.get("nav_page", fallback)
    state["nav_page"] = requested if requested in allowed else current if current in allowed else fallback
    return str(state["nav_page"])


def allowed_pages_for(role: str) -> tuple[str, ...]:
    return ROLE_PAGES.get(role, ("Inicio",))


def request_logout(state: MutableMapping[str, Any]) -> None:
    state["logout_requested"] = True

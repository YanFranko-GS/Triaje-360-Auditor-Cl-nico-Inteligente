from __future__ import annotations

from config import Settings
from ui.pages import render_triage_station


def render_triage_workspace(settings: Settings, profile: dict[str, str]) -> None:
    render_triage_station(settings, profile)

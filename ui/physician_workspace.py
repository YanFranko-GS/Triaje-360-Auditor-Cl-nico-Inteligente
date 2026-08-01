from __future__ import annotations

from config import Settings
from ui.pages import render_physician_panel


def render_physician_workspace(settings: Settings, profile: dict[str, str]) -> None:
    render_physician_panel(settings, profile)

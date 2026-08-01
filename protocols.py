from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

PROTOCOL_PATH = Path(__file__).parent / "data" / "protocols.json"
ALLOWED_PROTOCOL_IDS = frozenset({"respiratory_alert", "general_review"})


def load_protocols(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        protocols = json.load(source)
    if set(protocols) != ALLOWED_PROTOCOL_IDS:
        raise ValueError("El catálogo debe contener únicamente los protocolos autorizados.")
    return protocols


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def select_protocol(symptoms: str, model_protocol_id: str | None = None) -> tuple[str, dict[str, Any]]:
    protocols = load_protocols()
    if model_protocol_id in ALLOWED_PROTOCOL_IDS:
        return model_protocol_id, protocols[model_protocol_id]

    normalized = _normalize(symptoms)
    respiratory = protocols["respiratory_alert"]
    if any(_normalize(trigger) in normalized for trigger in respiratory["triggers"]):
        return "respiratory_alert", respiratory
    return "general_review", protocols["general_review"]


def is_action_complete(action: dict[str, Any], value: Any) -> bool:
    action_type = action["type"]
    if action_type == "checkbox":
        return value is True
    if action_type == "number":
        if value is None or isinstance(value, bool):
            return False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        return action.get("min", float("-inf")) <= numeric <= action.get("max", float("inf"))
    return bool(str(value or "").strip())


def completion_status(protocol: dict[str, Any], values: dict[str, Any]) -> tuple[int, int, bool]:
    actions = protocol["required_actions"]
    completed = sum(is_action_complete(action, values.get(action["id"])) for action in actions)
    return completed, len(actions), completed == len(actions)

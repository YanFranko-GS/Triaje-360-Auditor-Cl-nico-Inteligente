from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from config import Settings, load_settings
from services.ollama_client import OllamaError, OllamaStatus, check_ollama


@dataclass(frozen=True)
class ProbeResult:
    status: OllamaStatus
    responded: bool
    model_name: str
    duration_seconds: float
    detail: str


def provider_status(settings: Settings | None = None) -> OllamaStatus:
    settings = settings or load_settings()
    if settings.ai_provider == "hosted":
        return OllamaStatus(False, False, settings.ollama_model, (), False, "Proveedor hosted documentado pero no configurado en el MVP local.")
    return check_ollama(settings)


def probe_provider(settings: Settings | None = None) -> ProbeResult:
    settings = settings or load_settings()
    status = provider_status(settings)
    if settings.ai_provider != "ollama" or not status.model_available:
        return ProbeResult(status, False, settings.ollama_model, 0.0, status.detail)
    started = time.monotonic()
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": "Responde únicamente: LISTO",
                "stream": False,
                "think": False,
                "keep_alive": settings.ollama_keep_alive,
                "options": {"temperature": 0, "num_predict": 8, "num_ctx": 512, "num_gpu": settings.ollama_num_gpu},
            },
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OllamaError(f"La comprobación mínima de Gemma falló: {exc}") from exc
    duration = time.monotonic() - started
    model = body.get("model", "")
    responded = model == settings.ollama_model and bool(str(body.get("response", "")).strip())
    detail = "Gemma 4 respondió correctamente." if responded else "La respuesta mínima no pudo validarse."
    return ProbeResult(status, responded, model or settings.ollama_model, duration, detail)

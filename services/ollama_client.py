from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import ValidationError

from config import Settings, load_settings
from schemas import GemmaAnalysis


class OllamaError(RuntimeError):
    """Error seguro y esperable que activa el respaldo determinista."""


@dataclass(frozen=True)
class OllamaStatus:
    installed: bool
    reachable: bool
    configured_model: str
    available_models: tuple[str, ...]
    model_available: bool
    detail: str


def check_ollama(settings: Settings | None = None) -> OllamaStatus:
    settings = settings or load_settings()
    try:
        response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=min(settings.ollama_timeout_seconds, 5))
        response.raise_for_status()
        names = tuple(item.get("name", "") for item in response.json().get("models", []))
    except (requests.RequestException, ValueError) as exc:
        return OllamaStatus(False, False, settings.ollama_model, (), False, f"Ollama no responde: {exc}")
    available = settings.ollama_model in names
    detail = "Ollama y el modelo configurado están disponibles." if available else f"Falta el modelo {settings.ollama_model}."
    return OllamaStatus(True, True, settings.ollama_model, names, available, detail)


def _extract_json(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise OllamaError("Ollama devolvió una respuesta vacía.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OllamaError("Gemma no devolvió exclusivamente un objeto JSON válido.") from exc
    if not isinstance(parsed, dict):
        raise OllamaError("La salida de Gemma debe ser un objeto JSON.")
    return parsed


def validate_analysis(payload: dict[str, Any]) -> GemmaAnalysis:
    try:
        return GemmaAnalysis.model_validate(payload)
    except ValidationError as exc:
        raise OllamaError(f"La salida estructurada de Gemma fue rechazada: {exc.errors()[0]['msg']}") from exc


def analyze_case(
    symptoms: str, history: list[dict[str, Any]], settings: Settings | None = None,
) -> tuple[GemmaAnalysis, str]:
    settings = settings or load_settings()
    status = check_ollama(settings)
    if not status.reachable:
        raise OllamaError(status.detail)
    if not status.model_available:
        raise OllamaError(f"El modelo configurado {settings.ollama_model} no está instalado. Ejecute: ollama pull {settings.ollama_model}")

    system_prompt = (
        "Eres un asistente de auditoría concurrente de completitud documental para un prototipo educativo. "
        "No diagnostiques, prescribas, recomiendes medicamentos ni inventes datos. "
        "REGLA PRIORITARIA: si el relato contiene falta de aire, dificultad para respirar o dolor al respirar, "
        "protocol_id DEBE ser respiratory_alert. Usa general_review solo cuando no exista ninguna manifestación respiratoria. "
        "Cuando protocol_id sea respiratory_alert, risk_flags DEBE contener al menos una observación breve para revisión profesional. "
        "Ejemplo: 'me falta el aire y tengo dolor al respirar' siempre activa respiratory_alert. "
        "Resume únicamente el relato y antecedentes recibidos. Incluye los cinco campos requeridos por el esquema. "
        "El disclaimer debe ser exactamente 'No constituye diagnóstico ni indicación médica.'. "
        "No incluyas markdown, razonamiento interno ni campos adicionales."
    )
    user_prompt = json.dumps({"relato": symptoms, "antecedentes_ficticios": history}, ensure_ascii=False)
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "think": False,
        "format": GemmaAnalysis.model_json_schema(),
        "keep_alive": settings.ollama_keep_alive,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "options": {
            "temperature": 0.1,
            "num_predict": settings.ollama_num_predict,
            "num_ctx": settings.ollama_num_ctx,
            "num_gpu": settings.ollama_num_gpu,
        },
    }
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/chat", json=payload, timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
    except requests.Timeout as exc:
        raise OllamaError(f"Ollama excedió el tiempo límite de {settings.ollama_timeout_seconds} segundos.") from exc
    except (requests.RequestException, ValueError) as exc:
        raise OllamaError(f"No se pudo obtener una respuesta válida de Ollama: {exc}") from exc

    response_model = body.get("model")
    if not response_model or response_model != settings.ollama_model:
        raise OllamaError("Ollama no identificó correctamente el modelo utilizado.")
    content = body.get("message", {}).get("content", "")
    return validate_analysis(_extract_json(content)), response_model


def fallback_analysis(symptoms: str) -> GemmaAnalysis:
    normalized = symptoms.casefold()
    terms = ("falta de aire", "falta el aire", "dificultad para respirar", "dolor al respirar", "no puedo respirar", "respirar")
    respiratory = any(term in normalized for term in terms)
    flags = ["El relato contiene una manifestación respiratoria para revisión profesional."] if respiratory else []
    return GemmaAnalysis(
        summary=(symptoms.strip() or "Relato no disponible.")[:500],
        risk_flags=flags,
        protocol_id="respiratory_alert" if respiratory else "general_review",
        reason="Selección realizada mediante reglas cerradas del respaldo determinista.",
        disclaimer="No constituye diagnóstico ni indicación médica.",
    )

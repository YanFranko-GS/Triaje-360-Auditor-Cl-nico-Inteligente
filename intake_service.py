from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import ValidationError

from config import Settings, load_settings
from schemas import CapturedField, IntakeExtraction


FOLLOWUP_QUESTIONS = {
    "duration": "¿Desde cuándo presenta estos síntomas?",
    "pain_score": "En una escala de 0 a 10, ¿cuánto dolor siente ahora?",
    "onset": "¿El malestar comenzó de forma súbita o gradual?",
    "allergies": "¿Tiene alguna alergia conocida?",
    "usual_medications": "¿Toma medicamentos de manera habitual?",
    "evolution": "¿Los síntomas están mejorando, empeorando o siguen igual?",
    "location": "¿En qué parte del cuerpo siente el malestar principal?",
    "accompanying_symptoms": "¿Presenta dificultad respiratoria, pérdida de conciencia, sangrado, sudoración, náuseas o mareo?",
    "relevant_history": "¿Tiene antecedentes relevantes que debamos comunicar al personal?",
}


@dataclass(frozen=True)
class IntakeRun:
    extraction: IntakeExtraction
    model_used: bool
    model_name: str
    fallback_reason: str | None = None
    duration_seconds: float = 0.0


def _field(value: Any, source: str, confirmed: bool = False) -> CapturedField:
    missing = value is None or value == "" or value == []
    return CapturedField(
        value=None if missing else value,
        source=source,
        confidence_status="missing" if missing else "confirmed" if confirmed else "inferred_for_review",
        requires_confirmation=not confirmed,
    )


def fallback_extract_intake(text: str, source: str = "patient_text") -> IntakeExtraction:
    normalized = text.casefold()
    pain_present = any(term in normalized for term in ("dolor", "duele", "molestia"))
    score_match = re.search(r"(?:dolor|escala)\D{0,12}(10|[0-9])(?:\s*(?:de|/)?\s*10)?", normalized)
    duration_match = re.search(r"(?:desde hace|hace|desde)\s+([^.,;]{2,40})", text, flags=re.IGNORECASE)
    immediate = []
    if any(term in normalized for term in ("me falta el aire", "dificultad respiratoria", "no puedo respirar")):
        immediate.append("Manifestación respiratoria declarada; requiere revisión inmediata del personal.")
    values = {
        "chief_complaint": text[:240] if text.strip() else None,
        "onset": "súbito" if "súbit" in normalized else "gradual" if "gradual" in normalized else None,
        "duration": duration_match.group(1).strip() if duration_match else None,
        "evolution": "empeorando" if "empeor" in normalized else "mejorando" if "mejor" in normalized else None,
        "location": None,
        "pain_present": pain_present,
        "pain_score": int(score_match.group(1)) if score_match else None,
        "accompanying_symptoms": [],
        "allergies": [],
        "usual_medications": [],
        "relevant_history": [],
        "immediate_review_signals": immediate,
    }
    fields = {name: _field(value, source) for name, value in values.items()}
    missing = [name for name, field in fields.items() if field.confidence_status == "missing"]
    return IntakeExtraction(**fields, missing_fields=missing)


def extract_intake(text: str, source: str = "patient_text", settings: Settings | None = None) -> IntakeRun:
    settings = settings or load_settings()
    started = time.monotonic()
    system = (
        "Extrae únicamente información explícita del relato sintético. No diagnostiques, prescribas ni inventes. "
        "Cada campo no explícito debe usar value=null, confidence_status=missing y requires_confirmation=true. "
        "Los valores extraídos del relato usan inferred_for_review hasta que el paciente o profesional los confirme. "
        "Las señales inmediatas son frases documentales para revisión del personal, nunca instrucciones terapéuticas. "
        "Devuelve sólo JSON conforme al esquema."
    )
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model, "stream": False, "think": False,
                "format": IntakeExtraction.model_json_schema(), "keep_alive": settings.ollama_keep_alive,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps({"source": source, "relato": text}, ensure_ascii=False)}],
                "options": {"temperature": 0.1, "num_predict": 600, "num_ctx": settings.ollama_num_ctx, "num_gpu": settings.ollama_num_gpu},
            },
            timeout=settings.ollama_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("model") != settings.ollama_model:
            raise ValueError("El runtime no identificó el modelo configurado.")
        extraction = IntakeExtraction.model_validate(json.loads(body.get("message", {}).get("content", "")))
        return IntakeRun(extraction, True, settings.ollama_model, duration_seconds=time.monotonic() - started)
    except (requests.RequestException, ValueError, json.JSONDecodeError, ValidationError) as exc:
        return IntakeRun(
            fallback_extract_intake(text, source), False, "deterministic-intake-fallback", str(exc),
            time.monotonic() - started,
        )


def next_followup_question(extraction: IntakeExtraction, asked_fields: set[str], max_questions: int = 5) -> tuple[str, str] | None:
    if len(asked_fields) >= max_questions or extraction.immediate_review_signals.value:
        return None
    for field_name in extraction.missing_fields:
        if field_name not in asked_fields and field_name in FOLLOWUP_QUESTIONS:
            return field_name, FOLLOWUP_QUESTIONS[field_name]
    return None


def confirm_field(extraction: IntakeExtraction, field_name: str, value: Any, source: str) -> IntakeExtraction:
    if field_name not in IntakeExtraction.model_fields:
        raise ValueError("Campo de admisión no permitido.")
    updated = extraction.model_copy(deep=True)
    setattr(updated, field_name, _field(value, source, confirmed=True))
    updated.missing_fields = [item for item in updated.missing_fields if item != field_name]
    return IntakeExtraction.model_validate(updated.model_dump())


def resolve_field_as_null(extraction: IntakeExtraction, field_name: str, source: str = "patient_text") -> IntakeExtraction:
    """Record an explicit unknown/refusal/not-applicable resolution, never an inferred absence."""
    if field_name not in IntakeExtraction.model_fields or field_name == "missing_fields":
        raise ValueError("Campo de admisión no permitido.")
    updated = extraction.model_copy(deep=True)
    setattr(updated, field_name, CapturedField(value=None, source=source, confidence_status="confirmed", requires_confirmation=False))
    updated.missing_fields = [item for item in updated.missing_fields if item != field_name]
    return IntakeExtraction.model_validate(updated.model_dump())

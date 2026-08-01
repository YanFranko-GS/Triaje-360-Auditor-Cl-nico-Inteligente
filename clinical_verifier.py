from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from config import Settings, load_settings
from schemas import IntakeExtraction


MINIMUM_FIELDS = ("chief_complaint", "duration", "evolution", "pain_present", "allergies", "usual_medications")


class CompletenessVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    complete: bool
    missing_fields: list[str] = Field(default_factory=list, max_length=20)
    contradictions: list[str] = Field(default_factory=list, max_length=20)
    unsupported_claims: list[str] = Field(default_factory=list, max_length=20)
    requires_professional_review: list[str] = Field(default_factory=list, max_length=20)
    verification_model: str
    validated: bool


@dataclass(frozen=True)
class VerificationRun:
    result: CompletenessVerification
    model_used: bool
    duration_seconds: float
    error_detail: str | None = None


class ClinicalCompletenessVerifier:
    """Independent completeness review. It never diagnoses or prescribes."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def deterministic_review(self, extraction: IntakeExtraction) -> CompletenessVerification:
        missing: list[str] = []
        contradictions: list[str] = []
        unsupported: list[str] = []
        review: list[str] = []
        for name in MINIMUM_FIELDS:
            field = getattr(extraction, name)
            if field.value in (None, "", []) and name in extraction.missing_fields:
                missing.append(name)
        pain_present = extraction.pain_present.value
        pain_score = extraction.pain_score.value
        if pain_present is False and isinstance(pain_score, int) and pain_score > 0:
            contradictions.append("Dolor negado con escala de dolor mayor que cero.")
        if pain_present is True and pain_score is None:
            missing.append("pain_score")
        if isinstance(pain_score, int) and not 0 <= pain_score <= 10:
            contradictions.append("La escala de dolor está fuera del rango 0–10.")
        if extraction.immediate_review_signals.value:
            signals = extraction.immediate_review_signals.value
            if isinstance(signals, list):
                review.extend(str(item) for item in signals[:20])
            else:
                review.append(str(signals))
        if extraction.onset.value and not extraction.duration.value:
            review.append("Confirmar coherencia temporal entre inicio y duración.")
        missing = list(dict.fromkeys(missing))
        return CompletenessVerification(
            complete=not missing and not contradictions,
            missing_fields=missing,
            contradictions=contradictions,
            unsupported_claims=unsupported,
            requires_professional_review=review,
            verification_model="deterministic-rules-v1",
            validated=True,
        )

    def verify(self, extraction: IntakeExtraction, narrative: str, *, use_model: bool = True) -> VerificationRun:
        started = time.monotonic()
        rules = self.deterministic_review(extraction)
        if not use_model:
            return VerificationRun(rules, False, time.monotonic() - started)
        prompt = (
            "Actúa exclusivamente como verificador independiente de completitud documental. "
            "No diagnostiques, no prescribas y no agregues hechos. Compara el relato con los campos extraídos. "
            "Identifica contradicciones, afirmaciones no respaldadas y datos que requieren revisión profesional. "
            "Conserva los faltantes de las reglas. Devuelve solo JSON conforme al esquema."
        )
        payload = {
            "model": self.settings.review_model,
            "stream": False,
            "think": False,
            "format": CompletenessVerification.model_json_schema(),
            "keep_alive": self.settings.ollama_keep_alive,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"relato": narrative, "extraccion": extraction.model_dump(), "reglas": rules.model_dump()}, ensure_ascii=False)},
            ],
            "options": {"temperature": 0, "num_predict": 400, "num_ctx": self.settings.ollama_num_ctx, "num_gpu": self.settings.ollama_num_gpu},
        }
        try:
            response = requests.post(f"{self.settings.ollama_base_url}/api/chat", json=payload, timeout=self.settings.ollama_timeout_seconds)
            response.raise_for_status()
            body = response.json()
            if body.get("model") != self.settings.review_model:
                raise ValueError("El verificador no informó el modelo configurado.")
            reviewed = CompletenessVerification.model_validate(json.loads(body.get("message", {}).get("content", "")))
            reviewed.missing_fields = list(dict.fromkeys(rules.missing_fields + reviewed.missing_fields))
            reviewed.contradictions = list(dict.fromkeys(rules.contradictions + reviewed.contradictions))
            reviewed.requires_professional_review = list(dict.fromkeys(rules.requires_professional_review + reviewed.requires_professional_review))
            reviewed.complete = not reviewed.missing_fields and not reviewed.contradictions
            reviewed.verification_model = self.settings.review_model
            reviewed.validated = True
            return VerificationRun(reviewed, True, time.monotonic() - started)
        except (requests.RequestException, ValueError, json.JSONDecodeError, ValidationError) as exc:
            fallback = rules.model_copy(update={"verification_model": "deterministic-rules-v1"})
            return VerificationRun(fallback, False, time.monotonic() - started, str(exc))

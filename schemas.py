from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MissingInformation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=240)
    source_ids: list[str] = Field(min_length=1, max_length=4)


class ProfessionalReviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=240)
    rationale: str = Field(min_length=1, max_length=300)
    source_ids: list[str] = Field(min_length=1, max_length=4)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    statement: str = Field(min_length=1, max_length=300)
    source_ids: list[str] = Field(min_length=1, max_length=4)
    applicability: str = Field(min_length=1, max_length=300)
    limitations: str = Field(min_length=1, max_length=300)


class GemmaAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=500)
    risk_flags: list[str] = Field(max_length=5)
    protocol_id: Literal["respiratory_alert", "general_review"]
    reason: str = Field(min_length=1, max_length=300)
    disclaimer: str = Field(min_length=1, max_length=180)
    missing_information: list[MissingInformation] = Field(default_factory=list, max_length=4)
    questions_for_professional_review: list[ProfessionalReviewQuestion] = Field(default_factory=list, max_length=4)
    evidence_items: list[EvidenceItem] = Field(default_factory=list, max_length=4)

    @field_validator("risk_flags")
    @classmethod
    def validate_flags(cls, flags: list[str]) -> list[str]:
        if any(not flag.strip() or len(flag) > 220 for flag in flags):
            raise ValueError("Cada bandera debe contener entre 1 y 220 caracteres.")
        return flags

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer(cls, disclaimer: str) -> str:
        required = "no constituye diagnóstico ni indicación médica"
        if required not in disclaimer.casefold().rstrip("."):
            raise ValueError("El descargo de seguridad obligatorio no está presente.")
        return disclaimer

    @model_validator(mode="after")
    def require_respiratory_flag(self) -> "GemmaAnalysis":
        if self.protocol_id == "respiratory_alert" and not self.risk_flags:
            raise ValueError("respiratory_alert requiere al menos una bandera para revisión profesional.")
        return self


class CapturedField(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    value: str | int | bool | list[str] | None = None
    source: Literal["patient_audio", "patient_text", "history", "professional"]
    confidence_status: Literal["confirmed", "inferred_for_review", "missing"]
    requires_confirmation: bool


class IntakeExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chief_complaint: CapturedField
    onset: CapturedField
    duration: CapturedField
    evolution: CapturedField
    location: CapturedField
    pain_present: CapturedField
    pain_score: CapturedField
    accompanying_symptoms: CapturedField
    allergies: CapturedField
    usual_medications: CapturedField
    relevant_history: CapturedField
    immediate_review_signals: CapturedField
    missing_fields: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_pain(self) -> "IntakeExtraction":
        if isinstance(self.pain_present.value, str):
            normalized = self.pain_present.value.casefold()
            if normalized in {"true", "sí", "si"}:
                self.pain_present.value = True
            elif normalized in {"false", "no"}:
                self.pain_present.value = False
        if isinstance(self.pain_score.value, str) and self.pain_score.value.isdigit():
            self.pain_score.value = int(self.pain_score.value)
        if self.pain_present.value is True:
            score = self.pain_score.value
            if score is not None and (not isinstance(score, int) or not 0 <= score <= 10):
                raise ValueError("La escala de dolor debe estar entre 0 y 10.")
            if score is None and "pain_score" not in self.missing_fields:
                self.missing_fields.append("pain_score")
        return self

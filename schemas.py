from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GemmaAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=500)
    risk_flags: list[str] = Field(max_length=5)
    protocol_id: Literal["respiratory_alert", "general_review"]
    reason: str = Field(min_length=1, max_length=300)
    disclaimer: str = Field(min_length=1, max_length=180)

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

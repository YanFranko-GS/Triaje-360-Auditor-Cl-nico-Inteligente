from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str
    title: str
    institution: str
    country: str
    year: int
    document_type: str
    population: str
    clinical_scope: str
    url: str
    license: str
    access_date: str
    status: str
    superseded_by: str = ""
    approved_for_demo: bool
    notes: str = ""


class RagChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chunk_id: str
    source_id: str
    title: str
    institution: str
    year: int
    population: str
    section: str
    page: str
    url: str
    license: str
    text: str = Field(min_length=20, max_length=1200)
    applicability: str
    limitations: str
    content_hash: str
    ingested_at: str

    @field_validator("text")
    @classmethod
    def reject_active_content(cls, value: str) -> str:
        lowered = value.casefold()
        if any(token in lowered for token in ("<script", "javascript:", "ignore previous instructions")):
            raise ValueError("El chunk contiene contenido activo o una instrucción no confiable.")
        return value


class RetrievalResult(BaseModel):
    chunk: RagChunk
    score: float
    retrieval_reason: str

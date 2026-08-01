from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import Settings, load_settings
from database import create_consultation
from protocols import select_protocol
from schemas import GemmaAnalysis
from services.ollama_client import OllamaError, analyze_case, fallback_analysis


@dataclass(frozen=True)
class AnalysisRun:
    consultation_id: int
    analysis: GemmaAnalysis
    protocol: dict[str, Any]
    model_name: str
    model_used: bool
    fallback_reason: str | None


def process_case(
    *, dni: str, symptoms: str, history: list[dict[str, Any]], use_ollama: bool = True,
    settings: Settings | None = None, db_path: Path | str | None = None,
) -> AnalysisRun:
    settings = settings or load_settings()
    fallback_reason: str | None = None
    try:
        if not use_ollama:
            raise OllamaError("Gemma fue desactivado explícitamente para esta ejecución.")
        analysis, model_name = analyze_case(symptoms, history, settings)
        model_used = True
    except OllamaError as exc:
        fallback_reason = str(exc)
        analysis = fallback_analysis(symptoms)
        model_name = "deterministic-fallback"
        model_used = False

    protocol_id, protocol = select_protocol(symptoms, analysis.protocol_id)
    if protocol_id != analysis.protocol_id:
        analysis = analysis.model_copy(update={"protocol_id": protocol_id})
    consultation_id = create_consultation(
        dni=dni or "SIN-DNI", symptoms=symptoms, analysis=analysis.model_dump(), protocol=protocol,
        model_name=model_name, model_used=model_used, error_detail=fallback_reason, db_path=db_path,
    )
    return AnalysisRun(consultation_id, analysis, protocol, model_name, model_used, fallback_reason)

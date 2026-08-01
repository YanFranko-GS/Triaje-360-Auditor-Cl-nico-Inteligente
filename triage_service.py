from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCALE_NAME = "Sistema de prioridad de cinco niveles configurable, basado en ESI para validación profesional"


@dataclass(frozen=True)
class TriageProposal:
    level: int
    reasons: tuple[str, ...]
    requires_immediate_review: bool
    scale_name: str = SCALE_NAME


def propose_priority(vitals: dict[str, Any], context: dict[str, Any]) -> TriageProposal:
    """Conservative configurable proposal; the professional owns the final decision."""
    reasons: list[str] = []
    level = 5
    consciousness = str(vitals.get("consciousness_scale") or "").casefold()
    oxygen = vitals.get("oxygen_saturation")
    systolic = vitals.get("systolic")
    respiratory_rate = vitals.get("respiratory_rate")
    pain = vitals.get("pain_score")
    narrative = str(context.get("narrative") or "").casefold()
    population = str(vitals.get("population") or "adult")
    immediate_terms = ("no puedo respirar", "pérdida de conciencia", "sangrado abundante", "convulsión")
    if consciousness in {"sin respuesta", "responde a dolor"} or any(term in narrative for term in immediate_terms):
        level = 1
        reasons.append("Conciencia o manifestación declarada que exige valoración inmediata.")
    if oxygen is not None and oxygen < 90:
        level = min(level, 1)
        reasons.append("Saturación registrada marcadamente disminuida; confirmar medición y valorar de inmediato.")
    elif oxygen is not None and oxygen < 94:
        level = min(level, 2)
        reasons.append("Saturación registrada disminuida para revisión prioritaria.")
    if systolic is not None and systolic < 90:
        level = min(level, 1)
        reasons.append("Presión sistólica registrada compatible con perfusión comprometida; requiere valoración.")
    if respiratory_rate is not None and (respiratory_rate < 8 or respiratory_rate > 30):
        level = min(level, 2)
        reasons.append("Frecuencia respiratoria fuera del intervalo operativo configurado.")
    if isinstance(pain, int) and pain >= 8:
        level = min(level, 2)
        reasons.append("Dolor intenso declarado, considerado junto con el resto de la evaluación.")
    elif isinstance(pain, int) and pain >= 5:
        level = min(level, 3)
        reasons.append("Dolor moderado declarado; no se utiliza como criterio único.")
    if any(term in narrative for term in ("dificultad respiratoria", "me falta el aire", "dolor en el pecho")):
        level = min(level, 2)
        reasons.append("Motivo respiratorio o torácico declarado para revisión prioritaria.")
    if context.get("evolution", "").casefold() in {"empeora", "empeorando"}:
        level = min(level, 3)
        reasons.append("Evolución declarada en empeoramiento.")
    if population in {"pediatric", "obstetric", "older_adult"}:
        level = min(level, 3)
        reasons.append("Población que requiere aplicar configuración institucional específica.")
    if not reasons:
        level = 4
        reasons.append("Sin criterio configurado de prioridad alta; requiere confirmación profesional y recursos previsibles.")
    return TriageProposal(level, tuple(reasons), level <= 2)

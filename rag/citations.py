from __future__ import annotations

from datetime import datetime

from .schemas import RetrievalResult


def validate_analysis_citations(analysis: object, allowed_source_ids: set[str]) -> None:
    for field in ("missing_information", "questions_for_professional_review", "evidence_items"):
        for item in getattr(analysis, field, []):
            source_ids = set(item.source_ids)
            if not source_ids or not source_ids <= allowed_source_ids:
                raise ValueError(f"{field} contiene una referencia inexistente o no recuperada.")


def citation_payload(result: RetrievalResult) -> dict[str, object]:
    chunk = result.chunk
    return {
        "source_id": chunk.source_id,
        "title": chunk.title,
        "institution": chunk.institution,
        "year": chunk.year,
        "population": chunk.population,
        "section": chunk.section,
        "page": chunk.page,
        "url": chunk.url,
        "license": chunk.license,
        "fragment": chunk.text,
        "applicability": chunk.applicability,
        "limitations": chunk.limitations,
        "retrieval_reason": result.retrieval_reason,
    }


def traceability_metrics(results: list[RetrievalResult], cited_source_ids: set[str]) -> dict[str, object]:
    available = {result.chunk.source_id for result in results}
    covered = len(available & cited_source_ids)
    years = [result.chunk.year for result in results]
    return {
        "source_coverage_percent": round(100 * covered / len(available), 1) if available else 0.0,
        "applicable_documents": len(available),
        "latest_source_year": max(years) if years else None,
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "label": "Métrica de trazabilidad; no representa certeza ni precisión diagnóstica.",
    }

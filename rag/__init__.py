"""RAG clínico léxico, local y trazable."""

from .ingest import ingest_approved_sources
from .retriever import LexicalRetriever

__all__ = ["LexicalRetriever", "ingest_approved_sources"]

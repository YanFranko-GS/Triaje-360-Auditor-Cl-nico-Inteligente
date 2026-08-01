from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from config import load_settings

from .ingest import ingest_approved_sources, load_source_register
from .safety import source_is_eligible
from .schemas import RagChunk, RetrievalResult


STOPWORDS = {"de", "del", "la", "el", "y", "o", "un", "una", "desde", "tengo", "con", "al", "me"}


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-záéíóúñ]{3,}", query.casefold())
    # Preserve enough of the query for the structured clinical context appended
    # after a patient's narrative; a short free-text prefix must not crowd out it.
    return list(dict.fromkeys(word for word in words if word not in STOPWORDS))[:24]


class LexicalRetriever:
    def __init__(self, db_path: Path | str | None = None, limit: int = 4):
        self.db_path = Path(db_path or load_settings().database_path)
        self.limit = min(max(limit, 1), 6)

    def retrieve(self, query: str, population: str = "adult") -> list[RetrievalResult]:
        ingest_approved_sources(self.db_path)
        terms = _terms(query)
        if not terms:
            return []
        match_query = " OR ".join(f'"{term}"' for term in terms)
        register = load_source_register()
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """SELECT c.*, bm25(rag_chunks_fts) AS rank
                   FROM rag_chunks_fts f JOIN rag_chunks c ON c.chunk_id=f.chunk_id
                   WHERE rag_chunks_fts MATCH ? ORDER BY rank LIMIT ?""",
                (match_query, self.limit * 3),
            ).fetchall()
        results: list[RetrievalResult] = []
        seen_hashes: set[str] = set()
        for row in rows:
            source = register[row["source_id"]]
            eligible, reason = source_is_eligible(source, population)
            if not eligible or row["content_hash"] in seen_hashes:
                continue
            if row["population"] == "pediatric" and population != "pediatric":
                continue
            seen_hashes.add(row["content_hash"])
            chunk_data = {key: row[key] for key in RagChunk.model_fields}
            score = round(max(0.0, 1.0 / (1.0 + abs(float(row["rank"])))), 4)
            results.append(
                RetrievalResult(
                    chunk=RagChunk.model_validate(chunk_data),
                    score=score,
                    retrieval_reason=f"Coincidencia léxica con: {', '.join(terms[:4])}; {reason}.",
                )
            )
            if len(results) >= self.limit:
                break
        return results

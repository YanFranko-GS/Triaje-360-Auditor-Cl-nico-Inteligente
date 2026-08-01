from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from config import ROOT_DIR, load_settings

from .safety import sanitize_document_text
from .schemas import RagChunk, SourceMetadata


REGISTER_PATH = ROOT_DIR / "docs" / "source_register.csv"
CHUNKS_PATH = ROOT_DIR / "rag" / "data" / "approved_chunks.json"


def load_source_register(path: Path = REGISTER_PATH) -> dict[str, SourceMetadata]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    result: dict[str, SourceMetadata] = {}
    for row in rows:
        row["approved_for_demo"] = str(row["approved_for_demo"]).casefold() == "true"
        row["year"] = int(row["year"])
        metadata = SourceMetadata.model_validate(row)
        result[metadata.source_id] = metadata
    return result


def build_chunks() -> list[RagChunk]:
    register = load_source_register()
    raw_chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    chunks: list[RagChunk] = []
    for index, raw in enumerate(raw_chunks, 1):
        source = register[raw["source_id"]]
        if not source.approved_for_demo:
            raise ValueError(f"La fuente {source.source_id} no está aprobada para demo.")
        text = sanitize_document_text(raw["text"])
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunks.append(
            RagChunk(
                chunk_id=f"{source.source_id}-{index:03d}",
                source_id=source.source_id,
                title=source.title,
                institution=source.institution,
                year=source.year,
                population=raw["population"],
                section=raw["section"],
                page=raw["page"],
                url=source.url,
                license=source.license,
                text=text,
                applicability=raw["applicability"],
                limitations=raw["limitations"],
                content_hash=digest,
                ingested_at=now,
            )
        )
    return chunks


def ingest_approved_sources(db_path: Path | str | None = None) -> int:
    path = Path(db_path or load_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = build_chunks()
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rag_documents(
                source_id TEXT PRIMARY KEY, title TEXT NOT NULL, institution TEXT NOT NULL,
                country TEXT NOT NULL, year INTEGER NOT NULL, document_type TEXT NOT NULL,
                population TEXT NOT NULL, clinical_scope TEXT NOT NULL, url TEXT NOT NULL,
                license TEXT NOT NULL, access_date TEXT NOT NULL, status TEXT NOT NULL,
                approved_for_demo INTEGER NOT NULL CHECK(approved_for_demo IN (0,1)), notes TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rag_chunks(
                chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES rag_documents(source_id),
                title TEXT NOT NULL, institution TEXT NOT NULL, year INTEGER NOT NULL,
                population TEXT NOT NULL, section TEXT NOT NULL, page TEXT NOT NULL,
                url TEXT NOT NULL, license TEXT NOT NULL, text TEXT NOT NULL,
                applicability TEXT NOT NULL, limitations TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE, ingested_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks(source_id);
            CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(chunk_id UNINDEXED, text, title, section);
            """
        )
        register = load_source_register()
        for source in register.values():
            if not source.approved_for_demo:
                continue
            connection.execute(
                """INSERT INTO rag_documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_id) DO UPDATE SET title=excluded.title,status=excluded.status,
                   approved_for_demo=excluded.approved_for_demo,notes=excluded.notes""",
                (
                    source.source_id, source.title, source.institution, source.country, source.year,
                    source.document_type, source.population, source.clinical_scope, source.url,
                    source.license, source.access_date, source.status, int(source.approved_for_demo), source.notes,
                ),
            )
        for chunk in chunks:
            values = chunk.model_dump()
            connection.execute(
                """INSERT INTO rag_chunks VALUES(:chunk_id,:source_id,:title,:institution,:year,:population,
                   :section,:page,:url,:license,:text,:applicability,:limitations,:content_hash,:ingested_at)
                   ON CONFLICT(chunk_id) DO UPDATE SET text=excluded.text,content_hash=excluded.content_hash,
                   ingested_at=excluded.ingested_at""",
                values,
            )
            connection.execute("DELETE FROM rag_chunks_fts WHERE chunk_id=?", (chunk.chunk_id,))
            connection.execute(
                "INSERT INTO rag_chunks_fts(chunk_id,text,title,section) VALUES(?,?,?,?)",
                (chunk.chunk_id, chunk.text, chunk.title, chunk.section),
            )
    return len(chunks)


if __name__ == "__main__":
    print(f"Chunks aprobados indexados: {ingest_approved_sources()}")

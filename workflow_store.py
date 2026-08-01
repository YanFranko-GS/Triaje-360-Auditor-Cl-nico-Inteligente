from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from audio_pipeline import ProcessedAudio
from clinical_db import connect, migrate_demo_schema, utc_now
from schemas import IntakeExtraction


def create_audio_session(
    user_id: str, noise_profile: str, consent: bool, encounter_id: int | None = None,
    store_audio: bool = False, db_path: Path | str | None = None,
) -> str:
    migrate_demo_schema(db_path)
    if not consent:
        raise ValueError("Se requiere consentimiento para capturar audio.")
    session_id = "AUD_" + secrets.token_hex(10)
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO demo_audio_sessions VALUES(?,?,?,?,?,?,?,?,NULL)",
            (session_id, encounter_id, user_id, noise_profile, 1, int(store_audio), "capturing", utc_now()),
        )
    return session_id


def add_audio_segment(
    audio_session_id: str, processed: ProcessedAudio, mime_type: str = "audio/wav",
    sequence_no: int = 1, db_path: Path | str | None = None,
) -> str:
    segment_id = "SEG_" + secrets.token_hex(10)
    with connect(db_path) as connection:
        connection.execute(
            """INSERT INTO demo_audio_segments
               (id,audio_session_id,sequence_no,mime_type,duration_seconds,sample_rate,audio_sha256,signal_status,stored_path,created_at)
               VALUES(?,?,?,?,?,?,?,?,NULL,?)""",
            (
                segment_id, audio_session_id, sequence_no, mime_type, processed.duration_seconds,
                processed.sample_rate, processed.audio_sha256, processed.signal_status, utc_now(),
            ),
        )
        connection.execute("UPDATE demo_audio_sessions SET status='processed',completed_at=? WHERE id=?", (utc_now(), audio_session_id))
    return segment_id


def save_transcription(
    provider: str, text: str, *, segment_id: str | None = None, encounter_id: int | None = None,
    confidence: float | None = None, confirmed: bool = False, db_path: Path | str | None = None,
) -> str:
    transcription_id = "TRN_" + secrets.token_hex(10)
    now = utc_now()
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO demo_transcriptions VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                transcription_id, segment_id, encounter_id, provider, text, confidence, int(confirmed),
                text if confirmed else None, now, now if confirmed else None,
            ),
        )
    return transcription_id


def save_conversation_turn(
    encounter_id: int | None, turn_no: int, speaker: str, question: str | None, response: str | None,
    source: str, confirmed_by: str | None, db_path: Path | str | None = None,
) -> int:
    with connect(db_path) as connection:
        cursor = connection.execute(
            """INSERT INTO demo_conversation_turns
               (encounter_id,turn_no,speaker,question,response,source,confirmed_by,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (encounter_id, turn_no, speaker, question, response, source, confirmed_by, utc_now()),
        )
        return int(cursor.lastrowid)


def save_field_extractions(
    encounter_id: int | None, extraction: IntakeExtraction, model_run_id: int | None = None,
    db_path: Path | str | None = None,
) -> int:
    count = 0
    with connect(db_path) as connection:
        for field_name in IntakeExtraction.model_fields:
            if field_name == "missing_fields":
                continue
            field = getattr(extraction, field_name)
            connection.execute(
                """INSERT INTO demo_field_extractions
                   (encounter_id,field_name,value_json,source,confidence_status,requires_confirmation,model_run_id,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    encounter_id, field_name, json.dumps(field.value, ensure_ascii=False), field.source,
                    field.confidence_status, int(field.requires_confirmation), model_run_id, utc_now(),
                ),
            )
            count += 1
    return count

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clinical_db import connect  # noqa: E402
from database import initialize  # noqa: E402
from longitudinal_db import migrate_longitudinal_schema  # noqa: E402


def export_schema(output_dir: Path | None = None) -> tuple[Path, Path]:
    output_dir = output_dir or ROOT / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)
    initialize()
    migrate_longitudinal_schema()
    with connect() as connection:
        rows = connection.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL ORDER BY name"
        ).fetchall()
        schema_sql = "PRAGMA foreign_keys=ON;\n\n" + "\n\n".join(row["sql"].rstrip(";") + ";" for row in rows) + "\n"
        relations: list[tuple[str, str, str, str]] = []
        for row in rows:
            for fk in connection.execute(f"PRAGMA foreign_key_list({row['name']})"):
                relations.append((row["name"], fk["from"], fk["table"], fk["to"]))
    sql_path = output_dir / "database_schema.sql"
    mermaid_path = output_dir / "database_relationships.mmd"
    sql_path.write_text(schema_sql, encoding="utf-8")
    core = {
        "patients", "patient_identifiers", "users", "roles", "sessions", "institutions", "facilities",
        "encounters", "symptoms", "pain_assessments", "vital_signs", "allergies", "medications",
        "prescriptions", "diagnoses", "procedures", "laboratory_results", "imaging_results",
        "clinical_notes", "triage_assessments", "conversation_turns", "field_extractions",
        "field_confirmations", "model_runs", "rag_retrievals", "audit_events",
    }
    lines = ["erDiagram"]
    for child, child_column, parent, parent_column in relations:
        if child in core and parent in core:
            lines.append(f"    {parent} ||--o{{ {child} : \"{parent_column} to {child_column}\"")
    for table in sorted(core):
        lines.append(f"    {table} {{")
        lines.append("        string id")
        lines.append("    }")
    mermaid_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sql_path, mermaid_path


if __name__ == "__main__":
    for path in export_schema():
        print(path)

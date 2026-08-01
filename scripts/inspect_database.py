from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longitudinal_db import schema_catalog  # noqa: E402


def inspect_database(as_json: bool = False) -> list[dict[str, object]]:
    result = []
    for item in schema_catalog():
        safe_columns = [
            column["name"] for column in item["columns"]
            if not any(secret in column["name"].casefold() for secret in ("password", "hash", "salt", "secret", "token"))
        ]
        result.append({"table": item["table"], "rows": item["row_count"], "columns": safe_columns, "foreign_keys": len(item["foreign_keys"])})
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result:
            print(f"{item['table']}: {item['rows']} registros · {len(item['columns'])} columnas · {item['foreign_keys']} FK")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspección segura del esquema SQLite de TRIaje 360")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    inspect_database(arguments.json)

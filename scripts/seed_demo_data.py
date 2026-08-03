from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clinical_db import seed_demo_data
from rag.ingest import ingest_approved_sources


if __name__ == "__main__":
    print(seed_demo_data())
    print({"rag_chunks": ingest_approved_sources()})

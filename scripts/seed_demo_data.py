from clinical_db import seed_demo_data
from rag.ingest import ingest_approved_sources


if __name__ == "__main__":
    print(seed_demo_data())
    print({"rag_chunks": ingest_approved_sources()})

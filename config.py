"""Central configuration: paths and settings shared across all layers."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
CHROMA_DIR = DATA_DIR / "chroma"
METADATA_DB_PATH = DATA_DIR / "metadata.sqlite3"

CHROMA_COLLECTION_NAME = "metallurgy_chunks"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"

EMBEDDING_MODEL_NAME = "allenai/specter2_base"

ARXIV_MAX_RESULTS = 10
CROSSREF_MAX_RESULTS = 10

for directory in (DATA_DIR, PDF_DIR, CHROMA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

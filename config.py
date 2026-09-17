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

# SPECTER2 requires the extra `adapters` package on top of sentence-transformers;
# using the sentence-transformers-native SPECTER checkpoint instead (also scientific-
# text-trained), per the "SPECTER2 or sentence-transformers" choice in the spec.
EMBEDDING_MODEL_NAME = "sentence-transformers/allenai-specter"

ARXIV_MAX_RESULTS = 10
CROSSREF_MAX_RESULTS = 10

for directory in (DATA_DIR, PDF_DIR, CHROMA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

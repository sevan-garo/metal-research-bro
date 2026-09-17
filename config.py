"""Central configuration: paths and settings shared across all layers."""

import logging
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


def configure_logging(level: int = logging.INFO) -> None:
    """Called once by each entry point (agent/graph.py, interface/app.py).

    A zero-result search must be visible in the logs as "queried, found
    nothing" rather than being silently indistinguishable from "never ran" —
    see agent.state.SourceStatus and docs/adr/0016.
    """
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Third-party libraries logging at INFO (one line per HF Hub HEAD request,
    # per HTTP call) would drown out the agent's own retrieval trace, which is
    # the thing actually worth reading here.
    for noisy_logger in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

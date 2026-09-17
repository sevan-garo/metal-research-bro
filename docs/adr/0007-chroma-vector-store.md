# 0007 — Chroma as the embedded vector store

## Context

The POC is single-user and runs entirely on one machine — there's no need for
a networked vector database service, and standing one up (e.g. Qdrant as a
Docker container) would add operational overhead with no POC-stage benefit.

## Decision

Use Chroma in embedded/persistent mode (`chromadb.PersistentClient`, storing
to `data/chroma/` on disk) — no server process, no separate deployment.

## Consequences

- Zero setup: `pip install chromadb` and a local directory is the entire
  infrastructure. Fits the €0/single-user POC constraint directly.
- The collection is created with `hnsw:space: cosine`
  (`storage/vector_store.py`) rather than Chroma's default L2 distance,
  because `sentence-transformers` embeddings are normalized
  (`normalize_embeddings=True` in `ingestion/embed.py`) and cosine similarity
  is the metric SPECTER/SPECTER-family models are actually evaluated with.
- Migration path to Qdrant/pgvector for multi-user production is a
  `storage/vector_store.py` rewrite only — the rest of the codebase talks to
  it through `add_chunks()` / `query()`, never to Chroma's client directly.

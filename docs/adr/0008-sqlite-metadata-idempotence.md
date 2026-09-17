# 0008 — SQLite metadata DB + hash-based idempotence

## Context

Two separate needs: (1) structured metadata (title, authors, DOI, source)
that doesn't belong in the vector store's per-chunk records, and (2) a way to
avoid re-ingesting a PDF every time the ingestion pipeline runs — re-running
it should be safe to do repeatedly (e.g. after adding new files to
`data/pdfs/`) without duplicating existing chunks.

## Decision

Store document-level metadata in SQLite (`storage/metadata_db.py`,
`documents` + `ingestion_log` tables). Idempotence is enforced by hashing each
PDF's bytes (SHA-256, `ingestion/discover.py`) and skipping any file whose
hash already has a row in `documents` — a `UNIQUE` constraint on `file_hash`
backs this at the DB level, not just in application logic.

## Consequences

- SQLite needs no server process, matching the single-user €0 POC scope
  (same rationale as ADR 0007 for Chroma); migration to Postgres for
  multi-user production is a `storage/metadata_db.py` rewrite behind the same
  functions, not a schema redesign.
- Hashing file bytes (not filename or path) means renaming or moving a PDF
  doesn't trigger a duplicate re-ingestion, and a byte-identical file added
  under a different name is correctly recognized as already ingested.
- `ingestion_log` records every attempt (success/failed), not just successful
  ones — a failed Docling parse on a malformed PDF leaves an auditable trail
  instead of failing silently or crashing the whole batch run
  (`ingestion/pipeline.py` catches per-file, logs, and re-raises rather than
  swallowing the error).

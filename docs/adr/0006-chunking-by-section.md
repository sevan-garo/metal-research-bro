# 0006 — Semantic chunking by section, not fixed length

## Context

Fixed-length chunking (e.g. every 500 characters) is the default in most RAG
tutorials, but it routinely splits a sentence or a table row in half and mixes
content from two logical sections (e.g. the tail of "Methods" and the head of
"Results") into one chunk. For citation purposes specifically, a chunk that
spans two sections can't be honestly attributed to either one.

## Decision

Chunk by logical section first (using the section headings Docling extracts,
ADR 0004), and only apply a size cap (`MAX_CHUNK_CHARS = 1500` in
`ingestion/chunk.py`) as a secondary split within an oversized section — a
section boundary always forces a new chunk, but a chunk never crosses one.

## Consequences

- Every chunk has one unambiguous `section` label, which flows straight into
  the citation format `[Title, section, p.X]` — the citation is never a
  best-guess average over mixed content.
- A short section (e.g. an "Abstract") becomes exactly one chunk instead of
  being padded or merged with neighbors, which keeps retrieval precision high
  for questions that specifically target abstract-level claims.
- The 1500-char cap is a heuristic, not a token count — chosen to keep chunks
  well within the embedding model's context window without adding a
  tokenizer dependency just for size-checking. Revisit if a section
  regularly produces chunks that are still too large for the embedding model
  in practice.

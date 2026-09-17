# 0010 — Rank-based relevance score for arXiv/Crossref results

## Context

`search_local_rag` returns a genuine similarity score (cosine distance from
the query embedding, ADR 0007). Neither the arXiv API nor the Crossref API
returns a numeric relevance score — they return results already sorted by
relevance, but no score to sort by. The `dedupe_merge` graph node will need to
merge and rank results from all three sources into one list, which requires
every `RetrievedChunk` to carry a comparable `score`.

## Decision

Approximate a score from each API's own relevance ordering:
`score = 1 - rank / len(results)`, giving the top result 1.0 and later ones a
linearly decreasing score. Implemented in `tools/arxiv_tool.py` and
`tools/crossref_tool.py`.

## Consequences

- `dedupe_merge` can sort/merge all three sources by `score` without
  special-casing external results, at the cost of that score being an
  ordering proxy, not a real relevance measure — a rank-1 Crossref result and
  a rank-1 arXiv result both score 1.0 even though the two APIs' notions of
  "relevance" aren't calibrated against each other or against local RAG's
  cosine similarity.
- Also on formatting: Crossref abstracts (when publishers submit them) are
  JATS XML fragments with HTML-escaped entities (e.g. `Q&amp;amp;P`), not
  plain text — `tools/crossref_tool.py` strips tags and unescapes entities
  before use, otherwise citations would surface raw markup to the user. Many
  Crossref records have no abstract at all; those fall back to the title as
  the chunk's `text` rather than being dropped, so the paper is still
  discoverable/citable by title even without abstract content to search on.

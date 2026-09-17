# 0014 — Cap dedupe_merge output to the top N results

## Context

A broad external-search question ("deep learning for microstructure
segmentation in steel") pulled in 20 deduplicated results — arXiv and
Crossref keyword search matched on "deep learning" alone dragged in
completely unrelated papers (brain MRI segmentation, malware classification,
item price elasticity). Because arXiv/Crossref results are scored by rank
within their own API response rather than true relevance (ADR 0010), nothing
upstream of `dedupe_merge` already limits how much of this noise reaches
generation. Passing all 20 into `generate_answer`'s prompt was observed to
coincide with a worse answer (see ADR 0013) than a smaller, more focused
source list.

## Decision

`dedupe_merge_node` caps its output at `MAX_MERGED_RESULTS = 10`, keeping the
highest-scored results after sorting and deduplication.

## Consequences

- Bounds the prompt size sent to `generate_answer` regardless of how broad or
  keyword-ambiguous the external APIs' matching turns out to be for a given
  query.
- The cap doesn't fix the underlying precision problem — it was tested
  against the same "deep learning microstructure segmentation" query and the
  model still produced an incorrect summary sentence despite citing genuinely
  relevant papers (the faithfulness gap in ADR 0013, not a provenance
  problem). Capping reduces noise; it doesn't guarantee the surviving 10 are
  the *right* 10, since the rank-based score isn't a real relevance measure
  across sources.
- 10 is a starting heuristic, not a tuned value — worth revisiting alongside
  a real cross-source relevance signal (e.g. re-ranking all merged results
  against the query with the same embedding model used for local RAG,
  instead of trusting each API's own un-calibrated ranking).

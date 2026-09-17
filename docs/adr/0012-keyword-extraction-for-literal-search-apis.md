# 0012 — Extract keywords for Zotero/arXiv/Crossref; keep full questions for local RAG

## Context

Live end-to-end testing of the agent graph surfaced a real retrieval failure:
asking "What does my Zotero library say about induction hardening of steel?"
returned zero results from `search_zotero`, even though the library
demonstrably contains multiple induction-hardening papers (confirmed
separately with a plain `"induction hardening"` query, which returned 10).
The same thing happened with `search_arxiv` on a full natural-language
question — it returned physics and NLP papers that only shared incidental
words like "induction" or "does" with the question, because arXiv's query
parser and Zotero's local API both do literal keyword/phrase matching, not
semantic search. `search_local_rag` has no such problem, since embedding
similarity is exactly what it's built to handle regardless of phrasing.

## Decision

The router's structured-output call (`agent/nodes.py`, `RoutingDecision`) now
also extracts a short keyword query (`keyword_query`, 3-8 words, no stopwords
or question phrasing) in the same LLM call that decides which sources to
query. `retrieve_zotero_node` and `retrieve_external_node` use
`keyword_query`; `retrieve_local_node` keeps using the raw `state["question"]`.

## Consequences

- Fixed the observed failure: the same Zotero question, after this change,
  correctly returned and cited three real library items.
- Extracting keywords inside the router's existing structured-output call
  (rather than a separate LLM call per retrieval node) avoids doubling
  inference latency for questions that hit both Zotero and external search —
  one router call now produces routing *and* query normalization together.
- This couples query quality to the same 7B model's instruction-following as
  the rest of the pipeline (ADR 0003's known trade-off) — a keyword
  extraction that drops a load-bearing technical term would silently degrade
  recall with no visible error. Not yet guarded against; worth adding a
  regression check (fixed questions → expected keyword sets) if this proves
  brittle in practice.

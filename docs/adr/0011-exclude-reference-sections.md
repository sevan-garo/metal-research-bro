# 0011 — Exclude reference/bibliography sections from chunking

## Context

Live testing of `search_local_rag` (querying the 3-paper arXiv test corpus for
"quenching and partitioning of advanced high-strength steel") returned
`References`-section chunks as the *top two* results, ahead of the paper's
own abstract and conclusions. A reference list repeats other papers' titles
and author names verbatim — text that lexically overlaps a keyword-heavy
query far more than the source paper's own paraphrased prose does — while
containing no actual claim that section could be cited for.

## Decision

Exclude blocks under `References` / `Bibliography` / `Acknowledgment(s)`
headings from chunking entirely (`ingestion/chunk.py`,
`EXCLUDED_SECTION_KEYWORDS`), matched as a substring against the
alphabetic-only lowercased heading so numbered/decorated headings like
"VII. References" or "Acknowledgements & Funding" are still caught.

## Consequences

- Re-running `search_local_rag` on the same query after this fix returned the
  paper's actual title/abstract and conclusions section first — confirmed by
  direct comparison of the two ingestion runs.
- These sections would never be legitimate citation targets anyway (a
  reference list entry isn't a claim, it's a pointer to a different paper),
  so excluding them loses nothing the citation format could have used.
- The substring match is deliberately loose; a section genuinely named
  something like "Cross-References Between Alloy Systems" would be wrongly
  excluded. Not observed in the test corpus and judged an acceptable false
  -positive rate for a POC-stage heuristic — worth tightening only if it
  causes a real miss in practice.

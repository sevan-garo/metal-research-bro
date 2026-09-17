# 0002 — arXiv + Crossref instead of Google Scholar

## Context

The agent needs to search beyond the researcher's personal library. Google
Scholar has no official API; the practical options are fragile HTML scraping
(breaks on layout changes, risks IP blocks) or a paid proxy service like
SerpAPI. The project's budget is €0, non-negotiable, and the stack must not
depend on services that can disappear or start billing.

## Decision

Use the arXiv API and the Crossref API as the external search sources.

## Consequences

- Both are official, free, documented, and stable — no scraping, no API keys,
  no rate-limit-driven outages tied to a third party's ToS enforcement.
- Coverage trade-off: arXiv is preprint-only and Crossref indexes metadata (not
  full text) across publishers — this is narrower than what Google Scholar
  would surface, especially for older or non-preprinted metallurgy papers
  behind paywalls. Acceptable for the POC; revisit if coverage gaps show up in
  practice.
- Both APIs return structured metadata (DOI, title, authors) directly, which
  simplifies the dedup-against-Zotero step (`dedupe_merge` node) — matching on
  DOI is far more reliable than matching on scraped titles.

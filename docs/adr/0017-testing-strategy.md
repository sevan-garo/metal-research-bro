# 0017 — Two-tier testing: automated pure-logic, manual live integration

## Context

Almost every interesting behavior in this project depends on something that
isn't a pure function: `router_node` and `generate_answer_node` call a real
local LLM; `search_zotero` calls a real running Zotero app; `search_arxiv`/
`search_crossref` call real external APIs. Mocking all of that would mean
writing a fake Ollama that returns canned structured-output decisions, a fake
Zotero server, and fake arXiv/Crossref responses — at which point the tests
verify that the code correctly calls a mock, not that the agent actually
works. Several of this project's real bugs (docs/adr/0011 through 0014) were
found *only* by running the full pipeline against real services and reading
what came back; a mocked test suite would have had no chance of catching any
of them, since each one was a property of real model behavior or a real API's
actual matching semantics, not a logic error a mock could expose.

## Decision

Split testing into two tiers, not one compromise in between:

1. **`tests/` (pytest, automated, runs in CI-speed)** — only for logic that
   is a pure function of its inputs: `ingestion/chunk.py`'s section-boundary
   and size-cap splitting, `dedupe_merge_node`'s DOI/title dedup and result
   cap, `_enforce_citations`'s sentence-level filtering. These take plain
   Python values in and assert plain Python values out — no LLM, no network,
   no fixtures standing in for a live service.
2. **`docs/TESTING.md` (manual, live)** — everything that depends on
   `qwen2.5:7b`'s actual behavior, a real Zotero library, or real external
   APIs. Not automated, and not a lesser form of testing for it — it's the
   tier that actually exercises the thing the project is for.

## Consequences

- The automated suite stays fast (`pytest tests/` runs in under 5 seconds)
  and is safe to run on every change, but it cannot catch a regression in
  prompt phrasing, citation formatting compliance, or retrieval quality —
  those are tier 2's job, and the guide walks through them explicitly
  (including deliberately breaking Ollama and Zotero to confirm the
  error-vs-empty distinction from docs/adr/0016 actually holds).
- A contributor (or future Claude session) skimming only the automated suite
  would get a false sense of coverage — `docs/TESTING.md` is written to be
  read and followed by hand, not to imply "the important stuff is already
  automated."
- If this project moves toward CI, the honest next step isn't mocking
  Ollama/Zotero into the existing suite — it's standing up a real (if
  minimal) Ollama + test Zotero library in the CI environment and running
  tier 2's steps against them, so what gets automated is still the real
  behavior rather than a mock's approximation of it.

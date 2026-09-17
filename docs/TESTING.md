# Testing Guide

This project has two tiers of testing, and they cover different things on purpose:

1. **Automated (`pytest`)** — pure logic only: chunking, deduplication, citation
   enforcement. No LLM, no network, no Zotero. Fast and deterministic, so it runs on
   every change.
2. **Manual, live** — everything that actually depends on Ollama, Zotero, or the
   internet. This is most of what makes the app work, and it can't be meaningfully
   mocked without testing something other than the real behavior (see
   [docs/adr/0017](adr/0017-testing-strategy.md) for why). This guide is how you run
   that tier by hand.

If you're picking this project up fresh, run tier 1 first (it's quick and confirms
your environment isn't broken), then work through tier 2 in order — each step below
builds on the previous one's state.

## Prerequisites

```bash
source .venv/bin/activate    # created via: python3.11 -m venv .venv
pip install -r requirements.txt

brew services start ollama   # if not already running
ollama list                  # confirm qwen2.5:7b is present; if not: ollama pull qwen2.5:7b
```

For anything touching `search_zotero`, Zotero desktop must be running with
Settings > Advanced > "Allow other applications on this computer to communicate
with Zotero" enabled. Confirm with:

```bash
curl -s http://localhost:23119/api/users/0/items?limit=1
# "Local API is not enabled" (403) means the setting above is off.
```

## Tier 1 — Automated tests

```bash
python -m pytest tests/ -v
ruff check .
```

Both should be clean before committing. `tests/` covers:

| File | What it checks |
|---|---|
| `tests/test_chunk.py` | Section-boundary splitting, size-cap splitting, reference-section exclusion (docs/adr/0011) |
| `tests/test_dedupe_merge.py` | DOI/title dedup, `Untitled` filtering, the `MAX_MERGED_RESULTS` cap (docs/adr/0014), and that `search_diagnostics` actually distinguishes an error from a real empty result (docs/adr/0016) |
| `tests/test_citation_enforcement.py` | Sentence-level citation filtering and the trailing-citation reattachment fix (docs/adr/0013) |

These test the *logic*, not the *behavior of qwen2.5:7b* — a prompt change that
makes the model phrase citations differently won't be caught here. That's what
tier 2 is for.

## Tier 2 — Manual, live testing

### 1. Ingest the test corpus

```bash
ls data/pdfs/          # should have at least one PDF; if empty, drop some in
python -m ingestion.pipeline
```

Expect one line per new file: `Ingested N document(s): [...]`. Re-run it —
expect `Ingested 0 document(s): []` (idempotence, docs/adr/0008). If you need a
clean slate (e.g. after changing chunking logic), wipe the derived state and
re-ingest — this never touches `data/pdfs/` itself:

```bash
rm -rf data/chroma/* data/metadata.sqlite3 && touch data/chroma/.gitkeep
python -m ingestion.pipeline
```

### 2. Each tool in isolation

```bash
python -c "
from tools.local_rag import search_local_rag
for r in search_local_rag('<a phrase you know is in your corpus>', top_k=3):
    print(f\"[{r['score']:.3f}] {r['title']} | {r['section']!r} p.{r['page']}\")
"
```

Do the same for `tools.zotero_tool.search_zotero`, `tools.arxiv_tool.search_arxiv`,
`tools.crossref_tool.search_crossref` — each takes a plain keyword string, not a
question (docs/adr/0012). Expect non-empty, topically relevant results for each.
If `search_zotero` returns nothing, try a plainer keyword before assuming it's
broken — see the ADR for why full questions fail here.

### 3. The full agent, one path at a time

Ask a question shaped to route to each source, and check `SEARCH DIAGNOSTICS` in
the output for what actually got queried:

```bash
python -m agent.graph "According to my local corpus, <a question your test PDFs can answer>"
python -m agent.graph "What does my Zotero library say about <a topic you know is in it>"
python -m agent.graph "Find recent arXiv papers about <a topic>"
```

For each, check:
- **Diagnostics** show the source(s) you expected as queried, with a plausible
  result count.
- **Answer** — every sentence that states a fact ends in a `[Title, p.X]` or
  `[Title, section]` citation.
- **Citations** list is non-empty and each entry's title matches something you'd
  expect from that source.

If diagnostics show a source as "not queried" when you expected it to be, that's
the router misclassifying the question — try rephrasing before assuming a bug.

### 4. The "I don't know" and error paths

These matter as much as the happy path — the project's core promise is that
silence means "genuinely nothing found," not "something broke quietly."

```bash
# A question nothing in any source could plausibly answer:
python -m agent.graph "What is the tensile strength of unobtainium at 500K?"
```

Expect an answer that says it couldn't find sourced material, *and* diagnostics
showing each queried source with `error: None` (found nothing) rather than an
`ERROR` line.

Now force an actual error and confirm it's distinguishable:

```bash
# Stop Ollama, then:
brew services stop ollama
python -m agent.graph "any question"
# Expect a log line "router_node: LLM call failed" and the graph still
# completing (falls back to querying everything, per docs/adr/0016) rather
# than crashing.
brew services start ollama   # restore before continuing
```

```bash
# Quit Zotero (or disable its local API), then:
python -m agent.graph "What does my Zotero library say about induction hardening?"
# Expect diagnostics to show "Zotero: ERROR — ..." not "0 result(s)".
# Restart Zotero / re-enable the setting before continuing.
```

### 5. The interface

```bash
streamlit run interface/app.py
```

Open the printed local URL. Ask a question, confirm:
- The answer renders with inline citations.
- The "Sources" expander lists them with page/section.
- The "Search diagnostics" expander is present on *every* answer (not just
  failures) and shows a per-source breakdown.

For a headless/scripted check instead of opening a browser (useful after
changing `interface/app.py`), see `docs/adr/0015` for the Playwright driver
pattern used to verify it during development — `playwright install chromium`
once, then drive it with `sync_playwright()`, `page.goto(...)`,
`page.get_by_placeholder(...)`, and `page.screenshot(...)`.

## Resetting to a clean state

```bash
rm -rf data/chroma/* data/metadata.sqlite3 && touch data/chroma/.gitkeep
```

This never deletes `data/pdfs/` — your source PDFs are always safe; only the
derived vector store and metadata DB are wiped.

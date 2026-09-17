# metal-research-bro

An AI companion for metallurgy researchers: answers research questions by combining
a local paper corpus (RAG), a Zotero library, and arXiv/Crossref search, with
mandatory sourced citations. 100% free/open-source stack, runs fully local via
Ollama — no paper content or question ever leaves the machine.

## Motivation

I'm a PhD researcher working on AI applied to metallurgy. Over the course of my own
research I kept hitting the same friction: the literature I actually needed was
scattered across three places — a folder of papers I'd bought or co-authored, a
Zotero library, and the wider body of work on arXiv and in journals — with no
single place to ask a real question and trust the answer. Tools that promise to
"chat with your papers" are useful right up until the moment they're confidently
wrong, and in materials science a hallucinated claim — a fabricated alloy
composition, an invented mechanical property, a citation to a paper that doesn't
actually say what it's credited with saying — is worse than no answer at all,
because it looks exactly as credible as a correct one.

So this project is the tool I wished existed: every answer has to point to a real
retrieved source, section and page, so a claim can be checked in seconds instead of
trusted blindly — and when the literature it can see doesn't cover the question, it
has to say so instead of quietly making something up. It searches the three places
I actually keep my own papers, and it runs entirely locally so none of my
unpublished questions or purchased papers ever leave my machine.

Beyond solving my own problem, I built it so any student or researcher who's hit
the same wall — burning time hunting for a source they know exists somewhere in
their own library, or double-checking whether a plausible-sounding answer is
actually grounded in a real paper — has something ready to adapt to their own
corpus. The [ADR log](docs/adr/) is part of that: several entries exist because
live testing surfaced a specific place the system could have quietly hallucinated
or misattributed a claim, and the fix is documented rather than silently shipped —
so the "zero unsourced claims" rule stays a property you can verify, not just a
promise in this README.

### A note on how this was built

This project was built with [Claude Code](https://claude.com/claude-code), and
that's stated plainly rather than left for someone to guess: using it here was
itself part of the point. Alongside solving my own research problem, I wanted to
explore what an AI coding agent can actually carry end to end — not just writing
functions from a spec, but installing and configuring real local infrastructure
(Ollama, a Python environment), debugging against live services (a real Zotero
library, live arXiv/Crossref calls), catching its own failures during testing
(several ADRs exist because a live run surfaced a bug, not because it was
anticipated up front), and documenting the reasoning as it went rather than after
the fact. The [ADR log](docs/adr/) is as much a record of that exploration as it
is of the technical decisions themselves — including places where the first
attempt didn't work and the fix, and why, is written down rather than quietly
rewritten over.

See [CLAUDE.md](CLAUDE.md) for the full architecture, current status, and roadmap;
[docs/adr/](docs/adr/) for the reasoning behind individual engineering choices
(why LangGraph, why Docling, why SPECTER over SPECTER2, why pyzotero's local API
over an MCP server, etc.), written as each piece was built and tested; and
[docs/TESTING.md](docs/TESTING.md) for how to verify any of it still works.

## Setup

```bash
# Python 3.11+ virtualenv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium  # only needed for UI smoke-testing, see docs/adr/0015

# Ollama (local LLM), run as a background service via:
brew services start ollama
ollama pull qwen2.5:7b

# Zotero desktop must be running, with Settings > Advanced > "Allow other
# applications on this computer to communicate with Zotero" enabled
# (docs/adr/0009) — search_zotero talks to it at localhost:23119, no API key.
```

## Run

```bash
# Ingest PDFs dropped into data/pdfs/ (idempotent — safe to re-run)
python -m ingestion.pipeline

# Launch the chat interface
streamlit run interface/app.py

# Or query the agent directly from the CLI
python -m agent.graph "your question here"
```

## Test

```bash
python -m pytest tests/ -v   # pure logic: chunking, dedup, citation enforcement
ruff check .
```

See [docs/TESTING.md](docs/TESTING.md) for manual/live testing (everything that
depends on Ollama, Zotero, or the external APIs — most of what the app actually
does — can't be meaningfully unit-tested; see docs/adr/0017).

## Project structure

- `ingestion/` — PDF discovery, parsing (Docling), chunking, embedding
- `tools/` — agent tools: local RAG, Zotero, arXiv, Crossref
- `agent/` — LangGraph state graph: router, retrieval, dedupe, cited generation
- `storage/` — Chroma vector store + SQLite metadata DB wrappers
- `interface/` — Streamlit chat app
- `data/` — local PDFs and Chroma persistence (gitignored)

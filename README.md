# metal-research-bro

An AI companion for metallurgy researchers: answers research questions by combining
a local paper corpus (RAG), a Zotero library, and arXiv/Crossref search, with
mandatory sourced citations. 100% free/open-source stack, runs fully local via
Ollama — no paper content or question ever leaves the machine.

See [CLAUDE.md](CLAUDE.md) for the full architecture and project instructions, and
[docs/adr/](docs/adr/) for the reasoning behind individual engineering choices
(why LangGraph, why Docling, why SPECTER over SPECTER2, why pyzotero's local API
over an MCP server, etc.), written as each piece was built and tested.

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

## Project structure

- `ingestion/` — PDF discovery, parsing (Docling), chunking, embedding
- `tools/` — agent tools: local RAG, Zotero, arXiv, Crossref
- `agent/` — LangGraph state graph: router, retrieval, dedupe, cited generation
- `storage/` — Chroma vector store + SQLite metadata DB wrappers
- `interface/` — Streamlit chat app
- `data/` — local PDFs and Chroma persistence (gitignored)

# metal-research-bro

An AI companion for metallurgy researchers: answers research questions by combining
a local paper corpus (RAG), a Zotero library (via MCP), and arXiv/Crossref search,
with mandatory sourced citations. 100% free/open-source stack, runs fully local via
Ollama.

See [CLAUDE.md](CLAUDE.md) for the full architecture and project instructions.

## Setup

```bash
# Python 3.11+ virtualenv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama (local LLM), already running as a background service via:
#   brew services start ollama
ollama pull qwen2.5:7b
```

## Project structure

- `ingestion/` — PDF discovery, parsing (Docling), chunking, embedding
- `tools/` — agent tools: local RAG, Zotero, arXiv, Crossref
- `agent/` — LangGraph state graph
- `storage/` — Chroma vector store + SQLite metadata DB wrappers
- `interface/` — Streamlit app
- `data/` — local PDFs and Chroma persistence (gitignored)

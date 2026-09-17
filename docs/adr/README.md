# Architecture Decision Records

This log captures the reasoning behind non-obvious engineering choices as the
project is built — what was considered, what was picked, and why. It's written
as the code lands, not reconstructed afterward, so it reflects the actual
trade-offs at the time each decision was made.

Each record follows a short Context / Decision / Consequences format.

| # | Decision | Status |
|---|---|---|
| [0001](0001-langgraph-orchestration.md) | LangGraph for agent orchestration from the POC | Accepted |
| [0002](0002-arxiv-crossref-over-scholar.md) | arXiv + Crossref instead of Google Scholar | Accepted |
| [0003](0003-local-llm-ollama.md) | Ollama, 100% local LLM | Accepted |
| [0004](0004-docling-pdf-parsing.md) | Docling for layout-aware PDF parsing | Accepted |
| [0005](0005-embedding-model-specter.md) | SPECTER (not SPECTER2) for embeddings | Accepted |
| [0006](0006-chunking-by-section.md) | Semantic chunking by section, not fixed length | Accepted |
| [0007](0007-chroma-vector-store.md) | Chroma as the embedded vector store | Accepted |
| [0008](0008-sqlite-metadata-idempotence.md) | SQLite metadata DB + hash-based idempotence | Accepted |
| [0009](0009-zotero-local-api-pyzotero.md) | pyzotero against Zotero's local API, not zotero-mcp | Accepted |

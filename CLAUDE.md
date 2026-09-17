# Metallurgy Research Companion

## Context & Objective

An AI companion for PhD students and researchers in metallurgy, answering research
questions by drawing on three complementary sources:

1. A local corpus (RAG) of papers already purchased or co-authored by the researcher
2. Their Zotero library (via an MCP server)
3. arXiv / Crossref to expand beyond their personal library

**Current stage**: POC, single-user, no authentication or legal constraints. The
architecture must stay modular so it doesn't need a rewrite when moving to production
(multi-user, real web app).

**Non-negotiable requirement**: every answer must be sourced (paper + precise
section/page). Zero claims without a verifiable citation.

## Decisions already made

- **Orchestration**: LangGraph from the POC onward (no intermediate "simple function
  calling" version).
- **External search**: arXiv + Crossref (official, free, stable APIs) rather than
  Google Scholar (no official API, fragile scraping or paid SerpAPI).
- **Budget**: €0, non-negotiable. The entire stack must be free and open source — no
  paid API, no paid SaaS service, even for the POC.
- **LLM**: Ollama, 100% local. Priority on full independence — no research data
  (papers, questions) ever leaves the machine, no dependency on a third-party service.
- **Language**: all code, comments, and documentation must be written in English.

## Layered architecture

**Layer 1 — Ingestion (offline/batch)**: a watcher on the local PDF folder + periodic
sync with Zotero to spot new items; layout-aware parsing (tables, figures); semantic
chunking by article section; embeddings; writing to the vector store + metadata DB.

**Layer 2 — Tools (exposed to the agent)**:
- `search_local_rag`: vector search + reranking over the already-ingested corpus
- `search_zotero` (MCP): search by metadata/tags/collections, fetches the PDF if the
  item isn't indexed yet (triggers on-the-fly ingestion)
- `search_arxiv` / `search_crossref`: expands beyond the personal library

**Layer 3 — Orchestration (LangGraph agent)**: a state graph that routes the question
to the right tool(s), with multi-step logic (e.g. found via arXiv → check if already
in Zotero to avoid duplicates → offer to add it). Citations are enforced at every
generation step.

**Layer 4 — Interface**: POC uses Streamlit (chat + clickable sources panel).
Production (out of POC scope) will be a real web app with auth, multi-user support.

**Guiding principle**: each layer can be replaced independently (e.g. Chroma → Qdrant,
Streamlit → web app) without touching the others.

## Technical stack

| Component | POC choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | LangGraph ecosystem, PDF parsing, embeddings |
| Orchestration | LangGraph | Explicit state graph, native checkpointing, multi-tool support |
| LLM | Ollama (Llama 3.1 / Qwen2.5) | Free, 100% local, no research data ever leaves the machine |
| PDF parsing | Docling | Layout-aware: preserves table structure, spots figures |
| Embeddings | SPECTER2 or sentence-transformers (local) | Free, local, trained on scientific text |
| Vector store | Chroma (local, embedded) | Zero setup for POC, easy migration to Qdrant/pgvector |
| Metadata DB | SQLite | Sufficient for single-user, migration to Postgres in production |
| Zotero | zotero-mcp, pyzotero fallback | Explicitly requested |
| External search | arXiv API + Crossref API | Free, stable, no scraping |
| Interface | Streamlit | Chat + source display, no frontend dev needed |

Trade-off to keep in mind: a self-hosted open source LLM (Llama/Qwen) generally lags
behind larger hosted models on multi-hop reasoning — worth validating in the first
POC tests.

## LangGraph agent

**Graph nodes (starting proposal)**:
1. `router` — analyzes the question, decides which source(s) to query (local /
   Zotero / arXiv-Crossref), can pick several
2. `retrieve_local` — calls `search_local_rag`
3. `retrieve_zotero` — calls `search_zotero`
4. `retrieve_external` — calls `search_arxiv` / `search_crossref`
5. `dedupe_merge` — merges results from the queried sources, removes duplicates
   (same DOI/title)
6. `generate_answer` — generates the answer with mandatory citations, format
   `[Title, p.X]`
7. `offer_zotero_add` — if an external result isn't in Zotero, offers to add it
   (requires user confirmation)

**Tool signatures**:
```python
search_local_rag(query: str, top_k: int) -> list[Chunk]
search_zotero(query: str, filters: dict | None) -> list[ZoteroItem]
search_arxiv(query: str, max_results: int) -> list[Paper]
search_crossref(query: str, max_results: int) -> list[Paper]
add_to_zotero(item: Paper, tags: list[str]) -> ZoteroItem  # requires confirmation
```

**Graph state**: question, conversation history, raw results per source,
deduplicated results, answer being generated, list of citations used.

LangGraph checkpointing is used from the POC stage to replay/debug multi-step
reasoning, and is directly reusable in production for session persistence.

## Ingestion pipeline

1. **Discovery**: scan the local PDF folder (watcher or manual trigger for the POC)
   + call Zotero MCP to list library items not yet ingested
2. **Parsing**: extract text via Docling while preserving structure (headings,
   tables, figure captions); figures are extracted as images but not analyzed in the
   POC (V2: multimodal vision)
3. **Metadata enrichment**: prefer Zotero metadata (DOI, authors, year, journal) when
   the item comes from Zotero, rather than re-parsing it from the PDF
4. **Chunking**: split by logical scientific article section (abstract / methods /
   results / discussion), not by fixed character length
5. **Embedding**: generate vectors per chunk
6. **Writing**: chunks + vectors → Chroma; metadata → SQLite
7. **Idempotence**: an item already ingested (same DOI/file hash) is not re-ingested

## Data schemas

**Vector store (Chroma) — per chunk**: `chunk_id`, `document_id`, `text`,
`embedding`, `section` (abstract/methods/results/...), `page`

**Metadata DB (SQLite) — `documents` table**: `document_id`, `title`, `authors`,
`doi`, `year`, `journal`, `source` (local / zotero / arxiv / crossref), `file_path`,
`zotero_key` (nullable), `ingested_at`, `file_hash` (idempotence)

**Metadata DB — `ingestion_log` table**: `document_id`, `status`
(success/failed/pending), `error_message` (nullable), `timestamp`

This minimal schema is intentionally flat for the POC. In V2, a
`material_properties` table could store structured data extracted from papers
(alloy composition, heat treatment, mechanical properties) to power cross-paper
comparison.

## Project structure

```
metal-research-bro/
├── ingestion/
│   ├── discover.py        # scan local folder + list Zotero items
│   ├── parse.py           # Docling: text, tables, figures
│   ├── chunk.py           # semantic chunking by section
│   ├── embed.py           # embedding generation
│   └── pipeline.py        # ingestion run orchestration
├── tools/
│   ├── local_rag.py       # search_local_rag
│   ├── zotero_tool.py     # search_zotero, add_to_zotero (via MCP)
│   ├── arxiv_tool.py      # search_arxiv
│   └── crossref_tool.py   # search_crossref
├── agent/
│   ├── graph.py           # LangGraph graph definition
│   ├── nodes.py           # router, retrieve_*, dedupe_merge, generate_answer
│   └── state.py           # graph state schema
├── storage/
│   ├── vector_store.py    # Chroma wrapper
│   └── metadata_db.py     # SQLite wrapper
├── interface/
│   └── app.py             # Streamlit
├── data/
│   ├── pdfs/               # local PDF corpus (gitignored)
│   └── chroma/             # Chroma persistence directory (gitignored)
├── config.py               # paths, settings
└── requirements.txt
```

## POC scope vs production evolutions

**In POC scope**:
- Federated Q&A (local + Zotero + arXiv/Crossref) with sourced citations and
  deduplication
- Structured summary of a paper (materials studied, method, measured properties)
- Adding an externally found paper to Zotero, with user confirmation
- Single-user, no authentication

**Deliberately out of POC scope, but anticipated in the architecture**:
- Multi-user → migrating SQLite/Chroma to Postgres/Qdrant, per-user data isolation
- Real web app with authentication → the interface layer is isolated, replaceable
- Cross-paper structured extraction (material properties comparison table)
- Automatic watch (new papers matching the user's topics)
- Reading figures (phase diagrams, curves) via multimodal vision

## Metallurgy-specific points of attention

- **Information-rich figures**: phase diagrams, micrographs, stress-strain curves
  often carry the core result. A pure-text RAG completely misses them. Not addressed
  in the POC; keep in mind for a V2 with multimodal reading.
- **Structured tables**: alloy compositions and mechanical properties are highly
  tabular — hence Docling (layout-aware) over raw text extraction, which would break
  tables.
- **Terminology and nomenclature**: standardized designations (AFNOR, ASTM, EN) for
  alloys. A small glossary/term-normalization dictionary could improve retrieval
  matching (V2, not a POC blocker).

## Environment

- Python 3.11+ via Homebrew (`/opt/homebrew/bin/python3.11`); system Python remains
  3.9 and is not used for this project.
- Ollama via Homebrew, run as a background service (`brew services start ollama`).
  Starter model: `qwen2.5:7b`.
- Project virtualenv lives at `.venv/` (gitignored); always use it rather than the
  system interpreter.

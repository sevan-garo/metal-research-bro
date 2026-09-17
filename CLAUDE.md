# Metallurgy Research Companion

## Context & Objective

An AI companion for PhD students and researchers in metallurgy, answering research
questions by drawing on three complementary sources:

1. A local corpus (RAG) of papers already purchased or co-authored by the researcher
2. Their Zotero library (via pyzotero against Zotero desktop's local API — see
   docs/adr/0009; not an MCP server, despite the name in early planning notes below)
3. arXiv / Crossref to expand beyond their personal library

**If you are a Claude session picking this project up**: read
[docs/adr/README.md](docs/adr/README.md) before changing anything — it's the log of
what was tried, what broke, and why the current approach was chosen instead of an
apparently-simpler one. The "Decisions already made" and stack table below are the
*original* planning notes from before implementation started; where they conflict
with an ADR, the ADR reflects what's actually built and is authoritative. Then read
[Current Status](#current-status) and [Next Steps (V2)](#next-steps-v2) further down
for what's done and what's next, and [docs/TESTING.md](docs/TESTING.md) before
claiming anything works — most of this project's real behavior depends on a
running Ollama/Zotero and can't be verified by reading the code alone
(docs/adr/0017).

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
- `search_local_rag`: vector search over the already-ingested corpus (no reranking
  yet — see Next Steps)
- `search_zotero`: pyzotero against Zotero desktop's local API (docs/adr/0009),
  search by metadata/tags/collections. On-the-fly ingestion when a matched item
  isn't indexed yet, and `add_to_zotero`, are not built — see Next Steps.
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
| Embeddings | `sentence-transformers/allenai-specter` (local) | Free, local, scientific-text-trained; SPECTER not SPECTER2 — see docs/adr/0005 |
| Vector store | Chroma (local, embedded) | Zero setup for POC, easy migration to Qdrant/pgvector |
| Metadata DB | SQLite | Sufficient for single-user, migration to Postgres in production |
| Zotero | pyzotero against the local API | Explicitly requested; local API over Web API or an MCP server — see docs/adr/0009 |
| External search | arXiv API + Crossref API | Free, stable, no scraping |
| Interface | Streamlit | Chat + source display, no frontend dev needed |

Trade-off to keep in mind: a self-hosted open source LLM (Llama/Qwen) generally lags
behind larger hosted models on multi-hop reasoning — worth validating in the first
POC tests.

## LangGraph agent

**Graph nodes** (`agent/nodes.py`, wired in `agent/graph.py`):
1. `router` — LLM structured-output call: decides which source(s) to query, and
   extracts a keyword-only query for the literal-match APIs (docs/adr/0012).
   Falls back to querying every source if the LLM call fails or is undecided.
2. `retrieve_local` — calls `search_local_rag` with the full natural-language
   question (embeddings handle it fine, unlike the APIs below)
3. `retrieve_zotero` — calls `search_zotero` with the extracted keyword query
4. `retrieve_external` — calls `search_arxiv` + `search_crossref` with the
   keyword query
5. `dedupe_merge` — merges results from the queried sources, dedupes by DOI/title,
   caps to top 10 (docs/adr/0014), builds the `search_diagnostics` summary
   (docs/adr/0016)
6. `generate_answer` — generates the answer, then enforces citations at the
   *sentence* level: any sentence whose bracket doesn't match a retrieved
   source's title is dropped (docs/adr/0013)
7. `offer_zotero_add` — **not built**. See Next Steps.

Each `retrieve_*` node wraps its tool call(s) in try/except and reports a
`SourceStatus` (queried/count/error) rather than a bare list, so "found nothing"
and "the source errored out" are never conflated — see docs/adr/0016. This
pattern should be followed for any new tool/node added later.

**Tool signatures** (actual, not the original proposal — `Chunk`/`Paper`/
`ZoteroItem` below are all the one `RetrievedChunk` TypedDict in
`agent/state.py`, not separate per-source types):
```python
search_local_rag(query: str, top_k: int = 5) -> list[RetrievedChunk]
search_zotero(query: str, filters: dict | None = None) -> list[RetrievedChunk]
search_arxiv(query: str, max_results: int | None = None) -> list[RetrievedChunk]
search_crossref(query: str, max_results: int | None = None) -> list[RetrievedChunk]
add_to_zotero(item: Paper, tags: list[str]) -> ZoteroItem  # not built — see Next Steps
```

**Graph state** (`agent/state.py`, `AgentState`): question, history,
`sources_to_query`, `keyword_query`, per-source results and `SourceStatus`,
`merged_results`, `search_diagnostics`, `answer`, `citations`.

LangGraph checkpointing (native to the framework) is not yet wired up for this
graph — `run_agent` compiles and invokes a fresh graph per call, with no
persisted checkpointer. Worth adding once conversation history/multi-turn
context actually matters (see Next Steps); until then there's nothing to
checkpoint across, since `history` in `AgentState` is populated but not yet
read by any node.

## Ingestion pipeline

1. **Discovery**: scan the local PDF folder by file hash (`ingestion/discover.py`,
   manual trigger via `python -m ingestion.pipeline` — no watcher yet, see Next
   Steps). Listing not-yet-ingested Zotero items is not built; only plain-folder
   PDFs are ingested today.
2. **Parsing**: extract text via Docling while preserving structure (headings,
   tables, figure captions); figures are extracted as images but not analyzed in the
   POC (V2: multimodal vision)
3. **Metadata enrichment**: prefer Zotero metadata (DOI, authors, year, journal) when
   the item comes from Zotero, rather than re-parsing it from the PDF
4. **Chunking**: split by logical scientific article section (abstract / methods /
   results / discussion), not by fixed character length. Reference/bibliography/
   acknowledgment sections are excluded entirely — they lexically dominate keyword
   queries without containing any citable claim (docs/adr/0011).
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
│   ├── discover.py        # scan local folder by file hash (idempotence)
│   ├── parse.py           # Docling: text/tables/figures, tagged by section+page
│   ├── chunk.py           # semantic chunking by section, excludes references
│   ├── embed.py           # SPECTER embedding generation
│   └── pipeline.py        # ingestion run orchestration (entry point: __main__)
├── tools/
│   ├── local_rag.py       # search_local_rag
│   ├── zotero_tool.py     # search_zotero (no add_to_zotero yet)
│   ├── arxiv_tool.py      # search_arxiv
│   └── crossref_tool.py   # search_crossref
├── agent/
│   ├── graph.py           # LangGraph graph definition (entry point: __main__)
│   ├── nodes.py           # router, retrieve_*, dedupe_merge, generate_answer
│   ├── state.py           # graph state schema (AgentState, RetrievedChunk, SourceStatus)
│   └── llm.py             # shared Ollama ChatOllama client
├── storage/
│   ├── vector_store.py    # Chroma wrapper
│   └── metadata_db.py     # SQLite wrapper
├── interface/
│   └── app.py             # Streamlit chat app (entry point)
├── docs/
│   ├── adr/                # Architecture Decision Records — read before changing anything
│   └── TESTING.md          # automated + manual/live testing guide
├── tests/                  # pytest: pure logic only (chunking, dedup, citations) — see docs/adr/0017
├── data/
│   ├── pdfs/               # local PDF corpus (gitignored)
│   ├── chroma/             # Chroma persistence directory (gitignored)
│   └── metadata.sqlite3    # SQLite metadata DB (gitignored)
├── config.py               # paths, settings, logging setup
├── conftest.py             # empty — puts the project root on pytest's sys.path
└── requirements.txt
```

## Current Status

Everything below is built, live-tested (not just unit-tested), and on `master`.
See [docs/adr/README.md](docs/adr/README.md) for the reasoning behind each choice
and for issues found and fixed during that testing.

- **Ingestion**: Docling parsing → section-based chunking (references excluded) →
  SPECTER embeddings → Chroma + SQLite, idempotent by file hash. Tested against a
  3-paper arXiv metallurgy corpus in `data/pdfs/`.
- **Tools**: all four (`search_local_rag`, `search_zotero`, `search_arxiv`,
  `search_crossref`) implemented and tested live — `search_zotero` against a real
  283-item Zotero library, the others against live APIs.
- **Agent**: full graph (router → parallel retrieve → dedupe/merge → cited
  generation) working end-to-end with `qwen2.5:7b`, including per-source error
  tracing (docs/adr/0016) and sentence-level citation enforcement (docs/adr/0013).
- **Interface**: Streamlit chat app, screenshot-verified with headless Playwright
  (docs/adr/0015).

**Known gap, not yet fixed**: citation enforcement checks *provenance* (the cited
source was actually retrieved), not *faithfulness* (the sentence accurately
represents that source). A live test showed the model citing real, correctly
retrieved papers while still summarizing them incorrectly. See docs/adr/0013.

**Not built yet** (present in the original spec below, but out of what's landed):
`add_to_zotero`, the `offer_zotero_add` graph node, per-paper structured summaries,
the `material_properties` table, a PDF folder watcher, and any use of
`AgentState["history"]` for multi-turn context (it's populated by the interface but
no node reads it yet).

## Next Steps (V2)

Roughly in the order they'd likely get picked up. Each is a real, scoped task, not
just an idea — start by reading the linked ADR for the constraint it needs to
respect.

1. **`add_to_zotero` + `offer_zotero_add` node** — the last piece of the original
   POC scope that isn't built. Needs a write path to Zotero's local API, which is
   separate from the read path already working (docs/adr/0009 notes Zotero 7 gates
   local writes behind a `local_api_key` shown in Zotero's own settings — check
   whether `pyzotero`'s `local=True` mode supports passing it before assuming this
   is a small change). The graph node itself should reuse the existing
   confirmation-required pattern implied by the tool signature in this doc.
2. **Faithfulness checking** (docs/adr/0013's known gap) — citation enforcement
   currently can't catch a correctly-cited sentence that still misrepresents its
   source. Needs either an entailment/NLI pass over (sentence, source text) pairs,
   or a second LLM call asking specifically "does this source support this claim,
   yes/no" — cheaper to prototype than NLI given the local-LLM-only constraint.
3. **Per-paper structured summary** — materials studied, method, measured
   properties, as a distinct agent capability (POC scope, not yet built). Probably
   a new graph entry point rather than a node in the Q&A graph, since it operates
   on one already-known document rather than a search query.
4. **Cross-source relevance re-ranking** (docs/adr/0010, 0014) — arXiv/Crossref
   rank-based scores aren't calibrated against local RAG's cosine similarity or
   against each other. Re-embedding all `merged_results` text against the query
   with the same SPECTER model used for local RAG, then re-scoring, would give one
   consistent relevance signal instead of three incompatible ones.
5. **PDF folder watcher** — `ingestion/discover.py` requires a manual
   `python -m ingestion.pipeline` run today; the original spec called for a
   watcher. `watchdog` is already in `requirements.txt` but unused.
6. **Multi-turn context** — `AgentState["history"]` exists and the Streamlit
   interface populates it across turns, but no node reads it, so every question is
   answered as if it were the first. Wiring it into the router prompt (and
   possibly LangGraph's checkpointing for persistence) is what "conversation"
   actually requires here.
7. **`material_properties` table + structured extraction** — for cross-paper
   comparison (alloy composition, heat treatment, mechanical properties). Depends
   on (3) or can reuse the same extraction step.
8. **Multimodal figure reading** — phase diagrams, micrographs, stress-strain
   curves. Docling already extracts figures as images (docs/adr/0004); nothing
   downstream analyzes them yet. Needs a vision-capable local model (check what
   Ollama supports beyond `qwen2.5:7b`) or explicit descoping if none performs
   adequately.
9. **Terminology normalization** (AFNOR/ASTM/EN alloy designations) — a glossary
   mapping equivalent designations could improve retrieval matching. Not urgent;
   only worth it if real queries start missing matches over naming variants.
10. **Multi-user / production migration** — SQLite → Postgres, Chroma → Qdrant,
    auth, per-user isolation. Every storage/vector-store access already goes
    through `storage/vector_store.py` and `storage/metadata_db.py`, so this should
    be a rewrite of those two files' internals, not a wider refactor — verify that
    still holds before starting.
11. **Docker** — deliberately deferred, not forgotten. See docs/adr/0018 for the
    full reasoning (GPU passthrough, host-only dependencies, nothing to
    reproduce yet) and the specific triggers that should prompt revisiting it
    (multi-user migration, a hosted/remote LLM, a second contributor/machine).

**Deliberately out of scope until (10) above**: real web app with authentication,
per-user data isolation.

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

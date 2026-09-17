# 0016 — Distinguishing "found nothing" from "search failed"

## Context

Before this change, every retrieval node returned a plain list — `[]` meant
"queried, found nothing" and would also have meant "the search crashed",
had any node's tool call raised. Since none of them had a `try/except`, a
transient failure (Zotero desktop not running, Ollama down, a network
hiccup against arXiv/Crossref) would have just crashed the whole graph
instead of degrading gracefully — and even if caught generically, a caller
would have no way to tell "your library has nothing on this topic" from
"I couldn't reach your library at all." For a research tool whose entire
premise is trustworthy sourcing, that ambiguity is a real problem: a
researcher seeing "no results" needs to know whether to trust that silence
or go check why a source didn't respond.

## Decision

`agent/state.py` adds `SourceStatus` (`queried: bool`, `count: int`,
`error: str | None`), one per retrieval branch (`local_status`,
`zotero_status`, `external_status`). Each `retrieve_*_node` wraps its tool
call(s) in `try/except`, logs via `logger.exception` (full traceback) on
failure, and returns a `SourceStatus` that keeps "no results" (`error=None`)
and "failed" (`error=<message>`) distinct. `dedupe_merge_node` renders all
three into a `search_diagnostics` string carried through the rest of the
graph; `generate_answer_node` includes it in the fallback message when no
sources were found; the Streamlit UI shows it in an always-present
"Search diagnostics" expander (not just on failure), auto-expanded when
there are no citations to look at instead.

## Consequences

- Verified by deliberately pointing `search_zotero` at an unreachable port:
  the result was `{'queried': True, 'count': 0, 'error': '[Errno 61]
  Connection refused'}` with a full traceback in the log — clearly not the
  same thing as a legitimate empty search.
- The router itself also got a `try/except`: if the LLM call fails (Ollama
  unreachable), the agent logs it and falls back to querying every source
  rather than crashing before any retrieval happens at all.
- Global logging is configured once (`config.configure_logging`, called at
  import time by `agent/graph.py`) with third-party loggers (`httpx`,
  `sentence_transformers`, etc.) turned down to `WARNING` — left at the
  default `INFO`, they produced one line per HTTP HEAD request to the
  Hugging Face Hub and buried the agent's own retrieval trace, which is the
  part actually worth reading.
- This is per-branch status, not per-tool: `retrieve_external_node` calls
  both `search_arxiv` and `search_crossref` and merges their errors into one
  `external_status.error` string (e.g. `"crossref: ConnectionError(...)"`) if
  either fails, rather than tracking each API separately — matches the
  spec's node granularity (one `retrieve_external` node), at the cost of not
  being able to tell from `source_status` alone which of the two failed
  without reading the message text.

# 0015 — Streamlit chat interface, and its sys.path gotcha

## Context

The POC needs a way to actually use the agent interactively: ask a question,
see the cited answer, inspect the sources. The spec calls for Streamlit
specifically (chat + clickable sources panel, no separate frontend build).

## Decision

`interface/app.py` is a standard Streamlit chat app: `st.chat_input` for the
question, `st.chat_message` for the conversation, and an `st.expander` per
answer listing its citations (title + page/section). Session history lives in
`st.session_state.messages`.

## Consequences

- **Bug found by actually running it, not by reading the code**: `streamlit
  run interface/app.py` failed immediately with `ModuleNotFoundError: No
  module named 'agent'`. Streamlit puts the *script's own directory*
  (`interface/`) at the front of `sys.path`, not the project root — so
  `from agent.graph import run_agent` couldn't resolve, even though the same
  import works fine from the project root via `python -m agent.graph` or
  pytest. Fixed by explicitly inserting the project root into `sys.path` at
  the top of `app.py` before the `agent` import. This only surfaces at
  runtime, under Streamlit's specific invocation — a type-checker or a plain
  `python -c "import interface.app"` from the root would not have caught it,
  which is why the project's own guidance is to actually launch the app in a
  browser rather than trust static checks for UI changes.
- Verified live with Playwright (headless Chromium) end-to-end: app loads,
  a question is typed and submitted, the router/retrieval/generation pipeline
  runs for real against the local corpus, and the cited answer plus an
  expandable sources panel render correctly. `playwright` + a one-time
  `playwright install chromium` is now in `requirements.txt` under dev
  tooling for the same kind of check on future interface changes.
- Each `st.chat_input` submission re-runs the whole script, calling
  `run_agent` fresh (no result caching) — acceptable for a single-user POC
  where every question legitimately needs a new retrieval+generation pass;
  would need a caching or streaming layer if response latency becomes a
  problem with a heavier corpus.

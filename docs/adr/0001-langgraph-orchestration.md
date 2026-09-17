# 0001 — LangGraph for agent orchestration from the POC

## Context

The agent needs to route a question to one or more retrieval tools (local RAG,
Zotero, arXiv/Crossref), potentially in sequence (e.g. "found via arXiv → check
if already in Zotero → offer to add it"), and enforce that every generated
answer carries a citation. This is a multi-step, stateful control flow, not a
single request/response call.

The alternative was to start with plain function calling (LLM picks a tool,
result goes back in the prompt, loop) and introduce a graph framework later
once the control flow outgrew it.

## Decision

Use LangGraph from the first version of the agent, not as a later migration.

## Consequences

- The routing/retrieval/dedupe/generate steps are explicit graph nodes with a
  typed state ([`agent/state.py`](../../agent/state.py)) instead of being
  implicit in prompt/loop logic — easier to reason about and to unit-test each
  step in isolation.
- LangGraph's checkpointing is available from day one, which doubles as a
  debugging tool now (replay a multi-hop query to see which node produced
  what) and as the session-persistence mechanism needed later for a
  multi-user production version — no rewrite required for that part.
- Cost: more upfront structure than a bare loop for what is, initially, a
  simple routing decision. Accepted because the graph is expected to grow
  (dedup, Zotero-add confirmation) rather than stay simple.

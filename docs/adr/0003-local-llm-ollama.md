# 0003 — Ollama, 100% local LLM

## Context

The corpus includes papers the researcher purchased or co-authored, and the
questions asked over them can reveal unpublished research direction. Sending
either to a third-party LLM API is a hard no for this project, independent of
cost. The €0 budget constraint separately rules out any paid hosted model
regardless of the privacy question.

## Decision

Run the LLM locally via Ollama (starter model: `qwen2.5:7b`), with no
network call for generation or embeddings ever leaving the machine.

## Consequences

- Full data independence: no paper text or question ever crosses the network
  for inference. This holds even for the POC, where no auth/legal framework
  exists yet to govern third-party data handling.
- Reasoning quality trade-off: a 7B local model lags larger hosted models on
  multi-hop reasoning (e.g. chaining "search arXiv → check Zotero → dedupe →
  cite"). This is called out explicitly as something to validate empirically
  once the LangGraph routing logic is in place — the graph structure itself
  (ADR 0001) is partly there to compensate by making each reasoning step
  explicit and smaller, rather than relying on the model to reason it all in
  one pass.
- Embeddings are also local (see ADR 0005) for the same reason — a hosted
  embedding API would leak paper content just as much as a hosted LLM would.

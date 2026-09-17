# 0005 — SPECTER (not SPECTER2) for embeddings

## Context

The original spec called for "SPECTER2 or sentence-transformers", both
scientific-text-trained embedding models, leaving the exact choice open.
SPECTER2 (`allenai/specter2_base`) is distributed as a base transformer plus a
separately-loaded adapter, which requires the `adapters` (adapter-transformers)
library on top of `sentence-transformers` — an extra dependency and an extra
moving part (base model + adapter loaded and activated at runtime) for a POC.

## Decision

Use `sentence-transformers/allenai-specter` — the original SPECTER model,
published directly as a standard `sentence-transformers` checkpoint with no
adapter step.

## Consequences

- One dependency (`sentence-transformers`) instead of two, and one line to
  load the model (`SentenceTransformer(model_name)`) instead of tokenizer +
  base model + adapter wiring. See `ingestion/embed.py`.
- SPECTER is still trained on scientific paper text (title + abstract via
  citation graph supervision), so retrieval quality on metallurgy abstracts is
  expected to be close to SPECTER2's improvements, which mainly target
  multi-task retrieval scenarios (classification, proximity, adhoc search)
  the POC doesn't need — it only needs one flavor of semantic similarity
  search.
- If retrieval quality proves insufficient in practice, swapping the model is
  a one-line change in `config.EMBEDDING_MODEL_NAME` plus a re-ingestion run
  (embeddings from different models aren't compatible in the same Chroma
  collection) — no code structure change needed.

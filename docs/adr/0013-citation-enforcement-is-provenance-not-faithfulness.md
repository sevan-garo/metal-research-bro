# 0013 — Sentence-level citation enforcement, and its faithfulness gap

## Context

The project's non-negotiable requirement is "every answer must be sourced...
zero claims without a verifiable citation." An early implementation checked
only whether the *overall* answer contained at least one citation matching a
retrieved source. Live testing showed this was too weak: the model would
write several sentences of free claims and then bolt one real citation onto
the very end of the paragraph — e.g. "...does not delve into the specifics
[...]. For detailed information you may need to refer to [Fonstein, 2015] or
[Speer et al., 2003]." The bracket-shaped `[Fonstein, 2015]` looks like a
citation but names a source that was never retrieved — a fabricated
reference riding along next to a real one, which the answer-level check could
not distinguish.

## Decision

`agent/nodes.py`'s `_enforce_citations` splits the generated answer into
sentences and keeps only sentences whose citation bracket matches a title
actually present in `merged_results`; everything else is dropped. A model
also tends to place one citation for a whole paragraph as its own
sentence-shaped fragment (e.g. `"[Title, p.4]"` alone) rather than inline
per-sentence, despite the prompt asking for the latter — `_split_sentences`
reattaches a citation-only fragment to the sentence before it so the
claim and its citation are evaluated together instead of being split apart
and both discarded.

## Consequences

- Fabricated citations (`[Fonstein, 2015]`) no longer survive into the
  visible answer or the structured `citations` list — confirmed by testing
  the same query before and after this change.
- This is a blunt instrument: it can discard a legitimate synthesis sentence
  the model simply forgot to cite, at the cost of a thinner answer rather
  than a wrong one. Given the project's explicit "zero claims without a
  verifiable citation" rule, an incomplete answer is the correct failure mode
  to prefer over an unverifiable one.
- **Known gap, found in testing, not yet solved**: this enforces *provenance*
  (was the cited source actually retrieved) but not *faithfulness* (does the
  sentence accurately represent what that source says). Asking about
  "deep learning for steel microstructure segmentation," the model cited
  real, correctly-matched papers — several literally titled about steel
  microstructure segmentation — while still summarizing them as "none of
  these sources focus on microstructure segmentation in steel." Every
  citation passed provenance checking; the claim was wrong anyway. Catching
  that class of error needs an entailment/faithfulness check (e.g. NLI model,
  or a stronger model doing a verification pass) that this POC does not yet
  have. Flagged here rather than silently left implicit, since it directly
  bears on the project's core sourcing guarantee: today that guarantee covers
  "the citation is real," not "the claim is true of the citation."

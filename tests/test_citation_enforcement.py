"""Pure-logic tests for agent/nodes.py's citation enforcement (docs/adr/0013).

No LLM call involved — these test the post-processing that runs on whatever
text a model produced, using hand-written strings standing in for that output.
"""

from agent.nodes import _enforce_citations, _split_sentences
from agent.state import RetrievedChunk


def _chunk(title: str, doi: str | None = None, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=title,
        title=title,
        text="...",
        section="abstract",
        page=1,
        source="local",
        score=score,
        doi=doi,
    )


def test_keeps_sentences_citing_a_real_source():
    results = [_chunk("Real Paper")]
    raw = "This is a real claim [Real Paper, p.1]. This is fabricated [Fake Paper, 2020]."

    answer, citations = _enforce_citations(raw, results)

    assert "real claim" in answer
    assert "fabricated" not in answer
    assert [c["title"] for c in citations] == ["Real Paper"]


def test_falls_back_when_nothing_is_verifiably_cited():
    results = [_chunk("Real Paper")]
    raw = "This sentence makes a claim but cites nothing."

    answer, citations = _enforce_citations(raw, results)

    assert citations == []
    assert "Real Paper" in answer  # listed as retrieved-but-unused, not silently dropped


def test_reattaches_trailing_citation_only_fragment_to_its_claim():
    # Models often bolt one citation onto the end instead of citing inline —
    # this must not get split away from the sentence it belongs to.
    text = "A claim without an inline citation. [Some Paper, p.4]"

    sentences = _split_sentences(text)

    assert sentences == ["A claim without an inline citation. [Some Paper, p.4]"]


def test_does_not_merge_a_multi_citation_fragment_incorrectly():
    text = "First claim [A, p.1]. Second claim [B, p.2]."

    sentences = _split_sentences(text)

    assert sentences == ["First claim [A, p.1].", "Second claim [B, p.2]."]

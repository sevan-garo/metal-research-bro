"""Pure-logic tests for agent/nodes.py's dedupe_merge_node."""

from agent.nodes import MAX_MERGED_RESULTS, dedupe_merge_node
from agent.state import RetrievedChunk, SourceStatus


def _chunk(title: str, doi: str | None = None, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=title,
        title=title,
        text="text",
        section="abstract",
        page=1,
        source="local",
        score=score,
        doi=doi,
    )


def _status(queried: bool = True, count: int = 0, error: str | None = None) -> SourceStatus:
    return SourceStatus(queried=queried, count=count, error=error)


def _state(local=(), zotero=(), external=(), **statuses):
    return {
        "local_results": list(local),
        "zotero_results": list(zotero),
        "external_results": list(external),
        "local_status": statuses.get("local_status", _status()),
        "zotero_status": statuses.get("zotero_status", _status()),
        "external_status": statuses.get("external_status", _status()),
    }


def test_dedupes_by_doi_keeping_the_higher_scored_copy():
    state = _state(
        local=[_chunk("Paper A", doi="10.1/a", score=0.9)],
        zotero=[_chunk("Paper A (zotero copy)", doi="10.1/a", score=0.5)],
    )

    merged = dedupe_merge_node(state)["merged_results"]

    assert len(merged) == 1
    assert merged[0]["title"] == "Paper A"


def test_dedupes_by_normalized_title_when_no_doi():
    state = _state(
        local=[_chunk("Steel Alloys!!", score=0.9)],
        zotero=[_chunk("steel alloys", score=0.5)],
    )

    merged = dedupe_merge_node(state)["merged_results"]

    assert len(merged) == 1


def test_drops_untitled_results():
    state = _state(external=[_chunk("Untitled", score=1.0)])

    merged = dedupe_merge_node(state)["merged_results"]

    assert merged == []


def test_caps_output_at_max_merged_results():
    chunks = [_chunk(f"Paper {i}", score=1.0 - i * 0.01) for i in range(MAX_MERGED_RESULTS + 5)]
    state = _state(local=chunks)

    merged = dedupe_merge_node(state)["merged_results"]

    assert len(merged) == MAX_MERGED_RESULTS


def test_diagnostics_distinguish_error_from_legitimate_empty_result():
    state = _state(
        local_status=_status(queried=True, count=0, error=None),
        zotero_status=_status(queried=True, count=0, error="Connection refused"),
        external_status=_status(queried=False, count=0, error=None),
    )

    diagnostics = dedupe_merge_node(state)["search_diagnostics"]

    assert "Local corpus: 0 result(s)" in diagnostics
    assert "Zotero: ERROR — Connection refused" in diagnostics
    assert "arXiv/Crossref: not queried" in diagnostics

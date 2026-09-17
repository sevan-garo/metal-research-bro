"""search_arxiv tool: expands search beyond the personal library via the arXiv API."""

import arxiv

import config
from agent.state import RetrievedChunk

_CLIENT = arxiv.Client()


def search_arxiv(query: str, max_results: int | None = None) -> list[RetrievedChunk]:
    max_results = max_results or config.ARXIV_MAX_RESULTS
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    results = list(_CLIENT.results(search))

    # arXiv doesn't return a numeric relevance score; approximate one from the
    # API's own relevance-sorted rank so results merge sensibly with the
    # embedding-similarity scores from search_local_rag in dedupe_merge.
    return [
        RetrievedChunk(
            document_id=result.get_short_id(),
            title=result.title,
            text=result.summary,
            section="abstract",
            page=None,
            source="arxiv",
            score=round(1.0 - rank / max(len(results), 1), 3),
            doi=result.doi,
        )
        for rank, result in enumerate(results)
    ]

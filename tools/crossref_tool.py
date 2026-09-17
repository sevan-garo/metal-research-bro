"""search_crossref tool: expands search beyond the personal library via the Crossref API."""

import html
import re

from crossref.restful import Works

import config
from agent.state import RetrievedChunk

_WORKS = Works()
_TAG_RE = re.compile(r"<[^>]+>")


def _title_of(item: dict) -> str:
    titles = item.get("title") or []
    return titles[0] if titles else "Untitled"


def _clean_abstract(item: dict) -> str | None:
    # Crossref abstracts, when publishers submit one, are JATS XML fragments
    # (e.g. "<jats:p>...</jats:p>") rather than plain text.
    abstract = item.get("abstract")
    if not abstract:
        return None
    stripped = _TAG_RE.sub("", abstract)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def search_crossref(query: str, max_results: int | None = None) -> list[RetrievedChunk]:
    max_results = max_results or config.CROSSREF_MAX_RESULTS
    query_result = _WORKS.query(query).sort("relevance").order("desc")

    chunks: list[RetrievedChunk] = []
    for rank, item in enumerate(query_result):
        if rank >= max_results:
            break
        title = _title_of(item)
        abstract = _clean_abstract(item)
        chunks.append(
            RetrievedChunk(
                document_id=item.get("DOI", ""),
                title=title,
                text=abstract or title,
                section="abstract" if abstract else None,
                page=None,
                source="crossref",
                score=round(1.0 - rank / max_results, 3),
                doi=item.get("DOI") or None,
            )
        )
    return chunks

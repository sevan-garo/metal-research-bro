"""Shared state schema for the LangGraph agent."""

from typing import TypedDict


class Citation(TypedDict):
    document_id: str
    title: str
    section: str | None
    page: int | None


class RetrievedChunk(TypedDict):
    document_id: str
    title: str
    text: str
    section: str | None
    page: int | None
    source: str  # "local" | "zotero" | "arxiv" | "crossref"
    score: float
    doi: str | None


class SourceStatus(TypedDict):
    """Outcome of one retrieval branch, kept distinct from its result count.

    A source that was queried and legitimately found nothing (queried=True,
    count=0, error=None) must be distinguishable from one that failed to run
    at all (error set) and from one the router decided not to query
    (queried=False) — collapsing these into "no results" would hide a broken
    Zotero connection behind what looks like a normal empty search.
    """

    queried: bool
    count: int
    error: str | None


class AgentState(TypedDict):
    question: str
    history: list[dict[str, str]]
    sources_to_query: list[str]
    keyword_query: str
    local_results: list[RetrievedChunk]
    zotero_results: list[RetrievedChunk]
    external_results: list[RetrievedChunk]
    local_status: SourceStatus
    zotero_status: SourceStatus
    external_status: SourceStatus
    merged_results: list[RetrievedChunk]
    search_diagnostics: str
    answer: str
    citations: list[Citation]

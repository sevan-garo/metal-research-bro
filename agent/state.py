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


class AgentState(TypedDict):
    question: str
    history: list[dict[str, str]]
    sources_to_query: list[str]
    keyword_query: str
    local_results: list[RetrievedChunk]
    zotero_results: list[RetrievedChunk]
    external_results: list[RetrievedChunk]
    merged_results: list[RetrievedChunk]
    answer: str
    citations: list[Citation]

"""Graph nodes: router, retrieve_*, dedupe_merge, generate_answer."""

import logging
import re

from pydantic import BaseModel, Field

from agent.llm import get_llm
from agent.state import AgentState, Citation, RetrievedChunk, SourceStatus
from tools.arxiv_tool import search_arxiv
from tools.crossref_tool import search_crossref
from tools.local_rag import search_local_rag
from tools.zotero_tool import search_zotero

logger = logging.getLogger(__name__)

# --- router ---------------------------------------------------------------

ROUTER_PROMPT = """You are the routing step of a research assistant for a metallurgy PhD student.
Decide which of the following sources are relevant to answer the question below.
Only set a source to true if the question actually requires it; set more than
one to true if the question calls for combining sources.

- query_local: the researcher's own already-ingested local PDF corpus
- query_zotero: the researcher's personal Zotero reference library
- query_external: arXiv/Crossref, for finding papers NOT already in the personal library

Also extract a short keyword search query from the question: 3-8 words, only
the core technical terms, no question phrasing ("what does", "how does") and
no stopwords. Zotero and arXiv/Crossref do literal keyword matching, not
semantic search — a full natural-language question returns poor or wrong
results from them (e.g. "does" and "about" can spuriously match unrelated
papers), so this keyword form is what actually gets sent to those APIs.

Question: {question}
"""


class RoutingDecision(BaseModel):
    query_local: bool = Field(description="Search the researcher's own local paper corpus")
    query_zotero: bool = Field(description="Search the researcher's Zotero library")
    query_external: bool = Field(description="Search arXiv/Crossref for papers outside the personal library")
    keyword_query: str = Field(
        description="3-8 word keyword search query for Zotero/arXiv/Crossref, no question phrasing or stopwords"
    )


def router_node(state: AgentState) -> dict:
    try:
        structured_llm = get_llm().with_structured_output(RoutingDecision)
        decision = structured_llm.invoke(ROUTER_PROMPT.format(question=state["question"]))
    except Exception:
        # If the LLM itself is unreachable (e.g. Ollama isn't running), that's
        # a hard failure worth logging loudly — unlike an empty search result,
        # this means the agent can't reason at all, not just "found nothing".
        logger.exception("router_node: LLM call failed, defaulting to querying every source")
        return {
            "sources_to_query": ["retrieve_local", "retrieve_zotero", "retrieve_external"],
            "keyword_query": state["question"],
        }

    sources = []
    if decision.query_local:
        sources.append("retrieve_local")
    if decision.query_zotero:
        sources.append("retrieve_zotero")
    if decision.query_external:
        sources.append("retrieve_external")
    if not sources:
        # Never answer from nothing: if the router can't decide, query everything.
        sources = ["retrieve_local", "retrieve_zotero", "retrieve_external"]

    logger.info("router_node: sources=%s keyword_query=%r", sources, decision.keyword_query)
    return {"sources_to_query": sources, "keyword_query": decision.keyword_query}


# --- retrieve ---------------------------------------------------------------


def retrieve_local_node(state: AgentState) -> dict:
    try:
        # Embedding search handles full natural-language questions well
        # (unlike the keyword-matching APIs below) — see docs/adr/0011.
        results = search_local_rag(state["question"], top_k=5)
        logger.info("retrieve_local: %d result(s)", len(results))
        status = SourceStatus(queried=True, count=len(results), error=None)
    except Exception as exc:
        logger.exception("retrieve_local: search_local_rag failed")
        results, status = [], SourceStatus(queried=True, count=0, error=str(exc))
    return {"local_results": results, "local_status": status}


def retrieve_zotero_node(state: AgentState) -> dict:
    try:
        results = search_zotero(state["keyword_query"])
        logger.info("retrieve_zotero: %d result(s) for %r", len(results), state["keyword_query"])
        status = SourceStatus(queried=True, count=len(results), error=None)
    except Exception as exc:
        # e.g. Zotero desktop app not running, or its local API disabled
        # (docs/adr/0009) — a connection failure, not "no results".
        logger.exception("retrieve_zotero: search_zotero failed")
        results, status = [], SourceStatus(queried=True, count=0, error=str(exc))
    return {"zotero_results": results, "zotero_status": status}


def retrieve_external_node(state: AgentState) -> dict:
    keywords = state["keyword_query"]
    results: list[RetrievedChunk] = []
    errors: list[str] = []

    try:
        arxiv_results = search_arxiv(keywords)
        results.extend(arxiv_results)
        logger.info("retrieve_external: search_arxiv %d result(s) for %r", len(arxiv_results), keywords)
    except Exception as exc:
        logger.exception("retrieve_external: search_arxiv failed")
        errors.append(f"arxiv: {exc}")

    try:
        crossref_results = search_crossref(keywords)
        results.extend(crossref_results)
        logger.info("retrieve_external: search_crossref %d result(s) for %r", len(crossref_results), keywords)
    except Exception as exc:
        logger.exception("retrieve_external: search_crossref failed")
        errors.append(f"crossref: {exc}")

    status = SourceStatus(queried=True, count=len(results), error="; ".join(errors) or None)
    return {"external_results": results, "external_status": status}


# --- dedupe_merge -----------------------------------------------------------

# Keyword APIs (Zotero, arXiv, Crossref) return many loosely-matched results
# for a broad query — e.g. "deep learning microstructure segmentation steel"
# pulls in brain MRI and malware-classification papers on the strength of
# "deep learning" alone. Every arXiv/Crossref result also scores 1.0 at rank 0
# (ADR 0010's approximation, uncalibrated across sources), so nothing upstream
# already caps this. Passing all of them into generate_answer dilutes the
# prompt with noise and was observed to make the model unable to produce any
# properly cited sentence at all. Capping to the top N keeps the source list
# focused on what's actually likely to be relevant.
MAX_MERGED_RESULTS = 10


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _summarize_source_status(state: AgentState) -> str:
    """Render each source's outcome so "found nothing" and "search failed" are
    never ambiguous to whoever reads the answer — see docs/adr/0016."""
    lines = []
    for label, key in (
        ("Local corpus", "local_status"),
        ("Zotero", "zotero_status"),
        ("arXiv/Crossref", "external_status"),
    ):
        status: SourceStatus = state[key]
        if not status["queried"]:
            lines.append(f"- {label}: not queried")
        elif status["error"]:
            lines.append(f"- {label}: ERROR — {status['error']}")
        else:
            lines.append(f"- {label}: {status['count']} result(s)")
    return "\n".join(lines)


def dedupe_merge_node(state: AgentState) -> dict:
    all_results = state["local_results"] + state["zotero_results"] + state["external_results"]

    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    merged: list[RetrievedChunk] = []

    for chunk in sorted(all_results, key=lambda c: c["score"], reverse=True):
        if len(merged) >= MAX_MERGED_RESULTS:
            break
        if not chunk["title"] or chunk["title"] == "Untitled":
            continue
        doi = chunk["doi"]
        title_key = _normalize_title(chunk["title"])
        if (doi and doi in seen_dois) or title_key in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        seen_titles.add(title_key)
        merged.append(chunk)

    diagnostics = _summarize_source_status(state)
    logger.info("dedupe_merge: %d merged result(s) from %d raw\n%s", len(merged), len(all_results), diagnostics)
    return {"merged_results": merged, "search_diagnostics": diagnostics}


# --- generate_answer ---------------------------------------------------------

GENERATE_PROMPT = """You are a research assistant for a metallurgy PhD student.
Answer the question using ONLY the sources listed below. Every sentence that
states a fact must end with a citation in the exact format [Title, p.X] —
use the section name instead of a page number when no page is given, e.g.
[Title, Abstract]. Put a citation at the end of EVERY sentence that makes a
claim, not just once at the end of the paragraph. Do not use any knowledge
beyond what is in these sources. If the sources don't contain enough
information to answer, say so explicitly instead of guessing.

Example:
Sources:
1. [Grain Refinement in Al-Cu Alloys, p.4] (local): Grain refinement improves yield strength in Al-Cu alloys via Hall-Petch strengthening.

Question: How does grain size affect yield strength?

Answer: Grain refinement improves yield strength in Al-Cu alloys through Hall-Petch strengthening [Grain Refinement in Al-Cu Alloys, p.4].

Sources:
{sources_block}

Question: {question}

Answer:"""

_CITATION_PATTERN = re.compile(r"\[([^\[\]]+)\]")


def _format_sources_block(results: list[RetrievedChunk]) -> str:
    lines = []
    for i, chunk in enumerate(results, start=1):
        location = f"p.{chunk['page']}" if chunk["page"] else (chunk["section"] or "n/a")
        lines.append(f"{i}. [{chunk['title']}, {location}] ({chunk['source']}): {chunk['text'][:600]}")
    return "\n\n".join(lines)


def _extract_citations(text: str, results: list[RetrievedChunk]) -> list[Citation]:
    cited_titles = {match.rsplit(",", 1)[0].strip() for match in _CITATION_PATTERN.findall(text)}

    citations: list[Citation] = []
    seen_titles: set[str] = set()
    for chunk in results:
        if chunk["title"] in cited_titles and chunk["title"] not in seen_titles:
            seen_titles.add(chunk["title"])
            citations.append(
                Citation(
                    document_id=chunk["document_id"],
                    title=chunk["title"],
                    section=chunk["section"],
                    page=chunk["page"],
                )
            )
    return citations


_BRACKET_ONLY_RE = re.compile(r"^\[[^\[\]]*\]\.?$")


def _split_sentences(text: str) -> list[str]:
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    # A model tends to bolt one citation onto the very end of a paragraph
    # instead of citing each sentence inline, despite the prompt's example.
    # That citation then splits off as its own sentence-shaped fragment
    # (just "[Title, p.X]") holding no claim of its own — reattach it to the
    # sentence before it so citation-matching sees claim + citation together.
    sentences: list[str] = []
    for sentence in raw_sentences:
        if sentences and _BRACKET_ONLY_RE.match(sentence):
            sentences[-1] = f"{sentences[-1]} {sentence}"
        else:
            sentences.append(sentence)
    return sentences


def _sentence_cites_a_real_source(sentence: str, valid_titles: set[str]) -> bool:
    return any(match.rsplit(",", 1)[0].strip() in valid_titles for match in _CITATION_PATTERN.findall(sentence))


def _enforce_citations(raw_answer: str, results: list[RetrievedChunk]) -> tuple[str, list[Citation]]:
    """Drop any sentence whose citation doesn't match a retrieved source.

    A model-produced answer can name a citation-shaped bracket (e.g. an
    author-year reference it knows from training) that was never actually
    retrieved. Checking the overall answer for "has at least one valid
    citation" (as an earlier version of this function did) lets such
    fabricated brackets ride along next to one genuine one. Enforcing the
    "zero claims without a verifiable citation" requirement means checking
    every sentence individually and discarding the ones that fail — a blunt
    instrument (it can discard legitimate synthesis text a small local model
    forgot to cite), but the alternative is silently trusting the model, which
    the project's core requirement rules out. See docs/adr/0011.
    """
    valid_titles = {chunk["title"] for chunk in results}
    kept_sentences = [s for s in _split_sentences(raw_answer) if _sentence_cites_a_real_source(s, valid_titles)]

    if not kept_sentences:
        available = "\n".join(f"- {chunk['title']}" for chunk in results)
        message = (
            "I found related material but couldn't produce a properly sourced "
            f"answer from it. Retrieved but unused sources:\n{available}"
        )
        return message, []

    answer = " ".join(kept_sentences)
    return answer, _extract_citations(answer, results)


def generate_answer_node(state: AgentState) -> dict:
    merged = state["merged_results"]
    diagnostics = state["search_diagnostics"]

    if not merged:
        # Distinguish "every queried source legitimately found nothing" from
        # "a source errored out" in the answer itself, not just the logs —
        # a researcher relying on this for real work needs to know whether
        # to trust the silence or go check why Zotero/Ollama isn't reachable.
        logger.info("generate_answer: no merged results\n%s", diagnostics)
        answer = (
            "I couldn't find any sourced material to answer this question. "
            f"Search results by source:\n{diagnostics}"
        )
        return {"answer": answer, "citations": []}

    prompt = GENERATE_PROMPT.format(sources_block=_format_sources_block(merged), question=state["question"])
    raw_answer = get_llm().invoke(prompt).content

    answer, citations = _enforce_citations(raw_answer, merged)
    logger.info("generate_answer: %d citation(s) in final answer", len(citations))
    return {"answer": answer, "citations": citations}

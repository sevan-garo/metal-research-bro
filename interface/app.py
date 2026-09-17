"""Streamlit interface: chat with the agent, sources shown alongside each answer."""

import sys
from pathlib import Path

import streamlit as st

# Streamlit runs this script with its own directory as the sys.path root, not
# the project root, so `agent`/`tools`/`storage` aren't importable without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import run_agent

st.set_page_config(page_title="Metallurgy Research Companion", page_icon="🔬")
st.title("🔬 Metallurgy Research Companion")
st.caption(
    "Answers are drawn from your local corpus, your Zotero library, and arXiv/Crossref — "
    "every claim is cited, or the answer says so."
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_message(content: str, citations: list[dict], diagnostics: str) -> None:
    st.markdown(content)
    if citations:
        with st.expander(f"Sources ({len(citations)})"):
            for citation in citations:
                location = f"p.{citation['page']}" if citation["page"] else (citation["section"] or "")
                st.markdown(f"- **{citation['title']}** — {location}")
    # Always shown, even with zero citations: a source that was queried and
    # legitimately found nothing must stay visibly distinct from one that
    # errored out (e.g. Zotero not running) — see docs/adr/0016.
    if diagnostics:
        with st.expander("Search diagnostics", expanded=not citations):
            st.code(diagnostics, language=None)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_message(message["content"], message.get("citations", []), message.get("diagnostics", ""))
        else:
            st.markdown(message["content"])

if question := st.chat_input("Ask a metallurgy research question..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching local corpus, Zotero, and arXiv/Crossref..."):
            result = run_agent(question)
        render_message(result["answer"], result["citations"], result["search_diagnostics"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"],
            "diagnostics": result["search_diagnostics"],
        }
    )

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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("citations"):
            with st.expander(f"Sources ({len(message['citations'])})"):
                for citation in message["citations"]:
                    location = f"p.{citation['page']}" if citation["page"] else (citation["section"] or "")
                    st.markdown(f"- **{citation['title']}** — {location}")

if question := st.chat_input("Ask a metallurgy research question..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching local corpus, Zotero, and arXiv/Crossref..."):
            result = run_agent(question)
        st.markdown(result["answer"])
        if result["citations"]:
            with st.expander(f"Sources ({len(result['citations'])})"):
                for citation in result["citations"]:
                    location = f"p.{citation['page']}" if citation["page"] else (citation["section"] or "")
                    st.markdown(f"- **{citation['title']}** — {location}")

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "citations": result["citations"]}
    )

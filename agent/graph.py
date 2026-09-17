"""LangGraph state graph definition wiring the nodes in agent/nodes.py."""

from langgraph.graph import END, StateGraph

from agent.nodes import (
    dedupe_merge_node,
    generate_answer_node,
    retrieve_external_node,
    retrieve_local_node,
    retrieve_zotero_node,
    router_node,
)
from agent.state import AgentState

RETRIEVAL_NODES = ["retrieve_local", "retrieve_zotero", "retrieve_external"]


def _route_to_sources(state: AgentState) -> list[str]:
    return state["sources_to_query"]


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("retrieve_local", retrieve_local_node)
    graph.add_node("retrieve_zotero", retrieve_zotero_node)
    graph.add_node("retrieve_external", retrieve_external_node)
    graph.add_node("dedupe_merge", dedupe_merge_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", _route_to_sources, RETRIEVAL_NODES)
    for node in RETRIEVAL_NODES:
        graph.add_edge(node, "dedupe_merge")
    graph.add_edge("dedupe_merge", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


def run_agent(question: str) -> AgentState:
    app = build_graph()
    initial_state: AgentState = {
        "question": question,
        "history": [],
        "sources_to_query": [],
        "keyword_query": "",
        "local_results": [],
        "zotero_results": [],
        "external_results": [],
        "merged_results": [],
        "answer": "",
        "citations": [],
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    import sys

    user_question = " ".join(sys.argv[1:]) or "What does my corpus say about quenching and partitioning of AHSS steels?"
    result = run_agent(user_question)
    print("ANSWER:\n", result["answer"])
    print("\nCITATIONS:")
    for citation in result["citations"]:
        print(" -", citation)

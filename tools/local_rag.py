"""search_local_rag tool: vector search over the already-ingested local corpus."""

from agent.state import RetrievedChunk
from ingestion.embed import embed_texts
from storage import vector_store


def search_local_rag(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_embedding = embed_texts([query])[0]
    results = vector_store.query(query_embedding, top_k=top_k)

    ids = results["ids"][0]
    if not ids:
        return []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        RetrievedChunk(
            document_id=metadata["document_id"],
            title=metadata["title"],
            text=text,
            section=metadata["section"] or None,
            page=metadata["page"] or None,
            source="local",
            score=1.0 - distance,
            doi=None,
        )
        for text, metadata, distance in zip(documents, metadatas, distances)
    ]

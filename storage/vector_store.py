"""Chroma vector store wrapper (local, embedded, persisted to disk)."""

import chromadb
from chromadb.api.models.Collection import Collection

import config


def get_collection() -> Collection:
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    chunk_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    collection = get_collection()
    collection.add(ids=chunk_ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(embedding: list[float], top_k: int) -> dict:
    collection = get_collection()
    return collection.query(query_embeddings=[embedding], n_results=top_k)

"""Embedding generation for chunk text."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

import config


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(config.EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()

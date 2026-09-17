"""Shared local LLM client (Ollama)."""

from functools import lru_cache

from langchain_ollama import ChatOllama

import config


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.0) -> ChatOllama:
    return ChatOllama(model=config.OLLAMA_MODEL, base_url=config.OLLAMA_BASE_URL, temperature=temperature)

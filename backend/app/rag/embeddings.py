"""
Embeddings module using Google Gemini API.

Uses LangChain's GoogleGenerativeAIEmbeddings (gemini-embedding-001).

Model is configured via environment variables:
  - EMBEDDING_MODEL: Embedding model (default: models/gemini-embedding-001)
"""

import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings

DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"


def get_embedding_model_name() -> str:
    """Get embedding model name from environment variable."""
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


_embeddings_cache: dict[str, GoogleGenerativeAIEmbeddings] = {}


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Get GoogleGenerativeAIEmbeddings instance (cached per model name).

    GoogleGenerativeAIEmbeddings implements the Embeddings protocol:
    embed_documents(texts) and embed_query(text).
    Requires GOOGLE_API_KEY in the environment.
    """
    model_name = get_embedding_model_name()
    if model_name not in _embeddings_cache:
        print(f"[Embeddings] Loading model: {model_name}")
        _embeddings_cache[model_name] = GoogleGenerativeAIEmbeddings(model=model_name)
    return _embeddings_cache[model_name]


def get_model_info() -> dict:
    """Return information about current models."""
    return {
        "embedding_model": get_embedding_model_name(),
        "embedding_dimensions": 768,
    }

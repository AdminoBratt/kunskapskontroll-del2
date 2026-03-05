"""
Embeddings module using Google Gemini API.

Uses LangChain's GoogleGenerativeAIEmbeddings (gemini-embedding-001).
Cross-Encoder is kept from sentence-transformers for re-ranking search results.

Model is configured via environment variables:
  - EMBEDDING_MODEL: Embedding model (default: models/gemini-embedding-001)
  - CROSS_ENCODER_MODEL: Reranking model (default: ms-marco-MiniLM-L-6-v2)
"""

import os
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sentence_transformers import CrossEncoder

DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_embedding_model_name() -> str:
    """Get embedding model name from environment variable."""
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def get_cross_encoder_model_name() -> str:
    """Get cross-encoder model name from environment variable."""
    return os.getenv("CROSS_ENCODER_MODEL", DEFAULT_CROSS_ENCODER)


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


_cross_encoder_cache: dict[str, CrossEncoder] = {}


def get_cross_encoder() -> CrossEncoder:
    """
    Load and cache the Cross-Encoder model for re-ranking.

    Cross-Encoder sees query and document together and gives
    more accurate relevance scores than bi-encoder.
    """
    model_name = get_cross_encoder_model_name()
    if model_name not in _cross_encoder_cache:
        print(f"[CrossEncoder] Loading model: {model_name}")
        _cross_encoder_cache[model_name] = CrossEncoder(model_name)
    return _cross_encoder_cache[model_name]


def rerank_results(
    query: str,
    texts: List[str],
    top_k: int | None = None,
) -> List[tuple[int, float]]:
    """
    Re-rank texts with Cross-Encoder.

    Args:
        query: The search query
        texts: List of texts to re-rank
        top_k: Number of results to return (None = all)

    Returns:
        List of tuples (original_index, score) sorted by score (highest first)
    """
    if not texts:
        return []

    cross_encoder = get_cross_encoder()
    pairs = [[query, text] for text in texts]
    scores = cross_encoder.predict(pairs)

    indexed_scores = [(i, float(score)) for i, score in enumerate(scores)]
    indexed_scores.sort(key=lambda x: x[1], reverse=True)

    if top_k is not None:
        indexed_scores = indexed_scores[:top_k]

    return indexed_scores


def get_model_info() -> dict:
    """Return information about current models."""
    return {
        "embedding_model": get_embedding_model_name(),
        "cross_encoder_model": get_cross_encoder_model_name(),
        "embedding_dimensions": 768,
    }

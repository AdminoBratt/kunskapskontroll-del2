"""
Embeddings module for local vector representations.

Model is configured via environment variables:
  - EMBEDDING_MODEL: Embedding model (default: paraphrase-multilingual-mpnet-base-v2)
  - CROSS_ENCODER_MODEL: Reranking model (default: ms-marco-MiniLM-L-6-v2)

Cross-Encoder is used for re-ranking search results.
"""

import os
from functools import lru_cache
from typing import List, Protocol

from sentence_transformers import SentenceTransformer, CrossEncoder

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def get_embedding_model_name() -> str:
    """Get embedding model name from environment variable."""
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def get_cross_encoder_model_name() -> str:
    """Get cross-encoder model name from environment variable."""
    return os.getenv("CROSS_ENCODER_MODEL", DEFAULT_CROSS_ENCODER)


class Embeddings(Protocol):
    """Protocol for embeddings classes."""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...
    
    def embed_query(self, text: str) -> List[float]:
        ...


class LocalSentenceTransformerEmbeddings:
    """
    Wrapper for SentenceTransformer that runs completely locally.
    """
    
    def __init__(self, model: SentenceTransformer):
        self._model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute embeddings for a list of documents."""
        embeddings = self._model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Compute embedding for a single query."""
        return self.embed_documents([text])[0]


_embedding_model_cache: dict[str, SentenceTransformer] = {}


def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the SentenceTransformer model.
    
    Model is cached per model name so that switching via environment variable works.
    """
    model_name = get_embedding_model_name()
    
    if model_name not in _embedding_model_cache:
        print(f"[Embeddings] Loading model: {model_name}")
        _embedding_model_cache[model_name] = SentenceTransformer(model_name)
    
    return _embedding_model_cache[model_name]


def get_embeddings() -> LocalSentenceTransformerEmbeddings:
    """
    Get embeddings instance.
    
    Returns:
        LocalSentenceTransformerEmbeddings: Wrapper for embedding computations.
    """
    model = get_embedding_model()
    return LocalSentenceTransformerEmbeddings(model)


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
    top_k: int | None = None
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
        "embedding_dimensions": get_embedding_model().get_sentence_embedding_dimension(),
    }

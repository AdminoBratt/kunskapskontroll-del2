"""
Backwards compatibility for existing imports.

This file is kept to avoid breaking existing code that imports from chains.py.
All new search code is in search.py.
"""

from dataclasses import dataclass
from typing import List

from app.rag.search import (
    SearchResult,
    SearchResponse,
    hybrid_search,
    semantic_only_search,
    keyword_only_search,
)


@dataclass
class RAGResponse:
    """Backwards compatible response class."""
    answer: str
    sources: List[dict]
    question: str


def rag_query_without_llm(question: str, k: int = 5) -> RAGResponse:
    """
    Backwards compatible function for semantic search.
    
    Use instead: search.semantic_only_search()
    """
    from app.database import SessionLocal
    
    with SessionLocal() as db:
        response = semantic_only_search(db, question, k=k)
    
    class FakeDoc:
        def __init__(self, result: SearchResult):
            self.page_content = result.chunk_text
            self.metadata = {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.document_title,
                "page_number": result.page_number,
                "chunk_index": result.chunk_index,
                "similarity": result.score,
                "distance": 1 - result.score,
            }
    
    sources = [FakeDoc(r) for r in response.results]
    
    return RAGResponse(
        answer="",
        sources=sources,
        question=question
    )


def get_rag_chain_info() -> dict:
    """Return system information."""
    return {
        "llm": {
            "available": False,
            "model_path": None,
            "status": "LLM removed - search-only mode"
        },
        "retriever": {
            "type": "HybridSearch",
            "default_k": 10,
            "methods": ["semantic", "keyword", "hybrid"]
        },
    }

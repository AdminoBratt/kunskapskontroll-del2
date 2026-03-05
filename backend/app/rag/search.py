"""
Hybrid search using LangChain's PGVector, EnsembleRetriever,
and ContextualCompressionRetriever with CrossEncoderReranker.

Vector store: langchain_postgres.PGVector (manages langchain_pg_collection /
langchain_pg_embedding tables).
Hybrid fusion: EnsembleRetriever with weighted RRF (semantic 0.7, keyword 0.3).
Reranking: CrossEncoderReranker via ContextualCompressionRetriever.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.rag.embeddings import get_cross_encoder_model_name, get_embeddings

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres"
)
COLLECTION_NAME = "pdf_chunks"


# ---------------------------------------------------------------------------
# SQLAlchemy engine for direct SQL queries (keyword FTS, chunk listing, etc.)
# Uses psycopg2 dialect (same as the main app engine).
# ---------------------------------------------------------------------------

_search_engine = None


def _get_search_engine():
    global _search_engine
    if _search_engine is None:
        url = DATABASE_URL
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        _search_engine = create_engine(url)
    return _search_engine


# ---------------------------------------------------------------------------
# PGVector store (psycopg3 connection string required by langchain-postgres)
# ---------------------------------------------------------------------------

_vector_store: Optional[PGVector] = None


def _get_pgvector_url() -> str:
    """Convert DATABASE_URL to psycopg3 format for langchain-postgres."""
    url = DATABASE_URL
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url[len("postgresql+psycopg2://"):]
    return url


def get_vector_store() -> PGVector:
    """Get (or lazily create) the PGVector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = PGVector(
            connection=_get_pgvector_url(),
            embeddings=get_embeddings(),
            collection_name=COLLECTION_NAME,
            use_jsonb=True,
        )
    return _vector_store


# ---------------------------------------------------------------------------
# Data classes (unchanged public interface)
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A search result from the hybrid search."""
    chunk_id: int
    document_id: int
    document_title: str
    page_number: int
    chunk_index: int
    chunk_text: str
    category_id: Optional[int]
    category_name: Optional[str]
    language: str
    upload_date: datetime
    score: float
    vector_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    rerank_score: Optional[float] = None


@dataclass
class SearchResponse:
    """Response from the search function."""
    query: str
    results: List[SearchResult]
    total_count: int
    search_type: str  # "hybrid", "semantic", "keyword", "hybrid_reranked"


# ---------------------------------------------------------------------------
# Keyword retriever (custom BaseRetriever with PostgreSQL FTS)
# ---------------------------------------------------------------------------


class KeywordRetriever(BaseRetriever):
    """Full-text search retriever using PostgreSQL tsvector on langchain_pg_embedding."""

    k: int = 20
    category_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> List[Document]:
        engine = _get_search_engine()
        params: dict = {
            "query": query,
            "limit": self.k,
            "collection_name": COLLECTION_NAME,
        }

        extra_filters = [
            "to_tsvector('english', lpe.document) @@ plainto_tsquery('english', :query)"
        ]

        if self.category_id is not None:
            extra_filters.append("(lpe.cmetadata->>'category_id')::int = :category_id")
            params["category_id"] = self.category_id

        if self.date_from is not None:
            extra_filters.append(
                "(lpe.cmetadata->>'upload_date')::timestamp >= :date_from"
            )
            params["date_from"] = self.date_from

        if self.date_to is not None:
            extra_filters.append(
                "(lpe.cmetadata->>'upload_date')::timestamp <= :date_to"
            )
            params["date_to"] = self.date_to

        extra_where = " AND ".join(extra_filters)

        sql = text(f"""
            SELECT
                lpe.document,
                lpe.cmetadata,
                ts_rank_cd(
                    to_tsvector('english', lpe.document),
                    plainto_tsquery('english', :query)
                ) AS rank_score
            FROM langchain_pg_embedding lpe
            WHERE lpe.collection_id = (
                SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name
            )
            AND {extra_where}
            ORDER BY rank_score DESC
            LIMIT :limit
        """)

        with engine.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            Document(
                page_content=row.document,
                metadata=dict(row.cmetadata) if row.cmetadata else {},
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Helper: convert List[Document] → List[SearchResult]
# ---------------------------------------------------------------------------


def _parse_upload_date(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return datetime.now()


def _docs_to_results(
    docs: List[Document],
    search_type: str,
) -> List[SearchResult]:
    results = []
    n = len(docs)
    for i, doc in enumerate(docs):
        meta = doc.metadata or {}
        # Rank-based synthetic score so that position 0 has the highest value
        score = 1.0 / (1.0 + i) if search_type != "semantic" else meta.get("score", 0.0)
        results.append(
            SearchResult(
                chunk_id=0,  # No sequential int ID in LangChain's vector store
                document_id=meta.get("document_id", 0),
                document_title=meta.get("document_title", ""),
                page_number=meta.get("page_number", 0),
                chunk_index=meta.get("chunk_index", 0),
                chunk_text=doc.page_content,
                category_id=meta.get("category_id"),
                category_name=meta.get("category_name"),
                language=meta.get("language", ""),
                upload_date=_parse_upload_date(meta.get("upload_date")),
                score=score,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Helpers for document management
# ---------------------------------------------------------------------------


def delete_document_vectors(document_id: int) -> None:
    """Delete all langchain_pg_embedding rows for a document."""
    engine = _get_search_engine()
    sql = text("""
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name
        )
        AND cmetadata @> :metadata_filter::jsonb
    """)
    with engine.connect() as conn:
        conn.execute(
            sql,
            {
                "collection_name": COLLECTION_NAME,
                "metadata_filter": json.dumps({"document_id": document_id}),
            },
        )
        conn.commit()


def get_chunks_for_document(document_id: int) -> list[dict]:
    """Return ordered chunk rows for a document from langchain_pg_embedding."""
    engine = _get_search_engine()
    sql = text("""
        SELECT
            lpe.document AS chunk_text,
            lpe.cmetadata AS metadata
        FROM langchain_pg_embedding lpe
        WHERE lpe.collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name
        )
        AND lpe.cmetadata @> :metadata_filter::jsonb
        ORDER BY
            (lpe.cmetadata->>'page_number')::int,
            (lpe.cmetadata->>'chunk_index')::int
    """)
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "collection_name": COLLECTION_NAME,
                "metadata_filter": json.dumps({"document_id": document_id}),
            },
        ).fetchall()

    return [
        {
            "chunk_text": row.chunk_text,
            "page_number": (row.metadata or {}).get("page_number", 0),
            "chunk_index": (row.metadata or {}).get("chunk_index", 0),
        }
        for row in rows
    ]


def count_chunks_for_document(document_id: int) -> int:
    """Count chunks in langchain_pg_embedding for a specific document."""
    engine = _get_search_engine()
    sql = text("""
        SELECT COUNT(*) FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name
        )
        AND cmetadata @> :metadata_filter::jsonb
    """)
    with engine.connect() as conn:
        result = conn.execute(
            sql,
            {
                "collection_name": COLLECTION_NAME,
                "metadata_filter": json.dumps({"document_id": document_id}),
            },
        ).scalar()
    return result or 0


def count_all_chunks() -> int:
    """Count all chunks in the collection."""
    engine = _get_search_engine()
    sql = text("""
        SELECT COUNT(*) FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name
        )
    """)
    with engine.connect() as conn:
        result = conn.execute(
            sql, {"collection_name": COLLECTION_NAME}
        ).scalar()
    return result or 0


# ---------------------------------------------------------------------------
# Public search functions (same signatures as before)
# ---------------------------------------------------------------------------


def _build_filter(category_id, date_from, date_to) -> Optional[dict]:
    """Build a metadata filter dict for PGVector (supports category_id only)."""
    if category_id is not None:
        return {"category_id": category_id}
    return None


def hybrid_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> SearchResponse:
    """
    Hybrid search combining semantic (PGVector) and keyword (FTS) search
    via EnsembleRetriever with weighted Reciprocal Rank Fusion.
    """
    vs = get_vector_store()
    meta_filter = _build_filter(category_id, date_from, date_to)

    semantic_ret = vs.as_retriever(
        search_kwargs={"k": k * 2, "filter": meta_filter}
    )
    keyword_ret = KeywordRetriever(
        k=k * 2,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    ensemble = EnsembleRetriever(
        retrievers=[semantic_ret, keyword_ret],
        weights=[semantic_weight, keyword_weight],
    )

    docs = ensemble.invoke(query)[:k]
    results = _docs_to_results(docs, "hybrid")

    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="hybrid",
    )


def hybrid_search_with_reranking(
    db: Session,
    query: str,
    k: int = 10,
    rerank_candidates: int = 50,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> SearchResponse:
    """
    Hybrid search with Cross-Encoder reranking via ContextualCompressionRetriever.

    Step 1: EnsembleRetriever fetches rerank_candidates docs.
    Step 2: CrossEncoderReranker reranks and returns top-k.
    """
    vs = get_vector_store()
    meta_filter = _build_filter(category_id, date_from, date_to)

    semantic_ret = vs.as_retriever(
        search_kwargs={"k": rerank_candidates, "filter": meta_filter}
    )
    keyword_ret = KeywordRetriever(
        k=rerank_candidates,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    ensemble = EnsembleRetriever(
        retrievers=[semantic_ret, keyword_ret],
        weights=[semantic_weight, keyword_weight],
    )

    reranker = CrossEncoderReranker(
        model=HuggingFaceCrossEncoder(model_name=get_cross_encoder_model_name()),
        top_n=k,
    )
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=ensemble,
    )

    docs = compression_retriever.invoke(query)

    # Populate rerank_score from relevance_score metadata set by CrossEncoderReranker
    results = []
    for i, doc in enumerate(docs):
        meta = doc.metadata or {}
        upload_date = _parse_upload_date(meta.get("upload_date"))
        rerank_score = meta.get("relevance_score")
        results.append(
            SearchResult(
                chunk_id=0,
                document_id=meta.get("document_id", 0),
                document_title=meta.get("document_title", ""),
                page_number=meta.get("page_number", 0),
                chunk_index=meta.get("chunk_index", 0),
                chunk_text=doc.page_content,
                category_id=meta.get("category_id"),
                category_name=meta.get("category_name"),
                language=meta.get("language", ""),
                upload_date=upload_date,
                score=1.0 / (1.0 + i),
                rerank_score=float(rerank_score) if rerank_score is not None else None,
            )
        )

    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="hybrid_reranked",
    )


def semantic_only_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> SearchResponse:
    """Semantic search only using PGVector cosine similarity."""
    vs = get_vector_store()
    meta_filter = _build_filter(category_id, date_from, date_to)

    docs_and_scores = vs.similarity_search_with_relevance_scores(
        query, k=k, filter=meta_filter
    )

    results = []
    for i, (doc, score) in enumerate(docs_and_scores):
        meta = doc.metadata or {}
        results.append(
            SearchResult(
                chunk_id=0,
                document_id=meta.get("document_id", 0),
                document_title=meta.get("document_title", ""),
                page_number=meta.get("page_number", 0),
                chunk_index=meta.get("chunk_index", 0),
                chunk_text=doc.page_content,
                category_id=meta.get("category_id"),
                category_name=meta.get("category_name"),
                language=meta.get("language", ""),
                upload_date=_parse_upload_date(meta.get("upload_date")),
                score=float(score),
                vector_rank=i + 1,
            )
        )

    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="semantic",
    )


def keyword_only_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> SearchResponse:
    """Keyword (full-text) search only using PostgreSQL tsvector."""
    keyword_ret = KeywordRetriever(
        k=k,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )

    docs = keyword_ret.invoke(query)

    results = []
    for i, doc in enumerate(docs):
        meta = doc.metadata or {}
        results.append(
            SearchResult(
                chunk_id=0,
                document_id=meta.get("document_id", 0),
                document_title=meta.get("document_title", ""),
                page_number=meta.get("page_number", 0),
                chunk_index=meta.get("chunk_index", 0),
                chunk_text=doc.page_content,
                category_id=meta.get("category_id"),
                category_name=meta.get("category_name"),
                language=meta.get("language", ""),
                upload_date=_parse_upload_date(meta.get("upload_date")),
                score=1.0 / (1.0 + i),
                keyword_rank=i + 1,
            )
        )

    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="keyword",
    )

"""
Semantic search using LangChain's PGVector.

Vector store: langchain_postgres.PGVector (manages langchain_pg_collection /
langchain_pg_embedding tables).
Search: cosine similarity via PGVector.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.rag.embeddings import get_embeddings

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres"
)
COLLECTION_NAME = "pdf_chunks"


# ---------------------------------------------------------------------------
# SQLAlchemy engine for direct SQL queries (chunk listing, delete, count).
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
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A search result from semantic search."""
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


@dataclass
class SearchResponse:
    """Response from the search function."""
    query: str
    results: List[SearchResult]
    total_count: int
    search_type: str  # "semantic"


def _parse_upload_date(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return datetime.now()



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
        AND cmetadata @> CAST(:metadata_filter AS jsonb)
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
        AND lpe.cmetadata @> CAST(:metadata_filter AS jsonb)
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
        AND cmetadata @> CAST(:metadata_filter AS jsonb)
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
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sql, {"collection_name": COLLECTION_NAME}
            ).scalar()
        return result or 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Public search functions
# ---------------------------------------------------------------------------


def semantic_only_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    document_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> SearchResponse:
    """Semantic search using PGVector cosine similarity."""
    vs = get_vector_store()
    if document_id is not None:
        meta_filter = {"document_id": document_id}
    elif category_id is not None:
        meta_filter = {"category_id": category_id}
    else:
        meta_filter = None

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



"""
Hybrid search: combines semantic vector search with full-text search.

Uses Reciprocal Rank Fusion (RRF) to combine results from both search methods.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.embeddings import get_embeddings, rerank_results


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
    search_type: str  # "hybrid", "semantic", "keyword"


def semantic_search(
    db: Session,
    query: str,
    k: int = 20,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[tuple]:
    """
    Semantic search with vector similarity.
    
    Returns:
        List of tuples (chunk_id, distance, rank)
    """
    embedder = get_embeddings()
    query_embedding = embedder.embed_query(query)
    embedding_str = str(query_embedding)
    
    filters = []
    params = {"embedding": embedding_str, "limit": k}
    
    if category_id:
        filters.append("pd.category_id = :category_id")
        params["category_id"] = category_id
    if date_from:
        filters.append("pd.upload_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        filters.append("pd.upload_date <= :date_to")
        params["date_to"] = date_to
    
    where_clause = "WHERE " + " AND ".join(filters) if filters else ""
    
    sql = f"""
        SELECT 
            dc.chunk_id,
            ce.embedding <=> :embedding AS distance
        FROM chunk_embeddings ce
        JOIN document_chunks dc ON dc.chunk_id = ce.chunk_id
        JOIN pdf_documents pd ON pd.document_id = dc.document_id
        {where_clause}
        ORDER BY ce.embedding <=> :embedding
        LIMIT :limit
    """
    
    results = db.execute(text(sql), params).fetchall()
    return [(r.chunk_id, r.distance, idx + 1) for idx, r in enumerate(results)]


def keyword_search(
    db: Session,
    query: str,
    k: int = 20,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[tuple]:
    """
    Full-text search with PostgreSQL ts_vector.
    
    Returns:
        List of tuples (chunk_id, rank_score, rank)
    """
    filters = []
    params = {"query": query, "limit": k}
    
    if category_id:
        filters.append("pd.category_id = :category_id")
        params["category_id"] = category_id
    if date_from:
        filters.append("pd.upload_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        filters.append("pd.upload_date <= :date_to")
        params["date_to"] = date_to
    
    where_clause = " AND ".join(filters) if filters else "TRUE"
    
    sql = f"""
        SELECT 
            dc.chunk_id,
            ts_rank_cd(
                to_tsvector('english', dc.chunk_text),
                plainto_tsquery('english', :query)
            ) AS rank_score
        FROM document_chunks dc
        JOIN pdf_documents pd ON pd.document_id = dc.document_id
        WHERE to_tsvector('english', dc.chunk_text) @@ plainto_tsquery('english', :query)
          AND {where_clause}
        ORDER BY rank_score DESC
        LIMIT :limit
    """
    
    results = db.execute(text(sql), params).fetchall()
    return [(r.chunk_id, r.rank_score, idx + 1) for idx, r in enumerate(results)]


def rrf_merge(
    semantic_results: List[tuple],
    keyword_results: List[tuple],
    k: int = 60,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> List[int]:
    """
    Reciprocal Rank Fusion to combine search results.
    
    RRF Score = sum(weight / (k + rank)) for each search source
    
    Args:
        semantic_results: [(chunk_id, distance, rank), ...]
        keyword_results: [(chunk_id, score, rank), ...]
        k: RRF constant (default 60)
        semantic_weight: Weight for semantic search
        keyword_weight: Weight for keyword search
    
    Returns:
        Sorted list of chunk_ids
    """
    scores = {}
    chunk_ranks = {}
    
    for chunk_id, _, rank in semantic_results:
        scores[chunk_id] = scores.get(chunk_id, 0) + semantic_weight / (k + rank)
        if chunk_id not in chunk_ranks:
            chunk_ranks[chunk_id] = {"vector": None, "keyword": None}
        chunk_ranks[chunk_id]["vector"] = rank
    
    for chunk_id, _, rank in keyword_results:
        scores[chunk_id] = scores.get(chunk_id, 0) + keyword_weight / (k + rank)
        if chunk_id not in chunk_ranks:
            chunk_ranks[chunk_id] = {"vector": None, "keyword": None}
        chunk_ranks[chunk_id]["keyword"] = rank
    
    sorted_chunks = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return sorted_chunks, scores, chunk_ranks


def get_chunk_details(db: Session, chunk_ids: List[int]) -> dict:
    """Get complete information for a list of chunks."""
    if not chunk_ids:
        return {}
    
    placeholders = ", ".join(str(cid) for cid in chunk_ids)
    
    sql = f"""
        SELECT 
            dc.chunk_id,
            dc.document_id,
            dc.page_number,
            dc.chunk_index,
            dc.chunk_text,
            pd.title AS document_title,
            pd.category_id,
            pd.language,
            pd.upload_date,
            c.name AS category_name
        FROM document_chunks dc
        JOIN pdf_documents pd ON pd.document_id = dc.document_id
        LEFT JOIN categories c ON c.category_id = pd.category_id
        WHERE dc.chunk_id IN ({placeholders})
    """
    
    results = db.execute(text(sql)).fetchall()
    return {r.chunk_id: r for r in results}


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
    Hybrid search combining semantic and keyword search.
    
    Args:
        db: Database session
        query: Search query
        k: Number of results to return
        category_id: Filter by category
        date_from: Filter from date
        date_to: Filter to date
        semantic_weight: Weight for semantic search (0-1)
        keyword_weight: Weight for keyword search (0-1)
    
    Returns:
        SearchResponse with combined results
    """
    filter_kwargs = {
        "category_id": category_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    
    semantic_results = semantic_search(db, query, k=k*2, **filter_kwargs)
    keyword_results = keyword_search(db, query, k=k*2, **filter_kwargs)
    
    if not semantic_results and not keyword_results:
        return SearchResponse(
            query=query,
            results=[],
            total_count=0,
            search_type="hybrid"
        )
    
    sorted_chunk_ids, scores, chunk_ranks = rrf_merge(
        semantic_results,
        keyword_results,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
    )
    
    top_chunk_ids = sorted_chunk_ids[:k]
    chunk_details = get_chunk_details(db, top_chunk_ids)
    
    results = []
    for chunk_id in top_chunk_ids:
        if chunk_id not in chunk_details:
            continue
        
        row = chunk_details[chunk_id]
        ranks = chunk_ranks.get(chunk_id, {})
        
        results.append(SearchResult(
            chunk_id=chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            chunk_text=row.chunk_text,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            upload_date=row.upload_date,
            score=scores.get(chunk_id, 0),
            vector_rank=ranks.get("vector"),
            keyword_rank=ranks.get("keyword"),
        ))
    
    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="hybrid"
    )


def semantic_only_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> SearchResponse:
    """Semantic search only (without keywords)."""
    filter_kwargs = {
        "category_id": category_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    
    semantic_results = semantic_search(db, query, k=k, **filter_kwargs)
    
    if not semantic_results:
        return SearchResponse(
            query=query,
            results=[],
            total_count=0,
            search_type="semantic"
        )
    
    chunk_ids = [r[0] for r in semantic_results]
    chunk_details = get_chunk_details(db, chunk_ids)
    
    results = []
    for chunk_id, distance, rank in semantic_results:
        if chunk_id not in chunk_details:
            continue
        
        row = chunk_details[chunk_id]
        similarity = 1 - distance
        
        results.append(SearchResult(
            chunk_id=chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            chunk_text=row.chunk_text,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            upload_date=row.upload_date,
            score=similarity,
            vector_rank=rank,
            keyword_rank=None,
        ))
    
    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="semantic"
    )


def keyword_only_search(
    db: Session,
    query: str,
    k: int = 10,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> SearchResponse:
    """Keyword search only (without semantics)."""
    filter_kwargs = {
        "category_id": category_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    
    keyword_results = keyword_search(db, query, k=k, **filter_kwargs)
    
    if not keyword_results:
        return SearchResponse(
            query=query,
            results=[],
            total_count=0,
            search_type="keyword"
        )
    
    chunk_ids = [r[0] for r in keyword_results]
    chunk_details = get_chunk_details(db, chunk_ids)
    
    results = []
    for chunk_id, rank_score, rank in keyword_results:
        if chunk_id not in chunk_details:
            continue
        
        row = chunk_details[chunk_id]
        
        results.append(SearchResult(
            chunk_id=chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            chunk_text=row.chunk_text,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            upload_date=row.upload_date,
            score=float(rank_score),
            vector_rank=None,
            keyword_rank=rank,
        ))
    
    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="keyword"
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
    Hybrid search with Cross-Encoder re-ranking.
    
    Step 1: Fetch more candidates with regular hybrid search (bi-encoder)
    Step 2: Re-rank candidates with Cross-Encoder for better precision
    
    Args:
        db: Database session
        query: Search query
        k: Number of final results to return
        rerank_candidates: Number of candidates to fetch for re-ranking (should be > k)
        category_id: Filter by category
        date_from: Filter from date
        date_to: Filter to date
        semantic_weight: Weight for semantic search (0-1)
        keyword_weight: Weight for keyword search (0-1)
    
    Returns:
        SearchResponse with re-ranked results
    """
    filter_kwargs = {
        "category_id": category_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    
    semantic_results = semantic_search(db, query, k=rerank_candidates, **filter_kwargs)
    keyword_results = keyword_search(db, query, k=rerank_candidates, **filter_kwargs)
    
    if not semantic_results and not keyword_results:
        return SearchResponse(
            query=query,
            results=[],
            total_count=0,
            search_type="hybrid_reranked"
        )
    
    sorted_chunk_ids, scores, chunk_ranks = rrf_merge(
        semantic_results,
        keyword_results,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
    )
    
    candidate_chunk_ids = sorted_chunk_ids[:rerank_candidates]
    chunk_details = get_chunk_details(db, candidate_chunk_ids)
    
    texts_to_rerank = []
    valid_chunk_ids = []
    for chunk_id in candidate_chunk_ids:
        if chunk_id in chunk_details:
            texts_to_rerank.append(chunk_details[chunk_id].chunk_text)
            valid_chunk_ids.append(chunk_id)
    
    reranked = rerank_results(query, texts_to_rerank, top_k=k)
    
    results = []
    for new_rank, (original_idx, rerank_score) in enumerate(reranked, start=1):
        chunk_id = valid_chunk_ids[original_idx]
        row = chunk_details[chunk_id]
        ranks = chunk_ranks.get(chunk_id, {})
        
        results.append(SearchResult(
            chunk_id=chunk_id,
            document_id=row.document_id,
            document_title=row.document_title,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            chunk_text=row.chunk_text,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            upload_date=row.upload_date,
            score=scores.get(chunk_id, 0),
            vector_rank=ranks.get("vector"),
            keyword_rank=ranks.get("keyword"),
            rerank_score=rerank_score,
        ))
    
    return SearchResponse(
        query=query,
        results=results,
        total_count=len(results),
        search_type="hybrid_reranked"
    )

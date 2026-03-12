from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from langchain_core.documents import Document

from app.database import get_db, init_pgvector
from app.models import Category, PdfDocument
from app.pdf_extraction import extract_pdf_document
from app.rag.chunking import split_page_text
from app.rag.embeddings import get_embeddings, get_model_info
from app.rag.search import (
    hybrid_search,
    hybrid_search_with_reranking,
    semantic_only_search,
    keyword_only_search,
    SearchResponse,
    get_vector_store,
    delete_document_vectors,
    get_chunks_for_document,
    count_chunks_for_document,
    count_all_chunks,
)
from app.rag.llm import generate_answer, check_llm_status, get_llm_info

app = FastAPI(title="PDF Search API", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Pydantic Models
# =============================================================================

class SearchQuery(BaseModel):
    query: str
    k: int = 10
    category_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    rerank: bool = False
    rerank_candidates: int = 50


class AskQuery(BaseModel):
    question: str
    k: int = 5
    category_id: Optional[int] = None
    model: str = "gemini-2.0-flash"
    rerank: bool = True


class CategoryCreate(BaseModel):
    name: str


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[int] = None
    language: Optional[str] = None


class BulkCategoryUpdate(BaseModel):
    document_ids: list[int]
    category_id: int


# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
def startup():
    init_pgvector()
    # Warm up the vector store so langchain_pg_collection / langchain_pg_embedding
    # tables are created before the first request.
    get_vector_store()


# =============================================================================
# Health & Info
# =============================================================================

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/info")
async def system_info():
    model_info = get_model_info()
    llm_info = get_llm_info()
    ollama_status = await check_llm_status()
    return {
        "name": "PDF RAG API",
        "version": "4.0",
        "search_modes": ["hybrid", "hybrid_reranked", "semantic", "keyword"],
        "embedding_model": model_info["embedding_model"],
        "embedding_dimensions": model_info["embedding_dimensions"],
        "cross_encoder_model": model_info["cross_encoder_model"],
        "reranking_available": True,
        "llm": {
            **llm_info,
            "status": ollama_status,
        },
    }


# =============================================================================
# Categories
# =============================================================================

@app.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return [{"category_id": c.category_id, "name": c.name} for c in categories]


@app.post("/categories")
def create_category(cat: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(name=cat.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return {"category_id": category.category_id, "name": category.name}


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return {"deleted": True, "category_id": category_id}


# =============================================================================
# Documents
# =============================================================================

@app.get("/documents")
def list_documents(
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(PdfDocument)

    if category_id:
        query = query.filter(PdfDocument.category_id == category_id)

    documents = query.order_by(PdfDocument.upload_date.desc()).all()

    return [{
        "document_id": d.document_id,
        "title": d.title,
        "category_id": d.category_id,
        "category": d.category.name if d.category else None,
        "language": d.language,
        "upload_date": d.upload_date,
    } for d in documents]


@app.get("/documents/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(PdfDocument).filter(
        PdfDocument.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count = count_chunks_for_document(document_id)

    return {
        "document_id": document.document_id,
        "title": document.title,
        "category_id": document.category_id,
        "category": document.category.name if document.category else None,
        "language": document.language,
        "upload_date": document.upload_date,
        "size_bytes": len(document.pdf_data) if document.pdf_data else 0,
        "chunk_count": chunk_count,
    }


@app.patch("/documents/{document_id}")
def update_document(
    document_id: int,
    update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """Update a document's metadata (title, category, language)."""
    document = db.query(PdfDocument).filter(
        PdfDocument.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if update.title is not None:
        document.title = update.title
    if update.category_id is not None:
        document.category_id = update.category_id
    if update.language is not None:
        document.language = update.language

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.document_id,
        "title": document.title,
        "category_id": document.category_id,
        "category": document.category.name if document.category else None,
        "language": document.language,
        "updated": True,
    }


@app.patch("/documents/bulk/category")
def bulk_update_category(
    update: BulkCategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update category for multiple documents at once."""
    category = db.query(Category).filter(
        Category.category_id == update.category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    updated_count = db.query(PdfDocument).filter(
        PdfDocument.document_id.in_(update.document_ids)
    ).update({"category_id": update.category_id}, synchronize_session=False)

    db.commit()

    return {
        "updated_count": updated_count,
        "category_id": update.category_id,
        "category_name": category.name,
    }


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category_id: Optional[int] = Form(None),
    language: str = Form("sv"),
    extract_text: bool = Form(True),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content-type, must be application/pdf")

    pdf_data = await file.read()

    document = PdfDocument(
        title=title,
        category_id=category_id,
        language=language,
        pdf_data=pdf_data
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Resolve category name for metadata (needed for search result display)
    category_name = document.category.name if document.category else None

    extraction_result = None
    if extract_text:
        lang_map = {"en": "eng", "sv": "swe+eng", "de": "deu+eng"}
        ocr_lang = lang_map.get(language, "eng")

        extraction = extract_pdf_document(pdf_data, lang=ocr_lang)

        lc_docs = []
        for page in extraction.pages:
            sub_chunks = split_page_text(page.text)
            for idx, chunk_text in enumerate(sub_chunks):
                lc_docs.append(
                    Document(
                        page_content=chunk_text,
                        metadata={
                            "document_id": document.document_id,
                            "document_title": document.title,
                            "page_number": page.page_num,
                            "chunk_index": idx,
                            "category_id": document.category_id,
                            "category_name": category_name,
                            "language": document.language,
                            "upload_date": document.upload_date.isoformat(),
                        },
                    )
                )

        chunks_created = len(lc_docs)
        embeddings_created = 0

        if lc_docs:
            vs = get_vector_store()
            vs.add_documents(lc_docs)
            embeddings_created = chunks_created

        extraction_result = {
            "total_pages": extraction.total_pages,
            "ocr_pages": extraction.ocr_pages_count,
            "total_chars": len(extraction.full_text),
            "chunks_created": chunks_created,
            "embeddings_created": embeddings_created,
        }

    return {
        "document_id": document.document_id,
        "title": document.title,
        "language": document.language,
        "upload_date": document.upload_date,
        "size_bytes": len(pdf_data),
        "extraction": extraction_result,
    }


@app.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(PdfDocument).filter(
        PdfDocument.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    # Remove vectors from langchain_pg_embedding
    delete_document_vectors(document_id)

    return {"deleted": True, "document_id": document_id}


@app.get("/documents/{document_id}/pdf")
def get_document_pdf(
    document_id: int,
    download: bool = False,
    db: Session = Depends(get_db)
):
    document = db.query(PdfDocument).filter(
        PdfDocument.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    headers = {}
    if download:
        safe_title = document.title.replace('"', '\\"')
        headers["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'

    return Response(
        content=document.pdf_data,
        media_type="application/pdf",
        headers=headers
    )


@app.get("/documents/{document_id}/chunks")
def get_document_chunks(document_id: int, db: Session = Depends(get_db)):
    chunks = get_chunks_for_document(document_id)
    return [{
        "chunk_id": i,
        "page_number": c["page_number"],
        "chunk_index": c["chunk_index"],
        "chunk_text": c["chunk_text"],
        "has_embedding": True,  # All stored chunks have embeddings in PGVector
    } for i, c in enumerate(chunks)]


@app.get("/documents/{document_id}/text")
def get_document_text(document_id: int, db: Session = Depends(get_db)):
    document = db.query(PdfDocument).filter(
        PdfDocument.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = get_chunks_for_document(document_id)
    full_text = "\n\n".join(c["chunk_text"] for c in chunks if c["chunk_text"])

    return {
        "document_id": document_id,
        "title": document.title,
        "total_chunks": len(chunks),
        "total_chars": len(full_text),
        "full_text": full_text,
    }


# =============================================================================
# Search Endpoints
# =============================================================================

def format_search_response(response: SearchResponse) -> dict:
    """Format SearchResponse to JSON-compatible format."""
    return {
        "query": response.query,
        "search_type": response.search_type,
        "total_count": response.total_count,
        "results": [{
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "document_title": r.document_title,
            "page_number": r.page_number,
            "chunk_index": r.chunk_index,
            "chunk_text": r.chunk_text,
            "category_id": r.category_id,
            "category_name": r.category_name,
            "language": r.language,
            "upload_date": r.upload_date.isoformat() if r.upload_date else None,
            "score": round(r.score, 4),
            "vector_rank": r.vector_rank,
            "keyword_rank": r.keyword_rank,
            "rerank_score": round(r.rerank_score, 4) if r.rerank_score is not None else None,
        } for r in response.results]
    }


@app.post("/search")
def search(query: SearchQuery, db: Session = Depends(get_db)):
    """
    Hybrid search: combines semantic vector search with keyword search.

    Uses Reciprocal Rank Fusion (RRF) for best results.
    With rerank=true, Cross-Encoder is used to re-rank the results.
    """
    if query.rerank:
        response = hybrid_search_with_reranking(
            db=db,
            query=query.query,
            k=query.k,
            rerank_candidates=query.rerank_candidates,
            category_id=query.category_id,
            date_from=query.date_from,
            date_to=query.date_to,
            semantic_weight=query.semantic_weight,
            keyword_weight=query.keyword_weight,
        )
    else:
        response = hybrid_search(
            db=db,
            query=query.query,
            k=query.k,
            category_id=query.category_id,
            date_from=query.date_from,
            date_to=query.date_to,
            semantic_weight=query.semantic_weight,
            keyword_weight=query.keyword_weight,
        )
    return format_search_response(response)


@app.post("/search/semantic")
def search_semantic(query: SearchQuery, db: Session = Depends(get_db)):
    """
    Semantic search only with vector similarity.

    Best for conceptual queries and fuzzy matching.
    """
    response = semantic_only_search(
        db=db,
        query=query.query,
        k=query.k,
        category_id=query.category_id,
        date_from=query.date_from,
        date_to=query.date_to,
    )
    return format_search_response(response)


@app.post("/search/keyword")
def search_keyword(query: SearchQuery, db: Session = Depends(get_db)):
    """
    Keyword search only with PostgreSQL fulltext.

    Best for exact terms and specific phrases.
    """
    response = keyword_only_search(
        db=db,
        query=query.query,
        k=query.k,
        category_id=query.category_id,
        date_from=query.date_from,
        date_to=query.date_to,
    )
    return format_search_response(response)


# =============================================================================
# RAG - Ask (Question Answering)
# =============================================================================

@app.post("/ask")
async def ask_question(query: AskQuery, db: Session = Depends(get_db)):
    """
    Ask a question and get an AI-generated answer based on the documents.

    Full RAG pipeline:
    1. Searches for relevant chunks using hybrid search
    2. Uses Cross-Encoder reranking for better precision
    3. Generates answer with local LLM (Ollama via LangChain ChatOllama)

    Requires Ollama to run locally with the specified model.
    """
    if query.rerank:
        search_response = hybrid_search_with_reranking(
            db=db,
            query=query.question,
            k=query.k,
            rerank_candidates=query.k * 5,
            category_id=query.category_id,
        )
    else:
        search_response = hybrid_search(
            db=db,
            query=query.question,
            k=query.k,
            category_id=query.category_id,
        )

    if not search_response.results:
        return {
            "question": query.question,
            "answer": "I found no relevant documents to answer your question.",
            "sources": [],
            "model": query.model,
        }

    context_chunks = [r.chunk_text for r in search_response.results]

    try:
        answer = await generate_answer(
            query=query.question,
            context_chunks=context_chunks,
            model=query.model,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gemini API call failed. Check that GOOGLE_API_KEY is set in backend/.env. Error: {str(e)}"
        )

    sources = [{
        "document_id": r.document_id,
        "document_title": r.document_title,
        "page_number": r.page_number,
        "chunk_text": r.chunk_text[:200] + "..." if len(r.chunk_text) > 200 else r.chunk_text,
        "score": round(r.score, 4),
    } for r in search_response.results]

    return {
        "question": query.question,
        "answer": answer,
        "sources": sources,
        "model": query.model,
        "chunks_used": len(context_chunks),
    }


# =============================================================================
# Statistics
# =============================================================================

@app.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics."""
    doc_count = db.query(PdfDocument).count()
    category_count = db.query(Category).count()
    chunk_count = count_all_chunks()

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "embeddings": chunk_count,  # Every chunk has an embedding in PGVector
        "categories": category_count,
        "indexed_percentage": 100.0 if chunk_count > 0 else 0,
    }

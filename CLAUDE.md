# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A PDF RAG (Retrieval-Augmented Generation) system. Users upload PDFs, which are chunked and embedded. Questions are answered by retrieving relevant chunks via hybrid search and generating a response using Google Gemini.

## Running the System

**Prerequisites:** Docker Desktop running, Python 3.12+

### Start infrastructure
```bash
docker start postgres-pgvector
```

### Backend
```bash
cd backend
.\venv\Scripts\Activate.ps1        # Windows PowerShell
uvicorn app.main:app --reload      # http://localhost:8000
```

### Frontend
```bash
cd frontend
.\venv\Scripts\Activate.ps1
streamlit run app.py               # http://localhost:8501
```

### Install dependencies (first time)
```bash
# Backend
cd backend && python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd frontend && python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Variables

`backend/.env` requires:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
GOOGLE_API_KEY=<your-key>          # Required for embeddings and LLM
```

> **Note:** The README mentions Ollama/llama3.2 but the actual implementation uses Google Gemini API for both embeddings (`gemini-embedding-001`) and LLM (`gemini-2.0-flash`).

## Architecture

```
frontend/app.py  (Streamlit)
      |  HTTP
backend/app/main.py  (FastAPI)
      |
      +-- pdf_extraction.py     PyMuPDF + Tesseract OCR
      +-- rag/chunking.py       LangChain RecursiveCharacterTextSplitter (500 chars, 100 overlap)
      +-- rag/embeddings.py     Google Gemini embeddings + HuggingFace CrossEncoder reranker
      +-- rag/search.py         Hybrid search (EnsembleRetriever: PGVector + PostgreSQL FTS)
      +-- rag/llm.py            Google Gemini LLM via LangChain ChatGoogleGenerativeAI
      +-- rag/chains.py         LCEL RAG chain (create_rag_chain helper, not used by /ask directly)
      |
      +-- database.py           SQLAlchemy (psycopg2)
      +-- models.py             ORM: Category, PdfDocument, DocumentMetadata
```

### Dual database connection pattern

The codebase maintains two separate database connections:
- **psycopg2** (`postgresql://...`) — used by SQLAlchemy for the app's own tables (`categories`, `pdf_documents`, `document_metadata`)
- **psycopg3** (`postgresql+psycopg://...`) — required by `langchain-postgres` PGVector for the vector store (`langchain_pg_collection`, `langchain_pg_embedding`)

`search.py` converts the URL format automatically via `_get_pgvector_url()`.

### Search pipeline

1. **Semantic:** PGVector cosine similarity via `langchain_postgres.PGVector`
2. **Keyword:** Custom `KeywordRetriever` using PostgreSQL `tsvector`/`plainto_tsquery`
3. **Fusion:** `EnsembleRetriever` with weighted RRF (semantic 0.7, keyword 0.3)
4. **Reranking (optional):** `ContextualCompressionRetriever` + `CrossEncoderReranker` (`ms-marco-MiniLM-L-6-v2`)

### PDF processing

`pdf_extraction.py` auto-detects whether each page needs OCR: pages with fewer than 40 chars of extractable text and images are OCR'd with Tesseract. Tables are extracted as Markdown via `pdfplumber` when financial keywords are detected.

## Database Schema

**App tables** (SQLAlchemy-managed):
- `categories` — `category_id`, `name`
- `pdf_documents` — `document_id`, `title`, `category_id`, `language`, `upload_date`, `pdf_data` (raw PDF bytes stored in DB)
- `document_metadata` — key-value pairs per document

**LangChain tables** (auto-created by PGVector on startup):
- `langchain_pg_collection` — named collections
- `langchain_pg_embedding` — vectors + `cmetadata` JSONB (stores `document_id`, `document_title`, `page_number`, `chunk_index`, `category_id`, `language`, `upload_date`)

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ask` | RAG question answering |
| `POST` | `/search` | Hybrid search (supports `rerank`, `semantic_weight`, `keyword_weight`) |
| `POST` | `/search/semantic` | Vector-only search |
| `POST` | `/search/keyword` | FTS-only search |
| `POST` | `/documents/upload` | Upload PDF (multipart) |
| `GET` | `/documents/{id}/chunks` | List stored chunks for a document |
| `GET` | `/info` | System info including LLM/embedding model status |
| `GET` | `/stats` | Document and chunk counts |

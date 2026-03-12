# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A PDF RAG (Retrieval-Augmented Generation) system. Users upload PDFs, which are chunked and embedded into a pgvector database. Questions are answered using hybrid search (semantic + keyword) with optional Cross-Encoder reranking, followed by Google Gemini LLM generation.

## Running the Project

**Prerequisites:** Docker Desktop running, Python 3.12+, Node.js 18+, `GOOGLE_API_KEY` set in `backend/.env`.

```powershell
# 1. Start PostgreSQL
docker start postgres-pgvector

# 2. Start backend (from backend/ with venv active)
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# 3. Start React frontend (from frontend-react/)
npm run dev
# → http://localhost:5173
```

**Streamlit alternative** (from `frontend/` with its own venv):
```powershell
streamlit run app.py
# → http://localhost:8501
```

## First-Time Setup

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# React frontend
cd frontend-react
npm install
```

**`backend/.env`:**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
GOOGLE_API_KEY=your_google_api_key_here
```

## Architecture

```
frontend-react (React 19 + Vite) :5173
    └── src/api/client.js → BASE_URL = http://localhost:8000
frontend (Streamlit) :8501
    └── calls backend directly

backend (FastAPI + LangChain) :8000
    ├── app/main.py           — all FastAPI routes
    ├── app/models.py         — SQLAlchemy ORM: Category, PdfDocument, DocumentMetadata
    ├── app/database.py       — SQLAlchemy engine, get_db(), init_pgvector()
    ├── app/pdf_extraction.py — PyMuPDF + Tesseract OCR
    └── app/rag/
        ├── chunking.py       — RecursiveCharacterTextSplitter (500 chars, 100 overlap)
        ├── embeddings.py     — Google Gemini embeddings (gemini-embedding-001) + Cross-Encoder (ms-marco-MiniLM-L-6-v2)
        ├── llm.py            — ChatGoogleGenerativeAI (gemini-2.0-flash)
        └── search.py         — EnsembleRetriever (semantic 0.7 + keyword FTS 0.3), RRF, CrossEncoderReranker

PostgreSQL + pgvector (Docker, port 5433)
    ├── categories, pdf_documents, document_metadata  — SQLAlchemy-managed
    └── langchain_pg_collection, langchain_pg_embedding — LangChain PGVector-managed
```

## Key Design Decisions

- **Two database connections in `search.py`**: `_search_engine` uses `psycopg2` (for direct SQL / keyword FTS), while `_vector_store` uses `psycopg3` (`psycopg`) because `langchain-postgres` requires it. Both connect to the same DB.
- **Vector store collection name** is `"pdf_chunks"` (constant `COLLECTION_NAME` in `search.py`).
- **PDF binary is stored** in `pdf_documents.pdf_data` (LargeBinary); chunks/embeddings live separately in `langchain_pg_embedding`.
- **Metadata stored with every chunk**: `document_id`, `document_title`, `page_number`, `chunk_index`, `category_id`, `category_name`, `language`, `upload_date`. This enables filtering and display without joining back to the main tables.
- **Models are loaded lazily and cached** as module-level singletons (embedding model, cross-encoder, vector store). First query after startup will be slow.
- **`langchain-classic`** (not `langchain`) is used for `EnsembleRetriever`, `ContextualCompressionRetriever`, and `CrossEncoderReranker`.

## API Overview

Backend base: `http://localhost:8000`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ask` | Full RAG pipeline: hybrid search + Gemini answer |
| POST | `/search` | Hybrid search (semantic + keyword, optional rerank) |
| POST | `/search/semantic` | Vector similarity only |
| POST | `/search/keyword` | PostgreSQL FTS only |
| POST | `/documents/upload` | Upload PDF (triggers extraction + embedding) |
| GET/PATCH/DELETE | `/documents/{id}` | Document CRUD |
| GET/POST/DELETE | `/categories` | Category management |
| GET | `/health`, `/info`, `/stats` | System status |

## React Frontend Structure

```
src/
├── api/          — fetch wrappers (ask.js, search.js, documents.js, info.js)
├── components/   — shared UI (Layout, Button, Card, Alert)
└── pages/        — AskPage, SearchPage, UploadPage, LibraryPage, InfoPage
```

Routes: `/ask` (default), `/search`, `/upload`, `/library`, `/info`

## Troubleshooting

- **PowerShell execution policy**: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **DB connection refused**: `docker start postgres-pgvector`
- **503 from `/ask`**: `GOOGLE_API_KEY` missing in `backend/.env`

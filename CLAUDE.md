# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A PDF RAG (Retrieval-Augmented Generation) system. Users upload PDFs, which are chunked and embedded into a pgvector database. Documents are browsed and managed from an interactive Dashboard. Questions are answered using semantic search (cosine similarity via PGVector), followed by Google Gemini LLM generation.

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
        ├── embeddings.py     — Google Gemini embeddings (gemini-embedding-001)
        ├── llm.py            — ChatGoogleGenerativeAI (gemini-2.0-flash)
        └── search.py         — PGVector cosine similarity, supports document_id + category_id filter

PostgreSQL + pgvector (Docker, port 5433)
    ├── categories, pdf_documents, document_metadata  — SQLAlchemy-managed
    └── langchain_pg_collection, langchain_pg_embedding — LangChain PGVector-managed
```

## Key Design Decisions

- **Semantic search only**: Keyword FTS and Cross-Encoder reranking were evaluated (MRR, P@k, R@k, NDCG@k) and removed — both hurt retrieval quality compared to pure cosine similarity on Gemini embeddings.
- **Chunk size 500 / overlap 100**: Evaluated against 1200/200 — larger chunks hurt precision for these PDF types.
- **Two database connections in `search.py`**: `_search_engine` uses `psycopg2` (for direct SQL: delete, count, chunk listing), while `_vector_store` uses `psycopg3` (`psycopg`) because `langchain-postgres` requires it. Both connect to the same DB.
- **Vector store collection name** is `"pdf_chunks"` (constant `COLLECTION_NAME` in `search.py`).
- **PDF binary is stored** in `pdf_documents.pdf_data` (LargeBinary); chunks/embeddings live separately in `langchain_pg_embedding`.
- **Metadata stored with every chunk**: `document_id`, `document_title`, `page_number`, `chunk_index`, `category_id`, `category_name`, `language`, `upload_date`. This enables filtering and display without joining back to the main tables.
- **`document_id` filter**: `/ask` accepts an optional `document_id` to restrict retrieval to a single document. Used by DocumentPage for document-specific chat. When both `document_id` and `category_id` are provided, `document_id` takes precedence.
- **Category colors**: `categoryGradient(categoryId)` in `CategoryModal.jsx` maps `categoryId % 8` to one of 8 gradient pairs. Used as document thumbnail backgrounds on the Dashboard.
- **Null category PATCH**: `update.model_fields_set` is checked (not `is not None`) so that explicitly sending `category_id: null` removes the category rather than being silently ignored.
- **FK constraint on category delete**: Before deleting a category, all documents in that category have their `category_id` set to `null` to avoid a PostgreSQL FK constraint error.
- **Models are loaded lazily and cached** as module-level singletons (embedding model, vector store). First query after startup will be slow.

## API Overview

Backend base: `http://localhost:8000`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ask` | Full RAG pipeline: semantic search + Gemini answer. Accepts optional `document_id` to scope to one document. |
| POST | `/search` | Semantic search |
| POST | `/search/semantic` | Semantic search (same as `/search`) |
| POST | `/documents/upload` | Upload PDF (triggers extraction + embedding) |
| GET | `/documents` | List all documents (supports `?category_id=` filter) |
| GET | `/documents/{id}` | Get document metadata + chunk count |
| PATCH | `/documents/{id}` | Update title, category, or language |
| PATCH | `/documents/bulk/category` | Bulk-assign category to multiple documents |
| DELETE | `/documents/{id}` | Delete document + its vectors |
| GET | `/documents/{id}/pdf` | Serve raw PDF binary |
| GET | `/documents/{id}/chunks` | List all chunks for a document |
| GET | `/documents/{id}/text` | Full reconstructed text from chunks |
| GET/POST/DELETE | `/categories` | Category management |
| GET | `/health`, `/info`, `/stats` | System status |

## React Frontend Structure

```
src/
├── api/
│   ├── ask.js        — askQuestion({ question, k, document_id })
│   ├── search.js     — searchSemantic(query, { k, category_id })
│   ├── documents.js  — getDocuments, getDocument, uploadDocument,
│   │                   updateDocument, deleteDocument,
│   │                   getCategories, createCategory, deleteCategory
│   └── info.js       — getInfo
├── components/
│   ├── Layout.jsx        — sidebar nav (Documents, System)
│   ├── UploadModal.jsx   — drag-and-drop upload modal with category + language selects
│   └── CategoryModal.jsx — manage categories (create/delete); exports categoryGradient()
└── pages/
    ├── DashboardPage.jsx — interactive document grid (default route /)
    ├── DocumentPage.jsx  — split PDF viewer + chat for a single document
    └── InfoPage.jsx      — system info (/info)
```

**Routes**: `/` (Dashboard, default), `/library/:id` (DocumentPage), `/info`

### DashboardPage (`/`)
Interactive document grid with:
- **Search bar**: live title filter + semantic search on Enter / Search button
- **Semantic banner**: shown when semantic results are active, with result count and clear button
- **Filters**: category dropdown + date range (all / last month / last week)
- **Document cards**: colored thumbnail (by category), title, category picker, upload date, delete button
- **Upload button**: opens `UploadModal`
- **Settings icon**: opens `CategoryModal` for category management
- **CategoryPicker**: per-card inline category assignment. Uses React `createPortal` + `useLayoutEffect` to position the dropdown correctly within the viewport regardless of card position.

### DocumentPage (`/library/:id`)
Full-bleed split layout (`position: fixed`, left offset by sidebar width):
- Left pane: PDF iframe from `/documents/:id/pdf`
- Right pane: Chat interface scoped to the selected document via `document_id`
- Back button navigates to `/`

## Troubleshooting

- **PowerShell execution policy**: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **DB connection refused**: `docker start postgres-pgvector`
- **503 from `/ask`**: `GOOGLE_API_KEY` missing in `backend/.env`
- **Eval timeouts**: The embedding model loads lazily on first request. Increase timeout to ≥120s in eval scripts.
- **Eval returning all zeros**: Check that document IDs in `GROUND_TRUTH` match the actual IDs in the database — they change on re-upload.

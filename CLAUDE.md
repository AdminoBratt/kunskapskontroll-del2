# CLAUDE.md

## Project Overview

A PDF RAG (Retrieval-Augmented Generation) system built with LangChain. Users upload PDFs and ask questions; the system retrieves relevant chunks and generates AI answers using the Google Gemini API. Embeddings and reranking run fully locally; only LLM inference calls leave the machine.

## Architecture

```
Streamlit UI (port 8501)
    └── FastAPI backend (port 8000)
            ├── PostgreSQL + pgvector (port 5433, via Docker)
            │     └── langchain_pg_collection / langchain_pg_embedding (managed by LangChain PGVector)
            ├── Google Gemini API (gemini-2.0-flash, requires GOOGLE_API_KEY)
            └── sentence-transformers (local embeddings, 768-dim)
```

## Project Structure

```
kunskapskontroll-del2/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI routes & endpoints
│   │   ├── models.py          # SQLAlchemy ORM models (Category, PdfDocument, DocumentMetadata)
│   │   ├── database.py        # PostgreSQL connection
│   │   ├── pdf_extraction.py  # PyMuPDF + Tesseract OCR
│   │   └── rag/
│   │       ├── chains.py      # LCEL RAG chain (create_retrieval_chain)
│   │       ├── chunking.py    # RecursiveCharacterTextSplitter
│   │       ├── embeddings.py  # HuggingFaceEmbeddings + CrossEncoder reranking
│   │       ├── llm.py         # ChatGoogleGenerativeAI (Gemini)
│   │       └── search.py      # PGVector + EnsembleRetriever + ContextualCompressionRetriever
│   ├── requirements.txt
│   └── .env                   # DATABASE_URL + GOOGLE_API_KEY (not committed)
├── frontend/
│   ├── app.py                 # Streamlit UI
│   └── requirements.txt
├── setup.ps1                  # Windows first-time setup
└── README.md
```

## Running the Project

All commands use PowerShell and project-local virtual environments.

```powershell
# 1. Start PostgreSQL (Docker must be running)
docker start postgres-pgvector

# 2. Backend (Terminal 1)
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# 3. Frontend (Terminal 2)
cd frontend
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Visit `http://localhost:8501` in the browser.

## Environment Variables

```
# backend/.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
GOOGLE_API_KEY=your-gemini-api-key-here
```

Get a Gemini API key at https://aistudio.google.com/app/apikey

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | RAG question answering |
| `POST` | `/search` | Hybrid semantic + keyword search |
| `POST` | `/search/semantic` | Semantic-only search |
| `POST` | `/search/keyword` | Keyword-only search |
| `POST` | `/documents/upload` | Upload PDF |
| `GET` | `/documents` | List documents |
| `DELETE` | `/documents/{id}` | Delete document |
| `GET` | `/health` | Health check |
| `GET` | `/info` | System info |
| `GET` | `/stats` | Document statistics |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.115.6, Python 3.12, uvicorn |
| Database | PostgreSQL + pgvector (SQLAlchemy 2.0, psycopg2) |
| Vector store | langchain-postgres PGVector (psycopg3) |
| Embeddings | HuggingFaceEmbeddings / sentence-transformers 3.2.1 (768-dim) |
| Reranking | CrossEncoderReranker (cross-encoder/ms-marco-MiniLM-L-6-v2) |
| LLM | Google Gemini API (gemini-2.0-flash) via langchain-google-genai |
| RAG framework | LangChain 0.3 (LCEL, EnsembleRetriever, ContextualCompressionRetriever) |
| Frontend | Streamlit 1.41.1 |
| PDF | PyMuPDF + pytesseract + pdfplumber |

## Database Models (SQLAlchemy ORM)

- `Category` — document categories
- `PdfDocument` — uploaded PDF metadata and binary data
- `DocumentMetadata` — key/value metadata per document

Chunk storage is handled entirely by LangChain's PGVector in two auto-managed tables:
- `langchain_pg_collection` — collection registry (`pdf_chunks`)
- `langchain_pg_embedding` — chunk text + 768-dim vectors + JSONB metadata

## RAG Pipeline

1. User question → embed with `HuggingFaceEmbeddings` (local)
2. Hybrid search via `EnsembleRetriever`:
   - Semantic leg: `PGVector.as_retriever()` (cosine similarity)
   - Keyword leg: custom `KeywordRetriever` (PostgreSQL `tsvector` FTS on `langchain_pg_embedding.document`)
   - Merged with weighted Reciprocal Rank Fusion (semantic 0.7, keyword 0.3)
3. Optional cross-encoder reranking via `ContextualCompressionRetriever` + `CrossEncoderReranker`
4. Top-k chunks + question → `ChatGoogleGenerativeAI` (Gemini)
5. Gemini generates a grounded answer with source citations

## Development Notes

- **LangChain 0.3** — RAG pipeline uses LCEL; no custom SQL search code
- **No tests** — testing is done manually via the Streamlit UI or health/info endpoints
- Separate `venv/` in both `backend/` and `frontend/` — always activate the correct one
- PGVector tables are created automatically on first backend startup
- Embeddings load on first request (~a few seconds); subsequent requests are fast
- The `.env` file is gitignored; do not commit credentials
- `chunk_id` in search results is always `0` — LangChain uses UUIDs internally, not sequential ints

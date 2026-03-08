# PDF RAG System

A RAG (Retrieval-Augmented Generation) system for PDF documents. Ask questions and get AI-generated answers based on your documents.

## Features

- **RAG Pipeline**: Ask questions, get AI answers with source citations
- **Hybrid Search**: Semantic vector search + keyword full-text search
- **Cross-Encoder Reranking**: Improved precision for search results
- **PDF Processing**: Automatic text extraction with OCR support
- **Google Gemini LLM**: Cloud LLM via Google Gemini API (gemini-2.0-flash)
- **LangChain**: LCEL chains for RAG pipeline and retrieval
- **Streamlit UI**: Simple web interface for asking questions
- **React Frontend**: Full-featured UI with React 19 + Vite (Ask, Search, Upload, Library, Info pages)
- **Categories**: Organize documents into categories

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          WINDOWS PC                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │    DOCKER    │  │   GOOGLE GEMINI  │  │        BROWSER         │ │
│  │              │  │       API        │  │                        │ │
│  │  PostgreSQL  │  │  gemini-2.0-flash│  │  React UI  :5173       │ │
│  │  + pgvector  │  │  (cloud LLM)     │  │  Streamlit :8501       │ │
│  │  port 5433   │  │                  │  │                        │ │
│  └──────▲───────┘  └──────▲───────────┘  └───────────▲────────────┘ │
│         │                 │                          │              │
│         └────────┬────────┴──────────────────────────┘              │
│                  │                                                  │
│  ┌───────────────▼─────────────────────────────────────────────┐    │
│  │                      PYTHON / NODE                          │    │
│  │                                                             │    │
│  │   Backend:  http://localhost:8000                           │    │
│  │   └── FastAPI + LangChain + sentence-transformers           │    │
│  │       + Cross-Encoder + langchain-postgres (pgvector)       │    │
│  │                                                             │    │
│  │   Frontend (React): http://localhost:5173                   │    │
│  │   └── React 19 + Vite + react-router-dom                    │    │
│  │                                                             │    │
│  │   Frontend (Streamlit): http://localhost:8501               │    │
│  │   └── Streamlit                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Windows 10/11
- Python 3.12+ (https://python.org)
- Node.js 18+ (https://nodejs.org) — for React frontend
- Docker Desktop
- Google API key (https://aistudio.google.com/app/apikey)

## Quick Start

### 1. Start Docker
```powershell
docker start postgres-pgvector
```

### 2. Start Backend (PowerShell)
```powershell
cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### 3. Start React Frontend (new PowerShell window)
```powershell
cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\frontend-react"
npm run dev
```

### 4. Open Browser
```
http://localhost:5173
```

Upload a PDF and ask questions!

> **Alternative:** The Streamlit frontend is also available:
> ```powershell
> cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\frontend"
> .\venv\Scripts\Activate.ps1
> streamlit run app.py
> # Open http://localhost:8501
> ```

## First-Time Setup

### Install dependencies

**Backend:**
```powershell
cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**React Frontend:**
```powershell
cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\frontend-react"
npm install
```

**Streamlit Frontend:**
```powershell
cd "C:\Users\sigge bratt\Desktop\Examen\kunskapskontroll-del2\frontend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API Endpoints

### RAG (Question Answering)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | Ask a question - returns AI answer + sources |

```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "What does the document say about...?"}'
```

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/documents` | List all documents (filter by `?category_id=`) |
| `GET` | `/documents/{id}` | Get document metadata + chunk count |
| `POST` | `/documents/upload` | Upload PDF |
| `PATCH` | `/documents/{id}` | Update title, category, or language |
| `PATCH` | `/documents/bulk/category` | Bulk update category for multiple documents |
| `DELETE` | `/documents/{id}` | Delete document |
| `GET` | `/documents/{id}/pdf` | Download PDF (`?download=true` for attachment) |
| `GET` | `/documents/{id}/chunks` | List all chunks for a document |
| `GET` | `/documents/{id}/text` | Get full extracted text |

### Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/categories` | List all categories |
| `POST` | `/categories` | Create category |
| `DELETE` | `/categories/{id}` | Delete category |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Hybrid search (semantic + keyword, optional reranking) |
| `POST` | `/search/semantic` | Semantic vector search only |
| `POST` | `/search/keyword` | PostgreSQL fulltext keyword search only |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/info` | System info |
| `GET` | `/stats` | Document statistics |

## Project Structure

```
kunskapskontroll-del2\
├── backend\
│   ├── app\
│   │   ├── main.py              # FastAPI routes
│   │   ├── models.py            # Database models (PdfDocument, Category)
│   │   ├── database.py          # PostgreSQL connection
│   │   ├── pdf_extraction.py    # PDF text extraction
│   │   └── rag\
│   │       ├── search.py        # Hybrid search, RRF, reranking
│   │       ├── embeddings.py    # Sentence-transformers
│   │       ├── chunking.py      # Text chunking
│   │       ├── llm.py           # Google Gemini API integration
│   │       └── chains.py        # LangChain LCEL RAG chain
│   ├── venv\
│   ├── requirements.txt
│   └── .env
├── frontend\
│   ├── app.py                   # Streamlit UI
│   ├── venv\
│   └── requirements.txt
├── frontend-react\
│   ├── src\
│   │   ├── App.jsx              # Router + layout
│   │   ├── api\                 # API client modules (ask, search, documents, info)
│   │   ├── components\          # Shared UI components (Button, Card, Alert, Layout)
│   │   └── pages\               # Ask, Search, Upload, Library, Info pages
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL + pgvector |
| Embeddings | sentence-transformers (local) |
| Reranking | Cross-Encoder (local) |
| LLM | Google Gemini API (gemini-2.0-flash) |
| RAG Framework | LangChain (LCEL, langchain-postgres) |
| Frontend (React) | React 19 + Vite + react-router-dom |
| Frontend (Streamlit) | Streamlit |
| PDF Extraction | PyMuPDF + Tesseract OCR |

## How RAG Works

```
1. You ask a question
2. System searches for relevant chunks (hybrid search)
3. Cross-Encoder reranks for better precision
4. Top chunks + question sent to Google Gemini API
5. Gemini generates answer based only on your documents
6. Answer returned with source citations
```

## Environment Variables

```
# backend\.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
GOOGLE_API_KEY=your_google_api_key_here
```

Get a Google API key at: https://aistudio.google.com/app/apikey

## Troubleshooting

### PowerShell script execution disabled
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Gemini API not available
- Check that `GOOGLE_API_KEY` is set in `backend\.env`
- Get a key at https://aistudio.google.com/app/apikey

### Database connection refused
```powershell
docker start postgres-pgvector
```

### Slow first query
First query loads embedding and reranking models (~1GB). Subsequent queries are faster.

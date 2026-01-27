# PDF RAG System

A fully local RAG (Retrieval-Augmented Generation) system for PDF documents. Ask questions and get AI-generated answers based on your documents.



## Features

- **RAG Pipeline**: Ask questions, get AI answers with source citations
- **Hybrid Search**: Semantic vector search + keyword full-text search
- **Cross-Encoder Reranking**: Improved precision for search results
- **PDF Processing**: Automatic text extraction with OCR support
- **Local LLM**: Ollama integration (llama3.2 or any model)
- **Streamlit UI**: Simple web interface for asking questions
- **LangChain-free**: No framework dependencies, clean implementation

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          WINDOWS PC                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │    DOCKER    │  │    OLLAMA    │  │         BROWSER           │  │
│  │              │  │              │  │                           │  │
│  │  PostgreSQL  │  │  llama3.2    │  │  Streamlit UI             │  │
│  │  + pgvector  │  │  (local LLM) │  │  http://localhost:8501    │  │
│  │  port 5433   │  │  port 11434  │  │                           │  │
│  └──────▲───────┘  └──────▲───────┘  └─────────────▲─────────────┘  │
│         │                 │                        │                │
│         └────────┬────────┴────────────────────────┘                │
│                  │                                                  │
│  ┌───────────────▼─────────────────────────────────────────────┐    │
│  │                      PYTHON                                 │    │
│  │                                                             │    │
│  │   Backend: http://localhost:8000                            │    │
│  │   └── FastAPI + sentence-transformers + Cross-Encoder      │    │
│  │                                                             │    │
│  │   Frontend: http://localhost:8501                           │    │
│  │   └── Streamlit                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Windows 10/11
- Python 3.12+ (https://python.org)
- Docker Desktop
- Ollama (https://ollama.com)

## Quick Start

### 1. Start Docker
```powershell
docker start postgres-pgvector
```

### 2. Ollama (runs automatically after installation)
First time only:
```powershell
ollama pull llama3.2
```

### 3. Start Backend (PowerShell)
```powershell
cd "C:\Users\sigge bratt\RAG\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### 4. Start Frontend (new PowerShell window)
```powershell
cd "C:\Users\sigge bratt\RAG\frontend"
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

### 5. Open Browser
```
http://localhost:8501
```

Upload a PDF and ask questions!

## First-Time Setup

### Install dependencies

**Backend:**
```powershell
cd "C:\Users\sigge bratt\RAG\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Frontend:**
```powershell
cd "C:\Users\sigge bratt\RAG\frontend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API Endpoints

### RAG (Question Answering)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | **Ask a question** - returns AI answer + sources |

```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "What does the document say about...?"}'
```

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/documents` | List all documents |
| `POST` | `/documents/upload` | Upload PDF |
| `DELETE` | `/documents/{id}` | Delete document |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Hybrid search (semantic + keyword) |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/info` | System info |
| `GET` | `/stats` | Document statistics |

## Project Structure

```
C:\Users\sigge bratt\RAG\
├── backend\
│   ├── app\
│   │   ├── main.py              # FastAPI routes
│   │   ├── models.py            # Database models
│   │   ├── database.py          # PostgreSQL connection
│   │   ├── pdf_extraction.py    # PDF text extraction
│   │   └── rag\
│   │       ├── search.py        # Hybrid search, RRF, reranking
│   │       ├── embeddings.py    # Sentence-transformers
│   │       ├── chunking.py      # Text chunking
│   │       └── llm.py           # Ollama integration
│   ├── venv\                    # Python virtual environment
│   ├── requirements.txt
│   └── .env
├── frontend\
│   ├── app.py                   # Streamlit UI
│   ├── venv\
│   └── requirements.txt
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL + pgvector |
| Embeddings | sentence-transformers (768 dim) |
| Reranking | Cross-Encoder |
| LLM | Ollama (llama3.2) |
| Frontend | Streamlit |
| PDF Extraction | PyMuPDF + Tesseract OCR |

## How RAG Works

```
1. You ask a question
2. System searches for relevant chunks (hybrid search)
3. Cross-Encoder reranks for better precision
4. Top chunks + question sent to local LLM
5. LLM generates answer based only on your documents
6. Answer returned with source citations
```

## Environment Variables

```
# backend\.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres
```

## Troubleshooting

### PowerShell script execution disabled
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Ollama not found
Install from https://ollama.com/download/windows

### Database connection refused
```powershell
docker start postgres-pgvector
```

### Slow first query
First query downloads/loads embedding models (~1GB). Subsequent queries are faster.

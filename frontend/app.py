"""
PDF RAG - Ask your documents
"""

import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="PDF RAG",
    layout="centered",
)

st.title("PDF RAG")


@st.cache_data(ttl=30)
def get_stats():
    """Fetch statistics from the API."""
    try:
        response = httpx.get(f"{API_URL}/stats", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


@st.cache_data(ttl=60)
def check_ollama():
    """Check if Ollama is available."""
    try:
        response = httpx.get(f"{API_URL}/info", timeout=5.0)
        response.raise_for_status()
        info = response.json()
        return info.get("llm", {}).get("status", {})
    except Exception:
        return {"available": False, "error": "Could not connect to API"}


def ask_question(question: str, model: str = "llama3.2") -> dict:
    """Send question to the RAG API."""
    response = httpx.post(
        f"{API_URL}/ask",
        json={"question": question, "model": model, "k": 5, "rerank": True},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def upload_document(file, title: str) -> dict:
    """Upload document to the API."""
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    data = {"title": title}
    response = httpx.post(
        f"{API_URL}/documents/upload",
        files=files,
        data=data,
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


# Sidebar with status
with st.sidebar:
    st.header("Status")
    
    stats = get_stats()
    if stats:
        st.metric("Documents", stats.get("documents", 0))
        st.metric("Chunks", stats.get("chunks", 0))
    else:
        st.error("API not available")
        st.caption("Start backend: `uvicorn app.main:app`")
        st.stop()
    
    st.divider()
    
    ollama_status = check_ollama()
    if ollama_status.get("available"):
        st.success("Ollama running")
        models = ollama_status.get("models", [])
        if models:
            selected_model = st.selectbox("Model", models, index=0)
        else:
            selected_model = "llama3.2"
            st.warning("No models. Run: `ollama pull llama3.2`")
    else:
        st.error("Ollama not available")
        st.caption("Start: `ollama serve`")
        selected_model = "llama3.2"


# Tabs
tab_ask, tab_upload = st.tabs(["Ask", "Upload"])


# === ASK TAB ===
with tab_ask:
    if stats and stats.get("documents", 0) == 0:
        st.warning("No documents in database. Go to 'Upload' to add PDFs.")
    else:
        question = st.text_input(
            "Ask a question",
            placeholder="??",
            key="question_input",
        )

        if st.button("Ask", type="primary", disabled=not question):
            with st.spinner("Searching and generating answer..."):
                try:
                    result = ask_question(question, model=selected_model)
                    
                    st.subheader("Answer")
                    st.markdown(result.get("answer", "No answer"))
                    
                    sources = result.get("sources", [])
                    if sources:
                        st.subheader("Sources")
                        for src in sources:
                            with st.expander(f"{src.get('document_title', 'Unknown')} (p. {src.get('page_number', '?')})"):
                                st.caption(f"Relevance: {src.get('score', 0):.2%}")
                                st.text(src.get("chunk_text", ""))
                
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        st.error("Ollama is not available. Start with `ollama serve`.")
                    else:
                        st.error(f"Error: {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# === UPLOAD TAB ===
with tab_upload:
    st.subheader("Upload PDF")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        key="pdf_uploader",
    )
    
    if uploaded_file:
        default_title = uploaded_file.name.replace(".pdf", "").replace("_", " ").replace("-", " ")
        title = st.text_input("Title", value=default_title)
        
        if st.button("Upload", type="primary"):
            with st.spinner("Uploading and processing..."):
                try:
                    result = upload_document(uploaded_file, title)
                    st.success(f"Uploaded: {result.get('title')}")
                    
                    extraction = result.get("extraction", {})
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Pages", extraction.get("total_pages", 0))
                    col2.metric("Chunks", extraction.get("chunks_created", 0))
                    col3.metric("Characters", extraction.get("total_chars", 0))
                    
                    # Clear cache so statistics update
                    get_stats.clear()
                    st.rerun()
                    
                except httpx.HTTPStatusError as e:
                    st.error(f"Upload error: {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# Footer
st.divider()


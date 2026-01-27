"""
Local LLM integration via Ollama.

Requires Ollama to be installed and running locally.
Install: https://ollama.ai
Start model: ollama pull llama3.2
"""

import httpx
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"


async def generate_answer(
    query: str,
    context_chunks: list[str],
    model: str = DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Generate answer based on question and context chunks.
    
    Args:
        query: The user's question
        context_chunks: List of relevant text chunks from the search
        model: Ollama model name
        system_prompt: Optional system prompt
    
    Returns:
        Generated answer from LLM
    """
    if system_prompt is None:
        system_prompt = """You are a helpful assistant that answers questions based on provided context.

Rules:
- Answer ONLY based on the information in the context below
- If the answer is not in the context, say so clearly
- Be concise and direct
- Answer in the same language as the question"""

    context_text = "\n\n---\n\n".join(context_chunks)
    
    user_prompt = f"""CONTEXT:
{context_text}

QUESTION:
{query}

ANSWER:"""

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                }
            }
        )
        response.raise_for_status()
        return response.json()["response"]


async def check_ollama_status() -> dict:
    """Check if Ollama is available and which models exist."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return {
                "available": True,
                "models": [m["name"] for m in models],
                "default_model": DEFAULT_MODEL,
            }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "hint": "Start Ollama with: ollama serve",
        }


def get_llm_info() -> dict:
    """Return information about the LLM configuration."""
    return {
        "provider": "Ollama (local)",
        "base_url": OLLAMA_BASE_URL,
        "default_model": DEFAULT_MODEL,
        "privacy": "100% local - no data leaves the machine",
    }

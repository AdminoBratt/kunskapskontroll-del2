"""
LLM integration via Google Gemini API using LangChain's ChatGoogleGenerativeAI.

Requires a Google API key:
  Set GOOGLE_API_KEY in backend/.env
  Get a key at: https://aistudio.google.com/app/apikey
"""

import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

DEFAULT_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided context.

Rules:
- Answer ONLY based on the information in the context below
- If the answer is not in the context, say so clearly
- Be concise and direct
- Answer in the same language as the question"""


def get_llm(model: str = DEFAULT_MODEL) -> ChatGoogleGenerativeAI:
    """Get a ChatGoogleGenerativeAI instance for the given model."""
    return ChatGoogleGenerativeAI(model=model, temperature=0.3)


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
        model: Gemini model name (e.g. gemini-2.0-flash)
        system_prompt: Optional system prompt (uses default if None)

    Returns:
        Generated answer from Gemini
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

    context_text = "\n\n---\n\n".join(context_chunks)

    full_prompt = f"""{system_prompt}

CONTEXT:
{context_text}

QUESTION:
{query}

ANSWER:"""

    llm = get_llm(model)
    response = await llm.ainvoke([HumanMessage(content=full_prompt)])
    return response.content


async def check_llm_status() -> dict:
    """Check if the Gemini API key is configured."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return {
            "available": False,
            "error": "GOOGLE_API_KEY not set",
            "hint": "Add GOOGLE_API_KEY=<your-key> to backend/.env",
        }
    return {
        "available": True,
        "default_model": DEFAULT_MODEL,
        "provider": "Google Gemini API",
    }


def get_llm_info() -> dict:
    """Return information about the LLM configuration."""
    return {
        "provider": "Google Gemini API via LangChain ChatGoogleGenerativeAI",
        "default_model": DEFAULT_MODEL,
        "privacy": "Queries are sent to Google's API",
    }

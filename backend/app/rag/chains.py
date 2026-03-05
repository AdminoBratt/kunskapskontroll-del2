"""
LangChain LCEL RAG chain.

Provides create_rag_chain() which wires a retriever into a full
retrieve-then-generate pipeline using LangChain Expression Language (LCEL).
"""

from dataclasses import dataclass
from typing import List

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever

from app.rag.llm import DEFAULT_MODEL, get_llm

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided context.
Rules:
- Answer ONLY based on the information in the context below
- If the answer is not in the context, say so clearly
- Be concise and direct
- Answer in the same language as the question

Context: {context}"""


@dataclass
class RAGResponse:
    """Response shape returned by /ask."""
    answer: str
    sources: List[dict]
    question: str


def create_rag_chain(retriever: BaseRetriever, model: str = DEFAULT_MODEL):
    """
    Build a full LCEL RAG chain.

    Returns a chain that accepts {"input": question} and produces
    {"answer": str, "context": List[Document]}.

    Usage:
        chain = create_rag_chain(retriever)
        result = chain.invoke({"input": "What is X?"})
        answer = result["answer"]
        sources = result["context"]
    """
    llm = get_llm(model)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    doc_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, doc_chain)

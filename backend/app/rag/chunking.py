"""
Chunking module for splitting text into searchable pieces.

Uses LangChain's RecursiveCharacterTextSplitter with the same parameters
as the previous custom implementation.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

TEXT_SEPARATORS = [
    "\n\n",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
]


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=TEXT_SEPARATORS,
    )


def split_text(text: str) -> list[str]:
    """
    Split text into chunks.

    Args:
        text: The text to split.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    splitter = get_text_splitter()
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip() and len(c.strip()) > 20]


def split_page_text(page_text: str) -> list[str]:
    """
    Split text from a PDF page into chunks.

    Args:
        page_text: Text from a PDF page.

    Returns:
        List of text chunks from the page.
    """
    return split_text(page_text)

"""
Chunking module for splitting text into searchable pieces.

Optimized for documents with appropriate separators
and chunk sizes for the embedding model.

No LangChain - custom implementation.
"""

from typing import List

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


def _split_by_separator(text: str, separator: str) -> List[str]:
    """Split text with a separator, keep the separator at the end of each part."""
    if not separator:
        return list(text)
    
    parts = text.split(separator)
    result = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            result.append(part + separator)
        elif part:
            result.append(part)
    return result


def _merge_chunks(parts: List[str], chunk_size: int, overlap: int) -> List[str]:
    """Merge parts into chunks with overlap."""
    if not parts:
        return []
    
    chunks = []
    current = ""
    
    for part in parts:
        if len(current) + len(part) <= chunk_size:
            current += part
        else:
            if current:
                chunks.append(current)
            current = part if len(part) <= chunk_size else part[:chunk_size]
    
    if current:
        chunks.append(current)
    
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    
    overlapped = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        overlap_text = prev[-overlap:] if len(prev) > overlap else prev
        overlapped.append(overlap_text + chunks[i])
    
    return overlapped


def _recursive_split(text: str, separators: List[str], chunk_size: int) -> List[str]:
    """Recursively split text with descending separators."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    for sep in separators:
        parts = _split_by_separator(text, sep)
        if len(parts) > 1:
            result = []
            for part in parts:
                if len(part) <= chunk_size:
                    result.append(part)
                else:
                    remaining_seps = separators[separators.index(sep) + 1:]
                    if remaining_seps:
                        result.extend(_recursive_split(part, remaining_seps, chunk_size))
                    else:
                        for i in range(0, len(part), chunk_size):
                            result.append(part[i:i + chunk_size])
            return result
    
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def split_text(text: str) -> List[str]:
    """
    Split text into chunks.
    
    Args:
        text: The text to split.
        
    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []
    
    parts = _recursive_split(text, TEXT_SEPARATORS, CHUNK_SIZE)
    chunks = _merge_chunks(parts, CHUNK_SIZE, CHUNK_OVERLAP)
    
    return [c.strip() for c in chunks if c.strip() and len(c.strip()) > 20]


def split_page_text(page_text: str) -> List[str]:
    """
    Split text from a PDF page into chunks.
    
    Args:
        page_text: Text from a PDF page.
        
    Returns:
        List of text chunks from the page.
    """
    return split_text(page_text)

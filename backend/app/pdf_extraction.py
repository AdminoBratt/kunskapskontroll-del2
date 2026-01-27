import fitz
import pytesseract
import pdfplumber
import unicodedata
import re
from PIL import Image
from io import BytesIO
from dataclasses import dataclass, field
from typing import List, Optional, Literal


@dataclass
class PageResult:
    page_num: int
    text: str
    source: Literal["text", "ocr"]
    has_tables: bool = False
    tables_markdown: Optional[str] = None


@dataclass
class DocumentExtraction:
    pages: List[PageResult] = field(default_factory=list)
    
    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)
    
    @property
    def total_pages(self) -> int:
        return len(self.pages)
    
    @property
    def ocr_pages_count(self) -> int:
        return sum(1 for page in self.pages if page.source == "ocr")


MIN_TEXT_CHARS = 40


def page_needs_ocr(page: fitz.Page) -> bool:
    """Determine if a page needs OCR based on text content and images."""
    text = page.get_text("text") or ""
    text = text.strip()
    
    if len(text) >= MIN_TEXT_CHARS:
        return False
    
    images = page.get_images(full=True)
    if images and len(text) < MIN_TEXT_CHARS:
        return True
    
    blocks = page.get_text("blocks")
    has_text_blocks = any(b[4].strip() for b in blocks if len(b) > 4)
    return not has_text_blocks


def ocr_page(page: fitz.Page, lang: str = "eng") -> str:
    """Run OCR on a page by rendering it as an image."""
    zoom = 300 / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    text = pytesseract.image_to_string(
        img,
        lang=lang,
        config="--oem 1 --psm 6"
    )
    return text


def extract_text_from_page(page: fitz.Page) -> str:
    """Extract text from a digital PDF page."""
    return page.get_text("text") or ""


def fix_broken_hyphenation(text: str) -> str:
    """Fix hyphenation broken across lines."""
    pattern = r"(\w)-\n([a-z])"
    return re.sub(pattern, r"\1\2", text, flags=re.IGNORECASE)


def collapse_whitespace(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def postprocess_text(text: str) -> str:
    """Post-process extracted text."""
    text = unicodedata.normalize("NFC", text)
    text = fix_broken_hyphenation(text)
    text = collapse_whitespace(text)
    return text


def table_to_markdown(table: List[List[str]]) -> str:
    """Convert a table to markdown format."""
    if not table:
        return ""
    
    lines = []
    header = table[0]
    lines.append("| " + " | ".join(c or "" for c in header) + " |")
    lines.append("|" + "|".join("---" for _ in header) + "|")
    for row in table[1:]:
        lines.append("| " + " | ".join(c or "" for c in row) + " |")
    return "\n".join(lines)


def extract_tables_for_page(pdf_bytes: bytes, page_number: int) -> tuple[bool, Optional[str]]:
    """Extract tables from a specific page using pdfplumber."""
    tables_md_parts = []
    has_tables = False
    
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            if page_number >= len(pdf.pages):
                return False, None
            page = pdf.pages[page_number]
            tables = page.extract_tables()
            for table in tables or []:
                if table and len(table) > 1:
                    has_tables = True
                    tables_md_parts.append(table_to_markdown(table))
    except Exception:
        pass
    
    tables_md = "\n\n".join(tables_md_parts) if tables_md_parts else None
    return has_tables, tables_md


def should_extract_tables(text: str) -> bool:
    """Determine if we should try to extract tables based on text content."""
    keywords = [
        "invoice", "order", "specification",
        "sum", "total", "vat", "quantity",
        "price", "amount", "sek", "kr"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)


def extract_pdf_document(pdf_bytes: bytes, lang: str = "eng") -> DocumentExtraction:
    """
    Main function to extract text from a PDF.
    
    Handles both digital PDFs and scanned documents automatically.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    
    for i, page in enumerate(doc):
        if page_needs_ocr(page):
            try:
                text = ocr_page(page, lang=lang)
                source = "ocr"
            except Exception as e:
                text = f"[OCR error: {str(e)}]"
                source = "ocr"
        else:
            text = extract_text_from_page(page)
            source = "text"
        
        text = postprocess_text(text)
        
        has_tables = False
        tables_md = None
        
        if source == "text" and should_extract_tables(text):
            has_tables, tables_md = extract_tables_for_page(pdf_bytes, page_number=i)
        
        pages.append(PageResult(
            page_num=i,
            text=text,
            source=source,
            has_tables=has_tables,
            tables_markdown=tables_md
        ))
    
    doc.close()
    return DocumentExtraction(pages=pages)

"""Reading papers in many formats: PDF, Word (.docx), text, Markdown and web pages (.html).

PDFs have real pages. The other formats don't, so we cut them into "pages" of roughly
`PAGE_CHARS` characters. That way every answer can still point to "Page N".
"""

import io
import re
from html.parser import HTMLParser
from pathlib import Path

from docx import Document as WordDocument

from app.services.pdf_parser import parse_pdf
from app.services.security_filters import clean_paper_text

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".markdown", ".html", ".htm")
PAGE_CHARS = 2500  # size of a pretend "page" for formats that have no real pages


def is_supported(filename: str) -> bool:
    """Do we know how to read this kind of file?"""
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def paginate(text: str, max_chars: int = PAGE_CHARS) -> list[str]:
    """Group paragraphs into pretend pages without cutting any paragraph in half."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]
    pages: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) > max_chars:
            pages.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        pages.append(current)
    return pages


def _docx_text(data: bytes) -> str:
    """Pull the words out of a Word document (paragraphs and table cells)."""
    doc = WordDocument(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n\n".join(parts)


class _TextExtractor(HTMLParser):
    """Collects the visible words of a web page and ignores code (<script>) and styling (<style>)."""

    BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0  # >0 while inside <script> or <style>

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _html_text(data: bytes) -> str:
    """Turn a web page into plain text."""
    extractor = _TextExtractor()
    extractor.feed(data.decode("utf-8", errors="replace"))
    return "".join(extractor.parts)


def parse_document(filename: str, data: bytes) -> list[dict]:
    """Read any supported file and return pages: [{"page_number": 1, "text": "..."}, ...]."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(data)
    if ext == ".docx":
        text = _docx_text(data)
    elif ext in (".html", ".htm"):
        text = _html_text(data)
    elif ext in (".txt", ".md", ".markdown"):
        text = data.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
    return [
        {"page_number": number, "text": clean_paper_text(page)}
        for number, page in enumerate(paginate(text), start=1)
    ]

"""Reading PDF files page by page."""

import pymupdf

from app.services.security_filters import clean_paper_text


def parse_pdf(data: bytes) -> list[dict]:
    """Return one entry per page: {"page_number": 1, "text": "..."}.

    Scanned PDFs (pictures of text) have no real text, so their pages come back empty.
    """
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages = []
    try:
        for i, page in enumerate(doc, start=1):
            raw = page.get_text("text") or ""
            pages.append({"page_number": i, "text": clean_paper_text(raw)})
    finally:
        doc.close()
    return pages
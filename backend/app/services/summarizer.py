"""Writing summaries of a whole paper.

A small AI can't read a whole paper at once, so we hand it a sample of excerpts spread
evenly from start to finish (so the summary covers the beginning, middle and end).
"""

from sqlalchemy.orm import Session

from app.core.models import Chunk, Document
from app.repositories import chunks as chunk_repo
from app.services.llm.ollama import OllamaWriter

INSTRUCTIONS = {
    "short": "Write a summary in 3 to 4 plain sentences.",
    "key_points": "List the 5 most important points as short bullet points.",
    "simple": (
        "Explain the paper in everyday words, as if to a curious teenager with no science background. "
        "Use at most 6 sentences."
    ),
}


def spread_excerpts(chunks: list[Chunk], limit_chars: int = 5000) -> str:
    """Pick chunks evenly across the paper until about `limit_chars` characters are collected."""
    if not chunks:
        return ""
    avg = max(1, sum(len(c.text) for c in chunks) // len(chunks))
    wanted = max(1, min(len(chunks), limit_chars // avg))
    step = len(chunks) / wanted
    picked = [chunks[int(i * step)] for i in range(wanted)]
    return "\n\n".join(f"(Page {c.page_number}) {c.text}" for c in picked)


def summarize(db: Session, doc: Document, kind: str) -> str:
    """Return a summary of the paper in the requested style, or "" if the paper has no text."""
    excerpts = spread_excerpts(chunk_repo.list_for_document(db, doc.id))
    if not excerpts:
        return ""
    prompt = (
        "You summarize research papers. Use ONLY the excerpts below. Do not invent facts.\n"
        f"{INSTRUCTIONS.get(kind, INSTRUCTIONS['short'])}\n\n"
        f"Excerpts from '{doc.title or doc.filename}':\n{excerpts}\n\nSummary:"
    )
    return OllamaWriter().write(prompt)

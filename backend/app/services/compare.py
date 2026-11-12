"""Comparing papers: pull the best excerpts from each paper, then ask the AI to compare them."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.models import Document
from app.services.llm.ollama import OllamaWriter
from app.services.retriever import find_chunks


def compare_papers(db: Session, user_id: UUID, docs: list[Document], question: str) -> str:
    """Return a comparison that says which paper each fact comes from."""
    blocks = []
    for doc in docs:
        chunks = find_chunks(db, user_id, doc.id, question, k=4)
        name = doc.title or doc.filename
        if not chunks:
            blocks.append(f"Paper '{name}': (no matching pages)")
            continue
        excerpts = "\n".join(f"- Page {c.page_number}: {c.text}" for c in chunks)
        blocks.append(f"Paper '{name}':\n{excerpts}")
    prompt = (
        "Compare the papers using only the excerpts. "
        "Say which paper a fact comes from. If you cannot tell, say so.\n\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\nComparison:"
    )
    return OllamaWriter().write(prompt) or "The writer did not return a comparison."
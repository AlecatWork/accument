"""Database helpers for `chunks` (small pieces of papers)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Chunk


def add_many(db: Session, rows: list[Chunk]) -> list[Chunk]:
    """Save many chunks at once."""
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def list_for_document(db: Session, document_id: UUID) -> list[Chunk]:
    """Every chunk of a paper, in reading order."""
    return list(
        db.scalars(
            select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.page_number, Chunk.chunk_index)
        ).all()
    )
"""Database helpers for `documents` (papers).

Every lookup includes the owner's id, so one person can never reach another person's paper.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Document


def list_for_user(db: Session, user_id: UUID) -> list[Document]:
    """All of a person's papers, newest first."""
    return list(
        db.scalars(select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())).all()
    )


def get_owned(db: Session, user_id: UUID, document_id: UUID) -> Document | None:
    """One paper, but only if it belongs to this person."""
    return db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))


def create(db: Session, **kwargs) -> Document:
    """Add a new paper record."""
    doc = Document(**kwargs)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def save(db: Session, doc: Document) -> Document:
    """Save changes made to a paper record."""
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_owned(db: Session, doc: Document) -> None:
    """Delete a paper (the database also removes its chunks, chats, notes and summaries)."""
    db.delete(doc)
    db.commit()

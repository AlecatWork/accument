"""Database helpers for the `summaries` drawer."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Summary


def create(db: Session, user_id: UUID, document_id: UUID, kind: str, content: str) -> Summary:
    """Save a freshly written summary."""
    row = Summary(user_id=user_id, document_id=document_id, kind=kind, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_document(db: Session, user_id: UUID, document_id: UUID) -> list[Summary]:
    """A person's saved summaries for one paper, newest first."""
    return list(
        db.scalars(
            select(Summary)
            .where(Summary.user_id == user_id, Summary.document_id == document_id)
            .order_by(Summary.created_at.desc())
        ).all()
    )

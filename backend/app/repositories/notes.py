"""Database helpers for `notes`."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Note


def create(db: Session, user_id: UUID, document_id: UUID, content: str) -> Note:
    """Add a note to a paper."""
    row = Note(user_id=user_id, document_id=document_id, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_document(db: Session, user_id: UUID, document_id: UUID) -> list[Note]:
    """All of a person's notes on one paper, most recently touched first."""
    return list(
        db.scalars(
            select(Note)
            .where(Note.user_id == user_id, Note.document_id == document_id)
            .order_by(Note.updated_at.desc())
        ).all()
    )


def get_owned(db: Session, user_id: UUID, note_id: UUID) -> Note | None:
    """One note, but only if it belongs to this person."""
    return db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))


def update_content(db: Session, note: Note, content: str) -> Note:
    """Replace the text of a note."""
    note.content = content
    db.commit()
    db.refresh(note)
    return note


def delete(db: Session, note: Note) -> None:
    """Delete a note."""
    db.delete(note)
    db.commit()

"""Your own notes on papers. A paper can have as many notes as you like."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.schemas import NoteIn, NoteOut, NoteUpdate
from app.repositories import documents as doc_repo
from app.repositories import notes as note_repo

router = APIRouter()


@router.post("", response_model=NoteOut)
def create_note(body: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add a note to one of your papers."""
    doc = doc_repo.get_owned(db, user.id, body.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    return note_repo.create(db, user.id, doc.id, body.content)



@router.get("", response_model=list[NoteOut])
def list_notes(document_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every note you wrote on one paper."""
    return note_repo.list_for_document(db, user.id, document_id)



@router.put("/{note_id}", response_model=NoteOut)
def edit_note(note_id: UUID, body: NoteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change the text of a note."""
    note = note_repo.get_owned(db, user.id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note_repo.update_content(db, note, body.content)



@router.delete("/{note_id}")
def delete_note(note_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a note."""
    note = note_repo.get_owned(db, user.id, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note_repo.delete(db, note)
    return {"ok": True}
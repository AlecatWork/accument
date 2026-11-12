"""The library: list, open, upload, bookmark and delete papers."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.rate_limit import limiter
from app.core.schemas import PaperOut, ReadingStatusIn
from app.repositories import documents as doc_repo
from app.services.document_parser import SUPPORTED_EXTENSIONS, is_supported
from app.services.embeddings import delete_document
from app.services.file_storage import delete_file
from app.services.ingestion import ingest_document

router = APIRouter()


@router.get("", response_model=list[PaperOut])
def list_papers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """All of the logged-in person's papers."""
    return doc_repo.list_for_user(db, user.id)


@router.get("/{document_id}", response_model=PaperOut)
def get_paper(document_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One paper."""
    doc = doc_repo.get_owned(db, user.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    return doc



@router.post("", response_model=PaperOut)
@limiter.limit("8/minute")
def upload_paper(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Upload a paper (PDF, Word, text, Markdown or HTML). Reading it can take a minute."""
    filename = file.filename or "paper"
    if not is_supported(filename):
        allowed = ", ".join(SUPPORTED_EXTENSIONS)
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")
    data = file.file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="That file is empty")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File is larger than {settings.max_upload_mb} MB")
    return ingest_document(db, user.id, filename, data)



@router.patch("/{document_id}", response_model=PaperOut)
def set_reading_status(
    document_id: UUID, body: ReadingStatusIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Move a paper between "to read", "reading" and "done"."""
    doc = doc_repo.get_owned(db, user.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    doc.reading_status = body.reading_status
    return doc_repo.save(db, doc)



@router.delete("/{document_id}")
def delete_paper(document_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a paper everywhere: search shelf, stored file, and database rows."""
    doc = doc_repo.get_owned(db, user.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found")
    delete_document(str(doc.id))
    delete_file(doc.file_path)
    doc_repo.delete_owned(db, doc)
    return {"ok": True}


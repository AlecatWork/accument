"""Short, key-point or plain-English summaries of a paper."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.rate_limit import limiter
from app.core.schemas import SummaryIn, SummaryOut
from app.repositories import documents as doc_repo
from app.repositories import summaries as summary_repo
from app.services.summarizer import summarize

router = APIRouter()


@router.post("", response_model=SummaryOut)
@limiter.limit("8/minute")
def create_summary(
    request: Request, body: SummaryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Write (and save) a new summary of one paper."""
    doc = doc_repo.get_owned(db, user.id, body.document_id)
    if not doc or doc.status != "ready":
        raise HTTPException(status_code=400, detail="That paper must be yours and ready")
    text = summarize(db, doc, body.kind)
    if not text:
        raise HTTPException(status_code=502, detail="The writer did not return a summary. Try again.")
    return summary_repo.create(db, user.id, doc.id, body.kind, text)


@router.get("", response_model=list[SummaryOut])
def list_summaries(document_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Saved summaries for one paper."""
    return summary_repo.list_for_document(db, user.id, document_id)

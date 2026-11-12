"""Ask one question across several papers at once."""


from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.rate_limit import limiter
from app.core.schemas import CompareIn, CompareOut
from app.repositories import documents as doc_repo
from app.services.compare import compare_papers

router = APIRouter()


@router.post("", response_model=CompareOut)
@limiter.limit("8/minute")
def compare(request: Request, body: CompareIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compare 2-4 of your papers on a question."""
    docs = []
    for doc_id in body.document_ids:
        doc = doc_repo.get_owned(db, user.id, doc_id)
        if not doc or doc.status != "ready":
            raise HTTPException(status_code=400, detail="Every paper must be yours and ready")
        docs.append(doc)
    return CompareOut(answer=compare_papers(db, user.id, docs, body.question))

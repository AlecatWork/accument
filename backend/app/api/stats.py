"""Numbers for the dashboard."""


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.schemas import StatsOut
from app.repositories.stats import for_user

router = APIRouter()


@router.get("", response_model=StatsOut)
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Counts, trends and recent activity for the logged-in person."""
    return for_user(db, user.id)
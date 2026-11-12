"""Sign up, log in, and "who am I?"."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.rate_limit import limiter
from app.core.schemas import LoginIn, SignupIn, TokenOut, UserOut
from app.core.security import create_token, hash_password, verify_password
from app.repositories import users as user_repo

router = APIRouter()

@router.post("/signup", response_model=TokenOut)
@limiter.limit("10/minute")
def signup(request: Request, body: SignupIn, db: Session = Depends(get_db)):
    """Create an account and log in straight away."""
    if user_repo.get_by_email(db, body.email):
        raise HTTPException(status_code=400, detail="That email already has an account")
    user = user_repo.create(db, body.email, hash_password(body.password))
    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    """Check email + password and hand back a wristband."""
    user = user_repo.get_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    return TokenOut(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Return the logged-in user."""
    return user
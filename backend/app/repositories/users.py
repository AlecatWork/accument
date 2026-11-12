"""Database helpers for `users`."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import User


def get_by_id(db: Session, user_id: UUID) -> User | None:
    """Find a user by id."""
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    """Find a user by email (emails are stored in lower case)."""
    return db.scalar(select(User).where(User.email == email.lower()))


def create(db: Session, email: str, password_hash: str) -> User:
    """Create an account."""
    user = User(email=email.lower(), password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
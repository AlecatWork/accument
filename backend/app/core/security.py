"""Passwords and login wristbands.

* A password is never stored. We store a scrambled version (a "hash") that can't be unscrambled.
* After logging in you get a "token" (a signed wristband). Every later request shows it,
  so you don't have to type your password again.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import settings

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Scramble a password so we can store it safely."""
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a typed password against the stored scrambled version."""
    try:
        return hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    

def create_token(user_id: UUID) -> str:
    """Make a signed wristband that says who you are and when it expires."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.jwt_secret, algorithm="HS256")


def read_token(token: str) -> UUID | None:
    """Read a wristband. Returns the user's id, or None if it is fake or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None


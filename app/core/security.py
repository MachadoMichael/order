from datetime import timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings
from app.models.base import utcnow


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: UUID, email: str, role: str) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": utcnow(),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

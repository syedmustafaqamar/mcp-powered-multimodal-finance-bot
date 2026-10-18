from datetime import datetime, timedelta, timezone

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()

# FastAPI uses this scheme to read: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.TOKEN_EXPIRY)

    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "iss": settings.PROJECT_NAME,
    }

    return jwt.encode(
        payload,
        settings.SIGNING_KEY,
        algorithm=settings.AUTH_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SIGNING_KEY,
        algorithms=[settings.AUTH_ALGORITHM],
        issuer=settings.PROJECT_NAME,
    )

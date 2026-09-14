from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import decode_access_token, oauth2_scheme
from app.core.database import get_db


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        token_type = payload.get("type")

        if not subject or token_type != "access":
            raise credentials_exception()

    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise credentials_exception()

    user = db.scalar(select(User).where(User.username == subject))

    if user is None:
        raise credentials_exception()

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user


def require_roles(*allowed_roles: str) -> Callable:
    def role_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return role_dependency

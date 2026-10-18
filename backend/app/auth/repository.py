from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import hash_password, verify_password


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    statement = select(User).where(
        or_(User.username == identifier, User.email == identifier)
    )
    return db.scalar(statement)


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
) -> User:
    user = User(
        username=username,
        email=email.lower(),
        hashed_password=hash_password(password),
        role="user",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    identifier: str,
    password: str,
) -> User | None:
    user = get_user_by_identifier(db, identifier)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user

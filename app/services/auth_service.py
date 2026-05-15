from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    return db.scalars(statement).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.scalars(statement).first()


def register_user(db: Session, payload: RegisterRequest) -> User:
    email = payload.email.lower()

    existing_user_statement = select(User).where(
        or_(
            User.email == email,
            User.username == payload.username if payload.username else False,
        )
    )

    existing_user = db.scalars(existing_user_statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.READER,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, payload: LoginRequest) -> tuple[User, str]:
    user = get_user_by_email(db, payload.email)

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )

    token = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role.value,
            "email": user.email,
        },
    )

    return user, token
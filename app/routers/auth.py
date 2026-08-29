from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])

# HARDENING: neither endpoint had any rate limiting -- /auth/login could be
# brute-forced without friction, and /auth/register could be spammed to
# create accounts. See core/rate_limit.py for caveats (in-process only).
_register_rate_limit = rate_limit("auth-register", max_requests=5, window_seconds=60)
_login_rate_limit = rate_limit("auth-login", max_requests=10, window_seconds=60)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_register_rate_limit)],
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = register_user(db=db, payload=payload)

    user, token = authenticate_user(
        db=db,
        payload=LoginRequest(
            email=payload.email,
            password=payload.password,
        ),
    )

    return TokenResponse(
        access_token=token,
        user=user,
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_login_rate_limit)])
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user, token = authenticate_user(db=db, payload=payload)

    return TokenResponse(
        access_token=token,
        user=user,
    )


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
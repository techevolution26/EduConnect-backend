from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole

# NOTE: this file defines its own local UserRead below (duplicating the
# shape in schemas/user.py). Pre-existing duplication in the original
# codebase -- left as-is to avoid an unrelated cross-cutting refactor here,
# but worth consolidating into a single shared UserRead in a follow-up.


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    username: Optional[str] = Field(default=None, max_length=80)
    role: UserRole = UserRole.READER


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    username: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    username: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    bio: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    # HARDENING: previously `password: str` had no length constraint at all
    # on this schema (UserCreate, a separate schema, did have one) -- the
    # public /auth/register endpoint accepted empty or single-character
    # passwords. Matches the UserCreate constraint for consistency.
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    username: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # BUGFIX: routers/auth.py has always constructed this with a `user=`
    # kwarg, but this field never existed on the schema -- Pydantic v2's
    # default `extra="ignore"` silently dropped it rather than erroring,
    # so /auth/login and /auth/register responses never actually included
    # the user object the frontend almost certainly expects alongside the
    # token (to avoid an extra round-trip to /users/me right after login).
    user: UserRead

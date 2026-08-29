from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import School, StudentProfile
from app.models.user import User

logger = logging.getLogger("educonnect.students")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def search_schools(db: Session, query: str, limit: int = 20) -> list[School]:
    like = f"%{query.strip()}%"
    return list(
        db.scalars(select(School).where(School.name.ilike(like)).limit(limit)).all()
    )


def get_or_create_profile(db: Session, user: User) -> StudentProfile:
    profile = db.scalars(
        select(StudentProfile).where(StudentProfile.user_id == user.id)
    ).first()

    if profile:
        return profile

    profile = StudentProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_affiliation(
    db: Session,
    user: User,
    school_id: str,
    grade_level: str | None,
    curriculum: str | None,
) -> StudentProfile:
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School was not found.")

    profile = get_or_create_profile(db, user)
    profile.school_id = school_id
    profile.grade_level = grade_level
    profile.curriculum = curriculum

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def request_verification(db: Session, user: User, school_email: str) -> None:
    """
    Generate and "send" a verification code to the student's school email.

    NOTE: actual email delivery is out of scope for this pass -- this
    function generates and stores the code and logs it (so the flow is
    testable end-to-end in development). Wire in a real email provider at
    the marked call site before relying on this in production.
    """
    profile = get_or_create_profile(db, user)

    if not profile.school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your school affiliation before requesting verification.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    profile.verification_code = code
    profile.verification_email = school_email.strip().lower()

    db.add(profile)
    db.commit()

    # TODO: send `code` to `school_email` via the platform's email provider.
    logger.info("Student verification code for user_id=%s: %s (dev-mode log only)", user.id, code)


def confirm_verification(db: Session, user: User, code: str) -> StudentProfile:
    profile = get_or_create_profile(db, user)

    if not profile.verification_code or profile.verification_code != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    profile.verified = True
    profile.verified_at = _now()
    profile.verification_code = None  # single-use

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def admin_verify(db: Session, user_id: str) -> StudentProfile:
    """Manual verification path for STUDENTS_VERIFY-permission admins, e.g.
    when email verification isn't practical (no school email on file)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found.")

    profile = get_or_create_profile(db, user)
    profile.verified = True
    profile.verified_at = _now()
    profile.verification_code = None

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_my_profile(db: Session, user: User) -> StudentProfile | None:
    return db.scalars(select(StudentProfile).where(StudentProfile.user_id == user.id)).first()

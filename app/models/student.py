"""
Student identity: school affiliation, curriculum, and verification status.

DESIGN NOTE: StudentProfile is a one-to-one EXTENSION of User, not a
separate account type -- most users won't be students, and we don't want
nullable school/curriculum columns cluttering the frequently-queried
`users` table. A missing StudentProfile row simply means "this user hasn't
gone through student verification", independent of their UserRole (a user
can hold role=STUDENT without yet being verified, and verification is what
unlocks student-only events and the STUDENT_PARTNER discount tier's
strongest form of eligibility check).
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SchoolType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    COLLEGE = "COLLEGE"
    UNIVERSITY = "UNIVERSITY"


class School(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    county: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    type: Mapped[Optional[SchoolType]] = mapped_column(Enum(SchoolType), nullable=True)


class StudentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    school_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True
    )

    grade_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "Grade 8", "Form 3"
    curriculum: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)   # "CBC", "KCSE", "8-4-4"

    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # Short code emailed to the school-domain address the student provides;
    # cleared once verification succeeds so it can't be reused.
    verification_code: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    verification_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="student_profile")
    school = relationship("School", foreign_keys=[school_id])

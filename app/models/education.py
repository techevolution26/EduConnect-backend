import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CurriculumType(str, enum.Enum):
    CBC = "CBC"
    CBE = "CBE"
    CAMBRIDGE = "CAMBRIDGE"
    AMERICAN = "AMERICAN"
    HOMESCHOOL = "HOMESCHOOL"
    OTHER = "OTHER"


class EducationResourceType(str, enum.Enum):
    LESSON_NOTE = "LESSON_NOTE"
    REVISION = "REVISION"
    STUDY_GUIDE = "STUDY_GUIDE"
    SCHEME_OF_WORK = "SCHEME_OF_WORK"
    PRINTABLE = "PRINTABLE"
    ASSESSMENT = "ASSESSMENT"
    ARTICLE = "ARTICLE"


class ChildrenAgeGroup(str, enum.Enum):
    AGE_3_5 = "AGE_3_5"
    AGE_6_9 = "AGE_6_9"
    AGE_10_13 = "AGE_10_13"


class EducationResource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "education_resources"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
    )

    curriculum: Mapped[CurriculumType] = mapped_column(Enum(CurriculumType), nullable=False)
    grade_level: Mapped[Optional[str]] = mapped_column(String(80))
    subject: Mapped[Optional[str]] = mapped_column(String(120))
    resource_type: Mapped[EducationResourceType] = mapped_column(
        Enum(EducationResourceType),
        nullable=False,
    )

    download_url: Mapped[Optional[str]] = mapped_column(String(500))

    content: Mapped["Content"] = relationship()

    __table_args__ = (
        UniqueConstraint("content_id", name="uq_education_resource_content"),
    )


class ChildrenContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "children_contents"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
    )

    age_group: Mapped[ChildrenAgeGroup] = mapped_column(Enum(ChildrenAgeGroup), nullable=False)

    content: Mapped["Content"] = relationship()

    __table_args__ = (
        UniqueConstraint("content_id", name="uq_children_content_content"),
    )
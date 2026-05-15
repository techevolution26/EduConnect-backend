from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.content import Content, ContentStatus, ContentType
from app.models.education import EducationResource
from app.models.user import User, UserRole
from app.schemas.education import EducationResourceCreate


def ensure_can_create_education_resource(user: User) -> None:
    if user.role not in {UserRole.TEACHER, UserRole.WRITER, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers, writers, or admins can create education resources.",
        )


def get_resource_or_404(db: Session, resource_id: str) -> EducationResource:
    resource = db.scalars(
        select(EducationResource)
        .options(joinedload(EducationResource.content))
        .where(EducationResource.id == resource_id)
    ).first()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education resource was not found.",
        )

    return resource


def create_education_resource(
    db: Session,
    payload: EducationResourceCreate,
    user: User,
) -> EducationResource:
    ensure_can_create_education_resource(user)

    content = db.get(Content, payload.content_id)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    if content.author_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only attach education data to your own content.",
        )

    if content.content_type != ContentType.EDUCATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type must be EDUCATION.",
        )

    existing = db.scalars(
        select(EducationResource).where(
            EducationResource.content_id == payload.content_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This content already has an education resource record.",
        )

    resource = EducationResource(**payload.model_dump())

    db.add(resource)
    db.commit()
    db.refresh(resource)

    return resource


def list_education_resources(
    db: Session,
    curriculum: str | None = None,
    subject: str | None = None,
    grade_level: str | None = None,
) -> list[EducationResource]:
    statement = (
        select(EducationResource)
        .join(Content, Content.id == EducationResource.content_id)
        .options(joinedload(EducationResource.content))
        .where(Content.status == ContentStatus.PUBLISHED)
        .order_by(EducationResource.created_at.desc())
    )

    if curriculum:
        statement = statement.where(EducationResource.curriculum == curriculum)

    if subject:
        statement = statement.where(EducationResource.subject == subject)

    if grade_level:
        statement = statement.where(EducationResource.grade_level == grade_level)

    return list(db.scalars(statement).all())
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.education import (
    EducationResourceCreate,
    EducationResourceDetailRead,
    EducationResourceRead,
)
from app.services.education_service import (
    create_education_resource,
    get_resource_or_404,
    list_education_resources,
)

router = APIRouter(prefix="/education", tags=["Education"])


@router.get("/resources", response_model=list[EducationResourceDetailRead])
def get_education_resources(
    db: Annotated[Session, Depends(get_db)],
    curriculum: str | None = None,
    subject: str | None = None,
    grade_level: str | None = None,
) -> list[EducationResourceDetailRead]:
    return list_education_resources(
        db=db,
        curriculum=curriculum,
        subject=subject,
        grade_level=grade_level,
    )


@router.get("/resources/{resource_id}", response_model=EducationResourceDetailRead)
def get_education_resource(
    resource_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> EducationResourceDetailRead:
    return get_resource_or_404(db, resource_id)


@router.post("/resources", response_model=EducationResourceRead)
def create_new_education_resource(
    payload: EducationResourceCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EducationResourceRead:
    return create_education_resource(
        db=db,
        payload=payload,
        user=current_user,
    )
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.models.student import School
from app.models.user import User
from app.schemas.student import (
    SchoolCreate,
    SchoolRead,
    StudentAffiliationUpdate,
    StudentProfileRead,
    StudentVerificationConfirm,
    StudentVerificationRequest,
)
from app.services.student_service import (
    admin_verify,
    confirm_verification,
    get_my_profile,
    request_verification,
    search_schools,
    update_affiliation,
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/schools", response_model=list[SchoolRead])
def get_schools(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(min_length=2, max_length=120),
) -> list[SchoolRead]:
    return search_schools(db, q)


@router.post("/schools", response_model=SchoolRead, status_code=status.HTTP_201_CREATED)
def create_school(
    payload: SchoolCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SchoolRead:
    # Deliberately open to any authenticated user (not admin-gated) -- a
    # student verifying their affiliation should be able to add their
    # school if it's missing from the directory, the same way many
    # platforms let users add an employer that isn't listed yet.
    school = School(name=payload.name, county=payload.county, type=payload.type)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


@router.get("/me", response_model=StudentProfileRead | None)
def get_my_student_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_my_profile(db, current_user)


@router.put("/me/affiliation", response_model=StudentProfileRead)
def update_my_affiliation(
    payload: StudentAffiliationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StudentProfileRead:
    return update_affiliation(
        db,
        current_user,
        school_id=payload.school_id,
        grade_level=payload.grade_level,
        curriculum=payload.curriculum,
    )


@router.post("/me/verify/request", status_code=status.HTTP_202_ACCEPTED)
def request_my_verification(
    payload: StudentVerificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    request_verification(db, current_user, payload.school_email)
    return {"message": "Verification code sent to your school email."}


@router.post("/me/verify/confirm", response_model=StudentProfileRead)
def confirm_my_verification(
    payload: StudentVerificationConfirm,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StudentProfileRead:
    return confirm_verification(db, current_user, payload.code)


@router.post("/{user_id}/verify", response_model=StudentProfileRead)
def admin_verify_student(
    user_id: str,
    current_user: Annotated[User, Depends(require_permission(Permission.STUDENTS_VERIFY))],
    db: Annotated[Session, Depends(get_db)],
) -> StudentProfileRead:
    return admin_verify(db, user_id)

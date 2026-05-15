from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.partnership import (
    AdminActivatePartnershipRequest,
    PartnershipAccessRead,
    PartnershipCreate,
    PartnershipPlanRead,
    PartnershipRead,
)
from app.services.partnership_service import (
    admin_activate_partnership,
    cancel_my_partnership,
    get_my_partnership_access,
    list_partnership_plans,
    start_partnership,
)

router = APIRouter(prefix="/partnerships", tags=["Partnerships"])


@router.get("/plans", response_model=list[PartnershipPlanRead])
def get_partnership_plans() -> list[PartnershipPlanRead]:
    return list_partnership_plans()


@router.get("/me", response_model=PartnershipAccessRead)
def get_my_partnership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipAccessRead:
    return get_my_partnership_access(db, current_user)


@router.post("/start", response_model=PartnershipRead)
def start_new_partnership(
    payload: PartnershipCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipRead:
    return start_partnership(
        db=db,
        user=current_user,
        plan=payload.plan,
        referral_creator_id=payload.referral_creator_id,
    )


@router.post("/cancel", response_model=PartnershipRead)
def cancel_existing_partnership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipRead:
    return cancel_my_partnership(db=db, user=current_user)


@router.post("/{partnership_id}/activate", response_model=PartnershipRead)
def activate_partnership_as_admin(
    partnership_id: str,
    payload: AdminActivatePartnershipRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipRead:
    return admin_activate_partnership(
        db=db,
        partnership_id=partnership_id,
        months=payload.months,
    )
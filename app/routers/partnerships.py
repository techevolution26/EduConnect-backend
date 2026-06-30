from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.partnership import (
    AdminActivatePartnershipRequest,
    PartnershipAccessRead,
    PartnershipCheckoutResponse,
    PartnershipCreate,
    PartnershipPaymentStatusRead,
    PartnershipPlanRead,
    PartnershipRead,
)
from app.services.partnership_service import (
    cancel_my_partnership,
    get_my_partnership_access,
    list_partnership_plans,
    start_partnership_checkout,
    handle_mpesa_callback,
    get_latest_payment_for_user,
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


@router.get("/me/payment-status", response_model=PartnershipPaymentStatusRead)
def get_my_partnership_payment_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipPaymentStatusRead:
    payment = get_latest_payment_for_user(db=db, user=current_user)
    partnership = payment.partnership if payment else None

    return PartnershipPaymentStatusRead(
        payment=payment,
        partnership=partnership,
        message="No recent payment found." if not payment else "Payment status loaded.",
    )


@router.post("/start", response_model=PartnershipCheckoutResponse)
async def start_new_partnership(
    payload: PartnershipCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipCheckoutResponse:
    result = await start_partnership_checkout(
        db=db,
        user=current_user,
        plan=payload.plan,
        phone_number=payload.phone_number,
        referral_creator_id=payload.referral_creator_id,
    )

    return PartnershipCheckoutResponse(
        partnership=result["partnership"],
        payment=result.get("payment"),
        message=result["message"],
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
    from app.services.partnership_service import admin_activate_partnership

    return admin_activate_partnership(
        db=db,
        partnership_id=partnership_id,
        months=payload.months,
    )


@router.post("/mpesa/callback", status_code=status.HTTP_200_OK)
async def mpesa_callback(request: Request, db: Annotated[Session, Depends(get_db)]):
    payload = await request.json()
    payment = handle_mpesa_callback(db, payload)
    return {"ok": True, "matched": bool(payment)}
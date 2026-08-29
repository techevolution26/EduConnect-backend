import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.rate_limit import rate_limit
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
from app.schemas.monetization import ReferralEarningListResponse, ReferralSummaryRead
from app.services.monetization_service import get_my_referral_summary, list_my_referral_earnings
from app.services.partnership_service import (
    admin_activate_partnership,
    cancel_my_partnership,
    get_latest_payment_for_user,
    get_my_partnership_access,
    handle_mpesa_callback,
    list_partnership_plans,
    start_partnership_checkout,
)

logger = logging.getLogger("educonnect.mpesa")

router = APIRouter(prefix="/partnerships", tags=["Partnerships"])

_mpesa_callback_rate_limit = rate_limit("mpesa-callback", max_requests=30, window_seconds=60)


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


@router.get("/referrals/summary", response_model=ReferralSummaryRead)
def get_my_referral_summary_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReferralSummaryRead:
    """Pending/paid commission totals for the current user as a referrer.
    See services/monetization_service.py for the commission mechanics."""
    return get_my_referral_summary(db, current_user)


@router.get("/referrals/earnings", response_model=ReferralEarningListResponse)
def get_my_referral_earnings_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReferralEarningListResponse:
    items = list_my_referral_earnings(db, current_user)
    return ReferralEarningListResponse(items=items, total=len(items), skip=0, limit=len(items))


@router.post("/{partnership_id}/activate", response_model=PartnershipRead)
def activate_partnership_as_admin(
    partnership_id: str,
    payload: AdminActivatePartnershipRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.PARTNERSHIPS_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
) -> PartnershipRead:
    return admin_activate_partnership(
        db=db,
        partnership_id=partnership_id,
        months=payload.months,
    )


@router.post(
    "/mpesa/callback/{secret}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_mpesa_callback_rate_limit)],
)
async def mpesa_callback(
    secret: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Daraja STK push callback endpoint.

    HARDENING: this used to be a bare `/mpesa/callback` route with no
    authentication of any kind -- see the long comment on
    `mpesa_callback_secret` in core/config.py for the exploit this closes.
    Configure Safaricom's callback URL as:

        {PUBLIC_BASE_URL}/api/v1/partnerships/mpesa/callback/{MPESA_CALLBACK_SECRET}

    The secret is compared with constant-time semantics is not critical
    here (it's not a per-request HMAC, just a bearer-style path secret),
    but we still avoid leaking *why* a request was rejected -- an invalid
    secret gets an identical 404 to a route that doesn't exist at all.

    We also always return 200 to Safaricom once the secret check passes,
    even if something goes wrong internally while processing -- Daraja
    aggressively retries non-200 responses, and a flood of retries for a
    genuine internal error just makes debugging harder. Errors are logged
    instead so they're visible without disrupting the webhook contract.
    """
    settings = get_settings()

    if not settings.mpesa_callback_secret or secret != settings.mpesa_callback_secret:
        # 404, not 401/403 -- don't confirm to a prober that this path
        # segment scheme is even the right shape.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    payload = await request.json()

    try:
        payment = handle_mpesa_callback(db, payload)
    except Exception:
        logger.exception("Failed to process M-Pesa callback payload=%r", payload)
        return {"ok": False}

    return {"ok": True, "matched": bool(payment)}
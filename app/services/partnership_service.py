from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.partnership import Partnership, PartnershipPlan, PartnershipStatus
from app.models.partnership_payment import (
    PartnershipPayment,
    PaymentProvider,
    PaymentStatus,
)
from app.models.user import User, UserRole
from app.services.mpesa_service import normalize_phone_number, stk_push

PARTNERSHIP_PLANS = [
    {
        "plan": PartnershipPlan.FREE,
        "label": "Free Reader",
        "description": "Basic access to public content.",
        "recommended_for": "New readers exploring the platform.",
        "price_kes": 0,
        "duration_days": 0,
        "allows_premium_content": False,
    },
    {
        "plan": PartnershipPlan.MONTHLY_PARTNER,
        "label": "Monthly Partner",
        "description": "Monthly support for writers, education, and community content.",
        "recommended_for": "Regular readers and supporters.",
        "price_kes": 300,
        "duration_days": 30,
        "allows_premium_content": True,
    },
    {
        "plan": PartnershipPlan.ANNUAL_PARTNER,
        "label": "Annual Partner",
        "description": "Yearly access and long-term support for the ecosystem.",
        "recommended_for": "Committed community members.",
        "price_kes": 3000,
        "duration_days": 365,
        "allows_premium_content": True,
    },
    {
        "plan": PartnershipPlan.STUDENT_PARTNER,
        "label": "Student Partner",
        "description": "Discounted learning-focused partnership.",
        "recommended_for": "Students.",
        "price_kes": 150,
        "duration_days": 30,
        "allows_premium_content": True,
    },
    {
        "plan": PartnershipPlan.TEACHER_PARTNER,
        "label": "Teacher Partner",
        "description": "Discounted access for teachers and education contributors.",
        "recommended_for": "Teachers and tutors.",
        "price_kes": 200,
        "duration_days": 30,
        "allows_premium_content": True,
    },
]

PLAN_LOOKUP = {item["plan"]: item for item in PARTNERSHIP_PLANS}

# Plans that require the purchasing user to hold a specific role. Enforced
# server-side in start_partnership_checkout below.
#
# HARDENING: previously ANY authenticated user could pass
# plan=STUDENT_PARTNER or plan=TEACHER_PARTNER and pay the discounted rate
# regardless of whether they were actually a student or teacher -- a
# direct revenue leak (every reader could self-serve a 50% discount).
ROLE_RESTRICTED_PLANS: dict[PartnershipPlan, UserRole] = {
    PartnershipPlan.STUDENT_PARTNER: UserRole.STUDENT,
    PartnershipPlan.TEACHER_PARTNER: UserRole.TEACHER,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_partnership_plans() -> list[dict]:
    return PARTNERSHIP_PLANS


def get_plan_meta(plan: PartnershipPlan) -> dict:
    meta = PLAN_LOOKUP.get(plan)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid partnership plan.",
        )
    return meta


def ensure_plan_eligibility(user: User, plan: PartnershipPlan) -> None:
    """Raise 403 if `user` isn't eligible for a role-restricted discount plan.

    Admin-tier accounts are exempt so support staff can test the checkout
    flow, but this is not a way for ordinary users to bypass the check.
    """
    from app.core.permissions import is_admin_tier

    required_role = ROLE_RESTRICTED_PLANS.get(plan)
    if required_role is None:
        return

    if user.role == required_role or is_admin_tier(user.role):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"The {plan.value} plan is only available to {required_role.value.lower()} accounts.",
    )


def get_active_partnership(db: Session, user_id: str) -> Partnership | None:
    now = _now()
    return db.scalars(
        select(Partnership).where(
            Partnership.user_id == user_id,
            Partnership.status == PartnershipStatus.ACTIVE,
            Partnership.expires_at > now,
        )
    ).first()


def user_has_active_partnership(db: Session, user: User | None) -> bool:
    if not user:
        return False
    return get_active_partnership(db, user.id) is not None


def get_my_partnership_access(db: Session, user: User):
    active = get_active_partnership(db, user.id)

    if not active:
        return {
            "has_active_partnership": False,
            "active_plan": None,
            "expires_at": None,
        }

    return {
        "has_active_partnership": True,
        "active_plan": active.plan,
        "expires_at": active.expires_at,
    }


def cancel_my_partnership(db: Session, user: User) -> Partnership:
    active = get_active_partnership(db, user.id)

    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active partnership was found.",
        )

    active.status = PartnershipStatus.CANCELLED
    db.add(active)
    db.commit()
    db.refresh(active)
    return active


def get_latest_payment_for_user(db: Session, user: User) -> PartnershipPayment | None:
    return db.scalars(
        select(PartnershipPayment)
        .where(PartnershipPayment.user_id == user.id)
        .order_by(PartnershipPayment.created_at.desc())
    ).first()


def _get_or_create_pending_partnership(
    db: Session,
    user: User,
    plan: PartnershipPlan,
    referral_creator_id: str | None = None,
) -> Partnership:
    pending = db.scalars(
        select(Partnership).where(
            Partnership.user_id == user.id,
            Partnership.plan == plan,
            Partnership.status == PartnershipStatus.PENDING,
        )
    ).first()

    if pending:
        return pending

    partnership = Partnership(
        user_id=user.id,
        plan=plan,
        status=PartnershipStatus.PENDING,
        referral_creator_id=referral_creator_id,
    )
    db.add(partnership)
    db.commit()
    db.refresh(partnership)
    return partnership


async def start_partnership_checkout(
    db: Session,
    user: User,
    plan: PartnershipPlan,
    phone_number: str,
    referral_creator_id: str | None = None,
) -> dict:
    meta = get_plan_meta(plan)

    # HARDENING: closes the student/teacher discount leak described above.
    ensure_plan_eligibility(user, plan)

    if plan == PartnershipPlan.FREE:
        partnership = Partnership(
            user_id=user.id,
            plan=plan,
            status=PartnershipStatus.ACTIVE,
            started_at=_now(),
            expires_at=None,
            referral_creator_id=referral_creator_id,
        )
        db.add(partnership)
        db.commit()
        db.refresh(partnership)

        return {
            "partnership": partnership,
            "payment": None,
            "message": "Free access activated.",
        }

    normalized_phone = normalize_phone_number(phone_number)
    if len(normalized_phone) != 12 or not normalized_phone.startswith("254"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid Kenyan phone number.",
        )

    partnership = _get_or_create_pending_partnership(
        db=db,
        user=user,
        plan=plan,
        referral_creator_id=referral_creator_id,
    )

    payment = PartnershipPayment(
        partnership_id=partnership.id,
        user_id=user.id,
        provider=PaymentProvider.MPESA,
        status=PaymentStatus.INITIATED,
        plan=plan.value,
        amount=int(meta["price_kes"]),
        currency="KES",
        phone_number=normalized_phone,
        requested_at=_now(),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    settings = get_settings()

    if settings.payment_mode.lower() != "mpesa":
        payment.status = PaymentStatus.PENDING
        payment.raw_request = {
            "mode": "stub",
            "message": "M-Pesa checkout disabled until production shortcode is acquired.",
        }
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "partnership": partnership,
            "payment": payment,
            "message": "Checkout recorded. M-Pesa is temporarily disabled in this environment.",
        }

    stk_response = await stk_push(
        phone_number=normalized_phone,
        amount=int(meta["price_kes"]),
        account_reference=settings.mpesa_account_reference,
        transaction_desc=settings.mpesa_transaction_desc,
    )

    payment.status = PaymentStatus.PENDING
    payment.merchant_request_id = stk_response.get("MerchantRequestID")
    payment.checkout_request_id = stk_response.get("CheckoutRequestID")
    payment.raw_request = stk_response

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "partnership": partnership,
        "payment": payment,
        "message": "STK push sent. Complete payment on your phone.",
    }


def activate_partnership_from_payment(
    db: Session,
    payment: PartnershipPayment,
) -> Partnership:
    partnership = db.get(Partnership, payment.partnership_id)
    if not partnership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partnership was not found.",
        )

    meta = get_plan_meta(PartnershipPlan(partnership.plan))
    duration_days = int(meta["duration_days"])

    partnership.status = PartnershipStatus.ACTIVE
    partnership.started_at = _now()
    partnership.expires_at = (
        partnership.started_at + timedelta(days=duration_days) if duration_days > 0 else None
    )

    db.add(partnership)
    db.commit()
    db.refresh(partnership)

    # Monetization hook: reward the referring creator, if any. See
    # services/monetization_service.py -- this turns the previously-dead
    # `referral_creator_id` field into an actual creator incentive.
    from app.services.monetization_service import credit_referral_commission

    credit_referral_commission(db, payment=payment, partnership=partnership)

    return partnership


def admin_activate_partnership(
    db: Session,
    partnership_id: str,
    months: int = 1,
) -> Partnership:
    """
    Manually activate (or extend) a partnership as an admin action --
    e.g. for an off-platform payment (bank transfer, cash at an event).

    NOTE: this function was referenced by routers/partnerships.py but was
    never actually implemented in the original codebase -- calling that
    endpoint would have raised an ImportError/AttributeError at request
    time. Implemented here to match the router's existing contract.
    """
    partnership = db.get(Partnership, partnership_id)
    if not partnership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partnership was not found.",
        )

    if months < 1 or months > 24:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Months must be between 1 and 24.",
        )

    now = _now()
    # Extend from the current expiry if it's still in the future, otherwise
    # from now -- avoids losing remaining paid time on a re-activation.
    base = partnership.expires_at if (partnership.expires_at and partnership.expires_at > now) else now

    partnership.status = PartnershipStatus.ACTIVE
    if not partnership.started_at:
        partnership.started_at = now
    partnership.expires_at = base + timedelta(days=30 * months)

    db.add(partnership)
    db.commit()
    db.refresh(partnership)
    return partnership


def handle_mpesa_callback(db: Session, payload: dict) -> PartnershipPayment | None:
    """
    Process a Daraja STK push callback.

    Caller (routers/partnerships.py) is responsible for verifying the
    callback secret path segment BEFORE calling this function -- that check
    happens at the router boundary so this function stays focused on
    payment-state logic and stays easy to unit test without HTTP concerns.
    """
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = callback.get("CheckoutRequestID")
    if not checkout_request_id:
        return None

    payment = db.scalars(
        select(PartnershipPayment).where(
            PartnershipPayment.checkout_request_id == checkout_request_id
        )
    ).first()

    if not payment:
        return None

    # Idempotency: ignore duplicate callbacks for an already-finalized payment.
    if payment.status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.CANCELLED):
        payment.raw_callback = payload
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    result_code = str(callback.get("ResultCode"))
    result_desc = callback.get("ResultDesc")

    payment.raw_callback = payload
    payment.result_code = result_code
    payment.result_desc = result_desc

    items = callback.get("CallbackMetadata", {}).get("Item", [])
    data = {item.get("Name"): item.get("Value") for item in items if isinstance(item, dict)}

    try:
        if result_code == "0":
            # HARDENING: cross-check the amount M-Pesa says was paid against
            # what we expected to charge for this plan. Without this, a
            # callback reporting success with a mismatched (e.g. lower)
            # amount would still activate full access.
            paid_amount = data.get("Amount")
            if paid_amount is not None and int(paid_amount) < payment.amount:
                payment.status = PaymentStatus.FAILED
                payment.result_desc = (
                    f"Amount mismatch: expected {payment.amount}, received {paid_amount}."
                )
                payment.failed_at = _now()

                partnership = db.get(Partnership, payment.partnership_id)
                if partnership and partnership.status == PartnershipStatus.PENDING:
                    partnership.status = PartnershipStatus.CANCELLED
                    db.add(partnership)

                db.add(payment)
                db.commit()
                db.refresh(payment)
                return payment

            payment.status = PaymentStatus.SUCCESS
            payment.mpesa_receipt_number = data.get("MpesaReceiptNumber")
            payment.paid_at = _now()

            partnership = activate_partnership_from_payment(db, payment)
            db.add(partnership)
        else:
            payment.status = PaymentStatus.FAILED
            payment.failed_at = _now()

            partnership = db.get(Partnership, payment.partnership_id)
            if partnership and partnership.status == PartnershipStatus.PENDING:
                partnership.status = PartnershipStatus.CANCELLED
                db.add(partnership)

        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    except Exception:
        db.rollback()
        raise

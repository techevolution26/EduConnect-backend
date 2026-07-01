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
from app.models.user import User
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


# async def start_partnership_checkout(
#     db: Session,
#     user: User,
#     plan: PartnershipPlan,
#     phone_number: str,
#     referral_creator_id: str | None = None,
# ) -> dict:
#     meta = get_plan_meta(plan)

#     if plan == PartnershipPlan.FREE:
#         partnership = Partnership(
#             user_id=user.id,
#             plan=plan,
#             status=PartnershipStatus.ACTIVE,
#             started_at=_now(),
#             expires_at=None,
#             referral_creator_id=referral_creator_id,
#         )
#         db.add(partnership)
#         db.commit()
#         db.refresh(partnership)

#         return {
#             "partnership": partnership,
#             "payment": None,
#             "message": "Free access activated.",
#         }

#     normalized_phone = normalize_phone_number(phone_number)
#     if len(normalized_phone) != 12 or not normalized_phone.startswith("254"):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Enter a valid Kenyan phone number.",
#         )

#     partnership = _get_or_create_pending_partnership(
#         db=db,
#         user=user,
#         plan=plan,
#         referral_creator_id=referral_creator_id,
#     )

#     payment = PartnershipPayment(
#         partnership_id=partnership.id,
#         user_id=user.id,
#         provider=PaymentProvider.MPESA,
#         status=PaymentStatus.INITIATED,
#         plan=plan.value,
#         amount=int(meta["price_kes"]),
#         currency="KES",
#         phone_number=normalized_phone,
#         requested_at=_now(),
#     )
#     db.add(payment)
#     db.commit()
#     db.refresh(payment)

#     stk_response = await stk_push(
#         phone_number=normalized_phone,
#         amount=int(meta["price_kes"]),
#         account_reference=get_settings().mpesa_account_reference,
#         transaction_desc=get_settings().mpesa_transaction_desc,
#     )

#     payment.status = PaymentStatus.PENDING
#     payment.merchant_request_id = stk_response.get("MerchantRequestID")
#     payment.checkout_request_id = stk_response.get("CheckoutRequestID")
#     payment.raw_request = stk_response

#     db.add(payment)
#     db.commit()
#     db.refresh(payment)

#     return {
#         "partnership": partnership,
#         "payment": payment,
#         "message": "STK push sent. Complete payment on your phone.",
#     }




async def start_partnership_checkout(
    db: Session,
    user: User,
    plan: PartnershipPlan,
    phone_number: str,
    referral_creator_id: str | None = None,
) -> dict:
    meta = get_plan_meta(plan)

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
        account_reference=get_settings().mpesa_account_reference,
        transaction_desc=get_settings().mpesa_transaction_desc,
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
    return partnership


def handle_mpesa_callback(db: Session, payload: dict) -> PartnershipPayment | None:
    # Ensure we handle idempotent callbacks and atomic updates
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = callback.get("CheckoutRequestID")
    if not checkout_request_id:
        return None

    # Lock/lookup payment
    payment = db.scalars(
        select(PartnershipPayment).where(
            PartnershipPayment.checkout_request_id == checkout_request_id
        )
    ).first()

    if not payment:
        return None

    # If payment already finalized, ignore duplicate callback
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
        # On any error during processing, roll back to avoid partial state
        db.rollback()
        raise
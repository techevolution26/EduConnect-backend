from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.monetization import ReferralEarning, ReferralEarningStatus
from app.models.partnership import Partnership
from app.models.partnership_payment import PartnershipPayment
from app.models.user import User

# 10% of the payment amount goes to the referring creator. Expressed in
# basis points (1000 = 10.00%) so it's stored precisely as an integer
# alongside the earning record rather than a float that could drift.
REFERRAL_COMMISSION_RATE_BPS = 1000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def credit_referral_commission(
    db: Session,
    payment: PartnershipPayment,
    partnership: Partnership,
) -> ReferralEarning | None:
    """
    Credit the referring creator's commission ledger after a successful
    payment. No-op if the partnership has no referral_creator_id, if the
    payment amount is zero (FREE plan), or if this payment was already
    credited (idempotency guard -- callbacks can be re-delivered).
    """
    if not partnership.referral_creator_id:
        return None

    if payment.amount <= 0:
        return None

    existing = db.scalars(
        select(ReferralEarning).where(
            ReferralEarning.partnership_payment_id == payment.id
        )
    ).first()
    if existing:
        return existing

    commission_amount = (payment.amount * REFERRAL_COMMISSION_RATE_BPS) // 10_000

    if commission_amount <= 0:
        return None

    earning = ReferralEarning(
        referrer_id=partnership.referral_creator_id,
        partnership_id=partnership.id,
        partnership_payment_id=payment.id,
        source_amount_kes=payment.amount,
        commission_rate_bps=REFERRAL_COMMISSION_RATE_BPS,
        commission_amount_kes=commission_amount,
        status=ReferralEarningStatus.PENDING,
    )
    db.add(earning)
    db.commit()
    db.refresh(earning)
    return earning


def get_my_referral_summary(db: Session, user: User) -> dict:
    pending = db.scalar(
        select(func.coalesce(func.sum(ReferralEarning.commission_amount_kes), 0)).where(
            ReferralEarning.referrer_id == user.id,
            ReferralEarning.status == ReferralEarningStatus.PENDING,
        )
    ) or 0

    paid = db.scalar(
        select(func.coalesce(func.sum(ReferralEarning.commission_amount_kes), 0)).where(
            ReferralEarning.referrer_id == user.id,
            ReferralEarning.status == ReferralEarningStatus.PAID,
        )
    ) or 0

    referral_count = db.scalar(
        select(func.count()).select_from(ReferralEarning).where(
            ReferralEarning.referrer_id == user.id,
        )
    ) or 0

    return {
        "pending_kes": int(pending),
        "paid_kes": int(paid),
        "total_referrals": int(referral_count),
    }


def list_my_referral_earnings(db: Session, user: User) -> list[ReferralEarning]:
    return list(
        db.scalars(
            select(ReferralEarning)
            .where(ReferralEarning.referrer_id == user.id)
            .order_by(ReferralEarning.created_at.desc())
        ).all()
    )


def list_pending_payouts(db: Session, skip: int = 0, limit: int = 50) -> tuple[list[ReferralEarning], int]:
    statement = (
        select(ReferralEarning)
        .where(ReferralEarning.status == ReferralEarningStatus.PENDING)
        .order_by(ReferralEarning.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    count_statement = select(func.count()).select_from(ReferralEarning).where(
        ReferralEarning.status == ReferralEarningStatus.PENDING
    )

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0
    return items, total


def mark_earning_paid(db: Session, earning_id: str) -> ReferralEarning:
    earning = db.get(ReferralEarning, earning_id)
    if not earning:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral earning was not found.")

    if earning.status != ReferralEarningStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Earning is already {earning.status.value.lower()}.",
        )

    earning.status = ReferralEarningStatus.PAID
    db.add(earning)
    db.commit()
    db.refresh(earning)
    return earning

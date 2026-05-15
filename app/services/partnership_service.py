from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.partnership import Partnership, PartnershipPlan, PartnershipStatus
from app.models.user import User


PARTNERSHIP_PLANS = [
    {
        "plan": PartnershipPlan.FREE,
        "label": "Free Reader",
        "description": "Basic access to free public content.",
        "recommended_for": "New readers exploring the platform.",
    },
    {
        "plan": PartnershipPlan.MONTHLY_PARTNER,
        "label": "Monthly Partner",
        "description": "Monthly support for writers, education, and community content.",
        "recommended_for": "Regular readers and supporters.",
    },
    {
        "plan": PartnershipPlan.ANNUAL_PARTNER,
        "label": "Annual Partner",
        "description": "Yearly access and long-term support for the ecosystem.",
        "recommended_for": "Committed community members.",
    },
    {
        "plan": PartnershipPlan.STUDENT_PARTNER,
        "label": "Student Partner",
        "description": "Discounted learning-focused partnership.",
        "recommended_for": "Students.",
    },
    {
        "plan": PartnershipPlan.TEACHER_PARTNER,
        "label": "Teacher Partner",
        "description": "Discounted access for teachers and education contributors.",
        "recommended_for": "Teachers and tutors.",
    },
]


def list_partnership_plans() -> list[dict]:
    return PARTNERSHIP_PLANS


def get_active_partnership(db: Session, user_id: str) -> Partnership | None:
    now = datetime.now(timezone.utc)

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

    active = get_active_partnership(db, user.id)
    return active is not None


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


def start_partnership(
    db: Session,
    user: User,
    plan: PartnershipPlan,
    referral_creator_id: str | None = None,
) -> Partnership:
    if plan == PartnershipPlan.FREE:
        status_value = PartnershipStatus.ACTIVE
        started_at = datetime.now(timezone.utc)
        expires_at = started_at + timedelta(days=30)
    else:
        status_value = PartnershipStatus.PENDING
        started_at = None
        expires_at = None

    partnership = Partnership(
        user_id=user.id,
        plan=plan,
        status=status_value,
        referral_creator_id=referral_creator_id,
        started_at=started_at,
        expires_at=expires_at,
    )

    db.add(partnership)
    db.commit()
    db.refresh(partnership)

    return partnership


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


def admin_activate_partnership(
    db: Session,
    partnership_id: str,
    months: int,
) -> Partnership:
    partnership = db.get(Partnership, partnership_id)

    if not partnership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partnership was not found.",
        )

    now = datetime.now(timezone.utc)

    partnership.status = PartnershipStatus.ACTIVE
    partnership.started_at = now
    partnership.expires_at = now + timedelta(days=30 * months)

    db.add(partnership)
    db.commit()
    db.refresh(partnership)

    return partnership
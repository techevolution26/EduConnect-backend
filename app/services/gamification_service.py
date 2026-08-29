from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event import EventParticipant, ParticipationStatus
from app.models.gamification import Badge, UserBadge, XPLedgerEntry
from app.models.user import User

# Centralised XP rules -- see routers/events.py and services/event_service.py
# for where each of these fires. Keeping the amounts here (not scattered
# across endpoints) means a rebalance is a one-line change.
XP_RULES: dict[str, int] = {
    "event_rsvp": 5,
    "event_attended": 20,
    "event_submitted": 50,
    "event_completed": 30,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def award_xp(
    db: Session,
    user_id: str,
    source_type: str,
    source_id: str | None = None,
    *,
    override_amount: int | None = None,
    note: str | None = None,
) -> XPLedgerEntry:
    amount = override_amount if override_amount is not None else XP_RULES.get(source_type, 0)

    entry = XPLedgerEntry(
        user_id=user_id,
        amount=amount,
        source_type=source_type,
        source_id=source_id,
        note=note,
        earned_at=_now(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Badge conditions are re-checked after every grant. This runs inline
    # (not as a background task) to keep the initial implementation simple;
    # the condition set below is cheap (a couple of COUNT queries), so this
    # is fine at current scale. If badge conditions grow more numerous or
    # expensive, move this to a background task queue.
    check_and_award_badges(db, user_id)

    return entry


def get_user_total_xp(db: Session, user_id: str) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(XPLedgerEntry.amount), 0)).where(
            XPLedgerEntry.user_id == user_id
        )
    )
    return int(total or 0)


def get_leaderboard(
    db: Session,
    *,
    period: str = "all_time",
    school_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Returns [{user_id, total_xp}, ...] ordered by XP descending.

    `period`: "all_time" or "month" (rolling 30 days, kept simple rather
    than calendar-month bucketing for a first version).
    `school_id`: filter to students affiliated with a given school (joins
    through StudentProfile) -- powers the "school ranking" surface.
    """
    from app.models.student import StudentProfile  # local import avoids a cycle at module load

    query = select(
        XPLedgerEntry.user_id, func.sum(XPLedgerEntry.amount).label("total_xp")
    ).group_by(XPLedgerEntry.user_id)

    if period == "month":
        cutoff = _now() - timedelta(days=30)
        query = query.where(XPLedgerEntry.earned_at >= cutoff)

    if school_id:
        query = query.join(StudentProfile, StudentProfile.user_id == XPLedgerEntry.user_id).where(
            StudentProfile.school_id == school_id
        )

    query = query.order_by(func.sum(XPLedgerEntry.amount).desc()).limit(limit)

    rows = db.execute(query).all()
    return [{"user_id": row.user_id, "total_xp": int(row.total_xp)} for row in rows]


def get_user_rank(db: Session, user_id: str, *, school_id: str | None = None) -> int | None:
    """1-indexed rank of a user on the (optionally school-scoped) all-time
    leaderboard, or None if they have no XP yet."""
    board = get_leaderboard(db, period="all_time", school_id=school_id, limit=100_000)
    for index, row in enumerate(board, start=1):
        if row["user_id"] == user_id:
            return index
    return None


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

def _user_already_has_badge(db: Session, user_id: str, badge_id: str) -> bool:
    return (
        db.scalars(
            select(UserBadge).where(UserBadge.user_id == user_id, UserBadge.badge_id == badge_id)
        ).first()
        is not None
    )


def _count_events_attended(db: Session, user_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(EventParticipant)
            .where(
                EventParticipant.user_id == user_id,
                EventParticipant.status.in_(
                    [ParticipationStatus.ATTENDED, ParticipationStatus.COMPLETED]
                ),
            )
        )
        or 0
    )


def _condition_met(db: Session, user_id: str, condition: dict) -> bool:
    """Small, explicit set of supported condition types -- see
    models/gamification.py::Badge.condition for the shape."""
    condition_type = condition.get("type")
    threshold = condition.get("threshold", 0)

    if condition_type == "events_attended":
        return _count_events_attended(db, user_id) >= threshold

    if condition_type == "total_xp":
        return get_user_total_xp(db, user_id) >= threshold

    return False


def check_and_award_badges(db: Session, user_id: str) -> list[UserBadge]:
    badges = db.scalars(select(Badge)).all()
    newly_awarded: list[UserBadge] = []

    for badge in badges:
        if _user_already_has_badge(db, user_id, badge.id):
            continue

        if _condition_met(db, user_id, badge.condition):
            award = UserBadge(user_id=user_id, badge_id=badge.id, awarded_at=_now())
            db.add(award)
            db.commit()
            db.refresh(award)
            newly_awarded.append(award)

            if badge.xp_reward:
                # Direct ledger insert (not a recursive award_xp call) to
                # avoid re-triggering badge checks mid-check-and-award pass.
                db.add(
                    XPLedgerEntry(
                        user_id=user_id,
                        amount=badge.xp_reward,
                        source_type="badge",
                        source_id=badge.id,
                        note=f"Badge earned: {badge.name}",
                        earned_at=_now(),
                    )
                )
                db.commit()

    return newly_awarded


def list_user_badges(db: Session, user_id: str) -> list[UserBadge]:
    return list(
        db.scalars(
            select(UserBadge).where(UserBadge.user_id == user_id).order_by(UserBadge.awarded_at.desc())
        ).all()
    )

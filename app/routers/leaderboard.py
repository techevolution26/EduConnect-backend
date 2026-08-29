from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.gamification import (
    BadgeRead,
    LeaderboardEntry,
    LeaderboardResponse,
    MyXPRead,
    UserBadgeRead,
)
from app.services.gamification_service import (
    get_leaderboard,
    get_user_rank,
    get_user_total_xp,
    list_user_badges,
)
from app.services.student_service import get_my_profile

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard_endpoint(
    db: Annotated[Session, Depends(get_db)],
    period: Literal["all_time", "month"] = "all_time",
    school_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> LeaderboardResponse:
    rows = get_leaderboard(db, period=period, school_id=school_id, limit=limit)

    if not rows:
        return LeaderboardResponse(period=period, school_id=school_id, entries=[])

    user_ids = [row["user_id"] for row in rows]
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()}

    entries = [
        LeaderboardEntry(
            user_id=row["user_id"],
            full_name=users[row["user_id"]].full_name if row["user_id"] in users else None,
            total_xp=row["total_xp"],
            rank=index,
        )
        for index, row in enumerate(rows, start=1)
    ]

    return LeaderboardResponse(period=period, school_id=school_id, entries=entries)


@router.get("/me", response_model=MyXPRead)
def get_my_xp(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MyXPRead:
    total_xp = get_user_total_xp(db, current_user.id)
    rank = get_user_rank(db, current_user.id)

    profile = get_my_profile(db, current_user)
    school_rank = (
        get_user_rank(db, current_user.id, school_id=profile.school_id)
        if profile and profile.school_id
        else None
    )

    return MyXPRead(total_xp=total_xp, rank=rank, school_rank=school_rank)


@router.get("/badges", response_model=list[BadgeRead])
def get_all_badges(db: Annotated[Session, Depends(get_db)]) -> list[BadgeRead]:
    from app.models.gamification import Badge

    return list(db.scalars(select(Badge)).all())


@router.get("/me/badges", response_model=list[UserBadgeRead])
def get_my_badges(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserBadgeRead]:
    return list_user_badges(db, current_user.id)

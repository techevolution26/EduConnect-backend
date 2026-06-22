from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.read_session import ContentReadSession
from app.models.user import User


QUALIFIED_SCROLL_THRESHOLD = 70
QUALIFIED_TIME_RATIO = 0.65
VIEW_COOLDOWN_HOURS = 24

def _should_count_view(
    db: Session,
    content_id: str,
    user_id: str,
    now: datetime,
) -> bool:
    cutoff = now - timedelta(hours=VIEW_COOLDOWN_HOURS)

    recent_session = db.scalars(
        select(ContentReadSession).where(
            ContentReadSession.content_id == content_id,
            ContentReadSession.user_id == user_id,
            ContentReadSession.started_at >= cutoff,
        )
    ).first()

    return recent_session is None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_published_content_or_404(db: Session, content_id: str) -> Content:
    content = db.get(Content, content_id)
    if not content or content.status != ContentStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published content was not found.",
        )
    return content


def start_read_session(db: Session, content_id: str, user: User) -> ContentReadSession:
    content = get_published_content_or_404(db, content_id)

    existing = db.scalars(
        select(ContentReadSession).where(
            ContentReadSession.content_id == content_id,
            ContentReadSession.user_id == user.id,
            ContentReadSession.is_completed == False,  # noqa: E712
        )
    ).first()

    now = _now()

    if existing:
        existing.last_active_at = now
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    if _should_count_view(db, content_id, user.id, now):
        content.views_count = (content.views_count or 0) + 1
        db.add(content)

    session = ContentReadSession(
        content_id=content_id,
        user_id=user.id,
        started_at=now,
        last_active_at=now,
        ended_at=None,
        active_seconds=0,
        max_scroll_percent=0,
        tab_visible=True,
        is_completed=False,
        is_qualified=False,
    )

    db.add(session)
    db.commit()
    db.refresh(content)
    db.refresh(session)
    return session


def heartbeat_read_session(
    db: Session,
    session_id: str,
    user: User,
    active_seconds_delta: int = 0,
    scroll_percent: int = 0,
    tab_visible: bool = True,
) -> ContentReadSession:
    session = db.get(ContentReadSession, session_id)

    if not session or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Read session was not found.",
        )

    now = _now()

    session.last_active_at = now
    session.active_seconds = max(0, session.active_seconds + max(0, active_seconds_delta))
    session.max_scroll_percent = max(session.max_scroll_percent, max(0, min(scroll_percent, 100)))
    session.tab_visible = tab_visible

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def finish_read_session(
    db: Session,
    session_id: str,
    user: User,
    active_seconds_delta: int = 0,
    scroll_percent: int = 0,
    tab_visible: bool = True,
) -> ContentReadSession:
    session = heartbeat_read_session(
        db=db,
        session_id=session_id,
        user=user,
        active_seconds_delta=active_seconds_delta,
        scroll_percent=scroll_percent,
        tab_visible=tab_visible,
    )

    content = db.get(Content, session.content_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    session.ended_at = _now()
    session.is_completed = True

    estimated_seconds = max(60, content.reading_time_minutes * 60)
    qualified_time = int(estimated_seconds * QUALIFIED_TIME_RATIO)

    session.is_qualified = (
        session.tab_visible
        and session.max_scroll_percent >= QUALIFIED_SCROLL_THRESHOLD
        and session.active_seconds >= qualified_time
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_my_read_sessions(db: Session, user: User, content_id: str | None = None) -> list[ContentReadSession]:
    statement = select(ContentReadSession).where(ContentReadSession.user_id == user.id)

    if content_id:
        statement = statement.where(ContentReadSession.content_id == content_id)

    return list(
        db.scalars(statement.order_by(ContentReadSession.created_at.desc())).all()
    )
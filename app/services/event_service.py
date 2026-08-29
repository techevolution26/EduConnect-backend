from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import is_admin_tier
from app.models.event import (
    Event,
    EventParticipant,
    EventStatus,
    EventType,
    ParticipationStatus,
)
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.services.gamification_service import award_xp
from app.services.partnership_service import user_has_active_partnership


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def ensure_can_host_events(user: User) -> None:
    """Who may CREATE events at all. WRITER/TEACHER can host their own
    events (workshops, book clubs, competitions) -- this is the direct
    "build creator-student relationships" lever from the goals ranking.
    Admin-tier accounts can always create events too."""
    if user.role not in {UserRole.WRITER, UserRole.TEACHER} and not is_admin_tier(
        user.role
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only writers, teachers, or admins can host events.",
        )


def ensure_event_host_or_admin(event: Event, user: User) -> None:
    if event.host_id != user.id and not is_admin_tier(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own events.",
        )


def get_event_or_404(db: Session, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event was not found."
        )
    return event


def get_event_by_slug_or_404(db: Session, slug: str) -> Event:
    event = db.scalars(select(Event).where(Event.slug == slug)).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event was not found."
        )
    return event


def create_event(
    db: Session,
    host: User,
    *,
    title: str,
    description: str | None,
    type: EventType,
    curriculum_tags: list[str],
    student_only: bool,
    school_id: str | None,
    requires_partnership: bool,
    starts_at: datetime | None,
    ends_at: datetime | None,
    max_participants: int | None,
    metadata: dict,
    cover_image_url: str | None,
) -> Event:
    ensure_can_host_events(host)

    base_slug = _slugify(title)
    slug = base_slug
    suffix = 1
    while db.scalars(select(Event).where(Event.slug == slug)).first() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    event = Event(
        title=title,
        slug=slug,
        description=description,
        type=type,
        status=EventStatus.DRAFT,
        host_id=host.id,
        curriculum_tags=curriculum_tags or [],
        student_only=student_only,
        school_id=school_id,
        requires_partnership=requires_partnership,
        starts_at=starts_at,
        ends_at=ends_at,
        max_participants=max_participants,
        metadata_json=metadata or {},
        cover_image_url=cover_image_url,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def publish_event(db: Session, event_id: str, user: User) -> Event:
    event = get_event_or_404(db, event_id)
    ensure_event_host_or_admin(event, user)

    event.status = EventStatus.PUBLISHED
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def cancel_event(db: Session, event_id: str, user: User) -> Event:
    event = get_event_or_404(db, event_id)
    ensure_event_host_or_admin(event, user)

    event.status = EventStatus.CANCELLED
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
    type: EventType | None = None,
    curriculum_tag: str | None = None,
    status_filter: EventStatus | None = None,
) -> tuple[list[Event], int]:
    filters = []

    # Default: only show published/ongoing events on the public listing,
    # unless a specific status is requested (e.g. by the host viewing drafts).
    if status_filter:
        filters.append(Event.status == status_filter)
    else:
        filters.append(Event.status.in_([EventStatus.PUBLISHED, EventStatus.ONGOING]))

    if type:
        filters.append(Event.type == type)

    statement = select(Event)
    count_statement = select(func.count()).select_from(Event)

    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)

    # curriculum_tag filtering happens in Python since JSON containment
    # queries aren't portably expressible across SQLite/MySQL/Postgres
    # with plain SQLAlchemy core -- acceptable at this table's expected
    # scale (event counts, not content-scale volume).
    items = list(
        db.scalars(
            statement.order_by(
                Event.starts_at.is_(None),
                Event.starts_at.asc(),
            )
            .offset(skip)
            .limit(limit * 3)
        ).all()
    )
    if curriculum_tag:
        items = [e for e in items if curriculum_tag in (e.curriculum_tags or [])]
    items = items[:limit]

    total = db.scalar(count_statement) or 0
    return items, total


def _ensure_student_eligible(db: Session, user: User) -> None:
    """Gate for `student_only` events. Accepts either role=STUDENT or a
    verified StudentProfile -- mirrors the same bar used for the
    STUDENT_PARTNER discount in partnership_service.py."""
    if is_admin_tier(user.role):
        return

    if user.role == UserRole.STUDENT:
        return

    profile = db.scalars(
        select(StudentProfile).where(
            StudentProfile.user_id == user.id, StudentProfile.verified.is_(True)
        )
    ).first()
    if profile:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This event is only open to verified students.",
    )


def _get_or_create_participant(
    db: Session, event: Event, user: User
) -> EventParticipant:
    participant = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
        )
    ).first()
    if participant:
        return participant

    participant = EventParticipant(
        event_id=event.id, user_id=user.id, status=ParticipationStatus.RSVP
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def rsvp_to_event(db: Session, event_id: str, user: User) -> EventParticipant:
    event = get_event_or_404(db, event_id)

    if event.status not in {EventStatus.PUBLISHED, EventStatus.ONGOING}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event is not open for RSVPs.",
        )

    if event.student_only:
        _ensure_student_eligible(db, user)

    if event.requires_partnership and not user_has_active_partnership(db, user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This event requires an active partnership to join.",
        )

    existing = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
        )
    ).first()
    if existing and existing.status != ParticipationStatus.WITHDREW:
        return existing

    if event.max_participants is not None:
        current_count = (
            db.scalar(
                select(func.count())
                .select_from(EventParticipant)
                .where(
                    EventParticipant.event_id == event.id,
                    EventParticipant.status != ParticipationStatus.WITHDREW,
                )
            )
            or 0
        )
        if current_count >= event.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="This event is full."
            )

    if existing:
        existing.status = ParticipationStatus.RSVP
        participant = existing
        db.add(participant)
        db.commit()
        db.refresh(participant)
    else:
        participant = _get_or_create_participant(db, event, user)

    xp_entry = award_xp(db, user.id, "event_rsvp", source_id=participant.id)
    participant.xp_awarded += xp_entry.amount
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def withdraw_from_event(db: Session, event_id: str, user: User) -> None:
    event = get_event_or_404(db, event_id)
    participant = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
        )
    ).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not RSVPed to this event.",
        )

    # No XP deduction on withdrawal -- keeps the ledger append-only and
    # avoids punishing a change of plans; the RSVP XP was for engaging with
    # the platform, which already happened.
    participant.status = ParticipationStatus.WITHDREW
    db.add(participant)
    db.commit()


def mark_attended(
    db: Session, event_id: str, user_id: str, marking_user: User
) -> EventParticipant:
    event = get_event_or_404(db, event_id)
    ensure_event_host_or_admin(event, marking_user)

    participant = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user_id
        )
    ).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This user has not RSVPed."
        )

    if participant.status == ParticipationStatus.ATTENDED:
        return participant

    participant.status = ParticipationStatus.ATTENDED
    xp_entry = award_xp(db, user_id, "event_attended", source_id=participant.id)
    participant.xp_awarded += xp_entry.amount

    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def submit_to_event(
    db: Session, event_id: str, user: User, submission: dict
) -> EventParticipant:
    event = get_event_or_404(db, event_id)

    if event.type != EventType.COMPETITION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only competitions accept submissions.",
        )

    participant = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
        )
    ).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RSVP to this event before submitting.",
        )

    already_submitted = participant.status == ParticipationStatus.SUBMITTED
    participant.status = ParticipationStatus.SUBMITTED
    participant.submission = submission

    if not already_submitted:
        xp_entry = award_xp(db, user.id, "event_submitted", source_id=participant.id)
        participant.xp_awarded += xp_entry.amount

    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def mark_completed(
    db: Session, event_id: str, user_id: str, marking_user: User
) -> EventParticipant:
    """Workshops/book clubs: host marks a participant as having completed
    the event (finished the reading, attended all sessions, etc.)."""
    event = get_event_or_404(db, event_id)
    ensure_event_host_or_admin(event, marking_user)

    participant = db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user_id
        )
    ).first()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This user has not RSVPed."
        )

    if participant.status == ParticipationStatus.COMPLETED:
        return participant

    participant.status = ParticipationStatus.COMPLETED
    xp_entry = award_xp(db, user_id, "event_completed", source_id=participant.id)
    participant.xp_awarded += xp_entry.amount

    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def list_event_participants(db: Session, event_id: str) -> list[EventParticipant]:
    return list(
        db.scalars(
            select(EventParticipant)
            .where(EventParticipant.event_id == event_id)
            .order_by(EventParticipant.created_at.asc())
        ).all()
    )


def get_my_participation(
    db: Session, event_id: str, user: User
) -> EventParticipant | None:
    return db.scalars(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id, EventParticipant.user_id == user.id
        )
    ).first()

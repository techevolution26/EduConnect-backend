from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role_or_permission
from app.core.permissions import Permission
from app.models.event import EventStatus, EventType
from app.models.user import User, UserRole
from app.schemas.event import (
    EventCreate,
    EventDetailRead,
    EventListResponse,
    EventParticipantRead,
    EventRead,
    EventSubmissionCreate,
)
from app.services.event_service import (
    cancel_event,
    create_event,
    get_event_by_slug_or_404,
    get_event_or_404,
    get_my_participation,
    list_event_participants,
    list_events,
    mark_attended,
    mark_completed,
    publish_event,
    rsvp_to_event,
    submit_to_event,
    withdraw_from_event,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=EventListResponse)
def get_events(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    type: EventType | None = None,
    curriculum_tag: str | None = None,
) -> EventListResponse:
    items, total = list_events(db=db, skip=skip, limit=limit, type=type, curriculum_tag=curriculum_tag)
    return EventListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/mine", response_model=EventListResponse)
def get_my_hosted_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: EventStatus | None = None,
) -> EventListResponse:
    from sqlalchemy import func, select

    from app.models.event import Event

    filters = [Event.host_id == current_user.id]
    if status_filter:
        filters.append(Event.status == status_filter)

    statement = select(Event)
    count_statement = select(func.count()).select_from(Event)
    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)

    items = list(db.scalars(statement.order_by(Event.created_at.desc()).offset(skip).limit(limit)).all())
    total = db.scalar(count_statement) or 0
    return EventListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{slug}", response_model=EventDetailRead)
def get_event_detail(slug: str, db: Annotated[Session, Depends(get_db)]) -> EventDetailRead:
    return get_event_by_slug_or_404(db, slug)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_new_event(
    payload: EventCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    # Role check (WRITER/TEACHER/admin-tier) happens inside create_event ->
    # ensure_can_host_events, keeping the "who can host" rule in one place.
    return create_event(
        db=db,
        host=current_user,
        title=payload.title,
        description=payload.description,
        type=payload.type,
        curriculum_tags=payload.curriculum_tags,
        student_only=payload.student_only,
        school_id=payload.school_id,
        requires_partnership=payload.requires_partnership,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        max_participants=payload.max_participants,
        metadata=payload.metadata,
        cover_image_url=payload.cover_image_url,
    )


@router.post("/{event_id}/publish", response_model=EventRead)
def publish_existing_event(
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    return publish_event(db, event_id, current_user)


@router.post("/{event_id}/cancel", response_model=EventRead)
def cancel_existing_event(
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventRead:
    return cancel_event(db, event_id, current_user)


# ---------------------------------------------------------------------------
# Participation lifecycle
# ---------------------------------------------------------------------------

@router.post("/{event_id}/rsvp", response_model=EventParticipantRead)
def rsvp(
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventParticipantRead:
    return rsvp_to_event(db, event_id, current_user)


@router.delete("/{event_id}/rsvp", status_code=status.HTTP_204_NO_CONTENT)
def withdraw(
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    withdraw_from_event(db, event_id, current_user)


@router.get("/{event_id}/me", response_model=EventParticipantRead | None)
def get_my_event_participation(
    event_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return get_my_participation(db, event_id, current_user)


@router.post("/{event_id}/submit", response_model=EventParticipantRead)
def submit_competition_entry(
    event_id: str,
    payload: EventSubmissionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventParticipantRead:
    return submit_to_event(db, event_id, current_user, payload.model_dump(exclude_none=True))


@router.get("/{event_id}/participants", response_model=list[EventParticipantRead])
def get_event_participants(
    event_id: str,
    current_user: Annotated[
        User, Depends(require_role_or_permission(UserRole.MODERATOR, Permission.EVENTS_MODERATE))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[EventParticipantRead]:
    # NOTE: reachable by MODERATOR/EVENTS_MODERATE rather than requiring
    # event ownership. A host who is neither an admin nor a moderator
    # currently manages their roster via the attend/complete endpoints
    # below rather than a full participant listing -- a host-scoped
    # listing endpoint is a natural next addition if needed.
    get_event_or_404(db, event_id)
    return list_event_participants(db, event_id)


@router.post("/{event_id}/participants/{user_id}/attend", response_model=EventParticipantRead)
def mark_participant_attended(
    event_id: str,
    user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventParticipantRead:
    # Ownership (host or admin) enforced inside mark_attended.
    return mark_attended(db, event_id, user_id, current_user)


@router.post("/{event_id}/participants/{user_id}/complete", response_model=EventParticipantRead)
def mark_participant_completed(
    event_id: str,
    user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventParticipantRead:
    return mark_completed(db, event_id, user_id, current_user)

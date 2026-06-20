from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.read_session import (
    ReadSessionFinish,
    ReadSessionHeartbeat,
    ReadSessionRead,
    ReadSessionStart,
)
from app.services.read_session import (
    finish_read_session,
    get_my_read_sessions,
    heartbeat_read_session,
    start_read_session,
)

router = APIRouter(prefix="/read-sessions", tags=["Read Sessions"])


@router.post("/start", response_model=ReadSessionRead)
def start_session(
    payload: ReadSessionStart,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReadSessionRead:
    return start_read_session(db=db, content_id=payload.content_id, user=current_user)


@router.patch("/{session_id}/heartbeat", response_model=ReadSessionRead)
def heartbeat_session(
    session_id: str,
    payload: ReadSessionHeartbeat,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReadSessionRead:
    return heartbeat_read_session(
        db=db,
        session_id=session_id,
        user=current_user,
        active_seconds_delta=payload.active_seconds_delta,
        scroll_percent=payload.scroll_percent,
        tab_visible=payload.tab_visible,
    )


@router.post("/{session_id}/finish", response_model=ReadSessionRead)
def finish_session(
    session_id: str,
    payload: ReadSessionFinish,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReadSessionRead:
    return finish_read_session(
        db=db,
        session_id=session_id,
        user=current_user,
        active_seconds_delta=payload.active_seconds_delta,
        scroll_percent=payload.scroll_percent,
        tab_visible=payload.tab_visible,
    )


@router.get("/me", response_model=list[ReadSessionRead])
def my_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    content_id: str | None = None,
) -> list[ReadSessionRead]:
    return get_my_read_sessions(db=db, user=current_user, content_id=content_id)
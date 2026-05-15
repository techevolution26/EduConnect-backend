from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_moderator_or_admin
from app.models.user import User
from app.schemas.content import ContentListResponse, ContentRead, ContentRejectRequest
from app.services.content_service import (
    approve_content,
    list_pending_content,
    reject_content,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/content/pending", response_model=ContentListResponse)
def get_pending_content(
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContentListResponse:
    items, total = list_pending_content(db=db, skip=skip, limit=limit)

    return ContentListResponse(items=items, total=total)


@router.post("/content/{content_id}/approve", response_model=ContentRead)
def approve_pending_content(
    content_id: str,
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return approve_content(
        db=db,
        content_id=content_id,
        moderator=current_user,
    )


@router.post("/content/{content_id}/reject", response_model=ContentRead)
def reject_pending_content(
    content_id: str,
    payload: ContentRejectRequest,
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return reject_content(
        db=db,
        content_id=content_id,
        moderator=current_user,
        reason=payload.reason,
    )
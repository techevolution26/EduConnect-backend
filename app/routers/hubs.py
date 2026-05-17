from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.hub import HubCreate, HubRead, HubUpdate
from app.services.hub_service import (
    create_hub,
    get_hub_by_slug_or_404,
    get_hub_or_404,
    join_hub,
    leave_hub,
    list_hubs,
    update_hub,
)

router = APIRouter(prefix="/hubs", tags=["Hubs"])


@router.get("", response_model=list[HubRead])
def get_hubs(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = False,
) -> list[HubRead]:
    return list_hubs(db, include_inactive=include_inactive)


@router.get("/{slug}", response_model=HubRead)
def get_hub_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> HubRead:
    return get_hub_by_slug_or_404(db, slug)


@router.post("", response_model=HubRead)
def create_new_hub(
    payload: HubCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> HubRead:
    return create_hub(db, payload)


@router.patch("/{hub_id}", response_model=HubRead)
def update_existing_hub(
    hub_id: str,
    payload: HubUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> HubRead:
    return update_hub(db, hub_id, payload)


@router.post("/{hub_id}/join", response_model=MessageResponse)
def join_existing_hub(
    hub_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    join_hub(db, hub_id, current_user)
    return MessageResponse(message="Joined hub successfully.")


@router.post("/{hub_id}/leave", response_model=MessageResponse)
def leave_existing_hub(
    hub_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    leave_hub(db, hub_id, current_user)
    return MessageResponse(message="Left hub successfully.")
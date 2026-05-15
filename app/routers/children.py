from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_moderator_or_admin
from app.models.user import User
from app.schemas.education import (
    ChildrenContentCreate,
    ChildrenContentDetailRead,
    ChildrenContentRead,
)
from app.services.children_service import (
    create_children_content,
    get_children_content_or_404,
    list_children_content,
)

router = APIRouter(prefix="/children", tags=["Children"])


@router.get("/content", response_model=list[ChildrenContentDetailRead])
def get_children_content(
    db: Annotated[Session, Depends(get_db)],
    age_group: str | None = None,
) -> list[ChildrenContentDetailRead]:
    return list_children_content(db=db, age_group=age_group)


@router.get("/content/{children_content_id}", response_model=ChildrenContentDetailRead)
def get_single_children_content(
    children_content_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ChildrenContentDetailRead:
    return get_children_content_or_404(db, children_content_id)


@router.post("/content", response_model=ChildrenContentRead)
def create_new_children_content(
    payload: ChildrenContentCreate,
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ChildrenContentRead:
    return create_children_content(
        db=db,
        payload=payload,
        user=current_user,
    )
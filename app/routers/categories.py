from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category_service import (
    create_category,
    get_category_or_404,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryRead])
def get_categories(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = False,
) -> list[CategoryRead]:
    return list_categories(db, include_inactive=include_inactive)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CategoryRead:
    return get_category_or_404(db, category_id)


@router.post("", response_model=CategoryRead)
def create_new_category(
    payload: CategoryCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryRead:
    return create_category(db, payload)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_existing_category(
    category_id: str,
    payload: CategoryUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryRead:
    return update_category(db, category_id, payload)
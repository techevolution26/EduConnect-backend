from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.feed import FeedResponse
from app.services.feed_service import (
    list_category_feed,
    list_discovery_feed,
    list_hub_feed,
    list_personalized_feed,
)

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/discover", response_model=FeedResponse)
def get_discovery_feed(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    content_type: str | None = None,
    category_id: str | None = None,
    hub_id: str | None = None,
) -> FeedResponse:
    items, total = list_discovery_feed(
        db=db,
        skip=skip,
        limit=limit,
        content_type=content_type,
        category_id=category_id,
        hub_id=hub_id,
    )

    return FeedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/for-you", response_model=FeedResponse)
def get_personalized_feed(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    items, total = list_personalized_feed(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
    )

    return FeedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/by-category/{category_id}", response_model=FeedResponse)
def get_category_feed(
    category_id: str,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    items, total = list_category_feed(
        db=db,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )

    return FeedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/by-hub/{hub_id}", response_model=FeedResponse)
def get_hub_feed(
    hub_id: str,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    items, total = list_hub_feed(
        db=db,
        hub_id=hub_id,
        skip=skip,
        limit=limit,
    )

    return FeedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
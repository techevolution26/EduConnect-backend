from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.feed import SearchResponse
from app.services.feed_service import search_content

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/content", response_model=SearchResponse)
def search_published_content(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(min_length=2, max_length=120),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    content_type: str | None = None,
    category_id: str | None = None,
) -> SearchResponse:
    items, total = search_content(
        db=db,
        query=q,
        skip=skip,
        limit=limit,
        content_type=content_type,
        category_id=category_id,
    )

    return SearchResponse(
        query=q,
        items=items,
        total=total,
    )
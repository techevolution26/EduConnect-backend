from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.content import ContentListResponse
from app.schemas.writer import WriterProfileRead
from app.services.writer_service import (
    get_writer_or_404,
    get_writer_stats,
    list_writer_content,
    list_writers,
)

router = APIRouter(prefix="/writers", tags=["Writers"])


@router.get("", response_model=list[WriterProfileRead])
def get_writers(
    db: Annotated[Session, Depends(get_db)],
) -> list[WriterProfileRead]:
    writers = list_writers(db)

    response = []

    for writer in writers:
        stats = get_writer_stats(db, writer.id)
        response.append(
            WriterProfileRead(
                id=writer.id,
                email=writer.email,
                full_name=writer.full_name,
                username=writer.username,
                role=writer.role,
                avatar_url=writer.avatar_url,
                bio=writer.bio,
                is_verified=writer.is_verified,
                created_at=writer.created_at,
                followers_count=stats["followers_count"],
                published_count=stats["published_count"],
            )
        )

    return response


@router.get("/{writer_id}", response_model=WriterProfileRead)
def get_writer_profile(
    writer_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> WriterProfileRead:
    writer = get_writer_or_404(db, writer_id)
    stats = get_writer_stats(db, writer.id)

    return WriterProfileRead(
        id=writer.id,
        email=writer.email,
        full_name=writer.full_name,
        username=writer.username,
        role=writer.role,
        avatar_url=writer.avatar_url,
        bio=writer.bio,
        is_verified=writer.is_verified,
        created_at=writer.created_at,
        followers_count=stats["followers_count"],
        published_count=stats["published_count"],
    )


@router.get("/{writer_id}/content", response_model=ContentListResponse)
def get_writer_published_content(
    writer_id: str,
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContentListResponse:
    items, total = list_writer_content(
        db=db,
        writer_id=writer_id,
        skip=skip,
        limit=limit,
    )

    return ContentListResponse(items=items, total=total)
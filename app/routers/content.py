from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_current_user
from app.models.content import ContentStatus
from app.models.user import User
from app.schemas.content import (
    ContentAssetRead,
    ContentCreate,
    ContentDetailRead,
    ContentListResponse,
    ContentRead,
    ContentUpdate,
    ContentAccessRead,
)
from app.schemas.moderation import ModerationLogRead
from app.schemas.writer import WriterAnalyticsRead
from app.services.content_service import (
    add_content_assets,
    build_content_access_response,
    create_content,
    delete_content,
    get_content_by_slug_or_404,
    get_content_detail,
    get_my_content,
    get_my_content_or_404,
    get_my_writer_analytics,
    list_my_content_moderation_logs,
    list_public_content,
    submit_content_for_review,
    update_content,
)

router = APIRouter(prefix="/content", tags=["Content"])


@router.post("", response_model=ContentRead, status_code=status.HTTP_201_CREATED)
def create_new_content(
    payload: ContentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return create_content(db=db, payload=payload, author=current_user)


@router.get("", response_model=ContentListResponse)
def get_public_content(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    category_id: str | None = None,
    content_type: str | None = None,
) -> ContentListResponse:
    items, total = list_public_content(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        content_type=content_type,
    )
    return ContentListResponse(items=items, total=total)


@router.get("/mine", response_model=ContentListResponse)
def get_my_content_list(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: ContentStatus | None = None,
) -> ContentListResponse:
    items, total = get_my_content(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
    )
    return ContentListResponse(items=items, total=total)


@router.get("/analytics/me", response_model=WriterAnalyticsRead)
def get_my_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WriterAnalyticsRead:
    return get_my_writer_analytics(db=db, user=current_user)


@router.get("/mine/{content_id}", response_model=ContentRead)
def get_my_single_content(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return get_my_content_or_404(
        db=db,
        content_id=content_id,
        user=current_user,
    )


@router.get("/mine/{content_id}/moderation", response_model=list[ModerationLogRead])
def get_my_content_moderation_logs(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ModerationLogRead]:
    return list_my_content_moderation_logs(
        db=db,
        content_id=content_id,
        user=current_user,
    )


@router.get("/{slug}", response_model=ContentAccessRead)
def get_content_detail_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> ContentAccessRead:
    content = get_content_by_slug_or_404(db=db, slug=slug)
    return build_content_access_response(
        db=db,
        content=content,
        user=current_user,
    )


@router.get("/id/{content_id}", response_model=ContentDetailRead)
def get_content_detail_by_id(
    content_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ContentDetailRead:
    return get_content_detail(db=db, content_id=content_id)


@router.patch("/{content_id}", response_model=ContentRead)
def update_existing_content(
    content_id: str,
    payload: ContentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return update_content(
        db=db,
        content_id=content_id,
        payload=payload,
        user=current_user,
    )


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_content(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    delete_content(db=db, content_id=content_id, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{content_id}/submit-review", response_model=ContentRead)
def submit_for_review(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return submit_content_for_review(
        db=db,
        content_id=content_id,
        user=current_user,
    )


@router.post(
    "/{content_id}/assets",
    response_model=list[ContentAssetRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_content_assets(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    images: list[UploadFile] = File(default_factory=list),
    files: list[UploadFile] = File(default_factory=list),
) -> list[ContentAssetRead]:
    return await add_content_assets(
        db=db,
        content_id=content_id,
        user=current_user,
        images=images,
        files=files,
    )
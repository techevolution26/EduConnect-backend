from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.content import ContentRead
from app.schemas.engagement import CommentCreate, CommentRead
from app.services.engagement_service import (
    bookmark_content,
    create_comment,
    follow_writer,
    get_content_counts,
    get_my_bookmarks,
    like_content,
    list_comments,
    remove_bookmark,
    unfollow_writer,
    unlike_content,
)

router = APIRouter(tags=["Engagement"])


@router.post("/content/{content_id}/like", response_model=MessageResponse)
def like_existing_content(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    like_content(db, content_id, current_user)
    return MessageResponse(message="Content liked successfully.")


@router.delete("/content/{content_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_existing_content(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    unlike_content(db, content_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/content/{content_id}/bookmark", response_model=MessageResponse)
def bookmark_existing_content(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    bookmark_content(db, content_id, current_user)
    return MessageResponse(message="Content bookmarked successfully.")


@router.delete("/content/{content_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def remove_existing_bookmark(
    content_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    remove_bookmark(db, content_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/content/{content_id}/comments", response_model=CommentRead)
def create_content_comment(
    content_id: str,
    payload: CommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommentRead:
    return create_comment(db, content_id, payload, current_user)


@router.get("/content/{content_id}/comments", response_model=list[CommentRead])
def get_content_comments(
    content_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[CommentRead]:
    return list_comments(db, content_id)


@router.get("/content/{content_id}/counts")
def get_existing_content_counts(
    content_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    return get_content_counts(db, content_id)


@router.get("/users/me/bookmarks", response_model=list[ContentRead])
def get_my_saved_content(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ContentRead]:
    return get_my_bookmarks(db, current_user)


@router.post("/writers/{writer_id}/follow", response_model=MessageResponse)
def follow_existing_writer(
    writer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    follow_writer(db, writer_id, current_user)
    return MessageResponse(message="Writer followed successfully.")


@router.delete("/writers/{writer_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_existing_writer(
    writer_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    unfollow_writer(db, writer_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
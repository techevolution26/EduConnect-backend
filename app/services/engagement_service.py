from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.content import Content, ContentStatus
from app.models.engagement import Bookmark, Comment, Follow, Like
from app.models.user import User
from app.schemas.engagement import CommentCreate


def get_published_content_or_404(db: Session, content_id: str) -> Content:
    content = db.get(Content, content_id)

    if not content or content.status != ContentStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published content was not found.",
        )

    return content


def like_content(db: Session, content_id: str, user: User) -> Like:
    get_published_content_or_404(db, content_id)

    existing = db.scalars(
        select(Like).where(
            Like.content_id == content_id,
            Like.user_id == user.id,
        )
    ).first()

    if existing:
        return existing

    like = Like(content_id=content_id, user_id=user.id)

    db.add(like)
    db.commit()
    db.refresh(like)

    return like


def unlike_content(db: Session, content_id: str, user: User) -> None:
    like = db.scalars(
        select(Like).where(
            Like.content_id == content_id,
            Like.user_id == user.id,
        )
    ).first()

    if like:
        db.delete(like)
        db.commit()


def bookmark_content(db: Session, content_id: str, user: User) -> Bookmark:
    get_published_content_or_404(db, content_id)

    existing = db.scalars(
        select(Bookmark).where(
            Bookmark.content_id == content_id,
            Bookmark.user_id == user.id,
        )
    ).first()

    if existing:
        return existing

    bookmark = Bookmark(content_id=content_id, user_id=user.id)

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return bookmark


def remove_bookmark(db: Session, content_id: str, user: User) -> None:
    bookmark = db.scalars(
        select(Bookmark).where(
            Bookmark.content_id == content_id,
            Bookmark.user_id == user.id,
        )
    ).first()

    if bookmark:
        db.delete(bookmark)
        db.commit()


def create_comment(
    db: Session,
    content_id: str,
    payload: CommentCreate,
    user: User,
) -> Comment:
    get_published_content_or_404(db, content_id)

    if payload.parent_id:
        parent = db.get(Comment, payload.parent_id)

        if not parent or parent.content_id != content_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment is invalid.",
            )

    comment = Comment(
        content_id=content_id,
        user_id=user.id,
        parent_id=payload.parent_id,
        body=payload.body,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


def list_comments(db: Session, content_id: str) -> list[Comment]:
    get_published_content_or_404(db, content_id)

    return list(
        db.scalars(
            select(Comment)
            .options(joinedload(Comment.user))
            .where(
                Comment.content_id == content_id,
                Comment.is_hidden == False,
            )
            .order_by(Comment.created_at.asc())
        ).all()
    )


def follow_writer(db: Session, writer_id: str, user: User) -> Follow:
    if writer_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself.",
        )

    writer = db.get(User, writer_id)

    if not writer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Writer was not found.",
        )

    existing = db.scalars(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.following_id == writer_id,
        )
    ).first()

    if existing:
        return existing

    follow = Follow(follower_id=user.id, following_id=writer_id)

    db.add(follow)
    db.commit()
    db.refresh(follow)

    return follow


def unfollow_writer(db: Session, writer_id: str, user: User) -> None:
    follow = db.scalars(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.following_id == writer_id,
        )
    ).first()

    if follow:
        db.delete(follow)
        db.commit()


def get_content_counts(db: Session, content_id: str) -> dict[str, int]:
    likes_count = db.scalar(
        select(func.count()).select_from(Like).where(Like.content_id == content_id)
    ) or 0

    bookmarks_count = db.scalar(
        select(func.count()).select_from(Bookmark).where(Bookmark.content_id == content_id)
    ) or 0

    comments_count = db.scalar(
        select(func.count()).select_from(Comment).where(
            Comment.content_id == content_id,
            Comment.is_hidden == False,
        )
    ) or 0

    return {
        "likes": likes_count,
        "bookmarks": bookmarks_count,
        "comments": comments_count,
    }


def get_my_bookmarks(db: Session, user: User) -> list[Content]:
    statement = (
        select(Content)
        .join(Bookmark, Bookmark.content_id == Content.id)
        .where(
            Bookmark.user_id == user.id,
            Content.status == ContentStatus.PUBLISHED,
        )
        .order_by(Bookmark.created_at.desc())
    )

    return list(db.scalars(statement).all())
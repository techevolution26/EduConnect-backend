from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.content import Content, ContentStatus, ContentVisibility
from app.models.engagement import Bookmark, Comment, CommentLike, Follow, Like
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.engagement import CommentCreate, EngagementStatus
from app.services.notification_service import create_notification
from app.services.partnership_service import user_has_active_partnership


def get_published_content_or_404(db: Session, content_id: str) -> Content:
    statement = (
        select(Content)
        .options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.hub),
            joinedload(Content.assets),
        )
        .where(
            Content.id == content_id,
            Content.status == ContentStatus.PUBLISHED,
        )
    )

    content = db.scalars(statement).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published content was not found.",
        )

    return content


def get_comment_or_404(db: Session, comment_id: str) -> Comment:
    comment = db.scalars(
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.id == comment_id, Comment.is_hidden == False)
    ).first()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment was not found.",
        )

    get_published_content_or_404(db, comment.content_id)
    return comment


def get_content_engagement_status(
    db: Session,
    content_id: str,
    user: User | None = None,
) -> EngagementStatus:
    get_published_content_or_404(db, content_id)

    liked = False
    bookmarked = False
    following = False

    if user:
        liked = (
            db.scalar(
                select(Like.id).where(
                    Like.content_id == content_id,
                    Like.user_id == user.id,
                )
            )
            is not None
        )

        bookmarked = (
            db.scalar(
                select(Bookmark.id).where(
                    Bookmark.content_id == content_id,
                    Bookmark.user_id == user.id,
                )
            )
            is not None
        )

        content = db.get(Content, content_id)
        if content and content.author_id != user.id:
            following = (
                db.scalar(
                    select(Follow.id).where(
                        Follow.follower_id == user.id,
                        Follow.following_id == content.author_id,
                    )
                )
                is not None
            )

    return EngagementStatus(
        liked=liked,
        bookmarked=bookmarked,
        following=following,
    )


def _attach_comment_meta(
    db: Session,
    comments: list[Comment],
    user: User | None = None,
) -> list[Comment]:
    if not comments:
        return comments

    comment_ids = [comment.id for comment in comments]

    likes_rows = db.execute(
        select(
            CommentLike.comment_id,
            func.count(CommentLike.id),
        )
        .where(CommentLike.comment_id.in_(comment_ids))
        .group_by(CommentLike.comment_id)
    ).all()

    likes_count_map = {row[0]: int(row[1]) for row in likes_rows}

    liked_ids: set[str] = set()
    if user:
        liked_ids = set(
            db.scalars(
                select(CommentLike.comment_id).where(
                    CommentLike.user_id == user.id,
                    CommentLike.comment_id.in_(comment_ids),
                )
            ).all()
        )

    for comment in comments:
        setattr(comment, "likes_count", likes_count_map.get(comment.id, 0))
        setattr(comment, "liked_by_me", comment.id in liked_ids)

    return comments


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
    content = get_published_content_or_404(db, content_id)

    if payload.parent_id:
        parent = db.get(Comment, payload.parent_id)
        if not parent or parent.content_id != content_id or parent.is_hidden:
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

    if content.author_id != user.id:
        create_notification(
            db=db,
            user_id=content.author_id,
            notification_type=NotificationType.COMMENT,
            title="New comment on your content",
            body=f"{user.full_name} commented on “{content.title}”.",
        )

    db.commit()
    db.refresh(comment)

    setattr(comment, "likes_count", 0)
    setattr(comment, "liked_by_me", False)

    return comment


def list_comments(
    db: Session,
    content_id: str,
    user: User | None = None,
) -> list[Comment]:
    get_published_content_or_404(db, content_id)

    comments = list(
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

    return _attach_comment_meta(db, comments, user)


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

    create_notification(
        db=db,
        user_id=writer_id,
        notification_type=NotificationType.NEW_FOLLOWER,
        title="You have a new follower",
        body=f"{user.full_name} started following you.",
    )

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
    content = db.get(Content, content_id)
    views_count = content.views_count if content else 0

    return {
        "likes": likes_count,
        "bookmarks": bookmarks_count,
        "comments": comments_count,
        "views": views_count,
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


def get_content_detail(db: Session, content_id: str) -> Content:
    statement = (
        select(Content)
        .options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.hub),
            joinedload(Content.assets),
        )
        .where(Content.id == content_id)
    )

    content = db.scalars(statement).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    return content
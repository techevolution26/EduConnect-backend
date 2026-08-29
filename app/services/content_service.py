from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.storage import normalize_public_url, save_upload_file
from app.models.content import Content, ContentStatus, ContentVisibility
from app.models.content_asset import ContentAsset, ContentAssetType
from app.models.moderation import ModerationAction, ModerationLog
from app.models.user import User, UserRole
from app.schemas.content import ContentAccessRead, ContentCreate, ContentUpdate
from app.services.partnership_service import user_has_active_partnership
from app.models.notification import NotificationType
from app.services.notification_service import create_notification
from app.models.moderation import ModerationLog
from app.models.engagement import Bookmark, Comment, Follow, Like


from app.core.permissions import is_admin_tier


def calculate_reading_time_minutes(body: str) -> int:
    words = len(body.split())
    return max(1, round(words / 200))


def ensure_can_write_content(user: User) -> None:
    # FIX: previously excluded SUPER_ADMIN (checked `role == UserRole.ADMIN`
    # explicitly via set membership that never included SUPER_ADMIN). Use
    # is_admin_tier so the super admin can always author/manage content.
    if user.role not in {UserRole.WRITER, UserRole.TEACHER} and not is_admin_tier(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only writers, teachers, or admins can publish content.",
        )


def ensure_content_owner_or_admin(content: Content, user: User) -> None:
    # FIX: same SUPER_ADMIN exclusion bug as above.
    if content.author_id != user.id and not is_admin_tier(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own content.",
        )


def get_content_or_404(db: Session, content_id: str) -> Content:
    content = db.get(Content, content_id)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    return content


def get_content_by_slug_or_404(db: Session, slug: str) -> Content:
    statement = (
        select(Content)
        .options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.hub),
            joinedload(Content.assets),
        )
        .where(
            Content.slug == slug,
            Content.status == ContentStatus.PUBLISHED,
        )
    )

    content = db.scalars(statement).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    return content


def create_content(db: Session, payload: ContentCreate, author: User) -> Content:
    ensure_can_write_content(author)

    existing = db.scalars(select(Content).where(Content.slug == payload.slug)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content slug already exists.",
        )

    content = Content(
        author_id=author.id,
        title=payload.title,
        slug=payload.slug,
        excerpt=payload.excerpt,
        body=payload.body,
        content_type=payload.content_type,
        visibility=payload.visibility,
        is_premium=payload.is_premium,
        category_id=payload.category_id,
        hub_id=payload.hub_id,
        cover_image_url=normalize_public_url(payload.cover_image_url),
        status=ContentStatus.DRAFT,
        reading_time_minutes=calculate_reading_time_minutes(payload.body),
    )

    db.add(content)
    db.commit()
    db.refresh(content)

    return content


def update_content(
    db: Session,
    content_id: str,
    payload: ContentUpdate,
    user: User,
) -> Content:
    content = get_content_or_404(db, content_id)
    ensure_content_owner_or_admin(content, user)

    # FIX: same SUPER_ADMIN exclusion bug as ensure_can_write_content /
    # ensure_content_owner_or_admin above -- was `!= UserRole.ADMIN`.
    if content.status == ContentStatus.PUBLISHED and not is_admin_tier(user.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Published content cannot be edited directly. Create a revision flow later.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "slug" in update_data:
        existing = db.scalars(
            select(Content).where(
                Content.slug == update_data["slug"],
                Content.id != content.id,
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Content slug already exists.",
            )

    if "cover_image_url" in update_data:
        update_data["cover_image_url"] = normalize_public_url(update_data["cover_image_url"])

    for field, value in update_data.items():
        setattr(content, field, value)

    if payload.body:
        content.reading_time_minutes = calculate_reading_time_minutes(payload.body)

    db.add(content)
    db.commit()
    db.refresh(content)

    return content


def submit_content_for_review(db: Session, content_id: str, user: User) -> Content:
    content = get_content_or_404(db, content_id)
    ensure_content_owner_or_admin(content, user)

    if content.status not in {ContentStatus.DRAFT, ContentStatus.REJECTED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected content can be submitted for review.",
        )

    content.status = ContentStatus.PENDING_REVIEW

    db.add(content)
    db.commit()
    db.refresh(content)

    return content


def approve_content(db: Session, content_id: str, moderator: User) -> Content:
    content = get_content_or_404(db, content_id)

    if content.status != ContentStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending content can be approved.",
        )

    content.status = ContentStatus.PUBLISHED
    content.published_at = datetime.now(timezone.utc)

    log = ModerationLog(
        moderator_id=moderator.id,
        content_id=content.id,
        action=ModerationAction.APPROVED,
        note="Content approved for publishing.",
    )

    db.add(content)
    db.add(log)

    create_notification(
    db=db,
    user_id=content.author_id,
    notification_type=NotificationType.CONTENT_APPROVED,
    title="Your content was approved",
    body=f"“{content.title}” is now published and visible to readers.",
)

    db.commit()
    db.refresh(content)
    db.refresh(content)

    return content


def reject_content(
    db: Session,
    content_id: str,
    moderator: User,
    reason: str,
) -> Content:
    content = get_content_or_404(db, content_id)

    if content.status != ContentStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending content can be rejected.",
        )

    content.status = ContentStatus.REJECTED

    log = ModerationLog(
        moderator_id=moderator.id,
        content_id=content.id,
        action=ModerationAction.REJECTED,
        note=reason,
    )

    db.add(content)
    db.add(log)

    create_notification(
    db=db,
    user_id=content.author_id,
    notification_type=NotificationType.CONTENT_REJECTED,
    title="Your content needs revision",
    body=f"“{content.title}” was rejected. Reason: {reason}",
)
    db.commit()
    db.refresh(content)

    return content


def delete_content(db: Session, content_id: str, user: User) -> None:
    content = get_content_or_404(db, content_id)
    ensure_content_owner_or_admin(content, user)

    db.delete(content)
    db.commit()


def list_public_content(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    category_id: str | None = None,
    content_type: str | None = None,
) -> tuple[list[Content], int]:
    statement = select(Content).where(Content.status == ContentStatus.PUBLISHED)
    count_statement = select(func.count()).select_from(Content).where(
        Content.status == ContentStatus.PUBLISHED
    )

    if category_id:
        statement = statement.where(Content.category_id == category_id)
        count_statement = count_statement.where(Content.category_id == category_id)

    if content_type:
        statement = statement.where(Content.content_type == content_type)
        count_statement = count_statement.where(Content.content_type == content_type)

    statement = statement.order_by(Content.published_at.desc()).offset(skip).limit(limit)

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def list_pending_content(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Content], int]:
    statement = (
        select(Content)
        .where(Content.status == ContentStatus.PENDING_REVIEW)
        .order_by(Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(Content).where(
        Content.status == ContentStatus.PENDING_REVIEW
    )

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def content_requires_partnership(content: Content) -> bool:
    return (
        content.is_premium
        or content.visibility == ContentVisibility.PARTNERS_ONLY
    )


def build_content_access_response(
    db: Session,
    content: Content,
    user: User | None = None,
) -> ContentAccessRead:
    premium_locked = content.visibility == ContentVisibility.PARTNERS_ONLY or content.is_premium

    has_access = True
    preview_body = None
    requires_partnership = premium_locked

    if premium_locked:
        has_access = user_has_active_partnership(db, user)
        if not has_access:
            preview_body = content.excerpt or content.body[:400]

    return ContentAccessRead(
        id=content.id,
        author_id=content.author_id,
        author=content.author,
        category_id=content.category_id,
        hub_id=content.hub_id,
        title=content.title,
        slug=content.slug,
        excerpt=content.excerpt,
        body=content.body if has_access else "",
        cover_image_url=content.cover_image_url,
        content_type=content.content_type,
        status=content.status,
        visibility=content.visibility,
        is_premium=content.is_premium,
        reading_time_minutes=content.reading_time_minutes,
        is_featured=content.is_featured,
        featured_at=content.featured_at,
        published_at=content.published_at,
        created_at=content.created_at,
        updated_at=content.updated_at,
        category=content.category,
        hub=content.hub,
        assets=content.assets,
        requires_partnership=requires_partnership,
        has_access=has_access,
        preview_body=preview_body,
    )

def get_my_content(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 50,
    status_filter: ContentStatus | None = None,
) -> tuple[list[Content], int]:
    ensure_can_write_content(user)

    filters = [Content.author_id == user.id]

    if status_filter:
        filters.append(Content.status == status_filter)

    statement = (
        select(Content)
        .where(*filters)
        .order_by(Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(Content).where(*filters)

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


list_my_content = get_my_content

def get_my_content_or_404(db: Session, content_id: str, user: User) -> Content:
    ensure_can_write_content(user)

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
            Content.author_id == user.id,
        )
    )

    content = db.scalars(statement).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    return content



def list_my_content_moderation_logs(
    db: Session,
    content_id: str,
    user: User,
) -> list[ModerationLog]:
    content = get_my_content_or_404(db, content_id, user)

    return list(
        db.scalars(
            select(ModerationLog)
            .where(ModerationLog.content_id == content.id)
            .order_by(ModerationLog.created_at.desc())
        ).all()
    )



def get_my_writer_analytics(db: Session, user: User) -> dict:
    ensure_can_write_content(user)

    total_content = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(Content.author_id == user.id)
        )
        or 0
    )

    drafts = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == user.id,
                Content.status == ContentStatus.DRAFT,
            )
        )
        or 0
    )

    pending = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == user.id,
                Content.status == ContentStatus.PENDING_REVIEW,
            )
        )
        or 0
    )

    published = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == user.id,
                Content.status == ContentStatus.PUBLISHED,
            )
        )
        or 0
    )

    rejected = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == user.id,
                Content.status == ContentStatus.REJECTED,
            )
        )
        or 0
    )

    followers = (
        db.scalar(
            select(func.count())
            .select_from(Follow)
            .where(Follow.following_id == user.id)
        )
        or 0
    )

    likes_received = (
        db.scalar(
            select(func.count())
            .select_from(Like)
            .join(Content, Content.id == Like.content_id)
            .where(Content.author_id == user.id)
        )
        or 0
    )

    comments_received = (
        db.scalar(
            select(func.count())
            .select_from(Comment)
            .join(Content, Content.id == Comment.content_id)
            .where(Content.author_id == user.id)
        )
        or 0
    )

    bookmarks_received = (
        db.scalar(
            select(func.count())
            .select_from(Bookmark)
            .join(Content, Content.id == Bookmark.content_id)
            .where(Content.author_id == user.id)
        )
        or 0
    )

    return {
        "total_content": total_content,
        "drafts": drafts,
        "pending": pending,
        "published": published,
        "rejected": rejected,
        "followers": followers,
        "likes_received": likes_received,
        "comments_received": comments_received,
        "bookmarks_received": bookmarks_received,
    }

def toggle_featured_content(
    db: Session,
    content: Content,
) -> Content:
    content.is_featured = not content.is_featured

    if content.is_featured:
        content.featured_at = datetime.now(timezone.utc)
    else:
        content.featured_at = None

    db.add(content)
    db.commit()
    db.refresh(content)

    return content



async def add_content_assets(
    db: Session,
    content_id: str,
    user: User,
    images: list[UploadFile],
    files: list[UploadFile],
) -> list[ContentAsset]:
    content = get_content_or_404(db, content_id)
    ensure_content_owner_or_admin(content, user)

    created_assets: list[ContentAsset] = []

    for image in images:
        url = await save_upload_file(image, "images", is_image=True)
        asset = ContentAsset(
            content_id=content.id,
            asset_type=ContentAssetType.IMAGE,
            url=url,
            filename=image.filename,
            mime_type=image.content_type,
            size_bytes=None,
        )
        db.add(asset)
        created_assets.append(asset)

    for file in files:
        url = await save_upload_file(file, "files", is_image=False)
        asset = ContentAsset(
            content_id=content.id,
            asset_type=ContentAssetType.FILE,
            url=url,
            filename=file.filename,
            mime_type=file.content_type,
            size_bytes=None,
        )
        db.add(asset)
        created_assets.append(asset)

    db.commit()

    for asset in created_assets:
        db.refresh(asset)

    return created_assets

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
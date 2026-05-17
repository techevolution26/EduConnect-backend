from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def list_categories(db: Session, include_inactive: bool = False) -> list[Category]:
    statement = select(Category).order_by(Category.name.asc())

    if not include_inactive:
        statement = statement.where(Category.is_active == True)

    return list(db.scalars(statement).all())

def get_category_or_404(db: Session, category_id: str) -> Category:
    category = db.get(Category, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category was not found.",
        )

    return category


def create_category(db: Session, payload: CategoryCreate) -> Category:
    existing = db.scalars(
        select(Category).where(Category.slug == payload.slug)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category slug already exists.",
        )

    category = Category(**payload.model_dump())

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


def update_category(db: Session, category_id: str, payload: CategoryUpdate) -> Category:
    category = get_category_or_404(db, category_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "slug" in update_data:
        existing = db.scalars(
            select(Category).where(
                Category.slug == update_data["slug"],
                Category.id != category.id,
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category slug already exists.",
            )

    for field, value in update_data.items():
        setattr(category, field, value)

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


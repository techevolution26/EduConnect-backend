from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.hub import Hub
from app.models.user import User, UserRole


DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "AdminPass123!"
DEFAULT_ADMIN_NAME = "Platform Admin"

DEFAULT_CATEGORIES = [
    {
        "name": "Stories & Fiction",
        "slug": "stories-fiction",
        "description": "Original stories, fiction, and creative writing.",
    },
    {
        "name": "Poetry & Spoken Word",
        "slug": "poetry-spoken-word",
        "description": "Poems, spoken word, and literary expression.",
    },
    {
        "name": "Faith-Based Content",
        "slug": "faith-based-content",
        "description": "Christian faith, biblical teaching, devotionals, and inspiration.",
    },
    {
        "name": "Relationships & Lifestyle",
        "slug": "relationships-lifestyle",
        "description": "Relationships, life lessons, culture, and daily living.",
    },
    {
        "name": "Business & Entrepreneurship",
        "slug": "business-entrepreneurship",
        "description": "Business, startups, money, and entrepreneurship.",
    },
    {
        "name": "Mental Wellness",
        "slug": "mental-wellness",
        "description": "Mental wellness, encouragement, and personal growth.",
    },
    {
        "name": "Education & Learning",
        "slug": "education-learning",
        "description": "Learning resources, revision, teaching, and academic materials.",
    },
    {
        "name": "Technology",
        "slug": "technology",
        "description": "Technology, digital skills, software, and innovation.",
    },
    {
        "name": "Parenting",
        "slug": "parenting",
        "description": "Parenting, family, and child development.",
    },
    {
        "name": "Sports",
        "slug": "sports",
        "description": "Sports stories, analysis, and community updates.",
    },
    {
        "name": "Agriculture",
        "slug": "agriculture",
        "description": "Farming, agribusiness, and agricultural education.",
    },
    {
        "name": "Gardening",
        "slug": "gardening",
        "description": "Gardening, home growing, and practical guides.",
    },
    {
        "name": "Children",
        "slug": "children",
        "description": "Safe stories and learning content for children.",
    },
]

DEFAULT_HUBS = [
    {
        "name": "Writers Hub",
        "slug": "writers-hub",
        "description": "A community for writers to grow, collaborate, and publish.",
    },
    {
        "name": "African Stories Hub",
        "slug": "african-stories-hub",
        "description": "A home for African storytelling, culture, and voices.",
    },
    {
        "name": "Faith & Inspiration Hub",
        "slug": "faith-inspiration-hub",
        "description": "Faith-based discussions, devotionals, and encouragement.",
    },
    {
        "name": "Women’s Stories Hub",
        "slug": "womens-stories-hub",
        "description": "Stories, discussions, and resources centered around women’s voices.",
    },
    {
        "name": "Teachers Hub",
        "slug": "teachers-hub",
        "description": "Resources and collaboration space for teachers.",
    },
    {
        "name": "Students Hub",
        "slug": "students-hub",
        "description": "Revision, learning support, and student discussions.",
    },
    {
        "name": "Children’s Stories Hub",
        "slug": "childrens-stories-hub",
        "description": "Curated safe stories and learning materials for children.",
    },
    {
        "name": "Spoken Word & Poetry Hub",
        "slug": "spoken-word-poetry-hub",
        "description": "A creative space for poets and spoken word artists.",
    },
]


def seed_admin() -> None:
    db = SessionLocal()

    try:
        existing_admin = db.scalars(
            select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
        ).first()

        if existing_admin:
            print("Admin user already exists.")
            return

        admin = User(
            email=DEFAULT_ADMIN_EMAIL,
            full_name=DEFAULT_ADMIN_NAME,
            username="admin",
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )

        db.add(admin)
        db.commit()

        print("Admin user created.")
        print(f"Email: {DEFAULT_ADMIN_EMAIL}")
        print(f"Password: {DEFAULT_ADMIN_PASSWORD}")

    finally:
        db.close()


def seed_categories() -> None:
    db = SessionLocal()

    try:
        for item in DEFAULT_CATEGORIES:
            existing = db.scalars(
                select(Category).where(Category.slug == item["slug"])
            ).first()

            if existing:
                continue

            category = Category(**item)
            db.add(category)

        db.commit()
        print("Categories seeded.")

    finally:
        db.close()


def seed_hubs() -> None:
    db = SessionLocal()

    try:
        for item in DEFAULT_HUBS:
            existing = db.scalars(
                select(Hub).where(Hub.slug == item["slug"])
            ).first()

            if existing:
                continue

            hub = Hub(**item)
            db.add(hub)

        db.commit()
        print("Hubs seeded.")

    finally:
        db.close()


def main() -> None:
    seed_admin()
    seed_categories()
    seed_hubs()


if __name__ == "__main__":
    main()
"""add rbac permissions, events, students, gamification, monetization tables

Revision ID: 2481109ac4ee
Revises: 568c6b5dc7ca
Create Date: 2026-08-20

Adds every table introduced in this hardening + feature pass:
  - admin_permissions        (scoped admin permission grants)
  - schools, student_profiles (student identity / verification)
  - events, event_participants (marketing events: competitions/workshops/book clubs)
  - xp_ledger, badges, user_badges (gamification)
  - referral_earnings         (creator referral commission ledger)

Column types follow the existing project convention (String(36) UUID PKs,
generic JSON instead of PostgreSQL-specific ARRAY/JSONB, native SQLAlchemy
Enum, server_default="0"/"1" for MySQL-compatible booleans) to match how
prior migrations in this repo were written for MySQL compatibility.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2481109ac4ee"
down_revision = "568c6b5dc7ca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # RBAC: scoped admin permissions
    # -----------------------------------------------------------------
    op.create_table(
        "admin_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.Column("granted_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "permission", name="uq_admin_permission_user_perm"),
    )
    op.create_index("ix_admin_permissions_user_id", "admin_permissions", ["user_id"])
    op.create_index("ix_admin_permissions_permission", "admin_permissions", ["permission"])

    # -----------------------------------------------------------------
    # Student identity
    # -----------------------------------------------------------------
    op.create_table(
        "schools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("county", sa.String(100), nullable=True),
        sa.Column("type", sa.Enum("PRIMARY", "SECONDARY", "COLLEGE", "UNIVERSITY", name="schooltype"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schools_name", "schools", ["name"])

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grade_level", sa.String(50), nullable=True),
        sa.Column("curriculum", sa.String(30), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("verification_code", sa.String(12), nullable=True),
        sa.Column("verification_email", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"])
    op.create_index("ix_student_profiles_verified", "student_profiles", ["verified"])

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.Enum("COMPETITION", "WORKSHOP", "BOOK_CLUB", name="eventtype"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ONGOING", "COMPLETED", "CANCELLED", name="eventstatus"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("host_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curriculum_tags", sa.JSON(), nullable=False),
        sa.Column("student_only", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requires_partnership", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_slug", "events", ["slug"])
    op.create_index("ix_events_type", "events", ["type"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_host_id", "events", ["host_id"])

    op.create_table(
        "event_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("RSVP", "ATTENDED", "SUBMITTED", "COMPLETED", "WITHDREW", name="participationstatus"),
            nullable=False,
            server_default="RSVP",
        ),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submission", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_participant_event_user"),
    )
    op.create_index("ix_event_participants_event_id", "event_participants", ["event_id"])
    op.create_index("ix_event_participants_user_id", "event_participants", ["user_id"])
    op.create_index("ix_event_participants_status", "event_participants", ["status"])

    # -----------------------------------------------------------------
    # Gamification
    # -----------------------------------------------------------------
    op.create_table(
        "xp_ledger",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_xp_ledger_user_id", "xp_ledger", ["user_id"])
    op.create_index("ix_xp_ledger_source_type", "xp_ledger", ["source_type"])
    op.create_index("ix_xp_ledger_earned_at", "xp_ledger", ["earned_at"])

    op.create_table(
        "badges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("icon", sa.String(120), nullable=True),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("condition_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_badges_slug", "badges", ["slug"])

    op.create_table(
        "user_badges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_id", sa.String(36), sa.ForeignKey("badges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge_user_badge"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])

    # -----------------------------------------------------------------
    # Monetization: referral commissions
    # -----------------------------------------------------------------
    op.create_table(
        "referral_earnings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("referrer_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("partnership_id", sa.String(36), sa.ForeignKey("partnerships.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "partnership_payment_id",
            sa.String(36),
            sa.ForeignKey("partnership_payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_amount_kes", sa.Integer(), nullable=False),
        sa.Column("commission_rate_bps", sa.Integer(), nullable=False),
        sa.Column("commission_amount_kes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PAID", "VOID", name="referralearningstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_referral_earnings_referrer_id", "referral_earnings", ["referrer_id"])
    op.create_index("ix_referral_earnings_status", "referral_earnings", ["status"])


def downgrade() -> None:
    op.drop_index("ix_referral_earnings_status", table_name="referral_earnings")
    op.drop_index("ix_referral_earnings_referrer_id", table_name="referral_earnings")
    op.drop_table("referral_earnings")

    op.drop_index("ix_user_badges_badge_id", table_name="user_badges")
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")

    op.drop_index("ix_badges_slug", table_name="badges")
    op.drop_table("badges")

    op.drop_index("ix_xp_ledger_earned_at", table_name="xp_ledger")
    op.drop_index("ix_xp_ledger_source_type", table_name="xp_ledger")
    op.drop_index("ix_xp_ledger_user_id", table_name="xp_ledger")
    op.drop_table("xp_ledger")

    op.drop_index("ix_event_participants_status", table_name="event_participants")
    op.drop_index("ix_event_participants_user_id", table_name="event_participants")
    op.drop_index("ix_event_participants_event_id", table_name="event_participants")
    op.drop_table("event_participants")

    op.drop_index("ix_events_host_id", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_type", table_name="events")
    op.drop_index("ix_events_slug", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_student_profiles_verified", table_name="student_profiles")
    op.drop_index("ix_student_profiles_user_id", table_name="student_profiles")
    op.drop_table("student_profiles")

    op.drop_index("ix_schools_name", table_name="schools")
    op.drop_table("schools")

    op.drop_index("ix_admin_permissions_permission", table_name="admin_permissions")
    op.drop_index("ix_admin_permissions_user_id", table_name="admin_permissions")
    op.drop_table("admin_permissions")

    # Enum types created implicitly by sa.Enum(...) on table create need an
    # explicit drop on PostgreSQL (MySQL stores enums inline on the column
    # and drops them automatically with drop_table). This is a no-op on
    # MySQL and a real cleanup step if this ever runs against Postgres.
    sa.Enum(name="referralearningstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="participationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="schooltype").drop(op.get_bind(), checkfirst=True)

"""
Granular permission system for EduConnect.

WHY THIS EXISTS
----------------
Before this change, the platform had exactly two effective admin tiers:
`ADMIN` (all-or-nothing access to every admin endpoint) and `SUPER_ADMIN`
(which, due to a bug in core/deps.py, actually had LESS access than ADMIN --
every `require_admin` check did `role != UserRole.ADMIN`, which excludes
SUPER_ADMIN entirely).

This module introduces:
  1. A `Permission` enum of granular capabilities.
  2. A `Role` hierarchy (see ROLE_RANK below) so we can reason about
     "who can promote/demote whom" instead of relying on scattered
     equality checks.
  3. Helper functions used by app.core.deps to build permission-gated
     dependencies, e.g. `require_permission(Permission.EVENTS_MANAGE)`.

DESIGN
------
- SUPER_ADMIN implicitly holds every permission and can manage every other
  account, including other admins. There is exactly one tier above it:
  none. It is the account of last resort.
- ADMIN accounts hold NO permissions by default. A SUPER_ADMIN grants
  specific permissions to specific admins via the `admin_permissions`
  table (see models/permission.py). This is the "factor down admins to
  specific functions" requirement -- e.g. one admin might only get
  CONTENT_MODERATE + REPORTS_MANAGE, another only PARTNERSHIPS_MANAGE.
- MODERATOR keeps its existing, fixed capability (content moderation)
  without needing rows in admin_permissions -- it's a role-based
  shortcut for a single, well-understood job, not a general admin tier.
- Staff roles (MODERATOR, ADMIN, SUPER_ADMIN) can only ever be assigned
  by a SUPER_ADMIN. A scoped ADMIN with USERS_MANAGE can promote/demote
  ordinary member roles (READER, WRITER, TEACHER, STUDENT, PARENT) but
  can never create another admin or moderator, and can never touch a
  SUPER_ADMIN account. See services/admin_service.py::update_user_role.
"""
from __future__ import annotations

import enum

from app.models.user import UserRole


class Permission(str, enum.Enum):
    """Granular capabilities that can be granted to an ADMIN-role user."""

    # User & account management
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"          # change role (non-staff) / activate / deactivate

    # Content moderation & catalog management
    CONTENT_MODERATE = "content.moderate"  # approve / reject submitted content
    CONTENT_MANAGE = "content.manage"      # feature/unfeature, delete any content
    CATALOG_MANAGE = "catalog.manage"      # categories & hubs CRUD

    # Role requests (writer/teacher upgrade requests)
    ROLE_REQUESTS_REVIEW = "role_requests.review"

    # Monetization
    PARTNERSHIPS_MANAGE = "partnerships.manage"   # manually activate/adjust partnerships
    PAYOUTS_MANAGE = "payouts.manage"             # view/mark referral commission payouts

    # Marketing / events / student identity
    EVENTS_MANAGE = "events.manage"        # create/edit/cancel ANY event (not just one's own)
    EVENTS_MODERATE = "events.moderate"    # review competition submissions, mark attendance overrides
    STUDENTS_VERIFY = "students.verify"    # manually verify a student's school affiliation
    BADGES_MANAGE = "badges.manage"        # create/edit badge definitions

    # Reports (user-submitted content/user reports)
    REPORTS_MANAGE = "reports.manage"

    # System-level (reserved for SUPER_ADMIN in practice, but modelled so a
    # trusted admin could be granted read-only visibility in the future)
    SYSTEM_SETTINGS = "system.settings"


# Roles a plain ADMIN (even with USERS_MANAGE) is NEVER allowed to grant or
# revoke via the self-service admin endpoints. Only a SUPER_ADMIN may move
# a user into or out of these roles.
STAFF_ROLES: frozenset[UserRole] = frozenset(
    {UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN}
)

# Simple rank so "can A act on B" checks are one comparison instead of a
# scattered pile of `if role == ...` conditions. Higher number = more power.
ROLE_RANK: dict[UserRole, int] = {
    UserRole.READER: 0,
    UserRole.STUDENT: 0,
    UserRole.PARENT: 0,
    UserRole.WRITER: 0,
    UserRole.TEACHER: 0,
    UserRole.MODERATOR: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPER_ADMIN: 3,
}


def is_admin_tier(role: UserRole) -> bool:
    """True for ADMIN and SUPER_ADMIN (the two roles that can hold admin
    permissions / pass through admin-gated dependencies)."""
    return role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}


def outranks(actor_role: UserRole, target_role: UserRole) -> bool:
    """Whether `actor_role` is strictly senior to `target_role`."""
    return ROLE_RANK[actor_role] > ROLE_RANK[target_role]

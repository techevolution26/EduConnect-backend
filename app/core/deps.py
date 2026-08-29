from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Permission, is_admin_tier
from app.core.security import decode_access_token
from app.models.permission import AdminPermission
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account was not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )

    return user


def get_optional_current_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if not token:
        return None

    payload = decode_access_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")

    if not user_id:
        return None

    user = db.get(User, user_id)

    if not user or not user.is_active:
        return None

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return dependency


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Any admin-tier user (ADMIN or SUPER_ADMIN).

    FIX: previously this checked `role != UserRole.ADMIN`, which silently
    excluded SUPER_ADMIN from every admin-gated endpoint in the platform --
    the super-admin role was, in effect, powerless. Use `is_admin_tier`
    instead of a raw equality check anywhere a role hierarchy is involved.

    NOTE: this dependency only confirms "is this an admin-tier account".
    It does NOT check granular permissions. Endpoints that should be
    restricted to admins holding a *specific* capability should use
    `require_permission(...)` below instead -- `require_admin` is now
    reserved for actions every admin-tier account may do regardless of
    their granted permissions (e.g. viewing their own permission set).
    """
    if not is_admin_tier(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )

    return current_user


def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Reserved for the handful of actions only the super admin tier may
    perform: granting/revoking admin permissions, promoting/demoting staff
    roles (MODERATOR/ADMIN/SUPER_ADMIN), and system settings."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access is required.",
        )

    return current_user


def require_permission(*permissions: Permission) -> Callable[..., User]:
    """
    Build a dependency that requires the caller to hold ALL of the given
    permissions.

    SUPER_ADMIN always passes (implicitly holds every permission).
    ADMIN passes only if they have a matching AdminPermission row for each
    requested permission. Any other role is rejected outright.

    This is the primary mechanism for "factor admins down to specific
    functions" -- e.g.:

        @router.post("/categories", ...)
        def create_new_category(
            current_user: Annotated[User, Depends(require_permission(Permission.CATALOG_MANAGE))],
            ...
        )

    only allows admins who were explicitly granted CATALOG_MANAGE (plus
    the super admin, always).
    """

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user

        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access is required.",
            )

        needed = {p.value for p in permissions}
        granted = set(
            db.scalars(
                select(AdminPermission.permission).where(
                    AdminPermission.user_id == current_user.id,
                    AdminPermission.permission.in_(needed),
                )
            ).all()
        )

        if not needed.issubset(granted):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permission for this action.",
            )

        return current_user

    return dependency


def require_role_or_permission(
    role: UserRole, *permissions: Permission
) -> Callable[..., User]:
    """
    Composite dependency: passes if the caller either holds the given
    fixed role (e.g. MODERATOR, which has a built-in, non-revocable
    capability) OR is an admin-tier account holding all of the given
    granular permissions (SUPER_ADMIN always passes; ADMIN needs the
    matching AdminPermission rows).

    Used for endpoints like content moderation, which both MODERATOR
    (by role) and a scoped ADMIN (granted CONTENT_MODERATE) should reach.
    """
    permission_dependency = require_permission(*permissions)

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> User:
        if current_user.role == role:
            return current_user

        return permission_dependency(current_user=current_user, db=db)

    return dependency


def require_moderator_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """FIX: previously excluded SUPER_ADMIN for the same reason as
    require_admin above."""
    if current_user.role != UserRole.MODERATOR and not is_admin_tier(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin access is required.",
        )

    return current_user


def require_writer_teacher_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """FIX: previously excluded SUPER_ADMIN for the same reason as
    require_admin above."""
    if current_user.role not in {UserRole.WRITER, UserRole.TEACHER} and not is_admin_tier(
        current_user.role
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writer, teacher, or admin access is required.",
        )

    return current_user

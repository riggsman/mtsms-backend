"""Branch-based data scoping for multi-campus tenants."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.role import UserRole
from app.models.user import User
from app.models.tenant_settings import TenantSettings
from app.helpers.user_roles import user_has_role, user_is_system_admin


def is_branches_enabled(db: Session, institution_id: Optional[int]) -> bool:
    if not institution_id:
        return False
    ts = (
        db.query(TenantSettings)
        .filter(TenantSettings.institution_id == institution_id)
        .first()
    )
    return bool(ts and getattr(ts, "branches_enabled", False))


def effective_branch_scope_id(db: Session, current_user: User) -> Optional[int]:
    """
    Returns branch_id to filter listings by, or None = no extra branch filter (see all).

    - System roles: no branch filter.
    - Tenant super_admin: no branch filter (sees all campuses).
    - Other tenant users when branches_enabled: filter by their branch_id if set.
    """
    if not current_user:
        return None
    if user_is_system_admin(current_user):
        return None
    if user_has_role(current_user, UserRole.SUPER_ADMIN.value):
        return None
    inst_id = current_user.institution_id
    if not is_branches_enabled(db, inst_id):
        return None
    bid = getattr(current_user, "branch_id", None)
    return bid if bid is not None else None
